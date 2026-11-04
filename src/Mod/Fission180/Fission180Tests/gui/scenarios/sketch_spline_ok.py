# SPDX-License-Identifier: LGPL-2.1-or-later
"""A spline whose ends land on existing points is kept by every way of finishing it
(Luca, 2026-11-04: "after connecting the last point and pressing ok, it just
dissapears. and it leaves behind a ton of yellow points. it only works if you press
enter").

Fusion (Autodesk's help "Create splines in a sketch"): click the points, then the green
check (or OK in the right-click menu, or Enter) makes the spline. Its ends snap to the
points they were clicked on.

A two-line L is drawn first, (10,0) - (50,0) - (50,30); each case then draws a spline from
(10,0) over the top to (50,30), both ends clicked on the L's free ends:

A  Control Point Spline, finished with the green check beside the last point.
B  Fit Point Spline, finished with the green check.
C  Control Point Spline, finished with OK in the right-click menu.
D  Fit Point Spline, finished with OK in the right-click menu.
E  Control Point Spline, finished with Enter (the way that already worked).

F  Control Point Spline closed on its first point (FreeCAD makes it at that click), then OK.
G  Control Point Spline, then Finish Sketch (the ribbon's green check) while it is drawn:
   the spline is kept, as with OK (it vanished and its points stayed behind).

After A - E: one spline more, its ends on (0,0) and (40,30) (coincident with the lines),
no loose points or circles left (every construction point / circle belongs to a spline:
FreeCAD's internal alignment), and Ctrl+Z takes the whole spline back in one press.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import sketch_input as si

V = App.Vector
EMPTY = V(-25, -25, 0)
s = {}


def session():
    from fission180 import sketch_mode

    return sketch_mode.current()


def check_button():
    from fission180 import sketch_check

    gl = h.gl_widget()
    for button in gl.findChildren(QtWidgets.QAbstractButton, sketch_check.NAME):
        if button.isVisible():
            return button
    return None


def splines():
    return [i for i, g in enumerate(s["sk"].Geometry) if g.TypeId == "Part::GeomBSplineCurve"]


def loose():
    """Construction points / circles that belong to no spline (no InternalAlignment)."""
    sk = s["sk"]
    aligned = set()
    for c in sk.Constraints:
        if c.Type == "InternalAlignment":
            aligned.add(c.First)
    out = []
    for i, g in enumerate(sk.Geometry):
        if g.TypeId in ("Part::GeomPoint", "Part::GeomCircle") and sk.getConstruction(i):
            if i not in aligned:
                out.append((i, g.TypeId))
    return out


def ends_on_the_l(index):
    g = s["sk"].Geometry[index]
    a, b = g.StartPoint, g.EndPoint
    want = (V(10, 0, 0), V(50, 30, 0))
    ok = (si.vnear(a, want[0], 1e-4) and si.vnear(b, want[1], 1e-4)) or (
        si.vnear(a, want[1], 1e-4) and si.vnear(b, want[0], 1e-4)
    )
    return ok, (a, b)


def press_check():
    h.wait_for(lambda: check_button() is not None, "the green check beside the spline's last point")
    button = check_button()
    if not h.check("the check is there to click", button is not None):
        return False
    centre = button.rect().center()
    QtTest.QTest.mouseMove(button, centre)
    QtTest.QTest.mouseClick(button, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, centre)
    QtWidgets.QApplication.processEvents()
    return True


def right_click():
    h.click(EMPTY, button=QtCore.Qt.RightButton)


# -- setup ----------------------------------------------------------------------------------
def new_design():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("SplineOK")
    h.fit()
    Gui.getMainWindow().activateWindow()


def create_sketch():
    h.ribbon("Create Sketch")


def pick_xy():
    pl.click_square("XY_Plane")


def opened():
    s["sk"] = h.in_sketch()
    h.check("sketch open on XY", s["sk"] is not None)
    h.fit(iso=False)  # straight onto the sketch, as it opens for a person


def l_tool():
    h.press("l")


def l_p1():
    si.click(V(10, 0, 0))


def l_p2():
    si.click(V(50, 0, 0))


def l_p3():
    si.click(V(50, 30, 0))


def l_done():
    si.key(QtCore.Qt.Key_Escape)


def l_check():
    h.check("the L: two lines", len(si.lines(s["sk"])) == 2, len(si.lines(s["sk"])))
    h.check("no tool running", not si.drawing())


def undo_names():
    doc = App.ActiveDocument
    return list(doc.UndoNames)[:6] if doc is not None else []


# -- one spline, finished in a given way --------------------------------------------------
def spline_case(letter, entry, how):
    """Steps: start the tool, four clicks (ends on the L's ends), finish `how`, check."""

    def start():
        s["before"] = len(splines())
        s["geo_before"] = len(s["sk"].Geometry)
        si.menu_item("CREATE", entry)

    def p1():
        si.click(V(10, 0, 0))

    def p2():
        si.click(V(18, 22, 0))

    def p3():
        si.click(V(38, 40, 0))

    def p4():
        si.click(V(50, 30, 0))

    def finish():
        h.shot("%s-before-finish" % letter)
        if how == "check":
            press_check()
        elif how == "menu":
            right_click()
            si.marking_choose("OK")
        else:
            si.key(QtCore.Qt.Key_Return)

    def made():
        h.settle("the spline to be made")
        print("[Fission 180] %s undo steps after finishing: %s" % (letter, undo_names()), flush=True)
        h.shot("%s-after-finish" % letter)
        now = splines()
        h.check(
            "%s: %s, finished with %s: one spline more" % (letter, entry, how),
            len(now) == s["before"] + 1,
            [g.TypeId for g in s["sk"].Geometry],
        )
        h.check("%s: no loose points or circles left" % letter, not loose(), loose())
        if len(now) > s["before"]:
            ok, ends = ends_on_the_l(now[-1])
            h.check("%s: the spline's ends are on the L's ends" % letter, ok, ends)
        h.check("%s: the sketch solves" % letter, s["sk"].solve() == 0, s["sk"].solve())

    def stop():
        if si.drawing():
            si.key(QtCore.Qt.Key_Escape)

    def stopped():
        h.check("%s: no tool running" % letter, not si.drawing())
        h.check("%s: the spline is still there" % letter, len(splines()) == s["before"] + 1)

    def undo():
        print("[Fission 180] %s undo steps before Ctrl+Z: %s" % (letter, undo_names()), flush=True)
        h.press("z", QtCore.Qt.ControlModifier)

    def undone():
        h.settle("the undo")
        h.check(
            "%s: one Ctrl+Z takes the whole spline back" % letter,
            len(s["sk"].Geometry) == s["geo_before"] and len(splines()) == s["before"],
            [g.TypeId for g in s["sk"].Geometry],
        )
        h.press("y", QtCore.Qt.ControlModifier)

    def redone():
        h.settle("the redo")
        h.check("%s: Ctrl+Y brings it back" % letter, len(splines()) == s["before"] + 1)

    steps = [start, p1, p2, p3, p4, finish, made, stop, stopped, undo, undone, redone]
    for step in steps:
        step.__name__ = "%s_%s" % (letter.lower(), step.__name__)
    return steps


# -- F: a closed spline (the last click on its first point), then OK ----------------------
def f_start():
    s["before"] = len(splines())
    si.menu_item("CREATE", "Control Point Spline")


def f_p1():
    si.click(V(-40, 10, 0))


def f_p2():
    si.click(V(-25, 35, 0))


def f_p3():
    si.click(V(-10, 12, 0))


def f_close():
    si.click(V(-40, 10, 0))  # back on the first point: the spline closes


def f_closed():
    h.settle("the closed spline")
    print("[Fission 180] F undo steps after closing: %s" % undo_names(), flush=True)
    h.shot("F-closed")
    h.check("F: closing on the first point makes the spline", len(splines()) == s["before"] + 1,
            [g.TypeId for g in s["sk"].Geometry])


def f_menu():
    right_click()
    si.marking_choose("OK")


def f_kept():
    h.settle("OK")
    h.shot("F-after-ok")
    print("[Fission 180] F undo steps after OK: %s" % undo_names(), flush=True)
    h.check("F: OK keeps the closed spline", len(splines()) == s["before"] + 1,
            [g.TypeId for g in s["sk"].Geometry])
    h.check("F: no loose points or circles left", not loose(), loose())
    h.check("F: the tool ended", not si.drawing())


# -- G: Finish Sketch (the ribbon's green check) while a spline is being drawn ------------
def g_start():
    s["before"] = len(splines())
    s["sketch_name"] = s["sk"].Name
    si.menu_item("CREATE", "Control Point Spline")


def g_p1():
    si.click(V(-40, -10, 0))


def g_p2():
    si.click(V(-25, -30, 0))


def g_p3():
    si.click(V(-10, -12, 0))


def g_p4():
    si.click(V(0, -30, 0))


def finish_sketch():
    h.shot("G-before-finish-sketch")
    h.ribbon("Finish Sketch")


def closed():
    h.check("the sketch is closed", h.in_sketch() is None)
    h.settle("the sketch to close")
    s["sk"] = App.ActiveDocument.getObject(s["sketch_name"])
    h.check(
        "G: Finish Sketch keeps the spline being drawn",
        len(splines()) == s["before"] + 1,
        [g.TypeId for g in s["sk"].Geometry],
    )
    h.check("G: no loose points or circles left", not loose(), loose())
    print("[Fission 180] G undo steps after Finish Sketch: %s" % undo_names(), flush=True)
    h.expect_no_errors("splines finished every way")


STEPS = (
    [new_design, create_sketch, pick_xy, opened, l_tool, l_p1, l_p2, l_p3, l_done, l_check]
    + spline_case("A", "Control Point Spline", "check")
    + spline_case("B", "Fit Point Spline", "check")
    + spline_case("C", "Control Point Spline", "menu")
    + spline_case("D", "Fit Point Spline", "menu")
    + spline_case("E", "Control Point Spline", "enter")
    + [f_start, f_p1, f_p2, f_p3, f_close, f_closed, f_menu, f_kept]
    + [g_start, g_p1, g_p2, g_p3, g_p4, finish_sketch, closed]
)


h.run("sketch_spline_ok", si.watched(STEPS), paced_by="state")
