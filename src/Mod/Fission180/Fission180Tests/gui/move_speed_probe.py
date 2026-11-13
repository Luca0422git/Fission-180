# SPDX-License-Identifier: LGPL-2.1-or-later
"""Measuring how a dragged Move/Copy handle feels (scenario move_speed.py, and the same probe on
any design): a drag at a hand's pace with real mouse events, and what the 3D view drew meanwhile.

HandDrag   the button goes down on a handle; every EVERY_MS (a 125 Hz mouse) the pointer is
           where a hand moving at a steady speed is at that moment (a move the program could
           not take in time is folded into the next, as Qt folds a real mouse's moves); at the
           end it stays still with the button down until the app has caught up, then lets go.
Probe      during the drag: every frame the 3D view draws (its time and where the moved body is
           drawn in it, read from the scene: the shown step's shape and the transform node of
           its view), a 2 ms heartbeat (a gap is a time the program did not run), the values
           the handle gave the dialog, how long each frame took to draw, and (optionally)
           a cProfile of everything Python ran from the press to the exact result.

summary() gives, in milliseconds:
  step        the time between two frames that showed the body somewhere new while the hand
              moved (median, 90th percentile, worst): the frame time of the live movement
  lag         how far the drawn body was behind the hand, in time (median, worst)
  frames      every frame drawn while the hand moved (median gap)
  draw        how long a frame took to draw (median): the 3D view's own drawing
  between     from one frame to the start of the next one's drawing (median): the work done
              for the mouse in between (Fission 180's and FreeCAD's), when the hand keeps moving
  blocked     the longest time the program did not run while the hand moved
  release     from the release until the exact result was shown (the shape built at the final
              value, nothing drawn moved by a transform any more)
and counts: moves sent, values the dialog took, frames, frames that showed the body move.
Not a scenario itself.
"""

import cProfile
import io
import pstats
import statistics
import time

import FreeCAD as App
from PySide import QtCore, QtGui, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import harness as h

EVERY_MS = 8  # a 125 Hz mouse


def drawn_transform(obj):
    """The placement the 3D view draws `obj`'s geometry with now (its view's transform node,
    the first SoTransform under its root), or None."""
    try:
        from pivy import coin

        root = obj.ViewObject.RootNode
        for i in range(root.getNumChildren()):
            node = root.getChild(i)
            if node.isOfType(coin.SoTransform.getClassTypeId()):
                x, y, z = node.translation.getValue().getValue()
                q = node.rotation.getValue().getValue()
                return App.Placement(App.Vector(x, y, z), App.Rotation(*q))
    except Exception:
        return None
    return None


class _Centers:
    """Two points of an object's shape (the middle of its box and its first corner) in the
    coordinates its view tessellated it in (its Placement taken out), kept per shape: a
    solid of 8,500 faces is not measured every frame."""

    def __init__(self):
        self.known = {}

    def points(self, obj):
        shape = obj.Shape
        if shape.isNull():
            return None
        try:
            key = (obj.Name, shape.hashCode())
        except Exception:
            key = None
        if key is not None and key in self.known:
            return self.known[key]
        back = shape.Placement.inverse()
        found = [back.multVec(shape.BoundBox.Center)]
        if shape.Vertexes:
            found.append(back.multVec(shape.Vertexes[0].Point))
        if key is not None:
            self.known[key] = found
        return found

    def local(self, obj):
        found = self.points(obj)
        return found[0] if found else None


def drawn_placement(obj):
    """The placement the 3D view draws `obj`'s geometry with, in design coordinates: its own
    view's transform node and those of the bodies and components around it."""
    place = drawn_transform(obj) or App.Placement(obj.Placement)
    try:
        parent = obj.getParentGeoFeatureGroup()
    except Exception:
        parent = None
    while parent is not None:
        outer = drawn_transform(parent)
        if outer is None:
            outer = App.Placement(parent.Placement)
        place = outer.multiply(place)
        try:
            parent = parent.getParentGeoFeatureGroup()
        except Exception:
            parent = None
    return place


def drawn_points(obj, centers):
    """Where the 3D view draws the two points of `obj` (_Centers), design coordinates."""
    found = centers.points(obj)
    if not found:
        return None
    place = drawn_placement(obj)
    return [place.multVec(p) for p in found]


def drawn_center(obj, centers):
    """Where the 3D view draws the middle of `obj`'s shape (design coordinates)."""
    found = drawn_points(obj, centers)
    return found[0] if found else None


def shown_object(body):
    """The object the 3D view draws a body with (its Tip)."""
    return getattr(body, "Tip", None) or body


class HandDrag:
    """Press at widget pixel `start`, the hand moves to `end` in `duration_ms` (a pointer
    position every EVERY_MS), holds still until the app has caught up, lets go. `path(t)`,
    t from 0 to 1, may replace the straight line (a turn handle's arc). self.done at the end;
    self.moves: [(time, t)] of each move sent."""

    def __init__(self, start, end, duration_ms=1000, path=None, every_ms=EVERY_MS):
        self.start, self.end = start, end
        self.duration = duration_ms / 1000.0
        self.path = path
        self.every_ms = every_ms
        self.moves = []
        self.done = False
        self.error = None
        self.on_moved_all = None  # called once the last move was sent (the hand stops)
        self.on_hold = None  # called right before the release (the app has caught up)
        self.t_press = self.t_first = self.t_last = self.t_release = None
        self._last_pos = None
        self.timer = None

    def _pos(self, t):
        if self.path is not None:
            p = self.path(t)
            return QtCore.QPointF(p.x(), p.y())
        return QtCore.QPointF(
            self.start.x() + (self.end.x() - self.start.x()) * t,
            self.start.y() + (self.end.y() - self.start.y()) * t,
        )

    def run(self):
        h.BUSY.add(self)
        self.widget = h.gl_widget()
        h.press_pace()
        h.move(self.start)
        QtTest.QTest.mousePress(self.widget, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, self.start)
        QtWidgets.QApplication.processEvents()
        self.t_press = time.perf_counter()
        self.timer = QtCore.QTimer()
        self.timer.setTimerType(QtCore.Qt.PreciseTimer)
        self.timer.setInterval(self.every_ms)
        self.timer.timeout.connect(self._tick)
        self._t0 = None
        self.timer.start()  # input pace: a 125 Hz mouse

    def _tick(self):
        try:
            now = time.perf_counter()
            if self._t0 is None:
                self._t0 = now
            t = min(1.0, (now - self._t0) / self.duration)
            pos = self._pos(t)
            key = (round(pos.x(), 3), round(pos.y(), 3))
            if key != self._last_pos:
                self._last_pos = key
                event = QtGui.QMouseEvent(
                    QtCore.QEvent.MouseMove,
                    pos,
                    QtCore.QPointF(self.widget.mapToGlobal(pos.toPoint())),
                    QtCore.Qt.NoButton,
                    QtCore.Qt.LeftButton,
                    QtCore.Qt.NoModifier,
                )
                QtWidgets.QApplication.sendEvent(self.widget, event)
                sent = time.perf_counter()
                if self.t_first is None:
                    self.t_first = sent
                self.t_last = sent
                self.moves.append((sent, t))
            if t >= 1.0:
                self.timer.stop()
                if self.on_moved_all is not None:
                    self.on_moved_all()
                h.when(
                    h._calm(ignore_input=True),
                    self._release,
                    "the app to catch up with the held drag",
                    timeout_s=120,
                )
        except Exception as exc:
            self.error = str(exc)
            self.timer.stop()
            self._release()

    def _release(self):
        if self.on_hold is not None:
            try:
                self.on_hold()
            except Exception as exc:
                self.error = str(exc)
        try:
            last = self._pos(1.0)
            QtTest.QTest.mouseRelease(
                self.widget,
                QtCore.Qt.LeftButton,
                QtCore.Qt.NoModifier,
                QtCore.QPoint(int(round(last.x())), int(round(last.y()))),
            )
            self.t_release = time.perf_counter()
            QtWidgets.QApplication.processEvents()
        except Exception as exc:
            self.error = self.error or str(exc)
        self.done = True
        h.BUSY.discard(self)


class Probe:
    """What happens during one drag (see the module). `watched`: the objects whose drawn
    middle is followed (the shown steps of the moved bodies; the first one is measured);
    `axis`: the design direction the drag moves them along (None: the distance from where they
    started); `handle`: the dragged handle (its on_drag is wrapped to record the values)."""

    def __init__(self, watched, axis=None, handle=None, profile=False, profile_moving=False):
        self.watched = list(watched)
        self.axis = App.Vector(axis) if axis is not None else None
        self.centers = _Centers()
        self.frames = []  # (time, drawn offset of the first watched object)
        self.paints = []  # time a paint of the 3D view began
        self.draws = []  # how long each frame took to draw (paint to swap)
        self.beats = []
        self.taken = []  # (time, value) the handle gave
        self.start = self._now_points()
        self.handle = handle
        self._saved_drag = None
        if handle is not None and getattr(handle, "on_drag", None) is not None:
            self._saved_drag = handle.on_drag
            probe = self

            def drag(*args):
                probe.taken.append((time.perf_counter(), args[-1]))
                return probe._saved_drag(*args)

            handle.on_drag = drag
        self.gl = h.gl_widget()
        self.gl.frameSwapped.connect(self._frame)
        self._paint_filter = _PaintTimes(self)
        self.gl.installEventFilter(self._paint_filter)
        self.timer = QtCore.QTimer()
        self.timer.setTimerType(QtCore.Qt.PreciseTimer)
        self.timer.setInterval(2)
        self.timer.timeout.connect(lambda: self.beats.append(time.perf_counter()))
        self.timer.start()
        self.profiler = cProfile.Profile() if (profile or profile_moving) else None
        self.profile_moving = profile_moving
        if self.profiler is not None:
            self.profiler.enable()
        self.exact_at = None
        self.held = None  # the drawn points of every watched object right before the release
        self.recomputes = []  # when a design was recomputed during the drag
        probe = self

        class _Recomputes:
            def slotRecomputedDocument(self, doc):
                probe.recomputes.append(time.perf_counter())

        self._observer = _Recomputes()
        App.addDocumentObserver(self._observer)

    def hold(self):
        """The app caught up with the hand, the button still down: what is drawn now."""
        self.held = self.points_now()

    def points_now(self):
        return [drawn_points(obj, self.centers) for obj in self.watched]

    def _now_points(self):
        obj = self.watched[0] if self.watched else None
        if obj is None:
            return None
        try:
            return drawn_points(obj, self.centers)
        except Exception:
            return None

    def offset(self):
        """How far the first watched object is drawn from where it was at the start (mm):
        its middle along the axis when one was given, else the farther its two points moved
        (a turn about the middle leaves the middle where it was)."""
        now = self._now_points()
        if not now or not self.start:
            return None
        if self.axis is not None:
            return (now[0] - self.start[0]).dot(self.axis)
        return max((a - c).Length for a, c in zip(now, self.start))

    def _frame(self):
        t = time.perf_counter()
        try:
            self.frames.append((t, self.offset()))
        except Exception:
            self.frames.append((t, None))
        if self.paints:
            self.draws.append(t - self.paints[-1])

    def moving_done(self):
        """The hand stopped: a profile of the moving only ends here."""
        if self.profiler is not None and self.profile_moving:
            self.profiler.disable()

    def stop(self):
        if self.profiler is not None:
            self.profiler.disable()
        try:
            App.removeDocumentObserver(self._observer)
        except Exception:
            pass
        self.timer.stop()
        try:
            self.gl.frameSwapped.disconnect(self._frame)
        except Exception:
            pass
        try:
            self.gl.removeEventFilter(self._paint_filter)
        except Exception:
            pass
        if self._saved_drag is not None and self.handle is not None:
            try:
                self.handle.on_drag = self._saved_drag
            except Exception:
                pass

    def profile_lines(self, count=35, key="cumulative"):
        if self.profiler is None:
            return []
        out = io.StringIO()
        pstats.Stats(self.profiler, stream=out).sort_stats(key).print_stats(count)
        return [ln for ln in out.getvalue().splitlines() if ln.strip()]

    def summary(self, drag, final=None, lag=True):
        """The numbers of this drag (see the module); `final`: how far the drag moved the
        body along the axis (mm; default: the last value the handle gave); lag False: no lag
        (a turn: its angle and the distance a point moved do not compare)."""
        t0, t1 = drag.t_first, drag.t_last
        if t0 is None or t1 is None:
            return {"error": "no move was sent"}
        if final is None and lag:
            final = self.taken[-1][1] if self.taken else None
        moving = [(t, d) for t, d in self.frames if t0 <= t <= t1 + 0.002]
        gaps = [b[0] - a[0] for a, b in zip(moving, moving[1:])]
        steps = []
        last_d = self.frames[0][1] if self.frames else None
        for t, d in self.frames:
            if t < t0:
                last_d = d
                continue
            if t > t1 + 0.002:
                break
            if d is not None and (last_d is None or abs(d - last_d) > 1e-6):
                steps.append(t)
            last_d = d
        step_gaps = [b - a for a, b in zip([t0] + steps, steps)]
        lags = []
        span = max(t1 - t0, 1e-6)
        if final:
            for t, d in moving:
                if d is None:
                    continue
                share = max(0.0, min(1.0, d / final))
                lags.append(t - (t0 + span * share))
        beats = [b for b in self.beats if t0 <= b <= t1 + 0.002]
        blocked = max((b - a for a, b in zip(beats, beats[1:])), default=None)
        release = None
        if drag.t_release is not None and self.exact_at is not None:
            release = max(0.0, self.exact_at - drag.t_release)
        caught = None
        if final:
            for t, d in self.frames:
                if t >= t1 and d is not None and abs(d - final) < max(0.05, 0.01 * abs(final)):
                    caught = t - t1
                    break
        draws = [d for t, d in zip([f[0] for f in self.frames], self.draws) if t0 <= t <= t1]
        between = []
        swaps = [f[0] for f in self.frames]
        for prev, nxt in zip(swaps, swaps[1:]):
            if not (t0 <= nxt <= t1 + 0.002):
                continue
            starts = [p for p in self.paints if prev < p < nxt]
            if starts:
                between.append(starts[-1] - prev)

        def ms(values, how):
            if not values:
                return None
            values = sorted(values)
            if how == "median":
                v = statistics.median(values)
            elif how == "p90":
                v = values[min(len(values) - 1, int(round(0.9 * (len(values) - 1))))]
            else:
                v = values[-1]
            return round(v * 1000.0, 1)

        return {
            "recomputes_moving": len([r for r in self.recomputes if t0 <= r <= t1]),
            "moves": len(drag.moves),
            "taken": len([x for x in self.taken if t0 <= x[0] <= t1 + 0.002]),
            "frames": len(moving),
            "body_frames": len(steps),
            "step_median": ms(step_gaps, "median"),
            "step_p90": ms(step_gaps, "p90"),
            "step_worst": ms(step_gaps, "max"),
            "frame_median": ms(gaps, "median"),
            "frame_p90": ms(gaps, "p90"),
            "lag_median": ms(lags, "median"),
            "lag_worst": ms(lags, "max"),
            "draw_median": ms(draws, "median"),
            "between_median": ms(between, "median"),
            "between_p90": ms(between, "p90"),
            "blocked": ms([blocked] if blocked is not None else [], "max"),
            "caught_up": ms([caught] if caught is not None else [], "max"),
            "release": ms([release] if release is not None else [], "max"),
            "stop_to_result": ms([self.exact_at - t1] if self.exact_at is not None else [], "max"),
            "final": final,
            "drag_ms": round(span * 1000.0, 1),
        }


class _PaintTimes(QtCore.QObject):
    """Notes when the 3D view starts painting (its frame ends at frameSwapped)."""

    def __init__(self, probe):
        super().__init__()
        self.probe = probe

    def eventFilter(self, obj, event):
        try:
            if event.type() in (QtCore.QEvent.Paint, QtCore.QEvent.UpdateRequest):
                self.probe.paints.append(time.perf_counter())
        except Exception:
            pass
        return False
