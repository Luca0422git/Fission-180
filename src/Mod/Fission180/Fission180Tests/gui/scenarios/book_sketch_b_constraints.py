# SPDX-License-Identifier: LGPL-2.1-or-later
"""Wave 7, the book parity report: the constraint tools work both ways Fusion does (tool first
then clicks; picks first then the tool) and never silently do nothing.

Report items (docs/fission180/dev/research/book-parity-report.txt):
- Donut 810-822: Fix/Unfix, tool first, a click on a spline did nothing; on a selection
  where one circle was fixed already it did nothing.
- Hot End 1768-1773: Collinear on two vertical lines refused as "the Vertical on Line 12
  already makes it so" (they are only parallel); Pizza Cutter 2037-2039: Collinear on lines
  that are each Horizontal added nothing.
- Tensegrity 1100-1106: Horizontal/Vertical between a point and the origin picked the one
  that conflicts and refused silently.
- Tensegrity 1083-1088: Coincident, tool first: a click on a line made the centre the line's
  MIDPOINT (a Symmetric).

Fix/Unfix; Coincident; Collinear; Horizontal/Vertical. (Tangent, Symmetry, Parallel,
Perpendicular and Equal: book_sketch_b_constraints2.)
"""

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import book_sketch_b_steps as b
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_tools_steps as st

V = App.Vector
s = st.s


def reference():
    import Part

    spline = Part.BSplineCurve()
    spline.buildFromPoles([V(-90, 45, 0), V(-80, 60, 0), V(-70, 60, 0), V(-60, 45, 0)], False, 3)
    s["spline"] = b.add(spline)
    s["c1"] = b.add(Part.Circle(V(-80, 20, 0), V(0, 0, 1), 5))
    s["c2"] = b.add(Part.Circle(V(-62, 20, 0), V(0, 0, 1), 5))
    s["c3"] = b.add(Part.Circle(V(-44, 20, 0), V(0, 0, 1), 5))
    b.con("Block", s["c1"])
    s["f"] = b.add(Part.LineSegment(V(-90, -5, 0), V(-70, -2, 0)))
    s["v1"] = b.add(Part.LineSegment(V(20, 20, 0), V(20, 35, 0)))
    s["v2"] = b.add(Part.LineSegment(V(24, 40, 0), V(24, 55, 0)))
    b.con("Vertical", s["v1"])
    b.con("Vertical", s["v2"])
    s["h1"] = b.add(Part.LineSegment(V(40, 30, 0), V(55, 30, 0)))
    s["h2"] = b.add(Part.LineSegment(V(60, 34, 0), V(80, 34, 0)))
    b.con("Horizontal", s["h1"])
    b.con("Horizontal", s["h2"])
    s["hv1"] = b.add(Part.LineSegment(V(40, 5, 0), V(60, 8, 0)))
    s["hv2"] = b.add(Part.LineSegment(V(70, 0, 0), V(72, 18, 0)))
    s["p1"] = b.add(Part.Point(V(-30, -20, 0)))
    s["base"] = b.add(Part.LineSegment(V(-80, -45, 0), V(-30, -45, 0)))
    b.con("Horizontal", s["base"])
    b.con("DistanceY", s["base"], 1, -1, 1, 45.0)
    s["p2"] = b.add(Part.Point(V(-60, -45, 0)))
    b.con("PointOnObject", s["p2"], 1, s["base"])
    s["cc"] = b.add(Part.Circle(V(60, -30, 0), V(0, 0, 1), 4))
    s["cl"] = b.add(Part.LineSegment(V(45, -50, 0), V(85, -50, 0)))
    s["p3"] = b.add(Part.Point(V(10, -30, 0)))
    s["p4"] = b.add(Part.Point(V(16, -36, 0)))
    App.ActiveDocument.recompute()
    b.clean("the reference sketch")
    b.watch_modals()


# == Fix/Unfix =============================================================================
def fix_open():
    b.menu("Fix/Unfix")


def fix_spline():
    h.check("Fix/Unfix runs and waits for clicks", st.tool_title() == "Fix/Unfix", st.tool_title())
    b.mark()
    b.click(b.mid(b.geo("spline")))


def fix_spline_check():
    h.check(
        "report Donut: tool first, a click on a SPLINE fixes it (Block)",
        b.new_cons() == [("Block", s["spline"], 0, -2000, 0, -2000)],
        b.new_cons(),
    )
    h.check("the tool stays on for the next one", st.tool_title() == "Fix/Unfix")
    b.click(b.mid(b.geo("spline")))


def unfix_spline_check():
    h.check("a click on a fixed curve frees it (Unfix)", not b.has("Block", s["spline"]), b.cons())
    h.check("...and says so", "freed" in b.said(), b.said())
    b.mark()
    b.click(V(-70, -2, 0))  # the free line's end point


def fix_point_check():
    kinds = sorted(c[0] for c in b.new_cons())
    h.check(
        "a click on a point fixes the point (two distances from the origin)",
        kinds == ["DistanceX", "DistanceY"],
        b.new_cons(),
    )
    end = b.geo("f").EndPoint
    h.check("the point stayed where it was", st.vnear(end, V(-70, -2, 0), 1e-6), end)
    b.forget_said()
    b.click(V(0, 0, 0))


def fix_origin_check():
    h.check(
        "the origin: refused with the reason (never silence)",
        "always fixed" in b.said(),
        b.said(),
    )
    st.esc()


def fix_select_mixed():
    h.check("Esc ended Fix/Unfix", st.tool() is None, st.tool_title())
    b.select(V(-75, 20, 0), V(-57, 20, 0), V(-39, 20, 0))


def fix_mixed_run():
    h.check("three circles selected by clicks", len(b.selected()) == 3, b.selected())
    s["undo"] = len(b.undo_names())
    b.menu("Fix/Unfix")


def fix_mixed_check():
    blocked = sorted(c[1] for c in b.cons() if c[0] == "Block")
    h.check(
        "report Donut: a selection with one circle fixed already: the other two get fixed",
        blocked == sorted([s["c1"], s["c2"], s["c3"]]),
        blocked,
    )
    h.check("...and it says what it did", "2 fixed (1 was fixed already)" in b.said(), b.said())
    h.check("picks first: the tool is done", st.tool() is None, st.tool_title())
    h.check("...in one undo step", len(b.undo_names()) == s["undo"] + 1, b.undo_names()[:3])
    h.check("the selection is let go", not b.selected(), b.selected())
    b.select(V(-75, 20, 0), V(-57, 20, 0), V(-39, 20, 0))


def unfix_all_run():
    b.menu("Fix/Unfix")


def unfix_all_check():
    h.check("all three fixed and selected: all freed", b.count("Block") == 0, b.cons())
    st.undo()


def unfix_undo_check():
    h.check("Undo: the three are fixed again (one step)", b.count("Block") == 3, b.cons())
    b.clean("fix / unfix")


# == Collinear =============================================================================
def co_open():
    b.menu("Collinear")


def co_verticals():
    s["verticals"] = b.count("Vertical")
    b.mark()
    b.click(V(20, 27, 0))
    b.click(V(24, 47, 0))


def co_verticals_check():
    off = max(b.off_line(b.geo("v1"), p) for p in (b.geo("v2").StartPoint, b.geo("v2").EndPoint))
    h.check(
        "report Hot End: Collinear on two VERTICAL lines puts them on one line", off < 1e-6, off
    )
    h.check("...something was added", len(b.new_cons()) == 1, b.new_cons())
    h.check("...both lines keep their Vertical", b.count("Vertical") == s["verticals"], b.cons())
    b.clean("collinear verticals")
    s["horizontals"] = b.count("Horizontal")
    b.click(V(47, 30, 0))
    b.click(V(70, 34, 0))


def co_horizontals_check():
    dy = abs(b.geo("h1").StartPoint.y - b.geo("h2").StartPoint.y)
    h.check("report Pizza Cutter: Collinear on two HORIZONTAL lines: one line", dy < 1e-6, dy)
    h.check("...both keep their Horizontal", b.count("Horizontal") == s["horizontals"], b.cons())
    b.clean("collinear horizontals")
    b.mark()
    b.forget_said()
    b.click(V(47, b.geo("h1").StartPoint.y, 0))
    b.click(V(70, b.geo("h2").StartPoint.y, 0))


def co_again_check():
    h.check("Collinear again on the same lines adds nothing", not b.new_cons(), b.new_cons())
    h.check(
        "...and says it is so already, naming what makes it so",
        "not added" in b.said() and "already" in b.said(),
        b.said(),
    )
    st.esc()
    st.undo()


def co_undo_check():
    dy = abs(b.geo("h1").StartPoint.y - b.geo("h2").StartPoint.y)
    h.check("Undo takes back the horizontals' Collinear only", abs(dy - 4.0) < 1e-6, dy)
    off = b.off_line(b.geo("v1"), b.geo("v2").StartPoint)
    h.check("...the verticals stay collinear", off < 1e-6, off)
    st.redo()


def co_redo_check():
    dy = abs(b.geo("h1").StartPoint.y - b.geo("h2").StartPoint.y)
    h.check("Redo: collinear again", dy < 1e-6, dy)


# == Horizontal/Vertical ===================================================================
def hv_open():
    b.menu("Horizontal/Vertical")


def hv_line():
    h.check("Horizontal/Vertical runs", st.tool_title() == "Horizontal/Vertical", st.tool_title())
    b.click(V(50, 6.5, 0))  # the nearly level line: one click is enough


def hv_line_check():
    g = b.geo("hv1")
    h.check("a nearly level line becomes Horizontal", abs(g.StartPoint.y - g.EndPoint.y) < 1e-6, g)
    h.check("...by a Horizontal constraint", b.has("Horizontal", s["hv1"]), b.cons())
    b.click(V(-30, -20, 0))  # the point
    b.click(V(0, 0, 0))  # the origin


def hv_points_check():
    p = b.geo("p1")
    h.check(
        "a point and the origin: 30 across, 20 down: level with it (the nearest)",
        abs(p.Y) < 1e-6 and abs(p.X + 30) < 1e-6,
        (p.X, p.Y),
    )
    b.mark()
    b.forget_said()
    b.click(V(-60, -45, 0))  # the point held on the dimensioned line, 60 across, 45 down
    b.click(V(0, 0, 0))


def hv_fallback_check():
    p = b.geo("p2")
    # (60 across and 45 down: nearest to horizontal, which the 45 mm dimension forbids)
    h.check(
        "report Tensegrity: the nearest (horizontal) conflicts: the point goes upright "
        "with the origin instead",
        abs(p.X) < 1e-6 and abs(p.Y + 45) < 1e-6,
        (p.X, p.Y),
    )
    h.check(
        "...by a Vertical between the point and the origin", len(b.new_cons()) == 1, b.new_cons()
    )
    h.check(
        "...and it says why (what horizontal conflicts with)",
        "made vertical instead" in b.said() and "45 mm" in b.said(),
        b.said(),
    )
    b.clean("horizontal/vertical")
    b.forget_said()
    b.click(V(0, 0, 0))
    b.click(V(-30, 0, 0))  # the first point again: level with the origin already


def hv_same_check():
    h.check(
        "two points that are level already: refused, saying it is so already",
        "not added" in b.said() and "already" in b.said(),
        b.said(),
    )
    st.esc()
    b.select(V(71, 9, 0))


def hv_selected_run():
    h.check("the steep line selected", len(b.selected()) == 1, b.selected())
    b.menu("Horizontal/Vertical")


def hv_selected_check():
    g = b.geo("hv2")
    h.check(
        "picks first: the steep line becomes Vertical", abs(g.StartPoint.x - g.EndPoint.x) < 1e-6, g
    )
    h.check("...and the tool is done", st.tool() is None, st.tool_title())


# == Coincident ============================================================================
def coin_open():
    b.menu("Coincident")


def coin_centre_line():
    b.mark()
    b.click(V(60, -30, 0))  # the circle's centre
    b.click(V(65, -50, 0))  # the line, at its very middle


def coin_centre_line_check():
    h.check(
        "report Tensegrity: tool first, a click on a line puts the centre ON the line "
        "(not at its midpoint)",
        b.new_cons() == [("PointOnObject", s["cc"], 3, s["cl"], 0, -2000)],
        b.new_cons(),
    )
    off = b.off_line(b.geo("cl"), b.geo("cc").Center)
    h.check("the centre is on the line", off < 1e-6, off)
    b.forget_said()
    b.mark()
    b.click(b.geo("cl").StartPoint)  # the line's start
    b.click(b.geo("cl").EndPoint)  # ...and its own end


def coin_same_line_check():
    h.check("the two ends of one line: nothing added", not b.new_cons(), b.new_cons())
    h.check("...and it says why", "shrink to nothing" in b.said(), b.said())
    b.forget_said()
    circle, line = b.geo("cc"), b.geo("cl")
    b.click(circle.Center + V(0, circle.Radius, 0))  # the circle (a curve) first...
    b.click(line.StartPoint + (line.EndPoint - line.StartPoint) * 0.15)  # ...then a line


def coin_two_curves_check():
    h.check(
        "two curves: refused with what to click instead",
        "click a point" in b.said(),
        b.said(),
    )
    st.esc()
    b.select(V(10, -30, 0), V(16, -36, 0))


def coin_selected_run():
    h.check("two points selected", len(b.selected()) == 2, b.selected())
    b.menu("Coincident")


def coin_selected_check():
    p, q = b.geo("p3"), b.geo("p4")
    h.check(
        "picks first: the two points meet",
        abs(p.X - q.X) < 1e-6 and abs(p.Y - q.Y) < 1e-6,
        (p, q),
    )
    h.check("...and the tool is done", st.tool() is None, st.tool_title())
    b.clean("coincident")
    b.no_modal("constraints")


def finish():
    h.ribbon("Finish Sketch")


def finished():
    h.check("the sketch closed", h.in_sketch() is None)
    sk = App.ActiveDocument.getObject(s["sk"].Name)
    h.check("the finished sketch is valid", sk.isValid() and not sk.Shape.isNull())
    Gui.Selection.clearSelection()


h.run(
    "book_sketch_b_constraints",
    st.start_steps("BookSketchBConstraints")
    + [
        reference,
        fix_open,
        fix_spline,
        fix_spline_check,
        unfix_spline_check,
        fix_point_check,
        fix_origin_check,
        fix_select_mixed,
        fix_mixed_run,
        fix_mixed_check,
        unfix_all_run,
        unfix_all_check,
        unfix_undo_check,
        co_open,
        co_verticals,
        co_verticals_check,
        co_horizontals_check,
        co_again_check,
        co_undo_check,
        co_redo_check,
        hv_open,
        hv_line,
        hv_line_check,
        hv_points_check,
        hv_fallback_check,
        hv_same_check,
        hv_selected_run,
        hv_selected_check,
        coin_open,
        coin_centre_line,
        coin_centre_line_check,
        coin_same_line_check,
        coin_two_curves_check,
        coin_selected_run,
        coin_selected_check,
        finish,
        finished,
    ],
    paced_by="state",
)
