# SPDX-License-Identifier: LGPL-2.1-or-later
"""Wave 7, sketch-c: what Sketch Dimension still lacked.

- Right-click while a dimension follows the pointer: Aligned / Horizontal / Vertical
  (Autodesk blog "Mastering Sketch Dimensions: 5 Essential Right-Click Tricks"; sketch-b:
  "not built").
- A second click on the same spot as the first pick takes the next thing under the pointer
  (sketch-b: "not exercised").
- A dimension that was given a name (`Width = 12`) IS that parameter: a number typed into
  it later sets Width (params' known issue: "typing a new number unlinks it").

A sketch on the XY plane: a slanted line A, an arc that starts at the origin, two level
lines B and C.

  A  D, the two ends of A clicked; the pointer beside the line (the aligned length follows);
     right-click > Horizontal: the horizontal distance follows, also beside the line; a click
     places a DistanceX; D, line A clicked, right-click > Vertical, placed: a DistanceY;
     right-click > Aligned with the pointer past the line's ends: a Distance
  B  right-click with nothing to turn (a circle... an arc picked): the list has no
     Aligned / Horizontal / Vertical
  C  D, a click on the origin, a second click on the same spot: the arc that starts there
     is the second pick (not the arc's end at the same place); placed: the distance from
     the origin to the arc's centre
  D  D on line B, placed, `Width = 12` typed: the parameter Width is made, B is 12 long.
     The dimension double-clicked: the box shows Width and says what a number will do;
     40 typed: Width IS 40 now (the dimension still follows it), B is 40 long.
     Ctrl+Z: Width is 12 again.
  E  D on line C, `Width` typed: C follows Width. That dimension double-clicked, 25 typed:
     C is 25 and no longer follows; Width and B are unchanged (a dimension that only USES
     a parameter is unlinked by a number, as in Fusion)
  F  the named dimension takes a formula too: `Width` dimension double-clicked, `30 + 5`
     typed: Width is 35
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide6 import QtCore, QtTest, QtWidgets

from Fission180Tests.gui import book_sketch_b_steps as b
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st
from Fission180Tests.gui import x_input as x

V = App.Vector
s = st.s


def sk():
    return b.sk()


def px(point):
    return h.screen_point(st.g(point))


def click(point):
    x.click(px(point))
    h.settle()


def editor():
    return st.session().editor if st.session() is not None else None


def length(name):
    return sk().Geometry[s[name]].length()


def formulas():
    from fission180 import sketch_named_dimensions

    return sketch_named_dimensions.formulas(sk())


def width():
    from fission180 import parameters, parameters_core

    held = getattr(parameters.container(App.ActiveDocument), parameters_core.prop_name("Width"))
    return held.Value


def end_tool():
    st.esc()
    st.esc()
    Gui.Selection.clearSelection()


def right_click(point):
    h.click(st.g(point), button=QtCore.Qt.RightButton)


def rows():
    menu = si.marking_menu()
    if menu is None:
        return []
    listing = menu.findChild(QtWidgets.QListWidget, "Fission180MarkingList")
    return [listing.item(i).text().strip() for i in range(listing.count())]


def choose(label):
    h.wait_for(lambda: si.marking_menu() is not None, "the marking menu to open")
    menu = si.marking_menu()
    listing = menu.findChild(QtWidgets.QListWidget, "Fission180MarkingList")
    for i in range(listing.count()):
        if listing.item(i).text().strip() == label:
            rect = listing.visualItemRect(listing.item(i))
            h.pointer_to(listing.viewport(), rect.center())
            QtTest.QTest.mouseClick(
                listing.viewport(), QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, rect.center()
            )
            QtWidgets.QApplication.processEvents()
            return
    h.check("the right-click menu has %s" % label, False, rows())
    menu.close()


def setup():
    import Part

    h.check("the X server takes test input (XTEST)", x.available())
    doc = App.ActiveDocument
    doc.openTransaction("setup")
    s["a"] = b.add(Part.LineSegment(V(-60, 10, 0), V(-30, 26, 0)))
    arc = Part.ArcOfCircle(
        Part.Circle(V(14, 0, 0), V(0, 0, 1), 14), 3.141592653589793 / 2, 3.141592653589793
    )
    s["arc"] = b.add(arc)
    b.con("Coincident", s["arc"], 2, -1, 1)
    s["b"] = b.add(Part.LineSegment(V(-60, -20, 0), V(-30, -20, 0)))
    b.con("Horizontal", s["b"])
    s["c"] = b.add(Part.LineSegment(V(-60, -34, 0), V(-38, -34, 0)))
    b.con("Horizontal", s["c"])
    doc.commitTransaction()
    doc.recompute()
    Gui.Selection.clearSelection()
    h.fit(iso=False)
    b.watch_modals()


def dimension():
    b.mark()
    h.press("d")


# == A ======================================================================================
# beside line A, inside the box its ends span (Fusion's aligned zone, fix-5:
# sketch_dimension_core.linear_kind); it was (-50, 26), on the box's top edge: a pixel decided
BESIDE = V(-48, 21, 0)
PAST = V(-8, 40, 0)  # past its upper end


def a_end_1():
    click(V(-60, 10, 0))


def a_end_2():
    click(V(-30, 26, 0))


def a_hover():
    st.move(BESIDE)
    h.settle()


def a_right_click():
    tool = st.tool()
    spec = tool._spec(tool.cursor)
    h.check("A beside the line the aligned length follows", getattr(spec, "kind", "") == "Distance")
    h.check(
        "A ...and the hint offers the right click", "Right-click" in tool.prompt(), tool.prompt()
    )
    right_click(BESIDE)


def a_horizontal():
    found = rows()
    h.check(
        "A the right-click menu offers Aligned, Horizontal and Vertical",
        found[:3] == ["Aligned", "Horizontal", "Vertical"],
        found[:4],
    )
    choose("Horizontal")


def a_place():
    tool = st.tool()
    h.check(
        "A Sketch Dimension still runs with its two picks",
        tool is not None and len(tool.picks) == 2,
    )
    st.move(BESIDE)
    h.settle()
    spec = tool._spec(tool.cursor)
    h.check(
        "A the horizontal distance follows now, also beside the line",
        getattr(spec, "kind", "") == "DistanceX",
        getattr(spec, "kind", spec),
    )
    click(BESIDE)


def a_placed():
    cons = b.new_cons()
    h.check("A a horizontal dimension was placed", [c[0] for c in cons] == ["DistanceX"], cons)
    h.check("A its value box is open", editor() is not None)
    h.check("A ...showing 30", editor() is not None and editor().edit.text().startswith("30"))
    end_tool()


def a_line():
    click(V(-45, 18, 0))


def a_right_click_2():
    st.move(BESIDE)
    h.settle()
    right_click(BESIDE)


def a_vertical():
    choose("Vertical")


def a_place_2():
    click(BESIDE)


def a_placed_2():
    cons = b.new_cons()
    h.check(
        "A line picked, Vertical chosen: a DistanceY", [c[0] for c in cons] == ["DistanceY"], cons
    )
    h.check(
        "A the choice ends with the dimension", st.tool() is not None and st.tool().forced is None
    )
    end_tool()


def a_right_click_3():
    st.move(PAST)
    h.settle()
    tool = st.tool()
    spec = tool._spec(tool.cursor)
    h.check(
        "A past the line's ends a level or upright distance follows",
        getattr(spec, "kind", "") in ("DistanceX", "DistanceY"),
        getattr(spec, "kind", spec),
    )
    right_click(PAST)


def a_aligned():
    choose("Aligned")


def a_place_past():
    click(PAST)


def a_placed_3():
    cons = b.new_cons()
    h.check(
        "A Aligned chosen past the ends: the line's own length",
        [c[0] for c in cons] == ["Distance"],
        cons,
    )
    end_tool()
    sketch = sk()
    doc = App.ActiveDocument
    doc.openTransaction("tidy")
    for i in reversed(range(len(sketch.Constraints))):
        if sketch.Constraints[i].Type in ("Distance", "DistanceX", "DistanceY"):
            sketch.delConstraint(i)
    doc.commitTransaction()
    doc.recompute()


# == B ======================================================================================
def b_arc():
    g = sk().Geometry[s["arc"]]
    click(g.value((g.FirstParameter + g.LastParameter) / 2))


def b_right_click():
    h.check("B the arc is picked", st.tool() is not None and st.tool().picks == [(s["arc"], 0)])
    right_click(V(30, 30, 0))


def b_menu():
    h.wait_for(lambda: si.marking_menu() is not None, "the marking menu to open")
    found = rows()
    h.check(
        "B a radius cannot be turned: no Aligned / Horizontal / Vertical in the menu",
        "Aligned" not in found and "Horizontal" not in found,
        found[:4],
    )
    si.marking_menu().close()
    end_tool()


# == C ======================================================================================
def c_origin():
    click(V(0, 0, 0))


def c_same_spot():
    tool = st.tool()
    h.check(
        "C a point at the origin is picked", tool is not None and len(tool.picks) == 1, tool.picks
    )
    s["first"] = tool.picks[0]
    click(V(0, 0, 0))


def c_picked():
    tool = st.tool()
    h.check(
        "C the second click on the same spot took the arc (the next thing under the pointer)",
        tool is not None and tool.picks == [s["first"], (s["arc"], 0)],
        tool and tool.picks,
    )
    click(V(8, -12, 0))


def c_placed():
    cons = b.new_cons()
    h.check("C one dimension was placed", len(cons) == 1, cons)
    named = {(cons[0][1], cons[0][2]), (cons[0][3], cons[0][4])} if cons else set()
    h.check("C ...to the arc's centre", (s["arc"], 3) in named, cons)
    end_tool()


# == D ======================================================================================
def d_line():
    click(sk().Geometry[s["b"]].value(15))


def d_place():
    click(V(-45, -14, 0))


def d_name():
    h.check("D the value box is open", editor() is not None)
    si.type_text("Width = 12")


def d_made():
    h.check("D Width = 12 made the parameter", abs(width() - 12) < 1e-9)
    h.check("D line B is 12 long", abs(length("b") - 12) < 1e-6, length("b"))
    s["wdim"] = max(formulas())
    h.check("D the dimension follows Width", formulas().get(s["wdim"]) == "Width", formulas())
    end_tool()


def d_open():
    h.double_click(si.dimension_label(sk(), s["wdim"]))


def d_hint():
    ed = editor()
    h.check("D the box is open on the named dimension", ed is not None and ed.index == s["wdim"])
    if ed is None:
        return
    h.check("D it shows the name", ed.edit.text().strip() == "Width", ed.edit.text())
    hint = ed.hint.text() if ed.hint.isVisible() else ""
    h.check(
        "D ...and says that a number changes Width",
        "Width = 12" in hint and "type a number to change Width" in hint,
        hint,
    )
    s["undo"] = len(b.undo_names())
    si.type_text("40")


def d_set():
    h.check("D the box closed", editor() is None)
    h.check("D 40 typed: Width is 40", abs(width() - 40) < 1e-9, width())
    h.check("D ...line B is 40 long", abs(length("b") - 40) < 1e-6, length("b"))
    h.check(
        "D ...and the dimension still IS Width", formulas().get(s["wdim"]) == "Width", formulas()
    )
    h.check("D one undo step", len(b.undo_names()) == s["undo"] + 1, b.undo_names()[:3])
    st.undo()


def d_undone():
    h.check("D Ctrl+Z: Width is 12 again", abs(width() - 12) < 1e-9, width())
    h.check("D ...and line B", abs(length("b") - 12) < 1e-6, length("b"))
    st.redo()


# == E ======================================================================================
def e_line():
    h.check("E Ctrl+Y: Width is 40", abs(width() - 40) < 1e-9, width())
    click(sk().Geometry[s["c"]].value(8))


def e_place():
    click(V(-50, -42, 0))


def e_name():
    si.type_text("Width")


def e_follows():
    h.check("E line C follows Width (40)", abs(length("c") - 40) < 1e-6, length("c"))
    s["cdim"] = max(formulas())
    end_tool()


def e_open():
    h.double_click(si.dimension_label(sk(), s["cdim"]))


def e_number():
    ed = editor()
    h.check("E the box is open on the second dimension", ed is not None and ed.index == s["cdim"])
    h.check(
        'E it has no "this dimension is Width" hint', ed is not None and not ed.hint.isVisible()
    )
    si.type_text("25")


def e_unlinked():
    h.check("E 25 typed: line C is 25", abs(length("c") - 25) < 1e-6, length("c"))
    h.check("E ...it no longer follows Width", s["cdim"] not in formulas(), formulas())
    h.check("E Width is still 40", abs(width() - 40) < 1e-9, width())
    h.check("E ...and line B", abs(length("b") - 40) < 1e-6, length("b"))


# == F ======================================================================================
def f_open():
    h.double_click(si.dimension_label(sk(), s["wdim"]))


def f_formula():
    h.check("F the box is open on the named dimension", editor() is not None)
    si.type_text("30 + 5")


def f_check():
    h.check("F a formula typed into the named dimension: Width is 35", abs(width() - 35) < 1e-9)
    h.check("F ...line B is 35 long", abs(length("b") - 35) < 1e-6, length("b"))
    b.no_modal("the dimension tool")
    st.sketch_ok("at the end")


h.run(
    "book_sketch_c_dimension",
    st.start_steps("BookSketchCDimension")
    + [
        setup,
        dimension,
        a_end_1,
        a_end_2,
        a_hover,
        a_right_click,
        a_horizontal,
        a_place,
        a_placed,
        dimension,
        a_line,
        a_right_click_2,
        a_vertical,
        a_place_2,
        a_placed_2,
        dimension,
        a_line,
        a_right_click_3,
        a_aligned,
        a_place_past,
        a_placed_3,
        dimension,
        b_arc,
        b_right_click,
        b_menu,
        dimension,
        c_origin,
        c_same_spot,
        c_picked,
        c_placed,
        dimension,
        d_line,
        d_place,
        d_name,
        d_made,
        d_open,
        d_hint,
        d_set,
        d_undone,
        dimension,
        e_line,
        e_place,
        e_name,
        e_follows,
        e_open,
        e_number,
        e_unlinked,
        f_open,
        f_formula,
        f_check,
    ],
    paced_by="state",
)
