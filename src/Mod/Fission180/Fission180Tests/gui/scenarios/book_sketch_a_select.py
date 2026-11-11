# SPDX-License-Identifier: LGPL-2.1-or-later
"""Selecting in an open sketch the way the book says it (wave 7, the book parity report:
"Ctrl+click does not add to a sketch selection", "a plain click on a second curve ADDS it",
"double-clicking a line does not chain-select the triangle" in Circular Pattern).

Every click here goes through the X server (x_input: the XTEST extension), as a person's
mouse and keyboard do: the keys are really held, Qt works out the double-click itself.

A sketch on the XY plane: three circles, a triangle of three joined lines, two loose lines.

  A  a plain click on a circle selects it; a plain click on a second circle REPLACES the
     selection (Fusion; FreeCAD's sketch added it)
  B  Ctrl+click adds a circle; Ctrl+click on a selected one takes it out again
  C  Shift+click adds; Shift+click on something selected keeps it (Shift never removes)
  D  a plain click on one of several selected curves leaves only that one; a click on empty
     space clears the selection
  E  a double-click on a line of the triangle selects its three lines; Ctrl+click then adds
     a circle to them
  F  the book's "hold Ctrl, click the two lines, Parallel": two lines picked with Ctrl, then
     CONSTRAINTS > Parallel constrains them; with nothing selected the Parallel tool waits
     and two plain clicks give it its two lines (a running tool's clicks add)
  G  Circular Pattern (the book's Tensegrity step): a double-click on a line of the triangle
     takes the whole triangle as the Objects; one more click on a line drops just that line
  H  a press on a circle that drags still drags it (the click rule leaves a drag alone)
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st
from Fission180Tests.gui import x_input as x

V = App.Vector
s = st.s


def names():
    found = set()
    for sel in Gui.Selection.getSelectionEx():
        if sel.Object is s.get("sk"):
            for n in sel.SubElementNames:
                found.add(n.rsplit(".", 1)[-1])
    return found


def edge(i):
    return "Edge%d" % (i + 1)


def px(point):
    return h.screen_point(st.g(point))


def real_click(point, held=()):
    x.click(px(point), held=held)
    h.settle()


def setup():
    import Part
    import Sketcher

    h.check("the X server takes test input (XTEST)", x.available())
    sk = s["sk"]
    App.ActiveDocument.openTransaction("setup")
    s["c"] = [
        sk.addGeometry(Part.Circle(V(60, 40, 0), V(0, 0, 1), 8)),
        sk.addGeometry(Part.Circle(V(60, 10, 0), V(0, 0, 1), 8)),
        sk.addGeometry(Part.Circle(V(60, -20, 0), V(0, 0, 1), 8)),
    ]
    a = sk.addGeometry(Part.LineSegment(V(-60, -10, 0), V(-20, -10, 0)))
    b = sk.addGeometry(Part.LineSegment(V(-20, -10, 0), V(-40, 25, 0)))
    c = sk.addGeometry(Part.LineSegment(V(-40, 25, 0), V(-60, -10, 0)))
    sk.addConstraint(Sketcher.Constraint("Coincident", a, 2, b, 1))
    sk.addConstraint(Sketcher.Constraint("Coincident", b, 2, c, 1))
    sk.addConstraint(Sketcher.Constraint("Coincident", c, 2, a, 1))
    s["tri"] = [a, b, c]
    s["l1"] = sk.addGeometry(Part.LineSegment(V(-10, 40, 0), V(25, 46, 0)))
    s["l2"] = sk.addGeometry(Part.LineSegment(V(-10, 55, 0), V(25, 58, 0)))
    App.ActiveDocument.commitTransaction()
    App.ActiveDocument.recompute()
    Gui.Selection.clearSelection()
    h.fit(iso=False)


# -- A ------------------------------------------------------------------------------------
def a_first():
    real_click(V(68, 40, 0))
    h.check("A a click selects the circle", names() == {edge(s["c"][0])}, sorted(names()))


def a_second():
    real_click(V(68, 10, 0))
    h.check(
        "A a plain click on a second circle replaces the selection",
        names() == {edge(s["c"][1])},
        sorted(names()),
    )


# -- B ------------------------------------------------------------------------------------
def b_ctrl_adds():
    real_click(V(68, -20, 0), held=("ctrl",))
    h.check(
        "B Ctrl+click adds the third circle",
        names() == {edge(s["c"][1]), edge(s["c"][2])},
        sorted(names()),
    )


def b_ctrl_removes():
    real_click(V(68, 10, 0), held=("ctrl",))
    h.check(
        "B Ctrl+click on a selected circle takes it out",
        names() == {edge(s["c"][2])},
        sorted(names()),
    )


# -- C ------------------------------------------------------------------------------------
def c_shift_adds():
    real_click(V(68, 40, 0), held=("shift",))
    h.check(
        "C Shift+click adds",
        names() == {edge(s["c"][2]), edge(s["c"][0])},
        sorted(names()),
    )


def c_shift_keeps():
    real_click(V(68, 40, 0), held=("shift",))
    h.check(
        "C Shift+click on a selected circle keeps it (Shift never removes)",
        names() == {edge(s["c"][2]), edge(s["c"][0])},
        sorted(names()),
    )


# -- D ------------------------------------------------------------------------------------
def d_plain_on_selected():
    real_click(V(68, 40, 0))
    h.check(
        "D a plain click on one of two selected circles leaves only it",
        names() == {edge(s["c"][0])},
        sorted(names()),
    )


def d_empty():
    real_click(V(20, -45, 0))
    h.check("D a click on empty space clears the selection", names() == set(), sorted(names()))


# -- E ------------------------------------------------------------------------------------
def e_double():
    x.double_click(px(V(-40, -10, 0)))
    h.settle()
    h.check(
        "E a double-click on a line selects the triangle's three lines",
        names() == {edge(i) for i in s["tri"]},
        sorted(names()),
    )
    h.shot("E-chain")


def e_ctrl_circle():
    real_click(V(68, 10, 0), held=("ctrl",))
    h.check(
        "E Ctrl+click adds a circle to the chain",
        names() == {edge(i) for i in s["tri"]} | {edge(s["c"][1])},
        sorted(names()),
    )
    st.esc()


# -- F ------------------------------------------------------------------------------------
def f_pick_two():
    Gui.Selection.clearSelection()
    real_click(V(7.5, 43, 0))
    real_click(V(7.5, 56.5, 0), held=("ctrl",))
    h.check(
        "F two lines picked with Ctrl held",
        names() == {edge(s["l1"]), edge(s["l2"])},
        sorted(names()),
    )
    s["cons"] = len(s["sk"].Constraints)


def f_parallel():
    si.menu_item("CONSTRAINTS", "Parallel")


def f_parallel_check():
    sk = s["sk"]
    added = [c.Type for c in sk.Constraints[s["cons"] :]]
    h.check("F Parallel constrained the two selected lines", added == ["Parallel"], added)
    a, b = sk.Geometry[s["l1"]], sk.Geometry[s["l2"]]
    da, db = a.EndPoint - a.StartPoint, b.EndPoint - b.StartPoint
    h.check("F ...and they are parallel", st.angle_deg(da, db) < 1e-6, st.angle_deg(da, db))
    st.undo()


def f_tool_first():
    Gui.Selection.clearSelection()
    s["cons"] = len(s["sk"].Constraints)
    si.menu_item("CONSTRAINTS", "Parallel")


def f_tool_click_a():
    real_click(V(7.5, 43, 0))


def f_tool_click_b():
    real_click(V(7.5, 56.5, 0))


def f_tool_check():
    st.esc()
    st.esc()
    added = [c.Type for c in s["sk"].Constraints[s["cons"] :]]
    h.check(
        "F the Parallel tool started first takes two plain clicks (a tool's clicks add)",
        added == ["Parallel"],
        added,
    )


# -- G ------------------------------------------------------------------------------------
def g_pattern():
    Gui.Selection.clearSelection()
    si.menu_item("CREATE", "Circular Pattern")


def g_double():
    h.check("G Circular Pattern runs", st.tool_title() == "Circular Pattern", st.tool_title())
    x.double_click(px(V(-40, -10, 0)))
    h.settle()
    tool = st.tool()
    got = sorted(tool.objects) if tool is not None else None
    h.check(
        "G a double-click on a line takes the whole triangle as the Objects",
        got == sorted(s["tri"]),
        got,
    )
    h.shot("G-pattern-chain")


def g_single_drops():
    real_click(V(-30, 7.5, 0))
    tool = st.tool()
    got = sorted(tool.objects) if tool is not None else None
    h.check(
        "G one more click on a line drops just that line",
        got == sorted([s["tri"][0], s["tri"][2]]),
        got,
    )


def g_cancel():
    st.esc()
    st.esc()
    h.check("G Esc ends the pattern tool", st.tool() is None or not st.tool().active)


# -- H ------------------------------------------------------------------------------------
def h_drag():
    Gui.Selection.clearSelection()
    sk = s["sk"]
    before = sk.Geometry[s["c"][2]].Radius
    a = px(V(68, -20, 0))
    b = QtCore.QPoint(a.x() + 40, a.y())
    x.press_drag_release(a, b, steps=8)
    h.settle()
    after = sk.Geometry[s["c"][2]].Radius
    h.check("H a press on a circle that moves away drags it (bigger)", after > before + 3, after)


def done():
    st.sketch_ok("at the end")
    h.ribbon("Finish Sketch")


h.run(
    "book_sketch_a_select",
    st.start_steps("BookSketchSelect")
    + [
        setup,
        a_first,
        a_second,
        b_ctrl_adds,
        b_ctrl_removes,
        c_shift_adds,
        c_shift_keeps,
        d_plain_on_selected,
        d_empty,
        e_double,
        e_ctrl_circle,
        f_pick_two,
        f_parallel,
        f_parallel_check,
        f_tool_first,
        f_tool_click_a,
        f_tool_click_b,
        f_tool_check,
        g_pattern,
        g_double,
        g_single_drops,
        g_cancel,
        h_drag,
        done,
    ],
    paced_by="state",
)
