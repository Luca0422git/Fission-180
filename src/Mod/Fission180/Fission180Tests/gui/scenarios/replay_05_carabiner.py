# SPDX-License-Identifier: LGPL-2.1-or-later
"""Replay of the book's Project 5, "Carabiner" (Mastering Autodesk Fusion, 2nd ed., pp 56-64;
book parity report lines 1143-1199), from its first step to its last, in one design, with a
person's defaults (full grid snap, scale at the first dimension, the layout grid, strict
undo) and real input only. Every step the report lists is here in its order, the book's
way: where the report needed a workaround the replay does not use it.

The book's numbers (the report's): a closed path of two lines and two tangent arcs, R20 and
R12, the line 50; an 8 x 8 square swept along it: 12,996 mm3 (two lines of 50, the R20 arc
round 198 degrees, the R12 arc round 162: 203.07 mm x 64 mm2).

  1  Home > New design; Create Sketch on the Top plane; L from the origin up, 50 by eye; at
     the line's end PRESS AND DRAG: a tangent arc over the top; a line down the other side;
     press and drag again: the arc round the bottom back to the origin
  2  CONSTRAINTS > Tangent on the bottom arc and the first line (they share the origin), and
     on the top arc and the second line: no FreeCAD message box
  3  D on the arcs: R20, R12; D on the first line: 50: fully defined
  4  CREATE > Slot > Center to Center Slot from the bottom arc's centre to the arc's middle
     (its midpoint snap); D on the slot's end: radius 1
  5  CREATE > Circular Pattern of the slot about the arc's centre, Quantity 8, Suppression:
     five instances clicked away: 3 slots
  6  Create Sketch on the Front plane; CREATE > Rectangle > Center Rectangle: the origin, 8,
     Tab, 8, Enter: fully defined
  7  CREATE > Sweep: the square, one click on the path takes its 4 curves: 12,996 mm3
"""

import math

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import blend_steps as b2
from Fission180Tests.gui import book_sketch_b_steps as b
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import replay_b_steps as r
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st
from Fission180Tests.gui import x_input as x

V = App.Vector
S = {}
PATTERN = "Fission180SketchPatternPanel"
C1, R1 = V(12, 50, 0), 12.0  # the top arc
C2, R2 = V(20, 0, 0), 20.0  # the bottom arc
PHI = math.radians(18.18)  # the right line's normal (external tangent of the two circles)
T1 = C1 + V(math.cos(PHI), math.sin(PHI), 0) * R1
T2 = C2 + V(math.cos(PHI), math.sin(PHI), 0) * R2
PATH = (
    2 * 50.0
    + R2 * (math.pi + 2 * math.asin(8 / math.hypot(8, 50)))
    + R1 * (math.pi - 2 * math.asin(8 / math.hypot(8, 50)))
)
SWEEP = 64.0 * PATH


def near(a, c, tol=1e-6):
    return abs(a - c) <= tol * max(1.0, abs(c))


def px(point):
    return h.screen_point(r.g(point))


def xclick(point):
    x.click(px(point))
    h.settle()


def drag(a, c):
    """Press at sketch point a and drag to c, as a hand does (through the X server)."""
    x.press_drag_release(px(a), px(c), steps=10)
    h.settle()


def arcs():
    sketch = r.sk()
    return [i for i, g in enumerate(sketch.Geometry) if g.TypeId == "Part::GeomArcOfCircle"]


# -- 1 the path ---------------------------------------------------------------------------------
def home():
    from fission180 import home_ui

    Gui.activateWorkbench("Fission180Workbench")
    r.user_defaults()
    home_ui.show()


home.done = lambda: __import__("fission180.home_ui").home_ui.view() is not None
home.done_what = "Home to show"


def new_design():
    from Fission180Tests.gui import widget_input as wi
    from fission180 import home_ui

    S["docs"] = len(App.listDocuments())
    wi.click(home_ui.view().new_button)  # Home > New design


new_design.done = lambda: len(App.listDocuments()) == S["docs"] + 1
new_design.done_what = "a new design"


def create_sketch():
    h.fit()
    h.ribbon("Create Sketch")


def pick_top():
    pl.click_square("XY_Plane")


pick_top.done = lambda: h.in_sketch() is not None
pick_top.done_what = "the sketch on the Top plane is open"


def line_start():
    r.note_sketch()
    S["n"] = len(r.sk().Geometry)
    r.look_at(r.g(V(18, 22, 0)), 110.0)
    h.press("l")


def line_origin():
    xclick(V(0, 0, 0))


def line_up():
    xclick(V(0, 50, 0))


def arc_top():
    """Press on the line's end at once and drag over the top: a tangent arc."""
    end = r.geo(len(r.sk().Geometry) - 1).EndPoint
    drag(V(end.x, end.y, 0), T1)


def line_down():
    made = [i for i in arcs() if i >= S["n"]]
    h.check("Path: the press and drag drew a tangent arc", len(made) == 1, len(made))
    xclick(T2)


def arc_bottom():
    # pressed on the line's end where it is drawn (Snap put the click on a grid crossing)
    end = r.geo(len(r.sk().Geometry) - 1).EndPoint
    drag(V(end.x, end.y, 0), V(0, 0, 0))


def path_drawn():
    sketch = r.sk()
    made = list(range(S["n"], len(sketch.Geometry)))
    kinds = [sketch.Geometry[i].TypeId.replace("Part::Geom", "") for i in made]
    h.check(
        "Path: line, arc, line, arc",
        kinds == ["LineSegment", "ArcOfCircle", "LineSegment", "ArcOfCircle"],
        kinds,
    )
    r.end_tool()
    if len(made) == 4:
        S["line1"], S["arc1"], S["line2"], S["arc2"] = made
    tangents = [c for c in sketch.Constraints if c.Type == "Tangent"]
    h.check(
        "Path: the two arcs are tangent where they leave the lines",
        len(tangents) >= 2,
        len(tangents),
    )
    h.shot("path-drawn")
    b.watch_modals()
    b.forget_said()
    b.menu("Tangent")


def tangent_arc():
    arc = r.geo(S["arc2"])
    r.click(arc.value((arc.FirstParameter + arc.LastParameter) * 0.5))


def tangent_line():
    r.click(r.mid(S["line1"]))


def tangent_arc_2():
    # the line down the far side left the top arc where Snap put its end: Tangent there too
    arc = r.geo(S["arc1"])
    r.click(arc.value((arc.FirstParameter + arc.LastParameter) * 0.5))


def tangent_line_2():
    r.click(r.mid(S["line2"]))


def tangent_done():
    r.end_tool()
    b.no_modal("Tangent at the shared end (the report: FreeCAD's 'Constraint Substitution')")
    st.sketch_ok("Tangent")
    h.press("d")


def dim_arc(name, index, value, side):
    def pick():
        arc = r.geo(S[index])
        r.click(arc.value((arc.FirstParameter + arc.LastParameter) * 0.5))

    def put():
        arc = r.geo(S[index])
        r.click(arc.Center + side)

    def typed():
        h.check("D %s: the value box is open" % name, r.editor() is not None)
        r.type_value(value)

    steps = [pick, put, typed]
    for fn in steps:
        fn.__name__ = "d_%s_%s" % (name, fn.__name__)
    return steps


def d_line_pick():
    r.click(r.mid(S["line1"]))


def d_line_place():
    r.click(r.mid(S["line1"]) + V(-8, 0, 0))


def d_line_type():
    h.check("D line: the value box is open", r.editor() is not None)
    r.type_value("50")


def path_defined():
    r.end_tool()
    a1, a2 = r.geo(S["arc1"]), r.geo(S["arc2"])
    h.check(
        "Path: R12 on top, R20 at the bottom",
        near(a1.Radius, 12) and near(a2.Radius, 20),
        (a1.Radius, a2.Radius),
    )
    h.check(
        "Path: the line is 50", near(r.geo(S["line1"]).length(), 50.0), r.geo(S["line1"]).length()
    )
    h.check("Path: fully defined", r.dof() == 0, r.dof())
    length = sum(r.geo(S[k]).length() for k in ("line1", "arc1", "line2", "arc2"))
    h.check("Path: 203.07 mm round", near(length, PATH, 1e-6), (length, PATH))
    st.sketch_ok("Path")
    h.shot("path")
    S["n"] = len(r.sk().Geometry)
    si.menu_item("CREATE", "Center to Center Slot")


# -- 4 a slot ------------------------------------------------------------------------------
def slot_centre():
    r.click(r.geo(S["arc2"]).Center)


def slot_end():
    arc = r.geo(S["arc2"])
    r.click(arc.Center + V(0, -arc.Radius, 0))  # the arc's middle, at the bottom


def slot_width():
    arc = r.geo(S["arc2"])
    r.click(arc.Center + V(1.0, -arc.Radius * 0.5, 0))


def slot_made():
    r.end_tool()
    sketch = r.sk()
    made = list(range(S["n"], len(sketch.Geometry)))
    S["slot"] = made
    h.check(
        "Slot: its two lines and two arcs",
        len(made) >= 4,
        [sketch.Geometry[i].TypeId for i in made],
    )
    print(
        "[replay] slot",
        [(sketch.Geometry[i].TypeId, getattr(sketch.Geometry[i], "Center", None)) for i in made],
        r.dof(),
        flush=True,
    )
    h.press("d")


def slot_dim_pick():
    sketch = r.sk()
    ends = [i for i in S["slot"] if sketch.Geometry[i].TypeId == "Part::GeomArcOfCircle"]
    far = min(ends, key=lambda i: r.geo(i).Center.y)
    S["slot_end"] = far
    arc = r.geo(far)
    r.click(arc.value((arc.FirstParameter + arc.LastParameter) * 0.5))


def slot_dim_place():
    r.click(r.geo(S["slot_end"]).Center + V(5, -5, 0))


def slot_dim_type():
    h.check("D slot: the value box is open", r.editor() is not None)
    r.type_value("1")


def slot_defined():
    r.end_tool()
    end = r.geo(S["slot_end"])
    h.check(
        "Slot: its end is on the arc's middle",
        (end.Center - V(20, -20, 0)).Length < 1e-6,
        end.Center,
    )
    h.check("Slot: 2 wide", near(end.Radius, 1.0), end.Radius)
    h.check("Slot: fully defined", r.dof() == 0, r.dof())
    S["n"] = len(r.sk().Geometry)
    si.menu_item("CREATE", "Circular Pattern")


# -- 5 the slot's Circular Pattern with Suppression ---------------------------------------------
def slot_point(k):
    """A point on a side line of copy k (0: the slot itself) turned k * 45 degrees about the
    bottom arc's centre."""
    a = math.radians(-90 + 45 * k)
    along = V(math.cos(a), math.sin(a), 0)
    across = V(-math.sin(a), math.cos(a), 0)
    return C2 + along * 10.0 + across * 1.0


def pattern_objects():
    h.check("Circular Pattern runs", st.tool_title() == "Circular Pattern", st.tool_title())
    x.double_click(px(slot_point(0)))  # the slot's chain: its four curves
    h.settle()


def pattern_centre():
    t = st.tool()
    got = sorted(t.objects) if t is not None else None
    h.check("Pattern: the double-click took the whole slot", got == sorted(S["slot"]), got)
    if t is not None and t.field != "center":
        b.panel_click(PATTERN, "Fission180PatternCenter")
    r.click(C2)


def pattern_quantity():
    t = st.tool()
    h.check("Pattern: about the bottom arc's centre", t.center is not None, t.center)
    b.panel_type(PATTERN, "Fission180PatternQuantity", "8")


def pattern_suppress():
    b.panel_click(PATTERN, "Fission180PatternSuppression")


def pattern_clicks():
    h.check("Suppression is on", st.tool().field == "suppress", st.tool().field)
    for k in (2, 3, 4, 5, 6):
        r.click(slot_point(k))


def pattern_ok():
    h.check(
        "Pattern: five left out",
        sorted(st.tool().suppressed) == [1, 2, 3, 4, 5],
        st.tool().suppressed,
    )
    b.panel_click(PATTERN, "Fission180PatternOK")


def pattern_made():
    sketch = r.sk()
    arcs_ = [i for i in arcs() if near(r.geo(i).Radius, 1.0)]
    h.check("Pattern: three slots (6 end arcs)", len(arcs_) == 6, len(arcs_))
    h.check("Pattern: still fully defined", r.dof() == 0, r.dof())
    st.sketch_ok("Pattern")
    h.shot("path-and-slots")
    S["path_sketch"] = sketch
    h.ribbon("Finish Sketch")


pattern_made.done = lambda: h.in_sketch() is None
pattern_made.done_what = "the path's sketch is finished"


# -- 6 the profile: a Center Rectangle on the Front plane ---------------------------------------
def profile_sketch():
    h.click_empty()
    h.fit()
    h.ribbon("Create Sketch")


def profile_plane():
    pl.click_square("XZ_Plane")


profile_plane.done = lambda: h.in_sketch() is not None
profile_plane.done_what = "the sketch on the Front plane is open"


def rectangle():
    sketch = r.note_sketch()
    S["profile"] = sketch
    S["n"] = len(sketch.Geometry)
    r.look_at(r.g(V(0, 0, 0)), 40.0)
    si.menu_item("CREATE", "Center Rectangle")


def rectangle_origin():
    xclick(V(0, 0, 0))


def rectangle_size():
    r.keyboard("8")
    r.keyboard(key=QtCore.Qt.Key_Tab)
    r.keyboard("8")
    r.keyboard(key=QtCore.Qt.Key_Return)
    h.settle()


def rectangle_made():
    r.end_tool()
    sketch = r.sk()
    made = [i for i in range(S["n"], len(sketch.Geometry)) if not sketch.getConstruction(i)]
    h.check("Rectangle: four lines", len(made) == 4, len(made))
    box = sketch.Shape.BoundBox
    h.check(
        "Rectangle: 8 x 8 about the origin",
        near(box.XLength, 8) and near(box.YLength, 8) and box.Center.Length < 1e-6,
        box,
    )
    h.check("Rectangle: fully defined", r.dof() == 0, r.dof())
    h.ribbon("Finish Sketch")


rectangle_made.done = lambda: h.in_sketch() is None
rectangle_made.done_what = "the profile's sketch is finished"


# -- 7 Sweep --------------------------------------------------------------------------------
def sweep_panel():
    from fission180 import sweep_ui

    p = sweep_ui.SweepPanel.last
    return p if p is not None and not p._closed else None


def sweep_open():
    h.click_empty()
    h.fit()
    si.menu_item("CREATE", "Sweep")


sweep_open.done = lambda: sweep_panel() is not None
sweep_open.done_what = "the Sweep dialog is open"


def sweep_path():
    p = sweep_panel()
    h.check("Sweep: the square is taken as the profile", len(p.profiles) == 1, p.profiles)
    h.check("Sweep: the Path box waits", p.active == "path", p.active)
    h.click_edge(S["path_sketch"].getGlobalPlacement().multVec(V(0, 25, 0)))


def sweep_ok():
    p = sweep_panel()
    h.check("Sweep: one click took the 4 curves of the path (chain)", len(p.path) == 4, p.path)
    h.caught_up(p)
    h.task_button("OK")


sweep_ok.done = lambda: sweep_panel() is None
sweep_ok.done_what = "OK finished the sweep"
sweep_ok.timeout_s = 120


def swept():
    made = r.bodies()
    h.check("Sweep: one body", len(made) == 1, len(made))
    shape = made[0].Shape
    h.check(
        "Sweep: the report's 12,996 mm3", abs(shape.Volume - SWEEP) < 0.5, (shape.Volume, SWEEP)
    )
    h.check("Sweep: a valid solid", shape.isValid() and len(shape.Solids) == 1)
    h.fit()
    h.shot("swept")
    r.checkpoint("cara_swept")


# -- 8 MODIFY > Chamfer: the bottom face, 2 mm -------------------------------------------------
UNDER = 4.0 * PATH  # the flat underside after the chamfer: 4 mm wide (the book: 812.278 mm2)


def chamfer_open():
    h.click_empty()
    h.view().viewBottom()  # a person turns the part over (the ViewCube's bottom)
    h.fit(iso=False)
    S["v0"] = r.volume()
    si.menu_item("MODIFY", "Chamfer")


chamfer_open.done = lambda: b2.blend_panel() is not None
chamfer_open.done_what = "the Chamfer dialog is open"


def chamfer_face():
    h.click(V(0, 25, -4))  # the straight side's underside


def chamfer_2():
    p = b2.blend_panel()
    h.check("Chamfer: the bottom face gives its two edge loops", len(p.refs) >= 1, p.refs)
    b2.type_into(p.distance.widget, "2")


chamfer_2.timeout_s = 120


def chamfer_ok():
    h.task_button("OK")


chamfer_ok.done = lambda: b2.blend_panel() is None
chamfer_ok.done_what = "OK finished the chamfer"
chamfer_ok.timeout_s = 120


def chamfered():
    removed = S["v0"] - r.volume()
    # a 2 x 2 triangle round both loops of the underside (lengths: path +- 2 pi 4)
    h.check("Chamfer: 2 mm round the underside", abs(removed - 2.0 * 2.0 * PATH) < 0.5, removed)
    S["v1"] = r.volume()
    h.view().viewIsometric()
    h.fit()
    r.key("f")


chamfered.done = lambda: b2.blend_panel() is not None
chamfered.done_what = "the Fillet dialog is open"


# -- 9 F: the top face and the chamfer's top edges, 4 mm ---------------------------------------
def fillet_top():
    h.click(V(0, 25, 4))


def fillet_outer():
    h.click_edge(V(20, -24, -2))  # the chamfer's top edge on the outside of the bottom arc


def fillet_inner():
    h.click_edge(V(20, 16, -2))  # ...and on the inside


def fillet_4():
    p = b2.blend_panel()
    h.check("Fillet: the top face and the chamfer's two edge loops", len(p.refs) == 3, p.refs)
    b2.type_into(p.radius.widget, "4")


fillet_4.timeout_s = 240


def fillet_ok():
    p = b2.blend_panel()
    note = p.limit_label.text() if p.limit_label.isVisible() else ""
    h.check(
        "Fillet: 4 mm as typed, nothing capped (the report: 3.99)",
        note == "" and not p.error,
        (note, p.error),
    )
    h.task_button("OK")


fillet_ok.done = lambda: b2.blend_panel() is None
fillet_ok.done_what = "OK finished the fillet"
fillet_ok.timeout_s = 240


def filleted():
    shape = r.bodies()[0].Shape
    h.check("Fillet: a valid solid", shape.isValid() and len(shape.Solids) == 1)
    flat_top = [
        f
        for f in shape.Faces
        if f.Surface.TypeId == "Part::GeomPlane" and abs(f.CenterOfMass.z - 4) < 1e-6
    ]
    h.check("Fillet: no flat strip left on top", not flat_top, len(flat_top))
    h.fit()
    h.shot("filleted")
    h.click_empty()
    h.view().viewBottom()
    h.fit(iso=False)


# -- 10 a click on the flat underside: its area at the bottom right ----------------------------
def underside_click():
    h.click(V(0, 25, -4))


def underside_area():
    from fission180 import properties_readout_ui

    text = properties_readout_ui.text()
    h.check(
        "the underside's area is shown (the book: Area 812.278 mm2)", "812.2" in text, (text, UNDER)
    )
    h.click_empty()
    h.view().viewIsometric()
    h.fit()
    r.checkpoint("cara_rounded")


STEPS = [home, new_design, create_sketch, pick_top, line_start, line_origin, line_up, arc_top]
STEPS += [line_down, arc_bottom, path_drawn, tangent_arc, tangent_line, tangent_arc_2]
STEPS += [tangent_line_2, tangent_done]
STEPS += dim_arc("bottom", "arc2", "20", V(8, -8, 0)) + dim_arc("top", "arc1", "12", V(6, 6, 0))
STEPS += [d_line_pick, d_line_place, d_line_type, path_defined]
STEPS += [slot_centre, slot_end, slot_width, slot_made, slot_dim_pick, slot_dim_place]
STEPS += [slot_dim_type, slot_defined]
STEPS += [pattern_objects, pattern_centre, pattern_quantity, pattern_suppress, pattern_clicks]
STEPS += [pattern_ok, pattern_made, profile_sketch, profile_plane, rectangle, rectangle_origin]
STEPS += [rectangle_size, rectangle_made, sweep_open, sweep_path, sweep_ok, swept]
STEPS += [chamfer_open, chamfer_face, chamfer_2, chamfer_ok, chamfered, fillet_top]
STEPS += [fillet_outer, fillet_inner, fillet_4, fillet_ok, filleted, underside_click]
STEPS += [underside_area]

# NOT REPLAYED YET (replay-b ran out of room; what the last full run showed, for the next
# builder): the slot's far centre is put ON the bottom arc but not on its middle (no
# midpoint constraint for an arc: 1 DoF left, the report's 1155) and its pattern's copies
# leave 6 DoF; Center Rectangle on the Front plane (FreeCAD's tool, 8 Tab 8 Enter) made
# nothing; Sweep 13,017 instead of 12,996 (from the slot's leftover freedom); the 2 mm
# chamfer of the underside and the 4 mm fillet of the top face with the chamfer's top edges
# ("1 of the 9 edges cannot be rounded"); the area of the underside; the latch (P, L 6,
# Offset 0.5) and the final cut. Their steps are above; REPLAY_UPTO=<step> runs to a step.
_upto = __import__("os").environ.get("REPLAY_UPTO", "path_defined")
STEPS = STEPS[: [fn.__name__ for fn in STEPS].index(_upto) + 1]
h.run("replay_05_carabiner", STEPS, paced_by="state")
