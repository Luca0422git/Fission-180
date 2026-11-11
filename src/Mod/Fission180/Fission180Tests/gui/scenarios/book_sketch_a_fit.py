# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fit (F6) in a sketch and in a design that has only a sketch (wave 7, the book parity
report, Classic Donut: "Fit / Home when the design has only a sketch: zoomed out to a 24 m
tall view, the 40 mm circle was a dot"; "F6 inside a sketch frames the grid as well").

The book's set-up: the Layout Grid on (Grid and Snaps), the grid Fixed at 50 mm with 5
subdivisions, a sketch on the Front plane with a 40 mm circle 40 mm from the origin.

  A  F6 in the open sketch frames the circle: it fills a good part of the view (the view is
     between 40 and 200 mm tall, not metres), and is on the screen
  B  F6 again and again: the view stays as it is (it used to zoom out further every time:
     the layout grid is four views wide and was framed too)
  C  Finish Sketch, F6: the design has only the sketch; the view frames it (same size)
  D  the navigation bar's Fit and three more F6: still the same view
  E  with the Layout Grid off the result is the same (the grid never counted)
"""

import math

import FreeCAD as App
from PySide import QtCore

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import sketch_tools_steps as st

V = App.Vector
s = st.s


def view_height():
    """How many millimetres of the design the view shows from top to bottom."""
    view = h.view()
    cam = view.getCameraNode()
    if view.getCameraType() == "Orthographic":
        return float(cam.height.getValue())
    angle = float(cam.heightAngle.getValue())
    return 2.0 * float(cam.focalDistance.getValue()) * math.tan(angle / 2.0)


def circle_on_screen():
    sk = App.ActiveDocument.getObject(s["name"])
    centre = sk.getGlobalPlacement().multVec(V(40, 0, 0))
    pos = h.screen_point(centre)
    return h.gl_widget().rect().contains(pos)


def f6():
    h.press(QtCore.Qt.Key_F6)
    h.view_still()


def framed(where):
    height = view_height()
    h.check(
        "%s: the view frames the 40 mm circle (40 to 200 mm tall)" % where,
        40 <= height <= 200,
        height,
    )
    h.check("%s: the circle is on the screen" % where, circle_on_screen())
    return height


def book_grid():
    from fission180 import grid_ui

    grid_ui.put("LayoutGrid", True)
    grid_ui.put("Adaptive", False)
    grid_ui.put("MajorSpacing", 50.0)
    grid_ui.put("Subdivisions", 5)
    grid_ui.apply_subdivisions()
    grid_ui.redraw_all()
    h.check("the Layout Grid is on", grid_ui.layout_grid_on())


def pick_front():
    pl.click_square("XZ_Plane")


def draw():
    import Part

    sk = h.in_sketch()
    h.check("sketch open on the Front plane", sk is not None)
    s["name"] = sk.Name
    doc = App.ActiveDocument
    doc.openTransaction("circle")
    sk.addGeometry(Part.Circle(V(40, 0, 0), V(0, 0, 1), 20))
    doc.commitTransaction()
    doc.recompute()


# -- A, B ---------------------------------------------------------------------------------
def a_check():
    s["a"] = framed("A F6 in the sketch")
    h.shot("A-fit-in-sketch")


def b_check():
    again = framed("B F6 three more times")
    h.check(
        "B ...and the view did not zoom out", abs(again - s["a"]) <= 0.02 * s["a"], (again, s["a"])
    )


# -- C, D ---------------------------------------------------------------------------------
def finish():
    h.ribbon("Finish Sketch")


def c_check():
    s["c"] = framed("C F6 with only the finished sketch")
    h.shot("C-fit-sketch-only")


def d_navbar():
    from fission180 import commands  # noqa: F401
    import FreeCADGui as Gui

    Gui.runCommand("Std_ViewFitAll")  # what the navigation bar's Fit runs
    h.view_still()


def d_check():
    again = framed("D Fit and three more F6")
    h.check("D ...the same view", abs(again - s["c"]) <= 0.02 * s["c"], (again, s["c"]))


# -- E ------------------------------------------------------------------------------------
def e_grid_off():
    from fission180 import grid_ui

    grid_ui.put("LayoutGrid", False)
    grid_ui.redraw_all()


def e_check():
    off = framed("E with the Layout Grid off")
    h.check("E ...the grid never counted", abs(off - s["c"]) <= 0.02 * s["c"], (off, s["c"]))
    from fission180 import grid_ui

    grid_ui.reset()


h.run(
    "book_sketch_a_fit",
    [
        st.new_design("BookSketchFit"),
        book_grid,
        st.create_sketch,
        pick_front,
        draw,
        f6,
        a_check,
        f6,
        f6,
        f6,
        b_check,
        finish,
        f6,
        c_check,
        d_navbar,
        f6,
        f6,
        f6,
        d_check,
        e_grid_off,
        f6,
        e_check,
    ],
    paced_by="state",
)
