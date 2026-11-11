# SPDX-License-Identifier: LGPL-2.1-or-later
"""Bug 18 of the book parity report (the Drone, lines 1557-1566): "extruding the strip areas
as New Body gave 5 separate bodies; a Combine Join kept 5 solids in one body. Undo of Combine
left an orphan, invalid Combine 1 step in the timeline (There is no solid in the target
body)". Rebuilt the way the report did it, with real input:

  a user parameter Thickness = 2.5 mm (made as the report made it: parameters.add_user);
  one sketch with five separate strips; E, the five areas clicked, Distance "-Thickness"
  (the report's way round the negative parameter), Operation New Body: five bodies from one
  extrude; MODIFY > Combine, the first body as the target, the other four as tools, Join, OK:
  one body of five solids.

  A  Ctrl+Z: the Combine is gone from the timeline and from the design, the five bodies are
     back, nothing is red. Ctrl+Y: it is back and valid. Ctrl+Z again.
  B  The parameter changed (Thickness 4) and Ctrl+Z of that: the bodies follow, no step is
     left behind.
  C  Combine again, Ctrl+Z pressed while its dialog is still open: the dialog closes, no
     Combine stays; Ctrl+Y does not bring half a Combine back as a red step.
  D  Combine once more, OK; Ctrl+Z twice with nothing in between (the Combine and the
     Extrude under it), Ctrl+Y twice the same way: nothing red, no step left behind.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import timeline_input as t

V = App.Vector
S = {}
XS = (0, 30, 60, 90, 120)  # the strips: 20 x 60 each, 10 apart
T = 2.5
STRIP = 20 * 60 * T


def doc():
    return App.ActiveDocument


def combines():
    return [o for o in doc().Objects if getattr(o, "Fission180Type", "") == "Combine"]


def volumes():
    """The volumes of the bodies that are shown (a body used up by a Combine is hidden)."""
    return sorted(round(s.volume(x), 3) for x in s.bodies() if s.volume(x) > 1e-9 and s.shown(x))


def red():
    return {k: v for k, v in t.states().items() if v[1] not in ("ok", "")}


def clean(where, count=5):
    h.check("%s: no Combine object is left" % where, not combines(), [c.Name for c in combines()])
    h.check(
        "%s: no Combine step in the timeline" % where,
        not [x for x in t.titles() if x.startswith("Combine")],
        t.titles(),
    )
    h.check("%s: nothing is red" % where, not red(), red())
    h.check("%s: the %d bodies are back" % (where, count), len(volumes()) == count, volumes())
    hidden = [x.Label for x in s.bodies() if s.volume(x) > 1e-9 and not s.shown(x)]
    h.check("%s: every body is shown" % where, not hidden, hidden)


def setup():
    from fission180 import parameters

    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("Drone")
    parameters.add_user(doc(), "Thickness", "mm", "2.5")
    doc().recompute()
    h.fit()
    h.ribbon("Create Sketch")


def pick_xy():
    if pl.square_point("XY_Plane") is not None:
        pl.click_square("XY_Plane")
    else:
        pl.click_on_plane(V(15, 15, 0))


def draw():
    sk = h.in_sketch()
    if h.check("sketch open", sk is not None):
        for x in XS:
            h.draw_rectangle(sk, x, 0, x + 20, 60)


def finish():
    h.ribbon("Finish Sketch")


def extrude():
    h.fit()
    h.press("e")


def make_click(x):
    def click():
        h.click(V(x + 10, 30, 0))

    click.__name__ = "area_%d" % x
    return click


def distance():
    panel = b.active_panel()
    field = getattr(getattr(panel, "distance", None), "widget", None)
    if h.check("Extrude dialog", field is not None):
        b.type_into(field, "-Thickness")
        QtTest.QTest.keyClick(field, QtCore.Qt.Key_Tab)
        QtWidgets.QApplication.processEvents()


def operation():
    panel = b.active_panel()
    if panel is not None:
        b.choose(panel.operation, "New Body")


def extrude_ok():
    h.task_button("OK")


def five_bodies():
    h.check(
        "five bodies of one extrude, each a strip %g thick" % T, volumes() == [STRIP] * 5, volumes()
    )
    h.check(
        "the distance follows the parameter",
        any(
            "Thickness" in str(e)
            for o in doc().Objects
            for _p, e in getattr(o, "ExpressionEngine", [])
        ),
    )
    S["titles"] = list(t.titles())
    h.click_empty()
    h.fit()
    h.ribbon("Combine")


def make_body_click(x):
    def click():
        h.click(V(x + 10, 30, 0))

    click.__name__ = "body_%d" % x
    return click


def combine_ok():
    p = s.panel()
    ok = p is not None and p.options["target"] is not None and len(p.options["tools"]) == 4
    h.check("target and four tools", ok, p and p.options)
    h.task_button("OK")


def combined():
    h.check("one Combine", len(combines()) == 1, combines())
    h.check("one body of five solids", volumes() == [5 * STRIP], volumes())
    h.check("nothing is red", not red(), red())
    S["undo"] = list(doc().UndoNames)
    h.check(
        "the Combine is one undo step",
        S["undo"][:1] == ["Combine"] and S["undo"].count("Combine") == 1,
        S["undo"],
    )
    t.undo()


def a_undone():
    clean("A Ctrl+Z")
    h.check("the timeline is as before the Combine", t.titles() == S["titles"], t.titles())
    t.redo()


def a_redone():
    h.check("Ctrl+Y: the Combine is back and valid", len(combines()) == 1 and not red(), red())
    h.check("one body of five solids again", volumes() == [5 * STRIP], volumes())
    t.undo()


def a_undone_again():
    clean("A Ctrl+Z again")


def b_parameter():
    from fission180 import parameters

    doc().openTransaction("Change Parameters")
    parameters.set_user(doc(), "Thickness", "4 mm")
    doc().commitTransaction()
    doc().recompute()


def b_changed():
    h.check("the strips follow the parameter", volumes() == [20 * 60 * 4.0] * 5, volumes())
    t.undo()


def b_undone():
    h.check("Ctrl+Z: 2.5 thick again", volumes() == [STRIP] * 5, volumes())
    clean("B")
    h.click_empty()
    h.ribbon("Combine")


def c_undo_in_dialog():
    p = s.panel()
    h.check("the Combine is previewed", p is not None and len(combines()) == 1, combines())
    t.undo()


def c_closed():
    h.check("Ctrl+Z in the dialog closes it", s.panel() is None)
    clean("C Ctrl+Z in the dialog")
    t.redo()


def c_redo():
    h.check("Ctrl+Y brings no half-made Combine back as a red step", not red(), red())
    for combine in combines():
        h.check("a Combine that is there is valid", "Invalid" not in combine.State, combine.State)
    h.shot("end")


def d_combine_again():
    for combine in combines():
        App.Console.PrintMessage("[Fission 180] after C: %s %s\n" % (combine.Name, combine.State))
    S["had"] = len(combines())
    if not combines():
        h.click_empty()
        h.ribbon("Combine")


def d_ok():
    if s.panel() is not None:
        h.task_button("OK")


def d_two_undos_at_once():
    """Ctrl+Z twice with nothing in between (the Combine, then the Extrude under it), then
    Ctrl+Y twice the same way: the hands of someone going back to redo the extrude."""
    h.check("a Combine to undo", len(combines()) == 1 and not red(), (combines(), red()))
    S["names"] = list(doc().UndoNames)[:2]
    h.press(QtCore.Qt.Key_Z, QtCore.Qt.ControlModifier)
    h.press(QtCore.Qt.Key_Z, QtCore.Qt.ControlModifier)


def d_both_undone():
    h.check(
        "two steps were undone: %s" % S["names"],
        list(doc().RedoNames)[:2] == S["names"][::-1],
        doc().RedoNames,
    )
    h.check("no Combine is left behind", not combines(), [c.Name for c in combines()])
    h.check("nothing is red", not red(), red())
    h.press(QtCore.Qt.Key_Y, QtCore.Qt.ControlModifier)
    h.press(QtCore.Qt.Key_Y, QtCore.Qt.ControlModifier)


def d_both_redone():
    h.check("both are back and valid", len(combines()) == 1 and not red(), (combines(), red()))
    h.check("one body of five solids", volumes() == [5 * STRIP], volumes())
    t.undo()


def d_end():
    clean("D")


steps = [setup, pick_xy, draw, finish, extrude]
steps += [make_click(x) for x in XS]
steps += [distance, operation, extrude_ok, five_bodies]
steps += [make_body_click(x) for x in XS]
steps += [
    combine_ok,
    combined,
    a_undone,
    a_redone,
    a_undone_again,
    b_parameter,
    b_changed,
    b_undone,
]
steps += [make_body_click(x) for x in XS]
steps += [c_undo_in_dialog, c_closed, c_redo, d_combine_again]
steps += [make_body_click(x) for x in XS]
steps += [d_ok, d_two_undos_at_once, d_both_undone, d_both_redone, d_end]
for step in steps:
    step.timeout_s = 120

h.run("book_modify_combine_undo", steps, paced_by="state")
