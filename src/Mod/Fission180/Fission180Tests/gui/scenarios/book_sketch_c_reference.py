# SPDX-License-Identifier: LGPL-2.1-or-later
"""Wave 7, sketch-c: Fusion's "Auto project edges on reference" (the book parity report,
components' builder: "draw tools and dimensions do not snap or infer to OTHER components'
geometry until projected with P"; sketch-a: "not built").

Setup as components' own Project scenario: "Nozzle" with a 20 x 20 x 10 block standing 30 mm
along X, "Pins" with a cylinder (radius 5, height 20, axis through x 0, y 40), the empty
component "Heat Break", which is active and gets a sketch on its XY plane. Nothing of the
other components is in that sketch.

  A  Line (FreeCAD's tool): a click on empty space, a click ON the Nozzle's back edge: the
     edge is projected (one purple line from (30, 20) to (50, 20)) and the line ends on it,
     held there by a constraint. Ctrl+Z, Ctrl+Z: the line, then the projection, are gone;
     Ctrl+Y twice brings both back
  B  Sketch Dimension: the centre of a sketch circle, then the Pins' top edge (another
     component): the edge is projected (a circle about (0, 40)) and picked; placed, 30
     typed: the two centres are 30 apart
  C  a constraint tool, tool first: Parallel, a slanted sketch line, then the Nozzle's right
     edge: projected, and the line is parallel to it (upright)
  D  Fission 180's own 2-Point Circle: its first click on a corner of the Nozzle: the corner
     is projected as a point and the circle starts on it
  E  Preferences > Design > "Auto project edges on reference" off: a line ended on the
     Nozzle's left edge projects nothing (the end stays where it was clicked, free)
"""

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import book_components_steps as k
from Fission180Tests.gui import book_sketch_b_steps as b
from Fission180Tests.gui import component_steps as cs
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st

V = App.Vector
s = st.s


def new_design():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("BookSketchCReference")
    nozzle = k.new_component("Nozzle", at=(30, 0, 0))
    k.add_box(nozzle, (0, 0, 20, 20), 10)
    pins = k.new_component("Pins")
    k.add_cylinder(pins, (0, 40), 5, 20)
    k.new_component("Heat Break")
    k.settle_design()


def sk():
    return st.sketch()


def externals():
    return list(sk().ExternalGeo)[2:]


def describe():
    out = []
    for g in externals():
        if g.TypeId == "Part::GeomLineSegment":
            out.append(("line", tuple(round(v, 3) for v in (*g.StartPoint, *g.EndPoint))))
        elif "Circle" in g.TypeId:
            out.append(("circle", tuple(round(v, 3) for v in (*g.Center, g.Radius))))
        elif g.TypeId == "Part::GeomPoint":
            out.append(("point", (round(g.X, 3), round(g.Y, 3))))
        else:
            out.append((g.TypeId,))
    return out


def on_external(geo):
    """The constraints that tie sketch curve `geo` to a projected curve."""
    out = []
    for c in sk().Constraints:
        named = [g for g in (c.First, c.Second, c.Third) if g != -2000]
        if geo in named and any(g <= -3 for g in named):
            out.append(c.Type)
    return out


def end_tool():
    st.esc()
    st.esc()
    Gui.Selection.clearSelection()


def activate():
    cs.click_radio("Heat Break")


activate.done = lambda: k.active_label() == "Heat Break"
activate.done_what = "Heat Break is active"


def create_sketch():
    h.fit()
    h.ribbon("Create Sketch")


def plane():
    pl.click_square("XY_Plane")


plane.done = lambda: h.in_sketch() is not None
plane.done_what = "the sketch is open"


def opened():
    import Part

    sketch = h.in_sketch()
    s["sk"] = sketch
    h.check("the sketch is in Heat Break", k.container_label(sketch) == "Heat Break")
    doc = App.ActiveDocument
    doc.openTransaction("setup")
    s["circle"] = b.add(Part.Circle(V(-20, 10, 0), V(0, 0, 1), 4))
    s["slant"] = b.add(Part.LineSegment(V(60, -25, 0), V(66, -8, 0)))
    doc.commitTransaction()
    doc.recompute()
    h.check("nothing of the other components is in the sketch", len(externals()) == 0, describe())
    h.fit(iso=False)
    b.watch_modals()


# == A ======================================================================================
def a_line():
    s["geo"] = len(sk().Geometry)
    h.press("l")


def a_first():
    st.click(V(15, -22, 0))


def a_on_edge():
    st.click(V(42, 20, 10))  # the Nozzle's top back edge, seen from above


def a_check():
    h.check("A the Nozzle's edge was projected on the click", len(externals()) == 1, describe())
    found = describe()
    h.check(
        "A ...where the edge is: (30, 20) to (50, 20)",
        found and found[0][0] == "line" and sorted(found[0][1][0:4:3]) == [30.0, 50.0],
        found,
    )
    lines = [
        i
        for i, g in enumerate(sk().Geometry)
        if i >= s["geo"] and g.TypeId == "Part::GeomLineSegment"
    ]
    h.check("A one line was drawn", len(lines) == 1, lines)
    if lines:
        end = sk().Geometry[lines[0]].EndPoint
        h.check(
            "A ...ending on the edge",
            abs(end.y - 20) < 1e-6 and 30 - 1e-6 <= end.x <= 50 + 1e-6,
            end,
        )
        h.check(
            "A ...held on it by a constraint", bool(on_external(lines[0])), on_external(lines[0])
        )
        s["line"] = lines[0]
    h.check("A Heat Break is still the active component", k.active_label() == "Heat Break")
    end_tool()
    st.undo()


def a_undo_line():
    h.check("A Ctrl+Z took the line", len(sk().Geometry) == s["geo"], len(sk().Geometry))
    h.check("A ...the projection is still there", len(externals()) == 1, describe())
    st.undo()


def a_undo_projection():
    h.check("A a second Ctrl+Z took the projection", len(externals()) == 0, describe())
    h.check("A still in the sketch", h.in_sketch() is not None)
    st.redo()


def a_redo():
    st.redo()


def a_redone():
    h.check(
        "A Ctrl+Y twice: the projection and the line are back", len(externals()) == 1, describe()
    )
    h.check("A ...the line too", len(sk().Geometry) == s["geo"] + 1, len(sk().Geometry))


# == B ======================================================================================
def b_dimension():
    s["cons"] = len(sk().Constraints)
    h.press("d")


def b_centre():
    st.click(V(-20, 10, 0))


def b_pin():
    h.check("B the circle's centre is picked", st.tool() is not None and len(st.tool().picks) == 1)
    st.click(V(3.5355, 43.5355, 20))  # the Pins' top edge (clear of the sketch's Y axis)


def b_picked():
    circles = [d for d in describe() if d[0] == "circle"]
    h.check(
        "B the pin's edge (another component) was projected: a circle about (0, 40)",
        len(circles) == 1 and circles[0][1][:2] == (0.0, 40.0),
        describe(),
    )
    picks = st.tool().picks
    h.check("B ...and picked", len(picks) == 2 and picks[1][0] <= -3, picks)
    st.click(V(-30, 30, 0))


def b_type():
    h.check("B the value box is open", st.session().editor is not None)
    si.type_text("30")


def b_check():
    c = sk().Geometry[s["circle"]].Center
    d = ((c.x - 0) ** 2 + (c.y - 40) ** 2) ** 0.5
    h.check("B 30 typed: the two centres are 30 apart", abs(d - 30) < 1e-6, d)
    end_tool()


# == C ======================================================================================
def c_parallel():
    s["ext"] = len(externals())
    b.mark()
    b.menu("Parallel")


def c_line():
    g = sk().Geometry[s["slant"]]
    st.click((g.StartPoint + g.EndPoint) * 0.5)


def c_edge():
    st.click(V(50, 10, 10))  # the Nozzle's right edge


def c_check():
    h.check("C the Nozzle's right edge was projected", len(externals()) == s["ext"] + 1, describe())
    g = sk().Geometry[s["slant"]]
    h.check(
        "C the sketch line is parallel to it (upright)",
        abs(g.StartPoint.x - g.EndPoint.x) < 1e-6,
        (g.StartPoint, g.EndPoint),
    )
    kinds = [c[0] for c in b.new_cons()]
    h.check("C ...by a Parallel constraint", kinds == ["Parallel"], b.new_cons())
    end_tool()


# == D ======================================================================================
def d_tool():
    s["ext"] = len(externals())
    s["geo"] = len(sk().Geometry)
    si.menu_item("CREATE", "2-Point Circle")


def d_corner():
    h.check("D 2-Point Circle runs", st.tool_title() == "2-Point Circle", st.tool_title())
    st.click(V(30, 20, 10))  # the Nozzle's back left corner


def d_second():
    points = [d for d in describe() if d[0] == "point"]
    h.check(
        "D the corner was projected as a point",
        len(points) == 1 and points[0][1] == (30.0, 20.0),
        describe(),
    )
    st.click(V(18, 32, 0))


def d_check():
    circles = [
        i for i, g in enumerate(sk().Geometry) if i >= s["geo"] and g.TypeId == "Part::GeomCircle"
    ]
    h.check("D one circle was drawn", len(circles) == 1, circles)
    if circles:
        g = sk().Geometry[circles[0]]
        d = ((g.Center.x - 30) ** 2 + (g.Center.y - 20) ** 2) ** 0.5
        h.check("D ...through the projected corner", abs(d - g.Radius) < 1e-6, (d, g.Radius))
        h.check("D ...held on it", bool(on_external(circles[0])), on_external(circles[0]))
    end_tool()


# == E ======================================================================================
def e_off():
    from fission180 import preferences_ui, sketch_reference

    preferences_ui.write("sketch_project_on_reference", False)
    h.check("E the preference is off", not sketch_reference.enabled())
    s["ext"] = len(externals())
    s["geo"] = len(sk().Geometry)
    h.press("l")


def e_first():
    st.click(V(15, 45, 0))


def e_on_edge():
    st.click(V(30, 8, 10))  # the Nozzle's left edge


def e_check():
    h.check("E nothing was projected", len(externals()) == s["ext"], describe())
    lines = [
        i
        for i, g in enumerate(sk().Geometry)
        if i >= s["geo"] and g.TypeId == "Part::GeomLineSegment"
    ]
    h.check("E the line was drawn all the same", len(lines) == 1, lines)
    if lines:
        h.check("E ...its end is free", not on_external(lines[0]), on_external(lines[0]))
    end_tool()
    from fission180 import preferences_ui

    preferences_ui.write("sketch_project_on_reference", True)
    b.no_modal("auto project on reference")
    st.sketch_ok("at the end")


h.run(
    "book_sketch_c_reference",
    [
        new_design,
        activate,
        create_sketch,
        plane,
        opened,
        a_line,
        a_first,
        a_on_edge,
        a_check,
        a_undo_line,
        a_undo_projection,
        a_redo,
        a_redone,
        b_dimension,
        b_centre,
        b_pin,
        b_picked,
        b_type,
        b_check,
        c_parallel,
        c_line,
        c_edge,
        c_check,
        d_tool,
        d_corner,
        d_second,
        d_check,
        e_off,
        e_first,
        e_on_edge,
        e_check,
    ],
    paced_by="state",
)
