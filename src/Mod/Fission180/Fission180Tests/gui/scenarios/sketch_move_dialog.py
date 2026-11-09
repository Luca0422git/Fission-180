# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's sketch Move/Copy with its MOVE/COPY panel and manipulator
(fission180/sketch_move_tool.py; Luca, 2026-11-09: "Move copy ... just does not want to work
... the icon is NOT the fission icon, you cant click and drag to select multiple sketch lines
... the arrows that Fusion would have to move it are just not there ... it leaves behind the
FUCKING ORANGE DOTS").

The sketch: a rectangle (10,10)-(30,20) (lines 0-3, level / upright, width 20, height 10), a
circle r 4 at (50,15) (4, radius 4), a line (30,20)-(40,30) joined to the rectangle's top
right corner (5), a sketch point at (0,30) (6).

A  L (a drawing tool), then MODIFY > Move/Copy: the MOVE/COPY panel, Fission 180's Move/Copy
   pointer, OK greyed, no FreeCAD tool left running.
B  A box from left to right round the rectangle picks its 4 lines; the manipulator shows. A
   click on the circle adds it, a second click drops it; the same for the sketch point.
C  Real drags: the red arrow 10 mm along X, the green one 5 mm along Y, the turn handle a
   quarter turn (90 degrees): the panel's values follow; the moved curves show.
D  Typed: X 15, Y -5, Angle 0; OK: the rectangle exactly at (25,5)-(45,15), the joined line
   left where it was (its tie to the corner went), the sketch solves, one undo step
   "Move/Copy", the panel and every handle and preview gone, no curve or point added.
E  Ctrl+Z puts it back in one press.
F  The circle selected, then M: it is the Objects; Create Copy, X 20, Enter: a copy at (70,15)
   with its radius, the original unchanged.
G  Angle 90 typed: the rectangle turned about its middle, level and upright swapped.
H  Esc after a drag: nothing changes, nothing left.
I  M while Mirror runs: Move/Copy takes over; M again while it runs: it keeps running.
J  Point to Point: the corner (10,10) to the sketch point (0,30).
K  A sketch on the XZ plane: the green arrow moves along the sketch's own Y (the model's Z).
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st
from Fission180Tests.gui import widget_input as wi

V = App.Vector
s = {}
RECT = [V(10, 10, 0), V(30, 10, 0), V(30, 20, 0), V(10, 20, 0)]


def panel():
    w = Gui.getMainWindow().findChild(QtWidgets.QFrame, "Fission180SketchMovePanel")
    return w if w is not None and w.isVisible() else None


def widget(name):
    p = panel()
    return p.findChild(QtWidgets.QWidget, name) if p is not None else None


def click_widget(name):
    w = widget(name)
    if not h.check("the MOVE/COPY panel has %s" % name, w is not None and w.isVisible()):
        return
    wi.click(w)


def type_field(name, text):
    """Click into a value of the panel, select what is there and type (as a person)."""
    w = widget(name)
    if not h.check("the MOVE/COPY panel has %s" % name, w is not None and w.isVisible()):
        return
    wi.click(w)
    QtTest.QTest.keyClick(w, QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
    QtTest.QTest.keyClicks(w, text)
    QtWidgets.QApplication.processEvents()


def tool():
    return st.tool()


def moving():
    t = tool()
    return t if t is not None and t.title == "Move/Copy" else None


def sk():
    return s["sk"]


def ends(i):
    g = sk().Geometry[i]
    return g.StartPoint, g.EndPoint


def line_is(i, a, b, tol=1e-6):
    p, q = ends(i)
    return (si.vnear(p, a, tol) and si.vnear(q, b, tol)) or (
        si.vnear(p, b, tol) and si.vnear(q, a, tol)
    )


def leftovers():
    """Nodes of a sketch tool still in the 3D view: its preview, its handles."""
    graph = Gui.ActiveDocument.ActiveView.getSceneGraph()
    names = ("Fission180SketchTool", "Fission180SketchHandle")
    found = []
    for i in range(graph.getNumChildren()):
        name = graph.getChild(i).getName()
        name = str(name.getString() if hasattr(name, "getString") else name)
        if name in names:
            found.append(name)
    return found


def points_count():
    return len([g for g in sk().Geometry if g.TypeId == "Part::GeomPoint"])


def nothing_left(where):
    """No panel, no tool, no handle or preview node, no wheel, no new curve or point."""
    from fission180 import protractor

    h.check(
        "%s: the panel is gone and Move/Copy ended" % where,
        panel() is None and moving() is None,
        st.tool_title(),
    )
    h.check("%s: no handle or preview left in the view" % where, not leftovers(), leftovers())
    h.check("%s: no protractor left" % where, not protractor.WHEELS)
    h.check(
        "%s: no curve or point added" % where,
        len(sk().Geometry) == s["count"] and points_count() == s["points"],
        (len(sk().Geometry), s["count"], points_count(), s["points"]),
    )


def arrow_point(name, share=0.7):
    """A sketch point on the manipulator's arrow `name` ("x" / "y"), `share` from its foot."""
    foot, tip = tool().manipulator.parts()[name]
    return V(foot[0] + (tip[0] - foot[0]) * share, foot[1] + (tip[1] - foot[1]) * share, 0)


def drag(start, end):
    pos = st.press(start)
    end_pos = st.drag_to(end, steps=12)
    st.release(end_pos)
    QtWidgets.QApplication.processEvents()
    return pos


# -- setup -------------------------------------------------------------------------------------
def new_design():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("MovePanel")
    h.fit()
    Gui.getMainWindow().activateWindow()


def create_sketch():
    h.ribbon("Create Sketch")


def pick_xy():
    pl.click_square("XY_Plane")


def opened():
    import Part
    import Sketcher

    s["sk"] = st.s["sk"] = h.in_sketch()
    if not h.check("sketch open on XY", s["sk"] is not None):
        return
    doc = App.ActiveDocument
    doc.openTransaction("Setup")
    h.draw_rectangle(sk(), 10, 10, 30, 20)
    sk().addConstraint(Sketcher.Constraint("DistanceX", 0, 1, 0, 2, 20.0))
    sk().renameConstraint(len(sk().Constraints) - 1, "width")
    sk().addConstraint(Sketcher.Constraint("DistanceY", 1, 1, 1, 2, 10.0))
    sk().addGeometry(Part.Circle(V(50, 15, 0), V(0, 0, 1), 4.0))
    sk().addConstraint(Sketcher.Constraint("Radius", 4, 4.0))
    sk().addGeometry(Part.LineSegment(V(30, 20, 0), V(40, 30, 0)))
    sk().addConstraint(Sketcher.Constraint("Coincident", 5, 1, 1, 2))
    sk().addGeometry(Part.Point(V(0, 30, 0)))
    sk().solve()
    doc.commitTransaction()
    doc.recompute()
    h.fit(iso=False)
    s["count"] = len(sk().Geometry)
    s["points"] = points_count()
    s["cons"] = len(sk().Constraints)
    h.check(
        "the setup: 7 curves and points, 12 constraints",
        s["count"] == 7 and s["cons"] == 12,
        (s["count"], s["cons"]),
    )


# -- A: the button, right after another tool ---------------------------------------------------
def a_line_tool():
    h.press("l")


def a_line_runs():
    h.wait_for(si.drawing, "the Line tool to run")


def a_button():
    si.menu_item("MODIFY", "Move/Copy")


def a_panel():
    from fission180 import sketch_cursor

    h.wait_for(lambda: panel() is not None, "the MOVE/COPY panel")
    h.check("A: Move/Copy runs", moving() is not None, st.tool_title())
    gl = h.gl_widget()
    widget_ = st.session().viewer if st.session().viewer is not None else gl
    own = sketch_cursor.cursor_for("Fission180_SketchMove", widget_)
    h.check(
        "A: Fission 180's Move/Copy pointer",
        widget_.cursor().pixmap().cacheKey() == own.pixmap().cacheKey(),
        widget_.cursor().shape(),
    )
    h.check(
        "A: OK greyed before anything is picked",
        not widget("Fission180SketchMovePanelOK").isEnabled(),
    )
    h.check(
        "A: X Distance, Y Distance, Angle and Create Copy in the panel",
        all(
            widget(n) is not None
            for n in (
                "Fission180SketchMoveX",
                "Fission180SketchMoveY",
                "Fission180SketchMoveAngle",
                "Fission180SketchMoveCopy",
            )
        ),
    )
    h.shot("A-panel")


# -- B: box selection, clicks ------------------------------------------------------------------
def b_box():
    from Fission180Tests.gui import selection_input as sel

    sel.box_around(RECT, margin=14)


def b_boxed():
    t = moving()
    h.check(
        "B: the box took the rectangle's 4 lines",
        t is not None and sorted(t.objects) == [0, 1, 2, 3],
        t.objects if t else None,
    )
    h.check(
        "B: the panel says 4 selected",
        widget("Fission180SketchMoveObjects").text() == "4 selected",
        widget("Fission180SketchMoveObjects").text(),
    )
    h.check("B: the manipulator shows", t.manipulator is not None and t.manipulator.attached)
    h.check("B: OK can be pressed", widget("Fission180SketchMovePanelOK").isEnabled())
    h.shot("B-picked")


def b_circle():
    st.click(V(54, 15, 0), towards=V(1.0, 0.3, 0))


def b_circle_in():
    h.check("B: a click on the circle adds it", 4 in moving().objects, moving().objects)


def b_circle_again():
    st.click(V(54, 15, 0), towards=V(1.0, 0.3, 0))


def b_circle_out():
    h.check(
        "B: a second click drops it", sorted(moving().objects) == [0, 1, 2, 3], moving().objects
    )


def b_point():
    st.click(V(0, 30, 0), towards=V(-0.5, 1.0, 0))


def b_point_in():
    h.check("B: a click on the sketch point adds it", 6 in moving().objects, moving().objects)


def b_point_again():
    st.click(V(0, 30, 0), towards=V(-0.5, 1.0, 0))


def b_point_out():
    h.check(
        "B: a second click drops the point",
        sorted(moving().objects) == [0, 1, 2, 3],
        moving().objects,
    )


# -- C: real drags -----------------------------------------------------------------------------
def c_drag_x():
    start = arrow_point("x")
    s["mm"] = si.mm_per_pixel(sk())
    drag(start, start + V(10, 0, 0))


def c_dragged_x():
    t = moving()
    tol = 4 * s["mm"]
    h.check(
        "C: the red arrow moved them 10 mm along X",
        abs(t.dx - 10) <= tol and abs(t.dy) < 1e-9,
        (t.dx, t.dy, tol),
    )
    h.check(
        "C: the panel's X Distance follows",
        abs(float(widget("Fission180SketchMoveX").property("rawValue")) - t.dx) < 1e-6,
    )
    shown = t.preview.drawn().get("curves", [])
    h.check("C: the moved curves show", len(shown) == 4, len(shown))


def c_drag_y():
    start = arrow_point("y")
    drag(start, start + V(0, 5, 0))


def c_dragged_y():
    t = moving()
    tol = 4 * s["mm"]
    h.check(
        "C: the green arrow moved them 5 mm along Y",
        abs(t.dy - 5) <= tol and abs(t.dx - 10) <= tol,
        (t.dx, t.dy),
    )
    h.check(
        "C: the panel's Y Distance follows",
        abs(float(widget("Fission180SketchMoveY").property("rawValue")) - t.dy) < 1e-6,
    )


def c_turn():
    import math

    t = moving()
    disc = t.manipulator.disc_point()
    c = t.center()
    r = math.hypot(disc[0] - c[0], disc[1] - c[1])
    start = V(disc[0], disc[1], 0)
    end = V(c[0] + r * math.cos(math.radians(135)), c[1] + r * math.sin(math.radians(135)), 0)
    s["wheel_seen"] = False
    pos = st.press(start)
    mid = V(c[0] + r * math.cos(math.radians(90)), c[1] + r * math.sin(math.radians(90)), 0)
    st.drag_to(mid, steps=8)
    from fission180 import protractor

    s["wheel_seen"] = bool(protractor.WHEELS)
    end_pos = st.drag_to(end, steps=8)
    st.release(end_pos)
    del pos


def c_turned():
    t = moving()
    h.check("C: the protractor showed while the turn handle was held", s["wheel_seen"])
    h.check("C: the turn handle turned them a quarter turn", abs(t.angle - 90.0) < 1e-6, t.angle)
    h.check(
        "C: the panel's Angle follows",
        abs(float(widget("Fission180SketchMoveAngle").property("rawValue")) - 90.0) < 1e-6,
    )
    h.check("C: nothing changed in the sketch yet", line_is(0, RECT[0], RECT[1]))
    h.shot("C-dragged")


# -- D: typed values, OK -----------------------------------------------------------------------
def d_type():
    s["undo"] = len(App.ActiveDocument.UndoNames)
    type_field("Fission180SketchMoveX", "15")
    type_field("Fission180SketchMoveY", "-5")
    type_field("Fission180SketchMoveAngle", "0")


def d_typed():
    t = moving()
    h.check(
        "D: the typed values", (t.dx, t.dy, t.angle) == (15.0, -5.0, 0.0), (t.dx, t.dy, t.angle)
    )


def d_ok():
    click_widget("Fission180SketchMovePanelOK")


def d_moved():
    h.settle("the move")
    h.check("D: the bottom line at (25,5)-(45,5)", line_is(0, V(25, 5, 0), V(45, 5, 0)), ends(0))
    h.check("D: the right line at (45,5)-(45,15)", line_is(1, V(45, 5, 0), V(45, 15, 0)), ends(1))
    h.check("D: the top line at (45,15)-(25,15)", line_is(2, V(45, 15, 0), V(25, 15, 0)), ends(2))
    h.check(
        "D: the joined line stays where it was", line_is(5, V(30, 20, 0), V(40, 30, 0)), ends(5)
    )
    h.check(
        "D: the circle and the point stay",
        si.vnear(sk().Geometry[4].Center, V(50, 15, 0)) and abs(sk().Geometry[6].X) < 1e-9,
    )
    tie = [c for c in sk().Constraints if c.Type == "Coincident" and 5 in (c.First, c.Second)]
    h.check("D: the tie to the line that stayed went", not tie, tie)
    names = [c.Name for c in sk().Constraints]
    h.check(
        "D: the width and height stay (20 and 10)",
        "width" in names and abs(sk().Constraints[names.index("width")].Value - 20) < 1e-9,
    )
    st.sketch_ok("D")
    undo = list(App.ActiveDocument.UndoNames)
    h.check(
        "D: one undo step Move/Copy",
        undo and undo[0] == "Move/Copy" and len(undo) == s["undo"] + 1,
        undo[:3],
    )
    nothing_left("D")
    h.shot("D-moved")


# -- E: undo -----------------------------------------------------------------------------------
def e_undo():
    st.undo()


def e_undone():
    h.settle("the undo")
    h.check(
        "E: one Ctrl+Z puts the rectangle back",
        line_is(0, RECT[0], RECT[1]) and line_is(1, RECT[1], RECT[2]),
        ends(0),
    )
    h.check("E: and its tie to the line", len(sk().Constraints) == s["cons"], len(sk().Constraints))
    st.sketch_ok("E")


# -- F: selected first, M, Create Copy, Enter --------------------------------------------------
def f_select():
    si.click(V(54, 15, 0), V(1.0, 0.3, 0))


def f_m():
    h.check("F: the circle is selected", bool(Gui.Selection.getSelectionEx()))
    h.press("m")


def f_ready():
    h.wait_for(lambda: panel() is not None, "the MOVE/COPY panel")
    h.check(
        "F: the selected circle is the Objects",
        moving() is not None and moving().objects == [4],
        moving().objects if moving() else None,
    )


def f_copy():
    from Fission180Tests.gui import misc_steps

    box = widget("Fission180SketchMoveCopy")
    if h.check("F: the Create Copy box", box is not None):
        misc_steps.set_check(box, True)


def f_values():
    h.check("F: Create Copy is on", moving().copy)
    type_field("Fission180SketchMoveX", "20")


def f_enter():
    QtTest.QTest.keyClick(widget("Fission180SketchMoveX"), QtCore.Qt.Key_Return)
    QtWidgets.QApplication.processEvents()


def f_copied():
    h.settle("the copy")
    circles = si.circles(sk())
    h.check("F: two circles", len(circles) == 2, [c.Center for _i, c in circles])
    h.check("F: the original unchanged", si.vnear(sk().Geometry[4].Center, V(50, 15, 0)))
    copies = [c for _i, c in circles if si.vnear(c.Center, V(70, 15, 0))]
    h.check("F: the copy at (70,15), r 4", len(copies) == 1 and abs(copies[0].Radius - 4) < 1e-9)
    radii = [c for c in sk().Constraints if c.Type == "Radius"]
    h.check("F: the copy has its own radius", len(radii) == 2, len(radii))
    st.sketch_ok("F")
    h.check("F: the panel is gone", panel() is None and moving() is None)
    h.check(
        "F: only the copy was added",
        len(sk().Geometry) == s["count"] + 1 and points_count() == s["points"],
    )
    h.check("F: no handle or preview left in the view", not leftovers(), leftovers())
    h.shot("F-copied")


def f_undo():
    st.undo()


def f_undone():
    h.settle("the undo")
    h.check("F: Ctrl+Z takes the copy back", len(sk().Geometry) == s["count"], len(sk().Geometry))


# -- G: a quarter turn typed -------------------------------------------------------------------
def g_start():
    Gui.Selection.clearSelection()
    si.menu_item("MODIFY", "Move/Copy")


def g_box():
    from Fission180Tests.gui import selection_input as sel

    h.wait_for(lambda: panel() is not None, "the MOVE/COPY panel")
    sel.box_around(RECT, margin=14)


def g_number():
    h.check("G: the rectangle picked", sorted(moving().objects) == [0, 1, 2, 3], moving().objects)
    st.move(V(20, 40, 0))
    h.press("7")  # a number typed over the sketch: into the value in use (X Distance)


def g_type():
    field = widget("Fission180SketchMoveX")
    h.check(
        "G: a number typed over the sketch went into X Distance",
        moving().dx == 7.0 and field.hasFocus(),
        (moving().dx, QtWidgets.QApplication.focusWidget()),
    )
    type_field("Fission180SketchMoveX", "0")
    type_field("Fission180SketchMoveY", "0")
    type_field("Fission180SketchMoveAngle", "90")


def g_ok():
    click_widget("Fission180SketchMovePanelOK")


def g_turned():
    h.settle("the turn")
    h.check(
        "G: the bottom line turned upright about the middle (25,5)-(25,25)",
        line_is(0, V(25, 5, 0), V(25, 25, 0), 1e-6),
        ends(0),
    )
    h.check(
        "G: the right line turned level (25,25)-(15,25)",
        line_is(1, V(25, 25, 0), V(15, 25, 0), 1e-6),
        ends(1),
    )
    kinds = {(c.Type, c.First) for c in sk().Constraints}
    h.check(
        "G: level and upright swapped",
        ("Vertical", 0) in kinds and ("Horizontal", 1) in kinds,
        kinds,
    )
    st.sketch_ok("G")
    h.shot("G-turned")
    st.undo()


def g_undone():
    h.settle("the undo")
    h.check("G: Ctrl+Z puts it back", line_is(0, RECT[0], RECT[1]), ends(0))


# -- H: Esc after a drag -----------------------------------------------------------------------
def h_start():
    Gui.Selection.clearSelection()
    h.press("m")


def h_box():
    from Fission180Tests.gui import selection_input as sel

    h.wait_for(lambda: panel() is not None, "the MOVE/COPY panel")
    sel.box_around(RECT, margin=14)


def h_drag():
    start = arrow_point("x")
    drag(start, start + V(8, 0, 0))


def h_esc():
    h.check(
        "H: dragged", moving() is not None and moving().dx > 1, moving().dx if moving() else None
    )
    si.key(QtCore.Qt.Key_Escape)


def h_nothing():
    h.settle("Esc")
    h.check("H: Esc moved nothing", line_is(0, RECT[0], RECT[1]), ends(0))
    h.check("H: no undo step", len(sk().Constraints) == s["cons"])
    nothing_left("H")


# -- I: M while another Fission 180 tool runs; M again while Move runs -------------------------
def i_mirror():
    si.menu_item("CREATE", "Mirror")


def i_m():
    h.wait_for(lambda: st.tool_title() == "Mirror", "Mirror to run")
    h.press("m")


def i_moving():
    h.wait_for(lambda: panel() is not None, "the MOVE/COPY panel")
    mirror = Gui.getMainWindow().findChild(QtWidgets.QFrame, "Fission180MirrorPanel")
    h.check("I: M after Mirror starts Move/Copy", moving() is not None, st.tool_title())
    h.check("I: Mirror's panel went", mirror is None or not mirror.isVisible())
    s["running"] = moving()
    h.press("m")


def i_still():
    h.settle("M again")
    h.check(
        "I: M again while it runs: it keeps running",
        moving() is s["running"] and panel() is not None,
    )
    si.key(QtCore.Qt.Key_Escape)


# -- J: Point to Point -------------------------------------------------------------------------
def j_start():
    h.settle("Esc")
    Gui.Selection.clearSelection()
    h.press("m")


def j_box():
    from Fission180Tests.gui import selection_input as sel

    h.wait_for(lambda: panel() is not None, "the MOVE/COPY panel")
    sel.box_around(RECT, margin=14)


def j_type():
    combo = widget("Fission180SketchMoveType")
    if not h.check("J: the Move Type list", combo is not None):
        return
    from Fission180Tests.gui import dialog_input

    h.check("J: Point to Point picked in Move Type", dialog_input.choose(combo, "Point to Point"))


def j_from():
    h.check("J: Point to Point chosen", moving().mode == "point_to_point", moving().mode)
    h.check("J: From Point is active", moving().field == "from", moving().field)
    h.check(
        "J: no manipulator for Point to Point",
        moving().manipulator is None or not moving().manipulator.attached,
    )
    st.click(V(10, 10, 0), towards=V(-0.6, -1.0, 0))


def j_to():
    h.check("J: the From point", moving().from_point == (10.0, 10.0), moving().from_point)
    st.click(V(0, 30, 0), towards=V(-0.5, 1.0, 0))


def j_ok():
    h.check("J: the To point", moving().to_point == (0.0, 30.0), moving().to_point)
    h.shot("J-point-to-point")
    st.enter()


def j_moved():
    h.settle("the move")
    h.check(
        "J: the corner went onto the point: bottom line (0,30)-(20,30)",
        line_is(0, V(0, 30, 0), V(20, 30, 0)),
        ends(0),
    )
    st.sketch_ok("J")
    h.check("J: nothing added", len(sk().Geometry) == s["count"] and points_count() == s["points"])
    st.undo()


def j_undone():
    h.settle("the undo")
    h.check("J: Ctrl+Z puts it back", line_is(0, RECT[0], RECT[1]), ends(0))
    # Move/Copy remembers the move type (Fusion): back to Free Move for the next person
    from fission180 import sketch_move_tool

    sketch_move_tool.SketchMove.last_mode = sketch_move_tool.FREE


def finish():
    h.ribbon("Finish Sketch")


# -- K: a sketch on the XZ plane: the arrows follow the sketch's own X and Y -------------------
def k_sketch():
    h.check("the sketch is closed", h.in_sketch() is None)
    h.ribbon("Create Sketch")


def k_pick():
    pl.click_square("XZ_Plane")


def k_opened():
    import Part

    s["sk"] = st.s["sk"] = h.in_sketch()
    if not h.check("K: a sketch on XZ", s["sk"] is not None):
        return
    doc = App.ActiveDocument
    doc.openTransaction("Setup")
    sk().addGeometry(Part.LineSegment(V(10, 10, 0), V(30, 10, 0)))
    doc.commitTransaction()
    doc.recompute()
    h.fit(iso=False)
    h.press("m")


def k_box():
    from Fission180Tests.gui import selection_input as sel

    h.wait_for(lambda: panel() is not None, "the MOVE/COPY panel")
    sel.box_around([st.g(V(10, 10, 0)), st.g(V(30, 10, 0))], margin=14)


def k_drag():
    h.check("K: the line picked", moving().objects == [0], moving().objects)
    start = arrow_point("y")
    s["mm"] = si.mm_per_pixel(sk())
    drag(start, start + V(0, 10, 0))


def k_ok():
    t = moving()
    tol = 4 * s["mm"]
    h.check(
        "K: the green arrow moves along the sketch's Y",
        abs(t.dy - 10) <= tol and abs(t.dx) < 1e-9,
        (t.dx, t.dy),
    )
    type_field("Fission180SketchMoveY", "10")
    click_widget("Fission180SketchMovePanelOK")


def k_moved():
    h.settle("the move")
    h.check("K: the line 10 mm up the sketch's Y", line_is(0, V(10, 20, 0), V(30, 20, 0)), ends(0))
    p, q = ends(0)
    a, b = st.g(p), st.g(q)
    h.check(
        "K: in the model: at z 20 on the XZ plane",
        abs(a.z - 20) < 1e-6 and abs(b.z - 20) < 1e-6 and abs(a.y) < 1e-6,
        (a, b),
    )
    h.shot("K-xz")
    h.ribbon("Finish Sketch")


def end():
    h.check("the sketch is closed", h.in_sketch() is None)
    h.expect_no_errors("the MOVE/COPY panel")


STEPS = [
    new_design,
    create_sketch,
    pick_xy,
    opened,
    a_line_tool,
    a_line_runs,
    a_button,
    a_panel,
    b_box,
    b_boxed,
    b_circle,
    b_circle_in,
    b_circle_again,
    b_circle_out,
    b_point,
    b_point_in,
    b_point_again,
    b_point_out,
    c_drag_x,
    c_dragged_x,
    c_drag_y,
    c_dragged_y,
    c_turn,
    c_turned,
    d_type,
    d_typed,
    d_ok,
    d_moved,
    e_undo,
    e_undone,
    f_select,
    f_m,
    f_ready,
    f_copy,
    f_values,
    f_enter,
    f_copied,
    f_undo,
    f_undone,
    g_start,
    g_box,
    g_number,
    g_type,
    g_ok,
    g_turned,
    g_undone,
    h_start,
    h_box,
    h_drag,
    h_esc,
    h_nothing,
    i_mirror,
    i_m,
    i_moving,
    i_still,
    j_start,
    j_box,
    j_type,
    j_from,
    j_to,
    j_ok,
    j_moved,
    j_undone,
    finish,
    k_sketch,
    k_pick,
    k_opened,
    k_box,
    k_drag,
    k_ok,
    k_moved,
    end,
]

h.run("sketch_move_dialog", si.watched(STEPS), paced_by="state")
