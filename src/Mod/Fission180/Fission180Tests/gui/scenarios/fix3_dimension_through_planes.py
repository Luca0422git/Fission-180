# SPDX-License-Identifier: LGPL-2.1-or-later
"""Wave 7, fix-3: Sketch Dimension (D) and the constraint tools pick the sketch line under the
pointer where an origin plane lies edge-on over the sketch's axis, with the Origin shown.

The book's Tensegrity (replay_04_tensegrity, step arm_base_driven, failed once): the arm's
sketch is on the Front plane and the Origin is shown (for the holes' Mirror). D on the arm's
bottom line, clicked at its middle, where the YZ plane (and the Z axis) lie edge-on over the
sketch's Y axis: the click picked the sketch's AXIS, a hair nearer the pointer than the line,
and the next click made no dimension ("click the point or line to measure from the axis").
In Fusion a command picks the sketch's curve there: the origin's planes and axes come after it
(selection priority).

Each click here is aimed on the plane's line, OFF_PX pixels off the sketch line (inside the
pick radius, where a hand lands): the axis is then always the nearer one, so before the fix
every such click took the axis (deterministically: the Parallel refused, no dimension, an
angle to the axis).

The Origin's planes are drawn as squares about 55 pixels wide by the origin, whatever the
zoom: the lines are drawn there (the view at 10 pixels a millimetre).

  A  Parallel: the level line, then the slanted one (the one to turn), each clicked on the YZ
     plane's line
  B  D on one line there, placed below it: its length; typed 25
  C  D line to line there (now parallel): the gap; typed 3
  D  D line to axis: the X axis (where the XY plane lies edge-on), then the line on the YZ
     plane's line: their distance; typed 2
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import book_sketch_b_steps as b
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import replay_b_steps as r
from Fission180Tests.gui import sketch_tools_steps as st
from Fission180Tests.gui import timeline_input as tl

V = App.Vector
s = st.s
OFF_PX = 2.0  # how far off the sketch line the click lands (pixels; the pick radius is 5)


def near(a, c, tol=1e-6):
    return abs(a - c) <= tol * max(1.0, abs(c))


def view_map():
    from fission180.sketch_infer import _ViewMap

    gl = h.gl_widget()
    return _ViewMap(st.session(), gl, QtCore.QPointF(gl.width() / 2.0, gl.height() / 2.0))


def glyphs_under(pos):
    """Names of the origin's planes and axes FreeCAD finds under widget pixel `pos` (within
    2 pixels: a plane seen edge-on is a line one pixel wide)."""
    from fission180 import profile_pick

    gl = h.gl_widget()
    pixel = profile_pick.coin_pixel(gl, QtCore.QPoint(pos.x(), pos.y() + 1))
    return sorted(
        {
            obj.Name
            for obj, _short, _p in profile_pick.under(h.view(), pixel, 2)
            if profile_pick.is_glyph(obj)
        }
    )


def click_pixel(pos, what):
    """A real click on widget pixel `pos`: the pointer comes there in a few steps and rests
    until the view drew (as st.click does for a sketch point), then press and release."""
    for d in (6, 3, 1, 0):
        h.move(QtCore.QPoint(pos.x() + d, pos.y() - d))
    h.view_drawn()
    QtTest.QTest.mouseClick(h.gl_widget(), QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, pos)
    QtWidgets.QApplication.processEvents()
    h.state["last_click"] = "%s at %s; origin glyphs there: %s" % (
        what,
        (pos.x(), pos.y()),
        glyphs_under(pos),
    )


def aim(point, plane, what):
    """Click the sketch point `point` moved OFF_PX pixels up on the screen: on the edge-on
    `plane`'s line when `point` lies on it. Checks that the plane is under the pointer there
    (the situation this scenario is about)."""
    vm = view_map()
    found = vm.pixel_for((point.x, point.y + OFF_PX * vm.px))
    pos = QtCore.QPoint(int(found.x()), int(found.y()))
    under = glyphs_under(pos)
    h.check(
        "%s: the %s, seen edge-on, is under the pointer" % (what, plane),
        any(name.startswith(plane) for name in under),
        under,
    )
    click_pixel(pos, what)


def line_y(name, x=0.0):
    """The y of sketch line `name` at x."""
    g = b.geo(name)
    a, e = g.StartPoint, g.EndPoint
    t = (x - a.x) / (e.x - a.x)
    return a.y + (e.y - a.y) * t


def on_line(name, x=0.0):
    return V(x, line_y(name, x), 0)


def picks():
    t = st.tool()
    return list(t.picks) if t is not None else None


def last():
    c = b.sk().Constraints[-1]
    return c.Type, c.First, c.Second, c.Value, c.Driving


# -- a sketch on the Front plane, the Origin shown ---------------------------------------------
def create_sketch():
    h.ribbon("Create Sketch")


def pick_front():
    pl.click_square("XZ_Plane")


pick_front.done = lambda: h.in_sketch() is not None
pick_front.done_what = "the sketch on the Front plane is open"


def sketch_open():
    sketch = h.in_sketch()
    s["sk"] = sketch
    normal = sketch.getGlobalPlacement().Rotation.multVec(V(0, 0, 1))
    h.check("the sketch lies on the Front plane", near(abs(normal.y), 1.0), normal)
    tl.click_eye("Origin")  # the book shows the Origin (for a Mirror)


def origin_shown():
    import Part

    doc = App.ActiveDocument
    shown = [
        o.Name
        for o in doc.Objects
        if o.TypeId == "App::Plane" and o.ViewObject is not None and o.ViewObject.Visibility
    ]
    h.check(
        "the Origin's planes are shown",
        any(n.startswith("YZ_Plane") for n in shown)
        and any(n.startswith("XY_Plane") for n in shown),
        shown,
    )
    s["a"] = b.add(Part.LineSegment(V(-15, 2, 0), V(15, 2, 0)))
    s["b"] = b.add(Part.LineSegment(V(-15, 3.5, 0), V(15, 5.5, 0)))
    b.con("Horizontal", s["a"])  # (the level line stays level: Parallel turns the other)
    doc.recompute()
    b.clean("the two lines")
    r.look_at(st.g(V(0, 3, 0)), h.gl_widget().height() / 10.0)  # 10 pixels a millimetre
    h.shot("origin")


# == A  Parallel through the YZ plane ===========================================================
def par_menu():
    b.forget_said()
    b.menu("Parallel")


def par_first():
    h.check("Parallel runs", st.tool_title() == "Parallel", st.tool_title())
    aim(on_line("a"), "YZ_Plane", "Parallel, the level line")


def par_second():
    h.check(
        "Parallel: the level line is picked (not the Y axis under the YZ plane)",
        picks() == [(s["a"], 0)],
        (picks(), b.said()),
    )
    aim(on_line("b"), "YZ_Plane", "Parallel, the slanted line")


def par_check():
    h.check(
        "Parallel: the two lines are parallel",
        b.has("Parallel", s["a"], s["b"]),
        (b.cons(), b.said()),
    )
    g = b.geo("b")
    h.check("Parallel: the slanted line turned level", near(g.StartPoint.y, g.EndPoint.y), g)
    b.clean("Parallel")
    r.end_tool()


# == B  D on one line, clicked on the YZ plane's line =============================================
def d_key():
    h.press("d")


def d_line_pick():
    h.check("D starts Sketch Dimension", st.tool_title() == "Sketch Dimension", st.tool_title())
    s["count"] = len(b.sk().Constraints)
    aim(on_line("a"), "YZ_Plane", "D, the level line")


def d_line_place():
    h.check(
        "D: the line is picked (not the Y axis under the YZ plane)",
        picks() == [(s["a"], 0)],
        picks(),
    )
    st.click(on_line("a") - V(0, 1, 0))  # below it, on the YZ plane's line


def d_line_check():
    cons = b.sk().Constraints
    h.check("D: one dimension added", len(cons) == s["count"] + 1, b.cons()[s["count"] :])
    kind, first, _second, value, driving = last()
    length = b.geo("a").length()
    h.check(
        "D: the line's length, driving (the replay's arm_base_driven)",
        kind in ("Distance", "DistanceX") and first == s["a"] and near(value, length) and driving,
        (last(), length),
    )
    h.check("D: the value box is open", r.editor() is not None)
    r.type_value("25")


def d_line_value():
    g = b.geo("a")
    h.check("typed 25: the line is 25 long", near(g.length(), 25.0), g.length())
    b.clean("one line")


# == C  D line to line, both clicked on the YZ plane's line ====================================
def d_two_first():
    s["count"] = len(b.sk().Constraints)
    aim(on_line("a"), "YZ_Plane", "D, the first line")


def d_two_second():
    h.check("D: the first line is picked", picks() == [(s["a"], 0)], picks())
    aim(on_line("b"), "YZ_Plane", "D, the second line")


def d_two_place():
    h.check(
        "D: both lines are picked (not the Y axis)",
        picks() == [(s["a"], 0), (s["b"], 0)],
        picks(),
    )
    s["gap"] = abs(line_y("b") - line_y("a"))
    st.click(on_line("b") + V(0, 1, 0))  # above them, on the YZ plane's line


def d_two_check():
    cons = b.sk().Constraints
    h.check("D: one dimension added", len(cons) == s["count"] + 1, b.cons()[s["count"] :])
    kind, first, second, value, driving = last()
    h.check(
        "D: the gap between the two lines, driving",
        kind == "Distance"
        and {first, second} == {s["a"], s["b"]}
        and near(value, s["gap"])
        and driving,
        (last(), s["gap"]),
    )
    h.check("D: the value box is open", r.editor() is not None)
    r.type_value("3")


def d_two_value():
    gap = line_y("b") - line_y("a")
    h.check("typed 3: the lines are 3 apart", near(gap, 3.0), gap)
    b.clean("two lines")


# == D  D line to axis: the X axis (under the XY plane), the line on the YZ plane's line =======
def on_x_axis_under(plane):
    """A point of the sketch's X axis where the edge-on `plane` is under the pointer (aim()'s
    pixel), clear of the origin point and of the YZ plane and Z axis drawn edge-on through it:
    found on the screen, not assumed (fix-5: x = 3 mm had the XY plane under the pointer
    here, nothing on GitHub's renderer, whose origin squares end nearer the origin). 3 mm
    first, then nearer the origin, then farther; none: 3 mm (aim() then says what is there)."""
    vm = view_map()
    for tenths in list(range(30, 14, -1)) + list(range(31, 61)):
        x = tenths / 10.0
        found = vm.pixel_for((x, OFF_PX * vm.px))
        under = glyphs_under(QtCore.QPoint(int(found.x()), int(found.y())))
        if any(n.startswith(plane) for n in under) and not any(
            n.startswith(("YZ_Plane", "Z_Axis")) for n in under
        ):
            return V(x, 0, 0)
    return V(3, 0, 0)


def d_axis_first():
    s["count"] = len(b.sk().Constraints)
    aim(on_x_axis_under("XY_Plane"), "XY_Plane", "D, the X axis")


def d_axis_second():
    h.check("D: the X axis is picked", picks() == [(-1, 0)], picks())
    aim(on_line("a"), "YZ_Plane", "D, the line after the axis")


def d_axis_place():
    h.check("D: the X axis and the line are picked", picks() == [(-1, 0), (s["a"], 0)], picks())
    s["height"] = line_y("a")
    st.click(V(-6, s["height"] / 2.0, 0))  # left of the origin


def d_axis_check():
    cons = b.sk().Constraints
    h.check("D: one dimension added", len(cons) == s["count"] + 1, b.cons()[s["count"] :])
    kind, first, second, value, driving = last()
    h.check(
        "D: the line's distance from the X axis, driving",
        kind == "DistanceY"
        and s["a"] in (first, second)
        and near(value, abs(s["height"]))
        and driving,
        (last(), s["height"]),
    )
    h.check("D: the value box is open", r.editor() is not None)
    r.type_value("2")


def d_axis_value():
    h.check("typed 2: the line is 2 above the X axis", near(line_y("a"), 2.0), line_y("a"))
    gap = line_y("b") - line_y("a")
    h.check("the lines are still 3 apart", near(gap, 3.0), gap)
    b.clean("line to axis")
    h.shot("dimensioned")
    r.end_tool()


def finish():
    h.ribbon("Finish Sketch")


finish.done = lambda: h.in_sketch() is None
finish.done_what = "the sketch is finished"


def finished():
    h.check("the sketch closed", h.in_sketch() is None)
    Gui.Selection.clearSelection()


h.run(
    "fix3_dimension_through_planes",
    [
        st.new_design("Fix3DimensionThroughPlanes"),
        create_sketch,
        pick_front,
        sketch_open,
        origin_shown,
        par_menu,
        par_first,
        par_second,
        par_check,
        d_key,
        d_line_pick,
        d_line_place,
        d_line_check,
        d_line_value,
        d_two_first,
        d_two_second,
        d_two_place,
        d_two_check,
        d_two_value,
        d_axis_first,
        d_axis_second,
        d_axis_place,
        d_axis_check,
        d_axis_value,
        finish,
        finished,
    ],
    paced_by="state",
)
