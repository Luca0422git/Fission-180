# SPDX-License-Identifier: LGPL-2.1-or-later
"""The Line tool and the snap the way the book uses them (wave 7, the book parity report:
"snap is far too strong", "a 45 degree driving angle appeared by itself", "press and drag at
a line's end draws no arc", "the chain stops at the origin").

Every click goes through the X server (x_input), as a person's mouse does. The grid is the
book's: Grid Settings Fixed, Major Grid Spacing 50 mm, Minor Subdivisions 5.

  A  the book's grid draws a line every 10 mm (50 / 5), not every 50
  B  L, a click 40 pixels above the X axis and one 40 pixels below it: the line's ends stay
     where they were clicked (the report: the line came out flat on the axis); a click 3
     pixels off a grid line lands on it
  C  a line drawn 2 degrees off 45 snaps to exactly 45 degrees and gets NO Angle dimension;
     a second one likewise; Ctrl+click both, Parallel: added, the sketch solves cleanly (the
     report: refused as redundant)
  D  the book's Carabiner: L, two clicks, then press on the line's end RIGHT AWAY (inside
     the double-click time) and drag: a tangent arc; the chain goes on from the arc's end;
     the same press-and-drag after a pause: an arc too; a double-click on the end with no
     drag ends the chain
  E  a chain drawn through the bare origin goes on (the click 5 pixels off the origin lands
     on it and is joined to it); a line that ends on another line ends
     the chain (Fusion: "the line continues until you click an existing sketch object"), and
     Fission 180 says so beside the pointer
"""

import math

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st
from Fission180Tests.gui import x_input as x

V = App.Vector
s = st.s


def sk():
    return s["sk"]


def px(point):
    return h.screen_point(st.g(point))


def off(point, dx, dy):
    """The widget pixel dx to the right of and dy above the sketch point."""
    at = px(point)
    return QtCore.QPoint(at.x() + dx, at.y() - dy)


def click_px(pos, held=()):
    x.click(pos, held=held)
    h.settle()


def click(point, held=()):
    click_px(px(point), held)


def lines():
    return si.lines(sk())


def new_lines():
    """(index, line) of the lines drawn since the step that noted s["n"]."""
    return [(i, line) for i, line in lines() if i >= s["n"]]


def types_on(index):
    return sorted(
        c.Type for c in sk().Constraints if index in (c.First, c.Second, getattr(c, "Third", -9))
    )


def angle_of(line):
    d = line.EndPoint - line.StartPoint
    return math.degrees(math.atan2(d.y, d.x))


def stop_tool():
    st.esc()
    st.esc()
    Gui.Selection.clearSelection()


# -- A ------------------------------------------------------------------------------------
def book_grid():
    from fission180 import grid_ui

    h.check("the X server takes test input (XTEST)", x.available())
    grid_ui.put("Adaptive", False)
    grid_ui.put("MajorSpacing", 50.0)
    grid_ui.put("Subdivisions", 5)
    grid_ui.apply_subdivisions()
    grid_ui.apply_to_sketch(sk())
    vp = sk().ViewObject
    size = float(getattr(vp.GridSize, "Value", vp.GridSize))
    h.check(
        "A the book's grid (Fixed, 50 mm, 5) has a line every 10 mm", abs(size - 10) < 1e-9, size
    )
    h.check("A ...and is not adaptive", not vp.GridAuto)
    # about 0.15 mm per pixel: 40 pixels are about 6 mm, well between two grid lines
    view = h.view()
    view.viewTop()
    cam = view.getCameraNode()
    cam.height.setValue(115.0)
    cam.position.setValue((0, 0, 100))
    h.view_still()
    s["mm"] = si.mm_per_pixel(sk())
    h.check("A the view shows about 0.15 mm per pixel", 0.12 < s["mm"] < 0.18, s["mm"])


# -- B ------------------------------------------------------------------------------------
def b_line():
    s["n"] = sk().GeometryCount
    h.press("l")


def b_first():
    s["p1"] = off(V(-30, 0, 0), 0, 40)
    s["want1"] = si.sketch_at(sk(), s["p1"])
    click_px(s["p1"])


def b_second():
    s["p2"] = off(V(40, 0, 0), 0, -40)
    s["want2"] = si.sketch_at(sk(), s["p2"])
    click_px(s["p2"])


def b_check():
    stop_tool()
    new = new_lines()
    h.check("B the two clicks drew one line", len(new) == 1, len(new))
    if not new:
        return
    line = new[0][1]
    tol = 1.5 * s["mm"]
    h.check(
        "B a click 40 px above the X axis stays where it was clicked",
        abs(line.StartPoint.y - s["want1"].y) <= tol and line.StartPoint.y > 4,
        (line.StartPoint, s["want1"]),
    )
    h.check(
        "B a click 40 px below the X axis stays where it was clicked",
        abs(line.EndPoint.y - s["want2"].y) <= tol and line.EndPoint.y < -4,
        (line.EndPoint, s["want2"]),
    )
    h.check(
        "B ...and neither end is tied to the axis",
        "PointOnObject" not in types_on(new[0][0]),
        types_on(new[0][0]),
    )
    s["b_line"] = new[0][0]
    h.shot("B-where-clicked")


def b_near_line():
    s["n"] = sk().GeometryCount
    h.press("l")


def b_near_a():
    click_px(off(V(-63, 30, 0), 0, 3))  # 3 px above the grid line y = 30


def b_near_b():
    click_px(off(V(-63, 50, 0), 3, 0))  # 3 px right of the point (x = -63: no grid line)


def b_near_check():
    stop_tool()
    new = new_lines()
    h.check("B a second line", len(new) == 1, len(new))
    if not new:
        return
    line = new[0][1]
    h.check(
        "B a click 3 px off a grid line lands on it exactly",
        abs(line.StartPoint.y - 30.0) < 1e-9,
        line.StartPoint,
    )


# -- C ------------------------------------------------------------------------------------
def c_line():
    s["n"] = sk().GeometryCount
    h.press("l")


def _diagonal_end(start, length, degrees):
    r = math.radians(degrees)
    return V(start.x + length * math.cos(r), start.y + length * math.sin(r), 0)


def c_a1():
    click(V(17, 23, 0))


def c_a2():
    click(_diagonal_end(V(17, 23, 0), 26.0, 47.0))


def c_between():
    stop_tool()


def c_again():
    h.press("l")


def c_b1():
    click(V(-100, 17, 0))


def c_b2():
    click(_diagonal_end(V(-100, 17, 0), 24.0, 43.2))


def c_check():
    stop_tool()
    new = new_lines()
    h.check("C two lines near 45 degrees", len(new) == 2, len(new))
    if len(new) != 2:
        return
    s["diag"] = [i for i, _l in new]
    for index, line in new:
        h.check(
            "C line %d snapped to exactly 45 degrees" % (index + 1),
            abs(angle_of(line) - 45.0) < 1e-6,
            angle_of(line),
        )
    angles = [c.Type for c in sk().Constraints if c.Type == "Angle"]
    h.check("C no Angle dimension appeared by itself", angles == [], angles)
    h.check(
        "C ...nothing at all holds the direction of either line",
        types_on(new[0][0]) == [] and types_on(new[1][0]) == [],
        (types_on(new[0][0]), types_on(new[1][0])),
    )


def c_pick():
    a, b = (sk().Geometry[i] for i in s["diag"])
    click((a.StartPoint + a.EndPoint) * 0.5)
    click((b.StartPoint + b.EndPoint) * 0.5, held=("ctrl",))
    s["cons"] = len(sk().Constraints)


def c_parallel():
    si.menu_item("CONSTRAINTS", "Parallel")


def c_parallel_check():
    added = [c.Type for c in sk().Constraints[s["cons"] :]]
    h.check(
        "C Parallel on the two 45 degree lines is added (not redundant)",
        added == ["Parallel"],
        added,
    )
    st.sketch_ok("C after Parallel")
    Gui.Selection.clearSelection()


# -- D ------------------------------------------------------------------------------------
def d_line():
    s["n"] = sk().GeometryCount
    h.press("l")


def d_a():
    click(V(-80, -20, 0))


def d_b():
    click(V(-50, -20, 0))


def d_fast_drag():
    """Press on the end at once (the click before was a moment ago: inside the system's
    double-click time, so Qt calls this press a double-click) and drag."""
    a = px(V(-50, -20, 0))
    b = px(V(-36, -34, 0))
    x.move_to(a)
    x.button(True)
    for i in range(1, 9):
        x.move_to(QtCore.QPoint(a.x() + (b.x() - a.x()) * i // 8, a.y() + (b.y() - a.y()) * i // 8))
    x.button(False)
    h.settle()


def arcs():
    return [(i, g) for i, g in enumerate(sk().Geometry) if g.TypeId == "Part::GeomArcOfCircle"][:]


def d_fast_check():
    new = [(i, g) for i, g in arcs() if i >= s["n"]]
    h.check("D a press right after the click that drags draws an arc", len(new) == 1, len(new))
    if not new:
        return
    index, arc = new[0]
    tangent = [c for c in sk().Constraints if c.Type == "Tangent" and index in (c.First, c.Second)]
    h.check("D ...tangent to the line", len(tangent) == 1, types_on(index))
    ends = sorted((arc.StartPoint, arc.EndPoint), key=lambda p: (p - V(-50, -20, 0)).Length)
    h.check("D ...from the line's end", (ends[0] - V(-50, -20, 0)).Length < 1e-6, ends[0])
    s["arc_end"] = ends[1]
    chain = st.session().line
    h.check(
        "D the chain goes on from the arc's end",
        chain.active and chain.current is not None and (chain.current - ends[1]).Length < 1e-6,
        chain.current,
    )
    h.shot("D-line-arc")


def d_next():
    click(V(-20, -44, 0))


def d_slow_drag():
    """The same gesture after a pause (a plain press, no double-click)."""
    h.check("D a line from the arc's end", len(lines()) >= 1)
    x.press_drag_release(px(V(-20, -44, 0)), px(V(-6, -36, 0)), steps=8)
    h.settle()


def d_slow_check():
    new = [(i, g) for i, g in arcs() if i >= s["n"]]
    h.check("D press and drag after a pause draws an arc too", len(new) == 2, len(new))


def d_double():
    end = st.session().line.current
    s["d_end"] = V(end) if end is not None else None
    h.check("D the chain waits at the second arc's end", end is not None)
    if end is not None:
        x.double_click(px(V(end)))
        h.settle()


def d_double_check():
    chain = st.session().line
    h.check(
        "D a double-click on the end (no drag) ends the chain, the tool stays on",
        chain.active and chain.current is None,
        chain.current,
    )
    stop_tool()
    st.sketch_ok("D after the arcs")


# -- E ------------------------------------------------------------------------------------
def e_line():
    s["n"] = sk().GeometryCount
    h.press("l")


def e_1():
    click(V(-40, 48, 0))


def e_origin():
    click_px(off(V(0, 0, 0), 4, 3))  # 5 px off the origin: it lands on the origin


def e_3():
    chain = st.session().line
    h.check(
        "E the chain goes on from the origin",
        chain.active and chain.current is not None and chain.current.Length < 1e-6,
        chain.current,
    )
    click(V(47, 49, 0))


def e_onto_line():
    # ends on the first line of B, well away from its ends and its middle
    line = sk().Geometry[s["b_line"]]
    click(line.StartPoint + (line.EndPoint - line.StartPoint) * 0.8)


def e_check():
    new = new_lines()
    h.check("E three lines, the second from the origin", len(new) == 3, len(new))
    if len(new) == 3:
        h.check(
            "E a click 5 px off the origin landed on it",
            new[0][1].EndPoint.Length < 1e-9 and new[1][1].StartPoint.Length < 1e-9,
            (new[0][1].EndPoint, new[1][1].StartPoint),
        )
        joined = [
            c
            for c in sk().Constraints
            if c.Type == "Coincident" and {c.First, c.Second} == {new[0][0], -1}
        ]
        h.check(
            "E ...and the line's end is joined to the origin", len(joined) == 1, types_on(new[0][0])
        )
    chain = st.session().line
    h.check(
        "E a line that ends on another line ends the chain (Fusion)",
        chain.active and chain.current is None,
        chain.current,
    )
    h.check(
        "E ...and Fission 180 says so beside the pointer",
        "chain ends" in si.tooltip(),
        si.tooltip(),
    )
    stop_tool()
    st.sketch_ok("E at the end")


def done():
    from fission180 import grid_ui

    grid_ui.reset()
    h.ribbon("Finish Sketch")


h.run(
    "book_sketch_a_line",
    st.start_steps("BookSketchLine")
    + [
        book_grid,
        b_line,
        b_first,
        b_second,
        b_check,
        b_near_line,
        b_near_a,
        b_near_b,
        b_near_check,
        c_line,
        c_a1,
        c_a2,
        c_between,
        c_again,
        c_b1,
        c_b2,
        c_check,
        c_pick,
        c_parallel,
        c_parallel_check,
        d_line,
        d_a,
        d_b,
        d_fast_drag,
        d_fast_check,
        d_next,
        d_slow_drag,
        d_slow_check,
        d_double,
        d_double_check,
        e_line,
        e_1,
        e_origin,
        e_3,
        e_onto_line,
        e_check,
        done,
    ],
    paced_by="state",
)
