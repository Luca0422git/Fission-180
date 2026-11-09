# SPDX-License-Identifier: LGPL-2.1-or-later
"""A laptop's touchpad in the 3D view (Luca, 2026-11-09: "2 fingers drag to pan, pinch to
zoom"): two fingers dragged pan the view, a pinch zooms about the pointer, a mouse wheel
still zooms as before. touchpad_core.py decides what each event means (unit tested); this
file watches the 3D views and moves the camera.

Where the events arrive (Qt 6):
* A two-finger scroll and a mouse wheel are both wheel events. A real one goes to the 3D
  view's drawing area (a QOpenGLWidget), which does not take it; Qt then hands it to the
  viewer around it (Gui::View3DInventorViewer), where FreeCAD turns it into its wheel zoom.
  FreeCAD's see-through panels send theirs to the viewer straight. Both widgets are watched,
  and an event passed on is judged the same way twice (touchpad_core.Stream).
* A pinch is a zoom gesture (QNativeGestureEvent: macOS, Wayland, X11 with XInput 2.4) on
  the drawing area; on a Windows precision touchpad it is Ctrl + wheel.

Pan: the camera moves sideways like Navigation bar > Pan does (navigate_ui.pan_by). Zoom:
FreeCAD gets a wheel event of the right size at the pointer, so it is FreeCAD's own zoom at
the cursor (orthographic and perspective alike).

Scrolling inside panels (the browser, a dialog, FreeCAD's task panels) never reaches these
widgets: it scrolls the panel as before. Never lets an exception out of the event filter.
Preferences > General > Navigation > Touchpad: Auto, Off (everything as before), On.
"""

import sys
import time

import FreeCAD as App

from . import log, warn
from . import touchpad_core as core
from .compat import QtCore, QtGui, QtWidgets

PARAMS = "User parameter:BaseApp/Preferences/Mod/Fission180/Preferences"  # prefs_core.PREFS
KEY = "Touchpad"
VIEW_PARAMS = "User parameter:BaseApp/Preferences/View"
VIEWER = "Gui::View3DInventorViewer"

_state = {"filter": None, "widgets": [], "area": None, "on": False}


def mode():
    """The Touchpad preference: "auto", "off" or "on"."""
    try:
        return core.normalise_mode(App.ParamGet(PARAMS).GetString(KEY, core.DEFAULT_MODE))
    except Exception:
        return core.DEFAULT_MODE


def set_mode(value):
    App.ParamGet(PARAMS).SetString(KEY, core.normalise_mode(value))


def _zoom_settings():
    """(FreeCAD's wheel zoom step, its InvertZoom)."""
    group = App.ParamGet(VIEW_PARAMS)
    return group.GetFloat("ZoomStep", 0.2), group.GetBool("InvertZoom", True)


def _phase(event):
    try:
        return int(event.phase().value)
    except AttributeError:
        return int(event.phase())


def _from_touchpad(event):
    """Qt 6 says the event's device is a touchpad (X11 / Windows when it knows)."""
    try:
        device = event.pointingDevice() or event.device()
        return device is not None and device.type() == QtGui.QInputDevice.DeviceType.TouchPad
    except Exception:
        return False


def _viewer_of(widget):
    while widget is not None:
        if widget.metaObject().className() == VIEWER:
            return widget
        widget = widget.parentWidget()
    return None


def _parts(obj):
    """(the 3D view, its drawing area, its viewer) for a watched widget, or Nones."""
    from .orbit_ui import _view_for

    viewer = _viewer_of(obj)
    if viewer is None:
        return None, None, None
    gl = obj if obj is not viewer else None
    if gl is None:
        try:
            gl = viewer.viewport()  # (the viewer is a QGraphicsView)
        except AttributeError:
            gl = None
    if gl is None or gl.metaObject().className() != "QOpenGLWidget":
        gl = None
        for child in viewer.findChildren(QtWidgets.QWidget):
            if child.metaObject().className() == "QOpenGLWidget":
                gl = child
                break
    if gl is None:
        return None, None, None
    view = _view_for(gl)
    if view is None or not hasattr(view, "getCameraNode"):
        return None, None, None
    return view, gl, viewer


class _Filter(QtCore.QObject):
    """Wheel and pinch events on the 3D views' drawing areas and viewers."""

    def __init__(self):
        super().__init__()
        self.busy = False  # our own wheel event to FreeCAD is on its way
        self.stream = core.Stream()
        self.units = core.Units()
        self.told = False  # the log said once that a touchpad is in use

    def eventFilter(self, obj, event):
        try:
            if self.busy:
                return False
            kind = event.type()
            if kind == QtCore.QEvent.Wheel:
                return self._wheel(obj, event)
            if kind == QtCore.QEvent.NativeGesture:
                return self._gesture(obj, event)
        except Exception as exc:
            warn("touchpad: %s" % exc)
        return False

    # -- two fingers dragged, Ctrl + wheel (a Windows pinch) ----------------------------------
    def _wheel(self, obj, event):
        chosen = mode()
        if chosen == core.OFF:
            return False
        pixel = event.pixelDelta()
        angle = event.angleDelta()
        seen = core.look(
            _from_touchpad(event),
            _phase(event),
            (pixel.x(), pixel.y()),
            (angle.x(), angle.y()),
        )
        kind = self.stream.judge(seen, time.monotonic())
        ctrl = bool(event.modifiers() & QtCore.Qt.ControlModifier)
        buttons = event.buttons() != QtCore.Qt.NoButton
        what = core.action(chosen, seen, kind, ctrl=ctrl, buttons=buttons)
        if what == core.PASS:
            return False
        view, gl, viewer = _parts(obj)
        if view is None:
            return False
        self._tell(
            "scroll %s (angle %d, %d; pixels %d, %d; phase %d)"
            % (what, angle.x(), angle.y(), pixel.x(), pixel.y(), _phase(event))
        )
        if what == core.PAN:
            dx, dy = core.pan_pixels((pixel.x(), pixel.y()), (angle.x(), angle.y()), sys.platform)
            if dx or dy:
                from . import navigate_ui

                navigate_ui.pan_by(view, gl, dx, dy)
        else:
            step, _invert = _zoom_settings()
            self._zoom(viewer, event.globalPosition(), core.ctrl_wheel_log(angle.y(), step))
        event.accept()
        return True

    # -- a pinch (and the move of the fingers' middle in it) ----------------------------------
    def _gesture(self, obj, event):
        if mode() == core.OFF:
            return False
        gesture = event.gestureType()
        types = QtCore.Qt.NativeGestureType
        if gesture == types.BeginNativeGesture or gesture == types.EndNativeGesture:
            self.units.reset()
            return False  # (nothing to do; whoever else wants them still gets them)
        if gesture == types.ZoomNativeGesture:
            view, _gl, viewer = _parts(obj)
            if view is None:
                return False
            self._tell("pinch")
            self._zoom(viewer, event.globalPosition(), core.pinch_log(event.value()))
            event.accept()
            return True
        if gesture == types.PanNativeGesture and _finger_count(event) == 2:
            # the fingers' middle moving during a pinch (X11 XInput 2.4, Wayland)
            view, gl, _viewer = _parts(obj)
            delta = event.delta()
            if view is None or (not delta.x() and not delta.y()):
                return False
            from . import navigate_ui

            navigate_ui.pan_by(view, gl, delta.x(), delta.y())
            event.accept()
            return True
        return False  # rotation, smart zoom, swipes: not used (the ViewCube turns the view)

    def _zoom(self, viewer, global_pos, log_factor):
        """FreeCAD's wheel zoom at the pointer, exp(log_factor) times as big."""
        step, invert = _zoom_settings()
        units = self.units.take(core.zoom_units(log_factor, step, invert))
        if not units:
            return
        pos = QtCore.QPointF(viewer.mapFromGlobal(global_pos.toPoint()))
        wheel = QtGui.QWheelEvent(
            pos,
            QtCore.QPointF(global_pos),
            QtCore.QPoint(0, 0),
            QtCore.QPoint(0, units),
            QtCore.Qt.NoButton,
            QtCore.Qt.NoModifier,
            QtCore.Qt.NoScrollPhase,
            False,
        )
        self.busy = True
        try:
            QtWidgets.QApplication.sendEvent(viewer, wheel)
        finally:
            self.busy = False

    def _tell(self, first):
        """One line in the log the first time (what the first touchpad event was: a help
        when a touchpad or a mouse does something unexpected on someone's computer)."""
        if not self.told:
            self.told = True
            log(
                "touchpad: two fingers pan, a pinch zooms (Preferences > General > Touchpad); "
                "first: %s" % first
            )


def _finger_count(event):
    try:
        return int(event.fingerCount())
    except Exception:
        return 0


# -- turning it on and off ------------------------------------------------------------------


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
                widget.installEventFilter(_state["filter"])
                _state["widgets"].append(widget)
        except RuntimeError:
            pass  # the view of a design being closed


def _installed_soon():
    try:
        if _state["on"]:
            _install()
    except Exception as exc:
        warn("touchpad: %s" % exc)


def enable():
    """Fission 180's interface turned on: the filter on every 3D view, now and later ones."""
    _state["on"] = True
    if _state["filter"] is None:
        _state["filter"] = _Filter()
    _install()
    area = _mdi_area()
    try:
        if area is not None and _state["area"] is None:
            area.subWindowActivated.connect(lambda *_: _installed_soon())
            _state["area"] = area
    except Exception as exc:
        warn("touchpad: %s" % exc)


def _mdi_area():
    try:
        import FreeCADGui as Gui

        return Gui.getMainWindow().findChild(QtWidgets.QMdiArea)
    except Exception:
        return None


def disable():
    """Fission 180's interface turned off: FreeCAD's own wheel handling everywhere."""
    from .orbit_ui import _is_valid

    _state["on"] = False
    filt, _state["filter"] = _state["filter"], None
    for widget in _state["widgets"]:
        try:
            if filt is not None and _is_valid(widget):
                widget.removeEventFilter(filt)
        except RuntimeError:
            pass
    _state["widgets"] = []


def watched():
    """How many widgets the filter is on (tests)."""
    return len(_state["widgets"])
