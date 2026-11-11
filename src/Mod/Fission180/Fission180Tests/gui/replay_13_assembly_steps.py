# SPDX-License-Identifier: LGPL-2.1-or-later
"""The Tesla Turbine's assembly (replay_13_tesla_turbine; the book parity report, lines
2246-2281). Kept outside scenarios/ because every file there is run as a scenario.

  As-built Joint, Steam Side Wall + Housing & Inlet Tube, Type Slider, the axis by hovering
  into the wall's middle hole; slide Minimum 0 and Rest, Preview Motion (and Flip when it
  showed the wall going into the housing): the wall slides away only (report: no Flip, no
  Preview in the as-built dialog). INSERT > Hardware...: a 1/4-20 screw in a threaded hole
  of the Power Side Wall (report: no McMaster bolts; the book's catalogue is out of scope,
  the same standard part comes from Hardware): Hardware puts one in each of the four holes
  like it, each joined to its hole, where the book patterns one bolt round with Circular
  Pattern of components. As-built Slider of the Power Side Wall; Motion Link of the two
  sliders, 1 and -1: the walls come off together. Rigid Group of the four screws picked in
  the window (zoomed in: the joints' symbols cover the heads at the whole design's zoom).
  Duplicate With Joints: a screw, then a hole of the Steam Side Wall: refused with the reason
  (known open: Hardware's joint is not made on a face of the screw). CREATE > Rectangular
  Pattern, Pattern Type Components: a click on a screw (inside the Stator Subassembly) picks
  the screw, not the subassembly (report: picked the whole subassembly and OK made nothing);
  Esc. Appearance: search "anodized", Aluminium anodized blue on the Steam Side Wall.

Not replayed (time): Circular Pattern of components and of a hole's faces (the Hardware
screws fill the holes; book_components_pattern and the pattern scenarios test the tool),
Copy / Paste of a screw, Save As DXF, Link with Same Joint on a rotor (replayed in the Pizza
Cutter), bearings, set screws and retaining rings from Hardware (each tested by
book_hardware_*).
"""

import math

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import book_hardware_steps as bh
from Fission180Tests.gui import book_joints_steps as bj
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import joints_steps as j
from Fission180Tests.gui import replay_12_inner2_steps as inner2
from Fission180Tests.gui import replay_13_housing_steps as hs
from Fission180Tests.gui import replay_13_walls_steps as ws
from Fission180Tests.gui import replay_e_steps as r
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import timeline_input as ti
from Fission180Tests.gui import widget_input as w

V = App.Vector
IN = r.IN
S = r.S
STEAM = "Steam Side Wall"
OUT = ws.HALF + ws.GASKET + ws.WALL  # the walls' outer faces lie at +-OUT


def jm():
    from fission180 import joints

    return joints


def joint(label):
    for obj in jm().joints(r.doc()):
        if obj.Label == label:
            return obj
    return None


def place_y(label):
    return jm().global_placement(r.component(label)).Base.y / IN


# -- As-built Slider of the Steam Side Wall -------------------------------------------------------
STEAM_FACE = r.gp(2.0, -OUT, -2.0)
HOUSING_SIDE = r.gp(hs.R_OUT * 0.7071, 0.0, -hs.R_OUT * 0.7071)
STEAM_HOLE = r.gp(0.0, -OUT, 0.0)


def asbuilt_open():
    h.click_empty()
    j.menu("As-built Joint")


asbuilt_open.done = lambda: inner2.joint_panel() is not None
asbuilt_open.done_what = "the As-built Joint dialog is open"


def pick_steam():
    r.xclick(STEAM_FACE)


def pick_housing():
    # (the walls cover the housing from the front and the back: its browser row, inside the
    # Stator Subassembly)
    ti.click_row(hs.NAME)


def slider_type():
    p = inner2.joint_panel()
    h.check(
        "the Steam Side Wall and the housing",
        [x.Label for x in p.parts] == [STEAM, hs.NAME],
        [x.Label for x in p.parts],
    )
    j.choose_type(p, "Slider")


def hover_steam_hole():
    bj.hover_point(STEAM_HOLE)


def click_steam_hole():
    p = inner2.joint_panel()
    hot = bj.hot(p)
    h.check("the pointer in the wall's middle hole lights its centre", hot is not None, hot)
    r.xclick(STEAM_HOLE)


def slider_axis():
    p = inner2.joint_panel()
    snap = p.position_snap
    if not h.check("the hole gives the slider's axis", snap is not None, p.message.text()):
        return
    axis = snap["frame"].Rotation.multVec(V(0, 0, 1))
    h.check(
        "along Y, through the middle",
        abs(abs(axis.y) - 1) < 1e-6 and abs(snap["point"].x) < 0.01 and abs(snap["point"].z) < 0.01,
        (axis, snap["point"]),
    )


def slider_limits():
    from Fission180Tests.gui import bodies_steps as s

    p = inner2.joint_panel()
    # (report: "No Flip and no Preview Limits in the as-built dialog")
    h.check(
        "the as-built dialog has Flip and Preview Motion",
        hasattr(p, "slide_limits") and p.slide_limits.preview.isVisible(),
    )
    rows = p.slide_limits.rows
    s.toggle(rows["min"][0])
    s.toggle(rows["rest"][0])
    h.caught_up(p)
    S["steam_y"] = place_y(STEAM)
    w.click(p.slide_limits.preview)
    S["steam_preview"] = bj.sample(
        lambda: inner2.joint_panel().animator, p.joint, [r.component(STEAM)]
    )


slider_limits.while_busy = True


def ys(samples):
    return [rec["places"][0][1] / IN for rec in samples]


def slider_preview_seen():
    seen = ys(S.get("steam_preview") or [])
    h.check(
        "Preview Motion moves the wall",
        len(seen) >= 5 and max(seen) - min(seen) > 0.1,
        (len(seen), seen[:3]),
    )
    S["steam_inward"] = bool(seen) and max(seen) > S["steam_y"] + 0.05
    w.click(inner2.joint_panel().slide_limits.preview)


slider_preview_seen.while_busy = True
slider_preview_seen.done = lambda: inner2.joint_panel() is not None and (
    inner2.joint_panel().animator is None
)
slider_preview_seen.done_what = "the preview stopped"


def slider_flip():
    p = inner2.joint_panel()
    if S["steam_inward"]:  # it went into the housing: Flip swaps the limits
        w.click(p.slide_limits.flip)
    h.caught_up(p)
    w.click(p.slide_limits.preview)
    S["steam_preview2"] = bj.sample(
        lambda: inner2.joint_panel().animator, p.joint, [r.component(STEAM)]
    )


slider_flip.while_busy = True


def slider_away():
    seen = ys(S.get("steam_preview2") or [])
    h.check(
        "the Steam Side Wall slides away from the housing only",
        len(seen) >= 5 and max(seen) < S["steam_y"] + 1e-3 and min(seen) < S["steam_y"] - 0.1,
        (min(seen or [0]), max(seen or [0]), S["steam_y"]),
    )
    w.click(inner2.joint_panel().slide_limits.preview)


slider_away.while_busy = True
slider_away.done = slider_preview_seen.done
slider_away.done_what = "the preview stopped"


def slider_made():
    r.no_dialog("As-built Joint")
    made = joint("Slider 1")
    h.check(
        "Slider 1 is made", made is not None and made.JointType == "Slider", inner2.joints_now()
    )
    h.check("the wall is back where it was made", r.near(place_y(STEAM), S["steam_y"], 1e-6))
    h.check("the joints are satisfied", jm().solve(r.doc()) == 0)


# -- a 1/4-20 screw from Hardware -----------------------------------------------------------------
HOLE_RIM = r.gp(4.5 + 0.12, OUT, 0.0)


def hardware_open():
    bh.open_hardware()


hardware_open.done = bh.is_open
hardware_open.done_what = "the Hardware dialog is open"


def hardware_hole():
    S["parts_before"] = len(bh.parts())
    h.click_edge(HOLE_RIM)


def hardware_fits():
    p = bh.panel()
    shown = bh.shown()
    print("[Fission 180] replay tesla hardware: %s" % (shown,), flush=True)
    h.check(
        "an inch screw that fits the 1/4-20 hole", shown[0] == "Inch" and "1/4" in shown[3], shown
    )
    h.check("no second hole made in the threaded one", not p.make_hole.isChecked())


def screw_spots():
    """(x, z) in inches of the middle of each screw's solid."""
    out = []
    for comp in screws():
        box = jm().part_shape(comp).BoundBox
        out.append(
            (
                round((box.XMin + box.XMax) / 2.0 / IN, 2),
                round((box.ZMin + box.ZMax) / 2.0 / IN, 2),
                (box.YMin + box.YMax) / 2.0 / IN,
            )
        )
    return out


def hardware_made():
    r.no_dialog("Hardware")
    found = screws()
    # (Hardware puts the part in every hole like the one clicked, each joined to it: the
    # book's four bolts at once, where it patterns one bolt round; see Known issues)
    spots = sorted((x, z) for x, z, _y in screw_spots())
    h.check(
        "a screw in each of the wall's four 1/4-20 holes",
        spots == [(-4.5, 0.0), (0.0, -4.5), (0.0, 4.5), (4.5, 0.0)],
        spots,
    )
    if found:
        comp = found[0]
        S["screw"] = comp.Label
        holder = r.comps().container_of(comp)
        h.check(
            "a component of its own in the Stator Subassembly",
            holder is not None and holder.Label == hs.STATOR,
            holder and holder.Label,
        )
        h.check(
            "each held by a joint to the wall", len(inner2.joints_now()) >= 5, inner2.joints_now()
        )


# -- As-built Slider of the Power Side Wall, Motion Link ------------------------------------------
POWER_FACE = r.gp(2.0, OUT, -2.0)
POWER_HOLE = r.gp(0.0, OUT, 0.0)


def pick_power():
    r.xclick(POWER_FACE)


def power_type():
    p = inner2.joint_panel()
    h.check(
        "the Power Side Wall and the housing",
        [x.Label for x in p.parts] == [ws.POWER, hs.NAME],
        [x.Label for x in p.parts],
    )
    j.choose_type(p, "Slider")


def hover_power_hole():
    bj.hover_point(POWER_HOLE)


def click_power_hole():
    r.xclick(POWER_HOLE)


def power_made():
    r.no_dialog("As-built Joint")
    h.check("Slider 2 is made", joint("Slider 2") is not None, inner2.joints_now())


def link_open():
    h.click_empty()
    j.menu("Motion Link")


link_open.done = lambda: j.panel() is not None
link_open.done_what = "Motion Link is open"


def link_first():
    ti.click_row("Slider 1")


def link_second():
    ti.click_row("Slider 2")


def link_values():
    from Fission180Tests.gui import bodies_steps as s

    p = j.panel()
    h.check(
        "the two sliders are taken",
        [x.Label for x in p.picked] == ["Slider 1", "Slider 2"],
        [x.Label for x in p.picked],
    )
    # the report's "Distances 1 / 2"; here the walls come off together: 1 and -1
    s.type_value(p.rows[0]["field"].widget, "1")
    s.type_value(p.rows[1]["field"].widget, "-1")
    h.caught_up(p)
    print("[Fission 180] replay tesla link note: %s" % p.note.text(), flush=True)
    h.check(
        "the note is in inches",
        " in " in p.note.text() and "mm" not in p.note.text(),
        p.note.text(),
    )


def linked():
    r.no_dialog("Motion Link")
    links = jm().motion_links(r.doc())
    h.check("Motion Link 1 ties the two sliders", len(links) == 1, links)
    h.check("the joints are satisfied", jm().solve(r.doc()) == 0)


# -- Rigid Group of the four screws -------------------------------------------------------------
def pattern_panel():
    return inner2.mirror_panel()


def screw_label():
    labels = [x.Label for x in r.doc().Objects if jm().is_part(x) and "1/4-20" in x.Label]
    return labels[0] if labels else ""


def screws():
    return [x for x in r.doc().Objects if jm().is_part(x) and "1/4-20" in x.Label]


def group_open():
    h.click_empty()
    j.menu("Rigid Group")


group_open.done = lambda: inner2.joint_panel() is not None
group_open.done_what = "Rigid Group is open"


def head_side(x, z):
    """A point on the side of a screw's head standing in the hole at (x, z) of the Power Side
    Wall, on the side the view from +X +Y +Z shows (the joint's symbol is drawn on the axis)."""
    return r.gp(x + 0.13, OUT + 0.12, z + 0.13)


def zoom_to(point, width_in):
    cam = h.view().getCameraNode()
    rot = App.Rotation(*cam.orientation.getValue().getValue())
    eye = point + rot.multVec(V(0, 0, 1)) * 500.0
    cam.position.setValue((eye.x, eye.y, eye.z))
    gl = h.gl_widget()
    cam.height.setValue(width_in * IN * gl.height() / float(max(1, gl.width())))
    h.view_still()


def group_screw(k):
    def step():
        a = math.radians(90.0 * k)
        spot = head_side(4.5 * math.cos(a), 4.5 * math.sin(a))
        # (a person zooms in: at the whole design's zoom the joints' symbols cover the heads)
        zoom_to(spot, 1.5)
        r.xclick(spot)

    step.__name__ = "group_screw_%d" % (k + 1)
    return step


def group_ready():
    p = inner2.joint_panel()
    h.check(
        "the four screws, picked in the window", len(p.members) == 4, [m.Label for m in p.members]
    )


def grouped():
    r.no_dialog("Rigid Group")
    groups = jm().rigid_groups(r.doc())
    h.check(
        "a rigid group of the four screws",
        any(len(g.Members) == 4 for g in groups),
        [[m.Label for m in g.Members] for g in groups],
    )
    h.check("the joints are satisfied", jm().solve(r.doc()) == 0)


# -- Duplicate With Joints ------------------------------------------------------------------------
def duplicate_pick():
    h.click_empty()
    ti.click_row(screw_label())


def duplicate_open():
    si.menu_item("ASSEMBLE", "Duplicate With Joints")


def dup_panel():
    from fission180 import duplicate_joints_ui

    p = duplicate_joints_ui.DuplicatePanel.last
    return None if p is None or p._closed else p


duplicate_open.done = lambda: dup_panel() is not None
duplicate_open.done_what = "Duplicate With Joints is open"

STEAM_SCREW_HOLE = r.gp(4.5, -OUT, 0.0)


def duplicate_position_box():
    p = dup_panel()
    if p.active != "position":
        # (the screw has two open joints, its joint to the wall and its rigid group: the
        # dialog waits for the Joint list or a click on the Position box, as it says)
        r.click_widget(p.fields[p.slots["position"].first_box()].button)


def duplicate_hover():
    p = dup_panel()
    h.check(
        "the screw and its joint are taken",
        len(p.members) == 1 and p.chosen()[0] is not None,
        ([m.Label for m in p.members], p.chosen()),
    )
    # the report's way: hover the face next to the hole, move into the hole (its centre
    # stays lit), click
    bj.hover_point(STEAM_SCREW_HOLE + V(0.3 * IN, 0, 0.2 * IN))
    bj.hover_point(STEAM_SCREW_HOLE + V(0.05 * IN, 0, 0.02 * IN))
    hov = getattr(dup_panel(), "hover", None)
    h.check("the hole's centre is lit", hov is not None and hov.hot is not None, hov and hov.hot)


def duplicate_click():
    r.xclick(STEAM_SCREW_HOLE + V(0.05 * IN, 0, 0.02 * IN))


def duplicate_made():
    p = dup_panel()
    made = len(p.copies) if p is not None else 0
    said = p.message.text() if p is not None else ""
    if made == 1:
        h.check("one copy made", True)
    else:
        # KNOWN OPEN (replay-e): a screw put in by Hardware is held by a joint that is not
        # made on one of its faces or edges (Hardware stores where it sits), and Duplicate
        # With Joints needs one that is. The dialog says so; the book's bolt was jointed by
        # hand. What it would take: Hardware making its joint on the head's bearing edge.
        h.check(
            "known open: Duplicate With Joints says why it cannot copy a Hardware screw",
            made == 0 and "Duplicate With Joints needs one that is" in said,
            (made, said),
        )
    S["duplicated"] = made
    h.press(QtCore.Qt.Key_Escape)


duplicate_made.done = lambda: dup_panel() is None
duplicate_made.done_what = "Duplicate With Joints closed"


def duplicated():
    found = screws()
    want = 4 + S.get("duplicated", 0)
    h.check("%d screws" % want, len(found) == want, [x.Label for x in found])
    on_steam = [spot for spot in screw_spots() if spot[2] < 0]
    h.check(
        "one in the Steam Side Wall when a copy was made",
        len(on_steam) == S.get("duplicated", 0),
        screw_spots(),
    )


# -- Rectangular Pattern of components: a nested screw picked in the window -----------------------
def rect_open():
    h.click_empty()
    si.menu_item("CREATE", "Rectangular Pattern")


rect_open.done = lambda: pattern_panel() is not None
rect_open.done_what = "the Rectangular Pattern dialog is open"


def rect_components():
    p = pattern_panel()
    if p.options["pattern_type"] != "components":
        r.choose(p.pattern_type, "Components")


def rect_screw():
    zoom_to(head_side(4.5, 0.0), 1.5)
    r.xclick(head_side(4.5, 0.0))


def rect_picked():
    p = pattern_panel()
    picked = [o[0] if isinstance(o, tuple) else o for o in p.options["objects"]]
    labels = [getattr(o, "Label", o) for o in picked]
    # (report: "clicking a bolt in the canvas picked the whole Stator Subassembly; OK then
    # made nothing (no message)")
    h.check(
        "the screw is picked, not the subassembly around it",
        len(labels) == 1 and "1/4-20" in labels[0],
        labels,
    )
    h.press(QtCore.Qt.Key_Escape)


rect_picked.done = lambda: pattern_panel() is None
rect_picked.done_what = "the dialog closed (Esc)"


# -- Appearance: anodized -------------------------------------------------------------------------
def anodized_search():
    p = r.looks().panel()
    if not h.check("the Appearance dialog is open (A)", p is not None):
        return
    w.click(p.search)
    w.type_text(p.search, "anodized")
    h.settle()


def anodized_drop():
    found = r.looks().library_labels()
    h.check(
        "the search finds the anodized aluminiums", "Aluminium, anodized blue" in found, found[:10]
    )
    p = r.looks().panel()
    took = r.looks().drop_look("Aluminium, anodized blue", STEAM_FACE)
    h.check("the Steam Side Wall takes it", took and p.message.text() == "", p.message.text())


def anodized_done():
    label = r.looks().body_look_label(r.body_of(STEAM))
    h.check("the Steam Side Wall is anodized blue", label == "Aluminium, anodized blue", label)
    r.all_ok("the Tesla Turbine")
    h.fit()
    h.shot("tesla-done")


def steps():
    out = [r.view_from(0.3, -1, 0.2, "steam_front"), asbuilt_open, pick_steam, pick_housing]
    out += [slider_type, hover_steam_hole, click_steam_hole, slider_axis, slider_limits]
    out += [slider_preview_seen, slider_flip, slider_away, r.ok("steam_slider_ok"), slider_made]
    out += [r.view_from(0.3, 1, 0.3, "power_back"), r.zoom_on(HOLE_RIM, 3.0, "power_zoom")]
    # (the screws go into the Stator Subassembly, as the book's bolts: the active component)
    out += [ws.activate(hs.STATOR), hardware_open, hardware_hole, hardware_fits]
    out += [r.ok("hardware_ok", 120)]
    out += [
        r.named(
            "hardware_move_ok", lambda: h.task_button("OK") if Gui.Control.activeDialog() else None
        ),
        hardware_made,
    ]
    out += [r.view_from(0.3, 1, 0.3, "power_back_again"), asbuilt_open, pick_power, pick_housing]
    out += [power_type, hover_power_hole, click_power_hole, r.ok("power_slider_ok"), power_made]
    out += [link_open, link_first, link_second, link_values, r.ok("link_ok"), linked]
    out += [r.view_from(0.3, 1, 0.3, "screws_back"), group_open]
    out += [group_screw(k) for k in range(4)] + [group_ready]
    out += [r.ok("group_ok"), grouped]
    out += [duplicate_pick, duplicate_open, r.view_from(0.3, -1, 0.2, "steam_front_again")]
    out += [r.zoom_on(STEAM_SCREW_HOLE, 3.0, "steam_zoom"), duplicate_position_box, duplicate_hover]
    out += [duplicate_click]
    out += [duplicate_made, duplicated]
    out += [r.view_from(0.3, 1, 0.3, "power_back_rect"), rect_open, rect_components]
    out += [rect_screw, rect_picked]
    out += [
        r.view_from(0.3, -1, 0.2, "steam_front_look"),
        r.named("tesla_appearance", r.appearance_open),
    ]
    out += [anodized_search, anodized_drop, r.ok("anodized_ok"), anodized_done]
    return out
