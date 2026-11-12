# SPDX-License-Identifier: LGPL-2.1-or-later
"""Revolve, Move and deleting a step, compared with the released 0.1.0-beta.3.3.10 (builder
regress, wave 7): only real input, checked on the model, the timeline and the screen.

1. Create Sketch on the XZ plane, a rectangle x 0..10, z 0..20 against the Z axis (sizes
   typed); Finish Sketch.
2. Revolve (ribbon): the profile is taken by itself; click the Z axis; OK: a cylinder r 10,
   h 20 round the Z axis, drawn.
3. M, click the cylinder, type X Distance 30; OK: it stands at x 20..40.
4. Right-click the Move in the timeline > Delete: back round the Z axis; Ctrl+Z: at x 30
   again; Ctrl+Y: back.

Hand-derived: pi 10^2 20 = 2000 pi.
"""

import math

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import bodies_steps as bs
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import regress_steps as r
from Fission180Tests.gui import timeline_input as tl

V = App.Vector
s = {}
CYL = 2000.0 * math.pi


def body():
    return r.bodies()[0]


def centre_x():
    bb = body().Shape.BoundBox
    return (bb.XMin + bb.XMax) / 2.0


def b_revolve():
    Gui.Selection.clearSelection()
    h.fit()
    h.ribbon("Revolve")


def b_axis():
    p = r.panel()
    h.check("the Revolve dialog is open", p is not None and getattr(p, "title", "") == "Revolve")
    h.check("the profile is taken", p is not None and bool(getattr(p, "profiles", None)))
    h.fit()
    pl.click_on_plane(V(0, 0, 32))


def b_ok():
    h.shot("b-preview")
    h.task_button("OK")


def b_made():
    bodies = r.bodies()
    h.check("one body", len(bodies) == 1, r.bodies_summary())
    if not bodies:
        return
    v = r.volume(bodies[0])
    h.check("a cylinder r 10 h 20", r.close(v, CYL), v)
    h.check("round the Z axis", abs(centre_x()) < 1e-6, body().Shape.BoundBox)
    h.fit()
    r.away()
    r.body_drawn(V(0, 0, 20), bodies[0], "the top of the cylinder")
    s["titles"] = r.timeline_titles()
    r.info("timeline after the revolve: %s" % s["titles"])


def c_m():
    h.click_empty()
    h.fit()
    h.press("m")


def c_click():
    p = r.panel()
    h.check("M opens Move/Copy", p is not None and getattr(p, "title", "") == "Move/Copy", p)
    h.click(V(0, 0, 20))


def c_type():
    p = r.panel()
    h.check("the cylinder is picked", p is not None and p.options.get("bodies") == [body()])
    if p is not None:
        bs.type_value(p.distance_fields[0].widget, "30")


def c_ok():
    h.task_button("OK")


def c_made():
    h.check("moved 30 along X", r.close(centre_x(), 30.0), body().Shape.BoundBox)
    h.check("the same cylinder", r.close(r.volume(body()), CYL), r.volume(body()))
    h.fit()
    r.away()
    r.body_drawn(V(30, 0, 20), body(), "the moved cylinder")
    s["moved_titles"] = r.timeline_titles()
    r.info("timeline after the move: %s" % s["moved_titles"])


def d_delete():
    new = [t for t in s["moved_titles"] if t not in s["titles"]]
    if h.check("the Move is a new step in the timeline", len(new) == 1, s["moved_titles"]):
        s["move_title"] = new[0]
        tl.menu(new[0], "Delete")


def d_deleted():
    h.check("the Move is gone", s.get("move_title") not in r.timeline_titles(), r.timeline_titles())
    h.check("back round the Z axis", abs(centre_x()) < 1e-6, body().Shape.BoundBox)
    h.fit()
    r.away()
    r.body_drawn(V(0, 0, 20), body(), "the cylinder back round the Z axis")


def d_undo():
    r.undo()


def d_undone():
    h.check("Ctrl+Z: moved again", r.close(centre_x(), 30.0), body().Shape.BoundBox)
    h.check("the Move is back", s.get("move_title") in r.timeline_titles(), r.timeline_titles())


def d_redo():
    r.redo()


def d_redone():
    h.check("Ctrl+Y: deleted again", abs(centre_x()) < 1e-6, body().Shape.BoundBox)
    h.fit()
    r.away()
    r.body_drawn(V(0, 0, 20), body(), "at the end")
    h.shot("d-end")


steps = r.new_design("RegressRevolve", s)
steps += r.sketch_on_plane("a", s, role="XZ_Plane")
steps += r.rectangle("a", s, V(0, 0, 0), V(10, 0, 20), 10, 20)
steps += r.finish_sketch("a", s, r.rect_bottom_mid)
steps += [b_revolve, b_axis, b_ok, b_made]
steps += [c_m, c_click, c_type, c_ok, c_made]
steps += [d_delete, d_deleted, d_undo, d_undone, d_redo, d_redone]

h.run("regress_revolve_move", steps, paced_by="state")
