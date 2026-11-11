# SPDX-License-Identifier: LGPL-2.1-or-later
"""The appearance library, its search box, textured looks and the look editor, on the book's
Classic Donut (book parity report: "No look editor exists", "no appearance search box", "flat
colours only", "In This Design starting with the default look"). Only real input.

Donut = a torus on the XY plane, inner diameter 40, tube 20 (CREATE > Torus).

  A  Appearance: In This Design lists the design's default look from the start ("Steel, satin
     (default)", on the donut). The library lists well over a hundred looks with their names.
  B  the book's pink icing: double-click the default look, type #FF6FB5 in the editor: the
     donut turns pink at once; OK.
  C  search "oak": only oak looks are listed, "Oak" among them; a word that matches nothing
     says so; the category list narrows to Wood.
  D  "Oak" dragged onto the donut: stored with its pattern, and the screen shows a texture
     (the pixels vary far more than under the flat colour).
  E  right-click Oak in the library > Add to Favorites: the Favorites category lists it;
     Remove from Favorites empties it again.
  F  double-click Oak under In This Design: the editor. A click on the colour wheel, then a
     colour typed; Scale 40 %, Rotation 90: the donut follows each change. Advanced shows
     Shine / See-through / Glow, and what only a renderer shows greyed with the reason.
     A name another look has is refused; "Donut wood" is taken. OK.
  G  right-click the look: Duplicate ("Donut wood (1)", on nothing), Select Objects Applied To
     (the donut), Rename (the editor on the name), Delete of the duplicate; Delete of the
     default look is refused with the reason.
  H  Cancel in the editor puts a changed colour back.
  I  OK; Ctrl+Z takes it all back (grey donut, no pattern), Ctrl+Y brings it again.
  J  save, close, reopen: the look, its pattern on screen and the edited default are back.
"""

import os

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import looks_steps as k
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import primitive_input as pi
from Fission180Tests.gui import widget_input as w

V = App.Vector
PINK = (1.0, 0x6F / 255.0, 0xB5 / 255.0)
ON_DONUT = V(0, -30, 10)  # the top of the tube, on the side that faces the home view
state = {}


def body():
    return s.bodies()[0]


def look():
    return k.stored(body())["body"]


def tip_colour():
    cols = k.shown_colors(body().Tip)
    return cols[0] if cols else None


# -- the donut ---------------------------------------------------------------------------------
def torus_menu():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("Donut")
    h.fit()
    pi.menu("Torus")


def torus_plane():
    pl.click_square("XY_Plane")


def torus_centre():
    pl.click_on_plane(V(0, 0, 0))


def torus_circle():
    pl.click_on_plane(V(20, 0, 0))


def torus_inner():
    p = pi.panel("TorusPanel")
    if h.check("torus placed", p is not None and p.target is not None):
        ui.type_into(p.inner.widget, "40")


def torus_tube():
    ui.type_into(pi.panel("TorusPanel").tube.widget, "20")


def torus_ok():
    h.task_button("OK")


def torus_made():
    h.check("a donut", len(s.bodies()) == 1 and body().Shape.Volume > 1000, body().Shape.Volume)
    h.fit()
    state["flat"] = k.roughness(ON_DONUT)


# -- A ---------------------------------------------------------------------------------------------
def a_open():
    k.open_appearance()


def a_default():
    p = k.panel()
    if not h.check("Appearance dialog", p is not None):
        return
    labels = k.design_labels()
    h.check(
        "In This Design starts with the default look", labels == ["Steel, satin (default)"], labels
    )
    item = k.design_item("Steel, satin (default)")
    h.check("it says the donut has it", item is not None and body().Label in item.toolTip())
    names = k.library_labels()
    h.check("well over a hundred looks", len(names) > 150, len(names))
    for name in ("Oak", "Mahogany", "Pine", "Walnut", "Leather, brown", "Carbon fibre, twill"):
        h.check("the library lists %s" % name, name in names)
    shown = [p.library.item(i).text() for i in range(p.library.count())]
    h.check("the looks are listed by name", "Oak" in shown, shown[:3])
    h.shot("A-dialog")


# -- B: the pink icing -------------------------------------------------------------------------
def b_edit_default():
    k.double_click_design("Steel, satin (default)")


def b_editor():
    e = k.editor()
    if h.check("the look editor opens on a double-click", e is not None):
        h.check("it shows the look's name", e.name.text() == "Steel, satin (default)")
        k.type_field(e.hex, "#FF6FB5", QtCore.Qt.Key_Return)


def b_pink():
    e = k.editor()
    h.check("Enter in the colour box keeps the editor open", e is not None)
    h.check("the donut is pink at once", k.same(tip_colour(), PINK), tip_colour())
    if e is not None:
        h.check("R G B follow", [x.value() for x in e.rgb] == [255, 0x6F, 0xB5])
        w.click(e.ok_button)


def b_done():
    h.check("the editor closed", k.editor() is None)
    h.click_empty()
    rgb = k.screen_rgb(ON_DONUT)
    h.check("the screen shows the donut pink", k.hue_like(rgb, PINK, 0.12), rgb)
    h.check("the body itself stores no look", k.stored(body())["body"] is None)
    h.shot("B-pink")


# -- C: search ---------------------------------------------------------------------------------
def c_search_oak():
    p = k.panel()
    w.click(p.search)
    w.type_text(p.search, "oak")


def c_found():
    p = k.panel()
    names = k.library_labels()
    h.check("only oak looks", bool(names) and all("oak" in n.lower() for n in names), names)
    h.check("Oak is among them", "Oak" in names, names)
    h.check("the dialog counts them", p.found.text() == "%d looks" % len(names), p.found.text())
    w.key(p.search, QtCore.Qt.Key_Return)
    h.check("Enter in the search box does not close the dialog", k.panel() is not None)


def c_search_nothing():
    p = k.panel()
    k.type_field(p.search, "zzqq", QtCore.Qt.Key_Return)


def c_nothing():
    p = k.panel()
    h.check("nothing listed", k.library_labels() == [])
    h.check("and it says so", 'No look called "zzqq"' in p.found.text(), p.found.text())


def c_clear():
    p = k.panel()
    w.key(p.search, QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
    w.key(p.search, QtCore.Qt.Key_Delete)


def c_category():
    p = k.panel()
    h.check("everything is listed again", len(k.library_labels()) > 150)
    b.choose(p.category, "Wood")


def c_wood():
    from fission180 import appearance_library

    names = k.library_labels()
    want = [x["label"] for x in appearance_library.in_category("Wood")]
    h.check("the Wood category lists the woods", names == want, names)


def c_all():
    b.choose(k.panel().category, "All")


# -- D: a textured look ------------------------------------------------------------------------
def d_drop_oak():
    h.check("the 3D view takes the swatch", k.drop_look("Oak", ON_DONUT))


def d_oak():
    data = look() or {}
    h.check("the donut is Oak", data.get("key") == "wood_oak", data)
    h.check("Oak has a pattern", data.get("texture") == "wood_oak", data.get("texture"))
    groups, triangles = k.pattern_drawn(body().Tip)
    h.check("the pattern is drawn over the donut's faces", groups == 1 and triangles > 50)
    state["triangles"] = triangles
    h.click_empty()
    rough = k.roughness(ON_DONUT)
    h.check(
        "the screen shows a texture, not a flat colour",
        rough > 3.0 * state["flat"] + 1.0,
        (rough, state["flat"]),
    )
    state["rough"] = rough
    h.check("In This Design lists Oak", "Oak" in k.design_labels(), k.design_labels())
    h.shot("D-oak")


# -- E: favourites -----------------------------------------------------------------------------
def e_favorite():
    k.library_menu("Oak", "Add to Favorites")


def e_favorites_category():
    b.choose(k.panel().category, "Favorites")


def e_listed():
    h.check("Favorites lists Oak", k.library_labels() == ["Oak"], k.library_labels())


def e_unfavorite():
    k.library_menu("Oak", "Remove from Favorites")


def e_empty():
    p = k.panel()
    h.check("Favorites is empty again", k.library_labels() == [])
    h.check("and says how to fill it", "Add to Favorites" in p.found.text(), p.found.text())
    b.choose(p.category, "All")


# -- F: the editor -----------------------------------------------------------------------------
def f_edit():
    k.double_click_design("Oak")


def f_wheel():
    e = k.editor()
    if not h.check("the editor opens on Oak", e is not None and e.name.text() == "Oak"):
        return
    h.check("Scale and Rotation can be set (it has a pattern)", e.scale.isEnabled())
    h.check("Scale starts at 100 %", abs(e.scale.value() - 100.0) < 1e-6, e.scale.value())
    state["before_wheel"] = tip_colour()
    w.click(e.wheel, e.wheel.point_for(0.6, 0.8))  # a blue


def f_wheeled():
    col = tip_colour()
    h.check("a click on the colour wheel changes the donut", not k.same(col, state["before_wheel"]))
    h.check("to a blue", col is not None and col[2] > col[0] and col[2] > col[1], col)
    e = k.editor()
    k.type_field(e.hex, "#B5855A", QtCore.Qt.Key_Return)


def f_scale():
    h.check("the typed colour is on the donut", k.same(tip_colour(), (0.71, 0.522, 0.353), 0.01))
    e = k.editor()
    k.type_field(e.scale, "40")


def f_rotation():
    data = look()
    h.check("Scale 40 % is stored", abs(data.get("scale", 100) - 40.0) < 1e-6, data.get("scale"))
    k.type_field(k.editor().rotation, "90")


def f_advanced():
    data = look()
    h.check("Rotation 90 is stored", abs(data.get("rotation", 0) - 90.0) < 1e-6, data)
    groups, triangles = k.pattern_drawn(body().Tip)
    h.check("the pattern is still drawn", groups == 1 and triangles == state["triangles"])
    e = k.editor()
    h.check("Advanced is folded away", not e.shine.isVisible())
    k.click_group_tick(e.advanced)


def f_advanced_shown():
    e = k.editor()
    h.check("Advanced opens", e.advanced.isChecked() and e.shine.isVisible())
    h.check("Shine, See-through and Glow can be set", e.shine.isEnabled() and e.glow.isEnabled())
    greyed = [f for f in e.render_only if not f.isEnabled() and f.isVisible()]
    h.check("what only a renderer shows is greyed", len(greyed) == 3, len(greyed))
    h.check("with the reason", all("renderer" in f.toolTip() for f in e.render_only))
    k.type_field(e.name, "Steel, satin (default)")


def f_name_taken():
    e = k.editor()
    h.check(
        "a name another look has is refused",
        e is not None and "already" in e.message.text(),
        e and e.message.text(),
    )
    k.type_field(e.name, "Donut wood")


def f_ok():
    e = k.editor()
    h.check("the name is taken", e.message.text() == "", e.message.text())
    w.click(e.ok_button)


def f_done():
    h.check("the editor closed", k.editor() is None)
    data = look()
    h.check("the look is called Donut wood", data.get("label") == "Donut wood", data.get("label"))
    h.check("In This Design shows the new name", "Donut wood" in k.design_labels())
    h.check("and no Oak any more", "Oak" not in k.design_labels(), k.design_labels())
    h.click_empty()
    h.check("the texture is still on screen", k.roughness(ON_DONUT) > 3.0 * state["flat"] + 1.0)
    h.shot("F-edited")


# -- G: the look's menu ------------------------------------------------------------------------
def g_entries():
    entries = k.design_menu_entries("Donut wood")
    want = [
        "Edit",
        "Duplicate",
        "Rename",
        "Delete",
        "Select Objects Applied To",
        "Add to Favorites",
    ]
    h.check("the look's right-click menu", entries == want, entries)


def g_duplicate():
    k.design_menu("Donut wood", "Duplicate")


def g_duplicated():
    labels = k.design_labels()
    h.check("a duplicate is in In This Design", "Donut wood (1)" in labels, labels)
    item = k.design_item("Donut wood (1)")
    h.check("it is on nothing yet", item is not None and "not on anything" in item.toolTip())


def g_select():
    k.design_menu("Donut wood", "Select Objects Applied To")


def g_selected():
    names = [x.ObjectName for x in Gui.Selection.getSelectionEx()]
    h.check("the donut is selected", names == [body().Name], names)
    p = k.panel()
    h.check("the dialog names it", body().Label in p.note.text(), p.note.text())
    h.check("the selection did not give anything a look", look().get("label") == "Donut wood")


def g_rename():
    h.click_empty()
    k.design_menu("Donut wood (1)", "Rename")


def g_renaming():
    e = k.editor()
    named = e is not None and e.name.selectedText() == "Donut wood (1)"
    if h.check("Rename opens the editor with the name selected", named):
        w.type_text(e.name, "Spare wood")
        w.click(e.ok_button)


def g_renamed():
    h.check("renamed", "Spare wood" in k.design_labels(), k.design_labels())


def g_delete():
    k.design_menu("Spare wood", "Delete")


def g_deleted():
    h.check("the duplicate is gone", "Spare wood" not in k.design_labels(), k.design_labels())


def g_delete_default():
    k.design_menu("Steel, satin (default)", "Delete")


def g_refused():
    p = k.panel()
    h.check("the default look is still there", "Steel, satin (default)" in k.design_labels())
    h.check("and the dialog says why", "default look" in p.message.text(), p.message.text())


# -- H: Cancel in the editor -------------------------------------------------------------------
def h_edit():
    k.double_click_design("Donut wood")


def h_change():
    e = k.editor()
    if h.check("editor open", e is not None):
        state["before_cancel"] = tip_colour()
        k.type_field(e.hex, "#00FF00", QtCore.Qt.Key_Return)


def h_cancel():
    h.check("green for now", k.same(tip_colour(), (0.0, 1.0, 0.0)), tip_colour())
    w.click(k.editor().cancel_button)


def h_back():
    h.check("the editor closed", k.editor() is None)
    h.check("Cancel puts the colour back", k.same(tip_colour(), state["before_cancel"]))


# -- I ---------------------------------------------------------------------------------------------
def i_ok():
    h.task_button("OK")


def i_undo():
    s.undo()


def i_undone():
    from fission180 import appearance

    h.check("Undo: the donut has no look", look() is None, look())
    h.check(
        "Undo: the default look is not edited",
        appearance.edited_default(App.ActiveDocument) is None,
    )
    h.check("Undo: no pattern on screen", k.pattern_drawn(body().Tip) == (0, 0))
    h.click_empty()
    h.check("Undo: the screen is flat again", k.roughness(ON_DONUT) < state["flat"] + 1.0)


def i_redo():
    s.redo()


def i_redone():
    h.check("Redo: Donut wood again", (look() or {}).get("label") == "Donut wood", look())
    h.check("Redo: its pattern on screen", k.pattern_drawn(body().Tip)[0] == 1)


# -- J ---------------------------------------------------------------------------------------------
def j_save():
    path = os.path.join(h.OUT_DIR, "book_looks_library.FCStd")
    state["path"] = path
    App.ActiveDocument.saveAs(path)
    App.closeDocument(App.ActiveDocument.Name)


def j_reopen():
    App.openDocument(state["path"])
    h.fit()


def j_back():
    from fission180 import appearance

    data = look() or {}
    h.check("the look is in the file", data.get("label") == "Donut wood", data)
    h.check(
        "with its scale and rotation", data.get("scale") == 40.0 and data.get("rotation") == 90.0
    )
    h.check("its pattern is drawn again", k.pattern_drawn(body().Tip)[0] == 1)
    default = appearance.edited_default(App.ActiveDocument)
    h.check(
        "the edited default look is in the file",
        default is not None and k.same(default["color"], PINK),
    )
    h.click_empty()
    h.check("the screen shows the texture", k.roughness(ON_DONUT) > 3.0 * state["flat"] + 1.0)
    h.check("the design opens unchanged", not Gui.ActiveDocument.Modified)
    h.shot("J-reopened")


h.run(
    "book_looks_library",
    [
        torus_menu,
        torus_plane,
        torus_centre,
        torus_circle,
        torus_inner,
        torus_tube,
        torus_ok,
        torus_made,
        a_open,
        a_default,
        b_edit_default,
        b_editor,
        b_pink,
        b_done,
        c_search_oak,
        c_found,
        c_search_nothing,
        c_nothing,
        c_clear,
        c_category,
        c_wood,
        c_all,
        d_drop_oak,
        d_oak,
        e_favorite,
        e_favorites_category,
        e_listed,
        e_unfavorite,
        e_empty,
        f_edit,
        f_wheel,
        f_wheeled,
        f_scale,
        f_rotation,
        f_advanced,
        f_advanced_shown,
        f_name_taken,
        f_ok,
        f_done,
        g_entries,
        g_duplicate,
        g_duplicated,
        g_select,
        g_selected,
        g_rename,
        g_renaming,
        g_renamed,
        g_delete,
        g_deleted,
        g_delete_default,
        g_refused,
        h_edit,
        h_change,
        h_cancel,
        h_back,
        i_ok,
        i_undo,
        i_undone,
        i_redo,
        i_redone,
        j_save,
        j_reopen,
        j_back,
    ],
    paced_by="state",
)
