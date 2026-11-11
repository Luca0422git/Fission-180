# SPDX-License-Identifier: LGPL-2.1-or-later
"""Wave 7, the book parity report: Sketch Dimension (D) like Fusion's, with real clicks and keys.

Report items (docs/fission180/dev/research/book-parity-report.txt):
- Drone 1483-1488: D on two parallel lines, then the click that places the dimension ON another
  line: taken as a third pick, Equal constraints added (the sketch went "Redundant").
- Hot End 1812-1813: a dimension placed on top of the Y axis became an Angle.
- Tensegrity 1056-1060: D on two polygon CORNERS that also lie on the construction
  circumcircle made no dimension.
- Strandbeest 2317-2318: a slanted line placed far off gave a horizontal distance; Fusion
  offers the aligned length beside the line.
- Fire Piston 1694-1697: D, a point, a click in empty space sometimes made the dimension with
  no value box.
- Hot End 1821-1823: Ctrl+Z after a "driven dimension" conversion left a driving duplicate
  (the sketch "Redundant").
- Drone 1461-1463: no right-click "Toggle Driven" on a dimension.
- Tensegrity 1104: a dimension typed as 0 is refused (Fusion refuses 0 too): it now says
  what to use instead.
- Fire Piston 1693: rotated dimension labels are hard to hit.
"""

import math

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import book_sketch_b_steps as b
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st

V = App.Vector
s = st.s
HEX = V(-50, -40, 0)
HEX_R = 15.0


def reference():
    import Part

    s["l1"] = b.add(Part.LineSegment(V(-80, 10, 0), V(-80, 40, 0)))
    s["l2"] = b.add(Part.LineSegment(V(-60, 12, 0), V(-60, 42, 0)))
    b.con("Vertical", s["l1"])
    b.con("Vertical", s["l2"])
    s["mid"] = b.add(Part.LineSegment(V(-70, 0, 0), V(-70, 55, 0)), True)
    s["slant"] = b.add(Part.LineSegment(V(20, 10, 0), V(50, 30, 0)))
    s["pt"] = b.add(Part.Point(V(30, -30, 0)))
    # a hexagon the way FreeCAD's polygon tool builds it: corners joined, and on a
    # construction circle
    corners = [
        HEX + V(HEX_R * math.cos(math.radians(60 * i)), HEX_R * math.sin(math.radians(60 * i)), 0)
        for i in range(6)
    ]
    sides = [b.add(Part.LineSegment(corners[i], corners[(i + 1) % 6])) for i in range(6)]
    s["sides"] = sides
    s["ring"] = b.add(Part.Circle(HEX, V(0, 0, 1), HEX_R), True)
    for i in range(6):
        b.con("Coincident", sides[i], 2, sides[(i + 1) % 6], 1)
        b.con("PointOnObject", sides[i], 1, s["ring"])
    for i in range(1, 6):
        b.con("Equal", sides[0], sides[i])
    s["circle"] = b.add(Part.Circle(V(60, -25, 0), V(0, 0, 1), 5))
    s["on"] = b.add(Part.LineSegment(V(-20, 30, 0), V(5, 45, 0)))
    s["onp"] = b.add(Part.Point(V(-10, 36, 0)))
    b.con("PointOnObject", s["onp"], 1, s["on"])
    App.ActiveDocument.recompute()
    b.clean("the reference sketch")
    b.watch_modals()


def editor():
    return st.session().editor


def box_open(where):
    h.check("%s: the value box is open" % where, editor() is not None)


def type_value(text):
    si.type_text(text)


def last():
    """The last constraint as (type, value, driving)."""
    c = b.sk().Constraints[-1]
    return c.Type, c.Value, c.Driving


# == two parallel lines, placed ON a third line ============================================
def d_key():
    h.press("d")


def lines_pick():
    h.check("D starts Sketch Dimension", st.tool_title() == "Sketch Dimension", st.tool_title())
    s["count"] = len(b.sk().Constraints)
    s["undo"] = len(b.undo_names())
    b.click(V(-80, 25, 0))
    b.click(V(-60, 25, 0))


def lines_place_on_third():
    h.check("two lines picked", len(st.tool().picks) == 2, st.tool().picks)
    b.click(V(-70, 48, 0))  # on the construction line between them


def lines_placed_check():
    cons = b.sk().Constraints
    h.check(
        "report Drone: the placing click ON another line places the dimension (one "
        "constraint, no Equal)",
        len(cons) == s["count"] + 1 and b.count("Equal") == 5,
        b.cons()[s["count"] :],
    )
    kind, value, driving = last()
    h.check(
        "...the distance between the lines, 20 mm, driving",
        kind == "Distance" and abs(value - 20) < 1e-6 and driving,
        last(),
    )
    box_open("two lines")
    type_value("25")


def lines_value_check():
    gap = abs(b.geo("l1").StartPoint.x - b.geo("l2").StartPoint.x)
    h.check("typed 25: the lines are 25 apart", abs(gap - 25) < 1e-6, gap)
    h.check("the tool goes on for the next dimension", st.tool_title() == "Sketch Dimension")
    b.clean("two lines dimensioned")


# == a slanted line: aligned beside it, horizontal past its ends below ======================
def slant_pick():
    b.click(V(35, 20, 0))


def slant_hover_beside():
    st.hover(V(42, 10, 0))  # off the line, square to its middle


def slant_place_beside():
    h.check(
        "beside the line the hint offers its length",
        "36.0" in st.tool().hint_text(),
        st.tool().hint_text(),
    )
    b.click(V(42, 10, 0))


def slant_aligned_check():
    kind, value, driving = last()
    h.check(
        "report Strandbeest: a slanted line placed beside it: the ALIGNED length",
        kind == "Distance" and abs(value - math.hypot(30, 20)) < 1e-6,
        last(),
    )
    box_open("slanted line")
    type_value("40")


def slant_again():
    g = b.geo("slant")
    h.check("typed 40: the line is 40 long", abs(g.length() - 40) < 1e-6, g.length())
    b.click(b.mid(g))


def slant_place_far_below():
    g = b.geo("slant")
    b.click(V(b.mid(g).x, min(g.StartPoint.y, g.EndPoint.y) - 30, 0))


def slant_horizontal_check():
    kind, value, driving = last()
    g = b.geo("slant")
    h.check(
        "far below the line: the HORIZONTAL distance of its ends",
        kind == "DistanceX" and abs(value - abs(g.EndPoint.x - g.StartPoint.x)) < 1e-6 and driving,
        last(),
    )
    box_open("horizontal")
    si.key(QtCore.Qt.Key_Escape)  # keeps the measured value


def slant_third():
    h.check(
        "Esc closed the box, the tool goes on",
        editor() is None and st.tool_title() == "Sketch Dimension",
    )
    s["count"] = len(b.sk().Constraints)
    s["undo"] = len(b.undo_names())
    b.click(b.mid(b.geo("slant")))


def slant_place_far_right():
    g = b.geo("slant")
    b.click(V(max(g.StartPoint.x, g.EndPoint.x) + 25, b.mid(g).y, 0))


def slant_driven_check():
    kind, value, driving = last()
    h.check(
        "the vertical distance is set already (length + horizontal): a DRIVEN dimension",
        kind == "DistanceY" and not driving,
        last(),
    )
    from fission180 import commands

    told = commands._TOLD.get("msg") or ""
    h.check(
        "...and it says what sets it", "driven dimension" in told and "already set by" in told, told
    )
    h.check("...no value box (a driven dimension shows, it does not set)", editor() is None)
    h.check("...in ONE undo step", len(b.undo_names()) == s["undo"] + 1, b.undo_names()[:3])
    b.clean("with the driven dimension")
    st.undo()


def slant_driven_undo_check():
    h.check(
        "report Hot End: Undo takes the driven dimension away whole (no driving duplicate)",
        len(b.sk().Constraints) == s["count"],
        b.cons()[s["count"] :],
    )
    b.clean("after undoing the driven dimension")


# == a point, then empty space ==============================================================
def point_pick():
    h.check(
        "the tool still runs after Undo", st.tool_title() == "Sketch Dimension", st.tool_title()
    )
    b.click(V(30, -30, 0))


def point_place():
    b.click(V(22, -12, 0))  # an empty spot beside the stretch from the origin to the point


def point_check():
    kind, value, driving = last()
    h.check(
        "report Fire Piston: a point and an empty spot: its distance from the origin",
        kind == "Distance" and abs(value - math.hypot(30, 30)) < 1e-6 and driving,
        last(),
    )
    box_open("a point and empty space (always)")
    type_value("50")


def point_value_check():
    p = b.geo("pt")
    h.check(
        "typed 50: the point is 50 from the origin",
        abs(math.hypot(p.X, p.Y) - 50) < 1e-6,
        (p.X, p.Y),
    )


# == two polygon corners that also lie on the construction circle ===========================
def corners_pick():
    ring = b.geo("ring")
    s["count"] = len(b.sk().Constraints)
    b.click(ring.Center + V(-ring.Radius, 0, 0))  # the leftmost corner
    b.click(ring.Center + V(ring.Radius, 0, 0))  # the rightmost corner


def corners_place():
    picks = st.tool().picks
    h.check(
        "two CORNERS picked (points, not the circle)",
        len(picks) == 2 and all(p[1] != 0 for p in picks),
        picks,
    )
    ring = b.geo("ring")
    b.click(ring.Center + V(0, -ring.Radius - 8, 0))


def corners_check():
    kind, value, driving = last()
    h.check(
        "report Tensegrity: the distance across the two corners",
        len(b.sk().Constraints) == s["count"] + 1
        and kind == "Distance"
        and abs(value - 2 * HEX_R) < 1e-6,
        last(),
    )
    box_open("corners")
    type_value("40")


def corners_value_check():
    h.check(
        "typed 40: the hexagon is 40 across",
        abs(b.geo("ring").Radius - 20) < 1e-6,
        b.geo("ring").Radius,
    )
    b.clean("hexagon dimensioned")


# == a circle, placed on top of an axis =====================================================
def circle_pick():
    c = b.geo("circle")
    s["count"] = len(b.sk().Constraints)
    b.click(c.Center + V(-c.Radius, 0, 0))


def circle_place_on_axis():
    b.click(V(70, 0, 0))  # on the X axis


def circle_check():
    kind, value, driving = last()
    h.check(
        "report Hot End: placed on top of an axis: still the circle's diameter (no Angle, "
        "no distance to the axis)",
        len(b.sk().Constraints) == s["count"] + 1 and kind == "Diameter" and abs(value - 10) < 1e-6,
        last(),
    )
    box_open("diameter")
    type_value("0")


def zero_check():
    box = editor()
    text = box.message.text() if box is not None else ""
    h.check(
        "a value of 0 is refused, the box stays open",
        box is not None and abs(b.geo("circle").Radius - 5) < 1e-6,
    )
    h.check(
        "...and says what to use instead",
        "more than 0" in text and "Coincident" in text,
        text,
    )
    si.key("a", QtCore.Qt.ControlModifier)
    type_value("12")


def circle_value_check():
    h.check("typed 12: the circle is 12 across", abs(b.geo("circle").Radius - 6) < 1e-6)


# == a point that is on the line: no dimension of 0 =========================================
def on_line_pick():
    s["count"] = len(b.sk().Constraints)
    p = b.geo("onp")
    b.click(V(p.X, p.Y, 0))
    g = b.geo("on")
    b.click(g.StartPoint + (g.EndPoint - g.StartPoint) * 0.9)


def on_line_place():
    b.forget_said()
    b.click(V(-25, 50, 0))


def on_line_check():
    from fission180 import sketch_draw

    text = st.tool().hint_text() if st.tool() else ""
    h.check("a point ON the line: nothing added", len(b.sk().Constraints) == s["count"])
    h.check(
        "...it says a dimension cannot be 0 and what to use",
        "cannot be 0" in text and "Coincident" in text,
        text,
    )
    h.check("no value box", editor() is None and sketch_draw.current_tool() is not None)
    st.esc()


# == Toggle Driven from the right-click menu ================================================
def find(kind):
    return max(i for i, c in enumerate(b.sk().Constraints) if c.Type == kind)


def label(index):
    return si.dimension_label(b.sk(), index)


def toggle_select():
    h.check("Esc ended Sketch Dimension", st.tool() is None, st.tool_title())
    s["dia"] = find("Diameter")
    si.click(label(s["dia"]))


def toggle_menu():
    h.check("the diameter is selected", any("Constraint" in n for n in b.selected()), b.selected())
    pos = h.screen_point(label(s["dia"]) + V(14, 9, 0))
    QtTest.QTest.mouseClick(h.gl_widget(), QtCore.Qt.RightButton, QtCore.Qt.NoModifier, pos)


toggle_menu.done = lambda: si.marking_menu() is not None
toggle_menu.done_what = "the sketch's right-click menu is open"


def toggle_choose():
    menu = si.marking_menu()
    listing = menu.findChild(QtWidgets.QListWidget, "Fission180MarkingList")
    rows = [listing.item(i).text() for i in range(listing.count())]
    h.check(
        "report Drone: the right-click menu on a dimension has Toggle Driven",
        "Toggle Driven" in " | ".join(rows),
        rows,
    )
    for i in range(listing.count()):
        if "Toggle Driven" in listing.item(i).text():
            rect = listing.visualItemRect(listing.item(i))
            h.pointer_to(listing.viewport(), rect.center())
            QtTest.QTest.mouseClick(
                listing.viewport(), QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, rect.center()
            )
            break
    QtWidgets.QApplication.processEvents()


def toggle_check():
    c = b.sk().Constraints[s["dia"]]
    h.check("Toggle Driven: the diameter is driven now", not c.Driving, c.Driving)
    b.clean("diameter driven")
    st.undo()


def toggle_undo_check():
    c = b.sk().Constraints[s["dia"]]
    h.check("Undo: driving again", c.Driving)


# == a vertical dimension's turned text is easy to hit ======================================
def vertical_add():
    """A vertical dimension on the left line (its text is turned upright)."""
    h.press("d")


def vertical_pick():
    b.click(b.mid(b.geo("l1")))


def vertical_place():
    g = b.geo("l1")
    b.click(V(g.StartPoint.x - 12, b.mid(g).y, 0))


def vertical_typed():
    box_open("vertical")
    type_value("30")


def vertical_double_click():
    st.esc()
    index = find("Distance")
    s["vert"] = index
    g = b.geo("l1")
    h.check("the left line is 30 long", abs(g.length() - 30) < 1e-6, g.length())
    # 2.5 mm along the turned text from its middle: FreeCAD's own picking misses there
    spot = label(index) + V(0, 2.5, 0)
    pos = h.screen_point(spot)
    h.pointer_to(h.gl_widget(), pos)
    h.view_drawn()
    si.double_click_widget(h.gl_widget(), pos)


def vertical_box_check():
    box = editor()
    h.check(
        "report Fire Piston: a double-click on a turned dimension text, off its middle, "
        "opens its box",
        box is not None and box.index == s["vert"],
        getattr(box, "index", None),
    )
    type_value("32")


def vertical_value_check():
    h.check("typed 32 there", abs(b.geo("l1").length() - 32) < 1e-6, b.geo("l1").length())
    b.no_modal("Sketch Dimension")


def finish():
    h.ribbon("Finish Sketch")


def finished():
    h.check("the sketch closed", h.in_sketch() is None)
    Gui.Selection.clearSelection()


h.run(
    "book_sketch_b_dimension",
    st.start_steps("BookSketchBDimension")
    + [
        reference,
        d_key,
        lines_pick,
        lines_place_on_third,
        lines_placed_check,
        lines_value_check,
        slant_pick,
        slant_hover_beside,
        slant_place_beside,
        slant_aligned_check,
        slant_again,
        slant_place_far_below,
        slant_horizontal_check,
        slant_third,
        slant_place_far_right,
        slant_driven_check,
        slant_driven_undo_check,
        point_pick,
        point_place,
        point_check,
        point_value_check,
        corners_pick,
        corners_place,
        corners_check,
        corners_value_check,
        circle_pick,
        circle_place_on_axis,
        circle_check,
        zero_check,
        circle_value_check,
        on_line_pick,
        on_line_place,
        on_line_check,
        toggle_select,
        toggle_menu,
        toggle_choose,
        toggle_check,
        toggle_undo_check,
        vertical_add,
        vertical_pick,
        vertical_place,
        vertical_typed,
        vertical_double_click,
        vertical_box_check,
        vertical_value_check,
        finish,
        finished,
    ],
    paced_by="state",
)
