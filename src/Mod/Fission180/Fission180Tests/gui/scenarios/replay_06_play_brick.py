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
from PySide import QtCore, QtWidgets

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
    h.check(
        "D the second direction's box takes the next click by itself (Fusion: one "
        "Directions box takes both)",
        q.active == "direction2",
        q.active,
    )
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


steps = r.home_steps() + [a_box, a_plane, a_corner, a_length, a_width, a_height, a_done]
steps += [b_sketch, b_face, b_circle, b_centre, b_diameter, b_drawn]
steps += [b_dim_x_pick, b_dim_x_origin, b_dim_x_place, b_dim_x_value]
steps += [b_dim_y_pick, b_dim_x_origin, b_dim_y_place, b_dim_y_value]
steps += [b_finish, b_profile, b_extrude, b_distance, b_done]
steps += [c_draft, c_pull, c_ok_too_early, c_refused, c_side, c_angle, c_done]
steps += [d_pattern, d_type, d_extrude, d_draft, d_direction_box, d_edge_x, d_edge_y]
steps += [d_values, d_ok, d_done]
steps += [e_shell, e_bottom, e_thickness, e_done]

h.run("replay_06_play_brick", steps, paced_by="state")
