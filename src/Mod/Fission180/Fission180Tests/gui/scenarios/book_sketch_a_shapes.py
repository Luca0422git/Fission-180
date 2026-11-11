# SPDX-License-Identifier: LGPL-2.1-or-later
"""What a sketch shows of an ellipse, a polygon and a spline (wave 7, the book parity
report, "FreeCAD shows through": a hexagon with two dashed circles, a dashed line and a
cloud of "= 14, 15, 16" labels; a fit point spline with its control polygon and "= 37, 39,
41"; an ellipse with focus points and one degree of freedom left after the book's
dimensions).

Drawn from the CREATE menu with real clicks through the X server (x_input).

  A  Circumscribed Polygon (6 sides): six lines; the circle that touches the edges is the
     one shown (its centre is the polygon's centre, its size the size across the flats);
     the corner circle and the spoke are on the hidden layer: not drawn (screen pixels) and
     not clickable; every helper constraint is in the sketch's virtual space (no "="
     labels); the sketch solves with no redundant constraint; one Ctrl+Z takes the polygon
     back, Ctrl+Y brings it back as it was
  B  Inscribed Polygon: its one circle (through the corners) stays, its helper constraints
     are not drawn either
  C  Fit Point Spline (five points, Enter): the curve and its five fit points are shown;
     its control circles are on the hidden layer and their Equal / Weight constraints in
     the virtual space; FreeCAD's control polygon is off; the sketch solves, nothing in the
     Report view; one Ctrl+Z takes the spline back with its points
  D  Control Point Spline: its control circles stay (they are what one drags), and Fission
     180 draws the control frame through them
  E  Ellipse drawn level (2 degrees off): no focus points, its two axes are construction
     lines, the major one is held Horizontal; with the centre on the origin and the two
     axes dimensioned (the book's dimensions) the sketch is fully defined; one Ctrl+Z takes
     the ellipse back
  F  Finish Sketch, save, close, open: the hidden curves and constraints are still hidden
"""

import os
import tempfile

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st
from Fission180Tests.gui import x_input as x

V = App.Vector
s = st.s
ORANGE = "#f5a623"


def sk():
    return App.ActiveDocument.getObject(s["name"])


def px(point):
    return h.screen_point(st.g(point))


def click(point, held=()):
    x.click(px(point), held=held)
    h.settle()


def helpers():
    from fission180 import sketch_draw_helpers

    return sketch_draw_helpers


def kinds(indices):
    return [sk().Geometry[i].TypeId.replace("Part::Geom", "") for i in indices]


def new_ids():
    return list(range(s["n"], len(sk().Geometry)))


def new_cons():
    return list(range(s["c"], len(sk().Constraints)))


def note():
    s["n"], s["c"] = len(sk().Geometry), len(sk().Constraints)


def stop_tool():
    st.esc()
    st.esc()
    Gui.Selection.clearSelection()


def dof():
    """The sketch's degrees of freedom, as the solver last found them."""
    sk().solve()
    return int(sk().DoF)


def drawn_bright(point):
    """A line is drawn at the sketch point (brighter than the dark background)."""
    colours = si.screen_colours(st.g(point), radius=3)
    return sum(si.rgb(si.brightest(colours))) > 3 * 110


def state():
    return (
        [g.TypeId for g in sk().Geometry],
        [(c.Type, c.First, c.Second, c.InVirtualSpace) for c in sk().Constraints],
        sorted(helpers().hidden(sk())),
    )


# -- A ------------------------------------------------------------------------------------
def setup():
    h.check("the X server takes test input (XTEST)", x.available())
    s["name"] = s["sk"].Name
    h.fit(iso=False)


def a_polygon():
    note()
    si.menu_item("CREATE", "Circumscribed Polygon")


def a_centre():
    click(V(-50, -20, 0))


def a_edge():
    click(V(-35, -20, 0))


def a_check():
    stop_tool()
    ids = new_ids()
    h.check(
        "A six lines, the corner circle, the spoke, the edge circle",
        kinds(ids) == ["LineSegment"] * 6 + ["Circle", "LineSegment", "Circle"],
        kinds(ids),
    )
    if len(ids) != 9:
        return
    hidden = helpers().hidden(sk())
    corner, spoke, edge = ids[6], ids[7], ids[8]
    h.check(
        "A the corner circle and the spoke are on the hidden layer",
        {corner, spoke} <= hidden,
        sorted(hidden),
    )
    h.check(
        "A the lines and the edge circle are not",
        not (set(ids[:6]) | {edge}) & hidden,
        sorted(hidden),
    )
    cons = sk().Constraints
    shown = [
        (cons[i].Type, cons[i].First, cons[i].Second)
        for i in new_cons()
        if not cons[i].InVirtualSpace and cons[i].Type != "Coincident"
    ]
    h.check("A no helper constraint is drawn (all in the virtual space)", shown == [], shown)
    h.check(
        "A the sketch solves, nothing redundant",
        sk().solve() >= 0 and not sk().RedundantConstraints and not sk().ConflictingConstraints,
        (sk().solve(), sk().RedundantConstraints),
    )
    geo = sk().Geometry
    r_edge, r_corner = geo[edge].Radius, geo[corner].Radius
    h.check("A the edge circle is where it was clicked (15 mm)", abs(r_edge - 15) < 0.3, r_edge)
    s["a"] = {"ids": ids, "state": state()}
    # a point of the corner circle away from the hexagon (between two corners the circle
    # bulges out of it): nothing drawn there; on the edge circle (inside): drawn
    import math

    mid = math.radians(0)  # the middle of the first edge is at 0 degrees: a corner at 30
    out = V(-50 + r_corner * math.cos(mid), -20 + r_corner * math.sin(mid), 0)
    inside = V(
        -50 + r_edge * math.cos(math.radians(30)), -20 + r_edge * math.sin(math.radians(30)), 0
    )
    Gui.updateGui()
    h.view_drawn("the 3D view to draw the polygon")
    h.check(
        "A the corner circle is not drawn on the screen",
        not drawn_bright(out),
        si.screen_colours(st.g(out), 1),
    )
    h.check("A the edge circle is drawn", drawn_bright(inside), si.screen_colours(st.g(inside), 1))
    h.shot("A-polygon")


def a_click_hidden():
    import math

    r = sk().Geometry[s["a"]["ids"][6]].Radius
    click(V(-50 + r, -20, 0))  # on the hidden corner circle, beside the hexagon
    names = [n for sel in Gui.Selection.getSelectionEx() for n in sel.SubElementNames]
    h.check("A a click on the hidden circle selects nothing", names == [], names)
    _ = math


def undo():
    st.undo()


def redo():
    st.redo()


def a_undone():
    h.check("A one Ctrl+Z took the polygon back", len(sk().Geometry) == s["n"], len(sk().Geometry))
    h.check("A ...with its constraints", len(sk().Constraints) == s["c"], len(sk().Constraints))


def a_redone():
    h.check("A Ctrl+Y brought it back as it was (hidden parts too)", state() == s["a"]["state"])


# -- B ------------------------------------------------------------------------------------
def b_polygon():
    note()
    si.menu_item("CREATE", "Inscribed Polygon")


def b_centre():
    click(V(-50, 25, 0))


def b_corner():
    click(V(-35, 25, 0))


def b_check():
    stop_tool()
    ids = new_ids()
    h.check(
        "B six lines and their circle", kinds(ids) == ["LineSegment"] * 6 + ["Circle"], kinds(ids)
    )
    h.check("B the circle is shown", not set(ids) & helpers().hidden(sk()))
    cons = sk().Constraints
    shown = [
        cons[i].Type
        for i in new_cons()
        if not cons[i].InVirtualSpace and cons[i].Type != "Coincident"
    ]
    h.check("B no helper constraint is drawn", shown == [], shown)
    st.sketch_ok("B")


# -- C ------------------------------------------------------------------------------------
def c_spline():
    note()
    si.menu_item("CREATE", "Fit Point Spline")


def c_points():
    for p in (V(5, -12, 0), V(18, -25, 0), V(31, -13, 0), V(44, -27, 0), V(57, -16, 0)):
        click(p)


def c_enter():
    st.enter()


def c_check():
    st.esc()
    Gui.Selection.clearSelection()
    ids = new_ids()
    splines = [i for i in ids if sk().Geometry[i].TypeId == "Part::GeomBSplineCurve"]
    h.check("C one spline", len(splines) == 1, kinds(ids))
    if not splines:
        return
    roles = helpers().aligned_to(sk(), splines[0])
    poles = roles.get("BSplineControlPoint", [])
    knots = roles.get("BSplineKnotPoint", [])
    hidden = helpers().hidden(sk())
    h.check(
        "C its five fit points are shown",
        len(knots) == 5 and not set(knots) & hidden,
        (knots, sorted(hidden)),
    )
    h.check(
        "C its control circles are on the hidden layer",
        poles and set(poles) <= hidden,
        (poles, sorted(hidden)),
    )
    cons = sk().Constraints
    shown = [
        cons[i].Type
        for i in new_cons()
        if cons[i].Type in ("Equal", "Weight") and not cons[i].InVirtualSpace
    ]
    h.check("C no Equal / Weight label of the control circles is drawn", shown == [], shown)
    param = App.ParamGet("User parameter:BaseApp/Preferences/Mod/Sketcher/General")
    h.check(
        "C FreeCAD's control polygon is off",
        not param.GetBool("BSplineControlPolygonVisible", True),
    )
    st.sketch_ok("C")
    for a, b in zip(
        (V(5, -12, 0), V(57, -16, 0)),
        (sk().Geometry[splines[0]].StartPoint, sk().Geometry[splines[0]].EndPoint),
    ):
        h.check("C the spline ends where it was clicked", (a - b).Length < 2.5, (a, b))
    s["c_spline"] = {"n": s["n"], "frames": len(st.session().frames.drawn)}
    h.check("C no control frame is drawn for a fit point spline", st.session().frames.drawn == [])
    h.shot("C-fit-spline")


def c_undone():
    h.check(
        "C one Ctrl+Z took the spline back with its points",
        len(sk().Geometry) == s["n"],
        kinds(new_ids()),
    )


# -- D ------------------------------------------------------------------------------------
def d_spline():
    note()
    si.menu_item("CREATE", "Control Point Spline")


def d_points():
    for p in (V(5, 40, 0), V(20, 27, 0), V(35, 41, 0), V(50, 29, 0)):
        click(p)


def d_check():
    st.esc()
    Gui.Selection.clearSelection()
    ids = new_ids()
    splines = [i for i in ids if sk().Geometry[i].TypeId == "Part::GeomBSplineCurve"]
    h.check("D one spline", len(splines) == 1, kinds(ids))
    if not splines:
        return
    poles = helpers().aligned_to(sk(), splines[0]).get("BSplineControlPoint", [])
    h.check(
        "D its four control circles are shown",
        len(poles) == 4 and not set(poles) & helpers().hidden(sk()),
        poles,
    )
    frames = st.session().frames.drawn
    h.check(
        "D Fission 180 draws its control frame", len(frames) == 1 and len(frames[0]) == 4, frames
    )
    cons = sk().Constraints
    shown = [
        cons[i].Type
        for i in new_cons()
        if cons[i].Type in ("Equal", "Weight") and not cons[i].InVirtualSpace
    ]
    h.check("D ...and no Equal / Weight labels", shown == [], shown)
    st.sketch_ok("D")
    h.shot("D-control-spline")


# -- E ------------------------------------------------------------------------------------
def e_ellipse():
    note()
    si.menu_item("CREATE", "Ellipse")


def e_centre():
    click(V(15, 5, 0))


def e_major():
    click(V(35, 5.7, 0))  # 2 degrees off level


def e_minor():
    click(V(15, 13, 0))


def e_check():
    stop_tool()
    ids = new_ids()
    h.check(
        "E the ellipse and its two axes, no focus points",
        kinds(ids) == ["Ellipse", "LineSegment", "LineSegment"],
        kinds(ids),
    )
    if len(ids) != 3:
        return
    ellipse, major, minor = ids
    h.check(
        "E the axes are construction lines",
        sk().getConstruction(major) and sk().getConstruction(minor),
    )
    level = [c for c in sk().Constraints if c.Type == "Horizontal" and c.First == major]
    h.check("E the major axis, drawn 2 degrees off level, is held Horizontal", len(level) == 1)
    d = sk().Geometry[major].EndPoint - sk().Geometry[major].StartPoint
    h.check("E ...and is level", abs(d.y) < 1e-7, d)
    st.sketch_ok("E")
    s["e"] = ids


def e_book_dimensions():
    """The book's ellipse: its centre on the origin... here on a fixed point; the two axes
    dimensioned. Fusion's turns black (fully defined)."""
    import Sketcher

    ellipse, major, minor = s["e"]
    before = dof()
    doc = App.ActiveDocument
    doc.openTransaction("book dimensions")
    sk().addConstraint(Sketcher.Constraint("DistanceX", -1, 1, ellipse, 3, 15.0))
    sk().addConstraint(Sketcher.Constraint("DistanceY", -1, 1, ellipse, 3, 5.0))
    sk().addConstraint(Sketcher.Constraint("Distance", major, 40.0))
    sk().addConstraint(Sketcher.Constraint("Distance", minor, 16.0))
    doc.commitTransaction()
    after = dof()
    h.check(
        "E the centre and the two axes dimensioned take the ellipse's 4 freedoms",
        before - after == 4,
        (before, after),
    )
    h.shot("E-ellipse")


def e_undone_dims():
    pass


def e_undone():
    h.check("E one Ctrl+Z took the ellipse back", len(sk().Geometry) == s["n"], kinds(new_ids()))


# -- F ------------------------------------------------------------------------------------
def finish():
    s["final"] = state()
    h.ribbon("Finish Sketch")


def f_save():
    path = os.path.join(tempfile.mkdtemp(prefix="f180-shapes-"), "shapes.FCStd")
    s["path"] = path
    App.ActiveDocument.saveAs(path)
    name = App.ActiveDocument.Name
    App.closeDocument(name)


def f_open():
    App.openDocument(s["path"])


f_open.done = (
    lambda: App.ActiveDocument is not None and App.ActiveDocument.getObject(s["name"]) is not None
)
f_open.done_what = "the saved design is open"


def f_check():
    h.check(
        "F after save and open the same curves and constraints are hidden", state() == s["final"]
    )
    h.check("F ...and some are", len(s["final"][2]) > 0, s["final"][2])


h.run(
    "book_sketch_a_shapes",
    st.start_steps("BookSketchShapes")
    + [
        setup,
        a_polygon,
        a_centre,
        a_edge,
        a_check,
        a_click_hidden,
        undo,
        a_undone,
        redo,
        a_redone,
        b_polygon,
        b_centre,
        b_corner,
        b_check,
        c_spline,
        c_points,
        c_enter,
        c_check,
        undo,
        c_undone,
        redo,
        d_spline,
        d_points,
        c_enter,
        d_check,
        e_ellipse,
        e_centre,
        e_major,
        e_minor,
        e_check,
        undo,
        e_undone,
        redo,
        e_book_dimensions,
        finish,
        f_save,
        f_open,
        f_check,
    ],
    paced_by="state",
)
