# SPDX-License-Identifier: LGPL-2.1-or-later
"""Wave 7 (the book parity report), params: parameters in dialog fields, only real input.

The book's Drone: "Typing Thickness= -2.5 mm in Distance (Fusion's quick way to create a
parameter): 'Thickness= -2.5 mm' is not a value here: Failed to parse expression. A user
parameter in mm cannot be negative: -2.5 becomes 0 mm (bug 4)." And: "Move dialog distances
do not take parameters: Arm_Length, =Arm_Length, Parameters.Arm_Length all silently give
0.00 mm; WORSE, -2 * Arm_Length is silently read as -2 mm."

Parameter made by script: Arm_Length = 53 (the "+" button has its own scenario).

  A  A 40 x 30 rectangle on XY (drawn by script), Finish Sketch, E: `Thickness= -2.5 mm`
     typed in Distance: the user parameter Thickness = -2.5 mm is made (negative: bug 4),
     the field follows it and the plate goes 2.5 mm down. OK. Ctrl+Z takes the extrude and
     the parameter back together, Ctrl+Y brings both again.
  B  Extrude 1 edited from the timeline: Distance typed `Ar`: a list offers Arm_Length;
     Enter fills the name in and does not close the dialog; ` / -10` typed after it, Tab:
     5.3 mm down, the formula kept as typed. Then `-2 * 1.5`: 3 mm down, kept as the
     formula `-2 mm * 1.5` (Fusion keeps what was typed). OK.
  C  A typo: Extrude 1 edited again, `Arm_Lenght` typed: the dialog says "There is no
     parameter named 'Arm_Lenght'. Did you mean Arm_Length?" and keeps its value. Cancel.
  D  M (Move/Copy), the body clicked: X Distance typed `Arm_Length`: the body moves 53 mm
     (it gave 0); `-2 * Arm_Length`: -106 mm (it was read as -2 mm); `Arm_Length + 5`: 58;
     `=Arm_Length`: 53. `Arm_Lenght`: refused next to the mouse with the reason, the field
     keeps 53. Z Angle `30 + 15`: 45 degrees. OK: the body is 53 mm to the right, turned 45.
  E  MODIFY > Change Parameters lists Thickness as -2.5 mm; Arm_Length typed 60 moves nothing
     in the Move step (the Move dialog takes the parameter's value; its fields hold no
     formula: said in parity/parameters.md).
"""

import FreeCAD as App
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import bodies_steps as bs
from Fission180Tests.gui import dialog_input as di
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import widget_input as w

V = App.Vector
s = {}


def doc():
    return App.ActiveDocument


def value(name):
    from fission180 import parameters, parameters_core

    holder = parameters.container(doc())
    if holder is None or parameters_core.prop_name(name) not in holder.PropertiesList:
        return None
    return getattr(holder, parameters_core.prop_name(name)).Value


def pad():
    found = [o for o in doc().Objects if o.TypeId in ("PartDesign::Pad", "PartDesign::Pocket")]
    return found[0] if found else None


def body():
    return bs.bodies()[0]


def box():
    bb = body().Shape.BoundBox
    return [round(x, 6) for x in (bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax)]


def formula(prop="Length"):
    from fission180 import preview

    return preview.formula_of(pad(), prop)


def distance_field():
    panel = b.active_panel()
    return getattr(getattr(panel, "distance", None), "widget", None)


def message():
    panel = b.active_panel()
    for name in ("status", "message", "info"):
        label = getattr(panel, name, None)
        if label is not None and hasattr(label, "text") and label.text():
            return label.text()
    return ""


def names():
    from fission180 import parameters_complete

    return parameters_complete.shown()


def told():
    from fission180 import commands

    return commands._TOLD.get("msg") or ""


# == A: Name = value in Extrude ====================================================================
def a_new():
    from fission180 import parameters
    import FreeCADGui as Gui

    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("BookParamsFields")
    parameters.add_user(doc(), "Arm_Length", "mm", "53")
    doc().recompute()
    h.fit()
    h.ribbon("Create Sketch")


def a_plane():
    pl.click_on_plane(V(12, -8, 0))


def a_draw():
    sk = h.in_sketch()
    h.check("A: sketch open on XY", sk is not None)
    if sk:
        h.draw_rectangle(sk, 0, 0, 40, 30)


def a_finish():
    h.ribbon("Finish Sketch")


def a_extrude():
    h.fit()
    h.press("e")


def a_type():
    field = distance_field()
    h.check("A: Extrude's Distance field is there", field is not None)
    if field is not None:
        di.type_into(field, "Thickness= -2.5 mm")  # (then Tab, as a person leaves a field)


def a_typed():
    h.check("A: the parameter Thickness is made", value("Thickness") is not None)
    h.check(
        "A: it holds -2.5 mm (bug 4)",
        value("Thickness") is not None and abs(value("Thickness") + 2.5) < 1e-9,
        value("Thickness"),
    )
    h.check(
        "A: no complaint in the dialog",
        "⚠" not in message() and "not a value" not in message(),
        message(),
    )
    h.task_button("OK")


def a_made():
    v = h.solid_volume()
    h.check("A: the plate is 40 x 30 x 2.5", b.close(v, 1200.0 * 2.5), v)
    h.check(
        "A: it goes down from the sketch", b.close(box()[2], -2.5) and b.close(box()[5], 0.0), box()
    )
    shown = formula()
    h.check("A: the extrude follows Thickness", "Thickness" in shown, shown)
    s["names"] = ["Arm_Length", "Thickness"]


def a_undo():
    h.press(QtCore.Qt.Key_Z, QtCore.Qt.ControlModifier)


def a_undone():
    h.check("A: Ctrl+Z takes the extrude back", pad() is None, pad())
    h.check("A: and the parameter made with it", value("Thickness") is None, value("Thickness"))
    h.check("A: Arm_Length stays", value("Arm_Length") == 53.0, value("Arm_Length"))


def a_redo():
    h.press(QtCore.Qt.Key_Y, QtCore.Qt.ControlModifier)


def a_redone():
    h.check("A: Ctrl+Y brings the plate", b.close(h.solid_volume(), 1200.0 * 2.5), h.solid_volume())
    h.check(
        "A: and the parameter",
        value("Thickness") is not None and abs(value("Thickness") + 2.5) < 1e-9,
        value("Thickness"),
    )
    h.check("A: still following it", "Thickness" in formula(), formula())


# == B: the list of names, a sum kept ==============================================================
def b_edit():
    h.click_empty()
    b.timeline_double_click("Extrude 1", click_first=True)


def b_type():
    field = distance_field()
    h.check("B: Extrude 1 is open for editing", field is not None)
    if field is None:
        return
    edit = field.findChild(QtWidgets.QLineEdit)
    QtTest.QTest.mouseClick(
        field, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, QtCore.QPoint(10, field.height() // 2)
    )
    QtWidgets.QApplication.processEvents()
    field.setFocus()
    QtTest.QTest.keyClick(field, QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
    QtTest.QTest.keyClicks(QtWidgets.QApplication.focusWidget() or edit, "Ar")
    QtWidgets.QApplication.processEvents()


b_type.done = lambda: bool(names())
b_type.done_what = "the list of parameter names is open"


def b_fill():
    h.check("B: Ar offers Arm_Length", names() == ["Arm_Length"], names())
    target = QtWidgets.QApplication.focusWidget()
    QtTest.QTest.keyClick(target, QtCore.Qt.Key_Return)
    QtWidgets.QApplication.processEvents()
    field = distance_field()
    h.check("B: Enter filled the name and did not close the dialog", field is not None)
    if field is None:
        return
    text = field.findChild(QtWidgets.QLineEdit).text()
    h.check("B: the field reads Arm_Length", text == "Arm_Length", text)
    h.check("B: the list closed", names() == [], names())
    target = QtWidgets.QApplication.focusWidget()
    QtTest.QTest.keyClicks(target, " / -10")
    QtTest.QTest.keyClick(target, QtCore.Qt.Key_Tab)
    QtWidgets.QApplication.processEvents()


def b_filled():
    h.caught_up(b.active_panel())
    h.check(
        "B: Arm_Length / -10 is 5.3 mm down",
        b.close(h.solid_volume(), 1200.0 * 5.3),
        h.solid_volume(),
    )
    h.check(
        "B: no complaint",
        "not a value" not in message() and "no parameter" not in message(),
        message(),
    )
    field = distance_field()
    if field is not None:
        di.type_into(field, "-2 * 1.5")


def b_sum():
    h.caught_up(b.active_panel())
    h.check("B: -2 * 1.5 is 3 mm down", b.close(h.solid_volume(), 1200.0 * 3), h.solid_volume())
    h.task_button("OK")


def b_done():
    h.check("B: OK keeps 3 mm", b.close(h.solid_volume(), 1200.0 * 3), h.solid_volume())
    h.check("B: still below the sketch", b.close(box()[2], -3.0) and b.close(box()[5], 0.0), box())
    shown = formula().replace(" ", "")
    h.check(
        "B: the sum is kept as a formula, its length with the unit", "2mm*1.5" in shown, formula()
    )


# == C: a typo =====================================================================================
def c_edit():
    h.click_empty()
    b.timeline_double_click("Extrude 1", click_first=True)


def c_type():
    field = distance_field()
    h.check("C: Extrude 1 is open for editing", field is not None)
    if field is not None:
        di.type_into(field, "Arm_Lenght")


def c_refused():
    text = message()
    h.check(
        "C: the dialog says the name is unknown", "no parameter named 'Arm_Lenght'" in text, text
    )
    h.check("C: and offers the right one", "Did you mean Arm_Length?" in text, text)
    h.check("C: the plate keeps its 3 mm", b.close(h.solid_volume(), 1200.0 * 3), h.solid_volume())
    h.task_button("Cancel")


def c_cancelled():
    h.check("C: Cancel leaves 3 mm", b.close(h.solid_volume(), 1200.0 * 3), h.solid_volume())
    h.check("C: and the formula", "1.5" in formula(), formula())


# == D: Move/Copy ==================================================================================
def d_move():
    h.click_empty()
    h.fit()
    h.press("m")


def d_click():
    h.click(V(20, 15, 0))


def move_field(name):
    p = bs.panel()
    return {"dx": p.distance_fields[0], "rz": p.angle_fields[2]}[name]


def typed(name, text, tag):
    def step():
        p = bs.panel()
        h.check(
            "D %s: Move/Copy is open with the body" % tag,
            p is not None and bool(p.options.get("bodies")),
        )
        if p is not None:
            bs.type_value(move_field(name).widget, text)

    step.__name__ = "d_type_" + tag
    return step


def moved(expected, tag):
    def step():
        p = bs.panel()
        got = p.options["dx"] if p is not None else None
        h.check(
            "D %s: X Distance is %s" % (tag, expected),
            got is not None and abs(got - expected) < 1e-9,
            got,
        )
        h.check("D %s: the body follows" % tag, abs(box()[0] - expected) < 1e-6, box())
        h.check(
            "D %s: nothing refused" % tag, move_field("dx").refused == "", move_field("dx").refused
        )

    step.__name__ = "d_check_" + tag
    return step


def d_typo_check():
    p = bs.panel()
    field = move_field("dx")
    h.check(
        "D typo: refused with the reason",
        "no parameter named 'Arm_Lenght'" in field.refused,
        field.refused,
    )
    h.check("D typo: said next to the mouse", "no parameter named 'Arm_Lenght'" in told(), told())
    h.check("D typo: X Distance keeps 53", abs(p.options["dx"] - 53) < 1e-9, p.options["dx"])
    h.check("D typo: the field shows 53 again", abs(field.value() - 53) < 1e-9, field.value())
    h.check("D typo: the body did not move", abs(box()[0] - 53) < 1e-6, box())


def d_angle_check():
    p = bs.panel()
    h.check("D: Z Angle 30 + 15 is 45 degrees", abs(p.options["rz"] - 45) < 1e-9, p.options["rz"])
    h.task_button("OK")


def d_done():
    moves = bs.steps_of_kind("MoveCopy")
    h.check("D: one Move step", len(moves) == 1, moves)
    bb = body().Shape.BoundBox
    centre = ((bb.XMin + bb.XMax) / 2.0, (bb.YMin + bb.YMax) / 2.0)
    h.check(
        "D: the body's middle is 53 mm to the right",
        abs(centre[0] - 73) < 1e-6 and abs(centre[1] - 15) < 1e-6,
        centre,
    )
    h.check(
        "D: and it is turned 45 degrees",
        abs((bb.XMax - bb.XMin) - (40 + 30) / 2**0.5) < 1e-6,
        bb.XMax - bb.XMin,
    )
    s["box"] = box()


# == E: Change Parameters ==========================================================================
def dialog():
    from fission180 import parameters_ui

    d = parameters_ui.ParametersDialog.last
    return d if d is not None and d.isVisible() else None


def e_open():
    si.menu_item("MODIFY", "Change Parameters")


e_open.done = lambda: dialog() is not None
e_open.done_what = "the Parameters dialog is open"


def type_parameter(name, text):
    d = dialog()
    row = [
        r for r in range(d.user.rowCount()) if d.user.item(r, 0).data(QtCore.Qt.UserRole) == name
    ]
    h.check("E: %s is in the table" % name, bool(row))
    if not row:
        return
    rect = d.user.visualItemRect(d.user.item(row[0], 2))
    d.window().activateWindow()
    w.double_click(d.user.viewport(), rect.center())
    editors = [e for e in d.user.findChildren(QtWidgets.QLineEdit) if e.isVisible()]
    h.check("E: an editor opened for %s" % name, bool(editors))
    if editors:
        QtTest.QTest.keyClick(editors[0], QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
        QtTest.QTest.keyClicks(editors[0], text)
        QtTest.QTest.keyClick(editors[0], QtCore.Qt.Key_Return)


def e_listed():
    d = dialog()
    shown = {
        d.user.item(r, 0).data(QtCore.Qt.UserRole): d.user.item(r, 2).text()
        for r in range(d.user.rowCount())
    }
    h.check("E: Thickness is listed as -2.5 mm", shown.get("Thickness") == "-2.5 mm", shown)
    h.check("E: Arm_Length as 53 mm", shown.get("Arm_Length") == "53 mm", shown)
    type_parameter("Arm_Length", "60")


def e_arm():
    d = dialog()
    h.check("E: no complaint", d.message.text() == "", d.message.text())
    h.check("E: Arm_Length is 60", abs(value("Arm_Length") - 60) < 1e-9, value("Arm_Length"))
    h.check(
        "E: the Move step holds the value it was given (53)", box() == s["box"], (box(), s["box"])
    )
    w.click(
        [x for x in d.findChildren(QtWidgets.QPushButton) if x.text().replace("&", "") == "OK"][0]
    )


e_arm.done = lambda: dialog() is None
e_arm.done_what = "the Parameters dialog closed"


steps = [a_new, a_plane, a_draw, a_finish, a_extrude, a_type, a_typed, a_made]
steps += [a_undo, a_undone, a_redo, a_redone]
steps += [b_edit, b_type, b_fill, b_filled, b_sum, b_done]
steps += [c_edit, c_type, c_refused, c_cancelled]
steps += [d_move, d_click]
for text, expected, tag in (
    ("Arm_Length", 53.0, "name"),
    ("-2 * Arm_Length", -106.0, "product"),
    ("Arm_Length + 5", 58.0, "sum"),
    ("=Arm_Length", 53.0, "equals"),
):
    steps += [typed("dx", text, tag), moved(expected, tag)]
steps += [
    typed("dx", "Arm_Lenght", "typo"),
    d_typo_check,
    typed("rz", "30 + 15", "angle"),
    d_angle_check,
    d_done,
]
steps += [e_open, e_listed, e_arm]

h.run("book_params_fields", steps, paced_by="state")
