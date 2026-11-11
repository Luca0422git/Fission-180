# SPDX-License-Identifier: LGPL-2.1-or-later
"""The click that places a dimension places it (wave 7, the book parity report, Drone,
Pizza Cutter, Hot End: "Placing a dimension on top of the Y axis turned it into an Angle
constraint: the placement click is treated as a pick", "some dimensions turned into Angle
constraints or reference dimensions when the placement click touched other lines").

A sketch on the XY plane: a slanted line A, a line B, a line C between them. Real clicks
through the X server (x_input); D starts the Dimension tool.

  A  D, a click on line A (its length follows the pointer), then a click ON the sketch's Y
     axis: the dimension is placed there (one dimension between A's ends, no Angle to the
     axis), the value box opens
  B  D, a click on an end of A, a click on an end of B (the distance between them follows
     the pointer), then a click ON line C: the distance is placed (C is not picked as a
     third thing), the value box opens
  C  picking is unchanged where nothing can be placed yet: D, a click on an end of A (a
     point alone has no dimension), a click on the X axis: the axis is picked (the distance
     from the point to it follows the pointer), a click on empty space places it
"""

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_tools_steps as st
from Fission180Tests.gui import x_input as x

V = App.Vector
s = st.s


def sk():
    return App.ActiveDocument.getObject(s["name"])


def px(point):
    return h.screen_point(st.g(point))


def click(point):
    x.click(px(point))
    h.settle()


def editor():
    return st.session().editor if st.session() is not None else None


def new_cons():
    return [
        (c.Type, c.First, c.FirstPos, c.Second, c.SecondPos) for c in sk().Constraints[s["cons"] :]
    ]


def end_tool():
    st.esc()
    st.esc()
    st.esc()
    Gui.Selection.clearSelection()


def setup():
    import Part

    h.check("the X server takes test input (XTEST)", x.available())
    sketch = s["sk"]
    s["name"] = sketch.Name
    doc = App.ActiveDocument
    doc.openTransaction("setup")
    s["a"] = sketch.addGeometry(Part.LineSegment(V(-45, 12, 0), V(-15, 24, 0)))
    s["b"] = sketch.addGeometry(Part.LineSegment(V(15, -12, 0), V(40, -25, 0)))
    s["c"] = sketch.addGeometry(Part.LineSegment(V(-10, -28, 0), V(8, -12, 0)))
    doc.commitTransaction()
    doc.recompute()
    Gui.Selection.clearSelection()
    h.fit(iso=False)


def dimension():
    s["cons"] = len(sk().Constraints)
    h.press("d")


# -- A ------------------------------------------------------------------------------------
def a_pick():
    click(V(-30, 18, 0))


def a_place_on_axis():
    click(V(0, 33, 0))  # on the Y axis


def a_check():
    cons = new_cons()
    h.check("A one dimension was placed", len(cons) == 1, cons)
    # (wave 7's merge: D is Fission 180's own Sketch Dimension. A slanted line's dimension is
    # its length while the pointer is beside it and, like Fusion's, the vertical or
    # horizontal distance between its ends once the pointer is past them: the click on the
    # axis is up and to the right of the line's end, nearer its side: vertical)
    h.check(
        "A it is a dimension of the line (between its two ends, no Angle to the axis)",
        len(cons) == 1
        and cons[0][0] in ("Distance", "DistanceX", "DistanceY")
        and cons[0][1] == s["a"]
        and cons[0][3] in (s["a"], -2000),  # (between its two ends, or the line itself)
        cons,
    )
    h.check("A ...the vertical one (the pointer is past the line's end)", cons[0][0] == "DistanceY")
    h.check("A the value box is open", editor() is not None)
    h.shot("A-placed-on-the-axis")
    end_tool()


# -- B ------------------------------------------------------------------------------------
def b_pick_1():
    click(V(-15, 24, 0))


def b_pick_2():
    click(V(15, -12, 0))


def b_place_on_line():
    line = sk().Geometry[s["c"]]
    click((line.StartPoint + line.EndPoint) * 0.5)  # on line C


def b_check():
    cons = new_cons()
    kinds = [c[0] for c in cons]
    h.check("B one dimension was placed", len(cons) == 1, cons)
    ends = {(cons[0][1], cons[0][2]), (cons[0][3], cons[0][4])} if cons else set()
    h.check(
        "B it is the distance between the two ends (line C was not picked)",
        len(cons) == 1 and kinds[0].startswith("Distance") and ends == {(s["a"], 2), (s["b"], 1)},
        cons,
    )
    h.check("B the value box is open", editor() is not None)
    end_tool()


# -- C ------------------------------------------------------------------------------------
def c_pick_point():
    click(V(-45, 12, 0))


def c_pick_axis():
    click(V(-30, 0, 0))  # the X axis: nothing follows the pointer yet, so it is picked


def c_place():
    click(V(-55, 5, 0))


def c_check():
    cons = new_cons()
    h.check("C one dimension was placed", len(cons) == 1, cons)
    named = {cons[0][1], cons[0][3]} if cons else set()
    h.check(
        "C from the point to the X axis (the axis was picked)",
        len(cons) == 1 and s["a"] in named and bool(named & {-1, -2}),
        cons,
    )
    end_tool()
    st.sketch_ok("at the end")


h.run(
    "book_sketch_a_dimension",
    st.start_steps("BookSketchDimension")
    + [
        setup,
        dimension,
        a_pick,
        a_place_on_axis,
        a_check,
        dimension,
        b_pick_1,
        b_pick_2,
        b_place_on_line,
        b_check,
        dimension,
        c_pick_point,
        c_pick_axis,
        c_place,
        c_check,
    ],
    paced_by="state",
)
