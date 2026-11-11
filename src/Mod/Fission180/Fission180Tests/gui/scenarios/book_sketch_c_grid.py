# SPDX-License-Identifier: LGPL-2.1-or-later
"""Wave 7, sketch-c: Fusion's Snap puts every free point on a grid crossing.

sketch-a (wave 7) found that the book parity report was wrong about Fusion here ("Fusion
would place them where clicked"): with Snap to Grid on (Fusion's default) the pointer goes
from one grid crossing to the next (Lynda, "Snap to grid": "By default, Snap to Grid is
enabled ... as I move my cursor, it snaps to the grid's intersection"), to the MINOR lines
(Autodesk forum: "major lines at 5 mm with 20 subdivisions in order to snap your sketch
geometry every .25 mm"), and sketch geometry comes before the grid (Autodesk forum: "the
line is in the sketch and has snap priority over the grid"). sketch-a kept a pull of 8
screen pixels; this is Fusion's rule (sketch_infer "GridSnapFull", on by default; the test
harness switches it off for the scenarios written before, this one switches it on).

The book's grid: Fixed, Major Grid Spacing 50 mm, Minor Subdivisions 5: a line every 10 mm.
About 0.15 mm per pixel, so a grid line every 67 pixels.

  A  Line: a click 27 px right of and 22 px above the crossing (-30, 10), a click 30 px left
     of and 25 px below (20, 30): one line from (-30, 10) to (20, 30), exactly
  B  what the pointer infers comes first: a line from the END of that line (clicked a few
     pixels off) starts on the end exactly, not on a grid crossing ... (the end is one);
     a line to the MIDDLE of the first line, (-5, 20), which is no grid crossing, ends there;
     a line ended ON the first line 7 pixels from its middle ends on the line where it was
     clicked, not on the middle (the middle's reach is its triangle, about 5 pixels)
  C  a typed value comes first: Line, a click near (-30, -20), the pointer moved to the
     right, 37 typed: the line is 37 long (its end is on no grid line)
  D  Fission 180's own 2-Point Circle: both clicks off the crossings (-20, -40) and (10, -40):
     the circle runs through them exactly
  E  Snap unticked in the Sketch Palette: a click between the lines stays where it was
     clicked; ticked again
  F  an inch design (Adaptive): the lines the grid draws are whole inches or fifths of them
     (the base is one inch), and a free point lands on such a crossing
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide6 import QtCore

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st
from Fission180Tests.gui import x_input as x

V = App.Vector
s = st.s


def sk():
    return st.sketch()


def off(point, dx, dy):
    """The widget pixel `dx` right of and `dy` above the sketch point."""
    p = h.screen_point(st.g(point))
    return QtCore.QPoint(p.x() + dx, p.y() - dy)


def click_px(pos):
    x.click(pos)
    h.settle()


def new(kind):
    return [
        g
        for i, g in enumerate(sk().Geometry)
        if i >= s["n"] and g.TypeId == kind and not sk().getConstruction(i)
    ]


def near(p, xy, tol=1e-6):
    return abs(p.x - xy[0]) <= tol and abs(p.y - xy[1]) <= tol


def stop_tool():
    st.esc()
    st.esc()
    Gui.Selection.clearSelection()


def book_grid():
    from fission180 import grid_ui, sketch_infer

    h.check("the X server takes test input (XTEST)", x.available())
    App.ParamGet(sketch_infer.PARAMS).SetBool("GridSnapFull", True)
    h.check("Fusion's full grid snap is on", bool(sketch_infer.setting("GridSnapFull")))
    grid_ui.put("Adaptive", False)
    grid_ui.put("MajorSpacing", 50.0)
    grid_ui.put("Subdivisions", 5)
    grid_ui.apply_subdivisions()
    grid_ui.apply_to_sketch(sk())
    vp = sk().ViewObject
    size = float(getattr(vp.GridSize, "Value", vp.GridSize))
    h.check("the book's grid (Fixed, 50 mm, 5) has a line every 10 mm", abs(size - 10) < 1e-9, size)
    view = h.view()
    view.viewTop()
    cam = view.getCameraNode()
    cam.height.setValue(115.0)
    cam.position.setValue((0, 0, 100))
    h.view_still()
    s["mm"] = si.mm_per_pixel(sk())
    h.check("the view shows about 0.15 mm per pixel", 0.12 < s["mm"] < 0.18, s["mm"])


# == A ======================================================================================
def a_line():
    s["n"] = sk().GeometryCount
    h.press("l")


def a_first():
    click_px(off(V(-30, 10, 0), 27, 22))


def a_second():
    click_px(off(V(20, 30, 0), -30, -25))


def a_check():
    stop_tool()
    lines = new("Part::GeomLineSegment")
    h.check("A the two clicks drew one line", len(lines) == 1, len(lines))
    if lines:
        g = lines[0]
        h.check(
            "A a click 27 px / 22 px off a grid crossing starts ON the crossing (-30, 10)",
            near(g.StartPoint, (-30, 10)),
            g.StartPoint,
        )
        h.check(
            "A ...and the second click ends on (20, 30)", near(g.EndPoint, (20, 30)), g.EndPoint
        )


# == B ======================================================================================
def b_line():
    s["n"] = sk().GeometryCount
    h.press("l")


def b_first():
    click_px(off(V(40, -10, 0), 20, 18))


def b_middle():
    click_px(off(V(-5, 20, 0), 3, -2))  # the middle of the first line: no grid crossing


def b_check():
    stop_tool()
    lines = new("Part::GeomLineSegment")
    h.check("B one line", len(lines) == 1, len(lines))
    if lines:
        g = lines[0]
        h.check(
            "B it starts on the crossing (40, -10)", near(g.StartPoint, (40, -10)), g.StartPoint
        )
        h.check(
            "B it ends on the MIDDLE of the first line (-5, 20): what is inferred comes first",
            near(g.EndPoint, (-5, 20)),
            g.EndPoint,
        )


def b2_line():
    s["n"] = sk().GeometryCount
    s["cons"] = len(sk().Constraints)
    h.press("l")


def b2_first():
    click_px(off(V(40, 30, 0), -22, 19))


def b2_beside_the_middle():
    # ON the first line, 7 pixels along it from its middle: aimed at the line, not at the
    # middle (the book parity report, Drone: such an end "snapped to the MIDPOINT")
    g = sk().Geometry[0]
    d = g.EndPoint - g.StartPoint
    d.normalize()
    s["aim"] = V(-5, 20, 0) + d * (7 * s["mm"])
    click_px(off(s["aim"], 0, 0))


def b2_check():
    import Part

    stop_tool()
    lines = new("Part::GeomLineSegment")
    h.check("B one more line", len(lines) == 1, len(lines))
    if lines:
        end = lines[0].EndPoint
        first = sk().Geometry[0]
        gap = first.toShape().distToShape(Part.Vertex(end))[0]
        h.check("B a click on the line 7 px from its middle ends ON the line", gap < 1e-6, gap)
        h.check(
            "B ...where it was clicked, not on the middle",
            (end - V(-5, 20, 0)).Length > 3 * s["mm"],
            end,
        )
        kinds = [c.Type for c in sk().Constraints[s["cons"] :]]
        h.check(
            "B ...held by point-on-line, not by a midpoint constraint",
            "Symmetric" not in kinds,
            kinds,
        )


# == C ======================================================================================
def c_line():
    s["n"] = sk().GeometryCount
    h.press("l")


def c_first():
    click_px(off(V(-30, -20, 0), 12, -9))


def c_move():
    st.move(V(5, -19.8, 0))
    h.settle()


def c_type():
    si.type_text("37")


def c_check():
    stop_tool()
    lines = new("Part::GeomLineSegment")
    h.check("C one line", len(lines) == 1, len(lines))
    if lines:
        g = lines[0]
        h.check(
            "C it starts on the crossing (-30, -20)", near(g.StartPoint, (-30, -20)), g.StartPoint
        )
        h.check(
            "C 37 typed: it is 37 long (the grid does not move it)", abs(g.length() - 37) < 1e-6
        )


# == D ======================================================================================
def d_tool():
    s["n"] = sk().GeometryCount
    si.menu_item("CREATE", "2-Point Circle")


def d_first():
    h.check("D 2-Point Circle runs", st.tool_title() == "2-Point Circle", st.tool_title())
    click_px(off(V(-20, -40, 0), -25, 20))


def d_second():
    click_px(off(V(10, -40, 0), 24, -21))


def d_check():
    stop_tool()
    circles = new("Part::GeomCircle")
    h.check("D one circle", len(circles) == 1, len(circles))
    if circles:
        g = circles[0]
        h.check(
            "D Fission 180's own tool: through the crossings (-20, -40) and (10, -40)",
            near(g.Center, (-5, -40)) and abs(g.Radius - 15) < 1e-6,
            (g.Center, g.Radius),
        )


# == E ======================================================================================
def e_snap_off():
    si.palette_click("Fission180Palette_snap")


def e_line():
    from fission180 import sketch_mode

    h.check("E Snap is unticked", not sketch_mode.option("snap"))
    s["n"] = sk().GeometryCount
    h.press("l")


def e_first():
    s["want"] = si.sketch_at(sk(), off(V(30, -30, 0), 27, 22))
    click_px(off(V(30, -30, 0), 27, 22))


def e_second():
    click_px(off(V(45, -45, 0), 20, 0))


def e_check():
    stop_tool()
    lines = new("Part::GeomLineSegment")
    h.check("E one line", len(lines) == 1, len(lines))
    if lines:
        p = lines[0].StartPoint
        tol = 1.5 * s["mm"]
        h.check(
            "E with Snap off the click stays where it was clicked",
            abs(p.x - s["want"].x) <= tol
            and abs(p.y - s["want"].y) <= tol
            and not near(p, (30, -30), 1.0),
            (p, s["want"]),
        )
    si.palette_click("Fission180Palette_snap")


# == F ======================================================================================
def f_inches():
    from fission180 import browser_ui, grid_ui, sketch_mode

    h.check("F Snap is ticked again", sketch_mode.option("snap"))
    grid_ui.reset()
    names = App.ActiveDocument.getEnumerationsOfProperty("UnitSystem")
    inch = next(i for i, n in enumerate(names) if "Imperial decimal" in n)
    browser_ui.set_units(App.ActiveDocument, inch)
    grid_ui.apply_subdivisions()
    grid_ui.apply_to_sketch(sk())
    vp = sk().ViewObject
    size = float(getattr(vp.GridSize, "Value", vp.GridSize))
    h.check(
        "F an inch design: the adaptive grid starts from one inch", abs(size - 25.4) < 1e-9, size
    )
    h.check("F ...and is adaptive", bool(vp.GridAuto))
    s["n"] = sk().GeometryCount
    h.press("l")


def f_first():
    click_px(off(V(-40, 40, 0), 7, 5))


def f_second():
    click_px(off(V(-10, 45, 0), -6, 8))


def f_check():
    from fission180 import sketch_infer

    stop_tool()
    lines = new("Part::GeomLineSegment")
    h.check("F one line", len(lines) == 1, len(lines))
    grid = sketch_infer._grid_size(st.session())
    fifths = round(grid / 5.08, 6) if grid else 0
    h.check(
        "F the grid's lines are fifths of an inch apart, or whole multiples (0.2 in, 1 in, 5 in)",
        bool(grid) and abs(fifths - round(fifths)) < 1e-6,
        grid,
    )
    if lines and grid:
        for name, p in (("start", lines[0].StartPoint), ("end", lines[0].EndPoint)):
            on = all(abs(v / grid - round(v / grid)) < 1e-6 for v in (p.x, p.y))
            h.check("F the line's %s is on a crossing of the inch grid" % name, on, (p, grid))
    from fission180 import browser_ui, grid_ui

    browser_ui.set_units(App.ActiveDocument, 0)
    grid_ui.reset()
    st.sketch_ok("at the end")


h.run(
    "book_sketch_c_grid",
    st.start_steps("BookSketchCGrid")
    + [
        book_grid,
        a_line,
        a_first,
        a_second,
        a_check,
        b_line,
        b_first,
        b_middle,
        b_check,
        b2_line,
        b2_first,
        b2_beside_the_middle,
        b2_check,
        c_line,
        c_first,
        c_move,
        c_type,
        c_check,
        d_tool,
        d_first,
        d_second,
        d_check,
        e_snap_off,
        e_line,
        e_first,
        e_second,
        e_check,
        f_inches,
        f_first,
        f_second,
        f_check,
    ],
    paced_by="state",
)
