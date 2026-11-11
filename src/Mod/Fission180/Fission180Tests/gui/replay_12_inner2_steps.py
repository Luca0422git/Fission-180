# SPDX-License-Identifier: LGPL-2.1-or-later
"""The Pizza Cutter's Inner Body, second half (replay_12_pizza_cutter; the book parity
report, lines 2013-2021). Kept outside scenarios/ because every file there is run as a
scenario.

  Hole (H) on the far end face, the blue dot dragged onto the centre: Countersink, Tapped,
  ANSI Unified 1/4-20 UNC, Depth 0.625, Countersink Diameter 0.25, Modeled; CONSTRUCT >
  Midplane of the two end faces; CREATE > Mirror, Pattern Type Features, Hole 1 from the
  timeline, Plane 1; Plane 1 hidden; ASSEMBLE > As-built Joint (Rigid) End Cap + Inner
  Body; Unground From Parent on the End Cap, Ground to Parent on the Inner Body.
"""

import math

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import replay_e_steps as r
from Fission180Tests.gui import timeline_input as ti

V = App.Vector
IN = r.IN
S = r.S
PI = math.pi

# -- Hole -----------------------------------------------------------------------------------------
END_FACE = r.gp(4.25, -0.07, 0.11)  # on the far end face, off its centre
END_CENTRE = r.gp(4.25, 0.0, 0.0)
ROUND_FACE = r.gp(2.6, -0.25 * 0.7071, 0.25 * 0.7071)


def hole_panel():
    from Fission180Tests.gui import hole_steps

    return hole_steps.hole_panel()


def hole_key():
    S.setdefault("inner_chamfered", r.vol_in3("Inner Body"))
    Gui.Selection.clearSelection()
    h.fit()
    h.press("h")


hole_key.done = lambda: hole_panel() is not None
hole_key.done_what = "the Hole dialog is open"


def hole_face():
    r.xclick(END_FACE)


def hole_drag_dot():
    from Fission180Tests.gui import x_input as x

    p = hole_panel()
    dot = p.draggers.get("centre") if p is not None else None
    if not h.check("the hole is placed, with its blue dot", dot is not None, p and p.error):
        return
    x.press_drag_release(h.screen_point(dot.point()), h.screen_point(END_CENTRE), steps=14)
    h.settle()


def hole_snapped():
    from Fission180Tests.gui import hole_steps

    p = hole_panel()
    if p is None:
        return
    centre = hole_steps.centre_of(p.target)
    h.check(
        "the dot snapped onto the centre of the end face",
        centre is not None and (centre - END_CENTRE).Length < 1e-6,
        centre,
    )
    texts = (p.pos_x.widget.text(), p.pos_y.widget.text())
    print("[Fission 180] replay hole position boxes: %s" % (texts,), flush=True)
    h.check(
        "X and Y read 0 in inches",
        abs(p.pos_x.value()) < 1e-9 and abs(p.pos_y.value()) < 1e-9 and "in" in texts[0],
        texts,
    )


def combo_texts(combo):
    return [combo.itemText(i) for i in range(combo.count())]


def hole_options():
    p = hole_panel()
    if p is None:
        return
    r.choose(p.hole_type, "Countersink")
    r.choose(p.tap_type, "Tapped")
    h.caught_up(p)


def hole_thread():
    p = hole_panel()
    if p is None:
        return
    # hitch found by the replay: the first tapped hole of an inch design came up as "ISO
    # Metric profile", M6x1 (the Thread tool already followed the design's units)
    h.check(
        "a tapped hole in an inch design starts as ANSI Unified, 1/4-20 UNC",
        p.standard.currentData() == "ansi" and p.designation.currentText().startswith("1/4-20"),
        (p.standard.currentText(), p.size.currentText(), p.designation.currentText()),
    )
    if p.standard.currentData() != "ansi":
        r.choose(p.standard, "ANSI Unified Screw Threads")
    h.caught_up(p)


def hole_size():
    p = hole_panel()
    if p is None:
        return
    if not p.designation.currentText().startswith("1/4-20"):
        want = [t for t in combo_texts(p.size) if t.strip().startswith("1/4")]
        if h.check("the size list has 1/4", bool(want), combo_texts(p.size)[:20]):
            r.choose(p.size, want[0])
            h.caught_up(p)
    p = hole_panel()
    if not p.designation.currentText().startswith("1/4-20"):
        r.choose(p.designation, "1/4-20 UNC")
        h.caught_up(p)


def hole_sizes():
    p = hole_panel()
    if p is None:
        return
    h.check(
        "ANSI Unified 1/4-20 UNC",
        p.standard.currentData() == "ansi" and p.designation.currentText().startswith("1/4-20"),
        (p.standard.currentText(), p.designation.currentText()),
    )
    r.type_field(p.depth.widget, "0.625")
    r.type_field(p.csink_diameter.widget, "0.25")
    r.tick(p.modeled, True)
    h.caught_up(p)


def hole_ready():
    p = hole_panel()
    if p is None:
        return
    h.check("no complaint in the Hole dialog", not p.error, p.error)
    values = (p.depth.value() / IN, p.csink_diameter.value() / IN)
    h.check(
        "Depth 0.625 and Countersink Diameter 0.25 (inches)",
        r.near(values[0], 0.625) and r.near(values[1], 0.25),
        values,
    )


def hole_made():
    r.no_dialog("Hole")
    got = r.vol_in3("Inner Body")
    S["hole_drop"] = S["inner_chamfered"] - got
    # at least the tap drill's bore (0.201 across, 0.625 deep), less than a 0.28 bore
    low, high = PI * 0.1005**2 * 0.6, PI * 0.14**2 * 0.7
    h.check(
        "a tapped hole is cut into the far end",
        low < S["hole_drop"] < high,
        (S["hole_drop"], low, high),
    )
    h.check("one Hole step in the timeline", r.timeline()[-1] == "Hole 1", r.timeline())
    r.all_ok("Inner Body, hole")
    hidden = [x for x in ti.labels() if "Hole" in x and "Sketch" in x]
    # (report: "Each single Hole adds a Hole 1 Sketch row under Sketches; Fusion hides it")
    h.check("no helper sketch of the hole in the browser", not hidden, hidden)
    S["inner_holed"] = got


# -- Midplane and Mirror --------------------------------------------------------------------------
FAR_RING = r.gp(4.25, -0.127, 0.127)  # on the far end face, between the hole and the chamfer
NEAR_FACE = r.gp(0.25, 0.1, 0.1)  # the end face the End Cap's head lies against


def construct_panel():
    from Fission180Tests.gui import inspect_steps

    return inspect_steps.construct_panel()


def midplane_far():
    h.fit()
    r.xclick(FAR_RING)


def hide_cap():
    # the other end face lies against the End Cap's head: a person hides the End Cap (its
    # eye in the browser) to reach it
    ti.click_eye("End Cap")


def look_from_cap():
    view = h.view()
    view.viewLeft()
    view.fitAll()
    h.view_still()


def midplane_near():
    p = construct_panel()
    h.check("the first face is taken", p is not None and p.boxes[1].button.isChecked())
    r.xclick(NEAR_FACE)


def midplane_shown():
    p = construct_panel()
    h.check("the Midplane dialog is still open with both faces", p is not None)
    h.caught_up(p)


def plane():
    for obj in r.doc().Objects:
        if obj.Label.replace(" ", "") == "Plane1":
            return obj
    return None


def midplane_made():
    r.no_dialog("Midplane")
    made = plane()
    if not h.check("Plane 1 is made", made is not None, ti.labels()):
        return
    base = made.getGlobalPlacement().Base
    normal = made.getGlobalPlacement().Rotation.multVec(V(0, 0, 1))
    h.check("halfway along the rod (x = 2.25)", r.near(base.x / IN, 2.25, 1e-6), base)
    h.check("across the rod", abs(abs(normal.x) - 1) < 1e-9, normal)
    owner = r.comps().container_of(made)
    h.check(
        "it belongs to the Inner Body",
        owner is not None and owner.Label == "Inner Body",
        owner and owner.Label,
    )
    ti.click_eye("End Cap")  # shown again


def mirror_panel():
    from Fission180Tests.gui import pattern_steps

    return pattern_steps.panel()


def mirror_open():
    Gui.Selection.clearSelection()
    h.fit()
    h.ribbon("Mirror")


mirror_open.done = lambda: mirror_panel() is not None
mirror_open.done_what = "the Mirror dialog is open"


def mirror_features():
    p = mirror_panel()
    if p.options["pattern_type"] != "features":
        r.choose(p.pattern_type, "Features")


def mirror_hole_step():
    from Fission180Tests.gui import pattern_steps

    pattern_steps.timeline_click("Hole 1")


def mirror_plane_box():
    from Fission180Tests.gui import pattern_steps

    p = mirror_panel()
    h.check(
        "Features: Hole 1 from the timeline",
        p.options["pattern_type"] == "features" and len(p.options["objects"]) == 1,
        (p.options["pattern_type"], p.options["objects"]),
    )
    pattern_steps.click_box("plane")


def mirror_plane():
    from Fission180Tests.gui import bodies_steps

    bodies_steps.click_browser_row("Plane 1")


def mirror_ready():
    p = mirror_panel()
    picked = p.options["plane"]
    h.check(
        "Plane 1 is the mirror plane",
        picked is not None and picked[0] is plane(),
        picked and picked[0].Label,
    )
    h.caught_up(p)


def mirrored():
    r.no_dialog("Mirror")
    got = r.vol_in3("Inner Body")
    drop = S["inner_holed"] - got
    h.check(
        "the mirrored hole takes exactly what the first took",
        r.near(drop, S["hole_drop"], 2e-6),
        (drop, S["hole_drop"]),
    )
    r.all_ok("Inner Body, mirror")


def hide_plane():
    ti.click_eye("Plane 1")


def plane_hidden():
    made = plane()
    h.check("Plane 1 is hidden (Construction)", made is not None and not made.Visibility)
    h.fit()
    h.shot("inner-body")


# -- As-built Joint, grounds ----------------------------------------------------------------------
CAP_BACK = r.gp(0.25, -0.2, 0.3)


def joint_panel():
    from Fission180Tests.gui import joints_steps

    return joints_steps.panel()


def asbuilt_cap():
    r.xclick(CAP_BACK)


def asbuilt_inner():
    r.xclick(ROUND_FACE)


def asbuilt_ok():
    p = joint_panel()
    h.check(
        "End Cap and Inner Body taken",
        p is not None and [x.Label for x in p.parts] == ["End Cap", "Inner Body"],
        p and [x.Label for x in p.parts],
    )
    h.check("Type Rigid", p is not None and p.type_box.currentText() == "Rigid")
    h.task_button("OK")


def joints_now():
    from fission180 import joints

    return [(x.Label, x.JointType) for x in joints.joints(r.doc())]


def asbuilt_made():
    r.no_dialog("As-built Joint")
    h.check(
        "Rigid 1 holds the End Cap on the Inner Body",
        joints_now() == [("Rigid 1", "Fixed")],
        joints_now(),
    )


def unground_cap():
    ti.row_menu("End Cap", "Unground From Parent")


def ground_inner():
    ti.row_menu("Inner Body", "Ground to Parent")


def grounds():
    from fission180 import joints

    h.check("the End Cap is no longer grounded", not joints.is_grounded(r.component("End Cap")))
    h.check("the Inner Body is grounded", joints.is_grounded(r.component("Inner Body")))
    h.check("the joint is satisfied", joints.solve(r.doc()) == 0)


def steps():
    out = [hole_key, hole_face, hole_drag_dot, hole_snapped, hole_options, hole_thread]
    out += [hole_size, hole_sizes, hole_ready, r.ok("inner_hole_ok", 120), hole_made]
    out += [r.menu("CONSTRUCT", "Midplane", "inner_midplane"), midplane_far, hide_cap]
    out += [look_from_cap, midplane_near, midplane_shown, r.ok("inner_midplane_ok")]
    out += [midplane_made]
    out += [mirror_open, mirror_features, mirror_hole_step, mirror_plane_box, mirror_plane]
    out += [mirror_ready, r.ok("inner_mirror_ok", 120), mirrored, hide_plane, plane_hidden]
    out += [r.menu("ASSEMBLE", "As-built Joint", "inner_asbuilt"), asbuilt_cap, asbuilt_inner]
    out += [asbuilt_ok, asbuilt_made, unground_cap, ground_inner, grounds]
    return out
