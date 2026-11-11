# SPDX-License-Identifier: LGPL-2.1-or-later
"""Wave 7, the book parity report: sketch patterns whose copies are TIED to the original, like
Fusion's, with Suppression, Symmetric counting the instances, and a typed Quantity that
counts without an extra commit.

Report items (docs/fission180/dev/research/book-parity-report.txt):
- Tensegrity 1077-1079, Drone 1466-1474, Hot End 1873-1879, Tesla 2185-2188: "the patterned
  copies are not tied to the original: the sketch went from fully constrained to 25 Degrees of
  Freedom"; copies drifted by micrometres (profiles did not close); a dimension added AFTER
  the pattern moved only the original.
- Carabiner 1157-1163: no Suppression (book: Quantity 8, then untick 5 instances); Symmetric
  counted each side (Quantity 3 gave 5).
- Tesla 2185: Rectangular Pattern, Symmetric, Quantity 5 gave 9 circles (the book: 5).
- Drone 1544-1546: a typed Quantity kept the old value until the field was committed.

A  A fully constrained triangle, Circular Pattern about the origin, Quantity typed 6 and OK
   clicked straight away: 5 copies, the sketch still FULLY constrained, no helper line to
   see. The original's 30 mm dimension double-clicked and set to 36: every copy follows, the
   corners of each copy still meet exactly. Undo, Undo: the value, then the whole pattern.
B  A circle, Circular Pattern, Quantity 8, Suppression: five copies clicked away: 3 circles.
C  A circle, Rectangular Pattern, Spacing 6, Symmetric, Quantity 5: five circles in all,
   two on each side. Its height dimension set afterwards: the copies come along.
"""

import math

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import book_sketch_b_steps as b
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st

V = App.Vector
s = st.s
PANEL = "Fission180SketchPatternPanel"


def reference():
    import Part

    # a triangle pointing right, fully constrained: corners (30, -5), (40, 0), (30, 5)
    pts = [V(30, -5, 0), V(40, 0, 0), V(30, 5, 0)]
    tri = [b.add(Part.LineSegment(pts[i], pts[(i + 1) % 3])) for i in range(3)]
    s["tri"] = tri
    for i in range(3):
        b.con("Coincident", tri[i], 2, tri[(i + 1) % 3], 1)
    b.con("Vertical", tri[2])
    b.con("Equal", tri[0], tri[1])
    s["d30"] = b.con("DistanceX", -1, 1, tri[0], 1, 30.0)
    b.con("DistanceY", tri[0], 1, -1, 1, 5.0)
    b.con("Distance", tri[2], 10.0)
    b.con("DistanceX", tri[0], 1, tri[0], 2, 10.0)
    b.sk().setLabelDistance(s["d30"], -14.0)
    App.ActiveDocument.recompute()
    b.clean("the reference sketch")
    h.check("the triangle is fully constrained", b.dof() == 0, b.dof())
    s["geos"] = len(b.sk().Geometry)
    s["cons"] = len(b.sk().Constraints)
    b.watch_modals()


def tool():
    return st.tool()


def label(index):
    """Where a dimension's text is (a global point)."""
    from fission180 import sketch_mode

    return st.g(sketch_mode.label_point(b.sk(), index))


def hidden():
    from fission180 import sketch_helpers

    return sketch_helpers.hidden(b.sk())


def helper_nodes():
    from fission180 import sketch_helpers

    return sketch_helpers.nodes(st.session().view) > 0


def own_lines():
    """The sketch's lines a person can see (not the hidden helpers)."""
    unseen = hidden()
    sk = b.sk()
    return [
        g
        for i, g in enumerate(sk.Geometry)
        if i not in unseen and g.TypeId == "Part::GeomLineSegment"
    ]


# == A: a circular pattern that stays fully constrained ====================================
def a_select():
    # (a third of the way along each line: the Vertical's symbol sits on a line's middle)
    lines = [b.sk().Geometry[i] for i in s["tri"]]
    spots = (0.8, 0.2, 0.3)  # (clear of the Equal symbols too)
    b.select(*[g.StartPoint + (g.EndPoint - g.StartPoint) * f for g, f in zip(lines, spots)])


def a_start():
    picked = sorted(b.selected())
    h.check(
        "the triangle's three lines are selected", picked == ["Edge1", "Edge2", "Edge3"], picked
    )
    si.menu_item("CREATE", "Circular Pattern")


def a_centre():
    t = tool()
    h.check(
        "Circular Pattern runs with the triangle as Objects", t is not None and len(t.objects) == 3
    )
    h.check(
        "...and waits for the Center Point", t is not None and t.field == "center", t and t.field
    )
    st.click(V(0, 0, 0), towards=V(-0.6, -1.0, 0))


def a_quantity():
    h.check("the origin is the centre", tool().center == (-1, 1), tool().center)
    # typed and NOT committed: no Enter, no Tab; OK is clicked straight away
    b.panel_type(PANEL, "Fission180PatternQuantity", "6", enter=False)


def a_ok():
    s["undo"] = len(b.undo_names())
    b.panel_click(PANEL, "Fission180PatternOK")


def a_made():
    sk = b.sk()
    h.check(
        "report Drone: the typed Quantity 6 counts without an extra commit (5 copies)",
        len(own_lines()) == 18,
        len(own_lines()),
    )
    h.check("the tool is done, its panel gone", tool() is None and b.panel(PANEL) is None)
    h.check(
        "report Tensegrity: the sketch is still FULLY constrained (was: 25 degrees of freedom)",
        b.dof() == 0 and sk.solve() == 0,
        b.dof(),
    )
    b.clean("after the circular pattern")
    h.check(
        "one undo step",
        b.undo_names()[: len(b.undo_names()) - s["undo"]] == ["Circular Pattern"],
        b.undo_names()[:3],
    )
    h.check("the ties work through hidden helper lines", len(hidden()) > 0, len(hidden()))
    h.check("...that are not drawn (and so never picked)", helper_nodes())
    lines = [g for g in own_lines()]
    # the copy turned 180 degrees: the corner (30, -5) lands on (-30, 5)
    ends = [(g.StartPoint.x, g.StartPoint.y) for g in lines]
    h.check(
        "a copy stands exactly where the pattern puts it",
        any(math.dist(e, (-30.0, 5.0)) < 1e-7 for e in ends),
        ends[:8],
    )
    h.shot("circular-tied")
    pos = h.screen_point(label(s["d30"]))
    h.pointer_to(h.gl_widget(), pos)
    h.view_drawn()
    si.double_click_widget(h.gl_widget(), pos)


def a_edit_dimension():
    h.check("the 30 mm dimension's box is open", st.session().editor is not None)
    si.type_text("36")


def corners_meet(lines):
    """Every end of the lines meets another line's end (closed profiles)."""
    ends = [(g.StartPoint.x, g.StartPoint.y) for g in lines] + [
        (g.EndPoint.x, g.EndPoint.y) for g in lines
    ]
    worst = 0.0
    for i, e in enumerate(ends):
        nearest = min(math.dist(e, o) for k, o in enumerate(ends) if k != i)
        worst = max(worst, nearest)
    return worst


def a_follows():
    lines = own_lines()
    ends = [(g.StartPoint.x, g.StartPoint.y) for g in lines]
    h.check(
        "the original moved to 36", any(math.dist(e, (36.0, -5.0)) < 1e-7 for e in ends), ends[:4]
    )
    for want in (
        (-36.0, 5.0),
        (
            36 * math.cos(math.radians(60)) + 5 * math.sin(math.radians(60)),
            36 * math.sin(math.radians(60)) - 5 * math.cos(math.radians(60)),
        ),
    ):
        h.check(
            "report Drone: a dimension changed AFTER the pattern moves the copies too (%.1f, %.1f)"
            % want,
            any(math.dist(e, want) < 1e-6 for e in ends),
            ends,
        )
    gap = corners_meet(lines)
    h.check(
        "report Drone: every copy's corners still meet exactly (profiles close)", gap < 1e-7, gap
    )
    h.check("still fully constrained", b.dof() == 0, b.dof())
    from fission180 import parameters

    rows = [
        r for r in parameters.model_parameters(App.ActiveDocument) if r["object"] == b.sk().Name
    ]
    h.check(
        "the Parameters list shows the 4 dimensions, not the pattern's hidden ties",
        len(rows) == 4,
        len(rows),
    )
    st.undo()


def a_undo_value():
    ends = [(g.StartPoint.x, g.StartPoint.y) for g in own_lines()]
    h.check(
        "Undo: 30 again, the copies too",
        any(math.dist(e, (-30.0, 5.0)) < 1e-7 for e in ends),
        ends[:6],
    )
    st.undo()


def a_undo_pattern():
    sk = b.sk()
    h.check(
        "Undo: the whole pattern is gone, its hidden lines too",
        len(sk.Geometry) == s["geos"] and len(sk.Constraints) == s["cons"] and not hidden(),
        (len(sk.Geometry), len(sk.Constraints), len(hidden())),
    )
    st.redo()


def a_redo_pattern():
    h.check(
        "Redo: the pattern is back, fully constrained",
        len(own_lines()) == 18 and b.dof() == 0,
        (len(own_lines()), b.dof()),
    )
    h.check("...its helper lines still unseen", helper_nodes() and len(hidden()) > 0)


# == B: Suppression =========================================================================
def b_reference():
    import Part

    s["hole"] = b.add(Part.Circle(V(0, 62, 0), V(0, 0, 1), 3))
    b.con("Radius", s["hole"], 3.0)
    b.con("DistanceY", -1, 1, s["hole"], 3, 62.0)
    b.con("PointOnObject", s["hole"], 3, -2)
    App.ActiveDocument.recompute()
    h.check("the hole is fully constrained too", b.dof() == 0, b.dof())
    s["circles"] = len(si.circles(b.sk()))
    Gui.Selection.clearSelection()
    b.select(V(3, 62, 0))


def b_start():
    si.menu_item("CREATE", "Circular Pattern")


def b_centre():
    st.click(V(0, 0, 0), towards=V(-0.6, -1.0, 0))


def b_quantity():
    b.panel_type(PANEL, "Fission180PatternQuantity", "8")


def b_suppression():
    h.check("eight in the preview (7 copies)", len(tool().moves_now) == 7, len(tool().moves_now))
    b.panel_click(PANEL, "Fission180PatternSuppression")


def copy_point(k):
    """A point on the rim of copy k (1..7) of the hole, turned k * 45 degrees."""
    a = math.radians(90 + 45 * k)
    return V(62 * math.cos(a) + 3 * math.cos(a), 62 * math.sin(a) + 3 * math.sin(a), 0)


def b_click_copies():
    h.check("Suppression is on: clicks leave copies out", tool().field == "suppress", tool().field)
    for k in (2, 3, 4, 5, 6):
        st.click(copy_point(k))


def b_left_out():
    t = tool()
    h.check(
        "five copies are left out", sorted(t.suppressed) == [1, 2, 3, 4, 5], sorted(t.suppressed)
    )
    msg = b.in_panel(PANEL, "Fission180PatternMessage")
    h.check("the panel says so", msg is not None and "5 of 7" in msg.text(), msg and msg.text())
    st.click(copy_point(2))  # one too many: a click brings it back
    st.click(copy_point(2))  # ...and leaves it out again


def b_ok():
    h.check(
        "a click brings a copy back, the next leaves it out",
        sorted(tool().suppressed) == [1, 2, 3, 4, 5],
    )
    b.panel_click(PANEL, "Fission180PatternOK")


def b_made():
    circles = [g for _i, g in si.circles(b.sk())]
    h.check(
        "report Carabiner: Quantity 8 with 5 instances suppressed: 3 circles",
        len(circles) == s["circles"] + 2,
        len(circles),
    )
    centres = sorted((round(g.Center.x, 6), round(g.Center.y, 6)) for g in circles)
    want = sorted(
        (round(62 * math.cos(math.radians(a)), 6), round(62 * math.sin(math.radians(a)), 6))
        for a in (90, 135, 45)
    )
    h.check("...the original and its two neighbours", centres == want, centres)
    h.check("still fully constrained", b.dof() == 0, b.dof())
    b.clean("after the suppressed pattern")


# == C: Rectangular, Symmetric, then a dimension ============================================
def c_reference():
    import Part

    s["pin"] = b.add(Part.Circle(V(0, -40, 0), V(0, 0, 1), 2))
    b.con("Radius", s["pin"], 2.0)
    s["dy"] = b.con("DistanceY", s["pin"], 3, -1, 1, 40.0)
    b.con("PointOnObject", s["pin"], 3, -2)
    b.sk().setLabelDistance(s["dy"], 26.0)
    App.ActiveDocument.recompute()
    h.check("the pin hole is fully constrained", b.dof() == 0, b.dof())
    s["circles"] = len(si.circles(b.sk()))
    Gui.Selection.clearSelection()
    a = math.radians(215)  # (a spot on its rim clear of the radius and its symbols)
    b.select(V(2 * math.cos(a), -40 + 2 * math.sin(a), 0))


def c_start():
    si.menu_item("CREATE", "Rectangular Pattern")


def c_values():
    h.check(
        "Rectangular Pattern runs with the circle",
        tool() is not None and tool().objects == [s["pin"]],
        tool() and tool().objects,
    )
    b.panel_choose(PANEL, "Fission180PatternDistanceType", "Spacing")


def c_symmetric():
    b.panel_choose(PANEL, "Fission180PatternDirectionType", "Symmetric")


def c_quantity():
    b.panel_type(PANEL, "Fission180PatternDistance", "6")
    b.panel_type(PANEL, "Fission180PatternQuantity", "5", enter=False)


def c_ok():
    b.panel_click(PANEL, "Fission180PatternOK")


def pins():
    return sorted(
        (round(g.Center.x, 6), round(g.Center.y, 6))
        for _i, g in si.circles(b.sk())
        if abs(g.Radius - 2.0) < 1e-6
    )


def c_made():
    h.check(
        "report Tesla: Symmetric, Quantity 5: FIVE circles in all, two on each side",
        pins() == [(-12.0, -40.0), (-6.0, -40.0), (0.0, -40.0), (6.0, -40.0), (12.0, -40.0)],
        pins(),
    )
    h.check("still fully constrained", b.dof() == 0, b.dof())
    b.clean("after the rectangular pattern")
    pos = h.screen_point(label(s["dy"]))
    h.pointer_to(h.gl_widget(), pos)
    h.view_drawn()
    si.double_click_widget(h.gl_widget(), pos)


def c_edit():
    h.check("the 40 mm dimension's box is open", st.session().editor is not None)
    si.type_text("46")


def c_follows():
    h.check(
        "report Hot End: dimensioned AFTER the pattern: the copies come along",
        pins() == [(-12.0, -46.0), (-6.0, -46.0), (0.0, -46.0), (6.0, -46.0), (12.0, -46.0)],
        pins(),
    )
    h.check("still fully constrained", b.dof() == 0, b.dof())
    b.no_modal("the patterns")


def finish():
    h.ribbon("Finish Sketch")


def reopen():
    h.check("the sketch closed", h.in_sketch() is None)
    sk = App.ActiveDocument.getObject(s["sk"].Name)
    h.check("the finished sketch is valid", sk.isValid())
    si.timeline_double_click("Sketch 1")


reopen.done = lambda: h.in_sketch() is not None
reopen.done_what = "the sketch is open again"


def reopened():
    s["sk"] = h.in_sketch()
    h.check("opened again: the helper lines are still unseen", helper_nodes() and len(hidden()) > 0)
    h.check("...and it is still fully constrained", b.dof() == 0, b.dof())
    h.ribbon("Finish Sketch")


def closed():
    h.check("closed", h.in_sketch() is None)
    Gui.Selection.clearSelection()


h.run(
    "book_sketch_b_pattern",
    st.start_steps("BookSketchBPattern")
    + [
        reference,
        a_select,
        a_start,
        a_centre,
        a_quantity,
        a_ok,
        a_made,
        a_edit_dimension,
        a_follows,
        a_undo_value,
        a_undo_pattern,
        a_redo_pattern,
        b_reference,
        b_start,
        b_centre,
        b_quantity,
        b_suppression,
        b_click_copies,
        b_left_out,
        b_ok,
        b_made,
        c_reference,
        c_start,
        c_values,
        c_symmetric,
        c_quantity,
        c_ok,
        c_made,
        c_edit,
        c_follows,
        finish,
        reopen,
        reopened,
        closed,
    ],
    paced_by="state",
)
