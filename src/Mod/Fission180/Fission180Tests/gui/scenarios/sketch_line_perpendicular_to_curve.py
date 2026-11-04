# SPDX-License-Identifier: LGPL-2.1-or-later
"""A line drawn at 90 degrees from the line it starts on keeps its 90 degrees all the way
onto a curve (Luca, 2026-11-02: "sketching a line from a perpendicular line to a curved
surface does not snap to the 90 degree of the perp line").

The pointer on the curve used to be left to FreeCAD: the line ended wherever the pointer
touched the arc, a degree or two off the right angle, with no Perpendicular. Now the line
ends where its snapped direction meets the curve.

A slanted line A (-20, -12)-(20, 12) and an arc of radius 20 across the perpendicular from
(10, 6) on A, 25 out.

A  Line (L): a click on A at (10, 6), then the pointer onto the arc 2 degrees round from
   where the perpendicular meets it: the right-angle mark shows at the start; a click
   there: the new line is exactly at 90 degrees to A (a Perpendicular constraint), its end
   exactly on the arc (kept on it), its start kept on A; the sketch solves; Ctrl+Z twice
   (the inferred constraints, then the line) takes it away.
B  The same onto a circle, level from the end of a level line: Horizontal, end on the circle.
"""

import math

import FreeCAD as App

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_tools_steps as st

V = App.Vector
s = st.s
START = V(10, 6, 0)
U = V(20, 12, 0).normalize()  # along A
N = V(-U.y, U.x, 0)  # A's normal (towards the arc)
R = 20.0


def rot(v, deg):
    r = math.radians(deg)
    return V(v.x * math.cos(r) - v.y * math.sin(r), v.x * math.sin(r) + v.y * math.cos(r), 0)


def shapes():
    import Part

    sk = st.sketch()
    s["a"] = sk.addGeometry(Part.LineSegment(V(-20, -12, 0), V(20, 12, 0)))
    s["centre"] = START + N * (25 + R)
    mid = math.atan2(-N.y, -N.x)
    circle = Part.Circle(s["centre"], V(0, 0, 1), R)
    # lopsided, so that its middle (a snap point of its own) is far from where the
    # perpendicular meets it
    s["arc"] = sk.addGeometry(
        Part.ArcOfCircle(circle, mid - math.radians(15), mid + math.radians(85))
    )
    # B: a level line ending at (-40, -30) and a circle ahead of it (centre 25 further on,
    # 3 above the level)
    s["level"] = sk.addGeometry(Part.LineSegment(V(-70, -30, 0), V(-40, -30, 0)))
    s["c_centre"] = V(-10, -27, 0)
    s["circle"] = sk.addGeometry(Part.Circle(s["c_centre"], V(0, 0, 1), 8.0))
    # held where they are (a free curve would be dragged a pixel by the new line's joins)
    import Sketcher

    for geo in (s["a"], s["arc"], s["level"], s["circle"]):
        sk.addConstraint(Sketcher.Constraint("Block", geo))
    App.ActiveDocument.recompute()
    s["n"] = len(sk.Geometry)
    h.fit(iso=False)


def new_lines():
    sk = st.sketch()
    return [
        (i, g)
        for i, g in enumerate(sk.Geometry)
        if i >= s["n"] and g.TypeId == "Part::GeomLineSegment"
    ]


def has(kind, first, second=None):
    for c in st.sketch().Constraints:
        if c.Type != kind:
            continue
        if second is None and c.First == first:
            return True
        if {c.First, c.Second} == {first, second}:
            return True
    return False


# == A ==================================================================================
def a_line():
    st.hover(START + V(2, -6, 0))
    h.press("l")


def a_start():
    st.click(START, towards=V(1.0, -0.6, 0))


def a_onto_arc():
    target = START + N * 25
    s["pointer"] = s["centre"] + rot(target - s["centre"], 2.0)
    st.hover(s["pointer"], towards=V(0.4, -1.0, 0))


def a_mark():
    from fission180 import sketch_infer_core as core

    sess = st.session()
    last = sess.infer.last if sess is not None and sess.infer is not None else None
    h.check(
        "A the line snaps at 90 degrees to A on the arc",
        last is not None and last.kind == core.PERPENDICULAR and last.on_curve is not None,
        last,
    )
    drawn = sess.infer.overlay.drawn() if sess is not None else {}
    h.check("A the right-angle mark shows", bool(drawn.get("marks")), drawn)
    h.shot("A-perpendicular-onto-arc")
    st.click(s["pointer"], towards=V(0.0, 0.0, 0))


def a_check():
    st.esc()
    st.esc()
    new = new_lines()
    h.check("A one new line", len(new) == 1, new)
    if len(new) != 1:
        return
    i, g = new[0]
    d = (g.EndPoint - g.StartPoint).normalize()
    h.check("A exactly at 90 degrees to A", abs(d.dot(U)) < 1e-6, d.dot(U))
    h.check("A a Perpendicular constraint to A", has("Perpendicular", i, s["a"]))
    far = max((g.StartPoint, g.EndPoint), key=lambda p: (p - START).Length)
    h.check(
        "A its end exactly on the arc",
        abs((far - s["centre"]).Length - R) < 1e-6,
        (far - s["centre"]).Length,
    )
    h.check("A its end kept on the arc", has("PointOnObject", i, s["arc"]))
    h.check("A its start kept on A", has("PointOnObject", i, s["a"]))
    st.sketch_ok("A")
    st.undo()  # the inferred constraints (their own step, as sketch_infer_undo U2)


def a_undo_line():
    st.undo()  # the line


def a_undone():
    h.check("A Ctrl+Z, Ctrl+Z takes the line away", len(new_lines()) == 0, new_lines())


# == B ==================================================================================
def b_line():
    st.hover(V(-40, -33, 0))
    h.press("l")


def b_start():
    st.click(V(-40, -30, 0), towards=V(-0.6, -1.0, 0))


def b_onto_circle():
    # on the circle, a little above where the level from (-40, -30) meets it
    meet_x = s["c_centre"].x - math.sqrt(8.0**2 - 3.0**2)
    angle = math.atan2(-30 - s["c_centre"].y, meet_x - s["c_centre"].x) + math.radians(6)
    s["pointer"] = s["c_centre"] + V(8 * math.cos(angle), 8 * math.sin(angle), 0)
    s["meet"] = V(meet_x, -30, 0)
    st.hover(s["pointer"], towards=V(-1.0, 0.3, 0))


def b_click():
    st.click(s["pointer"], towards=V(0.0, 0.0, 0))


def b_check():
    st.esc()
    st.esc()
    new = new_lines()
    h.check("B one new line", len(new) == 1, new)
    if len(new) != 1:
        return
    i, g = new[0]
    h.check(
        "B exactly level", abs(g.StartPoint.y - g.EndPoint.y) < 1e-6, (g.StartPoint, g.EndPoint)
    )
    far = max((g.StartPoint, g.EndPoint), key=lambda p: p.x)
    h.check("B its end where the level meets the circle", (far - s["meet"]).Length < 1e-6, far)
    h.check("B its end kept on the circle", has("PointOnObject", i, s["circle"]))
    st.sketch_ok("B")


h.run(
    "sketch_line_perpendicular_to_curve",
    st.start_steps("LinePerpendicularToCurve")
    + [
        shapes,
        a_line,
        a_start,
        a_onto_arc,
        a_mark,
        a_check,
        a_undo_line,
        a_undone,
        b_line,
        b_start,
        b_onto_circle,
        b_click,
        b_check,
    ],
    paced_by="state",
)
