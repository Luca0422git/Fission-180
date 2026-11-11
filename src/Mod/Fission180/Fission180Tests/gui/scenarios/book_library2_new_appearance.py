# SPDX-License-Identifier: LGPL-2.1-or-later
"""Manage Materials > New Appearance: the colour is picked on a colour wheel (wave 7,
library-2, item 10). Until now the colour of a new appearance had to be typed as a code
("#RRGGBB"); Fusion's appearance editor has a colour picker.

A  MODIFY > Manage Materials, the Appearance tab, New Appearance: a colour wheel, a
   brightness slider and a swatch are there; nothing has to be typed for the colour.
B  The name "Sea Green" typed, a green clicked on the wheel: the swatch and the Colour box
   show that green. Create: "Sea Green" is in My Appearances, with the colour picked.
C  The body clicked, Assign to Selection: the body is that green.
D  New Appearance again: a code typed (#c04020) still works, and the wheel follows it.
"""

import colorsys

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import misc_steps as m
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import widget_input as w

V = App.Vector
S = {}
HUE, SAT = 0.40, 0.75  # a green


def browser():
    from fission180 import materials_ui

    d = materials_ui.MaterialBrowser.last
    try:
        return d if d is not None and d.isVisible() else None
    except RuntimeError:
        return None


def tab():
    d = browser()
    return d.appearance if d is not None else None


def leaves(under):
    return [i.text(0) for i in tab().items(under=under)]


def press(name):
    button = m.find_child(browser(), name)
    if h.check("button %s" % name, button is not None and button.isEnabled()):
        w.click(button)
        m.process()


def body():
    return App.ActiveDocument.getObject(S["body"])


def rgb_of(code):
    c = QtGui.QColor(code)
    return (c.redF(), c.greenF(), c.blueF())


def near(a, b, tol=0.06):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def setup():
    from fission180 import appearance, commands, extrude, sketch_ui

    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("NewAppearance")
    b = commands.ensure_body()
    planes = sketch_ui.origin_planes(b)
    sk = sketch_ui.create_sketch(b, (planes["XY_Plane"], ""))
    h.draw_rectangle(sk, 0, 0, 40, 30)
    extrude.make(b, sk, {"distance": 10.0})
    App.ActiveDocument.recompute()
    S["body"] = b.Name
    h.fit()
    appearance.save_my_looks([])  # (a profile left from an earlier run)
    si.menu_item("MODIFY", "Manage Materials")


setup.done = lambda: browser() is not None
setup.done_what = "the Material Browser is open"


# -- A --------------------------------------------------------------------------------------------
def a_tab():
    d = browser()
    bar = d.tabs.tabBar()
    w.click(bar, bar.tabRect(1).center())
    m.process()


def a_new():
    h.check("the Appearance tab", browser().tabs.currentIndex() == 1)
    press("Fission180MaterialNew_appearance")


def a_wheel():
    t = tab()
    h.check("New Appearance is open", t.new_box.isVisible())
    h.check("a colour wheel", t.wheel is not None and t.wheel.isVisible())
    h.check(
        "a brightness slider and a swatch", t.brightness.isVisible() and t.new_swatch.isVisible()
    )
    h.check("nothing typed for the colour", t.new_value.text() == "", t.new_value.text())
    w.click(t.new_name)
    w.type_text(t.new_name, "Sea Green")


# -- B --------------------------------------------------------------------------------------------
def b_pick():
    t = tab()
    w.click(t.wheel, t.wheel.point_for(HUE, SAT))
    m.process()


def b_shown():
    t = tab()
    want = colorsys.hsv_to_rgb(HUE, SAT, t.brightness.value() / 100.0)
    code = t.new_value.text()
    h.check("the Colour box shows a code now", code.startswith("#") and len(code) == 7, code)
    h.check("the green that was clicked", near(rgb_of(code), want), (code, want))
    h.check("the swatch shows it", code in t.new_swatch.styleSheet(), t.new_swatch.styleSheet())
    S["code"] = code
    press("Fission180MaterialCreate_appearance")


def b_made():
    from fission180 import appearance

    h.check(
        "Sea Green is in My Appearances",
        leaves("My Appearances") == ["Sea Green"],
        leaves("My Appearances"),
    )
    mine = [look for look in appearance.my_looks() if look["label"] == "Sea Green"]
    h.check(
        "with the colour picked", mine and near(mine[0]["color"], rgb_of(S["code"]), 0.01), mine
    )
    h.click(V(20, 15, 10))
    m.process()
    press("Fission180MaterialAssign_appearance")


# -- C --------------------------------------------------------------------------------------------
def c_assigned():
    from fission180 import appearance

    look = appearance.get(body()).get("body") or {}
    h.check("the body has the look", look.get("label") == "Sea Green", look)
    drawn = [tuple(mat.DiffuseColor[:3]) for mat in body().Tip.ViewObject.ShapeAppearance]
    h.check(
        "and is drawn in that green",
        drawn and all(near(c, rgb_of(S["code"]), 0.01) for c in drawn),
        drawn,
    )
    press("Fission180MaterialNew_appearance")


# -- D --------------------------------------------------------------------------------------------
def d_code():
    t = tab()
    w.click(t.new_name)
    w.type_text(t.new_name, "Brick")
    w.click(t.new_value)
    w.key(t.new_value, QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
    w.type_text(t.new_value, "#c04020")


def d_follows():
    t = tab()
    h.check(
        "the swatch follows the typed code",
        "#c04020" in t.new_swatch.styleSheet(),
        t.new_swatch.styleSheet(),
    )
    hue = QtGui.QColor("#c04020").hueF()
    h.check("and the wheel", abs(t.wheel.hue - hue) < 0.01, (t.wheel.hue, hue))
    press("Fission180MaterialCreate_appearance")


def d_made():
    from fission180 import appearance

    h.check(
        "Brick is made too",
        sorted(leaves("My Appearances")) == ["Brick", "Sea Green"],
        leaves("My Appearances"),
    )
    mine = [look for look in appearance.my_looks() if look["label"] == "Brick"]
    h.check("in the typed colour", mine and near(mine[0]["color"], rgb_of("#c04020"), 0.01), mine)
    appearance.save_my_looks([])
    browser().close()


h.run(
    "book_library2_new_appearance",
    [setup, a_tab, a_new, a_wheel, b_pick, b_shown, b_made, c_assigned, d_code, d_follows, d_made],
    paced_by="state",
)
