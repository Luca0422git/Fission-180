# SPDX-License-Identifier: LGPL-2.1-or-later
"""A second click on a selected browser row's name renames it in place (Luca, 2026-11-02:
"a second click on a body in the browser should allow me to rename the body. same with
sketches and assemblies"). Fusion and Windows Explorer: click once to select, click the
selected row's name again (not a double-click) and the name field opens, like Rename.
Like Qt's own SelectedClicked trigger, the field opens once the double-click time has
passed; a double-click instead keeps doing its own thing. Only real input.

A 40 x 30 x 10 box (Body: Sketch 1, Extrude 1).

  A  Body: the first click on its name selects it, no field. The second click: no field at
     once (the double-click time runs), then the name field over the row, holding "Body"
     selected. The 3D view takes the keyboard a moment (as after a selection change): the
     field takes it back, and "Bracket" typed then replaces the name (Enter): the body is
     Bracket, the browser shows it, one undo step.
  B  Sketch 1: two clicks rename it to Profile; the timeline shows Profile too. Two clicks
     again, Esc: the name stays.
  C  The sketch picked in the timeline (its row is selected from there): one click on the
     row only selects; the next one opens the field (Esc).
  D  A double-click on the selected sketch's row edits the sketch, no name field (its first
     click had started one: the double-click drops it). Finish Sketch: still no field.
  E  No field for a click on the eye (it hides the sketch), on the icon, after a drag of the
     selected body's row, nor with two rows selected (Ctrl+click).
  F  F2 and right-click > Rename still open the field (Esc / a new name).
  G  A component (New Component, Arm): two clicks rename it to Lever, the timeline's step
     follows. A click on its activate ring after selecting it activates, no field.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from SciForgeTests.gui import blend_steps as b
from SciForgeTests.gui import component_steps as cs
from SciForgeTests.gui import harness as h
from SciForgeTests.gui import timeline_input as t
from SciForgeTests.gui import widget_input as w

s = {}


def browser():
    from sciforge import browser_ui

    return browser_ui.widget()


def field():
    """The name field open in the browser, or None."""
    editor = browser()._renaming
    if editor is None or not editor.is_open():
        return None
    return editor.field if editor.field.isVisible() else None


def field_open():
    return field() is not None


def no_field():
    return field() is None and not browser()._slow_timer.isActive()


def click_at(label, where="name"):
    """A real click on a row: its name (where the label is), its icon or its eye."""
    tree = t.tree()

    def point_of(item):
        rect = tree.visualRect(tree.indexFromItem(item, 1))
        if where == "icon":
            return QtCore.QPoint(rect.left() + 30, rect.center().y())
        if where == "eye":
            return tree.eye_point(item)
        return tree.label_point(item)

    return w.click_item(tree, lambda: t.tree().row(label), point_of, what="the row %r" % label)


def double_click_name(label):
    tree = t.tree()
    return w.click_item(
        tree, lambda: t.tree().row(label), tree.label_point, double=True, what="the row %r" % label
    )


def second_click(label):
    """The second click on a selected row: no field yet (the double-click time runs)."""
    click_at(label)
    s["at_once"] = field()
    s["waiting"] = browser()._slow_timer.isActive()


def opened_after_wait(where, text):
    h.check("%s: no field at once (the double-click time runs)" % where, s["at_once"] is None)
    h.check("%s: ... it was waiting for it" % where, s["waiting"])
    f = field()
    if h.check("%s: the name field opened" % where, f is not None):
        h.check("%s: it holds %r, selected" % (where, text), f.text() == text, f.text())
        h.check("%s: ... all of it selected" % where, f.selectedText() == text, f.selectedText())


def selected():
    """The names of the selected rows (without the active body's mark)."""
    return [i.data(1, QtCore.Qt.UserRole)["label"] for i in t.tree().selectedItems()]


def body():
    return App.ActiveDocument.getObject("Body")


def sketch():
    return App.ActiveDocument.getObject("Sketch")


# -- A: the body -------------------------------------------------------------------------------
def a_first():
    click_at("Body")


def a_selected_only():
    h.check("A: the first click selects the body's row", selected() == ["Body"], selected())
    h.check("A: ... and opens no field", no_field())
    second_click("Body")


a_selected_only.done = field_open
a_selected_only.done_what = "the name field to open after the second click"


def a_field():
    opened_after_wait("A", "Body")
    # the 3D view takes the keyboard a moment, as after a selection change (MEMORY, "Typing
    # right after Rename"): the field keeps its selection and takes the keyboard back
    h.gl_widget().setFocus()


a_field.done = lambda: field() is not None and field().hasFocus()
a_field.done_what = "the name field to take the keyboard back"


def a_type():
    f = field()
    h.check("A: the field kept its selection", f.selectedText() == "Body", f.selectedText())
    QtTest.QTest.keyClicks(QtWidgets.QApplication.focusWidget(), "Bracket")
    QtTest.QTest.keyClick(QtWidgets.QApplication.focusWidget(), QtCore.Qt.Key_Return)


def a_renamed():
    h.check("A: the body is Bracket", body().Label == "Bracket", body().Label)
    h.check("A: the browser shows it", t.tree().row("Bracket") is not None, t.labels())
    h.check("A: the field closed", field() is None)
    names = App.ActiveDocument.UndoNames
    h.check("A: one undo step, Rename", names[:1] == ["Rename Body"], names[:3])


# -- B: the sketch -------------------------------------------------------------------------------
def b_first():
    click_at("Sketch 1")


def b_second():
    h.check("B: the first click opens no field", no_field())
    second_click("Sketch 1")


b_second.done = field_open
b_second.done_what = "the sketch's name field to open"


def b_type():
    opened_after_wait("B", "Sketch 1")
    f = field()
    if f is not None:
        w.type_text(f, "Profile")
        w.key(f, QtCore.Qt.Key_Return)


def b_renamed():
    h.check("B: the sketch is Profile", sketch().Label == "Profile", sketch().Label)
    h.check("B: the timeline shows Profile", "Profile" in t.titles(), t.titles())
    h.check("B: the browser too", t.tree().row("Profile") is not None, t.labels())
    click_at("Profile")  # (it is still the last click: this one is a second click again)


b_renamed.done = field_open
b_renamed.done_what = "the field again on a further click"


def b_escape():
    w.key(field(), QtCore.Qt.Key_Escape)


def b_kept():
    h.check("B: Esc keeps the name", sketch().Label == "Profile", sketch().Label)
    h.check("B: the field closed", field() is None)


# -- C: selected from the timeline ----------------------------------------------------------------
def c_timeline():
    h.click_empty()


def c_pick():
    t.click("Profile")


def c_row_selected():
    h.check(
        "C: the timeline's pick selects the sketch's row",
        selected() == ["Profile"],
        selected(),
    )
    click_at("Profile")


def c_only_selects():
    h.check("C: one click on a row selected elsewhere only selects", no_field())
    click_at("Profile")


c_only_selects.done = field_open
c_only_selects.done_what = "the field on the next click"


def c_escape():
    w.key(field(), QtCore.Qt.Key_Escape)


# -- D: a double-click edits ----------------------------------------------------------------------
def d_double():
    h.check("D: the field closed", field() is None)
    h.check("D: the row is still selected", selected() == ["Profile"], selected())
    double_click_name("Profile")


d_double.done = lambda: h.in_sketch() is not None
d_double.done_what = "the sketch to open for editing"


def d_editing():
    h.check("D: the double-click edits the sketch", h.in_sketch() is sketch())
    h.check("D: ... and opens no name field", no_field())
    h.ribbon("Finish Sketch")


d_editing.done = lambda: h.in_sketch() is None
d_editing.done_what = "the sketch to close"


def d_after():
    h.check("D: still no name field after Finish Sketch", no_field())
    h.check("D: the name is unchanged", sketch().Label == "Profile", sketch().Label)


# -- E: what must not rename ---------------------------------------------------------------------
def e_select():
    click_at("Profile")


def e_eye():
    s["shown"] = t.shown(sketch())
    click_at("Profile", "eye")


def e_eye_done():
    h.check("E: the eye click hides or shows the sketch", t.shown(sketch()) != s["shown"])
    h.check("E: ... and opens no field", no_field())
    click_at("Profile", "eye")


def e_icon():
    h.check("E: the eye again", t.shown(sketch()) == s["shown"])
    click_at("Profile")


def e_icon_click():
    click_at("Profile", "icon")


def e_icon_done():
    h.check("E: a click on the icon opens no field", no_field())
    click_at("Bracket")


def e_drag():
    tree = t.tree()
    item = tree.row("Bracket")
    start = tree.label_point(item)
    s["container"] = cs.container_label(body())
    # dragged down, to an empty spot under the rows (no component there to drop it on)
    end = tree.viewport().mapToGlobal(QtCore.QPoint(start.x(), tree.viewport().height() - 6))
    w.drag(tree.viewport(), start, end)


def e_drag_done():
    h.check("E: a drag of the selected body opens no field", no_field())
    h.check("E: ... and moves nothing", cs.container_label(body()) == s["container"])
    click_at("Bracket")


def e_two():
    tree = t.tree()
    w.click_item(
        tree,
        lambda: t.tree().row("Profile"),
        tree.label_point,
        modifiers=QtCore.Qt.ControlModifier,
        what="the row 'Profile'",
    )


def e_two_selected():
    h.check("E: Ctrl+click selects both rows", sorted(selected()) == ["Bracket", "Profile"], selected())
    click_at("Profile")  # (a plain click: Profile alone, a first click)


def e_two_done():
    h.check("E: a click among several selected rows opens no field", no_field())
    h.check("E: ... it selects that row", selected() == ["Profile"], selected())


# -- F: F2 and Rename still work -----------------------------------------------------------------
def f_f2():
    w.key(t.tree(), QtCore.Qt.Key_F2)


f_f2.done = field_open
f_f2.done_what = "F2 to open the name field"


def f_f2_escape():
    h.check("F: F2 opens the field", field() is not None and field().text() == "Profile")
    w.key(field(), QtCore.Qt.Key_Escape)


def f_menu():
    h.check("F: Esc closed it", field() is None)
    cs.rename_row("Bracket", "Plate")


def f_menu_done():
    h.check("F: right-click > Rename still renames", body().Label == "Plate", body().Label)
    h.check("F: no field left", no_field())


# -- G: a component ------------------------------------------------------------------------------
def g_new():
    h.ribbon("New Component")


def g_dialog():
    h.check("G: New Component dialog", cs.new_component_panel() is not None)
    cs.type_name("Arm")


def g_ok():
    h.task_button("OK")


def g_first():
    h.check("G: Arm made", cs.component("Arm") is not None)
    click_at("Arm")


def g_second():
    h.check("G: the first click opens no field", no_field())
    second_click("Arm")


g_second.done = field_open
g_second.done_what = "the component's name field to open"


def g_type():
    opened_after_wait("G", "Arm")
    f = field()
    if f is not None:
        w.type_text(f, "Lever")
        w.key(f, QtCore.Qt.Key_Return)


def g_renamed():
    part = cs.component("Lever")
    h.check("G: the component is Lever", part is not None, [p.Label for p in cs.components()])
    h.check("G: the timeline's step follows", "Lever" in t.titles(), t.titles())
    cs.click_radio(App.ActiveDocument.Label)  # the design (root) active


def g_root():
    h.check("G: the root is active", cs.active_label() is None, cs.active_label())
    click_at("Lever")


def g_ring():
    h.check("G: Lever selected", selected() == ["Lever"], selected())
    tree = t.tree()
    w.click_item(tree, lambda: t.tree().row("Lever"), tree.radio_point, what="Lever's ring")


def g_activated():
    h.check("G: the ring of the selected row activates Lever", cs.active_label() == "Lever")
    h.check("G: ... and opens no field", no_field())
    t.no_popups("the end")
    h.shot("G-end")


STEPS = b.box_steps("SecondClick") + [
    a_first,
    a_selected_only,
    a_field,
    a_type,
    a_renamed,
    b_first,
    b_second,
    b_type,
    b_renamed,
    b_escape,
    b_kept,
    c_timeline,
    c_pick,
    c_row_selected,
    c_only_selects,
    c_escape,
    d_double,
    d_editing,
    d_after,
    e_select,
    e_eye,
    e_eye_done,
    e_icon,
    e_icon_click,
    e_icon_done,
    e_drag,
    e_drag_done,
    e_two,
    e_two_selected,
    e_two_done,
    f_f2,
    f_f2_escape,
    f_menu,
    f_menu_done,
    g_new,
    g_dialog,
    g_ok,
    g_first,
    g_second,
    g_type,
    g_renamed,
    g_root,
    g_ring,
    g_activated,
]

def watched(steps):
    """t.watched (the Report view and FreeCAD's balloons after each step), keeping each
    step's done / ready (t.watched's wrappers leave them out)."""
    wrapped = t.watched(steps)
    for one, run in zip(steps, wrapped):
        for attr in ("done", "done_what", "ready", "ready_what", "timeout_s"):
            if hasattr(one, attr):
                setattr(run, attr, getattr(one, attr))
    return wrapped


h.run("browser_second_click", watched(STEPS), paced_by="state")
