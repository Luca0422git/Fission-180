# SPDX-License-Identifier: LGPL-2.1-or-later
"""Replay of the book, Project 1 "Classic Donut" (pp 22-29), step by step the way a person
follows it: wave 7's acceptance test (docs/fission180/dev/briefs/book-replay.md; the book
parity report lines 742-868). Real input only, a user's defaults (the layout grid, grid snap,
scale at first dimension), the book's grid (Fixed, 50 mm, 5 subdivisions: set in The Basics),
an undo step left open fails it.

  A  Home > New design; the book's grid; the project "Mastering Autodesk Fusion Edt. 2" with
     its folder "1 - Fundamentals" in the Data Panel (made in The Basics).
  B  Create Sketch, the Front plane's square: the view turns to FRONT, the SKETCH tab and
     the Sketch Palette show; the sketch's upright axis is blue (the world's Z), the level
     one red. C, a circle drawn by eye to the right of the origin and a little above the
     axis: with Snap its centre lands on a grid crossing, not on the axis. F6 frames the
     circle. One Ctrl+Z too many: still in the sketch; Ctrl+Y brings the circle back.
  C  Constraints > Horizontal/Vertical: the circle's centre, then the origin: level with it.
     D: the origin, the centre, a place, 40: the centre is 40 mm from the origin (the first
     dimension scales the sketch); D on the circle: 40 across. Fully constrained. Finish
     Sketch, the ViewCube's Home.
  D  CREATE > Revolve: the circle is taken by itself and the sketch stays on show; a click
     on the Z axis previews the donut; OK: a torus 120 x 120 x 40 of 2 pi^2 40 20^2 mm3,
     the body "Body1" under Bodies; the eye of Bodies hides and shows it.
  E  A (Appearance): In This Design lists the design's default look; the library has a Wood
     category with Oak (search "oak" finds it); Oak dragged onto the donut with the mouse:
     its grain shows. A double-click on Oak under In This Design: the editor, Scale 44 %.
  F  Create Sketch on the Front plane; CREATE > Spline > Fit Point Spline, six clicks across
     the donut, Enter: one curve, no control frame, no cloud of labels, the sketch solves.
     Constraints > Fix/Unfix, a click on the spline: fixed. Finish Sketch (it stays on show).
  G  MODIFY > Split Body: the donut, the spline, Extend Splitting Tool; OK: two bodies, the
     same volume together. The eye of the nested row Sketch 2 hides it.
  H  Create Sketch on the Top plane; C, three circles that overlap near the donut's outer
     edge; Esc. Ctrl + click on the second and third circle adds them to the selection (a
     plain click replaced it); Constraints > Fix/Unfix fixes the three. Finish Sketch.
  I  CREATE > Extrude: the five areas are picked one by one; Operation is Cut by itself;
     Direction Symmetric keeps Cut and shows Measurement; 20 and Enter: the bite is taken
     out of both halves.
  J  The pink icing: A, Apply To Faces... the book edits the top half's look: a double-click
     on the look, colour #FF6FB5 for the top half's body.
  K  Save (Ctrl+S): the Save dialog with its folders, the name "Classic Donut", the folder
     "1 - Fundamentals" clicked in the dialog's tree; Save: the file is there.

Out of scope here (brief): a rendered wood (Fission 180 shows a pattern, no reflections).
"""

import math
import os

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import bodies_steps as bs
from Fission180Tests.gui import book_sketch_b_steps as b
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import looks_steps as k
from Fission180Tests.gui import nav_input as nav
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import replay_a_steps as r
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st
from Fission180Tests.gui import timeline_input as t
from Fission180Tests.gui import versions_input as vi
from Fission180Tests.gui import viewcube_input as vc
from Fission180Tests.gui import widget_input as w
from Fission180Tests.gui import x_input as xi

V = App.Vector
s = r.s
PI = math.pi
TORUS = 2.0 * PI * PI * 40.0 * 20.0 * 20.0  # 315,827.3 mm3


def sk():
    return st.sketch()


def circles():
    return [g for g in sk().Geometry if g.TypeId == "Part::GeomCircle"]


def freedom():
    pal = si.palette()
    return pal.freedom.text() if pal is not None else ""


# == A: a new design, the book's grid, the project ============================================
def a_setup():
    root = r.project_folder("fission180-replay-01-")
    os.makedirs(os.path.join(root, r.BOOK, r.FUND))  # made in The Basics (replay_00_basics)


def a_grid():
    h.check("A a new design: the Home view", r.isometric(), r.direction())
    nav.choose("Grid and Snaps", "Grid Settings")


a_grid.done = lambda: r.grid_dialog() is not None
a_grid.done_what = "Grid Settings"


def a_fixed():
    d = r.grid_dialog()
    w.click(d.fixed, QtCore.QPoint(8, d.fixed.height() // 2))


def a_values():
    r.grid_values(50, 5)


a_values.done = lambda: r.grid_dialog() is None
a_values.done_what = "Grid Settings to close"


# == B: the first sketch =======================================================================
def b_create():
    from fission180 import grid_ui

    h.check("A the grid is the book's: 50 mm", abs(grid_ui.current_step(r.view()) - 50.0) < 1e-9)
    h.ribbon("Create Sketch")


b_create.done = lambda: pl.picker() is not None
b_create.done_what = "the origin's three squares"


def b_front():
    pl.click_square("XZ_Plane")


b_front.done = lambda: h.in_sketch() is not None
b_front.done_what = "the sketch on the Front plane"


def b_look():
    st.s["sk"] = h.in_sketch()
    h.view_still()
    h.check("B the ViewCube says FRONT", vc.looks_along((0, 1, 0)), vc.describe())
    h.check(
        "B the SKETCH tab shows", r.ribbon().current_tab() == "sketch", r.ribbon().current_tab()
    )
    pal = si.palette()
    h.check("B the Sketch Palette shows", pal is not None and pal.isVisible())
    rows = [x.text() for x in pal.findChildren(QtWidgets.QLabel) if x.text()]
    for row in (
        "Linetype",
        "Look At",
        "Sketch Grid",
        "Snap",
        "Slice",
        "Show Profile",
        "Show Points",
        "Show Dimensions",
        "Show Constraints",
        "Show Projected Geometries",
        "3D Sketch",
    ):
        h.check("B the palette has %s" % row, row in rows, rows)
    h.check("B ... and Finish Sketch", pal.finish.isVisible())
    h.check("B Snap is ticked", pal.boxes["snap"].isChecked(), list(pal.boxes))
    h.shot("B-front-sketch")


def b_axes():
    """The book: "a green vertical axis means your Z-up preference is wrong". A sketch on
    the Front plane shows the world's X (red) across and Z (blue) up (Fusion draws the
    origin's axes in their own colours in a sketch: Book)."""
    up = si.screen_colours(st.g(V(0, 37, 0)), 2)
    across = si.screen_colours(st.g(V(37, 0, 0)), 2)
    s["axis_up"], s["axis_across"] = up, across
    h.check("B the upright axis is not green", not r.greenish(up), up)
    h.check("B the upright axis is blue (the world's Z)", r.bluish(up), up)
    h.check("B the level axis is red (the world's X)", r.reddish(across), across)
    st.hover(V(0, 37, 0))
    lit = si.screen_colours(st.g(V(0, 25, 0)), 2)
    h.check(
        "B the mouse on the upright axis lights it up as before",
        not si.colour_near("#4d85fa", lit, 24),
        lit,
    )
    st.hover(V(40, 30, 0))
    again = si.screen_colours(st.g(V(0, 25, 0)), 2)
    h.check("B ... and off it, it is blue again", r.bluish(again), again)


def b_circle():
    h.press("c")


def b_centre():
    # by eye: to the right of the origin, a little above the axis (the report: 6-8 mm off)
    st.click(V(33, 8, 0))


def b_rim():
    st.click(V(48, 22, 0))


def b_drawn():
    st.esc()
    found = circles()
    if not h.check("B a circle is drawn", len(found) == 1, [g.TypeId for g in sk().Geometry]):
        return
    c = found[0]
    s["drawn"] = (c.Center.x, c.Center.y, c.Radius)
    # Fusion's Snap (on by default): a free point goes to the nearest crossing of the grid
    # lines, here every 10 mm (Lynda, Autodesk forum: docs/fission180/parity/sketch.md
    # "Wave 7, sketch-c"). The report's "Fusion would place them where clicked" is Snap off.
    h.check(
        "B Snap: the centre is on the grid crossing next to the click (30, 10)",
        st.vnear(c.Center, V(30, 10, 0), 1e-6),
        c.Center,
    )
    h.check("B ... not pulled onto the axis from 8 mm away", abs(c.Center.y) > 1.0, c.Center)
    h.check("B Esc ended the tool", st.tool() is None and not si.drawing(), st.tool_title())
    s["undo"] = r.doc().UndoCount
    cam = r.view().getCameraNode()
    cam.height.setValue(cam.height.getValue() * 12)  # (a person zoomed far out)
    h.press(QtCore.Qt.Key_F6)


def b_fit():
    c = circles()[0]
    a = h.screen_point(st.g(c.Center - V(c.Radius, 0, 0)))
    e = h.screen_point(st.g(c.Center + V(c.Radius, 0, 0)))
    wide = abs(e.x() - a.x())
    gl = h.gl_widget()
    h.check(
        "B F6 in the sketch frames the circle, not the grid",
        wide > 0.3 * min(gl.width(), gl.height()),
        (wide, gl.width(), gl.height()),
    )
    st.undo()


def b_undo():
    h.check("B Ctrl+Z took the circle away", not circles(), [g.TypeId for g in sk().Geometry])
    h.check("B ... the sketch is still open", h.in_sketch() is not None)
    st.undo()  # one too many


def b_undo_again():
    h.check("B one Ctrl+Z too many: still in the sketch", h.in_sketch() is not None)
    h.check("B ... the SKETCH tab still shows", r.ribbon().current_tab() == "sketch")
    h.check("B ... still looking from the FRONT", vc.looks_along((0, 1, 0)), vc.describe())
    st.redo()


def b_redo():
    found = circles() if h.in_sketch() is not None else []
    h.check("B Ctrl+Y: the circle is back, in the open sketch", len(found) == 1, found)
    if found:
        c = found[0]
        h.check("B ... as drawn", (c.Center.x, c.Center.y, c.Radius) == s["drawn"], s["drawn"])


# == C: constraints and dimensions =============================================================
def editor():
    return st.session().editor


def cons(kind):
    return [c for c in sk().Constraints if c.Type == kind]


def c_hv():
    b.watch_modals()
    b.menu("Horizontal/Vertical")


def c_hv_centre():
    h.check("C Horizontal/Vertical runs", st.tool_title() == "Horizontal/Vertical", st.tool_title())
    st.click(circles()[0].Center)


def c_hv_origin():
    st.click(V(0, 0, 0))


def c_hv_check():
    c = circles()[0]
    h.check("C the centre is level with the origin", abs(c.Center.y) < 1e-6, c.Center)
    h.check("C ... by one Horizontal constraint", len(cons("Horizontal")) == 1, b.cons())
    h.check("C ... the centre stayed 30 mm out", abs(c.Center.x - 30.0) < 1e-6, c.Center)
    s["radius"] = c.Radius
    st.esc()
    h.press("d")


def c_d_origin():
    h.check("C D starts Sketch Dimension", st.tool_title() == "Sketch Dimension", st.tool_title())
    st.click(V(0, 0, 0))


def c_d_centre():
    st.click(circles()[0].Center)


def c_d_place():
    st.click(V(15, -14, 0))


c_d_place.done = lambda: editor() is not None
c_d_place.done_what = "the dimension's value box"


def c_d_type():
    h.check("C the value box is open at the dimension", editor().just_placed)
    si.type_text("40")


c_d_type.done = lambda: editor() is None
c_d_type.done_what = "Enter to take the value"


def c_d_check():
    c = circles()[0]
    h.check(
        "C 40, Enter: the centre is 40 mm from the origin",
        st.vnear(c.Center, V(40, 0, 0)),
        c.Center,
    )
    # Fusion's "Scale entire sketch at first dimension" (on by default): the circle drawn
    # by eye grows with it, by 40 / 30
    h.check(
        "C the first dimension scaled the sketch: the circle grew by 4 / 3",
        abs(c.Radius - s["radius"] * 4.0 / 3.0) < 1e-6,
        (c.Radius, s["radius"]),
    )
    h.check("C not yet fully constrained", freedom() != "Fully constrained", freedom())
    rim = c.Center + V(math.cos(2.3), math.sin(2.3), 0) * c.Radius
    st.click(rim)  # (the Dimension tool is still on)


def c_dia_place():
    c = circles()[0]
    st.click(c.Center + V(-1, 1, 0) * (c.Radius * 0.75 + 12))


c_dia_place.done = lambda: editor() is not None
c_dia_place.done_what = "the diameter's value box"


def c_dia_type():
    si.type_text("40")


c_dia_type.done = lambda: editor() is None


def c_done():
    st.esc()
    c = circles()[0]
    h.check("C the circle is 40 across", abs(c.Radius - 20.0) < 1e-6, c.Radius)
    h.check("C ... a diameter dimension", len(cons("Diameter")) == 1, b.cons())
    h.check("C its centre still 40 out, on the axis", st.vnear(c.Center, V(40, 0, 0)), c.Center)
    r.fully_constrained("C", freedom)
    st.sketch_ok("C")
    b.no_modal("C the first sketch")
    h.shot("C-circle")
    h.ribbon("Finish Sketch")


c_done.done = lambda: h.in_sketch() is None
c_done.done_what = "the sketch to close"


def c_home():
    vc.hover("front")
    vc.click("home")


c_home.done = r.isometric
c_home.done_what = "the Home view"


# == D: Revolve ================================================================================
def revolve_panel():
    from Fission180Tests.gui import revolve_input as ri

    return ri.panel()


def d_revolve():
    vc.move_away()
    Gui.Selection.clearSelection()
    si.menu_item("CREATE", "Revolve")


d_revolve.done = lambda: revolve_panel() is not None
d_revolve.done_what = "the Revolve dialog"


def d_axis():
    p = revolve_panel()
    sketch = r.doc().getObject("Sketch")
    h.check("D the circle is taken by itself", len(p.profiles) == 1, p.profiles)
    h.check("D the Axis box waits for a click", p.active == "axis" and p.axis is None, p.active)
    h.check("D the sketch stays on show while the axis is picked", sketch.ViewObject.Visibility)
    kinds = sorted(l[1] for l in p.axes.lines if l[1] != "construction")
    h.check("D the origin's axes are there to click", kinds == ["X", "Y", "Z"], kinds)
    pl.click_on_plane(V(0, 0, 45))


d_axis.done = lambda: revolve_panel().axis is not None
d_axis.done_what = "the Z axis to be picked"


def d_preview():
    p = revolve_panel()
    h.caught_up(p)
    h.check("D the Z axis is picked", p.axis[0].Role == "Z_Axis", p.axis)
    h.check("D the preview is the donut", r.rel(r.volume(), TORUS), (r.volume(), TORUS))
    h.check("D an angle handle with its value box", "angle" in p.handles, list(p.handles))
    h.check("D Operation: New Body", p.operation.currentText() == "New Body")
    h.task_button("OK")


d_preview.done = r.no_panel
d_preview.done_what = "Revolve to finish"


def d_done():
    found = r.solids()
    h.check("D one body", len(found) == 1, [x.Label for x in found])
    h.check("D its volume is 2 pi^2 40 20^2", r.rel(r.volume(), TORUS, 1e-6), (r.volume(), TORUS))
    h.check("D it is 120 x 120 x 40", r.box_size() == (120.0, 120.0, 40.0), r.box_size())
    h.check("D the body is called Body1", found[0].Label == "Body1", found[0].Label)
    kinds = [f.Surface.TypeId for f in found[0].Shape.Faces]
    h.check("D the donut is one round face", kinds == ["Part::GeomToroid"], kinds)
    labels = r.labels()
    h.check("D the browser shows Bodies > Body1", "Bodies" in labels and r.has_row("Body1"), labels)
    titles = t.titles()
    h.check("D the timeline: Sketch 1, Revolve 1", titles == ["Sketch 1", "Revolve 1"], titles)
    h.shot("D-donut")
    t.click_eye("Bodies")


def d_hidden():
    from Fission180Tests.gui import revolve_input as ri

    h.check("D the eye of Bodies hides the donut", not ri.shown(r.solids()[0]))
    t.click_eye("Bodies")


def d_shown():
    from Fission180Tests.gui import revolve_input as ri

    h.check("D ... and shows it again", ri.shown(r.solids()[0]))
    h.press(QtCore.Qt.Key_F6)


def d_fit():
    gl = h.gl_widget()
    a, e = h.screen_point(V(-60, 0, 0)), h.screen_point(V(60, 0, 0))
    wide = math.hypot(a.x() - e.x(), a.y() - e.y())
    h.check("D F6 frames the donut", 0.25 * gl.width() < wide < gl.width(), (wide, gl.width()))


# == E: Appearance =============================================================================
ON_DONUT = V(0, -40, 20)  # the top of the tube, on the side that faces the Home view


def donut():
    return r.solids()[0]


def e_open():
    h.click_empty()
    s["flat"] = k.roughness(ON_DONUT)
    h.press("a")


e_open.done = lambda: k.panel() is not None
e_open.done_what = "the Appearance dialog (A)"


def e_look():
    p = k.panel()
    labels = k.design_labels()
    h.check("E In This Design lists the design's default look", len(labels) == 1, labels)
    h.check("E ... a steel, as Fusion's Steel - Satin", "Steel" in labels[0], labels)
    categories = [p.category.itemText(i) for i in range(p.category.count())]
    h.check("E the library has a Wood category", "Wood" in categories, categories)
    h.check("E ... and a search box", p.search.isVisible())
    w.click(p.search)
    w.type_text(p.search, "oak")


def e_found():
    names = k.library_labels()
    h.check("E the search finds Oak", "Oak" in names, names)
    h.check("E ... and only oak looks", all("oak" in n.lower() for n in names), names)
    r.drag_look("Oak", ON_DONUT)


e_found.done = r.drag_done
e_found.done_what = "the drag of Oak onto the donut"
e_found.while_busy = True


def e_oak():
    h.check("E the drag ran", not r._drag["error"], r._drag["error"])
    h.settle()
    r.keys_to_window()  # (no window manager under xvfb: nothing is active after a drag)
    data = k.stored(donut())["body"] or {}
    h.check(
        "E Oak dragged onto the donut with the mouse: the donut is Oak",
        data.get("key") == "wood_oak",
        data,
    )
    h.check("E Oak has a grain", data.get("texture") == "wood_oak", data.get("texture"))
    h.check("E In This Design lists Oak", "Oak" in k.design_labels(), k.design_labels())
    vc.move_away()
    h.click_empty()
    rough = k.roughness(ON_DONUT)
    h.check("E the grain shows on the screen", rough > 2.0 * s["flat"], (rough, s["flat"]))
    h.shot("E-oak")
    k.double_click_design("Oak")


e_oak.done = lambda: k.editor() is not None
e_oak.done_what = "the look's editor (a double-click under In This Design)"


def e_scale():
    e = k.editor()
    h.check("E the editor shows the look's name", e.name.text() == "Oak", e.name.text())
    h.check("E it has a Scale", e.scale.isVisible())
    s["uvs"] = k.pattern_uvs(donut().Tip)[:40]
    k.type_field(e.scale, "44")


def e_scaled():
    e = k.editor()
    data = k.stored(donut())["body"] or {}
    h.check("E Scale 44 %: the look keeps it", abs(float(data.get("scale", 0)) - 44.0) < 1e-6, data)
    h.check("E ... and the grain on the donut follows", k.pattern_uvs(donut().Tip)[:40] != s["uvs"])
    w.click(e.ok_button)


e_scaled.done = lambda: k.editor() is None
e_scaled.done_what = "the editor to close"


def e_close():
    h.task_button("OK")


e_close.done = r.no_panel
e_close.done_what = "Appearance to close"


def e_closed():
    data = k.stored(donut())["body"] or {}
    h.check("E after OK the donut is still Oak at 44 %", data.get("key") == "wood_oak", data)
    h.check("E no error on the way", True)


# == F: the spline =============================================================================
SPLINE = (V(-72, 8, 0), V(-44, -7, 0), V(-17, 8, 0), V(13, -7, 0), V(42, 8, 0), V(71, -6, 0))


def sketches():
    return [o for o in r.doc().Objects if o.TypeId == "Sketcher::SketchObject"]


def splines():
    return [i for i, g in enumerate(sk().Geometry) if g.TypeId == "Part::GeomBSplineCurve"]


def f_create():
    h.click_empty()
    h.ribbon("Create Sketch")


f_create.done = lambda: pl.picker() is not None
f_create.done_what = "the origin's three squares"


def f_front():
    pl.click_square("XZ_Plane")


f_front.done = lambda: h.in_sketch() is not None
f_front.done_what = "the second sketch, on the Front plane"


def f_spline():
    st.s["sk"] = h.in_sketch()
    h.view_still()
    h.check("F the view looks from the FRONT", vc.looks_along((0, 1, 0)), vc.describe())
    b.watch_modals()
    si.menu_item("CREATE", "Fit Point Spline")


def f_points():
    for point in SPLINE:
        st.click(point)


def f_enter():
    st.enter()


def along(curve, share):
    return curve.value(curve.parameterAtDistance(curve.length() * share, curve.FirstParameter))


def f_drawn():
    from fission180 import sketch_draw_helpers as sketch_helpers

    found = splines()
    if not h.check("F Enter finished one spline", len(found) == 1, len(sk().Geometry)):
        return
    curve = sk().Geometry[found[0]]
    s["spline"] = found[0]
    ys = [along(curve, f).y for f in (0.1, 0.3, 0.5, 0.7, 0.9)]
    h.check("F it waves above and below the axis (not flat on it)", max(ys) > 3 > -3 > min(ys), ys)
    for want, have in ((SPLINE[0], curve.StartPoint), (SPLINE[-1], curve.EndPoint)):
        # (Snap: a spline's point goes to a grid line it is close to)
        h.check("F it ends where it was clicked", (want - have).Length < 5.1, (want, have))
    roles = sketch_helpers.aligned_to(sk(), found[0])
    hidden = sketch_helpers.hidden(sk())
    poles = roles.get("BSplineControlPoint", [])
    h.check(
        "F only the curve shows: its control circles are hidden", poles and set(poles) <= hidden
    )
    labels = [
        c.Type for c in sk().Constraints if c.Type in ("Equal", "Weight") and not c.InVirtualSpace
    ]
    h.check("F ... no cloud of equality labels", labels == [], labels)
    h.check("F ... no control frame", st.session().frames.drawn == [], st.session().frames.drawn)
    st.sketch_ok("F the spline")
    st.esc()


def f_kept():
    h.check("F the spline is still there after Esc", len(splines()) == 1)
    h.check("F Esc left the sketch open", h.in_sketch() is not None)
    Gui.Selection.clearSelection()
    b.menu("Fix/Unfix")


def f_fix():
    h.check("F Fix/Unfix waits for a click", st.tool_title() == "Fix/Unfix", st.tool_title())
    st.click(along(sk().Geometry[s["spline"]], 0.42))


def f_fixed():
    h.check("F a click on the spline fixes it", b.has("Block", s["spline"]), b.cons())
    r.fully_constrained("F", freedom)
    st.esc()
    b.no_modal("F the spline sketch")
    h.shot("F-spline")
    h.ribbon("Finish Sketch")


f_fixed.done = lambda: h.in_sketch() is None
f_fixed.done_what = "the sketch to close"


def f_home():
    vc.hover("front")
    vc.click("home")


f_home.done = r.isometric


# == G: Split Body =============================================================================
def g_split():
    vc.move_away()
    sketch = sketches()[-1]
    s["sketch2"] = sketch
    h.check("G the spline's sketch stays on show after Finish Sketch", bs.shown(sketch))
    h.click_empty()
    si.menu_item("MODIFY", "Split Body")


g_split.done = lambda: r.panel() is not None and getattr(r.panel(), "title", "") == "Split Body"
g_split.done_what = "the Split Body dialog"


def g_body():
    p = r.panel()
    h.check("G Body to Split waits for a click", p.active == "body", p.active)
    h.click(ON_DONUT)


def g_tool():
    p = r.panel()
    h.check("G the donut is the body to split", p.options["body"] is donut(), p.options)
    h.check("G Splitting Tool(s) waits", p.active == "tool", p.active)
    # where the spline sticks out of the donut, at its left end
    on = along(s["sketch2"].Geometry[s["spline"]], 0.035)
    h.click_edge(s["sketch2"].getGlobalPlacement().multVec(on))


def g_extend():
    p = r.panel()
    tool = p.options["tool"]
    h.check(
        "G the spline is the splitting tool", tool is not None and tool[0] is s["sketch2"], tool
    )
    if not p.extend.isChecked():
        bs.toggle(p.extend)


def g_ok():
    p = r.panel()
    h.caught_up(p)
    h.check("G Extend Splitting Tool is ticked", p.extend.isChecked())
    h.check("G no complaint in the dialog", p.message.text() == "", p.message.text())
    h.check("G the preview shows two bodies", len(r.solids()) == 2, [x.Label for x in r.solids()])
    h.task_button("OK")


g_ok.done = r.no_panel
g_ok.done_what = "Split Body to finish"


def top_and_bottom():
    found = sorted(r.solids(), key=lambda x: r.centre(x).z)
    return found[-1], found[0]


def g_done():
    found = r.solids()
    if not h.check("G two bodies", len(found) == 2, [x.Label for x in found]):
        return
    volumes = sorted(x.Shape.Volume for x in found)
    # (1e-5: the split's two volumes add up to the torus within OpenCASCADE's own
    # integration noise, which differs between builds: 1.2e-6 on GitHub's runner, CI #76;
    # the golden models allow 2e-5 on curved solids)
    h.check("G together they are the donut", r.rel(sum(volumes), TORUS, 1e-5), volumes)
    h.check("G two halves of about the same size", volumes[0] > 0.4 * TORUS, volumes)
    top, bottom = top_and_bottom()
    h.check(
        "G one above the other",
        r.centre(top).z > 2 and r.centre(bottom).z < -2,
        (r.centre(top), r.centre(bottom)),
    )
    names = sorted(x.Label for x in found)
    h.check("G they are called Body1 and Body2", names == ["Body1", "Body2"], names)
    for body in found:
        look = k.stored(body)["body"] or {}
        h.check("G %s is still Oak" % body.Label, look.get("key") == "wood_oak", look)
    titles = t.titles()
    h.check("G the timeline ends with the split", titles[-1].startswith("Split Body"), titles)
    h.shot("G-split")
    s["torus_halves"] = {x.Name: x.Shape.copy() for x in found}
    t.click_eye("Sketch 2")


def g_eye():
    h.check("G the eye of the nested row Sketch 2 hides it", not bs.shown(s["sketch2"]))


# == H: the three circles ======================================================================
CIRCLES = (
    (V(60, -20, 0), V(70, -10, 0)),
    (V(70, 0, 0), V(80, 10, 0)),
    (V(60, 20, 0), V(70, 30, 0)),
)
RADIUS = math.sqrt(200.0)


def h_create():
    h.click_empty()
    h.ribbon("Create Sketch")


h_create.done = lambda: pl.picker() is not None
h_create.done_what = "the origin's three squares"


def h_top():
    pl.click_square("XY_Plane")


h_top.done = lambda: h.in_sketch() is not None
h_top.done_what = "the third sketch, on the Top plane"


def h_circle_tool():
    st.s["sk"] = h.in_sketch()
    h.view_still()
    h.check("H the view looks from the TOP", vc.looks_along((0, 0, -1)), vc.describe())
    b.watch_modals()
    h.press("c")


def circle_steps():
    steps = []
    for i, (centre, rim) in enumerate(CIRCLES):
        # by eye: a millimetre or two off the grid crossings Snap puts them on
        def click_centre(centre=centre):
            st.click(centre + V(1.5, -1.0, 0))

        def click_rim(rim=rim):
            st.click(rim + V(-1.0, 1.5, 0))

        click_centre.__name__ = "h_centre_%d" % (i + 1)
        click_rim.__name__ = "h_rim_%d" % (i + 1)
        steps += [click_centre, click_rim]
    return steps


def h_drawn():
    st.esc()
    found = circles()
    if not h.check("H three circles", len(found) == 3, [g.TypeId for g in sk().Geometry]):
        return
    for circle, (centre, _rim) in zip(found, CIRCLES):
        h.check(
            "H a circle at (%g, %g), on the grid" % (centre.x, centre.y),
            st.vnear(circle.Center, centre, 1e-6) and abs(circle.Radius - RADIUS) < 1e-6,
            (circle.Center, circle.Radius),
        )
    h.check("H Esc ended the tool", st.tool() is None and not si.drawing())
    st.sketch_ok("H the circles")
    c = found[0]
    xi.click(h.screen_point(st.g(c.Center + V(-RADIUS, 0, 0))))


def selected_edges():
    found = set()
    for sel in Gui.Selection.getSelectionEx():
        for name in sel.SubElementNames:
            found.add(name.rsplit(".", 1)[-1])
    return found


def h_ctrl_second():
    h.settle()
    h.check("H a click selects the first circle", selected_edges() == {"Edge1"}, selected_edges())
    c = circles()[1]
    xi.click(h.screen_point(st.g(c.Center + V(RADIUS, 0, 0))), held=("ctrl",))


def h_ctrl_third():
    h.settle()
    h.check(
        "H Ctrl + click adds the second", selected_edges() == {"Edge1", "Edge2"}, selected_edges()
    )
    c = circles()[2]
    xi.click(h.screen_point(st.g(c.Center + V(-RADIUS, 0, 0))), held=("ctrl",))


def h_fix():
    h.settle()
    h.check(
        "H Ctrl + click adds the third",
        selected_edges() == {"Edge1", "Edge2", "Edge3"},
        selected_edges(),
    )
    b.menu("Fix/Unfix")


def h_fixed():
    blocked = sorted(c.First for c in sk().Constraints if c.Type == "Block")
    h.check("H Fix/Unfix fixes the three circles", blocked == [0, 1, 2], b.cons())
    r.fully_constrained("H", freedom)
    st.esc()
    b.no_modal("H the circles' sketch")
    h.shot("H-circles")
    h.ribbon("Finish Sketch")


h_fixed.done = lambda: h.in_sketch() is None
h_fixed.done_what = "the sketch to close"


def h_home():
    vc.hover("front")
    vc.click("home")


h_home.done = r.isometric


# == I: the bite ===============================================================================
def extrude_panel():
    from fission180 import extrude_ui

    p = extrude_ui.ExtrudePanel.last
    return p if p is not None and not p._closed else None


def bite_regions():
    """A point inside each of the five areas of the circles' sketch."""
    a, mid, c = (g for g in s["sketch3"].Geometry if g.TypeId == "Part::GeomCircle")
    away_a = a.Center + (a.Center - mid.Center).normalize() * (RADIUS * 0.5)
    away_c = c.Center + (c.Center - mid.Center).normalize() * (RADIUS * 0.5)
    return [
        away_a,
        (a.Center + mid.Center) * 0.5,
        mid.Center + V(RADIUS * 0.5, 0, 0),
        (mid.Center + c.Center) * 0.5,
        away_c,
    ]


def i_extrude():
    vc.move_away()
    s["sketch3"] = sketches()[-1]
    h.check("I the circles' sketch is on show", bs.shown(s["sketch3"]))
    h.click_empty()
    si.menu_item("CREATE", "Extrude")


i_extrude.done = lambda: extrude_panel() is not None
i_extrude.done_what = "the Extrude dialog"


def region_steps():
    steps = []
    for i in range(5):

        def pick(i=i):
            p = extrude_panel()
            if i == 0:
                h.check("I nothing is picked by itself (five areas to choose from)", not p.profiles)
            point = bite_regions()[i]
            h.click(s["sketch3"].getGlobalPlacement().multVec(point))
            h.settle()
            h.check("I a click picks area %d" % (i + 1), len(p.profiles) == i + 1, len(p.profiles))

        pick.__name__ = "i_pick_%d" % (i + 1)
        steps.append(pick)
    return steps


def i_symmetric():
    from Fission180Tests.gui import dialog_input as di

    p = extrude_panel()
    h.caught_up(p)
    text = p.fields["profiles"].button.text()
    h.check("I the dialog counts 5 profiles", len(p.profiles) == 5, text)
    h.check("I Operation is Cut by itself", p.operation.currentText() == "Cut")
    directions = [p.direction.itemText(i) for i in range(p.direction.count())]
    h.check("I Direction has Symmetric", "Symmetric" in directions, directions)
    di.choose(p.direction, "Symmetric")


def i_distance():
    p = extrude_panel()
    h.caught_up(p)
    h.check("I Symmetric keeps Cut", p.operation.currentText() == "Cut", p.operation.currentText())
    h.check("I Symmetric shows Measurement", p.measurement.isVisible())
    kinds = [p.measurement.itemText(i) for i in range(p.measurement.count())]
    h.check("I ... Half Length / Whole Length", kinds == ["Half Length", "Whole Length"], kinds)
    h.check("I ... Half Length to start with", p.measurement.currentText() == "Half Length")
    field = p.distance.widget
    QtTest.QTest.mouseClick(field, QtCore.Qt.LeftButton)
    QtTest.QTest.keyClick(field, QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
    QtTest.QTest.keyClicks(field, "20")
    QtTest.QTest.keyClick(field, QtCore.Qt.Key_Return)


i_distance.done = lambda: extrude_panel() is None
i_distance.done_what = "Enter in the Distance box to finish the extrude"
i_distance.timeout_s = 120


def i_done():
    import Part

    found = r.solids()
    h.check("I still two bodies (a bite, nothing joined on)", len(found) == 2, len(found))
    cutters = [
        Part.makeCylinder(RADIUS, 40.0, V(c.x, c.y, -20.0), V(0, 0, 1)) for c, _rim in CIRCLES
    ]
    tool = cutters[0].fuse(cutters[1:])
    total = 0.0
    for body in found:
        before = s["torus_halves"][body.Name]
        want = before.cut(tool).Volume
        total += want
        h.check(
            "I the bite is taken out of %s" % body.Label,
            r.rel(body.Shape.Volume, want, 1e-5) and want < before.Volume - 100.0,
            (body.Shape.Volume, want, before.Volume),
        )
    h.check("I together: the donut less the bite", r.rel(r.volume(), total, 1e-5), r.volume())
    h.check("I the donut is no higher", r.box_size()[2] == 40.0, r.box_size())
    pieces = [len(x.Shape.Solids) for x in found]
    h.check("I each half is still one piece", pieces == [1, 1], pieces)
    titles = t.titles()
    h.check("I the timeline ends with the extrude", titles[-1].startswith("Extrude"), titles)
    for body in found:
        look = k.stored(body)["body"] or {}
        h.check("I %s is still Oak" % body.Label, look.get("key") == "wood_oak", look)
    h.shot("I-bite")


# == J: the pink icing =========================================================================
PINK = (1.0, 0x6F / 255.0, 0xB5 / 255.0)
ON_BOTTOM = V(39.6, -39.6, -12)  # the lower half's outer wall, facing the Home view


def default_label():
    return [x for x in k.design_labels() if "default" in x][0]


def j_open():
    vc.move_away()
    h.click_empty()
    h.press("a")


j_open.done = lambda: k.panel() is not None
j_open.done_what = "the Appearance dialog (A)"


def j_drag_default():
    labels = k.design_labels()
    h.check("J In This Design lists the default look and Oak", len(labels) == 2, labels)
    # The book: the plain look of In This Design (Fusion's Steel - Satin) goes onto the top
    # half, then its colour is edited to pink.
    r.drag_look(default_label(), ON_DONUT, from_design=True)


j_drag_default.done = r.drag_done
j_drag_default.done_what = "the drag of the default look onto the top half"
j_drag_default.while_busy = True


def j_edit():
    h.settle()
    r.keys_to_window()  # (no window manager under xvfb: nothing is active after a drag)
    top, bottom = top_and_bottom()
    look = k.body_look_label(top)
    h.check("J the top half has the plain look now", look == default_label(), look)
    h.check("J the bottom half is still Oak", k.body_look_label(bottom) == "Oak")
    k.double_click_design(default_label())


j_edit.done = lambda: k.editor() is not None
j_edit.done_what = "the look's editor (a double-click)"


def j_pink():
    e = k.editor()
    k.type_field(e.hex, "#FF6FB5", QtCore.Qt.Key_Return)


def j_pinked():
    e = k.editor()
    h.check("J Enter in the colour box keeps the editor open", e is not None)
    top, _bottom = top_and_bottom()
    shown = k.shown_colors(top.Tip)
    h.check("J the top half turns pink at once", shown and k.same(shown[0], PINK), shown[:2])
    w.click(e.ok_button)


j_pinked.done = lambda: k.editor() is None
j_pinked.done_what = "the editor to close"


def j_ok():
    h.task_button("OK")


j_ok.done = r.no_panel
j_ok.done_what = "Appearance to close"


def j_done():
    vc.move_away()
    h.click_empty()
    top, bottom = top_and_bottom()
    rgb = k.screen_rgb(ON_DONUT)
    h.check("J the icing is pink on the screen", k.hue_like(rgb, PINK, 0.12), rgb)
    rgb = k.screen_rgb(ON_BOTTOM)
    h.check("J the lower half is not", not k.hue_like(rgb, PINK, 0.08), rgb)
    look = k.stored(bottom)["body"] or {}
    h.check(
        "J ... it is still Oak at 44 %", look.get("key") == "wood_oak" and look.get("scale") == 44
    )
    groups, triangles = k.pattern_drawn(bottom.Tip)
    h.check("J ... with its grain drawn", groups == 1 and triangles > 50, (groups, triangles))
    groups, _triangles = k.pattern_drawn(top.Tip)
    h.check("J no grain on the icing", groups == 0, groups)
    h.shot("J-icing")


# == K: Save ===================================================================================
def k_save():
    r.keys_to_window()  # (the look editor's window closed: no window manager under xvfb)
    h.press("s", QtCore.Qt.ControlModifier)


k_save.done = lambda: vi.save_dialog() is not None
k_save.done_what = "the Save dialog (Ctrl+S)"


def tree_item(d, *names):
    item = d.tree.topLevelItem(0)
    for name in names:
        found = None
        for i in range(item.childCount()):
            if item.child(i).text(0) == name:
                found = item.child(i)
        if found is None:
            return None
        item = found
    return item


def k_dialog():
    d = vi.save_dialog()
    h.check("K the dialog has a Name and a Location", d.location.isVisible())
    h.check("K the folders are shown in the dialog", d.tree.isVisible())
    blank = h.blank_buttons(d)
    h.check("K every button of it paints (the ...)", not blank, blank)
    project = tree_item(d, r.BOOK)
    if not h.check("K the project is in the tree", project is not None):
        return
    if not project.isExpanded():  # a double-click opens a folder of the tree
        w.double_click(d.tree.viewport(), d.tree.visualItemRect(project).center())


k_dialog.done = (
    lambda: tree_item(vi.save_dialog(), r.BOOK, r.FUND) is not None
    and tree_item(vi.save_dialog(), r.BOOK).isExpanded()
)
k_dialog.done_what = "1 - Fundamentals to show in the tree"


def k_folder():
    d = vi.save_dialog()
    item = tree_item(d, r.BOOK, r.FUND)
    w.click(d.tree.viewport(), d.tree.visualItemRect(item).center())


def k_name():
    d = vi.save_dialog()
    fund = os.path.join(s["root"], r.BOOK, r.FUND)
    h.check(
        "K a click on the folder sets the Location", d.location.text() == fund, d.location.text()
    )
    vi.fill_save_dialog(name="Classic Donut")
    h.shot("K-save")
    vi.click_save()


k_name.done = lambda: vi.save_dialog() is None and os.path.isfile(
    os.path.join(s["root"], r.BOOK, r.FUND, "Classic Donut.FCStd")
)
k_name.done_what = "the design to be saved in 1 - Fundamentals"
k_name.timeout_s = 120


def k_saved():
    d = r.doc()
    fund = os.path.join(s["root"], r.BOOK, r.FUND)
    h.check("K the design is in 1 - Fundamentals", d.FileName.startswith(fund), d.FileName)
    tabs = h.document_tabs()
    texts = [tabs.tabText(i) for i in range(tabs.count())]
    h.check("K its tab says Classic Donut", any("Classic Donut" in x for x in texts), texts)
    h.check("K two bodies, as modelled", len(r.solids()) == 2)
    titles = t.titles()
    kinds = [x.rstrip("0123456789 ") for x in titles]
    h.check(
        "K the timeline is the book's",
        kinds == ["Sketch", "Revolve", "Sketch", "Split Body", "Sketch", "Extrude"],
        titles,
    )
    h.shot("K-end")


h.run(
    "replay_01_donut",
    [
        r.start,
        a_setup,
        r.new_design,
        a_grid,
        a_fixed,
        a_values,
        b_create,
        b_front,
        b_look,
        b_axes,
        b_circle,
        b_centre,
        b_rim,
        b_drawn,
        b_fit,
        b_undo,
        b_undo_again,
        b_redo,
        c_hv,
        c_hv_centre,
        c_hv_origin,
        c_hv_check,
        c_d_origin,
        c_d_centre,
        c_d_place,
        c_d_type,
        c_d_check,
        c_dia_place,
        c_dia_type,
        c_done,
        c_home,
        d_revolve,
        d_axis,
        d_preview,
        d_done,
        d_hidden,
        d_shown,
        d_fit,
        e_open,
        e_look,
        e_found,
        e_oak,
        e_scale,
        e_scaled,
        e_close,
        e_closed,
        f_create,
        f_front,
        f_spline,
        f_points,
        f_enter,
        f_drawn,
        f_kept,
        f_fix,
        f_fixed,
        f_home,
        g_split,
        g_body,
        g_tool,
        g_extend,
        g_ok,
        g_done,
        g_eye,
        h_create,
        h_top,
        h_circle_tool,
    ]
    + circle_steps()
    + [
        h_drawn,
        h_ctrl_second,
        h_ctrl_third,
        h_fix,
        h_fixed,
        h_home,
        i_extrude,
    ]
    + region_steps()
    + [
        i_symmetric,
        i_distance,
        i_done,
        j_open,
        j_drag_default,
        j_edit,
        j_pink,
        j_pinked,
        j_ok,
        j_done,
        k_save,
        k_dialog,
        k_folder,
        k_name,
        k_saved,
    ],
    paced_by="state",
)
