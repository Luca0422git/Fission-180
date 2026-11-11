# SPDX-License-Identifier: LGPL-2.1-or-later
"""The book replay, project 12: the Pizza Cutter (Mastering Autodesk Fusion, 2nd ed.,
pp 144-155; the book parity report, lines 1960-2144). Built the way the book writes it, in
one design, in the book's order, by real input only, with a person's defaults.
"""

import math

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import replay_12_bolt_steps as bolt
from Fission180Tests.gui import replay_12_bracket_steps as bracket
from Fission180Tests.gui import replay_12_handle_steps as handle
from Fission180Tests.gui import replay_12_inner2_steps as inner2
from Fission180Tests.gui import replay_12_inner_steps as inner
from Fission180Tests.gui import replay_e_steps as r
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import timeline_input as ti

V = App.Vector
IN = r.IN
S = r.S
PI = math.pi


# == the design, in inches ========================================================================
def new_design():
    r.user_defaults()
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("PizzaCutter")
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


def units_check():
    from fission180 import browser_ui, design_units

    h.check("the design is in inches", design_units.length_unit(r.doc()) == "in")
    h.check("the browser says Units: in", browser_ui.units(r.doc()) == "in")
    r.no_dialog("Change Active Units")


new_component = r.new_component
create_sketch = r.create_sketch
at, on, g, inch = r.at, r.on, r.g, r.inch
blend, thread_panel, looks = r.blend, r.thread_panel, r.looks
revolve_open, appearance_open, chamfer_ring = r.revolve_open, r.appearance_open, r.chamfer_ring


# == End Cap =====================================================================================
def cap_grounded():
    from fission180 import joints

    h.check(
        "the first component is grounded by itself (Fusion's default)",
        joints.is_grounded(r.component("End Cap")),
    )


# the curves of the End Cap's sketch, in the order drawn
RIM, SHANK, END, AXIS, DOME = 0, 1, 2, 3, 4


def cap_lines_done():
    r.stop_tool()
    lines = si.lines(r.sk())
    if not h.check("End Cap: four lines drawn", len(lines) == 4, len(lines)):
        r.dump_sketch("cap lines")


def cap_arc_done():
    r.stop_tool()
    arcs = [x for x in r.sk().Geometry if x.TypeId == "Part::GeomArcOfCircle"]
    if not h.check("End Cap: one arc drawn", len(arcs) == 1, len(arcs)):
        r.dump_sketch("cap arc")


def cap_coincident_centre():
    h.check("Coincident runs and waits for clicks", r.st.tool_title() == "Coincident")
    r.xclick(r.geo_point(DOME, 3))


def cap_coincident_line():
    r.xclick(r.geo_mid(AXIS, 0.6))


def cap_coincident_done():
    r.stop_tool()
    c = g(DOME).Center
    if not h.check("the arc's centre is on the bottom line", abs(c.y) < 1e-6, (c.x, c.y)):
        r.dump_sketch("cap coincident")
    # ...which makes the arc tangent to the vertical axis at the origin, as the book says
    h.check(
        "the arc leaves the origin straight up (tangent to the Z axis)",
        abs(g(DOME).Radius - abs(c.x)) < 1e-6,
        (g(DOME).Radius, c.x),
    )


def cap_centerline_select():
    r.xclick(r.geo_mid(AXIS, 0.6))


def cap_centerline():
    si.palette_click("Fission180PaletteCenterline")


def cap_centerline_done():
    from fission180 import sketch_centerline

    lines = sketch_centerline.lines(r.sk())
    h.check("the bottom line is a centerline", lines == [AXIS], lines)
    Gui.Selection.clearSelection()


def cap_sketch_done():
    r.dump_sketch("cap")
    r.fully_constrained("End Cap")
    h.shot("cap-sketch")


def cap_revolve_panel():
    p = r.panel()
    if not h.check("the Revolve dialog is open", p is not None):
        return
    h.check("the one profile is taken by itself", len(p.profiles) == 1, p.profiles)
    axis = p.axis
    h.check(
        "the centerline is the axis by itself (Fusion)",
        axis is not None and axis[1].startswith("Edge"),
        axis and (axis[0].Name, axis[1]),
    )
    h.caught_up(p)


CAP_VOLUME = PI * (0.25**2 * (3 * 0.625 - 0.25) / 3.0 + 0.125**2 * 0.5)


def cap_revolved():
    h.check("End Cap: one body", len(r.bodies_of("End Cap")) == 1, r.bodies_of("End Cap"))
    got = r.vol_in3("End Cap")
    h.check("End Cap: the dome and the shank", r.near(got, CAP_VOLUME, 2e-5), (got, CAP_VOLUME))
    r.box_is("End Cap: 0.75 long, 1.00 across", "End Cap", (0, -0.5, -0.5, 0.75, 0.5, 0.5))
    h.fit()


CAP_END_EDGE = r.gp(0.75, -0.125 * 0.7071, 0.125 * 0.7071)
CAP_SHANK = r.gp(0.55, -0.125 * 0.7071, 0.125 * 0.7071)


def cap_chamfer_edge():
    h.click_edge(CAP_END_EDGE)


def cap_chamfer_size():
    p = blend()
    if not h.check("Chamfer has the shank's end edge", p is not None and len(p.refs) == 1, p):
        return
    tip = p.distance.widget.toolTip()
    h.check("the value box's tooltip names inches (report: it said mm)", "(mm)" not in tip, tip)
    r.type_field(p.distance.widget, "0.02")
    h.caught_up(p)


def cap_chamfered():
    got = r.vol_in3("End Cap")
    want = CAP_VOLUME - chamfer_ring(0.125, 0.02)
    h.check("End Cap: the 0.02 chamfer on the shank's end", r.near(got, want, 2e-6), (got, want))
    S["cap_chamfered"] = got


def cap_thread_face():
    h.fit()
    r.xclick(CAP_SHANK)


def cap_thread_offered():
    from Fission180Tests.gui import hole_steps

    p = thread_panel()
    if not h.check("a thread is offered", p is not None and p.target is not None, p):
        return
    print(
        "[Fission 180] replay thread: %s | %s | %s"
        % (p.standard.currentText(), p.designation.currentText(), p.info.text()),
        flush=True,
    )
    h.check(
        "an inch design offers ANSI Unified Screw Threads (report: ISO)",
        p.standard.currentData() != "iso",
        p.standard.currentText(),
    )
    h.check(
        "1/4-20 UNC is offered for the 0.25 shank",
        p.designation.currentText().startswith("1/4-20"),
        p.designation.currentText(),
    )
    h.check("the read-out is in inches (report: mm)", " mm" not in p.info.text(), p.info.text())
    hole_steps.click_checkbox(p.modeled)
    h.caught_up(p)


def cap_threaded():
    got = r.vol_in3("End Cap")
    h.check("the thread is cut into the shank", got < S["cap_chamfered"] - 1e-4, got)
    S["cap_thread_last"] = got
    titles = r.timeline()
    h.check("Chamfer 1, then Thread 1", titles[-2:] == ["Chamfer 1", "Thread 1"], titles)
    r.all_ok("End Cap, thread after chamfer")


def cap_drag_thread():
    h.check("dragged", ti.drag_step("Thread 1", before_title="Chamfer 1"))


cap_drag_thread.timeout_s = 120


def cap_thread_first():
    titles = r.timeline()
    h.check(
        "the book's drag: Thread 1 before Chamfer 1",
        titles[-2:] == ["Thread 1", "Chamfer 1"],
        titles,
    )
    r.all_ok("End Cap, thread before chamfer")
    h.check("no refusal shown", ti.tl().refusal() == "", ti.tl().refusal())
    got = r.vol_in3("End Cap")
    h.check(
        "the thread runs into the chamfer (more is cut than before the drag)",
        got < S["cap_thread_last"] - 1e-6,
        (got, S["cap_thread_last"]),
    )
    shape = r.shape_of("End Cap")
    h.check("a valid solid", shape.isValid() and len(shape.Solids) == 1)
    h.shot("cap-threaded")


def cap_look():
    p = looks().panel()
    if not h.check("the Appearance dialog is open (A)", p is not None):
        return
    # dropped on the head's flat back face, where the shank leaves it
    took = looks().drop_look("Stainless steel, brushed", r.gp(0.25, -0.2, 0.3))
    h.check("the 3D view takes the swatch", took, p.message.text())
    h.check("the dialog has no complaint", p.message.text() == "", p.message.text())
    h.shot("cap-look")


def cap_look_done():
    label = looks().body_look_label(r.body_of("End Cap"))
    h.check("End Cap wears Stainless steel, brushed", label == "Stainless steel, brushed", label)


def cap_menu():
    # (Create Selection Set, which the report also missed here, is not built: Fission 180
    # has no selection sets; the book does not use one in this chapter)
    entries = [text for text, _on in ti.row_menu_entries("End Cap")]
    for wanted in ("Move/Copy", "Create Drawing"):
        h.check(
            "the component's menu has %s (report: missing)" % wanted, wanted in entries, entries
        )


cap = [new_design, units_row, units_inch, units_check]
cap += new_component("End Cap") + [cap_grounded]
cap += create_sketch("XZ_Plane", "cap")
cap += [r.sketch_view(2.0, (0.4, 0.2), "cap_view")]
# the book: Line, from the rim down to the shank, along it, down to the axis and back
cap += [
    r.key("l", "cap_line"),
    r.draw_at(0.25, 0.5, "cap_l1"),
    r.draw_at(0.25, 0.125, "cap_l2"),
    r.draw_at(0.75, 0.125, "cap_l3"),
    r.draw_at(0.75, 0.0, "cap_l4"),
    r.draw_at(0.0, 0.0, "cap_l5"),
    cap_lines_done,
]
# CREATE > Arc > 3-Point Arc: from the origin to the rim, a point between
cap += [
    r.menu("CREATE", "3-Point Arc", "cap_arc"),
    r.draw_at(0.0, 0.0, "cap_a1"),
    r.draw_at(0.25, 0.5, "cap_a2"),
    r.draw_at(0.06, 0.25, "cap_a3"),
    cap_arc_done,
]
# Coincident: the arc's centre onto the bottom line
cap += [
    r.menu("CONSTRAINTS", "Coincident", "cap_coincident"),
    cap_coincident_centre,
    cap_coincident_line,
    cap_coincident_done,
]
# the bottom line is the centerline: dimensions to it are diameters
cap += [cap_centerline_select, cap_centerline, cap_centerline_done]
cap += r.dimension(
    [at(RIM, 1), on(AXIS, 0.6)],
    (-0.2, 0.3),
    "1",
    "cap_dia_head",
    lambda sk: r.near(inch(sk.getPoint(RIM, 1).y), 0.5),
)
cap += r.dimension(
    [on(SHANK), on(AXIS, 0.3)],
    (1.0, 0.06),
    "0.25",
    "cap_dia_shank",
    lambda sk: r.near(inch(sk.getPoint(SHANK, 1).y), 0.125),
)
# (report: this one made a grey driven 0: both clicks were taken as points on the origin)
cap += r.dimension(
    [(0.0, 0.0), at(RIM, 1)],
    (0.12, 0.7),
    "0.25",
    "cap_head_thick",
    lambda sk: r.near(inch(sk.getPoint(RIM, 1).x), 0.25),
)
cap += r.dimension(
    [on(SHANK)],
    (0.5, 0.25),
    "0.5",
    "cap_shank_long",
    lambda sk: r.near(inch(sk.Geometry[SHANK].length()), 0.5),
)
cap += [cap_sketch_done, r.finish_sketch("cap_finish")]
cap += [revolve_open, cap_revolve_panel, r.ok("cap_revolve_ok"), cap_revolved]
cap += [
    r.named("cap_chamfer", lambda: h.ribbon("Chamfer")),
    cap_chamfer_edge,
    cap_chamfer_size,
    r.ok("cap_chamfer_ok"),
    cap_chamfered,
]
cap += [
    r.menu("CREATE", "Thread", "cap_thread"),
    cap_thread_face,
    cap_thread_offered,
    r.ok("cap_thread_ok", 120),
    cap_threaded,
    cap_drag_thread,
    cap_thread_first,
]
cap += [appearance_open, cap_look, r.ok("cap_look_ok"), cap_look_done, cap_menu]


def split(steps, at):
    """(before, from) the step called `at` (the parts of a section, for development)."""
    cut = [x.__name__ for x in steps].index(at)
    return steps[:cut], steps[cut:]


handle_a, handle_b = split(handle.steps(), "fillet_key")
SECTIONS = [("cap", cap), ("inner", inner.steps()), ("inner2", inner2.steps())]
SECTIONS += [("handle", handle_a), ("handle2", handle_b)]
bracket_a, bracket_b = split(bracket.steps(), "bracket_flat_create_sketch")
bracket_b, bracket_c = split(bracket_b, "bracket_home")
SECTIONS += [("bracket", bracket_a), ("bracket2", bracket_b), ("bracket3", bracket_c)]
bolt_a, bolt_b = split(bolt.steps(), "slot_sketch")
bolt_b, bolt_c = split(bolt_b, "exit_isolate")
SECTIONS += [("bolt", bolt_a), ("bolt2", bolt_b), ("bolt3", bolt_c)]

h.run("replay_12_pizza_cutter", r.assemble(SECTIONS), paced_by="state")
