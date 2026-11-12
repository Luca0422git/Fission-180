# SPDX-License-Identifier: LGPL-2.1-or-later
"""A beginner's first part, compared with the released 0.1.0-beta.3.3.10 (builder regress,
wave 7): only real input, checked on the model and on the screen.

1. Create Sketch on XY, R, two corners, D 40 and 30; Finish Sketch: the rectangle shows.
2. E, 10, OK: the first body, 40 x 30 x 10, drawn where it is.
3. Create Sketch on the top face, C, a circle d 10 at (30, 15); Finish: the circle shows.
4. E, 5: Join is proposed (it builds on the part); OK: one body with a boss.
5. Create Sketch on the top face, a circle d 8 at (10, 15); E, -4: Cut is proposed (into the
   part); OK: a pocket.

Hand-derived: 40*30*10 = 12000; boss pi 5^2 5; pocket pi 4^2 4.
"""

import math

import FreeCAD as App

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import regress_steps as r

V = App.Vector
s = {}
BOX = 12000.0
BOSS = math.pi * 25.0 * 5.0
POCKET = math.pi * 16.0 * 4.0


def first_body(s):
    bodies = r.bodies()
    h.check("one body", len(bodies) == 1, r.bodies_summary())
    if not bodies:
        return
    s["body"] = bodies[0]
    h.check("40 x 30 x 10", r.close(r.volume(bodies[0]), BOX), r.volume(bodies[0]))
    r.body_drawn(V(20, 15, 10), bodies[0], "the top of the box")
    r.body_drawn(V(20, 0, 5), bodies[0], "the front of the box")
    sk = r.sketches()[0]
    r.info("the extruded sketch is shown: %s" % r.shown(sk))


def joined(s):
    bodies = r.bodies()
    h.check("still one body (Join)", len(bodies) == 1, r.bodies_summary())
    v = r.volume(s["body"])
    h.check("the boss joined: 12000 + pi 25 5", r.close(v, BOX + BOSS), v)
    h.check("one solid", r.solids(s["body"]) == 1, r.solids(s["body"]))
    r.body_drawn(V(30, 15, 15), s["body"], "the top of the boss")
    r.body_drawn(V(20, 5, 10), s["body"], "the top of the box beside the boss")


def cut(s):
    bodies = r.bodies()
    h.check("still one body (Cut)", len(bodies) == 1, r.bodies_summary())
    v = r.volume(s["body"])
    h.check("the pocket cut: - pi 16 4", r.close(v, BOX + BOSS - POCKET), v)
    r.body_drawn(V(20, 5, 10), s["body"], "the top of the box after the pocket")
    r.body_drawn(V(10, 15, 6), s["body"], "the floor of the pocket")


def last_look():
    h.fit()
    r.away()
    h.shot("end")
    r.body_drawn(V(30, 15, 15), s["body"], "at the end, the boss")


steps = r.new_design("RegressFirst", s)
steps += r.sketch_on_plane("a", s)
steps += r.rectangle("a", s, V(0, 0, 0), V(40, 30, 0), 40, 30)
steps += r.finish_sketch("a", s, r.rect_bottom_mid)
steps += r.extrude("b", s, 10, check=first_body)
steps += r.sketch_on_face("c", s, V(20, 25, 10))
steps += r.circle("c", s, V(30, 15, 10), 5)
steps += r.finish_sketch("c", s, r.circle_rim)
steps += r.extrude("d", s, 5, expect_op="Join", check=joined)
steps += r.sketch_on_face("e", s, V(15, 5, 10))
steps += r.circle("e", s, V(10, 15, 10), 4)
steps += r.finish_sketch("e", s, r.circle_rim)
steps += r.extrude("e", s, -4, expect_op="Cut", check=cut)
steps += [last_look]

h.run("regress_first_part", steps, paced_by="state")
