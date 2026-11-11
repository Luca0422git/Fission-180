# SPDX-License-Identifier: LGPL-2.1-or-later
"""Wave 7, sketch-c: sketch-a's selection and sketch-b's tools work together (the merge).

sketch-a made a plain click REPLACE the selection outside a tool (Ctrl toggles, Shift adds);
sketch-b's tools act on a selection made before them, or collect plain clicks when started
first. Both were only tested apart (sketch-b's scenarios click through Qt). Here every click
goes through the X server (x_input), the way a mouse does.

A sketch on the XY plane: four slanted lines, three circles, a construction line from the
origin.

  A  selection first: a click on line 1, Ctrl+click on line 2 (both selected), CONSTRAINTS >
     Parallel: they are parallel
  B  tool first: CONSTRAINTS > Perpendicular, a plain click on line 3, a plain click on line
     4 (plain clicks are the tool's picks, nothing is "replaced"): perpendicular
  C  tool first: Equal, the two circles; selection first: Shift+click two lines, Equal
  D  a plain click on line 4 replaces that selection (one line selected); D: the line is the
     dimension's pick; a click places it, 20 typed
  E  selection first: the small circle clicked, CREATE > Circular Pattern (it is the
     Objects), the origin clicked as centre, Quantity 4, OK: three copies tied by hidden
     spokes
  F  a real box drag round everything: FreeCAD's box takes hidden helpers too; none of them,
     nor an end point of one, stays selected (the sketch is edited through its body, where
     FreeCAD names the elements "Sketch.Edge5": sketch-b's own check added them by the
     sketch's name)
  G  a real double-click on the construction line that ends in the pattern's centre: the
     chain is that line alone (sketch-b's gap: it walked into the hidden spokes, which are
     construction lines ending in the same point)
  H  Delete with everything boxed: the pattern's hidden helpers are not deleted behind the
     person's back (the copies and the original go, as selected)
  I  tool first: CREATE > Mirror, two plain clicks collect two lines as Objects (the second
     click does not replace the first)
"""

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import book_sketch_b_steps as b
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st
from Fission180Tests.gui import x_input as x

V = App.Vector
s = st.s
PATTERN = "Fission180SketchPatternPanel"
MIRROR = "Fission180MirrorPanel"


def sk():
    return b.sk()


def px(point):
    return h.screen_point(st.g(point))


def click(point, held=()):
    x.click(px(point), held=held)
    h.settle()


def at(name, f=0.5):
    g = sk().Geometry[s[name]]
    return g.StartPoint + (g.EndPoint - g.StartPoint) * f


def rim(name, direction=V(0.6, 0.8, 0)):
    g = sk().Geometry[s[name]]
    return g.Center + direction * g.Radius


def edges():
    return sorted(n for n in b.selected() if n.startswith("Edge"))


def name(key):
    return "Edge%d" % (s[key] + 1)


def hidden():
    from fission180 import sketch_helpers

    return sketch_helpers.hidden(sk())


def end_tool():
    st.esc()
    st.esc()
    Gui.Selection.clearSelection()


def setup():
    import Part

    h.check("the X server takes test input (XTEST)", x.available())
    doc = App.ActiveDocument
    doc.openTransaction("setup")
    s["l1"] = b.add(Part.LineSegment(V(-70, 34, 0), V(-40, 39, 0)))
    s["l2"] = b.add(Part.LineSegment(V(-70, 22, 0), V(-40, 24, 0)))
    s["l3"] = b.add(Part.LineSegment(V(-30, 20, 0), V(-25, 42, 0)))
    s["l4"] = b.add(Part.LineSegment(V(-15, 26, 0), V(8, 30, 0)))
    s["c1"] = b.add(Part.Circle(V(30, 32, 0), V(0, 0, 1), 6))
    s["c2"] = b.add(Part.Circle(V(55, 32, 0), V(0, 0, 1), 9))
    s["p"] = b.add(Part.Circle(V(28, -24, 0), V(0, 0, 1), 4))
    s["k"] = b.add(Part.LineSegment(V(0, 0, 0), V(-34, -8, 0)), True)
    b.con("Coincident", s["k"], 1, -1, 1)
    doc.commitTransaction()
    doc.recompute()
    Gui.Selection.clearSelection()
    h.fit(iso=False)
    b.watch_modals()


# == A ======================================================================================
def a_click_1():
    click(at("l1"))


def a_ctrl_click_2():
    click(at("l2"), held=("ctrl",))


def a_parallel():
    h.check("A a click, then Ctrl+click: two lines selected", edges() == [name("l1"), name("l2")])
    b.mark()
    b.menu("Parallel")


def a_check():
    h.check("A Parallel acted on the selection", b.has("Parallel", s["l1"], s["l2"]), b.new_cons())
    end_tool()


# == B ======================================================================================
def b_tool():
    b.mark()
    b.menu("Perpendicular")


def b_click_3():
    h.check("B the Perpendicular tool runs", st.tool() is not None, st.tool_title())
    click(at("l3"))


def b_click_4():
    click(at("l4", 0.3))


def b_check():
    h.check(
        "B two plain clicks in the tool: perpendicular",
        b.has("Perpendicular", s["l3"], s["l4"]),
        b.new_cons(),
    )
    end_tool()


# == C ======================================================================================
def c_tool():
    b.mark()
    b.menu("Equal")


def c_click_1():
    click(rim("c1"))


def c_click_2():
    click(rim("c2"))


def c_check():
    h.check("C Equal, tool first, on two circles", b.has("Equal", s["c1"], s["c2"]), b.new_cons())
    end_tool()


def c_shift_1():
    click(at("l1", 0.25), held=("shift",))


def c_shift_2():
    click(at("l3", 0.3), held=("shift",))


def c_equal():
    h.check("C Shift+click twice: two lines selected", edges() == [name("l1"), name("l3")], edges())
    b.mark()
    b.menu("Equal")


def c_equal_check():
    h.check("C Equal acted on the selection", b.has("Equal", s["l1"], s["l3"]), b.new_cons())
    st.esc()


# == D ======================================================================================
def d_select_two():
    click(at("l1", 0.25))
    click(at("l2", 0.3), held=("ctrl",))


def d_click_4():
    h.check("D two lines are selected", len(edges()) == 2, edges())
    click(at("l4", 0.7))


def d_key():
    h.check("D a plain click replaced the selection", edges() == [name("l4")], edges())
    b.mark()
    h.press("d")


def d_place():
    tool = st.tool()
    h.check(
        "D Sketch Dimension took the selected line as its pick",
        tool is not None and list(tool.picks) == [(s["l4"], 0)],
        tool and tool.picks,
    )
    p = at("l4")
    g = sk().Geometry[s["l4"]]
    d = g.EndPoint - g.StartPoint
    normal = V(d.y, -d.x, 0)
    normal.normalize()
    click(p + normal * 12)


def d_type():
    ed = st.session().editor
    h.check("D the dimension is placed and its box is open", ed is not None, b.new_cons())
    si.type_text("20")


def d_check():
    g = sk().Geometry[s["l4"]]
    h.check("D 20 typed: the line is 20 long", abs(g.length() - 20) < 1e-6, g.length())
    end_tool()


# == E ======================================================================================
def e_select():
    click(rim("p"))


def e_pattern():
    h.check("E the small circle is selected", edges() == [name("p")], edges())
    s["geos"] = len(sk().Geometry)
    si.menu_item("CREATE", "Circular Pattern")


def e_centre():
    t = st.tool()
    h.check(
        "E Circular Pattern runs with the circle as Objects", t is not None and len(t.objects) == 1
    )
    x.click(px(V(0, 0, 0)))
    h.settle()


def e_quantity():
    h.check("E the origin is the centre", st.tool().center == (-1, 1), st.tool().center)
    b.panel_type(PATTERN, "Fission180PatternQuantity", "4")


def e_ok():
    b.panel_click(PATTERN, "Fission180PatternOK")


def e_made():
    circles = [
        i
        for i, g in enumerate(sk().Geometry)
        if g.TypeId == "Part::GeomCircle" and abs(g.Radius - 4) < 1e-6
    ]
    s["copies"] = circles
    h.check("E four circles (three copies)", len(circles) == 4, len(circles))
    h.check("E ...tied by hidden helper lines", len(hidden()) >= 3, sorted(hidden()))
    Gui.Selection.clearSelection()


# == F ======================================================================================
def f_box():
    # a window box (left to right) round the whole sketch, started on empty space
    x.press_drag_release(px(V(-82, 50, 0)), px(V(72, -50, 0)))
    h.settle()


def f_check():
    from fission180 import sketch_helpers

    unseen = hidden()
    names = b.selected()
    short = [n.rsplit(".", 1)[-1] for n in names]
    picked = {int(n[4:]) - 1 for n in short if n.startswith("Edge")}
    h.check("F the box selected the curves a person sees", len(picked) >= 11, sorted(picked))
    h.check(
        "F no hidden helper line stays selected", not (picked & unseen), sorted(picked & unseen)
    )
    stray = [n for n in short if sketch_helpers.unseen_element(sk(), n, unseen)]
    h.check("F ...nor an end point of one", not stray, stray)
    s["boxed"] = len(short)


# == G ======================================================================================
def g_clear():
    click(V(-60, -40, 0))  # empty space: nothing selected


def g_double_click():
    h.check("G a click on empty space cleared the selection", not b.selected(), b.selected())
    x.double_click(px(at("k", 0.6)))
    h.settle()


def g_check():
    h.check(
        "G the chain of the construction line is that line alone (no hidden spoke)",
        edges() == [name("k")],
        edges(),
    )
    Gui.Selection.clearSelection()


# == H ======================================================================================
def h_delete():
    s["hidden_before"] = len(hidden())
    h.press("Delete")


def h_check():
    left = [
        i
        for i, g in enumerate(sk().Geometry)
        if g.TypeId in ("Part::GeomCircle", "Part::GeomLineSegment") and i not in hidden()
    ]
    h.check("H Delete removed what was selected", len(left) == 0, len(left))
    b.clean("after Delete")
    st.undo()


def h_undone():
    h.check("H Ctrl+Z brings it all back", len(sk().Geometry) >= s["geos"] + 3, len(sk().Geometry))
    Gui.Selection.clearSelection()


# == I ======================================================================================
def i_mirror():
    si.menu_item("CREATE", "Mirror")


def i_click_1():
    h.check("I Mirror runs with nothing picked", st.tool() is not None and not st.tool().objects)
    click(at("l1", 0.6))


def i_click_2():
    click(at("l2", 0.6))


def i_check():
    t = st.tool()
    h.check(
        "I two plain clicks collected two Objects (the second did not replace the first)",
        t is not None and sorted(t.objects) == sorted([s["l1"], s["l2"]]),
        t and t.objects,
    )
    end_tool()
    b.no_modal("the merged tools")
    st.sketch_ok("at the end")


h.run(
    "book_sketch_c_merge",
    st.start_steps("BookSketchMerge")
    + [
        setup,
        a_click_1,
        a_ctrl_click_2,
        a_parallel,
        a_check,
        b_tool,
        b_click_3,
        b_click_4,
        b_check,
        c_tool,
        c_click_1,
        c_click_2,
        c_check,
        c_shift_1,
        c_shift_2,
        c_equal,
        c_equal_check,
        d_select_two,
        d_click_4,
        d_key,
        d_place,
        d_type,
        d_check,
        e_select,
        e_pattern,
        e_centre,
        e_quantity,
        e_ok,
        e_made,
        f_box,
        f_check,
        g_clear,
        g_double_click,
        g_check,
        f_box,
        h_delete,
        h_check,
        h_undone,
        i_mirror,
        i_click_1,
        i_click_2,
        i_check,
    ],
    paced_by="state",
)
