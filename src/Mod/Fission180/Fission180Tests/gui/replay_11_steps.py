# SPDX-License-Identifier: LGPL-2.1-or-later
"""The steps of replay_11_hot_end: the book's Project 11 "3D Printer Hot End" (Mastering
Autodesk Fusion, 2nd ed., pp 124-141) as the book parity report lists it (lines 1758-1947),
in one design (millimetres), by real input, with a user's defaults.

A part of the project, the steps where the report found hitches across components (see
docs/fission180/sessions/replay-d.md for what is not replayed). The parts are stand-ins
to the report's numbers (the book's figures and the CADclass STEP files are not here).

Kept outside scenarios/ because every file there is run as a scenario."""

import math

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import component_steps as cs
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import joints_steps as j
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import replay_d_steps as r
from Fission180Tests.gui import timeline_input as t

V = App.Vector
S = {}
FLATS, HEX_H = 5.95, 3.0  # report 1763: "5.95 across flats"
BORE_R, BORE_Z0 = 1.0, 1.0
PLANE_Z, BLOCK = 9.0, (20.0, 12.0, 10.0)  # report 1808: "Offset Plane 9 mm", "Extrude 10"
FLAT_W = 4.0


def mm(where):
    from fission180 import browser_ui

    d = r.doc()
    return h.check("%s: the design is in millimetres" % where, browser_ui.units(d) == "mm")


def _parts():
    from fission180 import components

    return components.list_components(r.doc())


def new_design():
    r.user_defaults()
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("HotEnd")
    h.fit()


def root_activate():
    r.click_radio(r.doc().Label)


root_activate.done = lambda: r.active_label() == ""
root_activate.done_what = "the design's row is active"


def component(name, key, first=False):
    def open_dialog():
        j.menu("New Component")

    open_dialog.done = lambda: cs.new_component_panel() is not None
    open_dialog.done_what = "the New Component dialog is open"

    def type_name():
        p = cs.new_component_panel()
        h.check("From Bodies is not ticked", not p.from_bodies.isChecked(), p.bodies_label.text())
        cs.type_name(name)
        r.ok()

    type_name.done = lambda: cs.new_component_panel() is None
    type_name.done_what = "the dialog closed"

    def made():
        h.check("%s is active" % name, r.active_label() == name, r.active_label())
        grounded = [p.Label for p in _parts() if r.grounded(p.Label)]
        # report 1762: "New Component (+ Ground by hand again)"
        want = ["0.4 mm Nozzle"]
        h.check("the first component is the grounded one", grounded == want, grounded)
        mm("New Component " + name)

    return ([] if first else [r.named(root_activate, key + "_root")]) + [
        r.named(open_dialog, key + "_component"),
        r.named(type_name, key + "_component_name"),
        r.named(made, key + "_component_made"),
    ]


def create_sketch():
    h.ribbon("Create Sketch")


def sketch_on(role):
    def step():
        pl.click_square(role)

    step.done = lambda: h.in_sketch() is not None
    step.done_what = "the sketch is open"
    return r.named(step, "sketch_on_" + role)


def in_component(name):
    def step():
        from fission180 import components

        sketch = r.sk()
        owner = components.container_of(components.body_of(sketch) or sketch)
        label = owner.Label if owner is not None else ""
        h.check("the sketch is in %s" % name, label == name, label)
        h.check("%s is still active" % name, r.active_label() == name, r.active_label())

    return r.named(step, "sketch_in_" + name.replace(" ", "_").replace(".", ""))


# == the Nozzle's hexagon (report 1762-1765) =====================================================
def hex_polygon():
    r.menu("CREATE", "Circumscribed Polygon")


def hex_centre():
    S["n"] = len(r.sk().Geometry)
    S["pitch"] = r.grid_pitch()
    r.click(V(0, 0, 0))


def hex_up():
    # report 1762: "click centre, click straight up: 6 sides with a horizontal top edge"
    r.click(V(0, 3 * S["pitch"], 0))
    r.esc_tool()


def _hex_lines():
    sketch = r.sk()
    return [
        (i, g)
        for i, g in enumerate(sketch.Geometry)
        if i >= S["n"] and g.TypeId == "Part::GeomLineSegment" and not sketch.getConstruction(i)
    ]


def _edge_circle():
    sketch = r.sk()
    circles = [
        (i, g)
        for i, g in enumerate(sketch.Geometry)
        if i >= S["n"] and g.TypeId == "Part::GeomCircle"
    ]
    lines = _hex_lines()
    if not lines or not circles:
        return None
    mid = lines[0][1].value(0.5 * (lines[0][1].FirstParameter + lines[0][1].LastParameter))
    # the circle that touches the edges: through the edges' middles
    return min(circles, key=lambda c: abs(c[1].Radius - mid.Length))


def hex_drawn():
    lines = _hex_lines()
    h.check("six sides", len(lines) == 6, len(lines))
    top = max(lines, key=lambda l: l[1].StartPoint.y + l[1].EndPoint.y)[1]
    h.check("the top edge is level", abs(top.StartPoint.y - top.EndPoint.y) < 1e-6, top)
    S["top"] = top


def hex_dim_flats():
    circle = _edge_circle()
    if not h.check("the circle that touches the edges", circle is not None):
        return
    _i, c = circle
    a = math.radians(30.0)  # towards a corner: inside the hexagon, on the circle only
    on = V(c.Radius * math.cos(a), c.Radius * math.sin(a), 0)
    place = V(1.6 * c.Radius, 1.4 * c.Radius, 0)
    r.dimension([on], place, "5.95")


def hex_level():
    lines = _hex_lines()
    top = max(lines, key=lambda l: l[1].StartPoint.y + l[1].EndPoint.y)[1]
    flats = 2 * top.value(0.5 * (top.FirstParameter + top.LastParameter)).y
    h.check("5.95 typed: 5.95 across the flats", abs(flats - FLATS) < 1e-6, flats)
    if r.dof() != 0:  # (the polygon can still turn about its centre)
        # report 1764: "Horizontal constraint; fully constrained"
        r.menu("CONSTRAINTS", "Horizontal/Vertical")
        mid = top.value(0.5 * (top.FirstParameter + top.LastParameter))
        r.click(V(mid.x + 0.3 * top.length(), mid.y, 0))
        r.esc_tool()


def hex_constrained():
    r.fully_constrained("the hexagon")
    h.shot("11-hex-sketch")


def press_e():
    h.click_empty()
    h.press("e")


def _extrude():
    from fission180 import extrude_ui

    p = extrude_ui.ExtrudePanel.last
    return p if p is not None and not p._closed else None


press_e.done = lambda: _extrude() is not None
press_e.done_what = "the Extrude dialog is open"


def hex_extrude():
    p = _extrude()
    # report 1765: "E did not pre-pick the only profile (Fusion picks it)"
    h.check("E takes the only profile by itself", len(p.profiles) == 1, p.profiles)
    r.type_field(p.distance.widget, "3")


def extrude_ok():
    r.ok()


extrude_ok.done = lambda: _extrude() is None
extrude_ok.done_what = "the Extrude dialog closed"


def _hex_area():
    a = FLATS / 2.0
    return 2.0 * math.sqrt(3.0) * a * a


def hex_made():
    S["v_hex"] = _hex_area() * HEX_H
    r.check_volume("the hexagon 3 high", "0.4 mm Nozzle", S["v_hex"], 1e-6)
    r.timeline_ok("the hexagon")
    mm("the hexagon")


# == the bore, revolved as a cut with the body hidden (report 1766-1779) ===========================
def hide_body():
    t.row_menu("Body1", "Hide")


def body_hidden():
    body = r.bodies_of("0.4 mm Nozzle")[0]
    h.check("the Nozzle's body is hidden", not t.shown(body))


def bore_polyline():
    p = r.grid_pitch()
    S["first"] = r.polyline([V(x * p, y * p, 0) for x, y in ((0, 1), (1, 1), (1, 3), (0, 3))])


def bore_dims():
    # the first dimension scales the drawing (one grid step is 1 mm then)
    line = S["first"]
    sketch = r.sk()
    r.dimension([r.mid(line)], r.mid(line) + V(0, -1.5 * S.get("pitch", 1.0), 0), "1")
    S["scaled"] = sketch.Geometry[line].length()


def bore_drawn():
    sketch = r.sk()
    pts = sorted(
        (round(g.StartPoint.x, 6), round(g.StartPoint.y, 6))
        for g in sketch.Geometry[S["first"] :]
        if g.TypeId == "Part::GeomLineSegment"
    )
    App.Console.PrintMessage("[Fission 180] replay: bore sketch %s\n" % (pts,))
    h.check("a 1 x 2 rectangle beside the axis", len(pts) == 4, pts)


def open_revolve():
    r.menu("CREATE", "Revolve")


def _revolve():
    from fission180 import revolve_ui

    p = revolve_ui.RevolvePanel.last
    return p if p is not None and not p._closed else None


open_revolve.done = lambda: _revolve() is not None
open_revolve.done_what = "the Revolve dialog is open"


def bore_axis():
    p = _revolve()
    # report 1774: "with the body hidden, as the book says: the shaded profiles cannot be
    # clicked at all (the sketch lives inside the hidden body)"
    h.check("the profile of the hidden body's sketch is taken", len(p.profiles) == 1, p.profiles)
    h.fit()
    h.click(V(0, 0, 5.0))  # the Z axis above the part


def bore_cut():
    p = _revolve()
    axis = p.axis
    h.check(
        "the Z axis", axis is not None and "Z_Axis" in str(getattr(axis[0], "Role", axis)), axis
    )
    if p.operation.currentText() != "Cut":
        h.check("Cut", r.choose(p.operation, "Cut"))


def bore_hidden_said():
    """The report (1774) follows the book: the body hidden, the bore revolved as a Cut.
    Fusion leaves hidden bodies out of what a cut acts on (Autodesk, Extrude reference:
    "Auto-Select re-computes the bodies to cut based on the current visibility state"), so
    the dialog says so and names the hidden body. Cancel, the body shown (right-click >
    Show), Revolve again: the cut goes through it."""
    p = _revolve()
    text = p.message.text()
    ok = "Hidden bodies are not cut" in text and "Body1" in text
    h.check("the dialog says hidden bodies are not cut, naming Body1", ok, text)
    h.task_button("Cancel")


bore_hidden_said.done = lambda: _revolve() is None
bore_hidden_said.done_what = "the Revolve dialog closed"


def show_body():
    t.row_menu("Body1", "Show")


def bore_again():
    p = _revolve()
    h.check("the profile is taken again", len(p.profiles) == 1, p.profiles)
    h.fit()
    h.click(V(0, 0, 5.0))


def bore_ok():
    p = _revolve()
    if p.operation.currentText() != "Cut":
        h.check("Cut", r.choose(p.operation, "Cut"))
    h.caught_up(p)
    h.check("shown, the body is cut: no message", not p.message.text(), p.message.text())
    removed = S["v_hex"] - r.volume_of("0.4 mm Nozzle")
    h.check("the preview cuts the bore", abs(removed - math.pi * 2.0) < 1e-6, removed)
    r.ok()


bore_ok.done = lambda: _revolve() is None
bore_ok.done_what = "the Revolve dialog closed"


def bore_made():
    removed = S["v_hex"] - r.volume_of("0.4 mm Nozzle")
    h.check("the bore is cut out of the hidden body", abs(removed - math.pi * 2.0) < 1e-6, removed)
    r.timeline_ok("Revolve")


def remember_sketch():
    S["bore_sketch"] = r.sk().Name


# == the Heater Block on an offset plane (report 1806-1811) ========================================
def plane_open():
    h.click_empty()
    r.menu("CONSTRUCT", "Offset Plane")


def _construct():
    from Fission180Tests.gui import inspect_steps as ins

    return ins.construct_panel()


plane_open.done = lambda: _construct() is not None
plane_open.done_what = "the Offset Plane dialog is open"


def plane_xy_row():
    # report 1808: "Offset Plane 9 mm from XY (plane picked in the browser)"
    pl.pick_in_browser("XY_Plane")


def plane_distance():
    p = _construct()
    if h.check("the XY plane is taken", p is not None and p.datum is not None):
        r.type_field(p.distance.widget, "9")


def plane_ok():
    r.ok()


plane_ok.done = lambda: _construct() is None
plane_ok.done_what = "the Offset Plane dialog closed"


def _plane():
    return [o for o in r.doc().Objects if o.TypeId == "PartDesign::Plane"][-1]


def plane_made():
    from fission180 import components

    plane = _plane()
    z = plane.getGlobalPlacement().Base.z
    h.check("9 mm above XY", abs(z - PLANE_Z) < 1e-6, z)
    owner = components.container_of(components.body_of(plane) or plane)
    h.check(
        "the plane is in the Heater Block",
        owner is not None and owner.Label == "Heater Block",
        owner,
    )
    t.click_eye("0.4 mm Nozzle")  # report 1809: "hide Nozzle"


def sketch_on_plane():
    plane = _plane()
    t.click_row(plane.Label)
    h.ribbon("Create Sketch")


sketch_on_plane.done = lambda: h.in_sketch() is not None
sketch_on_plane.done_what = "the sketch is open on the plane"


def block_polyline():
    from fission180 import components

    nozzle = r.part("0.4 mm Nozzle")
    h.check("the Nozzle is hidden (report 1809)", not t.shown(nozzle))
    _ = components
    p = r.grid_pitch()
    S["pitch"] = p
    pts = [(-10, -6), (10, -6), (10, 6), (-10, 6)]
    S["first"] = r.polyline([V(x * p, y * p, 0) for x, y in pts])


def block_dims():
    # the first dimension scales the drawing: 20 grid steps become 20 mm
    first = S["first"]
    line = r.sk().Geometry[first]
    at = line.value(line.FirstParameter + 0.3 * (line.LastParameter - line.FirstParameter))
    # (a quarter along: the line's middle is on the Y axis, which a click there takes)
    r.dimension([at], at + V(0, -3.0 * S["pitch"], 0), "20")
    h.fit(iso=False)


def block_dim_height():
    side = r.mid(S["first"] + 1)
    r.dimension([side], side + V(3.0, 0, 0), "12")


def block_drawn():
    sketch = r.sk()
    xs = sorted({round(g.StartPoint.x, 6) for g in sketch.Geometry[S["first"] :]})
    ys = sorted({round(g.StartPoint.y, 6) for g in sketch.Geometry[S["first"] :]})
    h.check("20 x 12 about the origin", xs == [-10.0, 10.0] and ys == [-6.0, 6.0], (xs, ys))


def block_extrude():
    p = _extrude()
    h.check("E takes the only profile by itself", len(p.profiles) == 1, p.profiles)
    r.type_field(p.distance.widget, "10")


def block_made():
    want = BLOCK[0] * BLOCK[1] * BLOCK[2]
    r.check_volume("the block 20 x 12 x 10", "Heater Block", want, 1e-6)
    r.check_box("on the plane, 9 to 19 high", "Heater Block", [-10, -6, 9, 10, 6, 19])
    r.check_volume(
        "the Nozzle is as it was", "0.4 mm Nozzle", _hex_area() * HEX_H - 2 * math.pi, 1e-6
    )
    r.timeline_ok("the block")


# == a flat cut To Object on the top face (report 1884-1899, "the cut does not go through any
# body") ===========================================================================================
def _top_face():
    shape = r.shape_of("Heater Block")
    return [f for f in shape.Faces if abs(f.CenterOfMass.z - 19.0) < 1e-6][0]


def sketch_on_top():
    h.ribbon("Create Sketch")


def top_face_click():
    h.fit()
    spot = r.seen_spot(_top_face())
    if h.check("the block's top face is in view", spot is not None):
        h.click(spot)


top_face_click.done = lambda: h.in_sketch() is not None
top_face_click.done_what = "the sketch is open on the top face"


def flat_rectangle():
    r.menu("CREATE", "Center Rectangle")


def flat_centre():
    S["n"] = len(r.sk().Geometry)
    # the middle of the block's right side, in the sketch's own coordinates
    loc = r.sk().getGlobalPlacement().inverse()
    S["c0"] = loc.multVec(V(10, 0, 19))
    S["c1"] = loc.multVec(V(12, 3, 19))
    r.click(S["c0"])


def flat_corner():
    r.click(S["c1"])
    r.esc_tool()


def flat_drawn():
    sketch = r.sk()
    S["flat_sketch"] = sketch.Name
    lines = [g for g in sketch.Geometry[S["n"] :] if g.TypeId == "Part::GeomLineSegment"]
    h.check("a rectangle", len(lines) >= 4, len(lines))


def flat_profile():
    """E: the rectangle's two halves (the block's top edge splits it) are taken, the
    rectangle the person just drew; the top face's own area is not."""
    p = _extrude()
    sketch = r.doc().getObject(S["flat_sketch"])
    halves = []
    for name, face in extrude_regions(sketch):
        box = face.BoundBox
        if box.XLength < 4.5 and box.YLength < 6.5:
            halves.append(name)
    picked = sorted(short for _o, short in p.profiles)
    App.Console.PrintMessage("[Fission 180] replay: E picked %s, halves %s\n" % (picked, halves))
    h.check("E takes the rectangle (its two halves)", picked == sorted(halves), (picked, halves))


def extrude_regions(sketch):
    from fission180 import extrude

    return extrude.regions(sketch)


def flat_to_object():
    p = _extrude()
    h.check("To Object", r.choose(p.extent, "To Object"))


def flat_underside():
    shape = r.shape_of("Heater Block")
    under = [f for f in shape.Faces if abs(f.CenterOfMass.z - 9.0) < 1e-6][0]
    r.cube_click("bottom") if "bottom" in r.cube_names() else r.orbit(0, -200)
    spot = r.seen_spot(under)
    if h.check("the block's underside is in view", spot is not None, r.looking()):
        h.click(spot)


def flat_cut():
    p = _extrude()
    obj = p.options.get("extent_object")
    App.Console.PrintMessage(
        "[Fission 180] replay: To Object: %s, operation %s, message %r\n"
        % (obj and (obj[0].Label, obj[1]), p.operation.currentText(), p.message.text())
    )
    # report 1885: "the dialog chose Join"; with half of the rectangle outside the block
    # Fusion's own choice is not documented: the book chooses Cut, as the report did
    if p.operation.currentText() != "Cut":
        h.check("Cut", r.choose(p.operation, "Cut"))


def flat_ok():
    p = _extrude()
    h.caught_up(p)
    # report 1886: "editing it to Cut ... said 'The cut does not go through any body'
    # though it obviously does"
    h.check(
        "Cut, and no message",
        p.operation.currentText() == "Cut" and not p.message.text(),
        (p.operation.currentText(), p.message.text()),
    )
    r.ok()


flat_ok.done = lambda: _extrude() is None
flat_ok.done_what = "the Extrude dialog closed"


def flat_made():
    sketch = r.doc().getObject(S["flat_sketch"])
    place = sketch.getGlobalPlacement()
    inner = 0.0
    for _name, face in extrude_regions(sketch):
        box = face.BoundBox
        if box.XLength < 4.5 and box.YLength < 6.5:
            centre = place.multVec(face.CenterOfMass)
            if abs(centre.x) < BLOCK[0] / 2.0:  # the half over the block
                inner += face.Area
    want = BLOCK[0] * BLOCK[1] * BLOCK[2] - inner * BLOCK[2]
    h.check("a flat 6 wide", inner > 1.0, inner)
    r.check_volume("the flat is cut through the block's whole height", "Heater Block", want, 1e-6)
    r.timeline_ok("the flat")
    r.cube_click("home")
    h.fit()
    h.shot("11-flat")


# == PTFE Tube: a sketch on another component's face keeps the active component (1919-1923) ======
def show_nozzle():
    t.click_eye("0.4 mm Nozzle")


def hide_heater():
    # the Nozzle's top is under the Heater Block: hidden to reach it
    t.click_eye("Heater Block")


def nozzle_top_click():
    h.fit()
    shape = r.shape_of("0.4 mm Nozzle")
    tops = [
        f
        for f in shape.Faces
        if abs(f.CenterOfMass.z - HEX_H) < 1e-6 and f.Surface.TypeId == "Part::GeomPlane"
    ]
    spot = r.seen_spot(tops[0]) if tops else None
    if h.check("the Nozzle's top face is in view", spot is not None):
        h.click(spot)


nozzle_top_click.done = lambda: h.in_sketch() is not None
nozzle_top_click.done_what = "the sketch is open on the Nozzle's top face"


def tube_circle():
    S["n"] = len(r.sk().Geometry)
    h.press("c")
    h.settle()
    loc = r.sk().getGlobalPlacement().inverse()
    r.click(loc.multVec(V(0, 0, HEX_H)))
    r.click(loc.multVec(V(2 * r.grid_pitch(), 0, HEX_H)))
    r.esc_tool()


def tube_extrude():
    p = _extrude()
    App.Console.PrintMessage("[Fission 180] replay: tube profiles %s\n" % (p.profiles,))
    r.type_field(p.distance.widget, "4")


def tube_new_body():
    p = _extrude()
    h.check(
        "New Body (PTFE Tube is empty)",
        p.operation.currentText() == "New Body",
        p.operation.currentText(),
    )


def tube_made():
    h.check(
        "PTFE Tube is still the active component", r.active_label() == "PTFE Tube", r.active_label()
    )
    h.check(
        "the tube's body is in PTFE Tube",
        len(r.bodies_of("PTFE Tube")) == 1,
        [b.Label for b in r.bodies_of("PTFE Tube")],
    )
    r.check_volume(
        "the Nozzle is as it was", "0.4 mm Nozzle", _hex_area() * HEX_H - 2 * math.pi, 1e-6
    )
    r.timeline_ok("the tube")
    mm("the end")
    h.shot("11-tube")


def steps():
    return r.stages(
        "replay_11",
        [
            (
                "nozzle",
                [new_design]
                + component("0.4 mm Nozzle", "nozzle", first=True)
                + [
                    create_sketch,
                    sketch_on("XY_Plane"),
                    in_component("0.4 mm Nozzle"),
                    hex_polygon,
                    hex_centre,
                    hex_up,
                    hex_drawn,
                    hex_dim_flats,
                    hex_level,
                    hex_constrained,
                    r.finish_sketch,
                    press_e,
                    hex_extrude,
                    extrude_ok,
                    hex_made,
                    hide_body,
                    body_hidden,
                    create_sketch,
                    sketch_on("XZ_Plane"),
                    remember_sketch,
                    bore_polyline,
                    bore_dims,
                    bore_drawn,
                    r.finish_sketch,
                    open_revolve,
                    bore_axis,
                    bore_cut,
                    bore_hidden_said,
                    show_body,
                    open_revolve,
                    bore_again,
                    bore_ok,
                    bore_made,
                ],
            ),
            (
                "heater",
                component("Heater Block", "heater")
                + [
                    plane_open,
                    plane_xy_row,
                    plane_distance,
                    plane_ok,
                    plane_made,
                    sketch_on_plane,
                    in_component("Heater Block"),
                    block_polyline,
                    block_dims,
                    block_dim_height,
                    block_drawn,
                    r.finish_sketch,
                    press_e,
                    block_extrude,
                    extrude_ok,
                    block_made,
                ],
            ),
            (
                "flat",
                [
                    sketch_on_top,
                    top_face_click,
                    in_component("Heater Block"),
                    flat_rectangle,
                    flat_centre,
                    flat_corner,
                    flat_drawn,
                    r.finish_sketch,
                    press_e,
                    flat_profile,
                    flat_to_object,
                    flat_underside,
                    flat_cut,
                    flat_ok,
                    flat_made,
                ],
            ),
            (
                "tube",
                component("PTFE Tube", "tube")
                + [
                    show_nozzle,
                    hide_heater,
                    create_sketch,
                    nozzle_top_click,
                    in_component("PTFE Tube"),
                    tube_circle,
                    r.finish_sketch,
                    press_e,
                    tube_extrude,
                    tube_new_body,
                    extrude_ok,
                    tube_made,
                ],
            ),
        ],
    )
