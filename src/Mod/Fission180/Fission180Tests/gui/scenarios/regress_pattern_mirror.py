# SPDX-License-Identifier: LGPL-2.1-or-later
"""A circular pattern and a mirror of a feature, compared with the released 0.1.0-beta.3.3.10
(builder regress, wave 7): only real input, checked on the model and on the screen.

1. A disc d 40 x 10 centred on the origin, a boss d 6 x 5 at (12, 0) on its top.
2. CREATE > Pattern > Circular Pattern, Pattern Type Features, click the boss's step in the
   timeline, the Axis box, the Z axis; Quantity 4; OK: four bosses at 0, 90, 180, 270
   degrees, all drawn.
3. Ctrl+Z: one boss; Ctrl+Y: four.
4. A boss d 6 x 5 at (-6, 6); Mirror (ribbon), its step in the timeline (Pattern Type
   Features by itself), the Mirror Plane box, the XZ square; OK: a copy at (-6, -6), drawn.

Hand-derived: disc pi 20^2 10 = 4000 pi; a boss pi 3^2 5.
"""

import math

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import pattern_steps as ps
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import regress_steps as r

V = App.Vector
s = {}
PLATE = 4000.0 * math.pi
BOSS = math.pi * 9.0 * 5.0


def body():
    return r.bodies()[0]


def a_made(s):
    h.check("the disc", r.close(r.total_volume(), PLATE), r.bodies_summary())


def boss_made(s):
    h.check("the boss joined", r.close(r.volume(body()), PLATE + BOSS), r.bodies_summary())
    s["boss_title"] = r.timeline_titles()[-1]
    r.info("the boss's step: %s; timeline %s" % (s["boss_title"], r.timeline_titles()))


def b_open():
    Gui.Selection.clearSelection()
    h.fit()
    ps.menu("Circular Pattern")


def b_features():
    p = ps.panel()
    if h.check("the Circular Pattern dialog is open", p is not None and p.kind == "circular"):
        b.choose(p.pattern_type, "Features")


def b_pick_step():
    ps.timeline_click(s["boss_title"])


def b_axis_box():
    p = ps.panel()
    h.check("the boss is picked", p is not None and len(p.options["objects"]) == 1, p and p.options)
    ps.click_box("axis")


def b_z_axis():
    h.fit()
    pl.click_on_plane(V(0, 0, 22))


def b_quantity():
    p = ps.panel()
    axis = p.options["axis"] if p else None
    h.check("the Z axis is the axis", axis is not None and axis[0].Role == "Z_Axis", axis)
    if p is not None:
        ps.type_quantity(p.quantity, 4)


def b_ok():
    h.shot("b-preview")
    h.task_button("OK")


def b_made():
    v = r.volume(body())
    h.check("four bosses", r.close(v, PLATE + 4 * BOSS), v)
    centres = ps.circle_centres(body().Shape, 3.0, z=15)
    want = [(-12.0, 0.0), (0.0, -12.0), (0.0, 12.0), (12.0, 0.0)]
    got = sorted((round(x, 3) + 0.0, round(y, 3) + 0.0) for x, y in centres)
    h.check("at 0, 90, 180, 270 degrees", got == sorted(want), got)
    r.away()
    for x, y in want:
        r.drawn_here(V(x, y, 15), "the top of the boss at (%g, %g)" % (x, y))
    h.shot("b-pattern")


def c_undo():
    r.undo()


def c_undone():
    v = r.volume(body())
    h.check("Ctrl+Z: one boss", r.close(v, PLATE + BOSS), v)
    r.away()
    r.not_drawn_here(V(-12, 0, 15), "after Ctrl+Z, the top of a copy")


def c_redo():
    r.redo()


def c_redone():
    v = r.volume(body())
    h.check("Ctrl+Y: four bosses", r.close(v, PLATE + 4 * BOSS), v)
    r.away()
    r.drawn_here(V(-12, 0, 15), "after Ctrl+Y, the top of a copy")


def second_boss_made(s):
    h.check("a fifth boss", r.close(r.volume(body()), PLATE + 5 * BOSS), r.bodies_summary())
    s["boss2_title"] = r.timeline_titles()[-1]


def e_open():
    Gui.Selection.clearSelection()
    h.fit()
    h.ribbon("Mirror")


def e_pick_step():
    """A step clicked in the timeline: Mirror takes it as a feature (Pattern Type Features)."""
    p = ps.panel()
    h.check("the Mirror dialog is open", p is not None and p.kind == "mirror")
    ps.timeline_click(s["boss2_title"])


def e_plane_box():
    p = ps.panel()
    h.check("the boss is picked", p is not None and len(p.options["objects"]) == 1, p and p.options)
    ps.click_box("plane")


def e_plane():
    h.fit()
    pl.click_square("XZ_Plane")


def e_ok():
    h.task_button("OK")


def e_made():
    v = r.volume(body())
    h.check("the mirrored boss", r.close(v, PLATE + 6 * BOSS), v)
    centres = ps.circle_centres(body().Shape, 3.0, z=15)
    got = sorted((round(x, 3) + 0.0, round(y, 3) + 0.0) for x, y in centres)
    h.check("the copy at (-6, -6)", (-6.0, -6.0) in got, got)
    r.away()
    r.drawn_here(V(-6, -6, 15), "the top of the mirrored boss")
    h.shot("e-mirror")


steps = r.new_design("RegressPattern", s)
steps += r.sketch_on_plane("a", s)
steps += r.circle("a", s, V(0, 0, 0), 20)
steps += r.finish_sketch("a", s, r.circle_rim)
steps += r.extrude("a", s, 10, check=a_made)
steps += r.boss("boss", s, V(-10, -10, 10), V(12, 0, 10), 3, 5, expect_op="Join", check=boss_made)
steps += [b_open, b_features, b_pick_step, b_axis_box, b_z_axis, b_quantity, b_ok, b_made]
steps += [c_undo, c_undone, c_redo, c_redone]
steps += r.boss(
    "d", s, V(-10, -10, 10), V(-6, 6, 10), 3, 5, expect_op="Join", check=second_boss_made
)
steps += [e_open, e_pick_step, e_plane_box, e_plane, e_ok, e_made]

h.run("regress_pattern_mirror", steps, paced_by="state")
