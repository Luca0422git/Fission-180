# SPDX-License-Identifier: LGPL-2.1-or-later
"""Texture Map Controls, patterns under Opacity Control and Display Component Colors, a
textured face on a textured body, and the Component Color Swatch (book parity report:
"Texture Map Controls (Box projection, grain direction ring) do not exist", "Gear icon (bottom
right) > Component Color Swatch does not exist"). Only real input.

Body = box 0..40 x 0..30 x 10.

  A  MODIFY > Texture Map Controls on a body whose look has no pattern: the dialog says
     there is nothing to see yet. Cancel.
  B  Appearance, "Mahogany" dragged onto the body, OK: its grain is drawn.
  C  Texture Map Controls, a click on the body: Projection Automatic. Scale 50 %: the
     pattern is half as big (twice the repeats). Rotation 90, Offset U 10: the pattern
     moves. Planar needs an Axis, Box and Automatic do not. Reset: as at the start. Then
     Box, Scale 200 %, OK.
  D  Ctrl+Z: the map is gone; Ctrl+Y: back. Texture Map Controls again, Scale 30, Esc: back
     to 200.
  E  the browser's Opacity Control 60 % on the body: it is 40 % see-through and still
     mahogany, its pattern as see-through as the body; 100 %: solid again.
  F  Appearance, Faces, "Leather, brown" dragged onto the top face: two patterns on one body.
  G  INSPECT > Display Component Colors: the patterns are off under the colours; again: on.
  H  the timeline's gear > Component Color Swatch: no component yet, it says so; with a
     component its row and the design's row are marked in the browser, its steps in the
     timeline; the gear's entry is ticked;
     once more: off.
  I  save, close, reopen: the map and both patterns are back.
"""

import os

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import component_steps as cs
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import looks_steps as k
from Fission180Tests.gui import timeline_input as t
from Fission180Tests.gui import widget_input as w

V = App.Vector
MAHOGANY = (0.50, 0.22, 0.14)
TOP = V(20, 15, 10)
state = {}


def body():
    return s.bodies()[0]


def stored_map():
    from fission180 import appearance

    return appearance.get_map(body())


def panel():
    p = s.panel()
    return p if p is not None and p.title == "Texture Map Controls" else None


def span():
    """How many repeats of the pattern the body's faces span, along u and along v."""
    uvs = k.pattern_uvs(body().Tip)
    if not uvs:
        return None
    us, vs = [p[0] for p in uvs], [p[1] for p in uvs]
    return max(us) - min(us), max(vs) - min(vs)


def near(a, c, tol=0.02):
    return abs(a - c) <= tol * max(1.0, abs(c))


def open_map():
    h.click_empty()
    s.menu("MODIFY", "Texture Map Controls")


# -- A ---------------------------------------------------------------------------------------------
def a_open():
    h.fit()
    h.click_empty()
    state["flat"] = k.roughness(TOP)
    open_map()


def a_waits():
    p = panel()
    if h.check("Texture Map Controls dialog", p is not None):
        h.check("it waits for a body", "Click the body" in p.info.text(), p.info.text())
        h.click(TOP)


def a_no_pattern():
    p = panel()
    h.check("the body is taken", p.body is body() and p.body_label.text() == body().Label)
    h.check("no pattern: it says so", "has no pattern" in p.info.text(), p.info.text())
    h.task_button("Cancel")


# -- B ---------------------------------------------------------------------------------------------
def b_open():
    k.open_appearance()


def b_drop():
    k.drop_look("Mahogany", TOP)


def b_ok():
    h.task_button("OK")


def b_grain():
    groups, triangles = k.pattern_drawn(body().Tip)
    h.check("the grain is drawn on the body", groups == 1 and triangles == 12, (groups, triangles))
    state["span"] = span()
    # Mahogany's pattern repeats every 90 mm: 40 x 30 x 10 spans less than one repeat
    h.check("at its own size", state["span"] is not None and state["span"][0] < 1.0, state["span"])
    h.click_empty()
    # (mahogany's grain is fine and low in contrast: a few tenths against a flat 0.0)
    rough = k.roughness(TOP)
    h.check("the screen shows a texture", rough > state["flat"] + 0.25, (rough, state["flat"]))
    h.shot("B-mahogany")


# -- C ---------------------------------------------------------------------------------------------
def c_open():
    open_map()


def c_click():
    h.click(TOP)


def c_taken():
    p = panel()
    if not h.check("the body is taken", p is not None and p.body is body()):
        return
    h.check("no complaint: it has a pattern", p.info.text() == "", p.info.text())
    h.check("Projection Automatic", p.projection.currentText() == "Automatic")
    h.check("Automatic needs no Axis", not p.axis.isEnabled())
    h.check("Scale 100 %", abs(p.scale.value() - 100.0) < 1e-6, p.scale.value())
    k.type_field(p.scale, "50")


def c_half():
    now = span()
    h.check(
        "Scale 50 %: twice the repeats", near(now[0], 2 * state["span"][0]), (now, state["span"])
    )
    h.check("stored", stored_map().get("scale") == 50.0, stored_map())
    k.type_field(panel().rotation, "90")


def c_turned():
    now = span()
    h.check("Rotation 90 is stored", stored_map().get("rotation") == 90.0, stored_map())
    h.check(
        "the pattern turned",
        not near(now[0], 2 * state["span"][0]) or not near(now[1], 2 * state["span"][1]),
    )
    state["before_offset"] = k.pattern_uvs(body().Tip)[0]
    k.type_field(panel().offset_u, "10")


def c_offset():
    first = k.pattern_uvs(body().Tip)[0]
    h.check("Offset U 10 mm is stored", stored_map().get("offset_u") == 10.0, stored_map())
    h.check("the pattern slid", first != state["before_offset"], (first, state["before_offset"]))
    b.choose(panel().projection, "Planar")


def c_planar():
    p = panel()
    h.check("Planar needs an Axis", p.axis.isEnabled())
    h.check("Planar is stored", stored_map().get("projection") == "planar", stored_map())
    b.choose(p.axis, "X")


def c_axis():
    h.check("Axis X is stored", stored_map().get("axis") == "x", stored_map())
    w.click(panel().reset)


def c_reset():
    p = panel()
    h.check("Reset: no map stored", stored_map() == {}, stored_map())
    h.check(
        "Reset: Automatic, 100 %",
        p.projection.currentText() == "Automatic" and abs(p.scale.value() - 100) < 1e-6,
    )
    now = span()
    h.check(
        "Reset: the pattern as at the start",
        near(now[0], state["span"][0]) and near(now[1], state["span"][1]),
    )
    b.choose(p.projection, "Box")


def c_box():
    p = panel()
    h.check("Box needs no Axis", not p.axis.isEnabled())
    k.type_field(p.scale, "200")


def c_ok():
    now = span()
    h.check(
        "Scale 200 %: half the repeats", near(now[0], state["span"][0] / 2.0), (now, state["span"])
    )
    h.task_button("OK")


def c_kept():
    want = {"projection": "box", "scale": 200.0}
    got = {key: stored_map().get(key) for key in want}
    h.check("OK keeps the map", got == want, stored_map())


# -- D ---------------------------------------------------------------------------------------------
def d_undo():
    s.undo()


def d_undone():
    h.check("Undo: no map", stored_map() == {}, stored_map())
    h.check("Undo: the pattern at its own size", near(span()[0], state["span"][0]), span())


def d_redo():
    s.redo()


def d_redone():
    h.check("Redo: the map again", stored_map().get("scale") == 200.0, stored_map())
    h.check("Redo: the pattern follows", near(span()[0], state["span"][0] / 2.0), span())


def d_open():
    open_map()


def d_click():
    h.click(TOP)


def d_change():
    p = panel()
    h.check(
        "the dialog shows the body's map",
        p.projection.currentText() == "Box" and abs(p.scale.value() - 200) < 1e-6,
    )
    k.type_field(p.scale, "30")


def d_esc():
    h.check("30 % for now", stored_map().get("scale") == 30.0, stored_map())
    h.press(QtCore.Qt.Key_Escape)


def d_back():
    h.check("Esc closed the dialog", panel() is None)
    h.check("Esc: 200 % again", stored_map().get("scale") == 200.0, stored_map())
    h.check("and the pattern with it", near(span()[0], state["span"][0] / 2.0), span())


# -- E ---------------------------------------------------------------------------------------------
def opacity_menu(entry):
    tree, pos = t.row_point(body().Label)
    result = w.right_click_sub(tree.viewport(), pos, "Opacity Control", entry)
    h.check("browser menu > Opacity Control > %s" % entry, result["ok"], result)


def e_60():
    opacity_menu("60%")


def e_see_through():
    step = body().Tip
    mats = list(step.ViewObject.ShapeAppearance)
    h.check(
        "the body is 40 % see-through", abs(mats[0].Transparency - 0.4) < 0.01, mats[0].Transparency
    )
    h.check(
        "and still mahogany",
        k.same(tuple(mats[0].DiffuseColor[:3]), MAHOGANY),
        mats[0].DiffuseColor,
    )
    h.check(
        "its pattern is as see-through",
        abs(k.pattern_transparency(step) - 0.4) < 0.01,
        k.pattern_transparency(step),
    )


def e_100():
    opacity_menu("100%")


def e_solid():
    step = body().Tip
    h.check("solid again", abs(list(step.ViewObject.ShapeAppearance)[0].Transparency) < 0.01)
    h.check("its pattern too", abs(k.pattern_transparency(step)) < 0.01)
    h.check("still mahogany", k.same(k.shown_colors(step)[0], MAHOGANY), k.shown_colors(step)[:1])


# -- F ---------------------------------------------------------------------------------------------
def f_open():
    k.open_appearance()


def f_faces():
    b.choose(k.panel().apply_to, "Faces")


def f_drop():
    k.drop_look("Leather, brown", TOP)


def f_ok():
    h.task_button("OK")


def f_two():
    groups, triangles = k.pattern_drawn(body().Tip)
    h.check("two patterns on one body", groups == 2 and triangles == 12, (groups, triangles))
    h.click_empty()
    h.shot("F-leather-top")


# -- G ---------------------------------------------------------------------------------------------
def g_colors_on():
    state["rough"] = k.roughness(TOP)
    s.menu("INSPECT", "Display Component Colors")


def g_flat():
    from fission180 import component_colors_ui

    h.check("component colours are on", component_colors_ui.is_on())
    h.click_empty()
    rough = k.roughness(TOP)
    h.check(
        "the patterns are off under the colours",
        rough < 0.5 and state["rough"] > 1.0,
        (rough, state["rough"]),
    )


def g_colors_off():
    s.menu("INSPECT", "Display Component Colors")


def g_back():
    from fission180 import component_colors_ui

    h.check("component colours are off", not component_colors_ui.is_on())
    h.click_empty()
    h.check("the patterns show again", k.roughness(TOP) > 1.0, k.roughness(TOP))


# -- H ---------------------------------------------------------------------------------------------
def gear(entry):
    from fission180 import timeline_ui

    button = timeline_ui.widget().findChild(QtWidgets.QToolButton, "Fission180Timeline_settings")
    found = {}

    def read(menu):
        for action in menu.actions():
            if h.entry_text(action) == "Component Color Swatch":
                found["ticked"] = action.isChecked()

    ok = h.choose_from(
        lambda: w.click(button, w.center(button)),
        [entry] if entry else [],
        "the timeline settings menu",
        read=read,
    )
    return ok, found.get("ticked")


def swatch_rows():
    from fission180 import component_colors_ui

    return component_colors_ui.marks_shown()["rows"]


def h_swatch_on():
    ok, ticked = gear("Component Color Swatch")
    h.check("the gear's menu has Component Color Swatch", ok)
    h.check("it was not ticked", ticked is False, ticked)


def h_no_components():
    from fission180 import component_colors_ui

    h.check("the swatch is on", component_colors_ui.swatch_on())
    h.check("no component yet: nothing to mark", swatch_rows() == [], swatch_rows())


def h_component():
    h.click_empty()
    h.ribbon("New Component")


def h_name():
    cs.type_name("Lid")


def h_ok():
    h.task_button("OK")


def h_listed():
    rows = swatch_rows()
    names = [name for name, _color in rows]
    h.check(
        "the design's row and the component's row are marked in the browser",
        names == [App.ActiveDocument.Label, "Lid"],
        names,
    )
    h.check("each in a colour of its own", len(rows) == 2 and rows[0][1] != rows[1][1], rows)
    from fission180 import component_colors_ui

    steps = component_colors_ui.marks_shown()["steps"]
    h.check("and the steps in the timeline", bool(steps), steps)
    label = Gui.getMainWindow().findChild(QtWidgets.QLabel, "Fission180ComponentColorSwatch")
    h.check("no list in the 3D view any more", label is None or not label.isVisible())
    h.shot("H-swatch")
    _ok, ticked = gear(None)
    h.check("the gear's entry is ticked now", ticked is True, ticked)


def h_swatch_off():
    s.menu("INSPECT", "Component Color Swatch")


def h_hidden():
    from fission180 import component_colors_ui

    h.check("the swatch is off", not component_colors_ui.swatch_on())
    h.check("the marks are gone", swatch_rows() == [])


# -- I ---------------------------------------------------------------------------------------------
def i_save():
    path = os.path.join(h.OUT_DIR, "book_looks_map.FCStd")
    state["path"] = path
    App.ActiveDocument.saveAs(path)
    App.closeDocument(App.ActiveDocument.Name)


def i_reopen():
    App.openDocument(state["path"])
    h.fit()


def i_back():
    h.check("the map is in the file", stored_map().get("scale") == 200.0, stored_map())
    groups, triangles = k.pattern_drawn(body().Tip)
    h.check("both patterns are drawn again", groups == 2 and triangles == 12, (groups, triangles))
    h.click_empty()
    h.check("the screen shows the texture", k.roughness(TOP) > 1.0, k.roughness(TOP))


h.run(
    "book_looks_map",
    [s.new_design("LooksMap")]
    + s.box_steps("box", (0, 0, 40, 30), 10, V(6, -6, 0))
    + [
        a_open,
        a_waits,
        a_no_pattern,
        b_open,
        b_drop,
        b_ok,
        b_grain,
        c_open,
        c_click,
        c_taken,
        c_half,
        c_turned,
        c_offset,
        c_planar,
        c_axis,
        c_reset,
        c_box,
        c_ok,
        c_kept,
        d_undo,
        d_undone,
        d_redo,
        d_redone,
        d_open,
        d_click,
        d_change,
        d_esc,
        d_back,
        e_60,
        e_see_through,
        e_100,
        e_solid,
        f_open,
        f_faces,
        f_drop,
        f_ok,
        f_two,
        g_colors_on,
        g_flat,
        g_colors_off,
        g_back,
        h_swatch_on,
        h_no_components,
        h_component,
        h_name,
        h_ok,
        h_listed,
        h_swatch_off,
        h_hidden,
        i_save,
        i_reopen,
        i_back,
    ],
    paced_by="state",
)
