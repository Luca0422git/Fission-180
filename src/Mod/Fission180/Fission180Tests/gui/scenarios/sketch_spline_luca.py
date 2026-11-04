# SPDX-License-Identifier: LGPL-2.1-or-later
"""Luca's own steps, 2026-11-04 (after patch 0.1.0-beta.3.3.1: "the first time the spline
failed ... it worked the second time ... i created another file, tried the same thing, and
now the spline still disapears when i click the checkmark. AND the orange dots are still
there"; then "i went and tried to cut the top of the rectangle and only the middle portion
of the line was getting deleted. some of it is staying back at the corners").

Everything with the mouse, as a person does it (the ribbon's big buttons, the floating
check, Finish Sketch): a rectangle whose left side is on the Y axis, a spline over its top
from the top-left corner to the top-right corner, then Trim on the rectangle's top line.

A  First design, first spline of the session: Fit Point Spline (the big Spline button), six
   points from corner to corner, the green check beside the last point: the spline is made,
   its ends on the corners, no loose points left.
B  A second spline in the same sketch (Control Point Spline, from the menu), the check.
C  Trim (T) on the rectangle's top line, under the splines: the whole top line goes (the
   splines touch it only at the corners), nothing of it stays at the corners.
D  A new design, the same steps again with Finish Sketch (the ribbon's green check) at the
   end instead of the floating check: the spline is kept, no loose points.
E  A third design: the spline started, the pointer moved over the ribbon and back (as a
   hand does on its way to a button), the floating check.
F  The Line tool on (two lines drawn, no Esc), then Control Point Spline started from the
   command search (S): the check sits by the spline's last point (not the old line's end)
   and makes the spline. (Before: search did not record the command, so the spline was not
   recognised; the check ended the Line "chain" instead and the spline was lost.)
F2 The same with FreeCAD's spline tool started directly (its own toolbar would: nothing of
   Fission 180 records it): FreeCAD's spline panel tells the spline is being drawn.
G  FreeCAD's spline tool does not make the spline on Fission 180's Esc (forced here): Fission
   180 makes it from the points itself, ends joined to the corners, the tool stays on, one
   Ctrl+Z takes it back.
H  Esc while a spline is drawn: it is cancelled and none of its points stay.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import sketch_input as si

V = App.Vector
TL, TR, BR = V(0, 10, 0), V(60, 10, 0), V(60, -20, 0)
OVER = [V(8, 22, 0), V(20, 30, 0), V(36, 28, 0), V(50, 20, 0)]
s = {}


def check_button():
    from fission180 import sketch_check

    for button in h.gl_widget().findChildren(QtWidgets.QAbstractButton, sketch_check.NAME):
        if button.isVisible():
            return button
    return None


def splines():
    return [i for i, g in enumerate(s["sk"].Geometry) if g.TypeId == "Part::GeomBSplineCurve"]


def loose():
    """Construction points / circles that belong to no spline (FreeCAD's internal alignment)."""
    sk = s["sk"]
    aligned = {c.First for c in sk.Constraints if c.Type == "InternalAlignment"}
    return [
        (i, g.TypeId)
        for i, g in enumerate(sk.Geometry)
        if g.TypeId in ("Part::GeomPoint", "Part::GeomCircle") and sk.getConstruction(i) and i not in aligned
    ]


def real_click(widget, pos=None):
    """The pointer goes to the widget and clicks it (as a hand: the 3D view sees it leave)."""
    pos = widget.rect().center() if pos is None else pos
    h.pointer_to(widget, pos)
    QtTest.QTest.mouseClick(widget, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, pos)
    QtWidgets.QApplication.processEvents()


def big_button(label):
    name = "Fission180Big_" + label.replace(" ", "_")
    for button in h.ribbon_buttons():
        if button.objectName() == name:
            return button
    return None


def click_big(label):
    button = big_button(label)
    if h.check("the big %s button is there" % label, button is not None):
        real_click(button)


def ends_on_corners(index):
    g = s["sk"].Geometry[index]
    a, b = g.StartPoint, g.EndPoint
    return (si.vnear(a, TL, 1e-6) and si.vnear(b, TR, 1e-6)) or (si.vnear(a, TR, 1e-6) and si.vnear(b, TL, 1e-6)), (a, b)


def top_pieces():
    """Lines lying on the rectangle's top (y = 10, between the corners)."""
    out = []
    for i, g in enumerate(s["sk"].Geometry):
        if g.TypeId != "Part::GeomLineSegment" or s["sk"].getConstruction(i):
            continue
        a, b = g.StartPoint, g.EndPoint
        if abs(a.y - 10) < 1e-6 and abs(b.y - 10) < 1e-6:
            out.append((i, round(a.x, 4), round(b.x, 4)))
    return out


# -- a design with the rectangle ---------------------------------------------------------
def design_steps(tag):
    def new_design():
        Gui.activateWorkbench("Fission180Workbench")
        App.newDocument("Luca" + tag)
        h.fit()
        Gui.getMainWindow().activateWindow()

    def create_sketch():
        click_big("Create Sketch")

    def pick_xy():
        pl.click_square("XY_Plane")

    def opened():
        s["sk"] = h.in_sketch()
        h.check("%s: sketch open on XY" % tag, s["sk"] is not None)
        h.fit(iso=False)

    def rect():
        click_big("2-Point Rectangle")

    def r1():
        si.click(TL)

    def r2():
        si.click(BR)

    def r_esc():
        si.key(QtCore.Qt.Key_Escape)

    def r_made():
        h.check("%s: the rectangle (4 lines)" % tag, len(si.lines(s["sk"])) == 4, len(si.lines(s["sk"])))

    steps = [new_design, create_sketch, pick_xy, opened, rect, r1, r2, r_esc, r_made]
    for step in steps:
        step.__name__ = "%s_%s" % (tag.lower(), step.__name__)
    return steps


def spline_steps(tag, start, finish, wiggle=False):
    """start: "big" (the big Spline button: Fit Point Spline) or "menu-control";
    finish: "check" (the floating check) or "finish" (Finish Sketch in the ribbon)."""

    def begin():
        s["before"] = len(splines())
        s["geo_before"] = len(s["sk"].Geometry)
        if start == "big":
            click_big("Fit Point Spline")  # the big Spline button (its first entry)
        else:
            si.menu_item("CREATE", "Control Point Spline")

    def clicks():
        si.click(TL)
        for p in OVER:
            si.click(p)
        if wiggle:  # on the way to a button and back
            button = big_button("Fit Point Spline")
            if button is not None:
                h.pointer_to(button, button.rect().center())
            QtWidgets.QApplication.processEvents()
        si.click(TR)

    def done():
        h.settle("the last point")
        h.shot("%s-before-finish" % tag)
        if finish == "check":
            h.wait_for(lambda: check_button() is not None, "the green check beside the last point")
            real_click(check_button())
        else:
            click_big("Finish Sketch")

    def made():
        h.settle("the spline")
        h.shot("%s-after-finish" % tag)
        if finish == "finish":
            sk = App.ActiveDocument.getObject(s["sk"].Name)
            s["sk"] = sk
        now = splines()
        h.check("%s: the spline is made" % tag, len(now) == s["before"] + 1, [g.TypeId for g in s["sk"].Geometry])
        h.check("%s: no loose points or circles left" % tag, not loose(), loose())
        if len(now) > s["before"]:
            ok, ends = ends_on_corners(now[-1])
            h.check("%s: its ends are on the rectangle's top corners" % tag, ok, ends)

    def stop():
        if h.in_sketch() is not None and si.drawing():
            si.key(QtCore.Qt.Key_Escape)

    steps = [begin, clicks, done, made, stop]
    for step in steps:
        step.__name__ = "%s_%s" % (tag.lower(), step.__name__)
    return steps


# -- C: Trim the top line --------------------------------------------------------------
def c_trim():
    s["top_before"] = top_pieces()
    h.check("C: the top line is one line before the trim", len(s["top_before"]) == 1, s["top_before"])
    h.press("t")


def c_click():
    si.click(V(30, 10, 0))


# The rectangle's top crosses the circles round the spline's end control points at their 0
# degree point: FreeCAD 1.1.4 then makes a malformed constraint in its trim and says so
# (core patch #7 fixes it in the Fission 180 program; on the official FreeCAD the Python
# repair, sketch_fix, puts it right after the trim: checked in c_trimmed).
if App.ConfigGet("Application") != "Fission 180":
    c_click.notes_ok = ("malformed",)


def c_trimmed():
    h.settle("the trim")
    h.shot("C-after-trim")
    left = top_pieces()
    h.check("C: the whole top line went, nothing left at the corners", left == [], left)
    sk = s["sk"]
    h.check("C: no malformed constraint is left", not list(sk.MalformedConstraints), list(sk.MalformedConstraints))
    h.check("C: the sketch solves", sk.solve() == 0, sk.solve())
    h.check("C: the splines are still there", len(splines()) == 2, len(splines()))
    si.key(QtCore.Qt.Key_Escape)


def finish_sketch():
    click_big("Finish Sketch")


# -- F: Line on, then a spline from the command search ------------------------------------
def f_line():
    h.press("l")


def f_l1():
    si.click(V(-30, -10, 0))


def f_l2():
    si.click(V(-10, -10, 0))  # the chain goes on from here (no Esc)


def f_search():
    s["before"] = len(splines())
    h.press("s")


def f_type():
    from fission180 import search_ui

    def dialog():
        for w in QtWidgets.QApplication.topLevelWidgets():
            if isinstance(w, search_ui.CommandSearchDialog) and w.isVisible():
                return w
        return None

    h.wait_for(lambda: dialog() is not None, "the command search")
    box = dialog()
    QtTest.QTest.keyClicks(box._edit, "Control Point Spline")
    QtWidgets.QApplication.processEvents()
    h.wait_for(lambda: box._list.count() > 0, "a search result")
    item = box._list.currentItem() or box._list.item(0)
    print("[Fission 180] F: search shows %r first (%s)" % (item.text(), item.data(QtCore.Qt.UserRole)), flush=True)
    h.check("F: the search finds Control Point Spline", "Control Point Spline" in item.text(), item.text())
    QtTest.QTest.keyClick(box._edit, QtCore.Qt.Key_Return)
    QtWidgets.QApplication.processEvents()


def f_clicks():
    h.settle("the spline tool")
    from fission180 import recent

    print("[Fission 180] F: running tool after the search: %s" % recent.running_tool(), flush=True)
    h.shot("F-after-search")
    si.click(TL)
    for p in OVER:
        si.click(p)
    si.click(TR)


def f_check_at_spline():
    h.wait_for(lambda: check_button() is not None, "the green check")
    from fission180 import sketch_check

    end = h.screen_point(s["sk"].getGlobalPlacement().multVec(TR))
    centre = check_button().geometry().center()
    dx, dy = centre.x() - end.x(), centre.y() - end.y()
    h.check("F: the check is beside the spline's last point, not the old line's end",
            0 <= dx <= 45 and 0 <= dy <= 45, (dx, dy))
    real_click(check_button())


def f_made():
    h.settle("the spline")
    h.check("F: the spline is made", len(splines()) == s["before"] + 1, [g.TypeId for g in s["sk"].Geometry])
    h.check("F: no loose points or circles left", not loose(), loose())
    si.key(QtCore.Qt.Key_Escape)


# -- F2: FreeCAD's spline tool started with no record of it (its own toolbar, a macro) ---
def f2_line():
    h.press("l")


def f2_l1():
    si.click(V(-30, -15, 0))


def f2_l2():
    si.click(V(-10, -15, 0))  # the chain goes on from here (no Esc)


def f2_start():
    s["before"] = len(splines())
    Gui.runCommand("Sketcher_CreateBSpline")  # nothing of Fission 180 records it


def f2_clicks():
    h.settle("the spline tool")
    si.click(TL)
    for p in OVER:
        si.click(p)
    si.click(TR)


def f2_check():
    h.wait_for(lambda: check_button() is not None, "the green check")
    end = h.screen_point(s["sk"].getGlobalPlacement().multVec(TR))
    centre = check_button().geometry().center()
    dx, dy = centre.x() - end.x(), centre.y() - end.y()
    h.check("F2: the check is beside the spline's last point (FreeCAD's spline panel told it)",
            0 <= dx <= 45 and 0 <= dy <= 45, (dx, dy))
    real_click(check_button())


def f2_made():
    h.settle("the spline")
    h.check("F2: the spline is made", len(splines()) == s["before"] + 1, [g.TypeId for g in s["sk"].Geometry])
    h.check("F2: no loose points or circles left", not loose(), loose())
    si.key(QtCore.Qt.Key_Escape)


# -- G: FreeCAD does not make it: Fission 180 does --------------------------------------
def g_begin():
    s["before"] = len(splines())
    s["geo_before"] = len(s["sk"].Geometry)
    click_big("Fit Point Spline")


def g_clicks():
    si.click(TL)
    for p in OVER[:2]:
        si.click(p)
    si.click(TR)


def g_forced():
    from fission180 import sketch_mode

    real = sketch_mode.QtGui.QKeyEvent

    def not_escape(kind, key, modifiers):  # Fission 180's Esc reaches FreeCAD as Shift
        return real(kind, QtCore.Qt.Key_Shift if key == QtCore.Qt.Key_Escape else key, modifiers)

    sketch_mode.QtGui.QKeyEvent = not_escape
    try:
        h.wait_for(lambda: check_button() is not None, "the green check")
        real_click(check_button())
        h.settle("the spline")
    finally:
        sketch_mode.QtGui.QKeyEvent = real


def g_made():
    now = splines()
    h.check("G: Fission 180 made the spline", len(now) == s["before"] + 1, [g.TypeId for g in s["sk"].Geometry])
    h.check("G: no loose points or circles left", not loose(), loose())
    if len(now) > s["before"]:
        ok, ends = ends_on_corners(now[-1])
        h.check("G: its ends are on the corners", ok, ends)
        h.check("G: the sketch solves", s["sk"].solve() == 0)
    h.check("G: the spline tool stays on", si.drawing())
    si.key(QtCore.Qt.Key_Escape)


def g_undo():
    h.press("z", QtCore.Qt.ControlModifier)


def g_undone():
    h.settle("the undo")
    h.check("G: one Ctrl+Z takes it back", len(s["sk"].Geometry) == s["geo_before"],
            (len(s["sk"].Geometry), s["geo_before"]))
    h.press("y", QtCore.Qt.ControlModifier)


# -- H: Esc cancels, no points stay --------------------------------------------------
def h_begin():
    s["geo_before"] = len(s["sk"].Geometry)
    s["before"] = len(splines())
    click_big("Fit Point Spline")


def h_clicks():
    si.click(V(-40, 20, 0))
    si.click(V(-30, 35, 0))
    si.click(V(-15, 25, 0))


def h_esc():
    si.key(QtCore.Qt.Key_Escape)


def h_none_left():
    h.settle("Esc")
    h.check("H: Esc made no spline", len(splines()) == s["before"])
    h.check("H: none of its points stay", not loose() and len(s["sk"].Geometry) == s["geo_before"],
            (loose(), len(s["sk"].Geometry), s["geo_before"]))


def end():
    h.expect_no_errors("Luca's spline and trim steps")


STEPS = (
    design_steps("A")
    + spline_steps("A", "big", "check")
    + spline_steps("B", "menu-control", "check")
    + [c_trim, c_click, c_trimmed, finish_sketch]
    + design_steps("D")
    + spline_steps("D", "big", "finish")
    + design_steps("E")
    + spline_steps("E", "big", "check", wiggle=True)
    + [f_line, f_l1, f_l2, f_search, f_type, f_clicks, f_check_at_spline, f_made]
    + [f2_line, f2_l1, f2_l2, f2_start, f2_clicks, f2_check, f2_made]
    + [g_begin, g_clicks, g_forced, g_made, g_undo, g_undone]
    + [h_begin, h_clicks, h_esc, h_none_left]
    + [finish_sketch, end]
)

h.run("sketch_spline_luca", si.watched(STEPS), paced_by="state")
