# SPDX-License-Identifier: LGPL-2.1-or-later
"""Several bodies selected before a body tool starts are all taken, each once (Luca,
2026-11-10: "if i select a group of bodies first, then use the move/copy tool, it just
selects a random body of the ones i selected instead of all of them"). A box round bodies
gives every face and edge it meets; each of them used to toggle its body, so a body with
an even number of them dropped out again. Only real input. Three 20 x 20 x 10 boxes: B1
x 0..20, B2 x 40..60, B3 x 80..100 (y 0..20).

  A  A window round the three bodies, M: Objects holds B1, B2 and B3; X Distance 10: all
     three move 10 in X; OK; Ctrl+Z puts all three back.
  B  The three rows clicked in the browser (Ctrl adds), the Move/Copy button: all three;
     Y Distance 5: all three move; OK; Ctrl+Z.
  C  B1's, B2's and B3's top faces clicked (Shift adds), M: all three; Esc: nothing moved.
  D  A window round the three, Combine: B1 is the target, B2 and B3 the tools. Esc.
  E  The three rows in the browser, Scale: all three are scaled (factor 2: each 8 x its
     volume). Esc: back.
  F  Interference with nothing selected: a window round the three picks all three; the same
     window again keeps all three (a box adds, never drops). Esc.
  G  Move/Copy with nothing selected: a click on B1, then a window round the three: all
     three, B1 kept. Esc.
  H  A window round the three, Physical Material, Aluminium: all three are aluminium. Esc.
  I  A window round the three, Appearance: Apply To stays Bodies (the window brought edges
     too: it means the bodies); "Glossy plastic, red": all three are red all over. Esc.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import selection_input as si
from Fission180Tests.gui import widget_input as w

V = App.Vector
st = {}
X0 = (0, 40, 80)  # where B1, B2, B3 start in x


def body(i):
    return s.bodies()[i]


def three():
    return list(s.bodies())


def top(i):
    return V(X0[i] + 10, 10, 10)


def panel():
    return s.panel()


def boxes():
    return [(round(b.Shape.BoundBox.XMin, 6), round(b.Shape.BoundBox.YMin, 6)) for b in s.bodies()]


def at_start():
    return boxes() == [(float(x), 0.0) for x in X0]


def window_round_all():
    """A window (left to right) round the three bodies, as a person drags it."""
    corners = []
    for x0 in X0:
        corners += [V(x0, 0, 0), V(x0 + 20, 20, 10), V(x0, 20, 10), V(x0 + 20, 0, 0)]
    si.box_around(corners, margin=25)


def rows_selected():
    """The three bodies' rows clicked in the browser, Ctrl adding the second and third."""
    h.click_empty()
    s.click_browser_row(body(0).Label)
    s.click_browser_row(body(1).Label, QtCore.Qt.ControlModifier)
    s.click_browser_row(body(2).Label, QtCore.Qt.ControlModifier)


def selected_bodies():
    from fission180 import bodies

    found = []
    for sel in Gui.Selection.getSelectionEx():
        b = bodies.body_of(sel.Object)
        if b is not None and b not in found:
            found.append(b)
    return found


def setup():
    from fission180 import commands, extrude, sketch_ui

    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("BodyPickMany")
    first = commands.ensure_body()
    planes = sketch_ui.origin_planes(first)
    for i, x0 in enumerate(X0):
        sketch = sketch_ui.create_sketch(first, (planes["XY_Plane"], ""))
        h.draw_rectangle(sketch, x0, 0, x0 + 20, 20)
        extrude.make(first, sketch, {"distance": 10.0, "operation": "new_body" if i else "join"})
        App.ActiveDocument.recompute()
    Gui.Selection.clearSelection()
    h.fit()
    h.check(
        "three boxes",
        len(s.bodies()) == 3 and all(s.close(s.volume(b), 4000) for b in s.bodies()),
        [s.volume(b) for b in s.bodies()],
    )
    h.check("at their places", at_start(), boxes())


# -- A: a window, then M ------------------------------------------------------------------------
def a_window():
    h.click_empty()
    h.fit()
    window_round_all()


def a_press_m():
    entries = len(si.selected())
    h.check("A the window selected the three bodies' faces and edges", selected_bodies() == three() and entries >= 3, (selected_bodies(), entries))
    st["entries"] = sum(len(sel.SubElementNames) for sel in Gui.Selection.getSelectionEx())
    h.press("m")


def a_taken():
    p = panel()
    taken = p.options["bodies"] if p is not None and p.title == "Move/Copy" else None
    h.check(
        "A Move/Copy holds all three bodies (from %d faces and edges)" % st.get("entries", 0),
        taken == three(),
        taken,
    )
    if p is not None:
        h.check("A the Objects box says 3 bodies", "3" in p.fields["objects"].button.text(), p.fields["objects"].button.text())
        s.type_value(p.distance_fields[0].widget, "10")


def a_moved():
    h.check(
        "A X Distance 10: all three moved",
        boxes() == [(float(x + 10), 0.0) for x in X0],
        boxes(),
    )
    h.shot("A-move-three-bodies")
    h.task_button("OK")


def a_ok():
    h.check("A OK closed the dialog", panel() is None, panel())
    h.check("A all three stay moved", boxes() == [(float(x + 10), 0.0) for x in X0], boxes())
    h.press(QtCore.Qt.Key_Z, QtCore.Qt.ControlModifier)


def a_undone():
    h.check("A Ctrl+Z: all three back (one undo step)", at_start(), boxes())


# -- B: the browser rows, then the Move/Copy button ------------------------------------------------
def b_rows():
    rows_selected()


def b_button():
    h.check("B the three rows are selected", selected_bodies() == three(), selected_bodies())
    h.ribbon("Move/Copy")


def b_taken():
    p = panel()
    taken = p.options["bodies"] if p is not None and p.title == "Move/Copy" else None
    h.check("B Move/Copy holds all three bodies", taken == three(), taken)
    if p is not None:
        s.type_value(p.distance_fields[1].widget, "5")


def b_moved():
    h.check("B Y Distance 5: all three moved", boxes() == [(float(x), 5.0) for x in X0], boxes())
    h.task_button("OK")


def b_ok():
    h.check("B all three stay moved", boxes() == [(float(x), 5.0) for x in X0], boxes())
    h.press(QtCore.Qt.Key_Z, QtCore.Qt.ControlModifier)


def b_undone():
    h.check("B Ctrl+Z: all three back", at_start(), boxes())


# -- C: Shift + clicks on faces, then M ----------------------------------------------------------
def c_clicks():
    h.click_empty()
    h.fit()
    h.click(top(0))
    h.click(top(1), QtCore.Qt.ShiftModifier)
    h.click(top(2), QtCore.Qt.ShiftModifier)


def c_press_m():
    h.check("C three faces selected", selected_bodies() == three(), si.selected())
    h.press("m")


def c_taken():
    p = panel()
    taken = p.options["bodies"] if p is not None and p.title == "Move/Copy" else None
    h.check("C Move/Copy holds all three bodies", taken == three(), taken)
    h.press(QtCore.Qt.Key_Escape)


def c_cancelled():
    h.check("C Esc: closed, nothing moved", panel() is None and at_start(), (panel(), boxes()))


# -- D: Combine -----------------------------------------------------------------------------------
def d_window():
    h.click_empty()
    window_round_all()


def d_combine():
    h.check("D the window selected the three", selected_bodies() == three(), selected_bodies())
    h.ribbon("Combine")


def d_taken():
    p = panel()
    ok = p is not None and p.title == "Combine"
    h.check("D Combine: B1 is the target", ok and p.options["target"] is body(0), ok and p.options["target"])
    h.check("D B2 and B3 are the tools", ok and p.options["tools"] == three()[1:], ok and p.options["tools"])
    h.shot("D-combine-three")
    h.press(QtCore.Qt.Key_Escape)


# -- E: Scale -------------------------------------------------------------------------------------
def e_rows():
    h.wait_for(lambda: panel() is None, "Combine to close")
    rows_selected()


def e_scale():
    h.check("E the three rows are selected", selected_bodies() == three(), selected_bodies())
    h.ribbon("Scale")


def e_taken():
    p = panel()
    ok = p is not None and p.title == "Scale"
    got = ([p.body] + [m.body for m in p.members]) if ok else None
    h.check("E Scale takes all three bodies", got == three(), got)
    if ok:
        h.check("E Entities says 3 selected", p.entities.button.text() == "3 selected", p.entities.button.text())
        ui.type_into(p.factor.widget, "2")


def e_scaled():
    vols = [round(s.volume(b)) for b in s.bodies()]
    h.check("E factor 2: all three are 8 x bigger", vols == [32000] * 3, vols)
    h.shot("E-scale-three")
    h.press(QtCore.Qt.Key_Escape)


def e_cancelled():
    h.wait_for(lambda: panel() is None, "Scale to close")
    vols = [round(s.volume(b)) for b in s.bodies()]
    h.check("E Esc: back to their size", vols == [4000] * 3, vols)


# -- F: Interference, a window inside the dialog ---------------------------------------------
def f_open():
    h.click_empty()
    s.menu("INSPECT", "Interference")


def f_window():
    p = panel()
    h.check("F Interference open, nothing picked", p is not None and p.title == "Interference" and not p.picked, p and p.picked)
    window_round_all()


def f_three():
    p = panel()
    picked = list(p.picked) if p is not None else None
    h.check("F a window picks all three", picked is not None and sorted(b.Name for b in picked) == sorted(b.Name for b in three()), picked)
    window_round_all()


def f_again():
    p = panel()
    picked = list(p.picked) if p is not None else None
    h.check("F the same window again keeps all three", picked is not None and len(picked) == 3, picked)
    h.press(QtCore.Qt.Key_Escape)


# -- G: Move/Copy, a click then a window inside the dialog ---------------------------------------
def g_open():
    h.wait_for(lambda: panel() is None, "Interference to close")
    h.click_empty()
    h.press("m")


def g_click():
    p = panel()
    h.check("G Move/Copy open, nothing picked", p is not None and p.title == "Move/Copy" and not p.options["bodies"], p and p.options["bodies"])
    h.click(top(0))


def g_window():
    p = panel()
    h.check("G B1 picked", p is not None and p.options["bodies"] == [body(0)], p and p.options["bodies"])
    window_round_all()


def g_three():
    p = panel()
    taken = p.options["bodies"] if p is not None else None
    h.check("G the window adds B2 and B3 and keeps B1", taken is not None and sorted(b.Name for b in taken) == sorted(b.Name for b in three()), taken)
    h.press(QtCore.Qt.Key_Escape)


# -- H: Physical Material ----------------------------------------------------------------------------
def h_window():
    h.wait_for(lambda: panel() is None, "Move/Copy to close")
    h.check("G Esc: nothing moved", at_start(), boxes())
    h.click_empty()
    window_round_all()


def h_material():
    h.check("H the window selected the three", selected_bodies() == three(), selected_bodies())
    s.menu("MODIFY", "Physical Material")


def h_pick():
    p = panel()
    ok = p is not None and p.title == "Physical Material"
    h.check("H all three wait for the material", ok and p.pending == three(), ok and p.pending)
    item = p.item_for("Aluminium") if ok else None
    if h.check("H the library has Aluminium", item is not None):
        p.library.scrollToItem(item)
        w.click(p.library.viewport(), p.library.visualItemRect(item).center())


def h_assigned():
    names = [b.ShapeMaterial.Name for b in s.bodies()]
    h.check("H all three are aluminium", names == ["Aluminum-Generic"] * 3, names)
    h.press(QtCore.Qt.Key_Escape)


def i_window():
    h.wait_for(lambda: panel() is None, "Physical Material to close")
    names = [b.ShapeMaterial.Name for b in s.bodies()]
    h.check("H Esc: the old material back", "Aluminum-Generic" not in names, names)
    h.click_empty()
    window_round_all()


def i_appearance():
    h.check("I the window selected the three", selected_bodies() == three(), selected_bodies())
    s.menu("MODIFY", "Appearance")


def i_pick():
    p = panel()
    ok = p is not None and p.title == "Appearance"
    h.check("I Apply To stays Bodies", ok and p.apply_to.currentData() == "bodies", ok and p.apply_to.currentText())
    item = p.item_for("Glossy plastic, red") if ok else None
    if h.check("I the library has red plastic", item is not None):
        p.library.scrollToItem(item)
        w.click(p.library.viewport(), p.library.visualItemRect(item).center())


def colours_of(b):
    """Diffuse colours on screen, per face, of a body's end step."""
    try:
        return [tuple(round(c, 3) for c in m.DiffuseColor[:3]) for m in b.Tip.ViewObject.ShapeAppearance]
    except Exception:
        return []


def red(b):
    cols = colours_of(b)
    return bool(cols) and all(abs(c[0] - 0.80) < 0.01 and c[1] < 0.1 and c[2] < 0.1 for c in cols)


def i_red():
    h.check("I all three are red all over", all(red(b) for b in s.bodies()), [colours_of(b)[:2] for b in s.bodies()])
    h.shot("I-appearance-three-red")
    h.press(QtCore.Qt.Key_Escape)


def end():
    h.wait_for(lambda: panel() is None, "Appearance to close")
    h.check("I Esc: none is red any more", not any(red(b) for b in s.bodies()), [colours_of(b)[:1] for b in s.bodies()])


def cleanup():
    for name in list(App.listDocuments()):
        Gui.getDocument(name).Modified = False
        App.closeDocument(name)


h.run(
    "body_pick_many",
    [
        setup,
        a_window,
        a_press_m,
        a_taken,
        a_moved,
        a_ok,
        a_undone,
        b_rows,
        b_button,
        b_taken,
        b_moved,
        b_ok,
        b_undone,
        c_clicks,
        c_press_m,
        c_taken,
        c_cancelled,
        d_window,
        d_combine,
        d_taken,
        e_rows,
        e_scale,
        e_taken,
        e_scaled,
        e_cancelled,
        f_open,
        f_window,
        f_three,
        f_again,
        g_open,
        g_click,
        g_window,
        g_three,
        h_window,
        h_material,
        h_pick,
        h_assigned,
        i_window,
        i_appearance,
        i_pick,
        i_red,
        end,
        cleanup,
    ],
    paced_by="state",
)
