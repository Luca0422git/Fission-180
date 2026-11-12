# SPDX-License-Identifier: LGPL-2.1-or-later
"""A sketch on an offset plane, compared with the released 0.1.0-beta.3.3.10 (builder regress,
wave 7): only real input, checked on the model and on the screen.

1. A block 40 x 30 x 10.
2. CONSTRUCT > Offset Plane, click the top face, type 15, OK: a plane at z 25, drawn.
3. Create Sketch, click the plane (above the part): the sketch is on it; C, a circle round
   (20, 10) through (30, 10), D 20; Finish Sketch: the circle is drawn up there.
4. E, 5 (up, away from the part): New Body, z 25..30, drawn above the block.
5. A second sketch on the plane, a circle d 20 round the block's corner (40, 30); E, -15
   (down onto the block's top): it starts in the air and ends on the top face: Join (it
   builds on the body); its part beyond the block is drawn.
6. A third sketch on the plane: C, the centre clicked at (20, 15), the rim 5 mm beside it:
   a circle is made (the sketch grid is 10 mm here: with full grid snap the rim landed on
   the centre and FreeCAD made nothing, without a word); Finish Sketch.

The clicks are on crossings of the sketch grid whatever its step (2 or 10 mm), and the
first dimension typed is the size drawn: full grid snap and "scale the sketch at the first
dimension" (a new user's settings) leave the circles where they were clicked. A 5 mm circle
on a 10 mm grid made nothing at all with those settings (the rim landed on the centre): the
fix of builder regress, sketch_infer._apart_from_start.

Hand-derived: block 12000; disc pi 10^2 5; post pi 10^2 15.
"""

import math

import FreeCAD as App
from PySide import QtCore

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import inspect_steps as ins
from Fission180Tests.gui import regress_steps as r
from Fission180Tests.gui import sketch_input as si

V = App.Vector
s = {}
BOX = 12000.0
DISC = math.pi * 100.0 * 5.0
POST = math.pi * 100.0 * 15.0


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
    h.check("a disc d 20 x 5", r.close(r.volume(bodies[1]), DISC), r.bodies_summary())
    bb = bodies[1].Shape.BoundBox
    h.check("from z 25 to 30", r.close(bb.ZMin, 25.0) and r.close(bb.ZMax, 30.0), bb)
    h.fit()
    r.drawn_here(V(20, 10, 30), "the top of the disc up on the plane")
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
    # (its top lies in the plane: the side that hangs beyond the block, towards the viewer)
    r.drawn_here(V(40 + 10 * 0.7071, 30 - 10 * 0.7071, 17), "the side of the post")


def g_create_sketch():
    h.click_empty()
    h.fit()
    h.ribbon("Create Sketch")


def g_click_plane():
    h.fit()
    h.click(s["plane_spot"])


def g_c():
    sk = h.in_sketch()
    h.check("the third sketch is on the plane", sk is not None)
    s["sk"] = sk
    h.press("c")


def g_centre():
    si.click(V(20, 15, 25))


def g_rim():
    si.click(V(25, 15, 25))


def g_esc():
    h.press(QtCore.Qt.Key_Escape)


def g_drawn():
    circles = si.circles(s["sk"], construction=False) if s.get("sk") else []
    h.check("two clicks 5 mm apart made a circle", len(circles) == 1, circles)
    if circles:
        g = circles[0][1]
        r.info("the third circle: centre %s r %g" % (tuple(g.Center), g.Radius))
        h.check("it has a size", g.Radius > 1.0, g.Radius)


def g_finish():
    h.ribbon("Finish Sketch")


def g_left():
    h.check("left the third sketch", h.in_sketch() is None)


steps = r.new_design("RegressOffset", s)
steps += r.box("a", s, 0, 0, 40, 30, 10, check=a_made)
steps += [b_open, b_click_top, b_type, b_ok, b_made]
steps += [c_create_sketch, c_click_plane, c_open]
steps += r.circle("c", s, V(20, 10, 25), 10)
steps += r.finish_sketch("c", s, r.circle_rim)
steps += r.extrude("d", s, 5, expect_op="New Body", check=d_made)
steps += [e_create_sketch, e_click_plane, e_open]
steps += r.circle("e", s, V(40, 30, 25), 10)
steps += r.finish_sketch("e", s, r.circle_rim)
steps += r.extrude("f", s, -15, expect_op="Join", check=f_made)

steps += [g_create_sketch, g_click_plane, g_c, g_centre, g_rim, g_esc, g_drawn, g_finish, g_left]

h.run("regress_offset_plane", steps, paced_by="state")
