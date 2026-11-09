# SPDX-License-Identifier: LGPL-2.1-or-later
"""A laptop's touchpad in the 3D view (Luca, 2026-11-09: "2 fingers drag to pan, pinch to
zoom ... im ok with no rotation"): touchpad_ui.py, touchpad_core.py.

Real Qt events sent to the 3D view's drawing area as the system hands them over (a real wheel
event the drawing area does not take goes on to the viewer around it: sent ones are sent there
too). A block 40 x 30 x 10, orthographic, fitted. Checked:
  T1 Two fingers (Linux / Windows: wheel units that are no whole notch, sideways too): the
     view pans, the model follows the fingers, the view's size and direction do not change.
  T2 Two fingers on macOS / Wayland (scroll phases, pixel deltas): the model moves by those
     pixels; a touchpad Qt names as one pans even with whole notches.
  T3 A mouse wheel notch still zooms (FreeCAD's own zoom: the drawing area lets it go on);
     a high-resolution wheel's eighth of a notch too.
  T4 A Windows pinch (Ctrl + touchpad wheel) zooms in about the pointer: the point under it
     stays put. Ctrl + a mouse wheel zooms as before.
  T5 A pinch (Qt's zoom gesture, macOS / Wayland / X11): fingers apart zoom in about the
     pointer, together zoom out; the fingers' middle moving pans; with Reverse zoom
     direction ticked a spread still zooms in.
  T6 Preferences > General > Touchpad = Off: the touchpad scroll zooms as before, a pinch
     does nothing. On: a mouse wheel notch pans too. Auto again.
  T7 Scrolling over the browser does not move the view. Fission 180 switched off: FreeCAD's
     own wheel handling (nothing taken).
"""

import math

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui, QtWidgets

from Fission180Tests.gui import dialog_input as di
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import insert_steps as i
from Fission180Tests.gui import misc_steps as m
from Fission180Tests.gui import viewcube_input as vc
from Fission180Tests.gui import widget_input as w

V = App.Vector
VIEW = "User parameter:BaseApp/Preferences/View"
PREFS = "User parameter:BaseApp/Preferences/Mod/Fission180/Preferences"
NONE = QtCore.Qt.NoModifier
CTRL = QtCore.Qt.ControlModifier
CENTRE = V(20, 15, 10)  # the middle of the block's top face
OFF_CENTRE = V(34, 26, 10)  # a corner of the top face, away from the window's middle
st = {}


def touchpad():
    from fission180 import touchpad_ui

    return touchpad_ui


def camera():
    return h.view().getCameraNode()


def cam():
    """(position, height, orientation) of the camera now."""
    c = camera()
    pos = V(*c.position.getValue().getValue())
    return pos, float(c.height.getValue()), h.view().getCameraOrientation()


def gl():
    return h.gl_widget()


def viewer():
    widget = gl()
    while widget is not None and widget.metaObject().className() != "Gui::View3DInventorViewer":
        widget = widget.parentWidget()
    return widget


_DEVICE = {}


def touchpad_device():
    """A pointing device Qt calls a touchpad (as Qt 6 does for one it recognises)."""
    if "pad" not in _DEVICE:
        _DEVICE["pad"] = QtGui.QPointingDevice(
            "Fission 180 test touchpad",
            4711,
            QtGui.QInputDevice.DeviceType.TouchPad,
            QtGui.QPointingDevice.PointerType.Finger,
            QtGui.QInputDevice.Capability.Position | QtGui.QInputDevice.Capability.Scroll,
            5,
            0,
        )
    return _DEVICE["pad"]


def wheel(
    angle,
    pixel=(0, 0),
    phase=QtCore.Qt.NoScrollPhase,
    modifiers=NONE,
    device=None,
    at=None,
    target=None,
):
    """A wheel event over widget pixel `at` of the drawing area (default its middle), sent
    to `target` (the drawing area unless said). Returns whether something took it."""
    area = gl()
    target = target or area
    at = at or QtCore.QPoint(area.width() // 2, area.height() // 2)
    pos = QtCore.QPointF(target.mapFrom(area, at)) if target is not area else QtCore.QPointF(at)
    args = [
        pos,
        QtCore.QPointF(area.mapToGlobal(at)),
        QtCore.QPoint(*pixel),
        QtCore.QPoint(*angle),
        QtCore.Qt.NoButton,
        modifiers,
        phase,
        False,
    ]
    if device is not None:
        args += [QtCore.Qt.MouseEventNotSynthesized, device]
    event = QtGui.QWheelEvent(*args)
    QtWidgets.QApplication.sendEvent(target, event)
    QtWidgets.QApplication.processEvents()
    return event.isAccepted()


def as_qt_hands_it_on(angle, **kw):
    """A wheel event the way Qt delivers a real one: to the drawing area first, then (not
    taken there) on to the viewer, where FreeCAD zooms. True when the drawing area took it."""
    taken = wheel(angle, **kw)
    if not taken:
        wheel(angle, target=viewer(), **kw)
    return taken


def gesture(kind, value=0.0, at=None, delta=(0, 0), fingers=2):
    """Qt's native gesture event over widget pixel `at` of the drawing area."""
    area = gl()
    at = at or QtCore.QPoint(area.width() // 2, area.height() // 2)
    event = QtGui.QNativeGestureEvent(
        kind,
        touchpad_device(),
        fingers,
        QtCore.QPointF(at),
        QtCore.QPointF(at),
        QtCore.QPointF(area.mapToGlobal(at)),
        float(value),
        QtCore.QPointF(*delta),
    )
    QtWidgets.QApplication.sendEvent(area, event)
    QtWidgets.QApplication.processEvents()
    return event.isAccepted()


G = QtCore.Qt.NativeGestureType


def pinch(value, at=None):
    gesture(G.BeginNativeGesture, at=at)
    taken = gesture(G.ZoomNativeGesture, value, at=at)
    gesture(G.EndNativeGesture, at=at)
    return taken


def scroll_ended():
    """The last scroll is over (a person lifts the fingers before reaching for the mouse):
    the next wheel event starts a new one (touchpad_core.STREAM_GAP)."""
    import time

    from fission180 import touchpad_core

    filt = touchpad()._state["filter"]
    last = filt.stream.last if filt is not None else None
    return last is None or time.monotonic() - last > touchpad_core.STREAM_GAP


def same_size(before, after):
    return abs(before[1] - after[1]) <= 1e-6 * max(1.0, before[1])


def same_turn(before, after):
    return abs(before[2].inverted().multiply(after[2]).Angle) < 1e-6


def moved(before_px, after_px):
    return after_px.x() - before_px.x(), after_px.y() - before_px.y()


def near(a, b, tol):
    return abs(a - b) <= tol


# -- setup ----------------------------------------------------------------------------------
def setup():
    vc.setup("Touchpad")
    h.view().setCameraType("Orthographic")
    h.view().viewIsometric()
    h.fit()


def defaults():
    module = touchpad()
    h.check("touchpad_ui watches the 3D view", module.watched() >= 2, module.watched())
    h.check("Touchpad is Auto by default", module.mode() == "auto", module.mode())
    st["start"] = cam()


# -- T1 -------------------------------------------------------------------------------------
def t1_two_fingers():
    before = cam()
    before_px = h.screen_point(CENTRE)
    taken = []
    for delta in ((13, -37), (8, -41), (0, -29), (-5, -35)):  # (x, y) units: up and a bit right
        taken.append(as_qt_hands_it_on(delta))
    after = cam()
    after_px = h.screen_point(CENTRE)
    dx, dy = moved(before_px, after_px)
    # units / 8 are pixels on Linux (touchpad_core.PIXELS_PER_NOTCH): 16/8 = 2, -142/8 = -17.75
    h.check("T1 the drawing area took the two-finger scroll", all(taken), taken)
    h.check("T1 the view panned", (after[0] - before[0]).Length > 1e-3, (before[0], after[0]))
    h.check("T1 its size did not change", same_size(before, after), (before[1], after[1]))
    h.check("T1 nor its direction", same_turn(before, after))
    h.check(
        "T1 the model followed the fingers (2, -17.75 pixels)",
        near(dx, 2.0, 1.5) and near(dy, -17.75, 1.5),
        (dx, dy),
    )
    h.shot("T1-panned")


t1_two_fingers.ready = lambda: scroll_ended()


def t1_sideways():
    before_px = h.screen_point(CENTRE)
    before = cam()
    taken = as_qt_hands_it_on((-120, 0))  # sideways: only a touchpad (or a tilted wheel)
    dx, dy = moved(before_px, h.screen_point(CENTRE))
    h.check("T1 a sideways scroll pans sideways", taken and near(dx, -15, 1.5) and near(dy, 0, 1), (dx, dy))
    h.check("T1 ... without zooming", same_size(before, cam()))


# -- T2 -------------------------------------------------------------------------------------
def t2_phases():
    before = cam()
    before_px = h.screen_point(CENTRE)
    taken = [wheel((0, 0), phase=QtCore.Qt.ScrollBegin)]
    for _ in range(3):
        taken.append(wheel((48, 96), pixel=(6, 12), phase=QtCore.Qt.ScrollUpdate))
    taken.append(wheel((0, 0), phase=QtCore.Qt.ScrollEnd))
    dx, dy = moved(before_px, h.screen_point(CENTRE))
    h.check("T2 the scroll (begin, updates, end) was taken", all(taken), taken)
    h.check(
        "T2 the model moved by the system's pixels (18, 36)",
        near(dx, 18, 1.5) and near(dy, 36, 1.5),
        (dx, dy),
    )
    h.check("T2 no zoom", same_size(before, cam()))


t2_phases.ready = lambda: scroll_ended()


def t2_named_touchpad():
    before = cam()
    before_px = h.screen_point(CENTRE)
    taken = wheel((0, 120), device=touchpad_device())  # a whole notch, but Qt says touchpad
    dx, dy = moved(before_px, h.screen_point(CENTRE))
    h.check("T2 Qt's touchpad pans even with a whole notch", taken and near(dy, 15, 1.5), (dx, dy))
    h.check("T2 ... without zooming", same_size(before, cam()))


t2_named_touchpad.ready = lambda: scroll_ended()


# -- T3 -------------------------------------------------------------------------------------
def t3_mouse_wheel():
    before = cam()
    taken = as_qt_hands_it_on((0, 120))
    after = cam()
    h.check("T3 the drawing area lets a mouse wheel notch go on", not taken)
    ratio = after[1] / before[1]
    h.check(
        "T3 a mouse wheel notch away from you still zooms in (FreeCAD's step)",
        near(ratio, math.exp(-0.2), 0.01),
        ratio,
    )
    h.check("T3 ... and does not turn the view", same_turn(before, after))
    st["t3"] = after


t3_mouse_wheel.ready = lambda: scroll_ended()


def t3_mouse_back():
    before = cam()
    as_qt_hands_it_on((0, -240))  # two notches towards you at once
    ratio = cam()[1] / before[1]
    h.check("T3 two notches back zoom out two steps", near(ratio, math.exp(0.4), 0.02), ratio)


t3_mouse_back.ready = lambda: scroll_ended()


def t3_fine_wheel():
    before = cam()
    taken = as_qt_hands_it_on((0, 15))  # an eighth of a notch (a high-resolution wheel)
    ratio = cam()[1] / before[1]
    h.check("T3 a high-resolution wheel's step goes on to FreeCAD", not taken)
    h.check("T3 ... and zooms in a little", near(ratio, math.exp(-0.2 / 8), 0.003), ratio)


t3_fine_wheel.ready = lambda: scroll_ended()


# -- T4 -------------------------------------------------------------------------------------
def t4_windows_pinch():
    area = gl()
    at = h.screen_point(OFF_CENTRE)
    before = cam()
    taken = as_qt_hands_it_on((0, 37), modifiers=CTRL, at=at)
    taken = as_qt_hands_it_on((0, 41), modifiers=CTRL, at=at) and taken
    after = cam()
    ratio = after[1] / before[1]
    still = h.screen_point(OFF_CENTRE)
    h.check("T4 the drawing area took Ctrl + touchpad scroll", taken)
    h.check(
        "T4 a Windows pinch apart zooms in (FreeCAD's step per notch)",
        near(ratio, math.exp(-0.2 * 78 / 120), 0.01),
        ratio,
    )
    h.check(
        "T4 about the pointer: the point under it stays put",
        abs(still.x() - at.x()) <= 2 and abs(still.y() - at.y()) <= 2,
        (at, still, area.size()),
    )
    h.shot("T4-pinch-zoomed")


t4_windows_pinch.ready = lambda: scroll_ended()


def t4_ctrl_mouse_wheel():
    before = cam()
    taken = as_qt_hands_it_on((0, -120), modifiers=CTRL)
    ratio = cam()[1] / before[1]
    h.check("T4 Ctrl + a mouse wheel goes on to FreeCAD", not taken)
    h.check("T4 ... and zooms as before (out)", near(ratio, math.exp(0.2), 0.01), ratio)


t4_ctrl_mouse_wheel.ready = lambda: scroll_ended()


# -- T5 -------------------------------------------------------------------------------------
def t5_pinch():
    h.fit()
    at = h.screen_point(OFF_CENTRE)
    before = cam()
    taken = pinch(0.25, at=at)
    after = cam()
    ratio = after[1] / before[1]
    still = h.screen_point(OFF_CENTRE)
    h.check("T5 the zoom gesture was taken", taken)
    h.check("T5 fingers apart zoom in (1.25 times)", near(ratio, 1 / 1.25, 0.01), ratio)
    h.check(
        "T5 about the pointer",
        abs(still.x() - at.x()) <= 2 and abs(still.y() - at.y()) <= 2,
        (at, still),
    )
    h.check("T5 the view did not turn", same_turn(before, after))
    st["t5"] = after


def t5_pinch_in():
    before = cam()
    # a slow pinch: each step alone is less than one of FreeCAD's wheel units; they add up
    gesture(G.BeginNativeGesture)
    small = [gesture(G.ZoomNativeGesture, -0.0015) for _ in range(10)]
    gesture(G.EndNativeGesture)
    ratio = cam()[1] / before[1]
    h.check("T5 fingers together zoom out, tiny steps add up", all(small) and ratio > 1.01, ratio)


def t5_middle_moves():
    before = cam()
    before_px = h.screen_point(CENTRE)
    gesture(G.BeginNativeGesture)
    taken = gesture(G.PanNativeGesture, delta=(12, -8))
    gesture(G.EndNativeGesture)
    dx, dy = moved(before_px, h.screen_point(CENTRE))
    h.check("T5 the fingers' middle moving pans", taken and near(dx, 12, 1.5) and near(dy, -8, 1.5), (dx, dy))
    h.check("T5 ... without zooming", same_size(before, cam()))
    swipe = gesture(G.PanNativeGesture, delta=(30, 0), fingers=3)
    h.check("T5 a three-finger swipe is not taken (the system's)", not swipe)


def t5_reversed():
    App.ParamGet(VIEW).SetBool("InvertZoom", False)  # Reverse zoom direction ticked
    before = cam()
    pinch(0.25)
    ratio = cam()[1] / before[1]
    App.ParamGet(VIEW).SetBool("InvertZoom", True)
    h.check("T5 with Reverse zoom direction a spread still zooms in", near(ratio, 0.8, 0.01), ratio)
    h.shot("T5-pinched")


# -- T6 -------------------------------------------------------------------------------------
def dialog():
    from fission180 import preferences_ui

    d = preferences_ui.PreferencesDialog.last
    try:
        return d if d is not None and d.isVisible() else None
    except RuntimeError:
        return None


def pref_widget(key):
    d = dialog()
    return d.widgets.get(key) if d is not None else None


def press(name):
    d = dialog()
    b = m.find_child(d, name) if d is not None else None
    if h.check("button %s" % name, b is not None):
        w.click(b)
        m.process()


def open_prefs():
    i.ribbon_tab("UTILITIES")
    h.ribbon("Preferences")
    m.process()


def t6_open():
    open_prefs()


def t6_off():
    combo = pref_widget("touchpad")
    h.check("T6 Preferences > General has Touchpad", combo is not None)
    if combo is None:
        return
    items = [combo.itemText(n) for n in range(combo.count())]
    h.check("T6 Auto, Off, On", items == ["Auto", "Off", "On"], items)
    h.check("T6 Auto chosen", combo.currentText() == "Auto", combo.currentText())
    h.shot("T6-preferences")
    di.choose(combo, "Off")
    press("Fission180PreferencesOK")


t6_off.ready = lambda: pref_widget("touchpad") is not None
t6_off.done = lambda: dialog() is None


def t6_off_done():
    h.check("T6 the window closed", dialog() is None)
    h.check("T6 kept as Off", App.ParamGet(PREFS).GetString("Touchpad", "") == "off")
    h.check("T6 touchpad_ui reads Off", touchpad().mode() == "off")



def t6_off_scroll():
    before = cam()
    taken = as_qt_hands_it_on((0, 37))
    after = cam()
    h.check("T6 Off: the drawing area lets a two-finger scroll go on", not taken)
    h.check(
        "T6 Off: ... and it zooms, as before",
        near(after[1] / before[1], math.exp(-0.2 * 37 / 120), 0.01),
        after[1] / before[1],
    )
    before = cam()
    taken = pinch(0.25)
    h.check("T6 Off: a pinch is not taken", not taken)
    h.check("T6 Off: ... and does nothing", same_size(before, cam()))


t6_off_scroll.ready = lambda: scroll_ended()


def t6_on():
    App.ParamGet(PREFS).SetString("Touchpad", "on")  # (the window's choice, as above)
    before = cam()
    before_px = h.screen_point(CENTRE)
    taken = as_qt_hands_it_on((0, 120))
    dx, dy = moved(before_px, h.screen_point(CENTRE))
    h.check("T6 On: a whole notch pans too", taken and near(dy, 15, 1.5), (dx, dy))
    h.check("T6 On: ... without zooming", same_size(before, cam()))
    before = cam()
    taken = as_qt_hands_it_on((0, 120), modifiers=CTRL)
    ratio = cam()[1] / before[1]
    h.check("T6 On: Ctrl + scroll zooms in", taken and near(ratio, math.exp(-0.2), 0.01), ratio)
    App.ParamGet(PREFS).SetString("Touchpad", "auto")


t6_on.ready = lambda: scroll_ended()


# -- T7 -------------------------------------------------------------------------------------
def t7_browser():
    from fission180 import browser_ui

    tree = browser_ui.widget()
    h.check("T7 the browser is there", tree is not None)
    if tree is None:
        return
    before = cam()
    viewport = tree.viewport()
    at = QtCore.QPoint(viewport.width() // 2, viewport.height() // 2)
    event = QtGui.QWheelEvent(
        QtCore.QPointF(at),
        QtCore.QPointF(viewport.mapToGlobal(at)),
        QtCore.QPoint(0, 0),
        QtCore.QPoint(0, -37),
        QtCore.Qt.NoButton,
        NONE,
        QtCore.Qt.NoScrollPhase,
        False,
    )
    QtWidgets.QApplication.sendEvent(viewport, event)
    QtWidgets.QApplication.processEvents()
    after = cam()
    h.check(
        "T7 a two-finger scroll over the browser leaves the view alone",
        (after[0] - before[0]).Length < 1e-9 and same_size(before, after),
    )


t7_browser.ready = lambda: scroll_ended()


def t7_off():
    Gui.activateWorkbench("PartDesignWorkbench")


t7_off.done = lambda: touchpad().watched() == 0


def t7_off_done():
    h.check("T7 Fission 180 off: the filter is gone", touchpad().watched() == 0, touchpad().watched())
    before = cam()
    taken = wheel((0, -37))
    h.check("T7 Fission 180 off: a two-finger scroll is not taken", not taken)
    h.check("T7 ... and does not pan", (cam()[0] - before[0]).Length < 1e-9)
    Gui.activateWorkbench("Fission180Workbench")


t7_off_done.ready = lambda: scroll_ended()
t7_off_done.done = lambda: touchpad().watched() >= 2


def t7_back():
    h.check("T7 back in Fission 180: watched again", touchpad().watched() >= 2, touchpad().watched())
    before = cam()
    taken = as_qt_hands_it_on((5, -37))
    h.check("T7 ... and two fingers pan again", taken and same_size(before, cam()))


t7_back.ready = lambda: scroll_ended() and touchpad().watched() >= 2


def cleanup():
    for name in list(App.listDocuments()):
        Gui.getDocument(name).Modified = False
        App.closeDocument(name)


h.run(
    "navigation_touchpad",
    [
        setup,
        defaults,
        t1_two_fingers,
        t1_sideways,
        t2_phases,
        t2_named_touchpad,
        t3_mouse_wheel,
        t3_mouse_back,
        t3_fine_wheel,
        t4_windows_pinch,
        t4_ctrl_mouse_wheel,
        t5_pinch,
        t5_pinch_in,
        t5_middle_moves,
        t5_reversed,
        t6_open,
        t6_off,
        t6_off_done,
        t6_off_scroll,
        t6_on,
        t7_browser,
        t7_off,
        t7_off_done,
        t7_back,
        cleanup,
    ],
    paced_by="state",
)
