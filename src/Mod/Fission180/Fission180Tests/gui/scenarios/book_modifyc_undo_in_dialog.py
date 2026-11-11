# SPDX-License-Identifier: LGPL-2.1-or-later
"""Undo pressed while a command's dialog is open cancels that command and leaves nothing to
redo (book parity report, bug 18: "undo of Combine leaves an orphan invalid Combine 1 step").

Reproduced with this scenario before the fix (the toolbar's Undo; only the Ctrl+Z key was
caught by the dialogs):
* Fillet with an edge picked: FreeCAD closed the dialog's unfinished step as if it were
  done and undid it; the Redo list then held "Fillet", and Redo brought the preview back
  as a step of the design ("Fillet 1" in the timeline): the report's orphan step.
* Combine with only its target picked (nothing changed yet): the Undo took away the step
  BEFORE the command (the sketch made last) under the open dialog.
Now Undo from the toolbar, a menu or the key cancels the command being made, whatever the
dialog, and FreeCAD's Undo does not run (preview.dialog_takes, from commands.make_way_for).

A 40 x 30 x 10 box with a hole (real input, so there is something to undo), a second body
and a sketch with a circle on the box's top (made in undo steps of their own). Then, for
each dialog below: the command started, the clicks that give it a preview (or half of
one), the toolbar's Undo, then the toolbar's Redo:

  Combine with only its target picked (an incomplete preview), Combine with target and tool,
  Extrude of the sketch's circle, Fillet of an edge, Rectangular Pattern with a body and no
  direction yet, Hole placed on the top face; and Combine once more with Ctrl+Z on the
  keyboard.

After the Undo: the dialog is closed, the design is exactly as before the command (objects,
volumes, timeline, the Undo list), the Redo list is empty. After the Redo: still so, and
nothing is red.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import pattern_steps as ps
from Fission180Tests.gui import timeline_input as t

V = App.Vector
S = {}


def doc():
    return App.ActiveDocument


def snapshot():
    volumes = []
    for body in doc().findObjects("PartDesign::Body"):
        shape = body.Shape
        volumes.append((body.Name, 0.0 if shape.isNull() else round(shape.Volume, 4)))
    return {
        "objects": sorted(o.Name for o in doc().Objects),
        "volumes": sorted(volumes),
        "timeline": list(t.titles()),
        "undo": list(doc().UndoNames),
    }


def red():
    return {k: v for k, v in t.states().items() if v[1] not in ("ok", "")}


def differences(now, before):
    return {k: (now[k], before[k]) for k in before if now[k] != before[k]}


def extras():
    """A second body beside the box and a sketch on the box's top, each one undo step."""
    import Part

    d = doc()
    d.openTransaction("Second body")
    body = d.addObject("PartDesign::Body", "Body")
    block = body.newObject("PartDesign::AdditiveBox", "Block")
    block.Length, block.Width, block.Height = 20, 30, 10
    body.Placement = App.Placement(V(30, 0, 5), App.Rotation())
    d.commitTransaction()
    d.recompute()
    d.openTransaction("Sketch")
    first = h.body()
    sketch = first.newObject("Sketcher::SketchObject", "Ring")
    plane = [f for f in first.Origin.OriginFeatures if f.Role == "XY_Plane"][0]
    sketch.AttachmentSupport = (plane, [""])
    sketch.MapMode = "FlatFace"
    sketch.AttachmentOffset = App.Placement(V(0, 0, 10), App.Rotation())
    sketch.addGeometry(Part.Circle(V(14, 22, 0), V(0, 0, 1), 4))
    d.commitTransaction()
    d.recompute()
    S["second"] = body.Name
    S["sketch"] = sketch.Name
    h.fit()


def ready():
    bodies = doc().findObjects("PartDesign::Body")
    h.check("two bodies", len(bodies) == 2, [x.Label for x in bodies])
    h.check("something to undo", len(doc().UndoNames) >= 3, list(doc().UndoNames))
    h.check("nothing is red", not red(), red())


def case(tag, start, clicks, keyboard=False):
    """The steps of one dialog: start, the clicks, Undo, the checks, Redo, the checks."""

    def begin():
        Gui.Selection.clearSelection()
        S["before"] = snapshot()
        start()

    begin.__name__ = "%s_start" % tag
    begin.done = lambda: bool(Gui.Control.activeDialog())
    begin.done_what = "the %s dialog is open" % tag
    steps = [begin]
    for index, click in enumerate(clicks):

        def one(click=click):
            click()

        one.__name__ = "%s_click_%d" % (tag, index + 1)
        steps.append(one)

    def undo():
        h.check("%s: its dialog is open" % tag, bool(Gui.Control.activeDialog()))
        S["made"] = sorted(set(o.Name for o in doc().Objects) - set(S["before"]["objects"]))
        if keyboard:
            t.ctrl("z")
        else:
            t.undo()

    undo.__name__ = "%s_undo" % tag
    undo.done = lambda: not Gui.Control.activeDialog()
    undo.done_what = "Undo closed the %s dialog" % tag

    def undone():
        now = snapshot()
        h.check(
            "%s: the design is as before the command" % tag,
            now == S["before"],
            differences(now, S["before"]),
        )
        h.check("%s: nothing to redo" % tag, list(doc().RedoNames) == [], list(doc().RedoNames))
        h.check("%s: nothing is red" % tag, not red(), red())
        t.redo()

    undone.__name__ = "%s_undone" % tag

    def redone():
        now = snapshot()
        h.check(
            "%s: Redo brings no half-made step back" % tag,
            now == S["before"],
            (differences(now, S["before"]), S.get("made")),
        )
        h.check("%s: nothing is red after Redo" % tag, not red(), red())
        h.check("%s: no dialog" % tag, not Gui.Control.activeDialog())

    redone.__name__ = "%s_redone" % tag
    return steps + [undo, undone, redone]


def on_box():
    h.click(V(8, 25, 10))


def on_second():
    h.click(V(45, 15, 15))


def pattern_start():
    h.ribbon("Rectangular Pattern")


def hole_start():
    h.press("h")


def show_sketch():
    sketch = doc().getObject(S["sketch"])
    sketch.ViewObject.Visibility = True
    h.press("e")


def circle():
    h.click(V(14, 22, 10))


def edge():
    h.click_edge(V(20, 0, 10))


def combine():
    h.ribbon("Combine")


def previewed_combine():
    made = [o for o in doc().Objects if getattr(o, "Fission180Type", "") == "Combine"]
    h.check("the Combine is previewed", len(made) == 1, [o.Name for o in made])


def end():
    h.check("the timeline is as at the start", t.titles() == S["start"], t.titles())
    h.shot("undo-in-dialog")


def start_state():
    S["start"] = list(t.titles())


steps = b.box_steps("UndoInDialog") + ps.make_cut("hole", (30, 8), 2.0) + [extras, ready]
steps += [start_state]
steps += case("Combine (target only)", combine, [on_box])
steps += case("Combine", combine, [on_box, on_second, previewed_combine])
steps += case("Extrude", show_sketch, [circle])
steps += case("Fillet", lambda: h.press("f"), [edge])
steps += case("Rectangular Pattern", pattern_start, [on_box])
steps += case("Hole", hole_start, [on_box])
steps += case("Combine (Ctrl+Z)", combine, [on_box, on_second], keyboard=True)
steps += [end]
h.run("book_modifyc_undo_in_dialog", steps, paced_by="state")
