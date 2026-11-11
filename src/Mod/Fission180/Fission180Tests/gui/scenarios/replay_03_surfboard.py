# SPDX-License-Identifier: LGPL-2.1-or-later
"""Replay of the book's Project 3, "Finger Surfboard" (Mastering Autodesk Fusion, 2nd ed.,
pp 40-46; book parity report lines 974-1045), from its first step to its last, in one
design, with a person's defaults (full grid snap, scale at the first dimension, the layout
grid, strict undo) and real input only. Every step the report lists is here in its order,
the book's way: where the report needed a workaround the replay does not use it.

  1  a new design from the "+" beside the design tabs
  2  CONSTRUCT > Offset Plane from the Right plane, four times: 24 / 72 / 116 / 140 mm
  3  on each: Create Sketch (the plane clicked in the view), CREATE > Ellipse, D on the
     major axis, the minor axis and origin-to-centre: 26 x 3.5 @ 5.2, 38 x 4 @ 7,
     29.6 x 4 @ 6, 18 x 4 @ 4.2; each sketch fully defined (the book: "turns black").
     The centres lie BELOW the origin: a board's nose turns up, and the book's hole
     needs Flip from the Top plane, which it only does with the board under that plane.
  4  CREATE > Loft: the four ellipses from the tail to the nose, then the ORIGIN clicked
     in the view (its dot under an offset plane's square): the board ends in a point,
     12,617 mm3 (the report: 12,618)
  5  A: Appearance, "polystyrene" searched, the look dragged onto the board, its editor
     (double-click under In This Design), Scale 25 %
  6  INSERT > Canvas (a stand-in picture: the book's is a download of its publisher), the
     Front plane, Scale Plane XY 8.25, Horizontal Flip
  7  Create Sketch on the Front plane, CREATE > Project / Include > Intersect: a click on
     an offset plane's line across the board (FreeCAD's tool failed there with a
     traceback) gives that plane's line, Ctrl+Z; a click on the board gives its outline
  8  Fit Point Spline from the outline to the outline, Enter; the spline selected,
     Fix/Unfix: fully defined; Finish Sketch; the Canvases eye
  9  E: the fin's area, Symmetric, Whole Length, 2.4: Join by itself
 10  Create Sketch on the Top plane, a circle; D from its centre to the board's tail EDGE
     (a model edge: projected on the spot) = 2, D on the circle = 2: fully defined
 11  E: Extent All goes up, away from the board (said); Flip: Cut by itself
 12  F: the fin's two edges and the hole's inner face, 1 mm
 13  File > Export, STL (Binary): the file's volume is the board's
"""

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import insert_steps as ins_file
from Fission180Tests.gui import inspect_steps as ins
from Fission180Tests.gui import looks_steps as k
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import replay_b_steps as r
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st
from Fission180Tests.gui import timeline_input as tl
from Fission180Tests.gui import widget_input as w

V = App.Vector
S = {}

# the book's four sections: the plane's distance from the Right plane, the ellipse's major
# and minor axis, and how far its centre is from the origin (below it)
SECTIONS = (
    (24.0, 26.0, 3.5, 5.2),
    (72.0, 38.0, 4.0, 7.0),
    (116.0, 29.6, 4.0, 6.0),
    (140.0, 18.0, 4.0, 4.2),
)


def near(a, b, tol=1e-6):
    return abs(a - b) <= tol * max(1.0, abs(b))


# -- a new design from the "+" beside the tabs ------------------------------------------------
def home():
    from fission180 import home_ui

    Gui.activateWorkbench("Fission180Workbench")
    r.user_defaults()
    home_ui.show()


home.done = lambda: __import__("fission180.home_ui").home_ui.view() is not None
home.done_what = "Home to show"


def first_design():
    from fission180 import home_ui

    w.click(home_ui.view().new_button)


first_design.done = lambda: App.ActiveDocument is not None and h.gl_widget().isVisible()
first_design.done_what = "the first design's 3D view"


def plus_tab():
    ribbon = __import__("fission180.shell").shell.ribbon()
    S["docs"] = len(App.listDocuments())
    h.check('a "+" beside the design tabs', ribbon.new_tab.isVisible())
    w.click(ribbon.new_tab)


plus_tab.done = lambda: len(App.listDocuments()) == S["docs"] + 1
plus_tab.done_what = "a new design in a second tab"


# -- CONSTRUCT > Offset Plane from the Right plane --------------------------------------------
def section_steps(n, distance, major, minor, up):
    t = {}
    tag = "section %d" % (n + 1)

    def plane_start():
        h.click_empty()
        h.fit()
        si.menu_item("CONSTRUCT", "Offset Plane")

    plane_start.done = lambda: ins.construct_panel() is not None
    plane_start.done_what = "the Offset Plane dialog is open"

    def plane_pick():
        pl.click_square("YZ_Plane")

    plane_pick.done = lambda: ins.construct_panel() is not None and (
        ins.construct_panel().datum is not None
    )
    plane_pick.done_what = "the plane shows"

    def plane_distance():
        p = ins.construct_panel()
        ins.type_into(p.distance.widget, "%g" % distance)
        h.caught_up(p)

    def plane_ok():
        p = ins.construct_panel()
        t["datum"] = p.datum
        h.task_button("OK")

    plane_ok.done = lambda: ins.construct_panel() is None
    plane_ok.done_what = "the Offset Plane dialog is closed"

    def plane_made():
        base = t["datum"].getGlobalPlacement().Base
        h.check(
            "%s: the plane lies %g mm to the right" % (tag, distance), near(base.x, distance), base
        )
        labels = r.browser_labels()
        h.check("%s: the browser has a Construction folder" % tag, "Construction" in labels, labels)
        h.fit()
        h.ribbon("Create Sketch")

    def sketch_plane():
        # a spot of the new plane's square that no older plane is in front of
        h.click(V(distance, -20, -20))

    sketch_plane.done = lambda: h.in_sketch() is not None
    sketch_plane.done_what = "the sketch on the offset plane is open"

    def sketch_open():
        sketch = r.note_sketch()
        t["sketch"] = sketch
        base = sketch.getGlobalPlacement().Base
        h.check("%s: the sketch lies on the offset plane" % tag, near(base.x, distance), base)
        t["n"] = len(sketch.Geometry)
        si.menu_item("CREATE", "Ellipse")

    def ellipse_centre():
        r.click(V(0, -5, 0))

    def ellipse_major():
        r.click(V(15, -5, 0))

    def ellipse_minor():
        r.click(V(0, -8, 0))

    def ellipse_drawn():
        r.end_tool()
        sketch = r.sk()
        kinds = [x.TypeId.replace("Part::Geom", "") for x in sketch.Geometry[t["n"] :]]
        h.check(
            "%s: an ellipse with its two axes, no focus points" % tag,
            kinds == ["Ellipse", "LineSegment", "LineSegment"],
            kinds,
        )
        t["ellipse"], t["major"], t["minor"] = t["n"], t["n"] + 1, t["n"] + 2
        centre = r.geo(t["ellipse"]).Center
        # (the book adds Horizontal/Vertical between the centre and the origin here; the
        # centre clicked on the axis is on it already, as in Fusion)
        h.check("%s: its centre is on the vertical axis" % tag, abs(centre.x) < 1e-9, centre)
        h.check("%s: 3 left to define (two axes, the height)" % tag, r.dof() == 3, r.dof())
        h.press("d")

    def major_pick():
        h.check("%s: D starts Sketch Dimension" % tag, st.tool_title() == "Sketch Dimension")
        line = r.geo(t["major"])
        r.click(line.StartPoint * 0.75 + line.EndPoint * 0.25)

    def major_place():
        r.click(r.mid(t["major"]) + V(4, -9, 0))

    def major_type():
        h.check("%s: the major axis' value box is open" % tag, r.editor() is not None)
        r.type_value("%g" % major)

    def major_done():
        value = 2 * r.geo(t["ellipse"]).MajorRadius
        h.check("%s: the major axis is %g" % (tag, major), near(value, major), value)
        # a closer look for the short axis (setting the view up is not what is tested)
        r.look_at(r.g(r.geo(t["ellipse"]).Center), major * 1.6)

    def minor_pick():
        line = r.geo(t["minor"])
        r.click(line.StartPoint * 0.72 + line.EndPoint * 0.28)

    def minor_place():
        r.click(r.geo(t["ellipse"]).Center + V(major * 0.3, major * 0.2, 0))

    def minor_type():
        h.check("%s: the minor axis' value box is open" % tag, r.editor() is not None)
        r.type_value("%g" % minor)

    def height_pick_origin():
        value = 2 * r.geo(t["ellipse"]).MinorRadius
        h.check("%s: the minor axis is %g" % (tag, minor), near(value, minor), value)
        r.click(V(0, 0, 0))

    def height_pick_centre():
        r.click(r.geo(t["ellipse"]).Center)

    def height_place():
        r.click(r.geo(t["ellipse"]).Center * 0.5 + V(-major * 0.4, 0, 0))

    def height_type():
        h.check("%s: the height's value box is open" % tag, r.editor() is not None)
        r.type_value("%g" % up)

    def defined():
        r.end_tool()
        e = r.geo(t["ellipse"])
        h.check(
            "%s: the ellipse is %g x %g, %g below the origin" % (tag, major, minor, up),
            near(2 * e.MajorRadius, major)
            and near(2 * e.MinorRadius, minor)
            and near(e.Center.y, -up)
            and abs(e.Center.x) < 1e-9,
            (e.MajorRadius, e.MinorRadius, e.Center),
        )
        h.check("%s: fully defined (the book: it turns black)" % tag, r.dof() == 0, r.dof())
        st.sketch_ok(tag)
        h.shot("section-%d" % (n + 1))
        h.ribbon("Finish Sketch")

    defined.done = lambda: h.in_sketch() is None
    defined.done_what = "the sketch is finished"

    steps = [
        plane_start,
        plane_pick,
        plane_distance,
        plane_ok,
        plane_made,
        sketch_plane,
        sketch_open,
        ellipse_centre,
        ellipse_major,
        ellipse_minor,
        ellipse_drawn,
        major_pick,
        major_place,
        major_type,
        major_done,
        minor_pick,
        minor_place,
        minor_type,
        height_pick_origin,
        height_pick_centre,
        height_place,
        height_type,
        defined,
    ]
    for fn in steps:
        fn.__name__ = "s%d_%s" % (n + 1, fn.__name__)
    S.setdefault("sections", []).append(t)
    return steps


# -- CREATE > Loft: the four ellipses from the tail to the nose, then the origin ---------------
def loft_panel():
    from fission180 import loft_ui

    p = loft_ui.LoftPanel.last
    return p if p is not None and not p._closed else None


def loft_open():
    h.click_empty()
    h.fit()
    si.menu_item("CREATE", "Loft")


loft_open.done = lambda: loft_panel() is not None
loft_open.done_what = "the Loft dialog is open"


def loft_pick(n):
    distance, _major, _minor, up = SECTIONS[n]

    def step():
        p = loft_panel()
        before = len(p.profiles)
        h.click(V(distance, 0, -up))
        h.caught_up(p)
        h.check(
            "Loft: a click in ellipse %d adds it as section %d" % (n + 1, before + 1),
            len(p.profiles) == before + 1 and p.profiles[-1][0] is S["sections"][n]["sketch"],
            (p.profiles, p.message.text(), h.state.get("last_click")),
        )

    step.__name__ = "loft_pick_%d" % (n + 1)
    step.timeout_s = 120
    return step


def loft_origin():
    p = loft_panel()
    h.check("Loft: the four ellipses in the order 4-3-2-1", len(p.profiles) == 4, p.profiles)
    S["loft4"] = r.volume()
    h.shot("loft-4-sections")
    h.click(V(0, 0, 0))  # the origin, as the book says: the board ends in a point


loft_origin.timeout_s = 120


def loft_pointed():
    p = loft_panel()
    h.caught_up(p)
    h.check(
        "Loft: the click on the origin adds the origin point as the last section",
        len(p.profiles) == 5,
        (p.profiles, p.message.text(), h.state.get("last_click")),
    )
    h.check("Loft: nothing refused", "\u26a0" not in p.message.text(), p.message.text())
    texts = [p.list.item(i).text().split(None, 1)[1] for i in range(p.list.count())]
    want = ["Sketch %d (area)" % n for n in (4, 3, 2, 1)] + ["Origin (point)"]
    h.check("Loft: the list names the sections as the browser does", texts == want, texts)
    h.shot("loft-preview")
    h.task_button("OK")


loft_pointed.done = lambda: loft_panel() is None
loft_pointed.done_what = "OK finished the loft"
loft_pointed.timeout_s = 120


def loft_made():
    made = r.bodies()
    h.check("Loft: one body", len(made) == 1, [b.Label for b in made])
    if len(made) != 1:
        return
    shape = made[0].Shape
    S["board"] = shape.Volume
    box = shape.BoundBox
    h.check("Loft: a valid solid", shape.isValid() and len(shape.Solids) == 1)
    h.check(
        "Loft: the board runs from the origin (a point) to the last plane at 140",
        abs(box.XMin) < 1e-6 and near(box.XMax, 140.0),
        box,
    )
    h.check("Loft: the report's 12,618 mm3", abs(shape.Volume - 12618.0) < 15.0, shape.Volume)
    h.check("Loft: in the timeline", any(x.startswith("Loft") for x in r.timeline()), r.timeline())
    h.check("nothing in error", not r.errors(), r.errors())
    h.fit()
    h.shot("board")


# -- Appearance (A): Polystyrene, its pattern scaled to 25 % ----------------------------------
ON_BOARD = V(72, 0, -5)  # the top of the board over the second section


def board():
    return r.bodies()[0]


def look_open():
    h.click_empty()
    r.key("a")


look_open.done = lambda: k.panel() is not None
look_open.done_what = "the Appearance dialog is open"


def look_search():
    p = k.panel()
    w.click(p.search)
    w.type_text(p.search, "polystyrene")


def look_drop():
    names = k.library_labels()
    h.check("Appearance: the search finds a Polystyrene look", "Polystyrene foam" in names, names)
    h.check("Appearance: the view takes the swatch", k.drop_look("Polystyrene foam", ON_BOARD))


def look_edit():
    data = k.stored(board())["body"] or {}
    h.check("Appearance: the board is Polystyrene", data.get("key") == "polystyrene", data)
    h.check("Appearance: it has a pattern (a texture)", bool(data.get("texture")), data)
    k.double_click_design("Polystyrene foam")


look_edit.done = lambda: k.editor() is not None
look_edit.done_what = "the look's editor is open"


def look_scale():
    e = k.editor()
    h.check("Appearance: the editor has a Scale", e.scale.isEnabled())
    k.type_field(e.scale, "25")


def look_ok():
    data = k.stored(board())["body"] or {}
    h.check("Appearance: Scale 25 % is stored", abs(data.get("scale", 100) - 25.0) < 1e-6, data)
    w.click(k.editor().ok_button)


look_ok.done = lambda: k.editor() is None
look_ok.done_what = "the editor is closed"


def look_close():
    groups, triangles = k.pattern_drawn(board().Tip)
    h.check("Appearance: the pattern is drawn on the board", groups >= 1 and triangles > 50)
    h.shot("polystyrene")
    h.task_button("OK")


look_close.done = lambda: k.panel() is None
look_close.done_what = "the Appearance dialog is closed"


# -- INSERT > Canvas on the Front plane -------------------------------------------------------
def canvas():
    found = ins_file.canvases()
    return found[0] if found else None


def canvas_open():
    # (the book's picture is a download of its publisher: a stand-in picture, 80 x 40 pixels)
    ins_file.use_file(ins_file.fixture("canvas.png"))
    h.click_empty()
    h.fit()
    si.menu_item("INSERT", "Canvas")


canvas_open.done = lambda: ins_file.panel() is not None
canvas_open.done_what = "the Canvas dialog is open"


def canvas_face():
    p = ins_file.panel()
    h.check("Canvas: the dialog waits for a face", p.title == "Canvas" and canvas() is None)
    pl.click_square("XZ_Plane")


canvas_face.done = lambda: canvas() is not None
canvas_face.done_what = "the canvas shows on the Front plane"


def canvas_scale():
    p = ins_file.panel()
    c = canvas()
    S["canvas_size"] = (c.XSize.Value, c.YSize.Value)
    ins_file.set_spin(p.scale_xy, 8.25)
    h.caught_up(p)


def canvas_flip():
    p = ins_file.panel()
    c = canvas()
    h.check(
        "Canvas: Scale Plane XY 8.25 makes it 8.25 times as large",
        near(c.XSize.Value, 8.25 * S["canvas_size"][0], 1e-4)
        and near(c.YSize.Value, 8.25 * S["canvas_size"][1], 1e-4),
        (c.XSize, c.YSize, S["canvas_size"]),
    )
    ins_file.set_check(p.flip_h, True)
    h.caught_up(p)


def canvas_ok():
    h.shot("canvas")
    h.task_button("OK")


canvas_ok.done = lambda: ins_file.panel() is None
canvas_ok.done_what = "the Canvas dialog is closed"


def canvas_made():
    c = canvas()
    labels = r.browser_labels()
    h.check("Canvas: in the browser's Canvases folder", "Canvases" in labels, labels)
    normal = c.Placement.Rotation.multVec(V(0, 0, 1))
    h.check("Canvas: it lies on the Front plane", abs(abs(normal.y) - 1.0) < 1e-6, normal)


# -- the fin: a sketch on the Front plane, the board's outline (Intersect), a spline -----------
def fin_sketch():
    h.click_empty()
    h.fit()
    h.ribbon("Create Sketch")


def fin_plane():
    pl.click_square("XZ_Plane")


fin_plane.done = lambda: h.in_sketch() is not None
fin_plane.done_what = "the sketch on the Front plane is open"


def fin_intersect():
    sketch = r.note_sketch()
    S["fin"] = sketch
    normal = sketch.getGlobalPlacement().Rotation.multVec(V(0, 0, 1))
    h.check("Fin: the sketch lies on the Front plane", abs(abs(normal.y) - 1.0) < 1e-6, normal)
    # a closer look at the board, a thin sliver from the front (the report: "the first
    # clicks missed it; zooming in worked")
    r.look_at(V(70, 0, -3), 90.0)
    S["external"] = len(sketch.ExternalGeo)
    si.menu_item("CREATE", "Intersect")


def fin_click_plane():
    # a click on the board where an offset plane crosses it, seen edge-on (a yellow line):
    # the plane is in front. FreeCAD's tool failed there with a traceback in the Report view.
    h.click(V(72, 0, -7))


def fin_plane_line():
    sketch = r.sk()
    made = sketch.ExternalGeo[S["external"] :]
    h.check(
        "Fin: Intersect on a plane's line brings in the line where the planes cut",
        len(made) == 1 and made[0].TypeId == "Part::GeomLineSegment",
        [g.TypeId for g in made],
    )
    if made:
        x = r.g(made[0].StartPoint).x
        h.check("Fin: ...the line of Plane 2, at x = 72", near(x, 72.0), x)
    st.undo()


def fin_click_board():
    sketch = r.sk()
    h.check(
        "Fin: Ctrl+Z takes the plane's line back, the tool goes on",
        len(sketch.ExternalGeo) == S["external"],
        len(sketch.ExternalGeo),
    )
    h.click(V(90, 0, -6.6))  # the board, seen from the front


def fin_outline():
    sketch = r.sk()
    made = sketch.ExternalGeo[S["external"] :]
    h.check("Fin: Intersect draws the board's outline in the sketch", len(made) >= 2, len(made))
    h.shot("fin-intersect")
    r.end_tool()
    # the board's underside: the outline curve that is lower in the middle of the board
    S["under"] = min(made, key=lambda g: r.on_curve_at_x(g, 72.0).y)
    S["n"] = len(sketch.Geometry)
    r.look_at(V(116, 0, -12), 60.0)
    si.menu_item("CREATE", "Fit Point Spline")


def fin_spline_points():
    first = r.on_curve_at_x(S["under"], 100.0)
    last = r.on_curve_at_x(S["under"], 132.0)
    S["ends"] = (first, last)
    for point in (first, V(110, -17, 0), V(124, -19, 0), last):
        r.click(point)


def fin_spline_enter():
    st.enter()


def fin_spline_made():
    r.end_tool()
    sketch = r.sk()
    splines = [
        i
        for i in range(S["n"], len(sketch.Geometry))
        if sketch.Geometry[i].TypeId == "Part::GeomBSplineCurve"
    ]
    h.check("Fin: one fit point spline", len(splines) == 1, splines)
    if not splines:
        return
    S["spline"] = splines[0]
    curve = sketch.Geometry[splines[0]]
    on = [
        (c.Type, c.First, c.FirstPos, c.Second, c.SecondPos)
        for c in sketch.Constraints
        if c.Type == "PointOnObject" and c.Second <= -3
    ]
    h.check("Fin: its first and last point snapped onto the purple curve", len(on) == 2, on)
    for end in (curve.StartPoint, curve.EndPoint):
        gap = S["under"].toShape().distToShape(__import__("Part").Vertex(end))[0]
        h.check("Fin: an end of the spline lies on the board's outline", gap < 1e-6, gap)
    st.sketch_ok("Fin")
    # the book: select the spline, Fix/Unfix
    r.click(curve.value((curve.FirstParameter + curve.LastParameter) * 0.37))


def fin_fix():
    names = [n for sel in Gui.Selection.getSelectionEx() for n in sel.SubElementNames]
    h.check("Fin: the spline is selected", names == ["Edge%d" % (S["spline"] + 1)], names)
    si.menu_item("CONSTRAINTS", "Fix/Unfix")


def fin_fixed():
    sketch = r.sk()
    blocked = [c.First for c in sketch.Constraints if c.Type == "Block"]
    h.check("Fin: Fix/Unfix fixed the spline", blocked == [S["spline"]], blocked)
    h.check("Fin: fully defined after Fix/Unfix", r.dof() == 0, r.dof())
    st.sketch_ok("Fin, fixed")
    h.shot("fin-sketch")
    h.ribbon("Finish Sketch")


fin_fixed.done = lambda: h.in_sketch() is None
fin_fixed.done_what = "the sketch is finished"


def canvas_hide():
    h.fit()
    tl.click_eye("Canvases")


def canvas_hidden():
    h.check("the Canvases eye hides the canvas", not canvas().ViewObject.Visibility)
    h.fit()
    h.shot("fin-sketch-done")


# -- E: the fin, Symmetric, Whole Length, 2.4 -------------------------------------------------
def extrude_panel():
    from fission180 import extrude_ui

    p = extrude_ui.ExtrudePanel.last
    return p if p is not None and not p._closed else None


def press_e():
    S["before"] = r.volume()
    h.click_empty()
    r.key("e")


press_e.done = lambda: extrude_panel() is not None
press_e.done_what = "the Extrude dialog is open"


def fin_profile():
    p = extrude_panel()
    if not p.profiles:  # (the one area of the sketch just made is taken by itself)
        first, last = S["ends"]
        h.click(S["fin"].getGlobalPlacement().multVec((first + last) * 0.5 + V(0, -4, 0)))
    h.caught_up(p)


fin_profile.done = lambda: extrude_panel() is not None and len(extrude_panel().profiles) == 1
fin_profile.done_what = "the fin's area is the profile"


def fin_symmetric():
    p = extrude_panel()
    h.check("Fin: the fin's sketch is the profile", p.profiles[0][0] is S["fin"], p.profiles)
    ui.choose(p.direction, "Symmetric")
    h.caught_up(p)


def fin_whole():
    p = extrude_panel()
    ui.choose(p.measurement, "Whole Length")
    h.caught_up(p)


def fin_distance():
    p = extrude_panel()
    ui.type_into(p.distance.widget, "2.4")
    h.caught_up(p)


fin_distance.timeout_s = 120


def fin_ok():
    p = extrude_panel()
    h.check(
        "Fin: the Operation is Join by itself (the fin touches the board)",
        p.operation.currentText() == "Join",
        p.operation.currentText(),
    )
    h.check(
        "Fin: Bodies to Join lists the board",
        p.bodies_names.text().strip() == "Body1",
        p.bodies_names.text(),
    )
    h.shot("fin-extrude")
    h.task_button("OK")


fin_ok.done = lambda: extrude_panel() is None
fin_ok.done_what = "OK finished the fin"
fin_ok.timeout_s = 120


def fin_made():
    made = r.bodies()
    h.check("Fin: still one body", len(made) == 1, [x.Label for x in made])
    shape = made[0].Shape
    grown = shape.Volume - S["before"]
    h.check("Fin: joined to the board (the body grew)", 100.0 < grown < 1000.0, grown)
    # The fin touches the board only along the Intersect curve (the board's underside is
    # round and rises away from the fin's flat top): one body, the two solids side by side
    # (OpenCASCADE's fuse of the two returned the fin alone and the deck vanished)
    h.check(
        "Fin: one valid body: the board and the fin side by side",
        shape.isValid() and len(shape.Solids) == 2,
        len(shape.Solids),
    )
    h.check(
        "Fin: the board is all there (its deck was lost by a fuse)",
        any(abs(sol.Volume - S["before"]) < 1e-3 for sol in shape.Solids),
        [sol.Volume for sol in shape.Solids],
    )
    # 2.4 mm across the Front plane in all: the fin's flat sides are at y = -1.2 and +1.2
    sides = sorted(
        round(f.CenterOfMass.y, 6)
        for f in shape.Faces
        if f.Surface.TypeId == "Part::GeomPlane" and abs(abs(f.normalAt(0, 0).y) - 1.0) < 1e-9
    )
    h.check("Fin: 2.4 mm thick in all, half to each side", sides == [-1.2, 1.2], sides)
    h.check("nothing in error", not r.errors(), r.errors())
    S["with_fin"] = shape.Volume
    h.fit()
    h.shot("fin")
    r.checkpoint("surf_hole")


# -- the tail hole: a circle on the Top plane, dimensioned to the board's tail edge ----------
def hole_sketch():
    h.click_empty()
    h.fit()
    h.ribbon("Create Sketch")


def hole_plane():
    pl.click_square("XY_Plane")


hole_plane.done = lambda: h.in_sketch() is not None
hole_plane.done_what = "the sketch on the Top plane is open"


def hole_circle():
    sketch = r.note_sketch()
    S["hole"] = sketch
    normal = sketch.getGlobalPlacement().Rotation.multVec(V(0, 0, 1))
    h.check("Hole: the sketch lies on the Top plane", abs(abs(normal.z) - 1.0) < 1e-6, normal)
    S["n"] = len(sketch.Geometry)
    S["external"] = len(sketch.ExternalGeo)
    r.look_at(V(125, 0, 0), 60.0)
    h.press("c")


def hole_centre():
    r.click(V(130, 0, 0))


def hole_rim():
    r.click(V(132, 0, 0))


def hole_dimension():
    r.end_tool()
    sketch = r.sk()
    circles = [
        i
        for i in range(S["n"], len(sketch.Geometry))
        if sketch.Geometry[i].TypeId == "Part::GeomCircle"
    ]
    h.check("Hole: one circle", len(circles) == 1, circles)
    S["circle"] = circles[0]
    centre = r.geo(S["circle"]).Center
    h.check("Hole: its centre is on the board's long axis", abs(centre.y) < 1e-9, centre)
    h.press("d")


def hole_pick_centre():
    r.click(r.geo(S["circle"]).Center)


def hole_pick_edge():
    picks = st.tool().picks
    h.check("Hole: the centre is picked", picks == [(S["circle"], 3)], picks)
    r.click(V(140, 5, 0))  # the board's tail edge: a model edge, nothing of the sketch


def hole_place():
    sketch = r.sk()
    h.check(
        "Hole: the board's tail edge is projected into the sketch on the spot",
        len(sketch.ExternalGeo) == S["external"] + 1,
        len(sketch.ExternalGeo),
    )
    picks = st.tool().picks
    h.check("Hole: ...and picked", len(picks) == 2 and picks[1][0] <= -3, picks)
    r.click(V(135, -6, 0))


def hole_type():
    c = r.sk().Constraints[-1]
    h.check(
        "Hole: a distance from the centre to the edge, with its value box",
        c.Type.startswith("Distance") and c.Driving and r.editor() is not None,
        (c.Type, c.Value, c.Driving),
    )
    r.type_value("2")


def hole_pick_circle():
    centre = r.geo(S["circle"]).Center
    h.check("Hole: the centre is 2 mm from the tail", near(centre.x, 138.0), centre)
    radius = r.geo(S["circle"]).Radius
    r.click(centre + V(-radius * 0.7071, radius * 0.7071, 0))


def hole_place_diameter():
    r.click(r.geo(S["circle"]).Center + V(-6, 5, 0))


def hole_type_diameter():
    h.check("Hole: the diameter's value box is open", r.editor() is not None)
    r.type_value("2")


def hole_defined():
    r.end_tool()
    circle = r.geo(S["circle"])
    h.check(
        "Hole: a 2 mm circle, its centre 2 mm from the tail",
        near(circle.Radius, 1.0) and near(circle.Center.x, 138.0) and abs(circle.Center.y) < 1e-9,
        (circle.Radius, circle.Center),
    )
    h.check("Hole: fully defined", r.dof() == 0, r.dof())
    st.sketch_ok("Hole")
    h.shot("hole-sketch")
    h.ribbon("Finish Sketch")


hole_defined.done = lambda: h.in_sketch() is None
hole_defined.done_what = "the sketch is finished"


# -- E: Extent All, Flip: Cut ------------------------------------------------------------------
def hole_profile():
    p = extrude_panel()
    if not p.profiles:
        h.click(V(138, 0.3, 0))
    h.caught_up(p)


hole_profile.done = lambda: extrude_panel() is not None and len(extrude_panel().profiles) == 1
hole_profile.done_what = "the circle is the profile"


def hole_all():
    p = extrude_panel()
    h.check("Hole: the circle's sketch is the profile", p.profiles[0][0] is S["hole"], p.profiles)
    ui.choose(p.extent, "All")
    h.caught_up(p)


hole_all.timeout_s = 120


def hole_flip():
    p = extrude_panel()
    S["said_all"] = p.message.text()
    h.check(
        "Hole: Extent All up from the Top plane goes away from the board, and says so",
        "No faces found in this direction" in S["said_all"],
        S["said_all"],
    )
    ui.click(p.flip)
    h.caught_up(p)


hole_flip.timeout_s = 120


def hole_ok():
    p = extrude_panel()
    h.check(
        "Hole: after Flip the extrusion goes into the board: Cut by itself",
        p.operation.currentText() == "Cut",
        (p.operation.currentText(), p.message.text()),
    )
    h.shot("hole-extrude")
    h.task_button("OK")


hole_ok.done = lambda: extrude_panel() is None
hole_ok.done_what = "OK finished the hole"
hole_ok.timeout_s = 120


def hole_made():
    made = r.bodies()
    shape = made[0].Shape
    removed = S["with_fin"] - shape.Volume
    h.check("Hole: one body, valid", len(made) == 1 and shape.isValid())
    # a 2 mm hole through a board about 4 mm thick there
    h.check("Hole: a 2 mm hole through the board", 8.0 < removed < 16.0, removed)
    inner = [
        f
        for f in shape.Faces
        if f.Surface.TypeId == "Part::GeomCylinder" and near(f.Surface.Radius, 1.0)
    ]
    h.check("Hole: its wall is a cylinder of radius 1", len(inner) == 1, len(inner))
    h.check("nothing in error", not r.errors(), r.errors())
    S["with_hole"] = shape.Volume
    h.fit()


STEPS_FIN = [press_e, fin_profile, fin_symmetric, fin_whole, fin_distance, fin_ok, fin_made]
STEPS_HOLE = [hole_sketch, hole_plane, hole_circle, hole_centre, hole_rim, hole_dimension]
STEPS_HOLE += [hole_pick_centre, hole_pick_edge, hole_place, hole_type, hole_pick_circle]
STEPS_HOLE += [hole_place_diameter, hole_type_diameter, hole_defined]
STEPS_HOLE += [press_e, hole_profile, hole_all, hole_flip, hole_ok, hole_made]


# -- F: the fin's two edges and the hole's inner face, 1 mm ------------------------------------
def fillet_open():
    h.click_empty()
    h.fit()
    S["before_fillet"] = r.volume()
    r.key("f")


fillet_open.done = lambda: b.blend_panel() is not None
fillet_open.done_what = "the Fillet dialog is open"


def fin_side_edges():
    """The fin's outline on each of its two flat sides (the spline, at y = -1.2 and +1.2:
    the lower of the two curves of each side; the upper one runs under the board)."""
    shape = r.bodies()[0].Shape
    found = []
    for side in (-1.2, 1.2):
        edges = [
            edge
            for edge in shape.Edges
            if abs(edge.BoundBox.YMin - side) < 1e-6 and abs(edge.BoundBox.YMax - side) < 1e-6
        ]
        if edges:
            found.append(min(edges, key=lambda e: e.BoundBox.ZMin))
    return found


def fillet_edge_1():
    edges = fin_side_edges()
    h.check("Fillet: the fin has its outline on both sides", len(edges) == 2, len(edges))
    S["fin_edges"] = edges
    # the side that faces the home view (it looks from -Y): y = -1.2
    edge = edges[0]
    point = edge.valueAt(edge.FirstParameter + 0.55 * (edge.LastParameter - edge.FirstParameter))
    r.look_at(point, 30.0)
    h.click(point)  # (Plane 3 is drawn over it: the click goes through to the edge)


def fillet_edge_2():
    p = b.blend_panel()
    h.check("Fillet: the first edge is picked", len(p.refs) == 1, p.refs)
    # the other side, seen through the fin's edge from below: the view is turned to look at
    # it (the ViewCube's bottom-back corner, as a person turns the part)
    h.view().viewRear()
    edge = S["fin_edges"][1]
    point = edge.valueAt(edge.FirstParameter + 0.55 * (edge.LastParameter - edge.FirstParameter))
    r.look_at(point, 30.0)
    h.click(point)


def is_hole_wall(face):
    return face.Surface.TypeId == "Part::GeomCylinder" and near(face.Surface.Radius, 1.0)


def hole_wall_aim(wall):
    """A point of the hole's inner wall that the view shows, found by state: the first thing
    FreeCAD's pick finds there, behind the construction planes (Plane 4 is drawn over the
    hole), is the wall. The view looks down at the board at about 35 degrees, so through the
    2 mm hole only the far wall's top 1.4 mm shows; the wall's middle (aimed at until wave 7,
    fix-8) lies behind the board's top skin, and the click picked the skin, the whole board's
    lofted face, on every screen (its edges, not the hole's two rims, were rounded). None:
    nowhere (the check after the click says what was picked)."""
    import math

    import Part

    from fission180 import profile_pick

    view = h.view()
    centre, radius = wall.Surface.Center, wall.Surface.Radius
    d = view.getViewDirection()
    away = V(d.x, d.y, 0)
    away.normalize()
    side = V(-away.y, away.x, 0)
    top = wall.BoundBox.ZMax
    for below in (0.3, 0.5, 0.7, 0.2, 0.9):  # mm under the wall's highest point
        for turn in (0.0, 20.0, -20.0, 40.0, -40.0):  # degrees around the far side
            a = math.radians(turn)
            out = away * math.cos(a) + side * math.sin(a)
            point = V(centre.x + out.x * radius, centre.y + out.y * radius, top - below)
            if wall.distToShape(Part.Vertex(point))[0] > 1e-4:
                continue  # above the rim there (the board's top is curved)
            for obj, short, _at in profile_pick.under(view, view.getPointOnViewport(point)):
                if profile_pick.is_glyph(obj):
                    continue
                face = obj.Shape.getElement(short) if short.startswith("Face") else None
                if face is not None and is_hole_wall(face):
                    return point
                break
    return None


def fillet_hole_face():
    p = b.blend_panel()
    h.check("Fillet: the fin's two edges are picked", len(p.refs) == 2, p.refs)
    h.fit()
    shape = r.bodies()[0].Shape
    wall = [f for f in shape.Faces if is_hole_wall(f)][0]
    centre = wall.Surface.Center
    r.look_at(V(centre.x, centre.y, wall.BoundBox.ZMax), 8.0)
    point = hole_wall_aim(wall)
    h.check("Fillet: the hole's inner wall shows through its opening", point is not None)
    if point is None:  # (the click below then says what it picked)
        point = V(centre.x, centre.y, wall.BoundBox.ZMax)
    h.click(point)


# (the three picks with the dialog's 1 mm: it looks for what fits, one trial build after the
# other, the app answering in between)
fillet_hole_face.timeout_s = 240


def fillet_size():
    p = b.blend_panel()
    faces = [ref for ref in p.refs if ref.startswith("Face")]
    walls = [ref for ref in faces if is_hole_wall(p.info.shape.getElement(ref))]
    h.check(
        "Fillet: 3 picks, the third the hole's inner wall (it gives its two rims)",
        len(p.refs) == 3 and faces == walls == p.refs[2:],
        (p.refs, [(f, p.info.shape.getElement(f).Surface.TypeId) for f in faces]),
    )
    b.type_into(p.radius.widget, "1")


fillet_size.timeout_s = 240


def fillet_ok():
    p = b.blend_panel()
    h.caught_up(p)
    d = p._value(p._row_key(), "radius")
    note = p.limit_label.text() if p.limit_label.isVisible() else ""
    S["fillet_note"], S["fillet_size"] = note, d
    # The book's 1 mm on the fin's two edges and the hole's rims: built on every board tried
    # (wave 7, fix-8; replay-b's "does not fit: 0.49 mm" came from the click on the hole,
    # which picked the board's whole skin). The board's lofted skin comes out a little
    # different from run to run (8513 or 8781 mm2 here, the fin's spline is clicked), and
    # OpenCASCADE's answer for a round on it is not the same for every size (on one board 0.3
    # and 0.4 mm refused, 0.49 built): where 1 mm is refused, the dialog must say so with the
    # size that fits, and OK makes that. Never 1 mm in the box with no note and no fillet.
    built = abs(d - 1.0) < 1e-9 and not note and not p.message.text()
    held = note.startswith("1 mm does not fit: limited to ") and 0.0 < d < 1.0
    h.check(
        "Fillet: 1 mm (the book), or the dialog says it does not fit and holds what fits",
        built or held,
        (note, d, p.message.text()),
    )
    h.fit()
    h.shot("fillet")
    h.task_button("OK")


fillet_ok.done = lambda: b.blend_panel() is None
fillet_ok.done_what = "OK finished the fillet"
fillet_ok.timeout_s = 240


def fillet_made():
    made = r.bodies()
    shape = made[0].Shape
    h.check("Fillet: one body, valid", len(made) == 1 and shape.isValid(), len(made))
    changed = S["before_fillet"] - shape.Volume
    # a round of radius r takes (1 - pi/4) r2 off per mm of edge: the fin's two 43 mm edges
    # and the hole's two rims, about 21 mm3 at 1 mm (20.7 - 21.8 on the boards here)
    expected = 21.3 * S["fillet_size"] ** 2
    h.check(
        "Fillet: the four rounds took their share of material off",
        0.6 * expected < changed < 1.4 * expected,
        (changed, expected),
    )
    h.check("nothing in error", not r.errors(), r.errors())
    S["final"] = shape.Volume
    h.fit()
    h.shot("finished-board")


# -- File > Export, STL (Binary) ---------------------------------------------------------------
def export_dialog():
    from fission180 import export_ui

    d = export_ui.ExportDialog.last
    return d if d is not None and d.isVisible() else None


def export_open():
    import os

    folder = os.path.join(h.OUT_DIR, "replay_03_surfboard")
    os.makedirs(folder, exist_ok=True)
    for name in os.listdir(folder):
        os.remove(os.path.join(folder, name))
    S["export_dir"] = folder
    ins_file.record_exports()
    button = w.quick_access("Menu")
    h.pointer_to(button, button.rect().center())
    h.choose_from(button.click, ["File", "Export"], "the application menu")


export_open.done = lambda: export_dialog() is not None
export_open.done_what = "the Export dialog is open"


def export_stl():
    d = export_dialog()
    b.choose(d.type, "STL (Binary)")
    b.type_into(d.folder, S["export_dir"])
    b.type_into(d.name, "Finger Surfboard")


def export_go():
    b.click_widget(export_dialog().export_button)


export_go.done = lambda: export_dialog() is None
export_go.done_what = "the Export dialog is closed"
export_go.timeout_s = 120


def export_done():
    import os

    path = os.path.join(S["export_dir"], "Finger Surfboard.stl")
    h.check(
        "Export: Finger Surfboard.stl written", os.path.isfile(path), os.listdir(S["export_dir"])
    )
    if os.path.isfile(path):
        volume, _facets, _solid = ins_file.read_mesh_volume(path)
        h.check(
            "Export: the file holds the board's volume",
            abs(volume / S["final"] - 1.0) < 0.01,
            (volume, S["final"]),
        )
    titles = r.timeline()
    h.check(
        "the timeline: 4 planes, 7 sketches, the loft, 2 extrudes and the fillet",
        len(titles) >= 14,
        titles,
    )


STEPS_END = [fillet_open, fillet_edge_1, fillet_edge_2, fillet_hole_face, fillet_size, fillet_ok]
STEPS_END += [fillet_made, export_open, export_stl, export_go, export_done]


STEPS = [home, first_design, plus_tab]
for _n, (_d, _major, _minor, _up) in enumerate(SECTIONS):
    STEPS += section_steps(_n, _d, _major, _minor, _up)
STEPS += [loft_open, loft_pick(3), loft_pick(2), loft_pick(1), loft_pick(0), loft_origin]
STEPS += [loft_pointed, loft_made]
STEPS += [look_open, look_search, look_drop, look_edit, look_scale, look_ok, look_close]
STEPS += [canvas_open, canvas_face, canvas_scale, canvas_flip, canvas_ok, canvas_made]
STEPS += [fin_sketch, fin_plane, fin_intersect, fin_click_plane, fin_plane_line]
STEPS += [fin_click_board, fin_outline, fin_spline_points, fin_spline_enter, fin_spline_made]
STEPS += [fin_fix, fin_fixed, canvas_hide, canvas_hidden]
STEPS += STEPS_FIN + STEPS_HOLE + STEPS_END

h.run("replay_03_surfboard", STEPS, paced_by="state")
