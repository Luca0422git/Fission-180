# SPDX-License-Identifier: LGPL-2.1-or-later
"""Wave 7, sketch-c: a parameter's name typed into the value boxes while drawing.

params' hand-over (book parity report, Metric Bolt / Drone): "FreeCAD's own Line, Circle and
Rectangle tools take numbers only in their boxes", and "Fission 180's own sketch tools take
`=name`" (the "=" was needed: a letter typed first was a tool's shortcut).

A design with the parameters Length = 30 mm, Wide = 18 mm and Dia = 12 mm; a sketch on XY.

  A  Line (L, FreeCAD's tool): a click, the pointer moved to the right; `L` typed: the text
     box for a name opens over FreeCAD's length box and the list offers Length; `e` typed;
     Enter fills Length in, Enter takes it: a line 30 long whose length dimension follows
     Length. ONE Ctrl+Z takes the line with its dimension; Ctrl+Y brings both back.
     Length changed to 44: the line is 44 long.
  B  2-Point Rectangle (R): a click, `Wide` + Tab, `Length / 2` + Enter: 18 wide, 22 high,
     both dimensions follow their formulas
  C  Center Diameter Circle (C): a click, `Dia` + Enter: a circle 12 across that follows Dia
  D  a typo (`Lenght`): the text box stays, marked, and says there is no such parameter
     (with the name it nearly was); Esc closes the text box only, the tool still runs
  E  a letter that starts no parameter is still a tool's key: `c` while the Line tool's box
     has the keyboard starts the Circle tool
  F  Fission 180's own 2-Point Circle: a click, the pointer moved, `Di` typed with no "=" in
     front: its box takes the letters and the list offers Dia; Enter fills it in, Enter draws
     the circle: 12 across, following Dia, in ONE undo step
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide6 import QtCore, QtTest, QtWidgets

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st

V = App.Vector
s = st.s


def doc():
    return App.ActiveDocument


def sk():
    return st.sketch()


def names():
    return st.session().names


def shown():
    from fission180 import parameters_complete

    return parameters_complete.shown()


def formulas():
    from fission180 import sketch_named_dimensions

    return sketch_named_dimensions.formulas(sk())


def type_chars(text):
    """Type one key after the other to whatever has the keyboard then (a text box that
    opens on the first letter takes the rest)."""
    for ch in text:
        target = QtWidgets.QApplication.focusWidget() or h.gl_widget()
        if ch == "\n":
            QtTest.QTest.keyClick(target, QtCore.Qt.Key_Return)
        elif ch == "\t":
            QtTest.QTest.keyClick(target, QtCore.Qt.Key_Tab)
        else:
            QtTest.QTest.keyClicks(target, ch)
        QtWidgets.QApplication.processEvents()
    h.settle()


def new_geo(kind):
    return [
        i
        for i, g in enumerate(sk().Geometry)
        if i >= s["geo"] and g.TypeId == kind and not sk().getConstruction(i)
    ]


def new_dims():
    kinds = ("Distance", "DistanceX", "DistanceY", "Radius", "Diameter")
    return [
        (i, c.Type, round(abs(c.Value), 6))
        for i, c in enumerate(sk().Constraints)
        if i >= s["cons"] and c.Type in kinds
    ]


def mark():
    s["geo"] = len(sk().Geometry)
    s["cons"] = len(sk().Constraints)


def end_tool():
    st.esc()
    st.esc()
    Gui.Selection.clearSelection()


def setup():
    from fission180 import parameters

    d = doc()
    d.openTransaction("parameters")
    parameters.add_user(d, "Length", "mm", "30")
    parameters.add_user(d, "Wide", "mm", "18")
    parameters.add_user(d, "Dia", "mm", "12")
    d.commitTransaction()
    d.recompute()
    h.fit(iso=False)


# == A ======================================================================================
def a_line():
    mark()
    h.press("l")


def a_first():
    st.click(V(-60, 30, 0))


def a_move():
    st.move(V(-25, 30.4, 0))
    h.settle()


def a_letter():
    focus = QtWidgets.QApplication.focusWidget()
    h.check(
        "A FreeCAD's length box has the keyboard",
        isinstance(focus, QtWidgets.QAbstractSpinBox),
        type(focus).__name__,
    )
    type_chars("L")


def a_box():
    box = names().box
    h.check(
        "A a text box for the name opened over FreeCAD's box", box is not None and box.isVisible()
    )
    h.check(
        "A ...holding the letter typed", box is not None and box.text() == "L", box and box.text()
    )
    h.check("A the list offers Length", "Length" in shown(), shown())
    type_chars("e")


def a_fill():
    h.check("A the list still offers Length", shown() == ["Length"], shown())
    type_chars("\n")


def a_take():
    box = names().box
    h.check(
        "A Enter filled the name in", box is not None and box.text() == "Length", box and box.text()
    )
    type_chars("\n")


def a_drawn():
    lines = new_geo("Part::GeomLineSegment")
    h.check("A one line was drawn", len(lines) == 1, lines)
    if lines:
        g = sk().Geometry[lines[0]]
        h.check("A ...30 long (Length)", abs(g.length() - 30) < 1e-6, g.length())
        s["line"] = lines[0]
    dims = new_dims()
    h.check("A its length dimension was added", len(dims) == 1, dims)
    bound = {i: f for i, f in formulas().items() if i >= s["cons"]}
    h.check("A ...and follows Length", list(bound.values()) == ["Length"], bound)
    end_tool()
    st.undo()


def a_undone():
    h.check("A ONE Ctrl+Z took the line back", len(sk().Geometry) == s["geo"], len(sk().Geometry))
    h.check("A ...with its dimension", len(sk().Constraints) == s["cons"], len(sk().Constraints))
    st.redo()


def a_redone():
    lines = new_geo("Part::GeomLineSegment")
    h.check("A Ctrl+Y brought the line back", len(lines) == 1, lines)
    bound = {i: f for i, f in formulas().items() if i >= s["cons"]}
    h.check("A ...still following Length", list(bound.values()) == ["Length"], bound)
    from fission180 import parameters

    d = doc()
    d.openTransaction("Change Parameters")
    parameters.set_user(d, "Length", "44")
    d.commitTransaction()
    d.recompute()


def a_follows():
    g = sk().Geometry[s["line"]]
    h.check("A Length changed to 44: the line is 44 long", abs(g.length() - 44) < 1e-6, g.length())


# == B ======================================================================================
def b_rect():
    mark()
    h.press("r")


def b_first():
    st.click(V(-60, -10, 0))


def b_move():
    st.move(V(-30, -32, 0))
    h.settle()


def b_wide():
    type_chars("Wide\t")


def b_high():
    h.check("B Tab took Wide (no text box left)", names().box is None)
    type_chars("Length / 2\n")


def b_drawn():
    lines = new_geo("Part::GeomLineSegment")
    h.check("B a rectangle was drawn", len(lines) == 4, lines)
    xs, ys = [], []
    for i in lines:
        g = sk().Geometry[i]
        xs += [g.StartPoint.x, g.EndPoint.x]
        ys += [g.StartPoint.y, g.EndPoint.y]
    if xs:
        size = (round(max(xs) - min(xs), 6), round(max(ys) - min(ys), 6))
        h.check("B ...18 wide (Wide) and 22 high (Length / 2)", size == (18.0, 22.0), size)
    bound = sorted(f for i, f in formulas().items() if i >= s["cons"])
    h.check("B both dimensions follow their formulas", bound == ["Length / 2", "Wide"], bound)
    end_tool()


# == C ======================================================================================
def c_circle():
    mark()
    h.press("c")


def c_centre():
    st.click(V(30, 20, 0))


def c_move():
    st.move(V(41, 23, 0))
    h.settle()


def c_dia():
    type_chars("Dia\n")


def c_drawn():
    circles = new_geo("Part::GeomCircle")
    h.check("C one circle was drawn", len(circles) == 1, circles)
    if circles:
        r = sk().Geometry[circles[0]].Radius
        h.check("C ...12 across (Dia)", abs(2 * r - 12) < 1e-6, 2 * r)
    bound = [f for i, f in formulas().items() if i >= s["cons"]]
    h.check("C its dimension follows Dia", len(bound) == 1 and "Dia" in bound[0], bound)
    end_tool()


# == D ======================================================================================
def d_line():
    mark()
    h.press("l")


def d_first():
    st.click(V(20, -20, 0))


def d_move():
    st.move(V(50, -19.7, 0))
    h.settle()


def d_typo():
    type_chars("Lenght\n")


def d_refused():
    box = names().box
    h.check("D the text box stays open on a name that does not exist", box is not None)
    h.check("D ...marked", box is not None and bool(box.property("bad")))
    said = si.tooltip()
    h.check(
        "D ...and says so, with the name it nearly was", "Lenght" in said and "Length" in said, said
    )
    h.check("D nothing was drawn", len(sk().Geometry) == s["geo"], len(sk().Geometry))
    QtTest.QTest.keyClick(box, QtCore.Qt.Key_Escape)
    h.settle()


def d_escaped():
    from fission180 import recent

    h.check("D Esc closed the text box", names().box is None)
    h.check("D ...and the Line tool still runs", si.drawing(), recent.running_tool())


# == E ======================================================================================
def e_key():
    st.move(V(52, -19, 0))
    h.settle()
    type_chars("c")


def e_circle():
    from fission180 import recent

    h.check("E no parameter starts with c: no text box", names().box is None)
    h.check(
        "E ...the key started the Circle tool",
        recent.running_tool() == "Sketcher_CreateCircle",
        recent.running_tool(),
    )
    end_tool()


# == F ======================================================================================
def f_tool():
    mark()
    si.menu_item("CREATE", "2-Point Circle")


def f_first():
    h.check("F 2-Point Circle runs", st.tool_title() == "2-Point Circle", st.tool_title())
    st.click(V(-10, 45, 0))


def f_move():
    st.hover(V(4, 45, 0))


def f_letters():
    st.keys("Di")
    h.settle()


def f_list():
    tool = st.tool()
    h.check(
        "F the box took the letters without an = in front",
        tool is not None and tool.boxes.typing == "Di",
        tool and tool.boxes.typing,
    )
    h.check("F the list offers Dia", shown() == ["Dia"], shown())
    s["undo"] = len(doc().UndoNames)
    st.keys("\n")
    h.settle()


def f_filled():
    tool = st.tool()
    h.check(
        "F Enter filled the name in",
        tool is not None and tool.boxes.typing == "Dia",
        tool and tool.boxes.typing,
    )
    h.check("F ...and closed the list", shown() == [], shown())
    st.keys("\n")
    h.settle()


def f_drawn():
    circles = new_geo("Part::GeomCircle")
    h.check("F one circle was drawn", len(circles) == 1, circles)
    if circles:
        r = sk().Geometry[circles[0]].Radius
        h.check("F ...12 across (Dia)", abs(2 * r - 12) < 1e-6, 2 * r)
    bound = [f for i, f in formulas().items() if i >= s["cons"]]
    h.check("F its dimension follows Dia", len(bound) == 1 and "Dia" in bound[0], bound)
    end_tool()
    st.undo()


def f_undone():
    h.check("F ONE Ctrl+Z took the circle with its dimension", len(sk().Geometry) == s["geo"])
    h.check("F ...and its formula", len(sk().Constraints) == s["cons"], len(sk().Constraints))
    st.sketch_ok("at the end")


h.run(
    "book_sketch_c_names",
    st.start_steps("BookSketchCNames")
    + [
        setup,
        a_line,
        a_first,
        a_move,
        a_letter,
        a_box,
        a_fill,
        a_take,
        a_drawn,
        a_undone,
        a_redone,
        a_follows,
        b_rect,
        b_first,
        b_move,
        b_wide,
        b_high,
        b_drawn,
        c_circle,
        c_centre,
        c_move,
        c_dia,
        c_drawn,
        d_line,
        d_first,
        d_move,
        d_typo,
        d_refused,
        d_escaped,
        e_key,
        e_circle,
        f_tool,
        f_first,
        f_move,
        f_letters,
        f_list,
        f_filled,
        f_drawn,
        f_undone,
    ],
    paced_by="state",
)
