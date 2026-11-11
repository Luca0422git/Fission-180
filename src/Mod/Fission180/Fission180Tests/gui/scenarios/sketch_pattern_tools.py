# SPDX-License-Identifier: LGPL-2.1-or-later
"""The sketch Rectangular and Circular Pattern as Fission 180 tools with a panel and drag
handles like the body patterns' (fission180/sketch_pattern_tool.py; Luca, 2026-11-09: "they
should all behave like all the rest of the body tools ... rectangular has arrows to change
spacing, circular has angle dragger").

Setup (by the sketch's API): a 6 x 4 rectangle at the origin (lines 0-3, corners joined,
level and upright), a circle r 2 at (15, 0) with a Radius dimension (4), a circle r 1 at
(-20, 12) (5).

A  Rectangular Pattern from SKETCH > CREATE: the panel shows, Objects active, OK greyed,
   the tool's own pointer. A small box from right to left over the rectangle's right side
   takes only that line; a box from left to right round the rectangle takes its 4 lines (not
   the circles). The copies show; an arrow along the sketch's X and one along its Y.
B  Quantity 4, Distance 30 typed: the arrow stands at 30. The arrow dragged with the mouse
   6 mm on: Distance about 36 in the panel and the copies follow.
C  Distance Type Spacing, Distance 8 typed: the arrow moves to 8. Direction 2: Quantity 2;
   its arrow dragged out: Distance (Y) follows; 12 typed: the arrow moves to 12.
D  OK: 7 copies of the rectangle exactly 8 / 12 apart, corners joined, level and upright as
   the original, the sketch solves cleanly; one undo step "Rectangular Pattern"; the panel,
   the arrows and the preview are gone (the scene has what it had). Ctrl+Z / Ctrl+Y.
E  A click on the small circle picks it; Cancel: nothing is made, nothing is left behind.
F  Circular Pattern: the circle at (15, 0) clicked; Center Point's Select, the origin
   clicked: a Full pattern of 3, the disc at 360 (on the circle). The disc dragged round to
   180: Type Angle, Total Angle 180 (snapped), copies at 90 and 180; on to 90. 270 typed: the
   disc moves; Quantity 4. OK: circles at (0, 15), (-15, 0), (0, -15) exactly, Equal to the
   original (its Radius holds them); one undo step "Circular Pattern".
G  The circle selected first, then Circular Pattern: it is the Objects and Center Point is
   the active selection. Esc: nothing made, the panel gone.
"""

import math

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import selection_input as sel
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st

V = App.Vector
s = {}


def panel():
    w = Gui.getMainWindow().findChild(QtWidgets.QFrame, "Fission180SketchPatternPanel")
    return w if w is not None and w.isVisible() else None


def widget(name):
    p = panel()
    return p.findChild(QtWidgets.QWidget, name) if p is not None else None


def click_widget(name):
    w = widget(name)
    if not h.check("the pattern panel has %s" % name, w is not None and w.isVisible()):
        return
    h.pointer_to(w, w.rect().center())
    QtTest.QTest.mouseClick(w, QtCore.Qt.LeftButton)
    QtWidgets.QApplication.processEvents()


def tool():
    return st.tool()


def field_value(name):
    """The value a Distance / Angle field of the panel shows."""
    w = widget(name)
    try:
        return float(w.property("rawValue"))
    except Exception:
        return None


def type_field(name, text):
    w = widget(name)
    if h.check("the pattern panel has %s" % name, w is not None):
        si.type_into(w, text)
        QtWidgets.QApplication.processEvents()


def type_count(name, value):
    w = widget(name)
    if h.check("the pattern panel has %s" % name, w is not None):
        w.setFocus()
        QtTest.QTest.mouseClick(w, QtCore.Qt.LeftButton)
        QtTest.QTest.keyClick(w, QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
        QtTest.QTest.keyClicks(w, str(value))
        QtTest.QTest.keyClick(w, QtCore.Qt.Key_Return)
        QtWidgets.QApplication.processEvents()


def choose(name, text):
    from Fission180Tests.gui import blend_steps as b

    w = widget(name)
    if h.check("the pattern panel has %s" % name, w is not None):
        b.choose(w, text)


def drag_path(points):
    """Press on the first sketch point, move through the others with the button held,
    release on the last (real mouse events on the 3D view)."""
    widget_ = h.gl_widget()
    pixels = [h.screen_point(st.g(p)) for p in points]
    st.hover(points[0], towards=V(0.0, 0.0, 0))
    QtTest.QTest.mousePress(widget_, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, pixels[0])
    QtWidgets.QApplication.processEvents()
    for pixel in pixels[1:]:
        pos = QtCore.QPointF(pixel)
        event = QtGui.QMouseEvent(
            QtCore.QEvent.MouseMove,
            pos,
            QtCore.QPointF(widget_.mapToGlobal(pixel)),
            QtCore.Qt.NoButton,
            QtCore.Qt.LeftButton,
            QtCore.Qt.NoModifier,
        )
        QtWidgets.QApplication.sendEvent(widget_, event)
        QtWidgets.QApplication.processEvents()
    QtTest.QTest.mouseRelease(widget_, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, pixels[-1])
    QtWidgets.QApplication.processEvents()


def p2(v):
    return V(v[0], v[1], 0)


def nodes():
    return h.view().getSceneGraph().getNumChildren()


def dx_of(t):
    """The X offsets of the copies the tool shows (its moves)."""
    return sorted(round(m[1][0], 6) for m in t.moves_now)


def lines_set(sk, first=0):
    out = []
    for g in sk.Geometry[first:]:
        if g.TypeId == "Part::GeomLineSegment":
            out.append(((g.StartPoint.x, g.StartPoint.y), (g.EndPoint.x, g.EndPoint.y)))
    return out


def has_line(found, a, b, tol=1e-9):
    for p, q in found:
        if (math.dist(p, a) < tol and math.dist(q, b) < tol) or (
            math.dist(p, b) < tol and math.dist(q, a) < tol
        ):
            return True
    return False


RECT = [((0, 0), (6, 0)), ((6, 0), (6, 4)), ((6, 4), (0, 4)), ((0, 4), (0, 0))]


# -- setup ----------------------------------------------------------------------------------------
def new_design():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("SketchPatternTools")
    h.fit()
    Gui.getMainWindow().activateWindow()


def create_sketch():
    h.ribbon("Create Sketch")


def pick_xy():
    pl.click_square("XY_Plane")


def opened():
    import Part
    import Sketcher

    sk = s["sk"] = st.s["sk"] = h.in_sketch()
    if not h.check("sketch open on XY", sk is not None):
        return
    doc = App.ActiveDocument
    doc.openTransaction("Setup")
    h.draw_rectangle(sk, 0, 0, 6, 4)
    sk.addGeometry(Part.Circle(V(15, 0, 0), V(0, 0, 1), 2), False)
    sk.addConstraint(Sketcher.Constraint("Radius", 4, 2.0))
    sk.addGeometry(Part.Circle(V(-20, 12, 0), V(0, 0, 1), 1), False)
    doc.commitTransaction()
    doc.recompute()
    h.check("6 curves drawn", len(sk.Geometry) == 6, len(sk.Geometry))
    view = h.view()
    view.viewTop()
    view.fitAll()


def framed():
    h.view_still()
    s["nodes"] = nodes()


# -- A: the panel, box selection ------------------------------------------------------------------
def a_start():
    s["count"] = len(s["sk"].Geometry)
    si.menu_item("CREATE", "Rectangular Pattern")


def a_panel():
    h.wait_for(lambda: panel() is not None, "the pattern panel")
    t = tool()
    h.check("A: Rectangular Pattern runs", st.tool_title() == "Rectangular Pattern", st.tool_title())
    h.check("A: Objects is the active selection", t is not None and t.field == "objects")
    h.check("A: OK greyed before anything is picked", not widget("Fission180PatternOK").isEnabled())
    h.check("A: directions start as the sketch's X and Y",
            widget("Fission180PatternDirection1").text() == "X Axis"
            and widget("Fission180PatternDirection2").text() == "Y Axis")
    from fission180 import sketch_cursor

    h.check("A: Fission 180's own pointer (with the tool's picture)",
            sketch_cursor.is_own(h.gl_widget().cursor()) or sketch_cursor.is_own(st.session().viewer.cursor()))
    h.shot("A-panel")


def a_crossing():
    sel.box_at(V(6, 2, 0), half=8, crossing=True)


def a_crossing_took():
    t = tool()
    h.check("A: a small box from right to left takes only the line it touches",
            t is not None and t.objects == [1], t and t.objects)


def a_window():
    sel.box_around([V(0, 0, 0), V(6, 4, 0)], margin=14)


def a_window_took():
    t = tool()
    h.check("A: a box from left to right takes the rectangle's 4 lines (not the circles)",
            t is not None and sorted(t.objects) == [0, 1, 2, 3], t and t.objects)
    h.check("A: the panel says 4 selected", widget("Fission180PatternObjects").text() == "4 selected")
    h.check("A: OK can be pressed", widget("Fission180PatternOK").isEnabled())
    h.check("A: the copies show (2 copies of 4 lines)", len(t.copies()) == 8, len(t.copies()))
    h.check("A: an arrow for each direction", sorted(t.looks) == ["distance", "distance2"], sorted(t.looks))
    h.check("A: the sketch is unchanged while previewing", len(s["sk"].Geometry) == s["count"])
    h.shot("A-preview")


# -- B: typed values, the arrow dragged --------------------------------------------------------
def b_quantity():
    type_count("Fission180PatternQuantity", 4)


def b_distance():
    type_field("Fission180PatternDistance", "30")


def b_typed():
    t = tool()
    h.check("B: Quantity 4, Distance 30", t.values["quantity"] == 4 and abs(t.values["distance"] - 30) < 1e-9,
            t.values)
    look = t.looks.get("distance")
    h.check("B: the arrow stands at the typed 30 (base at x = 3)",
            look is not None and abs(look.anchor[0] - 33.0) < 1e-9 and abs(look.anchor[1] - 2.0) < 1e-9,
            look and look.anchor)
    xs = dx_of(t)
    h.check("B: copies at x = 10, 20, 30 (Extent 30, 4 of them)", xs == [10.0, 20.0, 30.0], xs)
    h.check("B: 3 copies of 4 lines shown", len(t.copies()) == 12, len(t.copies()))


def b_drag():
    look = tool().looks.get("distance")
    if not h.check("B: the Direction 1 arrow is there", look is not None):
        return
    head = look.head()
    s["drag_from"] = head
    drag_path([p2(head), p2((head[0] + 2, head[1])), p2((head[0] + 4, head[1])), p2((head[0] + 6, head[1]))])


def b_dragged():
    t = tool()
    value = t.values["distance"]
    shown = field_value("Fission180PatternDistance")
    h.check("B: dragging the arrow 6 mm on makes the Distance about 36", 34.5 < value < 37.5, value)
    h.check("B: the panel shows the dragged Distance", shown is not None and abs(shown - value) < 1e-6,
            (shown, value))
    look = t.looks.get("distance")
    h.check("B: the arrow followed", look is not None and abs(look.anchor[0] - 3.0 - value) < 1e-6,
            look and look.anchor)
    xs = dx_of(t)
    want = [round(value / 3.0 * i, 6) for i in (1, 2, 3)]
    h.check("B: the copies followed", xs == want, (xs, want))
    h.check("B: the arrow is not hot after the release", not look.hot)
    h.shot("B-dragged")


# -- C: Spacing, direction 2 -----------------------------------------------------------------------
def c_spacing():
    choose("Fission180PatternDistanceType", "Spacing")


def c_spacing_8():
    type_field("Fission180PatternDistance", "8")


def c_typed():
    t = tool()
    h.check("C: Distance Type Spacing", t.values["distribution"] == "spacing", t.values)
    look = t.looks.get("distance")
    h.check("C: the typed Distance moved the arrow to 8 (the first copy)",
            look is not None and abs(look.anchor[0] - 11.0) < 1e-9, look and look.anchor)
    xs = dx_of(t)
    h.check("C: copies 8 apart", xs == [8.0, 16.0, 24.0], xs)


def c_quantity2():
    type_count("Fission180PatternQuantity2", 2)


def c_drag2():
    look = tool().looks.get("distance2")
    if not h.check("C: the Direction 2 arrow is there", look is not None):
        return
    head = look.head()
    drag_path([p2(head), p2((head[0], head[1] + 3)), p2((head[0], head[1] + 5))])


def c_dragged2():
    t = tool()
    value = t.values["distance2"]
    before = s.get("d2_before", 0.0)
    h.check("C: dragging the Direction 2 arrow 5 mm on adds about 5 to its Distance",
            3.5 < value - before < 6.5, (before, value))
    shown = field_value("Fission180PatternDistance2")
    h.check("C: the panel shows the dragged Distance (Y)", shown is not None and abs(shown - value) < 1e-6,
            (shown, value))
    h.check("C: 7 copies (4 x 2)", len(t.moves_now) == 7, len(t.moves_now))
    h.shot("C-two-directions")


def c_type12():
    type_field("Fission180PatternDistance2", "12")


def c_typed12():
    t = tool()
    look = t.looks.get("distance2")
    h.check("C: 12 typed moves the arrow of direction 2 (base at y = 2)",
            look is not None and abs(look.anchor[1] - 14.0) < 1e-9 and abs(look.anchor[0] - 3.0) < 1e-9,
            look and look.anchor)


def c_before_drag2():
    s["d2_before"] = tool().values["distance2"]


# -- D: OK -------------------------------------------------------------------------------------------
def d_ok():
    s["undo"] = len(App.ActiveDocument.UndoNames)
    s["sk"].solve()
    s["dof"] = s["sk"].DoF
    click_widget("Fission180PatternOK")


def d_made():
    h.settle("the pattern")
    sk = s["sk"]
    h.check("D: 28 new lines (7 copies of 4)", len(sk.Geometry) == s["count"] + 28,
            (len(sk.Geometry), s["count"]))
    found = lines_set(sk, s["count"])
    missing = []
    for i in range(4):
        for j in range(2):
            if i == 0 and j == 0:
                continue
            for a, b in RECT:
                a2, b2 = (a[0] + 8 * i, a[1] + 12 * j), (b[0] + 8 * i, b[1] + 12 * j)
                if not has_line(found, a2, b2):
                    missing.append((a2, b2))
    h.check("D: every copy exactly 8 / 12 apart", not missing, missing[:4])
    kinds = si.constraint_types(sk)
    h.check("D: the copies' corners are joined (Coincident copied)", kinds.count("Coincident") >= 4 * 8, kinds.count("Coincident"))
    # (wave 7: the copies are TIED to the original point by point, sketch_pattern_ties.py;
    # they no longer carry Horizontal / Vertical of their own, they follow the original's)
    made = sk.Geometry[s["count"]:]
    level = [g for g in made if abs(g.StartPoint.y - g.EndPoint.y) < 1e-9]
    upright = [g for g in made if abs(g.StartPoint.x - g.EndPoint.x) < 1e-9]
    h.check("D: level and upright as the original", len(level) == 14 and len(upright) == 14,
            (len(level), len(upright)))
    before = sk.DoF
    h.check("D: the copies add no freedom (tied to the original)", sk.solve() == 0 and sk.DoF == s["dof"],
            (sk.DoF, s.get("dof"), before))
    h.check("D: the sketch solves", sk.solve() == 0)
    h.check("D: no conflicting or redundant constraints",
            not list(sk.ConflictingConstraints) and not list(sk.RedundantConstraints),
            (list(sk.ConflictingConstraints), list(sk.RedundantConstraints)))
    names = list(App.ActiveDocument.UndoNames)
    h.check("D: one undo step Rectangular Pattern", names and names[0] == "Rectangular Pattern", names[:3])
    h.check("D: the panel is gone and the tool ended", panel() is None and st.tool_title() is None, st.tool_title())
    h.check("D: nothing left in the 3D view (no arrows, no preview)", nodes() == s["nodes"], (nodes(), s["nodes"]))
    s["made"] = len(sk.Geometry)
    h.shot("D-made")


def d_undo():
    st.undo()


def d_undone():
    h.settle("the undo")
    h.check("D: one Ctrl+Z takes the whole pattern back", len(s["sk"].Geometry) == s["count"],
            (len(s["sk"].Geometry), s["count"]))


def d_redo():
    st.redo()


def d_redone():
    h.settle("the redo")
    h.check("D: Ctrl+Y brings it back", len(s["sk"].Geometry) == s["made"])
    st.undo()


def d_back():
    h.settle("the undo")
    h.check("D: undone again for the next part", len(s["sk"].Geometry) == s["count"])


# -- E: click pick, Cancel ----------------------------------------------------------------------------
def e_start():
    si.menu_item("CREATE", "Rectangular Pattern")


def e_pick():
    h.wait_for(lambda: panel() is not None, "the pattern panel")
    st.click(V(-19, 12, 0), towards=V(1.0, 0.4, 0))


def e_picked():
    t = tool()
    h.check("E: a click on the small circle picks it", t is not None and t.objects == [5], t and t.objects)
    h.check("E: its copies show", t is not None and len(t.copies()) == 2)
    click_widget("Fission180PatternCancel")


def e_cancelled():
    h.settle("Cancel")
    h.check("E: Cancel makes nothing", len(s["sk"].Geometry) == s["count"])
    h.check("E: the panel went and the tool ended", panel() is None and st.tool_title() is None)
    h.check("E: nothing left in the 3D view", nodes() == s["nodes"], (nodes(), s["nodes"]))


# -- F: Circular Pattern ---------------------------------------------------------------------------
def f_start():
    si.menu_item("CREATE", "Circular Pattern")


def f_pick():
    h.wait_for(lambda: panel() is not None, "the pattern panel")
    st.click(V(17, 0, 0), towards=V(0.4, 1.0, 0))


def f_picked():
    t = tool()
    h.check("F: Circular Pattern runs", st.tool_title() == "Circular Pattern", st.tool_title())
    h.check("F: the circle is the Objects", t is not None and t.objects == [4], t and t.objects)
    h.check("F: OK greyed (no centre yet)", not widget("Fission180PatternOK").isEnabled())
    msg = widget("Fission180PatternMessage")
    h.check("F: the panel says Center Point is next", msg is not None and "Center Point" in msg.text(),
            msg and msg.text())
    h.check("F: Total Angle hidden for Full", not widget("Fission180PatternAngle").isVisible())


def f_center_field():
    click_widget("Fission180PatternCenter")


def f_center_click():
    h.wait_for(lambda: tool() is not None and tool().field == "center", "Center Point to be active")
    st.click(V(0, 0, 0), towards=V(-0.6, -1.0, 0))


def f_full():
    t = tool()
    h.check("F: the origin is the centre", t is not None and t.center_point() is not None
            and math.hypot(*t.center_point()) < 1e-9, t and t.center_point())
    h.check("F: Full, 3: copies at 120 and 240", len(t.moves_now) == 2 and sorted(m[2] for m in t.moves_now) == [120.0, 240.0],
            t.moves_now)
    look = t.looks.get("angle")
    h.check("F: the disc stands at 360, on the circle", look is not None and math.dist(look.point, (15, 0)) < 1e-6,
            look and look.point)
    h.shot("F-full")


def _arc(start, end, step=5.0):
    count = max(1, int(abs(end - start) / step))
    return [p2((15 * math.cos(math.radians(start + (end - start) * i / count)),
                15 * math.sin(math.radians(start + (end - start) * i / count))))
            for i in range(count + 1)]


def f_drag_180():
    drag_path(_arc(360.0, 180.0))


def f_at_180():
    t = tool()
    h.check("F: the drag made it an Angle pattern", t.values["circular_type"] == "angle", t.values)
    h.check("F: Total Angle 180 (snapped)", abs(t.values["angle"] - 180.0) < 1e-9, t.values["angle"])
    h.check("F: the panel shows Angle and 180",
            widget("Fission180PatternType").currentText() == "Angle"
            and widget("Fission180PatternAngle").isVisible()
            and abs(field_value("Fission180PatternAngle") - 180.0) < 1e-9,
            (widget("Fission180PatternType").currentText(), field_value("Fission180PatternAngle")))
    h.check("F: copies at 90 and 180", sorted(m[2] for m in t.moves_now) == [90.0, 180.0], t.moves_now)
    h.shot("F-180")


def f_drag_90():
    drag_path(_arc(180.0, 90.0))


def f_at_90():
    t = tool()
    h.check("F: dragged on to 90", abs(t.values["angle"] - 90.0) < 1e-9, t.values["angle"])
    h.check("F: the panel shows 90", abs(field_value("Fission180PatternAngle") - 90.0) < 1e-9)
    look = t.looks.get("angle")
    h.check("F: the disc at 90", look is not None and math.dist(look.point, (0, 15)) < 1e-6, look and look.point)


def f_type_270():
    type_field("Fission180PatternAngle", "270")


def f_typed_270():
    look = tool().looks.get("angle")
    h.check("F: 270 typed moves the disc", look is not None and math.dist(look.point, (0, -15)) < 1e-6,
            look and look.point)


def f_quantity4():
    type_count("Fission180PatternQuantity", 4)


def f_four():
    t = tool()
    h.check("F: copies at 90, 180, 270", sorted(m[2] for m in t.moves_now) == [90.0, 180.0, 270.0], t.moves_now)
    h.shot("F-270")


def f_ok():
    click_widget("Fission180PatternOK")


def f_made():
    h.settle("the pattern")
    sk = s["sk"]
    # (wave 7: the copies are tied to the original through hidden helper lines from the
    # centre, sketch_pattern_ties.py: counted apart from the curves a person sees)
    from fission180 import sketch_helpers

    unseen = sketch_helpers.hidden(sk)
    new = [g for i, g in enumerate(sk.Geometry) if i >= s["count"] and i not in unseen]
    h.check("F: 3 new circles", len(new) == 3 and all(g.TypeId == "Part::GeomCircle" for g in new), len(new))
    h.check("F: the helper lines that tie them are hidden", len(unseen) == 4, len(unseen))
    centres = [(g.Center.x, g.Center.y) for g in new]
    for want in ((0, 15), (-15, 0), (0, -15)):
        h.check("F: a copy exactly at %s" % (want,), any(math.dist(c, want) < 1e-9 for c in centres), centres)
    radii = [g.Radius for g in new]
    h.check("F: the copies have the original's radius", all(abs(r - 2.0) < 1e-9 for r in radii), radii)
    ties = [c for c in sk.Constraints if c.Type == "Equal" and 4 in (c.First, c.Second)]
    h.check("F: each copy is Equal to the original (its Radius holds them)", len(ties) == 3, len(ties))
    h.check("F: the sketch solves cleanly", sk.solve() == 0 and not list(sk.RedundantConstraints))
    names = list(App.ActiveDocument.UndoNames)
    h.check("F: one undo step Circular Pattern", names and names[0] == "Circular Pattern", names[:3])
    h.check("F: nothing left in the 3D view", nodes() == s["nodes"], (nodes(), s["nodes"]))
    h.shot("F-made")


def f_undo():
    st.undo()


def f_undone():
    h.settle("the undo")
    h.check("F: one Ctrl+Z takes it back", len(s["sk"].Geometry) == s["count"])


# -- G: selected first, Esc ------------------------------------------------------------------------------
def g_select():
    si.click(V(17, 0, 0), V(0.4, 1.0, 0))


def g_start():
    h.check("G: the circle is selected", bool(Gui.Selection.getSelectionEx()))
    si.menu_item("CREATE", "Circular Pattern")


def g_ready():
    h.wait_for(lambda: panel() is not None, "the pattern panel")
    t = tool()
    h.check("G: the selected circle is the Objects", t is not None and t.objects == [4], t and t.objects)
    h.check("G: Center Point is the active selection", t is not None and t.field == "center", t and t.field)


def g_esc():
    st.esc()


def g_nothing():
    h.settle("Esc")
    h.check("G: Esc made nothing", len(s["sk"].Geometry) == s["count"])
    h.check("G: the panel went", panel() is None and st.tool_title() is None)
    h.check("G: nothing left in the 3D view", nodes() == s["nodes"], (nodes(), s["nodes"]))


def finish():
    h.ribbon("Finish Sketch")


def end():
    h.check("the sketch is closed", h.in_sketch() is None)
    h.expect_no_errors("the sketch patterns")


STEPS = [
    new_design, create_sketch, pick_xy, opened, framed,
    a_start, a_panel, a_crossing, a_crossing_took, a_window, a_window_took,
    b_quantity, b_distance, b_typed, b_drag, b_dragged,
    c_spacing, c_spacing_8, c_typed, c_quantity2, c_before_drag2, c_drag2, c_dragged2, c_type12, c_typed12,
    d_ok, d_made, d_undo, d_undone, d_redo, d_redone, d_back,
    e_start, e_pick, e_picked, e_cancelled,
    f_start, f_pick, f_picked, f_center_field, f_center_click, f_full, f_drag_180, f_at_180,
    f_drag_90, f_at_90, f_type_270, f_typed_270, f_quantity4, f_four, f_ok, f_made, f_undo, f_undone,
    g_select, g_start, g_ready, g_esc, g_nothing,
    finish, end,
]

h.run("sketch_pattern_tools", si.watched(STEPS), paced_by="state")
