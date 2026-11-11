# SPDX-License-Identifier: LGPL-2.1-or-later
"""Wave 7, sketch-c: Fusion's "Scale entire sketch at first dimension" (the book parity
report, Basics: "Scale entire sketch at first dimension does not exist").

The preference is on by default; the test harness switches it off for the scenarios written
before it, this one switches it on. A sketch on the XY plane, drawn "by eye" with no
dimension: a 30 x 20 rectangle (its sides joined, level and upright) and a circle of radius
5 beside it.

  A  D, the rectangle's bottom side, placed, 60 typed: the FIRST dimension scales the whole
     sketch by 2: the rectangle is 60 x 40 and the circle has radius 10, twice as far from
     the origin; a note says so. ONE Ctrl+Z puts everything back; Ctrl+Y scales it again
  B  the second dimension changes only what it measures: D on the circle, 8 typed: the
     circle is 8 across, the rectangle still 60 x 40
  C  nothing is scaled when something in the sketch is fixed: the dimensions deleted, the
     circle fixed (Fix/Unfix), D on the rectangle's left side, 10 typed: that side is 10
     long, the bottom side still 60, the circle where it was
  D  the preference off: a fresh sketch state without dimensions or fixed curves, D, 90
     typed for the bottom side: only that side follows (the circle keeps its size)
"""

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import book_sketch_b_steps as b
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st

V = App.Vector
s = st.s
SIZES = ("Distance", "DistanceX", "DistanceY", "Radius", "Diameter")


def sk():
    return b.sk()


def geo(name):
    return sk().Geometry[s[name]]


def size():
    """(width, height) of the rectangle."""
    return round(geo("bottom").length(), 6), round(geo("left").length(), 6)


def circle():
    g = geo("circle")
    return round(g.Radius, 6), (round(g.Center.x, 6), round(g.Center.y, 6))


def mid(name):
    g = geo(name)
    return (g.StartPoint + g.EndPoint) * 0.5


def end_tool():
    st.esc()
    st.esc()
    Gui.Selection.clearSelection()


def setup():
    import Part

    from fission180 import sketch_first_dimension, sketch_infer

    App.ParamGet(sketch_infer.PARAMS).SetBool("ScaleAtFirstDimension", True)
    h.check("the preference is on", sketch_first_dimension.enabled())
    doc = App.ActiveDocument
    doc.openTransaction("setup")
    pts = [V(10, 10, 0), V(40, 10, 0), V(40, 30, 0), V(10, 30, 0)]
    lines = [b.add(Part.LineSegment(pts[i], pts[(i + 1) % 4])) for i in range(4)]
    s["bottom"], s["right"], s["top"], s["left"] = lines
    for i in range(4):
        b.con("Coincident", lines[i], 2, lines[(i + 1) % 4], 1)
    b.con("Horizontal", lines[0])
    b.con("Horizontal", lines[2])
    b.con("Vertical", lines[1])
    b.con("Vertical", lines[3])
    s["circle"] = b.add(Part.Circle(V(-20, 20, 0), V(0, 0, 1), 5))
    doc.commitTransaction()
    doc.recompute()
    Gui.Selection.clearSelection()
    view = h.view()
    view.viewTop()
    cam = view.getCameraNode()
    cam.height.setValue(260.0)
    cam.position.setValue((30, 20, 100))
    h.view_still()
    b.watch_modals()


def dimension():
    h.press("d")


# == A ======================================================================================
def a_pick():
    st.click(mid("bottom"))


def a_place():
    st.click(mid("bottom") + V(0, -8, 0))


def a_type():
    ed = st.session().editor
    h.check("A the first dimension's box is open", ed is not None and ed.just_placed)
    s["undo"] = len(b.undo_names())
    si.type_text("60")


def a_scaled():
    h.check("A 60 typed: the rectangle is 60 x 40 (twice as big)", size() == (60.0, 40.0), size())
    h.check(
        "A ...the circle too: radius 10, twice as far from the origin",
        circle() == (10.0, (-40.0, 40.0)),
        circle(),
    )
    corner = geo("bottom").StartPoint
    h.check(
        "A the rectangle's corner moved from (10, 10) to (20, 20)",
        (corner - V(20, 20, 0)).Length < 1e-6,
    )
    h.check("A a note says the whole sketch was scaled", "scaled" in si.tooltip(), si.tooltip())
    h.check("A one undo step", len(b.undo_names()) == s["undo"] + 1, b.undo_names()[:3])
    b.clean("after the scale")
    end_tool()
    st.undo()


def a_undone():
    h.check("A ONE Ctrl+Z: the rectangle is 30 x 20 again", size() == (30.0, 20.0), size())
    h.check("A ...and the circle", circle() == (5.0, (-20.0, 20.0)), circle())
    st.redo()


def a_redone():
    h.check(
        "A Ctrl+Y: scaled again", size() == (60.0, 40.0) and circle()[0] == 10.0, (size(), circle())
    )


# == B ======================================================================================
def b_pick():
    g = geo("circle")
    st.click(g.Center + V(0.6, 0.8, 0) * g.Radius)


def b_place():
    g = geo("circle")
    st.click(g.Center + V(-1, 1, 0) * (g.Radius + 6))


def b_type():
    h.check("B the second dimension's box is open", st.session().editor is not None)
    si.type_text("8")


def b_check():
    h.check("B 8 typed: the circle is 8 across", circle()[0] == 4.0, circle())
    h.check("B the rectangle is still 60 x 40", size() == (60.0, 40.0), size())
    end_tool()


# == C ======================================================================================
def c_setup():
    sketch = sk()
    doc = App.ActiveDocument
    doc.openTransaction("setup C")
    for i in reversed(range(len(sketch.Constraints))):
        if sketch.Constraints[i].Type in SIZES:
            sketch.delConstraint(i)
    b.con("Block", s["circle"])
    doc.commitTransaction()
    doc.recompute()
    s["circle_before"] = circle()
    h.press("d")


def c_pick():
    st.click(mid("left"))


def c_place():
    st.click(mid("left") + V(-8, 0, 0))


def c_type():
    h.check("C the box is open", st.session().editor is not None)
    si.type_text("10")


def c_check():
    h.check("C 10 typed: the left side is 10 long", size()[1] == 10.0, size())
    h.check(
        "C ...the bottom side still 60 (nothing was scaled: the circle is fixed)", size()[0] == 60.0
    )
    h.check("C the fixed circle did not move", circle() == s["circle_before"], circle())
    end_tool()


# == D ======================================================================================
def d_setup():
    from fission180 import sketch_first_dimension, sketch_infer

    sketch = sk()
    doc = App.ActiveDocument
    doc.openTransaction("setup D")
    for i in reversed(range(len(sketch.Constraints))):
        if sketch.Constraints[i].Type in SIZES + ("Block",):
            sketch.delConstraint(i)
    doc.commitTransaction()
    doc.recompute()
    App.ParamGet(sketch_infer.PARAMS).SetBool("ScaleAtFirstDimension", False)
    h.check("D the preference is off", not sketch_first_dimension.enabled())
    s["circle_before"] = circle()
    h.press("d")


def d_pick():
    st.click(mid("bottom"))


def d_place():
    st.click(mid("bottom") + V(0, -8, 0))


def d_type():
    si.type_text("90")


def d_check():
    h.check("D 90 typed with the preference off: the bottom side is 90", size()[0] == 90.0, size())
    h.check("D ...the left side keeps its 10", size()[1] == 10.0, size())
    h.check("D ...and the circle its size and place", circle() == s["circle_before"], circle())
    end_tool()
    b.no_modal("scale at first dimension")
    st.sketch_ok("at the end")


h.run(
    "book_sketch_c_scale",
    st.start_steps("BookSketchCScale")
    + [
        setup,
        dimension,
        a_pick,
        a_place,
        a_type,
        a_scaled,
        a_undone,
        a_redone,
        dimension,
        b_pick,
        b_place,
        b_type,
        b_check,
        c_setup,
        c_pick,
        c_place,
        c_type,
        c_check,
        d_setup,
        d_pick,
        d_place,
        d_type,
        d_check,
    ],
    paced_by="state",
)
