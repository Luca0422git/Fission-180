# SPDX-License-Identifier: LGPL-2.1-or-later
"""Two bodies, a rename and Combine, compared with the released 0.1.0-beta.3.3.10 (builder
regress, wave 7): only real input, checked on the model, the browser and the screen.

1. A block 40 x 30 x 10, and a second block x 30..70 overlapping it, extruded 10 with
   Operation New Body chosen: two bodies.
2. Click the second body's row in the browser, F2, type "Lid", Enter: it is called Lid in
   the browser and the design.
3. MODIFY > Combine, click the first body (target), click Lid (tool), OK: one block
   70 x 30 x 10, drawn; Lid is used up.
4. Ctrl+Z: two bodies again, both drawn; Ctrl+Y: one.

Hand-derived: 12000 + 12000 - the overlap 10 x 30 x 10 = 21000.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import regress_steps as r
from Fission180Tests.gui import timeline_input as tl
from Fission180Tests.gui import widget_input as w

V = App.Vector
s = {}


def a_made(s):
    h.check("the block", r.close(r.total_volume(), 12000.0), r.bodies_summary())


def b_made(s):
    bodies = r.bodies()
    h.check("two bodies", len(bodies) == 2, r.bodies_summary())
    if len(bodies) == 2:
        s["first"], s["second"] = bodies
        h.check("each 12000", r.close(r.volume(bodies[1]), 12000.0), r.bodies_summary())
        r.body_drawn(V(65, 15, 10), bodies[1], "the second block")
        r.body_drawn(V(5, 15, 10), bodies[0], "the first block")


def c_select_row():
    tl.click_row(s["second"].Label)


def c_f2():
    w.key(tl.tree(), QtCore.Qt.Key_F2)


def c_type():
    field = tl.browser_field()
    if h.check("F2 opens the name field", field is not None and field.isVisible()):
        w.type_text(field, "Lid")
        w.key(field, QtCore.Qt.Key_Return)


def c_renamed():
    h.check("the body is called Lid", s["second"].Label == "Lid", s["second"].Label)
    h.check("the browser says Lid", tl.tree().row("Lid") is not None, tl.labels())
    Gui.Selection.clearSelection()


def d_open():
    h.click_empty()
    h.fit()
    r.menu("MODIFY", "Combine")


def d_target():
    p = r.panel()
    h.check("the Combine dialog is open", p is not None and p.title == "Combine", p)
    h.click(V(5, 15, 10))


def d_tool():
    p = r.panel()
    if p is not None:
        h.check("the first body is the target", p.options["target"] is s["first"])
    h.click(V(65, 15, 10))


def d_ok():
    p = r.panel()
    if p is not None:
        h.check("Lid is the tool", p.options["tools"] == [s["second"]], p.options)
    h.shot("d-preview")
    h.task_button("OK")


def d_joined():
    v = r.volume(s["first"])
    h.check("one block 70 x 30 x 10", r.close(v, 21000.0), r.bodies_summary())
    h.check("Lid is used up (hidden)", not r.shown(s["second"]), r.bodies_summary())
    h.check("6 faces", len(s["first"].Shape.Faces) == 6, len(s["first"].Shape.Faces))
    r.away()
    r.body_drawn(V(65, 15, 10), s["first"], "where Lid was, the combined block")
    r.info("browser after Combine: %s" % tl.labels())
    h.shot("d-combined")


def e_undo():
    r.undo()


def e_undone():
    h.check("Ctrl+Z: two bodies again", r.close(r.volume(s["first"]), 12000.0), r.bodies_summary())
    h.check("Lid shown again", r.shown(s["second"]), r.bodies_summary())
    h.check("still called Lid", s["second"].Label == "Lid", s["second"].Label)
    r.away()
    r.body_drawn(V(65, 15, 10), s["second"], "Lid after Ctrl+Z")


def e_redo():
    r.redo()


def e_redone():
    h.check("Ctrl+Y: one block", r.close(r.volume(s["first"]), 21000.0), r.bodies_summary())
    r.away()
    r.body_drawn(V(65, 15, 10), s["first"], "after Ctrl+Y")


steps = r.new_design("RegressCombine", s)
steps += r.box("a", s, 0, 0, 40, 30, 10, check=a_made)
steps += r.sketch_on_plane("b", s)
steps += r.rectangle("b", s, V(30, 0, 0), V(70, 30, 0), 40, 30)
steps += r.finish_sketch("b", s, r.rect_bottom_mid)
steps += r.extrude("b", s, 10, op="New Body", check=b_made)
steps += [c_select_row, c_f2, c_type, c_renamed]
steps += [d_open, d_target, d_tool, d_ok, d_joined]
steps += [e_undo, e_undone, e_redo, e_redone]

h.run("regress_bodies_combine", steps, paced_by="state")
