# SPDX-License-Identifier: LGPL-2.1-or-later
"""Probe (not committed)."""

import math

import FreeCAD as App

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import book_components_steps as k
from Fission180Tests.gui import fillet2_steps as f2
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import hole_steps as hs
from Fission180Tests.gui import inspect_steps as ins
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
)

h.run("replay_27_hilt", steps, paced_by="state")
