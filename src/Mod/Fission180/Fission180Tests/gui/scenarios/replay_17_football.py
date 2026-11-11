# SPDX-License-Identifier: LGPL-2.1-or-later
"""Replay of the book's Project 17 "American Football" (chapter 7, pp 210 - 217), the way a
person follows it. Report lines 2423 - 2461. Real input only, a user's defaults.

The book's picture (a CADclass download) cannot be reached: the stand-in is the canvas
fixture (two dots 60 pixels apart), calibrated so that the dots are the ball's tips.

  A  Home > New Design; the browser's Units row > Change Active Units: Inch (the book's
     ball is 11.25 in long).
  B  INSERT > Canvas, the Front plane, Z Angle 1, OK. Right-click the canvas > Calibrate:
     the two tips clicked, 11.25 typed: the tips are 285.75 mm apart.
  C  Create Sketch on the Front plane. L, the origin, 11.25 Tab 0 Enter: the ball's axis.
     X (construction), L, the line's middle, 3.4 Tab 90 Enter: the half-height. CREATE >
     Fit Point Spline from the axis' end through two points to the half-height's top,
     Enter. CREATE > Mirror: the spline, Mirror Line the construction line, OK.
     CONSTRAINTS > Tangent, the two splines: smooth where they meet (the report: "added
     nothing (no message)").
  D  Revolve: the profile, the X axis, Angle 90: a quarter ball.
  E  Fillet 1/8 on its two curved edges (Tangent Chain takes each spline's mirror too).
  F  CREATE > Circular Pattern, Pattern Type Bodies, the quarter, the X axis, Quantity 4.
  G  MODIFY > Combine: Target the quarter, the three copies as tools: one body.
  H  Navigation bar > Display Settings > Visual Style: Shaded with Visible Edges Only, then
     Shaded again.
  I  Appearance: Leather, brown dropped on the ball; its look under In This Design
     right-click > Duplicate; the copy double-clicked: renamed "Football leather", Scale
     50 %, Advanced opened, OK; the copy dropped on the ball.
  J  INSERT > Decal: the picture, a click on the ball's curved side, Chain Faces, Opacity
     80; a right-click on a browser row keeps the dialog (the report: "cancels the Decal
     dialog"); OK: in the Decals folder.
  K  At the end: one body, nothing broken, no undo step left open.

Skipped as out of scope: the Render workspace (report 2451). Not replayed: the laces (Sketch
Offset, Sweep, Pattern on Path: "not re-tested" in the report; those tools are replayed in
the Carabiner and Hot End scenarios).
"""

import math

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import book_components_steps as k
from Fission180Tests.gui import book_sketch_b_steps as bb
from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import insert_steps as ins
from Fission180Tests.gui import looks_steps as lk
from Fission180Tests.gui import pattern_steps as ps
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import replay_g_steps as r
from Fission180Tests.gui import revolve_input as ri
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import sketch_tools_steps as st
from Fission180Tests.gui import timeline_input as t

V = App.Vector
S = {}
IN = 25.4
LENGTH = 11.25 * IN
HALF = 3.4 * IN
MID = V(LENGTH / 2.0, 0, 0)


def doc():
    return App.ActiveDocument


def solids():
    from fission180 import bodies

    return [x for x in doc().Objects if bodies.is_body(x) and bodies.has_solid(x)]


# -- A: inches --------------------------------------------------------------------------------
def a_units():
    t.click_row("Units: mm")


def units_panel():
    from fission180 import browser_ui

    p = browser_ui.UnitsPanel.last
    return p if p is not None and not p._closed else None


a_units.done = lambda: units_panel() is not None
a_units.done_what = "Change Active Units is open"


def a_inch():
    combo = units_panel().form.findChild(QtWidgets.QComboBox, "Fission180UnitType")
    ui.choose(combo, "Inch")
    h.task_button("OK")


a_inch.done = lambda: units_panel() is None
a_inch.done_what = "Change Active Units closed"


def a_inched():
    h.check("A the design is in inches", "Units: in" in t.labels(), t.labels()[:6])


# -- B: canvas and calibrate ------------------------------------------------------------------
def canvas():
    found = ins.canvases()
    return found[0] if found else None


def b_canvas():
    ins.use_file(ins.fixture("canvas.png"))
    h.click_empty()
    h.fit()
    h.ribbon("Canvas")


b_canvas.done = lambda: ins.panel() is not None
b_canvas.done_what = "the Canvas dialog is open"


def b_front():
    pl.click_square("XZ_Plane")


b_front.done = lambda: canvas() is not None
b_front.done_what = "a canvas on the Front plane"


def b_angle():
    p = ins.panel()
    c = canvas()
    normal = c.Placement.Rotation.multVec(V(0, 0, 1))
    h.check("B the canvas lies in the Front plane", abs(abs(normal.y) - 1) < 1e-6, normal)
    ins.type_value(p.angle, "1")
    h.caught_up(p)


def b_ok():
    h.task_button("OK")


b_ok.done = lambda: ins.panel() is None
b_ok.done_what = "the Canvas dialog closed"


def b_turned():
    c = canvas()
    angle = math.degrees(c.Placement.Rotation.Angle)
    print("CANVAS", c.Placement, c.XSize, c.YSize, flush=True)
    h.check("B the canvas is turned (Z Angle 1)", angle > 1e-3, c.Placement.Rotation)


def b_calibrate():
    tree = t.tree()
    item = tree.row(canvas().Label)
    from Fission180Tests.gui import widget_input as w

    h.check(
        "B right-click > Calibrate",
        w.right_click(tree.viewport(), tree.label_point(item), "Calibrate"),
    )


b_calibrate.done = lambda: ins.panel() is not None and ins.panel().title == "Calibrate"
b_calibrate.done_what = "Calibrate is open"


def dots():
    c = canvas()
    half = c.XSize.Value * 60.0 / 80.0 / 2.0
    return c.Placement.multVec(V(-half, 0, 0)), c.Placement.multVec(V(half, 0, 0))


def b_first():
    h.fit()
    h.click(dots()[0])


def b_second():
    h.click(dots()[1])


def b_distance():
    p = ins.panel()
    S["picked"] = p.distance.value()
    ins.type_value(p.distance, "11.25")


def b_cal_ok():
    h.task_button("OK")


b_cal_ok.done = lambda: ins.panel() is None
b_cal_ok.done_what = "Calibrate closed"


def b_calibrated():
    a, c = dots()
    apart = (c - a).Length
    # the clicks land on screen pixels: the scale is the typed length over the picked one
    h.check(
        "B the two tips are 11.25 in apart (285.75 mm), to the clicks' pixel",
        abs(apart - LENGTH) < 0.02 * LENGTH,
        (apart, S["picked"]),
    )
    h.shot("b-canvas")


# -- C: the profile ---------------------------------------------------------------------------
def sk():
    return h.in_sketch()


def c_line():
    S["sk"] = sk().Name
    st.s["sk"] = sk()
    h.press("l")


def c_line_start():
    si.click(V(0, 0, 0))


def c_line_typed():
    si.type_text("11.25", enter=False)
    si.tab()
    si.type_text("0")


def c_line_done():
    r.esc()
    lines = si.lines(sk())
    if h.check("C one line", len(lines) == 1, lines):
        g = lines[0][1]
        h.check(
            "C 11.25 in along X from the origin",
            st.vnear(g.StartPoint, V(0, 0, 0)) and st.vnear(g.EndPoint, V(LENGTH, 0, 0)),
            (g.StartPoint, g.EndPoint),
        )
    r.esc()
    h.press("x")


def c_construction():
    h.check("C X: new lines are construction", "construction" in r.told().lower(), r.told())
    h.press("l")


def c_mid():
    si.click(MID)


def c_mid_typed():
    si.type_text("3.4", enter=False)
    si.tab()
    si.type_text("90")


def c_mid_done():
    r.esc()
    found = si.lines(sk(), construction=True)
    if h.check("C one construction line", len(found) == 1, found):
        g = found[0][1]
        S["axis"] = found[0][0]
        h.check(
            "C up from the middle, 3.4 in",
            st.vnear(g.StartPoint, V(LENGTH / 2, 0, 0))
            and st.vnear(g.EndPoint, V(LENGTH / 2, HALF, 0)),
            (g.StartPoint, g.EndPoint),
        )
    r.esc()
    h.press("x")


def c_spline():
    S["geo"] = len(sk().Geometry)
    si.menu_item("CREATE", "Fit Point Spline")


def c_spline_points():
    for p in (V(0, 0, 0), V(2 * IN, 2.2 * IN, 0), V(4 * IN, 3.2 * IN, 0), V(LENGTH / 2, HALF, 0)):
        st.click(p)
        h.settle()


def c_spline_enter():
    st.enter()


def splines():
    return [
        (i, g)
        for i, g in enumerate(sk().Geometry)
        if g.TypeId == "Part::GeomBSplineCurve" and not sk().getConstruction(i)
    ]


def c_spline_made():
    r.esc()
    found = splines()
    if h.check("C one spline", len(found) == 1, len(found)):
        g = found[0][1]
        S["s1"] = found[0][0]
        h.check(
            "C from the axis' end to the half-height's top",
            {tuple(round(c, 6) for c in g.StartPoint), tuple(round(c, 6) for c in g.EndPoint)}
            == {(0.0, 0.0, 0.0), (round(LENGTH / 2, 6), round(HALF, 6), 0.0)},
            (g.StartPoint, g.EndPoint),
        )
    Gui.Selection.clearSelection()
    si.menu_item("CREATE", "Mirror")


def mirror_widget(name):
    frame = Gui.getMainWindow().findChild(QtWidgets.QFrame, "Fission180MirrorPanel")
    return frame.findChild(QtWidgets.QWidget, name) if frame is not None else None


def click_mirror(name):
    w = mirror_widget(name)
    if h.check("C the MIRROR panel has %s" % name, w is not None and w.isVisible()):
        h.pointer_to(w, w.rect().center())
        QtTest.QTest.mouseClick(w, QtCore.Qt.LeftButton)
        QtWidgets.QApplication.processEvents()


def spline_point(i, share):
    g = sk().Geometry[i]
    return g.value(g.FirstParameter + share * (g.LastParameter - g.FirstParameter))


def c_mirror_spline():
    st.click(spline_point(S["s1"], 0.5), towards=V(0.3, 1.0, 0))


def c_mirror_line_box():
    click_mirror("Fission180MirrorLine")


c_mirror_line_box.done = lambda: st.tool() is not None and st.tool().field == "line"
c_mirror_line_box.done_what = "Mirror Line takes the next click"


def c_mirror_line():
    st.click(V(LENGTH / 2, HALF * 0.4, 0), towards=V(1.0, 0.2, 0))


def c_mirror_ok():
    click_mirror("Fission180MirrorOK")


def c_mirrored():
    h.settle("the mirror")
    r.esc()
    found = splines()
    if h.check("C two splines", len(found) == 2, len(found)):
        S["s2"] = [i for i, _g in found if i != S["s1"]][0]
        g = found[1][1]
        ends = sorted(round(p.x, 4) for p in (g.StartPoint, g.EndPoint))
        h.check(
            "C the copy reaches the far tip", ends == [round(LENGTH / 2, 4), round(LENGTH, 4)], ends
        )
    Gui.Selection.clearSelection()
    S["cons"] = len(sk().Constraints)
    bb.menu("Tangent")


def c_tangent_first():
    st.click(spline_point(S["s1"], 0.93), towards=V(0.2, 1.0, 0))


def c_tangent_second():
    st.click(
        spline_point(S["s2"], 0.07 if sk().Geometry[S["s2"]].StartPoint.x < LENGTH * 0.6 else 0.93),
        towards=V(0.2, 1.0, 0),
    )


def top_tangents():
    g1, g2 = sk().Geometry[S["s1"]], sk().Geometry[S["s2"]]
    top = V(LENGTH / 2, HALF, 0)

    def at_top(g):
        u = g.FirstParameter if (g.StartPoint - top).Length < 1e-6 else g.LastParameter
        return g.tangent(u)[0]

    return at_top(g1), at_top(g2)


def c_tangent_made():
    t1, t2 = top_tangents()
    cross = abs(t1.x * t2.y - t1.y * t2.x) / (t1.Length * t2.Length)
    print("TANGENT", t1, t2, r.told(), sk().Constraints[S["cons"] :], flush=True)
    h.check("C Tangent: the two splines are smooth at the top", cross < 1e-6, (t1, t2, r.told()))
    h.check("C ...and level there (the ball's widest point)", abs(t1.y) < 1e-6 * t1.Length, t1)
    r.esc()
    h.check("C the sketch solves cleanly", sk().solve() == 0 and not sk().ConflictingConstraints)
    h.shot("c-profile")


# -- D: revolve -------------------------------------------------------------------------------
def d_revolve():
    h.click_empty()
    h.fit()
    h.ribbon("Revolve")


d_revolve.done = lambda: ri.panel() is not None
d_revolve.done_what = "the Revolve dialog is open"


def d_axis():
    p = ri.panel()
    h.check("D the one profile is taken by itself", bool(p.profiles), p.message.text())
    pl.click_on_plane(V(-40, 0, 0))


def d_angle():
    p = ri.panel()
    h.check("D the X axis", p.axis is not None and p.axis[0].Role == "X_Axis", p.axis)
    if p.type.currentText() != "Angle":
        ui.choose(p.type, "Angle")
    ui.type_into(p.angle.widget, "90")
    h.caught_up(p)


def d_ok():
    h.check("D no error", "⚠" not in ri.panel().message.text(), ri.panel().message.text())
    h.task_button("OK")


d_ok.done = lambda: ri.panel() is None
d_ok.done_what = "the Revolve dialog closed"


def d_made():
    found = solids()
    if not h.check("D one body", len(found) == 1, [x.Label for x in found]):
        return
    box = k.box(found[0])
    print("QUARTER", box, k.volume(found[0]), flush=True)
    h.check("D 11.25 in long", abs(box[3] - box[0] - LENGTH) < 1e-3, box)
    h.check("D 3.4 in high", abs(box[5] - HALF) < 1e-3 and abs(box[2]) < 1e-3, box)
    h.check("D a quarter: 3.4 in to one side", abs(abs(box[1] + box[4]) - HALF) < 1e-3, box)
    S["quarter"] = k.volume(found[0])
    S["body"] = found[0].Name
    h.shot("d-quarter")


STEPS_A_D = (
    r.new_design_steps("football")
    + [a_units, a_inch, a_inched]
    + [b_canvas, b_front, b_angle, b_ok, b_turned]
    + [b_calibrate, b_first, b_second, b_distance, b_cal_ok, b_calibrated]
    + r.sketch_on_plane("profile", "XZ_Plane")
    + [c_line, c_line_start, c_line_typed, c_line_done, c_construction, c_mid, c_mid_typed]
    + [c_mid_done, c_spline, c_spline_points, c_spline_enter, c_spline_made]
    + [c_mirror_spline, c_mirror_line_box, c_mirror_line, c_mirror_ok, c_mirrored]
    + [c_tangent_first, c_tangent_second, c_tangent_made, r.finish_sketch("profile")]
    + [d_revolve, d_axis, d_angle, d_ok, d_made]
)


# -- E: fillet --------------------------------------------------------------------------------
def body():
    return doc().getObject(S["body"])


def profile_point(share=0.3):
    """A point of the profile curve in the Front plane (y 0), on the quarter's edge."""
    sketch = doc().getObject(S["sk"])
    g = sketch.Geometry[S["s1"]]
    p = g.value(g.FirstParameter + share * (g.LastParameter - g.FirstParameter))
    return sketch.getGlobalPlacement().multVec(p)


def e_fillet():
    h.click_empty()
    h.fit()
    h.press("f")


e_fillet.done = lambda: b.blend_panel() is not None
e_fillet.done_what = "the Fillet dialog is open"


def e_edges():
    p = profile_point()
    h.check("E the edge in the Front plane", h.click_edge(p))
    h.settle()
    turned = V(p.x, -p.z, 0)  # the same edge after the 90 degree turn
    h.check("E the edge in the Top plane", h.click_edge(turned, QtCore.Qt.ControlModifier))


def e_radius():
    p = b.blend_panel()
    print("FILLET REFS", p.refs, flush=True)
    h.check("E the two curved edges (and their mirrored halves) picked", len(p.refs) >= 2, p.refs)
    b.type_into(p.radius.widget, "1/8")
    h.caught_up(p)


def e_ok():
    p = b.blend_panel()
    h.check("E 1/8 in", abs(p.radius.value() - IN / 8) < 1e-6, p.radius.value())
    h.check("E no error", "⚠" not in r.message(), r.message())
    h.task_button("OK")


e_ok.done = lambda: b.blend_panel() is None
e_ok.done_what = "the Fillet dialog closed"


def e_made():
    v = k.volume(body())
    print("FILLETED", v, S["quarter"], flush=True)
    h.check(
        "E the edges are rounded (a little less volume)",
        S["quarter"] * 0.97 < v < S["quarter"] - 1.0,
        v,
    )
    r.nothing_broken("E")
    S["filleted"] = v
    h.shot("e-fillet")


# -- F: circular pattern of bodies ------------------------------------------------------------
def f_pattern():
    h.click_empty()
    h.fit()
    ps.menu("Circular Pattern")


f_pattern.done = lambda: ps.panel() is not None
f_pattern.done_what = "the Circular Pattern dialog is open"


def f_bodies():
    b.choose(ps.panel().pattern_type, "Bodies")


def f_body():
    h.click(V(LENGTH / 2, -HALF * 0.7071, HALF * 0.7071))


def f_axis_box():
    p = ps.panel()
    objs = p.options["objects"]
    h.check("F the quarter is the object", len(objs) == 1 and objs[0][0] is body(), objs)
    ps.click_box("axis")


def f_axis():
    pl.click_on_plane(V(-40, 0, 0))


def f_quantity():
    p = ps.panel()
    ps.type_quantity(p.quantity, 4)
    h.caught_up(p)


def f_ok():
    h.check("F no error", "⚠" not in r.message(), r.message())
    h.task_button("OK")


f_ok.done = lambda: ps.panel() is None
f_ok.done_what = "the Circular Pattern dialog closed"


def f_made():
    found = solids()
    print("BODIES", [(x.Label, round(k.volume(x), 1)) for x in found], flush=True)
    if not h.check("F four bodies", len(found) == 4, [x.Label for x in found]):
        return
    h.check("F each a quarter", all(abs(k.volume(x) - S["filleted"]) < 1e-3 for x in found))
    import Part

    whole = Part.makeCompound([k.global_shape(x) for x in found]).BoundBox
    h.check(
        "F round the X axis: 6.8 in across",
        abs(whole.YMax + whole.YMin) < 1e-3
        and abs(whole.ZMax + whole.ZMin) < 1e-3
        and abs(whole.YMax - HALF) < 0.1,  # (the 1/8 in round takes 0.03 mm off the widest)
        whole,
    )
    S["bodies"] = [x.Name for x in found]
    h.shot("f-pattern")


# -- G: combine -------------------------------------------------------------------------------
def combine_panel():
    p = r.panel()
    return p if p is not None and getattr(p, "title", "") == "Combine" else None


def g_combine():
    h.click_empty()
    h.fit()
    h.ribbon("Combine")


g_combine.done = lambda: combine_panel() is not None
g_combine.done_what = "the Combine dialog is open"


QUADRANTS = [(-1, 1), (1, 1), (-1, -1), (1, -1)]  # (sign of y, sign of z) of each quarter


def quadrant_point(sy, sz):
    return V(LENGTH / 2, sy * HALF * 0.7071, sz * HALF * 0.7071)


def g_target():
    h.click(quadrant_point(-1, 1))


def owner_of(sy, sz):
    for name in S["bodies"]:
        box = k.box(doc().getObject(name))
        if sy * (box[1] + box[4]) > 0 and sz * (box[2] + box[5]) > 0:
            return doc().getObject(name)
    return None


def g_tools():
    p = combine_panel()
    h.check("G the first quarter is the target", p.options["target"] is owner_of(-1, 1))
    for sy, sz in QUADRANTS[1:3]:
        h.click(quadrant_point(sy, sz))
        h.settle()
    # the fourth quarter is behind the others from where the view looks: its row in the browser
    hidden = owner_of(1, -1)
    t.click_row(hidden.Label, QtCore.Qt.ControlModifier)


def g_ok():
    p = combine_panel()
    print("COMBINE", p.options["target"].Label, [x.Label for x in p.options["tools"]], flush=True)
    h.check("G three tools", len(p.options["tools"]) == 3, [x.Label for x in p.options["tools"]])
    h.check("G Join", p.operation.currentText() == "Join", p.operation.currentText())
    h.check("G no error", "⚠" not in r.message(), r.message())
    h.task_button("OK")


g_ok.done = lambda: combine_panel() is None
g_ok.done_what = "the Combine dialog closed"


def g_made():
    found = [x for x in solids() if x.ViewObject.Visibility]
    if not h.check(
        "G one body (the tools are taken in)", len(found) == 1, [x.Label for x in found]
    ):
        return
    S["ball"] = found[0].Name
    v = k.volume(found[0])
    h.check(
        "G the four quarters' volume",
        abs(v - 4 * S["filleted"]) < 4 * S["filleted"] * 0.01,
        (v, S["filleted"]),
    )
    r.nothing_broken("G")
    h.shot("g-ball")


# -- H: visual style --------------------------------------------------------------------------
def h_visible_edges():
    from Fission180Tests.gui import nav_input as nav

    nav.choose("Display Settings", "Shaded with Visible Edges Only")


def h_shaded():
    from fission180 import display_ui
    from Fission180Tests.gui import nav_input as nav

    h.check("H Shaded with Visible Edges Only", display_ui.is_shaded_visible())
    nav.choose("Display Settings", "Shaded")


def h_back():
    from fission180 import display_ui

    h.check("H Shaded again", display_ui.is_shaded())


# -- I: appearance ----------------------------------------------------------------------------
ON_BALL = V(LENGTH / 2, -HALF * 0.7071, HALF * 0.7071)


def ball():
    return doc().getObject(S["ball"])


def i_open():
    h.click_empty()
    h.fit()
    h.press("a")


i_open.done = lambda: lk.panel() is not None
i_open.done_what = "the Appearance dialog is open"


def i_leather():
    h.check("I the library has leather", lk.library_item("Leather, brown") is not None)
    h.check("I the view takes Leather, brown", lk.drop_look("Leather, brown", ON_BALL))


def i_duplicate():
    data = lk.stored(ball())
    h.check(
        "I the ball is leather", (data["body"] or {}).get("key") == "leather_brown", data["body"]
    )
    lk.design_menu("Leather, brown", "Duplicate")


def i_edit():
    labels = lk.design_labels()
    S["copy"] = [x for x in labels if x.startswith("Leather, brown (")]
    if h.check("I a duplicate under In This Design", len(S["copy"]) == 1, labels):
        lk.double_click_design(S["copy"][0])


i_edit.done = lambda: lk.editor() is not None
i_edit.done_what = "the look editor is open"


def i_rename():
    e = lk.editor()
    h.check("I a leather look has a pattern to scale", e.scale.isEnabled())
    lk.type_field(e.name, "Football leather")
    lk.type_field(e.scale, "50")
    lk.click_group_tick(e.advanced)


def i_editor_ok():
    from Fission180Tests.gui import widget_input as w

    e = lk.editor()
    h.check("I Advanced opens", e.advanced.isChecked() and e.shine.isVisible())
    h.check("I the name is taken", e.message.text() == "", e.message.text())
    w.click(e.ok_button)


i_editor_ok.done = lambda: lk.editor() is None
i_editor_ok.done_what = "the look editor closed"


def i_drop_copy():
    labels = lk.design_labels()
    h.check("I Football leather under In This Design", "Football leather" in labels, labels)
    h.check("I the view takes Football leather", lk.drop_look("Football leather", ON_BALL, True))


def i_done():
    data = lk.stored(ball())
    look = data["body"] or {}
    h.check("I the ball is Football leather", look.get("label") == "Football leather", look)
    h.check("I at 50 %", abs(look.get("scale", 100) - 50.0) < 1e-6, look)
    h.task_button("OK")


i_done.done = lambda: lk.panel() is None
i_done.done_what = "the Appearance dialog closed"


# -- J: decal ---------------------------------------------------------------------------------
def decal_panel():
    from fission180 import decal_ui, taskui

    p = taskui.current()
    return p if isinstance(p, decal_ui.DecalPanel) else None


def decals():
    from fission180 import decal

    return decal.decals(doc())


def j_decal():
    from fission180 import decal_ui

    decal_ui.FILE_PICKER = lambda kind: ins.fixture("canvas.png")  # (the system's file chooser)
    h.click_empty()
    h.fit()
    si.menu_item("INSERT", "Decal")


j_decal.done = lambda: decal_panel() is not None
j_decal.done_what = "the Decal dialog is open"


def j_face():
    h.click(ON_BALL)


def j_options():
    p = decal_panel()
    h.check("J a decal on the ball", len(decals()) == 1, decals())
    ins.set_check(p.chain, True)
    ins.set_spin(p.opacity, 80)
    h.caught_up(p)


def j_right_click():
    from Fission180Tests.gui import widget_input as w

    tree = t.tree()
    item = tree.row(ball().Label)
    texts = w.menu_texts(tree.viewport(), tree.label_point(item))
    print("MENU WHILE DECAL", texts, flush=True)


def j_kept():
    h.check("J a right-click in the browser keeps the Decal dialog", decal_panel() is not None)
    h.task_button("OK")


j_kept.done = lambda: decal_panel() is None
j_kept.done_what = "the Decal dialog closed"


def j_made():
    found = decals()
    if h.check("J one decal", len(found) == 1, found):
        h.check("J it chains the faces", bool(getattr(found[0], "ChainFaces", True)))
        h.check("J in the Decals folder", "Decals" in t.labels(), t.labels()[:20])
    h.shot("j-decal")


def k_end():
    shown = [x for x in solids() if x.ViewObject.Visibility]
    h.check("K one body (the tools were taken in)", len(shown) == 1, [x.Label for x in shown])
    tree = t.tree()
    gone = [x.Label for x in solids() if not x.ViewObject.Visibility and tree.row(x.Label)]
    h.check("K the used-up tools are out of the browser, like Fusion", not gone, gone)
    r.nothing_broken("K")
    h.check("K no undo step left open", not h.open_undo_step(), h.open_undo_step())
    h.fit()
    h.shot("k-end")


STEPS_E_K = (
    [e_fillet, e_edges, e_radius, e_ok, e_made]
    + [f_pattern, f_bodies, f_body, f_axis_box, f_axis, f_quantity, f_ok, f_made]
    + [g_combine, g_target, g_tools, g_ok, g_made]
    + [h_visible_edges, h_shaded, h_back]
    + [i_open, i_leather, i_duplicate, i_edit, i_rename, i_editor_ok, i_drop_copy, i_done]
    + [j_decal, j_face, j_options, j_right_click, j_kept, j_made, k_end]
)


h.run("replay_17_football", STEPS_A_D + STEPS_E_K, paced_by="state")
