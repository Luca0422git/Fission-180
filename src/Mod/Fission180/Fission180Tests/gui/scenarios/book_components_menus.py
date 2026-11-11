# SPDX-License-Identifier: LGPL-2.1-or-later
"""The component menu, Isolate while something is isolated, the design's assembly icon,
rows dragged onto components and the empty body Move to Component left behind (book parity
report: Pizza Cutter 2002-2010 and 2087, Gear Train 2368-2374, bugs 5 - 9's workaround).
Only real input for what is tested.

Setup (through the modules): "Housing" (a 40 x 30 x 10 block), "Wall" (a block from x 60),
the empty component "Tube"; two blocks at the root: Body1 (x 0..20, y 50..70) and Body2
(x 30..50, y 50..70).

  A  The design's row shows the assembly icon (it holds components). Housing's menu has
     Move/Copy and Create Drawing; Move/Copy opens Move on Housing; Esc.
  B  Housing's menu > Isolate: the Wall and the root blocks hide. Wall's menu now offers
     Isolate (it only offered Exit Isolate): Isolate there shows the Wall and hides the
     Housing. Wall's menu > Exit Isolate: everything is back.
  C  Tube's ring, Create Sketch, Cancel: no body and no open undo step are left (wave 7,
     components-2: the body made to show the planes stayed). A body nothing was put in is
     then set up in Tube. The design's ring. Body1's row dragged onto Tube: it lands in
     Tube, and the empty body is gone (it would have taken the next sketch). Body2's row dragged onto
     Housing right after (the tree was rebuilt in between): it lands in Housing, the row
     under the pointer.
  D  Undo twice: both blocks are back at the root. Redo twice.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import book_components_steps as k
from Fission180Tests.gui import component2_steps as c
from Fission180Tests.gui import component_steps as cs
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import timeline_input as t

V = App.Vector
state = {}


def new_design():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("BookComponentsMenus")
    housing = k.new_component("Housing")
    k.add_box(housing, (0, 0, 40, 30), 10)
    wall = k.new_component("Wall")
    k.add_box(wall, (60, 0, 80, 30), 10)
    k.new_component("Tube")
    state["b1"] = k.add_box(None, (0, 50, 20, 70), 5).Name
    state["b2"] = k.add_box(None, (30, 50, 50, 70), 5).Name
    k.settle_design()


def obj(key):
    return k.doc().getObject(state[key])


def shown(thing):
    return bool(thing.ViewObject.Visibility)


# -- A ---------------------------------------------------------------------------------------------
def a_menu():
    node = cs.node_of("BookComponentsMenus")
    h.check(
        "the design's row shows the assembly icon",
        node is not None and node.get("icon") == "assembly",
        node and node.get("icon"),
    )
    entries = [e[0] for e in t.row_menu_entries("Housing")]
    h.check("Housing's menu has Move/Copy", "Move/Copy" in entries, entries)
    h.check("...and Create Drawing", "Create Drawing" in entries, entries)
    h.check("...and Ground to Parent", "Ground to Parent" in entries, entries)
    state["labels"] = (obj("b1").Label, obj("b2").Label)


def a_move():
    t.row_menu("Housing", "Move/Copy")


a_move.done = lambda: c.component_panel() is not None
a_move.done_what = "Move/Copy is open on components"


def a_on_housing():
    p = c.component_panel()
    if h.check("dialog open", p is not None):
        h.check(
            "on Housing",
            p.options.get("components") == [k.part("Housing")],
            [x.Label for x in p.options.get("components") or []],
        )


def a_escape():
    h.press(QtCore.Qt.Key_Escape)


a_escape.done = lambda: c.component_panel() is None
a_escape.done_what = "the dialog closed"


# -- B ---------------------------------------------------------------------------------------------
def b_isolate():
    h.click_empty()
    t.row_menu("Housing", "Isolate")


def b_isolated():
    h.check("the Wall is hidden", not shown(k.part("Wall")))
    h.check("the root blocks are hidden", not shown(obj("b1")) and not shown(obj("b2")))
    h.check("the Housing shows", shown(k.part("Housing")))
    entries = [e[0] for e in t.row_menu_entries("Housing")]
    h.check(
        "Housing's menu offers Exit Isolate",
        "Exit Isolate" in entries and "Isolate" not in entries,
        entries,
    )
    entries = [e[0] for e in t.row_menu_entries("Wall")]
    h.check(
        "Wall's menu offers Isolate while Housing is isolated",
        "Isolate" in entries and "Exit Isolate" not in entries,
        entries,
    )


def b_isolate_wall():
    t.row_menu("Wall", "Isolate")


def b_wall_isolated():
    h.check("the Wall shows", shown(k.part("Wall")))
    h.check("the Housing is hidden", not shown(k.part("Housing")))
    h.check("the root blocks stay hidden", not shown(obj("b1")) and not shown(obj("b2")))


def b_exit():
    t.row_menu("Wall", "Exit Isolate")


def b_all_back():
    h.check(
        "everything is back",
        shown(k.part("Wall"))
        and shown(k.part("Housing"))
        and shown(obj("b1"))
        and shown(obj("b2")),
    )


# -- C ---------------------------------------------------------------------------------------------
def c_activate():
    cs.click_radio("Tube")


c_activate.done = lambda: k.active_label() == "Tube"
c_activate.done_what = "Tube is active"


def c_sketch():
    h.fit()
    h.ribbon("Create Sketch")


def c_cancel():
    h.task_button("Cancel")


def c_empty_body():
    from fission180 import components

    # (wave 7, components-2) Create Sketch made a body in Tube to show its planes; Cancel
    # takes it away again and no undo step stays open (FreeCAD's "Add a Body" stayed
    # pending with the empty body: the harness's undo check found it here)
    found = k.all_bodies_of("Tube")
    h.check("the cancelled Create Sketch left no body in Tube", not found, [b.Label for b in found])
    doc = k.doc()
    h.check(
        "no undo step is left open",
        App.getActiveTransaction() is None and not doc.HasPendingTransaction,
        App.getActiveTransaction(),
    )
    # a body nothing was put in can still come about (its only sketch deleted again): one
    # is set up here through the module, for the drag below
    doc.openTransaction("New Body")
    empty = components.new_body_in(doc, k.part("Tube"))
    doc.commitTransaction()
    h.check("Tube holds one body nothing was put in", components.is_unused(empty))
    cs.click_radio("BookComponentsMenus")


c_empty_body.done = lambda: k.active_label() == ""
c_empty_body.done_what = "the root is active"


def c_drag_one():
    cs.drag_row(state["labels"][0], "Tube")


c_drag_one.done = lambda: k.container_label(obj("b1")) == "Tube"
c_drag_one.done_what = "Body1 is in Tube"


def c_drag_two():
    found = k.all_bodies_of("Tube")
    h.check(
        "Tube holds the block only: the empty body is gone",
        found == [obj("b1")],
        [b.Label for b in found],
    )
    k.box_is("the block stands where it stood", obj("b1"), [0, 50, 0, 20, 70, 5])
    cs.drag_row(state["labels"][1], "Housing")


c_drag_two.done = lambda: k.container_label(obj("b2")) != ""
c_drag_two.done_what = "Body2 left the root"


def c_landed():
    h.check(
        "the second drag landed on the row under the pointer: Housing",
        k.container_label(obj("b2")) == "Housing",
        k.container_label(obj("b2")),
    )
    k.box_is("in place", obj("b2"), [30, 50, 0, 50, 70, 5])
    k.no_empty_invalid_bodies()


# -- D ---------------------------------------------------------------------------------------------
def undo():
    t.undo()


def redo():
    t.redo()


def d_undone():
    h.check(
        "Undo twice: both blocks at the root",
        k.container_label(obj("b1")) == "" and k.container_label(obj("b2")) == "",
        (k.container_label(obj("b1")), k.container_label(obj("b2"))),
    )


def d_redone():
    h.check(
        "Redo twice: in Tube and in Housing",
        k.container_label(obj("b1")) == "Tube" and k.container_label(obj("b2")) == "Housing",
        (k.container_label(obj("b1")), k.container_label(obj("b2"))),
    )
    k.no_empty_invalid_bodies("no invalid body after redo")


h.run(
    "book_components_menus",
    [
        new_design,
        a_menu,
        a_move,
        a_on_housing,
        a_escape,
        b_isolate,
        b_isolated,
        b_isolate_wall,
        b_wall_isolated,
        b_exit,
        b_all_back,
        c_activate,
        c_sketch,
        c_cancel,
        c_empty_body,
        c_drag_one,
        c_drag_two,
        c_landed,
        undo,
        undo,
        d_undone,
        redo,
        redo,
        d_redone,
    ],
    paced_by="state",
)
