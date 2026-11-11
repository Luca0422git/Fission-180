# SPDX-License-Identifier: LGPL-2.1-or-later
"""The appearance and material commands in a design with nothing in it yet: each opens, says
what it waits for or why it cannot do anything, and closes again without an error. Only
real input.

  A  Appearance: In This Design shows the default look (on nothing); a look dropped on the
     empty view is refused with the reason; Esc.
  B  Physical Material: the library is there, no body to list; a material picked; Cancel.
  C  Texture Map Controls: OK without a body says what is missing; Cancel.
  D  INSPECT > Properties: the dialog says nothing has a solid yet; Esc closes it.
  E  Manage Materials opens and closes.
  F  nothing selected: no read-out.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import looks_steps as k
from Fission180Tests.gui import widget_input as w

state = {}


def new_design():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("LooksEmpty")
    h.fit()
    state["objects"] = len(App.ActiveDocument.Objects)


def unchanged(where):
    count = len(App.ActiveDocument.Objects)
    h.check("%s: the design is as it was" % where, count == state["objects"], count)


# -- A ---------------------------------------------------------------------------------------------
def a_open():
    s.menu("MODIFY", "Appearance")


def a_default():
    p = k.panel()
    if not h.check("Appearance opens in an empty design", p is not None):
        return
    h.check("the default look is listed", k.design_labels() == ["Steel, satin (default)"])
    item = k.design_item("Steel, satin (default)")
    h.check("on nothing", item is not None and "not on anything" in item.toolTip(), item.toolTip())
    k.drop_look("Oak", h._empty_spot(h.gl_widget()))


def a_refused():
    p = k.panel()
    h.check("a drop on nothing says so", "nothing was there" in p.message.text(), p.message.text())
    h.press(QtCore.Qt.Key_Escape)


def a_closed():
    h.check("Esc closes Appearance", k.panel() is None)
    unchanged("Appearance")


# -- B ---------------------------------------------------------------------------------------------
def b_open():
    s.menu("MODIFY", "Physical Material")


def b_pick():
    p = s.panel()
    if not h.check("Physical Material opens", p is not None and p.title == "Physical Material"):
        return
    h.check("no body to list", p.design.count() == 0 and p.masses.text() == "", p.masses.text())
    item = p.item_for("Brass")
    if h.check("the library is there", item is not None):
        k.click_item(p.library, item)
        h.check("the dialog waits for a body", "Click bodies" in p.info.text(), p.info.text())
    h.task_button("Cancel")


def b_closed():
    h.check("Cancel closes it", s.panel() is None)
    unchanged("Physical Material")


# -- C ---------------------------------------------------------------------------------------------
def c_open():
    s.menu("MODIFY", "Texture Map Controls")


def c_ok():
    p = s.panel()
    if h.check("Texture Map Controls opens", p is not None and p.title == "Texture Map Controls"):
        h.check("it waits for a body", "Click the body" in p.info.text(), p.info.text())
        h.task_button("OK")


def c_refused():
    p = s.panel()
    if h.check("OK without a body keeps the dialog open", p is not None):
        h.check("and says what is missing", "Click the body" in p.message.text(), p.message.text())
        h.task_button("Cancel")


def c_closed():
    h.check("Cancel closes it", s.panel() is None)
    unchanged("Texture Map Controls")


# -- D ---------------------------------------------------------------------------------------------
def props():
    from fission180 import properties_ui

    return properties_ui.dialog()


def d_open():
    s.menu("INSPECT", "Properties")


def d_nothing():
    d = props()
    if not h.check("Properties opens", d is not None):
        return
    h.check("0 bodies", "0 bodies" in d.title.text(), d.title.text())
    h.check("it says why", "has a solid yet" in d.message.text(), d.message.text())
    h.check("no mass", d.value("Physical", "Mass") == "-", d.value("Physical", "Mass"))
    w.key(d, QtCore.Qt.Key_Escape)


def d_closed():
    h.check("Esc closes Properties", props() is None)


# -- E ---------------------------------------------------------------------------------------------
def e_open():
    s.menu("MODIFY", "Manage Materials")


def e_browser():
    from fission180 import materials_ui

    d = materials_ui.MaterialBrowser.last
    if h.check("the Material Browser opens", d is not None and d.isVisible()):
        names = [i.text(0) for i in d.physical.items()]
        h.check("it lists Brass and Gold", "Brass" in names and "Gold" in names, names[:6])
        looks = [i.text(0) for i in d.appearance.items()]
        h.check("and the looks (Oak, Leather)", "Oak" in looks and "Leather, brown" in looks)
        tree = d.physical.tree
        item = d.physical.items("brass")[0]
        tree.scrollToItem(item)
        w.click(tree.viewport(), tree.visualItemRect(item).center())
        density = d.physical.detail_labels["Density"].text()
        h.check("Brass shows its density", density.startswith("8.5"), density)
        w.click(d.findChild(type(d.physical.assign), "Fission180MaterialClose"))


def e_closed():
    from fission180 import materials_ui

    h.check("Close closes it", not materials_ui.MaterialBrowser.last.isVisible())


# -- F ---------------------------------------------------------------------------------------------
def f_readout():
    from fission180 import properties_readout_ui

    h.click_empty()
    h.check("nothing selected: no read-out", properties_readout_ui.rows() == [])
    unchanged("the end")


h.run(
    "book_looks_empty",
    [
        new_design,
        a_open,
        a_default,
        a_refused,
        a_closed,
        b_open,
        b_pick,
        b_closed,
        c_open,
        c_ok,
        c_refused,
        c_closed,
        d_open,
        d_nothing,
        d_closed,
        e_open,
        e_browser,
        e_closed,
        f_readout,
    ],
    paced_by="state",
)
