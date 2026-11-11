# SPDX-License-Identifier: LGPL-2.1-or-later
"""New Component: From Bodies only when bodies are selected, the first component grounded,
a new component inside the active one (book parity report, bug 9, friction pattern 9; the
Fire Piston's "Piston", the Drone's "Drone Frame", the Gear Train's second gear). Only
real input for what is tested.

Setup (through the modules): a 40 x 30 x 10 block at the root (Body1, Extrude 1).
Fusion's preference "First component Ground to Parent" is on (its default; the harness
switches it off for the scenarios written before it).

  A  (bug 9) The block's Extrude step clicked in the timeline (it stays selected),
     ASSEMBLE > New Component: From Bodies is NOT ticked; name "Piston", OK: an empty
     component, active; the block is still at the root. Piston is the first component:
     it is grounded (Fusion), its menu offers Unground From Parent.
  B  The design's ring, a face of the block clicked (selected), New Component: From
     Bodies is not ticked; Cancel.
  C  The block's browser row clicked (the body selected), New Component: From Bodies is
     ticked by itself and the dialog says which body will move; Cancel: nothing moved.
  D  Piston's ring, New Component: Parent reads Piston (a new component goes inside the
     active one, as in Fusion); name "Rod", OK: Rod is inside Piston and grounded (the
     first of its level). The design's ring, New Component "Cap": at the root, not
     grounded (Piston was first).
  E  Undo: Cap is gone. Undo: Rod and its ground are gone in one step. Redo: back.
  F  Unground From Parent on Piston (its menu), then Ground to Parent again.
  G  Save, close, reopen: Piston grounded, Rod inside it.
"""

import os
import tempfile

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import book_components_steps as k
from Fission180Tests.gui import component_steps as cs
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import joints_steps as j
from Fission180Tests.gui import timeline_input as t

V = App.Vector
state = {}


def grounded(label):
    return j.joints_module().is_grounded(k.part(label))


def panel():
    return cs.new_component_panel()


def new_design():
    from fission180 import prefs_core

    App.ParamGet(prefs_core.PREFS).SetBool("FirstComponentGrounded", True)  # Fusion's default
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("BookComponentsNew")
    state["body"] = k.add_box(None, (0, 0, 40, 30), 10).Name
    k.settle_design()


def body():
    return k.doc().getObject(state["body"])


def open_dialog():
    j.menu("New Component")


open_dialog.done = lambda: panel() is not None
open_dialog.done_what = "the New Component dialog is open"


def closed():
    return panel() is None


# -- A ---------------------------------------------------------------------------------------------
def a_select_step():
    title = t.titles()[-1]
    state["step"] = title
    t.click(title)


def a_selected():
    names = [s.Object.Name for s in Gui.Selection.getSelectionEx()]
    h.check("the step is selected", len(names) == 1, names)


def a_dialog():
    p = panel()
    if not h.check("dialog open", p is not None):
        return
    h.settle()
    h.check(
        "From Bodies is not ticked by a step selected in the timeline (bug 9)",
        not p.from_bodies.isChecked(),
        p.bodies_label.text(),
    )
    cs.type_name("Piston")


def a_ok():
    h.task_button("OK")


a_ok.done = closed
a_ok.done_what = "the dialog closed"


def a_made():
    piston = k.part("Piston")
    if not h.check("Piston exists", piston is not None, k.labels()):
        return
    h.check(
        "Piston is empty",
        not k.all_bodies_of("Piston"),
        [b.Label for b in k.all_bodies_of("Piston")],
    )
    h.check(
        "the block is still at the root", k.container_label(body()) == "", k.container_label(body())
    )
    h.check("Piston is active", k.active_label() == "Piston", k.active_label())
    h.check("the first component is grounded (Fusion: Ground to Parent)", grounded("Piston"))
    entries = [e[0] for e in t.row_menu_entries("Piston")]
    h.check(
        "its menu offers Unground From Parent",
        "Unground From Parent" in entries and "Ground to Parent" not in entries,
        entries,
    )
    h.shot("A-piston")


# -- B ---------------------------------------------------------------------------------------------
def b_root():
    cs.click_radio("BookComponentsNew")


b_root.done = lambda: k.active_label() == ""
b_root.done_what = "the root is active"


def b_face():
    h.fit()
    h.click(V(20, 15, 10))


def b_dialog():
    p = panel()
    if h.check("dialog open", p is not None):
        h.settle()
        h.check(
            "From Bodies is not ticked by a selected face",
            not p.from_bodies.isChecked(),
            p.bodies_label.text(),
        )
        h.check(
            "Parent reads the design (the root is active)",
            "root" in p.parent_box.currentText(),
            p.parent_box.currentText(),
        )


def cancel():
    h.task_button("Cancel")


cancel.done = closed
cancel.done_what = "the dialog closed"


def b_nothing():
    h.check("Cancel made no component", k.labels() == ["Piston"], k.labels())


# -- C ---------------------------------------------------------------------------------------------
def c_row():
    h.click_empty()
    t.click_row(body().Label)


def c_dialog():
    p = panel()
    if h.check("dialog open", p is not None):
        h.settle()
        h.check("From Bodies ticked: a body was selected as a body", p.from_bodies.isChecked())
        text = p.bodies_label.text()
        h.check(
            "the dialog says which body will move",
            body().Label in text and "will move into the new component" in text,
            text,
        )
        h.shot("C-from-bodies")


def c_nothing():
    h.check("Cancel moved nothing", k.container_label(body()) == "", k.container_label(body()))
    h.check("...and made no component", k.labels() == ["Piston"], k.labels())


# -- D ---------------------------------------------------------------------------------------------
def d_activate():
    h.click_empty()
    cs.click_radio("Piston")


d_activate.done = lambda: k.active_label() == "Piston"
d_activate.done_what = "Piston is active"


def d_dialog():
    p = panel()
    if h.check("dialog open", p is not None):
        h.check(
            "Parent reads Piston (the active component)",
            p.parent_box.currentText() == "Piston",
            p.parent_box.currentText(),
        )
        cs.type_name("Rod")


def d_made():
    rod = k.part("Rod")
    if h.check("Rod exists", rod is not None, k.labels()):
        h.check("Rod is inside Piston", k.container_label(rod) == "Piston", k.container_label(rod))
        h.check("Rod is the first of its level: grounded", grounded("Rod"))


def d_cap_dialog():
    p = panel()
    if h.check("dialog open", p is not None):
        h.check(
            "Parent reads the design",
            "root" in p.parent_box.currentText(),
            p.parent_box.currentText(),
        )
        cs.type_name("Cap")


def d_cap_made():
    cap = k.part("Cap")
    if h.check("Cap exists", cap is not None, k.labels()):
        h.check("Cap is at the root", k.container_label(cap) == "", k.container_label(cap))
        h.check("Cap is not grounded (Piston was the first)", not grounded("Cap"))
        h.check("Piston is still grounded", grounded("Piston"))


# -- E ---------------------------------------------------------------------------------------------
def undo():
    t.undo()


def e_no_cap():
    h.check("Undo: Cap is gone", k.labels() == ["Piston", "Rod"], k.labels())


def e_no_rod():
    h.check("Undo: Rod is gone", k.labels() == ["Piston"], k.labels())
    grounds = j.joints_module().grounds(k.doc())
    h.check("...with its ground, in one step", len(grounds) == 1, [g.Label for g in grounds])
    h.check("Piston is still grounded", grounded("Piston"))


def redo():
    t.redo()


def e_back():
    h.check("Redo twice: Rod and Cap are back", k.labels() == ["Piston", "Rod", "Cap"], k.labels())
    h.check("Rod grounded again", grounded("Rod"))


# -- F ---------------------------------------------------------------------------------------------
def f_unground():
    t.row_menu("Piston", "Unground From Parent")


f_unground.done = lambda: not grounded("Piston")
f_unground.done_what = "Piston is free"


def f_ground():
    entries = [e[0] for e in t.row_menu_entries("Piston")]
    h.check("the menu offers Ground to Parent", "Ground to Parent" in entries, entries)
    t.row_menu("Piston", "Ground to Parent")


f_ground.done = lambda: grounded("Piston")
f_ground.done_what = "Piston is grounded again"


# -- G ---------------------------------------------------------------------------------------------
def g_save():
    path = os.path.join(tempfile.mkdtemp(prefix="fission180_bookcomp_"), "new.FCStd")
    state["path"] = path
    doc = k.doc()
    doc.saveAs(path)
    App.closeDocument(doc.Name)


def g_reopen():
    App.openDocument(state["path"])
    h.fit()


def g_reopened():
    k.doc().recompute()
    h.check("three components", k.labels() == ["Piston", "Rod", "Cap"], k.labels())
    h.check("Piston grounded", grounded("Piston"))
    h.check("Rod inside Piston", k.container_label(k.part("Rod")) == "Piston")
    h.check("the block at the root", len(k.bodies_of("")) == 1)


h.run(
    "book_components_new",
    [
        new_design,
        a_select_step,
        a_selected,
        open_dialog,
        a_dialog,
        a_ok,
        a_made,
        b_root,
        b_face,
        open_dialog,
        b_dialog,
        cancel,
        b_nothing,
        c_row,
        open_dialog,
        c_dialog,
        cancel,
        c_nothing,
        d_activate,
        open_dialog,
        d_dialog,
        a_ok,
        d_made,
        b_root,
        open_dialog,
        d_cap_dialog,
        a_ok,
        d_cap_made,
        undo,
        e_no_cap,
        undo,
        e_no_rod,
        redo,
        redo,
        e_back,
        f_unground,
        f_ground,
        g_save,
        g_reopen,
        g_reopened,
    ],
    paced_by="state",
)
