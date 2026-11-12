# SPDX-License-Identifier: LGPL-2.1-or-later
"""A sketch on an offset plane, compared with the released 0.1.0-beta.3.3.10 (builder regress,
wave 7): only real input, checked on the model and on the screen.

1. A block 40 x 30 x 10.
2. CONSTRUCT > Offset Plane, click the top face, type 15, OK: a plane at z 25, drawn.
3. Create Sketch, click the plane (beside the part): the sketch is on it; a circle d 10 at
   (20, 15); Finish Sketch: the circle is drawn up there.
4. E, 5 (up, away from the part): New Body, z 25..30, drawn above the block.
5. A second sketch on the plane, a circle d 6 at (8, 8); E, -15 (down onto the block's top):
   it starts in the air and ends on the top face: Join (it builds on the body).

Hand-derived: block 12000; cylinder pi 5^2 5; post pi 3^2 15.
"""

import math

import FreeCAD as App

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import inspect_steps as ins
from Fission180Tests.gui import regress_steps as r

V = App.Vector
s = {}
BOX = 12000.0
DISC = math.pi * 25.0 * 5.0
POST = math.pi * 9.0 * 15.0


def a_made(s):
    h.check("the block", r.close(r.total_volume(), BOX), r.bodies_summary())


def b_open():
    h.click_empty()
    h.fit()
    r.menu("CONSTRUCT", "Offset Plane")


def b_click_top():
    p = ins.construct_panel()
    h.check("the Offset Plane dialog is open", p is not None)
    h.fit()
    h.click(V(20, 15, 10))


def b_type():
    p = ins.construct_panel()
    if h.check("a plane is previewed", p is not None and p.datum is not None):
        ins.type_into(p.distance.widget, "15")


def b_ok():
    h.task_button("OK")


def b_made():
    planes = ins.datums()
    h.check("one construction plane", len(planes) == 1, planes)
    if not planes:
        return
    s["plane"] = planes[0]
    z = planes[0].getGlobalPlacement().Base.z
    h.check("the plane is at z 25", r.close(z, 25.0), planes[0].getGlobalPlacement())
    h.check("the plane is shown", r.shown(planes[0]))
    h.fit()
    r.away()
    picked = r.picked_at(r.V(20, 15, 25))
    r.info("picked on the plane: %s" % (picked,))
    h.check(
        "the plane is drawn above the part",
        picked is not None and picked[0] == planes[0].Name,
        picked,
    )
    h.shot("b-plane")


def c_create_sketch():
    h.click_empty()
    h.fit()
    h.ribbon("Create Sketch")


def c_click_plane():
    # the plane is above the part: a click there takes the plane, in front of the part
    s["plane_spot"] = V(30, 22, 25)
    h.fit()
    h.click(s["plane_spot"])


def c_open():
    sk = h.in_sketch()
    s["sk"] = sk
    ok = sk is not None and r.close(sk.getGlobalPlacement().Base.z, 25.0)
    h.check("the sketch is on the offset plane (z 25)", ok, sk and sk.getGlobalPlacement())
    r.info("sketch support: %s" % (sk and [o.Name for o, _e in sk.AttachmentSupport],))


def d_made(s):
    bodies = r.bodies()
    h.check("a second body", len(bodies) == 2, r.bodies_summary())
    if len(bodies) < 2:
        return
    s["b2"] = bodies[1]
    h.check("a disc d 10 x 5", r.close(r.volume(bodies[1]), DISC), r.bodies_summary())
    bb = bodies[1].Shape.BoundBox
    h.check("from z 25 to 30", r.close(bb.ZMin, 25.0) and r.close(bb.ZMax, 30.0), bb)
    h.fit()
    r.body_drawn(V(20, 15, 30), bodies[1], "the disc up on the plane")
    r.body_drawn(V(35, 5, 10), bodies[0], "the block below")


def e_create_sketch():
    h.click_empty()
    h.fit()
    h.ribbon("Create Sketch")


def e_click_plane():
    h.fit()
    h.click(s["plane_spot"])


def e_open():
    sk = h.in_sketch()
    s["sk"] = sk
    ok = sk is not None and r.close(sk.getGlobalPlacement().Base.z, 25.0)
    h.check("the second sketch is on the offset plane", ok, sk and sk.getGlobalPlacement())


def f_made(s):
    bodies = r.bodies()
    h.check("still two bodies (Join)", len(bodies) == 2, r.bodies_summary())
    h.check(
        "the post joined the block", r.close(r.volume(bodies[0]), BOX + POST), r.bodies_summary()
    )
    r.body_drawn(V(8, 8, 25), bodies[0], "the top of the post")


steps = r.new_design("RegressOffset", s)
steps += r.box("a", s, 0, 0, 40, 30, 10, check=a_made)
steps += [b_open, b_click_top, b_type, b_ok, b_made]
steps += [c_create_sketch, c_click_plane, c_open]
steps += r.circle("c", s, V(20, 15, 25), 5)
steps += r.finish_sketch("c", s, r.circle_rim)
steps += r.extrude("d", s, 5, expect_op="New Body", check=d_made)
steps += [e_create_sketch, e_click_plane, e_open]
steps += r.circle("e", s, V(8, 8, 25), 3)
steps += r.finish_sketch("e", s, r.circle_rim)
steps += r.extrude("f", s, -15, expect_op="Join", check=f_made)

h.run("regress_offset_plane", steps, paced_by="state")
