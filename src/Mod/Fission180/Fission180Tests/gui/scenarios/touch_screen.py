# SPDX-License-Identifier: LGPL-2.1-or-later
"""The touchscreen in the 3D view (Luca, 2026-11-23: "My laptop has a touch screen ... panning
around while using the touchscreen ... That and Zoom"; docs/fission180/touchscreen-design.md).

Fingers are simulated touch points (QTest touch sequences from a touchscreen device) on the
3D view's drawing area, the way Qt delivers a real touchscreen's:
1. one finger dragged turns the view; two fingers dragged pan it (it does not turn); a spread
   zooms (it does not turn);
2. a tap on the body selects it;
3. a finger held still opens the right-click menu; so does a two-finger tap;
4. with Extrude's dialog open one finger works like the mouse: a drag does not turn the view;
5. Preferences > Touchscreen Off: a finger drag does not turn the view either.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import harness as h

s = {}
PREFS = "User parameter:BaseApp/Preferences/Mod/Fission180/Preferences"


def gl():
    return h.gl_widget()


def device():
    if "device" not in s:
        s["device"] = QtTest.QTest.createTouchDevice(QtGui.QInputDevice.DeviceType.TouchScreen)
    return s["device"]


def touch(steps):
    """steps: [{finger: (x, y) or None}] one touch event each; None lifts that finger."""
    widget = gl()
    down = set()
    for step in steps:
        seq = QtTest.QTest.touchEvent(widget, device())
        for finger, pos in step.items():
            if pos is None:
                seq.release(finger, QtCore.QPoint(*s["last"][finger]), widget)
                down.discard(finger)
            elif finger in down:
                seq.move(finger, QtCore.QPoint(*pos), widget)
                s["last"][finger] = pos
            else:
                seq.press(finger, QtCore.QPoint(*pos), widget)
                down.add(finger)
                s["last"][finger] = pos
        for finger in down:
            if finger not in step:
                seq.stationary(finger)
        seq.commit()


def centre():
    widget = gl()
    return widget.width() // 2, widget.height() // 2


def camera():
    view = Gui.ActiveDocument.ActiveView
    return view.getCameraOrientation().Q, view.getCamera()


def turned():
    return Gui.ActiveDocument.ActiveView.getCameraOrientation().Q != s["camera"][0]


def moved():
    return Gui.ActiveDocument.ActiveView.getCamera() != s["camera"][1]


def menu():
    from fission180 import marking_menu

    for widget in QtWidgets.QApplication.topLevelWidgets() + Gui.getMainWindow().findChildren(
        QtWidgets.QWidget
    ):
        if isinstance(widget, marking_menu.MarkingMenu) and widget.isVisible():
            return widget
    return None


def close_menu():
    widget = menu()
    if widget is not None:
        widget.close()


# -- 1. orbit, pan, zoom ---------------------------------------------------------------------
def setup():
    s["last"] = {}
    App.ParamGet(PREFS).SetString("Touchscreen", "on")
    App.newDocument("Touch")
    from fission180 import commands, extrude, sketch_ui

    body = commands.ensure_body()
    planes = sketch_ui.origin_planes(body)
    sk = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    h.draw_rectangle(sk, -20, -15, 20, 15)
    extrude.make(body, sk, {"distance": 10.0})
    s["sketch2"] = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    h.draw_rectangle(s["sketch2"], 30, 0, 50, 20)
    App.ActiveDocument.recompute()
    Gui.Selection.clearSelection()
    h.fit()


def _taking_touch():
    from fission180 import orbit_ui, touch_ui

    widget = gl()
    return widget.testAttribute(QtCore.Qt.WA_AcceptTouchEvents) and any(
        orbit_ui._same(w, widget) for w in touch_ui._state["widgets"]
    )


setup.done = _taking_touch
setup.done_what = "the 3D view to take touch"


def one_finger():
    s["camera"] = camera()
    x, y = centre()
    touch([{1: (x + 200, y + 200)}] + [{1: (x + 200 + 12 * i, y + 200)} for i in range(1, 11)] + [{1: None}])


one_finger.done = turned
one_finger.done_what = "a one-finger drag to turn the view"


def two_fingers():
    s["camera"] = camera()
    x, y = centre()
    steps = [{1: (x - 50, y + 150), 2: (x + 50, y + 150)}]
    steps += [{1: (x - 50 + 8 * i, y + 150 - 6 * i), 2: (x + 50 + 8 * i, y + 150 - 6 * i)} for i in range(1, 11)]
    touch(steps + [{1: None, 2: None}])


two_fingers.done = moved
two_fingers.done_what = "a two-finger drag to move the view"


def panned():
    h.check("two fingers pan: the view did not turn", not turned())


def spread():
    s["camera"] = camera()
    x, y = centre()
    steps = [{1: (x - 40, y), 2: (x + 40, y)}]
    steps += [{1: (x - 40 - 8 * i, y), 2: (x + 40 + 8 * i, y)} for i in range(1, 11)]
    touch(steps + [{1: None, 2: None}])


spread.done = moved
spread.done_what = "a spread to zoom"


def zoomed():
    h.check("a pinch zooms: the view did not turn", not turned())


# -- 2. a tap selects ------------------------------------------------------------------------
def tap():
    Gui.Selection.clearSelection()
    h.fit()
    s["camera"] = camera()
    view = Gui.ActiveDocument.ActiveView
    point = view.getPointOnViewport(App.Vector(0, 0, 10))  # (the top face's middle)
    widget = gl()
    ratio = widget.devicePixelRatioF()
    x, y = int(point[0] / ratio), int(widget.height() - point[1] / ratio)
    touch([{1: (x, y)}, {1: None}])


tap.done = lambda: bool(Gui.Selection.getSelectionEx())
tap.done_what = "a tap on the body to select it"


def tapped():
    h.check("a tap does not turn the view", not turned())
    Gui.Selection.clearSelection()


# -- 3. right clicks -------------------------------------------------------------------------
def long_press():
    x, y = centre()
    touch([{1: (x + 250, y - 150)}])  # (held: the menu comes after half a second)


long_press.done = lambda: menu() is not None
long_press.done_what = "the right-click menu after a long press"


def long_press_up():
    touch([{1: None}])
    close_menu()


long_press_up.done = lambda: menu() is None
long_press_up.done_what = "the menu to close"


def two_finger_tap():
    x, y = centre()
    touch([{1: (x + 230, y - 150), 2: (x + 290, y - 150)}, {1: None, 2: None}])


two_finger_tap.done = lambda: menu() is not None
two_finger_tap.done_what = "the right-click menu after a two-finger tap"


def two_finger_tap_closed():
    close_menu()


two_finger_tap_closed.done = lambda: menu() is None
two_finger_tap_closed.done_what = "the menu to close"


# -- 4. a command open: one finger is the mouse ---------------------------------------------
def open_extrude():
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(App.ActiveDocument.Name, s["sketch2"].Name)
    Gui.runCommand("Fission180_Extrude")


open_extrude.done = lambda: bool(Gui.Control.activeDialog())
open_extrude.done_what = "the Extrude dialog to open"


def drag_in_command():
    s["camera"] = camera()
    x, y = centre()
    touch([{1: (x - 300, y + 250)}] + [{1: (x - 300 + 10 * i, y + 250 - 4 * i)} for i in range(1, 11)] + [{1: None}])


drag_in_command.done = lambda: bool(Gui.Control.activeDialog())
drag_in_command.done_what = "the drag to be over with the dialog still open"


def mouse_like():
    h.check("with a dialog open a one-finger drag does not turn the view", not turned())
    Gui.Control.closeDialog()


mouse_like.done = lambda: not Gui.Control.activeDialog()
mouse_like.done_what = "the dialog to close"


# -- 5. Off --------------------------------------------------------------------------------------
def switched_off():
    App.ParamGet(PREFS).SetString("Touchscreen", "off")
    s["camera"] = camera()
    x, y = centre()
    touch([{1: (x + 200, y + 200)}] + [{1: (x + 200 + 12 * i, y + 200)} for i in range(1, 11)] + [{1: None}])


def off_checked():
    h.check("Touchscreen Off: a one-finger drag does not turn the view", not turned())
    App.ParamGet(PREFS).SetString("Touchscreen", "on")
    Gui.Selection.clearSelection()


h.run(
    "touch_screen",
    [
        setup, one_finger, two_fingers, panned, spread, zoomed, tap, tapped, long_press,
        long_press_up, two_finger_tap, two_finger_tap_closed, open_extrude, drag_in_command,
        mouse_like, switched_off, off_checked,
    ],
    paced_by="state",
)  # fmt: skip
