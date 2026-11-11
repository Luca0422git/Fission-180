# SPDX-License-Identifier: LGPL-2.1-or-later
"""Book replay, Project 7 "Geocache Hide" (Mastering Autodesk Fusion 2nd ed., pp 76-84; the
book parity report, lines 1272-1363). One design from the first step to the last, the way
the book writes it, with a new profile's defaults. Real input only.

  A  CREATE > Cylinder on the Top plane: OK before the centre is clicked is refused; the
     centre, Diameter 33, Height 16. A double-click on Body1 in the browser renames it
     "Bottom Screw".
  B  Chamfer the top edge 3 mm; CREATE > Thread on the side: M33x3.5 offered, Modeled.
     Thread 1 dragged in front of Chamfer 1 in the timeline (the book's trick: the thread
     runs into the chamfer). MODIFY > Offset Face -0.25 on the thread (clearance).
  C  The knob: a second Cylinder on the same plane, Height -8 (it grows away from the
     screw). CREATE > Coil: 0.1 revolutions, -10 mm, Triangular (Internal), Inside, 1 mm,
     Cut. Mirror (Features, Coil 1, the XZ plane from the browser). Circular Pattern of
     Coil 1 and Mirror 1 about Z, Quantity 25: the knurl (previewed light, built once on OK
     outside the window's process, with a progress window).
  D  The Top Cap: a sketch on the Front plane, a six-line profile, Revolve about Z (the
     axis picked in the browser), New Body. Thread on its inner wall: Modeled, Full Length
     off, Thread Length 18.
  E  CONSTRUCT > Offset Plane -30 from XZ (picked in the browser); a sketch on it with the
     text "UNSCREW CAP OFFICIAL GEOCACHE." (Height 7.5, centred); CREATE > Emboss 0.75 onto
     the cap. A sketch with INSERT > Insert SVG (0.3, both flips, -15 / 2).
  F  The timeline: click the first step, Shift+click the last, right-click > Group Features.
     INSPECT > Section Analysis on the XZ plane. Ctrl+Z / Ctrl+Y, save, reopen.

The report gives the screw (33 x 16, chamfer 3, M33x3.5) and the coil's values; the knob
(40 across, 8 high) and the cap's profile are the stand-ins the knurl benchmark and the
report's thread read-out ("Inside thread, D 33 mm, 20.9 mm long") give.
"""

import math

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore
from PySide6 import QtTest

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import primitive_input as pi
from Fission180Tests.gui import replay_c_steps as r
from Fission180Tests.gui import timeline_input as t

V = App.Vector
s = {}
R, H = 16.5, 16.0
SCREW = math.pi * R * R * H
KNOB_R, KNOB_H = 20.0, 8.0
SIDE = V(R * math.cos(math.radians(-45)), R * math.sin(math.radians(-45)), 9.0)
TOP_EDGE = V(R * math.cos(math.radians(-45)), R * math.sin(math.radians(-45)), H)


def placing_boxes(p):
    return {
        k[len(p.PLACING) :]: b
        for k, b in p.value_boxes.boxes.items()
        if k.startswith(p.PLACING) and b.isVisible()
    }


def screw():
    return r.doc().getObject(s["screw"])


def vol():
    return screw().Shape.Volume


def states():
    return {k: v[1] for k, v in t.states().items()}


def all_ok(tag):
    bad = {k: v for k, v in states().items() if v != "ok"}
    h.check("%s no step is red in the timeline" % tag, not bad, bad)
    r.nothing_broken(tag)


# == A: the bottom screw ===========================================================================
def a_cylinder():
    r.defaults_are_on("A")
    h.fit()
    pi.menu("Cylinder")


a_cylinder.done = lambda: pi.panel("CylinderPanel") is not None
a_cylinder.done_what = "the Cylinder dialog is open"


def a_plane():
    pl.click_square("XY_Plane")


def a_ok_too_early():
    h.task_button("OK")


def a_centre():
    p = pi.panel("CylinderPanel")
    if h.check("A OK before the centre is clicked: the dialog stays", p is not None):
        text = r.panel_message(p)
        h.check("A ...and says to click the centre", "centre" in text.lower(), text)
    pl.click_on_plane(V(0, 0, 0))


def a_diameter():
    p = pi.panel("CylinderPanel")
    h.wait_for(lambda: "diameter" in placing_boxes(p), "the Diameter box on the canvas")
    r.keyboard("33")
    r.enter()


def a_height():
    p = pi.panel("CylinderPanel")
    h.check("A Enter placed the circle", p is not None and p.state == "ready", p and p.state)
    r.keyboard("16")
    r.enter()


a_height.done = pi.no_dialog
a_height.done_what = "Enter finished the Cylinder"


def a_rename():
    made = r.solid_bodies()
    h.check("A one body, Body1", [b.Label for b in made] == ["Body1"], [b.Label for b in made])
    s["screw"] = made[0].Name
    h.check("A 33 across, 16 high", r.near(vol(), SCREW), vol())
    h.check(
        "A from the plane upwards",
        r.box_near(screw().Shape, [-R, -R, 0, R, R, H], 0.05),  # (a round box is loose)
        r.bbox(screw().Shape),
    )
    Gui.Selection.clearSelection()
    t.double_click_row("Body1")


def name_field():
    from fission180 import browser_ui

    editor = browser_ui.widget()._renaming
    if editor is None or not editor.is_open():
        return None
    return editor.field if editor.field.isVisible() else None


a_rename.done = lambda: name_field() is not None
a_rename.done_what = "the name field after a double-click on Body1 (the book's way)"


def a_name():
    f = name_field()
    f.setFocus()
    QtTest.QTest.keyClicks(f, "Bottom Screw")
    QtTest.QTest.keyClick(f, QtCore.Qt.Key_Return)


def a_named():
    h.check("A the body is Bottom Screw", screw().Label == "Bottom Screw", screw().Label)
    shown = [x for x in t.labels() if x.startswith("Bottom Screw")]
    h.check("A the browser shows it", len(shown) == 1, t.labels())
    h.check("A no dialog opened and the body is not hidden", r.no_dialog() and screw().Visibility)


# == B: chamfer, thread, the thread before the chamfer, clearance ==================================
def blend():
    from Fission180Tests.gui import blend_steps as b

    return b


def b_chamfer():
    Gui.Selection.clearSelection()
    h.fit()
    h.ribbon("Chamfer")


def b_edge():
    h.click_edge(TOP_EDGE)


def b_size():
    p = blend().blend_panel()
    if h.check("B Chamfer with the top edge", p is not None and len(p.refs) == 1, p and p.refs):
        blend().type_into(p.distance.widget, "3")


def b_chamfer_ok():
    h.task_button("OK")


b_chamfer_ok.done = r.no_dialog
b_chamfer_ok.done_what = "OK finished the Chamfer"


def b_thread():
    from Fission180Tests.gui import sketch_input as si

    ring = math.pi * 3.0 * (R * R - (R * R + R * (R - 3) + (R - 3) ** 2) / 3.0)
    s["chamfered"] = SCREW - ring
    h.check("B the top edge is bevelled 3 mm", r.near(vol(), s["chamfered"], 1e-6), vol())
    Gui.Selection.clearSelection()
    si.menu_item("CREATE", "Thread")


def thread_panel():
    from Fission180Tests.gui import hole_steps as hs

    return hs.thread_panel()


b_thread.done = lambda: thread_panel() is not None
b_thread.done_what = "the Thread dialog is open"


def b_side():
    h.click(SIDE)


def b_offered():
    from Fission180Tests.gui import hole_steps as hs

    p = thread_panel()
    if not h.check("B a thread is previewed on the side", p.target is not None, hs.message(p)):
        return
    h.check("B M33x3.5 is offered (the face's size)", p.designation.currentText() == "M33x3.5")
    h.check("B ISO metric", p.standard.currentData() == "iso", p.standard.currentData())
    hs.click_checkbox(p.modeled)


def b_thread_ok():
    p = thread_panel()
    h.caught_up(p)
    h.check("B Modeled: a real thread is cut", vol() < s["chamfered"] - 100.0, vol())
    h.task_button("OK")


b_thread_ok.done = lambda: thread_panel() is None
b_thread_ok.done_what = "OK finished the Thread"
b_thread_ok.timeout_s = 120


def b_drag():
    s["thread_after"] = vol()
    h.check("B Chamfer 1, then Thread 1", t.titles()[-2:] == ["Chamfer 1", "Thread 1"], t.titles())
    all_ok("B thread:")
    h.check("B the drag is made", t.drag_step("Thread 1", before_title="Chamfer 1"))


b_drag.timeout_s = 120


def b_dragged():
    titles = t.titles()
    h.check(
        "B Thread 1 is in front of Chamfer 1 (the report: the drag did nothing)",
        titles[-2:] == ["Thread 1", "Chamfer 1"],
        titles,
    )
    h.check("B nothing is refused", t.tl().refusal() == "", t.tl().refusal())
    all_ok("B drag:")
    tip_shown("B after the drag:", screw())
    s["thread_through"] = vol()
    h.check(
        "B the thread runs into the chamfer (more is cut)",
        s["thread_through"] < s["thread_after"] - 50.0,
        (s["thread_through"], s["thread_after"]),
    )
    shape = screw().Shape
    h.check("B one valid solid", shape.isValid() and len(shape.Solids) == 1)
    top = max(shape.Faces, key=lambda f: f.CenterOfMass.z)
    h.check("B the end is still bevelled to 27 across", top.BoundBox.XLength < 2 * (R - 3) + 0.01)
    h.shot("B-thread-into-chamfer")
    Gui.Selection.clearSelection()
    r.menu("MODIFY", "Offset Face")


def offset_panel():
    return blend().active_panel()


b_dragged.done = lambda: offset_panel() is not None
b_dragged.done_what = "the Offset Face dialog is open"


def b_offset_click():
    h.click(V(11.6, -11.6, 7.0))  # on the thread


def b_offset_value():
    p = offset_panel()
    h.check(
        "B one click takes the whole thread (the report: no selection)",
        p.target is not None and "thread" in p.what.text().lower(),
        p.what.text(),
    )
    blend().type_into(p.field.widget, "-0.25")


b_offset_value.timeout_s = 120


def b_offset_ok():
    p = offset_panel()
    h.caught_up(p)
    h.check("B nothing is refused", "⚠" not in p.message.text(), p.message.text())
    h.check("B the thread is looser (material is gone)", vol() < s["thread_through"] - 100.0, vol())
    h.task_button("OK")


b_offset_ok.done = lambda: offset_panel() is None
b_offset_ok.done_what = "OK finished the Offset Face"
b_offset_ok.timeout_s = 120


def b_done():
    from fission180 import thread

    step = [o for o in r.doc().Objects if thread.is_thread(o)][0]
    h.check("B the thread holds -0.25 mm", abs(thread.face_offset(step) + 0.25) < 1e-9)
    h.check("B no step was added for it", t.titles()[-2:] == ["Thread 1", "Chamfer 1"], t.titles())
    all_ok("B offset:")
    s["v_screw"] = vol()
    h.shot("B-screw")


# == C: the knob and its knurl =====================================================================
def c_cylinder():
    Gui.Selection.clearSelection()
    r.look_from(V(-1, 1, 0.6))  # (from a little below: the knob will hang under the screw)
    pi.menu("Cylinder")


c_cylinder.done = lambda: pi.panel("CylinderPanel") is not None
c_cylinder.done_what = "the Cylinder dialog is open"


def c_plane():
    pl.pick_in_browser("XY_Plane")


def c_centre():
    p = pi.panel("CylinderPanel")
    h.check("C the Top plane is taken from the browser", p.state == "place", p.state)
    pl.click_on_plane(V(0, 0, 0))


def c_diameter():
    p = pi.panel("CylinderPanel")
    h.wait_for(lambda: "diameter" in placing_boxes(p), "the Diameter box on the canvas")
    r.keyboard("40")
    r.enter()


def c_height():
    p = pi.panel("CylinderPanel")
    h.check("C Enter placed the circle", p is not None and p.state == "ready", p and p.state)
    r.keyboard("-8")
    r.tab()


def c_knob_ok():
    p = pi.panel("CylinderPanel")
    h.caught_up(p)
    s["operation"] = p.operation.currentText()
    h.task_button("OK")


c_knob_ok.done = pi.no_dialog
c_knob_ok.done_what = "OK finished the Cylinder"


def c_knob():
    made = r.solid_bodies()
    h.check("C touching the screw: a Join by itself", s["operation"] == "Join", s["operation"])
    h.check("C still one body", len(made) == 1, [b.Label for b in made])
    knob = math.pi * KNOB_R**2 * KNOB_H
    h.check("C the knob is 40 across and 8 high", r.near(vol(), s["v_screw"] + knob, 1e-6), vol())
    bb = screw().Shape.BoundBox
    h.check(
        "C Height -8 grows away from the screw (the report: it went +8 into it)",
        r.near(bb.ZMin, -KNOB_H, 1e-6) and r.near(bb.ZMax, H, 1e-6),
        (bb.ZMin, bb.ZMax),
    )
    s["v_knob"] = vol()
    all_ok("C knob:")
    pi.menu("Coil")


c_knob.done = lambda: pi.panel("CoilPanel") is not None
c_knob.done_what = "the Coil dialog is open"


def c_coil_plane():
    pl.pick_in_browser("XY_Plane")


def c_coil_centre():
    p = pi.panel("CoilPanel")
    h.check("C Coil: the plane is taken", p.state == "place", p.state)
    pl.click_on_plane(V(0, 0, 0))


def c_coil_circle():
    pl.click_on_plane(V(KNOB_R, 0, 0))  # the knob's rim: Diameter 40


def c_coil_values():
    from Fission180Tests.gui import dialog_input as ui

    p = pi.panel("CoilPanel")
    h.check("C Coil: the circle gives Diameter 40", r.near(p.diameter.value(), 40.0, 1e-6))
    ui.type_into(p.revolutions.widget, "0.1")
    ui.type_into(p.height.widget, "-10")
    h.check("C Triangular (Internal)", ui.choose(p.section, "Triangular (Internal)"))
    h.check("C Inside", ui.choose(p.section_position, "Inside"))
    ui.type_into(p.section_size.widget, "1")
    h.check("C Cut", ui.choose(p.operation, "Cut"))


def c_coil_ok():
    p = pi.panel("CoilPanel")
    h.caught_up(p)
    h.check("C nothing is refused", "⚠" not in r.panel_message(p), r.panel_message(p))
    h.task_button("OK")


c_coil_ok.done = pi.no_dialog
c_coil_ok.done_what = "OK finished the Coil"
c_coil_ok.timeout_s = 120


def pattern_panel():
    from Fission180Tests.gui import pattern_steps as ps

    return ps.panel()


def c_mirror():
    from Fission180Tests.gui import pattern_steps as ps

    s["groove"] = s["v_knob"] - vol()
    h.check("C the coil cuts a slanted groove into the knob", 0.5 < s["groove"] < 20.0, s["groove"])
    h.check("C Coil 1 ends the timeline", t.titles()[-1] == "Coil 1", t.titles())
    all_ok("C coil:")
    Gui.Selection.clearSelection()
    ps.menu("Mirror")


c_mirror.done = lambda: pattern_panel() is not None
c_mirror.done_what = "the Mirror dialog is open"


def c_mirror_type():
    from Fission180Tests.gui import dialog_input as ui

    ui.choose(pattern_panel().pattern_type, "Features")


def c_mirror_coil():
    from Fission180Tests.gui import pattern_steps as ps

    ps.timeline_click("Coil 1")


def c_mirror_plane_box():
    from Fission180Tests.gui import pattern_steps as ps

    q = pattern_panel()
    h.check("C Mirror: Coil 1 is the object", len(q.options["objects"]) == 1, q.options["objects"])
    ps.click_box("plane")


def c_mirror_plane():
    pl.pick_in_browser("XZ_Plane")


def c_mirror_ok():
    q = pattern_panel()
    plane = q.options.get("plane")
    h.check(
        "C Mirror: the XZ plane from the browser",
        plane is not None and getattr(plane[0], "Role", "") == "XZ_Plane",
        plane,
    )
    h.caught_up(q)
    h.check("C nothing is refused", not q.message.text(), q.message.text())
    h.task_button("OK")


c_mirror_ok.done = lambda: pattern_panel() is None
c_mirror_ok.done_what = "OK finished the Mirror"
c_mirror_ok.timeout_s = 120


def c_pattern():
    from Fission180Tests.gui import pattern_steps as ps

    removed = s["v_knob"] - vol()
    # the coil runs 36 degrees round from the XZ plane down, its mirror the other way: a V
    # that meets at the top (two grooves, no crossing)
    h.check(
        "C the mirror cuts the same groove the other way",
        abs(removed - 2.0 * s["groove"]) < 0.01 * s["groove"],
        (removed, s["groove"]),
    )
    h.check("C at mid height: two grooves", len(grooves()) == 2, grooves())
    h.check("C Coil 1, Mirror 1", t.titles()[-2:] == ["Coil 1", "Mirror 1"], t.titles())
    all_ok("C mirror:")
    s["v_pair"] = vol()
    s["faces"] = len(screw().Shape.Faces)
    Gui.Selection.clearSelection()
    ps.menu("Circular Pattern")


c_pattern.done = lambda: pattern_panel() is not None
c_pattern.done_what = "the Circular Pattern dialog is open"


def c_pattern_coil():
    from Fission180Tests.gui import pattern_steps as ps

    ps.timeline_click("Coil 1")


def c_pattern_mirror():
    from Fission180Tests.gui import pattern_steps as ps

    ps.timeline_click("Mirror 1")


def c_axis_box():
    from Fission180Tests.gui import pattern_steps as ps

    q = pattern_panel()
    h.check("C two features picked", len(q.options["objects"]) == 2, q.options["objects"])
    ps.click_box("axis")


def c_axis():
    pl.pick_in_browser("Z_Axis")


def c_quantity():
    import time

    from Fission180Tests.gui import pattern_steps as ps

    q = pattern_panel()
    axis = q.options.get("axis")
    h.check("C the Z axis", axis is not None and getattr(axis[0], "Role", "") == "Z_Axis", axis)
    s["typed"] = time.time()
    ps.type_quantity(q.quantity, 25)


def c_light():
    import time

    q = pattern_panel()
    took = time.time() - s["typed"]
    h.check("C Quantity 25", q.options["quantity"] == 25, q.options["quantity"])
    h.check("C the 25 copies are previewed light (24 shaded copies)", q.light, q.info.text())
    h.check("C the dialog says that OK builds them", "OK" in q.info.text(), q.info.text())
    h.speed_check("C the dialog answered within 10 s", took < 10.0 * h.SLOWDOWN, took)
    h.shot("C-knurl-light")
    s["pressed"] = time.time()
    s["runs"] = progress()["runs"]
    h.task_button("OK")


c_light.done = lambda: pattern_panel() is None
c_light.done_what = "the knurl to be built (a progress window says so) and the dialog to close"
c_light.timeout_s = 600


def grooves(z=-5.0, radius=19.85):
    """The middles (degrees) of the dips a person sees going once round the knob at height z
    just under its rim (a slice of the part there): the grooves."""
    points = []
    for wire in screw().Shape.slice(V(0, 0, 1), z):
        for edge in wire.Edges:
            for p in edge.discretize(Distance=0.02):
                points.append((math.degrees(math.atan2(p.y, p.x)) % 360.0, math.hypot(p.x, p.y)))
    points = sorted(p for p in points if p[1] > 15.0)  # the knob's rim, not a hole
    if not points:
        return []
    dips = [a for a, r in points if r < radius]
    if not dips:
        return []
    runs = [[dips[0]]]
    for a in dips[1:]:
        if a - runs[-1][-1] > 0.5:
            runs.append([a])
        else:
            runs[-1].append(a)
    if len(runs) > 1 and runs[0][0] + 360.0 - runs[-1][-1] <= 0.5:
        runs[0] = runs.pop() + [x + 360.0 for x in runs[0]]
    return sorted(round(((r[0] + r[-1]) / 2.0) % 360.0, 2) for r in runs)


def progress():
    from fission180 import pattern_progress

    return pattern_progress.STATE


def c_knurled():
    import time

    took = time.time() - s["pressed"]
    shape = screw().Shape
    removed = s["v_knob"] - vol()
    pair = s["v_knob"] - s["v_pair"]
    h.check(
        "C 25 pairs of grooves, crossing their neighbours (less than 25 pairs apart)",
        10.0 * pair < removed < 25.0 * pair,
        (removed, pair),
    )
    found = grooves()
    h.check("C at mid height: 50 grooves round the knob", len(found) == 50, found)
    gaps = [round((b - a) % 360.0, 1) for a, b in zip(found, found[1:] + found[:1])]
    h.check("C ...7.2 degrees apart", all(abs(g - 7.2) < 0.6 for g in gaps), gaps)
    h.check("C one valid solid", shape.isValid() and len(shape.Solids) == 1)
    h.check("C built outside the window's process, once", progress()["runs"] == s["runs"] + 1)
    h.check(
        "C the knurl took under 2 minutes (the report: never finished)",
        took < 120.0 * h.SLOWDOWN,
        took,
    )
    App.Console.PrintMessage("[Fission 180] REPLAY geocache: the knurl took %.1f s\n" % took)
    h.check("C Circular Pattern 1 ends the timeline", t.titles()[-1] == "Circular Pattern 1")
    all_ok("C knurl:")
    s["v_knurl"] = vol()
    h.fit()
    h.shot("C-knurl")


# == D: the Top Cap =================================================================================
CAP_IN, CAP_OUT = 16.5, 19.5  # the cap's wall: 33 inside (on the screw), 3 thick
CAP_Z0, CAP_TOP, CAP_INSIDE = 30.0, 54.0, 51.0  # (made above the screw, as a separate body)
# the profile in the Front sketch (x along X, y along Z), drawn freehand a little off
ROUGH = [(17.2, 31.3), (20.4, 31.3), (20.4, 55.2), (0.0, 55.2), (0.0, 51.8), (17.2, 51.8)]


def cap():
    return r.doc().getObject(s["cap"]) if s.get("cap") else None


def d_sketch():
    Gui.Selection.clearSelection()
    h.fit()
    h.ribbon("Create Sketch")


def d_front():
    pl.pick_in_browser("XZ_Plane")  # Front


d_front.done = lambda: h.in_sketch() is not None
d_front.done_what = "the sketch on the Front plane is open"


def d_line():
    sk = r.sk()
    s["cap_sketch"] = sk.Name
    h.check(
        "D the sketch is on the Front (XZ) plane", sk.AttachmentSupport[0][0].Role == "XZ_Plane"
    )
    r.zoom_on(r.g(V(10, 43, 0)), 40.0)
    s["geo0"] = len(sk.Geometry)
    h.press("l")


def line_click(k):
    def step():
        x, y = ROUGH[k % len(ROUGH)]
        r.sclick(V(x, y, 0))

    return r.named(step, "d_line_%d" % k)


def d_lines_done():
    r.esc()
    r.esc()
    lines = [g for i, g in r.geo("Part::GeomLineSegment") if i >= s["geo0"]]
    h.check("D six lines", len(lines) == 6, len(lines))
    # Each line is held level or upright by what the Line tool inferred: its own Horizontal /
    # Vertical, or both of its ends put on the same sketch axis (a short line drawn along the
    # Y axis: on GitHub's renderer the tool inferred "on the axis" for both ends instead of
    # Vertical, which holds it upright just the same; fix-5's reading of CI run #76).
    # An end is on an axis when it was put there itself or is tied (Coincident) to a point
    # that was: the line drawn down the Y axis starts at the end of the line before, which
    # was put on the axis, so only its far end is put there (on GitHub's screen, 770 pixels
    # tall, CI #78; this screen made 770 tall draws the same: nothing of the model under the
    # pointer, no projection; wave 7, fix-7).
    held = []
    on_axis = {}  # (curve, end) -> the axes it is on
    for _i, c in r.cons(("PointOnObject",)):
        if c.Second in (-1, -2):
            on_axis.setdefault((c.First, c.FirstPos), set()).add(c.Second)
    tied = [((c.First, c.FirstPos), (c.Second, c.SecondPos)) for _i, c in r.cons(("Coincident",))]
    grew = True
    while grew:
        grew = False
        for a, b in tied:
            both = on_axis.get(a, set()) | on_axis.get(b, set())
            for end in (a, b):
                if both - on_axis.get(end, set()):
                    on_axis[end] = set(both)
                    grew = True
    kinds = {c.First: c.Type for _i, c in r.cons(("Horizontal", "Vertical"))}
    for i, g in r.geo("Part::GeomLineSegment"):
        if i < s["geo0"]:
            continue
        both = on_axis.get((i, 1), set()) & on_axis.get((i, 2), set())
        held.append(kinds.get(i) or ("on an axis" if both else None))
    h.check("D each line is level or upright by inference", all(held) and len(held) == 6, held)
    r.sketch_clean("D drawn:")
    s["lines"] = [i for i, _g in r.geo("Part::GeomLineSegment") if i >= s["geo0"]]
    h.press("d")


def cap_line(k):
    return r.sk().Geometry[s["lines"][k]]


def mid(g):
    return V((g.StartPoint.x + g.EndPoint.x) / 2.0, (g.StartPoint.y + g.EndPoint.y) / 2.0, 0)


def corner(k):
    g = cap_line(k)
    return V(g.StartPoint.x, g.StartPoint.y, 0)


def dim_line(k, value, offset):
    """D on line k, placed `offset` from its middle, the value typed."""

    def pick():
        r.sclick(mid(cap_line(k)))

    def place():
        r.sclick(mid(cap_line(k)) + offset)

    def typed():
        h.check("D the value box is open (line %d)" % k, r.value_editor() is not None)
        r.keyboard(value)
        r.enter()

    return [
        r.named(pick, "d_dim_line_%d_pick" % k),
        r.named(place, "d_dim_line_%d_place" % k),
        r.named(typed, "d_dim_line_%d_type" % k),
    ]


def dim_origin(name, value, across):
    """D from the origin to the profile's first corner: across (placed below) or up
    (placed to the left)."""

    def pick():
        r.sclick(corner(0))

    def origin():
        r.sclick(V(0, 0, 0))

    def place():
        c = corner(0)
        if across:
            r.sclick(V(c.x / 2.0, -4.0, 0))
        else:
            r.sclick(V(-4.0, c.y / 2.0, 0))

    def typed():
        h.check("D the value box is open (%s)" % name, r.value_editor() is not None)
        r.keyboard(value)
        r.enter()

    return [
        r.named(pick, "d_dim_%s_pick" % name),
        r.named(origin, "d_dim_%s_origin" % name),
        r.named(place, "d_dim_%s_place" % name),
        r.named(typed, "d_dim_%s_type" % name),
    ]


def d_profile_done():
    r.esc()
    want = [
        (CAP_IN, CAP_Z0),
        (CAP_OUT, CAP_Z0),
        (CAP_OUT, CAP_TOP),
        (0.0, CAP_TOP),
        (0.0, CAP_INSIDE),
        (CAP_IN, CAP_INSIDE),
    ]
    got = [(round(corner(k).x, 6), round(corner(k).y, 6)) for k in range(6)]
    h.check("D the profile has the cap's sizes", got == want, got)
    r.sketch_clean("D")
    h.check("D the profile is fully constrained", r.dof() == 0, r.dof())
    h.shot("D-profile")
    h.ribbon("Finish Sketch")


d_profile_done.done = lambda: h.in_sketch() is None
d_profile_done.done_what = "Finish Sketch closed the sketch"


def revolve_panel():
    from fission180 import revolve_ui

    p = revolve_ui.RevolvePanel.last
    return p if p is not None and not p._closed else None


def d_revolve():
    h.fit()
    Gui.Selection.clearSelection()
    h.ribbon("Revolve")


d_revolve.done = lambda: revolve_panel() is not None
d_revolve.done_what = "the Revolve dialog is open"


def d_axis_box():
    from Fission180Tests.gui import pattern_steps as ps  # noqa: F401 (click_box is generic)

    p = revolve_panel()
    h.check("D the profile is taken by itself", len(p.profiles) == 1, p.profiles)
    if p.active != "axis":
        from Fission180Tests.gui import widget_input as w

        w.click(p.fields["axis"].button)


def d_axis():
    pl.pick_in_browser("Z_Axis")


def d_revolve_ok():
    p = revolve_panel()
    axis = p.axis
    h.check(
        "D the Z axis from the browser",
        axis is not None and getattr(axis[0], "Role", "") == "Z_Axis",
        axis,
    )
    h.caught_up(p)
    s["operation"] = p.operation.currentText()
    h.task_button("OK")


d_revolve_ok.done = lambda: revolve_panel() is None
d_revolve_ok.done_what = "OK finished the Revolve"
d_revolve_ok.timeout_s = 120


def d_cap():
    made = r.solid_bodies()
    h.check("D touching nothing: a New Body", s["operation"] == "New Body", s["operation"])
    h.check("D two bodies", len(made) == 2, [b.Label for b in made])
    new = [b for b in made if b.Name != s["screw"]]
    if not new:
        return
    s["cap"] = new[0].Name
    want = math.pi * (CAP_OUT**2 - CAP_IN**2) * (
        CAP_INSIDE - CAP_Z0
    ) + math.pi * CAP_OUT**2 * (CAP_TOP - CAP_INSIDE)
    h.check("D the cap's size", r.near(cap().Shape.Volume, want, 1e-6), (cap().Shape.Volume, want))
    h.check("D the screw is untouched", r.near(vol(), s["v_knurl"], 1e-9), vol())
    all_ok("D revolve:")
    t.click_eye("Bottom Screw")  # the screw is in the way of a look into the cap


def d_screw_hidden():
    h.check("D the eye hides the screw", not screw().Visibility)
    r.look_from(V(-1, 1, 1.4))  # from below: into the cap
    Gui.Selection.clearSelection()
    r.menu("CREATE", "Thread")


d_screw_hidden.done = lambda: thread_panel() is not None
d_screw_hidden.done_what = "the Thread dialog is open"


def d_inner_wall():
    # the far side of the inner wall, seen through the cap's open end (a click on a wall
    # with another wall in front of it picks the front one, in Fusion too)
    a = math.radians(135)
    h.click(V(CAP_IN * math.cos(a), CAP_IN * math.sin(a), CAP_Z0 + 8.0))


def d_thread_values():
    from Fission180Tests.gui import hole_steps as hs

    p = thread_panel()
    if not h.check("D the inner wall is threaded", p.target is not None, hs.message(p)):
        return
    text = p.info.text()
    h.check("D the dialog says: inside thread, 33 mm", "nside" in text and "33" in text, text)
    s["designation"] = p.designation.currentText()
    # Fusion starts a thread with the last one's settings: Modeled is ticked already (the
    # book says to tick it: a person looks and leaves it)
    h.check("D Modeled is ticked from the last thread", p.modeled.isChecked())
    if not p.modeled.isChecked():
        hs.click_checkbox(p.modeled)


def d_thread_full_length():
    from Fission180Tests.gui import hole_steps as hs

    p = thread_panel()
    h.check("D Full Length is ticked at first", p.full_length.isChecked())
    hs.click_checkbox(p.full_length)


def d_thread_length():
    from Fission180Tests.gui import dialog_input as ui

    p = thread_panel()
    h.check("D Full Length unticked: Thread Length shows", p.length.widget.isVisible())
    ui.type_into(p.length.widget, "18")


def d_thread_ok():
    p = thread_panel()
    h.caught_up(p)
    from Fission180Tests.gui import hole_steps as hs

    h.check(
        "D Modeled, 18 long",
        p.modeled.isChecked() and not p.full_length.isChecked() and r.near(p.length.value(), 18),
        (p.modeled.isChecked(), p.full_length.isChecked(), p.length.value(), hs.message(p)),
    )
    h.task_button("OK")


d_thread_ok.done = lambda: thread_panel() is None
d_thread_ok.done_what = "OK finished the Thread"
d_thread_ok.timeout_s = 180


def d_threaded():
    shape = cap().Shape
    h.check("D the cap is one valid solid", shape.isValid() and len(shape.Solids) == 1)
    before = math.pi * (CAP_OUT**2 - CAP_IN**2) * (
        CAP_INSIDE - CAP_Z0
    ) + math.pi * CAP_OUT**2 * (CAP_TOP - CAP_INSIDE)
    # Fusion gives a threaded hole the thread's minor diameter and cuts the thread from
    # there (Autodesk forum "BUG thread changes the hole diameter": as designed), so the
    # cap gains material where the 18 mm are threaded
    h.check("D the 18 mm are threaded", shape.Volume > before + 50.0, (shape.Volume, before))
    bb = shape.BoundBox
    h.check(
        "D the cap keeps its outside",
        r.near(bb.ZMax, CAP_TOP, 1e-6) and r.near(bb.XMax, CAP_OUT, 1e-3),
    )
    # the nearest standard size, as Fusion offers it (Autodesk tech tip, thread_tables.closest;
    # the report's M36x3 was the older tap-drill rule): it fits the screw's M33x3.5
    h.check("D M33x3.5 is offered for a 33 bore", s["designation"] == "M33x3.5", s["designation"])
    all_ok("D thread:")
    h.shot("D-cap")
    t.click_eye("Bottom Screw")


def d_screw_shown():
    h.check("D the eye shows the screw again", screw().Visibility)
    h.fit()


# == E: the words wrapped round the cap, the mark ===================================================
WORDS = "UNSCREW CAP\nOFFICIAL GEOCACHE."  # (two lines: the stand-in cap is smaller)


def construct_panel():
    from fission180 import construct_ui, taskui

    p = taskui.current()
    return p if isinstance(p, construct_ui.ConstructPanel) else None


def e_plane():
    Gui.Selection.clearSelection()
    h.fit()
    h.ribbon("Offset Plane")


e_plane.done = lambda: construct_panel() is not None
e_plane.done_what = "the Offset Plane dialog is open"


def e_plane_xz():
    pl.pick_in_browser("XZ_Plane")


def e_plane_distance():
    from Fission180Tests.gui import dialog_input as ui

    p = construct_panel()
    h.check("E the Front plane is the reference", p.datum is not None)
    ui.type_into(p.distance.widget, "-30")


def e_plane_ok():
    p = construct_panel()
    h.caught_up(p)
    place = p.datum.getGlobalPlacement()
    s["plane_y"] = place.Base.y
    h.check("E the plane is 30 from the Front plane", r.near(abs(place.Base.y), 30.0), place.Base)
    h.task_button("OK")


e_plane_ok.done = lambda: construct_panel() is None
e_plane_ok.done_what = "OK finished the Offset Plane"


def offset_plane():
    found = [o for o in r.doc().Objects if o.TypeId == "PartDesign::Plane"]
    return found[-1] if found else None


def e_sketch():
    h.check("E Plane 1 is in the design", offset_plane() is not None)
    h.ribbon("Create Sketch")


def e_sketch_plane():
    t.click_row(offset_plane().Label)


e_sketch_plane.done = lambda: h.in_sketch() is not None
e_sketch_plane.done_what = "the sketch on the offset plane is open"


def text_dialog():
    from Fission180Tests.gui import text_input as ti

    return ti.dialog()


def e_text():
    from Fission180Tests.gui import text_input as ti

    sk = r.sk()
    s["word_sketch"] = sk.Name
    h.check(
        "E the sketch is on the offset plane",
        r.near(sk.getGlobalPlacement().Base.y, s["plane_y"], 1e-6),
        sk.getGlobalPlacement(),
    )
    s["texts"] = list(ti.texts(sk))
    r.zoom_on(r.g(V(0, 42, 0)), 60.0)
    ti.open_text_tool()


e_text.done = lambda: text_dialog() is not None
e_text.done_what = "the Text dialog is open"


def e_corner_1():
    r.sclick(V(-50, 33, 0))  # (wide enough for each line: the frame wraps words)


def e_corner_2():
    r.sclick(V(50, 51, 0))


def e_type():
    from Fission180Tests.gui import text_input as ti

    d = text_dialog()
    h.check("E the frame is placed", d.frame_placed)
    ti.type_text(WORDS)
    ti.type_field(d.height, "7.5")
    ti.press_button(d.h_buttons["center"])
    ti.press_button(d.v_buttons["middle"])


def e_text_ok():
    from Fission180Tests.gui import text_input as ti

    d = text_dialog()
    h.check("E nothing is refused", not d.message.text(), d.message.text())
    ti.ok()


e_text_ok.done = lambda: text_dialog() is None
e_text_ok.done_what = "OK closed the Text dialog"


def e_finish():
    from Fission180Tests.gui import text_input as ti

    new = [o for o in ti.texts(r.sk()) if o not in s["texts"]]
    h.check("E the text is in the sketch", len(new) == 1, new)
    s["words"] = new[0].Name if new else None
    if new:
        h.check("E ...7.5 high", r.near(new[0].TextHeight.Value, 7.5), new[0].TextHeight)
        h.check("E ...two lines", new[0].ResolvedText == WORDS, new[0].ResolvedText)
    h.ribbon("Finish Sketch")


e_finish.done = lambda: h.in_sketch() is None
e_finish.done_what = "Finish Sketch closed the sketch"


def emboss_panel():
    from fission180 import emboss_ui

    p = emboss_ui.EmbossPanel.last
    return p if p is not None and not p._closed and Gui.Control.activeDialog() else None


def e_emboss():
    Gui.Selection.clearSelection()
    r.look_from(V(0, 1, 0) if s["plane_y"] < 0 else V(0, -1, 0))  # facing the words
    r.menu("CREATE", "Emboss")


e_emboss.done = lambda: emboss_panel() is not None
e_emboss.done_what = "the Emboss dialog is open"


def e_letter():
    from Fission180Tests.gui import text_input as ti

    words = r.doc().getObject(s["words"])
    sk = r.doc().getObject(s["word_sketch"])
    x, y = ti.middle_of_first_letter(words)
    h.click(sk.getGlobalPlacement().multVec(V(x, y, 0)))


def e_face():
    p = emboss_panel()
    h.check("E the words are the profile", len(p.profiles) == 1, p.profiles)
    h.check("E now it waits for the faces", p.active == "faces", p.active)
    h.shot("E-faces")
    s["v_cap"] = cap().Shape.Volume
    # the cap's side beside the words, where the offset plane is in front of it (Fusion
    # picks the face through the plane: the Faces box takes faces only)
    side = -1.0 if s["plane_y"] < 0 else 1.0
    a = math.radians(10.0)
    h.click(V(CAP_OUT * math.sin(a), side * CAP_OUT * math.cos(a), CAP_Z0 + 0.8))  # below the words


def e_depth():
    from Fission180Tests.gui import dialog_input as ui

    p = emboss_panel()
    h.check(
        "E the cap's side is picked (the report: the plane took the click)",
        len(p.face_names) == 1,
        p.face_names,
    )
    ui.type_into(p.depth.widget, "0.75")


def e_emboss_ok():
    p = emboss_panel()
    h.caught_up(p)
    h.check("E nothing is refused", not p.message.text(), p.message.text())
    h.check("E the letters stand out", cap().Shape.Volume > s["v_cap"] + 5.0, cap().Shape.Volume)
    h.shot("E-emboss")
    h.task_button("OK")


e_emboss_ok.done = lambda: emboss_panel() is None
e_emboss_ok.done_what = "OK finished the Emboss"
e_emboss_ok.timeout_s = 300


def e_embossed():
    shape = cap().Shape
    h.check("E the cap is one valid solid", shape.isValid() and len(shape.Solids) == 1)
    bb = shape.BoundBox
    h.check(
        "E the letters stand 0.75 off the cap's side",
        r.near(max(abs(bb.YMin), abs(bb.YMax)), CAP_OUT + 0.75, 1e-3),
        (bb.YMin, bb.YMax),
    )
    all_ok("E emboss:")
    s["v_cap"] = shape.Volume
    h.fit()


def e_svg_sketch():
    from Fission180Tests.gui import insert_steps as ins

    ins.use_file(ins.fixture("replay_geocache_mark.svg"))
    Gui.Selection.clearSelection()
    h.ribbon("Create Sketch")


def e_svg_plane():
    t.click_row(offset_plane().Label)


e_svg_plane.done = lambda: h.in_sketch() is not None
e_svg_plane.done_what = "a second sketch on the offset plane is open"


def svg_panel():
    from fission180 import taskui

    p = taskui.current()
    return p if p is not None and getattr(p, "title", "") == "Insert SVG" else None


def e_svg():
    s["svg_sketch"] = r.sk().Name
    r.menu("INSERT", "Insert SVG")


e_svg.done = lambda: svg_panel() is not None
e_svg.done_what = "the Insert SVG dialog is open"


def e_svg_values():
    from Fission180Tests.gui import insert_steps as ins

    p = svg_panel()
    h.check("E the curves go into the open sketch", "Sketch" in p.plane_label.text())
    h.check("E no question about 96 dpi (FreeCAD's own box)", not h.popups(), h.popups())
    ins.set_spin(p.scale, 0.3)
    ins.set_check(p.flip_h, True)
    ins.set_check(p.flip_v, True)
    ins.type_value(p.dx, "-15")
    ins.type_value(p.dy, "2")


def e_svg_ok():
    sk = r.doc().getObject(s["svg_sketch"])
    h.check("E the mark's curves are in the sketch", sk.GeometryCount >= 4, sk.GeometryCount)
    h.task_button("OK")


e_svg_ok.done = lambda: svg_panel() is None and h.in_sketch() is not None
e_svg_ok.done_what = "OK closed Insert SVG and the sketch is open again"


def e_svg_done():
    from Fission180Tests.gui import insert_steps as ins

    box = r.sk().Shape.BoundBox
    # the outer ring is 52 px across: at 96 per inch 13.76 mm; at 0.3: 4.13 mm
    size = 52 * 25.4 / 96 * 0.3
    h.check(
        "E the mark is 0.3 of its size",
        abs(box.XLength - size) < 0.05 and abs(box.ZLength - size) < 0.05,
        (box.XLength, box.ZLength, size),
    )
    ins.no_file()
    h.ribbon("Finish Sketch")


e_svg_done.done = lambda: h.in_sketch() is None
e_svg_done.done_what = "Finish Sketch closed the sketch"


# == F: a group in the timeline, a section, undo, save, open again =================================
def f_group_first():
    s["titles"] = t.titles()
    t.click(s["titles"][0])


def f_group_last():
    t.click(s["titles"][-1], QtCore.Qt.ShiftModifier)


def f_group():
    t.menu(s["titles"][-1], "Create Group")


def f_grouped():
    from fission180 import timeline_ops as ops

    groups = {i.group for i in ops.timeline(r.doc(), deps=False).items}
    h.check("F every step is in one group", len(groups) == 1 and "" not in groups, groups)
    gid = groups.pop() if len(groups) == 1 else None
    h.check("F the timeline shows the group", gid and t.tl().group_button(gid) is not None)
    all_ok("F group:")
    h.click_empty()


def section_panel():
    from fission180 import section_ui, taskui

    p = taskui.current()
    return p if isinstance(p, section_ui.SectionPanel) else None


def f_section():
    Gui.Selection.clearSelection()
    h.fit()
    h.ribbon("Section Analysis")


f_section.done = lambda: section_panel() is not None
f_section.done_what = "the Section Analysis dialog is open"


def f_section_plane():
    import time

    s["section_t0"] = time.time()

    pl.pick_in_browser("XZ_Plane")


f_section_plane.timeout_s = 600


def f_section_ok():
    import time

    took = time.time() - s["section_t0"]
    App.Console.PrintMessage("[Fission 180] REPLAY geocache: the section took %.1f s\n" % took)
    # (it took 35 s: Create Group had marked every step for rebuilding, the knurl too)
    h.check("F the section shows within 10 s", took < 10.0 * h.SLOWDOWN, took)
    p = section_panel()
    h.caught_up(p)
    h.task_button("OK")


f_section_ok.done = lambda: section_panel() is None
f_section_ok.done_what = "OK finished the Section Analysis"


def volumes():
    return (round(vol(), 3), round(cap().Shape.Volume, 3))


def f_sectioned():
    from fission180 import section

    found = list(section.sections(r.doc()))
    h.check("F one section", len(found) == 1, [o.Label for o in found])
    h.check("F the browser has an Analysis folder", "Analysis" in " ".join(t.labels()), t.labels())
    s["volumes"] = volumes()
    h.shot("F-section")


def f_undone():
    from fission180 import section

    h.check("F Ctrl+Z takes the section away", not list(section.sections(r.doc())))
    h.check("F ...and nothing else", volumes() == s["volumes"], volumes())


def f_redone():
    from fission180 import section

    h.check("F Ctrl+Y brings it back", len(list(section.sections(r.doc()))) == 1)
    all_ok("F redo:")


def f_reopened():
    made = r.solid_bodies()
    labels = sorted(b.Label for b in made)
    h.check(
        "F reopened: the screw and the cap", len(made) == 2 and "Bottom Screw" in labels, labels
    )
    s["screw"] = [b for b in made if b.Label == "Bottom Screw"][0].Name
    s["cap"] = [b for b in made if b.Label != "Bottom Screw"][0].Name
    h.check("F reopened: the same solids", volumes() == s["volumes"], (volumes(), s["volumes"]))
    all_ok("F reopened:")
    h.shot("F-reopened")


def tip_shown(tag, body):
    """What the view draws of a body is its Tip (the last step), and the browser's eye says
    the body is shown."""
    from fission180 import body_visibility

    drawn = [
        o.Label
        for o in body.Group
        if o.isDerivedFrom("PartDesign::Feature") and o.ViewObject.Visibility
    ]
    h.check(
        "%s the view draws the body's last step" % tag,
        drawn == [body.Tip.Label],
        (drawn, body.Tip.Label),
    )
    h.check("%s the browser's eye shows the body" % tag, body_visibility.body_shown(body))


steps = r.home_steps()
steps += [a_cylinder, a_plane, a_ok_too_early, a_centre, a_diameter, a_height, a_rename]
steps += [a_name, a_named]
steps += [b_chamfer, b_edge, b_size, b_chamfer_ok, b_thread, b_side, b_offered, b_thread_ok]
steps += [b_drag, b_dragged, b_offset_click, b_offset_value, b_offset_ok, b_done]
steps += [c_cylinder, c_plane, c_centre, c_diameter, c_height, c_knob_ok, c_knob]
steps += [c_coil_plane, c_coil_centre, c_coil_circle, c_coil_values, c_coil_ok]
steps += [c_mirror, c_mirror_type, c_mirror_coil, c_mirror_plane_box, c_mirror_plane, c_mirror_ok]
steps += [c_pattern, c_pattern_coil, c_pattern_mirror, c_axis_box, c_axis, c_quantity, c_light]
steps += [c_knurled]
steps += [d_sketch, d_front, d_line] + [line_click(k) for k in range(7)] + [d_lines_done]
# (the inner wall before the outer one: the first dimension scales the whole sketch, and
# with the outer wall set first its top came below the inner top, crossing the profile;
# the solver moves only what a dimension pulls, in Fusion too)
steps += dim_line(0, "3", V(0, -3, 0)) + dim_line(5, "21", V(-3, 0, 0))
steps += dim_line(1, "24", V(3, 0, 0))
steps += dim_origin("radius", "16.5", True) + dim_origin("height", "30", False)
steps += [d_profile_done, d_revolve, d_axis_box, d_axis, d_revolve_ok, d_cap, d_screw_hidden]
steps += [d_inner_wall, d_thread_values, d_thread_full_length, d_thread_length, d_thread_ok]
steps += [d_threaded, d_screw_shown]
steps += [e_plane, e_plane_xz, e_plane_distance, e_plane_ok, e_sketch, e_sketch_plane, e_text]
steps += [e_corner_1, e_corner_2, e_type, e_text_ok, e_finish]
steps += [e_emboss, e_letter, e_face, e_depth, e_emboss_ok, e_embossed]
steps += [e_svg_sketch, e_svg_plane, e_svg, e_svg_values, e_svg_ok, e_svg_done]
steps += [f_group_first, f_group_last, f_group, f_grouped]
steps += [f_section, f_section_plane, f_section_ok, f_sectioned]
steps += [r.named(r.undo, "f_undo"), f_undone, r.named(r.redo, "f_redo"), f_redone]
steps += r.save_steps("f", "Geocache Hide") + r.reopen_steps("f", "Geocache Hide") + [f_reopened]

h.run("replay_07_geocache", steps, paced_by="state")
