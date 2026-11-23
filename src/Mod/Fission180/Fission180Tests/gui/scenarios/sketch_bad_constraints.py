# SPDX-License-Identifier: LGPL-2.1-or-later
"""A sketch whose constraints are redundant or conflict says which, with the constraint list's
numbers, and shows them (bug report 2026-11-23: the timeline passed on FreeCAD's message,
which counts from 1 and named a needed constraint; ideally the UI highlights them).

A  Redundant: an arc and a line joined end to end by a Tangent, then a Point on Curve of the
   same end on the arc (constraint 3, which the Tangent already says), then the join of the
   line's other end (constraint 4, needed). The timeline's message for the sketch names
   constraint 3 in words and by number, never 4. Opened: the Sketch Palette says "Redundant
   constraints"; a click on that note shows the same in words beside the pointer and
   highlights constraint 3 in the sketch.
B  Conflicting: a line with a 10 mm and, later, a 20 mm horizontal distance (constraints 2 and
   4). The timeline's message names both; the palette's note, clicked, highlights both.
"""

import FreeCAD as App
import FreeCADGui as Gui
import Part
import Sketcher
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_input as si

V = App.Vector
s = {}


def explain():
    from fission180 import sketch_explain

    return sketch_explain


def told():
    from fission180 import commands

    return commands._TOLD.get("msg") or ""


def note():
    pal = si.palette()
    return pal.findChild(QtWidgets.QLabel, "Fission180PaletteFreedom") if pal else None


def note_text():
    label = note()
    return label.text() if label is not None else None


def message(sketch):
    from fission180 import timeline_ops

    item = timeline_ops.timeline(sketch.Document).find(sketch.Name)
    return item.message if item is not None else ""


def new_sketch(name):
    from fission180 import commands, sketch_ui

    body = commands.ensure_body()
    planes = sketch_ui.origin_planes(body)
    sk = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    sk.Label = name
    return sk


# -- A -----------------------------------------------------------------------------------------
def a_setup():
    App.newDocument("BadConstraints")
    sk = new_sketch("Redundant")
    sk.addGeometry(Part.ArcOfCircle(Part.Circle(V(0, 0, 0), V(0, 0, 1), 10), 0.0, 1.5707963267948966))
    sk.addGeometry(Part.LineSegment(V(0, 10, 0), V(-20, 10, 0)))
    sk.addGeometry(Part.LineSegment(V(-20, 10, 0), V(-20, -10, 0)))
    sk.addConstraint(Sketcher.Constraint("Coincident", 0, 3, -1, 1))  # 0
    sk.addConstraint(Sketcher.Constraint("Radius", 0, 10.0))  # 1
    sk.addConstraint(Sketcher.Constraint("Tangent", 1, 1, 0, 2))  # 2
    sk.addConstraint(Sketcher.Constraint("PointOnObject", 1, 1, 0))  # 3 said by 2 already
    sk.addConstraint(Sketcher.Constraint("Coincident", 1, 2, 2, 1))  # 4 needed
    sk.addConstraint(Sketcher.Constraint("Vertical", 2))  # 5
    App.ActiveDocument.recompute()
    s["a"] = sk


a_setup.done = lambda: [i - 1 for i in s["a"].RedundantConstraints] == [3]
a_setup.done_what = "the solver to find constraint 3 redundant"


def a_timeline():
    text = message(s["a"])
    h.check("A: the timeline's message names constraint 3", "(constraint 3)" in text, text)
    h.check("A: ... and never the needed constraint 4", "4" not in text, text)
    h.check("A: ... in words", "Coincident" in text, text)
    h.check("A: ... as one plain line", "\n" not in text and "Remove the following" not in text, text)


def a_open():
    Gui.ActiveDocument.setEdit(s["a"].Name)


a_open.done = lambda: note_text() == "Redundant constraints"
a_open.done_what = 'the Sketch Palette to say "Redundant constraints"'


def a_click():
    label = note()
    h.check("A: the note can be clicked", label.cursor().shape() == QtCore.Qt.PointingHandCursor)
    pos = label.rect().center()
    h.pointer_to(label, pos)
    QtTest.QTest.mouseClick(label, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, pos)


a_click.done = lambda: explain().highlighted() == [3]
a_click.done_what = "constraint 3 to be highlighted"


def a_shown():
    text = told()
    h.check("A: the message names constraint 3 in words and by number", "(constraint 3)" in text and "Coincident" in text, text)
    h.check("A: ... and says it is highlighted", "highlighted" in text, text)
    h.check("A: the rings show", bool(explain().highlight_rings()))


def a_close():
    explain().clear_highlight()
    Gui.ActiveDocument.resetEdit()


a_close.done = lambda: h.in_sketch() is None
a_close.done_what = "the sketch to close"


# -- B -----------------------------------------------------------------------------------------
def b_setup():
    sk = new_sketch("Conflict")
    sk.addGeometry(Part.LineSegment(V(0, 0, 0), V(10, 0, 0)))
    sk.addGeometry(Part.LineSegment(V(10, 0, 0), V(10, 5, 0)))
    sk.addConstraint(Sketcher.Constraint("Coincident", 0, 1, -1, 1))  # 0
    sk.addConstraint(Sketcher.Constraint("Horizontal", 0))  # 1
    sk.addConstraint(Sketcher.Constraint("DistanceX", 0, 1, 0, 2, 10.0))  # 2
    sk.addConstraint(Sketcher.Constraint("Coincident", 0, 2, 1, 1))  # 3
    sk.addConstraint(Sketcher.Constraint("DistanceX", 0, 1, 0, 2, 20.0))  # 4 fights 2
    sk.addConstraint(Sketcher.Constraint("Vertical", 1))  # 5
    App.ActiveDocument.recompute()
    s["b"] = sk


b_setup.done = lambda: sorted(i - 1 for i in s["b"].ConflictingConstraints) == [2, 4]
b_setup.done_what = "the solver to find constraints 2 and 4 in conflict"


def b_timeline():
    text = message(s["b"])
    h.check("B: the timeline's message names constraints 2 and 4", "(constraints 2 and 4)" in text, text)


def b_open():
    Gui.ActiveDocument.setEdit(s["b"].Name)


b_open.done = lambda: note_text() == "Conflicting constraints"
b_open.done_what = 'the Sketch Palette to say "Conflicting constraints"'


def b_click():
    label = note()
    pos = label.rect().center()
    h.pointer_to(label, pos)
    QtTest.QTest.mouseClick(label, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, pos)


b_click.done = lambda: sorted(explain().highlighted()) == [2, 4]
b_click.done_what = "constraints 2 and 4 to be highlighted"


def b_shown():
    text = told()
    h.check("B: the message names both dimensions by number", "(constraints 2 and 4)" in text, text)


def b_close():
    explain().clear_highlight()
    Gui.ActiveDocument.resetEdit()


b_close.done = lambda: h.in_sketch() is None
b_close.done_what = "the sketch to close"


h.run(
    "sketch_bad_constraints",
    [a_setup, a_timeline, a_open, a_click, a_shown, a_close, b_setup, b_timeline, b_open, b_click, b_shown, b_close],
    paced_by="state",
)
