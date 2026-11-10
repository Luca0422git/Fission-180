# SPDX-License-Identifier: LGPL-2.1-or-later
"""The arrow keys in a sketch's value boxes move the typing caret, not the view (Luca,
2026-11-02: "when typing in sketch measurement windows, the arrow keys should move the
typing indicator. currently it moves the view").

Fission 180's own sketch tools (Fillet, Chamfer, 3-Point Rectangle, slots...) show value boxes
that never take the keyboard: keys typed on the 3D view come to them. They had no caret, and
an arrow key went on to FreeCAD's 3D view, which pans with the arrow keys.

Two corners of two lines each: (10, 10) and (60, 10).

A  MODIFY > Fillet, the corner (10, 10), the pointer out: the R box shows. Type
   15, Left, 2: "125" (the 2 went in before the 5), the caret drawn after the 2; the view
   did not move. Home, End, Backspace ("12"), Left, Delete ("1"), 0 ("10"), Up and Down:
   the view never moved. Enter: a fillet of radius 10.
B  Fillet again (Enter was its OK), the corner (60, 10), the pointer out: the R box shows
   the radius. Left: that value is typed into, the caret one place before its end; the view
   did not move. Esc, Esc.
C  FreeCAD's own fields keep working: Line (L), a first click, type 12, Left: the caret moves
   in the length field, the view does not move. Esc, Esc. 2-Point Rectangle, a first
   corner, type 12, Left: the same.
D  The dimension box: Sketch Dimension (D) on the line (60, 10)-(100, 10), placed below it:
   the box opens; type 8, Left: the caret moves in the box, the view does not move; Esc.
"""

import FreeCAD as App
from PySide import QtCore, QtWidgets

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st

V = App.Vector
s = st.s


def view_unmoved(label):
    h.view_still()
    h.check("%s: the view did not move" % label, h.view_key() == s["cam"], (s["cam"], h.view_key()))


def box(name="radius"):
    from fission180 import sketch_draw

    t = st.tool()
    if t is None:
        return None
    return t.boxes.widgets.get(name) if isinstance(t, sketch_draw.DrawTool) else None


def typing():
    t = st.tool()
    return (t.boxes.typing, getattr(t.boxes, "caret", None)) if t is not None else (None, None)


def field_caret():
    w = QtWidgets.QApplication.focusWidget()
    if not isinstance(w, QtWidgets.QAbstractSpinBox):
        return None
    edit = w.findChild(QtWidgets.QLineEdit)
    return edit.cursorPosition() if edit is not None else None


def corners():
    import Part
    import Sketcher

    sk = st.sketch()
    for x in (10.0, 60.0):
        a = sk.addGeometry(Part.LineSegment(V(x, 10, 0), V(x + 40, 10, 0)))
        b = sk.addGeometry(Part.LineSegment(V(x, 10, 0), V(x, 40, 0)))
        sk.addConstraint(Sketcher.Constraint("Coincident", a, 1, b, 1))
    App.ActiveDocument.recompute()
    s["n"] = len(sk.Geometry)
    h.fit(iso=False)


# == A ==================================================================================
def a_fillet():
    si.menu_item("MODIFY", "Fillet")


def a_corner():
    h.check("A Fission 180's Fillet runs", st.tool_title() == "Fillet", st.tool_title())
    st.click(V(10, 10, 0))


def a_size():
    h.check("A the corner is picked", st.tool() is not None and len(st.tool().corners) == 1)
    st.hover(V(16, 16, 0))


def a_type():
    b = box()
    h.check("A the R box shows", b is not None and b.isVisible(), st.box_texts())
    s["cam"] = h.view_key()
    st.keys("15")


def a_left():
    h.check("A typed 15", typing() == ("15", 2), typing())
    si.key(QtCore.Qt.Key_Left)


def a_left_check():
    view_unmoved("A Left")
    h.check("A Left moved the caret before the 5", typing() == ("15", 1), typing())
    st.keys("2")


def a_insert_check():
    h.check("A the 2 went in at the caret: 125", typing() == ("125", 2), typing())
    b = box()
    h.check("A the box shows R 125", b is not None and b.text() == "R 125", b and b.text())
    h.check(
        "A the caret is drawn after the 2", b is not None and b.caret == len("R 12"), b and b.caret
    )
    h.shot("A-caret")
    si.key(QtCore.Qt.Key_Home)


def a_home():
    h.check("A Home: the caret at the start", typing() == ("125", 0), typing())
    si.key(QtCore.Qt.Key_End)


def a_end():
    h.check("A End: the caret at the end", typing() == ("125", 3), typing())
    si.key(QtCore.Qt.Key_Backspace)


def a_backspace():
    h.check("A Backspace takes out the 5", typing() == ("12", 2), typing())
    si.key(QtCore.Qt.Key_Left)
    si.key(QtCore.Qt.Key_Delete)


def a_delete():
    h.check("A Left, Delete takes out the 2", typing() == ("1", 1), typing())
    st.keys("0")
    si.key(QtCore.Qt.Key_Up)
    si.key(QtCore.Qt.Key_Down)


def a_up_down():
    view_unmoved("A Up / Down while typing")
    h.check("A 10 typed", typing() == ("10", 2), typing())
    view_unmoved("A after all the keys")
    si.key(QtCore.Qt.Key_Return)


def a_made():
    sk = st.sketch()
    arcs = [g for g in sk.Geometry[s["n"] :] if g.TypeId == "Part::GeomArcOfCircle"]
    h.check(
        "A Enter made a fillet of radius 10", len(arcs) == 1 and st.near(arcs[0].Radius, 10.0), arcs
    )
    st.sketch_ok("A")


# == B ==================================================================================
def b_open():
    h.check("B Enter (OK) ended the Fillet", st.tool() is None, st.tool_title())
    si.menu_item("MODIFY", "Fillet")


def b_corner():
    h.check("B Fillet runs again", st.tool_title() == "Fillet", st.tool_title())
    st.click(V(60, 10, 0))


def b_size():
    st.hover(V(66, 16, 0))


def b_left():
    b = box()
    s["shown"] = b.text()[len("R ") :] if b is not None else None
    h.check("B the R box shows the radius", bool(s["shown"]), st.box_texts())
    s["cam"] = h.view_key()
    si.key(QtCore.Qt.Key_Left)


def b_check():
    view_unmoved("B Left")
    shown = s["shown"] or ""
    h.check(
        "B Left types into the shown value, the caret one place before its end",
        typing() == (shown, len(shown) - 1),
        (typing(), shown),
    )
    st.esc()
    st.esc()


# == C ==================================================================================
def c_line():
    h.check("C no tool left", st.tool() is None, st.tool_title())
    st.hover(V(-40, -20, 0))
    h.press("l")


def c_first():
    st.click(V(-40, -20, 0))


def c_size():
    st.hover(V(-20, -10, 0))
    s["cam"] = h.view_key()
    st.keys("12")


def c_left():
    s["caret"] = field_caret()
    h.check(
        "C the length field has the keyboard",
        s["caret"] is not None,
        h.describe(QtWidgets.QApplication.focusWidget()),
    )
    si.key(QtCore.Qt.Key_Left)


def c_check():
    view_unmoved("C Line, Left")
    h.check(
        "C Left moved the caret in FreeCAD's length field",
        s["caret"] is not None and field_caret() == s["caret"] - 1,
        (s["caret"], field_caret()),
    )
    st.esc()
    st.esc()


def c_rect():
    st.hover(V(-60, -40, 0))
    h.ribbon("2-Point Rectangle")


def c_rect_first():
    st.click(V(-60, -40, 0))


def c_rect_size():
    st.hover(V(-40, -25, 0))
    s["cam"] = h.view_key()
    st.keys("12")


def c_rect_left():
    s["caret"] = field_caret()
    h.check(
        "C the rectangle's field has the keyboard",
        s["caret"] is not None,
        h.describe(QtWidgets.QApplication.focusWidget()),
    )
    si.key(QtCore.Qt.Key_Left)


def c_rect_check():
    view_unmoved("C Rectangle, Left")
    h.check(
        "C Left moved the caret in FreeCAD's field",
        s["caret"] is not None and field_caret() == s["caret"] - 1,
        (s["caret"], field_caret()),
    )
    st.esc()
    st.esc()


# == D ==================================================================================
def d_dimension():
    st.hover(V(80, 20, 0))
    h.press("d")


def d_line():
    st.click(V(80, 10, 0))


def d_place():
    st.click(V(80, 2, 0))


def d_type():
    sess = st.session()
    h.check("D the dimension box is open", sess is not None and sess.editor is not None)
    s["cam"] = h.view_key()
    st.keys("8")
    si.key(QtCore.Qt.Key_Left)


def d_check():
    view_unmoved("D the dimension box, Left")
    sess = st.session()
    edit = sess.editor.edit if sess is not None and sess.editor is not None else None
    h.check(
        "D Left moved the caret in the box",
        edit is not None and edit.cursorPosition() == 0,
        edit and (edit.text(), edit.cursorPosition()),
    )
    st.esc()


h.run(
    "sketch_value_box_keys",
    st.start_steps("ValueBoxKeys")
    + [
        corners,
        a_fillet,
        a_corner,
        a_size,
        a_type,
        a_left,
        a_left_check,
        a_insert_check,
        a_home,
        a_end,
        a_backspace,
        a_delete,
        a_up_down,
        a_made,
        b_open,
        b_corner,
        b_size,
        b_left,
        b_check,
        c_line,
        c_first,
        c_size,
        c_left,
        c_check,
        c_rect,
        c_rect_first,
        c_rect_size,
        c_rect_left,
        c_rect_check,
        d_dimension,
        d_line,
        d_place,
        d_type,
        d_check,
    ],
    paced_by="state",
)
