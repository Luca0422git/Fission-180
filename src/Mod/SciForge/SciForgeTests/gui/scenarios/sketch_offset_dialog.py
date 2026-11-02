# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's sketch Offset with its OFFSET panel (sketch_offset_tool.py), with real clicks,
keys and the panel's own widgets.

A rectangle 50 x 30 ((-80, -15) to (-30, 15), its size and place set), a line
(10, -40)-(60, -40) and a circle r 10 at (30, 25) are put in the sketch first.

A  O opens the OFFSET panel (OK greyed, Chain Selection ticked). Chain Selection off, a
   click on the rectangle's bottom edge picks that one line; the offset follows the
   pointer below it; 4 and Enter: ONE line (-80, -19)-(-30, -19), its 4 mm dimension, one
   undo step "Offset"; the panel goes.
B  Ctrl+Z takes it back in one step.
C  O again: Chain Selection is remembered (off); ticked, one click takes the whole
   rectangle; 3 and Enter outside it: a rectangle 3 mm out, corners sharp (no arcs).
D  The offset keeps its distance: a double-click on its dimension, 5, Enter: every side
   of the offset moves to 5 mm.
E  Picks dropped: a picked chain clicked again goes (OK greyed again); Chain Selection off,
   two lines picked, one clicked again drops just that one; Cancel makes nothing.
F  Direction Symmetric, the circle, 2 and Enter: circles of radius 12 and 8 (both sides).
G  One Side (Direction remembered as Symmetric), Chain Selection ticked again (remembered
   off), the line, a click 4 above it keeps that distance, Flip puts it below; Enter: the
   offset is below the line by the kept distance.
H  Esc while picking makes nothing; the sketch stays open.
I  A line selected before O is the pick, as it is (Chain Selection on does not take its
   rectangle); 4 and Enter: that one line offset.
J  O while Offset runs ends it, nothing made; so does another sketch tool (L).
K  Ctrl+Z undoes only the last offset.
L  An inner offset typed too wide (20 mm in a 30 mm tall rectangle) stops at the largest
   that fits (Luca's rule) and says so.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets

from SciForgeTests.gui import dialog_input as di
from SciForgeTests.gui import harness as h
from SciForgeTests.gui import sketch_input as si
from SciForgeTests.gui import sketch_tools_steps as st
from SciForgeTests.gui import widget_input as wi

V = App.Vector
s = st.s
LINE = "Part::GeomLineSegment"


def tool():
    from sciforge import sketch_offset_tool

    t = st.tool()
    return t if isinstance(t, sketch_offset_tool.SketchOffset) else None


def panel():
    for widget in Gui.getMainWindow().findChildren(QtWidgets.QFrame, "SciForgeOffsetPanel"):
        if widget.isVisible():
            return widget
    return None


def picks():
    t = tool()
    return sorted(t.curves) if t is not None else None


def new_curves(before, construction=False):
    sk = st.sketch()
    return [
        (i, sk.Geometry[i])
        for i in range(before, len(sk.Geometry))
        if bool(sk.getConstruction(i)) == construction
    ]


def box(items):
    xs, ys = [], []
    for _i, g in items:
        b = g.toShape().BoundBox
        xs += [b.XMin, b.XMax]
        ys += [b.YMin, b.YMax]
    return (min(xs), min(ys), max(xs), max(ys))


def box_near(a, b, tol=1e-6):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def offset_dimensions(before_constraints):
    sk = st.sketch()
    return [
        (i, c)
        for i, c in enumerate(sk.Constraints)
        if i >= before_constraints and c.Type == "Distance" and not c.InVirtualSpace
    ]


def mark():
    sk = st.sketch()
    s["geo"] = len(sk.Geometry)
    s["cons"] = len(sk.Constraints)
    s["undo"] = len(App.ActiveDocument.UndoNames)


def click_panel(name, pos=None):
    p = panel()
    widget = p.findChild(QtWidgets.QWidget, name) if p is not None else None
    if widget is None or not widget.isVisible():
        h.check("the OFFSET panel shows %s" % name, False)
        return
    wi.click(widget, pos)


def click_chain():
    p = panel()
    box_ = p.findChild(QtWidgets.QCheckBox, "SciForgeOffsetChain") if p is not None else None
    if box_ is None:
        h.check("the OFFSET panel has Chain Selection", False)
        return
    wi.click(box_, QtCore.QPoint(8, box_.height() // 2))


def reference():
    import Part
    import Sketcher

    sk = st.sketch()
    corners = [V(-80, -15, 0), V(-30, -15, 0), V(-30, 15, 0), V(-80, 15, 0)]
    rect = [sk.addGeometry(Part.LineSegment(corners[i], corners[(i + 1) % 4])) for i in range(4)]
    cs = [Sketcher.Constraint("Coincident", rect[i], 2, rect[(i + 1) % 4], 1) for i in range(4)]
    cs += [
        Sketcher.Constraint("Horizontal", rect[0]),
        Sketcher.Constraint("Horizontal", rect[2]),
        Sketcher.Constraint("Vertical", rect[1]),
        Sketcher.Constraint("Vertical", rect[3]),
    ]
    sk.addConstraint(cs)
    # its size and place, as typed values would give them: a dimension change of the offset
    # then moves the offset (FreeCAD's solver spreads a change over curves that are free).
    # Kept unseen so their labels never sit under a click.
    first = len(sk.Constraints)
    sk.addConstraint(
        [
            Sketcher.Constraint("DistanceX", -1, 1, rect[0], 1, -80.0),
            Sketcher.Constraint("DistanceY", -1, 1, rect[0], 1, -15.0),
            Sketcher.Constraint("DistanceX", -1, 1, rect[2], 1, -30.0),
            Sketcher.Constraint("DistanceY", -1, 1, rect[2], 1, 15.0),
        ]
    )
    sk.setVirtualSpace(list(range(first, len(sk.Constraints))), True)
    s["rect"] = rect  # bottom, right, top, left
    s["line"] = sk.addGeometry(Part.LineSegment(V(10, -40, 0), V(60, -40, 0)))
    s["circle"] = sk.addGeometry(Part.Circle(V(30, 25, 0), V(0, 0, 1), 10))
    App.ActiveDocument.recompute()


# == A: Chain Selection off, one line ======================================================
def a_open():
    mark()
    st.hover(V(-50, 0, 0))
    h.press("o")


def a_chain_off():
    h.check("O runs SciForge's Offset", tool() is not None, st.tool_title())
    p = panel()
    h.check("the OFFSET panel shows", p is not None)
    if p is None:
        return
    ok = p.findChild(QtWidgets.QPushButton, "SciForgeOffsetOK")
    h.check("OK is greyed until curves are picked", ok is not None and not ok.isEnabled())
    chain = p.findChild(QtWidgets.QCheckBox, "SciForgeOffsetChain")
    h.check("Chain Selection starts ticked", chain is not None and chain.isChecked())
    h.check(
        "Curves says Select",
        p.findChild(QtWidgets.QPushButton, "SciForgeOffsetCurves").text() == "Select",
    )
    h.shot("A1-panel")
    click_chain()


def a_pick_bottom():
    from sciforge import sketch_offset_tool

    t = tool()
    h.check("Chain Selection unticked", t is not None and not t.chain)
    h.check("...and remembered", not sketch_offset_tool.chain_selection())
    st.click(V(-70, -15, 0), towards=V(0, 0, 0))


def a_hover():
    h.check("one click picks just that line", picks() == [s["rect"][0]], picks())
    p = panel()
    h.check(
        "the panel counts it",
        p is not None
        and p.findChild(QtWidgets.QPushButton, "SciForgeOffsetCurves").text() == "1 selected"
        and p.findChild(QtWidgets.QPushButton, "SciForgeOffsetOK").isEnabled(),
    )
    st.hover(V(-70, -19, 0), towards=V(0, -1, 0))
    curves = st.preview().get("curves", [])
    ok = len(curves) == 1 and all(abs(pt[1] + 19.0) < 0.6 for pt in curves[0])
    h.check("the offset of that one line follows the pointer below it", ok, curves)
    h.check("the distance box shows by the pointer", bool(st.box_texts()), st.box_texts())
    h.shot("A2-one-line")


def a_type():
    st.keys("4\n")


def a_check():
    h.check("Enter makes it and ends Offset", tool() is None and panel() is None)
    made = [(i, g) for i, g in new_curves(s["geo"]) if g.TypeId == LINE]
    h.check("one line made", len(made) == 1, made)
    if made:
        g = made[0][1]
        ends = sorted([(round(p.x, 6), round(p.y, 6)) for p in (g.StartPoint, g.EndPoint)])
        h.check("(-80, -19) to (-30, -19)", ends == [(-80.0, -19.0), (-30.0, -19.0)], ends)
    dims = offset_dimensions(s["cons"])
    h.check(
        "one 4 mm offset dimension shows",
        len(dims) == 1 and st.near(dims[0][1].Value, 4.0) and dims[0][1].Driving,
        [(i, c.Value) for i, c in dims],
    )
    names = App.ActiveDocument.UndoNames
    h.check("an undo step called Offset", names[:1] == ["Offset"], names[:3])
    st.sketch_ok("one line")
    s["a_geo"] = len(st.sketch().Geometry)
    h.shot("A3-one-line-made")


# == B: one Ctrl+Z ===========================================================================
def b_undo():
    st.undo()


def b_check():
    h.check(
        "Ctrl+Z takes the offset back in one step",
        len(st.sketch().Geometry) == s["geo"] and len(st.sketch().Constraints) == s["cons"],
        (len(st.sketch().Geometry), s["geo"]),
    )
    h.check("still in the sketch", h.in_sketch() is st.sketch())


# == C: the whole rectangle ===================================================================
def c_open():
    mark()
    st.hover(V(-50, 0, 0))
    h.press("o")


def c_chain_on():
    t = tool()
    h.check("Offset runs again", t is not None)
    h.check("Chain Selection remembered (off)", t is not None and not t.chain)
    click_chain()


def c_pick():
    t = tool()
    h.check("Chain Selection ticked", t is not None and t.chain)
    st.click(V(-80, 5, 0), towards=V(0, 0, 0))


def c_hover():
    h.check("one click takes the whole rectangle", picks() == sorted(s["rect"]), picks())
    st.hover(V(-84, 5, 0), towards=V(-1, 0, 0))
    curves = st.preview().get("curves", [])
    h.check("the offset of all four sides shows", len(curves) == 4, curves)
    h.shot("C1-rectangle")


def c_type():
    st.keys("3\n")


def c_check():
    made = [(i, g) for i, g in new_curves(s["geo"]) if g.TypeId == LINE]
    h.check("four lines made", len(made) == 4, made)
    s["outer"] = [i for i, _g in made]
    if len(made) == 4:
        h.check(
            "a rectangle exactly 3 mm out",
            box_near(box(made), (-83.0, -18.0, -27.0, 18.0)),
            box(made),
        )
        corners = {}
        for _i, g in made:
            for p in (g.StartPoint, g.EndPoint):
                key = (round(p.x, 6), round(p.y, 6))
                corners[key] = corners.get(key, 0) + 1
        h.check(
            "sharp corners: the sides meet two by two at the corners",
            sorted(corners.items())
            == sorted(
                {(-83.0, -18.0): 2, (-27.0, -18.0): 2, (-27.0, 18.0): 2, (-83.0, 18.0): 2}.items()
            ),
            corners,
        )
    arcs = [g for _i, g in new_curves(s["geo"]) if g.TypeId != LINE]
    h.check("no arcs (corners not rounded)", not arcs, arcs)
    dims = offset_dimensions(s["cons"])
    h.check("one 3 mm dimension", len(dims) == 1 and st.near(dims[0][1].Value, 3.0), dims)
    s["dim"] = dims[0][0] if dims else None
    st.sketch_ok("rectangle")
    h.shot("C2-rectangle-made")


# == D: the dimension moves the offset ========================================================
def d_double_click():
    if s.get("dim") is None:
        h.check("the offset dimension is there", False)
        return
    point = si.dimension_label(st.sketch(), s["dim"])
    h.move(h.screen_point(point + V(2, 1, 0)))
    h.move(h.screen_point(point))
    h.double_click(point)


def d_type():
    from sciforge import sketch_mode

    session = sketch_mode.current()
    h.check("a double-click on it opens the value box", session and session.editor is not None)
    si.type_text("5")


def d_check():
    sk = st.sketch()
    outer = [(i, sk.Geometry[i]) for i in s.get("outer", [])]
    h.check(
        "every side of the offset moved to 5 mm",
        len(outer) == 4 and box_near(box(outer), (-85.0, -20.0, -25.0, 20.0), 1e-6),
        box(outer) if outer else None,
    )
    orig = [(i, sk.Geometry[i]) for i in s["rect"]]
    h.check(
        "the rectangle itself stayed",
        box_near(box(orig), (-80.0, -15.0, -30.0, 15.0), 1e-6),
        box(orig),
    )
    st.sketch_ok("dimension changed")
    h.shot("D-dimension-5")


# == E: dropping picks, Cancel ================================================================
def e_open():
    mark()
    st.hover(V(-50, 0, 0))
    h.press("o")


def e_pick_chain():
    h.check("Chain Selection still on", tool() is not None and tool().chain)
    st.click(V(-70, -15, 0), towards=V(0, 0, 0))


def e_drop_chain():
    h.check("the rectangle picked", picks() == sorted(s["rect"]), picks())
    st.click(V(-70, -15, 0), towards=V(0, 0, 0))


def e_chain_off():
    h.check("a click on the picked chain drops it", picks() == [], picks())
    p = panel()
    h.check(
        "OK greyed again",
        p is not None and not p.findChild(QtWidgets.QPushButton, "SciForgeOffsetOK").isEnabled(),
    )
    click_chain()


def e_pick_two():
    h.check("Chain Selection off", tool() is not None and not tool().chain)
    st.click(V(-70, -15, 0), towards=V(0, 0, 0))
    st.click(V(-70, 15, 0), towards=V(0, 0, 0))


def e_drop_one():
    h.check(
        "two lines picked one by one",
        picks() == sorted([s["rect"][0], s["rect"][2]]),
        picks(),
    )
    st.click(V(-70, 15, 0), towards=V(0, 0, 0))


def e_cancel():
    h.check("a click on a picked line drops just that line", picks() == [s["rect"][0]], picks())
    h.shot("E-one-picked")
    click_panel("SciForgeOffsetCancel")


def e_check():
    h.check("Cancel ends Offset", tool() is None and panel() is None)
    h.check(
        "Cancel makes nothing",
        len(st.sketch().Geometry) == s["geo"] and len(App.ActiveDocument.UndoNames) == s["undo"],
        (len(st.sketch().Geometry), s["geo"]),
    )


# == F: Symmetric ===============================================================================
def f_open():
    mark()
    st.hover(V(0, 0, 0))
    h.press("o")


def f_symmetric():
    p = panel()
    combo = p.findChild(QtWidgets.QComboBox, "SciForgeOffsetDirection") if p else None
    h.check("Direction drop-down", combo is not None and combo.currentText() == "One Side")
    if combo is not None:
        di.choose(combo, "Symmetric")


def f_pick_circle():
    from sciforge import sketch_offset_tool

    h.check(
        "Direction Symmetric",
        sketch_offset_tool.SketchOffset.direction == "Symmetric",
        sketch_offset_tool.SketchOffset.direction,
    )
    p = panel()
    h.check(
        "Flip is greyed for Symmetric",
        p is not None and not p.findChild(QtWidgets.QToolButton, "SciForgeOffsetFlip").isEnabled(),
    )
    st.click(V(37.0711, 32.0711, 0), towards=V(0, 0, 0))  # on the circle, 45 degrees up


def f_hover():
    h.check("the circle picked", picks() == [s["circle"]], picks())
    st.hover(V(39.1924, 34.1924, 0), towards=V(1, 1, 0))  # 3 outside
    curves = st.preview().get("curves", [])
    h.check("both sides show", len(curves) == 2, len(curves))
    h.shot("F-symmetric")


def f_type():
    st.keys("2\n")


def f_check():
    made = [g for _i, g in new_curves(s["geo"]) if g.TypeId == "Part::GeomCircle"]
    radii = sorted(round(g.Radius, 6) for g in made)
    h.check("circles of radius 8 and 12", radii == [8.0, 12.0], radii)
    h.check(
        "around the same centre",
        all(st.vnear(g.Center, V(30, 25, 0)) for g in made),
        [g.Center for g in made],
    )
    dims = offset_dimensions(s["cons"])
    h.check("one 2 mm dimension for both", len(dims) == 1 and st.near(dims[0][1].Value, 2.0), dims)
    st.sketch_ok("symmetric")


# == G: Flip ====================================================================================
def g_open():
    mark()
    st.hover(V(0, -20, 0))
    h.press("o")


def g_one_side():
    p = panel()
    combo = p.findChild(QtWidgets.QComboBox, "SciForgeOffsetDirection") if p else None
    h.check(
        "Direction remembered (Symmetric)",
        combo is not None and combo.currentText() == "Symmetric",
        combo and combo.currentText(),
    )
    if combo is not None:
        di.choose(combo, "One Side")


def g_chain_on():
    t = tool()
    h.check("Chain Selection remembered (off since E)", t is not None and not t.chain)
    click_chain()


def g_pick_line():
    t = tool()
    h.check("Chain Selection ticked again", t is not None and t.chain)
    st.click(V(20, -40, 0), towards=V(0, 0, 0))


def g_keep():
    h.check("the line picked", picks() == [s["line"]], picks())
    st.click(V(20, -36, 0), towards=V(0, 0, 0))  # off the line: keeps the distance


def g_flip():
    f = st.field("distance")
    t = tool()
    kept = f.typed if f is not None else None
    s["kept"] = kept
    h.check("the click kept about 4 mm", kept is not None and abs(kept - 4.0) < 0.3, kept)
    h.check("above the line", t is not None and t.side == -1, t and t.side)
    click_panel("SciForgeOffsetFlip")


def g_after_flip():
    t = tool()
    h.check("Flip: the other side", t is not None and t.side == 1, t and t.side)
    curves = st.preview().get("curves", [])
    below = len(curves) == 1 and all(pt[1] < -40.0 for pt in curves[0])
    h.check("the preview is below the line now", below, curves)
    h.shot("G-flipped")
    st.enter()


def g_check():
    made = [g for _i, g in new_curves(s["geo"]) if g.TypeId == LINE]
    h.check("one line made", len(made) == 1, made)
    if made and s.get("kept"):
        g = made[0]
        h.check(
            "below the line by the kept distance",
            st.near(g.StartPoint.y, -40.0 - s["kept"], 1e-6)
            and st.near(g.EndPoint.y, -40.0 - s["kept"], 1e-6),
            (g.StartPoint, g.EndPoint, s["kept"]),
        )
    st.sketch_ok("flip")


# == H: Esc =======================================================================================
def h_open():
    mark()
    st.hover(V(0, -20, 0))
    h.press("o")


def h_pick():
    st.click(V(50, -40, 0), towards=V(0, 0, 0))
    st.hover(V(50, -35, 0), towards=V(0, 1, 0))


def h_esc():
    h.check("picked", picks() == [s["line"]], picks())
    st.esc()


def h_check():
    h.check("Esc ends Offset", tool() is None and panel() is None)
    h.check("Esc makes nothing", len(st.sketch().Geometry) == s["geo"])
    h.check("the sketch stays open", h.in_sketch() is st.sketch())


# == I: a selection made first ==================================================================
def i_select():
    mark()
    st.click(V(-30, 5, 0), towards=V(0, 0, 0))  # the rectangle's right side, no tool running


def i_open():
    sel = [n for x in Gui.Selection.getSelectionEx() for n in x.SubElementNames]
    h.check(
        "the right side is selected",
        any(n.endswith("Edge%d" % (s["rect"][1] + 1)) for n in sel),
        sel,
    )
    h.press("o")


def i_hover():
    from sciforge import sketch_tools_ui

    t = tool()
    h.check("Offset runs with Chain Selection on", t is not None and t.chain)
    h.check(
        "the selected line is the pick, as it is",
        picks() == [s["rect"][1]] and sketch_tools_ui.last_offset() == [s["rect"][1]],
        picks(),
    )
    st.hover(V(-26, 5, 0), towards=V(1, 0, 0))


def i_type():
    st.keys("4\n")


def i_check():
    made = [g for _i, g in new_curves(s["geo"]) if g.TypeId == LINE]
    h.check("one line made", len(made) == 1, made)
    if made:
        g = made[0]
        ends = sorted([(round(p.x, 6), round(p.y, 6)) for p in (g.StartPoint, g.EndPoint)])
        h.check("(-26, -15) to (-26, 15)", ends == [(-26.0, -15.0), (-26.0, 15.0)], ends)
    s["i_geo"] = s["geo"]


# == J: O again ===================================================================================
def j_open():
    mark()
    st.hover(V(0, -20, 0))
    h.press("o")


def j_again():
    h.check("Offset runs", tool() is not None)
    h.press("o")


def j_check():
    h.check("O again ends it", tool() is None and panel() is None, st.tool_title())
    h.check("nothing made", len(st.sketch().Geometry) == s["geo"])
    h.press("o")


def j_other_tool():
    h.check("Offset runs once more", tool() is not None)
    h.press("l")


def j_other_check():
    h.check("another sketch tool (L) ends Offset", tool() is None and panel() is None)
    h.check("...and runs", si.drawing())
    h.check("nothing made", len(st.sketch().Geometry) == s["geo"])
    st.esc()


# == K: one Ctrl+Z for the last offset ==========================================================
def k_undo():
    st.undo()


def k_check():
    sk = st.sketch()
    h.check(
        "Ctrl+Z takes back only the last offset",
        len(sk.Geometry) == s["i_geo"],
        (len(sk.Geometry), s["i_geo"]),
    )
    outer = [(i, sk.Geometry[i]) for i in s.get("outer", [])]
    h.check(
        "the rectangle offset before it stays",
        len(outer) == 4 and box_near(box(outer), (-85.0, -20.0, -25.0, 20.0)),
    )


# == L: too wide inside =========================================================================
def l_open():
    mark()
    st.hover(V(-50, 0, 0))
    h.press("o")


def l_pick():
    st.click(V(-80, 5, 0), towards=V(0, 0, 0))
    st.hover(V(-70, 5, 0), towards=V(1, 0, 0))  # inside


def l_type():
    h.check("the rectangle picked", picks() == sorted(s["rect"]), picks())
    st.keys("20\n")


def l_check():
    made = [(i, g) for i, g in new_curves(s["geo"]) if g.TypeId == LINE]
    h.check("four lines made", len(made) == 4, made)
    if len(made) == 4:
        h.check(
            "held at the largest that fits: 14.99 mm in",
            box_near(box(made), (-65.01, -0.01, -44.99, 0.01), 1e-6),
            box(made),
        )
    dims = offset_dimensions(s["cons"])
    h.check("its dimension says 14.99", len(dims) == 1 and st.near(dims[0][1].Value, 14.99), dims)
    from sciforge import sketch_offset_tool

    note = sketch_offset_tool._last.get("note", "")
    h.check("the note says so", "20 mm does not fit: limited to 14.99 mm" in note, note)
    st.sketch_ok("held inner offset")
    h.check("no pop-up", not h.popups(), h.popups())
    h.shot("L-held")


def finish():
    h.ribbon("Finish Sketch")


def finished():
    h.check("the sketch closes", h.in_sketch() is None)


h.run(
    "sketch_offset_dialog",
    si.watched(
        st.start_steps("SketchOffsetDialog")
        + [
            reference,
            a_open,
            a_chain_off,
            a_pick_bottom,
            a_hover,
            a_type,
            a_check,
            b_undo,
            b_check,
            c_open,
            c_chain_on,
            c_pick,
            c_hover,
            c_type,
            c_check,
            d_double_click,
            d_type,
            d_check,
            e_open,
            e_pick_chain,
            e_drop_chain,
            e_chain_off,
            e_pick_two,
            e_drop_one,
            e_cancel,
            e_check,
            f_open,
            f_symmetric,
            f_pick_circle,
            f_hover,
            f_type,
            f_check,
            g_open,
            g_one_side,
            g_chain_on,
            g_pick_line,
            g_keep,
            g_flip,
            g_after_flip,
            g_check,
            h_open,
            h_pick,
            h_esc,
            h_check,
            i_select,
            i_open,
            i_hover,
            i_type,
            i_check,
            j_open,
            j_again,
            j_check,
            j_other_tool,
            j_other_check,
            k_undo,
            k_check,
            l_open,
            l_pick,
            l_type,
            l_check,
            finish,
            finished,
        ]
    ),
    paced_by="state",
)
