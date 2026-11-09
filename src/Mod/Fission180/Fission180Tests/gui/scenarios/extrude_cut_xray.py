# SPDX-License-Identifier: LGPL-2.1-or-later
"""The red of a cut shows through the part that hides it (Luca, 2026-11-09: "when im extruding
a cut into an object and the cut is occluded by that object, i should still be able to see the
red of the cut through the walls of that object").

A block 40 x 30 x 20 (z 0..20). A sketch on XY (the block's bottom) with a rectangle
x 10..30, y 10..20. Seen from above (iso), E, 10: an automatic Cut up into the block, wholly
inside it. The red preview has its see-through layer drawn over the part (a Coin annotation:
no depth test); on the screen the block over the cut's middle is reddish, while its top away
from it is not. Cancel: nothing left.
"""
import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_input as si

V = App.Vector
state = {}


def xpanel():
    from fission180 import extrude_ui

    p = extrude_ui.ExtrudePanel.last
    return p if p is not None and not p._closed else None


def reddish(point):
    colours = si.screen_colours(point, radius=2)
    found = [si.rgb(c) for c in colours.values()]
    return any(r > g + 40 and r > b + 40 for r, g, b in found), sorted(set(colours.values()))[:6]


def setup():
    from fission180 import commands, extrude, sketch_ui

    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("CutXRay")
    body = commands.ensure_body()
    planes = sketch_ui.origin_planes(body)
    block = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    h.draw_rectangle(block, 0, 0, 40, 30)
    extrude.make(body, block, {"distance": 20.0})
    cut = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    h.draw_rectangle(cut, 10, 10, 30, 20)
    App.ActiveDocument.recompute()
    state["sketch"] = cut
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(cut)
    h.fit()
    h.press("e")


def type_10():
    p = xpanel()
    if h.check("Extrude is open on the sketch", p is not None, p and p.profiles):
        ui.type_into(p.distance.widget, "10")


def red_through():
    from fission180 import cut_preview

    p = xpanel()
    h.check("an automatic Cut up into the block", p is not None and p.operation.currentText() == "Cut",
            p and p.operation.currentText())
    nodes = cut_preview.find(name=cut_preview.NAME)
    h.check("the red preview is shown", bool(nodes), nodes)
    xray = [n.getChild(i) for n in nodes for i in range(n.getNumChildren())
            if n.getChild(i).getName().getString() == cut_preview.XRAY_NAME]
    h.check("with its see-through layer over the part", bool(xray), xray)
    inside, colours = reddish(V(20, 15, 5))  # the middle of the cut, inside the block
    h.check("on the screen: the block over the cut is reddish", inside, colours)
    away, colours2 = reddish(V(3, 3, 20))
    h.check("...and not away from it", not away, colours2)
    h.shot("1-cut-seen-through")
    h.task_button("Cancel")


def nothing_left():
    from fission180 import cut_preview

    h.check("Cancel: no red left", not cut_preview.find(name=cut_preview.NAME))


h.run("extrude_cut_xray", [setup, type_10, red_through, nothing_left], paced_by="state")
