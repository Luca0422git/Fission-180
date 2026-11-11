# SPDX-License-Identifier: LGPL-2.1-or-later
"""The Pizza Cutter's Shoulder Bolt (replay_12_pizza_cutter; the book parity report, lines
2085-2100). Kept outside scenarios/ because every file there is run as a scenario.

  The Wheel Bracket isolated again, then New Component: the new one can be isolated straight
  from its own menu (report: only "Exit Isolate" was offered). A profile on the Right plane
  (head 0.5 x 0.2, shoulder 0.3125 x 0.06, shank 0.25 x 0.2; the axis a Centerline, so the
  book's diameters are diameters); Revolve; Chamfer and Thread on the shank, the Thread
  dragged before the Chamfer; a sketch on the head: Center Rectangle, Tangent to the
  projected rim, 0.08 wide; Extrude -0.16: a Cut by itself (the screwdriver slot); Chamfer
  0.01 on the head's round face; Exit Isolate; Move (M) with X 6 and Y -0.6 typed; Joint
  (J): the shoulder's round edge and the rim of the bracket's hole, each snapping to its
  centre by hovering the edge (report: "(corner)", never the centre; the bolt ended 0.015 in
  off the hole's axis).

The report gives the slot (0.08, -0.16), the 0.01 chamfer, the move and the 0.06 shoulder;
the other sizes of the bolt are stand-ins.
"""

import math

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import replay_12_bracket_steps as bracket
from Fission180Tests.gui import replay_12_inner2_steps as inner2
from Fission180Tests.gui import replay_12_inner_steps as inner
from Fission180Tests.gui import replay_e_steps as r
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import timeline_input as ti

V = App.Vector
IN = r.IN
S = r.S
PI = math.pi
NAME = "Shoulder Bolt"
HEAD_R, HEAD_T = 0.25, 0.2
SHOULDER_R, SHOULDER_T = 0.15625, 0.06
SHANK_R, SHANK_L = 0.125, 0.2
PLAIN = PI * (HEAD_R**2 * HEAD_T + SHOULDER_R**2 * SHOULDER_T + SHANK_R**2 * SHANK_L)
LONG = HEAD_T + SHOULDER_T + SHANK_L


def isolate_bracket():
    ti.row_menu("Wheel Bracket", "Isolate")


def made():
    part = r.component(NAME)
    h.check("Shoulder Bolt stands at the top of the design", r.comps().container_of(part) is None)
    entries = [text for text, _on in ti.row_menu_entries(NAME)]
    # (report: "New Component made while another component is isolated: its menu shows only
    # Exit Isolate")
    h.check("the new component's menu offers Isolate", "Isolate" in entries, entries)


def isolate_bolt():
    ti.row_menu(NAME, "Isolate")


def bolt_isolated():
    others = [x for x in ("End Cap", "Inner Body", "Wooden Handle", "Wheel Bracket") if shown(x)]
    h.check("only the Shoulder Bolt is shown", not others and shown(NAME), others)


def shown(label):
    return bracket.shown(label)


def exit_isolate():
    entries = [text for text, _on in ti.row_menu_entries(NAME)]
    if "Exit Isolate" not in entries and r.START_AT:
        for label in ("End Cap", "Inner Body", "Wooden Handle", "Wheel Bracket"):
            if not shown(label):
                ti.click_eye(label)
        return
    ti.row_menu(NAME, "Exit Isolate")


def all_shown():
    labels = ("End Cap", "Inner Body", "Wooden Handle", "Wheel Bracket", NAME)
    hidden = [x for x in labels if not shown(x)]
    h.check("Exit Isolate shows every component again", not hidden, hidden)
    h.fit()


# -- the profile (Right plane: sketch x runs along the bolt, sketch y is its radius) --------------
BACK, HEAD, FACE, SHOULDER, STEP, SHANK, END, AXIS = range(8)


def lines_done():
    r.stop_tool()
    lines = si.lines(r.sk())
    if not h.check("eight lines drawn (a closed profile)", len(lines) == 8, len(lines)):
        r.dump_sketch("bolt lines")


def centerline_select():
    Gui.Selection.clearSelection()
    r.xclick(r.geo_mid(AXIS, 0.45))


def centerline():
    si.palette_click("Fission180PaletteCenterline")


def centerline_done():
    from fission180 import sketch_centerline

    lines = sketch_centerline.lines(r.sk())
    h.check("the axis line is a centerline", lines == [AXIS], lines)
    Gui.Selection.clearSelection()


def sketch_done():
    r.dump_sketch("bolt")
    r.fully_constrained(NAME)


def revolve_panel():
    p = r.panel()
    if not h.check("the Revolve dialog is open", p is not None):
        return
    h.check(
        "the profile and the centerline are taken by themselves",
        len(p.profiles) == 1 and p.axis is not None,
        (p.profiles, p.axis),
    )
    h.caught_up(p)


def revolved():
    bodies = r.bodies_of(NAME)
    if not h.check("the bolt is a body of its component", len(bodies) == 1, bodies):
        return
    got = r.vol_in3(NAME)
    h.check("head, shoulder and shank", r.near(got, PLAIN, 1e-5), (got, PLAIN))
    r.box_is("along Y from the origin", NAME, (-0.25, 0, -0.25, 0.25, LONG, 0.25))


# seen from the shank's end (+Y side)
SHANK_END_EDGE = r.gp(SHANK_R * 0.7071, LONG, SHANK_R * 0.7071)
SHANK_FACE = r.gp(SHANK_R * 0.7071, LONG - 0.1, SHANK_R * 0.7071)


def chamfer_edge():
    h.click_edge(SHANK_END_EDGE)


def chamfer_size():
    p = r.blend()
    if not h.check("Chamfer has the shank's end edge", p is not None and len(p.refs) == 1, p):
        return
    r.type_field(p.fields["distance"].widget, "0.02")
    h.caught_up(p)


def thread_face():
    r.xclick(SHANK_FACE)


def thread_offered():
    from Fission180Tests.gui import hole_steps

    p = r.thread_panel()
    if not h.check("a thread is offered", p is not None and p.target is not None, p):
        return
    h.check(
        "1/4-20 UNC",
        p.designation.currentText().startswith("1/4-20"),
        p.designation.currentText(),
    )
    if not p.modeled.isChecked():
        hole_steps.click_checkbox(p.modeled)
    h.caught_up(p)


def drag_thread():
    S["thread"], S["chamfer"] = bracket.last_title("Thread"), bracket.last_title("Chamfer")
    S["bolt_thread_last"] = r.vol_in3(NAME)
    h.check("dragged", ti.drag_step(S["thread"], before_title=S["chamfer"]))


drag_thread.timeout_s = 120


def thread_first():
    titles = r.timeline()
    h.check(
        "the book's drag: the Thread before the Chamfer",
        titles[-2:] == [S["thread"], S["chamfer"]],
        titles,
    )
    r.all_ok("Shoulder Bolt, thread before chamfer")
    h.check("no refusal shown", ti.tl().refusal() == "", ti.tl().refusal())
    got = r.vol_in3(NAME)
    h.check("the thread runs into the chamfer", got < S["bolt_thread_last"] - 1e-6, got)
    S["bolt_threaded"] = got


# -- the slot in the head -------------------------------------------------------------------------
ON_HEAD = r.gp(0.1, 0.0, 0.12)  # on the head's outer face (it faces the home view)


def slot_sketch():
    h.fit()
    Gui.Selection.clearSelection()
    h.ribbon("Create Sketch")


def slot_face():
    r.xclick(ON_HEAD)


slot_face.done = lambda: h.in_sketch() is not None
slot_face.done_what = "the sketch on the head is open"


def slot_open():
    sketch = h.in_sketch()
    S["sk"] = sketch
    circles = [x for x in inner.externals() if "Circle" in x.TypeId]
    h.check(
        "the head's rim is projected into the sketch by itself",
        len(circles) >= 1,
        [x.TypeId for x in inner.externals()],
    )


def rect_centre():
    r.sclick(0.0, 0.0)


def rect_corner():
    r.sclick(*r.on_grid(0.2, 0.05))


def rect_done():
    r.stop_tool()
    lines = [
        i
        for i, x in enumerate(r.sk().Geometry)
        if x.TypeId == "Part::GeomLineSegment" and not r.sk().getConstruction(i)
    ]
    if not h.check("a centre rectangle is drawn", len(lines) == 4, len(lines)):
        r.dump_sketch("bolt slot rect")


def rim():
    """A point on the projected rim, away from the rectangle (top of the head)."""
    sketch = r.sk()
    for x in inner.externals():
        if "Circle" in x.TypeId:
            c, radius = x.Center, x.Radius
            return sketch.getGlobalPlacement().multVec(
                V(c.x + radius * 0.5, c.y + radius * 0.866, 0)
            )
    return None


def tangent_side():
    h.check("Tangent waits for clicks", r.st.tool_title() == "Tangent", r.st.tool_title())
    r.xclick(r.geo_mid(inner.line_index("right"), 0.5))


def tangent_rim():
    r.xclick(rim())


def tangent_done():
    r.stop_tool()
    kinds = [c.Type for c in r.sk().Constraints]
    h.check("the rectangle's end is tangent to the rim", "Tangent" in kinds, kinds)
    x = r.sk().Geometry[inner.line_index("right")]
    h.check(
        "...at the rim (0.25 from the middle)",
        r.near(abs(x.StartPoint.x) / IN, HEAD_R, 1e-5),
        x.StartPoint.x / IN,
    )


def slot_sketch_done():
    r.dump_sketch("bolt slot")
    r.fully_constrained("Shoulder Bolt, the slot")


def extrude_key():
    S.setdefault("bolt_threaded", r.vol_in3(NAME))
    Gui.Selection.clearSelection()
    h.fit()
    h.press("e")


extrude_key.done = lambda: r.panel() is not None
extrude_key.done_what = "the Extrude dialog is open"


def extrude_distance():
    p = r.panel()
    h.check("the slot's profile is taken by itself", len(p.profiles) >= 1, p.profiles)
    r.type_field(p.distance.widget, "-0.16")
    h.caught_up(p)


def extrude_ready():
    p = r.panel()
    # (the report: "Extrude -0.16 auto-switched to Cut")
    h.check(
        "a negative distance into the head is a Cut by itself",
        p.operation.currentText() == "Cut",
        p.operation.currentText(),
    )
    h.check("no complaint", p.message.text() == "", p.message.text())


def slotted():
    r.no_dialog("Extrude")
    got = r.vol_in3(NAME)
    taken = S["bolt_threaded"] - got
    # the slot: 0.08 wide, 0.16 deep, across the 0.5 head (its ends follow the rim)
    half = 0.04
    area = 2 * (half * math.sqrt(HEAD_R**2 - half**2) + HEAD_R**2 * math.asin(half / HEAD_R))
    h.check("the screwdriver slot is cut", r.near(taken, area * 0.16, 2e-5), (taken, area * 0.16))
    S["bolt_slotted"] = got


HEAD_ROUND = r.gp(-HEAD_R * 0.7071, 0.1, HEAD_R * 0.7071)


def head_chamfer_face():
    r.xclick(HEAD_ROUND)


def head_chamfer_size():
    p = r.blend()
    if not h.check("Chamfer has the head's round face", p is not None and len(p.refs) >= 1, p):
        return
    r.type_field(p.fields["distance"].widget, "0.01")
    h.caught_up(p)
    h.check("0.01 is accepted", p.message.text() == "", p.message.text())


def head_chamfered():
    got = r.vol_in3(NAME)
    taken = S["bolt_slotted"] - got
    h.check("the head's rims are chamfered 0.01", 1e-6 < taken < 4e-4, taken)
    r.all_ok("Shoulder Bolt")


# -- Move -----------------------------------------------------------------------------------------
def move_select():
    h.click_empty()
    ti.click_row(NAME)


def move_key():
    h.press("m")


def move_panel():
    from Fission180Tests.gui import component2_steps as c

    return c.component_panel()


move_key.done = lambda: move_panel() is not None
move_key.done_what = "Move/Copy is open on the component"


def move_values():
    from Fission180Tests.gui import component2_steps as c

    p = move_panel()
    h.check(
        "Move/Copy moves the Shoulder Bolt",
        [x.Label for x in p.options.get("components") or []] == [NAME],
    )
    c.type_value(p, "dx", "6")
    c.type_value(p, "dy", "-0.6")
    h.caught_up(p)


def moved():
    r.no_dialog("Move")
    r.box_is(
        "the bolt stands beside the bracket's hole (X 6, Y -0.6)",
        NAME,
        (6 - 0.25, -0.6, -0.25, 6 + 0.25, -0.6 + LONG, 0.25),
        tol=3e-3,
    )
    h.fit()


# -- Joint (J): the bolt into the bracket's hole --------------------------------------------------
def joint_key():
    h.click_empty()
    h.fit()
    h.press("j")


joint_key.done = lambda: inner2.joint_panel() is not None
joint_key.done_what = "the Joint dialog is open"


def shoulder_edge_point():
    """A point on the round edge at the shoulder's end (where the shank starts): the face
    that lies on the bracket's flat. Seen from the side, between the head and the bracket."""
    y = -0.6 + HEAD_T + SHOULDER_T
    return r.gp(6.0 + SHOULDER_R * 0.94, y, SHOULDER_R * 0.342)


def hover_bolt():
    from Fission180Tests.gui import book_joints_steps as bj

    # the shoulder's end (a round edge): hovering the edge is enough for its centre
    bj.hover_edge(shoulder_edge_point())


def click_bolt():
    from Fission180Tests.gui import book_joints_steps as bj

    p = inner2.joint_panel()
    hot = bj.hot(p)
    h.check(
        "a round edge snaps to its centre (report: the seam's corner)",
        hot is not None and hot.get("kind") in ("circle", "centre"),
        hot and hot.get("kind"),
    )
    r.xclick_px(bj.edge_pixel(shoulder_edge_point()))


def hole_rim_point():
    """A point on the rim of the bracket's hole in its flat (round, cut by the thread)."""
    return r.gp(6.0 + 0.125 * 0.7071, -bracket.FLAT, 0.125 * 0.7071)


def hover_hole():
    from Fission180Tests.gui import book_joints_steps as bj

    bj.hover_edge(hole_rim_point())


def click_hole():
    from Fission180Tests.gui import book_joints_steps as bj

    p = inner2.joint_panel()
    hot = bj.hot(p)
    S["hole_snap"] = hot and dict(hot)
    r.xclick_px(bj.edge_pixel(hole_rim_point()))


def joint_ready():
    p = inner2.joint_panel()
    picked = [getattr(p.picks[k], "part", None) for k in ("comp1", "comp2")]
    labels = [x.Label if x is not None else None for x in picked]
    h.check("the bolt, then the bracket", labels == [NAME, "Wheel Bracket"], labels)
    h.check("Type Rigid", p.type_box.currentText() == "Rigid", p.type_box.currentText())
    h.caught_up(p)


def joined():
    from fission180 import joints

    r.no_dialog("Joint")
    made = [x for x in joints.joints(r.doc()) if x.Label == "Rigid 3"]
    h.check("Rigid 3 holds the bolt in the bracket", len(made) == 1, inner2.joints_now())
    shape = r.shape_of(NAME)
    box = shape.optimalBoundingBox(False, False)
    cx, cz = (box.XMin + box.XMax) / 2.0 / IN, (box.ZMin + box.ZMax) / 2.0 / IN
    # (report: "the loop centre on threaded geometry is ~0.37 mm off the true axis (bolt ended
    # 0.015 in off-centre in the hole)")
    h.check(
        "the bolt is on the hole's axis (X 6.00, Z 0) to a micron",
        abs(cx - 6.0) < 5e-5 and abs(cz) < 5e-5,
        (cx, cz),
    )
    box_in = r.box_in(NAME)
    # (hitch found by the replay: the bolt went in head first or shank first by the way the
    # kernel happened to run the two round edges)
    h.check(
        "the shoulder's end lies on the flat, the shank in the hole, the head outside",
        r.near(box_in[1], -bracket.FLAT - SHOULDER_T - HEAD_T, 2e-3)
        and r.near(box_in[4], -bracket.FLAT + SHANK_L, 2e-3),
        box_in,
    )
    h.check("the joints are satisfied", joints.solve(r.doc()) == 0)
    h.check(
        "nothing lost, nothing broken",
        not joints.lost_joints(r.doc()) and not joints.broken_joints(r.doc()),
    )
    h.shot("bolt-joined")


def steps():
    out = [isolate_bracket, inner.activate_design] + r.new_component(NAME)
    out += [made, isolate_bolt, bolt_isolated]
    out += r.create_sketch("YZ_Plane", "bolt")
    out += [r.sketch_view(2.0, (0.4, 0.15), "bolt_view")]
    # Line: the head's back from the axis up, the head, down to the shoulder, the shoulder,
    # down to the shank, the shank, down to the axis and back along it
    out += [r.key("l", "bolt_line"), r.draw_at(0.0, 0.0, "bolt_l1")]
    pts = [(0.0, HEAD_R), (HEAD_T, HEAD_R), (HEAD_T, SHOULDER_R)]
    pts += [(HEAD_T + SHOULDER_T, SHOULDER_R), (HEAD_T + SHOULDER_T, SHANK_R)]
    pts += [(LONG, SHANK_R), (LONG, 0.0), (0.0, 0.0)]
    for k, (u, v) in enumerate(pts):
        out += [r.draw_at(u, v, "bolt_l%d" % (k + 2))]
    out += [lines_done, centerline_select, centerline, centerline_done]
    out += r.dimension(
        [r.at(HEAD, 1), r.on(AXIS, 0.45)],
        (-0.2, 0.3),
        "0.5",
        "bolt_dia_head",
        lambda sk: r.near(sk.getPoint(HEAD, 1).y / IN, HEAD_R),
    )
    out += r.dimension(
        [r.on(HEAD)],
        (0.1, 0.4),
        "0.2",
        "bolt_head_thick",
        lambda sk: r.near(sk.Geometry[HEAD].length() / IN, HEAD_T),
    )
    out += r.dimension(
        [r.on(SHOULDER), r.on(AXIS, 0.45)],
        (0.45, 0.33),
        "0.3125",
        "bolt_dia_shoulder",
        lambda sk: r.near(sk.getPoint(SHOULDER, 1).y / IN, SHOULDER_R),
    )
    out += r.dimension(
        [r.on(SHOULDER)],
        (0.23, 0.45),
        "0.06",
        "bolt_shoulder_long",
        lambda sk: r.near(sk.Geometry[SHOULDER].length() / IN, SHOULDER_T),
    )
    out += r.dimension(
        [r.on(SHANK), r.on(AXIS, 0.45)],
        (0.95, 0.07),
        "0.25",
        "bolt_dia_shank",
        lambda sk: r.near(sk.getPoint(SHANK, 1).y / IN, SHANK_R),
    )
    out += r.dimension(
        [r.on(SHANK)],
        (0.36, 0.25),
        "0.2",
        "bolt_shank_long",
        lambda sk: r.near(sk.Geometry[SHANK].length() / IN, SHANK_L),
    )
    out += [sketch_done, r.finish_sketch("bolt_finish")]
    out += [r.named("bolt_revolve", r.revolve_open), revolve_panel]
    out += [r.ok("bolt_revolve_ok"), revolved]
    out += [r.view_from(1, 1, 1, "bolt_from_shank")]
    out += [r.named("bolt_chamfer", lambda: h.ribbon("Chamfer")), chamfer_edge, chamfer_size]
    out += [r.ok("bolt_chamfer_ok")]
    out += [r.menu("CREATE", "Thread", "bolt_thread"), thread_face, thread_offered]
    out += [r.ok("bolt_thread_ok", 120), drag_thread, thread_first]
    # the slot
    out += [slot_sketch, slot_face, slot_open, r.sketch_view(1.2, (0.0, 0.0), "bolt_slot_view")]
    out += [r.menu("CREATE", "Center Rectangle", "bolt_center_rectangle"), rect_centre]
    out += [rect_corner, rect_done]
    out += [r.menu("CONSTRAINTS", "Tangent", "bolt_tangent"), tangent_side, tangent_rim]
    out += [tangent_done]
    # (the slot's width: between its two long sides; its ends touch the rim)
    out += r.dimension(
        [inner.side("top", 0.3), inner.side("bottom", 0.3)],
        inner.above("right", 0.15, 0.1),
        "0.08",
        "bolt_slot_wide",
        lambda sk: r.near(sk.Geometry[inner.line_index("right")].length() / IN, 0.08),
    )
    out += [slot_sketch_done, r.finish_sketch("bolt_slot_finish")]
    out += [extrude_key, extrude_distance, extrude_ready, r.ok("bolt_extrude_ok"), slotted]
    out += [r.named("bolt_head_chamfer", lambda: h.ribbon("Chamfer")), head_chamfer_face]
    out += [head_chamfer_size, r.ok("bolt_head_chamfer_ok"), head_chamfered]
    out += [exit_isolate, all_shown]
    out += [move_select, move_key, move_values, r.ok("bolt_move_ok"), moved]
    # (a person orbits to see the shoulder's end behind the head, then back for the hole)
    out += [joint_key, r.view_from(1, 0.3, 0.3, "bolt_from_side"), hover_bolt, click_bolt]
    out += [r.iso_view("bolt_joint_home"), r.zoom_on(hole_rim_point, 1.6, "bolt_zoom_hole")]
    out += [hover_hole, click_hole, joint_ready]
    out += [r.ok("bolt_joint_ok"), joined]
    return out
