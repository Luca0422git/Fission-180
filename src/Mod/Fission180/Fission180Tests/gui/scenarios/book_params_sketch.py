# SPDX-License-Identifier: LGPL-2.1-or-later
"""Wave 7 (the book parity report), params: parameters in a sketch, only real input.

The book's Metric Bolt and Drone: "In a SKETCH dimension box a parameter must be typed with
a leading = (=Head_Length); typing the bare name (Fusion's way) silently keeps the measured
value. No autocomplete drop-down of parameter names appears while typing. Typing Head_Diam =
8.5 in a dimension box does not create a parameter. Deleting a sketch dimension does not
renumber the parameter links of the dimensions after it (bug 3)."

Parameters (made by script; the "+" button has its own scenario, book_params_dialog):
Head_Length 5, Head_Diam 8.5, Shank_Length 20, Support_Width 4.

  A  Create Sketch on XY, R: a rectangle. D on its top line, the box opens: `Head_Length`
     typed bare, Enter: the width is 5 and follows the parameter.
  B  D on the right line: `S` typed: a list opens under the box with Support_Width and
     Shank_Length; Down chooses the second, Tab fills it in; ` / 2` typed after it, Enter:
     the height is 10 with the formula Shank_Length / 2.
  C  Double-click that dimension: the box shows the formula as it was typed (no "=", no
     "Parameters."). `Width = 12` typed, Enter: the user parameter Width (12 mm) is made, a
     favourite, and the dimension follows it.
  D  CREATE > 2-Point Circle, its diameter typed `=Head_Diam` in the tool's own value box
     ("=" first: a letter typed first is its shortcut, as while drawing in Fusion): 8.5 across,
     and its dimension follows Head_Diam. Its dimension double-clicked and `9 * 1.02` typed:
     9.18, kept as the formula `9 mm * 1.02` (Fusion keeps what was typed).
  E  Refusals, the box stays open and says why: `Head_Lenght` ("Did you mean Head_Length?"),
     `Width = 3` (the name exists), `Head_Length +` (not a value), `30 deg` (an angle).
     Esc: nothing changed.
  F  Bug 3: the first dimension (the width, Head_Length) clicked and Delete pressed. The
     height still follows Width and the circle still holds 9 mm * 1.02, each on its own
     dimension. Ctrl+Z: the width's dimension is back with its formula; Ctrl+Y: gone again.
  G  Finish Sketch; MODIFY > Change Parameters: Width's Expression typed 15: the rectangle's
     height is 15 (and nothing else moved); the sketch's dimensions are listed with their
     formulas. OK.
"""

import FreeCAD as App
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st
from Fission180Tests.gui import widget_input as w

V = App.Vector
s = st.s


def sk():
    return st.sketch() or s.get("sketch")


def editor():
    from fission180 import sketch_mode

    session = sketch_mode.current()
    return session.editor if session is not None else None


def formulas():
    """{constraint index: formula as the person reads it} of the sketch."""
    from fission180 import parameters, parameters_core

    out = {}
    for path, expr in parameters.expressions_of(sk()).items():
        if path.startswith(".Constraints["):
            out[int(path[len(".Constraints[") : -1])] = parameters_core.from_freecad(expr)
    return out


def dims():
    """[(index, type, value)] of the sketch's driving dimensions."""
    kinds = ("Distance", "DistanceX", "DistanceY", "Radius", "Diameter")
    return [(i, c.Type, c.Value) for i, c in enumerate(sk().Constraints) if c.Type in kinds]


def extent():
    """(width, height) of the rectangle (the four lines drawn first)."""
    xs, ys = [], []
    for g in sk().Geometry[:4]:
        xs += [g.StartPoint.x, g.EndPoint.x]
        ys += [g.StartPoint.y, g.EndPoint.y]
    return max(xs) - min(xs), max(ys) - min(ys)


def value(name):
    from fission180 import parameters, parameters_core

    held = getattr(parameters.container(App.ActiveDocument), parameters_core.prop_name(name))
    return held.Value


def names():
    from fission180 import parameters_complete

    return parameters_complete.shown()


# == setup =========================================================================================
def p_setup():
    from fission180 import parameters

    d = App.ActiveDocument
    for name, text in (
        ("Head_Length", "5"),
        ("Head_Diam", "8.5"),
        ("Shank_Length", "20"),
        ("Support_Width", "4"),
    ):
        parameters.add_user(d, name, "mm", text)
    d.recompute()


def r_rect():
    h.press("r")


def r_c1():
    st.click(V(40, 20, 0))


def r_c2():
    st.click(V(0, 0, 0))


def r_done():
    st.esc()
    s["sketch"] = sk()
    s["count"] = len(sk().Constraints)


# == A: a bare name ================================================================================
def a_dim():
    h.press("d")


def a_pick():
    st.click(V(20, 20, 0))


def a_place():
    st.click(V(20, 28, 0))


a_place.done = lambda: editor() is not None
a_place.done_what = "the dimension box is open"


def a_type():
    si.type_text("Head_Length")


def a_check():
    h.check("A: the box closed", editor() is None, editor() and editor().reason())
    width, _height = extent()
    h.check("A: the bare name set the width to 5", abs(width - 5) < 1e-6, width)
    new = [i for i, _t, _v in dims() if i >= s["count"]]
    h.check("A: one dimension was added", len(new) == 1, dims())
    s["width_dim"] = new[0] if new else -1
    h.check(
        "A: and it follows the parameter",
        formulas().get(s["width_dim"]) == "Head_Length",
        formulas(),
    )
    st.esc()


# == B: the list of names ==========================================================================
def b_dim():
    h.press("d")


def b_pick():
    width, _h = extent()
    xs = sorted({round(g.StartPoint.x, 6) for g in sk().Geometry[:4]})
    s["right"] = xs[-1]
    st.click(V(s["right"], 10, 0))


def b_place():
    st.click(V(s["right"] + 9, 10, 0))


b_place.done = lambda: editor() is not None
b_place.done_what = "the dimension box is open"


def b_type_s():
    si.type_text("S", enter=False)


b_type_s.done = lambda: bool(names())
b_type_s.done_what = "the list of parameter names is open"


def b_list():
    h.check(
        "B: S offers the names that start with S",
        names() == ["Shank_Length", "Support_Width"],
        names(),
    )
    h.shot("B-names")
    target = QtWidgets.QApplication.focusWidget()
    QtTest.QTest.keyClick(target, QtCore.Qt.Key_Down)
    QtTest.QTest.keyClick(target, QtCore.Qt.Key_Up)
    QtTest.QTest.keyClick(target, QtCore.Qt.Key_Tab)
    QtWidgets.QApplication.processEvents()
    ed = editor()
    h.check(
        "B: Tab fills the name in",
        ed is not None and ed.edit.text() == "Shank_Length",
        ed and ed.edit.text(),
    )
    h.check("B: the list closed", names() == [], names())
    h.check("B: the box is still open (Tab was the list's)", ed is not None)


def b_finish():
    si.type_text(" / 2")


def b_check():
    h.check("B: the box closed", editor() is None, editor() and editor().reason())
    _w, height = extent()
    h.check("B: the height is Shank_Length / 2 = 10", abs(height - 10) < 1e-6, height)
    new = [i for i, _t, _v in dims() if i > s["width_dim"]]
    s["height_dim"] = new[0] if new else -1
    h.check(
        "B: the formula is kept as typed",
        formulas().get(s["height_dim"]) == "Shank_Length / 2",
        formulas(),
    )
    st.esc()


# == C: Name = value ===============================================================================
def c_open():
    h.double_click(si.dimension_label(sk(), s["height_dim"]))


c_open.done = lambda: editor() is not None
c_open.done_what = "the dimension box is open"


def c_shown():
    ed = editor()
    text = ed.edit.text() if ed is not None else ""
    h.check("C: the box shows the formula as typed", text == "Shank_Length / 2", text)
    si.type_text("Width = 12")


def c_check():
    from fission180 import parameters

    h.check("C: the box closed", editor() is None, editor() and editor().reason())
    rows = [r for r in parameters.user_parameters(App.ActiveDocument) if r["name"] == "Width"]
    h.check("C: the user parameter Width is made", len(rows) == 1, rows)
    if rows:
        h.check("C: 12 mm", abs(rows[0]["value"] - 12) < 1e-9 and rows[0]["unit"] == "mm", rows[0])
        h.check("C: a favourite", rows[0]["favorite"], rows[0])
    _w, height = extent()
    h.check("C: the height is 12", abs(height - 12) < 1e-6, height)
    h.check(
        "C: the dimension follows Width", formulas().get(s["height_dim"]) == "Width", formulas()
    )
    st.esc()


# == D: the circle tool's own box, a sum kept ======================================================
def d_circle():
    s["geo"] = len(sk().Geometry)
    s["cons"] = len(sk().Constraints)
    si.menu_item("CREATE", "2-Point Circle")


def d_center():
    h.check("D: 2-Point Circle runs", st.tool_title() == "2-Point Circle", st.tool_title())
    st.click(V(60, 30, 0))


def d_hover():
    st.hover(V(70, 30, 0))


def d_type():
    st.keys("=Head_Diam\n")


def d_check():
    circles = [g for g in sk().Geometry[s["geo"] :] if g.TypeId == "Part::GeomCircle"]
    h.check("D: one circle", len(circles) == 1, [g.TypeId for g in sk().Geometry[s["geo"] :]])
    if circles:
        h.check("D: 8.5 across", abs(circles[0].Radius * 2 - 8.5) < 1e-6, circles[0].Radius)
    new = [(i, t) for i, t, _v in dims() if i >= s["cons"]]
    h.check("D: its dimension was added", len(new) == 1, new)
    s["circle_dim"] = new[0][0] if new else -1
    shown = formulas().get(s["circle_dim"], "")
    h.check("D: and follows Head_Diam", "Head_Diam" in shown, formulas())
    st.esc()


def d_open():
    h.double_click(si.dimension_label(sk(), s["circle_dim"]))


d_open.done = lambda: editor() is not None
d_open.done_what = "the dimension box is open"


def d_sum():
    si.type_text("9 * 1.02")


def d_sum_check():
    h.check("D: the box closed", editor() is None, editor() and editor().reason())
    c = sk().Constraints[s["circle_dim"]]
    across = c.Value * (2 if c.Type == "Radius" else 1)
    h.check("D: 9 * 1.02 = 9.18 across", abs(across - 9.18) < 1e-6, (c.Type, c.Value))
    h.check(
        "D: kept as a formula, its length with the unit (Fusion keeps what was typed)",
        formulas().get(s["circle_dim"]) == "9 mm * 1.02",
        formulas(),
    )
    st.esc()


# == E: refusals ===================================================================================
def e_open():
    s["before"] = (
        dims(),
        formulas(),
        [r for r in sorted(value(n) for n in ("Width", "Head_Length"))],
    )
    h.double_click(si.dimension_label(sk(), s["height_dim"]))


e_open.done = lambda: editor() is not None
e_open.done_what = "the dimension box is open"


def refusal(text, words, tag):
    def step():
        ed = editor()
        h.check("E %s: the box is open" % tag, ed is not None)
        if ed is None:
            return
        ed.edit.selectAll()
        si.type_text(text)
        ed = editor()
        reason = ed.reason() if ed is not None else ""
        h.check("E %s: the box stays open" % tag, ed is not None)
        h.check("E %s: and says why (%s)" % (tag, words), words in reason, reason)
        h.new_errors()

    step.__name__ = "e_refuse_" + tag
    return step


def e_esc():
    st.esc()


def e_unchanged():
    now = (dims(), formulas(), [r for r in sorted(value(n) for n in ("Width", "Head_Length"))])
    h.check("E: nothing changed", now == s["before"], (now, s["before"]))
    from fission180 import parameters

    made = [n for n in parameters.own_names(App.ActiveDocument) if n not in s.get("names", [])]
    h.check("E: no parameter was made by a refused line", "Height" not in made, made)
    st.sketch_ok("after the refusals")


# == F: delete a dimension (bug 3) =================================================================
def f_select():
    st.esc()
    s["f_before"] = (dims(), formulas())
    h.click(si.dimension_label(sk(), s["width_dim"]))


def f_delete():
    h.press(QtCore.Qt.Key_Delete)


def f_check():
    before_dims, before = s["f_before"]
    now = formulas()
    h.check("F: the width's dimension is gone", len(dims()) == len(before_dims) - 1, dims())
    h.check("F: and its formula with it", "Head_Length" not in now.values(), now)
    # the two later dimensions moved one place up: their formulas must have moved with them
    by_formula = {text: sk().Constraints[i] for i, text in now.items()}
    h.check("F: two formulas are left", sorted(now.values()) == ["9 mm * 1.02", "Width"], now)
    c = by_formula.get("Width")
    h.check(
        "F: Width is still on the height (12)", c is not None and abs(abs(c.Value) - 12) < 1e-6, c
    )
    c = by_formula.get("9 mm * 1.02")
    h.check(
        "F: 9 mm * 1.02 is still on the circle",
        c is not None
        and c.Type in ("Radius", "Diameter")
        and abs(c.Value * (2 if c.Type == "Radius" else 1) - 9.18) < 1e-6,
        c,
    )
    h.check("F: the sketch is fine", "Invalid" not in sk().State, sk().State)
    st.sketch_ok("after the delete")
    s["f_after"] = (dims(), dict(now))


def f_undo():
    st.undo()


def f_undone():
    before_dims, before = s["f_before"]
    h.check("F: Ctrl+Z brings the dimension back", len(dims()) == len(before_dims), dims())
    h.check(
        "F: every formula on its own dimension again", formulas() == before, (formulas(), before)
    )
    width, height = extent()
    h.check(
        "F: 5 wide and 12 high", abs(width - 5) < 1e-6 and abs(height - 12) < 1e-6, (width, height)
    )


def f_redo():
    st.redo()


def f_redone():
    h.check(
        "F: Ctrl+Y deletes it again, the formulas as after the delete",
        formulas() == s["f_after"][1],
        formulas(),
    )
    st.sketch_ok("after the redo")


# == G: Change Parameters ==========================================================================
def dialog():
    from fission180 import parameters_ui

    d = parameters_ui.ParametersDialog.last
    return d if d is not None and d.isVisible() else None


def g_finish():
    st.esc()
    h.ribbon("Finish Sketch")


def g_open():
    si.menu_item("MODIFY", "Change Parameters")


g_open.done = lambda: dialog() is not None
g_open.done_what = "the Parameters dialog is open"


def g_type():
    from fission180 import parameters

    d = dialog()
    rows = parameters.model_parameters(App.ActiveDocument)
    shown = sorted(r["shown"] for r in rows if r["object"] == s["sketch"].Name)
    h.check(
        "G: the sketch's dimensions are listed with their formulas",
        shown == ["9 mm * 1.02", "Width"],
        shown,
    )
    row = [
        r for r in range(d.user.rowCount()) if d.user.item(r, 0).data(QtCore.Qt.UserRole) == "Width"
    ]
    h.check("G: Width is in the table", bool(row))
    if not row:
        return
    rect = d.user.visualItemRect(d.user.item(row[0], 2))
    d.window().activateWindow()
    w.double_click(d.user.viewport(), rect.center())
    editors = [e for e in d.user.findChildren(QtWidgets.QLineEdit) if e.isVisible()]
    h.check("G: an editor opened", bool(editors))
    if editors:
        QtTest.QTest.keyClick(editors[0], QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
        QtTest.QTest.keyClicks(editors[0], "15")
        QtTest.QTest.keyClick(editors[0], QtCore.Qt.Key_Return)


def g_check():
    d = dialog()
    h.check("G: no complaint", d is not None and d.message.text() == "", d and d.message.text())
    width, height = extent()
    h.check("G: the height follows Width (15)", abs(height - 15) < 1e-6, height)
    circle = [g for g in s["sketch"].Geometry if g.TypeId == "Part::GeomCircle"][0]
    h.check(
        "G: the circle did not move from 9.18", abs(circle.Radius * 2 - 9.18) < 1e-6, circle.Radius
    )
    w.click(
        [x for x in d.findChildren(QtWidgets.QPushButton) if x.text().replace("&", "") == "OK"][0]
    )


g_check.done = lambda: dialog() is None
g_check.done_what = "the Parameters dialog closed"


steps = st.start_steps("BookParamsSketch") + [p_setup, r_rect, r_c1, r_c2, r_done]
steps += [a_dim, a_pick, a_place, a_type, a_check]
steps += [b_dim, b_pick, b_place, b_type_s, b_list, b_finish, b_check]
steps += [c_open, c_shown, c_check]
steps += [d_circle, d_center, d_hover, d_type, d_check, d_open, d_sum, d_sum_check]
steps += [
    e_open,
    refusal("Head_Lenght", "Did you mean Head_Length?", "typo"),
    refusal("Width = 3", "already exists", "exists"),
    refusal("Height = Head_Lenght", "no parameter named", "bad_value"),
    refusal("Head_Length +", "not a value", "broken"),
    refusal("30 deg", "is an angle, not a length", "angle"),
    e_esc,
    e_unchanged,
]
steps += [f_select, f_delete, f_check, f_undo, f_undone, f_redo, f_redone]
steps += [g_finish, g_open, g_type, g_check]

h.run("book_params_sketch", steps, paced_by="state")
