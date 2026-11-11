# SPDX-License-Identifier: LGPL-2.1-or-later
"""Move/Copy turns a component about its own origin, a paste stands on the occurrence that
was copied, and Move to Component leaves nothing behind (book parity report: the Drone's
copied motor, the Tesla Turbine's Bolt:5, "an empty, invalid Body"). Only real input for
what is tested.

Setup (through the modules): the component "Motor" (a 10 x 10 x 6 block from x 0, y 0),
standing at (0, -53, 0): its origin is at (0, -53, 0), the middle of its solid at
(5, -48, 3). The empty component "Frame". A 20 x 20 x 5 block "Body1" at the root, at
x 40..60.

  A  Motor's browser row, Ctrl+C, Ctrl+V: a linked copy Motor:2 with Move/Copy open on it,
     standing on Motor. The manipulator sits on the copy's origin (0, -53, 0). Z Angle 180,
     OK: the copy turned about its ORIGIN: its solid now spans x -10..0, y -63..-53 (about
     the middle of its solid it would have stayed in place).
  B  Motor:2's row, Ctrl+C, Ctrl+V: the paste (Motor:3) stands where Motor:2 stands (it
     started on the original Motor before), turned like it. Esc keeps it there.
  C  Undo takes the paste. Undo again: the turn of Motor:2. Redo twice.
  D  The root block's browser row, right-click > Move to Component > Frame: the body is in
     Frame, where it stood; no body is left at the root, none is invalid. Undo, Redo.
  E  Save, close, reopen: Motor:2 turned, the block in Frame.
"""

import os
import tempfile

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import book_components_steps as k
from Fission180Tests.gui import component2_steps as c
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import timeline_input as t

V = App.Vector
state = {}


def new_design():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("BookComponentsMove")
    motor = k.new_component("Motor", at=(0, -53, 0))
    k.add_box(motor, (0, 0, 10, 10), 6)
    k.new_component("Frame")
    state["block"] = k.add_box(None, (40, 0, 60, 20), 5).Name
    k.settle_design()


def setup_done():
    k.box_is("Motor stands at y -53", k.part("Motor"), [0, -53, 0, 10, -43, 6])
    h.check(
        "its origin is (0, -53, 0)", (k.part("Motor").Placement.Base - V(0, -53, 0)).Length < 1e-9
    )


def panel_open():
    return c.component_panel() is not None


def panel_closed():
    return c.component_panel() is None


# -- A ---------------------------------------------------------------------------------------------
def a_select():
    h.click_empty()
    t.click_row("Motor")


def copy_key():
    t.ctrl("c")


def paste_key():
    t.ctrl("v")


paste_key.done = panel_open
paste_key.done_what = "Move/Copy opened on the paste"


def a_pasted():
    copy = k.part("Motor:2")
    if not h.check("Motor:2 exists", copy is not None, k.labels()):
        return
    k.box_is("it stands on Motor", copy, [0, -53, 0, 10, -43, 6])
    p = c.component_panel()
    if not h.check("Move/Copy open on it", p is not None):
        return
    h.check(
        "on Motor:2",
        p.options.get("components") == [copy],
        [x.Label for x in p.options.get("components") or []],
    )
    triad = getattr(p, "triad", None)
    if h.check("manipulator shown", triad is not None):
        h.check(
            "on the component's origin (0, -53, 0), not the middle of its solid",
            (triad.center - V(0, -53, 0)).Length < 1e-6,
            triad.center,
        )
    c.type_value(p, "rz", "180")


def ok():
    p = c.component_panel()
    if p is not None:
        h.caught_up(p)
    h.task_button("OK")


ok.done = panel_closed
ok.done_what = "the dialog closed"


def a_turned():
    copy = k.part("Motor:2")
    k.box_is("the copy turned 180 degrees about its origin", copy, [-10, -63, 0, 0, -53, 6])
    k.box_is("Motor itself stayed", k.part("Motor"), [0, -53, 0, 10, -43, 6])
    h.check(
        "the copy's origin did not move",
        (copy.Placement.Base - V(0, -53, 0)).Length < 1e-6,
        copy.Placement,
    )
    h.shot("A-turned")


# -- B ---------------------------------------------------------------------------------------------
def b_select():
    h.click_empty()
    t.click_row("Motor:2")


def b_pasted():
    copy = k.part("Motor:3")
    if h.check("Motor:3 exists", copy is not None, k.labels()):
        k.box_is(
            "it stands where Motor:2 stands, turned like it (not on the original Motor)",
            copy,
            [-10, -63, 0, 0, -53, 6],
        )


def escape():
    h.press(QtCore.Qt.Key_Escape)


escape.done = panel_closed
escape.done_what = "the dialog closed"


def b_kept():
    copy = k.part("Motor:3")
    if h.check("Esc keeps the paste", copy is not None, k.labels()):
        k.box_is("where it was pasted", copy, [-10, -63, 0, 0, -53, 6])


# -- C ---------------------------------------------------------------------------------------------
def undo():
    t.undo()


def redo():
    t.redo()


def c_no_paste():
    h.check("Undo takes the paste", k.part("Motor:3") is None, k.labels())


def c_not_turned():
    copy = k.part("Motor:2")
    if h.check("Motor:2 is still there", copy is not None, k.labels()):
        k.box_is("Undo takes its turn", copy, [0, -53, 0, 10, -43, 6])


def c_redone():
    k.box_is("Redo: Motor:2 turned again", k.part("Motor:2"), [-10, -63, 0, 0, -53, 6])
    h.check("Redo: Motor:3 is back", k.part("Motor:3") is not None, k.labels())


# -- D ---------------------------------------------------------------------------------------------
def block():
    return k.doc().getObject(state["block"])


def d_menu():
    from Fission180Tests.gui import widget_input as w

    h.click_empty()
    tree, pos = t.row_point(block().Label)
    ok = pos is not None and w.right_click_sub(tree.viewport(), pos, "Move to Component", "Frame")
    h.check("the body's menu > Move to Component > Frame", ok)


d_menu.done = lambda: k.container_label(block()) == "Frame"
d_menu.done_what = "the block is in Frame"


def d_moved():
    h.check(
        "the block is in Frame", k.container_label(block()) == "Frame", k.container_label(block())
    )
    k.box_is("where it stood", block(), [40, 0, 0, 60, 20, 5])
    h.check(
        "no body is left at the root",
        not k.all_bodies_of(""),
        [b.Label for b in k.all_bodies_of("")],
    )
    k.no_empty_invalid_bodies()
    h.check("Frame shows one body", len(k.bodies_of("Frame")) == 1)


def d_undone():
    h.check("Undo: the block is back at the root", k.container_label(block()) == "")
    k.box_is("in place", block(), [40, 0, 0, 60, 20, 5])


def d_redone():
    h.check("Redo: in Frame again", k.container_label(block()) == "Frame")


# -- E ---------------------------------------------------------------------------------------------
def e_save():
    path = os.path.join(tempfile.mkdtemp(prefix="fission180_bookcomp_"), "move.FCStd")
    state["path"] = path
    doc = k.doc()
    doc.saveAs(path)
    App.closeDocument(doc.Name)


def e_reopen():
    App.openDocument(state["path"])
    h.fit()


def e_reopened():
    k.doc().recompute()
    k.box_is("Motor:2 turned", k.part("Motor:2"), [-10, -63, 0, 0, -53, 6])
    k.box_is("Motor:3 on it", k.part("Motor:3"), [-10, -63, 0, 0, -53, 6])
    h.check("the block in Frame", len(k.bodies_of("Frame")) == 1)
    k.no_empty_invalid_bodies("no invalid body after reopening")


h.run(
    "book_components_move",
    [
        new_design,
        setup_done,
        a_select,
        copy_key,
        paste_key,
        a_pasted,
        ok,
        a_turned,
        b_select,
        copy_key,
        paste_key,
        b_pasted,
        escape,
        b_kept,
        undo,
        c_no_paste,
        undo,
        c_not_turned,
        redo,
        redo,
        c_redone,
        d_menu,
        d_moved,
        undo,
        d_undone,
        redo,
        d_redone,
        e_save,
        e_reopen,
        e_reopened,
    ],
    paced_by="state",
)
