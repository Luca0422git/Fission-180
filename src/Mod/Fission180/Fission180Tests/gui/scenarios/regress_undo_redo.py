# SPDX-License-Identifier: LGPL-2.1-or-later
"""Undo and redo through a beginner's first steps, compared with the released
0.1.0-beta.3.3.10 (builder regress, wave 7): only real input, checked on the model, the
timeline and the screen after every key.

1. A block 40 x 30 x 10, a fillet r 2 on its front top edge, a boss d 10 x 5 on the top.
2. Ctrl+Z back to the empty design: boss, its sketch (its circle and dimension are steps
   of their own), fillet, block, sketch; after each one the part (and the view) is what it
   was before that step, never inside a sketch or a dialog.
3. Ctrl+Y as often: everything comes back, drawn.

One undo step per command (feature-guide rule 10): the extrude and the fillet take one
Ctrl+Z each.
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
ROUND = 40.0 * 4.0 * (1 - math.pi / 4)
BOSS = math.pi * 25.0 * 5.0


def total():
    return sum(r.volume(x) for x in r.bodies())


def a_made(s):
    h.check("the block", r.close(total(), BOX), r.bodies_summary())
    s["undo_box"] = App.ActiveDocument.UndoCount


def f_key():
    Gui.Selection.clearSelection()
    h.fit()
    h.press("f")


def f_edge():
    h.fit()
    h.click_edge(V(20, 0, 10))


def f_size():
    p = b.blend_panel()
    if h.check("an edge is picked", p is not None and bool(p.refs)):
        b.type_into(p.radius.widget, "2")


def f_ok():
    h.task_button("OK")


def f_made():
    h.check("the round", r.close(total(), BOX - ROUND), total())
    s["undo_fillet"] = App.ActiveDocument.UndoCount
    r.info("undo steps: block %d, fillet %d" % (s["undo_box"], s["undo_fillet"]))


def c_made(s):
    h.check("the boss joined", r.close(total(), BOX - ROUND + BOSS), r.bodies_summary())
    s["undo_all"] = App.ActiveDocument.UndoCount
    s["titles_all"] = r.timeline_titles()
    r.info(
        "undo steps after the boss: %d; names %s" % (s["undo_all"], App.ActiveDocument.UndoNames)
    )
    r.info("timeline: %s" % s["titles_all"])


# Ctrl+Z from the end, step by step: (what goes, the volume after it, the timeline after
# it). A sketch's own steps (its circle, its dimensions) are undo steps of their own, as in
# both versions compared: Ctrl+Z is pressed until the timeline has lost the step, and never
# more than MAX_PRESSES times for one step; the part never changes on the way.
EXPECT = [
    ("the boss's extrude", BOX - ROUND, ["Sketch 1", "Extrude 1", "Fillet 1", "Sketch 2"]),
    ("the boss's sketch", BOX - ROUND, ["Sketch 1", "Extrude 1", "Fillet 1"]),
    ("the fillet", BOX, ["Sketch 1", "Extrude 1"]),
    ("the block's extrude", 0.0, ["Sketch 1"]),
    ("the block's sketch", 0.0, []),
]
MAX_PRESSES = 14


def _settle_after(what):
    h.settle("the app to settle after %s" % what)


def undo_step(i):
    what, vol, titles_after = EXPECT[i]
    before = EXPECT[i - 1][1] if i > 0 else BOX - ROUND + BOSS

    def undo_keys():
        presses = 0
        while presses < MAX_PRESSES:
            r.undo()
            presses += 1
            _settle_after("Ctrl+Z")
            h.check(
                "Ctrl+Z for %s: not in a sketch or a dialog" % what,
                h.in_sketch() is None and r.panel() is None,
            )
            if r.timeline_titles() == titles_after:
                break
            v = total()
            if not r.close(v, before):
                break  # (the check below says what went)
        s["presses_%d" % i] = presses
        r.info("Ctrl+Z pressed %d times to take %s back" % (presses, what))

    def undone():
        v = total()
        titles = r.timeline_titles()
        h.check("Ctrl+Z took %s back" % what, titles == titles_after, titles)
        h.check("the part after %s went" % what, r.close(v, vol), v)
        r.away()
        if vol > 0:
            r.body_drawn(V(30, 25, 10), r.bodies()[0], "after %s went" % what)
        else:
            r.nothing_drawn(V(20, 15, 10), "after %s went" % what)

    undo_keys.__name__ = "undo_%d" % (i + 1)
    undone.__name__ = "undone_%d" % (i + 1)
    return [undo_keys, undone]


def redo_step(i):
    # brings back EXPECT[j], undone with s["presses_j"] presses
    j = len(EXPECT) - 1 - i
    what = EXPECT[j][0]
    vol = EXPECT[j - 1][1] if j > 0 else BOX - ROUND + BOSS
    titles_after = EXPECT[j - 1][2] if j > 0 else None

    def redo_keys():
        for _n in range(s.get("presses_%d" % j, 1)):
            r.redo()
            _settle_after("Ctrl+Y")
            h.check(
                "Ctrl+Y for %s: not in a sketch or a dialog" % what,
                h.in_sketch() is None and r.panel() is None,
            )

    def redone():
        v = total()
        titles = r.timeline_titles()
        h.check("Ctrl+Y brought %s back" % what, r.close(v, vol), (v, titles))
        if titles_after is not None:
            h.check("the timeline after %s came back" % what, titles == titles_after, titles)
        r.away()
        if vol > 0:
            r.body_drawn(V(30, 25, 10), r.bodies()[0], "after %s came back" % what)

    redo_keys.__name__ = "redo_%d" % (i + 1)
    redone.__name__ = "redone_%d" % (i + 1)
    return [redo_keys, redone]


def all_back():
    titles = r.timeline_titles()
    h.check("the timeline is as before", titles == s["titles_all"], (titles, s["titles_all"]))
    h.check("one body", len(r.bodies()) == 1, r.bodies_summary())
    h.fit()
    r.away()
    r.body_drawn(V(30, 15, 15), r.bodies()[0], "the boss at the end")
    h.shot("end")


steps = r.new_design("RegressUndo", s)
steps += r.box("a", s, 0, 0, 40, 30, 10, check=a_made)
steps += [f_key, f_edge, f_size, f_ok, f_made]
steps += r.boss("c", s, V(20, 25, 10), V(30, 15, 10), 5, 5, expect_op="Join", check=c_made)
for _i in range(len(EXPECT)):
    steps += undo_step(_i)
for _i in range(len(EXPECT)):
    steps += redo_step(_i)
steps += [all_back]

h.run("regress_undo_redo", steps, paced_by="state")
