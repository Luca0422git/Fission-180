# SPDX-License-Identifier: LGPL-2.1-or-later
"""Probe (not committed)."""

import math
import os

import FreeCAD as App
from PySide import QtCore
from PySide6 import QtTest

from Fission180Tests.gui import animation_steps as a
from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import book_components_steps as k
from Fission180Tests.gui import book_hardware_steps as bh
from Fission180Tests.gui import drawing_input as d
from Fission180Tests.gui import fillet2_steps as f2
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import hole_steps as hs
from Fission180Tests.gui import inspect_steps as ins
from Fission180Tests.gui import joints_steps as j
from Fission180Tests.gui import looks_steps as lk
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import replay_g_steps as r
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import timeline_input as t
from Fission180Tests.gui import viewcube_input as vc

V = App.Vector
S = {}
C45 = math.cos(math.radians(45))


def ring(radius, z, degrees=-45.0):
    a = math.radians(degrees)
    return V(radius * math.cos(a), radius * math.sin(a), z)


def chamfer_ring(c, radius=16.0):
    """What a chamfer of size c takes off an outer round edge of that radius."""
    return math.pi * c * c * (radius - c / 3.0)


GRIP = r.tube(32, 26, 120)
GRIP_CHAMFERED = GRIP - chamfer_ring(0.4) - chamfer_ring(2.0)


def grip_made():
    h.check("Grip: a 32 x 26 tube, 120 long", r.near(r.vol("Grip"), GRIP), r.vol("Grip"))
    k.box_is("Grip: stands on the XY plane", r.body_in("Grip"), [-16, -16, 0, 16, 16, 120])
    h.check("Grip: one body, in Grip", len(k.bodies_of("Grip")) == 1 and not k.bodies_of(""))
    h.shot("grip")


# -- Chamfer: two selection sets in one feature (report 2566) ----------------------------------
def chamfer_start():
    h.click_empty()
    h.fit()
    h.ribbon("Chamfer")


chamfer_start.done = lambda: b.blend_panel() is not None
chamfer_start.done_what = "the Chamfer dialog is open"


def chamfer_top_edge():
    h.check("Chamfer: the top outer edge clicked", h.click_edge(ring(16, 120)))


def chamfer_small():
    p = b.blend_panel()
    if h.check("Chamfer: set 1 has the edge", p is not None and len(p.refs) == 1, p and p.refs):
        b.type_into(p.distance.widget, "0.4")
        h.caught_up(p)


def chamfer_plus():
    p = b.blend_panel()
    h.check(
        "Chamfer: 0.4 mm previewed",
        r.near(r.vol("Grip"), GRIP - chamfer_ring(0.4), 1e-6),
        r.vol("Grip"),
    )
    f2.press_plus(p)


def chamfer_bottom_edge():
    p = b.blend_panel()
    h.check("Chamfer: '+' adds set 2", p is not None and p.rows.count() == 2, f2.row_texts(p))
    h.check("Chamfer: the bottom outer edge clicked", h.click_edge(ring(16, 0)))


def chamfer_big():
    p = b.blend_panel()
    if h.check("Chamfer: set 2 has its edge", p is not None and len(p.refs) == 1, p and p.refs):
        b.type_into(p.distance.widget, "2")
        h.caught_up(p)


def chamfer_ok():
    h.check("Chamfer: no error", "⚠" not in r.message(), r.message())
    h.task_button("OK")


chamfer_ok.done = lambda: b.blend_panel() is None
chamfer_ok.done_what = "the Chamfer dialog closed"


def chamfer_made():
    h.check(
        "Chamfer: 0.4 mm on top and 2 mm at the bottom, one feature",
        r.near(r.vol("Grip"), GRIP_CHAMFERED, 1e-6),
        (r.vol("Grip"), GRIP_CHAMFERED),
    )
    titles = [x for x in t.titles() if "Chamfer" in x]
    h.check("Chamfer: ONE step in the timeline", len(titles) == 1, t.titles())
    r.nothing_broken("Chamfer")
    h.shot("chamfer")


# -- Emitter -----------------------------------------------------------------------------------
def emitter_sketch_look():
    sk = r.sketch()
    if not h.check("Emitter: sketch open", sk is not None):
        return
    h.check("Emitter: the sketch is in Emitter", k.container_label(sk) == "Emitter")
    base = sk.getGlobalPlacement().Base
    h.check("Emitter: the sketch lies on the Grip's top face (z 120)", abs(base.z - 120) < 1e-6)


def emitter_made():
    h.check(
        "Emitter: a 40 mm disc, 30 thick",
        r.near(r.vol("Emitter"), r.cyl(40, 30), 1e-6),
        r.vol("Emitter"),
    )
    k.box_is("Emitter: on top of the Grip", r.body_in("Emitter"), [-20, -20, 120, 20, 20, 150])
    h.check("Emitter: the Grip was not touched", r.near(r.vol("Grip"), GRIP_CHAMFERED, 1e-6))
    h.check("Emitter: still the active component", k.active_label() == "Emitter")
    h.shot("emitter")


def thread_start():
    h.click_empty()
    h.fit()
    si.menu_item("CREATE", "Thread")


thread_start.done = lambda: hs.thread_panel() is not None
thread_start.done_what = "the Thread dialog is open"


def thread_face():
    h.click(ring(20, 135))


def thread_ok():
    p = hs.thread_panel()
    if h.check("Thread: previewed", p is not None and p.target is not None, hs.message(p)):
        print("THREAD", p.designation.currentText(), p.standard.currentText(), flush=True)
        h.check("Thread: no error", "⚠" not in hs.message(p), hs.message(p))
    h.task_button("OK")


thread_ok.done = lambda: hs.thread_panel() is None
thread_ok.done_what = "the Thread dialog closed"


def thread_made():
    from fission180 import thread

    found = [o for o in k.doc().Objects if thread.is_thread(o)]
    h.check("Thread: one Thread step", len(found) == 1, [o.Label for o in found])
    if found:
        h.check("Thread: in Emitter", k.container_label(found[0]) == "Emitter")
    r.nothing_broken("Thread")
    h.shot("thread")


# -- Pommel: Project (P) the Grip's bottom edge from another component -------------------------
def look_from_top_front():
    vc.click("top-front")  # (the sketch looks down on its plane: the cube shows TOP)


look_from_top_front.done = lambda: "front" in vc.cube().targets() and vc.camera_stopped()
look_from_top_front.done_what = "the cube shows its FRONT face"


def look_from_front():
    vc.click("front")


look_from_front.done = lambda: vc.looks_along(V(0, 1, 0))
look_from_front.done_what = "the view looks at the front"


def tilt_up():
    vc.click("bottom-front")


tilt_up.done = lambda: h.view().getViewDirection().z > 0.3
tilt_up.done_what = "the view looks from below"


def tilted():
    h.fit(iso=False)
    d = h.view().getViewDirection()
    h.check("the view looks at the Grip from below", d.z > 0.3 and d.y > 0.3, d)


def pommel_sketch_look():
    sk = r.sketch()
    if h.check("Pommel: sketch open", sk is not None):
        h.check("Pommel: the sketch is in Pommel", k.container_label(sk) == "Pommel")
        h.check("Pommel: on the XY plane", abs(sk.getGlobalPlacement().Base.z) < 1e-6)


def pommel_projected():
    found = [g for g in r.externals() if "Circle" in g.TypeId]
    if h.check("Pommel: the Grip's bottom edge is a projected circle", len(found) == 1, found):
        h.check(
            "Pommel: 28 across (the 32 tube less its 2 mm chamfer)",
            abs(found[0].Radius - 14.0) < 1e-6,
            found[0].Radius,
        )


POMMEL = r.cyl(36, 15)


def pommel_made():
    h.check("Pommel: 36 across, 15 long", r.near(r.vol("Pommel"), POMMEL, 1e-6), r.vol("Pommel"))
    k.box_is("Pommel: under the Grip", r.body_in("Pommel"), [-18, -18, -15, 18, 18, 0])
    h.check("Pommel: the Grip was not touched", r.near(r.vol("Grip"), GRIP_CHAMFERED, 1e-6))
    h.shot("pommel")


def fillet_start():
    h.click_empty()
    h.press("f")


fillet_start.done = lambda: b.blend_panel() is not None
fillet_start.done_what = "the Fillet dialog is open"


def fillet_edge():
    h.check("Fillet: the Pommel's bottom edge clicked", h.click_edge(ring(18, -15, -90)))


def fillet_radius():
    p = b.blend_panel()
    if h.check("Fillet: the edge is picked", p is not None and len(p.refs) == 1, p and p.refs):
        b.type_into(p.radius.widget, "3")
        h.caught_up(p)


def fillet_ok():
    h.check("Fillet: no error", "⚠" not in r.message(), r.message())
    h.task_button("OK")


fillet_ok.done = lambda: b.blend_panel() is None
fillet_ok.done_what = "the Fillet dialog closed"

FILLET_OFF = 2 * math.pi * (18 - b.xbar(3)) * b.spandrel(3)


def fillet_made():
    h.check(
        "Fillet: 3 mm round on the Pommel's end",
        r.near(r.vol("Pommel"), POMMEL - FILLET_OFF, 1e-5),
        (r.vol("Pommel"), POMMEL - FILLET_OFF),
    )
    r.nothing_broken("Fillet")


POMMEL_STEPS = (
    [r.activate("")]
    + r.new_component("Pommel", grounded=False)
    + r.sketch_on_plane("pommel", "XY_Plane")
    + [pommel_sketch_look]
    # (the sketch turns the view to look down on its plane, as Fusion's does: the Emitter
    # is in the way of the Grip's bottom edge, so a person turns the view with the ViewCube)
    + [look_from_top_front, look_from_front, tilt_up, tilted]
    + r.project("pommel", [lambda: ring(14, 0, -90)])
    + [pommel_projected]
    + r.circle("pommel", (0, 0), 36)
    + [r.finish_sketch("pommel")]
    + r.extrude(
        "pommel",
        [V(3, 0, 0), lambda: ring(16, 0, -90)],
        -15,
        expect_operation="New Body",
        check=pommel_made,
        fit=False,
    )
    + [fillet_start, fillet_edge, fillet_radius, fillet_ok, fillet_made]
)


# -- Switch: an offset plane, a sketch on it, points, Hole From Sketch (report 2570) ----------
def plane_start():
    h.click_empty()
    h.fit()
    h.ribbon("Offset Plane")


plane_start.done = lambda: ins.construct_panel() is not None
plane_start.done_what = "the Offset Plane dialog is open"


def plane_pick():
    pl.click_square("XZ_Plane")


plane_pick.done = lambda: ins.construct_panel() is not None and (
    ins.construct_panel().datum is not None
)
plane_pick.done_what = "the plane shows"


def plane_distance():
    p = ins.construct_panel()
    ins.type_into(p.distance.widget, "-16")
    h.caught_up(p)


def plane_ok():
    p = ins.construct_panel()
    base = p.datum.getGlobalPlacement().Base
    h.check(
        "Offset Plane: -16 from the Front plane is y -16 (towards the viewer)",
        abs(base.y + 16) < 1e-6,
        base,
    )
    h.check("Offset Plane: it is in Switch", k.container_label(p.datum) == "Switch")
    S["plane"] = p.datum.Name
    h.task_button("OK")


plane_ok.done = lambda: ins.construct_panel() is None
plane_ok.done_what = "the Offset Plane dialog closed"


def switch_sketch_start():
    h.click_empty()
    h.fit()
    print("LABELS", t.labels(), flush=True)
    h.ribbon("Create Sketch")


def switch_sketch_plane():
    t.click_row(k.doc().getObject(S["plane"]).Label)


switch_sketch_plane.done = lambda: h.in_sketch() is not None
switch_sketch_plane.done_what = "a sketch opened on the offset plane"


def switch_sketch_look():
    sk = r.sketch()
    if h.check("Switch: sketch open", sk is not None):
        h.check("Switch: the sketch is in Switch", k.container_label(sk) == "Switch")
        h.check("Switch: on the offset plane", abs(sk.getGlobalPlacement().Base.y + 16) < 1e-6)


SWITCH = 10 * 40 * 5.0


def switch_made():
    h.check("Switch: a 10 x 40 x 5 plate", r.near(r.vol("Switch"), SWITCH, 1e-6), r.vol("Switch"))
    k.box_is("Switch: on the Grip's front", r.body_in("Switch"), [-5, -21, 40, 5, -16, 80])
    h.shot("switch")


def holes_sketch_look():
    sk = r.sketch()
    if h.check("Holes: sketch open", sk is not None):
        h.check("Holes: the sketch is in Switch", k.container_label(sk) == "Switch")
        h.check("Holes: on the plate's front face", abs(sk.getGlobalPlacement().Base.y + 21) < 1e-6)
        S["holes_sketch"] = sk.Name


def hole_start():
    h.click_empty()
    h.fit()
    h.press("h")


hole_start.done = lambda: hs.hole_panel() is not None
hole_start.done_what = "the Hole dialog is open"


def hole_from_sketch():
    p = hs.hole_panel()
    b.choose(p.placement, "From Sketch (Multiple Holes)")


def hole_points():
    for z in (50, 70):
        h.click(V(0, -21, z))
        h.settle()
    p = hs.hole_panel()
    found = hs.centres_all(p.target) if p.target is not None else []
    h.check("Hole: two sketch points picked", len(found) == 2, (found, hs.message(p)))


def hole_simple():
    p = hs.hole_panel()
    if p.tap_type.currentText() != "Simple":
        b.choose(p.tap_type, "Simple")
    print("HOLE", p.extent.currentText(), p.options, flush=True)


def hole_diameter():
    p = hs.hole_panel()
    hs.type_into(p.diameter.widget, "3.4")


def hole_depth():
    p = hs.hole_panel()
    hs.type_into(p.depth.widget, "5")
    h.caught_up(p)


def hole_ok():
    p = hs.hole_panel()
    h.check("Hole: no error", "⚠" not in hs.message(p), hs.message(p))
    h.task_button("OK")


hole_ok.done = lambda: hs.hole_panel() is None
hole_ok.done_what = "the Hole dialog closed"

DRILLED = SWITCH - 2 * math.pi * 1.7**2 * 5


def holes_made():
    h.check(
        "Hole: two 3.4 mm holes through the plate",
        r.near(r.vol("Switch"), DRILLED, 1e-6),
        (r.vol("Switch"), DRILLED),
    )
    found = [x for x in t.titles() if "Hole" in x]
    h.check("Hole: ONE step for both holes", len(found) == 1, t.titles())
    r.nothing_broken("Hole")
    h.shot("holes")


SWITCH_STEPS = (
    [r.activate("")]
    + r.new_component("Switch", grounded=False)
    + [plane_start, plane_pick, plane_distance, plane_ok]
    + [switch_sketch_start, switch_sketch_plane, switch_sketch_look]
    + r.center_rectangle("switch", V(0, -16, 60), 10, 40, [-5, -16, 40, 5, -16, 80])
    + [r.finish_sketch("switch")]
    + r.extrude("switch", [V(2, -16, 62)], -5, expect_operation="New Body", check=switch_made)
    + r.sketch_on_face("holes", V(3, -21, 60))
    + [holes_sketch_look]
    + r.points("holes", [V(0, -21, 50), V(0, -21, 70)])
    + [r.finish_sketch("holes")]
    + [hole_start, hole_from_sketch, hole_points, hole_simple, hole_diameter, hole_depth, hole_ok]
    + [holes_made]
)

# -- Screws: INSERT > Hardware stands in for the McMaster-Carr catalogue (report 2579) ---------
SCREW = "M3 x 10 Socket Head Cap Screw"


def hardware_open():
    S["components"] = k.labels()
    bh.open_hardware()


hardware_open.done = bh.is_open
hardware_open.done_what = "the Hardware dialog is open"


def hardware_click():
    p = bh.panel()
    h.check(
        "Hardware: starts on an M3 x 10 socket head screw", p.name.text() == SCREW, p.name.text()
    )
    h.check("Hardware: All holes like it is ticked", p.similar.isChecked())
    h.fit()
    h.check(
        "Hardware: the rim of the lower hole clicked",
        h.click_edge(V(1.7 * C45, -21, 50 - 1.7 * C45)),
    )


def hardware_placed():
    p = bh.panel()
    if not h.check("Hardware: placed", p.target is not None, (p.last_click, p.message.text())):
        return
    found = bh.hw().occurrences(p.target)
    h.check("Hardware: both holes are filled by the one click", len(found) == 2, len(found))
    spots = sorted(round(c.getGlobalPlacement().Base.z, 4) for c in found)
    h.check("Hardware: a screw at z 50 and one at z 70", spots == [50.0, 70.0], spots)
    h.check("Hardware: no error", "⚠" not in p.message.text(), p.message.text())
    h.task_button("OK")


hardware_placed.done = lambda: not bh.is_open()
hardware_placed.done_what = "the Hardware dialog closed"


def hardware_made():
    feature = bh.part_named(SCREW)
    if not h.check("Hardware: the screw is a component", feature is not None, k.labels()):
        return
    made = bh.joints_of(feature)
    h.check("Hardware: two rigid joints hold the screws", len(made) == 2, [x.Label for x in made])
    new = [x for x in k.labels() if x not in S["components"]]
    h.check("Hardware: one component and one more occurrence", new == [SCREW, SCREW + ":2"], new)
    h.check(
        "Hardware: the screws are at the top level, not in Switch",
        all(k.container_label(k.part(x)) == "" for x in new),
        [k.container_label(k.part(x)) for x in new],
    )
    h.check("Hardware: the plate is not cut again", r.near(r.vol("Switch"), DRILLED, 1e-6))
    r.nothing_broken("Hardware")
    h.shot("screws")


# -- As-built joints: the parts were modelled in place ------------------------------------------
def rigid(name, first, first_point, second, second_point):
    def command():
        h.click_empty()
        h.fit()
        S["joints"] = [x.Label for x in j.joint_list()]
        j.menu("As-built Joint")

    command.done = lambda: j.panel() is not None
    command.done_what = "the As-built Joint dialog is open"

    def click_first():
        h.click(first_point)

    def click_second():
        h.click(second_point)

    def ok():
        p = j.panel()
        got = [x.Label for x in p.parts] if p is not None else None
        h.check("As-built %s: %s and %s taken" % (name, first, second), got == [first, second], got)
        h.check(
            "As-built %s: Rigid by default" % name,
            p is not None and p.type_box.currentData() == "rigid",
        )
        j.ok()

    ok.done = lambda: j.panel() is None
    ok.done_what = "the As-built Joint dialog closed"

    def made():
        new = [x for x in j.joint_list() if x.Label not in S["joints"]]
        h.check(
            "As-built %s: one more joint, rigid" % name,
            len(new) == 1 and "Rigid" in new[0].Label,
            [x.Label for x in new],
        )
        h.check(
            "As-built %s: no undo step left open" % name,
            not h.open_undo_step(),
            h.open_undo_step(),
        )
        k.box_is(
            "As-built %s: %s did not move" % (name, first), r.body_in(first), S["boxes"][first]
        )

    out = [command, click_first, click_second, ok, made]
    for fn in out:
        fn.__name__ = "joint_%s_%s" % (name, fn.__name__)
    return out


def remember_boxes():
    S["boxes"] = {x: k.box(r.body_in(x)) for x in ("Grip", "Emitter", "Pommel", "Switch")}


def joints_solved():
    jm = j.joints_module()
    h.check("Joints: the Grip is grounded", jm.is_grounded(k.part("Grip")))
    h.check("Joints: the assembly solves", jm.solve(k.doc()) == 0)
    for label, box in S["boxes"].items():
        k.box_is("Joints: %s is where it was modelled" % label, r.body_in(label), box)
    print("JOINTS", [x.Label for x in j.joint_list()], flush=True)


# -- Physical materials (report 2572: Brass, Gold, ABS) ------------------------------------------
def material_panel():
    p = r.panel()
    return p if p is not None and p.title == "Physical Material" else None


def materials_open():
    h.click_empty()
    h.fit()
    si.menu_item("MODIFY", "Physical Material")


materials_open.done = lambda: material_panel() is not None
materials_open.done_what = "the Physical Material dialog is open"


def material_on(label, part, point, key, density):
    def pick():
        p = material_panel()
        item = p.item_for(label)
        if h.check("Physical Material: %s is in the library" % label, item is not None):
            lk.click_item(p.library, item)

    def click():
        h.click(point)

    def check():
        from fission180 import material

        body = r.body_in(part)
        h.check(
            "Physical Material: the %s is %s" % (part, label),
            material.key_of(body) == key,
            material.key_of(body),
        )
        mass = material.mass(body)
        if density is None:
            h.check("Physical Material: it has a mass", mass is not None and mass > 0, mass)
            return
        want = body.Shape.Volume * density * 1e-6
        h.check(
            "Physical Material: its mass follows (%.1f g)" % (want * 1000),
            mass is not None and abs(mass - want) < 1e-9 + 1e-6 * want,
            (mass, want),
        )

    out = [pick, click, check]
    for fn in out:
        fn.__name__ = "material_%s_%s" % (key, fn.__name__)
    return out


def materials_ok():
    h.task_button("OK")


materials_ok.done = lambda: material_panel() is None
materials_ok.done_what = "the Physical Material dialog closed"


# -- Appearances (report 2568, 2573: powder coat, black metallic paint, LED; Apply To Faces) ----
def looks_open():
    h.click_empty()
    h.fit()
    h.press("a")


looks_open.done = lambda: lk.panel() is not None
looks_open.done_what = "the Appearance dialog is open"


def look_grip():
    h.check(
        "Appearance: A opens it on Bodies/Components",
        lk.panel().apply_to.currentText() == "Bodies/Components",
    )
    h.check(
        "Appearance: the view takes Powder coat, black",
        lk.drop_look("Powder coat, black", ring(16, 25)),
    )


def look_grip_done():
    data = lk.stored(r.body_in("Grip"))
    h.check(
        "Appearance: the Grip is powder coated",
        (data["body"] or {}).get("key") == "powder_black",
        data["body"],
    )


def look_switch():
    h.check(
        "Appearance: the view takes Paint, metallic black",
        lk.drop_look("Paint, metallic black", V(3, -21, 60)),
    )


def look_switch_done():
    data = lk.stored(r.body_in("Switch"))
    h.check(
        "Appearance: the Switch is metallic black",
        (data["body"] or {}).get("key") == "paint_metallic_black",
        data["body"],
    )
    b.choose(lk.panel().apply_to, "Faces")


def look_led():
    h.check("Appearance: Apply To Faces", lk.panel().apply_to.currentText() == "Faces")
    h.check("Appearance: the view takes LED, red", lk.drop_look("LED, red", V(4, -3, 150)))


def look_led_done():
    body = r.body_in("Emitter")
    data = lk.stored(body)
    faces = data["faces"]
    h.check("Appearance: ONE face of the Emitter is LED red", len(faces) == 1, faces)
    h.check(
        "Appearance: ...the Emitter itself keeps its brass",
        (data["material"] or {}).get("key") == "brass" and data["body"] is None,
        data,
    )
    red = [n for n, c in lk.face_colors(body).items() if lk.same(c, (1.0, 0.10, 0.08), 0.05)]
    h.check("Appearance: that face is drawn red", len(red) == 1, lk.face_colors(body))
    h.check("Appearance: no question is open", lk.question() is None)
    h.shot("looks")
    h.task_button("OK")


look_led_done.done = lambda: lk.panel() is None
look_led_done.done_what = "the Appearance dialog closed"


def looks_kept():
    data = lk.stored(r.body_in("Emitter"))
    h.check("Appearance: the LED face is kept after Close", len(data["faces"]) == 1, data["faces"])
    r.nothing_broken("Appearance")


ASSEMBLY_STEPS = (
    [r.activate("")]
    + [hardware_open, hardware_click, hardware_placed, hardware_made, remember_boxes]
    + rigid("emitter", "Emitter", ring(20, 135), "Grip", ring(16, 100))
    + rigid("pommel", "Pommel", ring(18, -8), "Grip", ring(16, 100))
    + rigid("switch", "Switch", V(5, -18.5, 62), "Grip", ring(16, 100))
    + [joints_solved]
    + [materials_open]
    + material_on("Brass", "Emitter", ring(20, 135), "brass", 8.5)
    + material_on("Gold", "Pommel", ring(18, -8), "gold", 19.32)
    + material_on("ABS Plastic", "Switch", V(5, -18.5, 62), "abs", None)
    + [materials_ok]
    + [looks_open, look_grip, look_grip_done, look_switch, look_switch_done, look_led]
    + [look_led_done, looks_kept]
)


# -- The drawing: right-click the design's row > Create Drawing (report 2575) ----------------
def root_label():
    return t.tree().topLevelItem(0).data(1, QtCore.Qt.UserRole)["label"]


def drawing_right_click():
    S["drawings"] = len(d.drawing_module().drawings(k.doc()))
    S["home"] = a.design_placements()
    entries = [e[0] for e in t.row_menu_entries(root_label())]
    h.check("Drawing: the design's row offers Create Drawing", "Create Drawing" in entries, entries)
    t.row_menu(root_label(), "Create Drawing")


drawing_right_click.done = lambda: d.panel_of("CreateDrawingPanel") is not None
drawing_right_click.done_what = "the Create Drawing dialog is open"


def drawing_dialog():
    p = d.panel_of("CreateDrawingPanel")
    print(
        "DRAWING",
        p.contents.currentText(),
        p.sheet.currentText(),
        p.views.currentText(),
        p.standard.currentText(),
        flush=True,
    )
    h.check(
        "Drawing: the whole design is drawn (Full Assembly)",
        p.contents.currentText() == "Full Assembly",
        p.contents.currentText(),
    )
    d.ok()


drawing_dialog.done = lambda: d.panel_of("BaseViewPanel") is not None
drawing_dialog.done_what = "the Base View dialog follows"


def drawing_place():
    h.check(
        "Drawing: a new drawing", len(d.drawing_module().drawings(k.doc())) == S["drawings"] + 1
    )
    h.check("Drawing: the DRAWING workspace shows", d.page() is not None)
    d.move_to(110, 150)
    d.click_at(100, 140)


def drawing_base_ok():
    p = d.panel_of("BaseViewPanel")
    if h.check("Drawing: Base View dialog", p is not None, d.panel()):
        print("BASE", p.scale.currentText(), p.orientation.currentText(), flush=True)
    d.ok()


drawing_base_ok.done = lambda: d.panel() is None
drawing_base_ok.done_what = "the Base View dialog closed"


def drawing_made():
    found = d.bases()
    if not h.check("Drawing: one base view", len(found) == 1, found):
        return
    view = found[0]
    h.check(
        "Drawing: it draws the six bodies (four parts, two screws)",
        len(view.Source) == 6,
        [o.Label for o in view.Source],
    )
    h.check("Drawing: it has lines", d.visible_edge_count(view) > 0)
    S["page"] = d.page().Name
    S["page_label"] = d.page().Label
    h.shot("drawing")
    d.workspace("Design")


drawing_made.done = lambda: d.page() is None
drawing_made.done_what = "the Design workspace is back"


# -- The exploded animation (report 2577, chapter 10) -----------------------------------------
def animation_enter():
    a.enter()


def animation_playhead():
    a.click_time(3.0)


def animation_explode():
    h.ribbon("Auto Explode: One Level")


animation_explode.done = lambda: a.panel() is not None
animation_explode.done_what = "the Auto Explode dialog is open"


def animation_trails():
    a.tick("trails")


def animation_ok():
    a.ok()


animation_ok.done = a.panel_closed
animation_ok.done_what = "the Auto Explode dialog closed"


def animation_made():
    anim = a.anim()
    names = anim.storyboards(k.doc())
    if not h.check("Animation: one storyboard", len(names) == 1, names):
        return
    S["board"] = names[0]
    world = anim.global_placements_at(k.doc(), names[0])
    moved = sorted(
        c.Label
        for c in (k.part(x) for x in k.labels())
        if (world[c.Name].Base - c.getGlobalPlacement().Base).Length > 1.0
    )
    print(
        "EXPLODED",
        {k.doc().getObject(n).Label: tuple(round(v, 1) for v in p.Base) for n, p in world.items()},
        flush=True,
    )
    h.check("Animation: the parts fly apart at the storyboard's end", len(moved) >= 4, moved)
    h.check("Animation: the Grip stays (it is grounded)", "Grip" not in moved, moved)
    from fission180 import animation_view

    off = animation_view.hidden_extras(k.doc())
    plane = k.doc().getObject(S["plane"])
    h.check(
        "Animation: the Switch's offset plane is not drawn here (Fusion shows bodies only)",
        plane.Name in off and plane.ViewObject.Visibility,
        sorted(off),
    )
    marks = [x.Name for x in j.joint_list()]
    h.check("Animation: nor are the joints' marks", all(n in off for n in marks), marks)
    h.shot("exploded")
    a.leave()


def animation_left():
    h.check("Animation: the design itself did not move", a.design_placements() == S["home"])
    for label, box in S["boxes"].items():
        k.box_is("Animation: %s is where it was modelled" % label, r.body_in(label), box)
    h.check("Animation: the design's timeline is back", t.tl().isVisible())
    plane = k.doc().getObject(S["plane"])
    h.check(
        "Animation: back in Design the offset plane is drawn again",
        int(plane.ViewObject.SwitchNode.whichChild.getValue()) >= 0,
    )


# -- The exploded diagram: CREATE > Exploded View on the drawing (report 2530) ------------------
def diagram_open():
    h.check(
        "Diagram: the drawing has a row in the browser", S["page_label"] in t.labels(), t.labels()
    )
    t.double_click_row(S["page_label"])


diagram_open.done = lambda: d.page() is not None and d.page().Name == S["page"]
diagram_open.done_what = "the drawing is open again"


def diagram_command():
    d.group_menu("CREATE", "Exploded View")


diagram_command.done = lambda: d.panel_of("BaseViewPanel") is not None
diagram_command.done_what = "Base View opens for the exploded view"


def diagram_place():
    p = d.panel_of("BaseViewPanel")
    h.check(
        "Diagram: Representation is the storyboard",
        p.representation.currentText() == S["board"],
        p.representation.currentText(),
    )
    d.choose(p.orientation, "Home")  # (an exploded diagram is drawn from the corner view)
    d.move_to(290, 150)
    d.click_at(280, 140)


def diagram_ok():
    d.ok()


diagram_ok.done = lambda: d.panel() is None
diagram_ok.done_what = "the Base View dialog closed"


def drawing_overlaps():
    from fission180 import drawing
    from fission180 import drawing_core as core

    rects = [(v.Label, drawing.view_rect(v, 0.0)) for v in drawing.all_views(d.page())]
    return [
        (n1, n2)
        for i, (n1, r1) in enumerate(rects)
        for n2, r2 in rects[i + 1 :]
        if core.rects_overlap(r1, r2)
    ]


def diagram_made():
    from fission180 import drawing, drawing_exploded

    page = d.page()
    found = [v for v in drawing.base_views(page) if drawing_exploded.is_exploded(v)]
    if not h.check("Diagram: an exploded view beside the plain one", len(found) == 1, found):
        return
    h.check("Diagram: it has lines", d.visible_edge_count(found[0]) > 0)
    tags = list(getattr(found[0], "Fission180TrailTags", []) or [])
    h.check("Diagram: its five trail lines are drawn", len(tags) == 5, tags)
    S["exploded_view"] = found[0].Name
    h.check("Diagram: no view on another", not drawing_overlaps(), drawing_overlaps())


def parts_list_command():
    d.group_menu("TABLES", "Parts List")


parts_list_command.done = lambda: d.panel_of("PartsListPanel") is not None
parts_list_command.done_what = "the Parts List dialog is open"


def parts_list_place():
    p = d.panel_of("PartsListPanel")
    h.check("Parts list: with two views it asks which one", "Click the view" in p.hint.text())
    view = k.doc().getObject(S["exploded_view"])
    d.click_at(view.X.Value + 2.0, view.Y.Value + 2.0)


def parts_list_spot():
    spot = r.free_spot(165.0, 45.0)
    h.check("Parts list: there is a free place on the sheet", spot is not None)
    spot = spot or (20.0, 260.0)
    d.move_to(spot[0] + 6.0, spot[1] - 6.0)
    d.click_at(*spot)


def parts_list_ok():
    p = d.panel_of("PartsListPanel")
    if h.check("Parts list: dialog", p is not None, d.panel()):
        print("PARTS", p.hint.text(), flush=True)
    d.ok()


parts_list_ok.done = lambda: d.panel() is None
parts_list_ok.done_what = "the Parts List dialog closed"


def parts_list_made():
    from fission180 import drawing

    table = drawing.parts_list_of(d.page())
    if not h.check("Parts list: on the sheet", table is not None):
        return
    rows = drawing.table_rows(table)
    print("ROWS", rows, flush=True)
    by = {row["PartNumber"]: row for row in rows}
    h.check("Parts list: five rows (the two screws are one row)", len(rows) == 5, list(by))
    h.check(
        "Parts list: the screw, quantity 2",
        str((by.get(SCREW) or {}).get("Qty")) == "2",
        by.get(SCREW),
    )
    for part, material in (("Emitter", "Brass"), ("Pommel", "Gold"), ("Switch", "ABS Plastic")):
        h.check(
            "Parts list: the %s is %s" % (part, material),
            (by.get(part) or {}).get("Material") == material,
            by.get(part),
        )
    marks = [o for o in drawing.annotations(d.page()) if o.TypeId == drawing.BALLOON]
    h.check("Parts list: five balloons", len(marks) == 5, [m.Text for m in marks])
    h.shot("diagram")


def pdf_command():
    S["out"] = r.out_dir("replay_27_hilt")
    S["opened"] = d.record_opener()
    d.group_menu("EXPORT", "Export PDF")


pdf_command.done = lambda: r.export_dialog() is not None
pdf_command.done_what = "the Export PDF dialog is open"


def pdf_export():
    dlg = r.export_dialog()
    d.type_into(dlg.name, "hilt")
    d.type_into(dlg.folder, S["out"])
    QtTest.QTest.mouseClick(dlg.export_button, QtCore.Qt.LeftButton)


pdf_export.done = lambda: os.path.isfile(os.path.join(S["out"], "hilt.pdf"))
pdf_export.done_what = "the PDF is written"


def pdf_written():
    from fission180 import drawing_pdf

    with open(os.path.join(S["out"], "hilt.pdf"), "rb") as handle:
        data = handle.read()
    h.check(
        "PDF: a PDF of one page", data.startswith(b"%PDF-") and drawing_pdf.page_count(data) == 1
    )
    h.check("PDF: more than an empty sheet", len(data) > 20000, len(data))
    d.workspace("Design")


pdf_written.done = lambda: d.page() is None
pdf_written.done_what = "the Design workspace is back"


def the_end():
    h.check(
        "At the end: the Design workspace, SOLID tab", d.current_tab() == "solid", d.current_tab()
    )
    want = ["Grip", "Emitter", "Pommel", "Switch", SCREW, SCREW + ":2"]
    h.check("At the end: six components", k.labels() == want, k.labels())
    for label, box in S["boxes"].items():
        k.box_is("At the end: %s is where it was modelled" % label, r.body_in(label), box)
    h.check("At the end: the Grip as chamfered", r.near(r.vol("Grip"), GRIP_CHAMFERED, 1e-6))
    r.nothing_broken("At the end")
    h.check("At the end: no undo step left open", not h.open_undo_step(), h.open_undo_step())
    h.fit()
    h.shot("end")


DOCUMENT_STEPS = [
    drawing_right_click,
    drawing_dialog,
    drawing_place,
    drawing_base_ok,
    drawing_made,
    # (the book's Render part of this project is out of scope: no Render workspace)
    animation_enter,
    animation_playhead,
    animation_explode,
    animation_trails,
    animation_ok,
    animation_made,
    animation_left,
    diagram_open,
    diagram_command,
    diagram_place,
    diagram_ok,
    diagram_made,
    parts_list_command,
    parts_list_place,
    parts_list_spot,
    parts_list_ok,
    parts_list_made,
    pdf_command,
    pdf_export,
    pdf_written,
    the_end,
]


steps = (
    r.new_design_steps("hilt")
    + r.new_component("Grip", grounded=True)
    + r.sketch_on_plane("grip", "XY_Plane")
    + r.circle("grip_outer", (0, 0), 32)
    + r.circle("grip_inner", (0, 0), 26)
    + [r.finish_sketch("grip")]
    + r.extrude("grip", [V(14.5, 0, 0)], 120, expect_operation="New Body", check=grip_made)
    + [
        chamfer_start,
        chamfer_top_edge,
        chamfer_small,
        chamfer_plus,
        chamfer_bottom_edge,
        chamfer_big,
        chamfer_ok,
        chamfer_made,
    ]
    + [r.activate("")]
    + r.new_component("Emitter", grounded=False)
    + r.sketch_on_face("emitter", lambda: ring(14.3, 120))
    + [emitter_sketch_look]
    + r.circle("emitter", (0, 0), 40)
    + [r.finish_sketch("emitter")]
    + r.extrude(
        "emitter",
        [V(5, 0, 120), lambda: ring(14.3, 120), lambda: ring(18, 120)],
        30,
        expect_operation="New Body",
        check=emitter_made,
    )
    + [thread_start, thread_face, thread_ok, thread_made]
    + POMMEL_STEPS
    + SWITCH_STEPS
    + ASSEMBLY_STEPS
    + DOCUMENT_STEPS
)

h.run("replay_27_hilt", steps, paced_by="state")
