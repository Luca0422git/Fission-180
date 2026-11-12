# SPDX-License-Identifier: LGPL-2.1-or-later
"""Rounding and bevelling the edges of a block, compared with the released 0.1.0-beta.3.3.10
(builder regress, wave 7): only real input, checked on the model and on the screen.

1. A block 40 x 30 x 10.
2. F, click the front top edge, type 3, OK: a round of r 3 along 40 mm.
3. MODIFY > Chamfer, click the back top edge, type 2, OK: a chamfer 2 x 2 along 40 mm.
4. Double-click the fillet in the timeline, type 4, OK: the round is r 4.
5. Ctrl+Z: back to r 3; Ctrl+Y: r 4 again.

Hand-derived: a round of r along L removes L r^2 (1 - pi/4); a chamfer of d along L removes
L d^2 / 2.
"""

import math

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import regress_steps as r

V = App.Vector
s = {}
BOX = 12000.0


def round_off(rad, length=40.0):
    return length * rad * rad * (1 - math.pi / 4)


def bevel(d, length=40.0):
    return length * d * d / 2.0


def body():
    return r.bodies()[0]


def a_made(s):
    h.check("the block", r.close(r.total_volume(), BOX), r.bodies_summary())


def b_f():
    Gui.Selection.clearSelection()
    h.fit()
    h.press("f")


def b_click_edge():
    p = b.blend_panel()
    h.check("F opens Fillet", p is not None and p.title == "Fillet", p and p.title)
    h.fit()
    h.click_edge(V(20, 0, 10))


def b_type():
    p = b.blend_panel()
    if h.check("an edge is picked", p is not None and bool(p.refs), p and p.refs):
        b.type_into(p.radius.widget, "3")


def b_ok():
    h.shot("b-preview")
    h.task_button("OK")


def b_made():
    v = r.volume(body())
    h.check("a round of r 3", r.close(v, BOX - round_off(3)), v)
    h.check("the dialog closed", b.blend_panel() is None)
    r.away()
    r.body_drawn(V(20, 15, 10), body(), "the top after the fillet")
    r.body_drawn(V(20, 0, 4), body(), "the front after the fillet")
    s["titles"] = r.timeline_titles()
    r.info("timeline after the fillet: %s" % s["titles"])
    h.shot("b-filleted")


def c_open():
    Gui.Selection.clearSelection()
    h.fit()
    r.menu("MODIFY", "Chamfer")


def c_click_edge():
    p = b.blend_panel()
    h.check("Chamfer opens", p is not None and p.title == "Chamfer", p and p.title)
    h.fit()
    h.click_edge(V(20, 30, 10))


def c_type():
    p = b.blend_panel()
    if h.check("an edge is picked", p is not None and bool(p.refs), p and p.refs):
        b.type_into(p.distance.widget, "2")


def c_ok():
    h.task_button("OK")


def c_made():
    v = r.volume(body())
    h.check("a chamfer of 2", r.close(v, BOX - round_off(3) - bevel(2)), v)
    r.away()
    r.body_drawn(V(20, 15, 10), body(), "the top after the chamfer")
    s["after_c"] = r.timeline_titles()
    r.info("timeline after the chamfer: %s" % s["after_c"])
    h.shot("c-chamfered")


def d_edit():
    titles = r.timeline_titles()
    fillets = [t for t in titles if t.startswith("Fillet")]
    if h.check("the timeline shows the fillet", bool(fillets), titles):
        b.timeline_double_click(fillets[0])


def d_type():
    p = b.blend_panel()
    if h.check("double-click opens the fillet", p is not None and p.title == "Fillet"):
        h.check("with its radius 3", r.close(p.radius.value(), 3.0), p.radius.value())
        b.type_into(p.radius.widget, "4")


def d_ok():
    h.task_button("OK")


def d_made():
    v = r.volume(body())
    h.check("the round is r 4", r.close(v, BOX - round_off(4) - bevel(2)), v)
    h.check("the chamfer is still there", len(body().Shape.Faces) == 8, len(body().Shape.Faces))
    r.away()
    r.body_drawn(V(20, 15, 10), body(), "the top after the edit")
    titles = r.timeline_titles()
    h.check("the edit made no new step", titles == s["after_c"], (titles, s["after_c"]))
    r.info("timeline after the edit: %s" % r.timeline_titles())


def e_undo():
    r.undo()


def e_undone():
    v = r.volume(body())
    h.check("Ctrl+Z: the round is r 3 again", r.close(v, BOX - round_off(3) - bevel(2)), v)
    r.away()
    r.body_drawn(V(20, 15, 10), body(), "after Ctrl+Z")


def e_redo():
    r.redo()


def e_redone():
    v = r.volume(body())
    h.check("Ctrl+Y: r 4 again", r.close(v, BOX - round_off(4) - bevel(2)), v)
    r.away()
    r.body_drawn(V(20, 15, 10), body(), "after Ctrl+Y")
    h.shot("e-end")


steps = r.new_design("RegressFillet", s)
steps += r.box("a", s, 0, 0, 40, 30, 10, check=a_made)
steps += [b_f, b_click_edge, b_type, b_ok, b_made]
steps += [c_open, c_click_edge, c_type, c_ok, c_made]
steps += [d_edit, d_type, d_ok, d_made]
steps += [e_undo, e_undone, e_redo, e_redone]

h.run("regress_fillet_chamfer", steps, paced_by="state")
