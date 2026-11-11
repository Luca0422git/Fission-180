# SPDX-License-Identifier: LGPL-2.1-or-later
"""The Pizza Cutter's Blade and its joint (replay_12_pizza_cutter; the book parity report,
lines 2102-2115). Kept outside scenarios/ because every file there is run as a scenario.

  New Component; a half profile on the Right plane (half the thickness, the bore, the flat
  and the bevel to a sharp edge); its last line a construction line (X); sketch Mirror
  (Objects + Mirror Line): the ends on the mirror line are joined, one closed profile
  (report: two points 0.002 apart, profile not closed); Revolve about Y: a disc 2.75 across,
  0.05 thick; the stainless look; Joint (J): the rim of the blade's bore and the round edge
  under the bolt's head, each by hovering the edge; Motion tab: Type Revolute, Animate;
  Position tab: Offset Z 0.005: the blade is centred on the bolt's 0.06 shoulder. Ctrl+S:
  the Save dialog (Name, Location), "Pizza Cutter"; Ctrl+S again: a version description.

The report gives 2.75, 0.05, the 0.005 offset and the 0.06 shoulder; the bore (it fits the
shoulder, 0.3125) and where the bevel starts (1.25 from the middle) are stand-ins.
"""

import math

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import book_joints_steps as bj
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import joints_steps as j
from Fission180Tests.gui import replay_12_bolt_steps as bolt
from Fission180Tests.gui import replay_12_bracket_steps as bracket
from Fission180Tests.gui import replay_12_handle_steps as handle
from Fission180Tests.gui import replay_12_inner2_steps as inner2
from Fission180Tests.gui import replay_12_inner_steps as inner
from Fission180Tests.gui import replay_e_steps as r
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st

V = App.Vector
IN = r.IN
S = r.S
PI = math.pi
NAME = "Blade"
BORE, FLAT_TO, EDGE, HALF = 0.15625, 1.25, 1.375, 0.025
VOLUME = PI * 2 * HALF * (FLAT_TO**2 - BORE**2) + 2 * PI * (
    FLAT_TO + (EDGE - FLAT_TO) / 3.0
) * (0.5 * 2 * HALF * (EDGE - FLAT_TO))
MIRROR = "Fission180MirrorPanel"
# the curves, in the order drawn
BOTTOM, SIDE, BEVEL, MIDDLE = 0, 1, 2, 3


def made():
    part = r.component(NAME)
    h.check("Blade stands at the top of the design", r.comps().container_of(part) is None)


def lines_done():
    r.stop_tool()
    lines = si.lines(r.sk()) + si.lines(r.sk(), construction=True)
    if not h.check("four lines drawn", len(lines) == 4, len(lines)):
        r.dump_sketch("blade lines")


def construction_select():
    Gui.Selection.clearSelection()
    r.xclick(r.geo_mid(MIDDLE, 0.5))


def construction_key():
    h.press("x")


def construction_done():
    sketch = r.sk()
    h.check("the middle line is a construction line (X)", bool(sketch.getConstruction(MIDDLE)))
    Gui.Selection.clearSelection()


def select_half():
    Gui.Selection.clearSelection()
    r.xclick(r.geo_mid(BOTTOM, 0.5))
    r.xclick(r.geo_mid(SIDE, 0.5), held=("ctrl",))
    r.xclick(r.geo_mid(BEVEL, 0.5), held=("ctrl",))
    h.check(
        "the half profile is selected (Ctrl)",
        len(handle.selected_edges()) == 3,
        handle.selected_edges(),
    )


def mirror_line_field():
    from Fission180Tests.gui import book_sketch_b_steps as b

    tool = st.tool()
    h.check(
        "Mirror runs with the three lines",
        tool is not None and len(tool.objects) == 3,
        tool and tool.objects,
    )
    b.panel_click(MIRROR, "Fission180MirrorLine")


def mirror_line_click():
    r.xclick(r.geo_mid(MIDDLE, 0.45))


def mirror_ok():
    from Fission180Tests.gui import book_sketch_b_steps as b

    button = b.in_panel(MIRROR, "Fission180MirrorOK")
    h.check(
        "the mirror line is picked: OK can be pressed", button is not None and button.isEnabled()
    )
    b.panel_click(MIRROR, "Fission180MirrorOK")


def mirrored():
    import Part

    r.stop_tool()
    sketch = r.sk()
    solid = [
        x
        for i, x in enumerate(sketch.Geometry)
        if x.TypeId == "Part::GeomLineSegment" and not sketch.getConstruction(i)
    ]
    h.check("six lines: the half and its mirror image", len(solid) == 6, len(solid))
    wires = [Part.Wire(group) for group in Part.sortEdges([x.toShape() for x in solid])]
    # (report: "the mirrored copy's end points ON the mirror line were not merged with the
    # originals (two points 0.002 in apart, profile not closed)")
    h.check(
        "the ends on the mirror line are joined: ONE closed outline",
        len(wires) == 1 and wires[0].isClosed(),
        [(len(w.Edges), w.isClosed()) for w in wires],
    )
    kinds = [c.Type for c in sketch.Constraints]
    h.check("Mirror added Symmetric constraints", "Symmetric" in kinds, kinds)


def sketch_done():
    r.dump_sketch("blade")
    r.fully_constrained(NAME)


def revolve_panel():
    p = r.panel()
    if not h.check("the Revolve dialog is open", p is not None):
        return
    h.check("the one profile is taken by itself", len(p.profiles) == 1, p.profiles)
    if p.axis is None:
        handle.click_path([NAME, "Origin", "Y"], "the Y axis row")
    h.caught_up(p)


def revolved():
    p = r.panel()
    h.check("the Y axis is the axis", p is not None and p.axis is not None, p and p.axis)


def blade_made():
    bodies = r.bodies_of(NAME)
    if not h.check("the blade is a body of its component", len(bodies) == 1, bodies):
        return
    got = r.vol_in3(NAME)
    h.check(
        "a disc 2.75 across, 0.05 thick, bevelled to its edge",
        r.near(got, VOLUME, 2e-5),
        (got, VOLUME),
    )
    r.box_is("about the origin", NAME, (-EDGE, -HALF, -EDGE, EDGE, HALF, EDGE))
    h.fit()


ON_BLADE = r.gp(-0.5, -HALF, 0.6)  # on the blade's front face, left of the handle


def look_drop():
    p = r.looks().panel()
    if not h.check("the Appearance dialog is open (A)", p is not None):
        return
    took = r.looks().drop_look("Stainless steel, brushed", ON_BLADE)
    h.check("the blade takes the swatch", took and p.message.text() == "", p.message.text())


def look_done():
    label = r.looks().body_look_label(r.body_of(NAME))
    h.check("the blade wears Stainless steel, brushed", label == "Stainless steel, brushed", label)


# -- Joint (J): Revolute, blade onto the bolt -----------------------------------------------------
def bore_rim():
    """A point on the rim of the blade's bore, on its front face, left of the End Cap."""
    return r.gp(-BORE * 0.7071, -HALF, BORE * 0.7071)


def under_head():
    """A point on the round edge under the bolt's head (where the shoulder starts), seen
    from the side, into the 0.06 gap between the head and the bracket's flat."""
    y = -bracket.FLAT - bolt.SHOULDER_T
    return r.gp(6.0 + bolt.SHOULDER_R * 0.98, y, bolt.SHOULDER_R * 0.2)


def joint_key():
    h.click_empty()
    h.fit()
    h.press("j")


joint_key.done = lambda: inner2.joint_panel() is not None
joint_key.done_what = "the Joint dialog is open"


def hover_blade():
    bj.hover_edge(bore_rim())


def click_blade():
    hot = bj.hot(inner2.joint_panel())
    h.check(
        "the bore's rim snaps to its centre",
        hot is not None and hot.get("kind") in ("circle", "centre"),
        hot and hot.get("kind"),
    )
    r.xclick_px(bj.edge_pixel(bore_rim()))
    # (hitch found by the replay: on its way to the bore the pointer crosses the End Cap's
    # rim, and the click on the blade then took the End Cap's centre)
    pick = inner2.joint_panel().picks["comp1"]
    h.check(
        "the click on the blade's bore takes the blade",
        pick is not None and pick.part.Label == NAME,
        pick and pick.part.Label,
    )


def hover_bolt():
    bj.hover_edge(under_head())


def click_bolt():
    hot = bj.hot(inner2.joint_panel())
    h.check(
        "the edge under the bolt's head snaps to its centre",
        hot is not None and hot.get("kind") in ("circle", "centre"),
        hot and hot.get("kind"),
    )
    r.xclick_px(bj.edge_pixel(under_head()))


def motion_tab():
    p = inner2.joint_panel()
    picked = [getattr(p.picks[k], "part", None) for k in ("comp1", "comp2")]
    labels = [x.Label if x is not None else None for x in picked]
    h.check("the blade, then the bolt", labels == [NAME, "Shoulder Bolt"], labels)
    j.click_tab(p, "Motion")


def type_revolute():
    p = inner2.joint_panel()
    j.choose_type(p, "Revolute")
    h.caught_up(p)


def blade_place():
    return bj.place(r.component(NAME))


def animate():
    p = inner2.joint_panel()
    h.check("Type Revolute", p.type_box.currentText() == "Revolute", p.type_box.currentText())
    S["blade_still"] = blade_place()
    r.click_widget(p.animate)


animate.done = lambda: j.playing()
animate.done_what = "the joint's animation plays"
animate.while_busy = True


def animating():
    # the book's play button: the blade turns on the bolt until it is pressed again
    start = S["blade_still"]
    h.wait_for(lambda: bj.moved(blade_place(), start), "the blade to turn")
    h.check("Animate turns the blade", True)
    r.click_widget(inner2.joint_panel().animate)


animating.while_busy = True
animating.done = lambda: not j.playing()
animating.done_what = "the animation stopped"


def position_tab():
    h.check(
        "the blade is back where the joint holds it",
        not bj.moved(blade_place(), S["blade_still"]),
        (blade_place(), S["blade_still"]),
    )
    j.click_tab(inner2.joint_panel(), "Position")


def offset_z():
    p = inner2.joint_panel()
    r.type_field(p.offset_fields["z"].widget, "0.005")
    h.caught_up(p)


def joined():
    from fission180 import joints

    r.no_dialog("Joint")
    kinds = inner2.joints_now()
    h.check("Revolute 1 is made", ("Revolute 1", "Revolute") in kinds, kinds)
    box = r.box_in(NAME)
    head_face = -bracket.FLAT - bolt.SHOULDER_T
    h.check(
        "the blade turns about the bolt (X 6.00, Z 0)",
        r.near((box[0] + box[3]) / 2.0, 6.0, 1e-4) and r.near((box[2] + box[5]) / 2.0, 0.0, 1e-4),
        box,
    )
    # Offset Z 0.005: centred on the 0.06 shoulder, between the head and the bracket's flat
    h.check(
        "Offset Z 0.005: the blade is centred on the bolt's 0.06 shoulder",
        r.near(box[1], head_face + 0.005, 2e-4) and r.near(box[4], -bracket.FLAT - 0.005, 2e-4),
        (box[1], box[4], head_face + 0.005, -bracket.FLAT - 0.005),
    )
    h.check("the joints are satisfied", joints.solve(r.doc()) == 0)
    h.check(
        "nothing lost, nothing broken",
        not joints.lost_joints(r.doc()) and not joints.broken_joints(r.doc()),
    )
    h.fit()
    h.shot("pizza-cutter")


# -- Ctrl+S ---------------------------------------------------------------------------------------
def ctrl_s():
    h.press(QtCore.Qt.Key_S, QtCore.Qt.ControlModifier)


def steps():
    out = [inner.activate_design] + r.new_component(NAME) + [made]
    out += r.create_sketch("YZ_Plane", "blade")
    out += [r.sketch_view(3.2, (0.2, 0.75), "blade_view")]
    # Line: from the bore out along the bottom (half the thickness), up the flat side, the
    # bevel back to the middle at the edge, and the middle line down to the start
    out += [r.key("l", "blade_line"), r.draw_at(0.0, BORE, "blade_l1")]
    out += [r.draw_at(HALF, BORE, "blade_l2"), r.draw_at(HALF, FLAT_TO, "blade_l3")]
    out += [r.draw_at(0.0, EDGE, "blade_l4"), r.click_geo_point(BOTTOM, 1, "blade_l5")]
    out += [lines_done, construction_select, construction_key, construction_done]
    out += [r.named("blade_select_half", select_half)]
    out += [r.menu("CREATE", "Mirror", "blade_mirror"), mirror_line_field, mirror_line_click]
    out += [mirror_ok, mirrored]
    out += r.dimension(
        [r.on(BOTTOM)],
        (0.3, 0.05),
        "0.025",
        "blade_half_thick",
        lambda sk: r.near(sk.Geometry[BOTTOM].length() / IN, HALF),
    )
    out += r.dimension(
        [(0.0, 0.0), r.at(BOTTOM, 1)],
        (-0.35, 0.08),
        "0.15625",
        "blade_bore",
        lambda sk: r.near(sk.getPoint(BOTTOM, 1).y / IN, BORE),
    )
    out += r.dimension(
        [(0.0, 0.0), r.at(BEVEL, 2)],
        (-0.6, 0.7),
        "1.375",
        "blade_edge",
        lambda sk: r.near(sk.getPoint(BEVEL, 2).y / IN, EDGE),
    )
    out += r.dimension(
        [r.on(SIDE)],
        (0.5, 0.7),
        "1.09375",
        "blade_flat",
        lambda sk: r.near(sk.Geometry[SIDE].length() / IN, FLAT_TO - BORE),
    )
    out += [sketch_done, r.finish_sketch("blade_finish")]
    out += [r.named("blade_revolve", r.revolve_open), revolve_panel, revolved]
    out += [r.ok("blade_revolve_ok"), blade_made]
    out += [r.named("blade_appearance", r.appearance_open), look_drop]
    out += [r.ok("blade_look_ok"), look_done]
    out += [joint_key, hover_blade, click_blade]
    out += [r.view_from(1, 0.05, 0.2, "blade_from_side"), r.zoom_on(under_head, 1.2, "blade_zoom")]
    out += [hover_bolt, click_bolt, motion_tab, type_revolute, animate, animating]
    out += [position_tab, offset_z, r.ok("blade_joint_ok"), joined]
    return out
