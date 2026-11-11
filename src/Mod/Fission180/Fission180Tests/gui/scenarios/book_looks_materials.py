# SPDX-License-Identifier: LGPL-2.1-or-later
"""Physical materials, Properties and the selection read-out (book parity report: "Physical
Material has no Brass", "the density can't be edited on a library material", "every line is
'Body1: ...' with no component name", "No right-click > Properties (mass)", "Clicking the flat
underside shows no area in the bottom right"). Only real input.

Plate = a root body 40 x 30 x 10 (12000 mm3); Nozzle = a component with a body 20 x 20 x 10
at x 60 (4000 mm3).

  A  Physical Material lists Brass, Gold, Carbon Fibre, anodized aluminium, ABS; the search
     box narrows the list and says when nothing matches.
  B  Brass, a click on the Nozzle's body: it is brass, 4000 mm3 x 8.5 g/cm3 = 34.00 g, listed
     with its component's name, and it looks brass (the material brings its look).
  C  double-click Brass: library materials cannot be changed, a copy can. "Brass C360" with
     8.6 g/cm3 is made, listed and picked; the Nozzle's body made of it weighs 34.40 g. A
     copy may be called Chrome (FreeCAD has a colour card of that name no list shows; before,
     that was refused as "already a material").
  D  OK; Ctrl+Z: no material, no look; Ctrl+Y: back.
  E  Properties of the Nozzle (selected in the browser): mass 34.4 g, volume, area, density,
     material, size and centre of mass. Nothing selected: the whole design, 129.2 g, 2
     bodies. Copy to Clipboard.
  F  the read-out at the bottom right: a face says its area and outline, an edge its length,
     two faces their distance; nothing selected hides it.
  G  save, close, reopen: the Nozzle is still Brass C360 and looks brass.
"""

import os

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets

from Fission180Tests.gui import arrow_input as ai
from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import component_steps as cs
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import looks_steps as k
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import timeline_input as t
from Fission180Tests.gui import widget_input as w

V = App.Vector
BRASS = (0.78, 0.62, 0.30)
ON_NOZZLE = V(70, 10, 10)
ON_PLATE = V(20, 15, 10)
state = {}


def nozzle():
    return App.ActiveDocument.getObject(state["nozzle"])


def plate():
    return App.ActiveDocument.getObject(state["plate"])


def panel():
    p = s.panel()
    return p if p is not None and p.title == "Physical Material" else None


def close(a, b, tol=1e-6):
    return abs(a - b) <= tol


def mass_g(body):
    from fission180 import material

    kg = material.mass(body)
    return None if kg is None else kg * 1000.0


def remember_plate():
    state["plate"] = s.bodies()[0].Name


# -- the Nozzle component --------------------------------------------------------------------
def comp_ribbon():
    h.click_empty()
    h.ribbon("New Component")


def comp_name():
    cs.type_name("Nozzle")


def comp_ok():
    h.task_button("OK")


def comp_sketch():
    h.fit()
    h.ribbon("Create Sketch")


def comp_plane():
    pl.click_square("XY_Plane")


def comp_draw():
    sk = h.in_sketch()
    if h.check("sketch open in Nozzle", sk is not None):
        h.draw_rectangle(sk, 60, 0, 80, 20)


def comp_finish():
    h.ribbon("Finish Sketch")


def comp_extrude():
    h.fit()
    h.press("e")


def comp_distance():
    h.check("extrude dialog", ai.give_distance("10"))


def comp_ok2():
    h.task_button("OK")


def comp_made():
    found = [b for b in s.bodies() if cs.container_label(b) == "Nozzle"]
    if h.check("the Nozzle has a body", len(found) == 1):
        state["nozzle"] = found[0].Name
        h.check("4000 mm3", close(found[0].Shape.Volume, 4000.0), found[0].Shape.Volume)


def activate_root():
    cs.click_radio(App.ActiveDocument.Label)


def root_active():
    h.check("the root is active", cs.active_label() is None, cs.active_label())
    h.fit()


# -- A ---------------------------------------------------------------------------------------------
def a_open():
    h.click_empty()
    s.menu("MODIFY", "Physical Material")


def a_library():
    p = panel()
    if not h.check("Physical Material dialog", p is not None):
        return
    for label in (
        "Brass",
        "Gold",
        "Carbon Fibre",
        "Aluminium, anodized red",
        "ABS Plastic",
        "Bronze",
        "Oak",
    ):
        h.check("the library lists %s" % label, p.item_for(label) is not None)
    item = p.item_for("Brass")
    h.check("with its density", item is not None and "8.5 g/cm³" in item.text(), item.text())
    h.check("more than forty materials", p.library.count() > 40, p.library.count())
    state["all"] = p.library.count()


def a_search():
    p = panel()
    w.click(p.search)
    w.type_text(p.search, "anod red")


def a_found():
    p = panel()
    rows = [p.library.item(i).text() for i in range(p.library.count())]
    h.check("only the anodized red aluminium", len(rows) == 1 and "anodized red" in rows[0], rows)
    w.key(p.search, QtCore.Qt.Key_Return)
    h.check("Enter in the search box does not close the dialog", panel() is not None)
    k.type_field(p.search, "zzqq", QtCore.Qt.Key_Return)


def a_nothing():
    p = panel()
    h.check("nothing listed", p.library.count() == 0)
    h.check("and it says so", 'No material called "zzqq"' in p.found.text(), p.found.text())
    w.key(p.search, QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
    w.key(p.search, QtCore.Qt.Key_Delete)


# -- B ---------------------------------------------------------------------------------------------
def b_pick_brass():
    p = panel()
    h.check("the whole library again", p.library.count() == state["all"], p.library.count())
    k.click_item(p.library, p.item_for("Brass"))


def b_click_nozzle():
    h.click(ON_NOZZLE)


def b_brass():
    from fission180 import material

    p = panel()
    body = nozzle()
    h.check("the Nozzle's body is Brass", material.key_of(body) == "brass", material.key_of(body))
    h.check("34.00 g", close(mass_g(body), 34.0, 1e-6), mass_g(body))
    lines = p.masses.text().split("\n")
    mine = [x for x in lines if "(Nozzle)" in x]
    h.check("listed with its component's name", len(mine) == 1 and "34.00 g" in mine[0], lines)
    h.check("the plate is still default steel", any("94.80 g" in x for x in lines), lines)
    rows = [p.design.item(i).text() for i in range(p.design.count())]
    h.check("In This Design names the component too", any("(Nozzle)" in r for r in rows), rows)
    look = k.stored(body)["material"]
    h.check("the material brings its look", (look or {}).get("key") == "brass", look)
    cols = k.shown_colors(body.Tip)
    h.check("the body is drawn brass", bool(cols) and k.same(cols[0], BRASS), cols[:1])
    h.shot("B-brass")


# -- C ---------------------------------------------------------------------------------------------
def c_double_click():
    p = panel()
    item = p.item_for("Brass")
    p.library.scrollToItem(item)
    w.double_click(p.library.viewport(), p.library.visualItemRect(item).center())


def c_copy_box():
    p = panel()
    if not h.check("Edit a Copy opens", p.copy_box.isVisible()):
        return
    h.check("it says what it copies", p.copy_of.text() == "Brass", p.copy_of.text())
    h.check("a free name is offered", p.copy_name.text() == "Brass (1)", p.copy_name.text())
    h.check("with the density", p.copy_density.text() == "8.5", p.copy_density.text())
    h.check("and why", "cannot be changed" in p.info.text(), p.info.text())
    k.type_field(p.copy_name, "Brass")
    k.type_field(p.copy_density, "8.6")
    w.click(p.copy_create)


def c_name_taken():
    p = panel()
    h.check(
        "a name the list has is refused",
        "already a material called Brass" in p.message.text(),
        p.message.text(),
    )
    k.type_field(p.copy_name, "Brass C360")
    w.click(p.copy_create)


def c_made():
    from fission180 import material

    p = panel()
    h.check("no refusal left", p.message.text() == "", p.message.text())
    h.check("the box closed", not p.copy_box.isVisible())
    item = p.item_for("Brass C360")
    h.check("the copy is listed", item is not None and "8.6 g/cm³" in item.text())
    h.check("and picked", p.chosen.text() == "Brass C360", p.chosen.text())
    keys = [r["key"] for r in material.user_entries() if r["label"] == "Brass C360"]
    h.check("it is one of My Materials", len(keys) == 1, keys)
    h.check("Brass itself is unchanged", close(material.density_of("brass") * 1e6, 8.5))


def c_click_nozzle():
    h.click(ON_NOZZLE)


def c_heavier():
    from fission180 import material

    body = nozzle()
    label, _rho = material.effective(body)
    h.check("the Nozzle's body is Brass C360", label == "Brass C360", label)
    h.check("34.40 g", close(mass_g(body), 34.4, 1e-6), mass_g(body))
    cols = k.shown_colors(body.Tip)
    h.check("still drawn brass (the copy looks like Brass)", bool(cols) and k.same(cols[0], BRASS))


def c_chrome_copy():
    p = panel()
    item = p.item_for("Steel")
    w.right_click(p.library.viewport(), p.library.visualItemRect(item).center(), "Edit a Copy")


def c_chrome_name():
    p = panel()
    if h.check("Edit a Copy from the right-click menu", p.copy_box.isVisible()):
        h.check("of Steel", p.copy_of.text() == "Steel", p.copy_of.text())
        k.type_field(p.copy_name, "Chrome")
        w.click(p.copy_create)


def c_chrome_made():
    p = panel()
    h.check("a copy may be called Chrome", p.message.text() == "", p.message.text())
    h.check("and is listed", p.item_for("Chrome") is not None)
    k.click_item(p.library, p.item_for("Brass C360"))


# -- D ---------------------------------------------------------------------------------------------
def d_ok():
    h.task_button("OK")


def d_undo():
    s.undo()


def d_undone():
    from fission180 import material

    body = nozzle()
    h.check("Undo: default steel again", material.key_of(body) == "", material.key_of(body))
    h.check("Undo: 31.60 g", close(mass_g(body), 31.6, 1e-6), mass_g(body))
    h.check("Undo: no brass look", k.stored(body)["material"] is None)


def d_redo():
    s.redo()


def d_redone():
    from fission180 import material

    h.check("Redo: Brass C360", material.effective(nozzle())[0] == "Brass C360")
    cols = k.shown_colors(nozzle().Tip)
    h.check("Redo: drawn brass", bool(cols) and k.same(cols[0], BRASS), cols[:1])


# -- E: Properties -----------------------------------------------------------------------------
def props():
    from fission180 import properties_ui

    return properties_ui.dialog()


def e_select():
    t.click_row("Nozzle")


def e_open():
    s.menu("INSPECT", "Properties")


def e_nozzle():
    d = props()
    if not h.check("the Properties dialog", d is not None):
        return
    h.check("of the Nozzle", "Nozzle" in d.title.text() and "1 body" in d.title.text())
    for name, want in (
        ("Mass", "34.4 g"),
        ("Volume", "4000 mm^3"),
        ("Area", "1600 mm^2"),
        ("Density", "8.6 g/cm^3"),
        ("Physical Material", "Brass C360"),
        ("Appearance", "Brass"),
    ):
        h.check(
            "%s %s" % (name, want), d.value("Physical", name) == want, d.value("Physical", name)
        )
    h.check("Length 20 mm", d.value("Bounding Box", "Length") == "20 mm")
    h.check("Width 20 mm", d.value("Bounding Box", "Width") == "20 mm")
    h.check("Height 10 mm", d.value("Bounding Box", "Height") == "10 mm")
    centre = d.value("Center of Mass", "X, Y, Z")
    h.check("centre of mass 70, 10, 5 mm", centre == "70, 10, 5 mm", centre)
    ixx = d.value("Moment of Inertia at Center of Mass", "Ixx")
    # m (b^2 + c^2) / 12 = 34.4 g (400 + 100) / 12
    h.check("Ixx about the centre", ixx == "1433", ixx)
    h.shot("E-properties")


def e_whole():
    h.click_empty()


def e_design():
    d = props()
    if not h.check("the dialog stays open", d is not None):
        return
    h.check("it follows the selection: the whole design", "2 bodies" in d.title.text())
    h.check("Mass 129.2 g", d.value("Physical", "Mass") == "129.2 g", d.value("Physical", "Mass"))
    h.check("Volume 16000 mm^3", d.value("Physical", "Volume") == "16000 mm^3")
    h.check("two materials", d.value("Physical", "Physical Material") == "Various")
    h.check("Length 80 mm", d.value("Bounding Box", "Length") == "80 mm")
    w.click(d.copy)


def e_copied():
    d = props()
    text = QtWidgets.QApplication.clipboard().text()
    h.check("Copy to Clipboard", "Mass\t129.2 g" in text and "Bounding Box" in text, text[:80])
    w.click(d.close_button)


def e_closed():
    h.check("Close closes it", props() is None)


# -- F: the read-out ---------------------------------------------------------------------------
def readout():
    from fission180 import properties_readout_ui

    return properties_readout_ui.rows()


def f_face():
    h.click(ON_PLATE)


def f_area():
    rows = readout()
    h.check("a face says its area", ("Area", "1200 mm^2") in rows, rows)
    h.check("and its outline", ("Loop Length", "140 mm") in rows, rows)
    label = Gui.getMainWindow().findChild(QtWidgets.QLabel, "Fission180SelectionReadout")
    h.check("at the bottom right of the 3D view", label is not None and label.isVisible())
    if label is not None:
        gl = h.gl_widget()
        corner = gl.mapToGlobal(QtCore.QPoint(gl.width(), gl.height()))
        spot = label.mapToGlobal(QtCore.QPoint(label.width(), label.height()))
        # (in the strip under the view, beside the navigation bar: it covers no part)
        near = 0 <= corner.x() - spot.x() < 200 and abs(corner.y() - spot.y()) < 60
        h.check("in the corner", near, (corner, spot))
        h.check("it shows squared millimetres", "mm²" in label.text(), label.text())
    h.shot("F-readout")


def f_edge():
    h.check("an edge under the click", h.click_edge(V(20, 0, 10)))


def f_length():
    h.check("an edge says its length", readout() == [("Length", "40 mm")], readout())


def f_two_a():
    h.click(ON_PLATE)


def f_two_b():
    h.click(ON_NOZZLE, QtCore.Qt.ControlModifier)


def f_distance():
    rows = readout()
    h.check("two faces say their distance", rows == [("Distance", "20 mm")], rows)


def f_none():
    h.click_empty()


def f_hidden():
    h.check("nothing selected: no read-out", readout() == [])


# -- G ---------------------------------------------------------------------------------------------
def g_save():
    path = os.path.join(h.OUT_DIR, "book_looks_materials.FCStd")
    state["path"] = path
    App.ActiveDocument.saveAs(path)
    App.closeDocument(App.ActiveDocument.Name)


def g_reopen():
    App.openDocument(state["path"])
    h.fit()


def g_back():
    from fission180 import material

    body = nozzle()
    h.check("the Nozzle is still Brass C360", material.effective(body)[0] == "Brass C360")
    h.check("34.40 g", close(mass_g(body), 34.4, 1e-6), mass_g(body))
    cols = k.shown_colors(body.Tip)
    h.check("drawn brass", bool(cols) and k.same(cols[0], BRASS), cols[:1])
    h.click_empty()
    rgb = k.screen_rgb(ON_NOZZLE)
    h.check("the screen shows it brass", k.hue_like(rgb, BRASS, 0.12), rgb)


h.run(
    "book_looks_materials",
    [s.new_design("LooksMaterials")]
    + s.box_steps("plate", (0, 0, 40, 30), 10, V(6, -6, 0))
    + [
        remember_plate,
        comp_ribbon,
        comp_name,
        comp_ok,
        comp_sketch,
        comp_plane,
        comp_draw,
        comp_finish,
        comp_extrude,
        comp_distance,
        comp_ok2,
        comp_made,
        activate_root,
        root_active,
        a_open,
        a_library,
        a_search,
        a_found,
        a_nothing,
        b_pick_brass,
        b_click_nozzle,
        b_brass,
        c_double_click,
        c_copy_box,
        c_name_taken,
        c_made,
        c_click_nozzle,
        c_heavier,
        c_chrome_copy,
        c_chrome_name,
        c_chrome_made,
        d_ok,
        d_undo,
        d_undone,
        d_redo,
        d_redone,
        e_select,
        e_open,
        e_nozzle,
        e_whole,
        e_design,
        e_copied,
        e_closed,
        f_face,
        f_area,
        f_edge,
        f_length,
        f_two_a,
        f_two_b,
        f_distance,
        f_none,
        f_hidden,
        g_save,
        g_reopen,
        g_back,
    ],
    paced_by="state",
)
