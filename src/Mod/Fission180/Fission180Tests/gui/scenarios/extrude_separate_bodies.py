# SPDX-License-Identifier: LGPL-2.1-or-later
"""Extrude of separate sketch areas makes separate bodies; areas that touch make one (Luca,
2026-11-09: "extruding multiple sketch faces ... creates 1 body. It should make multiple bodies
if there are multiple disconnected sketch faces. if the sketches are connected, they should be
combined"). And Split Body splits only what it crosses ("one cut will create all the correct
bodies, no matter where the cutting plane is"). Real input for the sketch and the dialog.

A sketch on XY: two squares side by side (x -5..15, sharing the side x = 5), three apart.
E, click the five areas, 10, OK: four bodies (the touching pair is one), one timeline step,
each body one solid. Undo: no solid; Redo: four again. Double-click the step, 20, OK: the same
four bodies, twice as tall. Split the pair's body along the YZ plane (x = 0, through the first
square only): one more body, the others untouched.
"""
import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import timeline_input as t

V = App.Vector
state = {}
# (x0, y0, x1, y1) of each square; the first two touch along x = 5
SQUARES = [(-5, 0, 5, 10), (5, 0, 15, 10), (40, 0, 50, 10), (0, 40, 10, 50), (40, 40, 50, 50)]


def xpanel():
    from fission180 import extrude_ui

    p = extrude_ui.ExtrudePanel.last
    return p if p is not None and not p._closed else None


def solid_bodies():
    return [b for b in s.bodies() if not b.Shape.isNull() and b.Shape.Solids and s.shown(b)]


def volumes():
    return sorted(round(s.volume(b), 3) for b in solid_bodies())


def setup():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("SeparateBodies")
    h.fit()
    h.ribbon("Create Sketch")


def pick_xy():
    pl.click_square("XY_Plane")


def draw():
    sk = h.in_sketch()
    if h.check("a sketch is open on XY", sk is not None):
        for x0, y0, x1, y1 in SQUARES:
            h.draw_rectangle(sk, x0, y0, x1, y1)


def finish():
    h.ribbon("Finish Sketch")


def extrude():
    state["titles"] = list(t.titles())
    h.fit()
    h.press("e")


def click_areas():
    p = xpanel()
    if not h.check("E opens Extrude", p is not None):
        return
    have = len(p.profiles)
    for x0, y0, x1, y1 in SQUARES:
        middle = V((x0 + x1) / 2.0, (y0 + y1) / 2.0, 0)
        if any(abs(middle.x - (a + b) / 2.0) < 1e-6 and abs(middle.y - (c + d) / 2.0) < 1e-6
               for (a, c, b, d) in SQUARES[:have]):
            continue  # (already taken by itself)
        h.click(middle)
    h.check("five areas picked", len(p.profiles) == 5, p.profiles)


def type_10():
    p = xpanel()
    if p is not None:
        ui.type_into(p.distance.widget, "10")


def ok():
    p = xpanel()
    h.check("New Body (nothing to join)", p is not None and p.operation.currentText() == "New Body",
            p and p.operation.currentText())
    h.shot("1-five-areas")
    h.task_button("OK")


def four_bodies():
    h.check("dialog closed", xpanel() is None)
    found = solid_bodies()
    h.check("four bodies: the touching squares are one", len(found) == 4, [b.Label for b in found])
    h.check("each body is one solid", all(len(b.Shape.Solids) == 1 for b in found),
            [len(b.Shape.Solids) for b in found])
    h.check("volumes: the pair 2000, the others 1000", volumes() == [1000.0, 1000.0, 1000.0, 2000.0],
            volumes())
    after = list(t.titles())
    added = [x for x in after if x not in state["titles"]]
    h.check("one timeline step", len(added) == 1, added)
    state["title"] = added[0] if added else None
    h.shot("2-four-bodies")
    s.undo()


def undone():
    h.check("undo: no solid left", not solid_bodies(), [b.Label for b in solid_bodies()])
    s.redo()


def redone():
    h.check("redo: four bodies again", len(solid_bodies()) == 4, [b.Label for b in solid_bodies()])
    state["names"] = sorted(b.Name for b in solid_bodies())
    h.check("double-click the extrude", ui.double_click_timeline(state["title"] or "?"))


def edit_20():
    p = xpanel()
    if h.check("the extrude is open again", p is not None):
        ui.type_into(p.distance.widget, "20")
        h.task_button("OK")


def edited():
    h.check("edited: the same four bodies", sorted(b.Name for b in solid_bodies()) == state["names"],
            sorted(b.Name for b in solid_bodies()))
    h.check("edited: twice as tall", volumes() == [2000.0, 2000.0, 2000.0, 4000.0], volumes())
    from fission180 import split

    doc = App.ActiveDocument
    pair = [b for b in solid_bodies() if abs(s.volume(b) - 4000.0) < 1e-6]
    yz = [o for o in doc.Objects if o.Name.startswith("YZ_Plane")]
    if h.check("the pair's body and the YZ plane", pair and yz):
        doc.openTransaction("Split Body")
        split.build({"body": pair[0], "tool": (yz[0], ""), "extend": True})
        doc.commitTransaction()
        doc.recompute()


def split_one():
    h.check("split: one more body, only the square the plane crosses",
            len(solid_bodies()) == 5, [b.Label for b in solid_bodies()])
    h.check("split: the halves 1000 and 3000, the others untouched",
            volumes() == [1000.0, 2000.0, 2000.0, 2000.0, 3000.0], volumes())
    h.shot("3-split")


h.run(
    "extrude_separate_bodies",
    [setup, pick_xy, draw, finish, extrude, click_areas, type_10, ok, four_bodies, undone, redone,
     edit_20, edited, split_one],
    paced_by="state",
)
