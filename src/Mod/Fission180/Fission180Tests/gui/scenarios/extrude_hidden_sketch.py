# SPDX-License-Identifier: LGPL-2.1-or-later
"""A hidden sketch stays hidden while Extrude offers areas to click (Luca, 2026-11-09: "when
selecting a sketch to extrude, hidden sketches will be displayed. they should be hidden").

Sketch 1 (a square at x 0..10) is hidden with its eye in the browser; Sketch 2 (a square at
x 30..40) is shown. E: only Sketch 2's area is offered (shaded); a click where Sketch 1's
square is picks nothing; Sketch 1 is still hidden. Cancel. Show Sketch 1 again, E: both offered.
"""
import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import harness as h

V = App.Vector
state = {}


def xpanel():
    from fission180 import extrude_ui

    p = extrude_ui.ExtrudePanel.last
    return p if p is not None and not p._closed else None


def offered():
    p = xpanel()
    picker = getattr(p, "picker", None) if p is not None else None
    if picker is None:
        return []
    return sorted({sketch.Name for sketch, _sub, _face, _mat in picker.regions})


def setup():
    from fission180 import commands, sketch_ui

    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("HiddenSketch")
    body = commands.ensure_body()
    planes = sketch_ui.origin_planes(body)
    one = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    h.draw_rectangle(one, 0, 0, 10, 10)
    two = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    h.draw_rectangle(two, 30, 0, 40, 10)
    App.ActiveDocument.recompute()
    state["one"], state["two"] = one, two
    one.ViewObject.Visibility = False  # what the browser's eye does
    Gui.Selection.clearSelection()
    h.fit()


def press_e():
    h.click_empty()
    h.press("e")


def only_the_shown_one():
    h.check("Extrude is open", xpanel() is not None)
    h.check("only the shown sketch's area is offered", offered() == [state["two"].Name], offered())
    h.check("the hidden sketch is still hidden", not state["one"].ViewObject.Visibility)
    h.click(V(5, 5, 0))  # where the hidden square is


def nothing_picked():
    p = xpanel()
    h.check("a click on the hidden square picks nothing",
            p is not None and not [x for x in p.profiles if x[0] is state["one"]], p and p.profiles)
    h.check("still hidden", not state["one"].ViewObject.Visibility)
    h.shot("1-hidden-stays-hidden")
    h.task_button("Cancel")


def show_again():
    h.check("Cancel closes it", xpanel() is None)
    state["one"].ViewObject.Visibility = True
    h.click_empty()
    h.press("e")


def both_offered():
    h.check("shown again: both sketches offered",
            offered() == sorted([state["one"].Name, state["two"].Name]), offered())
    h.task_button("Cancel")


def closed():
    h.check("closed", xpanel() is None)


h.run(
    "extrude_hidden_sketch",
    [setup, press_e, only_the_shown_one, nothing_picked, show_again, both_offered, closed],
    paced_by="state",
)
