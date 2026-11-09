# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's Sketch Scale with its SKETCH SCALE panel and drag arrow
(fission180/sketch_scale_tool.py; Luca, 2026-11-09: "Sketch scale ... its just not fusion. there
should be a dialog box with the scale percentage, there should be drag to select what you want
to scale").

The sketch: a rectangle (10,10)-(30,20) (lines 0-3, width 20, height 10), a circle r 4 at
(50,15) (4), a line (30,20)-(40,30) joined to the rectangle's top right corner (5), a sketch
point at (0,30) (6), a line from the origin to (-10,-10) joined to it (7).

A  L (a drawing tool), then MODIFY > Sketch Scale: the SKETCH SCALE panel, Fission 180's Sketch
   Scale pointer, OK greyed.
B  A box from left to right round the rectangle picks its 4 lines; the blue arrow shows; the
   base point is their middle until one is picked.
C  The arrow dragged half its distance further out: a factor of about 1.5, the Scale Factor
   and Percent boxes say so; the scaled curves show.
D  "50%" typed as the factor: 0.5 (Percent 50 %); 200 typed as the percentage: 2. Point's
   Select, a click on the corner (10,10): the base point. OK: the rectangle exactly (10,10)-
   (50,30), its width 40 and height 20, the joined line left where it was (its tie went), the
   sketch solves, one undo step "Sketch Scale", nothing left behind.
E  Ctrl+Z puts it back.
F  The line from the origin selected first: it is the Objects, Point is active, the base
   point is the origin; factor 2, Enter: (0,0)-(-20,-20), still joined to the origin.
G  Esc after a drag: nothing changes, nothing left.
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
    w = Gui.getMainWindow().findChild(QtWidgets.QFrame, "Fission180SketchScalePanel")
    return w if w is not None and w.isVisible() else None


def widget(name):
    p = panel()
    return p.findChild(QtWidgets.QWidget, name) if p is not None else None


def click_widget(name):
    w = widget(name)
    if not h.check("the SKETCH SCALE panel has %s" % name, w is not None and w.isVisible()):
        return
    wi.click(w)


def type_field(name, text):
    w = widget(name)
    if not h.check("the SKETCH SCALE panel has %s" % name, w is not None and w.isVisible()):
        return
    wi.click(w)
    QtTest.QTest.keyClick(w, QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
    QtTest.QTest.keyClicks(w, text)
    QtWidgets.QApplication.processEvents()


def scaling():
    t = st.tool()
    return t if t is not None and t.title == "Sketch Scale" else None


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


def points_count():
    return len([g for g in sk().Geometry if g.TypeId == "Part::GeomPoint"])


def leftovers():
    graph = Gui.ActiveDocument.ActiveView.getSceneGraph()
    found = []
    for i in range(graph.getNumChildren()):
        name = graph.getChild(i).getName()
        name = str(name.getString() if hasattr(name, "getString") else name)
        if name in ("Fission180SketchTool", "Fission180SketchHandle"):
            found.append(name)
    return found


def nothing_left(where):
    h.check(
        "%s: the panel is gone and Sketch Scale ended" % where,
        panel() is None and scaling() is None,
        st.tool_title(),
    )
    h.check("%s: no arrow or preview left in the view" % where, not leftovers(), leftovers())
    h.check(
        "%s: no curve or point added" % where,
        len(sk().Geometry) == s["count"] and points_count() == s["points"],
        (len(sk().Geometry), s["count"], points_count(), s["points"]),
    )


def constraint(name):
    for c in sk().Constraints:
        if c.Name == name:
            return c
    return None


# -- setup -------------------------------------------------------------------------------------
def new_design():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("ScalePanel")
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
    sk().renameConstraint(len(sk().Constraints) - 1, "height")
    sk().addGeometry(Part.Circle(V(50, 15, 0), V(0, 0, 1), 4.0))
    sk().addConstraint(Sketcher.Constraint("Radius", 4, 4.0))
    sk().addGeometry(Part.LineSegment(V(30, 20, 0), V(40, 30, 0)))
    sk().addConstraint(Sketcher.Constraint("Coincident", 5, 1, 1, 2))
    sk().addGeometry(Part.Point(V(0, 30, 0)))
    sk().addGeometry(Part.LineSegment(V(0, 0, 0), V(-10, -10, 0)))
    sk().addConstraint(Sketcher.Constraint("Coincident", 7, 1, -1, 1))
    sk().solve()
    doc.commitTransaction()
    doc.recompute()
    h.fit(iso=False)
    s["count"] = len(sk().Geometry)
    s["points"] = points_count()
    s["cons"] = len(sk().Constraints)


# -- A -----------------------------------------------------------------------------------------
def a_line_tool():
    h.press("l")


def a_button():
    h.wait_for(si.drawing, "the Line tool to run")
    si.menu_item("MODIFY", "Sketch Scale")


def a_panel():
    from fission180 import sketch_cursor

    h.wait_for(lambda: panel() is not None, "the SKETCH SCALE panel")
    h.check("A: Sketch Scale runs", scaling() is not None, st.tool_title())
    viewer = st.session().viewer if st.session().viewer is not None else h.gl_widget()
    own = sketch_cursor.cursor_for("Fission180_SketchScale", viewer)
    h.check(
        "A: Fission 180's Sketch Scale pointer",
        viewer.cursor().pixmap().cacheKey() == own.pixmap().cacheKey(),
    )
    h.check(
        "A: OK greyed before anything is picked",
        not widget("Fission180SketchScalePanelOK").isEnabled(),
    )
    h.check(
        "A: Point, Scale Factor and Percent in the panel",
        all(
            widget(n) is not None
            for n in (
                "Fission180SketchScalePoint",
                "Fission180SketchScaleFactor",
                "Fission180SketchScalePercent",
            )
        ),
    )
    h.shot("A-panel")


# -- B -----------------------------------------------------------------------------------------
def b_box():
    from Fission180Tests.gui import selection_input as sel

    sel.box_around(RECT, margin=14)


def b_boxed():
    t = scaling()
    h.check("B: the box took the rectangle's 4 lines", sorted(t.objects) == [0, 1, 2, 3], t.objects)
    h.check("B: the arrow shows", t.arrow is not None and t.arrow.attached)
    h.check(
        "B: the base point is their middle until one is picked", t.base() == (20.0, 15.0), t.base()
    )
    note = widget("Fission180SketchScalePointNote").text()
    h.check("B: the panel says where the base point is", "middle" in note, note)
    h.shot("B-picked")


# -- C: the arrow dragged ----------------------------------------------------------------------
def c_drag():
    t = scaling()
    foot = t.arrow.foot()
    tip = t.arrow.tip()
    s["ref"] = t.ref()
    s["mm"] = si.mm_per_pixel(sk())
    start = V(foot[0] + 0.6 * (tip[0] - foot[0]), foot[1], 0)
    pos = st.press(start)
    end = st.drag_to(start + V(0.5 * s["ref"], 0, 0), steps=12)
    st.release(end)
    del pos


def c_dragged():
    t = scaling()
    tol = 4 * s["mm"] / s["ref"]
    h.check(
        "C: the arrow half its distance further out: about 1.5",
        abs(t.factor - 1.5) <= tol,
        (t.factor, tol),
    )
    factor = widget("Fission180SketchScaleFactor").text()
    percent = widget("Fission180SketchScalePercent").text()
    h.check("C: the Scale Factor box follows", abs(float(factor) - t.factor) < 1e-4, factor)
    h.check(
        "C: the Percent box follows",
        abs(float(percent.rstrip(" %")) - t.factor * 100) < 1e-2,
        percent,
    )
    h.check("C: the scaled curves show", len(t.preview.drawn().get("curves", [])) == 4)
    h.check("C: nothing changed in the sketch yet", line_is(0, RECT[0], RECT[1]))
    h.shot("C-dragged")


# -- D: typed, the base point picked, OK -------------------------------------------------------
def d_percent_in_factor():
    type_field("Fission180SketchScaleFactor", "50%")


def d_half():
    t = scaling()
    h.check("D: 50% typed as the factor is 0.5", abs(t.factor - 0.5) < 1e-12, t.factor)
    h.check(
        "D: Percent says 50 %",
        widget("Fission180SketchScalePercent").text() == "50 %",
        widget("Fission180SketchScalePercent").text(),
    )
    type_field("Fission180SketchScalePercent", "200")


def d_double():
    t = scaling()
    h.check(
        "D: 200 typed as the percentage is a factor of 2", abs(t.factor - 2.0) < 1e-12, t.factor
    )
    h.check(
        "D: Scale Factor says 2",
        widget("Fission180SketchScaleFactor").text() == "2",
        widget("Fission180SketchScaleFactor").text(),
    )


def d_point_field():
    click_widget("Fission180SketchScalePoint")


def d_point():
    h.wait_for(lambda: scaling().field == "point", "Point to be the active selection")
    st.click(V(10, 10, 0), towards=V(-0.6, -1.0, 0))


def d_ok():
    t = scaling()
    h.check("D: the corner is the base point", t.picked_base == (10.0, 10.0), t.picked_base)
    s["undo"] = len(App.ActiveDocument.UndoNames)
    h.shot("D-ready")
    click_widget("Fission180SketchScalePanelOK")


def d_scaled():
    h.settle("the scale")
    h.check("D: the bottom line (10,10)-(50,10)", line_is(0, V(10, 10, 0), V(50, 10, 0)), ends(0))
    h.check("D: the right line (50,10)-(50,30)", line_is(1, V(50, 10, 0), V(50, 30, 0)), ends(1))
    h.check("D: the top line (50,30)-(10,30)", line_is(2, V(50, 30, 0), V(10, 30, 0)), ends(2))
    width, height = constraint("width"), constraint("height")
    h.check(
        "D: the width dimension now 40",
        width is not None and abs(width.Value - 40) < 1e-9,
        width.Value if width else None,
    )
    h.check(
        "D: the height dimension now 20",
        height is not None and abs(height.Value - 20) < 1e-9,
        height.Value if height else None,
    )
    h.check("D: the joined line left where it was", line_is(5, V(30, 20, 0), V(40, 30, 0)), ends(5))
    tie = [c for c in sk().Constraints if c.Type == "Coincident" and 5 in (c.First, c.Second)]
    h.check("D: its tie to the moved corner went", not tie, tie)
    h.check(
        "D: the circle unchanged",
        si.vnear(sk().Geometry[4].Center, V(50, 15, 0)) and abs(sk().Geometry[4].Radius - 4) < 1e-9,
    )
    st.sketch_ok("D")
    undo = list(App.ActiveDocument.UndoNames)
    h.check(
        "D: one undo step Sketch Scale",
        undo and undo[0] == "Sketch Scale" and len(undo) == s["undo"] + 1,
        undo[:3],
    )
    nothing_left("D")
    h.shot("D-scaled")


# -- E -----------------------------------------------------------------------------------------
def e_undo():
    st.undo()


def e_undone():
    h.settle("the undo")
    h.check(
        "E: Ctrl+Z puts the rectangle back",
        line_is(0, RECT[0], RECT[1]) and line_is(1, RECT[1], RECT[2]),
        ends(0),
    )
    h.check("E: and its width", abs(constraint("width").Value - 20) < 1e-9)
    h.check("E: and the tie", len(sk().Constraints) == s["cons"])


# -- F: selected first, from the origin --------------------------------------------------------
def f_select():
    si.click(V(-6, -6, 0), V(-0.3, 1.0, 0))


def f_start():
    h.check("F: the line is selected", bool(Gui.Selection.getSelectionEx()))
    si.menu_item("MODIFY", "Sketch Scale")


def f_ready():
    h.wait_for(lambda: panel() is not None, "the SKETCH SCALE panel")
    t = scaling()
    h.check("F: the selected line is the Objects", t.objects == [7], t.objects)
    h.check("F: Point is active next", t.field == "point", t.field)
    h.check(
        "F: the base point is the origin (the line starts there)", t.base() == (0.0, 0.0), t.base()
    )
    type_field("Fission180SketchScaleFactor", "2")


def f_enter():
    QtTest.QTest.keyClick(widget("Fission180SketchScaleFactor"), QtCore.Qt.Key_Return)
    QtWidgets.QApplication.processEvents()


def f_scaled():
    h.settle("the scale")
    h.check("F: the line (0,0)-(-20,-20)", line_is(7, V(0, 0, 0), V(-20, -20, 0)), ends(7))
    tie = [c for c in sk().Constraints if c.Type == "Coincident" and 7 in (c.First, c.Second)]
    h.check("F: still joined to the origin", len(tie) == 1, tie)
    st.sketch_ok("F")
    nothing_left("F")
    st.undo()


def f_undone():
    h.settle("the undo")
    h.check("F: Ctrl+Z puts it back", line_is(7, V(0, 0, 0), V(-10, -10, 0)), ends(7))


# -- G: Esc ------------------------------------------------------------------------------------
def g_start():
    Gui.Selection.clearSelection()
    si.menu_item("MODIFY", "Sketch Scale")


def g_box():
    from Fission180Tests.gui import selection_input as sel

    h.wait_for(lambda: panel() is not None, "the SKETCH SCALE panel")
    sel.box_around(RECT, margin=14)


def g_drag():
    t = scaling()
    foot, tip = t.arrow.foot(), t.arrow.tip()
    start = V(foot[0] + 0.6 * (tip[0] - foot[0]), foot[1], 0)
    st.press(start)
    end = st.drag_to(start + V(5, 0, 0), steps=8)
    st.release(end)


def g_esc():
    h.check(
        "G: dragged",
        scaling() is not None and scaling().factor > 1.01,
        scaling().factor if scaling() else None,
    )
    si.key(QtCore.Qt.Key_Escape)


def g_nothing():
    h.settle("Esc")
    h.check("G: Esc scaled nothing", line_is(0, RECT[0], RECT[1]), ends(0))
    nothing_left("G")


def finish():
    h.ribbon("Finish Sketch")


def end():
    h.check("the sketch is closed", h.in_sketch() is None)
    h.expect_no_errors("the SKETCH SCALE panel")


STEPS = [
    new_design,
    create_sketch,
    pick_xy,
    opened,
    a_line_tool,
    a_button,
    a_panel,
    b_box,
    b_boxed,
    c_drag,
    c_dragged,
    d_percent_in_factor,
    d_half,
    d_double,
    d_point_field,
    d_point,
    d_ok,
    d_scaled,
    e_undo,
    e_undone,
    f_select,
    f_start,
    f_ready,
    f_enter,
    f_scaled,
    f_undone,
    g_start,
    g_box,
    g_drag,
    g_esc,
    g_nothing,
    finish,
    end,
]

h.run("sketch_scale_dialog", si.watched(STEPS), paced_by="state")
