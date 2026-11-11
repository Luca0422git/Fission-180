# SPDX-License-Identifier: LGPL-2.1-or-later
"""Replay of the book's Project 15, "Gear Train" (Mastering Autodesk Fusion, 2nd ed.,
pp 188-195), the way a person follows it: wave 7's acceptance test
(docs/fission180/dev/briefs/book-replay.md; the book parity report, lines 2336-2382).
Real input only, a person's defaults, no workaround.

The report tested "key tools only" and names these values: the Spur Gear sample with
module 1.5, 20 teeth, 8 thick, hole 4 (pitch diameter 30); a 100 tooth gear with the
book's 0.88 mm root fillet, 4 thick (pitch diameter 150); Move with Z Distance 4 and Z
Angle 360/20/2; a "Compound Gear" the two gears are dragged into; Split Body with a sketch
curve. Its last line was not tested: "the copy/paste train and its motion links". The
replay goes on to that with two compound gears (the book has eleven: the eleventh is
pasted like the second) on a stand-in for the book's frame: two axles 4 across, 90 apart
(the pitch radii 75 + 15), the second compound gear standing 4 higher so that its big
gear runs on the first one's pinion.

  1  Axles (the stand-in frame): two circles, Equal, 4 across, 90 apart, extruded 16.
  2  UTILITIES > ADD-INS > Scripts and Add-Ins > SpurGear: 20 teeth, module 1.5, root
     fillet 0.88, 8 thick, hole 4: a new component "Spur Gear (20 teeth)" by itself.
  3  SpurGear again: it starts with the last values; 100 teeth, 4 thick, the same 0.88
     (bug 19): "Spur Gear (100 teeth)", beside the first gear's component, not inside it.
  4  Timeline > Gear 2 > Edit Feature: the dialog opens on it; Cancel (bug 20).
  5  The 20 tooth gear clicked, M: Z Distance 4, Z Angle 360/20/2 = 9 degrees, about the
     component's origin.
  6  New Component "Compound Gear"; both gears dragged onto its row in the browser.
  7  Split Body: a line sketched on the big gear's top face, the body + the line, Extend
     Splitting Tool: two bodies whose volumes add up. Ctrl+Z (the train runs on whole gears).
  8  Compound Gear's row, Ctrl+C, Ctrl+V: X 90, Z 4, OK: the second compound gear.
  9  As-built Revolute joints of the two compound gears with the Axles; Motion Link between
     them: 360 to 72 degrees (20 : 100 teeth), Reverse; Animate.
 10  Animate Joint Relationships and Drive Joints: the second gear turns a fifth of the
     first, the other way. Save, close, reopen.
"""

import math
import os
import tempfile

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import bodies_steps
from Fission180Tests.gui import book_components_steps as k
from Fission180Tests.gui import book_joints_steps as bj
from Fission180Tests.gui import book_sketch_b_steps as b
from Fission180Tests.gui import component2_steps as c2
from Fission180Tests.gui import component_steps as cs
from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import insert_steps as ins
from Fission180Tests.gui import joints_steps as j
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import primitive_input as pi
from Fission180Tests.gui import replay_f_steps as r
from Fission180Tests.gui import sketch_tools_steps as st
from Fission180Tests.gui import timeline_input as t
from Fission180Tests.gui import widget_input as w

V = App.Vector
S = {}
M = 1.5  # the book's module
APART = 90.0  # 75 + 15: the pitch radii of a 100 and a 20 tooth gear
AXLE_D = 4.0
AXLE_L = 16.0
FILLET = 0.88


def jm():
    return bj.jm()


def gear_panel():
    return pi.panel("GearPanel")


def gears():
    return [o for o in r.doc().Objects if getattr(o, "Fission180Type", "") == "Gear"]


def hole_axis(part):
    """Where the axis of a gear's 4 mm hole stands in the design, as (x, y): the centres
    of the hole's rims (exact: a solid's bounding box is only as fine as its drawing)."""
    out = []
    for edge in jm().part_shape(part).Edges:
        curve = getattr(edge, "Curve", None)
        if (
            curve is not None
            and curve.TypeId == "Part::GeomCircle"
            and abs(curve.Radius - 2.0) < 1e-6
        ):
            out.append((round(curve.Center.x, 7), round(curve.Center.y, 7)))
    return sorted(set(out))


def gear_area(teeth):
    from fission180 import gear_core

    return gear_core.area(dict(module=M, teeth=teeth, hole=4.0, fillet=FILLET))


# == 1: Axles ======================================================================================
def ax_circle_tool():
    h.press("c")


def ax_circle_1():
    st.click(V(0, 0, 0))
    st.click(V(10, 0, 0))


def ax_circle_2():
    st.click(V(60, 0, 0))
    st.click(V(80, 0, 0))


def ax_drawn():
    st.esc()
    cs_ = r.circles()
    h.check("1 two circles drawn", len(cs_) == 2, [(g.Center, g.Radius) for _i, g in cs_])
    S["c2"] = V(cs_[1][1].Center)
    S["r1"], S["r2"] = cs_[0][1].Radius, cs_[1][1].Radius


def ax_select():
    Gui.Selection.clearSelection()
    st.click(V(0, S["r1"], 0))
    b.shift_click(S["c2"] + V(0, S["r2"], 0))


def ax_equal():
    h.check("1 both circles selected", len(b.selected()) == 2, b.selected())
    b.menu("Equal")


def ax_equalled():
    cs_ = r.circles()
    h.check("1 Equal: one size", abs(cs_[0][1].Radius - cs_[1][1].Radius) < 1e-9)
    st.esc()
    Gui.Selection.clearSelection()
    S["r"] = cs_[0][1].Radius
    S["c2"] = V(cs_[1][1].Center)


def ax_sized():
    cs_ = r.circles()
    h.check("1 both axles are 4 across", all(abs(g.Radius * 2 - AXLE_D) < 1e-6 for _i, g in cs_))
    S["c2"] = V(cs_[1][1].Center)


def ax_spaced():
    cs_ = r.circles()
    h.check(
        "1 the axles are 90 apart on the X axis",
        abs(cs_[1][1].Center.x - APART) < 1e-6 and abs(cs_[1][1].Center.y) < 1e-9,
        cs_[1][1].Center,
    )
    h.check("1 the sketch is fully defined", r.sk().solve() == 0, r.sk().solve())


def ax_extrude():
    h.click_empty()
    h.fit()
    h.press("e")


ax_extrude.done = lambda: r.extrude_panel() is not None
ax_extrude.done_what = "the Extrude dialog is open"


def ax_profiles():
    h.click(V(0, 0, 0))
    h.settle()
    h.click(V(APART, 0, 0))
    h.settle()
    p = r.extrude_panel()
    h.check("1 both circles are profiles", len(p.profiles) == 2, p.profiles)
    ui.type_into(p.distance.widget, "%g" % AXLE_L)
    h.caught_up(p)
    h.check(
        "1 New Body proposed", p.operation.currentText() == "New Body", p.operation.currentText()
    )
    h.task_button("OK")


ax_profiles.done = lambda: r.extrude_panel() is None
ax_profiles.done_what = "the Extrude dialog closed"


def ax_made():
    bodies = r.bodies("Axles")
    h.check("1 two axles", len(bodies) == 2, [x.Label for x in bodies])
    want = math.pi * (AXLE_D / 2) ** 2 * AXLE_L
    h.check("1 each 4 across and 16 long", all(r.near(k.volume(x), want) for x in bodies))
    r.box_is(
        "1 they stand up from the XY plane", r.part("Axles"), [-2, -2, 0, APART + 2, 2, AXLE_L]
    )
    h.check("1 Axles, the first component, is grounded", jm().is_grounded(r.part("Axles")))
    r.no_open_step("Extrude")


steps = list(r.START)
steps += r.new_component("Axles", parent_reads="root", activate_root=False)
steps += r.create_sketch("XY_Plane", "Axles", "axles")
steps += [ax_circle_tool, ax_circle_1, ax_circle_2, ax_drawn, ax_select, ax_equal, ax_equalled]
steps += r.dimension(
    [lambda: V(S["r"] * 0.7071, S["r"] * 0.7071, 0)],
    lambda: V(S["r"] + 6, S["r"] + 6, 0),
    "4",
    "axle_diameter",
    ax_sized,
)
steps += r.dimension(
    [V(0, 0, 0), lambda: S["c2"]],
    lambda: V(S["c2"].x / 2, -8, 0),
    "90",
    "axle_distance",
    ax_spaced,
)
steps += [r.finish_sketch, ax_extrude, ax_profiles, ax_made, r.activate("")]


# == 2 and 3: the Spur Gear sample =================================================================
def scripts():
    from fission180 import scripts_ui

    d = scripts_ui.ScriptsDialog.last
    try:
        return d if d is not None and d.isVisible() else None
    except RuntimeError:
        return None


def open_scripts():
    h.click_empty()
    h.fit()
    ins.ribbon_tab("UTILITIES")
    h.ribbon("Scripts and Add-Ins")


open_scripts.done = lambda: scripts() is not None
open_scripts.done_what = "the Scripts and Add-Ins window is open"


def run_spur_gear():
    from fission180 import scripts_core

    d = scripts()
    names = [d.list.topLevelItem(n).text(0) for n in range(d.list.topLevelItemCount())]
    # the report: "the list is EMPTY: no Spur Gear sample"
    h.check("the list has the SpurGear sample", "SpurGear" in names, names)
    item = d.item_for(scripts_core.SCRIPT, "SpurGear")
    rect = d.list.visualItemRect(item)
    w.click(d.list.viewport(), QtCore.QPoint(rect.left() + 20, rect.center().y()))
    h.check("Run is offered for it", d.run_button.isEnabled() and d.run_button.text() == "Run")
    w.click(d.run_button)


run_spur_gear.done = lambda: gear_panel() is not None
run_spur_gear.done_what = "SpurGear opened the Gear dialog"


def gear_started():
    # Fusion's window closes when a script is run; nothing is left over the design
    h.check("the Scripts and Add-Ins window closed by itself", scripts() is None)
    p = gear_panel()
    h.check("the Gear dialog waits for a plane", p is not None and p.target is None)


def gear_plane():
    pl.click_square("XY_Plane")


def gear_centre():
    h.click(V(0, 0, 0))


def gear_1_values():
    p = gear_panel()
    if not h.check("2 the gear is placed", p is not None and p.target is not None):
        return
    # Fusion's sample always makes a new component: nothing to choose
    h.check(
        "2 started from the sample, the dialog proposes a New Component by itself",
        p.operation.currentText() == "New Component",
        p.operation.currentText(),
    )
    for field, text in ((p.module, "1.5"), (p.teeth, "20"), (p.fillet, "0.88"), (p.thickness, "8")):
        ui.type_into(field.widget, text)
    ui.type_into(p.hole.widget, "4")
    h.caught_up(p)
    h.check("2 no problem said", p.message.text() == "", p.message.text())
    h.check("2 still a New Component", p.operation.currentText() == "New Component")
    h.shot("2-gear-20")
    h.task_button("OK")


gear_1_values.done = lambda: gear_panel() is None
gear_1_values.done_what = "the Gear dialog closed"


def gear_1_made():
    found = gears()
    if not h.check("2 one gear", len(found) == 1, found):
        return
    S["g20"] = found[0].Name
    part = r.part("Spur Gear (20 teeth)")
    # the report: 'Component names are "Component1/2", not "Spur Gear (20 teeth)"'
    h.check("2 its component is named Spur Gear (20 teeth)", part is not None, k.labels())
    if part is None:
        return
    h.check("2 ...at the top level", k.container_label(part) == "", k.container_label(part))
    h.check(
        "2 20 teeth, module 1.5, 8 thick, hole 4, root fillet 0.88",
        r.near(found[0].Shape.Volume, gear_area(20) * 8.0, 1e-6),
        (found[0].Shape.Volume, gear_area(20) * 8.0),
    )
    box = r.bbox(part)
    # pitch diameter 30: the outside diameter is m (z + 2) = 33
    h.check(
        "2 pitch diameter 30 (33 over the tips), on the origin, z 0..8",
        r.near(box[3] - box[0], 33.0, 1e-3) and r.near(box[5], 8.0) and abs(box[2]) < 1e-6,
        box,
    )
    h.check(
        "2 its hole stands exactly on the origin (the click snapped to it)",
        hole_axis(part) == [(0.0, 0.0)],
        hole_axis(part),
    )
    h.check("2 the timeline shows Gear 1", "Gear 1" in r.timeline(), r.timeline())
    r.no_open_step("Gear")
    S["active_after_gear"] = k.active_label()


def gear_2_values():
    p = gear_panel()
    if not h.check("3 the second gear is placed", p is not None and p.target is not None):
        return
    h.check("3 the dialog starts with the last gear's values", abs(p.teeth.value() - 20) < 1e-9)
    h.check(
        "3 ...its 0.88 root fillet too", abs(p.fillet.value() - FILLET) < 1e-9, p.fillet.value()
    )
    h.check("3 a New Component again", p.operation.currentText() == "New Component")
    ui.type_into(p.teeth.widget, "100")
    ui.type_into(p.thickness.widget, "4")
    h.caught_up(p)
    # bug 19: 'the dialog warns "does not fit ... at most 0.741 mm"'. Fusion's SpurGear
    # takes 0.88 for any number of teeth at module 1.5 (its limit is 0.4 x the tooth
    # thickness on the base circle, 0.8857 mm).
    h.check(
        "3 the book's 0.88 fits 100 teeth: nothing is said (bug 19)",
        p.message.text() == "",
        p.message.text(),
    )
    h.shot("3-gear-100")
    h.task_button("OK")


gear_2_values.done = lambda: gear_panel() is None
gear_2_values.done_what = "OK made the 100 tooth gear"


def gear_2_made():
    found = [g for g in gears() if g.Name != S["g20"]]
    if not h.check("3 a second gear", len(found) == 1, gears()):
        return
    S["g100"] = found[0].Name
    part = r.part("Spur Gear (100 teeth)")
    h.check("3 its component is named Spur Gear (100 teeth)", part is not None, k.labels())
    if part is None:
        return
    # the report: "the 2nd gear's New Component was created INSIDE the first gear's
    # component (it was left active)". Fusion's sample adds its component to the design.
    h.check(
        "3 ...beside the first gear's component, not inside it",
        k.container_label(part) == "",
        k.container_label(part),
    )
    h.check(
        "3 100 teeth, 4 thick, the book's 0.88 root fillet (not a copy of the first gear)",
        r.near(found[0].Shape.Volume, gear_area(100) * 4.0, 1e-6),
        (found[0].Shape.Volume, gear_area(100) * 4.0),
    )
    box = r.bbox(part)
    h.check(
        "3 pitch diameter 150 (153 over the tips), z 0..4",
        r.near(box[3] - box[0], 153.0, 1e-3) and r.near(box[5], 4.0),
        box,
    )
    h.check(
        "3 its hole stands exactly on the origin", hole_axis(part) == [(0.0, 0.0)], hole_axis(part)
    )
    h.check(
        "3 the first gear is untouched",
        r.near(r.doc().getObject(S["g20"]).Shape.Volume, gear_area(20) * 8.0, 1e-6),
    )
    h.check("3 the timeline shows Gear 2", "Gear 2" in r.timeline(), r.timeline())
    r.no_open_step("Gear")
    h.fit()
    h.shot("3-two-gears")


steps += [
    open_scripts,
    run_spur_gear,
    gear_started,
    gear_plane,
    gear_centre,
    gear_1_values,
    gear_1_made,
]
steps += [r.named(open_scripts, "open_scripts_2"), r.named(run_spur_gear, "run_spur_gear_2")]
steps += [r.named(gear_plane, "gear_plane_2"), r.named(gear_centre, "gear_centre_2")]
steps += [gear_2_values, gear_2_made]


# == 4: Edit Feature on Gear 2 (bug 20) ============================================================
def edit_gear_2():
    ins.ribbon_tab("SOLID")
    h.click_empty()
    t.menu("Gear 2", "Edit Feature")


edit_gear_2.done = lambda: gear_panel() is not None
edit_gear_2.done_what = "Edit Feature opened the Gear dialog"


def edit_shown():
    p = gear_panel()
    h.check(
        "4 it shows 100 teeth and 4 thick",
        abs(p.teeth.value() - 100) < 1e-9 and abs(p.thickness.value() - 4) < 1e-9,
        (p.teeth.value(), p.thickness.value()),
    )
    h.task_button("Cancel")


edit_shown.done = lambda: gear_panel() is None
edit_shown.done_what = "the Gear dialog closed"


def edit_cancelled():
    # bug 20: "the step VANISHED from the timeline (its objects stayed, body gone)"
    h.check("4 Gear 2 is still in the timeline", r.timeline().count("Gear 2") == 1, r.timeline())
    g = r.doc().getObject(S["g100"])
    h.check(
        "4 the gear is unchanged",
        g is not None and r.near(g.Shape.Volume, gear_area(100) * 4.0, 1e-6),
    )
    r.no_open_step("Edit Feature, Cancel")


steps += [edit_gear_2, edit_shown, edit_cancelled]


# == 5: Move the 20 tooth gear: Z 4, Z Angle 360/20/2 ==============================================
def move_key():
    h.click_empty()
    h.fit()
    h.press("m")


move_key.done = lambda: c2.panel() is not None
move_key.done_what = "Move/Copy is open"


def move_components():
    p = c2.panel()
    h.check("5 M opens Move/Copy", p is not None and p.title == "Move/Copy", p and p.title)
    if c2.component_panel() is None:
        c2.choose(p.move_object, "Components", closes=True)


move_components.done = lambda: c2.component_panel() is not None
move_components.done_what = "Move Object reads Components"


def pick_small_gear():
    h.click(V(0, 9, 8))  # the top of the 20 tooth gear, between its hole and its teeth


def move_picked():
    p = c2.component_panel()
    names = [x.Label for x in p.options.get("components") or []]
    h.check("5 the click took the gear's component", names == ["Spur Gear (20 teeth)"], names)


def move_values():
    p = c2.component_panel()
    triad = getattr(p, "triad", None)
    # the report: "the rotation pivot was ~0.003 mm off the origin"
    h.check(
        "5 the manipulator sits exactly on the component's origin",
        triad is not None and triad.center.Length < 1e-9,
        triad and triad.center,
    )
    c2.type_value(p, "dz", "4")
    c2.type_value(p, "rz", "360/20/2")


def move_ok():
    p = c2.component_panel()
    h.caught_up(p)
    shown = c2.field(p, "rz").text()
    h.check("5 360/20/2 is 9 degrees (half a tooth)", "9" in shown, shown)
    h.task_button("OK")


move_ok.done = lambda: c2.component_panel() is None
move_ok.done_what = "Move/Copy closed"


def moved():
    part = r.part("Spur Gear (20 teeth)")
    plc = jm().global_placement(part)
    h.check("5 the gear stands 4 higher", (plc.Base - V(0, 0, 4)).Length < 1e-6, plc.Base)
    turn = math.degrees(plc.Rotation.Angle) * (1 if plc.Rotation.Axis.z >= 0 else -1)
    h.check("5 ...turned 9 degrees about Z", abs(abs(turn) - 9.0) < 1e-6, (turn, plc.Rotation.Axis))
    box = r.bbox(part)
    # the report: "the rotation pivot was ~0.003 mm off the origin"
    h.check(
        "5 it still stands exactly on the origin's axis, z 4..12",
        hole_axis(part) == [(0.0, 0.0)] and r.near(box[2], 4) and r.near(box[5], 12),
        (hole_axis(part), box),
    )
    r.no_open_step("Move/Copy")


steps += [move_key, move_components, pick_small_gear, move_picked, move_values, move_ok, moved]


# == 6: Compound Gear: both gears dragged into it ==================================================
def drag_small():
    S["places"] = [bj.place(r.part(n)) for n in ("Spur Gear (20 teeth)", "Spur Gear (100 teeth)")]
    cs.drag_row("Spur Gear (20 teeth)", "Compound Gear")


drag_small.done = lambda: k.container_label(r.part("Spur Gear (20 teeth)")) == "Compound Gear"
drag_small.done_what = "the 20 tooth gear is inside Compound Gear"


def drag_big():
    # the report: "the 2nd drag landed on the wrong row after the tree re-expanded"
    cs.drag_row("Spur Gear (100 teeth)", "Compound Gear")


drag_big.done = lambda: k.container_label(r.part("Spur Gear (100 teeth)")) == "Compound Gear"
drag_big.done_what = "the 100 tooth gear is inside Compound Gear"


def compound_made():
    inside = cs.children_of(["Compound Gear"]) or []
    h.check(
        "6 both gears are rows of Compound Gear",
        "Spur Gear (20 teeth)" in inside and "Spur Gear (100 teeth)" in inside,
        inside,
    )
    now = [bj.place(r.part(n)) for n in ("Spur Gear (20 teeth)", "Spur Gear (100 teeth)")]
    h.check("6 neither gear moved", not any(bj.moved(a, c) for a, c in zip(now, S["places"])), now)
    r.box_is(
        "6 the compound gear: 153 across, 12 high",
        r.part("Compound Gear"),
        [-76.5, -76.5, 0, 76.5, 76.5, 12],
        0.05,
    )
    h.check(
        "6 both gears on one axis, the origin's",
        hole_axis(r.part("Compound Gear")) == [(0.0, 0.0)],
        hole_axis(r.part("Compound Gear")),
    )
    r.no_open_step("the drags")
    h.shot("6-compound-gear")


steps += r.new_component("Compound Gear", parent_reads="root", activate_root=True)
steps += [r.activate(""), drag_small, drag_big, compound_made]


# == 8: Copy and Paste: the second compound gear ===================================================
def copy_select():
    h.click_empty()
    t.click_row("Compound Gear")


def copy_key():
    t.ctrl("c")


def paste_key():
    S["labels"] = k.labels()
    t.ctrl("v")


paste_key.done = lambda: c2.component_panel() is not None
paste_key.done_what = "Move/Copy opened on the paste"


def paste_values():
    new = [x for x in k.labels() if x not in S["labels"] and k.container_label(r.part(x)) == ""]
    h.check("8 the paste is a new component at the top level", len(new) == 1, new)
    S["copy"] = new[0] if new else ""
    p = c2.component_panel()
    h.check(
        "8 Move/Copy is open on it",
        [x.Label for x in p.options.get("components") or []] == [S["copy"]],
    )
    c2.type_value(p, "dx", "90")
    c2.type_value(p, "dz", "4")


def paste_ok():
    p = c2.component_panel()
    h.caught_up(p)
    h.task_button("OK")


paste_ok.done = lambda: c2.component_panel() is None
paste_ok.done_what = "Move/Copy closed"


def pasted():
    copy = r.part(S["copy"])
    h.check(
        "8 the pasted compound gear is named after the first",
        S["copy"].startswith("Compound Gear"),
        S["copy"],
    )
    # the report (Tesla Turbine): "Copy/Paste ignores the copied component's position"
    h.check(
        "8 it stands 90 along X and 4 higher: on the second axle",
        hole_axis(copy) == [(APART, 0.0)],
        hole_axis(copy),
    )
    r.box_is(
        "8 ...its big gear at z 4..8, its pinion up to 16",
        copy,
        [APART - 76.5, -76.5, 4, APART + 76.5, 76.5, 16],
        0.05,
    )
    r.box_is(
        "8 the first compound gear did not move",
        r.part("Compound Gear"),
        [-76.5, -76.5, 0, 76.5, 76.5, 12],
        0.05,
    )
    inside = cs.children_of([S["copy"]]) or []
    h.check(
        "8 the copy shows its two gears in the browser",
        sum(1 for x in inside if x.startswith("Spur Gear")) == 2,
        inside,
    )
    r.no_open_step("Paste")
    h.fit()
    h.shot("8-two-compound-gears")


steps += [copy_select, copy_key, paste_key, paste_values, paste_ok, pasted]


# == 9: joints and the motion link =================================================================
def as_built(tag, gear_label, rim_at, name, on_gear=False):
    """Steps: As-built Joint, the gear's and the Axles' browser rows, Type Revolute, the
    position on the end of the axle the gear turns on (its centre lights up)."""

    def label():
        return gear_label() if callable(gear_label) else gear_label

    def command():
        h.click_empty()
        h.fit()
        S["before"] = bj.place(r.part(label()))
        j.menu("As-built Joint")

    command.done = lambda: j.panel() is not None
    command.done_what = "the As-built Joint dialog is open"

    def rows():
        t.click_row(label())
        h.settle()
        t.click_row("Axles")

    def kind():
        p = j.panel()
        h.check(
            "%s: %s and Axles are taken" % (tag, label()),
            [x.Label for x in p.parts] == [label(), "Axles"],
            [x.Label for x in p.parts],
        )
        h.check("%s: Type Revolute chosen" % tag, j.choose_type(p, "Revolute"))

    def aim():
        if on_gear:
            # the rim of the pinion's hole: an edge of a gear INSIDE the compound gear
            bj.hover_edge(bj.rim((rim_at.x, rim_at.y), 2.0, rim_at.z, 250))
        else:
            bj.hover_point(rim_at)

    def position():
        hov = bj.hover_of(j.panel())
        spot = bj.hot(j.panel())
        h.check(
            "%s: the centre of the %s is lit" % (tag, "hole's rim" if on_gear else "axle's end"),
            spot is not None and (spot["point"] - rim_at).Length < 1e-4,
            (spot and (spot["kind"], spot["point"]), hov and hov.pick),
        )
        if on_gear:
            h.click_edge(bj.rim((rim_at.x, rim_at.y), 2.0, rim_at.z, 250))
        else:
            h.click(rim_at)

    def ok():
        p = j.panel()
        h.check(
            "%s: %s is previewed, nothing wrong said" % (tag, name),
            bj.joint(name) is not None and p.message.text() == "",
            (bj.labels(), p.message.text()),
        )
        j.ok()

    ok.done = lambda: j.panel() is None
    ok.done_what = "the As-built Joint dialog closed"

    def made():
        joint = bj.joint(name)
        h.check("%s: %s made" % (tag, name), joint is not None and joint.JointType == "Revolute")
        h.check(
            "%s: the gear did not move" % tag, not bj.moved(bj.place(r.part(label())), S["before"])
        )
        h.check(
            "%s: the solver is happy" % tag, jm().solve(r.doc()) == 0, jm().broken_joints(r.doc())
        )
        r.no_open_step("As-built Joint")

    return [
        r.named(x, "%s_%s" % (tag, x.__name__))
        for x in (command, rows, kind, aim, position, ok, made)
    ]


def link_command():
    h.click_empty()
    j.menu("Motion Link")


link_command.done = lambda: j.panel() is not None and j.panel().title == "Motion Link"
link_command.done_what = "the Motion Link dialog is open"


def link_pick():
    t.click_row("Revolute 1")
    h.settle()
    t.click_row("Revolute 2")


def link_values():
    p = j.panel()
    h.check(
        "9 both joints are taken",
        p.picked == [bj.joint("Revolute 1"), bj.joint("Revolute 2")],
        p.picked,
    )
    captions = [row["caption"].text() for row in p.rows]
    h.check("9 each joint's rotation gets a value", len(captions) == 2, captions)
    # 20 teeth drive 100: a full turn of the first compound gear's pinion turns the
    # second one's big gear a fifth of a turn, the other way
    bodies_steps.type_value(p.rows[0]["field"].widget, "360")
    bodies_steps.type_value(p.rows[1]["field"].widget, "72")
    bodies_steps.toggle(p.reverse)


def link_animate():
    p = j.panel()
    h.caught_up(p)
    h.check(
        "9 a link is previewed, Reverse ticked",
        p.link is not None and p.reverse.isChecked(),
        p.message.text(),
    )
    S["home"] = [bj.place(r.part(n)) for n in ("Compound Gear", S["copy"])]
    w.click(p.animate)
    S["samples"] = sample_two(lambda: j.panel().animator)


def sample_two(get_animator):
    """Both joints' angles at every frame of a playing animation (one cycle)."""
    import time

    from fission180 import joints_ui

    out = []
    one, two = bj.joint("Revolute 1"), bj.joint("Revolute 2")

    def look():
        animator = get_animator()
        if animator is None or not animator.running:
            return True
        pair = (jm().value(one)[0], jm().value(two)[0])
        if not out or out[-1] != pair:
            out.append(pair)
        return time.perf_counter() - animator.started >= joints_ui.ANIMATION_SECONDS

    h.wait_for(look, "the animation to play a cycle")
    return out


def ratio_held(samples):
    return [x for x in samples if abs(x[1] + x[0] / 5.0) > 1e-4]


def link_watched():
    samples = S.get("samples") or []
    h.check("9 Animate plays", len(samples) >= 5, len(samples))
    h.check("9 the first gear turns", bj.spread(x[0] for x in samples) > 40)
    h.check(
        "9 the second turns a fifth of it, the other way, at every frame",
        not ratio_held(samples),
        ratio_held(samples)[:3],
    )
    h.shot("9-animating")
    w.click(j.panel().animate)


link_animate.while_busy = link_watched.while_busy = True


def link_ok():
    p = j.panel()
    h.check("9 Animate stopped", p.animator is None)
    now = [bj.place(r.part(n)) for n in ("Compound Gear", S["copy"])]
    h.check(
        "9 both gears stand where they were",
        not any(bj.moved(a, c) for a, c in zip(now, S["home"])),
    )
    j.ok()


link_ok.done = lambda: j.panel() is None
link_ok.done_what = "the Motion Link dialog closed"


def link_made():
    links = jm().motion_links(r.doc())
    h.check(
        "9 Motion Link 1 ties the two joints",
        len(links) == 1
        and links[0].Joint1 is bj.joint("Revolute 1")
        and links[0].Joint2 is bj.joint("Revolute 2"),
    )
    h.check(
        "9 it is in the browser's Joints folder", "Motion Link 1" in (t.children("Joints") or [])
    )
    r.no_open_step("Motion Link")


# == 10: Animate Joint Relationships, Drive Joints, save ===========================================
def relations():
    j.browser_menu("Revolute 1", "Animate Joint Relationships")
    S["all"] = sample_two(bj.standalone_animator)


def relations_watched():
    from Fission180Tests.gui import blend_steps

    samples = S.get("all") or []
    h.check("10 Animate Joint Relationships plays", len(samples) >= 5, len(samples))
    h.check("10 the first gear turns", bj.spread(x[0] for x in samples) > 40)
    h.check(
        "10 the second follows by the gear ratio", not ratio_held(samples), ratio_held(samples)[:3]
    )
    blend_steps.press_guarded(QtCore.Qt.Key_Escape)


relations.while_busy = relations_watched.while_busy = True


def drive_open():
    now = [bj.place(r.part(n)) for n in ("Compound Gear", S["copy"])]
    h.check(
        "10 Esc: both gears stand where they were",
        not any(bj.moved(a, c) for a, c in zip(now, S["home"])),
    )
    j.browser_menu("Revolute 1", "Drive Joints")


drive_open.done = lambda: j.panel() is not None and j.panel().title == "Drive Joints"
drive_open.done_what = "the Drive Joints dialog is open"


def drive_type():
    bodies_steps.type_value(j.panel().angle.widget, "100")


def driven():
    h.caught_up(j.panel())
    one, two = jm().value(bj.joint("Revolute 1"))[0], jm().value(bj.joint("Revolute 2"))[0]
    h.check(
        "10 the first gear at 100 degrees, the second at -20",
        abs(one - 100) < 1e-4 and abs(two + 20) < 1e-4,
        (one, two),
    )
    j.cancel()


driven.done = lambda: j.panel() is None
driven.done_what = "the Drive Joints dialog closed"


def summary():
    now = [bj.place(r.part(n)) for n in ("Compound Gear", S["copy"])]
    h.check(
        "10 Cancel puts both gears back", not any(bj.moved(a, c) for a, c in zip(now, S["home"]))
    )
    r.no_open_step("Drive Joints")
    top = [x for x in k.labels() if k.container_label(r.part(x)) == ""]
    h.check(
        "10 the design: Axles and two compound gears",
        top == ["Axles", "Compound Gear", S["copy"]],
        top,
    )
    titles = r.timeline()
    h.check(
        "10 the timeline has Gear 1, Gear 2, the move, the joints and the link",
        all(x in titles for x in ("Gear 1", "Gear 2", "Revolute 1", "Revolute 2", "Motion Link 1")),
        titles,
    )
    h.fit()
    h.shot("10-gear-train")


def save_close():
    S["path"] = os.path.join(tempfile.mkdtemp(prefix="fission180_replay15_"), "gear_train.FCStd")
    r.doc().saveAs(S["path"])
    App.closeDocument(r.doc().Name)


def reopen():
    App.openDocument(S["path"])
    h.fit()


def reopened():
    h.settle()
    h.check("10 reopened: the design is not marked changed", not Gui.ActiveDocument.Modified)
    h.check(
        "10 reopened: two gears, both joints and the link",
        len(gears()) == 2 and len(bj.labels()) == 2 and len(jm().motion_links(r.doc())) == 1,
    )
    h.check(
        "10 reopened: the solver is happy",
        jm().solve(r.doc()) == 0 and not jm().broken_joints(r.doc()),
    )
    r.no_open_step("reopening")


steps += as_built("j1", "Compound Gear", V(0, 0, AXLE_L), "Revolute 1")
steps += as_built("j2", lambda: S["copy"], V(APART, 0, AXLE_L), "Revolute 2", on_gear=True)
steps += [link_command, link_pick, link_values, link_animate, link_watched, link_ok, link_made]
steps += [relations, relations_watched, drive_open, drive_type, driven, summary]
steps += [save_close, reopen, reopened]

h.run("replay_15_gear_train", steps, paced_by="state")
