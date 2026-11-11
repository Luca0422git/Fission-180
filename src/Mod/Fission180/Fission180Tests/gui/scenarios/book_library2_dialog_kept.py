# SPDX-License-Identifier: LGPL-2.1-or-later
"""A dialog that is asked about while it is being built is not forgotten (wave 7, library-2,
item 13: the flake of body_pick_many, "Move/Copy opened from three browser rows held no body
at the next step", 1 run in 10).

What happened: a dialog registers itself as the open one while it is built, runs its first
preview, and only then is put on screen (Gui.Control.showDialog). taskui.current() forgot
the registered dialog whenever no task dialog was on screen. A timer that asked in that gap
(the selection read-out asks 'is a dialog open?' a moment after every selection change, and
a slow first preview lets timers run) made the dialog forgotten for good: it was on screen
and worked, but nothing knew it was open (no Esc, no "finish it before the next command",
no typing over the view).

A  (by script: it is the gap itself that is tested) Move/Copy built with three bodies
   selected, the question asked before it is shown: not open yet. Shown: it is the open
   dialog and holds the three bodies.
B  (real input) Y Distance 5 typed, Esc: the dialog closes, nothing moved; nothing is open.
C  (real input) the three rows clicked in the browser, the Move/Copy button: the open
   dialog holds all three; OK.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import harness as h

S = {}
X0 = (0, 40, 80)


def doc():
    return App.ActiveDocument


def three():
    return [doc().getObject("B%d" % i) for i in (1, 2, 3)]


def boxes():
    return [(round(b.Shape.BoundBox.XMin, 6), round(b.Shape.BoundBox.YMin, 6)) for b in three()]


def at_start():
    return boxes() == [(float(x), 0.0) for x in X0]


def setup():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("DialogKept")
    d = doc()
    for i, x in enumerate(X0, start=1):
        body = d.addObject("PartDesign::Body", "B%d" % i)
        box = d.addObject("PartDesign::AdditiveBox", "B%dBox" % i)
        body.addObject(box)
        box.Length, box.Width, box.Height = 20, 20, 10
        box.Placement.Base = App.Vector(x, 0, 0)
    d.recompute()
    h.fit()


# -- A --------------------------------------------------------------------------------------------
def a_built():
    from fission180 import move_ui, taskui

    d = doc()
    Gui.Selection.clearSelection()
    for body in three():
        Gui.Selection.addSelection(d.Name, body.Name)
    panel = S["panel"] = move_ui.MovePanel(d)
    h.check("built, not on screen yet", not Gui.Control.activeDialog())
    h.check("asked in the gap: no dialog is open yet", taskui.current() is None)
    h.check("asked again", taskui.current() is None)
    Gui.Control.showDialog(panel)


def a_shown():
    from fission180 import taskui

    panel = S["panel"]
    h.check("on screen", bool(Gui.Control.activeDialog()))
    h.check("it is the open dialog (not forgotten)", taskui.current() is panel, taskui.current())
    h.check(
        "it holds the three bodies", panel.options["bodies"] == three(), panel.options["bodies"]
    )
    s.type_value(panel.distance_fields[1].widget, "5")


def a_moved():
    h.check("Y Distance 5: all three moved", boxes() == [(float(x), 5.0) for x in X0], boxes())
    h.press(QtCore.Qt.Key_Escape)


a_moved.done = lambda: not Gui.Control.activeDialog()
a_moved.done_what = "Esc closed the dialog"


# -- B --------------------------------------------------------------------------------------------
def b_closed():
    from fission180 import taskui

    h.check("Esc: nothing moved", at_start(), boxes())
    h.check("nothing is open", taskui.current() is None and S["panel"]._closed)
    h.click_empty()
    s.click_browser_row(three()[0].Label)
    s.click_browser_row(three()[1].Label, QtCore.Qt.ControlModifier)
    s.click_browser_row(three()[2].Label, QtCore.Qt.ControlModifier)


# -- C --------------------------------------------------------------------------------------------
def c_button():
    h.ribbon("Move/Copy")


c_button.done = lambda: bool(Gui.Control.activeDialog())
c_button.done_what = "the Move/Copy dialog is on screen"


def c_taken():
    p = s.panel()
    h.check("the open dialog is Move/Copy", p is not None and p.title == "Move/Copy", p)
    if p is None:
        return
    h.check("it holds all three bodies", p.options["bodies"] == three(), p.options["bodies"])
    s.type_value(p.distance_fields[0].widget, "7")


def c_ok():
    h.check("X Distance 7: all three moved", boxes() == [(float(x + 7), 0.0) for x in X0], boxes())
    h.task_button("OK")


c_ok.done = lambda: not Gui.Control.activeDialog()
c_ok.done_what = "OK closed the dialog"


def c_done():
    from fission180 import taskui

    h.check("all three stay moved", boxes() == [(float(x + 7), 0.0) for x in X0], boxes())
    h.check("nothing is open", taskui.current() is None)


h.run(
    "book_library2_dialog_kept",
    [setup, a_built, a_shown, a_moved, b_closed, c_button, c_taken, c_ok, c_done],
    paced_by="state",
)
