# SPDX-License-Identifier: LGPL-2.1-or-later
"""Book replay, Project 6 "Play Brick" (Mastering Autodesk Fusion 2nd ed., pp 68-75; the
book parity report, lines 1218-1269). One design from the first step to the last, the way
the book writes it, with a new profile's defaults (Snap, Scale entire sketch at first
dimension, the layout grid, the first component grounded). Real input only.

  A  CREATE > Box on the Top plane: the origin corner clicked, 31.8 Tab 15.8 Enter typed
     on the canvas, 9.6 Enter: the brick, "Body1".
  B  The stud: Create Sketch on the top face, a circle D 4.8, dimensioned 3.9 / 3.9 from
     the origin, Finish Sketch, E 1.8 (Join).
  C  MODIFY > Draft: the top face as the pull direction, the stud's side, 1 degree. First
     an OK with no face: refused, the pull direction stays.
  D  Rectangular Pattern of Features (Extrude + Draft picked in the timeline), the two
     directions clicked on the brick's EDGES, Spacing, 4 x 8 mm and 2 x 8 mm: 8 studs.
  E  MODIFY > Shell: the bottom face, Inside Thickness 1.2.
  F  A sketch on a stud: CREATE > Text "PLAY" (Height 1, bold, centred, middle), Tangent
     between each of the frame's lines and the stud's projected circle; E the letters 0.1
     Join; Rectangular Pattern of that extrude.
  G  M (Move): Body1 picked in the browser, Y Angle 180: the brick turns over in place.
  H  A sketch on the inner face: three pairs of concentric circles, Equal, D 6.51 and 4.8;
     E the three rings 8.4 (Join); Draft on the tubes; the red plastic appearance; the
     brick turned back; Ctrl+Z / Ctrl+Y runs; save and reopen.
"""

import math

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import primitive_input as pi
from Fission180Tests.gui import replay_c_steps as r

V = App.Vector
s = {}
L, W, H = 31.8, 15.8, 9.6
BOX = L * W * H
STUD_R, STUD_H = 2.4, 1.8
PITCH = 8.0


def placing_boxes(p):
    return {
        k[len(p.PLACING) :]: b
        for k, b in p.value_boxes.boxes.items()
        if k.startswith(p.PLACING) and b.isVisible()
    }


# == A: the brick ==================================================================================
def a_box():
    r.defaults_are_on("A")
    h.fit()
    pi.menu("Box")


a_box.done = lambda: pi.panel("BoxPanel") is not None
a_box.done_what = "the Box dialog is open"


def a_plane():
    pl.click_square("XY_Plane")


def a_corner():
    pl.click_on_plane(V(0, 0, 0))


def a_length():
    p = pi.panel("BoxPanel")
    h.wait_for(lambda: len(placing_boxes(p)) == 2, "the Length and Width boxes on the canvas")
    r.keyboard("31.8")
    box = placing_boxes(p).get("length")
    h.check(
        "A 31.8 typed on the canvas goes into the Length box",
        box is not None and box.hasFocus() and box.text().strip() == "31.8",
        (r.focus_name(), box.text() if box is not None else None),
    )
    r.tab()


def a_width():
    p = pi.panel("BoxPanel")
    box = placing_boxes(p).get("width")
    h.check("A Tab goes to the Width box on the canvas", box is not None and box.hasFocus())
    r.keyboard("15.8")
    r.enter()


def a_height():
    p = pi.panel("BoxPanel")
    h.check("A Enter placed the rectangle", p is not None and p.state == "ready", p and p.state)
    r.keyboard("9.6")
    r.enter()


a_height.done = pi.no_dialog
a_height.done_what = "Enter finished the Box"


def a_done():
    made = r.solid_bodies()
    h.check("A one body", len(made) == 1, [b.Label for b in r.bodies()])
    if not made:
        return
    s["body"] = made[0].Name
    h.check("A 31.8 x 15.8 x 9.6", r.near(made[0].Shape.Volume, BOX), made[0].Shape.Volume)
    h.check("A at the origin, upwards", r.box_near(made[0].Shape, [0, 0, 0, L, W, H]))
    h.check("A the body is Body1", made[0].Label == "Body1", made[0].Label)
    h.check("A the timeline has the Box", len(r.timeline()) == 1, r.timeline())
    h.fit()
    h.shot("A-brick")


def body():
    return r.doc().getObject(s["body"])


def vol():
    return body().Shape.Volume


# == B: the stud ===================================================================================
def b_sketch():
    h.ribbon("Create Sketch")


def b_face():
    h.click(V(20, 10, H))  # the brick's top face


b_face.done = lambda: h.in_sketch() is not None
b_face.done_what = "the sketch on the top face is open"


def b_circle():
    sk = r.sk()
    s["stud_sketch"] = sk.Name
    place = sk.getGlobalPlacement()
    h.check("B the sketch is on the top face", r.near(place.Base.z, H), place.Base)
    s["geo0"] = len(sk.Geometry)
    h.press("c")


def b_centre():
    r.sclick(V(6, 6, 0))


def b_diameter():
    r.keyboard("4.8")
    r.enter()


def b_drawn():
    circles = [c for c in r.geo("Part::GeomCircle") if c[0] >= s["geo0"]]
    h.check("B one circle drawn", len(circles) == 1, circles)
    if circles:
        s["circle"] = circles[0][0]
        h.check("B ...4.8 across", r.near(circles[0][1].Radius, STUD_R), circles[0][1].Radius)
    r.esc()
    r.esc()
    h.check("B Esc ends the tool and keeps the sketch open", r.sk() is not None)
    h.press("d")


def stud_centre():
    c = r.sk().Geometry[s["circle"]].Center
    return V(c.x, c.y, 0)


def b_dim_x_pick():
    r.sclick(stud_centre())


def b_dim_x_origin():
    r.sclick(V(0, 0, 0))


def b_dim_x_place():
    r.sclick(V(stud_centre().x / 2.0, -3.0, 0))


def b_dim_x_value():
    h.check("B the dimension's value box is open", r.value_editor() is not None, r.focus_name())
    r.keyboard("3.9")
    r.enter()


def b_dim_y_pick():
    c = stud_centre()
    h.check("B the circle is 3.9 from the origin along X", r.near(c.x, 3.9), c)
    r.sclick(c)


def b_dim_y_place():
    r.sclick(V(-3.0, stud_centre().y / 2.0, 0))


def b_dim_y_value():
    h.check("B the dimension's value box is open", r.value_editor() is not None, r.focus_name())
    r.keyboard("3.9")
    r.enter()


def b_finish():
    c = stud_centre()
    h.check("B the circle is at 3.9 / 3.9", r.near(c.x, 3.9) and r.near(c.y, 3.9), c)
    r.sketch_clean("B")
    h.check("B the circle is fully constrained", r.dof() == 0, r.dof())
    r.esc()
    h.ribbon("Finish Sketch")


b_finish.done = lambda: h.in_sketch() is None
b_finish.done_what = "Finish Sketch closed the sketch"


def b_profile():
    sk = r.doc().getObject(s["stud_sketch"])
    h.check("B the sketch stays shown until it is used (Fusion)", sk.Visibility is True)
    h.fit()
    h.click(V(3.9, 3.9, H))


def b_extrude():
    h.press("e")


def b_distance():
    from Fission180Tests.gui import arrow_input as arrows

    arrows.give_distance("1.8")
    p = r.panel()
    s["operation"] = p.operation.currentText() if p is not None else None
    h.task_button("OK")


b_distance.done = r.no_dialog
b_distance.done_what = "OK finished the Extrude"


def b_done():
    import Part

    made = r.solid_bodies()
    h.check("B still one body", len(made) == 1, [b.Label for b in r.bodies()])
    h.check("B on the brick the stud is a Join", s.get("operation") == "Join", s.get("operation"))
    stud = math.pi * STUD_R**2 * STUD_H
    h.check("B the stud is 4.8 across and 1.8 high", r.near(vol(), BOX + stud), (vol(), BOX + stud))
    h.check("B it stands on the brick", r.box_near(body().Shape, [0, 0, 0, L, W, H + STUD_H]))
    centre = body().Shape.common(Part.makeCylinder(0.5, 1.0, V(3.9, 3.9, H + 0.2))).Volume
    h.check("B ...at 3.9 / 3.9", r.near(centre, math.pi * 0.25), centre)
    h.check("B the timeline: Box, Sketch, Extrude", len(r.timeline()) == 3, r.timeline())
    s["v_stud"] = vol()
    r.nothing_broken("B")


# == C: Draft ======================================================================================
def draft_panel():
    from Fission180Tests.gui import shell_draft_steps as sd

    return sd.draft_panel()


def c_draft():
    from Fission180Tests.gui import shell_draft_steps as sd

    Gui.Selection.clearSelection()
    sd.modify_menu("Draft")


c_draft.done = lambda: draft_panel() is not None
c_draft.done_what = "the Draft dialog is open"


def c_pull():
    p = draft_panel()
    h.check("C Draft waits for the pull direction", p.active == "plane", p.active)
    h.click(V(20, 10, H))


def c_ok_too_early():
    p = draft_panel()
    h.check("C the top face is the pull direction", p.plane_ref is not None, p.plane_ref)
    h.check("C the Faces box takes the clicks now", p.active == "faces", p.active)
    s["pull"] = p.plane_box.button.text()
    h.task_button("OK")  # no face yet


def c_refused():
    from Fission180Tests.gui import widget_input as w

    p = draft_panel()
    if not h.check("C OK with no face: the dialog stays and says why", p is not None):
        return
    h.check("C ...it names the faces", "faces" in p.message.text().lower(), p.message.text())
    h.check(
        "C ...and the pull direction is kept (the report: it was cleared)",
        p.plane_ref is not None and p.plane_box.button.text() == s["pull"],
        p.plane_box.button.text(),
    )
    w.click(p.faces_box.button)  # the report's step: the Faces box, then the face


def c_side():
    h.click(V(3.9 + STUD_R * math.cos(-0.6), 3.9 + STUD_R * math.sin(-0.6), H + 0.9))


def c_angle():
    from Fission180Tests.gui import dialog_input as di

    p = draft_panel()
    h.check("C the stud's side is the face to draft", len(p.names()) == 1, p.names())
    di.type_into(p.angle.widget, "1")
    h.caught_up(p)
    h.check("C nothing is refused", not p.message.text(), p.message.text())
    h.task_button("OK")


c_angle.done = lambda: draft_panel() is None
c_angle.done_what = "OK finished the Draft"
c_angle.timeout_s = 120


def frustum(r0, r1, height):
    return math.pi * height * (r0 * r0 + r0 * r1 + r1 * r1) / 3.0


def c_done():
    top = STUD_R - STUD_H * math.tan(math.radians(1.0))
    want = BOX + frustum(STUD_R, top, STUD_H)
    h.check(
        "C the stud narrows 1 degree from the brick's top face upwards",
        r.near(vol(), want, 1e-6),
        (vol(), want),
    )
    h.check("C the timeline has Draft 1", "Draft 1" in r.timeline(), r.timeline())
    s["v_draft"] = vol()
    s["stud"] = vol() - BOX
    r.nothing_broken("C")
    h.shot("C-draft")


# == D: Rectangular Pattern of the stud ============================================================
def pattern_panel():
    from Fission180Tests.gui import pattern_steps as ps

    return ps.panel()


def d_pattern():
    from Fission180Tests.gui import sketch_input as si

    h.fit()
    si.menu_item("CREATE", "Rectangular Pattern")


d_pattern.done = lambda: pattern_panel() is not None
d_pattern.done_what = "the Rectangular Pattern dialog is open"


def d_type():
    from Fission180Tests.gui import dialog_input as di

    di.choose(pattern_panel().pattern_type, "Features")


def d_extrude():
    from Fission180Tests.gui import pattern_steps as ps

    q = pattern_panel()
    h.check("D Pattern Type Features", q.options["pattern_type"] == "features")
    ps.timeline_click("Extrude 1")


def d_draft():
    from Fission180Tests.gui import pattern_steps as ps

    ps.timeline_click("Draft 1")


def d_direction_box():
    from Fission180Tests.gui import pattern_steps as ps

    q = pattern_panel()
    names = [o.Label for o, _s in q.options["objects"]]
    h.check("D the Extrude and the Draft are the objects", len(names) == 2, names)
    ps.click_box("direction")


def d_edge_x():
    h.click_edge(V(22.0, 0.0, H))  # the brick's long top front edge


def d_edge_y():
    q = pattern_panel()
    ref = q.options.get("direction")
    s["dir1"] = q._ref_text(ref, q._titles()) if ref else ""
    h.check(
        "D the first direction is the EDGE clicked (the report: the face beside it)",
        bool(ref) and ref[1].startswith("Edge"),
        (ref and ref[1], s["dir1"]),
    )
    # Fusion's one Axes field takes the second edge with the next click (Autodesk help
    # "Create a rectangular pattern"); Fission 180's dialog has a box per direction: the
    # second one is clicked first (NOT FIXED here: see the session log, replay-c)
    from Fission180Tests.gui import pattern_steps as ps

    ps.click_box("direction2")


def d_edge_y2():
    h.click_edge(V(L, 6.0, H))  # the short top right edge


def d_values():
    from Fission180Tests.gui import dialog_input as di
    from Fission180Tests.gui import pattern_steps as ps

    q = pattern_panel()
    ref = q.options.get("direction2")
    h.check(
        "D the second direction is the EDGE clicked",
        bool(ref) and ref[1].startswith("Edge"),
        (ref and ref[1], q._ref_text(ref, q._titles()) if ref else ""),
    )
    di.choose(q.distribution, "Spacing")
    ps.type_quantity(q.quantity, 4)
    ps.type_value(q.distance_field.widget, "8")
    ps.type_quantity(q.quantity2, 2)
    ps.type_value(q.distance2_field.widget, "8")


def d_ok():
    q = pattern_panel()
    h.caught_up(q)
    h.check("D nothing is refused", not q.message.text(), q.message.text())
    h.shot("D-pattern-dialog")
    h.task_button("OK")


d_ok.done = lambda: pattern_panel() is None
d_ok.done_what = "OK finished the pattern"
d_ok.timeout_s = 180


def stud_centres(z):
    """(x, y) of the round edges of the studs at height z, sorted."""
    found = set()
    for edge in body().Shape.Edges:
        curve = edge.Curve
        if curve.TypeId == "Part::GeomCircle" and abs(curve.Center.z - z) < 1e-6:
            found.add((round(curve.Center.x, 3), round(curve.Center.y, 3)))
    return sorted(found)


def d_done():
    want = BOX + 8 * s["stud"]
    h.check("D eight studs", r.near(vol(), want, 1e-6), (vol(), want))
    grid = sorted((3.9 + PITCH * i, 3.9 + PITCH * j) for i in range(4) for j in range(2))
    h.check("D a 4 x 2 grid 8 mm apart", stud_centres(H + STUD_H) == grid, stud_centres(H + STUD_H))
    h.check(
        "D side by side, not stacked upwards (the report: z 35)",
        r.box_near(body().Shape, [0, 0, 0, L, W, H + STUD_H]),
        r.bbox(body().Shape),
    )
    h.check("D one pattern step", r.timeline()[-1].startswith("Rectangular Pattern"), r.timeline())
    s["v_pattern"] = vol()
    r.nothing_broken("D")
    h.fit()
    h.shot("D-studs")


# == E: Shell ======================================================================================
def shell_panel():
    from Fission180Tests.gui import shell_draft_steps as sd

    return sd.shell_panel()


def e_shell():
    from Fission180Tests.gui import shell_draft_steps as sd

    r.look_from(V(1, 1, 1))  # (from below: the bottom face is in view)
    sd.modify_menu("Shell")


e_shell.done = lambda: shell_panel() is not None
e_shell.done_what = "the Shell dialog is open"


def e_bottom():
    h.click(V(16, 8, 0))


def e_thickness():
    from Fission180Tests.gui import dialog_input as di

    p = shell_panel()
    h.check("E the bottom face is picked", len(p.names()) == 1, p.names())
    di.type_into(p.inside.widget, "1.2")
    h.caught_up(p)
    h.check("E nothing is refused", not p.message.text(), p.message.text())
    h.task_button("OK")


e_thickness.done = lambda: shell_panel() is None
e_thickness.done_what = "OK finished the Shell"
e_thickness.timeout_s = 180


def e_done():
    import Part

    shape = body().Shape
    h.check("E a valid solid", shape.isValid() and len(shape.Solids) == 1)
    h.check("E the outside is unchanged", r.box_near(shape, [0, 0, 0, L, W, H + STUD_H]))
    inside = Part.makeBox(L - 2.4, W - 2.4, H - 1.2, V(1.2, 1.2, 0))
    h.check(
        "E the brick is hollow from below, walls and top 1.2 thick",
        shape.common(inside).Volume < 1e-6,
        shape.common(inside).Volume,
    )
    wall = Part.makeBox(1.2, W, H, V(0, 0, 0))
    h.check("E ...the wall is solid", r.near(shape.common(wall).Volume, 1.2 * W * H, 1e-6))
    h.check("E the timeline ends with Shell 1", r.timeline()[-1] == "Shell 1", r.timeline())
    s["v_shell"] = vol()
    r.nothing_broken("E")
    h.fit()
    h.shot("E-shell")


# == F: PLAY on a stud =============================================================================
TOP_R = STUD_R - STUD_H * math.tan(math.radians(1.0))  # the drafted stud's top
STUD = V(3.9, 3.9, H + STUD_H)


def f_sketch():
    h.ribbon("Create Sketch")


def f_face():
    h.click(STUD + V(0.8, -0.5, 0))  # the first stud's top


f_face.done = lambda: h.in_sketch() is not None
f_face.done_what = "the sketch on the stud is open"


def to_sketch(point):
    p = r.sk().getGlobalPlacement().inverse().multVec(point)
    return V(p.x, p.y, 0)


def f_text():
    from Fission180Tests.gui import text_input as ti

    sk = r.sk()
    s["text_sketch"] = sk.Name
    h.check("F the sketch is on the stud's top", r.near(sk.getGlobalPlacement().Base.z, STUD.z))
    rims = [
        g
        for g in sk.ExternalGeo
        if g.TypeId == "Part::GeomCircle" and r.near(g.Radius, TOP_R, 1e-6)
    ]
    h.check("F the stud's rim is projected into the sketch (Auto project)", len(rims) == 1, rims)
    r.zoom_on(STUD, 9.0)
    s["texts"] = list(ti.texts(sk))
    s["geo0"] = len(sk.Geometry)
    ti.open_text_tool()


f_text.done = lambda: __import__("Fission180Tests.gui.text_input").gui.text_input.dialog()
f_text.done_what = "the Text dialog is open"


def f_corner_1():
    c = to_sketch(STUD)
    r.sclick(c + V(-1.4, -0.8, 0))


def f_corner_2():
    c = to_sketch(STUD)
    r.sclick(c + V(1.4, 0.8, 0))


def f_type():
    from Fission180Tests.gui import text_input as ti

    d = ti.dialog()
    h.check("F two clicks placed the frame", d is not None and d.frame_placed)
    ti.type_text("PLAY")
    ti.type_field(d.height, "1")
    ti.press_button(d.bold)
    ti.press_button(d.italic)
    ti.press_button(d.h_buttons["center"])
    ti.press_button(d.v_buttons["middle"])


def f_ok():
    from Fission180Tests.gui import text_input as ti

    d = ti.dialog()
    h.check("F bold, italic, centred, middle", d.bold.isChecked() and d.italic.isChecked())
    h.check("F nothing is refused", not d.message.text(), d.message.text())
    ti.ok()


f_ok.done = lambda: __import__("Fission180Tests.gui.text_input").gui.text_input.dialog() is None
f_ok.done_what = "OK closed the Text dialog"


def frame_lines():
    """[index] of the text frame's four lines, in the order they were made."""
    return [i for i, _g in r.geo("Part::GeomLineSegment", construction=True) if i >= s["geo0"]]


def rim_spot(angle):
    """A sketch point on the stud's projected rim at `angle` degrees."""
    c = to_sketch(STUD)
    a = math.radians(angle)
    return c + V(TOP_R * math.cos(a), TOP_R * math.sin(a), 0)


def f_tangent():
    from Fission180Tests.gui import sketch_input as si
    from Fission180Tests.gui import text_input as ti

    new = [o for o in ti.texts(r.sk()) if o not in s["texts"]]
    h.check("F the text PLAY is in the sketch", len(new) == 1, new)
    s["text"] = new[0].Name if new else None
    if new:
        h.check("F ...1 mm high", r.near(new[0].TextHeight.Value, 1.0), new[0].TextHeight)
    h.check("F the frame has four lines", len(frame_lines()) == 4, frame_lines())
    s["dof_free"] = r.dof()
    si.menu_item("CONSTRAINTS", "Tangent")


def tangent_steps(k, angle):
    def line():
        g = r.sk().Geometry[frame_lines()[k]]
        r.sclick((g.StartPoint + g.EndPoint) * 0.5 + (g.EndPoint - g.StartPoint) * 0.2)

    def rim():
        r.sclick(rim_spot(angle))

    def check():
        g = r.sk().Geometry[frame_lines()[k]]
        c = to_sketch(STUD)
        d = g.EndPoint - g.StartPoint
        off = abs((c - g.StartPoint).cross(d).z) / d.Length
        h.check(
            "F frame line %d touches the stud's rim (the report: no constraint was added)"
            % (k + 1),
            r.near(off, TOP_R, 1e-6),
            (off, TOP_R),
        )
        r.sketch_clean("F tangent %d:" % (k + 1))

    return [
        r.named(line, "f_tangent_line_%d" % k),
        r.named(rim, "f_tangent_rim_%d" % k),
        r.named(check, "f_tangent_check_%d" % k),
    ]


def f_finish():
    from Fission180Tests.gui import text_input as ti

    tangents = [c for _i, c in r.cons(("Tangent",))]
    h.check("F four Tangent constraints", len(tangents) == 4, len(tangents))
    h.check(
        "F the frame is held (5 free before)", r.dof() < s["dof_free"], (s["dof_free"], r.dof())
    )
    text = r.doc().getObject(s["text"])
    box = ti.letters_box(text)
    c = to_sketch(STUD)
    h.check(
        "F PLAY sits in the middle of the stud",
        abs((box[0] + box[2]) / 2 - c.x) < 0.05 and abs((box[1] + box[3]) / 2 - c.y) < 0.05,
        (box, c),
    )
    h.shot("F-text")
    r.esc()
    h.ribbon("Finish Sketch")


f_finish.done = lambda: h.in_sketch() is None
f_finish.done_what = "Finish Sketch closed the sketch"


def f_letters():
    from Fission180Tests.gui import text_input as ti

    text = r.doc().getObject(s["text"])
    s["letters"] = sum(f.Area for f in text.Shape.Faces)
    r.zoom_on(STUD, 9.0)
    x, y = ti.middle_of_first_letter(text)
    sk = r.doc().getObject(s["text_sketch"])
    h.click(sk.getGlobalPlacement().multVec(V(x, y, 0)))


def f_extrude():
    h.press("e")


def f_distance():
    from fission180 import extrude_ui

    from Fission180Tests.gui import arrow_input as arrows

    p = extrude_ui.ExtrudePanel.last
    text = r.doc().getObject(s["text"])
    h.check("F the letters are the profile", p.profiles == [(text, "")], p.profiles)
    arrows.give_distance("0.1")
    s["operation"] = p.operation.currentText()
    h.task_button("OK")


f_distance.done = r.no_dialog
f_distance.done_what = "OK finished the Extrude"
f_distance.timeout_s = 120


def f_done():
    h.check("F raised letters are a Join", s.get("operation") == "Join", s.get("operation"))
    want = s["v_shell"] + s["letters"] * 0.1
    h.check("F PLAY stands 0.1 on the stud", r.near(vol(), want, 1e-5), (vol(), want))
    h.check("F the brick is 0.1 higher", r.near(body().Shape.BoundBox.ZMax, H + STUD_H + 0.1, 1e-6))
    s["v_text"] = vol()
    r.nothing_broken("F")
    h.fit()
    si_menu("CREATE", "Rectangular Pattern")


f_done.done = lambda: pattern_panel() is not None
f_done.done_what = "the Rectangular Pattern dialog is open"


def si_menu(group, label):
    from Fission180Tests.gui import sketch_input as si

    return si.menu_item(group, label)


def f_pattern_type():
    from Fission180Tests.gui import dialog_input as di

    di.choose(pattern_panel().pattern_type, "Features")


def f_pattern_feature():
    from Fission180Tests.gui import pattern_steps as ps

    s["text_extrude"] = r.timeline()[-1]
    ps.timeline_click(s["text_extrude"])


def f_direction_box():
    from Fission180Tests.gui import pattern_steps as ps

    q = pattern_panel()
    names = [o.Label for o, _s in q.options["objects"]]
    h.check("F the letters' Extrude is the object", len(names) == 1, names)
    ps.click_box("direction")


def f_pattern_ok():
    q = pattern_panel()
    h.caught_up(q)
    h.check("F nothing is refused", not q.message.text(), q.message.text())
    h.task_button("OK")


f_pattern_ok.done = lambda: pattern_panel() is None
f_pattern_ok.done_what = "OK finished the pattern"
f_pattern_ok.timeout_s = 300


def f_patterned():
    want = s["v_shell"] + 8 * s["letters"] * 0.1
    h.check("F PLAY on all eight studs", r.near(vol(), want, 1e-5), (vol(), want))
    s["v_brick"] = vol()
    r.nothing_broken("F pattern:")
    h.fit()
    h.shot("F-play")


# == G: the brick turned over ======================================================================
def move_panel():
    return r.panel("MovePanel")


def g_move():
    Gui.Selection.clearSelection()
    h.press("m")


g_move.done = lambda: move_panel() is not None
g_move.done_what = "the Move dialog is open"


def g_body():
    from Fission180Tests.gui import bodies_steps as bs

    bs.click_browser_row("Body1")


def g_angle():
    from Fission180Tests.gui import bodies_steps as bs

    p = move_panel()
    h.check("G Body1 is the object to move", [b.Label for b in p.options["bodies"]] == ["Body1"])
    s["box_before"] = r.bbox(body().Shape)
    bs.type_value(p.angle_fields[1].widget, "180")


def g_ok():
    p = move_panel()
    h.caught_up(p)
    h.check("G nothing is refused", not p.message.text(), p.message.text())
    h.task_button("OK")


g_ok.done = lambda: move_panel() is None
g_ok.done_what = "OK finished the Move"
g_ok.timeout_s = 120


def flipped(point):
    """Where a point of the brick is once it is turned over (180 degrees about the Y
    direction through the middle of its box)."""
    b = s["box_before"]
    cx, cz = (b[0] + b[3]) / 2.0, (b[2] + b[5]) / 2.0
    return V(2 * cx - point.x, point.y, 2 * cz - point.z)


def g_done():
    import Part

    shape = body().Shape
    h.check("G the same brick", r.near(shape.Volume, s["v_brick"], 1e-6), shape.Volume)
    h.check(
        "G turned over in place (the same box)",
        r.box_near(shape, s["box_before"], 1e-4),
        (r.bbox(shape), s["box_before"]),
    )
    probe = Part.makeSphere(0.3, flipped(V(3.9, 3.9, H + 0.9)))
    h.check(
        "G the studs point down now",
        r.near(shape.common(probe).Volume, probe.Volume, 1e-3),
        shape.common(probe).Volume,
    )
    h.check("G the timeline ends with the Move", r.timeline()[-1].startswith("Move"), r.timeline())
    r.nothing_broken("G")
    h.fit()
    h.shot("G-turned")


# == H: the tubes inside ===========================================================================
INNER_Z = H - 1.2  # the underside of the brick's top, before it was turned over
TUBES = [V(7.9 + PITCH * i, 7.9, INNER_Z) for i in range(3)]  # as built (before the turn)
OUTER_R, INNER_R = 6.51 / 2.0, 2.4
DEPTH = 8.4


def h_sketch():
    h.ribbon("Create Sketch")


def h_face():
    # the inner face, up now (near the far wall: the near wall hides the rest in this view)
    h.click(flipped(V(12, 13.2, INNER_Z)))


h_face.done = lambda: h.in_sketch() is not None
h_face.done_what = "the sketch on the inner face is open"


def tube(i):
    """The sketch point of tube i's centre (where it has to end up)."""
    return to_sketch(flipped(TUBES[i]))


def h_start():
    sk = r.sk()
    s["tube_sketch"] = sk.Name
    z = sk.getGlobalPlacement().Base.z
    h.check("H the sketch is on the inner face", r.near(z, flipped(TUBES[0]).z), z)
    s["geo0"] = len(sk.Geometry)
    s["rough"] = []
    # (zoomed in on the three tubes, as a person does: the grid Snap uses gets finer)
    r.zoom_on(flipped(TUBES[1]), 13.0)
    h.press("c")


def circle_steps(i, outer):
    """A circle drawn freehand: a click for the centre (the second of a pair on the first
    one's centre point: concentric by inference), a click for the size."""

    def centre():
        if outer:
            # (roughly where the tube goes: Snap puts the click on the grid)
            r.sclick(tube(i) + V(0.1, 0.1, 0))
        else:
            c = r.sk().Geometry[s["rough"][-1]].Center
            r.sclick(V(c.x, c.y, 0))

    def size():
        c = r.sk().Geometry[s["rough"][-1]].Center if not outer else None
        if outer:
            before = {k for k, _g in r.geo("Part::GeomCircle")}
            s["before"] = before
            r.sclick(tube(i) + V(0.1 + 3.0, 0.1, 0))
        else:
            s["before"] = {k for k, _g in r.geo("Part::GeomCircle")}
            r.sclick(V(c.x + 2.0, c.y, 0))

    def drawn():
        new = [k for k, _g in r.geo("Part::GeomCircle") if k not in s["before"]]
        h.check("H circle %d %s drawn" % (i + 1, "outer" if outer else "inner"), len(new) == 1, new)
        if not new:
            return
        if not outer:
            a = r.sk().Geometry[s["rough"][-1]].Center
            b = r.sk().Geometry[new[0]].Center
            h.check("H ...on the first one's centre", (a - b).Length < 1e-6, (a, b))
            joined = [
                c
                for _k, c in r.cons(("Coincident",))
                if {c.First, c.Second} == {s["rough"][-1], new[0]}
            ]
            h.check("H ...concentric by inference (a constraint, not luck)", len(joined) == 1)
        s["rough"].append(new[0])

    tag = "%d_%s" % (i, "outer" if outer else "inner")
    return [
        r.named(centre, "h_circle_%s_centre" % tag),
        r.named(size, "h_circle_%s_size" % tag),
        r.named(drawn, "h_circle_%s_drawn" % tag),
    ]


def outer(i):
    return s["rough"][2 * i]


def inner(i):
    return s["rough"][2 * i + 1]


def on_circle(index, angle):
    g = r.sk().Geometry[index]
    a = math.radians(angle)
    return V(g.Center.x + g.Radius * math.cos(a), g.Center.y + g.Radius * math.sin(a), 0)


def h_end_circle():
    r.esc()
    r.esc()
    h.check("H six circles", len(s["rough"]) == 6, s["rough"])
    h.check("H the sketch is still open", r.sk() is not None)
    Gui.Selection.clearSelection()


def equal_steps(which, name):
    """Ctrl+click three circles, CONSTRAINTS > Equal (the book: "hold Ctrl")."""

    def pick(i):
        def step():
            from Fission180Tests.gui import sketch_input as si

            si.click_held(r.g(on_circle(which(i), 200 + 20 * i)), r.CTRL)

        return r.named(step, "h_equal_%s_pick_%d" % (name, i))

    def equal():
        picked = [n for x in Gui.Selection.getSelectionEx() for n in x.SubElementNames]
        h.check(
            "H Ctrl+click adds: three circles selected (the report: Ctrl did not add)",
            len(picked) == 3,
            picked,
        )
        si_menu("CONSTRAINTS", "Equal")

    def check():
        radii = [r.sk().Geometry[which(i)].Radius for i in range(3)]
        h.check("H the three %s circles are equal" % name, max(radii) - min(radii) < 1e-6, radii)
        r.sketch_clean("H equal %s:" % name)
        r.esc()
        Gui.Selection.clearSelection()

    return [pick(0), pick(1), pick(2), r.named(equal, "h_equal_%s" % name)] + [
        r.named(check, "h_equal_%s_check" % name)
    ]


def diameter_steps(which, value, name):
    def pick():
        r.sclick(on_circle(which(0), 100))

    def place():
        # (in empty space below the pair: a click on another curve is a second pick)
        g = r.sk().Geometry[outer(0)]
        dx = -1.0 if name == "outer" else 1.0
        r.sclick(V(g.Center.x + dx, g.Center.y - g.Radius - 1.6, 0))

    def typed():
        h.check("H the value box is open", r.value_editor() is not None, r.focus_name())
        r.keyboard(value)
        r.enter()

    def check():
        radii = [r.sk().Geometry[which(i)].Radius for i in range(3)]
        h.check(
            "H all three %s circles are %s across" % (name, value),
            all(r.near(2 * x, float(value), 1e-6) for x in radii),
            radii,
        )

    return [
        r.named(pick, "h_dia_%s_pick" % name),
        r.named(place, "h_dia_%s_place" % name),
        r.named(typed, "h_dia_%s_type" % name),
        r.named(check, "h_dia_%s_check" % name),
    ]


def h_dimension():
    h.press("d")


def centre_of(i):
    c = r.sk().Geometry[outer(i)].Center
    return V(c.x, c.y, 0)


def place_steps(name, a, b, value, across):
    """D between two points (a function each), placed straight below them for the distance
    across, straight beside them for the distance up."""

    def pick_a():
        r.sclick(a())

    def pick_b():
        r.sclick(b())

    def place():
        p, q = a(), b()
        if across:
            r.sclick(V((p.x + q.x) / 2.0, min(p.y, q.y) - 2.5, 0))
        else:
            r.sclick(V(min(p.x, q.x) - 2.5, (p.y + q.y) / 2.0, 0))

    def typed():
        h.check("H %s: the value box is open" % name, r.value_editor() is not None, r.focus_name())
        r.keyboard(value)
        r.enter()

    return [
        r.named(pick_a, "h_%s_pick_a" % name),
        r.named(pick_b, "h_%s_pick_b" % name),
        r.named(place, "h_%s_place" % name),
        r.named(typed, "h_%s_type" % name),
    ]


def h_level():
    r.esc()
    si_menu("CONSTRAINTS", "Horizontal/Vertical")


def level_steps(i):
    def first():
        r.sclick(centre_of(i - 1))

    def second():
        r.sclick(centre_of(i))

    return [r.named(first, "h_level_%d_a" % i), r.named(second, "h_level_%d_b" % i)]


def h_finish():
    r.esc()
    want = [tube(i) for i in range(3)]
    got = sorted((centre_of(i) for i in range(3)), key=lambda p: (p.x, p.y))
    want = sorted(want, key=lambda p: (p.x, p.y))
    h.check(
        "H the tubes are between the studs, 8 mm apart",
        all((a - b).Length < 1e-5 for a, b in zip(got, want)),
        (got, want),
    )
    r.sketch_clean("H")
    h.check("H the six circles are fully constrained", r.dof() == 0, r.dof())
    h.shot("H-sketch")
    h.ribbon("Finish Sketch")


h_finish.done = lambda: h.in_sketch() is None
h_finish.done_what = "Finish Sketch closed the sketch"


STEEP = V(-0.35, 0.35, -1)  # from above, into the open brick


def h_extrude():
    r.look_from(STEEP)
    Gui.Selection.clearSelection()
    h.press("e")


def ring_steps(i):
    def step():
        mid = (OUTER_R + INNER_R) / 2.0
        h.click(flipped(TUBES[i]) + V(mid * 0.6, -mid * 0.8, 0))

    return r.named(step, "h_ring_%d" % i)


def h_distance():
    from fission180 import extrude_ui

    from Fission180Tests.gui import arrow_input as arrows

    p = extrude_ui.ExtrudePanel.last
    h.check("H the three rings are the profiles", len(p.profiles) == 3, p.profiles)
    arrows.give_distance("%g" % DEPTH)
    s["operation"] = p.operation.currentText()
    h.task_button("OK")


h_distance.done = r.no_dialog
h_distance.done_what = "OK finished the Extrude"
h_distance.timeout_s = 120


def h_tubes():
    ring = math.pi * (OUTER_R**2 - INNER_R**2) * DEPTH
    want = s["v_brick"] + 3 * ring
    h.check("H up from the inner face is a Join", s.get("operation") == "Join", s.get("operation"))
    h.check("H three tubes 6.51 / 4.8 across, 8.4 long", r.near(vol(), want, 1e-6), (vol(), want))
    h.check(
        "H they end level with the brick's rim", r.box_near(body().Shape, s["box_before"], 1e-4)
    )
    s["v_tubes"] = vol()
    r.nothing_broken("H tubes:")
    r.look_from(STEEP)
    Gui.Selection.clearSelection()
    si_menu("MODIFY", "Draft")


h_tubes.done = lambda: draft_panel() is not None
h_tubes.done_what = "the Draft dialog is open"


def h_pull():
    top = flipped(V(TUBES[1].x, TUBES[1].y, 0))  # a tube's end face (the brick's rim level)
    mid = (OUTER_R + INNER_R) / 2.0
    h.click(top + V(mid * 0.6, -mid * 0.8, 0))


def tube_face_steps(i, inside):
    def step():
        p = draft_panel()
        s["faces"] = len(p.names())
        top = flipped(V(TUBES[i].x, TUBES[i].y, 0))
        # the view looks along (-1, 1, ...): the far inside wall and the near outside wall
        # of a tube are in view just below its end
        k = math.sqrt(0.5)
        if inside:
            h.click(top + V(-INNER_R * k, INNER_R * k, -1.0))
        else:
            h.click(top + V(OUTER_R * k, -OUTER_R * k, -1.5))

    def check():
        p = draft_panel()
        h.check(
            "H draft: tube %d %s wall picked (one more face)"
            % (i + 1, "inside" if inside else "outside"),
            len(p.names()) == s["faces"] + 1,
            p.names(),
        )

    tag = "%d_%s" % (i, "in" if inside else "out")
    return [r.named(step, "h_draft_face_%s" % tag), r.named(check, "h_draft_face_%s_check" % tag)]


def h_draft_ok():
    from Fission180Tests.gui import dialog_input as di

    p = draft_panel()
    h.check("H the tube's end is the pull direction", p.plane_ref is not None, p.plane_ref)
    h.check("H six faces to draft", len(p.names()) == 6, p.names())
    di.type_into(p.angle.widget, "1")
    h.caught_up(p)
    h.check("H nothing is refused", not p.message.text(), p.message.text())
    h.task_button("OK")


h_draft_ok.done = lambda: draft_panel() is None
h_draft_ok.done_what = "OK finished the Draft"
h_draft_ok.timeout_s = 180


def leaning():
    """The round faces that lean 1 degree (a cone's half angle, either way)."""
    return [
        f
        for f in body().Shape.Faces
        if f.Surface.TypeId == "Part::GeomCone"
        and abs(abs(math.degrees(f.Surface.SemiAngle)) - 1.0) < 1e-6
    ]


def h_drafted():
    # 8 studs, outside and (since the Shell) inside, and the three tubes outside and inside
    h.check("H the six tube walls lean 1 degree", len(leaning()) == 16 + 6, len(leaning()))
    tubes = [f for f in leaning() if f.Area > 100]
    h.check(
        "H the tubes get thicker towards the brick's top (narrower at their free end)",
        len(tubes) == 6 and sorted(round(f.Area, 0) for f in tubes) == [123.0] * 3 + [176.0] * 3,
        sorted(round(f.Area, 1) for f in tubes),
    )
    h.check("H one valid solid", body().Shape.isValid() and len(body().Shape.Solids) == 1)
    s["v_drafted"] = vol()
    r.nothing_broken("H draft:")
    h.fit()
    h.shot("H-tubes")


# == I: red plastic, turned back, undo and redo, saved =============================================
RED = "Glossy plastic, red"


def i_appearance():
    from Fission180Tests.gui import looks_steps as ls

    ls.open_appearance()


i_appearance.done = lambda: __import__("Fission180Tests.gui.looks_steps").gui.looks_steps.panel()
i_appearance.done_what = "the Appearance dialog is open"


def i_search():
    from Fission180Tests.gui import looks_steps as ls
    from Fission180Tests.gui import widget_input as w

    p = ls.panel()
    w.click(p.search)
    w.type_text(p.search, "red plastic")


def i_drop():
    from Fission180Tests.gui import looks_steps as ls

    names = ls.library_labels()
    h.check(
        'I the search "red plastic" finds the red plastics (the report: no search)',
        RED in names and all("red" in n.lower() for n in names),
        names,
    )
    ls.drop_look(RED, flipped(V(16, 0.0, 5.0)))  # onto the brick's front wall


def i_look():
    from Fission180Tests.gui import looks_steps as ls

    h.check(
        "I the brick is red plastic", ls.body_look_label(body()) == RED, ls.body_look_label(body())
    )
    h.check("I the dialog asks nothing", ls.question() is None)
    h.task_button("OK")


i_look.done = r.no_dialog
i_look.done_what = "OK closed the Appearance dialog"


def i_red():
    from Fission180Tests.gui import looks_steps as ls

    h.click_empty()
    h.fit()
    rgb = ls.screen_rgb(flipped(V(16, 0.0, 5.0)))
    h.check("I the screen shows the brick red", ls.hue_like(rgb, (0.80, 0.08, 0.08), 0.12), rgb)
    h.shot("I-red")
    h.press("m")


i_red.done = lambda: move_panel() is not None
i_red.done_what = "the Move dialog is open"


def i_back_angle():
    from Fission180Tests.gui import bodies_steps as bs

    p = move_panel()
    h.check("I Body1 is the object to move", [b.Label for b in p.options["bodies"]] == ["Body1"])
    bs.type_value(p.angle_fields[1].widget, "180")


def i_back():
    import Part

    shape = body().Shape
    h.check("I the brick is the right way up again", r.box_near(shape, s["box_before"], 1e-4))
    probe = Part.makeSphere(0.3, V(3.9, 3.9, H + 0.9))
    h.check(
        "I the studs point up",
        shape.common(probe).Volume > 0.5 * probe.Volume,
        shape.common(probe).Volume,
    )
    h.check("I the same solid", r.near(shape.Volume, s["v_drafted"], 1e-6), shape.Volume)
    h.check("I still red", __import__("fission180.appearance").appearance.effective(body()))
    s["titles"] = r.timeline()
    r.nothing_broken("I")
    h.fit()
    h.shot("I-done")


def i_undo(count):
    def step():
        r.undo()

    return [r.named(step, "i_undo_%d" % k) for k in range(count)]


def i_redo(count):
    def step():
        r.redo()

    return [r.named(step, "i_redo_%d" % k) for k in range(count)]


def i_undone():
    # the second Move, the look, the Draft and the tubes' Extrude taken back
    h.check(
        "I four Ctrl+Z: the turned brick without tubes", r.near(vol(), s["v_brick"], 1e-6), vol()
    )
    h.check("I ...its timeline is shorter", len(r.timeline()) < len(s["titles"]), r.timeline())
    h.check("I ...no dialog and no sketch opened", r.no_dialog() and h.in_sketch() is None)
    r.nothing_broken("I undo:")


def i_redone():
    h.check("I four Ctrl+Y: the finished brick", r.near(vol(), s["v_drafted"], 1e-6), vol())
    h.check("I ...the same timeline", r.timeline() == s["titles"], (r.timeline(), s["titles"]))
    h.check("I ...the right way up", r.box_near(body().Shape, s["box_before"], 1e-4))
    r.nothing_broken("I redo:")


def i_reopened():
    made = r.solid_bodies()
    h.check("I reopened: one body, Body1", [b.Label for b in made] == ["Body1"], made)
    s["body"] = made[0].Name
    h.check("I reopened: the same solid", r.near(vol(), s["v_drafted"], 1e-6), vol())
    h.check("I reopened: the same timeline", r.timeline() == s["titles"], r.timeline())
    r.nothing_broken("I reopened:")
    # the book's brick: 31.8 x 15.8 x 9.6, studs 4.8 across and 1.8 high (PLAY 0.1 on top)
    h.check(
        "I the finished brick has the book's sizes",
        r.box_near(body().Shape, [0, 0, 0, L, W, H + STUD_H + 0.1], 1e-4),
        r.bbox(body().Shape),
    )
    h.fit()
    h.shot("I-reopened")


steps = r.home_steps() + [a_box, a_plane, a_corner, a_length, a_width, a_height, a_done]
steps += [b_sketch, b_face, b_circle, b_centre, b_diameter, b_drawn]
steps += [b_dim_x_pick, b_dim_x_origin, b_dim_x_place, b_dim_x_value]
steps += [b_dim_y_pick, b_dim_x_origin, b_dim_y_place, b_dim_y_value]
steps += [b_finish, b_profile, b_extrude, b_distance, b_done]
steps += [c_draft, c_pull, c_ok_too_early, c_refused, c_side, c_angle, c_done]
steps += [d_pattern, d_type, d_extrude, d_draft, d_direction_box, d_edge_x, d_edge_y, d_edge_y2]
steps += [d_values, d_ok, d_done]
steps += [e_shell, e_bottom, e_thickness, e_done]
steps += [f_sketch, f_face, f_text, f_corner_1, f_corner_2, f_type, f_ok, f_tangent]
for _k, _angle in enumerate((250, 340, 70, 160)):
    steps += tangent_steps(_k, _angle)
steps += [f_finish, f_letters, f_extrude, f_distance, f_done]
steps += [
    f_pattern_type,
    f_pattern_feature,
    f_direction_box,
    d_edge_x,
    d_edge_y,
    d_edge_y2,
    d_values,
]
steps += [f_pattern_ok, f_patterned]
steps += [g_move, g_body, g_angle, g_ok, g_done]
steps += [h_sketch, h_face, h_start]
for _i in range(3):
    steps += circle_steps(_i, True) + circle_steps(_i, False)
steps += [h_end_circle] + equal_steps(outer, "outer") + equal_steps(inner, "inner")
steps += [h_dimension] + diameter_steps(outer, "6.51", "outer")
steps += diameter_steps(inner, "4.8", "inner")
# (the brick is turned over: the third pair drawn is the one nearest the sketch's origin)
steps += place_steps("x0", lambda: centre_of(2), lambda: V(0, 0, 0), "7.9", True)
steps += place_steps("y0", lambda: centre_of(2), lambda: V(0, 0, 0), "7.9", False)
steps += [h_level] + level_steps(1) + level_steps(2) + [r.named(h_dimension, "h_dimension_2")]
steps += place_steps("x1", lambda: centre_of(2), lambda: centre_of(1), "8", True)
steps += place_steps("x2", lambda: centre_of(1), lambda: centre_of(0), "8", True)
steps += [h_finish, h_extrude, ring_steps(0), ring_steps(1), ring_steps(2), h_distance, h_tubes]
steps += [h_pull]
for _i in range(3):
    steps += tube_face_steps(_i, False) + tube_face_steps(_i, True)
steps += [h_draft_ok, h_drafted]
steps += [i_appearance, i_search, i_drop, i_look, i_red, g_body, i_back_angle]
steps += [r.named(g_ok, "i_back_ok"), i_back]
steps += i_undo(4) + [i_undone] + i_redo(4) + [i_redone]
steps += r.save_steps("i", "Play Brick") + r.reopen_steps("i", "Play Brick") + [i_reopened]

h.run("replay_06_play_brick", steps, paced_by="state")
