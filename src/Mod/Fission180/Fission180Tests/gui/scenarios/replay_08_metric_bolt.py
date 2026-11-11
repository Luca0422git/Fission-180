# SPDX-License-Identifier: LGPL-2.1-or-later
"""Book replay, Project 8 "Metric Bolt" (Mastering Autodesk Fusion 2nd ed., pp 88-93; the book
parity report, lines 1366-1418). Chapter 3 is the parameters chapter: one design from the
first step to the last, the way the book writes it, with a new profile's defaults. Real input
only.

  A  MODIFY > Change Parameters; "+" for each user parameter (Name, Unit, Expression):
     Head_Diam 8.5, Head_Length 5, Shank_Length 45, Bolt_Diam 5, Wrench_Width 4,
     Wrench_Depth 3, Thread_Length = Shank_Length / 2, Chamfer_Size 1, Quantity 6 (no
     units). OK.
  B  A sketch on the Front plane: the bolt's half profile drawn with L (six lines, from the
     origin and back), the bottom line made a Centerline (Sketch Palette > Linetype); D from
     the head's top line to the centerline gives its DIAMETER: "Head_Diam" typed (the bare
     name, Fusion's way), Bolt_Diam the same, Head_Length and Shank_Length on the lines.
  C  S, "rev", Enter: Revolve; the centerline is the axis by itself; OK.
  D  The hex socket: a sketch on the head's end face, Circumscribed Polygon on the centre,
     its circle dimensioned "Wrench_Width"; E, "-Wrench_Depth": Cut by itself.
  E  Chamfer with sets: set 1 the shank's end "Chamfer_Size"; "+", set 2 both head ends 0.5.
  F  Thread on the shank: Modeled, Full Length off, Thread Length "Thread_Length": M5x0.8,
     22.5 long. Thread 1 dragged in front of Chamfer 1 (the book's trick).
  G  Change Parameters: Shank_Length 25: the bolt and its thread follow (12.5 long).
  H  Circular Pattern of the bolt body about Z, Quantity "Quantity": 6 bolts; Change
     Parameters Quantity 8: 8 bolts. Ctrl+Z / Ctrl+Y; save, close, open again.

Skipped as the report did (it gives no sizes): the 40 straight knurls on the head
(`book_modifyc_knurl` builds them).
"""

import math

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
PARAMS = [
    ("Head_Diam", "mm", "8.5"),
    ("Head_Length", "mm", "5"),
    ("Shank_Length", "mm", "45"),
    ("Bolt_Diam", "mm", "5"),
    ("Wrench_Width", "mm", "4"),
    ("Wrench_Depth", "mm", "3"),
    ("Thread_Length", "mm", "Shank_Length / 2"),
    ("Chamfer_Size", "mm", "1"),
    ("Quantity", "No Units", "6"),
]
ROUGH = [(0, 0), (0, 4.6), (6, 4.6), (6, 2.6), (40, 2.6), (40, 0)]


def value(name):
    from fission180 import parameters, parameters_core

    held = getattr(parameters.container(r.doc()), parameters_core.prop_name(name))
    return held.Value if hasattr(held, "Value") else float(held)


def bolt():
    return r.doc().getObject(s["bolt"])


def vol():
    return bolt().Shape.Volume


def states():
    return {k: v[1] for k, v in t.states().items()}


def all_ok(tag):
    bad = {k: v for k, v in states().items() if v != "ok"}
    h.check("%s no step is red in the timeline" % tag, not bad, bad)
    r.nothing_broken(tag)


# == A: the parameters =============================================================================
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


def a_open():
    r.defaults_are_on("A")
    h.fit()
    r.menu("MODIFY", "Change Parameters")


a_open.done = lambda: dialog() is not None
a_open.done_what = "the Parameters dialog is open"


def add_steps(name, unit, expression):
    def open_box():
        w.click(dialog().add_button)

    open_box.done = lambda: adder() is not None
    open_box.done_what = "the Add User Parameter box is open"

    def fill():
        from Fission180Tests.gui import dialog_input as di

        a = adder()
        si.type_into(a.name, name, enter=False)
        if a.unit.currentText() != unit:
            di.choose(a.unit, unit)
        si.type_into(a.expression, expression, enter=False)
        w.click(a.buttons.button(QtWidgets.QDialogButtonBox.Ok))

    fill.done = lambda: adder() is None
    fill.done_what = "the Add User Parameter box closed"
    return [r.named(open_box, "a_add_%s" % name), r.named(fill, "a_fill_%s" % name)]


def a_ok():
    from fission180 import parameters

    names = list(parameters.own_names(r.doc()))
    h.check("A the nine parameters", sorted(names) == sorted(p[0] for p in PARAMS), names)
    h.check("A Thread_Length follows Shank_Length", r.near(value("Thread_Length"), 22.5))
    h.check("A Quantity has no units", r.near(value("Quantity"), 6.0))
    d = dialog()
    w.click(
        [x for x in d.findChildren(QtWidgets.QPushButton) if x.text().replace("&", "") == "OK"][0]
    )


a_ok.done = lambda: dialog() is None
a_ok.done_what = "the Parameters dialog closed"


# == B: the profile ================================================================================
def b_sketch():
    Gui.Selection.clearSelection()
    h.ribbon("Create Sketch")


def b_front():
    pl.pick_in_browser("XZ_Plane")


b_front.done = lambda: h.in_sketch() is not None
b_front.done_what = "the sketch on the Front plane is open"


def b_line():
    sk = r.sk()
    s["sketch"] = sk.Name
    r.zoom_on(r.g(V(20, 2, 0)), 40.0)
    s["geo0"] = len(sk.Geometry)
    h.press("l")


def line_click(k):
    def step():
        x, y = ROUGH[k % len(ROUGH)]
        r.sclick(V(x, y, 0))

    return r.named(step, "b_line_%d" % k)


def b_lines_done():
    r.esc()
    r.esc()
    s["lines"] = [i for i, _g in r.geo("Part::GeomLineSegment") if i >= s["geo0"]]
    h.check("B six lines", len(s["lines"]) == 6, s["lines"])
    r.sketch_clean("B drawn:")
    Gui.Selection.clearSelection()
    r.sclick(mid(5))  # the bottom line, on the X axis


def line(k):
    return r.sk().Geometry[s["lines"][k]]


def mid(k):
    g = line(k)
    return V((g.StartPoint.x + g.EndPoint.x) / 2.0, (g.StartPoint.y + g.EndPoint.y) / 2.0, 0)


def b_centerline():
    picked = [n for x in Gui.Selection.getSelectionEx() for n in x.SubElementNames]
    want = "Edge%d" % (s["lines"][5] + 1)
    h.check(
        "B a click on the bottom line picks the line (not the X axis under it)",
        picked == [want],
        (picked, want),
    )
    si.palette_click("Fission180PaletteCenterline")


def b_dimension():
    from fission180 import sketch_centerline

    lines = sketch_centerline.lines(r.sk())
    h.check("B the bottom line is a Centerline", lines == [s["lines"][5]], lines)
    h.check(
        "B ...still a normal line (the profile stays closed)",
        not r.sk().getConstruction(s["lines"][5]),
    )
    Gui.Selection.clearSelection()
    h.press("d")


def dim_steps(name, k, text, place, to_centerline):
    """D on line k (and the centerline: a diameter), placed at place() (a function), the
    parameter's bare name typed."""

    def pick():
        r.sclick(mid(k) + V(1.0, 0, 0))

    def centerline():
        r.sclick(mid(5) + V(-3.0, 0, 0))

    def placed():
        r.sclick(place())

    def typed():
        h.check("B %s: the value box is open" % name, r.value_editor() is not None, r.focus_name())
        r.keyboard(text)
        r.enter()

    found = [r.named(pick, "b_dim_%s_pick" % name)]
    if to_centerline:
        found.append(r.named(centerline, "b_dim_%s_centerline" % name))
    found += [r.named(placed, "b_dim_%s_place" % name), r.named(typed, "b_dim_%s_type" % name)]
    return found


def b_profile_done():
    from fission180 import parameters

    r.esc()
    got = [(round(line(k).StartPoint.x, 6), round(line(k).StartPoint.y, 6)) for k in range(6)]
    want = [(0, 0), (0, 4.25), (5, 4.25), (5, 2.5), (50, 2.5), (50, 0)]
    h.check("B the profile has the bolt's sizes", got == want, got)
    r.sketch_clean("B")
    h.check("B the profile is fully constrained", r.dof() == 0, r.dof())
    bound = parameters.expressions_of(r.sk())
    used = " ".join(bound.values())
    h.check(
        "B the four dimensions follow the parameters (bare names typed)",
        all(n in used for n in ("Head_Diam", "Bolt_Diam", "Head_Length", "Shank_Length")),
        bound,
    )
    h.shot("B-profile")
    h.ribbon("Finish Sketch")


b_profile_done.done = lambda: h.in_sketch() is None
b_profile_done.done_what = "Finish Sketch closed the sketch"


# == C: Revolve from the command search ============================================================
def search_popup():
    from fission180 import search_ui

    popup = QtWidgets.QApplication.activePopupWidget()
    return popup if isinstance(popup, search_ui.CommandSearchDialog) else None


def c_search():
    h.fit()
    Gui.Selection.clearSelection()
    h.press("s")


c_search.done = lambda: search_popup() is not None
c_search.done_what = "the command search"


def c_rev():
    popup = search_popup()
    QtTest.QTest.keyClicks(popup._edit, "rev")
    QtWidgets.QApplication.processEvents()
    found = [popup._list.item(k).text().split("    [")[0] for k in range(popup._list.count())]
    h.check('C "rev" lists Revolve first', found and found[0] == "Revolve", found[:4])
    QtTest.QTest.keyClick(popup._edit, QtCore.Qt.Key_Return)


def revolve_panel():
    from fission180 import revolve_ui

    p = revolve_ui.RevolvePanel.last
    return p if p is not None and not p._closed else None


c_rev.done = lambda: revolve_panel() is not None
c_rev.done_what = "Enter started Revolve"


def c_ok():
    p = revolve_panel()
    h.check("C the profile is taken by itself", len(p.profiles) == 1, p.profiles)
    h.check(
        "C the centerline is the axis by itself",
        p.axis is not None and p.axis[1].startswith("Edge"),
        p.axis,
    )
    h.caught_up(p)
    h.task_button("OK")


c_ok.done = lambda: revolve_panel() is None
c_ok.done_what = "OK finished the Revolve"


def bolt_volume(shank):
    return math.pi * 4.25**2 * 5 + math.pi * 2.5**2 * shank


def c_done():
    made = r.solid_bodies()
    h.check("C one body", len(made) == 1, [b.Label for b in made])
    s["bolt"] = made[0].Name
    h.check("C the bolt's exact volume", r.near(vol(), bolt_volume(45), 1e-6), vol())
    h.check(
        "C along X, round the X axis",
        r.box_near(bolt().Shape, [0, -4.25, -4.25, 50, 4.25, 4.25], 0.05),  # (a round box is loose)
        r.bbox(bolt().Shape),
    )
    all_ok("C")
    h.check("C the bolt is shown", bolt().Visibility, bolt().Visibility)
    s["v_bolt"] = vol()


# == D: the hex socket =============================================================================
def d_sketch():
    r.look_from(V(1, 1, -1))  # (the head's end face, x = 0, is in view)
    Gui.Selection.clearSelection()
    h.ribbon("Create Sketch")


def d_face():
    h.click(V(0, 2.6, -1.5))  # the head's end face, off its middle


d_face.done = lambda: h.in_sketch() is not None
d_face.done_what = "the sketch on the head's end face is open"


def to_sketch(point):
    p = r.sk().getGlobalPlacement().inverse().multVec(point)
    return V(p.x, p.y, 0)


def d_polygon():
    sk = r.sk()
    s["socket_sketch"] = sk.Name
    h.check("D the sketch is on the head's end", r.near(sk.getGlobalPlacement().Base.x, 0.0, 1e-9))
    r.zoom_on(V(0, 0, 0), 14.0)
    s["geo0"] = len(sk.Geometry)
    r.menu("CREATE", "Circumscribed Polygon")


def d_centre():
    r.sclick(to_sketch(V(0, 0, 0)))


def d_edge():
    r.sclick(to_sketch(V(0, 0, 0)) + V(2.2, 0, 0))


def d_drawn():
    r.esc()
    r.esc()
    sides = [i for i, _g in r.geo("Part::GeomLineSegment", construction=False) if i >= s["geo0"]]
    h.check("D six sides", len(sides) == 6, sides)
    circles = [i for i, g in r.geo("Part::GeomCircle") if i >= s["geo0"]]
    s["edge_circle"] = circles[-1] if circles else None
    centre = to_sketch(V(0, 0, 0))
    found = r.sk().Geometry[s["edge_circle"]].Center if circles else None
    h.check("D on the face's centre", found is not None and (found - centre).Length < 1e-6, found)
    Gui.Selection.clearSelection()
    h.press("d")


def edge_circle():
    return r.sk().Geometry[s["edge_circle"]]


def d_dim_pick():
    c = edge_circle()
    a = math.radians(30.0)
    r.sclick(c.Center + V(c.Radius * math.cos(a), c.Radius * math.sin(a), 0))


def d_dim_place():
    c = edge_circle()
    r.sclick(c.Center + V(c.Radius + 2.5, c.Radius + 1.5, 0))


def d_dim_type():
    h.check("D the value box is open", r.value_editor() is not None, r.focus_name())
    r.keyboard("Wrench_Width")
    r.enter()


def d_finish():
    r.esc()
    h.check("D across the flats: Wrench_Width", r.near(2 * edge_circle().Radius, 4.0, 1e-6))
    r.sketch_clean("D")
    h.ribbon("Finish Sketch")


d_finish.done = lambda: h.in_sketch() is None
d_finish.done_what = "Finish Sketch closed the sketch"


def d_profile():
    sk = r.doc().getObject(s["socket_sketch"])
    h.click(sk.getGlobalPlacement().multVec(to_sketch_of(sk, V(0, 0, 0)) + V(0.6, 0.4, 0)))


def to_sketch_of(sk, point):
    p = sk.getGlobalPlacement().inverse().multVec(point)
    return V(p.x, p.y, 0)


def d_extrude():
    h.press("e")


def extrude_panel():
    from fission180 import extrude_ui

    p = extrude_ui.ExtrudePanel.last
    return p if p is not None and not p._closed else None


d_extrude.done = lambda: extrude_panel() is not None
d_extrude.done_what = "the Extrude dialog is open"


def d_depth():
    from Fission180Tests.gui import arrow_input as arrows

    p = extrude_panel()
    h.check("D the hexagon is the profile", len(p.profiles) == 1, p.profiles)
    arrows.give_distance("-Wrench_Depth")


def d_ok():
    p = extrude_panel()
    h.caught_up(p)
    h.check(
        "D into the head: Cut by itself",
        p.operation.currentData() == "cut",
        p.operation.currentText(),
    )
    h.check("D nothing is refused", not p.message.text(), p.message.text())
    h.task_button("OK")


d_ok.done = lambda: extrude_panel() is None
d_ok.done_what = "OK finished the Extrude"


def d_done():
    hexagon = math.sqrt(3.0) / 2.0 * 4.0**2
    want = s["v_bolt"] - hexagon * 3.0
    h.check("D a hex socket 4 across the flats, 3 deep", r.near(vol(), want, 1e-6), (vol(), want))
    all_ok("D")
    s["v_socket"] = vol()
    h.fit()
    h.shot("D-socket")


# == E: Chamfer with two sets ======================================================================
def blend():
    from Fission180Tests.gui import blend_steps as b

    return b


def e_chamfer():
    Gui.Selection.clearSelection()
    r.look_from(V(-1, 1, -1))  # (the shank's end, x = 50, in view)
    h.ribbon("Chamfer")


e_chamfer.done = lambda: blend().blend_panel() is not None
e_chamfer.done_what = "the Chamfer dialog is open"


def ring_point(x, radius, angle_deg=-135.0):
    a = math.radians(angle_deg)
    return V(x, radius * math.cos(a), radius * math.sin(a))


def e_shank_end():
    p = blend().blend_panel()
    h.check("E one set to start with", p.rows.count() == 1, p.rows.count())
    h.click_edge(ring_point(50, 2.5, 135.0))


def e_size_1():
    p = blend().blend_panel()
    h.check("E set 1: the shank's end", len(p.refs) == 1, p.refs)
    blend().type_into(p.distance.widget, "Chamfer_Size")
    QtTest.QTest.keyClick(p.distance.widget, QtCore.Qt.Key_Tab)


def e_plus():
    p = blend().blend_panel()
    h.caught_up(p)
    w.click(p.add_row_button)
    r.look_from(V(1, 1, -1))  # (the head's two ends in view)


def e_head_end():
    p = blend().blend_panel()
    h.check("E '+' adds set 2", p.rows.count() == 2, p.rows.count())
    h.click_edge(ring_point(0, 4.25, 135.0))


def e_head_inner():
    h.click_edge(ring_point(5, 4.25, 100.0))


def e_size_2():
    p = blend().blend_panel()
    h.check("E set 2: both head ends", len(p.refs) == 2, p.refs)
    blend().type_into(p.distance.widget, "0.5")
    QtTest.QTest.keyClick(p.distance.widget, QtCore.Qt.Key_Tab)


def e_ok():
    p = blend().blend_panel()
    h.caught_up(p)
    h.check("E nothing is refused", not p.message.text(), p.message.text())
    h.task_button("OK")


e_ok.done = lambda: blend().blend_panel() is None
e_ok.done_what = "OK finished the Chamfer"
e_ok.timeout_s = 120


def bevel(radius, size):
    """What a 45 degree chamfer `size` takes off a round edge of `radius` (outside)."""
    return (
        math.pi
        * size
        * (radius**2 - (radius**2 + radius * (radius - size) + (radius - size) ** 2) / 3.0)
    )


def e_done():
    # the head's step: the chamfer runs round the outside corner of a flat face meeting the
    # head's side; a ring triangle at the radius 4.25 corner (the same formula)
    want = s["v_socket"] - bevel(2.5, 1.0) - 2 * bevel(4.25, 0.5)
    h.check("E the three edges bevelled", r.near(vol(), want, 1e-5), (vol(), want))
    h.check("E one Chamfer step", t.titles()[-1].startswith("Chamfer"), t.titles())
    all_ok("E")
    s["v_chamfer"] = vol()
    h.shot("E-chamfer")


# == F: the thread =================================================================================
def thread_panel():
    from Fission180Tests.gui import hole_steps as hs

    return hs.thread_panel()


def f_thread():
    Gui.Selection.clearSelection()
    h.fit()
    r.menu("CREATE", "Thread")


f_thread.done = lambda: thread_panel() is not None
f_thread.done_what = "the Thread dialog is open"


def f_shank():
    h.click(ring_point(30, 2.5, 135.0))


def f_modeled():
    from Fission180Tests.gui import hole_steps as hs

    p = thread_panel()
    h.check("F a thread on the shank", p.target is not None, hs.message(p))
    h.check(
        "F M5x0.8 offered", p.designation.currentText() == "M5x0.8", p.designation.currentText()
    )
    if not p.modeled.isChecked():
        hs.click_checkbox(p.modeled)


def f_full_length():
    from Fission180Tests.gui import hole_steps as hs

    p = thread_panel()
    h.check("F Modeled", p.modeled.isChecked())
    if p.full_length.isChecked():
        hs.click_checkbox(p.full_length)


def f_length():
    from Fission180Tests.gui import dialog_input as ui

    p = thread_panel()
    h.check("F Thread Length shows", p.length.widget.isVisible())
    ui.type_into(p.length.widget, "Thread_Length")


def f_ok():
    p = thread_panel()
    h.caught_up(p)
    h.check(
        "F the parameter is taken: 22.5", r.near(p.length.value(), 22.5, 1e-6), p.length.value()
    )
    h.task_button("OK")


f_ok.done = lambda: thread_panel() is None
f_ok.done_what = "OK finished the Thread"
f_ok.timeout_s = 180


def thread_length():
    from fission180 import thread

    step = [o for o in r.doc().Objects if thread.is_thread(o)][0]
    return step.Length.Value if hasattr(step.Length, "Value") else float(step.Length)


def f_drag():
    h.check("F a real thread is cut", vol() < s["v_chamfer"] - 5.0, vol())
    h.check("F 22.5 long", r.near(thread_length(), 22.5, 1e-6), thread_length())
    all_ok("F thread:")
    s["v_thread_after"] = vol()
    h.check("F the drag is made", t.drag_step("Thread 1", before_title="Chamfer 1"))


f_drag.timeout_s = 180


def f_dragged():
    titles = t.titles()
    h.check(
        "F Thread 1 before Chamfer 1", titles.index("Thread 1") < titles.index("Chamfer 1"), titles
    )
    h.check("F nothing is refused", t.tl().refusal() == "", t.tl().refusal())
    all_ok("F drag:")
    h.check("F the bolt is shown", bolt().Visibility, bolt().Visibility)
    s["v_threaded"] = vol()
    h.fit()
    h.shot("F-thread")


# == G: Change Parameters: the shank 25 ============================================================
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


def change_steps(tag, name, text, check):
    def open_():
        r.menu("MODIFY", "Change Parameters")

    open_.done = lambda: dialog() is not None
    open_.done_what = "the Parameters dialog is open"

    def typed():
        type_expression(name, text)

    typed.timeout_s = 300

    def ok():
        d = dialog()
        h.check(
            "%s the change is taken (nothing said)" % tag, not d.message.text(), d.message.text()
        )
        w.click(
            [x for x in d.findChildren(QtWidgets.QPushButton) if x.text().replace("&", "") == "OK"][
                0
            ]
        )

    ok.done = lambda: dialog() is None
    ok.done_what = "the Parameters dialog closed"
    return [
        r.named(open_, "%s_open" % tag),
        r.named(typed, "%s_type" % tag),
        r.named(ok, "%s_ok" % tag),
        r.named(check, "%s_check" % tag),
    ]


def g_check():
    h.check("G Shank_Length is 25", r.near(value("Shank_Length"), 25.0))
    h.check(
        "G the bolt is 30 long",
        r.box_near(bolt().Shape, [0, -4.25, -4.25, 30, 4.25, 4.25], 0.05),
        r.bbox(bolt().Shape),
    )
    h.check("G the thread follows: 12.5", r.near(thread_length(), 12.5, 1e-6), thread_length())
    all_ok("G")
    s["v_short"] = vol()
    h.fit()
    h.shot("G-short")


# == H: a pattern of bolts that follows Quantity ===================================================
def pattern_panel():
    from Fission180Tests.gui import pattern_steps as ps

    return ps.panel()


def h_pattern():
    from Fission180Tests.gui import pattern_steps as ps

    Gui.Selection.clearSelection()
    h.fit()
    ps.menu("Circular Pattern")


h_pattern.done = lambda: pattern_panel() is not None
h_pattern.done_what = "the Circular Pattern dialog is open"


def h_body():
    q = pattern_panel()
    h.check(
        "H Pattern Type Bodies", q.options["pattern_type"] == "bodies", q.options["pattern_type"]
    )
    h.click(ring_point(20, 2.5, 135.0))


def h_axis_box():
    from Fission180Tests.gui import pattern_steps as ps

    q = pattern_panel()
    h.check("H the bolt is picked", len(q.options["objects"]) == 1, q.options["objects"])
    ps.click_box("axis")


def h_axis():
    pl.pick_in_browser("Z_Axis")


def h_quantity():
    from Fission180Tests.gui import pattern_steps as ps

    q = pattern_panel()
    axis = q.options.get("axis")
    h.check("H the Z axis", axis is not None and getattr(axis[0], "Role", "") == "Z_Axis", axis)
    ps.type_quantity(q.quantity, "Quantity")


def h_ok():
    q = pattern_panel()
    h.caught_up(q)
    h.check("H no refusal", not q.message.text(), q.message.text())
    h.check("H the formula is kept", q.options["expressions"].get("quantity") == "Quantity")
    h.task_button("OK")


h_ok.done = lambda: pattern_panel() is None
h_ok.done_what = "OK finished the pattern"
h_ok.timeout_s = 300


def bolts():
    return [b for b in r.solid_bodies() if r.near(b.Shape.Volume, s["v_short"], 1e-6)]


def h_six():
    h.check("H six bolts", len(bolts()) == 6, [b.Label for b in r.solid_bodies()])
    hidden = [b.Label for b in bolts() if not b.Visibility]
    h.check("H every bolt is shown, the first one too (Fusion)", not hidden, hidden)
    all_ok("H 6:")


def h_eight():
    h.check("H Quantity 8: eight bolts", len(bolts()) == 8, [b.Label for b in r.solid_bodies()])
    all_ok("H 8:")
    s["titles"] = t.titles()
    h.fit()
    h.shot("H-eight")


def h_undone():
    h.check("H Ctrl+Z: six bolts again", len(bolts()) == 6, len(bolts()))
    h.check("H ...Quantity 6", r.near(value("Quantity"), 6.0))


def h_redone():
    h.check("H Ctrl+Y: eight", len(bolts()) == 8, len(bolts()))
    all_ok("H redo:")


def h_reopened():
    made = r.solid_bodies()
    s["bolt"] = sorted(made, key=lambda b: b.ID)[0].Name
    h.check("H reopened: eight bolts", len(bolts()) == 8, [b.Label for b in made])
    h.check("H reopened: the same timeline", t.titles() == s["titles"], t.titles())
    h.check("H reopened: Quantity still drives the pattern", r.near(value("Quantity"), 8.0))
    all_ok("H reopened:")
    h.shot("H-reopened")


steps = r.home_steps() + [a_open]
for _name, _unit, _expression in PARAMS:
    steps += add_steps(_name, _unit, _expression)
steps += [a_ok, b_sketch, b_front, b_line] + [line_click(k) for k in range(7)]
steps += [b_lines_done, b_centerline, b_dimension]
steps += dim_steps("head_diam", 1, "Head_Diam", lambda: V(-4.0, mid(1).y / 2.0, 0), True)
steps += dim_steps("bolt_diam", 3, "Bolt_Diam", lambda: V(line(4).StartPoint.x + 4.0, 1.2, 0), True)
steps += dim_steps("head_length", 1, "Head_Length", lambda: mid(1) + V(0, 3.0, 0), False)
steps += dim_steps("shank_length", 3, "Shank_Length", lambda: mid(3) + V(0, 4.0, 0), False)
steps += [b_profile_done, c_search, c_rev, c_ok, c_done]
steps += [d_sketch, d_face, d_polygon, d_centre, d_edge, d_drawn, d_dim_pick, d_dim_place]
steps += [d_dim_type, d_finish, d_profile, d_extrude, d_depth, d_ok, d_done]
steps += [e_chamfer, e_shank_end, e_size_1, e_plus, e_head_end, e_head_inner, e_size_2, e_ok]
steps += [e_done, f_thread, f_shank, f_modeled, f_full_length, f_length, f_ok, f_drag, f_dragged]
steps += change_steps("g", "Shank_Length", "25", g_check)
steps += [h_pattern, h_body, h_axis_box, h_axis, h_quantity, h_ok, h_six]
steps += change_steps("h8", "Quantity", "8", h_eight)
steps += [r.named(r.undo, "h_undo"), h_undone, r.named(r.redo, "h_redo"), h_redone]
steps += r.save_steps("h", "Metric Bolt") + r.reopen_steps("h", "Metric Bolt") + [h_reopened]

h.run("replay_08_metric_bolt", steps, paced_by="state")
