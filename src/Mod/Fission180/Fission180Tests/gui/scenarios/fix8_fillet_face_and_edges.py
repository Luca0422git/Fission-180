# SPDX-License-Identifier: LGPL-2.1-or-later
"""Wave 7, fix-8: Fillet with two edges and a face picked, a size typed, OK: OK makes the
fillet, or the dialog stays open and says why, in the dialog and next to the pointer. Only
real input.

The book's Finger Surfboard (replay_03_surfboard, step fillet_ok, failed twice on GitHub): the
fin's two edges and a face picked, 1 typed, OK. On that run's board the search for the largest
round that fits ended with "no limit": its smallest size (0.1 mm) was refused too, by an
OpenCASCADE that refuses some small rounds on a lofted skin and builds bigger ones (0.01 and
0.02 mm refused, 0.05 to 0.49 mm built). The box kept 1 mm with no note, OK refused it with
the reason shown before (nothing new on the screen, nothing by the pointer), and the dialog
stayed open for 240 s. Now the search tries a few sizes between before "no limit"
(value_limits.SCAN_TRIES, unit tested), and a refused OK says why next to the pointer too
(fillet_ui.BlendPanel._ok_refused).

Box 40 x 30 x 10, Fillet: the front top edge, the right top edge, then the front face (its
four edges are rounded):
  A  1 typed: it fits, no note, no message; the preview takes the rounds off
  B  50 typed: held at the largest that fits, the note says so; nothing in the message
  C  "100/2" typed and Tab (a formula: never rewritten): the message says it does not fit
     and the largest that fits
  D  OK: the dialog stays open, its message says why, and the same reason is shown next to
     the pointer
  E  50 typed again: held with the note; OK makes the fillet with that size
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import harness as h

V = App.Vector
s = {}
FRONT_TOP = V(20, 0, 10)
RIGHT_TOP = V(40, 15, 10)
FRONT_FACE = V(14, 0, 4)


def panel():
    return b.blend_panel()


def note(p):
    return p.limit_label.text() if p is not None and p.limit_label.isVisible() else ""


def told():
    from fission180 import commands

    return str(commands._TOLD.get("msg") or "")


def radius_of(step):
    from fission180 import fillet_sets

    if fillet_sets.is_sets(step):
        return float(fillet_sets.read_spec(step)["sets"][0]["radius"])
    return step.Radius.Value


def fillet_steps():
    from fission180 import fillet_sets

    return [o for o in h.body().Group if o.TypeId == "PartDesign::Fillet" or fillet_sets.is_sets(o)]


def picks():
    p = panel()
    return list(p.refs) if p is not None else []


# -- the picks ---------------------------------------------------------------------------------
def fillet_start():
    s["box"] = h.solid_volume()
    Gui.Selection.clearSelection()
    h.fit()
    h.ribbon("Fillet")


fillet_start.done = lambda: panel() is not None
fillet_start.done_what = "the Fillet dialog is open"


def pick_front_top():
    h.click_edge(FRONT_TOP)


pick_front_top.done = lambda: len(picks()) == 1
pick_front_top.done_what = "the front top edge picked"


def pick_right_top():
    h.click_edge(RIGHT_TOP)


pick_right_top.done = lambda: len(picks()) == 2
pick_right_top.done_what = "the right top edge picked"


def pick_front_face():
    h.click(FRONT_FACE)


pick_front_face.done = lambda: len(picks()) == 3
pick_front_face.done_what = "the front face picked"


# -- A: 1 mm fits ------------------------------------------------------------------------------
def type_1():
    p = panel()
    refs = picks()
    h.check(
        "two edges and a face picked",
        [r[:4] for r in refs] == ["Edge", "Edge", "Face"],
        refs,
    )
    b.type_into(p.radius.widget, "1")


def typed_1():
    p = panel()
    h.caught_up(p)
    d = p._value(p._row_key(), "radius")
    h.check("A: 1 mm fits: no note", note(p) == "" and abs(d - 1.0) < 1e-9, (note(p), d))
    h.check("A: no message", p.message.text() == "", p.message.text())
    v = h.solid_volume()
    # the five 1 mm rounds: (1 - pi/4) mm2 off per mm of edge, 30 + 2 x 40 + 2 x 10 mm
    h.check("A: the preview takes the rounds off", 20.0 < s["box"] - v < 35.0, (s["box"], v))


# -- B: 50 mm is held at what fits -------------------------------------------------------------
def type_50():
    b.type_into(panel().radius.widget, "50")


def typed_50():
    p = panel()
    h.caught_up(p)
    d = p._value(p._row_key(), "radius")
    s["limit"] = d
    text = note(p)
    h.check(
        "B: 50 is held at the largest that fits and the note says so",
        text == "50 mm does not fit: limited to %.2f mm" % d and 1.0 < d < 50.0,
        (text, d),
    )
    h.check("B: no message", p.message.text() == "", p.message.text())
    h.shot("b-held")


# -- C: a formula that does not fit is said, not rewritten -------------------------------------
def type_formula():
    p = panel()
    b.type_into(p.radius.widget, "100/2")
    QtTest.QTest.keyClick(p.radius.widget, QtCore.Qt.Key_Tab)  # leave the box: taken


def formula_said():
    p = panel()
    h.caught_up(p)
    text = p.message.text()
    h.check("C: it does not fit, the message says so", "too big" in text, text)
    h.check(
        "C: with the largest that fits",
        "Largest that fits here: %.2f mm" % s["limit"] in text,
        text,
    )
    h.check("C: no note (nothing held)", note(p) == "", note(p))
    s["told"] = told()


# -- D: OK refused: said in the dialog and next to the pointer ---------------------------------
def ok_refused():
    s["reason"] = panel().message.text()
    h.task_button("OK")


ok_refused.done = lambda: told() != s["told"] and "too big" in told()
ok_refused.done_what = "the reason OK did not finish shown next to the pointer"


def refused_said():
    p = panel()
    h.check("D: the dialog stays open", p is not None and Gui.Control.activeDialog())
    h.check("D: its message says why", "too big" in p.message.text(), p.message.text())
    h.check(
        "D: the same reason next to the pointer",
        told() and told() in s["reason"],
        (told(), s["reason"]),
    )
    tip = QtWidgets.QToolTip.text() if QtWidgets.QToolTip.isVisible() else ""
    h.check("D: shown as a tip", "too big" in tip, tip)
    h.shot("d-ok-refused")


# -- E: 50 held, OK makes it -------------------------------------------------------------------
def type_50_again():
    b.type_into(panel().radius.widget, "50")


def typed_50_again():
    p = panel()
    h.caught_up(p)
    d = p._value(p._row_key(), "radius")
    h.check(
        "E: 50 held again with the note",
        note(p).startswith("50 mm does not fit: limited to ") and abs(d - s["limit"]) < 1e-9,
        (note(p), d),
    )
    h.check("E: no message", p.message.text() == "", p.message.text())
    h.task_button("OK")


typed_50_again.done = lambda: panel() is None
typed_50_again.done_what = "OK made the fillet"


def fillet_made():
    h.check("E: the dialog closed", not Gui.Control.activeDialog())
    steps = fillet_steps()
    h.check("E: one fillet step", len(steps) == 1, steps)
    if steps:
        r = radius_of(steps[0])
        h.check("E: its radius is the one held", abs(r - s["limit"]) < 1e-9, (r, s["limit"]))
    shape = h.body().Shape
    h.check("E: a valid solid", shape.isValid() and len(shape.Solids) == 1)
    h.check("E: the rounds took material off", s["box"] - h.solid_volume() > 1.0)
    h.shot("e-made")


h.run(
    "fix8_fillet_face_and_edges",
    b.box_steps("Fix8FaceEdges")
    + [
        fillet_start,
        pick_front_top,
        pick_right_top,
        pick_front_face,
        type_1,
        typed_1,
        type_50,
        typed_50,
        type_formula,
        formula_said,
        ok_refused,
        refused_said,
        type_50_again,
        typed_50_again,
        fillet_made,
    ],
    paced_by="state",
)
