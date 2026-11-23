# SPDX-License-Identifier: LGPL-2.1-or-later
"""A touchscreen in the 3D view (Luca, 2026-11-23; docs/fission180/touchscreen-design.md).

Every 3D view's drawing area (a QOpenGLWidget) takes Qt's touch events; touch_core.Tracker
says what the fingers mean and this file does it:
  orbit  orbit_ui.drag_camera (the ViewCube's and Shift + middle-drag's orbit: the Orbit type
         and the pivot as set), as much per pixel as FreeCAD's own mouse orbit;
  pan    navigate_ui.pan_by (the navigation bar's pan);
  zoom   FreeCAD's own wheel zoom at the point between the fingers (as touchpad_ui does);
  click, double click, right click, a mouse-like drag: mouse events sent to the drawing area,
         the way FreeCAD forwards them itself (OverlayManager::interceptEvent), so a tap selects,
         a right click opens the marking menu and a drag moves a handle as the mouse would.
Every press comes after a move to it, and a finger's landing moves the mouse there first
(FreeCAD's sketch acts on what a move put under the pointer).
While a command's dialog is open or a sketch is in edit, one finger works like the mouse.
A touch that starts on a widget over the drawing area (the ViewCube, a sketch's green check)
is left to Qt's own mouse emulation, which takes it to that widget.
An accepted touch is not turned into mouse events by Qt; FreeCAD's own pan and pinch gestures
on the viewer are dropped while this is on (they would zoom a second time).
Preferences > General > Navigation > Touchscreen: On (default) / Off (Qt's mouse emulation,
as before). Never lets an exception out of the event filter or the timer.
"""

import time

import FreeCAD as App

from . import log, warn
from . import touch_core as core
from .compat import QtCore, QtGui, QtWidgets

PARAMS = "User parameter:BaseApp/Preferences/Mod/Fission180/Preferences"  # prefs_core.PREFS
KEY = "Touchscreen"
TICK_MS = 50  # the long press is looked at this often while a finger is down

_state = {"filter": None, "widgets": [], "area": None, "on": False, "timer": None}


def mode():
    try:
        return core.mode_of(App.ParamGet(PARAMS).GetString(KEY, core.DEFAULT_MODE))
    except Exception:
        return core.DEFAULT_MODE


def _mouse_like():
    """A command's dialog open or a sketch in edit: one finger is the mouse."""
    try:
        import FreeCADGui as Gui

        if Gui.Control.activeDialog():
            return True
        doc = Gui.ActiveDocument
        edited = doc.getInEdit() if doc is not None else None
        obj = getattr(edited, "Object", None)
        return obj is not None and obj.isDerivedFrom("Sketcher::SketchObject")
    except Exception:
        return False


def _on_a_child(widget, event):
    """The touch starts on a widget over the drawing area that takes the mouse (the ViewCube,
    a sketch's green check): Qt's own mouse emulation takes it there, as with Off."""
    points = event.points()
    if not points:
        return False
    pos = points[0].position().toPoint()
    child = widget.childAt(pos)
    while child is not None and child is not widget:
        if child.isVisible() and not child.testAttribute(QtCore.Qt.WA_TransparentForMouseEvents):
            return True
        child = child.parentWidget()
    return False


def _down(event):
    """{id: (x, y)} of the fingers still on the screen, in the drawing area's pixels."""
    points = {}
    for point in event.points():
        if point.state() == QtGui.QEventPoint.State.Released:
            continue
        pos = point.position()
        points[point.id()] = (pos.x(), pos.y())
    return points


class _Filter(QtCore.QObject):
    """Touch on the drawing areas; FreeCAD's gestures on the viewers."""

    def __init__(self):
        super().__init__()
        self.tracker = core.Tracker()
        self.widget = None  # the drawing area the fingers are on
        self.told = False

    def eventFilter(self, obj, event):
        try:
            kind = event.type()
            E = QtCore.QEvent
            if kind == E.Gesture:
                return mode() == core.ON
            if kind not in (E.TouchBegin, E.TouchUpdate, E.TouchEnd, E.TouchCancel):
                return False
            if mode() != core.ON or obj.metaObject().className() != "QOpenGLWidget":
                return False  # (Off: Qt makes mouse events of it, as before)
            device = event.device()
            if device is not None and device.type() != QtGui.QInputDevice.DeviceType.TouchScreen:
                return False  # (a touchpad's raw touches: touchpad_ui's)
            now = time.monotonic()
            if kind == E.TouchBegin and _on_a_child(obj, event):
                return False  # (not accepted: no more of this touch comes here)
            if kind == E.TouchBegin:
                try:
                    self._do(self.tracker.cancel(now))  # (the last touch's end never came)
                except Exception as exc:
                    warn("touchscreen: letting go of the last touch: %s" % exc)  # (its view closed)
                self.widget = obj
                self.tracker.mouse_like = _mouse_like()
                if not self.told:
                    self.told = True
                    log("touchscreen: fingers in the 3D view")
                down = _down(event)
                self._hover(down)
                self._do(self.tracker.begin(now, down))
                _tick_on()
            elif kind == E.TouchUpdate:
                self._do(self.tracker.update(now, _down(event)))
            elif kind == E.TouchEnd:
                self._do(self.tracker.end(now, {}))
                _tick_off()
            else:  # cancelled: as if lifted, without its click (a mouse drag is let go of)
                self._do(self.tracker.cancel(now))
                _tick_off()
            event.accept()
            return True
        except Exception as exc:
            warn("touchscreen: %s" % exc)
            return False

    def tick(self):
        try:
            self._do(self.tracker.tick(time.monotonic()))
        except Exception as exc:
            warn("touchscreen: %s" % exc)

    # -- doing what the fingers mean -----------------------------------------------------
    def _do(self, actions):
        if not actions or self.widget is None:
            return
        from .touchpad_ui import _parts

        view, gl, viewer = _parts(self.widget)
        if view is None:
            return
        for action in actions:
            what = action[0]
            if what == "orbit":
                from . import orbit, orbit_ui

                # (as much per pixel as FreeCAD's own mouse orbit on a view this size)
                deg_x, deg_y = orbit.degrees_per_pixel(gl.width(), gl.height(), orbit_ui._sensitivity())
                orbit_ui.drag_camera(view, action[1], action[2], deg_x, deg_y)
            elif what == "pan":
                from . import navigate_ui

                navigate_ui.pan_by(view, gl, action[1], action[2])
            elif what == "zoom":
                self._zoom(viewer, gl, action[1], action[2])
            elif what == "click":
                self._mouse(gl, (action[1], action[2]), ("press", "release"))
            elif what == "double_click":  # (the first tap was a click already: as a mouse's)
                self._mouse(gl, (action[1], action[2]), ("double", "release"))
            elif what == "right_click":
                self._mouse(gl, (action[1], action[2]), ("press", "release"), QtCore.Qt.RightButton)
            elif what in ("press", "move", "release"):
                self._mouse(gl, (action[1], action[2]), (what,))

    def _zoom(self, viewer, gl, log_factor, at):
        """FreeCAD's wheel zoom about `at`, exp(log_factor) times as big."""
        from . import touchpad_core, touchpad_ui

        step, invert = touchpad_ui._zoom_settings()
        units = self._units().take(touchpad_core.zoom_units(log_factor, step, invert))
        if not units:
            return
        point = gl.mapToGlobal(QtCore.QPoint(int(at[0]), int(at[1])))
        wheel = QtGui.QWheelEvent(
            QtCore.QPointF(viewer.mapFromGlobal(point)),
            QtCore.QPointF(point),
            QtCore.QPoint(0, 0),
            QtCore.QPoint(0, units),
            QtCore.Qt.NoButton,
            QtCore.Qt.NoModifier,
            QtCore.Qt.NoScrollPhase,
            False,
        )
        pad = touchpad_ui._state.get("filter")
        if pad is not None:
            pad.busy = True  # (not a touchpad's scroll: never a pan, whatever its setting)
        try:
            QtWidgets.QApplication.sendEvent(viewer, wheel)
        finally:
            if pad is not None:
                pad.busy = False

    def _units(self):
        from . import touchpad_core

        if not hasattr(self, "units"):
            self.units = touchpad_core.Units()
        return self.units

    def _hover(self, down):
        """The mouse onto the finger that just landed (FreeCAD's sketch picks what a move put
        under the pointer: a press acts on that, not on what is under the press), and a frame
        drawn so it is found before the finger lifts."""
        if not down or self.widget is None:
            return
        from .touchpad_ui import _parts

        _view, gl, _viewer = _parts(self.widget)
        if gl is None:
            return
        self._mouse(gl, down[min(down)], ("hover",))
        gl.update()

    def _mouse(self, gl, at, steps, button=QtCore.Qt.LeftButton):
        local = QtCore.QPointF(at[0], at[1])
        point = QtCore.QPointF(gl.mapToGlobal(QtCore.QPoint(int(at[0]), int(at[1]))))
        E = QtCore.QEvent
        none = QtCore.Qt.NoButton
        kinds = {
            "hover": (E.MouseMove, none, none),
            "press": (E.MouseButtonPress, button, button),
            "release": (E.MouseButtonRelease, button, none),
            "double": (E.MouseButtonDblClick, button, button),
            "move": (E.MouseMove, none, QtCore.Qt.LeftButton),
        }
        for step in steps:
            if step in ("press", "double"):  # (a mouse is over what it presses)
                self._send(gl, kinds["hover"], local, point)
            self._send(gl, kinds[step], local, point)

    @staticmethod
    def _send(gl, kind, local, point):
        what, which, held = kind
        event = QtGui.QMouseEvent(what, local, point, which, held, QtCore.Qt.NoModifier)
        QtWidgets.QApplication.sendEvent(gl, event)


# -- the long-press timer -----------------------------------------------------------------------
def _tick_on():
    timer = _state["timer"]
    if timer is None:
        timer = _state["timer"] = QtCore.QTimer()
        timer.setInterval(TICK_MS)
        timer.timeout.connect(lambda: _state["filter"] is not None and _state["filter"].tick())
    timer.start()


def _tick_off():
    if _state["timer"] is not None:
        _state["timer"].stop()


# -- turning it on and off ------------------------------------------------------------------------
def _install():
    if _state["filter"] is None:
        return
    from .orbit_ui import _is_valid, _same, _view_widgets

    try:
        widgets = _view_widgets()
    except RuntimeError:
        return
    _state["widgets"] = [w for w in _state["widgets"] if _is_valid(w)]  # closed views go
    for widget in widgets:
        try:
            if not any(_same(widget, w) for w in _state["widgets"]):
                if widget.metaObject().className() == "QOpenGLWidget":
                    widget.setAttribute(QtCore.Qt.WA_AcceptTouchEvents, True)
                widget.installEventFilter(_state["filter"])
                _state["widgets"].append(widget)
        except RuntimeError:
            pass  # the view of a design being closed


def _installed_soon():
    try:
        if _state["on"]:
            _install()
    except Exception as exc:
        warn("touchscreen: %s" % exc)


def _later():
    try:
        QtCore.QTimer.singleShot(0, _installed_soon)
        QtCore.QTimer.singleShot(300, _installed_soon)
    except Exception as exc:
        warn("touchscreen: %s" % exc)


def enable():
    """Fission 180's interface turned on: every 3D view takes touch, now and later ones."""
    _state["on"] = True
    if _state["filter"] is None:
        _state["filter"] = _Filter()
    _install()
    try:
        import FreeCADGui as Gui

        area = Gui.getMainWindow().findChild(QtWidgets.QMdiArea)
        if area is not None and _state["area"] is None:
            # (a new design's window is activated before its drawing area is made: the views
            # are looked for again once the event loop is back, and a moment later)
            area.subWindowActivated.connect(lambda *_: _later())
            _state["area"] = area
    except Exception as exc:
        warn("touchscreen: %s" % exc)


def disable():
    """Fission 180's interface turned off: Qt's and FreeCAD's own touch handling again."""
    from .orbit_ui import _is_valid

    _state["on"] = False
    _tick_off()
    for widget in _state["widgets"]:
        try:
            if _is_valid(widget):
                widget.removeEventFilter(_state["filter"])
        except RuntimeError:
            pass
    _state["widgets"] = []

