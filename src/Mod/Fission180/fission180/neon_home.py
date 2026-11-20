# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights: the animated Home background (docs/fission180/neon-lights-design.md 6.9, plan
task B9).

A slowly moving neon perspective grid (a floor running toward a glowing horizon) and a faint
stream of characters falling down the right side, drawn behind Home's content. home_ui calls
attach(page) when Home's page is made and detach(page) when it goes.

It is a child widget at the bottom of the page (clicks pass through it). Its timer runs at
most FPS frames a second, and only while Neon Lights is on, the setting HomeAnimation is on,
the page is visible (Home's tab in front) and the main window is active; otherwise it is
stopped (no timer, no painting). The still parts (the background, the grid's converging lines,
the horizon) are drawn once per size into a picture; each frame adds the moving lines and the
characters.

For the grid to show through, Home's own panels must not paint an opaque background in Neon
Lights (SEE_THROUGH lists the object names; builder "panels" makes them transparent there).
"""

import math
import random

from . import warn

FPS = 24  # at most 30 (design 6.9); 24 is smooth for slow motion and cheaper
SPEED = 0.18  # grid rows per second toward the viewer
# Not the page itself (#Fission180Home): it must stay opaque, or the 3D view of a design's tab
# behind Home (MDI tabs are stacked, all "visible") shows through on screen. The backdrop
# paints over the page's own background anyway.
SEE_THROUGH = ("Fission180HomeScroll", "Fission180HomeRows", "Fission180HomeList")
# ... and the scroll area's viewport, as a style-sheet rule:
SEE_THROUGH_QSS = (
    ", ".join("#%s" % n for n in SEE_THROUGH)
    + ", #Fission180HomeScroll > QWidget#qt_scrollarea_viewport { background: transparent; }"
)
NAME = "Fission180NeonHomeBackdrop"
_GLYPHS = "0123456789ABCDEF<>/\\|=+-:*#"
_state = {"on": False, "pages": [], "backdrops": {}, "app_hook": None}


def _setting():
    try:
        from . import neon_settings

        return bool(neon_settings.get("HomeAnimation"))
    except Exception:
        return True


def wanted():
    try:
        from . import theme

        return bool(_state["on"] and theme.is_neon() and _setting())
    except Exception:
        return False


def _colours():
    from . import theme

    p = theme.palette()
    return {
        "background": p.get("background", "#0b0d17"),
        "primary": p.get("primary", "#ff2a6d"),
        "secondary": p.get("secondary", "#05d9e8"),
        "grid": p.get("grid_major", p.get("secondary", "#05d9e8")),
    }


def rows(phase, count=14):
    """The floor's horizontal lines as depths 0..1 (0 the horizon, 1 the bottom edge) for a
    phase in rows (pure; a perspective spacing, wider toward the viewer)."""
    frac = phase - math.floor(phase)
    out = []
    for i in range(count):
        z = (i + 1 - frac) / float(count)  # 1/z spacing: evenly spaced in the world
        if z <= 0:
            continue
        depth = (1.0 / count) / z  # 1 at the nearest row, -> 0 at the horizon
        out.append(min(1.0, depth))
    return sorted(out)


def _backdrop_class():
    from PySide import QtCore, QtGui, QtWidgets

    class Backdrop(QtWidgets.QWidget):
        """The moving picture behind one Home page."""

        def __init__(self, page):
            super().__init__(page)
            self.setObjectName(NAME)
            self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
            self.setAttribute(QtCore.Qt.WA_OpaquePaintEvent, True)
            self.setFocusPolicy(QtCore.Qt.NoFocus)
            self.page = page
            self.colours = _colours()
            self.still = None
            self.clock = QtCore.QElapsedTimer()
            self.clock.start()
            self.timer = QtCore.QTimer(self)
            self.timer.setTimerType(QtCore.Qt.CoarseTimer)
            self.timer.setInterval(int(math.ceil(1000.0 / FPS)))
            self.timer.timeout.connect(self._tick)
            self.frames = 0
            self.rng = random.Random(180)
            self.drops = []
            self._viewports = None
            self.setGeometry(page.rect())
            self.lower()
            self.show()

        # -- running or not
        def stopped_because(self):
            """Why the animation is stopped now, or "" when it should run."""
            try:
                if not wanted():
                    return "Neon Lights or the setting is off"
                if not self.page.isVisible():
                    return "Home is hidden"
                window = self.page.window()
                if window is None or window.isMinimized():
                    return "the window is minimized"
                if not window.isActiveWindow():
                    return "the window is not active"
                sub = _subwindow(self.page)
                if sub is not None:
                    area = sub.mdiArea()
                    # a design's tab in front: Home stays "visible" under it (maximized tabs)
                    if area is not None and area.currentSubWindow() is not sub:
                        return "another tab is in front"
                return ""
            except RuntimeError:
                return "Home is gone"

        def should_run(self):
            return not self.stopped_because()

        def follow(self):
            try:
                if self.should_run():
                    if not self.timer.isActive():
                        self.timer.start()
                        self.update()
                elif self.timer.isActive():
                    self.timer.stop()
            except RuntimeError:
                pass

        def _tick(self):
            try:
                if not self.should_run():
                    self.timer.stop()
                    return
                self.update()
                # and the scroll areas' viewports over it: Qt did not repaint Home's
                # (see-through) list for the backdrop's own update, so the floor stood still
                # on screen behind it (window.grab() showed it moving). page.update() is
                # no help: the opaque backdrop covers the page, nothing under it is painted.
                try:
                    for viewport in self.viewports():
                        viewport.update()
                except RuntimeError:  # a scroll area went: found again next frame
                    self._viewports = None
            except Exception as exc:
                warn("Neon Lights: Home background: %s (switched off)" % exc)
                self.timer.stop()
                _drop(self.page)

        def viewports(self):
            """The see-through scroll areas' viewports (Home's list; the tile lists inside it
            are repainted with it, and are made again on every refresh, so not kept)."""
            if self._viewports is None:
                self._viewports = [
                    a.viewport() for a in self.page.findChildren(QtWidgets.QAbstractScrollArea)
                    if a.objectName() in SEE_THROUGH and a.objectName() != "Fission180HomeList"
                ]
            return self._viewports

        def recolour(self):
            self.colours = _colours()
            self.still = None
            self.update()

        def resizeEvent(self, event):  # noqa: N802
            super().resizeEvent(event)
            self.still = None
            self.drops = []

        # -- painting
        def _horizon(self):
            return int(self.height() * 0.38)

        def _make_still(self):
            w, h = max(1, self.width()), max(1, self.height())
            c = self.colours
            pix = QtGui.QPixmap(w, h)
            pix.fill(QtGui.QColor(c["background"]))
            p = QtGui.QPainter(pix)
            p.setRenderHint(QtGui.QPainter.Antialiasing, True)
            hy = self._horizon()
            # the sky: a soft glow rising from the horizon
            sky = QtGui.QLinearGradient(0, 0, 0, hy)
            top = QtGui.QColor(c["background"])
            glow = QtGui.QColor(c["primary"])
            glow.setAlpha(38)
            sky.setColorAt(0.0, top)
            sky.setColorAt(1.0, glow)
            p.fillRect(QtCore.QRect(0, 0, w, hy), QtGui.QBrush(sky))
            # the floor fades into the background toward the horizon
            floor = QtGui.QLinearGradient(0, hy, 0, h)
            f0 = QtGui.QColor(c["secondary"])
            f0.setAlpha(18)
            floor.setColorAt(0.0, f0)
            floor.setColorAt(1.0, QtGui.QColor(c["background"]))
            p.fillRect(QtCore.QRect(0, hy, w, h - hy), QtGui.QBrush(floor))
            # converging lines from the vanishing point
            cx = w / 2.0
            col = QtGui.QColor(c["grid"])
            n = 26
            spread = w * 2.4
            for i in range(n + 1):
                x_bottom = cx - spread / 2.0 + spread * i / float(n)
                fade = 1.0 - abs(i - n / 2.0) / (n / 2.0) * 0.6
                col.setAlpha(int(64 * fade))
                p.setPen(QtGui.QPen(col, 1.0))
                p.drawLine(QtCore.QPointF(cx, hy), QtCore.QPointF(x_bottom, h))
            # the horizon line, glowing
            for width, alpha in ((7.0, 26), (3.0, 60), (1.2, 170)):
                hc = QtGui.QColor(c["primary"])
                hc.setAlpha(alpha)
                p.setPen(QtGui.QPen(hc, width))
                p.drawLine(QtCore.QPointF(0, hy), QtCore.QPointF(w, hy))
            p.end()
            self.still = pix

        def _stream(self, p, t):
            """A faint column of characters falling down the right side."""
            w, h = self.width(), self.height()
            size = 12
            right = w - 18
            scroll = getattr(self.page, "scroll", None)  # Home's list: not under the AI column
            try:
                if scroll is not None and scroll.isVisible():
                    right = scroll.mapTo(self.page, QtCore.QPoint(scroll.width(), 0)).x() - 24
            except RuntimeError:
                pass
            columns = max(3, min(10, right // 140))
            left = right - columns * (size + 6)
            if len(self.drops) != columns:
                self.drops = [
                    (self.rng.uniform(0, h), self.rng.uniform(26, 60), self.rng.randint(6, 16))
                    for _ in range(columns)
                ]
            font = QtGui.QFont("Monospace")
            font.setStyleHint(QtGui.QFont.TypeWriter)
            font.setPixelSize(size)
            p.setFont(font)
            colour = QtGui.QColor(self.colours["secondary"])
            for i, (start, speed, length) in enumerate(self.drops):
                head = (start + t * speed) % (h + length * size)
                x = left + i * (size + 6)
                for k in range(length):
                    y = head - k * size
                    if y < -size or y > h:
                        continue
                    colour.setAlpha(int(70 * (1.0 - k / float(length))) + (30 if k == 0 else 0))
                    p.setPen(colour)
                    seed = (int(head / size) - k) * 31 + i * 17
                    p.drawText(QtCore.QPointF(x, y), _GLYPHS[seed % len(_GLYPHS)])

        def paintEvent(self, event):  # noqa: N802
            p = QtGui.QPainter(self)
            try:
                if self.still is None or self.still.size() != self.size():
                    self._make_still()
                p.drawPixmap(0, 0, self.still)
                t = self.clock.elapsed() / 1000.0
                w, h = self.width(), self.height()
                hy = self._horizon()
                col = QtGui.QColor(self.colours["grid"])
                p.setRenderHint(QtGui.QPainter.Antialiasing, False)
                for depth in rows(t * SPEED * 6.0):
                    y = hy + (h - hy) * depth
                    col.setAlpha(int(28 + 92 * depth))
                    p.setPen(QtGui.QPen(col, 1.0 if depth < 0.6 else 1.6))
                    p.drawLine(QtCore.QPointF(0, y), QtCore.QPointF(w, y))
                p.setRenderHint(QtGui.QPainter.TextAntialiasing, True)
                self._stream(p, t)
                self.frames += 1
            except Exception as exc:
                warn("Neon Lights: Home background: %s (switched off)" % exc)
                QtCore.QTimer.singleShot(0, lambda: _drop(self.page))
            finally:
                p.end()

    return Backdrop


def _subwindow(page):
    """The tab (QMdiSubWindow) Home's page is in, or None (a page shown on its own: tests)."""
    from PySide import QtWidgets

    w = page.parentWidget()
    while w is not None:
        if isinstance(w, QtWidgets.QMdiSubWindow):
            return w
        w = w.parentWidget()
    return None


def _tab_changed(*_args):
    from PySide import QtCore

    QtCore.QTimer.singleShot(0, follow_all)


def _hook_class():
    from PySide import QtCore

    class _Follow(QtCore.QObject):
        """Show/hide/resize of a Home page and the main window's activation: every backdrop
        starts or stops its timer (event driven: no polling while stopped)."""

        def eventFilter(self, obj, event):  # noqa: N802
            try:
                kind = event.type()
                if kind == QtCore.QEvent.Resize:
                    backdrop = _state["backdrops"].get(id(obj))
                    if backdrop is not None and backdrop.page is obj:
                        backdrop.setGeometry(obj.rect())
                        backdrop.lower()
                elif kind in (
                    QtCore.QEvent.Show,
                    QtCore.QEvent.Hide,
                    QtCore.QEvent.WindowActivate,
                    QtCore.QEvent.WindowDeactivate,
                    QtCore.QEvent.WindowStateChange,
                ):
                    QtCore.QTimer.singleShot(0, follow_all)
            except Exception as exc:
                warn("Neon Lights: Home background: %s" % exc)
            return False

    return _Follow


def _watch(page):
    hook = _state["app_hook"]
    if hook is None:
        hook = _hook_class()()
        _state["app_hook"] = hook
        try:
            window = page.window()
            if window is not None:
                window.installEventFilter(hook)
                _state["window"] = window
        except Exception:
            pass
    page.installEventFilter(hook)
    sub = _subwindow(page)
    area = sub.mdiArea() if sub is not None else None
    if area is not None and _state.get("area") is not area:
        _unconnect_area()
        area.subWindowActivated.connect(_tab_changed)
        _state["area"] = area


def _unconnect_area():
    area = _state.get("area")
    _state["area"] = None
    if area is not None:
        try:
            area.subWindowActivated.disconnect(_tab_changed)
        except (RuntimeError, TypeError):
            pass


def _unwatch_all():
    hook = _state["app_hook"]
    _state["app_hook"] = None
    if hook is None:
        return
    for page in list(_state["pages"]) + [_state.get("window")]:
        try:
            if page is not None:
                page.removeEventFilter(hook)
        except RuntimeError:
            pass
    _state["window"] = None
    _unconnect_area()


def _make(page):
    if id(page) in _state["backdrops"]:
        return _state["backdrops"][id(page)]
    backdrop = _backdrop_class()(page)
    _state["backdrops"][id(page)] = backdrop
    _watch(page)
    backdrop.follow()
    return backdrop


def _drop(page):
    backdrop = _state["backdrops"].pop(id(page), None)
    if backdrop is None:
        return
    try:
        backdrop.timer.stop()
        backdrop.hide()
        backdrop.setParent(None)
        backdrop.deleteLater()
    except RuntimeError:
        pass


def _alive(page):
    try:
        page.objectName()
        return True
    except RuntimeError:
        return False


def follow_all():
    """Every backdrop's timer on or off for the state now."""
    _state["pages"] = [p for p in _state["pages"] if _alive(p)]
    for key in list(_state["backdrops"]):
        backdrop = _state["backdrops"][key]
        try:
            backdrop.follow()
        except RuntimeError:
            _state["backdrops"].pop(key, None)


def _sync():
    """Backdrops made or taken away to match the settings."""
    _state["pages"] = [p for p in _state["pages"] if _alive(p)]
    if wanted():
        for page in _state["pages"]:
            try:
                _make(page)
            except Exception as exc:
                warn("Neon Lights: Home background: %s" % exc)
        follow_all()
    else:
        for page in list(_state["pages"]):
            _drop(page)
        _state["backdrops"] = {}
        _unwatch_all()


def attach(widget):
    """Draw the moving neon background behind Home's `widget` (while Neon Lights is on, the
    setting is on and the page is visible). Safe to call more than once; never raises."""
    try:
        if widget is None:
            return None
        if all(p is not widget for p in _state["pages"]):
            _state["pages"].append(widget)
            try:
                widget.destroyed.connect(lambda *_a, k=id(widget): _forget(k))
            except Exception:
                pass
        if wanted():
            return _make(widget)
    except Exception as exc:
        warn("Neon Lights: Home background: %s" % exc)
    return None


def _forget(key):
    _state["pages"] = [p for p in _state["pages"] if _alive(p) and id(p) != key]
    backdrop = _state["backdrops"].pop(key, None)
    if backdrop is not None:
        try:
            backdrop.timer.stop()
        except RuntimeError:
            pass


def detach(widget):
    """No moving background behind `widget` any more."""
    try:
        _state["pages"] = [p for p in _state["pages"] if p is not widget and _alive(p)]
        _drop(widget)
        try:
            if _state["app_hook"] is not None:
                widget.removeEventFilter(_state["app_hook"])
        except RuntimeError:
            pass
        if not _state["backdrops"]:
            _unwatch_all()
    except Exception as exc:
        warn("Neon Lights: Home background: %s" % exc)
    return None


def backdrop(widget):
    """The backdrop behind `widget`, or None (tests)."""
    return _state["backdrops"].get(id(widget))


def stopped_because(widget):
    """Why `widget`'s background is not animating ("" while it should; tests)."""
    b = backdrop(widget)
    if b is None:
        return "no backdrop"
    try:
        return b.stopped_because()
    except RuntimeError:
        return "no backdrop"


def running(widget):
    """True while `widget`'s background is animating (its timer runs; tests)."""
    b = backdrop(widget)
    try:
        return bool(b is not None and b.timer.isActive())
    except RuntimeError:
        return False


def enable():
    _state["on"] = True
    _sync()


def disable():
    _state["on"] = False
    _sync()


def refresh():
    """Colours or the HomeAnimation setting changed."""
    _sync()
    for b in list(_state["backdrops"].values()):
        try:
            b.recolour()
        except RuntimeError:
            pass
