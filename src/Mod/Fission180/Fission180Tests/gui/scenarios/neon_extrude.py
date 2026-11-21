# SPDX-License-Identifier: LGPL-2.1-or-later
"""Extrude works in Neon Lights (Luca, 2026-11-21: "whenever I switch over to the neon lights
setting, it just breaks extrude ... I drag the arrow and the distance stays at 0. If I change
the distance manually, it still doesn't extrude. And I get a warning saying the distance must
not be 0, even though I've typed in 10 millimeters").

Start in Dark, switch to Neon Lights in the running session, sketch a rectangle, Extrude it:
1. typing 10 into Distance (real keys) gives a 10 mm solid on OK;
2. dragging the arrow (real mouse) changes the distance and gives a solid on OK.
3. Fillet and Draft open with every number box of their panel still usable from Python (the
   cause: a Neon Lights watcher took hold of dialog widgets while Qt was still building them,
   and every QuantitySpinBox made after it was "already deleted" for Python).
The same in Dark first, so a failure here is Neon Lights' doing.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets

from Fission180Tests.gui import dialog_input as di
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import look_compare as lc

s = {}


def panel():
    from fission180 import extrude_ui

    return getattr(extrude_ui.ExtrudePanel, "last", None)


def new_design(look):
    def step():
        lc.set_look(look)
        App.newDocument("NeonExtrude_" + look)
        from fission180 import commands, sketch_ui

        body = commands.ensure_body()
        planes = sketch_ui.origin_planes(body)
        sk = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
        h.draw_rectangle(sk, 0, 0, 40, 30)
        App.ActiveDocument.recompute()
        s["sketch"], s["body"] = sk, body
        Gui.Selection.clearSelection()
        h.fit()

    step.__name__ = "%s_new_design" % look
    return step


def open_extrude():
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(App.ActiveDocument.Name, s["sketch"].Name)
    Gui.runCommand("Fission180_Extrude")


open_extrude.done = lambda: lc.task_open() and panel() is not None
open_extrude.done_what = "the Extrude dialog to open"


def solid_volume():
    shape = s["body"].Shape
    return shape.Volume if not shape.isNull() else 0.0


def make_round(look):
    def typed():
        p = panel()
        h.caught_up(what="the Extrude dialog's preview")
        di.type_into(p.distance.widget, "10")
        h.caught_up(what="the preview after typing 10")
        s["typed_value"] = p.distance.value()
        h.check("%s: Distance reads 10 after typing it" % look, abs(s["typed_value"] - 10.0) < 1e-6, s["typed_value"])

    def ok():
        h.task_button("OK")

    ok.done = lambda: not lc.task_open()
    ok.done_what = "the Extrude dialog to close"

    def solid():
        volume = solid_volume()
        h.check("%s: OK made a 40 x 30 x 10 solid" % look, abs(volume - 12000.0) < 1.0, volume)
        h.check("%s: no warning popped up" % look, not h.popups(), h.popups())

    def drag_open():
        App.ActiveDocument.undo()
        App.ActiveDocument.recompute()
        open_extrude()

    drag_open.done = open_extrude.done
    drag_open.done_what = open_extrude.done_what

    def dragged():
        p = panel()
        h.caught_up(what="the Extrude dialog's preview")
        arrow = p.draggers.get("distance")
        h.check("%s: the arrow is there" % look, arrow is not None)
        if arrow is None:
            return
        tip = getattr(arrow, "tip", None)
        start = h.screen_point(App.Vector(20, 15, 0))
        end = QtCore.QPoint(start.x(), start.y() - 80)
        h.view_drawn()
        h.drag(start, end)
        h.caught_up(what="the preview after the drag")
        s["dragged_value"] = p.distance.value()
        h.check("%s: dragging the arrow changed the distance" % look, abs(s["dragged_value"]) > 0.5, s["dragged_value"])

    for step in (typed, ok, solid, drag_open, dragged):
        step.__name__ = "%s_%s" % (look, step.__name__)
    return [typed, ok, solid, drag_open, dragged]


def _fields(obj, depth=0, seen=None):
    """Every value field (an object with a .widget that is a spin box) held by a panel."""
    seen = set() if seen is None else seen
    out = []
    if depth > 2 or id(obj) in seen:
        return out
    seen.add(id(obj))
    for name, value in list(vars(obj).items()):
        widget = getattr(value, "widget", None)
        if widget is not None and hasattr(value, "value"):
            out.append((name, widget))
        elif hasattr(value, "__dict__") and not isinstance(value, (QtWidgets.QWidget, type)):
            out += _fields(value, depth + 1, seen)
    return out


def command_round(look, command, module, cls, sub):
    def open_cmd():
        from fission180 import extrude

        if s.get("solid_for") != look:
            s["pad"] = extrude.make(s["body"], s["sketch"], {"distance": 10.0})
            App.ActiveDocument.recompute()
            s["solid_for"] = look
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(App.ActiveDocument.Name, s["pad"].Name, sub)
        Gui.runCommand(command)

    open_cmd.done = lambda: lc.task_open() and getattr(
        getattr(__import__("fission180." + module, fromlist=[cls]), cls), "last", None
    ) is not None
    open_cmd.done_what = "the %s dialog to open" % command

    def fields_alive():
        import shiboken6

        h.caught_up(what="the dialog")
        p = getattr(getattr(__import__("fission180." + module, fromlist=[cls]), cls), "last")
        found = _fields(p)
        dead = [name for name, widget in found if not shiboken6.isValid(widget)]
        h.check("%s: %s has value fields" % (look, command), bool(found), [n for n, _w in found])
        h.check("%s: every value field of %s is usable" % (look, command), not dead, dead)
        h.task_button("Cancel")

    fields_alive.done = lambda: not lc.task_open()
    fields_alive.done_what = "the dialog to close"
    for step in (open_cmd, fields_alive):
        step.__name__ = "%s_%s_%s" % (look, command, step.__name__)
    return [open_cmd, fields_alive]


def close_dialog():
    h.task_button("Cancel")


close_dialog.done = lambda: not lc.task_open()
close_dialog.done_what = "the Extrude dialog to close"


steps = []
for _look in ("dark", "neon"):
    steps += [new_design(_look), open_extrude] + make_round(_look) + [close_dialog]
    steps += command_round(_look, "Fission180_Fillet", "fillet_ui", "BlendPanel", "Edge1")
    steps += command_round(_look, "Fission180_Draft", "draft_ui", "DraftPanel", "Face1")
steps.append(lambda: lc.set_look("dark"))
h.run("neon_extrude", steps, paced_by="state")
