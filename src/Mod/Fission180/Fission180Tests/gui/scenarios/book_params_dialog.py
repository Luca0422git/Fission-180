# SPDX-License-Identifier: LGPL-2.1-or-later
"""Wave 7 (the book parity report), params: the Parameters dialog, with real clicks and keys.

The book's Metric Bolt and Prototype Drone start with MODIFY > Change Parameters and a table
of user parameters made with "+". In 0.1.0-beta.3.3.9 the "+" only showed "'bool' object has
no attribute 'strip'" (bug 1), "-2.5" for a length became 0 (bug 4), and the book's
`min(100;max(45;Arm_Length))` gave 0 mm with the reason only in the log.

  A  MODIFY > Change Parameters; the "+ User Parameter" button shows its words (it was a
     blank white square); a real click opens Add User Parameter; Name Head_Diam, Expression
     8.5, OK: Head_Diam = 8.5 mm, listed, a favourite.
  B  Refusals said in red in the Add box, nothing made: a unit as the name (mm), the name
     again, an expression that is no value (Head_Diam +), an unknown name with a hint.
  C  Thickness = -2.5 (bug 4): it holds -2.5 mm. Arm_Length = 53, then Limits_Arm_Length =
     min(100;max(45;Arm_Length)) (the book's line, no units): 53 mm, shown with its units
     added the way Fusion shows it; the Add box shows the value while typing.
  D  Arm_Length's Expression typed 40, 110, 53 in the table: the limit follows (45, 100, 53).
     `Arm_Length + 5` and `2 * (Head_Diam + 3)` typed for Limits: 58 and 23 mm.
  E  A parameter in inches (Unit: in, Expression 2): 50.8 mm, shown "2 in"; W, h and t are
     fine as names (FreeCAD reads them as units: Watt, hour, tonne).
  F  Rename: Arm_Length typed over with Arm: the limit's formula follows.
  G  Delete: Arm is used by Limits_Arm_Length: refused, in red, with what uses it. An unused
     one goes. Nothing selected: said.
  H  The star: a click on Head_Diam's star takes it out of Favorites, another puts it back.
     The filter box shows only the rows that hold the typed text.
  I  OK; Ctrl+Z takes the whole edit back in one step, Ctrl+Y brings it again; Cancel of a
     second visit leaves the design as it was.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import timeline_input as ti
from Fission180Tests.gui import widget_input as w

s = {}


def doc():
    return App.ActiveDocument


def dialog():
    from fission180 import parameters_ui

    d = parameters_ui.ParametersDialog.last
    return d if d is not None and d.isVisible() else None


def adder():
    d = dialog()
    a = d.adder if d is not None else None
    try:
        return a if a is not None and a.isVisible() else None
    except RuntimeError:
        return None


def value(name):
    from fission180 import parameters, parameters_core

    held = getattr(parameters.container(doc()), parameters_core.prop_name(name))
    return held.Value if hasattr(held, "Value") else float(held)


def row(name):
    from fission180 import parameters

    found = [r for r in parameters.user_rows(doc()) if r["name"] == name]
    return found[0] if found else None


def names():
    from fission180 import parameters

    return list(parameters.own_names(doc()))


def table_row(name):
    d = dialog()
    for r in range(d.user.rowCount()):
        if d.user.item(r, 0).data(QtCore.Qt.UserRole) == name:
            return r
    return -1


def edit_cell(view, rect, text):
    """Double-click a table cell, replace its text by typing, press Enter."""
    view.window().activateWindow()
    view.window().raise_()
    QtWidgets.QApplication.processEvents()
    w.double_click(view.viewport(), rect.center())
    editors = [e for e in view.findChildren(QtWidgets.QLineEdit) if e.isVisible()]
    h.check("an editor opened in the cell", bool(editors), rect)
    if not editors:
        return
    editor = editors[0]
    QtTest.QTest.keyClick(editor, QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
    QtTest.QTest.keyClicks(editor, text)
    QtTest.QTest.keyClick(editor, QtCore.Qt.Key_Return)
    QtWidgets.QApplication.processEvents()


def type_expression(name, text):
    d = dialog()
    r = table_row(name)
    h.check("%s is in the table" % name, r >= 0)
    if r >= 0:
        edit_cell(d.user, d.user.visualItemRect(d.user.item(r, 2)), text)


def add(name, expression, unit=None, ok=True):
    """The steps that add one parameter through the Add box, with real input."""

    def open_box():
        w.click(dialog().add_button)

    open_box.done = lambda: adder() is not None
    open_box.done_what = "the Add User Parameter box is open"
    open_box.__name__ = "add_%s_open" % name

    def fill():
        a = adder()
        si.type_into(a.name, name, enter=False)
        if unit is not None:
            from Fission180Tests.gui import dialog_input as di

            di.choose(a.unit, unit)
        si.type_into(a.expression, expression, enter=False)
        s["preview"] = a.value.text()
        if ok:
            w.click(a.buttons.button(QtWidgets.QDialogButtonBox.Ok))

    fill.__name__ = "add_%s_fill" % name
    if ok:
        fill.done = lambda: adder() is None
        fill.done_what = "the Add User Parameter box closed"
    return [open_box, fill]


# == A: the + button ===============================================================================
def setup():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("BookParams")
    h.fit()


def a_open():
    si.menu_item("MODIFY", "Change Parameters")


a_open.done = lambda: dialog() is not None
a_open.done_what = "the Parameters dialog is open"


def a_button():
    d = dialog()
    b = d.add_button
    h.check("A: the button says what it does", b.text() == "+ User Parameter", b.text())
    # (bug 1's second half: a blank white square. The words must be readable on the button)
    palette = b.palette()
    face = palette.color(b.backgroundRole())
    words = palette.color(b.foregroundRole())
    contrast = abs(face.lightness() - words.lightness())
    h.check("A: its words stand out from its face", contrast > 60, (face.name(), words.name()))
    h.check("A: no user parameter yet", names() == [], names())


def a_check():
    h.check("A: Head_Diam is made", "Head_Diam" in names(), names())
    h.check("A: it is 8.5 mm", abs(value("Head_Diam") - 8.5) < 1e-9, value("Head_Diam"))
    r = row("Head_Diam")
    h.check("A: shown as 8.5 mm", r is not None and r["shown"] == "8.5 mm", r)
    h.check("A: a favourite, like Fusion's new user parameter", r is not None and r["favorite"])
    d = dialog()
    h.check("A: no complaint", d.message.text() == "", d.message.text())
    h.check("A: listed in the table", table_row("Head_Diam") >= 0)
    favs = [d.favorites.item(i, 0).text().strip() for i in range(d.favorites.rowCount())]
    h.check("A: listed under Favorites", favs == ["Head_Diam"], favs)
    h.shot("A-added")


# == B: refusals ===================================================================================
def b_open():
    w.click(dialog().add_button)


b_open.done = lambda: adder() is not None
b_open.done_what = "the Add User Parameter box is open"


def refusal(name, expression, words, tag):
    def step():
        a = adder()
        si.type_into(a.name, name, enter=False)
        si.type_into(a.expression, expression, enter=False)
        w.click(a.buttons.button(QtWidgets.QDialogButtonBox.Ok))
        a = adder()
        h.check("B %s: the box stays open" % tag, a is not None)
        text = a.message.text() if a is not None else ""
        h.check("B %s: and says why (%s)" % (tag, words), words in text, text)
        h.check("B %s: nothing was made" % tag, names() == ["Head_Diam"], names())

    step.__name__ = "b_refuse_" + tag
    return step


def b_cancel():
    a = adder()
    w.click(a.buttons.button(QtWidgets.QDialogButtonBox.Cancel))


b_cancel.done = lambda: adder() is None
b_cancel.done_what = "the Add User Parameter box closed"


# == C: a negative length, the book's min / max ====================================================
def c_negative_check():
    h.check(
        "C: Thickness is -2.5 mm (bug 4)", abs(value("Thickness") + 2.5) < 1e-9, value("Thickness")
    )
    r = row("Thickness")
    h.check("C: shown as -2.5 mm", r is not None and r["shown"] == "-2.5 mm", r)


def c_limits_check():
    h.check(
        "C: the Add box showed the value while typing",
        s.get("preview") == "53 mm",
        s.get("preview"),
    )
    h.check(
        "C: the limit is 53 mm",
        abs(value("Limits_Arm_Length") - 53) < 1e-9,
        value("Limits_Arm_Length"),
    )
    r = row("Limits_Arm_Length")
    shown = r["shown"] if r is not None else ""
    h.check(
        "C: the formula is kept, its bare numbers in the design's units",
        shown.replace(" ", "") == "min(100mm;max(45mm;Arm_Length))",
        shown,
    )
    d = dialog()
    h.check("C: no complaint", d.message.text() == "", d.message.text())


# == D: the limits follow ==========================================================================
def typed(name, text, tag):
    def step():
        type_expression(name, text)

    step.__name__ = "d_type_" + tag
    return step


def limit_is(expected, tag):
    def step():
        got = value("Limits_Arm_Length")
        h.check("D %s: the limit is %s mm" % (tag, expected), abs(got - expected) < 1e-9, got)
        d = dialog()
        h.check("D %s: no complaint" % tag, d.message.text() == "", d.message.text())

    step.__name__ = "d_check_" + tag
    return step


def d_formula_text():
    r = row("Limits_Arm_Length")
    shown = (r["shown"] if r is not None else "").replace(" ", "")
    h.check(
        "D: `2 * (Head_Diam + 3)` is kept with the unit added", shown == "2*(Head_Diam+3mm)", shown
    )


# == E: other units, names FreeCAD reads as units ==================================================
def e_check():
    h.check(
        "E: Inch_Size is 2 in = 50.8 mm", abs(value("Inch_Size") - 50.8) < 1e-9, value("Inch_Size")
    )
    r = row("Inch_Size")
    h.check(
        "E: shown in its own unit", r is not None and r["shown"] == "2 in" and r["unit"] == "in", r
    )
    for name, expected in (("W", 12.0), ("h", 7.0), ("t", 1.5)):
        h.check(
            "E: %s holds %s mm" % (name, expected), abs(value(name) - expected) < 1e-9, value(name)
        )
    h.check(
        "E: a formula of them works (Sum = W + h * 2 + t)",
        abs(value("Sum") - (12 + 14 + 1.5)) < 1e-9,
        value("Sum"),
    )
    r = row("Sum")
    h.check("E: and reads as typed", r is not None and r["shown"].replace(" ", "") == "W+h*2+t", r)


# == F: rename =====================================================================================
def f_rename():
    d = dialog()
    r = table_row("Arm_Length")
    edit_cell(d.user, d.user.visualItemRect(d.user.item(r, 0)), "Arm")


def f_check():
    h.check("F: renamed", "Arm" in names() and "Arm_Length" not in names(), names())
    r = row("Limits_Arm_Length")
    h.check(
        "F: the formula that named it follows",
        r is not None and "Arm" in r["shown"] and "Arm_Length" not in r["shown"],
        r,
    )
    h.check(
        "F: its value is unchanged",
        abs(value("Limits_Arm_Length") - 58) < 1e-9,
        value("Limits_Arm_Length"),
    )
    d = dialog()
    h.check("F: no complaint", d.message.text() == "", d.message.text())
    order = names()
    h.check("F: it keeps its place in the list", order.index("Arm") == 2, order)


# == G: delete =====================================================================================
def g_none_selected():
    d = dialog()
    d.user.setCurrentCell(-1, -1)
    w.click(d.remove_button)
    h.check(
        "G: nothing selected: said",
        "Click the user parameter" in d.message.text(),
        d.message.text(),
    )


def click_row(name):
    d = dialog()
    r = table_row(name)
    rect = d.user.visualItemRect(d.user.item(r, 3))  # (the Value cell: no editor, no star)
    w.click(d.user.viewport(), rect.center())


def g_used():
    click_row("Arm")
    w.click(dialog().remove_button)


def g_used_check():
    d = dialog()
    text = d.message.text()
    h.check("G: a used parameter is not deleted", "Arm" in names(), names())
    h.check("G: said in red in the dialog", text.startswith("⚠") and "is used by" in text, text)
    h.check("G: with what uses it", "Limits_Arm_Length" in text, text)


def g_unused():
    click_row("Inch_Size")
    w.click(dialog().remove_button)


def g_unused_check():
    h.check("G: an unused one is deleted", "Inch_Size" not in names(), names())
    d = dialog()
    h.check("G: no complaint", d.message.text() == "", d.message.text())


# == H: favourites, filter =========================================================================
def star_click(name):
    d = dialog()
    r = table_row(name)
    rect = d.user.visualItemRect(d.user.item(r, 0))
    w.click(d.user.viewport(), QtCore.QPoint(rect.left() + 9, rect.center().y()))


def h_unstar():
    star_click("Head_Diam")


def h_unstar_check():
    r = row("Head_Diam")
    h.check(
        "H: a click on the star takes it out of Favorites", r is not None and not r["favorite"], r
    )
    d = dialog()
    favs = [d.favorites.item(i, 0).text().strip() for i in range(d.favorites.rowCount())]
    h.check("H: the Favorites list follows", "Head_Diam" not in favs and "Thickness" in favs, favs)


def h_star():
    star_click("Head_Diam")


def h_star_check():
    r = row("Head_Diam")
    h.check("H: another click puts it back", r is not None and r["favorite"], r)


def h_filter():
    d = dialog()
    si.type_into(d.filter, "thick", enter=False)
    shown = [
        d.user.item(r, 0).text().strip()
        for r in range(d.user.rowCount())
        if not d.user.isRowHidden(r)
    ]
    h.check("H: the filter shows only what holds the text", shown == ["Thickness"], shown)
    si.type_into(d.filter, "", enter=False)
    QtTest.QTest.keyClick(d.filter, QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
    QtTest.QTest.keyClick(d.filter, QtCore.Qt.Key_Delete)
    shown = [r for r in range(d.user.rowCount()) if not d.user.isRowHidden(r)]
    h.check("H: cleared, everything is back", len(shown) == d.user.rowCount(), shown)
    h.shot("H-dialog")


# == I: one undo step, Cancel ======================================================================
def i_ok():
    s["names"] = names()
    d = dialog()
    w.click(
        [b for b in d.findChildren(QtWidgets.QPushButton) if b.text().replace("&", "") == "OK"][0]
    )


i_ok.done = lambda: dialog() is None
i_ok.done_what = "the Parameters dialog closed"


def i_undo():
    ti.undo()


def i_undo_check():
    h.check("I: Ctrl+Z takes the whole edit back", names() == [], names())


def i_redo():
    ti.redo()


def i_redo_check():
    h.check("I: Ctrl+Y brings it again", names() == s["names"], names())
    h.check("I: with the values", abs(value("Thickness") + 2.5) < 1e-9, value("Thickness"))
    h.check(
        "I: and the formula's value",
        abs(value("Limits_Arm_Length") - 58) < 1e-9,
        value("Limits_Arm_Length"),
    )


def i_reopen():
    si.menu_item("MODIFY", "Change Parameters")


i_reopen.done = lambda: dialog() is not None
i_reopen.done_what = "the Parameters dialog is open"


def i_change():
    type_expression("Arm", "70")


def i_cancel():
    h.check("I: changed while the dialog is open", abs(value("Arm") - 70) < 1e-9, value("Arm"))
    d = dialog()
    w.click(
        [b for b in d.findChildren(QtWidgets.QPushButton) if b.text().replace("&", "") == "Cancel"][
            0
        ]
    )


i_cancel.done = lambda: dialog() is None
i_cancel.done_what = "the Parameters dialog closed"


def i_cancel_check():
    h.check("I: Cancel puts the value back", abs(value("Arm") - 53) < 1e-9, value("Arm"))
    h.check(
        "I: and the formula's",
        abs(value("Limits_Arm_Length") - 58) < 1e-9,
        value("Limits_Arm_Length"),
    )


steps = [setup, a_open, a_button]
steps += add("Head_Diam", "8.5") + [a_check]
steps += [
    b_open,
    refusal("mm", "5", "unit or function name", "unit"),
    refusal("Head_Diam", "5", "already exists", "twice"),
    refusal("Wall", "Head_Diam +", "not a value", "broken"),
    refusal("Wall", "Head_Dia / 2", "Did you mean Head_Diam", "typo"),
    refusal("2wide", "5", "not a valid name", "name"),
    b_cancel,
]
steps += add("Thickness", "-2.5") + [c_negative_check]
steps += add("Arm_Length", "53")
steps += add("Limits_Arm_Length", "min(100;max(45;Arm_Length))") + [c_limits_check]
for text, expected in (("40", 45), ("110", 100), ("53", 53)):
    steps += [typed("Arm_Length", text, text), limit_is(expected, text)]
steps += [
    typed("Limits_Arm_Length", "2 * (Head_Diam + 3)", "bare"),
    limit_is(23, "bare"),
    d_formula_text,
]
steps += [typed("Limits_Arm_Length", "Arm_Length + 5", "sum"), limit_is(58, "sum")]
steps += add("Inch_Size", "2", unit="in")
steps += add("W", "12") + add("h", "7") + add("t", "1.5") + add("Sum", "W + h * 2 + t") + [e_check]
steps += [f_rename, f_check, g_none_selected, g_used, g_used_check, g_unused, g_unused_check]
steps += [h_unstar, h_unstar_check, h_star, h_star_check, h_filter]
steps += [
    i_ok,
    i_undo,
    i_undo_check,
    i_redo,
    i_redo_check,
    i_reopen,
    i_change,
    i_cancel,
    i_cancel_check,
]

h.run("book_params_dialog", steps, paced_by="state")
