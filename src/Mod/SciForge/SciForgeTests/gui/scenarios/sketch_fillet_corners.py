# SPDX-License-Identifier: LGPL-2.1-or-later
"""Sketch Fillet: several corners at once, and a corner shows when the pointer is on it
(Luca, 2026-11-02: "sketching a fillet does not let me select multiple edges. also, corners
dont give any physical feedback to tell the user that the corner is being hovered over.
there should be a snap point and the corner should be highlighted").

A 40 x 30 rectangle with its corners at (0, 0), (40, 0), (40, 30), (0, 30).

A  MODIFY > Fillet, the pointer on the corner (40, 0): both of its sides light up, the arc
   it would get shows, and the snap dot sits on the corner. Off the corners, on a side:
   only that side lights up, no dot.
B  A click on the corner (0, 0), then on (40, 0) and (40, 30): three corners picked; with
   several corners the pointer no longer sizes them (it travels from corner to corner):
   the radius holds at a guess (a fifth of the shortest side: 6); type 5, Enter: three arcs of radius 5,
   one Radius dimension 5 and the other two Equal to the first; the sketch solves. Ctrl+Z
   takes all three back in one step; Ctrl+Y brings them again.
C  The Radius dimension set to 3: all three arcs follow (they stay equal).
D  A second rectangle 40 x 30 at x = 60: its corners (60, 0) and (100, 0) share the
   bottom side; type 25, Enter: held at 19.8 (each fillet alone could be 30; together they
   leave a piece of the 40 mm side), and the pointer says so.
"""

import FreeCAD as App

from SciForgeTests.gui import harness as h
from SciForgeTests.gui import sketch_input as si
from SciForgeTests.gui import sketch_tools_steps as st

V = App.Vector
s = st.s


def rectangle(x0, y0, w, hh):
    import Part
    import Sketcher

    sk = st.sketch()
    p = [V(x0, y0, 0), V(x0 + w, y0, 0), V(x0 + w, y0 + hh, 0), V(x0, y0 + hh, 0)]
    geos = [sk.addGeometry(Part.LineSegment(p[i], p[(i + 1) % 4])) for i in range(4)]
    for i in range(4):
        sk.addConstraint(Sketcher.Constraint("Coincident", geos[i], 2, geos[(i + 1) % 4], 1))
    sk.addConstraint(Sketcher.Constraint("Horizontal", geos[0]))
    sk.addConstraint(Sketcher.Constraint("Horizontal", geos[2]))
    sk.addConstraint(Sketcher.Constraint("Vertical", geos[1]))
    sk.addConstraint(Sketcher.Constraint("Vertical", geos[3]))
    sk.addConstraint(Sketcher.Constraint("DistanceX", geos[0], 1, geos[0], 2, w))
    sk.addConstraint(Sketcher.Constraint("DistanceY", geos[1], 1, geos[1], 2, hh))
    sk.addConstraint(Sketcher.Constraint("DistanceX", -1, 1, geos[0], 1, x0))
    sk.addConstraint(Sketcher.Constraint("DistanceY", -1, 1, geos[0], 1, y0))
    return geos


def shapes():
    s["r1"] = rectangle(0.0, 0.0, 40.0, 30.0)
    s["r2"] = rectangle(60.0, 0.0, 40.0, 30.0)
    App.ActiveDocument.recompute()
    st.sketch().solve()
    h.fit(iso=False)


def arcs():
    sk = st.sketch()
    return [(i, g) for i, g in enumerate(sk.Geometry) if g.TypeId == "Part::GeomArcOfCircle"]


def tool_dot():
    t = st.tool()
    dot = t.preview.drawn().get("dot") if t is not None else []
    return dot[0] if dot else None


def hint():
    t = st.tool()
    try:
        return t.hint.text() if t is not None and t.hint is not None else ""
    except Exception:
        return ""


# == A ==================================================================================
def a_fillet():
    si.menu_item("MODIFY", "Fillet")


def a_hover():
    h.check("A SciForge's Fillet runs", st.tool_title() == "Fillet", st.tool_title())
    st.hover(V(40.3, 0.4, 0))


def a_hover_check():
    drawn = st.preview()
    picked = drawn.get("picked", [])
    h.check("A both sides of the corner light up", len(picked) == 2, len(picked))
    curves = drawn.get("curves", [])
    h.check("A the arc it would get shows", len(curves) == 1 and len(curves[0]) > 2, curves)
    dot = tool_dot()
    h.check(
        "A the dot on the corner",
        dot is not None and abs(dot[0] - 40) < 1e-6 and abs(dot[1]) < 1e-6,
        dot,
    )
    h.shot("A-corner-hover")
    st.hover(V(20, 0.3, 0))


def a_side_check():
    drawn = st.preview()
    h.check("A on a side: only that side lights up", len(drawn.get("picked", [])) == 1, drawn)
    h.check("A ...no arc", not drawn.get("curves"), drawn.get("curves"))
    h.check("A ...no dot", tool_dot() is None, tool_dot())


# == B ==================================================================================
def b_first():
    s["n"] = len(st.sketch().Geometry)
    st.click(V(0, 0, 0), towards=V(-1.0, -0.6, 0))


def b_second():
    t = st.tool()
    h.check("B the first corner picked: the radius step", t is not None and t.step == 2)
    st.click(V(40, 0, 0), towards=V(1.0, -0.6, 0))


def b_third():
    t = st.tool()
    h.check(
        "B the second corner is added", t is not None and len(t._pairs()) == 2, t and t._pairs()
    )
    st.click(V(40, 30, 0), towards=V(1.0, 0.6, 0))


def b_away():
    t = st.tool()
    h.check("B three corners picked", t is not None and len(t._pairs()) == 3, t and t._pairs())
    h.check("B still the radius step", t is not None and t.step == 2)
    st.hover(V(20, 15, 0))  # into the middle: the pointer no longer sizes them


def b_type():
    f = st.field("radius")
    shown = f.value if f is not None else None
    h.check(
        "B with several corners the radius holds (a fifth of 30: 6)", st.near(shown, 6.0), shown
    )
    h.shot("B-three-corners")
    st.keys("5\n")


def b_check():
    found = arcs()
    h.check("B three arcs", len(found) == 3, found)
    h.check(
        "B all of radius 5",
        all(st.near(g.Radius, 5.0) for _i, g in found),
        [g.Radius for _i, g in found],
    )
    sk = st.sketch()
    radius = [c for c in sk.Constraints if c.Type == "Radius"]
    equal = [c for c in sk.Constraints if c.Type == "Equal"]
    h.check(
        "B one Radius dimension of 5", len(radius) == 1 and st.near(radius[0].Value, 5.0), radius
    )
    h.check("B the other two Equal to it", len(equal) == 2, equal)
    st.sketch_ok("B")
    s["dim"] = [i for i, c in enumerate(sk.Constraints) if c.Type == "Radius"]
    st.esc()
    st.undo()


def b_undone():
    h.check("B Ctrl+Z takes the three back in one step", len(arcs()) == 0, arcs())
    st.redo()


def b_redone():
    h.check("B Ctrl+Y brings them again", len(arcs()) == 3, arcs())


# == C ==================================================================================
def c_change():
    sk = st.sketch()
    index = [i for i, c in enumerate(sk.Constraints) if c.Type == "Radius"][0]
    App.ActiveDocument.openTransaction("radius 3")
    sk.setDatum(index, App.Units.Quantity("3 mm"))
    App.ActiveDocument.commitTransaction()
    App.ActiveDocument.recompute()


def c_check():
    found = arcs()
    h.check(
        "C all three follow the dimension (3)",
        len(found) == 3 and all(st.near(g.Radius, 3.0) for _i, g in found),
        [g.Radius for _i, g in found],
    )
    st.sketch_ok("C")


# == D ==================================================================================
def d_fillet():
    si.menu_item("MODIFY", "Fillet")


def d_first():
    s["before"] = len(arcs())
    st.click(V(60, 0, 0), towards=V(-1.0, -0.6, 0))


def d_second():
    st.click(V(100, 0, 0), towards=V(1.0, -0.6, 0))


def d_type():
    t = st.tool()
    h.check("D two corners sharing the bottom side", t is not None and len(t._pairs()) == 2)
    st.keys("25\n")


def d_check():
    new = arcs()[s["before"] :]
    h.check("D two arcs", len(new) == 2, new)
    h.check(
        "D held at 19.8 (they leave a piece of the 40 mm side)",
        len(new) == 2 and all(st.near(g.Radius, 19.8, 1e-4) for _i, g in new),
        [g.Radius for _i, g in new],
    )
    h.check("D ...and the pointer says so", "limited to 19.8" in hint(), hint())
    st.sketch_ok("D")
    st.esc()


h.run(
    "sketch_fillet_corners",
    st.start_steps("FilletCorners")
    + [
        shapes,
        a_fillet,
        a_hover,
        a_hover_check,
        a_side_check,
        b_first,
        b_second,
        b_third,
        b_away,
        b_type,
        b_check,
        b_undone,
        b_redone,
        c_change,
        c_check,
        d_fillet,
        d_first,
        d_second,
        d_type,
        d_check,
    ],
    paced_by="state",
)
