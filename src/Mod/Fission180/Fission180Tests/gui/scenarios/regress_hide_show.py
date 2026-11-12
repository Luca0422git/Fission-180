# SPDX-License-Identifier: LGPL-2.1-or-later
"""Hiding and showing bodies and sketches from the browser, compared with the released
0.1.0-beta.3.3.10 (builder regress, wave 7): only real input, checked on the model and on
the screen.

1. A block 40 x 30 x 10 (sketch, two typed sizes, E 10).
2. The body's eye in the browser: the body is no longer drawn; the eye again: drawn.
3. The sketch's eye: Sketch 1 is drawn (its bottom line); its eye again: gone.
4. Right-click the body > Hide: gone; right-click > Show: drawn.
5. A second block beside the first (x 50..70), extruded 10: a New Body of its own; both are
   drawn.
6. Hide the second body with its eye: only the first is drawn; its eye again: drawn.
(A sketch made while the body is hidden is fix-9's case: not here.)
"""

import FreeCAD as App

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import regress_steps as r
from Fission180Tests.gui import timeline_input as tl

V = App.Vector
s = {}
TOP = V(20, 15, 10)
FRONT = V(20, 0, 5)
TOP2 = V(60, 15, 10)


def body1():
    return r.bodies()[0]


def a_made(s):
    h.check("one body 40 x 30 x 10", r.close(r.total_volume(), 12000.0), r.bodies_summary())
    s["sk1"] = r.sketches()[0]


def b_eye_off():
    tl.click_eye(body1().Label)


def b_hidden():
    h.check("the eye hid the body", not r.shown(body1()), r.bodies_summary())
    r.away()
    r.nothing_drawn(TOP, "body hidden with its eye")
    r.nothing_drawn(FRONT, "body hidden with its eye, its front")
    h.shot("b-hidden")


def b_eye_on():
    tl.click_eye(body1().Label)


def b_shown():
    h.check("the eye showed the body", r.shown(body1()), r.bodies_summary())
    r.away()
    r.body_drawn(TOP, body1(), "body shown again with its eye")


def c_sketch_eye_on():
    tl.click_eye(s["sk1"].Label)


def c_sketch_shown():
    h.check("the sketch's eye showed it", r.shown(s["sk1"]))
    r.away()
    r.sketch_drawn(s["sk1"], V(20, 0, 0), "sketch shown with its eye")
    h.shot("c-sketch-shown")


def c_sketch_eye_off():
    tl.click_eye(s["sk1"].Label)


def c_sketch_hidden():
    h.check("the sketch's eye hid it", not r.shown(s["sk1"]))
    r.away()
    r.sketch_not_drawn(s["sk1"], V(20, 0, 0), "sketch hidden with its eye")


def d_menu_hide():
    tl.row_menu(body1().Label, "Hide")


def d_hidden():
    h.check("right-click > Hide hid the body", not r.shown(body1()), r.bodies_summary())
    r.away()
    r.nothing_drawn(TOP, "body hidden from its menu")


def d_menu_show():
    tl.row_menu(body1().Label, "Show")


def d_shown():
    h.check("right-click > Show showed the body", r.shown(body1()), r.bodies_summary())
    r.away()
    r.body_drawn(TOP, body1(), "body shown from its menu")


def e_made(s):
    bodies = r.bodies()
    h.check("a second body", len(bodies) == 2, r.bodies_summary())
    if len(bodies) == 2:
        s["b2"] = bodies[1]
        h.check("each 12000 and 6000", r.close(r.volume(bodies[1]), 6000.0), r.bodies_summary())
        r.body_drawn(TOP, bodies[0], "the first block")
        r.body_drawn(TOP2, bodies[1], "the second block")


def f_eye_off():
    s["undo_before"] = App.ActiveDocument.UndoCount
    tl.click_eye(s["b2"].Label)


def f_hidden():
    h.check("the second body is hidden", not r.shown(s["b2"]), r.bodies_summary())
    r.away()
    r.nothing_drawn(TOP2, "the second body hidden")
    r.body_drawn(TOP, body1(), "the first body still there")
    r.info(
        "hiding with the eye made %d undo steps" % (App.ActiveDocument.UndoCount - s["undo_before"])
    )


def f_eye_on():
    tl.click_eye(s["b2"].Label)


def f_shown():
    h.check("the second body is shown", r.shown(s["b2"]), r.bodies_summary())
    r.away()
    r.body_drawn(TOP2, s["b2"], "the second body shown again")
    h.check("both are still there", r.close(r.total_volume(), 18000.0), r.bodies_summary())
    h.shot("f-end")


steps = r.new_design("RegressHideShow", s)
steps += r.box("a", s, 0, 0, 40, 30, 10, check=a_made)
steps += [b_eye_off, b_hidden, b_eye_on, b_shown]
steps += [c_sketch_eye_on, c_sketch_shown, c_sketch_eye_off, c_sketch_hidden]
steps += [d_menu_hide, d_hidden, d_menu_show, d_shown]
steps += r.box("e", s, 50, 0, 70, 30, 10, expect_op="New Body", check=e_made)
steps += [f_eye_off, f_hidden, f_eye_on, f_shown]

h.run("regress_hide_show", steps, paced_by="state")
