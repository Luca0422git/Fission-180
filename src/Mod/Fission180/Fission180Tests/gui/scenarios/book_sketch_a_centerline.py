# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's Centerline line type (wave 7, the book parity report, Metric Bolt: "There is no
Centerline linetype ... dimensions to the axis are radii, not diameters; making the bottom
line construction opens the profile so Revolve finds no profile").

A sketch on the XY plane with the half profile of a turned part: a 30 x 10 rectangle whose
bottom side is level, 5 mm above the X axis. Clicks go through the X server (x_input).

  A  the bottom line selected, Sketch Palette > Linetype > Centerline: it is a centerline
     (drawn dashed on FreeCAD's discontinuous layer), still a normal line (not
     construction), and the rectangle is still one closed profile
  B  D, a click on the top-right corner, a click on the centerline, a click to place: the
     value box shows the DIAMETER (20: twice the 10 mm to the centerline); 24 typed: the
     corner is 12 mm from the centerline; the dimension is drawn across the centerline
     (to a hidden mirror point)
  C  Ctrl+Z twice: the value, then the dimension with its hidden helper, are gone
  D  nothing selected, Centerline clicked: new lines are centerlines (it says so); a line
     drawn with L is one; clicked again: the next line is a normal line
  E  that second centerline made a normal line again (selected, Centerline); one Ctrl+Z
     makes it a centerline again
  F  Finish Sketch, CREATE > Revolve: the profile is taken, and the sketch's one centerline
     is the axis by itself (no pick); OK: a cylinder 30 long with the radius the profile had
  G  saved, closed and opened: the centerline is still one
"""

import math
import os
import tempfile

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st
from Fission180Tests.gui import x_input as x

V = App.Vector
s = st.s


def doc():
    return App.ActiveDocument


def sk():
    return doc().getObject(s["name"])


def cl():
    from fission180 import sketch_centerline

    return sketch_centerline


def helpers():
    from fission180 import sketch_draw_helpers

    return sketch_draw_helpers


def px(point):
    return h.screen_point(st.g(point))


def click(point, held=()):
    x.click(px(point), held=held)
    h.settle()


def editor():
    return st.session().editor if st.session() is not None else None


def stop_tool():
    st.esc()
    st.esc()
    Gui.Selection.clearSelection()


def setup():
    import Part
    import Sketcher

    h.check("the X server takes test input (XTEST)", x.available())
    sketch = s["sk"]
    s["name"] = sketch.Name
    pts = [V(0, 5, 0), V(30, 5, 0), V(30, 15, 0), V(0, 15, 0)]
    doc().openTransaction("setup")
    lines = [sketch.addGeometry(Part.LineSegment(pts[i], pts[(i + 1) % 4])) for i in range(4)]
    cons = [Sketcher.Constraint("Coincident", lines[i], 2, lines[(i + 1) % 4], 1) for i in range(4)]
    cons += [
        Sketcher.Constraint("Horizontal", lines[0]),
        Sketcher.Constraint("Horizontal", lines[2]),
        Sketcher.Constraint("Vertical", lines[1]),
        Sketcher.Constraint("Vertical", lines[3]),
        Sketcher.Constraint("DistanceX", -1, 1, lines[0], 1, 0.0),
        Sketcher.Constraint("DistanceY", -1, 1, lines[0], 1, 5.0),
        Sketcher.Constraint("Distance", lines[0], 30.0),
    ]
    sketch.addConstraint(cons)
    doc().commitTransaction()
    doc().recompute()
    s["lines"] = lines
    Gui.Selection.clearSelection()
    h.fit(iso=False)


# -- A ------------------------------------------------------------------------------------
def a_select():
    click(V(15, 5, 0))
    names = [
        n.rsplit(".", 1)[-1] for sel in Gui.Selection.getSelectionEx() for n in sel.SubElementNames
    ]
    h.check("A the bottom line is selected", names == ["Edge1"], names)


def centerline_button():
    si.palette_click("Fission180PaletteCenterline")


def a_check():
    bottom = s["lines"][0]
    h.check("A the bottom line is a centerline", cl().lines(sk()) == [bottom], cl().lines(sk()))
    h.check("A ...still a normal line (not construction)", not sk().getConstruction(bottom))
    layer = helpers().layer_of(sk().GeometryFacadeList[bottom])
    h.check("A ...drawn dashed (FreeCAD's discontinuous layer)", layer == 1, layer)
    wires = sk().Shape.Wires
    h.check(
        "A the rectangle is still one closed profile",
        len(wires) == 1 and wires[0].isClosed(),
        len(wires),
    )
    h.check(
        "A the palette's button is not left pressed (no drawing mode)",
        not si.palette().centerline.isChecked(),
    )
    h.shot("A-centerline")


# -- B ------------------------------------------------------------------------------------
def b_dimension():
    s["cons"] = len(sk().Constraints)
    s["geos"] = len(sk().Geometry)

    h.press("d")


def b_corner():
    click(V(30, 15, 0))


def b_line():
    click(V(12, 5, 0))


def b_place():
    click(V(-8, 10, 0))


def b_box():
    ed = editor()
    h.check("B the value box is open", ed is not None)
    if ed is None:
        return
    text = ed.edit.text()
    h.check(
        "B it shows the diameter (20 mm), not the 10 mm to the centerline",
        text.startswith("20"),
        text,
    )
    c = sk().Constraints[ed.index]
    h.check(
        "B the dimension runs from the corner to its mirror point",
        c.Type == "Distance" and abs(c.Value - 20) < 1e-6,
        (c.Type, c.Value),
    )
    helper = len(sk().Geometry) - 1
    h.check("B one helper point was added", len(sk().Geometry) == s["geos"] + 1, len(sk().Geometry))
    h.check(
        "B ...on the hidden layer", helper in helpers().hidden(sk()), sorted(helpers().hidden(sk()))
    )
    p = sk().getPoint(helper, 1)
    h.check(
        "B ...the corner's mirror image across the centerline", (p - V(30, -5, 0)).Length < 1e-6, p
    )
    sym = [k for k in sk().Constraints if k.Type == "Symmetric"]
    h.check(
        "B the constraint that holds it is not drawn",
        len(sym) == 1 and sym[0].InVirtualSpace,
        len(sym),
    )
    si.type_text("24")


def b_typed():
    h.check("B the box closed", editor() is None)
    top = sk().Geometry[s["lines"][2]]
    h.check(
        "B 24 typed: the top is 12 mm from the centerline",
        abs(top.StartPoint.y - 17) < 1e-6,
        top.StartPoint,
    )
    st.sketch_ok("B")
    stop_tool()
    h.shot("B-diameter")


# -- C ------------------------------------------------------------------------------------
def undo():
    st.undo()


def c_value_back():
    top = sk().Geometry[s["lines"][2]]
    h.check("C Ctrl+Z took the 24 back", abs(top.StartPoint.y - 15) < 1e-6, top.StartPoint)


def c_dimension_back():
    for _ in range(3):  # (FreeCAD's dimension tool records a step of its own first)
        if len(sk().Constraints) <= s["cons"]:
            break
        st.undo()
        h.settle()
    h.check("C the dimension is gone", len(sk().Constraints) == s["cons"], len(sk().Constraints))
    h.check("C ...with its hidden helper", len(sk().Geometry) == s["geos"], len(sk().Geometry))
    h.check(
        "C the bottom line is still the centerline",
        cl().lines(sk()) == [s["lines"][0]],
        cl().lines(sk()),
    )


# -- D ------------------------------------------------------------------------------------
def d_mode_on():
    Gui.Selection.clearSelection()
    si.palette_click("Fission180PaletteCenterline")


def d_mode_check():
    from fission180 import sketch_mode

    h.check(
        "D with nothing selected the button turns the drawing mode on",
        sketch_mode.centerline_mode(),
    )
    h.check("D ...and says so", "New lines are centerlines" in si.tooltip(), si.tooltip())
    s["geos"] = len(sk().Geometry)
    h.press("l")


def d_1():
    click(V(3, 19, 0))


def d_2():
    click(V(27, 19, 0))


def d_drawn():
    stop_tool()
    new = list(range(s["geos"], len(sk().Geometry)))
    h.check("D one line drawn", len(new) == 1, new)
    s["second"] = new[0] if new else None
    h.check("D ...a centerline", s["second"] in cl().lines(sk()), cl().lines(sk()))
    h.check("D the palette's button shows the mode", si.palette().centerline.isChecked())


def d_mode_off():
    si.palette_click("Fission180PaletteCenterline")


def d_normal_line():
    from fission180 import sketch_mode

    h.check("D clicked again: the mode is off", not sketch_mode.centerline_mode())
    s["geos"] = len(sk().Geometry)
    h.press("l")


def d_3():
    click(V(3, 23, 0))


def d_4():
    click(V(27, 23, 0))


def d_normal_drawn():
    stop_tool()
    new = list(range(s["geos"], len(sk().Geometry)))
    h.check(
        "D the next line is a normal line",
        len(new) == 1 and new[0] not in cl().lines(sk()),
        cl().lines(sk()),
    )


# -- E ------------------------------------------------------------------------------------
def e_select():
    click(V(15, 19, 0))


def e_check():
    h.check(
        "E the second centerline is a normal line again",
        cl().lines(sk()) == [s["lines"][0]],
        cl().lines(sk()),
    )
    layer = helpers().layer_of(sk().GeometryFacadeList[s["second"]])
    h.check("E ...drawn solid again", layer == 0, layer)


def e_undone():
    h.check(
        "E Ctrl+Z makes it a centerline again", s["second"] in cl().lines(sk()), cl().lines(sk())
    )
    st.redo()


def e_cleanup():
    """The two extra lines go (only the profile's centerline is left for Revolve)."""
    h.check("E Ctrl+Y: a normal line again", cl().lines(sk()) == [s["lines"][0]], cl().lines(sk()))
    doc().openTransaction("tidy")
    sk().delGeometries([s["second"], s["second"] + 1])
    doc().commitTransaction()
    doc().recompute()


# -- F ------------------------------------------------------------------------------------
def finish():
    h.ribbon("Finish Sketch")


def f_revolve():
    h.ribbon("Revolve")


def f_panel():
    from fission180 import taskui

    panel = taskui.current()
    h.check("F the Revolve dialog is open", panel is not None)
    if panel is None:
        return
    h.check("F the profile is taken", len(panel.profiles) == 1, panel.profiles)
    axis = panel.axis
    h.check(
        "F the centerline is the axis by itself",
        axis is not None and axis[0].Name == s["name"] and axis[1].startswith("Edge"),
        axis and (axis[0].Name, axis[1]),
    )
    h.caught_up(panel)
    h.shot("F-revolve")
    h.task_button("OK")


def f_done():
    want = math.pi * 10.0**2 * 30.0
    got = h.solid_volume()
    h.check("F a cylinder of radius 10, 30 long", abs(got - want) < 1e-3 * want, (got, want))


# -- G ------------------------------------------------------------------------------------
def g_save():
    path = os.path.join(tempfile.mkdtemp(prefix="f180-centerline-"), "centerline.FCStd")
    s["path"] = path
    doc().saveAs(path)
    App.closeDocument(doc().Name)


def g_open():
    App.openDocument(s["path"])


g_open.done = (
    lambda: App.ActiveDocument is not None and App.ActiveDocument.getObject(s["name"]) is not None
)
g_open.done_what = "the saved design is open"


def g_check():
    h.check(
        "G saved and opened: the centerline is still one",
        cl().lines(sk()) == [s["lines"][0]],
        cl().lines(sk()),
    )
    layer = helpers().layer_of(sk().GeometryFacadeList[s["lines"][0]])
    h.check("G ...still dashed", layer == 1, layer)


h.run(
    "book_sketch_a_centerline",
    st.start_steps("BookSketchCenterline")
    + [
        setup,
        a_select,
        centerline_button,
        a_check,
        b_dimension,
        b_corner,
        b_line,
        b_place,
        b_box,
        b_typed,
        undo,
        c_value_back,
        c_dimension_back,
        d_mode_on,
        d_mode_check,
        d_1,
        d_2,
        d_drawn,
        d_mode_off,
        d_normal_line,
        d_3,
        d_4,
        d_normal_drawn,
        e_select,
        centerline_button,
        e_check,
        undo,
        e_undone,
        e_cleanup,
        finish,
        f_revolve,
        f_panel,
        f_done,
        g_save,
        g_open,
        g_check,
    ],
    paced_by="state",
)
