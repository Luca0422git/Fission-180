# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's Feature Options in the Sketch Palette: the running tool's types, a click switches
type mid-tool (fission180/sketch_feature_options.py, sketch_palette.FeatureOptions; Luca,
2026-11-04: "sketch objects and shapes and stuff should have their own dialoge box that lets
you change how you draw that tool. center rectangle and stuff").

A  R (2-Point Rectangle): Feature Options shows "Rectangle type" with 2-Point, 3-Point and
   Center; 2-Point is lit.
B  A click on Center: the Center Rectangle runs (lit); two clicks make a rectangle around the
   first point.
C  A click on 3-Point: Fission 180's 3-Point Rectangle runs (lit).
D  Esc: no tool, Feature Options hidden.
E  C (circle): "Circle type" with its five types; 2-Point switches to the 2-Point Circle.
F  The Line tool: Feature Options hidden (Line has no types).
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st

V = App.Vector
s = {}


def features():
    w = Gui.getMainWindow().findChild(QtWidgets.QWidget, "Fission180PaletteFeatures")
    return w


def shown():
    w = features()
    return w is not None and w.isVisible()


def button(label):
    w = features()
    return w.findChild(QtWidgets.QToolButton, "Fission180Feature_" + label.replace(" ", "_")) if w else None


def lit():
    w = features()
    if w is None:
        return []
    return [b.text() for b in w.findChildren(QtWidgets.QToolButton) if b.isVisible() and b.isChecked()]


def labels():
    w = features()
    return [b.text() for b in w.findChildren(QtWidgets.QToolButton) if b.isVisible()] if w else []


def kind():
    w = features()
    k = w.findChild(QtWidgets.QLabel, "Fission180PaletteFeaturesKind") if w else None
    return k.text() if k is not None else ""


def press(label):
    b = button(label)
    if not h.check("Feature Options has %s" % label, b is not None and b.isVisible(), labels()):
        return
    h.pointer_to(b, b.rect().center())
    QtTest.QTest.mouseClick(b, QtCore.Qt.LeftButton)
    QtWidgets.QApplication.processEvents()


def running_tool():
    from fission180 import recent

    return recent.running_tool()


def new_design():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("FeatureOptions")
    h.fit()
    Gui.getMainWindow().activateWindow()


def create_sketch():
    h.ribbon("Create Sketch")


def pick_xy():
    pl.click_square("XY_Plane")


def opened():
    s["sk"] = st.s["sk"] = h.in_sketch()
    h.check("sketch open on XY", s["sk"] is not None)
    h.fit(iso=False)
    h.check("no Feature Options while no tool runs", not shown())


def a_rect():
    st.hover(V(-40, 30, 0))
    h.press("r")


def a_shown():
    h.wait_for(shown, "Feature Options")
    h.check("A: Rectangle type", kind() == "Rectangle type", kind())
    h.check("A: its three types", labels() == ["2-Point", "3-Point", "Center"], labels())
    h.check("A: 2-Point is lit", lit() == ["2-Point"], lit())
    h.shot("A-rectangle-types")


def b_center():
    press("Center Rectangle")


def b_running():
    h.wait_for(lambda: running_tool() == "Sketcher_CreateRectangle_Center", "the Center Rectangle")
    h.wait_for(lambda: lit() == ["Center"], "Center to be lit")
    s["n"] = len(s["sk"].Geometry)


def b_c1():
    si.click(V(0, 0, 0) + V(30, 20, 0))


def b_c2():
    si.click(V(50, 30, 0))


def b_made():
    h.settle("the rectangle")
    pts = [g.StartPoint for _i, g in si.lines(s["sk"])]
    want = [V(10, 10, 0), V(50, 10, 0), V(50, 30, 0), V(10, 30, 0)]
    h.check("B: a rectangle around the first point", all(any(si.vnear(p, w, 1e-6) for p in pts) for w in want),
            pts)


def c_three():
    press("3-Point Rectangle")


def c_running():
    h.wait_for(lambda: st.tool_title() == "3-Point Rectangle", "Fission 180's 3-Point Rectangle")
    h.wait_for(lambda: lit() == ["3-Point"], "3-Point to be lit")
    h.shot("C-three-point")


def d_esc():
    st.esc()


def d_hidden():
    h.wait_for(lambda: not shown(), "Feature Options to hide")


def e_circle():
    st.hover(V(-40, 30, 0))
    h.press("c")


def e_shown():
    h.wait_for(shown, "Feature Options")
    h.check("E: Circle type", kind() == "Circle type", kind())
    h.check("E: five circle types", len(labels()) == 5, labels())
    press("2-Point Circle")


def e_two_point():
    h.wait_for(lambda: st.tool_title() == "2-Point Circle", "the 2-Point Circle")
    h.wait_for(lambda: lit() == ["2-Point"], "2-Point to be lit")
    st.esc()


def f_line():
    h.press("l")


def f_hidden():
    h.settle("the Line tool")
    h.check("F: the Line tool runs", si.drawing())
    h.wait_for(lambda: not shown(), "Feature Options to hide for Line (it has no types)")
    st.esc()


def finish():
    h.ribbon("Finish Sketch")


def end():
    h.expect_no_errors("Feature Options")


STEPS = [
    new_design, create_sketch, pick_xy, opened,
    a_rect, a_shown, b_center, b_running, b_c1, b_c2, b_made, c_three, c_running, d_esc, d_hidden,
    e_circle, e_shown, e_two_point, f_line, f_hidden, finish, end,
]

h.run("sketch_feature_options", si.watched(STEPS), paced_by="state")
