# SPDX-License-Identifier: LGPL-2.1-or-later
"""Replay of the book's Project 4, "Tensegrity Tower" (Mastering Autodesk Fusion, 2nd ed.,
pp 48-55; book parity report lines 1048-1141), from its first step to its last, in one
design, with a person's defaults (full grid snap, scale at the first dimension, the layout
grid, strict undo) and real input only. Every step the report lists is here in its order,
the book's way: where the report needed a workaround the replay does not use it.

  1  Home > New design; Create Sketch on the Top plane; CREATE > Circumscribed Polygon (6
     sides): the origin, then the middle of the top edge
  2  CONSTRAINTS > Horizontal/Vertical on the top edge: no redundant constraint
  3  D on the leftmost and the rightmost CORNERS, 100: 100 across, fully defined
  4  L, X (construction), the top-left corner, the ORIGIN, the top-right corner: the chain
     goes on through the origin, two guides
  5  L (X off again), a triangle; Equal on its sides; Parallel left side / left guide; the
     second Parallel (implied) is refused with the reason
  6  D 3 and 3 between the sides and the guides, 6 between the top lines: fully defined
  7  CREATE > Circular Pattern: a DOUBLE-CLICK on the triangle takes it whole, the origin,
     Quantity 6: still fully defined
  8  a circle; Coincident, tool first: its centre on the left guide, then on the triangle's
     top line; D 3.5
  9  the Origin's eye; CREATE > Mirror about the Y axis, then both circles about the X axis
 10  E: the frame's area, 6 mm: 18,376 mm3 (the report's hand check: 18,378)
"""

import math

import FreeCAD as App
import FreeCADGui as Gui

from PySide import QtWidgets

from Fission180Tests.gui import blend_steps as b2
from Fission180Tests.gui import book_sketch_b_steps as b
from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import hole_steps as hs
from Fission180Tests.gui import looks_steps as k
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import replay_b_steps as r
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st
from Fission180Tests.gui import timeline_input as tl
from Fission180Tests.gui import widget_input as w
from Fission180Tests.gui import x_input as x

V = App.Vector
S = {}
ROOT3 = math.sqrt(3.0)
MIRROR = "Fission180MirrorPanel"
PATTERN = "Fission180SketchPatternPanel"


def near(a, c, tol=1e-6):
    return abs(a - c) <= tol * max(1.0, abs(c))


def px(point):
    return h.screen_point(r.g(point))


def xclick(point):
    """A click through the X server (a person's mouse: Qt works out double-clicks itself)."""
    x.click(px(point))
    h.settle()


def lines(construction=False):
    sketch = r.sk()
    return [
        i
        for i, g in enumerate(sketch.Geometry)
        if g.TypeId == "Part::GeomLineSegment" and bool(sketch.getConstruction(i)) == construction
    ]


def hexagon():
    return S["hex"]


def corner(which):
    """The hexagon's corner: "left", "right", "top_left", "top_right"."""
    points = [r.geo(i).StartPoint for i in hexagon()]
    if which == "left":
        return min(points, key=lambda p: p.x)
    if which == "right":
        return max(points, key=lambda p: p.x)
    top = sorted(points, key=lambda p: -p.y)[:2]
    return min(top, key=lambda p: p.x) if which == "top_left" else max(top, key=lambda p: p.x)


def top_edge():
    return max(hexagon(), key=lambda i: r.mid(i).y)


# -- 1 a new design, the polygon ------------------------------------------------------------
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


def polygon():
    r.note_sketch()
    S["n"] = len(r.sk().Geometry)
    r.look_at(r.g(V(0, 0, 0)), 140.0)
    si.menu_item("CREATE", "Circumscribed Polygon")


def polygon_centre():
    t = st.tool()
    sides = getattr(t, "sides", None)
    h.check("Polygon: 6 sides in its box", sides in (None, 6), sides)
    r.click(V(0, 0, 0))


def polygon_edge():
    r.click(V(0, 40, 0))  # the middle of the top edge


def polygon_made():
    r.end_tool()
    sketch = r.sk()
    new = list(range(S["n"], len(sketch.Geometry)))
    from fission180 import sketch_draw_helpers

    hidden = sketch_draw_helpers.hidden(sketch)
    shown = [i for i in new if i in lines() and i not in hidden]
    S["hex"] = shown[:6]
    h.check("Polygon: six lines", len(S["hex"]) == 6, [sketch.Geometry[i].TypeId for i in new])
    st.sketch_ok("Polygon")
    S["dof_polygon"] = r.dof()
    # (the edge's middle clicked on the Y axis is put on it: the turn is held already)
    h.check(
        "Polygon: its centre on the origin, at most size and turn left to define",
        S["dof_polygon"] in (1, 2),
        S["dof_polygon"],
    )
    b.forget_said()
    b.menu("Horizontal/Vertical")


def hv_top():
    r.click(r.mid(top_edge()) + V(-6, 0, 0))


def hv_done():
    r.end_tool()
    sketch = r.sk()
    top = r.geo(top_edge())
    h.check("H/V: the top edge is horizontal", abs(top.StartPoint.y - top.EndPoint.y) < 1e-9, top)
    h.check(
        "H/V: no redundant constraint (the report: 'Redundant constraints (17)')",
        not sketch.RedundantConstraints and not sketch.ConflictingConstraints,
        (sketch.RedundantConstraints, sketch.ConflictingConstraints),
    )
    h.press("d")


def d_left():
    xclick(corner("left"))


def d_right():
    picks = st.tool().picks
    h.check("D: the left corner is picked", len(picks) == 1, picks)
    xclick(corner("right"))


def d_place():
    picks = st.tool().picks
    h.check("D: two corners picked (the report: no dimension)", len(picks) == 2, picks)
    xclick(V(0, -62, 0))


def d_type():
    h.check("D: the value box is open", r.editor() is not None)
    r.type_value("100")


def d_done():
    r.end_tool()
    left, right = corner("left"), corner("right")
    h.check("D: 100 across the corners", near(right.x - left.x, 100.0), (left, right))
    h.check("D: the hexagon is fully defined", r.dof() == 0, r.dof())
    st.sketch_ok("Hexagon")
    S["n"] = len(r.sk().Geometry)
    h.press("l")


# -- 4 the guides: L, X, corner - origin - corner -----------------------------------------
def guides_x():
    line = getattr(st.session(), "line", None)
    h.check("L starts the Line tool", line is not None and line.active, line)
    h.press("x")


def guide_1():
    xclick(corner("top_left"))


def guide_2():
    xclick(V(0, 0, 0))


def guide_3():
    xclick(corner("top_right"))


def guides_made():
    sketch = r.sk()
    h.shot("guides")
    made = [i for i in range(S["n"], len(sketch.Geometry))]
    construction = [i for i in made if sketch.getConstruction(i)]
    h.check(
        "Guides: two construction lines, corner - origin - corner (the chain went on)",
        len(made) == 2 and construction == made,
        [(sketch.Geometry[i].TypeId, sketch.getConstruction(i)) for i in made],
    )
    S["guides"] = sorted(made, key=lambda i: r.mid(i).x)  # left, right
    r.end_tool()
    S["n"] = len(sketch.Geometry)
    h.press("l")


# -- 5 the triangle ----------------------------------------------------------------------
def triangle_mode():
    from fission180 import sketch_mode

    S["was_construction"] = sketch_mode.construction_mode()
    if S["was_construction"]:
        h.press("x")  # (construction stays on into the next Line, as in Fusion)


def triangle_points():
    # (the bottom corner off the Y axis: on it, the triangle would be held symmetric and the
    # book's second 3 mm would be a driven dimension)
    for point in (V(-13, 36, 0), V(13, 36, 0), V(4, 14, 0)):
        xclick(point)


def triangle_close():
    sketch = r.sk()
    first = sketch.Geometry[S["n"]].StartPoint
    xclick(first)


def triangle_made():
    r.end_tool()
    sketch = r.sk()
    h.shot("triangle")
    made = list(range(S["n"], len(sketch.Geometry)))
    h.check(
        "Triangle: three lines, not construction",
        len(made) == 3 and not any(sketch.getConstruction(i) for i in made),
        [(sketch.Geometry[i].TypeId, sketch.getConstruction(i)) for i in made],
    )
    S["tri"] = made
    top = max(made, key=lambda i: r.mid(i).y)
    sides = sorted([i for i in made if i != top], key=lambda i: r.mid(i).x)
    S["tri_top"], S["tri_left"], S["tri_right"] = top, sides[0], sides[1]
    level = [c for c in sketch.Constraints if c.Type == "Horizontal" and c.First == top]
    h.check("Triangle: its top line got Horizontal by itself", len(level) == 1, len(level))
    b.forget_said()
    b.menu("Equal")


def equal_left():
    r.click(r.mid(S["tri_left"]))


def equal_right():
    r.click(r.mid(S["tri_right"]))


def equal_done():
    r.end_tool()
    h.check("Equal: the two sides", b.has("Equal", S["tri_left"], S["tri_right"]), b.cons()[-3:])
    b.menu("Parallel")


def parallel_left():
    r.click(r.mid(S["tri_left"]))


def parallel_guide():
    r.click(_on(S["guides"][0], 0.3))


def _on(index, f):
    g = r.geo(index)
    return g.StartPoint + (g.EndPoint - g.StartPoint) * f


def parallel_right():
    h.check(
        "Parallel: left side and left guide",
        b.has("Parallel", S["tri_left"], S["guides"][0]),
        b.cons()[-3:],
    )
    b.mark()
    b.forget_said()
    r.click(r.mid(S["tri_right"]))


def parallel_right_guide():
    r.click(_on(S["guides"][1], 0.3))


def parallel_refused():
    h.check("Parallel: the second one is not added (it is implied)", not b.new_cons(), b.new_cons())
    h.check(
        "Parallel: ...and that is said (the book: Fusion shows an error)", bool(b.said()), b.said()
    )
    st.sketch_ok("Parallel")
    r.end_tool()
    h.press("d")


# -- 6 D 3, 3, 6 -----------------------------------------------------------------------
def dimension_steps(name, first, second, place, value):
    def pick_1():
        r.click(first())

    def pick_2():
        r.click(second())

    def put():
        r.click(place())

    def typed():
        h.check("D %s: the value box is open" % name, r.editor() is not None)
        r.type_value(value)

    steps = [pick_1, pick_2, put, typed]
    for fn in steps:
        fn.__name__ = "d_%s_%s" % (name, fn.__name__)
    return steps


def gap_left():
    left = r.geo(S["tri_left"])
    return (left.StartPoint + left.EndPoint) * 0.5 + V(-6, 4, 0)


def dims_done():
    r.end_tool()
    sketch = r.sk()
    side = r.geo(S["tri_left"])
    guide = r.geo(S["guides"][0])
    h.check(
        "D: 3 between the left side and the left guide",
        near(b.off_line(guide, side.StartPoint), 3.0),
        b.off_line(guide, side.StartPoint),
    )
    side = r.geo(S["tri_right"])
    guide = r.geo(S["guides"][1])
    h.check(
        "D: 3 between the right side and the right guide",
        near(b.off_line(guide, side.StartPoint), 3.0),
        b.off_line(guide, side.StartPoint),
    )
    top = r.geo(S["tri_top"]).StartPoint.y
    edge = r.geo(top_edge()).StartPoint.y
    h.check("D: 6 between the two top lines", near(edge - top, 6.0), (edge, top))
    h.check("the sketch is fully defined", r.dof() == 0, r.dof())
    st.sketch_ok("Triangle")
    S["n"] = len(sketch.Geometry)
    si.menu_item("CREATE", "Circular Pattern")


# -- 7 Circular Pattern -------------------------------------------------------------------
def pattern_double():
    h.check("Circular Pattern runs", st.tool_title() == "Circular Pattern", st.tool_title())
    x.double_click(px(_on(S["tri_left"], 0.4)))
    h.settle()


def pattern_centre():
    t = st.tool()
    got = sorted(t.objects) if t is not None else None
    h.check("Pattern: the double-click took the whole triangle", got == sorted(S["tri"]), got)
    if t is not None and t.field != "center":
        b.panel_click(PATTERN, "Fission180PatternCenter")
    r.click(V(0, 0, 0), towards=V(-0.6, -1.0, 0))


def pattern_quantity():
    t = st.tool()
    centre = t.center
    at = r.sk().getPoint(*centre) if centre and centre[0] >= 0 else V(0, 0, 0)
    h.check("Pattern: the origin is the centre", centre is not None and at.Length < 1e-6, centre)
    b.panel_type(PATTERN, "Fission180PatternQuantity", "6", enter=False)


def pattern_ok():
    b.panel_click(PATTERN, "Fission180PatternOK")


def pattern_made():
    sketch = r.sk()
    made = [
        i
        for i in range(S["n"], len(sketch.Geometry))
        if sketch.Geometry[i].TypeId == "Part::GeomLineSegment" and not sketch.getConstruction(i)
    ]
    h.check("Pattern: 5 copies of the triangle (15 lines)", len(made) == 15, len(made))
    h.check(
        "Pattern: the sketch is still fully defined (the report: 25 DoF)", r.dof() == 0, r.dof()
    )
    st.sketch_ok("Pattern")
    h.shot("pattern")
    S["n"] = len(sketch.Geometry)
    h.press("c")


# -- 8 the hole: a circle, Coincident twice, D 3.5 ----------------------------------------
def hole_target():
    """Where the left guide meets the triangle's top line (extended)."""
    y = r.geo(S["tri_top"]).StartPoint.y
    return V(-y / ROOT3, y, 0)


def circle_centre():
    # zoomed in where the hole goes (at the whole hexagon's zoom the grid is 10 mm and Snap
    # puts both clicks of a small circle on one grid crossing), clear of the lines there
    r.look_at(r.g(hole_target()), 30.0)
    r.click(hole_target() + V(3.0, 1.0, 0))


def circle_rim():
    r.click(hole_target() + V(5.0, 1.0, 0))


def circle_made():
    r.end_tool()
    sketch = r.sk()
    circles = [
        i
        for i in range(S["n"], len(sketch.Geometry))
        if sketch.Geometry[i].TypeId == "Part::GeomCircle"
    ]
    h.check("Circle: one circle", len(circles) == 1, circles)
    S["circle"] = circles[0]
    b.mark()
    b.menu("Coincident")


def coin_centre_1():
    r.click(r.geo(S["circle"]).Center)


def coin_guide():
    r.click(_on(S["guides"][0], 0.35))


def coin_centre_2():
    centre = r.geo(S["circle"]).Center
    h.check(
        "Coincident: the centre is on the left guide",
        b.off_line(r.geo(S["guides"][0]), centre) < 1e-6,
        centre,
    )
    h.check(
        "Coincident: ...a point on the line, not its midpoint (Symmetric)",
        not any(c[0] == "Symmetric" for c in b.new_cons()),
        b.new_cons(),
    )
    r.click(centre)


def coin_top():
    r.click(_on(S["tri_top"], 0.25))  # (its middle is on the Y axis)


def coin_done():
    centre = r.geo(S["circle"]).Center
    target = hole_target()
    h.check(
        "Coincident: the centre is where the guide meets the top line",
        (centre - target).Length < 1e-6,
        (centre, target),
    )
    r.end_tool()
    h.press("d")


def circle_dim_pick():
    r.look_at(r.g(r.geo(S["circle"]).Center), 30.0)  # (still zoomed in on the hole)
    c = r.geo(S["circle"])
    r.click(c.Center + V(c.Radius * 0.7071, c.Radius * 0.7071, 0))


def circle_dim_place():
    r.click(r.geo(S["circle"]).Center + V(3, 3, 0))


def circle_dim_type():
    h.check("D circle: the value box is open", r.editor() is not None)
    r.type_value("3.5")


def circle_done():
    r.end_tool()
    r.look_at(r.g(V(0, 0, 0)), 140.0)
    radius = r.geo(S["circle"]).Radius
    h.check("the hole is 3.5 across", near(radius, 1.75), radius)
    h.check("still fully defined", r.dof() == 0, r.dof())
    tl.click_eye("Origin")


# -- 9 Mirror ------------------------------------------------------------------------------
def mirror_widget(name):
    return b.in_panel(MIRROR, name)


def mirror_open():
    S["n"] = len(r.sk().Geometry)
    si.menu_item("CREATE", "Mirror")


def mirror_objects():
    h.check("Mirror runs", st.tool_title() == "Mirror", st.tool_title())
    c = r.geo(S["circle"])
    r.click(c.Center + V(-c.Radius, 0, 0))


def mirror_line_box():
    b.panel_click(MIRROR, "Fission180MirrorLine")


def mirror_line_y():
    h.wait_for(
        lambda: st.tool() is not None and st.tool().field == "line",
        "Mirror Line to be the active box",
    )
    r.click(V(0, -30, 0))  # the Y axis


def mirror_ok():
    b.panel_click(MIRROR, "Fission180MirrorOK")


def mirrored_once():
    sketch = r.sk()
    circles = [
        i
        for i, g in enumerate(sketch.Geometry)
        if g.TypeId == "Part::GeomCircle" and not sketch.getConstruction(i)
    ]
    h.check("Mirror: two holes", len(circles) == 2, circles)
    S["circles"] = circles
    si.menu_item("CREATE", "Mirror")


def mirror2_objects():
    for i in S["circles"]:
        c = r.geo(i)
        r.click(c.Center + V(0, c.Radius, 0))


def mirror2_line_box():
    t = st.tool()
    h.check(
        "Mirror: both holes are the Objects", t is not None and len(t.objects) == 2, t and t.objects
    )
    b.panel_click(MIRROR, "Fission180MirrorLine")


def mirror2_line_x():
    h.wait_for(
        lambda: st.tool() is not None and st.tool().field == "line",
        "Mirror Line to be the active box",
    )
    r.click(V(-62, 0, 0))  # the X axis, past the hexagon


def mirrored_twice():
    sketch = r.sk()
    circles = [
        i
        for i, g in enumerate(sketch.Geometry)
        if g.TypeId == "Part::GeomCircle" and not sketch.getConstruction(i)
    ]
    h.check("Mirror: four holes", len(circles) == 4, circles)
    h.check("still fully defined", r.dof() == 0, r.dof())
    st.sketch_ok("Mirror")
    h.shot("frame-sketch")
    S["frame_sketch"] = r.sk()
    h.ribbon("Finish Sketch")


mirrored_twice.done = lambda: h.in_sketch() is None
mirrored_twice.done_what = "the sketch is finished"


# -- 10 E: the frame, 6 mm ------------------------------------------------------------------
def extrude_panel():
    from fission180 import extrude_ui

    p = extrude_ui.ExtrudePanel.last
    return p if p is not None and not p._closed else None


def frame_e():
    h.click_empty()
    h.fit()
    r.key("e")


frame_e.done = lambda: extrude_panel() is not None
frame_e.done_what = "the Extrude dialog is open"


def frame_area():
    p = extrude_panel()
    if not p.profiles:  # (the rim between the hexagon's top and the triangle's)
        h.click(S["frame_sketch"].getGlobalPlacement().multVec(V(0, 40.3, 0)))


frame_area.done = lambda: extrude_panel() is not None and len(extrude_panel().profiles) >= 1
frame_area.done_what = "the frame's area is picked"


def frame_distance():
    p = extrude_panel()
    h.check("E: one area, the frame's", len(p.profiles) == 1, p.profiles)
    ui.type_into(p.distance.widget, "6")
    h.caught_up(p)


def frame_ok():
    p = extrude_panel()
    h.check("E: a New Body", p.operation.currentText() == "New Body", p.operation.currentText())
    h.task_button("OK")


frame_ok.done = lambda: extrude_panel() is None
frame_ok.done_what = "OK finished the frame"


def frame_made():
    made = r.bodies()
    h.check("E: one body", len(made) == 1, len(made))
    shape = made[0].Shape
    h.check("E: the report's 18,376 mm3", abs(shape.Volume - 18376.109) < 0.01, shape.Volume)
    box = shape.BoundBox
    h.check("E: 100 across, 6 thick", near(box.XLength, 100.0) and near(box.ZLength, 6.0), box)
    h.fit()
    h.shot("frame")
    r.checkpoint("tens_frame")


# -- 11 Appearance: double-click the default look, move its colour -------------------------
def look_open():
    h.click_empty()
    r.key("a")


look_open.done = lambda: k.panel() is not None
look_open.done_what = "the Appearance dialog is open"


def look_edit():
    labels = k.design_labels()
    h.check("Appearance: In This Design shows the default look", len(labels) >= 1, labels)
    S["default_look"] = labels[0]
    k.double_click_design(labels[0])


look_edit.done = lambda: k.editor() is not None
look_edit.done_what = "the look's editor is open"


def tip_colour():
    cols = k.shown_colors(r.bodies()[0].Tip)
    return cols[0] if cols else None


def look_colour():
    S["before_colour"] = tip_colour()
    e = k.editor()
    w.click(e.wheel, e.wheel.point_for(0.6, 0.8))  # a blue, as moving the colour does


def look_ok():
    h.check(
        "Appearance: the frame follows the colour at once",
        not k.same(tip_colour(), S["before_colour"]),
    )
    w.click(k.editor().ok_button)


look_ok.done = lambda: k.editor() is None
look_ok.done_what = "the editor is closed"


def look_close():
    h.task_button("OK")


look_close.done = lambda: k.panel() is None
look_close.done_what = "the Appearance dialog is closed"


# -- 12 the arm: a sketch on the Front plane --------------------------------------------------
def L(x, z):
    """A point of the Front plane (global x, z) in the open sketch's coordinates."""
    p = r.local(V(x, 0, z))
    return V(p.x, p.y, 0)


def arm_sketch():
    h.click_empty()
    h.fit()
    h.ribbon("Create Sketch")


def arm_plane():
    pl.click_square("XZ_Plane")


arm_plane.done = lambda: h.in_sketch() is not None
arm_plane.done_what = "the sketch on the Front plane is open"


def arm_project():
    sketch = r.note_sketch()
    S["arm"] = sketch
    normal = sketch.getGlobalPlacement().Rotation.multVec(V(0, 0, 1))
    h.check("Arm: the sketch lies on the Front plane", abs(abs(normal.y) - 1.0) < 1e-6, normal)
    S["external"] = len(sketch.ExternalGeo)
    h.press("p")


def arm_front_face():
    # the frame's face towards the front (the hexagon's bottom edge, at y = -43.3)
    h.click(V(0, -50 * ROOT3 / 2, 3))


def arm_projected():
    sketch = r.sk()
    made = len(sketch.ExternalGeo) - S["external"]
    h.check("Arm: the front face is projected (its outline, purple)", made >= 4, made)
    r.end_tool()
    S["n"] = len(sketch.Geometry)
    r.look_at(V(18, 0, 40), 100.0)
    h.press("l")


def arm_lines():
    for gx, gz in ((4, 6), (40, 75), (30, 75), (30, 70), (-4, 6)):
        xclick(L(gx, gz))


def arm_bottom():
    sketch = r.sk()
    made = list(range(S["n"], len(sketch.Geometry)))
    h.check(
        "Arm: four lines; the chain ended on the projected edge (Fusion)",
        len(made) == 4 and st.tool_title() is None or len(made) == 4,
        (len(made), st.tool_title()),
    )
    r.end_tool()
    first = r.geo(S["n"]).StartPoint
    last = r.geo(S["n"] + 3).EndPoint
    h.press("l")
    xclick(last)
    xclick(first)


def arm_drawn():
    r.end_tool()
    sketch = r.sk()
    made = list(range(S["n"], len(sketch.Geometry)))
    h.check("Arm: five lines", len(made) == 5, len(made))
    S["arm_lines"] = made

    # which is which, by where they lie (global)
    def gm(i):
        return r.g(r.mid(i))

    S["top"] = max(made, key=lambda i: gm(i).z)
    S["base"] = min(made, key=lambda i: gm(i).z)
    rest = [i for i in made if i not in (S["top"], S["base"])]
    S["drop"] = min(rest, key=lambda i: abs(r.g(r.geo(i).StartPoint).x - r.g(r.geo(i).EndPoint).x))
    leaning = sorted([i for i in rest if i != S["drop"]], key=lambda i: gm(i).x)
    S["lean_left"], S["lean_right"] = leaning
    h.shot("arm-drawn")
    b.menu("Parallel")


def arm_parallel():
    r.click(_on(S["lean_right"], 0.5))
    r.click(_on(S["lean_left"], 0.5))


def arm_parallel_done():
    h.check(
        "Arm: the leaning lines are parallel",
        b.has("Parallel", S["lean_right"], S["lean_left"])
        or b.has("Parallel", S["lean_left"], S["lean_right"]),
        b.cons()[-2:],
    )
    r.end_tool()
    h.press("d")


def arm_dim_steps():
    steps = []
    steps += dimension_steps(
        "lean",
        lambda: _on(S["lean_right"], 0.6),
        lambda: _on(S["lean_left"], 0.6),
        lambda: _on(S["lean_right"], 0.6) + (L(10, 0) - L(0, 0)),
        "6",
    )
    steps += dimension_steps1(
        "top", lambda: _on(S["top"], 0.5), lambda: _on(S["top"], 0.5) + (L(0, 8) - L(0, 0)), "10"
    )
    steps += dimension_steps1(
        "drop", lambda: _on(S["drop"], 0.5), lambda: _on(S["drop"], 0.5) - (L(8, 0) - L(0, 0)), "6"
    )
    steps += dimension_steps(
        "height",
        lambda: _on(S["top"], 0.3),
        lambda: L(0, 0),  # the origin
        lambda: L(-30, 40) + (L(0, 0) - L(0, 0)),
        "75",
    )
    return steps


def dimension_steps1(name, first, place, value):
    def pick():
        r.click(first())

    def put():
        r.click(place())

    def typed():
        h.check("D %s: the value box is open" % name, r.editor() is not None)
        r.type_value(value)

    steps = [pick, put, typed]
    for fn in steps:
        fn.__name__ = "d_%s_%s" % (name, fn.__name__)
    return steps


def arm_base_pick():
    r.click(_on(S["base"], 0.5))


def arm_base_place():
    r.click(_on(S["base"], 0.5) - (L(0, 8) - L(0, 0)))


def arm_base_driven():
    sketch = r.sk()
    c = sketch.Constraints[-1]
    h.check(
        "Arm: a 5th dimension on the bottom is driven, (6.8) (Fusion shows it so too)",
        not c.Driving and near(c.Value, 6.8, 1e-4),
        (c.Type, c.Value, c.Driving),
    )
    r.end_tool()
    S["n"] = len(sketch.Geometry)
    si.menu_item("CREATE", "Point")


def arm_point():
    r.click(_on(S["base"], 0.5))


def arm_point_made():
    r.end_tool()
    sketch = r.sk()
    points = [
        i
        for i in range(S["n"], len(sketch.Geometry))
        if sketch.Geometry[i].TypeId == "Part::GeomPoint"
    ]
    h.check("Point: one point", len(points) == 1, points)
    S["point"] = points[0]
    on_mid = [c for c in sketch.Constraints if c.Type == "Symmetric" and c.Third == points[0]]
    h.check("Point: it snapped to the bottom line's midpoint", len(on_mid) == 1, b.cons()[-3:])
    b.forget_said()
    b.menu("Horizontal/Vertical")


def arm_hv_point():
    p = r.geo(S["point"])
    r.click(V(p.X, p.Y, 0))


def arm_hv_origin():
    r.click(V(0, 0, 0))


def arm_defined():
    r.end_tool()
    p = r.g(V(r.geo(S["point"]).X, r.geo(S["point"]).Y, 0))
    h.check(
        "H/V: the point is straight above the origin (Vertical)", abs(p.x) < 1e-6, (p, b.said())
    )
    h.check("Arm: fully defined", r.dof() == 0, r.dof())
    top = r.g(r.mid(S["top"]))
    h.check("Arm: its top 75 high", near(top.z, 75.0), top)
    st.sketch_ok("Arm")
    h.shot("arm-sketch")
    h.ribbon("Finish Sketch")


arm_defined.done = lambda: h.in_sketch() is None
arm_defined.done_what = "the sketch is finished"


def arm_e():
    S["frame"] = r.volume()
    h.click_empty()
    h.fit()
    r.key("e")


arm_e.done = lambda: extrude_panel() is not None
arm_e.done_what = "the Extrude dialog is open"


def arm_area():
    p = extrude_panel()
    if not p.profiles:
        h.click(V(20, 0, 40))
    h.caught_up(p)


arm_area.done = lambda: extrude_panel() is not None and len(extrude_panel().profiles) == 1
arm_area.done_what = "the arm's area is picked"


def arm_symmetric():
    p = extrude_panel()
    h.check("E: the arm's sketch is the profile", p.profiles[0][0] is S["arm"], p.profiles)
    ui.choose(p.direction, "Symmetric")
    h.caught_up(p)


def arm_whole():
    ui.choose(extrude_panel().measurement, "Whole Length")
    h.caught_up(extrude_panel())


def arm_distance():
    p = extrude_panel()
    ui.type_into(p.distance.widget, "6")
    h.caught_up(p)


def arm_ok():
    p = extrude_panel()
    h.check(
        "E: Join by itself (it stands on the frame)",
        p.operation.currentText() == "Join",
        p.operation.currentText(),
    )
    h.task_button("OK")


arm_ok.done = lambda: extrude_panel() is None
arm_ok.done_what = "OK finished the arm"


def arm_made():
    made = r.bodies()
    shape = made[0].Shape
    h.check("E: one body", len(made) == 1, len(made))
    grown = shape.Volume - S["frame"]
    h.check("E: the arm joined: 2872.8 mm3 more", abs(grown - 2872.8) < 0.1, grown)
    box = shape.BoundBox
    h.check("E: 75 high, the arm 6 thick", near(box.ZMax, 75.0) and shape.isValid(), box)
    S["v0"] = shape.Volume
    h.fit()
    h.shot("arm")
    r.checkpoint("tens_arm")


# -- 13 MODIFY > Chamfer on the arm's inner corner, 20 mm -------------------------------------
SIN = 15.0 / 17.0
GUSSET = 0.5 * 20.0 * 20.0 * SIN * 6.0  # the 20 mm triangle x the arm's 6 mm


def chamfer_open():
    h.click_empty()
    h.fit()
    si.menu_item("MODIFY", "Chamfer")


chamfer_open.done = lambda: b2.blend_panel() is not None
chamfer_open.done_what = "the Chamfer dialog is open"


def chamfer_corner():
    # where the arm's leaning side meets the frame (the Origin's planes, shown for the
    # holes' Mirror, are drawn over it: the click goes through them)
    h.click(V(3.4, 0, 6))


def chamfer_20():
    p = b2.blend_panel()
    h.check("Chamfer: the inner corner's edge is picked", len(p.refs) == 1, p.refs)
    b2.type_into(p.distance.widget, "20")


chamfer_20.timeout_s = 120


def chamfer_ok():
    p = b2.blend_panel()
    d = p._value(p._row_key(), "distance")
    note = p.limit_label.text() if p.limit_label.isVisible() else ""
    h.check("Chamfer: 20 mm taken (the report: 'limited to 1.79 mm')", abs(d - 20.0) < 1e-9, d)
    h.check("Chamfer: nothing says it does not fit", note == "" and not p.error, (note, p.error))
    h.task_button("OK")


chamfer_ok.done = lambda: b2.blend_panel() is None
chamfer_ok.done_what = "OK finished the chamfer"
chamfer_ok.timeout_s = 120


def chamfer_made():
    added = r.volume() - S["v0"]
    h.check("Chamfer: the 20 mm bevel fills the corner", abs(added - GUSSET) < 1e-3, added)
    S["v1"] = r.volume()
    h.fit()
    h.shot("chamfer-20")


# -- 14 H: a 3.5 mm hole through the arm's top ---------------------------------------------
def hole_open():
    h.click_empty()
    r.key("h")


hole_open.done = lambda: hs.hole_panel() is not None
hole_open.done_what = "the Hole dialog is open"


def hole_face():
    r.look_at(V(35, 0, 75), 40.0)
    h.click(V(35.2, 0.0, 75))  # the middle of the arm's flat top


def hole_options():
    p = hs.hole_panel()
    h.check(
        "Hole: the arm's top is the face",
        p.target is not None,
        hs.message(p) if hasattr(hs, "message") else p.target,
    )
    ui.choose(p.extent, "All")
    hs.type_into(p.diameter.widget, "3.5")
    h.caught_up(p)


def hole_ok():
    p = hs.hole_panel()
    texts = [b.text() for b in p.value_boxes.boxes.values()] if hasattr(p, "value_boxes") else []
    h.check(
        "Hole: no position shown in micrometres (the report: '-55.00 um')",
        not any("µm" in t or " um" in t for t in texts),
        texts,
    )
    h.shot("hole")
    h.task_button("OK")


hole_ok.done = lambda: hs.hole_panel() is None
hole_ok.done_what = "OK finished the hole"


def hole_made():
    removed = S["v1"] - r.volume()
    # All: through the arm's top (about 9.4 mm of it) and on through the frame's spoke
    # below (6 mm): about 148 mm3
    h.check("Hole: a 3.5 mm hole through the arm's top", 120.0 < removed < 170.0, removed)
    shape = r.bodies()[0].Shape
    walls = [
        f
        for f in shape.Faces
        if f.Surface.TypeId == "Part::GeomCylinder" and near(f.Surface.Radius, 1.75)
    ]
    h.check("Hole: its wall is a cylinder of 3.5", len(walls) >= 1, len(walls))
    S["v2"] = r.volume()
    h.click_empty()
    h.fit()


# -- 15 a window round the whole part, Chamfer 0.5 ----------------------------------------------
def window_all():
    from Fission180Tests.gui import selection_input as sel

    box = r.bodies()[0].Shape.BoundBox
    corners = [
        V(xx, yy, zz)
        for xx in (box.XMin, box.XMax)
        for yy in (box.YMin, box.YMax)
        for zz in (box.ZMin, box.ZMax)
    ]
    sel.box_around(corners, margin=20)


def window_picked():
    from fission180 import selection_ui

    picked = sum(len(o.SubElementNames) for o in Gui.Selection.getSelectionEx())
    S["picked"] = picked
    edges = len(r.bodies()[0].Shape.Edges)
    h.check("Select Through is on, as in Fusion", selection_ui.select_through())
    h.check(
        "Window: every edge of the part is picked (Select Through)",
        picked >= edges,
        (picked, edges),
    )
    si.menu_item("MODIFY", "Chamfer")


window_picked.timeout_s = 300


def all_half():
    p = b2.blend_panel()
    h.check("Chamfer: the window's pick went into the dialog", p is not None and p.refs, p)
    b2.type_into(p.distance.widget, "0.5")


all_half.timeout_s = 300


def all_ok():
    p = b2.blend_panel()
    d = p._value(p._row_key(), "distance")
    note = p.limit_label.text() if p.limit_label.isVisible() else ""
    h.check("Chamfer: 0.5 mm taken", abs(d - 0.5) < 1e-9, d)
    h.check(
        "Chamfer: nothing says it does not fit (the report: 'too big here')",
        note == "" and not p.error,
        (note, p.error),
    )
    h.task_button("OK")


all_ok.done = lambda: b2.blend_panel() is None
all_ok.done_what = "OK finished the chamfer"
all_ok.timeout_s = 300


def all_made():
    shape = r.bodies()[0].Shape
    removed = S["v2"] - shape.Volume
    h.check("Chamfer: every edge bevelled 0.5 mm", 150.0 < removed < 400.0, removed)
    h.check("Chamfer: one valid solid", shape.isValid() and len(shape.Solids) == 1)
    h.check("nothing in error", not r.errors(), r.errors())
    h.fit()
    h.shot("finished-tower")


# -- 16 the browser: right-click the body > Save As Mesh ---------------------------------------
def mesh_dialog():
    from fission180 import export_ui

    d = export_ui.SaveAsMeshDialog.last
    try:
        return d if d is not None and d.isVisible() else None
    except RuntimeError:
        return None


def save_as_mesh():
    tl.row_menu(r.bodies()[0].Label, "Save As Mesh")


save_as_mesh.done = lambda: mesh_dialog() is not None
save_as_mesh.done_what = "the Save As Mesh dialog is open"


def mesh_look():
    d = mesh_dialog()
    h.check("Save As Mesh: its own dialog", d.windowTitle() == "Save As Mesh", d.windowTitle())
    h.check("Save As Mesh: Send to 3D Print Utility is there", d.send_box.isVisible())
    cancel = d.findChild(QtWidgets.QDialogButtonBox).button(QtWidgets.QDialogButtonBox.Cancel)
    w.click(cancel)


mesh_look.done = lambda: mesh_dialog() is None
mesh_look.done_what = "the dialog is closed"


STEPS = [home, new_design, create_sketch, pick_top, polygon, polygon_centre, polygon_edge]
STEPS += [polygon_made, hv_top, hv_done, d_left, d_right, d_place, d_type, d_done]
STEPS += [guides_x, guide_1, guide_2, guide_3, guides_made]
STEPS += [triangle_mode, triangle_points, triangle_close, triangle_made, equal_left]
STEPS += [equal_right, equal_done, parallel_left, parallel_guide, parallel_right]
STEPS += [parallel_right_guide, parallel_refused]
STEPS += dimension_steps(
    "left", lambda: _on(S["tri_left"], 0.5), lambda: _on(S["guides"][0], 0.55), gap_left, "3"
)
STEPS += dimension_steps(
    "right",
    lambda: _on(S["tri_right"], 0.5),
    lambda: _on(S["guides"][1], 0.45),
    lambda: _on(S["tri_right"], 0.5) + V(6, 4, 0),
    "3",
)
STEPS += dimension_steps(
    "top",
    lambda: _on(S["tri_top"], 0.3),
    lambda: _on(top_edge(), 0.3),
    lambda: _on(S["tri_top"], 0.5) + V(0, 2, 0),
    "6",
)
STEPS += [dims_done, pattern_double, pattern_centre, pattern_quantity, pattern_ok]
STEPS += [pattern_made, circle_centre, circle_rim, circle_made, coin_centre_1, coin_guide]
STEPS += [coin_centre_2, coin_top, coin_done, circle_dim_pick, circle_dim_place]
STEPS += [circle_dim_type, circle_done, mirror_open, mirror_objects, mirror_line_box]
STEPS += [mirror_line_y, mirror_ok, mirrored_once, mirror2_objects, mirror2_line_box]
STEPS += [mirror2_line_x, mirror_ok, mirrored_twice]
STEPS += [frame_e, frame_area, frame_distance, frame_ok, frame_made]
STEPS += [look_open, look_edit, look_colour, look_ok, look_close]
STEPS += [arm_sketch, arm_plane, arm_project, arm_front_face, arm_projected, arm_lines]
STEPS += [arm_bottom, arm_drawn, arm_parallel, arm_parallel_done] + arm_dim_steps()
STEPS += [arm_base_pick, arm_base_place, arm_base_driven, arm_point, arm_point_made]
STEPS += [arm_hv_point, arm_hv_origin, arm_defined]
STEPS += [arm_e, arm_area, arm_symmetric, arm_whole, arm_distance, arm_ok, arm_made]
STEPS += [chamfer_open, chamfer_corner, chamfer_20, chamfer_ok, chamfer_made]
STEPS += [hole_open, hole_face, hole_options, hole_ok, hole_made]
STEPS += [window_all, window_picked, all_half, all_ok, all_made, save_as_mesh, mesh_look]

h.run("replay_04_tensegrity", STEPS, paced_by="state")
