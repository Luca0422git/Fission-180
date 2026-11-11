# SPDX-License-Identifier: LGPL-2.1-or-later
"""Parts inside a subassembly: picked in the browser and in the window (book parity report,
bug 15 and "clicking a part of a subassembly selects the whole subassembly"; the Tesla
Turbine's Stator Subassembly, the Gear Train's Compound Gear). Only real input for what is
tested.

Setup (through the modules): the subassembly "Stator" holding "Housing" (a 40 x 30 x 10
block) and "Wall" (a 20 x 30 x 10 block from x 60); "Bolt" (a cylinder, radius 4, height
25, at x 20, y 60) at the root.

  A  (bug 15) ASSEMBLE > As-built Joint: click the browser row of Housing (inside Stator),
     then the row of Wall: both nested components are taken; Cancel.
  B  ASSEMBLE > Rigid Group: click the rows of Housing and Bolt: both are members; OK:
     one rigid group of the two.
  C  M (Move/Copy), Move Object Components, click the Wall in the window: the Wall is
     picked (the part that was clicked), not the whole Stator; X Distance 5, OK: only the
     Wall moved. Undo.
  D  The same click with the Stator's row selected in the browser first: M opens on the
     Stator (the browser is how a whole subassembly is picked); Esc.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import book_components_steps as k
from Fission180Tests.gui import component2_steps as c
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import joints_steps as j
from Fission180Tests.gui import timeline_input as t

V = App.Vector
state = {}


def new_design():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("BookComponentsNested")
    stator = k.new_component("Stator")
    housing = k.new_component("Housing", parent=stator)
    k.add_box(housing, (0, 0, 40, 30), 10)
    wall = k.new_component("Wall", parent=stator)
    k.add_box(wall, (60, 0, 80, 30), 10)
    bolt = k.new_component("Bolt")
    k.add_cylinder(bolt, (20, 60), 4, 25)
    k.settle_design()


def setup_done():
    h.check("four components", len(k.labels()) == 4, k.labels())
    rows = t.children("Stator")
    h.check("Housing and Wall are rows inside Stator", "Housing" in rows and "Wall" in rows, rows)


# -- A: As-built Joint, nested rows -------------------------------------------------------------
def a_command():
    h.fit()
    j.menu("As-built Joint")


a_command.done = lambda: j.panel() is not None
a_command.done_what = "the As-built Joint dialog is open"


def a_row_housing():
    p = j.panel()
    h.check("As-Built Joint open", p is not None and p.title == "As-Built Joint", p and p.title)
    t.click_row("Housing")


def a_row_wall():
    p = j.panel()
    h.check(
        "the nested Housing is taken from its browser row (bug 15)",
        p is not None and p.parts == [k.part("Housing")],
        p and p.parts,
    )
    t.click_row("Wall")


def a_two():
    p = j.panel()
    h.check(
        "both nested components taken",
        p is not None and p.parts == [k.part("Housing"), k.part("Wall")],
        p and p.parts,
    )
    h.shot("A-asbuilt")


def a_cancel():
    j.cancel()


a_cancel.done = lambda: j.panel() is None
a_cancel.done_what = "the dialog closed"


# -- B: Rigid Group -------------------------------------------------------------------------------
def b_command():
    h.fit()
    j.menu("Rigid Group")


b_command.done = lambda: j.panel() is not None
b_command.done_what = "the Rigid Group dialog is open"


def b_row_housing():
    t.click_row("Housing")


def b_row_bolt():
    p = j.panel()
    h.check(
        "Housing is a member", p is not None and p.members == [k.part("Housing")], p and p.members
    )
    t.click_row("Bolt")


def b_members():
    p = j.panel()
    h.check(
        "Housing and Bolt are members",
        p is not None and p.members == [k.part("Housing"), k.part("Bolt")],
        p and p.members,
    )


def b_ok():
    j.ok()


b_ok.done = lambda: j.panel() is None
b_ok.done_what = "the dialog closed"


def b_done():
    groups = j.joints_module().rigid_groups(k.doc())
    h.check("one rigid group", len(groups) == 1, groups)


# -- C: Move, a click on a part of the subassembly ------------------------------------------------
def c_press_m():
    h.click_empty()
    h.fit()
    h.press("m")


c_press_m.done = lambda: c.panel() is not None
c_press_m.done_what = "Move/Copy is open"


def c_switch():
    p = c.panel()
    if h.check("Move/Copy open", p is not None, p):
        c.choose(p.move_object, "Components", closes=True)


c_switch.done = lambda: c.component_panel() is not None
c_switch.done_what = "the components dialog took over"


def c_click_wall():
    h.click(V(70, 15, 10))  # the Wall's top


def c_picked():
    p = c.component_panel()
    if not h.check("dialog open", p is not None):
        return
    h.check(
        "the Wall is picked, not the Stator",
        p.options.get("components") == [k.part("Wall")],
        [x.Label for x in p.options.get("components") or []],
    )
    c.type_value(p, "dx", "5")


def c_ok():
    h.task_button("OK")


c_ok.done = lambda: c.component_panel() is None
c_ok.done_what = "the dialog closed"


def c_moved():
    k.box_is("only the Wall moved 5 mm", k.part("Wall"), [65, 0, 0, 85, 30, 10])
    k.box_is("the Housing stayed", k.part("Housing"), [0, 0, 0, 40, 30, 10])
    h.check(
        "the Stator itself did not move",
        k.part("Stator").Placement.isIdentity(),
        k.part("Stator").Placement,
    )


def c_undo():
    t.undo()


def c_undone():
    k.box_is("Undo: the Wall is back", k.part("Wall"), [60, 0, 0, 80, 30, 10])


# -- D: the whole subassembly from the browser ---------------------------------------------------
def d_select_row():
    h.click_empty()
    t.click_row("Stator")


def d_press_m():
    h.press("m")


d_press_m.done = lambda: c.component_panel() is not None
d_press_m.done_what = "the components dialog is open"


def d_on_stator():
    p = c.component_panel()
    if h.check("dialog open", p is not None):
        h.check(
            "opened on the Stator",
            p.options.get("components") == [k.part("Stator")],
            [x.Label for x in p.options.get("components") or []],
        )


def d_escape():
    h.press(QtCore.Qt.Key_Escape)


d_escape.done = lambda: c.component_panel() is None
d_escape.done_what = "the dialog closed"


def d_nothing():
    h.check("Esc moved nothing", k.part("Stator").Placement.isIdentity())
    from fission180 import taskui

    h.check("no dialog is open after Esc", taskui.current() is None, taskui.current())


h.run(
    "book_components_nested",
    [
        new_design,
        setup_done,
        a_command,
        a_row_housing,
        a_row_wall,
        a_two,
        a_cancel,
        b_command,
        b_row_housing,
        b_row_bolt,
        b_members,
        b_ok,
        b_done,
        c_press_m,
        c_switch,
        c_click_wall,
        c_picked,
        c_ok,
        c_moved,
        c_undo,
        c_undone,
        d_select_row,
        d_press_m,
        d_on_stator,
        d_escape,
        d_nothing,
    ],
    paced_by="state",
)
