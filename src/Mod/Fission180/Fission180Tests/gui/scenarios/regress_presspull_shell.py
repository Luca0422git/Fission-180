# SPDX-License-Identifier: LGPL-2.1-or-later
"""Press Pull and Shell on a block, compared with the released 0.1.0-beta.3.3.10 (builder
regress, wave 7): only real input, checked on the model and on the screen.

1. A block 40 x 30 x 10.
2. Click the top face, Q (Press Pull), type 5, OK: the block is 15 high, drawn up there.
3. Click the front face, Q, type -2, OK: the front goes back 2 mm (30 -> 28 deep).
4. MODIFY > Shell, click the top face, type 2, OK: an open box with 2 mm walls; the view
   looks into it (its floor is drawn 2 mm above the bottom).
5. Ctrl+Z: the solid block again; Ctrl+Y: the open box.

Hand-derived: 40 x 28 x 15 = 16800; the shell leaves 16800 - 36 x 24 x 13 = 5568.
"""

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import regress_steps as r
from Fission180Tests.gui import shell_draft_steps as sd

V = App.Vector
s = {}


def body():
    return r.bodies()[0]


def pp_panel():
    from fission180 import presspull_ui

    p = presspull_ui.PressPullPanel.last
    return None if p is None or p._closed else p


def a_made(s):
    h.check("the block", r.close(r.total_volume(), 12000.0), r.bodies_summary())


def b_click_top():
    Gui.Selection.clearSelection()
    h.fit()
    h.click(V(20, 15, 10))


def b_q():
    h.press("q")


def b_type():
    p = pp_panel()
    if h.check("Q opens Press Pull on the top face", p is not None):
        b.type_into(p.field.widget, "5")


def b_ok():
    h.task_button("OK")


def b_made():
    v = r.volume(body())
    h.check("15 high", r.close(v, 18000.0), v)
    h.check("one body", len(r.bodies()) == 1, r.bodies_summary())
    r.info("timeline after Press Pull: %s" % r.timeline_titles())
    h.fit()
    r.away()
    r.body_drawn(V(20, 15, 15), body(), "the new top")
    h.shot("b-pulled")


def c_click_front():
    Gui.Selection.clearSelection()
    h.fit()
    h.click(V(20, 0, 7))


def c_q():
    h.press("q")


def c_type():
    p = pp_panel()
    if h.check("Q opens Press Pull on the front face", p is not None):
        b.type_into(p.field.widget, "-2")


def c_ok():
    h.task_button("OK")


def c_made():
    v = r.volume(body())
    h.check("the front went back 2 mm", r.close(v, 16800.0), v)
    bb = body().Shape.BoundBox
    h.check("from y 2", r.close(bb.YMin, 2.0), bb)
    h.fit()
    r.away()
    r.body_drawn(V(20, 2, 7), body(), "the front, 2 mm back")


def d_open():
    Gui.Selection.clearSelection()
    h.fit()
    r.menu("MODIFY", "Shell")


def d_click_top():
    p = sd.shell_panel()
    h.check("the Shell dialog is open", p is not None)
    h.click(V(20, 15, 15))


def d_type():
    p = sd.shell_panel()
    if h.check("the top face is picked", p is not None and len(p.names()) == 1):
        sd.type_into(p.inside.widget, "2")


def d_ok():
    h.shot("d-preview")
    h.task_button("OK")


def d_made():
    v = r.volume(body())
    h.check("an open box with 2 mm walls", r.close(v, 5568.0), v)
    h.fit()
    r.away()
    picked, mean, top = r.look(V(20, 16, 2))
    h.check(
        "its floor is drawn (seen through the open top)",
        picked is not None and r.part_of(picked[0], body()),
        (picked, mean, top),
    )
    h.shot("d-shelled")


def e_undo():
    r.undo()


def e_undone():
    v = r.volume(body())
    h.check("Ctrl+Z: the solid block", r.close(v, 16800.0), v)
    r.away()
    r.body_drawn(V(20, 16, 15), body(), "the top after Ctrl+Z")


def e_redo():
    r.redo()


def e_redone():
    v = r.volume(body())
    h.check("Ctrl+Y: the open box", r.close(v, 5568.0), v)


steps = r.new_design("RegressPressPull", s)
steps += r.box("a", s, 0, 0, 40, 30, 10, check=a_made)
steps += [b_click_top, b_q, b_type, b_ok, b_made]
steps += [c_click_front, c_q, c_type, c_ok, c_made]
steps += [d_open, d_click_top, d_type, d_ok, d_made]
steps += [e_undo, e_undone, e_redo, e_redone]

h.run("regress_presspull_shell", steps, paced_by="state")
