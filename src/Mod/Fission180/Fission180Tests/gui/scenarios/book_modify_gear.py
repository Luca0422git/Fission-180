# SPDX-License-Identifier: LGPL-2.1-or-later
"""The book's Gear Train (project 15), bugs 19 and 20 of the book parity report. Only real
input.

  A  UTILITIES > Scripts and Add-Ins lists "SpurGear" (it was empty); running it opens the
     Gear tool. Plane XY, centre on the origin; module 1.5, 20 teeth, 8 thick, hole 4,
     Operation New Component; OK: the component is named "Spur Gear (20 teeth)".
  B  Gear again, away from the first: the dialog starts with the last gear's values
     (Fusion's sample remembers them). Root Fillet Radius 0.89 (fits 20 teeth), then
     Number of Teeth 100: the dialog says it does not fit and how much does; Operation New
     Component stays chosen; OK is refused, says so next to the pointer, and no second
     gear is kept by it.
  C  While that dialog is still open (the unfinished gear shows as "Gear 2" in the
     timeline): right-click Gear 2 > Edit Feature. The step does not vanish (bug 20): the
     dialog stays and says to finish it first.
  D  Root fillet 0.88 (the book's value: Fusion's SpurGear takes up to 0.4 x the tooth
     thickness on the base circle, 0.8857 mm for module 1.5, whatever the teeth), thickness
     4, OK: 100 teeth, 4 thick, a New Component named "Spur Gear (100 teeth)".
  E  Right-click Gear 2 > Edit Feature: its dialog opens with 100 teeth; Cancel leaves it;
     again, 80 teeth, OK: the gear and its component's name follow. Ctrl+Z.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import insert_steps as i
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import primitive_input as pi
from Fission180Tests.gui import timeline_input as t
from Fission180Tests.gui import widget_input as w

V = App.Vector
s = {}


def doc():
    return App.ActiveDocument


def panel():
    return pi.panel("GearPanel")


def near(a, c, tol=1e-6):
    return pi.near(a, c, tol)


def gears():
    return [o for o in doc().Objects if getattr(o, "Fission180Type", "") == "Gear"]


def read(feature):
    from fission180 import gear

    return gear.read(feature)[1]


def component_of(feature):
    from fission180 import components

    body = feature.getParentGeoFeatureGroup()
    return components.container_of(body) if body is not None else None


def scripts():
    from fission180 import scripts_ui

    d = scripts_ui.ScriptsDialog.last
    try:
        return d if d is not None and d.isVisible() else None
    except RuntimeError:
        return None


# -- A ------------------------------------------------------------------------------------------
def a_new():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("GearTrain")
    h.fit()
    i.ribbon_tab("UTILITIES")
    h.ribbon("Scripts and Add-Ins")


def a_listed():
    d = scripts()
    if not h.check("the Scripts and Add-Ins window", d is not None, h.popups()):
        return
    names = [d.list.topLevelItem(r).text(0) for r in range(d.list.topLevelItemCount())]
    h.check("SpurGear is listed", "SpurGear" in names, names)
    from fission180 import scripts_core

    item = d.item_for(scripts_core.SCRIPT, "SpurGear")
    if h.check("its row", item is not None):
        rect = d.list.visualItemRect(item)
        w.double_click(d.list.viewport(), QtCore.QPoint(rect.left() + 20, rect.center().y()))


def a_gear_open():
    d = scripts()
    if d is not None:
        d.close()
    h.check("SpurGear opened the Gear tool", panel() is not None, h.popups())


a_gear_open.ready = lambda: panel() is not None
a_gear_open.ready_what = "the Gear dialog is open"


def a_plane():
    pl.click_on_plane(V(15, -15, 0))


def a_centre():
    pl.click_on_plane(V(0, 0, 0))


def a_module():
    ui.type_into(panel().module.widget, "1.5")


def a_teeth():
    ui.type_into(panel().teeth.widget, "20")


def a_thick():
    ui.type_into(panel().thickness.widget, "8")


def a_hole():
    ui.type_into(panel().hole.widget, "4")


def a_operation():
    h.check("New Component", ui.choose(panel().operation, "New Component"))


def a_ok():
    h.task_button("OK")


def a_done():
    from fission180 import gear_core

    h.check("dialog closed", pi.no_dialog())
    if not h.check("one gear", len(gears()) == 1, gears()):
        return
    first = gears()[0]
    s["first"] = first.Name
    s["v1"] = first.Shape.Volume
    want = gear_core.area(dict(module=1.5, teeth=20, hole=4.0, fillet=read(first)["fillet"])) * 8.0
    h.check("20 teeth, m 1.5, 8 thick, hole 4", near(s["v1"], want, 1e-6), (s["v1"], want))
    part = component_of(first)
    h.check(
        "its component is named like Fusion's sample names it",
        part is not None and part.Label == "Spur Gear (20 teeth)",
        part and part.Label,
    )
    h.click_empty()
    i.ribbon_tab("SOLID")


def b_gear():
    pi.menu("Gear")


# -- B ------------------------------------------------------------------------------------------
def b_plane():
    pl.click_on_plane(V(15, -15, 0))


def b_centre():
    pl.click_on_plane(V(120, 0, 0))


def b_fillet():
    p = panel()
    if not h.check("the second gear is placed", p is not None and p.target is not None):
        return
    h.check("the dialog starts with the last gear's values", near(p.teeth.value(), 20.0))
    # (wave 7, replay-f) 0.88, the book's value, was typed here and refused for 100 teeth
    # ("at most 0.741 mm"). Fusion's SpurGear makes that gear (its limit is 0.8857 mm for
    # module 1.5, whatever the teeth: the fillets of neighbouring teeth cross), and so does
    # Fission 180 now; the refusal is tested with 0.89, which only the 20 tooth gear takes.
    ui.type_into(p.fillet.widget, "0.89")


def b_teeth():
    h.check("0.89 fits 20 teeth", panel().message.text() == "", panel().message.text())
    ui.type_into(panel().teeth.widget, "100")


def b_operation():
    p = panel()
    text = p.message.text()
    h.check(
        "says the fillet does not fit, and what does",
        "does not fit" in text and "0.885" in text,
        text,
    )
    h.check("New Component", ui.choose(p.operation, "New Component"))


def b_ok():
    p = panel()
    h.check(
        "New Component stays chosen",
        p.operation.currentText() == "New Component",
        p.operation.currentText(),
    )
    h.task_button("OK")


def b_refused():
    from fission180 import commands

    p = panel()
    h.check("OK is refused: the dialog stays", p is not None)
    told = str(commands._TOLD.get("msg") or "")
    h.check(
        "and says so next to the pointer",
        told.startswith("Gear not made") and "does not fit" in told,
        told,
    )
    h.check("the first gear is untouched", near(doc().getObject(s["first"]).Shape.Volume, s["v1"]))
    h.check(
        "New Component still chosen", p is not None and p.operation.currentText() == "New Component"
    )
    h.shot("B-refused")


# -- C ------------------------------------------------------------------------------------------
def c_edit_unfinished():
    h.check("the unfinished gear shows as a step", "Gear 2" in t.titles(), t.titles())
    t.menu("Gear 2", "Edit Feature")


def c_still_there():
    from fission180 import commands

    p = panel()
    h.check("the Gear dialog is still open", p is not None and p.target is not None)
    h.check("the step did not vanish", "Gear 2" in t.titles(), t.titles())
    told = str(commands._TOLD.get("msg") or "")
    h.check("it says to finish the dialog first", "still open" in told, told)
    h.check("two gears", len(gears()) == 2, gears())


# -- D ------------------------------------------------------------------------------------------
def d_fillet():
    ui.type_into(panel().fillet.widget, "0.88")


def d_thick():
    h.check(
        "the book's 0.88 fits 100 teeth: no message",
        panel().message.text() == "",
        panel().message.text(),
    )
    ui.type_into(panel().thickness.widget, "4")


def d_ok():
    h.task_button("OK")


def d_done():
    from fission180 import gear_core

    h.check("dialog closed", pi.no_dialog())
    second = [g for g in gears() if g.Name != s["first"]]
    if not h.check("the second gear", len(second) == 1, gears()):
        return
    g = second[0]
    s["second"] = g.Name
    o = read(g)
    h.check("100 teeth, 4 thick", o["teeth"] == 100 and near(o["thickness"], 4.0), o)
    want = gear_core.area(dict(module=1.5, teeth=100, hole=4.0, fillet=0.88)) * 4.0
    s["v2"] = g.Shape.Volume
    h.check("its volume", near(s["v2"], want, 1e-6), (s["v2"], want))
    part = component_of(g)
    h.check(
        "a New Component, named for its teeth",
        part is not None and part.Label == "Spur Gear (100 teeth)",
        part and part.Label,
    )
    h.check("the first is still 20 teeth", near(doc().getObject(s["first"]).Shape.Volume, s["v1"]))
    h.fit()
    h.shot("D-two-gears")


# -- E ------------------------------------------------------------------------------------------
def e_edit():
    h.click_empty()
    t.menu("Gear 2", "Edit Feature")


def e_opened():
    p = panel()
    if h.check(
        "Edit Feature opens the gear's dialog", p is not None and p.target is not None, t.titles()
    ):
        h.check("with 100 teeth", near(p.teeth.value(), 100.0), p.teeth.value())
    h.task_button("Cancel")


def e_cancelled():
    h.check("Cancel: the step is still there", "Gear 2" in t.titles(), t.titles())
    g = doc().getObject(s["second"])
    h.check("unchanged", g is not None and near(g.Shape.Volume, s["v2"]), g and g.Shape.Volume)
    t.menu("Gear 2", "Edit Feature")


def e_teeth():
    p = panel()
    if h.check("opened again", p is not None):
        ui.type_into(p.teeth.widget, "80")


def e_ok():
    h.task_button("OK")


def e_done():
    g = doc().getObject(s["second"])
    h.check("80 teeth", g is not None and read(g)["teeth"] == 80, g and read(g))
    part = component_of(g)
    h.check(
        "the component's name follows",
        part is not None and part.Label == "Spur Gear (80 teeth)",
        part and part.Label,
    )
    h.check(
        "still one Gear 2 step, and two gears",
        t.titles().count("Gear 2") == 1 and len(gears()) == 2,
        t.titles(),
    )
    t.undo()


def e_undone():
    g = doc().getObject(s["second"])
    h.check("Ctrl+Z: 100 teeth again", g is not None and read(g)["teeth"] == 100, g and read(g))
    part = component_of(g)
    h.check(
        "and its name",
        part is not None and part.Label == "Spur Gear (100 teeth)",
        part and part.Label,
    )


h.run(
    "book_modify_gear",
    [
        a_new,
        a_listed,
        a_gear_open,
        a_plane,
        a_centre,
        a_module,
        a_teeth,
        a_thick,
        a_hole,
        a_operation,
        a_ok,
        a_done,
        b_gear,
        b_plane,
        b_centre,
        b_fillet,
        b_teeth,
        b_operation,
        b_ok,
        b_refused,
        c_edit_unfinished,
        c_still_there,
        d_fillet,
        d_thick,
        d_ok,
        d_done,
        e_edit,
        e_opened,
        e_cancelled,
        e_teeth,
        e_ok,
        e_done,
        e_undone,
    ],
    paced_by="state",
)
