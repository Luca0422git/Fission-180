# SPDX-License-Identifier: LGPL-2.1-or-later
"""The book's Saturn V (project 2) and Play Brick (project 6): a split face that stays split,
a feature pattern that repeats a Split Face, pattern directions picked on edges. Book parity
report, page 20 ("the split is LOST as soon as the next feature is added"), lines 964-968
("Split Face 3 does not change the part, so there is nothing to repeat") and 1231-1236
("clicking the brick's edges for the directions picked the faces next to them"). Only real
input.

Body: rectangle -20..20 x -15..15 extruded 10.
  A  MODIFY > Split Face: the top, Splitting Tool the YZ square: two halves. OK.
  B  A boss r 4 x 6 on the top's +X half (Create Sketch on the top, circle, E): the next
     feature. The top is still two faces (it was merged back into one), and a click on each
     half picks another face: each can be painted on its own.
  C  Split Face on the boss's top with the XZ square: two half discs.
  D  CREATE > Pattern > Rectangular Pattern, the boss and its Split Face clicked in the
     timeline; the direction box, then a click on the body's top right edge a few pixels
     off it, on the top face: the EDGE is taken (it was the face, and the copies went up).
     Quantity 2, distance 9: two bosses, and the copy's top is split in two as well.
  E  Ctrl+Z, Ctrl+Y; delete Split Face 1 from the timeline: the top is one face again
     (the steps after it are refined again).
"""

import math

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import direct_steps as d
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import pattern_steps as p
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import timeline_input as t

V = App.Vector
state = {}
BOX = 40 * 30 * 10.0
BOSS = math.pi * 16 * 6.0


def body():
    return d.bodies()[0]


def vol():
    return d.volume(body())


def flat_at(z):
    """Areas of the flat faces at height z, smallest first."""
    return sorted(
        round(f.Area, 3)
        for f in body().Shape.Faces
        if f.Surface.TypeId == "Part::GeomPlane"
        and abs(f.CenterOfMass.z - z) < 1e-6
        and abs(f.normalAt(0, 0).z) > 0.99
    )


def errors():
    return {k: v for k, v in t.states().items() if v[1] not in ("ok", "")}


# -- A: split the top ---------------------------------------------------------------------------
def a_start():
    h.click_empty()
    h.fit()
    d.ribbon_menu("MODIFY", "Split Face")


def a_click_top():
    h.click(V(-10, -8, 10))


def a_tool_box():
    d.click_box("tool")


def a_click_yz():
    pl.click_square("YZ_Plane")


def a_ok():
    h.check("split previewed: two halves", flat_at(10) == [600.0, 600.0], flat_at(10))
    h.task_button("OK")


def a_done():
    h.check("Split Face 1", "Split Face 1" in t.titles(), t.titles())
    h.check("the top is two faces of 600", flat_at(10) == [600.0, 600.0], flat_at(10))


# -- B: the next feature ------------------------------------------------------------------------
def b_split_kept():
    want = [round(600.0 - math.pi * 16, 3), 600.0]
    h.check("the boss is made", d.near(vol(), BOX + BOSS), vol())
    h.check(
        "the top is still two faces after the next feature",
        flat_at(10) == want,
        (flat_at(10), want),
    )
    h.check("nothing is red", not errors(), errors())
    h.click_empty()
    h.fit()


def b_click_left():
    h.click(V(-10, 8, 10))


def b_left_picked():
    state["left"] = [
        (x.Object.Name, tuple(x.SubElementNames)) for x in Gui.Selection.getSelectionEx()
    ]
    h.check(
        "a click on the -X half picks one face",
        len(state["left"]) == 1 and state["left"][0][1][0].startswith("Face"),
        state["left"],
    )
    h.click_empty()


def b_click_right():
    h.click(V(10, 10, 10))


def b_right_picked():
    right = [(x.Object.Name, tuple(x.SubElementNames)) for x in Gui.Selection.getSelectionEx()]
    h.check(
        "a click on the +X half picks another face",
        len(right) == 1 and right != state["left"],
        (right, state["left"]),
    )
    h.shot("B-split-kept")
    h.click_empty()


# -- C: split the boss's top --------------------------------------------------------------------
def c_start():
    d.ribbon_menu("MODIFY", "Split Face")


def c_click_boss_top():
    h.click(V(10, 2, 16))


def c_tool_box():
    d.click_box("tool")


def c_click_xz():
    pl.click_square("XZ_Plane")


def c_ok():
    h.task_button("OK")


def c_done():
    half = round(math.pi * 16 / 2.0, 3)
    h.check("Split Face 2", "Split Face 2" in t.titles(), t.titles())
    h.check("the boss's top is two half discs", flat_at(16) == [half, half], flat_at(16))
    h.click_empty()


# -- D: the pattern -----------------------------------------------------------------------------
def d_pattern():
    h.fit()
    si.menu_item("CREATE", "Rectangular Pattern")


def d_click_extrude():
    q = p.panel()
    h.check("Rectangular Pattern dialog", q is not None, h.popups())
    p.timeline_click("Extrude 2")


def d_click_split():
    p.timeline_click("Split Face 2")


def d_direction_box():
    q = p.panel()
    names = [o.Name for o, _s in (q.options["objects"] if q is not None else [])]
    h.check("the boss and its Split Face are the objects", len(names) == 2, names)
    h.check(
        "Pattern Type Features",
        q is not None and q.options["pattern_type"] == "features",
        q and q.options["pattern_type"],
    )
    p.click_box("direction")


def d_click_beside_edge():
    """On the top face, 0.5 mm from its right edge: a few pixels off the edge."""
    h.click(V(19.5, 6, 10))


def d_quantity():
    q = p.panel()
    ref = q.options.get("direction") if q is not None else None
    text = q._ref_text(ref, q._titles()) if ref else ""
    h.check(
        "the edge is the direction, not the face beside it",
        bool(ref) and ref[1].startswith("Edge"),
        (ref and ref[1], text),
    )
    if q is not None:
        p.type_quantity(q.quantity, 2)


def d_distance():
    q = p.panel()
    if q is not None:
        p.type_value(q.distance_field.widget, "9")


def d_ok():
    q = p.panel()
    h.check("no message", q is not None and not q.message.text(), q and q.message.text())
    h.task_button("OK")


d_ok.timeout_s = 120


def d_done():
    half = round(math.pi * 16 / 2.0, 3)
    h.check("dialog closed", p.panel() is None)
    h.check("two bosses", d.near(vol(), BOX + 2 * BOSS), vol())
    box = body().Shape.BoundBox
    h.check("side by side along the edge, not stacked", abs(box.ZMax - 16.0) < 1e-6, box.ZMax)
    h.check("the copy's top is split too", flat_at(16) == [half] * 4, flat_at(16))
    h.check("nothing is red", not errors(), errors())
    state["patterned"] = vol()
    h.shot("D-pattern")


# -- E ------------------------------------------------------------------------------------------
def e_undo():
    t.undo()


def e_undone():
    half = round(math.pi * 16 / 2.0, 3)
    h.check("Ctrl+Z: one boss", d.near(vol(), BOX + BOSS), vol())
    h.check("its top still split", flat_at(16) == [half, half], flat_at(16))
    t.redo()


def e_redone():
    half = round(math.pi * 16 / 2.0, 3)
    h.check(
        "Ctrl+Y: two bosses, both split",
        d.near(vol(), state["patterned"]) and flat_at(16) == [half] * 4,
        (vol(), flat_at(16)),
    )
    t.menu("Split Face 1", "Delete")


def e_deleted():
    count = len([x for x in t.titles() if x.startswith("Split Face")])
    h.check("one Split Face is left (the boss's)", count == 1, t.titles())
    tops = flat_at(10)
    h.check("the top is one face again", len(tops) == 1, tops)
    h.check("the bosses stay", d.near(vol(), state["patterned"]), vol())
    h.check("nothing is red", not errors(), errors())


h.run(
    "book_modify_split_pattern",
    t.watched(
        [s.new_design("SplitKept")]
        + s.box_steps("box", (-20, -15, 20, 15), 10, V(12, -22, 0))
        + [a_start, a_click_top, a_tool_box, a_click_yz, a_ok, a_done]
        + p.make_boss("boss", (10, 0), 4, 6, V(10, 0, 10))
        + [
            b_split_kept,
            b_click_left,
            b_left_picked,
            b_click_right,
            b_right_picked,
            c_start,
            c_click_boss_top,
            c_tool_box,
            c_click_xz,
            c_ok,
            c_done,
            d_pattern,
            d_click_extrude,
            d_click_split,
            d_direction_box,
            d_click_beside_edge,
            d_quantity,
            d_distance,
            d_ok,
            d_done,
            e_undo,
            e_undone,
            e_redone,
            e_deleted,
        ]
    ),
    paced_by="state",
)
