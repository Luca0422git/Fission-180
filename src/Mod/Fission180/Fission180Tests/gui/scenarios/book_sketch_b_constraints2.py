# SPDX-License-Identifier: LGPL-2.1-or-later
"""Wave 7, the book parity report: Tangent, Symmetry, Parallel, Perpendicular and Equal, both
ways (tool first; picks first), with refusals that say why, and never a FreeCAD message box.

Report items (docs/fission180/dev/research/book-parity-report.txt):
- Carabiner 1149-1153, Drone 1548-1550, Pizza Cutter 2056-2060: Tangent on an arc and a line
  that share an end popped FreeCAD's modal "Sketcher Constraint Substitution" box (it also
  took the keyboard away from the next value boxes).
- Play Brick 1241-1243: Tangent between a text frame line and a circle added nothing.
- Football 2431-2432: Tangent between two spline ends added nothing, no message.
- Drone 1474-1482: Symmetry the book's way (left line, right line, centre line) did nothing:
  only FreeCAD's two points + line worked.
"""

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import book_sketch_b_steps as b
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_tools_steps as st

V = App.Vector
s = st.s
SUBSTITUTION = "User parameter:BaseApp/Preferences/Mod/Sketcher/General"


def spline(poles):
    import Part

    curve = Part.BSplineCurve()
    curve.buildFromPoles([V(x, y, 0) for x, y in poles], False, 3)
    return b.add(curve)


def reference():
    import math

    import Part

    from fission180 import text

    sk = b.sk()
    # an arc and a line that share an end (a Coincident), not tangent yet
    s["aa"] = b.add(
        Part.ArcOfCircle(Part.Circle(V(34, -9, 0), V(0, 0, 1), 12.0), math.radians(250), 0.4)
    )
    start = sk.Geometry[s["aa"]].StartPoint
    s["al"] = b.add(Part.LineSegment(V(8, -22, 0), start))
    b.con("Coincident", s["al"], 2, s["aa"], 1)
    # a second pair, for FreeCAD's own command
    s["ab"] = b.add(
        Part.ArcOfCircle(Part.Circle(V(74, -9, 0), V(0, 0, 1), 12.0), math.radians(250), 0.4)
    )
    start = sk.Geometry[s["ab"]].StartPoint
    s["bl"] = b.add(Part.LineSegment(V(50, -24, 0), start))
    b.con("Coincident", s["bl"], 2, s["ab"], 1)
    # a line and a circle apart
    s["tl"] = b.add(Part.LineSegment(V(-90, 48, 0), V(-60, 50, 0)))
    s["tc"] = b.add(Part.Circle(V(-75, 34, 0), V(0, 0, 1), 6))
    # two splines that share an end
    s["s1"] = spline([(-40, 40), (-35, 55), (-30, 55), (-25, 48)])
    s["s2"] = spline([(-25, 48), (-22, 40), (-18, 40), (-15, 50)])
    b.con("Coincident", s["s1"], 2, s["s2"], 1)
    # a text frame (four construction lines held as a rectangle) and a fixed circle
    ids = text.add_frame(sk, (5, 30), 0.0, 20.0, 8.0)  # [bottom, right, top, left]
    by_id = {sk.getGeometryId(i): i for i in range(len(sk.Geometry))}
    s["frame"] = [by_id[i] for i in ids]
    s["fc"] = b.add(Part.Circle(V(15, 52, 0), V(0, 0, 1), 6))
    b.con("Block", s["fc"])
    # Symmetry: two lines and a construction line between them
    s["sa"] = b.add(Part.LineSegment(V(-80, -60, 0), V(-78, -40, 0)))
    s["sb"] = b.add(Part.LineSegment(V(-50, -60, 0), V(-55, -42, 0)))
    s["sc"] = b.add(Part.LineSegment(V(-65, -70, 0), V(-65, -30, 0)), True)
    # ...two circles and a construction line
    s["q1"] = b.add(Part.Circle(V(-25, -58, 0), V(0, 0, 1), 3))
    s["q2"] = b.add(Part.Circle(V(-3, -52, 0), V(0, 0, 1), 5))
    s["qm"] = b.add(Part.LineSegment(V(-13, -70, 0), V(-13, -38, 0)), True)
    # Parallel / Perpendicular / Equal
    s["p1"] = b.add(Part.LineSegment(V(48, 44, 0), V(78, 49, 0)))
    s["p2"] = b.add(Part.LineSegment(V(48, 36, 0), V(80, 34, 0)))
    s["p3"] = b.add(Part.LineSegment(V(50, 26, 0), V(76, 20, 0)))
    s["hh"] = b.add(Part.LineSegment(V(-90, 5, 0), V(-70, 5, 0)))
    s["vv"] = b.add(Part.LineSegment(V(-60, -5, 0), V(-60, 15, 0)))
    b.con("Horizontal", s["hh"])
    b.con("Vertical", s["vv"])
    s["e1"] = b.add(Part.LineSegment(V(20, -45, 0), V(38, -42, 0)))
    s["e2"] = b.add(Part.LineSegment(V(22, -55, 0), V(48, -57, 0)))
    s["k1"] = b.add(Part.Circle(V(62, -48, 0), V(0, 0, 1), 4))
    s["k2"] = b.add(Part.Circle(V(80, -52, 0), V(0, 0, 1), 7))
    App.ActiveDocument.recompute()
    b.clean("the reference sketch")
    b.watch_modals()


def unit(v):
    return v * (1.0 / v.Length)


# == Tangent ===============================================================================
def tan_open():
    b.menu("Tangent")


def tan_arc_line():
    h.check("Tangent runs", st.tool_title() == "Tangent", st.tool_title())
    s["undo"] = len(b.undo_names())
    b.click(b.mid(b.geo("aa")))
    b.click(b.mid(b.geo("al")))


def tan_arc_line_check():
    arc, line = b.geo("aa"), b.geo("al")
    radius = unit(arc.StartPoint - arc.Center)
    along = unit(line.EndPoint - line.StartPoint)
    h.check(
        "report Carabiner: an arc and a line that share an end become tangent there",
        abs(radius.dot(along)) < 1e-6,
        radius.dot(along),
    )
    h.check("...still joined", st.vnear(arc.StartPoint, line.EndPoint, 1e-6))
    h.check(
        "...FreeCAD's end-to-end tangency in place of the join (one constraint, no Coincident)",
        any(
            c[0] == "Tangent" and {c[1], c[3]} == {s["aa"], s["al"]} and c[2] and c[4]
            for c in b.cons()
        )
        and not any(c[0] == "Coincident" and {c[1], c[3]} == {s["aa"], s["al"]} for c in b.cons()),
        [c for c in b.cons() if s["aa"] in (c[1], c[3])],
    )
    h.check("...one undo step", len(b.undo_names()) == s["undo"] + 1, b.undo_names()[:3])
    b.no_modal("Tangent on joined curves (FreeCAD's Constraint Substitution box)")
    b.clean("tangent arc + line")
    b.click(V(-75, 49, 0))  # the line...
    b.click(V(-75, 28, 0))  # ...and the circle below it


def tan_line_circle_check():
    line, circle = b.geo("tl"), b.geo("tc")
    off = b.off_line(line, circle.Center)
    h.check(
        "a line and a circle apart: the line touches the circle",
        abs(off - circle.Radius) < 1e-6,
        off,
    )
    b.forget_said()
    b.mark()
    b.click(b.mid(b.geo("p1")))
    b.click(b.mid(b.geo("p2")))


def tan_two_lines_check():
    h.check("two lines: nothing added", not b.new_cons(), b.new_cons())
    h.check("...and it says to use Collinear", "Collinear" in b.said(), b.said())
    st.esc()
    # the text frame's top line and the fixed circle above it
    b.menu("Tangent")


def tan_frame():
    top = b.sk().Geometry[s["frame"][2]]
    b.click(b.mid(top))
    b.click(V(15, 46, 0))  # the circle's lowest point


def tan_frame_check():
    top = b.sk().Geometry[s["frame"][2]]
    circle = b.geo("fc")
    off = b.off_line(top, circle.Center)
    h.check(
        "report Play Brick: a text frame line and a circle become tangent",
        abs(off - circle.Radius) < 1e-6,
        off,
    )
    right = b.sk().Geometry[s["frame"][1]]
    h.check(
        "...the frame is still a rectangle",
        abs(unit(top.EndPoint - top.StartPoint).dot(unit(right.EndPoint - right.StartPoint)))
        < 1e-6,
    )
    b.clean("tangent text frame")
    st.esc()
    b.select(b.geo("s1").EndPoint)  # the corner the two splines share


def tan_splines_run():
    h.check("the splines' shared end selected", len(b.selected()) == 1, b.selected())
    s["undo"] = len(b.undo_names())
    b.menu("Tangent")


def tan_splines_check():
    s1, s2 = b.geo("s1"), b.geo("s2")
    t1 = s1.tangent(s1.LastParameter)[0]
    t2 = s2.tangent(s2.FirstParameter)[0]
    h.check(
        "report Football: Tangent on the end two splines share: smooth there",
        abs(b.cross(unit(t1), unit(t2))) < 1e-6,
        (t1, t2),
    )
    h.check("...still joined", st.vnear(s1.EndPoint, s2.StartPoint, 1e-6))
    h.check(
        "...one undo step, tool done", len(b.undo_names()) == s["undo"] + 1 and st.tool() is None
    )
    b.clean("tangent splines")
    b.no_modal("Tangent on splines")
    st.undo()


def tan_splines_undo_check():
    s1, s2 = b.geo("s1"), b.geo("s2")
    t1 = s1.tangent(s1.LastParameter)[0]
    t2 = s2.tangent(s2.FirstParameter)[0]
    h.check("Undo: the corner is back", abs(b.cross(unit(t1), unit(t2))) > 1e-3, (t1, t2))
    h.check(
        "...with its Coincident (nothing lost)",
        any(c[0] == "Coincident" and {c[1], c[3]} == {s["s1"], s["s2"]} for c in b.cons()),
    )
    st.redo()


def freecad_own_tangent():
    """FreeCAD's own Tangent command (a script, another workbench's toolbar, a macro) on
    joined curves: its "Sketcher Constraint Substitution" box is switched off for good."""
    group = App.ParamGet(SUBSTITUTION)
    h.check(
        "FreeCAD's substitution notice is off while Fission 180 is on",
        group.GetBool("NotifyConstraintSubstitutions", True) is False,
    )
    sk = b.sk()
    Gui.Selection.clearSelection()
    for name in ("ab", "bl"):
        Gui.Selection.addSelection(sk.Document.Name, sk.Name, "Edge%d" % (s[name] + 1))
    Gui.runCommand("Sketcher_ConstrainTangent")


def freecad_own_tangent_check():
    arc, line = b.geo("ab"), b.geo("bl")
    radius = unit(arc.StartPoint - arc.Center)
    along = unit(line.EndPoint - line.StartPoint)
    h.check("FreeCAD's own Tangent made them tangent", abs(radius.dot(along)) < 1e-6)
    b.no_modal("FreeCAD's own Tangent command")
    Gui.Selection.clearSelection()


# == Symmetry ==============================================================================
def sym_open():
    b.menu("Symmetry")


def sym_lines():
    h.check("Symmetry runs", st.tool_title() == "Symmetry", st.tool_title())
    s["undo"] = len(b.undo_names())
    b.mark()
    b.click(b.mid(b.geo("sa")))
    b.click(b.mid(b.geo("sb")))
    b.click(V(-65, -33, 0))


def mirrored(p, q, line):
    from fission180 import sketch_constrain_core as core

    o = line.StartPoint
    d = line.EndPoint - line.StartPoint
    return core.is_mirror((p.x, p.y), (q.x, q.y), (o.x, o.y), (d.x, d.y), 1e-6)


def sym_lines_check():
    a, c, m = b.geo("sa"), b.geo("sb"), b.geo("sc")
    h.check(
        "report Drone: Symmetry the book's way (left line, right line, centre line)",
        mirrored(a.StartPoint, c.StartPoint, m) and mirrored(a.EndPoint, c.EndPoint, m),
        (a, c, m),
    )
    h.check(
        "...two Symmetric constraints, one undo step",
        [x[0] for x in b.new_cons()] == ["Symmetric"] * 2,
    )
    h.check("...one undo step", len(b.undo_names()) == s["undo"] + 1, b.undo_names()[:3])
    b.clean("symmetry of two lines")
    b.forget_said()
    b.click(b.mid(b.geo("sa")))
    b.click(V(-28, -58, 0))  # a circle after a line


def sym_kind_check():
    h.check(
        "a line, then a circle: refused, the second must be the same kind",
        "same kind" in b.said(),
        b.said(),
    )
    st.esc()
    q1, q2 = b.geo("q1"), b.geo("q2")
    b.select(q1.Center + V(-q1.Radius, 0, 0), q2.Center + V(q2.Radius, 0, 0), V(-13, -68, 0))


def sym_circles_run():
    h.check("two circles and the line selected", len(b.selected()) == 3, b.selected())
    b.menu("Symmetry")


def sym_circles_check():
    q1, q2, m = b.geo("q1"), b.geo("q2"), b.geo("qm")
    h.check(
        "picks first: the circles mirror each other", mirrored(q1.Center, q2.Center, m), (q1, q2)
    )
    h.check("...and are the same size", abs(q1.Radius - q2.Radius) < 1e-6, (q1.Radius, q2.Radius))
    h.check("...the tool is done", st.tool() is None, st.tool_title())
    b.clean("symmetry of two circles")


# == Parallel / Perpendicular / Equal ======================================================
def par_open():
    b.menu("Parallel")


def par_pick():
    b.click(b.mid(b.geo("p1")))
    b.click(b.mid(b.geo("p2")))


def direction(name):
    g = b.geo(name)
    return unit(g.EndPoint - g.StartPoint)


def par_check():
    h.check("Parallel, tool first", abs(b.cross(direction("p1"), direction("p2"))) < 1e-6)
    b.forget_said()
    b.mark()
    b.click(V(-80, 5, 0))  # the Horizontal line
    b.click(V(-60, 5, 0))  # the Vertical line


def par_conflict_check():
    h.check("Parallel between a Horizontal and a Vertical line: nothing added", not b.new_cons())
    h.check(
        "...the refusal names what is in the way",
        "not added" in b.said() and "Horizontal" in b.said() and "Vertical" in b.said(),
        b.said(),
    )
    b.clean("after a refused Parallel")
    st.esc()
    b.menu("Perpendicular")


def perp_pick():
    b.click(b.mid(b.geo("p2")))
    b.click(b.mid(b.geo("p3")))


def perp_check():
    h.check("Perpendicular, tool first", abs(direction("p2").dot(direction("p3"))) < 1e-6)
    b.clean("perpendicular")
    st.esc()
    k1, k2 = b.geo("k1"), b.geo("k2")
    b.select(
        b.mid(b.geo("e1")),
        k1.Center + V(0, k1.Radius, 0),
        b.mid(b.geo("e2")),
        k2.Center + V(0, k2.Radius, 0),
    )


def equal_run():
    h.check("two lines and two circles selected", len(b.selected()) == 4, b.selected())
    s["undo"] = len(b.undo_names())
    b.menu("Equal")


def equal_check():
    e1, e2 = b.geo("e1"), b.geo("e2")
    h.check("picks first: the lines get one length", abs(e1.length() - e2.length()) < 1e-6)
    h.check("...the circles one size", abs(b.geo("k1").Radius - b.geo("k2").Radius) < 1e-6)
    h.check("...in one undo step", len(b.undo_names()) == s["undo"] + 1, b.undo_names()[:3])
    b.clean("equal")
    b.menu("Equal")


def equal_mixed():
    b.forget_said()
    b.click(b.mid(b.geo("p1")))
    k1 = b.geo("k1")
    b.click(k1.Center + V(0, k1.Radius, 0))


def equal_mixed_check():
    h.check(
        "Equal on a line and a circle: refused with why", "no size to share" in b.said(), b.said()
    )
    st.esc()
    b.no_modal("the whole scenario")


def finish():
    h.ribbon("Finish Sketch")


def finished():
    h.check("the sketch closed", h.in_sketch() is None)
    sk = App.ActiveDocument.getObject(s["sk"].Name)
    h.check("the finished sketch is valid", sk.isValid())


h.run(
    "book_sketch_b_constraints2",
    st.start_steps("BookSketchBConstraints2")
    + [
        reference,
        tan_open,
        tan_arc_line,
        tan_arc_line_check,
        tan_line_circle_check,
        tan_two_lines_check,
        tan_frame,
        tan_frame_check,
        tan_splines_run,
        tan_splines_check,
        tan_splines_undo_check,
        freecad_own_tangent,
        freecad_own_tangent_check,
        sym_open,
        sym_lines,
        sym_lines_check,
        sym_kind_check,
        sym_circles_run,
        sym_circles_check,
        par_open,
        par_pick,
        par_check,
        par_conflict_check,
        perp_pick,
        perp_check,
        equal_run,
        equal_check,
        equal_mixed,
        equal_mixed_check,
        finish,
        finished,
    ],
    paced_by="state",
)
