# SPDX-License-Identifier: LGPL-2.1-or-later
"""Drag handles and clickable markers drawn in the 3D view for the CONSTRUCT and INSPECT
dialogs (construct_ui.py, section_ui.py, measure_ui.py).

  LinearHandle  Fusion's blue arrow: drag it along its line to set a distance.
  PathHandle    a blue ball on an edge: drag it along the edge (Plane / Point Along Path).
  PointDots     points drawn as dots that can be clicked (the origin point, snap points).
  Overlay       lines, dots and text drawn over the part (measure results).

Measure's points, its snap points and the balls other dialogs give to click keep one size
on the screen (marker_core): drawn in pixels under FreeCAD's SoShapeScale like the handles.

Like revolve_ui.AngleHandle they are drawn over the part (Fusion's handles are never hidden
by it) and they are not Coin draggers: Coin lets only the nearest object take a click, and
its dragger callbacks run Python without its lock. FreeCAD's own mouse callbacks
(view.addEventCallback, safe) only record where the mouse is; a Qt timer applies it.
Nothing here keeps a FreeCAD-owned Coin node: every node is made and owned here.
"""

import math
import time

import FreeCAD as App
import FreeCADGui as Gui

from . import drag_guard, handle_look, increments, marker_core, taskui, warn
from .compat import QtCore
from .taskui import BoxCarrier
from .neon_scene_core import Live

BLUE = Live((0.30, 0.62, 0.95), "arrow")  # Fusion's manipulator blue
BLUE_ACTIVE = Live((0.55, 0.80, 1.0), "arrow_hot")
TEXT = Live((1.0, 1.0, 1.0), "bright")  # labels in the view
GRAB = {"time": 0.0}  # one press moves one handle
USED = {"time": 0.0}  # when any handle was last pressed, dragged or let go
JUST_USED_S = 0.6


def touch():
    USED["time"] = time.time()


# The release watchers alive: one per handle whose drag is under way (made at the press by
# watch_release, removed at the release). Handles that take the mouse through FreeCAD's
# view callbacks (these handles, Move's triad, Revolve's angle handle, the primitives'
# handles, the curve picker's path handle) all start one, so this is the one place that
# knows "a handle owns this drag": the box selection (selection_ui) must not take it.
WATCHES = set()


def dragging():
    """True while a handle's drag is under way (pressed on the handle, not released yet).
    A watcher left behind by a lost release does not count once the button is up."""
    try:
        if not WATCHES:
            return False
        if not drag_guard.left_held():
            return False
        return any(watch.handle is not None for watch in list(WATCHES))
    except Exception:
        return False


def just_used(seconds=JUST_USED_S):
    """True while a handle is in use and just after. FreeCAD's selection also takes the
    press and the release of a handle's drag as a click on what is under the mouse (the
    face behind the handle, or the face under the mouse where the drag ends): that is not
    a pick. A dialog often makes new handles when a drag ends (the old one's own memory of
    the drag is gone then), so this is remembered here, for every handle."""
    return time.time() - USED["time"] < seconds


def _mouse_ray(view, position):
    from .profile_pick import mouse_ray

    return mouse_ray(view, position)


def _screen(view, point):
    x, y = view.getPointOnViewport(App.Vector(point))
    return float(x), float(y)


def _segment_distance(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    length2 = dx * dx + dy * dy
    t = 0.0 if length2 < 1e-12 else max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / length2))
    return math.hypot(px - (ax + dx * t), py - (ay + dy * t))


class ReleaseWatch:
    """Ends a handle's drag on any left-button release in the application. FreeCAD's
    selection keeps the release of a drag that ends over a face (it selects the face and
    marks the event handled), so a view callback never saw it: the handle stayed "grabbed",
    followed the mouse with no button down and swallowed every later pick. Qt sees every
    release first: this filter is installed while the button is down on the handle."""

    def __init__(self, handle):
        from .compat import QtWidgets

        self.handle = handle
        self.filter = None
        watch = self

        class _Filter(QtCore.QObject):
            def eventFilter(self, obj, event):
                try:
                    if event.type() == QtCore.QEvent.MouseButtonRelease and (
                        event.button() == QtCore.Qt.LeftButton
                    ):
                        watch.released()
                except Exception:
                    pass
                return False

        self.filter = _Filter()
        QtWidgets.QApplication.instance().installEventFilter(self.filter)
        WATCHES.add(self)

    def released(self):
        handle = self.handle
        if handle is not None and getattr(handle, "_drag", False):
            handle._drag = False
            handle._released = True
            handle._last_event = time.time()
            touch()
        self.remove()

    def remove(self):
        from .compat import QtWidgets

        WATCHES.discard(self)
        self.handle = None
        if not WATCHES:
            release_preselection()
        if self.filter is not None:
            try:
                QtWidgets.QApplication.instance().removeEventFilter(self.filter)
            except Exception:
                pass
            # deleted later, never inside its own eventFilter call
            QtCore.QTimer.singleShot(0, self.filter.deleteLater)
            self.filter = None


def watch_release(handle):
    """Start watching for the release of a drag on `handle` (see ReleaseWatch)."""
    old = getattr(handle, "_release_watch", None)
    if old is not None:
        old.remove()
    touch()  # a handle took this press: it is not a pick, nor the start of a box
    try:
        handle._release_watch = ReleaseWatch(handle)
    except Exception as exc:
        handle._release_watch = None
        warn("handle: %s" % exc)
    hold_preselection(getattr(handle, "view", None))


# While a handle is dragged, FreeCAD's preselection is off (move-speed, 2026-11-13): it looked
# for what is under the mouse on every move, a ray through the whole part (4 ms a move on a
# 600-face part, more on bigger ones), and lit the faces the dragged handle passed over;
# Fusion lights nothing while a manipulator is dragged. Switched back on when the last drag
# ends (ReleaseWatch.remove), whatever ended it.
_PRESELECTION = {"root": None, "mode": None}
PRESELECTION_ON = "AUTO"  # FreeCAD's own default (SoFCUnifiedSelection.preselectionMode)


def preselection_mode(root):
    """The name of the 3D view's preselection mode ("AUTO", "ON", "OFF") as a plain string,
    or None when the view has none. (Coin hands the field's value back as an SbString, which
    the field does not take back: 0.1.0-beta.4.0.3 kept it and could never switch the hover
    highlight on again after the first drag of a handle.)"""
    try:
        field = root.getField("preselectionMode")
        if field is None:
            return None
        value = field.get()
        text = value.getString() if hasattr(value, "getString") else str(value)
        return str(text).strip() or None
    except Exception:
        return None


def _set_preselection(root, mode):
    """True when the view's preselection mode is `mode` afterwards."""
    try:
        root.getField("preselectionMode").set(str(mode))
    except Exception:
        return False
    return preselection_mode(root) == str(mode)


def hold_preselection(view=None):
    """Preselection off in `view` (default the active 3D view) until the drags end."""
    if _PRESELECTION["root"] is not None:
        return
    try:
        view = view or Gui.ActiveDocument.ActiveView
        root = view.getSceneGraph()
        mode = preselection_mode(root)
        if mode is None or mode == "OFF":
            return  # nothing to switch off (the person's own choice stays)
        _PRESELECTION["mode"] = mode
        _PRESELECTION["root"] = root
    except Exception:
        return

    def off():  # (not inside the Coin event that pressed the handle)
        try:
            root = _PRESELECTION["root"]
            if root is None or not WATCHES:
                return
            if _set_preselection(root, "OFF"):
                Gui.Selection.clearPreselection()
        except Exception as exc:
            warn("handle: preselection off: %s" % exc)

    QtCore.QTimer.singleShot(0, off)


def release_preselection():
    """Preselection back as it was (the last drag ended)."""
    root, mode = _PRESELECTION["root"], _PRESELECTION["mode"]
    _PRESELECTION["root"] = _PRESELECTION["mode"] = None
    if root is None or not mode:
        return
    try:
        if preselection_mode(root) is None:
            return  # the view went with its design
        if not _set_preselection(root, mode) and not _set_preselection(root, PRESELECTION_ON):
            warn("handle: the hover highlight could not be switched on again (%s)" % mode)
    except Exception as exc:
        warn("handle: preselection back: %s" % exc)


def stop_watching(handle):
    old = getattr(handle, "_release_watch", None)
    if old is not None:
        old.remove()
    handle._release_watch = None


def _rotation_y_to(direction):
    """Rotation that turns +Y (Coin's cylinder/cone axis) onto `direction`."""
    return App.Rotation(App.Vector(0, 1, 0), App.Vector(direction))


class _Handle(BoxCarrier):
    """What LinearHandle and PathHandle share: callbacks, polling, hover colour, and a
    value box when the dialog gives one (taskui.BoxCarrier). They look like Fusion's
    handles and keep their size on the screen (handle_look): `size` is now worked out from
    the zoom at the handle, not given in mm."""

    POLL_MS = 30
    GRAB_PIXELS = 12.0

    def __init__(self, view, on_drag, on_release):
        from pivy import coin

        self.coin = coin
        self.view = view or Gui.ActiveDocument.ActiveView
        self.on_drag = on_drag
        self.on_release = on_release
        self._pending = None
        self._released = False
        self._drag = False
        self._hover = False
        self._painted = None
        self._last_event = 0.0
        self.root = handle_look.top_root(coin)  # over the part, never picked by Coin
        self.paint = None  # the handle's handle_look paint (set by the subclass)
        self.pixels = None  # its handle_look.PixelScale
        self.callbacks = []
        self._timer = QtCore.QTimer()
        self._timer.setInterval(self.POLL_MS)
        self._timer.timeout.connect(self._poll)

    def _start(self):
        self._paint()
        self.view.getSceneGraph().addChild(self.root)
        self.callbacks = [
            ("SoMouseButtonEvent", self.view.addEventCallback("SoMouseButtonEvent", self._button)),
            ("SoLocation2Event", self.view.addEventCallback("SoLocation2Event", self._moved)),
        ]
        self._timer.start()
        self._move_poll = taskui.poll_on_move(self._poll)  # dragged: polled on every mouse move

    def _paint(self):
        state = self._hover or self._drag
        if self._painted == state:
            return
        self._painted = state
        if self.paint is not None:
            self.paint.set(state)

    def screen_point(self):
        """The 3D point the handle's drawing is scaled at (where it stands)."""
        return None

    def _follow_zoom(self):
        point = self.screen_point()
        if self.pixels is not None and point is not None:
            self.pixels.update(self.view, point)

    def hit(self, position):
        return False

    def _press(self, position):
        pass

    def _drag_to(self, position):
        return None

    def _button(self, info):
        try:
            if info.get("Button") != "BUTTON1":
                return
            position = info["Position"]
            if info.get("State") == "DOWN":
                if self.hit(position) and time.time() - GRAB["time"] > 0.05:
                    GRAB["time"] = time.time()
                    self._drag = True
                    self._last_event = time.time()
                    touch()
                    self._press(position)
                    watch_release(self)
            elif self._drag:
                self._drag = False
                self._released = True
                self._last_event = time.time()
                touch()
                stop_watching(self)
        except Exception as exc:
            warn("handle: %s" % exc)

    def _moved(self, info):
        try:
            position = info["Position"]
            if not self._drag:
                self._hover = self.hit(position)
                return
            self._last_event = time.time()
            touch()
            value = self._drag_to(position)
            if value is not None:
                self._pending = value
        except Exception as exc:
            warn("handle: %s" % exc)

    def dragging(self):
        return self._drag

    def box_active(self):
        return bool(self._drag or self._hover)

    def busy(self, seconds=0.6):
        """True while dragging and just after: that click is the handle's, not a pick."""
        return self._drag or time.time() - self._last_event < seconds

    def _apply(self, value):
        pass

    def value(self):
        return None

    def _poll(self):
        try:
            if Gui.ActiveDocument is None:
                self._timer.stop()
                return
            drag_guard.end_lost_drag(self, idle=False)  # its release never came (drag_guard)
            self._paint()
            self._follow_zoom()
            pending = self._pending
            if pending is not None and abs(pending - self.value()) > 1e-9:
                self._apply(pending)
                if self.on_drag:
                    self.on_drag(pending)
            if self._released and not self._drag:
                self._released = False
                self._pending = None
                touch()  # also a release found from Qt's mouse state (pickpanel.Arrow)
                if self.on_release:
                    self.on_release(self.value())
                taskui.handle_released()  # the dialog's waiting rebuild now
            self.follow_box()
        except Exception as exc:
            warn("handle drag: %s" % exc)

    def remove(self):
        stop_watching(self)
        try:
            self._timer.stop()
        except Exception:
            pass
        taskui.drop_poll_on_move(self)
        for kind, callback in self.callbacks:
            try:
                self.view.removeEventCallback(kind, callback)
            except Exception:
                pass
        self.callbacks = []
        try:
            self.view.getSceneGraph().removeChild(self.root)
        except Exception:
            pass
        self.drop_box()


def angle_handle(*args, **kwargs):
    """revolve_ui.AngleHandle (the blue ball turning about a line) whose drag also ends on a
    release FreeCAD's selection kept (see ReleaseWatch)."""
    from .revolve_ui import AngleHandle

    # Incremental Move (navigation bar) steps, the 45-degree snap and Ctrl's free turn are
    # the handle's own (protractor.snap_angle), as for every angle handle.

    class WatchedAngleHandle(AngleHandle):
        def _button(self, info):
            try:
                pressed = info.get("Button") == "BUTTON1" and info.get("State") == "DOWN"
                if pressed and not self._drag and time.time() - GRAB["time"] <= 0.05:
                    return  # an arrow of this dialog took this press (one press, one handle)
            except Exception:
                pass
            was = self._drag
            super()._button(info)
            try:
                if self._drag and not was:
                    GRAB["time"] = time.time()
                    touch()
                    watch_release(self)
                elif was and not self._drag:
                    touch()
                    stop_watching(self)
            except Exception as exc:
                warn("handle: %s" % exc)

        def _moved(self, info):
            super()._moved(info)
            if self._drag:
                touch()

        def remove(self):
            stop_watching(self)
            super().remove()

    return WatchedAngleHandle(*args, **kwargs)


class LinearHandle(_Handle):
    """A blue arrow at origin + direction * value, pointing along `direction`. Drag it to
    change `value` (signed, mm). on_drag(value) while dragging, on_release(value) after.
    `size` (the old arrow size in mm) is no longer used: the arrow is
    handle_look_core.ARROW_PX long on the screen (self.size is that length in mm now)."""

    def __init__(
        self, origin, direction, value, size, on_drag=None, on_release=None, view=None, step=0.0
    ):
        super().__init__(view, on_drag, on_release)
        self.origin = App.Vector(origin)
        self.direction = App.Vector(direction)
        self.direction.normalize()
        self.size_hint = float(size)
        self.step = float(step)
        self._value = float(value)
        self._offset = 0.0
        self._last_pos = None
        coin = self.coin
        self.place = coin.SoTransform()
        self.root.addChild(self.place)
        arrow, self.paint = handle_look.arrow_shape(coin)  # along +Y, in pixels
        self.pixels = handle_look.PixelScale(coin, arrow, self.view, self.base_point())
        self.root.addChild(self.pixels.node)
        self._draw()
        self._start()

    @property
    def size(self):
        """The arrow's length (mm) at its place in the view now."""
        return handle_look.mm(self.view, self.base_point(), handle_look.core.ARROW_PX)

    def screen_point(self):
        return self.base_point()

    def base_point(self):
        return self.origin + self.direction * self._value

    def tip_point(self):
        return self.base_point() + self.direction * self.size

    def box_geometry(self):
        """The arrow from its foot (the value's point) to its tip, as wide as its head."""
        base = self.base_point()
        tip = self.tip_point()
        width = handle_look.mm(self.view, base, handle_look.core.half_width_px("arrow"))
        return (base + tip) * 0.5, base, tip, width

    def value(self):
        return self._value

    def set_value(self, value):
        self._value = float(value)
        self._pending = None
        self._draw()

    def set_line(self, origin, direction):
        self.origin = App.Vector(origin)
        self.direction = App.Vector(direction)
        self.direction.normalize()
        self._draw()

    def _apply(self, value):
        self._value = float(value)
        self._draw()

    def _draw(self):
        p = self.base_point()
        self.place.translation.setValue(p.x, p.y, p.z)
        self.place.rotation.setValue(*_rotation_y_to(self.direction).Q)

    def hit(self, position):
        try:
            px, py = float(position[0]), float(position[1])
            ax, ay = _screen(self.view, self.base_point())
            bx, by = _screen(self.view, self.tip_point())
            reach = handle_look.core.grab_px("arrow", at_least=self.GRAB_PIXELS)
            return _segment_distance(px, py, ax, ay, bx, by) <= reach
        except Exception:
            return False

    def _along(self, position):
        """Distance along the line to where it passes closest to the mouse ray, or None
        when the line points (nearly) at the eye."""
        point, ray = _mouse_ray(self.view, tuple(position))
        d = self.direction
        b = d.dot(ray)
        denom = 1.0 - b * b
        if denom < 0.02:
            return None
        w0 = self.origin - point
        return (b * ray.dot(w0) - d.dot(w0)) / denom

    def _press(self, position):
        self._last_pos = (float(position[0]), float(position[1]))
        start = self._along(position)
        self._offset = 0.0 if start is None else start - self._value

    def _drag_to(self, position):
        t = self._along(position)
        if t is None:  # edge-on: follow the mouse along the arrow on screen
            if self._last_pos is None:
                return None
            ax, ay = _screen(self.view, self.base_point())
            bx, by = _screen(self.view, self.tip_point())
            tx, ty = bx - ax, by - ay
            length2 = tx * tx + ty * ty
            if length2 < 1e-6:
                return None
            dx = float(position[0]) - self._last_pos[0]
            dy = float(position[1]) - self._last_pos[1]
            value = self._value + (dx * tx + dy * ty) / length2 * self.size
        else:
            # Incremental Move (navigation bar): the arrow goes in steps of the increment
            value = increments.linear(t - self._offset)
        self._last_pos = (float(position[0]), float(position[1]))
        if self.step > 0:
            value = round(value / self.step) * self.step
        return value


class PathHandle(_Handle):
    """A blue ball on `edge` (a Part.Edge in global coordinates) at curve parameter
    `parameter`; drag it along the edge. Values are curve parameters. The ball keeps its
    size on the screen (handle_look); `size` (its old size in mm) is no longer used."""

    def __init__(self, edge, parameter, size, on_drag=None, on_release=None, view=None):
        super().__init__(view, on_drag, on_release)
        self.edge = edge
        self.size_hint = float(size)
        self._value = float(parameter)
        coin = self.coin
        self.place = coin.SoTranslation()
        self.root.addChild(self.place)
        ball, self.paint = handle_look.ball_shape(coin)
        self.pixels = handle_look.PixelScale(coin, ball, self.view, self.point())
        self.root.addChild(self.pixels.node)
        self._probe = None
        self._draw()
        self._start()

    def screen_point(self):
        return self.point()

    def value(self):
        return self._value

    def set_value(self, parameter):
        self._value = float(parameter)
        self._pending = None
        self._draw()

    def set_edge(self, edge):
        self.edge = edge
        self._draw()

    def point(self):
        return self.edge.valueAt(self._value)

    def box_geometry(self):
        point = self.point()
        return (
            point,
            point,
            point,
            handle_look.mm(self.view, point, handle_look.core.half_width_px("ball")),
        )

    def _apply(self, value):
        self._value = float(value)
        self._draw()

    def _draw(self):
        p = self.point()
        self.place.translation.setValue(p.x, p.y, p.z)

    def hit(self, position):
        try:
            bx, by = _screen(self.view, self.point())
            reach = handle_look.core.grab_px("ball", at_least=self.GRAB_PIXELS)
            return math.hypot(float(position[0]) - bx, float(position[1]) - by) <= reach
        except Exception:
            return False

    def _drag_to(self, position):
        import Part

        point, ray = _mouse_ray(self.view, tuple(position))
        box = self.edge.BoundBox
        reach = 10 * max(box.DiagonalLength, 1.0) + (box.Center - point).Length
        line = Part.LineSegment(point - ray * reach, point + ray * reach).toShape()
        _dist, pairs, _info = self.edge.distToShape(line)
        if not pairs:
            return None
        nearest = pairs[0][0]
        u = self.edge.Curve.parameter(nearest)
        first, last = self.edge.FirstParameter, self.edge.LastParameter
        return min(max(u, first), last)


class PointDots:
    """Points drawn as dots that light up under the mouse and can be clicked:
    on_pick(key) for a click within a few pixels. dots: [(key, App.Vector, colour)].

    size: a ball of 0.25 * size mm (it grows and shrinks with the zoom). pixels: a ball of
    that radius on the screen instead, the same at every zoom (they are clicked within
    PICK_PIXELS of their middle, also a size on the screen); flat: drawn as a flat dot with a
    light rim in exactly its colour (Measure's points, marker_core) rather than a shaded
    ball."""

    PICK_PIXELS = 9.0

    def __init__(self, view, dots, on_pick, size=1.0, pixels=None, flat=False):
        from pivy import coin

        self.coin = coin
        self.view = view
        self.on_pick = on_pick
        self.size = float(size)
        self.pixels = None if pixels is None else float(pixels)
        self.flat = bool(flat) and self.pixels is not None
        self.scales = []  # (PixelScale, point): kept right by hand only without SoShapeScale
        self.dots = []
        self.hovered = None
        self.enabled = True
        self.last_click = 0.0
        self.root = coin.SoAnnotation()
        pick = coin.SoPickStyle()
        pick.style = coin.SoPickStyle.UNPICKABLE
        self.root.addChild(pick)
        self.switch = coin.SoSwitch()
        self.switch.whichChild = coin.SO_SWITCH_ALL
        self.root.addChild(self.switch)
        for key, point, color in dots:
            self.dots.append(self._dot(key, point, color))
        view.getSceneGraph().addChild(self.root)
        self.callbacks = [
            ("SoMouseButtonEvent", view.addEventCallback("SoMouseButtonEvent", self._button)),
            ("SoLocation2Event", view.addEventCallback("SoLocation2Event", self._moved)),
        ]

    def _dot(self, key, point, color):
        coin = self.coin
        sep = coin.SoSeparator()
        move = coin.SoTranslation()
        move.translation.setValue(point.x, point.y, point.z)
        if self.flat:
            shape, paint = handle_look.marker_shape(
                coin, color, self.pixels, marker_core.RIM_PX, marker_core.RIM
            )
            sep.addChild(move)
            sep.addChild(self._in_pixels(shape, point))
        else:
            paint = coin.SoMaterial()
            paint.diffuseColor.setValue(*color)
            paint.emissiveColor.setValue(*[c * 0.6 for c in color])
            ball = coin.SoSphere()
            sep.addChild(paint)
            sep.addChild(move)
            if self.pixels is None:
                ball.radius.setValue(0.25 * self.size)
                sep.addChild(ball)
            else:
                ball.radius.setValue(self.pixels)
                sep.addChild(self._in_pixels(ball, point))
        self.switch.addChild(sep)
        return [key, App.Vector(point), color, paint]

    def _in_pixels(self, shape, point):
        pixels = handle_look.PixelScale(self.coin, shape, self.view, point)
        if pixels.scale is not None:  # no SoShapeScale: kept for the zoom on each mouse move
            self.scales.append((pixels, App.Vector(point)))
        return pixels.node

    def _paint(self, dot, color):
        if self.flat:
            dot[3].rgb.setValue(*color)
        else:
            dot[3].diffuseColor.setValue(*color)
            dot[3].emissiveColor.setValue(*[c * 0.6 for c in color])

    def set_enabled(self, enabled):
        self.enabled = bool(enabled)
        self.switch.whichChild = self.coin.SO_SWITCH_ALL if enabled else self.coin.SO_SWITCH_NONE

    def dot_at(self, position):
        if not self.enabled:
            return None
        try:
            px, py = float(position[0]), float(position[1])
        except Exception:
            return None
        best = None
        for dot in self.dots:
            try:
                x, y = _screen(self.view, dot[1])
            except Exception:
                continue
            d = math.hypot(px - x, py - y)
            if d <= self.PICK_PIXELS and (best is None or d < best[0]):
                best = (d, dot)
        return best[1] if best else None

    def _moved(self, info):
        try:
            for pixels, point in self.scales:
                pixels.update(self.view, point)
            hit = self.dot_at(info["Position"])
            if hit is self.hovered:
                return
            for dot, on in ((self.hovered, False), (hit, True)):
                if dot is not None:
                    self._paint(dot, BLUE_ACTIVE if on else dot[2])
            self.hovered = hit
        except Exception as exc:
            warn("point hover: %s" % exc)

    def _button(self, info):
        try:
            if info.get("Button") != "BUTTON1" or info.get("State") != "DOWN":
                return
            hit = self.dot_at(info["Position"])
            if hit is not None:
                self.last_click = time.time()
                key = hit[0]
                QtCore.QTimer.singleShot(0, lambda: self.on_pick(key))
        except Exception as exc:
            warn("point pick: %s" % exc)

    def clicked_recently(self, seconds=0.6):
        return time.time() - self.last_click < seconds

    def remove(self):
        for kind, callback in self.callbacks:
            try:
                self.view.removeEventCallback(kind, callback)
            except Exception:
                pass
        self.callbacks = []
        try:
            self.view.getSceneGraph().removeChild(self.root)
        except Exception:
            pass


class Overlay:
    """Lines, dots and labels drawn over the part (not clickable). clear() empties it.

    marker() and label() keep one size on the screen at every zoom (marker_core); a label is
    put beside its line again when the view turns (a poll, while there is a label)."""

    POLL_MS = 50

    def __init__(self, view=None):
        from pivy import coin

        self.coin = coin
        self.view = view or Gui.ActiveDocument.ActiveView
        self.root = coin.SoAnnotation()
        pick = coin.SoPickStyle()
        pick.style = coin.SoPickStyle.UNPICKABLE
        self.root.addChild(pick)
        self.content = coin.SoSeparator()
        self.root.addChild(self.content)
        self.view.getSceneGraph().addChild(self.root)
        self.labels = []  # the _Labels shown (the scenarios read where they are)
        self.scales = []  # (PixelScale, point) kept right by hand: only without SoShapeScale
        self._timer = None
        self._failed = False

    def clear(self):
        self.content.removeAllChildren()
        self.labels = []
        self.scales = []
        if self._timer is not None:
            self._timer.stop()

    def marker(self, p, color=BLUE, pixels=marker_core.DOT_RADIUS_PX, rim=marker_core.RIM_PX):
        """A point as a flat dot of `pixels` radius on the screen at every zoom, in exactly
        `color`, with a thin light rim (marker_core)."""
        coin = self.coin
        sep = coin.SoSeparator()
        move = coin.SoTranslation()
        move.translation.setValue(p.x, p.y, p.z)
        shape, _paint = handle_look.marker_shape(coin, color, pixels, rim, marker_core.RIM)
        sep.addChild(move)
        sep.addChild(self._in_pixels(shape, p))
        self.content.addChild(sep)

    def label(self, a, b, text, clear, colours):
        """The distance from a to b written in a box beside its line, clear of dots of
        radius `clear` (pixels) at a and b. colours: (backing, rim, text) as hex
        (marker_core.label_colours). Returns the _Label."""
        label = _Label(self, a, b, text, clear, colours)
        self.content.addChild(label.node)
        self.labels.append(label)
        self._poll_on()
        return label

    def _in_pixels(self, shape, point):
        pixels = handle_look.PixelScale(self.coin, shape, self.view, point)
        if pixels.scale is not None:  # no SoShapeScale: kept for the zoom by the poll
            self.scales.append((pixels, App.Vector(point)))
            self._poll_on()
        return pixels.node

    def _poll_on(self):
        if self._failed:
            return
        if self._timer is None:
            self._timer = QtCore.QTimer()
            self._timer.setInterval(self.POLL_MS)
            self._timer.timeout.connect(self._poll)
        if not self._timer.isActive():
            self._timer.start()

    def _poll(self):
        try:
            if not self.labels and not self.scales:
                self._timer.stop()
                return
            for pixels, point in self.scales:
                pixels.update(self.view, point)
            for label in self.labels:
                label.place()
        except Exception as exc:
            # (the view went with its design): stop asking it
            self._failed = True
            try:
                self._timer.stop()
            except Exception:
                pass
            warn("labels in the 3D view: %s" % exc)

    def _material(self, color):
        material = self.coin.SoMaterial()
        material.diffuseColor.setValue(*color)
        material.emissiveColor.setValue(*color)
        return material

    def line(self, a, b, color=BLUE, width=2.0, dashed=False):
        coin = self.coin
        sep = coin.SoSeparator()
        style = coin.SoDrawStyle()
        style.lineWidth.setValue(width)
        if dashed:
            style.linePattern.setValue(0xF0F0)
        coords = coin.SoCoordinate3()
        coords.point.setValues(0, 2, [(a.x, a.y, a.z), (b.x, b.y, b.z)])
        lines = coin.SoLineSet()
        lines.numVertices.setValue(2)
        sep.addChild(self._material(color))
        sep.addChild(style)
        sep.addChild(coords)
        sep.addChild(lines)
        self.content.addChild(sep)

    def polyline(self, points, color=BLUE, width=2.0):
        coin = self.coin
        if len(points) < 2:
            return
        sep = coin.SoSeparator()
        style = coin.SoDrawStyle()
        style.lineWidth.setValue(width)
        coords = coin.SoCoordinate3()
        coords.point.setValues(0, len(points), [(p.x, p.y, p.z) for p in points])
        lines = coin.SoLineSet()
        lines.numVertices.setValue(len(points))
        sep.addChild(self._material(color))
        sep.addChild(style)
        sep.addChild(coords)
        sep.addChild(lines)
        self.content.addChild(sep)

    def dot(self, p, radius, color=BLUE):
        coin = self.coin
        sep = coin.SoSeparator()
        move = coin.SoTranslation()
        move.translation.setValue(p.x, p.y, p.z)
        ball = coin.SoSphere()
        ball.radius.setValue(radius)
        sep.addChild(self._material(color))
        sep.addChild(move)
        sep.addChild(ball)
        self.content.addChild(sep)

    def text(self, p, text, color=TEXT):
        coin = self.coin
        sep = coin.SoSeparator()
        move = coin.SoTranslation()
        move.translation.setValue(p.x, p.y, p.z)
        font = coin.SoFont()
        font.size.setValue(14.0)
        label = coin.SoText2()
        label.string.setValue(text)
        sep.addChild(self._material(color))
        sep.addChild(move)
        sep.addChild(font)
        sep.addChild(label)
        self.content.addChild(sep)

    def remove(self):
        if self._timer is not None:
            self._timer.stop()
        self.labels = []
        self.scales = []
        try:
            self.view.getSceneGraph().removeChild(self.root)
        except Exception:
            pass


def _label_picture(text, colours, ratio):
    """The label's picture, drawn by Qt: `text` in the window's font on a rounded box (colours:
    backing, rim, text as hex), at the screen's pixel ratio (Coin shows a picture pixel for
    pixel). Returns (RGBA bytes, bottom row first as Coin wants them, width, height in the
    screen's own pixels)."""
    from .compat import QtGui, QtWidgets

    backing, rim, ink = colours
    font = QtGui.QFont(QtWidgets.QApplication.font())
    font.setPixelSize(max(1, int(round(marker_core.LABEL_FONT_PX * ratio))))
    font.setWeight(QtGui.QFont.Weight.DemiBold)
    metrics = QtGui.QFontMetricsF(font)
    w, h = marker_core.label_size(metrics.horizontalAdvance(text) / ratio, metrics.height() / ratio)
    width, height = int(math.ceil(w * ratio)), int(math.ceil(h * ratio))
    image = QtGui.QImage(width, height, QtGui.QImage.Format_RGBA8888)
    image.fill(QtGui.QColor(0, 0, 0, 0))
    painter = QtGui.QPainter(image)
    try:
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        painter.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
        pen = QtGui.QPen(QtGui.QColor(rim))
        pen.setWidthF(ratio)
        painter.setPen(pen)
        painter.setBrush(QtGui.QColor(backing))
        inset = ratio / 2.0
        corner = marker_core.LABEL_CORNER_PX * ratio
        painter.drawRoundedRect(
            QtCore.QRectF(inset, inset, width - 2.0 * inset, height - 2.0 * inset), corner, corner
        )
        painter.setPen(QtGui.QColor(ink))
        painter.setFont(font)
        painter.drawText(QtCore.QRectF(0.0, 0.0, width, height), QtCore.Qt.AlignCenter, text)
    finally:
        painter.end()
    image = image.mirrored(False, True)  # Coin's rows run from the bottom
    return bytes(image.constBits())[: width * height * 4], width, height


class _Label:
    """A distance written in a box beside its line (Measure's result): a picture of the text
    on a backing, shown pixel for pixel, put across the line from its middle by
    marker_core.label_offset so that it never covers the dots or the line. The offset is in
    pixels under FreeCAD's SoShapeScale (zooming and panning leave it right); turning the view
    changes which way is across the line, so the overlay's poll places it again."""

    def __init__(self, overlay, a, b, text, clear, colours):
        from .neon_palette import rgb01

        coin = overlay.coin
        self.overlay = overlay
        self.a, self.b = App.Vector(a), App.Vector(b)
        self.middle = (self.a + self.b) * 0.5
        self.text = text
        self.clear = float(clear)
        self.backing = tuple(rgb01(colours[0]))
        ratio = handle_look._pixel_ratio()
        data, width, height = _label_picture(text, colours, ratio)
        self.size = (width / ratio, height / ratio)
        picture = coin.SoImage()
        picture.vertAlignment = coin.SoImage.HALF
        picture.horAlignment = coin.SoImage.CENTER
        picture.image.setValue(coin.SbVec2s(width, height), 4, data)
        shape, self.shift = handle_look.facing_viewer(coin, picture)
        self.node = coin.SoSeparator()
        move = coin.SoTranslation()
        move.translation.setValue(self.middle.x, self.middle.y, self.middle.z)
        self.node.addChild(move)
        self.node.addChild(overlay._in_pixels(shape, self.middle))
        self.offset = None
        self.place()

    def _screen(self, point):
        x, y = self.overlay.view.getPointOnViewport(point)
        ratio = handle_look._pixel_ratio()
        return float(x) / ratio, float(y) / ratio

    def wanted(self):
        """The offset (pixels, y up) from the line's middle that the view as it is now asks."""
        ratio = handle_look._pixel_ratio()
        size = self.overlay.view.getSize()
        area = (float(size[0]) / ratio, float(size[1]) / ratio)
        return marker_core.label_offset(
            self._screen(self.a), self._screen(self.b), self.size, self.clear, view=area
        )

    def place(self):
        offset = self.wanted()
        if self.offset is not None and max(abs(u - v) for u, v in zip(offset, self.offset)) < 0.25:
            return
        self.offset = offset
        self.shift.translation.setValue(offset[0], offset[1], 0.0)

    def settled(self):
        """True when the label is where the view as it is now puts it."""
        if self.offset is None:
            return False
        return max(abs(u - v) for u, v in zip(self.wanted(), self.offset)) < 0.5

    def box(self):
        """(x, y, w, h) of the label in the 3D view's widget pixels (y down), as placed."""
        if self.offset is None:
            return None
        mx, my = self._screen(self.middle)
        ratio = handle_look._pixel_ratio()
        height = float(self.overlay.view.getSize()[1]) / ratio
        w, h = self.size
        cx, cy = mx + self.offset[0], my + self.offset[1]
        return (cx - w / 2.0, height - (cy + h / 2.0), w, h)
