# SPDX-License-Identifier: LGPL-2.1-or-later
"""A body keeps its look on screen (book parity report, bug 16: "Looks silently lost. A body
shows plain grey while the Appearance panel still lists its look, for example after Isolate /
Exit Isolate + Move. Dropping the same look again does nothing"). Only real input.

Handle = a root body 40 x 30 x 10; Bracket = a component with a body 40 x 30 x 10 at x 60.

  A  Appearance, drag "Wood, dark" (the report's look) onto the Handle, OK: the screen shows
     it brown.
  B  Isolate Bracket (the Handle is hidden), Exit Isolate: brown again.
  C  Move/Copy the Bracket component 15 mm (typed), OK: the Handle is still brown.
  D  the Handle's eye off and on in the browser: brown.
  E  Physical Material Aluminium, then Aluminium 6061 (two materials with the same look):
     the Handle keeps its Appearance (Fusion: an appearance overrides the material's look).
     Before the fix the second one turned every step grey and nothing put the look back.
  F  a boss on the Handle (a new step), Undo, Redo: brown each time.
  G  Appearance again. FreeCAD overwrites the Handle's colours (the body's material read, then
     written): the look is back at once. The same look dragged onto the Handle again is put
     on again (the dialog says so).
  H  save, close, reopen: brown.
"""

import os

import FreeCAD as App

from Fission180Tests.gui import arrow_input as ai
from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import component2_steps as c2
from Fission180Tests.gui import component_steps as cs
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import looks_steps as k
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import timeline_input as t

V = App.Vector
LOOK = "Wood, dark"
state = {}
ON_HANDLE = V(30, 22, 10)  # on its top face: where looks are dropped and clicks land
ON_SIDE = V(40, 15, 5)  # on its right face: where the screen is read (a sketch shown on the
# top face after an Undo shades that face blue)


def handle():
    return App.ActiveDocument.getObject(state["handle"])


def look_rgb():
    from fission180 import appearance

    look = appearance.effective(handle())
    return look["color"] if look else (0.5, 0.5, 0.5)


def brown(where):
    """The Handle shows its look: the property FreeCAD draws from, and the screen (with
    nothing selected and the pointer off the part: a hovered or selected face is drawn in
    the highlight's colour)."""
    h.click_empty()
    body = handle()
    cols = k.shown_colors(body.Tip)
    h.check(
        "%s: the Handle's end step is drawn in its look" % where,
        bool(cols) and all(k.same(col, look_rgb()) for col in cols),
        (cols[:2], look_rgb()),
    )
    rgb = k.screen_rgb(ON_SIDE)
    h.check(
        "%s: the screen shows the look's colour, not grey" % where,
        not k.is_grey(rgb) and k.hue_like(rgb, look_rgb()),
        rgb,
    )


def remember_handle():
    state["handle"] = s.bodies()[0].Name
    state["label"] = s.bodies()[0].Label


# -- the Bracket component -----------------------------------------------------------------------
def comp_ribbon():
    h.click_empty()
    h.ribbon("New Component")


def comp_name():
    cs.type_name("Bracket")


def comp_ok():
    h.task_button("OK")


def comp_sketch():
    h.fit()
    h.ribbon("Create Sketch")


def comp_plane():
    pl.click_square("XY_Plane")


def comp_draw():
    sk = h.in_sketch()
    if h.check("sketch open in Bracket", sk is not None):
        h.draw_rectangle(sk, 60, 0, 100, 30)


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
    h.check("two bodies", len(s.bodies()) == 2, [b.Label for b in s.bodies()])
    h.check("Bracket holds one", cs.container_label(s.bodies()[1]) == "Bracket")


def activate_root():
    cs.click_radio(App.ActiveDocument.Label)


def root_active():
    h.check("the root is active", cs.active_label() is None, cs.active_label())
    h.fit()


# -- A ---------------------------------------------------------------------------------------------
def a_open():
    k.open_appearance()


def a_drop():
    h.check("the 3D view takes the swatch", k.drop_look(LOOK, ON_HANDLE))


def a_ok():
    p = k.panel()
    h.check(
        "the dialog names the look", p is not None and LOOK in p.note.text(), p and p.note.text()
    )
    h.task_button("OK")


def a_brown():
    h.check("the Handle's look is stored", k.body_look_label(handle()) == LOOK)
    brown("A dropped")
    h.shot("A-look")


# -- B ---------------------------------------------------------------------------------------------
def b_isolate():
    t.row_menu("Bracket", "Isolate")


def b_isolated():
    h.check("the Handle is hidden", not t.shown(handle()))


def b_exit():
    t.row_menu("Bracket", "Exit Isolate")


def b_back():
    h.check("the Handle is shown again", t.shown(handle()))
    brown("B after Isolate / Exit Isolate")


# -- C ---------------------------------------------------------------------------------------------
def c_move():
    h.click_empty()
    h.press("m")


def c_components():
    p = c2.panel()
    if h.check("Move/Copy open", p is not None and p.title == "Move/Copy", p):
        c2.choose(p.move_object, "Components", closes=True)


def c_pick():
    h.click(V(80, 15, 10))


def c_type():
    p = c2.component_panel()
    if h.check("the components dialog", p is not None):
        h.check("Bracket picked", len(p.options.get("components") or []) == 1, p.options)
        c2.type_value(p, "dy", "15")


def c_ok():
    h.task_button("OK")


def c_moved():
    part = cs.component("Bracket")
    h.check("Bracket moved 15 in Y", abs(c2.at(part).y - 15) < 1e-6, c2.at(part))
    brown("C after Move")
    h.shot("C-moved")


# -- D ---------------------------------------------------------------------------------------------
def d_hide():
    t.click_eye(state["label"])


def d_hidden():
    from fission180 import body_visibility

    h.check("the Handle is hidden by its eye", not body_visibility.drawn(handle()))


def d_show():
    t.click_eye(state["label"])


def d_shown():
    brown("D after hide / show")


# -- E ---------------------------------------------------------------------------------------------
def material_steps(name, label, freecad_name):
    def open_():
        h.click_empty()
        s.menu("MODIFY", "Physical Material")

    def pick():
        p = s.panel()
        if h.check("Physical Material open", p is not None and p.title == "Physical Material"):
            item = p.item_for(label)
            if h.check("library has %s" % label, item is not None):
                k.click_item(p.library, item)

    def click():
        h.click(ON_HANDLE)

    def ok():
        h.task_button("OK")

    def made():
        h.check(
            "the Handle is %s" % label,
            handle().ShapeMaterial.Name == freecad_name,
            handle().ShapeMaterial.Name,
        )
        brown("E after %s" % label)

    steps = [open_, pick, click, ok, made]
    for step in steps:
        step.__name__ = "e_%s_%s" % (name, step.__name__.strip("_"))
    return steps


# -- F ---------------------------------------------------------------------------------------------
def f_made():
    brown("F after the boss")


def f_undo():
    s.undo()


def f_undone():
    h.check("the boss is gone", abs(handle().Shape.Volume - 12000) < 1e-6, handle().Shape.Volume)
    brown("F after Undo of the boss")


def f_redo():
    s.redo()


def f_redone():
    h.check("the boss is back", abs(handle().Shape.Volume - 12500) < 1e-6, handle().Shape.Volume)
    brown("F after Redo")


# -- G ---------------------------------------------------------------------------------------------
def g_open():
    k.open_appearance()


def g_listed():
    h.check("In This Design lists the look", LOOK in k.design_labels(), k.design_labels())


def g_read():
    """What took the looks away (found with FreeCAD 1.1.4): a physical value of a body's
    own material only read through Python makes FreeCAD write the material's grey on every
    step of the body. The look is back on its own, without a recompute."""
    state["density"] = str(handle().ShapeMaterial.getPhysicalValue("Density"))


def g_read_back():
    h.check("a density was read", bool(state.get("density")), state.get("density"))
    brown("G after the material's density was read")


def g_spoil():
    """The same when the body's material is written (even with what it is already)."""
    body = handle()
    body.ShapeMaterial = body.ShapeMaterial


def g_put_back():
    brown("G after the material was written")


def g_drop_again():
    from fission180 import appearance

    state["applied"] = appearance.applied_count()
    h.check("the 3D view takes the swatch again", k.drop_look(LOOK, ON_HANDLE))


def g_taken():
    from fission180 import appearance

    p = k.panel()
    h.check(
        "the same look dropped again is put on again",
        appearance.applied_count() > state["applied"],
        (state["applied"], appearance.applied_count()),
    )
    h.check("the dialog says so", p is not None and LOOK in p.note.text(), p and p.note.text())
    brown("G dropped again")


def g_ok():
    h.task_button("OK")


# -- H ---------------------------------------------------------------------------------------------
def h_save():
    path = os.path.join(h.OUT_DIR, "book_looks_kept.FCStd")
    state["path"] = path
    App.ActiveDocument.saveAs(path)
    App.closeDocument(App.ActiveDocument.Name)


def h_reopen():
    App.openDocument(state["path"])
    h.fit()


def h_back():
    h.check("the look is stored in the file", k.body_look_label(handle()) == LOOK)
    brown("H reopened")
    h.shot("H-reopened")


h.run(
    "book_looks_kept",
    [s.new_design("LooksKept")]
    + s.box_steps("handle", (0, 0, 40, 30), 10, V(6, -6, 0))
    + [
        remember_handle,
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
        a_drop,
        a_ok,
        a_brown,
        b_isolate,
        b_isolated,
        b_exit,
        b_back,
        c_move,
        c_components,
        c_pick,
        c_type,
        c_ok,
        c_moved,
        d_hide,
        d_hidden,
        d_show,
        d_shown,
    ]
    + material_steps("alu", "Aluminium", "Aluminum-Generic")
    + material_steps("6061", "Aluminium 6061", "Aluminum-6061-T6")
    + s.box_steps("boss", (5, 5, 15, 15), 5, V(10, 10, 10), check_volume=24000 + 500)
    + [
        f_made,
        f_undo,
        f_undone,
        f_redo,
        f_redone,
        g_open,
        g_listed,
        g_read,
        g_read_back,
        g_spoil,
        g_put_back,
        g_drop_again,
        g_taken,
        g_ok,
        h_save,
        h_reopen,
        h_back,
    ],
    paced_by="state",
)
