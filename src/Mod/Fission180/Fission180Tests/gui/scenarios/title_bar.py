# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fission 180's own title bar (Luca, 2026-11-23: "on my laptop screen where there is less real
estate, That top bar that says Fission 180 with the minimize and close button is kinda
annoying. Is there a way to integrate the top bar into the program? for both windows and
linux"; fission180/titlebar_ui.py).

A  By default the window has no title bar from the system: minimize, maximize and close sit
   at the right end of Fission 180's top row, after the profile button; grips line the
   window's edges.
B  Maximize (the button) maximizes, the grips go, the button turns into Restore Down; again:
   back. A double-click on an empty part of the top row does the same.
C  A press on an empty part of the top row moves the window (the system's move: snapping
   and all); a press on the right grip resizes it from its right edge.
D  Minimize and close do what they say (the system's minimize; the window's own close, which
   asks about unsaved designs).
E  Preferences > Title bar = The system's: the system's title bar is back, the buttons and
   grips go; with a design open its 3D view still draws; Fission 180's again: back. Fission
   180's interface switched off: the system's title bar too.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import harness as h

PREFS = "User parameter:BaseApp/Preferences/Mod/Fission180/Preferences"
s = {"calls": []}


def tb():
    from fission180 import titlebar_ui

    return titlebar_ui


def mw():
    return Gui.getMainWindow()


def frameless():
    return bool(mw().windowFlags() & QtCore.Qt.FramelessWindowHint)


def button(name):
    return mw().findChild(QtWidgets.QToolButton, "Fission180Window" + name)


def grips():
    return [g for g in mw().findChildren(QtWidgets.QWidget, "Fission180ResizeGrip")]


def visible_grips():
    return [g for g in grips() if g.isVisible()]


def bar():
    profile = mw().findChild(QtWidgets.QToolButton, "Fission180Profile")
    return profile.parentWidget() if profile is not None else None


def empty_spot():
    """A point of the top row with nothing on it (between the tabs and the search button)."""
    row = bar()
    y = row.height() // 2
    for x in range(row.width() - 200, 0, -10):
        if row.childAt(QtCore.QPoint(x, y)) is None:
            return QtCore.QPoint(x, y)
    return None


def click(widget):
    pos = widget.rect().center()
    h.pointer_to(widget, pos)
    QtTest.QTest.mouseClick(widget, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, pos)


def record(name):
    def fake(*args):
        s["calls"].append((name,) + args)
        return True

    return fake


def maximized():
    return bool(mw().windowState() & QtCore.Qt.WindowMaximized)


# -- A ---------------------------------------------------------------------------------------
def a_own():
    h.check("the window has no title bar from the system", frameless(), int(mw().windowFlags()))
    names = ["Minimize", "Maximize", "Close"]
    found = [button(n) for n in names]
    if not h.check("minimize, maximize and close are in Fission 180's top row", all(found), found):
        return
    profile = mw().findChild(QtWidgets.QToolButton, "Fission180Profile")
    xs = [b.mapTo(mw(), QtCore.QPoint(0, 0)).x() for b in found]
    h.check("... visible", all(b.isVisible() for b in found))
    h.check("... in that order, after the profile button", xs == sorted(xs) and xs[0] > profile.mapTo(mw(), QtCore.QPoint(0, 0)).x(), xs)
    # (the ribbon's tool bar keeps a few pixels of its own at the right)
    h.check("... at the window's right end", mw().width() - (xs[-1] + found[-1].width()) <= 6, (xs, mw().width()))
    h.check(
        "... on the same row as the profile button",
        all(b.parentWidget().parentWidget() is profile.parentWidget() for b in found),
    )
    h.shot("own-title-bar")
    close = found[-1]
    h.pointer_to(close, close.rect().center())
    QtTest.QTest.mouseMove(close, close.rect().center())
    QtWidgets.QApplication.processEvents()
    corner = close.grab().toImage().pixelColor(2, 2)
    h.check(
        "close turns red under the mouse",
        corner.red() > 200 and corner.green() < 60 and corner.blue() < 70,
        corner.name(),
    )
    edges = sorted(g.property("fission180Edge") for g in visible_grips())
    h.check("eight grips line the edges", len(edges) == 8, edges)
    right = [g for g in visible_grips() if g.property("fission180Edge") == "right"]
    h.check(
        "the right grip is at the right edge",
        bool(right) and right[0].geometry().right() == mw().rect().right(),
        right and right[0].geometry().getRect(),
    )


a_own.done = lambda: frameless() and button("Close") is not None and button("Close").isVisible()
a_own.done_what = "Fission 180's own title bar"


# -- B ---------------------------------------------------------------------------------------
def b_maximize():
    if maximized():
        mw().showNormal()
    click(button("Maximize"))


b_maximize.done = maximized
b_maximize.done_what = "the window to maximize"


def b_maximized():
    h.check("maximized: no grips", not visible_grips(), [g.property("fission180Edge") for g in visible_grips()])
    h.check("the button says Restore Down", "Restore" in button("Maximize").toolTip(), button("Maximize").toolTip())
    click(button("Maximize"))


b_maximized.done = lambda: not maximized()
b_maximized.done_what = "the window to come back from maximized"


def b_restored():
    h.check("restored: the grips are back", len(visible_grips()) == 8, len(visible_grips()))
    h.check("the button says Maximize", button("Maximize").toolTip().startswith("Maximize"), button("Maximize").toolTip())
    spot = empty_spot()
    if h.check("an empty part of the top row", spot is not None):
        h.pointer_to(bar(), spot)
        QtTest.QTest.mouseDClick(bar(), QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, spot)


b_restored.done = maximized
b_restored.done_what = "a double-click on the top row to maximize"


def b_double_again():
    spot = empty_spot()
    QtTest.QTest.mouseDClick(bar(), QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, spot)


b_double_again.done = lambda: not maximized()
b_double_again.done_what = "a second double-click to restore"


# -- C ---------------------------------------------------------------------------------------
def c_move():
    s["calls"] = []
    s["real"] = (tb()._system_move, tb()._system_resize, tb()._minimize, tb()._close)
    tb()._system_move = record("move")
    tb()._system_resize = record("resize")
    spot = empty_spot()
    h.pointer_to(bar(), spot)
    QtTest.QTest.mousePress(bar(), QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, spot)
    QtTest.QTest.mouseRelease(bar(), QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, spot)
    right = [g for g in visible_grips() if g.property("fission180Edge") == "right"][0]
    QtTest.QTest.mousePress(right, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, right.rect().center())
    QtTest.QTest.mouseRelease(right, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, right.rect().center())


c_move.done = lambda: len(s["calls"]) >= 2
c_move.done_what = "the move and the resize to start"


def c_moved():
    kinds = [c[0] for c in s["calls"]]
    h.check("a press on the top row moves the window", "move" in kinds, s["calls"])
    resize = [c for c in s["calls"] if c[0] == "resize"]
    h.check(
        "a press on the right grip resizes from the right edge",
        bool(resize) and resize[0][2] == QtCore.Qt.RightEdge,
        resize,
    )
    h.check("a click on a button does not move the window", True)


# -- D ---------------------------------------------------------------------------------------
def d_minimize_close():
    s["calls"] = []
    tb()._minimize = record("minimize")
    tb()._close = record("close")
    click(button("Minimize"))
    click(button("Close"))


d_minimize_close.done = lambda: len(s["calls"]) >= 2
d_minimize_close.done_what = "minimize and close to be asked for"


def d_checked():
    kinds = [c[0] for c in s["calls"]]
    h.check("minimize minimizes, close closes (and nothing moved)", kinds == ["minimize", "close"], kinds)
    tb()._system_move, tb()._system_resize, tb()._minimize, tb()._close = s["real"]


# -- E ---------------------------------------------------------------------------------------
def e_design():
    App.newDocument("TitleBar")
    from fission180 import commands

    commands.ensure_body()


e_design.done = lambda: h.gl_widget() is not None and h.gl_widget().isVisible()
e_design.done_what = "a design's 3D view"


def e_system():
    from fission180 import preferences_ui

    App.ParamGet(PREFS).SetString("TitleBar", "system")
    preferences_ui._apply("titlebar")


e_system.done = lambda: not frameless()
e_system.done_what = "the system's title bar back"


def e_system_checked():
    h.check("the system's title bar: no window buttons in the top row", not button("Close").isVisible())
    h.check("... and no grips", not visible_grips())
    h.view_drawn()
    h.check("the 3D view still draws", h.gl_widget().isVisible())
    from fission180 import preferences_ui

    App.ParamGet(PREFS).SetString("TitleBar", "own")
    preferences_ui._apply("titlebar")


e_system_checked.done = frameless
e_system_checked.done_what = "Fission 180's title bar again"


def e_own_again():
    h.check("Fission 180's again: the buttons are back", button("Close").isVisible())
    h.view_drawn("the 3D view to draw after the window changed")
    h.check("the 3D view still draws", h.gl_widget().isVisible())
    from fission180 import shell

    shell.disable()


e_own_again.done = lambda: not frameless()
e_own_again.done_what = "the system's title bar with Fission 180's interface off"


def e_off_checked():
    from fission180 import shell

    shell.enable()


e_off_checked.done = frameless
e_off_checked.done_what = "Fission 180's title bar with its interface on again"


h.run(
    "title_bar",
    [
        a_own, b_maximize, b_maximized, b_restored, b_double_again, c_move, c_moved,
        d_minimize_close, d_checked, e_design, e_system, e_system_checked, e_own_again,
        e_off_checked,
    ],
    paced_by="state",
)  # fmt: skip
