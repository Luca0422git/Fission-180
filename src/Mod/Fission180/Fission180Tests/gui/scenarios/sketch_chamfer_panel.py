# SPDX-License-Identifier: LGPL-2.1-or-later
"""Sketch Chamfer with its CHAMFER panel and drag arrows (fission180/sketch_chamfer_tool.py;
Luca, 2026-11-10: "all the tools should have some sort of dialogue box that displays the
numbers of the operation. and there should be a button to finish that operation").

The sketch: a 40 x 30 rectangle (0,0)-(40,30), fully dimensioned (lines 0 bottom, 1 right,
2 top, 3 left).

A  MODIFY > Chamfer: the CHAMFER panel (Chamfer Type, Corner, Distance; OK greyed).
B  Equal distance; a click on the corner (40,0): 1 selected, the distance a fifth of the
   30 mm side (6), the chamfer (34,0)-(40,6) shows, an arrow on the bottom line at (34,0)
   pointing away from the corner; the pointer far away changes nothing.
C  The arrow dragged 4 mm further: distance 10, the chamfer (30,0)-(40,10) exactly as the
   value says, the panel follows.
D  8 typed in the panel's Distance; Two distances: Distance 1 and Distance 2 in the panel,
   two arrows; the second arrow dragged 3 mm further (along the right side); 6 typed in
   Distance 2.
E  OK: the chamfer line (32,0)-(40,6), dimensions 8 and 6 from the old corner (a
   construction point); the sketch solves; one undo step "Chamfer"; nothing left behind.
F  Ctrl+Z puts the corner back.
G  Chamfer again (Two distances remembered), Distance and angle: Distance and Angle in the
   panel; the corner (0,0); 5, Tab, 30 typed over the sketch: the chamfer 5 along the bottom
   line at 30 degrees to it; Cancel: nothing made, nothing left.
H  Chamfer, the corner (40,0), the same corner again: dropped; the corner (0,30): picked;
   Esc: nothing made, nothing left.
"""

import math
import re

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st
from Fission180Tests.gui import widget_input as wi

V = App.Vector
s = st.s
LINE = "Part::GeomLineSegment"


def panel():
    w = Gui.getMainWindow().findChild(QtWidgets.QFrame, "Fission180SketchChamferPanel")
    return w if w is not None and w.isVisible() else None


def widget(name):
    p = panel()
    return p.findChild(QtWidgets.QWidget, name) if p is not None else None


def shown(name):
    w = widget(name)
    return w is not None and w.isVisible()


def click_widget(name):
    w = widget(name)
    if not h.check("the CHAMFER panel has %s" % name, w is not None and w.isVisible()):
        return
    wi.click(w)


def type_field(name, text):
    w = widget(name)
    if not h.check("the CHAMFER panel has %s" % name, w is not None and w.isVisible()):
        return
    wi.click(w)
    QtTest.QTest.keyClick(w, QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
    QtTest.QTest.keyClicks(w, text)
    QtWidgets.QApplication.processEvents()


def field_value(name):
    w = widget(name)
    edit = w.findChild(QtWidgets.QLineEdit) if w is not None else None
    found = re.match(r"\s*(-?[0-9]+(?:[.,][0-9]*)?)", edit.text() if edit is not None else "")
    return float(found.group(1).replace(",", ".")) if found else None


def choose(label):
    combo = widget("Fission180SketchChamferType")
    if h.check("the Chamfer Type drop-down", combo is not None and combo.isVisible()):
        h.check("type %s" % label, ui.choose(combo, label))


def chamfering():
    t = st.tool()
    return t if t is not None and t.title == "Chamfer" else None


def sk():
    return s["sk"]


def arrow(name):
    t = chamfering()
    if t is None or t.arrows is None:
        return None
    a = t.arrows.items.get(name)
    return a if a is not None and a.attached else None


def preview_line():
    curves = st.preview().get("curves", [])
    return curves[0] if len(curves) == 1 else None


def line_is(poly, a, b, tol=1e-9):
    if not poly or len(poly) != 2:
        return False
    p, q = V(poly[0][0], poly[0][1], 0), V(poly[1][0], poly[1][1], 0)
    return (st.vnear(p, a, tol) and st.vnear(q, b, tol)) or (st.vnear(p, b, tol) and st.vnear(q, a, tol))


def chamfer_lines(a, b, tol=1e-9):
    out = []
    for i, g in enumerate(sk().Geometry):
        if g.TypeId == LINE and line_is([(g.StartPoint.x, g.StartPoint.y), (g.EndPoint.x, g.EndPoint.y)], a, b, tol):
            out.append(i)
    return out


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
        "%s: the panel is gone and Chamfer ended" % where,
        panel() is None and chamfering() is None,
        st.tool_title(),
    )
    h.check("%s: no arrow or preview left in the view" % where, not leftovers(), leftovers())
    h.check("%s: no value box left" % where, not st.box_texts(), st.box_texts())
    if count is not None:
        h.check("%s: no curve added" % where, len(sk().Geometry) == count, (len(sk().Geometry), count))


def drag_arrow(name, mm):
    a = arrow(name)
    if not h.check("the %s arrow is there to drag" % name, a is not None):
        return
    foot, tip = a.foot, a.tip()
    start = V(foot[0] + 0.6 * (tip[0] - foot[0]), foot[1] + 0.6 * (tip[1] - foot[1]), 0)
    d = V(a.direction[0], a.direction[1], 0)
    st.press(start)
    end = st.drag_to(start + d * mm, steps=12)
    st.release(end)


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
    sketch.solve()
    doc.commitTransaction()
    doc.recompute()
    h.fit(iso=False)
    s["count"] = len(sketch.Geometry)


# -- A -----------------------------------------------------------------------------------------
def a_open():
    st.hover(V(20, 50, 0))
    si.menu_item("MODIFY", "Chamfer")


def a_panel():
    h.wait_for(lambda: panel() is not None, "the CHAMFER panel")
    h.check("A: Chamfer runs", chamfering() is not None, st.tool_title())
    h.check("A: OK greyed before a corner is picked", not widget("Fission180SketchChamferPanelOK").isEnabled())
    h.check(
        "A: Chamfer Type, Corner and Distance in the panel",
        shown("Fission180SketchChamferType")
        and shown("Fission180SketchChamferCorner")
        and shown("Fission180SketchChamferDistance"),
    )
    h.shot("A-panel")
    choose("Equal distance")


# -- B -----------------------------------------------------------------------------------------
def b_corner():
    h.check("B: Equal distance: one value", not shown("Fission180SketchChamferDistance2") and not shown("Fission180SketchChamferAngle"))
    st.click(V(40, 0, 0), towards=V(1.0, -0.6, 0))


def b_picked():
    t = chamfering()
    h.check("B: the corner picked", t is not None and sorted(t.picks) == [0, 1], t and t.picks)
    h.check(
        "B: the panel says 1 selected",
        widget("Fission180SketchChamferCorner").text() == "1 selected",
        widget("Fission180SketchChamferCorner").text(),
    )
    d = t.now["shown"]["distance"]
    h.check("B: the distance starts at a fifth of the 30 mm side", st.near(d, 6.0), d)
    h.check("B: the panel shows 6", st.near(field_value("Fission180SketchChamferDistance") or 0, 6.0))
    h.check("B: the chamfer (34,0)-(40,6) shows", line_is(preview_line(), V(34, 0, 0), V(40, 6, 0)), preview_line())
    a = arrow("distance")
    h.check(
        "B: an arrow on the bottom line at (34,0), pointing away from the corner",
        a is not None
        and st.vnear(V(a.foot[0], a.foot[1], 0), V(34, 0, 0), 1e-9)
        and st.vnear(V(a.direction[0], a.direction[1], 0), V(-1, 0, 0), 1e-9),
        a and (a.foot, a.direction),
    )
    h.check("B: OK can be pressed", widget("Fission180SketchChamferPanelOK").isEnabled())
    h.shot("B-picked")
    st.hover(V(-30, 60, 0), towards=V(-1.0, 1.0, 0))


def b_away():
    t = chamfering()
    h.check("B: the pointer far away changes nothing", st.near(t.now["shown"]["distance"], 6.0))
    s["mm"] = si.mm_per_pixel(sk())
    drag_arrow("distance", 4.0)


# -- C -----------------------------------------------------------------------------------------
def c_dragged():
    t = chamfering()
    d = t.now["shown"]["distance"]
    tol = 4 * s["mm"] + 0.011
    h.check("C: dragged 4 mm further: distance 10", abs(d - 10.0) <= tol, (d, tol))
    h.check(
        "C: the chamfer shows exactly as the value says",
        line_is(preview_line(), V(40 - d, 0, 0), V(40, d, 0)),
        (preview_line(), d),
    )
    a = arrow("distance")
    h.check("C: the arrow follows", a is not None and st.vnear(V(a.foot[0], a.foot[1], 0), V(40 - d, 0, 0), 1e-9))
    h.check("C: the panel follows", st.near(field_value("Fission180SketchChamferDistance") or 0, d, 0.006))
    h.check("C: nothing made by dragging", len(sk().Geometry) == s["count"])
    h.shot("C-dragged")
    type_field("Fission180SketchChamferDistance", "8")


# -- D -----------------------------------------------------------------------------------------
def d_two():
    t = chamfering()
    h.check("D: 8 typed in the panel", st.near(t.now["shown"]["distance"], 8.0, 1e-12), t.now["shown"])
    choose("Two distances")


def d_fields():
    t = chamfering()
    h.check(
        "D: Two distances: Distance 1 and Distance 2",
        shown("Fission180SketchChamferDistance") and shown("Fission180SketchChamferDistance2"),
    )
    h.check("D: two arrows", arrow("distance") is not None and arrow("distance2") is not None)
    a = arrow("distance2")
    h.check(
        "D: the second on the right side, pointing up",
        a is not None and st.near(a.foot[0], 40.0, 1e-9) and st.vnear(V(a.direction[0], a.direction[1], 0), V(0, 1, 0), 1e-9),
        a and (a.foot, a.direction),
    )
    s["second"] = t.now["shown"]["distance2"]
    h.shot("D-two")
    drag_arrow("distance2", 3.0)


def d_dragged():
    t = chamfering()
    d2 = t.now["shown"]["distance2"]
    tol = 4 * s["mm"] + 0.011
    h.check("D: the second arrow dragged 3 mm further", abs(d2 - (s["second"] + 3.0)) <= tol, (d2, s["second"]))
    h.check("D: the first distance stays 8", st.near(t.now["shown"]["distance"], 8.0, 1e-12))
    type_field("Fission180SketchChamferDistance2", "6")


def d_typed():
    t = chamfering()
    h.check("D: 6 typed in Distance 2", st.near(t.now["shown"]["distance2"], 6.0, 1e-12), t.now["shown"])
    h.check("D: the chamfer (32,0)-(40,6) shows", line_is(preview_line(), V(32, 0, 0), V(40, 6, 0)), preview_line())
    s["undo"] = len(App.ActiveDocument.UndoNames)
    s["before"] = len(sk().Geometry)
    click_widget("Fission180SketchChamferPanelOK")


# -- E -----------------------------------------------------------------------------------------
def e_made():
    h.settle("the chamfer")
    found = chamfer_lines(V(32, 0, 0), V(40, 6, 0))
    h.check("E: the chamfer line (32,0)-(40,6)", len(found) == 1, sk().Geometry)
    g = sk().Geometry
    h.check("E: the bottom line ends at (32,0)", st.vnear(g[0].EndPoint, V(32, 0, 0), 1e-9), g[0].EndPoint)
    h.check("E: the right side starts at (40,6)", st.vnear(g[1].StartPoint, V(40, 6, 0), 1e-9), g[1].StartPoint)
    corner = [
        i for i, x in enumerate(g) if x.TypeId == "Part::GeomPoint" and st.vnear(V(x.X, x.Y, 0), V(40, 0, 0))
    ]
    h.check("E: the old corner a construction point", len(corner) == 1 and sk().getConstruction(corner[0]), corner)
    if corner:
        dims = sorted(round(c.Value, 9) for c in sk().Constraints if c.Type == "Distance" and c.First == corner[0])
        h.check("E: dimensions 6 and 8 from it", dims == [6.0, 8.0], dims)
    h.check("E: only the line and the point added", len(g) == s["before"] + 2, len(g) - s["before"])
    st.sketch_ok("E")
    undo = list(App.ActiveDocument.UndoNames)
    h.check("E: one undo step Chamfer", undo and undo[0] == "Chamfer" and len(undo) == s["undo"] + 1, undo[:3])
    nothing_left("E")
    h.shot("E-made")
    st.undo()


# -- F -----------------------------------------------------------------------------------------
def f_undone():
    h.settle("the undo")
    h.check("F: Ctrl+Z puts the corner back", len(sk().Geometry) == s["count"] and st.vnear(sk().Geometry[0].EndPoint, V(40, 0, 0)))
    si.menu_item("MODIFY", "Chamfer")


# -- G -----------------------------------------------------------------------------------------
def g_type():
    h.wait_for(lambda: panel() is not None, "the CHAMFER panel")
    combo = widget("Fission180SketchChamferType")
    h.check("G: Two distances is remembered", combo is not None and combo.currentText() == "Two distances", combo and combo.currentText())
    choose("Distance and angle")


def g_corner():
    h.check(
        "G: Distance and angle: Distance and Angle",
        shown("Fission180SketchChamferDistance") and shown("Fission180SketchChamferAngle")
        and not shown("Fission180SketchChamferDistance2"),
    )
    st.click(V(0, 0, 0), towards=V(-1.0, -0.6, 0))


def g_keys():
    st.hover(V(20, 15, 0))
    st.keys("5\t30")


def g_values():
    t = chamfering()
    st.keys("\t")  # (Tab takes the angle typed)
    v = t.now["shown"]
    h.check("G: distance 5", st.near(v["distance"], 5.0, 1e-12), v)
    h.check("G: angle 30", st.near(math.degrees(v["angle"]), 30.0, 1e-9), v)
    h.check(
        "G: the panel shows them",
        st.near(field_value("Fission180SketchChamferDistance") or 0, 5.0)
        and st.near(field_value("Fission180SketchChamferAngle") or 0, 30.0),
        (field_value("Fission180SketchChamferDistance"), field_value("Fission180SketchChamferAngle")),
    )
    # the bottom line is the first (geometry 0): 5 along it, 30 degrees to it
    p = t.now["p2"]
    h.check(
        "G: the chamfer 5 along the bottom line at 30 degrees to it",
        line_is(preview_line(), V(5, 0, 0), V(p[0], p[1], 0)) and st.near(p[0], 0.0, 1e-9) and st.near(p[1], 5 * math.tan(math.radians(30)), 1e-9),
        (preview_line(), p),
    )
    h.shot("G-angle")
    click_widget("Fission180SketchChamferPanelCancel")


def g_nothing():
    h.settle("Cancel")
    nothing_left("G", s["count"])
    si.menu_item("MODIFY", "Chamfer")


# -- H -----------------------------------------------------------------------------------------
def h_corner():
    h.wait_for(lambda: panel() is not None, "the CHAMFER panel")
    st.click(V(40, 0, 0), towards=V(1.0, -0.6, 0))


def h_again():
    t = chamfering()
    h.check("H: picked", t is not None and len(t.picks) == 2)
    st.click(V(40, 0, 0), towards=V(1.0, -0.6, 0))


def h_dropped():
    t = chamfering()
    h.check("H: the same corner again: dropped", t is not None and not t.picks, t and t.picks)
    h.check("H: OK greyed again", not widget("Fission180SketchChamferPanelOK").isEnabled())
    st.click(V(0, 30, 0), towards=V(-1.0, 0.6, 0))


def h_other():
    t = chamfering()
    h.check("H: another corner picked", t is not None and sorted(t.picks) == [2, 3], t and t.picks)
    st.esc()


def h_nothing():
    h.settle("Esc")
    nothing_left("H", s["count"])


def finish():
    h.ribbon("Finish Sketch")


def end():
    h.check("the sketch is closed", h.in_sketch() is None)
    h.expect_no_errors("the CHAMFER panel")


STEPS = st.start_steps("ChamferPanel") + [
    shapes,
    a_open,
    a_panel,
    b_corner,
    b_picked,
    b_away,
    c_dragged,
    d_two,
    d_fields,
    d_dragged,
    d_typed,
    e_made,
    f_undone,
    g_type,
    g_corner,
    g_keys,
    g_values,
    g_nothing,
    h_corner,
    h_again,
    h_dropped,
    h_other,
    h_nothing,
    finish,
    end,
]

h.run("sketch_chamfer_panel", si.watched(STEPS), paced_by="state")
