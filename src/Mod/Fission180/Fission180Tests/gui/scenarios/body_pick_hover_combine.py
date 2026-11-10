# SPDX-License-Identifier: LGPL-2.1-or-later
"""Combine's Tool Bodies box lights the tool the pointer means, also where the preview covers
it (body_pick_hover is the rest of Luca's 2026-11-10 request: "for all tools that ask to
select a body, hovering over a body should highlight the WHOLE body"). Only real input.

B1 = x 0..20, z 0..10; B2 = x 10..30, z 0..14 (they overlap in x 10..20). Combine, click B1
(Target Body), click B2's top (a tool): the Join preview is drawn where the see-through B2
is, so the pointer on B2's top lands on the preview: B2 (the tool a click there takes)
lights whole, not the target. On B1's own top: nothing lit whole (the target is no tool).
The pointer leaves the view: nothing lit. Esc.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import selection_input as si

V = App.Vector
B1_TOP = V(5, 10, 10)
B2_TOP = V(25, 10, 14)


def body(i):
    return s.bodies()[i]


def lit():
    from fission180 import selection_ui

    found = selection_ui.lit_body()
    return found[1] if found else None


def hover(point):
    pos = h.screen_point(point)
    h.move(QtCore.QPoint(pos.x() + 3, pos.y()))
    h.move(pos)


def setup():
    from fission180 import commands, extrude, sketch_ui

    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("BodyPickHoverCombine")
    first = commands.ensure_body()
    planes = sketch_ui.origin_planes(first)
    for i, (x0, x1, height) in enumerate(((0, 20, 10.0), (10, 30, 14.0))):
        sketch = sketch_ui.create_sketch(first, (planes["XY_Plane"], ""))
        h.draw_rectangle(sketch, x0, 0, x1, 20)
        extrude.make(first, sketch, {"distance": height, "operation": "new_body" if i else "join"})
        App.ActiveDocument.recompute()
    Gui.Selection.clearSelection()
    h.fit()
    h.check("two bodies", len(s.bodies()) == 2, s.bodies())
    h.ribbon("Combine")


def pick_target():
    p = s.panel()
    h.check("Combine open", p is not None and p.title == "Combine", p)
    h.click(B1_TOP)


def pick_tool():
    p = s.panel()
    h.check("B1 is the target", p is not None and p.options["target"] is body(0), p and p.options["target"])
    h.click(B2_TOP)


def hover_tool():
    p = s.panel()
    ok = p is not None and p.options["tools"] == [body(1)]
    h.check("B2 is the tool, the Join preview shows", ok and p.target is not None, p and (p.options["tools"], p.target))
    hover(B2_TOP)


def tool_lit():
    under = h.under_mouse(B2_TOP)
    h.check(
        "on the preview over B2: B2 (the tool) lights whole",
        lit() == body(1).Name and si.preselected() == (body(1).Name, ""),
        (lit(), si.preselected(), under),
    )
    h.shot("combine-preview-tool-lit")
    hover(B1_TOP)


def target_dark():
    h.check("on B1 (the target): nothing lit whole", lit() is None, (lit(), si.preselected()))
    hover(B2_TOP)


def leave():
    h.check("back on B2: lit again", lit() == body(1).Name, (lit(), si.preselected()))
    p = s.panel()
    if p is not None:
        button = p.fields["tools"].button
        h.pointer_to(button, button.rect().center())


def left():
    h.check("the pointer left the view: nothing lit", lit() is None, (lit(), si.preselected()))
    h.press(QtCore.Qt.Key_Escape)


def cleanup():
    h.wait_for(lambda: s.panel() is None, "Combine to close")
    for name in list(App.listDocuments()):
        Gui.getDocument(name).Modified = False
        App.closeDocument(name)


h.run(
    "body_pick_hover_combine",
    [setup, pick_target, pick_tool, hover_tool, tool_lit, target_dark, leave, left, cleanup],
    paced_by="state",
)
