# SPDX-License-Identifier: LGPL-2.1-or-later
"""Sketch Fillet with its FILLET panel and radius arrow (fission180/sketch_fillet_tool.py; Luca,
2026-11-10: "sketch fillet just goes the second you touch a corner. it follows your mouse.
Why? theres zero control that way ... all the tools should have some sort of dialogue box
that displays the numbers of the operation. and there should be a button to finish that
operation").

The sketch: a 40 x 30 rectangle (0,0)-(40,30), fully dimensioned (lines 0 bottom, 1 right,
2 top, 3 left), and two lines meeting at (60,0): (60,0)-(100,0) (4) and (60,0)-(60,30) (5).

A  L (a drawing tool), then MODIFY > Fillet: the FILLET panel (Corners, Radius; OK greyed),
   Fission 180's Fillet pointer, no arrow yet.
B  The pointer on the corner (40,0): its sides and the arc it would get light up, the dot on
   the corner; nothing is made. A click: 1 corner, the radius a fifth of the 30 mm side (6),
   the arc shows, the arrow stands on its middle, the R box by it. The pointer far away: the
   radius stays 6 (the pointer does not size it).
C  A click on (40,30) adds it (2 corners), a second click drops it (1 corner).
D  The arrow dragged 4 (sqrt 2 - 1) mm further out: the radius 10 (the arc's middle runs
   sqrt 2 - 1 per mm of radius), the arc and the arrow follow it exactly, the panel shows it.
E  7 typed over the sketch, Tab: radius 7; 8 typed in the panel's Radius: radius 8.
F  OK: one arc r 8 at (32,8), the bottom line ends at (32,0), the right line starts at
   (40,8), a Radius dimension 8, the old corner a construction point; the sketch solves; one
   undo step "Fillet"; the panel, the arrow, the preview and the box are gone.
G  Ctrl+Z puts the corner back.
H  Fillet again starts at 8 (the last radius); the corner (0,0) and the two lines 4 and 5
   clicked as a pair: 2 corners; Cancel: nothing made, nothing left.
I  Fillet, the corner (0,30), Esc: nothing made, nothing left.
J  Fillet, the corner (0,0), MODIFY > Fillet again: still running, the corner kept; Enter:
   the fillet r 8 at (0,0) exactly, one undo step.
K  Fillet, the corner (40,30), 50 typed in the panel: held at 30 (the 30 mm side), the panel
   says so; Cancel.
"""

import math

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st
from Fission180Tests.gui import widget_input as wi

V = App.Vector
s = st.s
ARC = "Part::GeomArcOfCircle"
K = math.sqrt(2.0) - 1.0  # how far the arc's middle moves per mm of radius (square corner)


def panel():
    w = Gui.getMainWindow().findChild(QtWidgets.QFrame, "Fission180SketchFilletPanel")
    return w if w is not None and w.isVisible() else None


def widget(name):
    p = panel()
    return p.findChild(QtWidgets.QWidget, name) if p is not None else None


def click_widget(name):
    w = widget(name)
    if not h.check("the FILLET panel has %s" % name, w is not None and w.isVisible()):
        return
    wi.click(w)


def type_field(name, text):
    w = widget(name)
    if not h.check("the FILLET panel has %s" % name, w is not None and w.isVisible()):
        return
    wi.click(w)
    QtTest.QTest.keyClick(w, QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
    QtTest.QTest.keyClicks(w, text)
    QtWidgets.QApplication.processEvents()


def filleting():
    t = st.tool()
    return t if t is not None and t.title == "Fillet" else None


def sk():
    return s["sk"]


def arcs():
    return [(i, g) for i, g in enumerate(sk().Geometry) if g.TypeId == ARC]


def leftovers():
    graph = Gui.ActiveDocument.ActiveView.getSceneGraph()
    found = []
    for i in range(graph.getNumChildren()):
        name = graph.getChild(i).getName()
        name = str(name.getString() if hasattr(name, "getString") else name)
        if name in ("Fission180SketchTool", "Fission180SketchHandle"):
            found.append(name)
    return found


def nothing_left(where, count=None):
    h.check(
        "%s: the panel is gone and Fillet ended" % where,
        panel() is None and filleting() is None,
        st.tool_title(),
    )
    h.check("%s: no arrow or preview left in the view" % where, not leftovers(), leftovers())
    h.check("%s: no value box left" % where, not st.box_texts(), st.box_texts())
    if count is not None:
        h.check(
            "%s: no curve added" % where, len(sk().Geometry) == count, (len(sk().Geometry), count)
        )


def radius_text():
    w = widget("Fission180SketchFilletRadius")
    edit = w.findChild(QtWidgets.QLineEdit) if w is not None else None
    return edit.text() if edit is not None else ""


def shown_value(text):
    try:
        return float(text.replace(",", ".").split()[0])
    except Exception:
        return None


def arrow():
    t = filleting()
    if t is None or t.arrows is None:
        return None
    a = t.arrows.items.get("radius")
    return a if a is not None and a.attached else None


def curves_now(t, picks):
    return t._curve(picks[0]), t._curve(picks[1])


def told():
    from fission180 import commands

    return commands._TOLD["msg"] or ""


# -- setup -------------------------------------------------------------------------------------
def shapes():
    import Part
    import Sketcher

    doc = App.ActiveDocument
    doc.openTransaction("Setup")
    sketch = sk()
    p = [V(0, 0, 0), V(40, 0, 0), V(40, 30, 0), V(0, 30, 0)]
    g = [sketch.addGeometry(Part.LineSegment(p[i], p[(i + 1) % 4])) for i in range(4)]
    for i in range(4):
        sketch.addConstraint(Sketcher.Constraint("Coincident", g[i], 2, g[(i + 1) % 4], 1))
    sketch.addConstraint(Sketcher.Constraint("Horizontal", g[0]))
    sketch.addConstraint(Sketcher.Constraint("Horizontal", g[2]))
    sketch.addConstraint(Sketcher.Constraint("Vertical", g[1]))
    sketch.addConstraint(Sketcher.Constraint("Vertical", g[3]))
    sketch.addConstraint(Sketcher.Constraint("DistanceX", g[0], 1, g[0], 2, 40.0))
    sketch.addConstraint(Sketcher.Constraint("DistanceY", g[1], 1, g[1], 2, 30.0))
    sketch.addConstraint(Sketcher.Constraint("Coincident", g[0], 1, -1, 1))
    a = sketch.addGeometry(Part.LineSegment(V(60, 0, 0), V(100, 0, 0)))
    b = sketch.addGeometry(Part.LineSegment(V(60, 0, 0), V(60, 30, 0)))
    sketch.addConstraint(Sketcher.Constraint("Coincident", a, 1, b, 1))
    sketch.solve()
    doc.commitTransaction()
    doc.recompute()
    h.fit(iso=False)
    s["count"] = len(sketch.Geometry)


# -- A -----------------------------------------------------------------------------------------
def a_line_tool():
    st.hover(V(20, 50, 0))
    h.press("l")


def a_button():
    h.wait_for(si.drawing, "the Line tool to run")
    si.menu_item("MODIFY", "Fillet")


def a_panel():
    from fission180 import sketch_cursor

    h.wait_for(lambda: panel() is not None, "the FILLET panel")
    h.check("A: Fillet runs (the Line tool ended)", filleting() is not None, st.tool_title())
    viewer = st.session().viewer if st.session().viewer is not None else h.gl_widget()
    own = sketch_cursor.cursor_for("Fission180_SketchFillet", viewer)
    h.check(
        "A: Fission 180's Fillet pointer",
        viewer.cursor().pixmap().cacheKey() == own.pixmap().cacheKey(),
    )
    h.check("A: OK greyed before a corner is picked", not widget("Fission180SketchFilletPanelOK").isEnabled())
    h.check(
        "A: Corners and Radius in the panel",
        widget("Fission180SketchFilletCorners") is not None
        and widget("Fission180SketchFilletRadius") is not None,
    )
    h.check(
        "A: Corners says Select",
        widget("Fission180SketchFilletCorners").text() == "Select",
        widget("Fission180SketchFilletCorners").text(),
    )
    h.check("A: no arrow yet", arrow() is None)
    h.shot("A-panel")


# -- B -----------------------------------------------------------------------------------------
def b_hover():
    st.hover(V(40.3, 0.4, 0), towards=V(1.0, -0.6, 0))


def b_hover_check():
    t = filleting()
    drawn = st.preview()
    marks = drawn.get("marks", [])
    h.check("B: the corner's two sides and its arc light up", len(marks) == 3, len(marks))
    dot = drawn.get("dot") or [None]
    h.check(
        "B: the dot on the corner",
        dot[0] is not None and st.vnear(V(dot[0][0], dot[0][1], 0), V(40, 0, 0)),
        dot,
    )
    h.check("B: nothing picked or made by hovering", not t.corners and len(arcs()) == 0)
    h.shot("B-hover")
    st.click(V(40, 0, 0), towards=V(1.0, -0.6, 0))


def b_clicked():
    t = filleting()
    h.check("B: one corner picked", t is not None and len(t.corners) == 1, t and t.corners)
    h.check(
        "B: the panel says 1 selected",
        widget("Fission180SketchFilletCorners").text() == "1 selected",
        widget("Fission180SketchFilletCorners").text(),
    )
    h.check("B: the radius starts at a fifth of the 30 mm side", st.near(t.held(), 6.0), t.held())
    h.check("B: the panel shows 6", st.near(shown_value(radius_text()) or 0, 6.0), radius_text())
    h.check("B: OK can be pressed", widget("Fission180SketchFilletPanelOK").isEnabled())
    h.check("B: the arc shows", len(st.preview().get("curves", [])) == 1, st.preview().get("curves"))
    a = arrow()
    h.check("B: the arrow is up", a is not None)
    if a is not None:
        from fission180 import sketch_fillet_core as core

        picks, refs = t.corners[0]
        c1, c2 = curves_now(t, picks)
        mid = core.arc_middle(c1, c2, 6.0, refs[0], refs[1])
        h.check(
            "B: it stands on the arc's middle",
            st.vnear(V(a.foot[0], a.foot[1], 0), V(mid[0], mid[1], 0), 1e-9),
            (a.foot, mid),
        )
        h.check(
            "B: it points into the corner (the way the radius grows)",
            st.vnear(V(a.direction[0], a.direction[1], 0), V(-1, 1, 0) * (1 / math.sqrt(2)), 1e-6),
            a.direction,
        )
    h.check("B: the R box by the arrow", any(b.startswith("R ") for b in st.box_texts()), st.box_texts())
    h.shot("B-picked")
    st.hover(V(-30, 60, 0), towards=V(-1.0, 1.0, 0))


def b_away():
    t = filleting()
    h.check("B: the pointer far away: still 6", st.near(t.held(), 6.0), t.held())
    h.check("B: nothing made yet", len(arcs()) == 0)


# -- C -----------------------------------------------------------------------------------------
def c_add():
    st.click(V(40, 30, 0), towards=V(1.0, 0.6, 0))


def c_added():
    t = filleting()
    h.check("C: a second corner", len(t.corners) == 2, t.corners)
    h.check("C: two arcs show", len(st.preview().get("curves", [])) == 2)
    h.check(
        "C: the panel says 2 selected",
        widget("Fission180SketchFilletCorners").text() == "2 selected",
        widget("Fission180SketchFilletCorners").text(),
    )
    st.click(V(40, 30, 0), towards=V(1.0, 0.6, 0))


def c_dropped():
    t = filleting()
    h.check("C: clicked again it is dropped", len(t.corners) == 1, t.corners)
    h.check("C: one arc shows again", len(st.preview().get("curves", [])) == 1)


# -- D: the arrow dragged ------------------------------------------------------------------------
def d_drag():
    a = arrow()
    if not h.check("D: the arrow is there to drag", a is not None):
        return
    s["mm"] = si.mm_per_pixel(sk())
    foot, tip = a.foot, a.tip()
    start = V(foot[0] + 0.6 * (tip[0] - foot[0]), foot[1] + 0.6 * (tip[1] - foot[1]), 0)
    d = V(a.direction[0], a.direction[1], 0)
    st.press(start)
    end = st.drag_to(start + d * (4 * K), steps=12)
    st.release(end)


def d_dragged():
    from fission180 import sketch_fillet_core as core

    t = filleting()
    r = t.held()
    tol = 4 * s["mm"] / K + 0.011
    h.check("D: dragged 4 (sqrt 2 - 1) mm out: radius 10", abs(r - 10.0) <= tol, (r, tol))
    picks, refs = t.corners[0]
    c1, c2 = curves_now(t, picks)
    centre, t1, t2 = core.check(c1, c2, r, refs[0], refs[1])
    h.check(
        "D: the arc follows exactly (centre (40 - r, r))",
        st.vnear(V(centre[0], centre[1], 0), V(40 - r, r, 0), 1e-9),
        (centre, r),
    )
    shown = st.preview().get("curves", [[]])[0]
    ends = (shown[0], shown[-1]) if shown else ()
    h.check(
        "D: the arc drawn touches (40 - r, 0) and (40, r)",
        len(ends) == 2
        and {(round(p[0], 6), round(p[1], 6)) for p in ends}
        == {(round(40 - r, 6), 0.0), (40.0, round(r, 6))},
        ends,
    )
    a = arrow()
    mid = core.arc_middle(c1, c2, r, refs[0], refs[1])
    h.check(
        "D: the arrow follows the arc's middle",
        a is not None and st.vnear(V(a.foot[0], a.foot[1], 0), V(mid[0], mid[1], 0), 1e-9),
        a and (a.foot, mid),
    )
    h.check("D: the panel shows it", st.near(shown_value(radius_text()) or 0, r, 0.006), radius_text())
    h.check("D: nothing made by dragging", len(arcs()) == 0)
    h.shot("D-dragged")


# -- E: typed --------------------------------------------------------------------------------------
def e_type_view():
    st.hover(V(20, 15, 0))  # (the keyboard is the 3D view's while the pointer is on it)
    st.keys("7\t")


def e_typed_view():
    t = filleting()
    h.check("E: 7 typed over the sketch, Tab: radius 7", st.near(t.held(), 7.0, 1e-12), t.held())
    h.check("E: the panel follows", st.near(shown_value(radius_text()) or 0, 7.0), radius_text())
    type_field("Fission180SketchFilletRadius", "8")


def e_typed_panel():
    t = filleting()
    h.check("E: 8 typed in the panel: radius 8", st.near(t.held(), 8.0, 1e-12), t.held())
    shown = st.preview().get("curves", [[]])[0]
    h.check(
        "E: the arc drawn follows (it ends at (32, 0))",
        bool(shown) and any(st.vnear(V(p[0], p[1], 0), V(32, 0, 0), 1e-6) for p in (shown[0], shown[-1])),
        shown and (shown[0], shown[-1]),
    )
    a = arrow()
    mid = V(32 + 8 / math.sqrt(2), 8 - 8 / math.sqrt(2), 0)  # the arc's middle: centre (32, 8)
    h.check(
        "E: the arrow follows (on the arc's middle)",
        a is not None and st.vnear(V(a.foot[0], a.foot[1], 0), mid, 1e-9),
        a and (a.foot, mid),
    )


# -- F: OK -------------------------------------------------------------------------------------------
def f_ok():
    s["undo"] = len(App.ActiveDocument.UndoNames)
    s["before"] = len(sk().Geometry)
    h.shot("F-ready")
    click_widget("Fission180SketchFilletPanelOK")


def f_made():
    h.settle("the fillet")
    found = arcs()
    h.check("F: one arc", len(found) == 1, found)
    if found:
        i, g = found[0]
        h.check("F: radius 8", st.near(g.Radius, 8.0, 1e-9), g.Radius)
        h.check("F: centred at (32, 8)", st.vnear(g.Center, V(32, 8, 0), 1e-9), g.Center)
        radius = [c for c in sk().Constraints if c.Type == "Radius" and c.First == i]
        h.check(
            "F: a Radius dimension 8",
            len(radius) == 1 and st.near(radius[0].Value, 8.0),
            [(c.Type, c.Value) for c in radius],
        )
    g = sk().Geometry
    h.check(
        "F: the bottom line ends at (32, 0)",
        st.vnear(g[0].StartPoint, V(0, 0, 0), 1e-9) and st.vnear(g[0].EndPoint, V(32, 0, 0), 1e-9),
        (g[0].StartPoint, g[0].EndPoint),
    )
    h.check(
        "F: the right line starts at (40, 8)",
        st.vnear(g[1].StartPoint, V(40, 8, 0), 1e-9) and st.vnear(g[1].EndPoint, V(40, 30, 0), 1e-9),
        (g[1].StartPoint, g[1].EndPoint),
    )
    points = [
        j for j, x in enumerate(g) if x.TypeId == "Part::GeomPoint" and st.vnear(V(x.X, x.Y, 0), V(40, 0, 0))
    ]
    h.check(
        "F: the old corner stays a construction point",
        len(points) == 1 and sk().getConstruction(points[0]),
        points,
    )
    h.check(
        "F: only the arc and the corner point were added",
        len(g) == s["before"] + 2,
        len(g) - s["before"],
    )
    st.sketch_ok("F")
    undo = list(App.ActiveDocument.UndoNames)
    h.check(
        "F: one undo step Fillet",
        undo and undo[0] == "Fillet" and len(undo) == s["undo"] + 1,
        undo[:3],
    )
    nothing_left("F")
    h.shot("F-made")
    st.undo()


# -- G -----------------------------------------------------------------------------------------------
def g_undone():
    h.settle("the undo")
    h.check("G: Ctrl+Z: no arc", not arcs(), arcs())
    h.check("G: the corner is back", st.vnear(sk().Geometry[0].EndPoint, V(40, 0, 0)))
    si.menu_item("MODIFY", "Fillet")


# -- H: the last radius, a pair of curves, Cancel -------------------------------------------------------
def h_corner():
    h.wait_for(lambda: panel() is not None, "the FILLET panel")
    st.click(V(0, 0, 0), towards=V(-1.0, -0.6, 0))


def h_pair():
    t = filleting()
    h.check("H: it starts with the last radius (8)", st.near(t.held(), 8.0, 1e-12), t.held())
    st.click(V(85, 0, 0), towards=V(0.3, -1.0, 0))


def h_pair_second():
    t = filleting()
    h.check("H: the first curve of the pair waits", t.pending is not None and t.pending[0] == 4, t.pending)
    st.click(V(60, 18, 0), towards=V(-1.0, 0.3, 0))


def h_pair_check():
    t = filleting()
    h.check(
        "H: the two lines are the second corner",
        len(t.corners) == 2 and sorted(t.corners[1][0]) == [4, 5],
        t.corners,
    )
    h.check("H: two arcs show", len(st.preview().get("curves", [])) == 2)
    h.shot("H-pair")
    click_widget("Fission180SketchFilletPanelCancel")


def h_cancelled():
    h.settle("Cancel")
    h.check("H: Cancel made nothing", not arcs(), arcs())
    nothing_left("H", s["count"])
    si.menu_item("MODIFY", "Fillet")


# -- I: Esc ---------------------------------------------------------------------------------------------
def i_corner():
    h.wait_for(lambda: panel() is not None, "the FILLET panel")
    st.click(V(0, 30, 0), towards=V(-1.0, 0.6, 0))


def i_esc():
    t = filleting()
    h.check("I: the corner picked", t is not None and len(t.corners) == 1)
    st.esc()


def i_nothing():
    h.settle("Esc")
    h.check("I: Esc made nothing", not arcs(), arcs())
    nothing_left("I", s["count"])
    si.menu_item("MODIFY", "Fillet")


# -- J: the command again, then Enter ------------------------------------------------------------------
def j_corner():
    h.wait_for(lambda: panel() is not None, "the FILLET panel")
    st.click(V(0, 0, 0), towards=V(-1.0, -0.6, 0))


def j_again():
    s["tool"] = filleting()
    si.menu_item("MODIFY", "Fillet")


def j_still():
    t = filleting()
    h.check("J: Fillet again: it keeps running", t is not None and t is s["tool"], st.tool_title())
    h.check("J: the corner is kept", t is not None and len(t.corners) == 1, t and t.corners)
    s["undo"] = len(App.ActiveDocument.UndoNames)
    st.hover(V(20, 15, 0))
    st.enter()


def j_made():
    h.settle("Enter")
    found = arcs()
    h.check("J: Enter made the fillet", len(found) == 1, found)
    if found:
        g = found[0][1]
        h.check("J: radius 8 at (8, 8)", st.near(g.Radius, 8.0, 1e-9) and st.vnear(g.Center, V(8, 8, 0), 1e-9), (g.Radius, g.Center))
    st.sketch_ok("J")
    undo = list(App.ActiveDocument.UndoNames)
    h.check("J: one undo step", undo and undo[0] == "Fillet" and len(undo) == s["undo"] + 1, undo[:3])
    nothing_left("J")
    st.undo()


# -- K: too big ----------------------------------------------------------------------------------------
def k_open():
    h.settle("the undo")
    h.check("J: Ctrl+Z took it back", not arcs(), arcs())
    si.menu_item("MODIFY", "Fillet")


def k_corner():
    h.wait_for(lambda: panel() is not None, "the FILLET panel")
    st.click(V(40, 30, 0), towards=V(1.0, 0.6, 0))


def k_type():
    type_field("Fission180SketchFilletRadius", "50")


def k_held():
    t = filleting()
    h.check("K: 50 is held at 30 (the 30 mm side)", st.near(t.held(), 30.0, 1e-6), t.held())
    note = widget("Fission180SketchFilletPanelMessage").text()
    h.check("K: the panel says so", "limited to 30" in note, note)
    h.shot("K-held")
    click_widget("Fission180SketchFilletPanelCancel")


def k_nothing():
    h.settle("Cancel")
    nothing_left("K", s["count"])


def finish():
    h.ribbon("Finish Sketch")


def end():
    h.check("the sketch is closed", h.in_sketch() is None)
    h.expect_no_errors("the FILLET panel")


STEPS = st.start_steps("FilletPanel") + [
    shapes,
    a_line_tool,
    a_button,
    a_panel,
    b_hover,
    b_hover_check,
    b_clicked,
    b_away,
    c_add,
    c_added,
    c_dropped,
    d_drag,
    d_dragged,
    e_type_view,
    e_typed_view,
    e_typed_panel,
    f_ok,
    f_made,
    g_undone,
    h_corner,
    h_pair,
    h_pair_second,
    h_pair_check,
    h_cancelled,
    i_corner,
    i_esc,
    i_nothing,
    j_corner,
    j_again,
    j_still,
    j_made,
    k_open,
    k_corner,
    k_type,
    k_held,
    k_nothing,
    finish,
    end,
]

h.run("sketch_fillet_panel", si.watched(STEPS), paced_by="state")
