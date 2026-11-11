# SPDX-License-Identifier: LGPL-2.1-or-later
"""A hole dragged by its blue dot lands on clean values (book parity report, line 1132: "Real
drag of the blue dot works ... The position box shows "-55.00 um" (micrometres) instead of
0.00 mm": the drag had left a real -0.055 mm).

A 40 x 30 x 10 box (real input). H, a click on the top face at (20, 15); then the dot is
dragged three times, each a real press, move and release: by (-7.3, 0), back onto the Y
value 15 by a path that ends a fraction of a pixel beside it, and far to a corner. After
each: X and Y of the hole are multiples of the step the screen allows (the smallest clean
step of at least two pixels: 0.5 mm in this view), the position boxes show them without a
micrometre in sight, and the hole really is there (its centre on the part). A typed value
(12.345) is taken as typed: only drags are rounded. OK: the hole is cut at the typed place.
"""

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import hole_steps as hs

V = App.Vector
S = {}


def step_now():
    """The step a drag is rounded to in this view (mm)."""
    from fission180 import handle_look, hole_snaps_core

    p = hs.hole_panel()
    dot = p.draggers.get("centre")
    scale = handle_look.mm_per_px(Gui.ActiveDocument.ActiveView, dot.point())
    return hole_snaps_core.drag_step(scale)


def clean(value, step):
    return abs(value / step - round(value / step)) < 1e-6


def ribbon_hole():
    h.fit()
    Gui.Selection.clearSelection()
    h.ribbon("Hole")


def click_top():
    h.click(V(20, 15, 10))


def drag_by(dx, dy):
    def step():
        p = hs.hole_panel()
        dot = p.draggers.get("centre") if p else None
        if not h.check("the blue dot to drag", dot is not None):
            return
        start = dot.point()
        S["from"] = start
        h.drag(h.screen_point(start), h.screen_point(start + V(dx, dy, 0)))

    step.__name__ = "drag_%s_%s" % (str(dx).replace("-", "m"), str(dy).replace("-", "m"))
    return step


def after_drag(tag, want):
    def check():
        from fission180 import hole

        p = hs.hole_panel()
        x, y = hole.hole_xy(p.target)
        step = step_now()
        S.setdefault("steps", []).append(step)
        h.check(
            "%s: X and Y are multiples of %g mm" % (tag, step),
            clean(x, step) and clean(y, step),
            (x, y, step),
        )
        h.check(
            "%s: the hole went where it was dragged" % tag,
            abs(x - want[0]) <= step and abs(y - want[1]) <= step,
            ((x, y), want),
        )
        texts = (p.pos_x.widget.text(), p.pos_y.widget.text())
        h.check(
            "%s: the position boxes show millimetres" % tag,
            all("mm" in text and "µ" not in text and "um" not in text for text in texts),
            texts,
        )
        h.check(
            "%s: the boxes show the hole's place" % tag,
            abs(p.pos_x.value() - x) < 1e-9 and abs(p.pos_y.value() - y) < 1e-9,
            (p.pos_x.value(), p.pos_y.value(), x, y),
        )
        c = hs.centre_of(p.target)
        h.check("%s: the hole is there" % tag, c is not None and abs(c.x - x) < 1e-6, (c, x))

    check.__name__ = "dragged_%s" % tag.replace(" ", "_")
    return check


def type_x():
    p = hs.hole_panel()
    hs.type_into(p.pos_x.widget, "12.345")


def typed():
    from fission180 import hole

    p = hs.hole_panel()
    x, _y = hole.hole_xy(p.target)
    h.check("a typed value is taken as typed", abs(x - 12.345) < 1e-9, x)
    h.check("the step in this view is 0.1 mm or more", min(S["steps"]) >= 0.1, S["steps"])
    S["y"] = hole.hole_xy(p.target)[1]
    h.task_button("OK")


def done():
    h.check("dialog closed", hs.hole_panel() is None)
    holes = hs.holes()
    h.check("one hole", len(holes) == 1, holes)
    c = hs.centre_of(holes[0]) if holes else None
    h.check(
        "cut at the typed place",
        c is not None and abs(c.x - 12.345) < 1e-6 and abs(c.y - S["y"]) < 1e-6,
        c,
    )
    h.check("the box has a hole", h.solid_volume() < hs.BOX - 1.0, h.solid_volume())
    h.shot("hole-drag")


h.run(
    "book_modifyc_hole_drag",
    b.box_steps("HoleDrag")
    + [
        ribbon_hole,
        click_top,
        drag_by(-7.3, 0),
        after_drag("left", (12.7, 15.0)),
        drag_by(3.13, 4.06),
        after_drag("up", (15.83, 19.06)),
        drag_by(-0.97, -4.055),
        after_drag("back to 15", (14.86, 15.0)),
        type_x,
        typed,
        done,
    ],
    paced_by="state",
)
