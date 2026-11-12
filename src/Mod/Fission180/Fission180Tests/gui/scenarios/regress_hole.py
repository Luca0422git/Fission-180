# SPDX-License-Identifier: LGPL-2.1-or-later
"""Drilling holes in a block, compared with the released 0.1.0-beta.3.3.10 (builder regress,
wave 7): only real input, checked on the model and on the screen.

1. A block 40 x 30 x 10.
2. H, click the top face at (12, 8): a hole there; Diameter 6, Depth 5, Drill Point Flat;
   OK: a blind hole d 6 x 5; the view shows its floor 5 mm down.
3. Click the top face at (30, 20), then H: the hole goes where that click was; Extents All;
   OK: a hole d 6 through the block; the view looks into it.
4. Ctrl+Z: the through hole goes; Ctrl+Y: back.

Hand-derived: block 12000; a hole d x t removes pi (d/2)^2 t.
"""

import math

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import hole_steps as hs
from Fission180Tests.gui import regress_steps as r

V = App.Vector
s = {}
BOX = 12000.0
BLIND = math.pi * 9.0 * 5.0
THROUGH = math.pi * 9.0 * 10.0


def body():
    return r.bodies()[0]


def a_made(s):
    h.check("the block", r.close(r.total_volume(), BOX), r.bodies_summary())


def b_h():
    Gui.Selection.clearSelection()
    h.fit()
    h.press("h")


def b_click_top():
    p = hs.hole_panel()
    h.check("H opens Hole", p is not None)
    h.fit()
    h.click(V(12, 8, 10))


def b_sizes():
    p = hs.hole_panel()
    if not h.check("a hole is placed", p is not None and p.target is not None):
        return
    c = hs.centre_of(p.target)
    h.check("where the click was", hs.vnear(c, V(12, 8, 10), 0.5), c)
    hs.type_into(p.diameter.widget, "6")
    hs.type_into(p.depth.widget, "5")


def b_flat():
    p = hs.hole_panel()
    if p is not None:
        b.choose(p.drill_point, "Flat")


def b_ok():
    p = hs.hole_panel()
    if p is not None and p.target is not None:
        hs.type_into(p.pos_x.widget, "12")
        hs.type_into(p.pos_y.widget, "8")
    h.shot("b-preview")
    h.task_button("OK")


def b_made():
    v = r.volume(body())
    h.check("a blind hole d 6 x 5", r.close(v, BOX - BLIND), v)
    h.check("the dialog closed", hs.hole_panel() is None)
    r.away()
    picked, mean, top = r.look(V(12, 8, 5))
    ok = picked is not None and r.part_of(picked[0], body())
    h.check("the hole's floor is drawn 5 mm down", ok, (picked, mean, top))
    r.body_drawn(V(30, 20, 10), body(), "the top beside the hole")
    r.info("timeline after the hole: %s" % r.timeline_titles())
    h.shot("b-hole")


def c_click_top():
    h.click_empty()
    h.fit()
    h.click(V(30, 20, 10))


def c_h():
    h.press("h")


def c_all():
    p = hs.hole_panel()
    if not h.check("a second hole is placed", p is not None and p.target is not None):
        return
    c = hs.centre_of(p.target)
    h.check("where the click before H was", hs.vnear(c, V(30, 20, 10), 0.5), c)
    hs.type_into(p.pos_x.widget, "30")
    hs.type_into(p.pos_y.widget, "20")
    hs.type_into(p.diameter.widget, "6")
    b.choose(p.extent, "All")


def c_ok():
    h.task_button("OK")


def c_made():
    v = r.volume(body())
    h.check("a hole d 6 through", r.close(v, BOX - BLIND - THROUGH), v)
    r.away()
    picked = r.picked_at(V(30, 20, 10))
    face = None
    if picked is not None and picked[1]:
        face = App.ActiveDocument.getObject(picked[0]).Shape.getElement(picked[1])
    top = face is not None and face.Surface.TypeId == "Part::GeomPlane"
    top = top and abs(face.BoundBox.ZMax - 10) < 1e-6 and abs(face.BoundBox.ZMin - 10) < 1e-6
    h.check(
        "the hole's opening shows no top face (the view looks into the hole)",
        not top,
        (picked, face and face.Surface.TypeId),
    )
    h.shot("c-through")


def d_undo():
    r.undo()


def d_undone():
    v = r.volume(body())
    h.check("Ctrl+Z takes the through hole away", r.close(v, BOX - BLIND), v)
    r.away()
    r.body_drawn(V(30, 20, 10), body(), "the top where the hole was")


def d_redo():
    r.redo()


def d_redone():
    v = r.volume(body())
    h.check("Ctrl+Y brings it back", r.close(v, BOX - BLIND - THROUGH), v)


steps = r.new_design("RegressHole", s)
steps += r.box("a", s, 0, 0, 40, 30, 10, check=a_made)
steps += [b_h, b_click_top, b_sizes, b_flat, b_ok, b_made]
steps += [c_click_top, c_h, c_all, c_ok, c_made]
steps += [d_undo, d_undone, d_redo, d_redone]

h.run("regress_hole", steps, paced_by="state")
