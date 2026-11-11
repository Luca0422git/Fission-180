# SPDX-License-Identifier: LGPL-2.1-or-later
"""Book replay, Project 9 "Prototype Drone" (Mastering Autodesk Fusion 2nd ed., pp 96-109; the
book parity report, lines 1421-1634): the parametric frame, rebuilt step by step from the
report's text with its own sketch, then changed the way the book changes it. One design, a
new profile's defaults, real input only.

The frame here is the report's case in its plainest form: a hub, a middle ring and a rim
whose size is the parameter Limits_Arm_Length (= min(100; max(45; Arm_Length)), the book's
own formula), cut by twelve spokes made with one line and a sketch Circular Pattern: 36
areas. Four windows of the outer ring are left out of the plate.

  A  ASSEMBLE > New Component "Drone Frame": active, grounded (Fusion's first component).
  B  A sketch on its Top plane; MODIFY > Change Parameters inside the sketch: "+" Arm_Length
     53 and Limits_Arm_Length = min(100; max(45; Arm_Length)) (bare numbers). C at the
     origin, 20 typed; C again, the middle ring a click away (no size: dragged later); C, the
     rim "Limits_Arm_Length * 2" typed (a name in the box). L from the origin to the rim; the
     line selected, CREATE > Circular Pattern about the origin, 12: 36 areas.
  C  Finish Sketch (the sketch stays shown). E, the hub's and the middle ring's 24 areas
     clicked, Distance "Thickness = -2.5 mm" (a parameter made in the box, negative):
     one body. The sketch shown again (its eye), E, eight outer areas, "-Thickness", New
     Body: four bodies. MODIFY > Combine, the plate the target, the four the tools, Join:
     one body. Ctrl+Z / Ctrl+Y of the Combine.
  D  Change Parameters: Arm_Length 50, 40 (45, the limit), 110 (100), 53, 60: every time the
     same 32 areas make the plate (the report: "Extrude 1 would break: Sub shape not found:
     Sketch.InternalFace56").
  E  Fillet 2.5 on two inner corners of a window; the whole plate window-picked (a drag in the
     Chamfer dialog), Chamfer 0.25.
  F  The sketch opened again, the middle ring dragged, Ctrl+Z (the report: "One drag + undo
     froze the app for about 80 s"), Finish Sketch; Ctrl+Z / Ctrl+Y runs; save, close, open
     again; Arm_Length 70 after reopening.

Out of the replay (the report's own stand-ins, other builders' scenarios): the STEP motors,
board and battery from CADclass.org, their Move with parameters, Rigid Group, Properties.
"""

import math
import time

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import replay_c_steps as r
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import timeline_input as t
from Fission180Tests.gui import widget_input as w

V = App.Vector
s = {}
HUB_R = 10.0
T = 2.5
WINDOWS = (0, 3, 6, 9)  # the outer sectors left out (sector k: 30 k .. 30 (k + 1) degrees)
OUTER = [k for k in range(12) if k not in WINDOWS]
PAIRS = (60.0, 150.0, 240.0, 330.0)  # the middles of the four outer pieces


def value(name):
    from fission180 import parameters, parameters_core

    held = getattr(parameters.container(r.doc()), parameters_core.prop_name(name))
    return held.Value if hasattr(held, "Value") else float(held)


def rim():
    return min(100.0, max(45.0, value("Arm_Length")))


def mid_r():
    return s["mid_r"]


def polar(radius, degrees, z=0.0):
    a = math.radians(degrees)
    return V(radius * math.cos(a), radius * math.sin(a), z)


def plate_volume(radius=None, middle=None):
    radius = rim() if radius is None else radius
    middle = mid_r() if middle is None else middle
    windows = len(WINDOWS) * math.pi * (radius**2 - middle**2) / 12.0
    return T * (math.pi * radius**2 - windows)


def shown_bodies():
    """The bodies on the screen (a body used up by Combine is hidden: combine.py)."""
    return [b for b in r.solid_bodies() if b.Visibility]


def plate():
    found = shown_bodies()
    return found[0] if len(found) == 1 else None


def states():
    return {k: v[1] for k, v in t.states().items()}


def all_ok(tag):
    bad = {k: v for k, v in states().items() if v != "ok"}
    h.check("%s no step is red in the timeline" % tag, not bad, bad)
    r.nothing_broken(tag)


def sketch_obj():
    return r.doc().getObject(s["sketch"])


# == A: the component ==============================================================================
def component_panel():
    from Fission180Tests.gui import component_steps as k

    return k.new_component_panel()


def a_component():
    r.defaults_are_on("A")
    h.fit()
    r.menu("ASSEMBLE", "New Component")


a_component.done = lambda: component_panel() is not None
a_component.done_what = "the New Component dialog is open"


def a_name():
    from Fission180Tests.gui import component_steps as k

    k.type_name("Drone Frame")
    h.task_button("OK")


a_name.done = lambda: component_panel() is None
a_name.done_what = "OK made the component"


def a_made():
    from Fission180Tests.gui import component_steps as k

    h.check("A the component Drone Frame", k.component("Drone Frame") is not None, k.top_labels())
    h.check("A ...is the active one", k.active_label() == "Drone Frame", k.active_label())
    h.check("A ...grounded (the first component, Fusion)", k.grounded("Drone Frame"))


# == B: the sketch and its parameters ==============================================================
def b_sketch():
    Gui.Selection.clearSelection()
    h.fit()
    h.ribbon("Create Sketch")


def b_top():
    pl.click_square("XY_Plane")


b_top.done = lambda: h.in_sketch() is not None
b_top.done_what = "the sketch on the Top plane is open"


def dialog():
    from fission180 import parameters_ui

    d = parameters_ui.ParametersDialog.last
    return d if d is not None and d.isVisible() else None


def adder():
    d = dialog()
    a = d.adder if d is not None else None
    try:
        return a if a is not None and a.isVisible() else None
    except RuntimeError:
        return None


def b_parameters():
    from Fission180Tests.gui import component_steps as k

    sk = r.sk()
    s["sketch"] = sk.Name
    h.check("B the sketch is in Drone Frame", k.container_label(sk) == "Drone Frame")
    # the book: Change Parameters from the sketch's MODIFY menu (the report: not there)
    r.menu("MODIFY", "Change Parameters")


b_parameters.done = lambda: dialog() is not None
b_parameters.done_what = "Change Parameters opened from the sketch's MODIFY menu"


def add_steps(name, expression):
    def open_box():
        w.click(dialog().add_button)

    open_box.done = lambda: adder() is not None
    open_box.done_what = "the Add User Parameter box is open"

    def fill():
        a = adder()
        si.type_into(a.name, name, enter=False)
        si.type_into(a.expression, expression, enter=False)
        w.click(a.buttons.button(QtWidgets.QDialogButtonBox.Ok))

    fill.done = lambda: adder() is None
    fill.done_what = "the Add User Parameter box closed"
    return [r.named(open_box, "b_add_%s" % name), r.named(fill, "b_fill_%s" % name)]


def press_ok(d):
    w.click(
        [x for x in d.findChildren(QtWidgets.QPushButton) if x.text().replace("&", "") == "OK"][0]
    )


def b_params_ok():
    h.check(
        "B Limits_Arm_Length = 53 mm (bare numbers taken as mm)",
        r.near(value("Limits_Arm_Length"), 53.0),
    )
    press_ok(dialog())


b_params_ok.done = lambda: dialog() is None
b_params_ok.done_what = "the Parameters dialog closed"


def b_hub():
    h.check("B the sketch is still open", h.in_sketch() is not None)
    r.zoom_on(r.g(V(0, 0, 0)), 140.0)
    s["geo0"] = len(r.sk().Geometry)
    h.press("c")


def circle_steps(tag, radius_click=None, typed=None):
    def centre():
        r.sclick(V(0, 0, 0))

    def size():
        if typed is not None:
            r.smove(V(25.0, 9.0, 0))
            h.settle()
            r.keyboard(typed)
            r.enter()
        else:
            r.sclick(V(radius_click, 0.0, 0) + V(0, 0, 0))

    return [r.named(centre, "b_%s_centre" % tag), r.named(size, "b_%s_size" % tag)]


def circles():
    return sorted(
        ((i, g) for i, g in r.geo("Part::GeomCircle") if i >= s["geo0"]), key=lambda c: c[1].Radius
    )


def b_circles_done():
    r.esc()
    r.esc()
    found = circles()
    h.check("B three circles", len(found) == 3, [round(g.Radius, 3) for _i, g in found])
    if len(found) != 3:
        return
    h.check("B ...on the origin", all(g.Center.Length < 1e-9 for _i, g in found))
    h.check("B the hub 20 across", r.near(found[0][1].Radius, HUB_R))
    s["mid_r"] = found[1][1].Radius
    s["mid"] = found[1][0]
    h.check(
        "B the middle ring between the hub and the rim", HUB_R + 5 < s["mid_r"] < 45, s["mid_r"]
    )
    h.check("B the rim follows Limits_Arm_Length", r.near(found[2][1].Radius, 53.0, 1e-6))
    h.press("l")


def b_spoke_start():
    r.sclick(V(0, 0, 0))


def b_spoke_end():
    r.sclick(V(53.0, 0, 0), towards=V(1.0, 0.6, 0))


def b_spoke_done():
    r.esc()
    r.esc()
    lines = [(i, g) for i, g in r.geo("Part::GeomLineSegment") if i >= s["geo0"]]
    h.check("B one spoke", len(lines) == 1, lines)
    if not lines:
        return
    s["spoke"] = lines[0][0]
    g = lines[0][1]
    h.check(
        "B from the origin to the rim, level",
        g.StartPoint.Length < 1e-9
        and r.near(g.EndPoint.x, 53.0, 1e-6)
        and abs(g.EndPoint.y) < 1e-9,
        (g.StartPoint, g.EndPoint),
    )
    Gui.Selection.clearSelection()
    r.sclick(V(40.0, 0, 0))


def b_pattern():
    picked = [n for x in Gui.Selection.getSelectionEx() for n in x.SubElementNames]
    h.check("B the spoke is selected", picked == ["Edge%d" % (s["spoke"] + 1)], picked)
    si.menu_item("CREATE", "Circular Pattern")


PANEL = "Fission180SketchPatternPanel"


def b_pattern_centre():
    from Fission180Tests.gui import sketch_tools_steps as st

    tool = st.tool()
    h.check("B Circular Pattern waits for its centre", tool is not None and tool.field == "center")
    r.sclick(V(0, 0, 0), towards=V(-0.6, -1.0, 0))


def b_pattern_quantity():
    from Fission180Tests.gui import book_sketch_b_steps as b

    b.panel_type(PANEL, "Fission180PatternQuantity", "12", enter=False)


def b_pattern_ok():
    from Fission180Tests.gui import book_sketch_b_steps as b

    b.panel_click(PANEL, "Fission180PatternOK")


def areas():
    sk = sketch_obj()
    shape = sk.InternalShape if hasattr(sk, "InternalShape") else None
    return len(shape.Faces) if shape is not None and not shape.isNull() else 0


def b_patterned():
    r.esc()
    lines = [i for i, _g in r.geo("Part::GeomLineSegment", construction=False) if i >= s["geo0"]]
    h.check("B twelve spokes", len(lines) == 12, len(lines))
    r.sketch_clean("B")
    sk = r.sk()
    sk.recompute()
    h.check("B 36 areas (the report's count)", areas() == 36, areas())
    h.shot("B-sketch")
    h.ribbon("Finish Sketch")


b_patterned.done = lambda: h.in_sketch() is None
b_patterned.done_what = "Finish Sketch closed the sketch"


# == C: the plate ==================================================================================
def extrude_panel():
    from fission180 import extrude_ui

    p = extrude_ui.ExtrudePanel.last
    return p if p is not None and not p._closed else None


def c_extrude():
    h.check("C the sketch stays shown until it is used (Fusion)", sketch_obj().Visibility)
    r.look_from(V(0, 0, -1))  # the Top view
    Gui.Selection.clearSelection()
    h.press("e")


c_extrude.done = lambda: extrude_panel() is not None
c_extrude.done_what = "the Extrude dialog is open"


def area_click(radius, degrees, tag):
    def step():
        h.click(polar(radius() if callable(radius) else radius, degrees))

    return r.named(step, tag)


def inner_clicks():
    found = []
    for k in range(12):
        found.append(area_click(HUB_R / 2.0, 30 * k + 15, "c_hub_%d" % k))
        found.append(area_click(lambda: (HUB_R + mid_r()) / 2.0, 30 * k + 15, "c_ring_%d" % k))
    return found


def outer_clicks(prefix):
    return [
        area_click(lambda: (mid_r() + rim()) / 2.0, 30 * k + 15, "%s_outer_%d" % (prefix, k))
        for k in OUTER
    ]


def c_distance():
    from Fission180Tests.gui import arrow_input as arrows

    p = extrude_panel()
    h.check("C 24 areas picked", len(p.profiles) == 24, len(p.profiles))
    # Fusion's quick way to make a parameter in a box, a negative one
    arrows.give_distance("Thickness = -2.5 mm")


def c_ok():
    p = extrude_panel()
    h.caught_up(p)
    h.check("C nothing is refused", not p.message.text(), p.message.text())
    h.task_button("OK")


c_ok.done = lambda: extrude_panel() is None
c_ok.done_what = "OK finished the Extrude"
c_ok.timeout_s = 120


def c_first():
    h.check("C Thickness = -2.5 mm made", r.near(value("Thickness"), -2.5), value("Thickness"))
    body = plate()
    h.check("C one body", body is not None, [b.Label for b in r.solid_bodies()])
    if body is None:
        return
    s["plate"] = body.Name
    want = T * math.pi * mid_r() ** 2
    h.check(
        "C the hub and the middle ring, 2.5 down",
        r.near(body.Shape.Volume, want, 1e-6),
        (body.Shape.Volume, want),
    )
    h.check("C downwards", r.near(body.Shape.BoundBox.ZMin, -T, 1e-6), body.Shape.BoundBox.ZMin)
    all_ok("C first:")
    t.click_eye(sketch_obj().Label)  # the used sketch shown again for the next extrude


def c_second():
    h.check("C the sketch shows again", sketch_obj().Visibility)
    Gui.Selection.clearSelection()
    h.press("e")


c_second.done = lambda: extrude_panel() is not None
c_second.done_what = "the Extrude dialog is open"


def c_second_distance():
    from Fission180Tests.gui import arrow_input as arrows

    p = extrude_panel()
    h.check("C eight outer areas", len(p.profiles) == 8, len(p.profiles))
    arrows.give_distance("Thickness")  # (Thickness is -2.5: the same way down)


def c_new_body():
    from Fission180Tests.gui import dialog_input as ui

    p = extrude_panel()
    ui.choose(p.operation, "New Body")


def c_second_ok():
    p = extrude_panel()
    h.caught_up(p)
    h.check("C New Body", p.operation.currentData() == "new_body", p.operation.currentText())
    h.task_button("OK")


c_second_ok.done = lambda: extrude_panel() is None
c_second_ok.done_what = "OK finished the second Extrude"
c_second_ok.timeout_s = 120


def c_bodies():
    found = r.solid_bodies()
    h.check(
        "C five bodies (the plate and four outer pieces)", len(found) == 5, [b.Label for b in found]
    )
    all_ok("C second:")
    s["titles_before_combine"] = t.titles()
    Gui.Selection.clearSelection()
    h.ribbon("Combine")


def combine_panel():
    from fission180 import taskui

    p = taskui.current()
    return p if p is not None and getattr(p, "title", "") == "Combine" else None


c_bodies.done = lambda: combine_panel() is not None
c_bodies.done_what = "the Combine dialog is open"


def c_target():
    h.click(polar((HUB_R + mid_r()) / 2.0, 15.0))


def tool_click(degrees, k):
    def step():
        h.click(polar((mid_r() + rim()) / 2.0, degrees))

    return r.named(step, "c_tool_%d" % k)


def c_combine_ok():
    p = combine_panel()
    h.check(
        "C the plate the target, the four pieces the tools",
        p.options["target"] is not None and len(p.options["tools"]) == 4,
        p.options,
    )
    h.check("C Join", p.options.get("operation", "join") == "join", p.options.get("operation"))
    h.task_button("OK")


c_combine_ok.done = lambda: combine_panel() is None
c_combine_ok.done_what = "OK finished the Combine"
c_combine_ok.timeout_s = 120


def c_combined():
    body = plate()
    h.check("C one body", body is not None, [b.Label for b in r.solid_bodies()])
    if body is None:
        return
    s["plate"] = body.Name
    h.check(
        "C the windowed plate",
        r.near(body.Shape.Volume, plate_volume(), 1e-6),
        (body.Shape.Volume, plate_volume()),
    )
    h.check("C one solid", len(body.Shape.Solids) == 1, len(body.Shape.Solids))
    all_ok("C combine:")
    s["titles"] = t.titles()
    h.shot("C-plate")
    r.undo()


def c_undone():
    h.check("C Ctrl+Z: the five bodies back", len(shown_bodies()) == 5, len(shown_bodies()))
    h.check(
        "C ...no Combine left in the timeline", t.titles() == s["titles_before_combine"], t.titles()
    )
    all_ok("C undo:")
    r.redo()


def c_redone():
    h.check("C Ctrl+Y: one body again", plate() is not None, len(shown_bodies()))
    h.check("C ...the same timeline", t.titles() == s["titles"], t.titles())
    all_ok("C redo:")


# == D: the experiment with the parameters =========================================================
def type_expression(name, text):
    d = dialog()
    rows = [
        k for k in range(d.user.rowCount()) if d.user.item(k, 0).data(QtCore.Qt.UserRole) == name
    ]
    h.check("%s is in the table" % name, bool(rows))
    if not rows:
        return
    rect = d.user.visualItemRect(d.user.item(rows[0], 2))
    d.window().activateWindow()
    w.double_click(d.user.viewport(), rect.center())
    editors = [e for e in d.user.findChildren(QtWidgets.QLineEdit) if e.isVisible()]
    h.check("an editor opened for %s" % name, bool(editors))
    if editors:
        QtTest.QTest.keyClick(editors[0], QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
        QtTest.QTest.keyClicks(editors[0], text)
        QtTest.QTest.keyClick(editors[0], QtCore.Qt.Key_Return)


def d_open():
    Gui.Selection.clearSelection()
    r.menu("MODIFY", "Change Parameters")


d_open.done = lambda: dialog() is not None
d_open.done_what = "the Parameters dialog is open"


def windows_open(tag, radius):
    """The plate has its four windows and the eight outer sectors, at the rim `radius`."""
    shape = plate().Shape
    z = -T / 2.0
    mid = (mid_r() + radius) / 2.0
    solid = [k for k in range(12) if shape.isInside(polar(mid, 30 * k + 15, z), 1e-6, True)]
    h.check("%s the same sectors are solid (the windows stay)" % tag, solid == OUTER, solid)


def arm_steps(text, expected, from_60=None):
    tag = "D Arm_Length %s" % text

    def typed():
        s["t0"] = time.time()
        type_expression("Arm_Length", text)

    typed.timeout_s = 300

    def check():
        took = time.time() - s["t0"]
        d = dialog()
        h.check("%s: accepted (no 'would break')" % tag, not d.message.text(), d.message.text())
        h.check("%s: the rim is %g" % (tag, expected), r.near(rim(), expected), rim())
        body = plate()
        h.check("%s: one body" % tag, body is not None)
        if body is None:
            return
        if from_60 is None:
            want = plate_volume(expected)
            h.check(
                "%s: the plate follows" % tag,
                r.near(body.Shape.Volume, want, 1e-6),
                (body.Shape.Volume, want),
            )
        else:
            # rounded and bevelled now: it grows as the plain plate does (the bevel along the
            # longer rim adds a few mm3)
            grew = body.Shape.Volume - s[from_60]
            want = plate_volume(expected) - plate_volume(60.0)
            h.check("%s: the plate follows" % tag, abs(grew - want) < 10.0, (grew, want))
        windows_open(tag, expected)
        h.speed_check("%s: within 10 s" % tag, took < 10.0 * h.SLOWDOWN, took)

    return [r.named(typed, "d_type_%s" % text), r.named(check, "d_check_%s" % text)]


def d_ok():
    press_ok(dialog())


d_ok.done = lambda: dialog() is None
d_ok.done_what = "the Parameters dialog closed"


def d_done():
    all_ok("D")
    h.check("D Arm_Length 60", r.near(value("Arm_Length"), 60.0))
    h.fit()
    h.shot("D-60")


# == E: fillet and chamfer =========================================================================
def blend():
    from Fission180Tests.gui import blend_steps as b

    return b


def e_fillet():
    Gui.Selection.clearSelection()
    # from outside the window of 270..300 degrees, looking into it: both its corners show
    a = math.radians(285.0)
    r.look_from(V(-math.cos(a) * 0.7, -math.sin(a) * 0.7, -0.7))
    r.zoom_on(polar(mid_r(), 285.0, -T / 2.0), 30.0)  # (zoomed in on it: the corners are short)
    h.ribbon("Fillet")


e_fillet.done = lambda: blend().blend_panel() is not None
e_fillet.done_what = "the Fillet dialog is open"


def e_corner(degrees, k, side):
    """Turn the view to look at the corner from inside the window, low, zoomed in (a person
    turns the part until the short upright edge lights up), and click it."""

    def step():
        look = math.radians(degrees + side * 40.0)  # (from the window's side of the corner)
        r.look_from(V(-math.cos(look), -math.sin(look), -0.45))
        corner = polar(mid_r(), degrees, -T / 2.0)
        r.zoom_on(corner, 12.0)
        h.click_edge(corner)

    return r.named(step, "e_corner_%d" % k)


def e_radius():
    p = blend().blend_panel()
    picked = [p.base.Shape.getElement(ref) for ref in p.refs if str(ref).startswith("Edge")]
    upright = [e for e in picked if abs(e.Vertexes[0].Point.z - e.Vertexes[-1].Point.z) > T - 1e-6]
    h.check("E two upright inner corners of a window", len(upright) == 2 == len(p.refs), p.refs)
    h.shot("E-corners")
    blend().type_into(p.radius.widget, "2.5")
    QtTest.QTest.keyClick(p.radius.widget, QtCore.Qt.Key_Tab)


def e_fillet_ok():
    p = blend().blend_panel()
    h.caught_up(p)
    h.check("E nothing is refused", not p.message.text(), p.message.text())
    h.task_button("OK")


e_fillet_ok.done = lambda: blend().blend_panel() is None
e_fillet_ok.done_what = "OK finished the Fillet"
e_fillet_ok.timeout_s = 120


def e_filleted():

    v = plate().Shape.Volume
    # an inside corner rounded r adds material: (r^2 - pi r^2 / 4) through the plate at a
    # square corner between two flat walls; a little less here (one wall is the round ring)
    most = 2 * T * (2.5**2 - math.pi * 2.5**2 / 4.0)
    added = v - plate_volume()
    h.check("E two inside corners rounded 2.5", 0.6 * most < added <= most + 1e-6, (added, most))
    h.check("E no sliver face", min(f.Area for f in plate().Shape.Faces) > 1.0)
    all_ok("E fillet:")
    s["v_fillet"] = v
    r.look_from(V(0, 0, -1))
    Gui.Selection.clearSelection()
    h.ribbon("Chamfer")


e_filleted.done = lambda: blend().blend_panel() is not None
e_filleted.done_what = "the Chamfer dialog is open"


def e_window():
    from Fission180Tests.gui import selection_input as sel

    radius = rim()
    corners = [V(-radius, -radius, 0), V(radius, radius, 0)]
    sel.box_around(corners, margin=14)


def e_size():
    p = blend().blend_panel()
    s["edges"] = len(p.refs)
    h.check("E the window picks the plate's top edges", len(p.refs) >= 20, len(p.refs))
    blend().type_into(p.distance.widget, "0.25")
    QtTest.QTest.keyClick(p.distance.widget, QtCore.Qt.Key_Tab)
    s["t0"] = time.time()


def e_chamfer_ok():
    p = blend().blend_panel()
    h.caught_up(p)
    h.check(
        "E 0.25 is not refused (the report: too big, also at 0.1)",
        not p.message.text(),
        p.message.text(),
    )
    h.task_button("OK")


e_chamfer_ok.done = lambda: blend().blend_panel() is None
e_chamfer_ok.done_what = "OK finished the Chamfer"
e_chamfer_ok.timeout_s = 300


def e_chamfered():
    took = time.time() - s["t0"]
    body = plate()
    v = body.Shape.Volume
    h.check("E the edges bevelled", v < s["v_fillet"] - 1.0, (v, s["v_fillet"]))
    h.check("E one valid solid", body.Shape.isValid() and len(body.Shape.Solids) == 1)
    all_ok("E chamfer:")
    App.Console.PrintMessage(
        "[Fission 180] REPLAY drone: the chamfer of %d edges took %.1f s\n" % (s["edges"], took)
    )
    s["v_done"] = v
    s["titles"] = t.titles()
    h.fit()
    h.shot("E-chamfer")


# == F: a drag in the sketch and its undo, undo / redo runs, save, reopen ==========================
def f_edit():
    from Fission180Tests.gui import dialog_input as ui

    ui.double_click_timeline(
        t.titles()[t.titles().index("Sketch 1")] if "Sketch 1" in t.titles() else "Sketch 1"
    )


f_edit.done = lambda: h.in_sketch() is not None
f_edit.done_what = "the sketch is open for editing"


def f_drag():
    from Fission180Tests.gui import sketch_tools_steps as st

    r.look_from(V(0, 0, -1))
    r.zoom_on(r.g(V(0, 0, 0)), 2.6 * rim())
    s["mid_before"] = r.sk().Geometry[s["mid"]].Radius
    start = polar(mid_r(), 45.0)
    st.s["sk"] = r.sk()
    pos = st.press(start)
    st.drag_to(polar(mid_r() + 3.0, 45.0))
    s["t0"] = time.time()
    st.release(h.screen_point(r.g(polar(mid_r() + 3.0, 45.0))))
    del pos


f_drag.timeout_s = 300


def f_dragged():
    took = time.time() - s["t0"]
    now = r.sk().Geometry[s["mid"]].Radius
    h.check(
        "F the middle ring was dragged bigger", now > s["mid_before"] + 1.0, (now, s["mid_before"])
    )
    h.speed_check("F the drag answered within 10 s", took < 10.0 * h.SLOWDOWN, took)
    s["t0"] = time.time()
    r.undo()


f_dragged.timeout_s = 300


def f_undone():
    took = time.time() - s["t0"]
    App.Console.PrintMessage("[Fission 180] REPLAY drone: Ctrl+Z of the drag took %.1f s\n" % took)
    h.check(
        "F Ctrl+Z after the drag answered within 10 s (the report: 80 s)",
        took < 10.0 * h.SLOWDOWN,
        took,
    )
    h.check("F the ring is back", r.near(r.sk().Geometry[s["mid"]].Radius, s["mid_before"], 1e-9))
    h.check("F the sketch is still open", h.in_sketch() is not None)
    h.ribbon("Finish Sketch")


f_undone.timeout_s = 300
f_undone.done = lambda: h.in_sketch() is None
f_undone.done_what = "Finish Sketch closed the sketch"


def f_after_sketch():
    h.check(
        "F the plate as it was",
        r.near(plate().Shape.Volume, s["v_done"], 1e-6),
        plate().Shape.Volume,
    )
    all_ok("F sketch:")


def undo_run(count, tag):
    return [r.named(r.undo, "%s_%d" % (tag, k)) for k in range(count)]


def redo_run(count, tag):
    return [r.named(r.redo, "%s_%d" % (tag, k)) for k in range(count)]


def f_undone_run():
    # the chamfer, the fillet, the parameter changes: back to Arm_Length 53
    h.check(
        "F three Ctrl+Z: before the parameter changes",
        r.near(value("Arm_Length"), 53.0),
        value("Arm_Length"),
    )
    h.check("F ...the plate at 53", r.near(plate().Shape.Volume, plate_volume(53.0), 1e-6))
    all_ok("F undo run:")


def f_redone_run():
    h.check("F three Ctrl+Y: the finished frame", r.near(plate().Shape.Volume, s["v_done"], 1e-6))
    h.check("F ...the same timeline", t.titles() == s["titles"], t.titles())
    all_ok("F redo run:")


def f_reopened():
    from Fission180Tests.gui import component_steps as k

    body = plate()
    h.check("F reopened: one body", body is not None, [b.Label for b in r.solid_bodies()])
    s["plate"] = body.Name if body else None
    h.check(
        "F reopened: the same frame",
        body is not None and r.near(body.Shape.Volume, s["v_done"], 1e-6),
    )
    h.check("F reopened: Drone Frame still grounded", k.grounded("Drone Frame"))
    all_ok("F reopened:")


def f_70():
    body = plate()
    h.check(
        "F reopened, Arm_Length 70: the frame follows",
        body is not None and body.Shape.Volume > s["v_done"] + 100.0,
    )
    windows_open("F 70", 70.0)
    all_ok("F 70:")
    h.fit()
    h.shot("F-70")


steps = r.home_steps() + [a_component, a_name, a_made, b_sketch, b_top, b_parameters]
steps += add_steps("Arm_Length", "53") + add_steps(
    "Limits_Arm_Length", "min(100; max(45; Arm_Length))"
)
steps += [b_params_ok, b_hub]
steps += circle_steps("hub", typed="20") + circle_steps("ring", radius_click=30.0)
steps += circle_steps("rim", typed="Limits_Arm_Length * 2")
steps += [b_circles_done, b_spoke_start, b_spoke_end, b_spoke_done, b_pattern, b_pattern_centre]
steps += [b_pattern_quantity, b_pattern_ok, b_patterned, c_extrude] + inner_clicks()
steps += [c_distance, c_ok, c_first, c_second] + outer_clicks("c2")
steps += [c_second_distance, c_new_body, c_second_ok, c_bodies, c_target]
steps += [tool_click(a, k) for k, a in enumerate(PAIRS)] + [
    c_combine_ok,
    c_combined,
    c_undone,
    c_redone,
]
steps += [d_open]
for _text, _expected in (("50", 50.0), ("40", 45.0), ("110", 100.0), ("53", 53.0), ("60", 60.0)):
    steps += arm_steps(_text, _expected)
steps += [
    d_ok,
    d_done,
    e_fillet,
    e_corner(270.0, 0, 1),
    e_corner(300.0, 1, -1),
    e_radius,
    e_fillet_ok,
]
steps += [e_filleted, e_window, e_size, e_chamfer_ok, e_chamfered]
steps += [f_edit, f_drag, f_dragged, f_undone, f_after_sketch]
steps += undo_run(3, "f_undo") + [f_undone_run] + redo_run(3, "f_redo") + [f_redone_run]
steps += (
    r.save_steps("f", "Prototype Drone") + r.reopen_steps("f", "Prototype Drone") + [f_reopened]
)
steps += (
    [r.named(d_open, "f_params")]
    + arm_steps("70", 70.0, "v_done")
    + [r.named(d_ok, "f_params_ok"), f_70]
)

h.run("replay_09_drone", steps, paced_by="state")
