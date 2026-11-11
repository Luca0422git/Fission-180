# SPDX-License-Identifier: LGPL-2.1-or-later
"""A pattern of bodies whose Quantity is a parameter (the book's Metric Bolt, parity report
line 1417: "Circular Pattern of BODIES with Quantity = "Quantity" (a parameter): "A pattern
of bodies takes a plain number as its quantity." Workaround: type the number (6)").

Before: refused, then (wave 7, first pass) taken once as a number. Now the pattern keeps
the formula and its copies, each a body of its own, follow the parameter.

A bolt (d6 x 10 at 30 mm from the Z axis) and a user parameter Quantity = 6 are made by the
design-step builder and fission180.parameters (the Parameters dialog has its own scenarios).
Then real input:

1. CREATE > Circular Pattern, the bolt clicked (Pattern Type Bodies, the default), the Axis
   box, the Z axis, "Quantity" typed into Quantity, OK: 6 bodies; the dialog shows the
   formula and no longer says the number is kept.
2. MODIFY > Change Parameters, the expression of Quantity double-clicked, 8 typed, OK:
   8 bodies, 45 degrees apart. Ctrl+Z: 6 again (one step). Ctrl+Y: 8.
3. Change Parameters again: 4. Four bodies; the copies taken away leave nothing behind.
4. The history marker dragged before the pattern: only the bolt shows; dragged back to the
   end: four bodies again.
5. Edit Feature on the pattern: the dialog shows "Quantity" as the formula. Cancel changes
   nothing.
6. Ctrl+Z back to before the pattern: one body, no copy left; Ctrl+Y twice: 6, then 8.
"""

import math

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import pattern_steps as ps
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import timeline_input as t
from Fission180Tests.gui import widget_input as w

V = App.Vector
S = {}
BOLT = math.pi * 9 * 10
STEPS = [
    {"op": "sketch", "id": "s1", "plane": "XY", "geometry": [{"circle": [30, 0, 3]}]},
    {"op": "extrude", "id": "e1", "profile": "s1", "distance": 10},
]


def doc():
    return App.ActiveDocument


def solids():
    """Every body's solid that shows (design coordinates)."""
    from fission180 import bodies

    found = []
    for body in doc().findObjects("PartDesign::Body"):
        try:
            if body.Shape.isNull() or not body.Shape.Solids or not body.ViewObject.Visibility:
                continue
            found.append(bodies.global_shape(body))
        except Exception:
            continue
    return found


def count():
    return len(solids())


def angles():
    """Where the bolts stand round the Z axis, in whole degrees."""
    out = []
    for shape in solids():
        c = shape.CenterOfMass
        out.append(int(round(math.degrees(math.atan2(c.y, c.x)))) % 360)
    return sorted(out)


def every(n):
    return [int(round(360.0 * k / n)) % 360 for k in range(n)]


def copies():
    from fission180 import pattern

    return [o for o in doc().Objects if pattern.is_body_copy(o)]


def dialog():
    from fission180 import parameters_ui

    d = parameters_ui.ParametersDialog.last
    return d if d is not None and d.isVisible() else None


def type_expression(name, text):
    """Double-click the parameter's Expression cell, type, Enter."""
    d = dialog()
    row = -1
    for r in range(d.user.rowCount()):
        if d.user.item(r, 0).data(QtCore.Qt.UserRole) == name:
            row = r
    if not h.check("%s is in the table" % name, row >= 0):
        return
    view = d.user
    rect = view.visualItemRect(view.item(row, 2))
    view.window().activateWindow()
    view.window().raise_()
    QtWidgets.QApplication.processEvents()
    w.double_click(view.viewport(), rect.center())
    editors = [e for e in view.findChildren(QtWidgets.QLineEdit) if e.isVisible()]
    if not h.check("an editor opened in the cell", bool(editors)):
        return
    QtTest.QTest.keyClick(editors[0], QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
    QtTest.QTest.keyClicks(editors[0], text)
    QtTest.QTest.keyClick(editors[0], QtCore.Qt.Key_Return)
    QtWidgets.QApplication.processEvents()


def change_to(value, tag):
    def open_dialog():
        si.menu_item("MODIFY", "Change Parameters")

    open_dialog.done = lambda: dialog() is not None
    open_dialog.done_what = "the Parameters dialog is open"
    open_dialog.__name__ = "params_open_%s" % tag

    def typed():
        type_expression("Quantity", str(value))

    typed.__name__ = "params_type_%s" % tag

    def ok():
        d = dialog()
        buttons = d.findChildren(QtWidgets.QPushButton)
        w.click([b for b in buttons if b.text().replace("&", "") == "OK"][0])

    ok.done = lambda: dialog() is None
    ok.done_what = "the Parameters dialog closed"
    ok.__name__ = "params_ok_%s" % tag
    return [open_dialog, typed, ok]


def setup():
    from Fission180Tests.golden.builder import Builder
    from fission180 import parameters

    Gui.activateWorkbench("Fission180Workbench")
    d = App.newDocument("Bolts")
    builder = Builder(d)
    for step in STEPS:
        builder.run(step)
        d.recompute()
    parameters.add_user(d, "Quantity", "", "6")
    d.recompute()
    d.clearUndos()
    h.fit()


def start():
    h.check("one bolt", count() == 1 and abs(solids()[0].Volume - BOLT) < 1e-6, count())
    Gui.Selection.clearSelection()
    ps.menu("Circular Pattern")


def click_bolt():
    p = ps.panel()
    h.check("Pattern Type Bodies", p.options["pattern_type"] == "bodies", p.options["pattern_type"])
    h.click(V(30, 0, 10))


def axis_box():
    p = ps.panel()
    h.check("the bolt is picked", len(p.options["objects"]) == 1, p.options["objects"])
    ps.click_box("axis")


def z_axis():
    h.fit()
    pl.click_on_plane(V(0, 0, 6))


def quantity():
    p = ps.panel()
    axis = p.options["axis"] if p else None
    h.check("the Z axis", axis is not None and getattr(axis[0], "Role", "") == "Z_Axis", axis)
    ps.type_quantity(p.quantity, "Quantity")


def typed():
    p = ps.panel()
    h.check("no refusal", not p.message.text(), p.message.text())
    h.check(
        "the formula is kept",
        p.options["expressions"].get("quantity") == "Quantity",
        p.options["expressions"],
    )
    h.check("it is shown", "Quantity = Quantity" in p.formulas.text(), p.formulas.text())
    h.check("the field shows 6", p.quantity.value() == 6, p.quantity.value())
    h.check("nothing about a kept number", "keeps the number" not in p.info.text(), p.info.text())
    h.check("6 bolts previewed", count() == 6, count())
    h.task_button("OK")


def six():
    h.check("dialog closed", ps.panel() is None)
    h.check("6 bolts, 60 degrees apart", angles() == every(6), angles())
    h.check("5 copies", len(copies()) == 5, len(copies()))
    step = [o for o in doc().Objects if getattr(o, "Fission180Type", "") == "CircularPattern"][0]
    S["step"] = step.Name
    engine = dict(step.ExpressionEngine)
    h.check("the step's Quantity follows the parameter", "Quantity" in engine, engine)
    h.check("one undo step", list(doc().UndoNames) == ["Circular Pattern"], list(doc().UndoNames))
    h.check("nothing is red", all(v[1] == "ok" for v in t.states().values()), t.states())


def eight():
    h.check("8 bolts, 45 degrees apart", angles() == every(8), angles())
    h.check("7 copies", len(copies()) == 7, len(copies()))
    h.check("each a bolt", all(abs(s.Volume - BOLT) < 1e-6 for s in solids()))
    names = list(doc().UndoNames)
    h.check("the change is one undo step", names[0] == "Change Parameters", names)
    S["undo"] = len(names)
    h.check("nothing is red", all(v[1] == "ok" for v in t.states().values()), t.states())
    t.ctrl("z")


def undone():
    h.check("Ctrl+Z: 6 bolts again", angles() == every(6), angles())
    h.check("5 copies", len(copies()) == 5, len(copies()))
    h.check("one step went", len(doc().UndoNames) == S["undo"] - 1, list(doc().UndoNames))
    t.ctrl("y")


def redone():
    h.check("Ctrl+Y: 8 bolts", angles() == every(8), angles())
    h.check("7 copies", len(copies()) == 7, len(copies()))


def four():
    h.check("4 bolts, 90 degrees apart", angles() == every(4), angles())
    h.check("3 copies, the others are gone", len(copies()) == 3, len(copies()))
    bodies = doc().findObjects("PartDesign::Body")
    h.check("4 bodies in the design", len(bodies) == 4, [b.Label for b in bodies])
    h.check("nothing is red", all(v[1] == "ok" for v in t.states().values()), t.states())
    S["title"] = [x for x in t.titles() if "Pattern" in x][0]
    t.drag_marker(before_title=S["title"])


def rolled_back():
    h.check("rolled back before the pattern: the bolt alone", count() == 1, count())
    t.drag_marker(to_end=True)


def rolled_forward():
    h.check("the marker at the end: 4 bolts", angles() == every(4), angles())
    t.menu(S["title"], "Edit Feature")


rolled_forward.done = lambda: ps.panel() is not None
rolled_forward.done_what = "the pattern's dialog is open"


def edit_cancel():
    p = ps.panel()
    h.check(
        "the dialog shows the formula",
        p.options["expressions"].get("quantity") == "Quantity"
        and "Quantity = Quantity" in p.formulas.text(),
        (p.options["expressions"], p.formulas.text()),
    )
    h.check("and its value now", p.quantity.value() == 4, p.quantity.value())
    h.task_button("Cancel")


def after_cancel():
    h.check("dialog closed", ps.panel() is None)
    h.check("Cancel: still 4 bolts", angles() == every(4), angles())
    h.check("3 copies", len(copies()) == 3, len(copies()))
    t.ctrl("z")  # the change to 4


def back_one():
    h.check("Ctrl+Z: 8", angles() == every(8), angles())
    t.ctrl("z")  # the change to 8


def back_two():
    h.check("Ctrl+Z: 6", angles() == every(6), angles())
    t.ctrl("z")  # the pattern


def back_three():
    h.check("Ctrl+Z: the pattern is gone", count() == 1, count())
    h.check("no copy left behind", not copies(), [c.Name for c in copies()])
    bodies = doc().findObjects("PartDesign::Body")
    h.check("one body in the design", len(bodies) == 1, [b.Label for b in bodies])
    t.ctrl("y")


def forward_one():
    h.check("Ctrl+Y: the pattern, 6 bolts", angles() == every(6), angles())
    t.ctrl("y")


def forward_two():
    h.check("Ctrl+Y: 8 bolts", angles() == every(8), angles())
    h.check("7 copies", len(copies()) == 7, len(copies()))
    h.check("nothing is red", all(v[1] == "ok" for v in t.states().values()), t.states())
    h.shot("pattern-quantity")


h.run(
    "book_modifyc_pattern_quantity",
    [setup, start, click_bolt, axis_box, z_axis, quantity, typed, six]
    + change_to(8, "8")
    + [eight, undone, redone]
    + change_to(4, "4")
    + [four, rolled_back, rolled_forward, edit_cancel, after_cancel]
    + [back_one, back_two, back_three, forward_one, forward_two],
    paced_by="state",
)
