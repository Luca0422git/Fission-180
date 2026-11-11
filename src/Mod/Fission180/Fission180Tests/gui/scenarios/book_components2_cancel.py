# SPDX-License-Identifier: LGPL-2.1-or-later
"""A command that needs a body and is then cancelled leaves nothing behind: no empty body,
no open undo step (wave 7, components-2). Only real input.

Fission 180 makes a body when a command needs one in a design (or an active component)
that has none: Create Sketch (to show the origin planes), the CONSTRUCT tools, Box.
FreeCAD's Body command leaves its undo step "Add a Body" open when it is run from inside
another command, and nothing closed it when Create Sketch's plane picker was cancelled:
an empty body and a pending step stayed (the next change anywhere was recorded as "Add a
Body"). Found by the harness's check that no undo step stays open (`STRICT["undo"]`, on
for this scenario).

  A  A new, empty design. Create Sketch (the ribbon), Esc: no body, no open step, nothing
     to undo.
  B  Create Sketch again, Cancel (the button): the same.
  C  CONSTRUCT > Offset Plane, Cancel: the same.
  D  CREATE > Box, Esc: the same.
  E  A component "Tube" made and active (New Component, real input); Create Sketch, Esc:
     Tube holds no body.
  F  Create Sketch, the XY square: the sketch is in Body1 of Tube; Finish Sketch. Ctrl+Z
     until nothing is left to undo but the component: no sketch, no body.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import book_components_steps as k
from Fission180Tests.gui import component_steps as cs
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import inspect_steps as ist
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import primitive_input as pi
from Fission180Tests.gui import timeline_input as t

state = {}


def new_design():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("BookComponents2Cancel")
    h.fit()


def bodies():
    return [o for o in k.doc().Objects if o.TypeId == "PartDesign::Body"]


def nothing_left(tag):
    doc = k.doc()
    h.check("%s: no body is left" % tag, not bodies(), [b.Label for b in bodies()])
    h.check(
        "%s: no undo step is left open" % tag,
        App.getActiveTransaction() is None and not doc.HasPendingTransaction,
        App.getActiveTransaction(),
    )
    h.check(
        "%s: nothing new to undo" % tag,
        doc.UndoCount == state.get("undo", 0),
        (list(doc.UndoNames), state.get("undo", 0)),
    )


def picker_open():
    return pl.picker() is not None


def no_dialog():
    return not Gui.Control.activeDialog()


# -- A, B: Create Sketch cancelled ---------------------------------------------------------------
def a_sketch():
    state["undo"] = k.doc().UndoCount
    h.ribbon("Create Sketch")


a_sketch.done = picker_open
a_sketch.done_what = "Create Sketch shows its planes"


def a_escape():
    h.check("a body was made to show the planes", len(bodies()) == 1, [b.Label for b in bodies()])
    h.press(QtCore.Qt.Key_Escape)


a_escape.done = no_dialog
a_escape.done_what = "Create Sketch closed"


def a_clean():
    nothing_left("Create Sketch, Esc")


def b_sketch():
    h.ribbon("Create Sketch")


b_sketch.done = picker_open
b_sketch.done_what = "Create Sketch shows its planes"


def b_cancel():
    h.task_button("Cancel")


b_cancel.done = no_dialog
b_cancel.done_what = "Create Sketch closed"


def b_clean():
    nothing_left("Create Sketch, Cancel")


# -- C: a CONSTRUCT tool cancelled -------------------------------------------------------------
def c_offset():
    ist.menu("CONSTRUCT", "Offset Plane")


c_offset.done = lambda: ist.construct_panel() is not None
c_offset.done_what = "the Offset Plane dialog is open"


def c_cancel():
    h.task_button("Cancel")


c_cancel.done = no_dialog
c_cancel.done_what = "Offset Plane closed"


def c_clean():
    nothing_left("Offset Plane, Cancel")


# -- D: a primitive cancelled ------------------------------------------------------------------
def d_box():
    pi.menu("Box")


d_box.done = lambda: bool(Gui.Control.activeDialog())
d_box.done_what = "the Box dialog is open"


def d_escape():
    h.press(QtCore.Qt.Key_Escape)


d_escape.done = no_dialog
d_escape.done_what = "Box closed"


def d_clean():
    nothing_left("Box, Esc")


# -- E: in an empty, active component ------------------------------------------------------------
def e_new():
    Gui.Selection.clearSelection()
    h.ribbon("New Component")


e_new.done = lambda: cs.new_component_panel() is not None
e_new.done_what = "the New Component dialog is open"


def e_name():
    cs.type_name("Tube")


def e_ok():
    h.task_button("OK")


e_ok.done = lambda: k.active_label() == "Tube"
e_ok.done_what = "Tube is made and active"


def e_sketch():
    state["undo"] = k.doc().UndoCount
    h.ribbon("Create Sketch")


e_sketch.done = picker_open
e_sketch.done_what = "Create Sketch shows Tube's planes"


def e_escape():
    h.check("a body was made in Tube", len(k.all_bodies_of("Tube")) == 1)
    h.press(QtCore.Qt.Key_Escape)


e_escape.done = no_dialog
e_escape.done_what = "Create Sketch closed"


def e_clean():
    nothing_left("Create Sketch in Tube, Esc")
    h.check("Tube is still the active component", k.active_label() == "Tube", k.active_label())


# -- F: the sketch made ------------------------------------------------------------------------
def f_sketch():
    h.ribbon("Create Sketch")


f_sketch.done = picker_open
f_sketch.done_what = "Create Sketch shows Tube's planes"


def f_plane():
    pl.click_square("XY_Plane")


f_plane.done = lambda: h.in_sketch() is not None
f_plane.done_what = "a sketch opened"


def f_made():
    sk = h.in_sketch()
    if h.check("sketch open", sk is not None):
        h.check("the sketch is in Tube", k.container_label(sk) == "Tube", k.container_label(sk))
        found = k.all_bodies_of("Tube")
        h.check(
            "in Tube's one body, Body1",
            len(found) == 1 and found[0].Label == "Body1" and sk in found[0].Group,
            [b.Label for b in found],
        )
    h.ribbon("Finish Sketch")


f_made.done = lambda: h.in_sketch() is None
f_made.done_what = "the sketch closed"


def f_undo():
    doc = k.doc()
    h.check(
        "no undo step is left open after the sketch",
        App.getActiveTransaction() is None and not doc.HasPendingTransaction,
        App.getActiveTransaction(),
    )
    t.undo()


def f_undo_again():
    if bodies():
        t.undo()


def f_undone():
    sketches = [o for o in k.doc().Objects if o.TypeId == "Sketcher::SketchObject"]
    h.check("Ctrl+Z: the sketch is gone", not sketches, [o.Label for o in sketches])
    h.check("Ctrl+Z: and its body", not bodies(), [b.Label for b in bodies()])
    h.check("Tube is still there", k.part("Tube") is not None, k.labels())


h.STRICT["undo"] = True
h.run(
    "book_components2_cancel",
    [
        new_design,
        a_sketch,
        a_escape,
        a_clean,
        b_sketch,
        b_cancel,
        b_clean,
        c_offset,
        c_cancel,
        c_clean,
        d_box,
        d_escape,
        d_clean,
        e_new,
        e_name,
        e_ok,
        e_sketch,
        e_escape,
        e_clean,
        f_sketch,
        f_plane,
        f_made,
        f_undo,
        f_undo_again,
        f_undone,
    ],
    paced_by="state",
)
