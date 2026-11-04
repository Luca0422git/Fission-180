# SPDX-License-Identifier: LGPL-2.1-or-later
"""The 90 degree mark at corners where sketch lines meet at a right angle
(fission180/sketch_right_angles.py; Luca, 2026-11-04: "Sketch lines are still missing 90
degree markings where they connect at 90 degrees", screenshot: a line drawn down at 90
degrees onto the bottom line showed nothing at the corner).

A  L from the origin: a line along the X axis (FreeCAD holds it by its ends on the axis),
   then an upright one from its end (Vertical): one mark at the corner (40, 0), about 10
   pixels a side.
B  A line drawn down at 90 degrees onto the middle of a level line (Luca's screenshot):
   a mark at the foot (60, -20).
C  Zoom out: the mark keeps its size on the screen.
D  Show Constraints off in the SKETCH PALETTE: no marks; on again: back.
E  A 2-point rectangle: its four corners are marked (6 in all).
F  Ctrl+Z takes the rectangle back: its marks go with it (2 left).
G  Finish Sketch: no mark is left in the view.
"""

import math

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import sketch_input as si

V = App.Vector
s = {}


def marks():
    from fission180 import sketch_mode

    session = sketch_mode.current()
    return session.right_angles if session is not None else None


def corners():
    m = marks()
    return [c[0] for c in m.found] if m is not None else []


def has_corner(point, tol=1e-6):
    return any(abs(c[0] - point[0]) <= tol and abs(c[1] - point[1]) <= tol for c in corners())


def side_px(poly):
    """The length of a mark's side in screen pixels."""
    sk = s["sk"]
    place = sk.getGlobalPlacement()
    a = h.screen_point(place.multVec(V(poly[0][0], poly[0][1], 0)))
    b = h.screen_point(place.multVec(V(poly[1][0], poly[1][1], 0)))
    return math.hypot(a.x() - b.x(), a.y() - b.y())


def drawn_ok(count):
    m = marks()
    return m is not None and len(m.drawn) == count and (count == 0 or m.attached)


# -- setup ----------------------------------------------------------------------------------
def new_design():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("RightAngles")
    h.fit()
    Gui.getMainWindow().activateWindow()


def create_sketch():
    h.ribbon("Create Sketch")


def pick_xy():
    pl.click_square("XY_Plane")


def opened():
    s["sk"] = h.in_sketch()
    h.check("sketch open on XY", s["sk"] is not None)
    h.fit(iso=False)
    h.check("no marks in an empty sketch", marks() is not None and not marks().drawn)


# -- A: an L --------------------------------------------------------------------------------
def a_l():
    h.press("l")


def a_p1():
    si.click(V(0, 0, 0))


def a_p2():
    si.click(V(40, 0, 0))


def a_p3():
    si.click(V(40, 30, 0))


def a_esc():
    si.key(QtCore.Qt.Key_Escape)


def a_marked():
    cons = [(c.Type, c.First, int(c.FirstPos), c.Second, int(c.SecondPos)) for c in s["sk"].Constraints]
    print("[Fission 180] A: the L's constraints: %s" % cons, flush=True)
    # (from the origin along the X axis FreeCAD holds the first line by its ends on the
    # axis, not by Horizontal: that counts as level too)
    h.wait_for(lambda: drawn_ok(1), "the L's corner to be marked")
    h.check("A: one mark, at the corner (40, 0)", has_corner((40, 0)), corners())
    h.check("A: one mark drawn", len(marks().drawn) == 1, marks().drawn)
    if marks().drawn:
        px = side_px(marks().drawn[0])
        h.check("A: about 10 pixels a side", 8.0 <= px <= 12.0, px)
        s["side_mm"] = math.dist(marks().drawn[0][0], marks().drawn[0][1])
    h.shot("A-l-corner")


# -- B: a line dropped at 90 degrees onto the middle of another ---------------------------
def b_l():
    h.press("l")


def b_p1():
    si.click(V(0, -20, 0))


def b_p2():
    si.click(V(80, -20, 0))


def b_esc():
    si.key(QtCore.Qt.Key_Escape)


def b_l2():
    h.press("l")


def b_q1():
    si.click(V(60, 10, 0))


def b_q2():
    si.click(V(60, -20, 0))  # onto the bottom line, straight down


def b_esc2():
    si.key(QtCore.Qt.Key_Escape)


def b_marked():
    h.wait_for(lambda: has_corner((60, -20), 1e-4), "the foot of the dropped line to be marked")
    h.check("B: the foot (60, -20) is marked", has_corner((60, -20), 1e-4), corners())
    h.check("B: two marks drawn", len(marks().drawn) == 2, len(marks().drawn))
    h.shot("B-dropped-line")


# -- C: zoom --------------------------------------------------------------------------------
def c_zoom():
    h.view().zoomOut()


def c_same_size():
    h.wait_for(
        lambda: marks().drawn and math.dist(marks().drawn[0][0], marks().drawn[0][1]) > s["side_mm"] * 1.2,
        "the marks to be drawn again for the new zoom",
    )
    px = side_px(marks().drawn[0])
    h.check("C: still about 10 pixels a side after zooming out", 8.0 <= px <= 12.0, px)
    h.fit(iso=False)


# -- D: Show Constraints --------------------------------------------------------------------
def d_off():
    si.palette_click("Fission180Palette_constraints")


def d_hidden():
    h.wait_for(lambda: drawn_ok(0), "the marks to hide with the constraints")
    h.check("D: no marks with Show Constraints off", not marks().drawn and not marks().attached)


def d_on():
    si.palette_click("Fission180Palette_constraints")


def d_back():
    h.wait_for(lambda: drawn_ok(2), "the marks to come back")
    h.check("D: the marks are back", len(marks().drawn) == 2)


# -- E: a rectangle -------------------------------------------------------------------------
def e_rect():
    h.press("r")


def e_c1():
    si.click(V(-60, 10, 0))


def e_c2():
    si.click(V(-20, 40, 0))


def e_esc():
    si.key(QtCore.Qt.Key_Escape)


def e_marked():
    h.wait_for(lambda: drawn_ok(6), "the rectangle's four corners to be marked")
    for corner in ((-60, 10), (-20, 10), (-20, 40), (-60, 40)):
        h.check("E: corner %s marked" % (corner,), has_corner(corner, 1e-4), corners())
    h.shot("E-rectangle")


# -- F: undo ----------------------------------------------------------------------------------
def f_undo():
    for _ in range(4):
        if len(si.lines(s["sk"])) <= 4:
            break
        h.press("z", QtCore.Qt.ControlModifier)
        h.settle("the undo")


def f_marks_follow():
    h.check("F: the rectangle is gone", len(si.lines(s["sk"])) == 4, len(si.lines(s["sk"])))
    h.wait_for(lambda: drawn_ok(2), "the rectangle's marks to go")
    h.check("F: two marks left", len(marks().drawn) == 2, corners())


# -- G: finish ------------------------------------------------------------------------------
def g_finish():
    s["root"] = marks().root
    h.ribbon("Finish Sketch")


def g_none():
    h.check("G: the sketch is closed", h.in_sketch() is None)
    from pivy import coin

    search = coin.SoSearchAction()
    search.setNode(s["root"])
    search.apply(h.view().getSceneGraph())
    h.check("G: no mark left in the view", search.getPath() is None)
    h.expect_no_errors("right-angle marks")


STEPS = [
    new_design, create_sketch, pick_xy, opened,
    a_l, a_p1, a_p2, a_p3, a_esc, a_marked,
    b_l, b_p1, b_p2, b_esc, b_l2, b_q1, b_q2, b_esc2, b_marked,
    c_zoom, c_same_size,
    d_off, d_hidden, d_on, d_back,
    e_rect, e_c1, e_c2, e_esc, e_marked,
    f_undo, f_marks_follow,
    g_finish, g_none,
]

h.run("sketch_right_angle_marks", si.watched(STEPS), paced_by="state")
