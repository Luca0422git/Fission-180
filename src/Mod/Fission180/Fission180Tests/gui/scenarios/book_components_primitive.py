# SPDX-License-Identifier: LGPL-2.1-or-later
"""A primitive goes into the ACTIVE component too (wave 7: the one rule of the book parity
report's bugs 5 - 8, checked for CREATE > Box). Only real input for what is tested.

Setup (through the modules): "Nozzle" with a 20 x 20 x 10 block standing 60 mm along X; the
empty components "Block" and "Cap".

  A  Block made active (its ring), CREATE > Box, the XY plane, two corners, OK: the box's
     body is in Block (an empty component has no body yet: the box went to the design's
     root).
  B  Cap made active, CREATE > Box on the Nozzle's top face, Operation New Body, OK: the
     body is in Cap, standing on the Nozzle's face; the Nozzle is unchanged.
  C  Undo, Redo.
"""

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import book_components_steps as k
from Fission180Tests.gui import component_steps as cs
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import primitive_input as pi
from Fission180Tests.gui import timeline_input as t

V = App.Vector
state = {}


def panel():
    return pi.panel("BoxPanel")


def new_design():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("BookComponentsPrimitive")
    nozzle = k.new_component("Nozzle", at=(60, 0, 0))
    state["nozzle_body"] = k.add_box(nozzle, (0, 0, 20, 20), 10).Name
    k.new_component("Block")
    k.new_component("Cap")
    k.settle_design()


# -- A ---------------------------------------------------------------------------------------------
def a_activate():
    cs.click_radio("Block")


a_activate.done = lambda: k.active_label() == "Block"
a_activate.done_what = "Block is active"


def box_command():
    h.click_empty()
    h.fit()
    pi.menu("Box")


box_command.done = lambda: panel() is not None
box_command.done_what = "the Box dialog is open"


def a_plane():
    p = panel()
    h.check("waits for a plane", p is not None and p.state == "plane", p and p.state)
    pl.click_square("XY_Plane")


def a_corner1():
    p = panel()
    h.check("now placing", p is not None and p.state == "place", p and p.state)
    pl.click_on_plane(V(0, 0, 0))


def a_corner2():
    pl.click_on_plane(V(20, 30, 0))


def ok():
    p = panel()
    if h.check("the box is placed", p is not None and p.state == "ready", p and p.state):
        h.caught_up(p)
        h.check("the dialog shows no problem", not p.message.text().strip(), p.message.text())
    h.task_button("OK")


ok.done = lambda: panel() is None
ok.done_what = "the Box dialog closed"


def a_made():
    found = k.bodies_of("Block")
    h.check(
        "the box's body is in Block, the active component",
        len(found) == 1,
        [(x.Label, k.container_label(x)) for x in pi.bodies()],
    )
    h.check("nothing went to the root", not k.bodies_of(""), [x.Label for x in k.bodies_of("")])
    h.check("Block is still active", k.active_label() == "Block", k.active_label())
    k.no_empty_invalid_bodies()


# -- B ---------------------------------------------------------------------------------------------
def b_activate():
    cs.click_radio("Cap")


b_activate.done = lambda: k.active_label() == "Cap"
b_activate.done_what = "Cap is active"


def b_face():
    h.click(V(70, 10, 10))  # the Nozzle's top face


def b_corner1():
    p = panel()
    h.check("the face is the plane", p is not None and p.state == "place", p and p.state)
    h.click(V(64, 4, 10))


def b_corner2():
    h.click(V(76, 16, 10))


def b_operation():
    p = panel()
    if h.check("the box is placed", p is not None and p.state == "ready", p and p.state):
        h.caught_up(p)
        if p.operation.currentText() != "New Body":
            b.choose(p.operation, "New Body")


def b_made():
    found = k.bodies_of("Cap")
    if h.check(
        "the new body is in Cap, the active component",
        len(found) == 1,
        [(x.Label, k.container_label(x)) for x in pi.bodies()],
    ):
        box = k.box(found[0])
        h.check("it stands on the Nozzle's top face (z 10)", abs(box[2] - 10) < 1e-4, box)
        h.check("over the face", box[0] > 60 - 1e-6 and box[3] < 80 + 1e-6, box)
    nozzle = k.doc().getObject(state["nozzle_body"])
    h.check("the Nozzle is unchanged", k.close(k.volume(nozzle), 4000.0), k.volume(nozzle))
    h.check(
        "the Nozzle has one body",
        len(k.bodies_of("Nozzle")) == 1,
        [x.Label for x in k.all_bodies_of("Nozzle")],
    )
    h.check("Cap is still active", k.active_label() == "Cap", k.active_label())


# -- C ---------------------------------------------------------------------------------------------
def undo():
    t.undo()


def c_undone():
    h.check("Undo takes the box", not k.bodies_of("Cap"))


def redo():
    t.redo()


def c_redone():
    h.check("Redo brings it back, in Cap", len(k.bodies_of("Cap")) == 1)


h.run(
    "book_components_primitive",
    [
        new_design,
        a_activate,
        box_command,
        a_plane,
        a_corner1,
        a_corner2,
        ok,
        a_made,
        b_activate,
        box_command,
        b_face,
        b_corner1,
        b_corner2,
        b_operation,
        ok,
        b_made,
        undo,
        c_undone,
        redo,
        c_redone,
    ],
    paced_by="state",
)
