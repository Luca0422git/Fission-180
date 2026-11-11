# SPDX-License-Identifier: LGPL-2.1-or-later
"""Wave 7, the book parity report: the sketch's Mirror, Offset and Fillet.

Report items (docs/fission180/dev/research/book-parity-report.txt):
- Pizza Cutter 2104-2107: "the mirrored copy's end points ON the mirror line were not merged
  with the originals (two points 0.002 in apart, profile not closed)".
- Carabiner 1185-1188: Offset "besides the offset lines adds 6 short connector lines"; the
  offset did not close into a profile, so it could not be extruded.
- Fire Piston 1691-1694: the sketch Fillet's typed radius was not used.

A  A half profile whose two ends are 0.02 mm short of the mirror line (drawn by hand, not
   snapped): CREATE > Mirror about the construction line: the ends are joined with their
   mirror images, the whole outline is ONE closed loop.
B  A U of three lines standing on a base line: O, a click on the U (Chain Selection), the
   pointer inside, 6, Enter: three parallel lines and nothing else to see (the square
   helper lines are hidden); the strip between the U and its offset is a closed profile:
   Finish Sketch, click it, E, 5: a solid of 408 x 5 mm3.
C  MODIFY > Fillet, a corner, 4 typed over the sketch, Enter: the arc has radius 4 exactly,
   with its radius dimension.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets

from Fission180Tests.gui import book_sketch_b_steps as b
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st

V = App.Vector
s = st.s
MIRROR = "Fission180MirrorPanel"
LINE = "Part::GeomLineSegment"


def one_mm_grid():
    from fission180 import grid_ui

    grid_ui.put("Subdivisions", 10)
    grid_ui.apply_subdivisions()


def reference():
    import Part

    # A: the mirror line and a half profile whose ends stop 0.02 mm short of it
    s["axis"] = b.add(Part.LineSegment(V(-60, 15, 0), V(-60, 50, 0)), True)
    b.con("Vertical", s["axis"])
    half = [
        Part.LineSegment(V(-59.98, 20, 0), V(-40, 20, 0)),
        Part.LineSegment(V(-40, 20, 0), V(-40, 40, 0)),
        Part.LineSegment(V(-40, 40, 0), V(-59.985, 40, 0)),
    ]
    s["half"] = [b.add(g) for g in half]
    b.con("Coincident", s["half"][0], 2, s["half"][1], 1)
    b.con("Coincident", s["half"][1], 2, s["half"][2], 1)
    # B: a base line and a U standing on it
    s["base"] = b.add(Part.LineSegment(V(-30, -40, 0), V(30, -40, 0)))
    u = [
        Part.LineSegment(V(-20, -40, 0), V(-20, -20, 0)),
        Part.LineSegment(V(-20, -20, 0), V(20, -20, 0)),
        Part.LineSegment(V(20, -20, 0), V(20, -40, 0)),
    ]
    s["u"] = [b.add(g) for g in u]
    b.con("Coincident", s["u"][0], 2, s["u"][1], 1)
    b.con("Coincident", s["u"][1], 2, s["u"][2], 1)
    b.con("PointOnObject", s["u"][0], 1, s["base"])
    b.con("PointOnObject", s["u"][2], 2, s["base"])
    b.con("Horizontal", s["base"])
    b.con("Vertical", s["u"][0])
    b.con("Vertical", s["u"][2])
    b.con("Horizontal", s["u"][1])
    # C: a corner to round
    s["f1"] = b.add(Part.LineSegment(V(40, 10, 0), V(70, 10, 0)))
    s["f2"] = b.add(Part.LineSegment(V(70, 10, 0), V(70, 35, 0)))
    b.con("Coincident", s["f1"], 2, s["f2"], 1)
    App.ActiveDocument.recompute()
    b.clean("the reference sketch")
    b.watch_modals()


def seen_lines():
    """The lines of the sketch a person sees: (index, geometry), no hidden helpers."""
    from fission180 import sketch_helpers

    sk = b.sk()
    unseen = sketch_helpers.hidden(sk)
    return [(i, g) for i, g in enumerate(sk.Geometry) if i not in unseen and g.TypeId == LINE]


# == A: Mirror joins the ends that lie on the mirror line ===================================
def a_select():
    lines = [b.sk().Geometry[i] for i in s["half"]]
    b.select(*[g.StartPoint + (g.EndPoint - g.StartPoint) * 0.6 for g in lines])


def a_mirror():
    h.check("the half profile is selected", len(b.selected()) == 3, b.selected())
    si.menu_item("CREATE", "Mirror")


def a_line_field():
    h.check("Mirror runs with the three lines", st.tool() is not None and len(st.tool().objects) == 3)
    b.panel_click(MIRROR, "Fission180MirrorLine")


def a_line_click():
    b.click(V(-60, 46, 0))


def a_ok():
    ok = b.in_panel(MIRROR, "Fission180MirrorOK")
    h.check("the mirror line is picked: OK can be pressed", ok is not None and ok.isEnabled())
    s["undo"] = len(b.undo_names())
    b.panel_click(MIRROR, "Fission180MirrorOK")


def a_made():
    sk = b.sk()
    lines = [g for i, g in seen_lines() if g.StartPoint.y > 15 and not sk.getConstruction(i)]
    h.check("three mirrored lines", len(lines) == 6, len(lines))
    import Part

    edges = [g.toShape() for g in lines]
    wires = [Part.Wire(group) for group in Part.sortEdges(edges)]
    h.check(
        "report Pizza Cutter: the ends on the mirror line are joined: ONE closed outline",
        len(wires) == 1 and wires[0].isClosed(),
        [(len(w.Edges), w.isClosed()) for w in wires],
    )
    joins = [
        c
        for c in sk.Constraints
        if c.Type == "Coincident" and {c.First, c.Second} & set(s["half"]) and max(c.First, c.Second) > max(s["half"])
    ]
    h.check("...by a Coincident at each of the two ends", len(joins) == 2, len(joins))
    if len(wires) == 1 and wires[0].isClosed():
        area = Part.Face(wires[0]).Area
        h.check("the outline is the 40 x 20 rectangle", abs(area - 800.0) < 0.5, area)
    h.check("one undo step", len(b.undo_names()) == s["undo"] + 1, b.undo_names()[:3])
    b.clean("after Mirror")


# == B: Offset: the parallel curve only, and it closes a profile ============================
def b_offset():
    s["lines"] = len(seen_lines())
    s["geo"] = len(b.sk().Geometry)
    h.press("o")


def b_pick():
    h.check("Offset runs", st.tool_title() == "Offset", st.tool_title())
    st.click(V(0, -20, 0), towards=V(0, 1, 0))


def b_inside():
    st.hover(V(0, -30, 0), towards=V(0, -1, 0))  # inside the U


def b_type():
    st.keys("6\n")


def b_made():
    from fission180 import sketch_helpers

    sk = b.sk()
    new = [(i, g) for i, g in seen_lines() if i >= s["geo"]]
    h.check(
        "report Carabiner: the offset is three parallel lines and nothing else to see",
        len(new) == 3 and len(seen_lines()) == s["lines"] + 3,
        (len(new), len(seen_lines()), s["lines"]),
    )
    hidden = sketch_helpers.hidden(sk)
    h.check("...its square helper lines work unseen", len(hidden) >= 1 and sketch_helpers.nodes(st.session().view) > 0, len(hidden))
    ends = sorted((round(g.StartPoint.x, 6), round(g.StartPoint.y, 6)) for _i, g in new) + sorted(
        (round(g.EndPoint.x, 6), round(g.EndPoint.y, 6)) for _i, g in new
    )
    for want in ((-14.0, -40.0), (14.0, -40.0), (-14.0, -26.0), (14.0, -26.0)):
        h.check("an offset corner or end exactly at %s" % (want,), want in ends, ends)
    b.clean("after Offset")
    b.no_modal("Mirror and Offset")


# == C: Fillet with a typed radius ==========================================================
def c_fillet():
    si.menu_item("MODIFY", "Fillet")


def c_corner():
    h.check("Fillet runs", st.tool_title() == "Fillet", st.tool_title())
    st.click(V(70, 10, 0))


def c_type():
    h.check("the corner is picked", len(st.tool().corners) == 1, st.tool().corners)
    st.keys("4\n")


def c_made():
    sk = b.sk()
    arcs = [g for g in sk.Geometry if g.TypeId == "Part::GeomArcOfCircle"]
    h.check("report Fire Piston: the typed radius is the fillet's radius", len(arcs) == 1 and abs(arcs[0].Radius - 4.0) < 1e-9, [a.Radius for a in arcs])
    radii = [c for c in sk.Constraints if c.Type == "Radius"]
    h.check("...with its radius dimension of 4", len(radii) == 1 and abs(radii[0].Value - 4.0) < 1e-9)
    h.check("Enter made it and ended the tool", st.tool() is None, st.tool_title())
    b.clean("after Fillet")


# == the strip between the U and its offset is a profile ====================================
def finish():
    h.ribbon("Finish Sketch")


def pick_strip():
    h.check("the sketch closed", h.in_sketch() is None)
    h.fit()
    h.click(st.g(V(-17, -32, 0)))  # in the strip, between the U's left side and its offset


def extrude():
    h.press("e")


def distance():
    from Fission180Tests.gui import blend_steps

    panel = blend_steps.active_panel()
    field = getattr(getattr(panel, "distance", None), "widget", None)
    if h.check("the Extrude dialog is open", field is not None):
        blend_steps.type_into(field, "5")


def ok():
    h.task_button("OK")


def extruded():
    body = h.body()
    volume = body.Shape.Volume if body is not None and not body.Shape.isNull() else 0.0
    # the strip: inside the U (40 x 20) less inside its offset (28 x 14) = 408 mm2
    h.check(
        "report Carabiner: the strip between the lines and their offset is a closed "
        "profile and extrudes (408 x 5 mm3)",
        abs(volume - 2040.0) < 0.5,
        volume,
    )
    Gui.Selection.clearSelection()


h.run(
    "book_sketch_b_modify",
    [st.new_design("BookSketchBModify"), one_mm_grid, st.create_sketch, st.pick_xy, st.sketch_open]
    + [
        reference,
        a_select,
        a_mirror,
        a_line_field,
        a_line_click,
        a_ok,
        a_made,
        b_offset,
        b_pick,
        b_inside,
        b_type,
        b_made,
        c_fillet,
        c_corner,
        c_type,
        c_made,
        finish,
        pick_strip,
        extrude,
        distance,
        ok,
        extruded,
    ],
    paced_by="state",
)
assert QtWidgets  # (kept for the helpers' Qt types)
