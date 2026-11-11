# SPDX-License-Identifier: LGPL-2.1-or-later
"""The Tesla Turbine's assembly (replay_13_tesla_turbine; the book parity report, lines
2246-2281). Kept outside scenarios/ because every file there is run as a scenario.

  As-built Joint, Steam Side Wall + Housing & Inlet Tube, Type Slider, the axis by hovering
  into the wall's middle hole; slide Minimum 0 and Rest, Preview Motion (and Flip when it
  showed the wall going into the housing): the wall slides away only (report: no Flip, no
  Preview in the as-built dialog). INSERT > Hardware...: a 1/4-20 screw in a threaded hole
  of the Power Side Wall (report: no McMaster bolts; the book's catalogue is out of scope,
  the same standard part comes from Hardware). As-built Slider of the Power Side Wall; Motion
  Link of the two sliders, 1 and -1: the walls come off together. CREATE > Circular Pattern,
  Pattern Type Components, the screw, Axis Y, Quantity 4: a screw in each hole. Rigid Group
  of the four screws picked in the window. Duplicate With Joints: the screw, then a hole of
  the Steam Side Wall: one copy made. CREATE > Rectangular Pattern, Pattern Type Components:
  a click on a screw (inside the Stator Subassembly) picks the screw, not the subassembly
  (report: picked the whole subassembly and OK made nothing). Appearance: search "anodized",
  Aluminium anodized blue on the Steam Side Wall.

Not replayed (time): the Circular Pattern of a hole's faces, Copy / Paste of a screw, Save
As DXF, Link with Same Joint on a rotor (replayed in the Pizza Cutter), bearings, set screws
and retaining rings from Hardware (each tested by book_hardware_*).
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
    print("[Fission 180] replay steam under %s" % (h.under_mouse(STEAM_FACE),), flush=True)
    r.xclick(STEAM_FACE)
    h.shot("steam-pick")


def pick_housing():
    r.xclick(HOUSING_SIDE)


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


def hardware_made():
    r.no_dialog("Hardware")
    parts = bh.parts()
    h.check("one screw inserted", len(parts) == S["parts_before"] + 1, bh.labels())
    if parts:
        part = parts[-1]
        comp = bh.hw().component_of(part)
        S["screw"] = comp.Label
        centre = bh.axis_of(comp)
        h.check(
            "in the wall's hole (4.5 from the middle)",
            r.near(abs(centre[0]) / IN, 4.5, 2e-3) or r.near(abs(centre[2]) / IN, 4.5, 2e-3),
            centre,
        )
        h.check("held by a joint", bool(bh.joints_of(part)), bh.joints_of(part))


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


# -- Circular Pattern of the screw, Rigid Group ---------------------------------------------------
def pattern_panel():
    return inner2.mirror_panel()


def circular_open():
    h.click_empty()
    si.menu_item("CREATE", "Circular Pattern")


circular_open.done = lambda: pattern_panel() is not None
circular_open.done_what = "the Circular Pattern dialog is open"


def circular_components():
    p = pattern_panel()
    if p.options["pattern_type"] != "components":
        r.choose(p.pattern_type, "Components")


def circular_screw():
    ti.click_row(S.get("screw") or screw_label())


def screw_label():
    labels = [x.Label for x in r.doc().Objects if jm().is_part(x) and "1/4-20" in x.Label]
    return labels[0] if labels else ""


def circular_axis_box():
    from Fission180Tests.gui import pattern_steps

    p = pattern_panel()
    picked = [o[0] if isinstance(o, tuple) else o for o in p.options["objects"]]
    h.check(
        "Components: the screw",
        [getattr(o, "Label", o) for o in picked] == [screw_label()],
        [getattr(o, "Label", o) for o in picked],
    )
    pattern_steps.click_box("axis")


def circular_axis():
    from Fission180Tests.gui import replay_12_handle_steps as handle

    handle.click_path(["Origin", "Y"], "the design's Y axis row")


def circular_quantity():
    p = pattern_panel()
    from Fission180Tests.gui import pattern_steps

    pattern_steps.type_quantity(p.quantity, "4")
    h.caught_up(p)


def screws():
    return [x for x in r.doc().Objects if jm().is_part(x) and "1/4-20" in x.Label]


def circular_made():
    r.no_dialog("Circular Pattern")
    found = screws()
    h.check("four screws, one in each hole", len(found) == 4, [x.Label for x in found])
    spots = sorted(
        (round(bh.axis_of(x)[0] / IN, 2), round(bh.axis_of(x)[2] / IN, 2)) for x in found
    )
    h.check(
        "at 90 degrees about Y", spots == [(-4.5, 0.0), (0.0, -4.5), (0.0, 4.5), (4.5, 0.0)], spots
    )


def group_open():
    h.click_empty()
    j.menu("Rigid Group")


group_open.done = lambda: inner2.joint_panel() is not None
group_open.done_what = "Rigid Group is open"


def group_screw(k):
    def step():
        a = math.radians(90.0 * k)
        r.xclick(r.gp(4.5 * math.cos(a) + 0.1, OUT + 0.15, 4.5 * math.sin(a) + 0.1))

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


def duplicate_hover():
    p = dup_panel()
    h.check(
        "the screw and its joint are taken",
        len(p.members) == 1 and p.chosen()[0] is not None,
        ([m.Label for m in p.members], p.chosen()),
    )
    bj.hover_point(STEAM_SCREW_HOLE)


def duplicate_click():
    r.xclick(STEAM_SCREW_HOLE)


def duplicate_made():
    p = dup_panel()
    made = len(p.copies) if p is not None else 0
    h.check("one copy made", made == 1, made)
    h.press(QtCore.Qt.Key_Escape)


duplicate_made.done = lambda: dup_panel() is None
duplicate_made.done_what = "Duplicate With Joints closed"


def duplicated():
    found = screws()
    h.check("five screws", len(found) == 5, [x.Label for x in found])
    on_steam = [x for x in found if bh.axis_of(x)[1] < 0]
    h.check("one in the Steam Side Wall", len(on_steam) == 1, [bh.axis_of(x) for x in found])


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
    r.xclick(r.gp(4.5 + 0.1, OUT + 0.15, 0.1))


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
    out += [hardware_open, hardware_hole, hardware_fits, r.ok("hardware_ok", 120)]
    out += [
        r.named(
            "hardware_move_ok", lambda: h.task_button("OK") if Gui.Control.activeDialog() else None
        ),
        hardware_made,
    ]
    out += [r.view_from(0.3, 1, 0.3, "power_back_again"), asbuilt_open, pick_power, pick_housing]
    out += [power_type, hover_power_hole, click_power_hole, r.ok("power_slider_ok"), power_made]
    out += [link_open, link_first, link_second, link_values, r.ok("link_ok"), linked]
    out += [circular_open, circular_components, circular_screw, circular_axis_box, circular_axis]
    out += [circular_quantity, r.ok("circular_ok", 120), circular_made]
    out += [group_open] + [group_screw(k) for k in range(4)] + [group_ready]
    out += [r.ok("group_ok"), grouped]
    out += [duplicate_pick, duplicate_open, r.view_from(0.3, -1, 0.2, "steam_front_again")]
    out += [r.zoom_on(STEAM_SCREW_HOLE, 3.0, "steam_zoom"), duplicate_hover, duplicate_click]
    out += [duplicate_made, duplicated]
    out += [r.view_from(0.3, 1, 0.3, "power_back_rect"), rect_open, rect_components]
    out += [rect_screw, rect_picked]
    out += [
        r.view_from(0.3, -1, 0.2, "steam_front_look"),
        r.named("tesla_appearance", r.appearance_open),
    ]
    out += [anodized_search, anodized_drop, r.ok("anodized_ok"), anodized_done]
    return out
