# SPDX-License-Identifier: LGPL-2.1-or-later
"""The touchpad works in a design's 3D view from the moment the design opens (Luca,
2026-11-23: "get that touchpad timing flaw fixed"; while making the touchscreen, touchpad_ui's
list of views held only "deleted" entries after a new design).

For a design made from a script, one made with Ctrl+N (FreeCAD's New) and a saved one opened
again, with nothing else done: the touchpad's handler gets the new view's events, a pinch
zooms and a two-finger scroll pans the view (Fission 180's touchpad; FreeCAD's own wheel
handling zooms instead), and touchpad_ui lists the new view (touchpad_ui.watching).
Fission 180's interface turned off: the scroll zooms (FreeCAD's own), nothing listed; on
again: it pans. With Shift held (pressed in the middle of a scroll), two fingers orbit the
view as Shift + middle-drag does: it turns, its size stays; let go of Shift: it pans again.
"""

import os
import tempfile

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui, QtWidgets

from Fission180Tests.gui import harness as h

st = {"docs": 0}
_DEVICE = {}
G = QtCore.Qt.NativeGestureType


def touchpad():
    from fission180 import touchpad_ui

    return touchpad_ui


def touchpad_device():
    if "pad" not in _DEVICE:
        _DEVICE["pad"] = QtGui.QPointingDevice(
            "Fission 180 test touchpad",
            4712,
            QtGui.QInputDevice.DeviceType.TouchPad,
            QtGui.QPointingDevice.PointerType.Finger,
            QtGui.QInputDevice.Capability.Position | QtGui.QInputDevice.Capability.Scroll,
            5,
            0,
        )
    return _DEVICE["pad"]


def gesture(kind, value=0.0):
    area = h.gl_widget()
    at = QtCore.QPoint(area.width() // 2, area.height() // 2)
    event = QtGui.QNativeGestureEvent(
        kind,
        touchpad_device(),
        2,
        QtCore.QPointF(at),
        QtCore.QPointF(at),
        QtCore.QPointF(area.mapToGlobal(at)),
        float(value),
        QtCore.QPointF(0, 0),
    )
    QtWidgets.QApplication.sendEvent(area, event)
    QtWidgets.QApplication.processEvents()
    return event.isAccepted()


def viewer():
    widget = h.gl_widget()
    while widget is not None and widget.metaObject().className() != "Gui::View3DInventorViewer":
        widget = widget.parentWidget()
    return widget


def wheel(angle, target, modifiers=QtCore.Qt.NoModifier):
    """A touchpad's two-finger scroll (wheel units that are no whole notch) over the middle
    of the drawing area, sent to `target`; whether it was taken."""
    area = h.gl_widget()
    at = QtCore.QPoint(area.width() // 2, area.height() // 2)
    pos = QtCore.QPointF(target.mapFrom(area, at)) if target is not area else QtCore.QPointF(at)
    event = QtGui.QWheelEvent(
        pos,
        QtCore.QPointF(area.mapToGlobal(at)),
        QtCore.QPoint(0, 0),
        QtCore.QPoint(*angle),
        QtCore.Qt.NoButton,
        modifiers,
        QtCore.Qt.NoScrollPhase,
        False,
    )
    QtWidgets.QApplication.sendEvent(target, event)
    QtWidgets.QApplication.processEvents()
    return event.isAccepted()


def scroll(angle, modifiers=QtCore.Qt.NoModifier):
    """As Qt hands a real one on: the drawing area first, then (not taken) the viewer."""
    if not wheel(angle, h.gl_widget(), modifiers):
        wheel(angle, viewer(), modifiers)


def position():
    return App.Vector(*h.view().getCameraNode().position.getValue().getValue())


def height():
    return float(h.view().getCameraNode().height.getValue())


def new_view_up():
    """A new design is the active one and its drawing area is there."""
    area = h.gl_widget()
    return len(App.listDocuments()) > st["docs"] and area is not None and area.isVisible()


def opened(name, how):
    def step():
        st["docs"] = len(App.listDocuments())
        how()

    step.__name__ = "open_" + name
    step.done = new_view_up
    step.done_what = "the new design's 3D view"
    return step


def checked(name):
    def step():
        h.view().setCameraType("Orthographic")
        area = h.gl_widget()
        module = touchpad()
        filt = module._state["filter"]
        seen = []
        kind = type(filt)
        original = kind._gesture

        def spy(self, obj, event):
            seen.append(obj)
            return original(self, obj, event)

        kind._gesture = spy
        try:
            before = height()
            gesture(G.BeginNativeGesture)
            gesture(G.ZoomNativeGesture, 0.25)  # fingers apart: zoom in
            gesture(G.EndNativeGesture)
        finally:
            kind._gesture = original
        h.check(
            "%s: the touchpad's handler gets the new view's events" % name,
            any(obj is area for obj in seen),
            [o.metaObject().className() for o in seen],
        )
        h.check("%s: a pinch zooms in" % name, height() < before * 0.95, (before, height()))
        before, where = height(), position()
        for delta in ((13, -37), (8, -41), (0, -29), (-5, -35)):
            scroll(delta)
        h.check(
            "%s: a two-finger scroll pans (the view's size stays)" % name,
            abs(height() - before) < 1e-6 * max(1.0, before),
            (before, height()),
        )
        h.check("%s: ... and the view moves" % name, (position() - where).Length > 1e-6, (where, position()))
        h.check("%s: touchpad_ui lists the new view" % name, module.watching(area))

    step.__name__ = "check_" + name
    return step


def save_first():
    path = os.path.join(tempfile.mkdtemp(prefix="fission180-pad-"), "PadSaved.FCStd")
    doc = App.ActiveDocument
    doc.saveAs(path)
    st["saved"] = path
    App.closeDocument(doc.Name)


save_first.done = lambda: all(d.FileName != st.get("saved") for d in App.listDocuments().values())
save_first.done_what = "the saved design to close"


def interface_off():
    touchpad().disable()
    before = height()
    for delta in ((13, -37), (8, -41), (0, -29), (-5, -35)):
        scroll(delta)
    h.check("off: the scroll is FreeCAD's own again (it zooms)", abs(height() - before) > 1e-6, (before, height()))
    h.check("off: touchpad_ui lists no view", not touchpad().watching(h.gl_widget()))
    touchpad().enable()


interface_off.done = lambda: touchpad().watching(h.gl_widget())
interface_off.done_what = "touchpad_ui on the view again"


def interface_on():
    before, where = height(), position()
    for delta in ((13, -37), (8, -41), (0, -29), (-5, -35)):
        scroll(delta)
    h.check("on again: the scroll pans", abs(height() - before) < 1e-6 * max(1.0, before), (before, height()))
    h.check("on again: ... and the view moves", (position() - where).Length > 1e-6)


def shift_orbits():
    before, turn = height(), h.view().getCameraOrientation()
    for delta in ((13, -37), (8, -41)):  # panning ...
        scroll(delta)
    for delta in ((40, -10), (37, -8), (42, -12), (35, -9)):  # ... Shift pressed: orbit
        scroll(delta, QtCore.Qt.ShiftModifier)
    after = h.view().getCameraOrientation()
    angle = abs(turn.inverted().multiply(after).Angle)
    h.check("Shift + two fingers: the view turns", angle > 0.01, angle)
    h.check("Shift + two fingers: its size stays", abs(height() - before) < 1e-6 * max(1.0, before), (before, height()))
    st["turn"] = after
    where = position()
    for delta in ((13, -37), (8, -41)):  # Shift let go: pan again
        scroll(delta)
    angle = abs(st["turn"].inverted().multiply(h.view().getCameraOrientation()).Angle)
    h.check("Shift let go: it pans again (no turn)", angle < 1e-6 and (position() - where).Length > 1e-6, angle)


PREFS = "User parameter:BaseApp/Preferences/Mod/Fission180/Preferences"


def yaw(scroll_x=None, drag_x=None):
    """Degrees the view turns about the world's up axis (Z) for a Shift + two-finger scroll
    of `scroll_x` units sideways, or for a mouse orbit drag of `drag_x` pixels (orbit_ui)."""
    from fission180 import orbit_ui

    before = h.view().getCameraOrientation()
    if scroll_x is not None:
        for _ in range(3):
            scroll((scroll_x, 0), QtCore.Qt.ShiftModifier)
    else:
        orbit_ui.drag_camera(h.view(), drag_x, 0)
    turn = h.view().getCameraOrientation().multiply(before.inverted())
    return turn.Angle * 57.29578 * (1 if turn.Axis.z >= 0 else -1)


def orbit_direction():
    """Luca (2026-11-23): "the touchpad is backwards when revolving using shift and two
    fingers ... add the option to swap which way the trackpad turns"."""
    group = App.ParamGet(PREFS)
    group.SetString("TouchpadOrbit", "standard")
    standard = yaw(scroll_x=40)
    group.SetString("TouchpadOrbit", "reversed")
    reversed_ = yaw(scroll_x=40)
    group.RemString("TouchpadOrbit")
    # (a scroll of +x units pans the model +x pixels; Standard turns as a mouse drag the other
    # way, Reversed as one the same way: Reversed is how 0.1.0-beta.4.2.1 turned)
    mouse = yaw(drag_x=40)
    h.check("Touchpad orbit Standard and Reversed turn opposite ways", standard * reversed_ < 0, (standard, reversed_))
    h.check("Standard turns as a mouse drag the other way", standard * mouse < 0, (standard, mouse))
    h.check("Reversed turns as it did before (as a mouse drag the same way)", reversed_ * mouse > 0, (reversed_, mouse))


h.run(
    "touchpad_new_design",
    [
        opened("script", lambda: App.newDocument("PadScript")),
        checked("script"),
        opened("ctrl_n", lambda: Gui.runCommand("Std_New")),
        checked("ctrl_n"),
        save_first,
        opened("reopened", lambda: App.openDocument(st["saved"])),
        checked("reopened"),
        interface_off,
        interface_on,
        shift_orbits,
        orbit_direction,
    ],
    paced_by="state",
)
