# SPDX-License-Identifier: LGPL-2.1-or-later
"""Clicking another sketch tool replaces the one running, also when the running one is
FreeCAD's (Luca, 2026-11-02: "when sketching, clicking on any of the modify tools when a
create tool is selected, the tool does not change. for example, having rectangle selected
and then clicking on offset does not change out of rectangle").

Fission 180's commands that wait for picks (Offset, Mirror, the patterns, Move/Copy, Scale,
the constraints) ended only Fission 180's own drawing tools; FreeCAD's Rectangle went on
taking every click (two clicks drew a rectangle instead of picking).

Two lines: (-30, -20)-(30, -20) and (30, -20)-(30, 20).

A  2-Point Rectangle, then MODIFY > Offset: a click on the bottom line is Offset's (no
   rectangle is drawn); Esc, Esc.
B  2-Point Rectangle, then CREATE > Mirror: two clicks on the lines draw no rectangle, they
   are Mirror's picks; Esc, Esc.
C  2-Point Rectangle, then CONSTRAINTS > Perpendicular: two clicks on the lines make them
   perpendicular (no rectangle).
D  Line (L), a first click, then MODIFY > Fillet: Fission 180's Fillet runs and the next click
   (the corner) is its; Esc.
"""

import FreeCAD as App
from PySide import QtCore

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st

V = App.Vector
s = st.s
BOTTOM = V(0, -20, 0)
SIDE = V(30, 0, 0)


def lines():
    import Part
    import Sketcher

    sk = st.sketch()
    a = sk.addGeometry(Part.LineSegment(V(-30, -20, 0), V(30, -20, 0)))
    b = sk.addGeometry(Part.LineSegment(V(30, -20, 0), V(30, 20, 0)))
    sk.addConstraint(Sketcher.Constraint("Coincident", a, 2, b, 1))
    App.ActiveDocument.recompute()
    h.fit(iso=False)


def count():
    return len(st.sketch().Geometry)


def freecad_tool():
    """FreeCAD's drawing cursor is on the view (its tool runs)."""
    from fission180 import sketch_cursor

    sess = st.session()
    if sess is None:
        return False
    cursor = sess.gl.cursor()
    # neither the idle arrow nor a Fission 180 tool's own pointer (sketch_cursor.py)
    return cursor.shape() != QtCore.Qt.ArrowCursor and not sketch_cursor.is_own(cursor)


def rectangle():
    st.hover(V(-50, 30, 0))
    h.ribbon("2-Point Rectangle")


def rectangle_runs():
    h.check("the Rectangle runs (FreeCAD's tool)", freecad_tool())
    s["n"] = count()


def stop():
    st.esc()
    st.esc()


# == A ==================================================================================
def a_offset():
    h.ribbon("Offset")


def a_click():
    st.click(BOTTOM + V(-10, 0, 0), towards=V(0.3, -1.0, 0))


def a_check():
    from fission180 import recent

    h.check("A the click drew no rectangle", count() == s["n"], count() - s["n"])
    last = recent.last()
    h.check(
        "A Offset is the command now", last is not None and last[0] == "Fission180_SketchOffset", last
    )
    t = st.tool()
    h.check("A Fission 180's Offset runs", st.tool_title() == "Offset", st.tool_title())
    h.check(
        "A ...and the click picked the bottom line",
        t is not None and 0 in getattr(t, "curves", []),
        t and getattr(t, "curves", None),
    )
    h.shot("A-offset-after-rectangle")
    stop()


# == B ==================================================================================
def b_mirror():
    si.menu_item("CREATE", "Mirror")


def b_first():
    st.click(BOTTOM + V(-10, 0, 0), towards=V(0.3, -1.0, 0))


def b_second():
    st.click(SIDE, towards=V(1.0, 0.3, 0))


def b_check():
    h.check("B two clicks drew no rectangle", count() == s["n"], count() - s["n"])
    # Mirror runs (its MIRROR panel: sketch_mirror_tool) and took the clicks as picks
    h.check("B Mirror is waiting for its picks", st.tool_title() == "Mirror", st.tool_title())
    stop()


# == C ==================================================================================
def c_perpendicular():
    s["constraints"] = len(st.sketch().Constraints)
    h.ribbon("Perpendicular")


def c_first():
    st.click(BOTTOM + V(-10, 0, 0), towards=V(0.3, -1.0, 0))


def c_second():
    st.click(SIDE, towards=V(1.0, 0.3, 0))


def c_check():
    h.check("C two clicks drew no rectangle", count() == s["n"], count() - s["n"])
    added = [c.Type for c in st.sketch().Constraints[s["constraints"] :]]
    h.check("C the two lines were made perpendicular", "Perpendicular" in added, added)
    stop()


# == D ==================================================================================
def d_line():
    st.hover(V(-50, 30, 0))
    h.press("l")


def d_first():
    st.click(V(-50, 30, 0))


def d_fillet():
    s["n"] = count()
    h.ribbon("Fillet")


def d_corner():
    h.check("D Fission 180's Fillet runs", st.tool_title() == "Fillet", st.tool_title())
    st.click(V(30, -20, 0), towards=V(1.0, -0.6, 0))


def d_check():
    t = st.tool()
    h.check(
        "D the corner click was the Fillet's",
        t is not None and len(getattr(t, "corners", [])) == 1,
        t and getattr(t, "corners", None),
    )
    h.check("D no line was drawn", count() == s["n"], count() - s["n"])
    stop()


h.run(
    "sketch_tool_switch",
    st.start_steps("ToolSwitch")
    + [
        lines,
        rectangle,
        rectangle_runs,
        a_offset,
        a_click,
        a_check,
        rectangle,
        rectangle_runs,
        b_mirror,
        b_first,
        b_second,
        b_check,
        rectangle,
        rectangle_runs,
        c_perpendicular,
        c_first,
        c_second,
        c_check,
        d_line,
        d_first,
        d_fillet,
        d_corner,
        d_check,
    ],
    paced_by="state",
)
