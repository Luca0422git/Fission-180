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

h.run("replay_07_geocache", steps, paced_by="state")
