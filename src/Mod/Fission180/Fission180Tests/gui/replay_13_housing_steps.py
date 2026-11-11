# SPDX-License-Identifier: LGPL-2.1-or-later
"""The Tesla Turbine's Stator Subassembly and its Housing & Inlet Tube (replay_13_tesla_turbine;
the book parity report, lines 2147-2195). Kept outside scenarios/ because every file there is
run as a scenario.

The report gives some of the book's sizes: the housing's diameter typed as "9 * 1.02", its
whole length 2.25, a 0.84 hole 4.17 up on the Right plane, a 0.25 fillet where the tube leaves
the housing, a 0.04 chamfer on the two flat faces, five 1/16 holes 1.25 deep at the tube's
end, pipe threads. The rest is a stand-in consistent with those (named at each step): the
bore 8.50 (a 0.34 wall), the inlet a rod 1.09 across from the middle out to 2.5, its
centerline 4.17 up; the 0.84 hole goes through the wall on the other side (an outlet). The
book's triangle in the first sketch (no size given) is left out.

  New design in inches (Set as Default in the Pizza Cutter: here once more, then a second
  new design opens in inches by itself). New Component "Stator Subassembly"; New Component
  "Housing & Inlet Tube" inside it (the active one is its parent). Front sketch: two
  circles, the outer typed "9 * 1.02" (kept as typed), a construction centerline 4.17 up,
  the inlet's rectangle. E: the two ring profiles, Symmetric, Whole Length 2.25. Right
  sketch: a 0.84 circle, Vertical to the origin, 4.17 up; E, All, Cut through the wall.
  Revolve the inlet profiles about the centerline, Join. Sketch 1 shown again, E: its inner
  circle, a Cut through all (Extrude no longer hides the shown sketch). Fillet 0.25 at the
  tube's junction. Chamfer 0.04 on the two flat faces. A sketch on the tube's end: a 1/16
  circle, sketch Rectangular Pattern Symmetric Quantity 5 (five circles, not nine); E: the
  five profiles, Cut 1.25. Thread on the tube: Thread Type ISO Pipe / NPT.
"""

import math

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets

from Fission180Tests.gui import component_steps as cs
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import replay_e_steps as r
from Fission180Tests.gui import timeline_input as ti

V = App.Vector
IN = r.IN
S = r.S
PI = math.pi
NAME = "Housing & Inlet Tube"
STATOR = "Stator Subassembly"
R_OUT, R_IN, CL = 9.0 * 1.02 / 2.0, 4.25, 4.17
ROD, ROD_END, WIDTH = 0.545, 2.5, 2.25


# -- units and the subassembly --------------------------------------------------------------------
def first_design():
    r.user_defaults()
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("Scratch")
    h.fit()


def units_row():
    ti.click_row("Units: mm")


def units_inch():
    from fission180 import browser_ui

    panel = browser_ui.UnitsPanel.last
    if not h.check("Change Active Units opens", panel is not None and not panel._closed):
        return
    r.choose(panel.form.findChild(QtWidgets.QComboBox, "Fission180UnitType"), "Inch")
    r.tick(panel.form.findChild(QtWidgets.QCheckBox, "Fission180UnitDefault"), True)
    h.task_button("OK")


def new_design():
    # (a person's File > New Design: Ctrl+N)
    from PySide import QtCore

    S["scratch"] = App.ActiveDocument.Name
    h.press(QtCore.Qt.Key_N, QtCore.Qt.ControlModifier)


new_design.done = lambda: App.ActiveDocument is not None and App.ActiveDocument.Name != S.get(
    "scratch"
)
new_design.done_what = "a new design is open"


def design_inch():
    from fission180 import design_units

    h.fit()
    # (report: "Default units stayed Inch (Set as Default from the Pizza Cutter worked)")
    h.check(
        "a new design opens in inches (Set as Default)",
        design_units.length_unit(r.doc()) == "in",
        design_units.length_unit(r.doc()),
    )


def stator_made():
    from fission180 import joints

    part = r.component(STATOR)
    h.check(
        "the Stator Subassembly is grounded by itself (the first component)",
        joints.is_grounded(part),
    )


def parent_shown():
    from Fission180Tests.gui import component_steps as cs

    p = cs.new_component_panel()
    if not h.check("New Component is open", p is not None):
        return
    # (report: "Parent defaults to the active one")
    h.check(
        "its Parent is the active Stator Subassembly",
        p.parent_box.currentText() == STATOR,
        p.parent_box.currentText(),
    )


def housing_made():
    part = r.component(NAME)
    holder = r.comps().container_of(part)
    h.check(
        "Housing & Inlet Tube is inside the Stator Subassembly",
        holder is not None and holder.Label == STATOR,
        holder and holder.Label,
    )


# -- Sketch 1 -------------------------------------------------------------------------------------
OUTER, INNER, AXIS = 0, 1, 2


def circles():
    return [x for x in r.sk().Geometry if x.TypeId == "Part::GeomCircle"]


def circle_done(count):
    def step():
        r.stop_tool()
        if not h.check("%d circle(s) drawn" % count, len(circles()) == count, len(circles())):
            r.dump_sketch("housing circles")

    step.__name__ = "housing_circle_%d_done" % count
    return step


def rim(index, degrees=-60.0):
    def spot():
        g = r.sk().Geometry[index]
        a = math.radians(degrees)
        local = g.Center + V(g.Radius * math.cos(a), g.Radius * math.sin(a), 0)
        return r.sk().getGlobalPlacement().multVec(local)

    return spot


def formula_kept():
    from fission180 import parameters, parameters_core

    found = {}
    for path, expr in parameters.expressions_of(r.sk()).items():
        if path.startswith(".Constraints["):
            found[int(path[len(".Constraints[") : -1])] = parameters_core.from_freecad(expr)
    # (report: "The expression is not kept (dimension stores 9.18; Fusion keeps 9.00 in * 1.02")
    h.check(
        "the outer diameter keeps the formula as typed",
        any("1.02" in text for text in found.values()),
        found,
    )


def axis_done():
    r.stop_tool()
    sketch = r.sk()
    lines = [i for i, x in enumerate(sketch.Geometry) if x.TypeId == "Part::GeomLineSegment"]
    if h.check("the centerline is drawn", len(lines) == 1, lines):
        S["axis"] = lines[0]


def axis_select():
    Gui.Selection.clearSelection()
    r.xclick(r.geo_mid(S["axis"], 0.7))


def axis_construction():
    h.check("the line is a construction line (X)", bool(r.sk().getConstruction(S["axis"])))
    Gui.Selection.clearSelection()


def rect_lines():
    sketch = r.sk()
    return [
        i
        for i, x in enumerate(sketch.Geometry)
        if x.TypeId == "Part::GeomLineSegment" and not sketch.getConstruction(i)
    ]


def rect_done():
    r.stop_tool()
    if not h.check("the inlet's rectangle is drawn", len(rect_lines()) == 4, rect_lines()):
        r.dump_sketch("housing rect")


def rect_side(want):
    """Index of the rectangle's "top" / "bottom" / "left" / "right" side."""
    sketch = r.sk()
    best, value = None, None
    for i in rect_lines():
        x = sketch.Geometry[i]
        mid = (x.StartPoint + x.EndPoint) * 0.5
        flat = abs(x.StartPoint.y - x.EndPoint.y) < abs(x.StartPoint.x - x.EndPoint.x)
        if (want in ("top", "bottom")) != flat:
            continue
        v = {"top": mid.y, "bottom": -mid.y, "left": -mid.x, "right": mid.x}[want]
        if best is None or v > value:
            best, value = i, v
    return best


def side(want, t=0.5):
    return lambda: r.geo_mid(rect_side(want), t)


def beside(want, du, dv):
    def spot():
        sketch = r.sk()
        x = sketch.Geometry[rect_side(want)]
        mid = (x.StartPoint + x.EndPoint) * 0.5 + V(du * IN, dv * IN, 0)
        return sketch.getGlobalPlacement().multVec(mid)

    return spot


def sketch1_done():
    r.dump_sketch("housing")
    r.fully_constrained("the housing's sketch")
    sketch = r.sk()
    radii = sorted(round(x.Radius / IN, 4) for x in circles())
    h.check("the circles: 8.50 and 9.18 across", radii == [R_IN, round(R_OUT, 4)], radii)
    top = sketch.Geometry[rect_side("top")]
    bottom = sketch.Geometry[rect_side("bottom")]
    h.check(
        "the inlet: from the centerline (4.17) to 4.715, out to 2.5",
        r.near(bottom.StartPoint.y / IN, CL)
        and r.near(top.StartPoint.y / IN, CL + ROD)
        and r.near(max(top.StartPoint.x, top.EndPoint.x) / IN, ROD_END),
        (bottom.StartPoint.y / IN, top.StartPoint.y / IN, top.StartPoint.x / IN),
    )
    S["sketch1"] = sketch.Name
    h.shot("housing-sketch")


# -- Extrude the ring -----------------------------------------------------------------------------
def extrude_key():
    Gui.Selection.clearSelection()
    h.fit()
    h.press("e")


extrude_key.done = lambda: r.panel() is not None
extrude_key.done_what = "the Extrude dialog is open"


def sketch_point(u, v):
    sketch = r.doc().getObject(S["sketch1"])
    return sketch.getGlobalPlacement().multVec(V(u * IN, v * IN, 0))


def ring_bottom():
    # (report: "my first profile clicks were ignored right after the dialog opened")
    r.xclick(sketch_point(0.0, -(R_IN + R_OUT) / 2.0))


def ring_top():
    # the piece of the ring the inlet's rectangle cuts off (above the centerline)
    v = (max(CL, math.sqrt(R_IN**2 - 1.0)) + math.sqrt(R_OUT**2 - 1.0)) / 2.0
    r.xclick(sketch_point(1.0, v))


def ring_taken():
    p = r.panel()
    h.check("both ring profiles are taken, the first click too", len(p.profiles) == 2, p.profiles)
    r.choose(p.direction, "Symmetric")


def ring_whole():
    p = r.panel()
    r.choose(p.measurement, "Whole Length")


def ring_distance():
    p = r.panel()
    r.type_field(p.distance.widget, "2.25")
    h.caught_up(p)


def ring_ready():
    p = r.panel()
    h.check(
        "a New Body (the component's first solid)",
        p.operation.currentText() == "New Body",
        p.operation.currentText(),
    )


RING = PI * (R_OUT**2 - R_IN**2) * WIDTH


def ring_made():
    got = r.vol_in3(NAME)
    h.check("the ring: 9.18 / 8.50, 2.25 wide", r.near(got, RING, 1e-4), (got, RING))
    r.box_is(
        "centred on the Front plane", NAME, (-R_OUT, -WIDTH / 2, -R_OUT, R_OUT, WIDTH / 2, R_OUT)
    )


# -- the 0.84 hole on the Right plane -------------------------------------------------------------
def hole_circle_done():
    r.stop_tool()
    if not h.check("a circle on the Right plane", len(circles()) == 1, len(circles())):
        r.dump_sketch("housing hole")


def level_centre():
    r.xclick(r.geo_point(0, 3))


def level_origin():
    r.sclick(0.0, 0.0)


def hole_sketch_done():
    r.stop_tool()
    r.dump_sketch("housing hole")
    r.fully_constrained("the 0.84 hole's sketch")
    c = circles()[0]
    h.check(
        "0.84 across, 4.17 up, above the origin",
        r.near(c.Radius / IN, 0.42)
        and r.near(abs(c.Center.x) / IN, 0.0)
        and r.near(abs(c.Center.y) / IN, CL),
        (c.Radius / IN, c.Center.x / IN, c.Center.y / IN),
    )


def cut_all():
    p = r.panel()
    h.check("the circle is taken", len(p.profiles) == 1, p.profiles)
    r.choose(p.extent, "All")
    h.caught_up(p)


def cut_side():
    p = r.panel()
    S["cut_operation"] = p.operation.currentText()
    h.check(
        "All into the housing is a Cut by itself", S["cut_operation"] == "Cut", S["cut_operation"]
    )


def hole_cut():
    got = r.vol_in3(NAME)
    h.check("the wall is cut through", got < RING - 1e-3, (got, RING))
    S["holed"] = got


# -- Revolve the inlet ----------------------------------------------------------------------------
def show_sketch1():
    ti.click_eye(r.doc().getObject(S["sketch1"]).Label)


def revolve_open():
    h.ribbon("Revolve")


revolve_open.done = lambda: r.panel() is not None
revolve_open.done_what = "the Revolve dialog is open"


def inlet_piece(k):
    """A step that clicks the k-th piece of the inlet's rectangle: in the bore, in the wall,
    outside the housing."""
    spots = [
        (0.3, (CL + math.sqrt(R_IN**2 - 0.3**2)) / 2.0),
        (1.0, (max(CL, math.sqrt(R_IN**2 - 1.0)) + math.sqrt(R_OUT**2 - 1.0)) / 2.0),
        (2.0, CL + ROD * 0.6),
    ]
    u, v = spots[k]
    return r.named("inlet_piece_%d" % (k + 1), lambda: r.xclick(sketch_point(u, v)))


def revolve_axis_box():
    p = r.panel()
    h.check("the three inlet profiles are taken", len(p.profiles) == 3, p.profiles)
    if p.axis is None:
        r.click_widget(p.fields["axis"].button)


def revolve_axis():
    p = r.panel()
    if p.axis is None:
        r.xclick(sketch_point(1.5 * ROD_END, CL))  # the construction line, beyond the inlet


def revolve_ready():
    p = r.panel()
    axis = p.axis
    h.check(
        "the axis is the construction line of Sketch 1",
        axis is not None and axis[0].Name == S["sketch1"],
        axis and axis[0].Name,
    )
    r.choose(p.operation, "Join")
    h.caught_up(p)


def revolved():
    got = r.vol_in3(NAME)
    h.check("the inlet is joined", got > S["holed"] + 1.0, (got, S["holed"]))
    shape = r.shape_of(NAME)
    h.check("one solid", len(shape.Solids) == 1, len(shape.Solids))
    S["revolved"] = got


# -- Sketch 1 shown again: its inner circle cut ---------------------------------------------------
def sketch1_visible():
    return r.doc().getObject(S["sketch1"]).ViewObject.Visibility


def show_again():
    if not sketch1_visible():
        ti.click_eye(r.doc().getObject(S["sketch1"]).Label)


def cut_key():
    h.check("Sketch 1 is shown", sketch1_visible())
    Gui.Selection.clearSelection()
    h.press("e")


cut_key.done = lambda: r.panel() is not None
cut_key.done_what = "the Extrude dialog is open"


def inner_click():
    # (report: "starting Extrude HIDES the shown (already used) sketch again")
    h.check("Extrude leaves the shown sketch shown", sketch1_visible())
    r.xclick(sketch_point(0.0, 0.0))


def inner_all():
    p = r.panel()
    h.check("the inner circle's profile is taken", len(p.profiles) == 1, p.profiles)
    r.choose(p.direction, "Symmetric")
    r.choose(p.extent, "All")
    h.caught_up(p)


def inner_ready():
    p = r.panel()
    if p.operation.currentText() != "Cut":
        r.choose(p.operation, "Cut")
    h.caught_up(p)


def inner_cut():
    got = r.vol_in3(NAME)
    h.check(
        "what the inlet put into the chamber is cut away",
        got < S["revolved"] - 0.05,
        (got, S["revolved"]),
    )
    S["housing"] = got
    r.all_ok("Housing, inlet")
    h.shot("housing")


# -- Fillet 0.25 where the inlet leaves the housing -----------------------------------------------
def fillet_key():
    Gui.Selection.clearSelection()
    h.fit()
    h.press("f")


fillet_key.done = lambda: r.blend() is not None
fillet_key.done_what = "the Fillet dialog is open"


def fillet_edge():
    import Part

    shape = r.shape_of(NAME)
    # the junction: the edges shared by the housing's outside and the inlet's outside
    found = []
    for i, e in enumerate(shape.Edges):
        faces = list(shape.ancestorsOfType(e, Part.Face))
        kinds = sorted(type(f.Surface).__name__ for f in faces)
        if kinds == ["Cylinder", "Cylinder"]:
            radii = sorted(round(f.Surface.Radius / IN, 3) for f in faces)
            if radii == [round(ROD, 3), round(R_OUT, 3)]:
                found.append(e)
    S["junction"] = len(found)
    if not h.check("the inlet meets the housing along a junction edge", bool(found), len(found)):
        return
    e = max(found, key=lambda x: x.Length)
    h.click_edge(e.valueAt((e.FirstParameter + e.LastParameter) * 0.5))


def fillet_size():
    p = r.blend()
    if not h.check("Fillet has the junction", p is not None and len(p.refs) >= 1, p and p.refs):
        return
    r.type_field(p.fields["radius"].widget, "0.25")
    h.caught_up(p)
    S["fillet_said"] = p.message.text()
    print("[Fission 180] replay tesla fillet: %s | %s" % (p.refs, S["fillet_said"]), flush=True)


def fillet_close():
    h.task_button("Cancel" if S.get("fillet_said") else "OK")


fillet_close.done = lambda: not Gui.Control.activeDialog()
fillet_close.done_what = "the Fillet dialog closed"
fillet_close.timeout_s = 120


def filleted():
    got = r.vol_in3(NAME)
    if S.get("fillet_said"):
        # KNOWN OPEN (book-modify-b): a round that runs out where two cylinders touch
        h.check(
            "known open: the junction round is refused with the reason",
            "too big" in S["fillet_said"]
            or "smoothly" in S["fillet_said"]
            or "cannot" in S["fillet_said"],
            S["fillet_said"],
        )
    else:
        h.check("the junction is rounded 0.25", got > S["housing"], (got, S["housing"]))
    S["housing"] = got


# -- Chamfer 0.04 on the two flat faces -----------------------------------------------------------
FRONT_FACE = r.gp(-0.3, -WIDTH / 2.0, -(R_IN + R_OUT) / 2.0)


def chamfer_open():
    Gui.Selection.clearSelection()
    h.ribbon("Chamfer")


chamfer_open.done = lambda: r.blend() is not None
chamfer_open.done_what = "the Chamfer dialog is open"


def chamfer_front():
    r.xclick(FRONT_FACE)


def chamfer_back():
    r.xclick(r.gp(-0.3, WIDTH / 2.0, -(R_IN + R_OUT) / 2.0))


def chamfer_size():
    p = r.blend()
    if not h.check("Chamfer has both flat faces", p is not None and len(p.refs) == 2, p and p.refs):
        return
    r.type_field(p.fields["distance"].widget, "0.04")
    h.caught_up(p)
    # (report: "1.016 mm is too big here (even without the tube edge). Not resolved.")
    h.check("0.04 is accepted on the flat faces", p.message.text() == "", p.message.text())


def chamfered():
    got = r.vol_in3(NAME)
    h.check(
        "the rims of the flat faces are chamfered", got < S["housing"] - 1e-3, (got, S["housing"])
    )
    r.all_ok("Housing, chamfer")
    S["housing"] = got


# -- five 1/16 holes at the tube's end ------------------------------------------------------------
END_FACE = r.gp(ROD_END, -0.2, CL + 0.25)


def end_sketch():
    Gui.Selection.clearSelection()
    h.ribbon("Create Sketch")


def end_face():
    r.xclick(END_FACE)


end_face.done = lambda: h.in_sketch() is not None
end_face.done_what = "the sketch on the tube's end is open"


def end_open():
    S["sk"] = h.in_sketch()
    plc = S["sk"].getGlobalPlacement()
    h.check(
        "the sketch lies on the tube's end",
        r.near(plc.Base.x / IN, ROD_END, 1e-6)
        or r.near(plc.multVec(V(0, 0, 0)).x / IN, ROD_END, 1e-6),
        plc,
    )


def pin_rim():
    return r.gp(ROD_END, 1.0 / 32.0, CL)


def pin_done():
    r.stop_tool()
    h.check("one circle", len(circles()) == 1, len(circles()))


def pattern_select():
    Gui.Selection.clearSelection()
    found = [k for k, x in enumerate(r.sk().Geometry) if x.TypeId == "Part::GeomCircle"]
    r.xclick(r.geo_mid(found[0], 0.6))


PANEL = "Fission180SketchPatternPanel"


def pattern_values():
    from Fission180Tests.gui import book_sketch_b_steps as b

    b.panel_choose(PANEL, "Fission180PatternDistanceType", "Spacing")


def pattern_symmetric():
    from Fission180Tests.gui import book_sketch_b_steps as b

    b.panel_choose(PANEL, "Fission180PatternDirectionType", "Symmetric")


def pattern_numbers():
    from Fission180Tests.gui import book_sketch_b_steps as b

    b.panel_type(PANEL, "Fission180PatternDistance", "0.125")
    b.panel_type(PANEL, "Fission180PatternQuantity", "5", enter=False)


def pattern_ok():
    from Fission180Tests.gui import book_sketch_b_steps as b

    b.panel_click(PANEL, "Fission180PatternOK")


def patterned():
    r.stop_tool()
    found = circles()
    # (report: "Quantity counts PER SIDE in Symmetric mode (Quantity 5 -> 9 circles)")
    h.check("Symmetric, Quantity 5: five circles in all", len(found) == 5, len(found))
    r.dump_sketch("tube end")


def holes_key():
    S["before_holes"] = r.vol_in3(NAME)
    Gui.Selection.clearSelection()
    h.press("e")


holes_key.done = lambda: r.panel() is not None
holes_key.done_what = "the Extrude dialog is open"


def hole_profile(k):
    def step():
        sketch = r.doc().getObject(S["end_sketch"])
        g = [x for x in sketch.Geometry if x.TypeId == "Part::GeomCircle"]
        g = sorted(g, key=lambda c: (c.Center.x, c.Center.y))[k]
        r.xclick(sketch.getGlobalPlacement().multVec(g.Center))

    step.__name__ = "tube_hole_profile_%d" % (k + 1)
    return step


def remember_end_sketch():
    S["end_sketch"] = r.sk().Name


def holes_depth():
    p = r.panel()
    # (report: "every click went to the body face behind ('Face23') or set To Object silently")
    h.check(
        "the five hole profiles are taken (not the face behind them)",
        len(p.profiles) == 5,
        p.profiles,
    )
    r.type_field(p.distance.widget, "-1.25")
    h.caught_up(p)
    h.check("into the tube: a Cut", p.operation.currentText() == "Cut", p.operation.currentText())


def holes_made():
    got = r.vol_in3(NAME)
    want = 5 * PI * (1.0 / 32.0) ** 2 * 1.25
    h.check(
        "five 1/16 holes, 1.25 deep",
        r.near(S["before_holes"] - got, want, 2e-4),
        (S["before_holes"] - got, want),
    )
    S["housing"] = got
    r.all_ok("Housing, holes")


# -- a pipe thread on the inlet -------------------------------------------------------------------
INLET_SIDE = r.gp(2.2, -ROD * 0.7071, CL + ROD * 0.7071)


def thread_face():
    r.xclick(INLET_SIDE)


def thread_types():
    p = r.thread_panel()
    if not h.check("a thread is offered on the inlet", p is not None and p.target is not None, p):
        return
    types = [p.standard.itemText(i) for i in range(p.standard.count())]
    # (report: "only ISO Metric profile and ANSI Unified Screw Threads: no ISO Pipe / NPT")
    h.check(
        "pipe threads are offered",
        "ISO Pipe Threads" in types and any("NPT" in x for x in types),
        types,
    )
    r.choose(p.standard, [x for x in types if "NPT" in x][0])
    h.caught_up(p)


def thread_pipe():
    p = r.thread_panel()
    print(
        "[Fission 180] replay tesla thread: %s %s | %s"
        % (p.standard.currentText(), p.designation.currentText(), p.info.text()),
        flush=True,
    )
    h.check(
        "an NPT size is offered for the 1.09 inlet",
        "NPT" in p.designation.currentText(),
        p.designation.currentText(),
    )


def threaded():
    titles = r.timeline()
    h.check("a Thread step", any(x.startswith("Thread") for x in titles), titles)
    r.all_ok("Housing, pipe thread")
    h.fit()
    h.shot("housing-done")


def steps():
    out = [first_design, units_row, units_inch]
    out += [new_design, design_inch]
    out += r.new_component(STATOR) + [stator_made]
    out += [
        r.menu(
            "ASSEMBLE",
            "New Component",
            "new_component_housing",
            lambda: cs.new_component_panel() is not None,
            "the New Component dialog is open",
        ),
        parent_shown,
    ]
    out += [r.named("name_housing", lambda: cs.type_name(NAME))]
    out += [r.ok("ok_housing"), housing_made]
    out += r.create_sketch("XZ_Plane", "housing")
    out += [r.sketch_view(11.0, (0.8, 0.5), "housing_view")]
    out += [r.key("c", "housing_c1"), r.draw_at(0.0, 0.0, "housing_c1_centre")]
    out += [r.draw_at(4.5, 0.0, "housing_c1_rim"), circle_done(1)]
    # the first dimension: "9 * 1.02" (it scales what is drawn: only this circle)
    out += r.dimension(
        [rim(OUTER)],
        (3.5, -3.5),
        "9 * 1.02",
        "housing_dia_out",
        lambda sk: r.near(sk.Geometry[OUTER].Radius / IN, R_OUT),
    )
    out += [formula_kept]
    out += [r.key("c", "housing_c2"), r.draw_at(0.0, 0.0, "housing_c2_centre")]
    out += [r.draw_at(4.0, 0.0, "housing_c2_rim"), circle_done(2)]
    out += r.dimension(
        [rim(INNER, -120)],
        (-2.5, -2.5),
        "8.5",
        "housing_dia_in",
        lambda sk: r.near(sk.Geometry[INNER].Radius / IN, R_IN),
    )
    out += [r.key("l", "housing_axis"), r.draw_at(0.0, 4.0, "housing_axis_1")]
    out += [r.draw_at(6.0, 4.0, "housing_axis_2"), axis_done]
    out += r.dimension(
        [(0.0, 0.0), lambda: r.geo_point(S["axis"], 1)],
        (-0.7, 2.0),
        "4.17",
        "housing_axis_up",
        lambda sk: r.near(sk.getPoint(S["axis"], 1).y / IN, CL),
    )
    out += r.dimension(
        [lambda: r.geo_mid(S["axis"], 0.8)],
        (5.0, 3.6),
        "6",
        "housing_axis_long",
        lambda sk: r.near(sk.Geometry[S["axis"]].length() / IN, 6.0),
    )
    out += [axis_select, r.key("x", "housing_construction"), axis_construction]
    out += [r.sketch_view(4.0, (1.4, 4.4), "housing_view_inlet")]
    out += [
        r.key("r", "housing_rectangle"),
        r.named("housing_r1", lambda: r.xclick(r.geo_point(S["axis"], 1))),
    ]
    out += [r.draw_at(2.5, 4.75, "housing_r2"), rect_done]
    out += r.dimension(
        [side("right")],
        beside("right", 0.3, 0.0),
        "0.545",
        "housing_rod",
        lambda sk: r.near(sk.Geometry[rect_side("right")].length() / IN, ROD),
    )
    out += r.dimension(
        [side("top", 0.8)],
        beside("top", 0.6, 0.3),
        "2.5",
        "housing_inlet_long",
        lambda sk: r.near(sk.Geometry[rect_side("top")].length() / IN, ROD_END),
    )
    out += [sketch1_done, r.finish_sketch("housing_finish")]
    out += [extrude_key, ring_bottom, ring_top, ring_taken, ring_whole, ring_distance]
    out += [ring_ready, r.ok("housing_extrude_ok"), ring_made]
    out += r.create_sketch("YZ_Plane", "housing_hole")
    out += [r.sketch_view(4.0, (0.0, 3.5), "housing_hole_view")]
    out += [r.key("c", "housing_hole_c"), r.draw_at(0.0, 4.0, "housing_hole_centre")]
    out += [r.draw_at(0.5, 4.0, "housing_hole_rim"), hole_circle_done]
    out += r.dimension(
        [rim(0, -45)],
        (1.0, 3.0),
        "0.84",
        "housing_hole_dia",
        lambda sk: r.near(sk.Geometry[0].Radius / IN, 0.42),
    )
    out += [r.sketch_view(9.0, (0.0, 2.0), "housing_hole_view_wide")]
    out += [r.menu("CONSTRAINTS", "Horizontal/Vertical", "housing_hole_vertical")]
    out += [level_centre, level_origin, r.named("housing_hole_level_done", r.stop_tool)]
    out += r.dimension(
        [(0.0, 0.0), lambda: r.geo_point(0, 3)],
        (-1.0, 2.0),
        "4.17",
        "housing_hole_up",
        lambda sk: r.near(abs(sk.Geometry[0].Center.y) / IN, CL),
    )
    out += [hole_sketch_done, r.finish_sketch("housing_hole_finish")]
    out += [extrude_key, cut_all, cut_side, r.ok("housing_cut_ok"), hole_cut]
    out += [show_sketch1, revolve_open, r.sketch_view(4.0, (1.2, 4.3), "housing_inlet_view")]
    out += [inlet_piece(0), inlet_piece(1), inlet_piece(2)]
    out += [revolve_axis_box, revolve_axis, revolve_ready, r.ok("housing_revolve_ok"), revolved]
    out += [show_again, cut_key, inner_click, inner_all, inner_ready]
    out += [r.ok("housing_inner_ok"), inner_cut]
    out += [fillet_key, fillet_edge, fillet_size, fillet_close, filleted]
    out += [r.view_from(0.3, -1, 0.2, "housing_from_front"), chamfer_open, chamfer_front]
    out += [r.view_from(0.3, 1, 0.2, "housing_from_back"), chamfer_back, chamfer_size]
    out += [r.ok("housing_chamfer_ok", 120), chamfered]
    out += [r.view_from(1, -0.6, 0.4, "housing_tube_end"), r.zoom_on(END_FACE, 2.0, "tube_zoom")]
    out += [end_sketch, end_face, end_open, remember_end_sketch]
    out += [
        r.key("c", "tube_pin"),
        r.named("tube_pin_centre", lambda: r.xclick(r.gp(ROD_END, 0, CL))),
    ]
    out += [r.named("tube_pin_rim", lambda: r.xclick(pin_rim())), pin_done]
    out += r.dimension(
        [lambda: pin_rim()],
        lambda: r.gp(ROD_END, 0.2, CL + 0.2),
        "1/16",
        "tube_pin_dia",
        lambda sk: r.near(circles()[0].Radius / IN, 1.0 / 32.0),
    )
    out += [pattern_select, r.menu("CREATE", "Rectangular Pattern", "tube_pattern")]
    out += [pattern_values, pattern_symmetric, pattern_numbers, pattern_ok, patterned]
    out += [r.finish_sketch("tube_end_finish")]
    out += [holes_key] + [hole_profile(k) for k in range(5)] + [holes_depth]
    out += [r.ok("tube_holes_ok", 120), holes_made]
    out += [r.iso_view("housing_home"), r.menu("CREATE", "Thread", "housing_thread")]
    out += [thread_face, thread_types, thread_pipe, r.ok("housing_thread_ok", 120), threaded]
    return out
