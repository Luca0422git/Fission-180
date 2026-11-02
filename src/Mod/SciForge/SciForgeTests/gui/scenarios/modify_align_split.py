# SPDX-License-Identifier: LGPL-2.1-or-later
"""Align puts a split piece back (Luca, beta 3.2: "The align tool is WAY off ... i split the
body, moved it, then aligned it. didn't fit at all. way off."). Only real input.

What was wrong (all three seen here before the fix):
  1. A Split Body made with an origin plane leaves the cut faces lying exactly in that
     plane, and Align's To box shows the origin squares: a click on the cut face where the
     YZ square is too went to the square (the face and the square came out at the very same
     depth, and only a part strictly in front won).
  2. The squares are the moving body's own origin (FreeCAD gives every body one): the plane
     was refused as "on what moves", so the click did nothing.
  3. An origin plane picked as To (its browser row, the square) took the From point to the
     plane's origin instead of only across onto the plane: here the cut face's centre
     (60, 20, 80) went to (0, 0, 0), not (0, 20, 80): 20 mm off sideways and 80 mm too
     low, half the piece under the ground. A piece on the minus side of the plane was also
     turned over, into the other piece (the plane's normal was taken as a face's outside).

Body = rectangle -40..40 x -10..50, extruded 40 (192000).

  A  Split Body: click the body, the YZ origin square: two bodies, Body x -40..0, Body2
     x 0..40 (96000 each). OK.
  B  M, click Body2, X Distance 60, Z Distance 60: x 60..100, z 60..100. OK.
  C  MODIFY > Align. Seen from the left, the mouse on Body2's cut face (x 60, facing -X)
     away from its corners and edge middles: its centre (60, 20, 80) is lit; click: From =
     that centre, facing -X.
  D  Seen from the right, the YZ square shows over Body's cut face (x 0, facing +X): on
     every spot where both are, the face takes the click (not the square). Click there:
     To = Body's cut face at its centre (0, 20, 20), not the YZ plane; the preview puts
     Body2 back exactly where it was split off: x 0..40, y -10..50, z 0..40.
  E  OK: one Align step, Body2 where it was, same volume; the two bodies touch along the
     whole cut (their common face is 60 x 40). Undo.
  F  Align again, From = Body2's cut face (as C), To = the YZ plane (its square; Body's cut
     face covers it here, so its row in the browser): taken, not refused; Body2 only slides
     across onto the plane: x 0..40, y -10..50, z 60..100. Esc: nothing moved.
"""

import FreeCAD as App
from PySide import QtCore

from SciForgeTests.gui import bodies_steps as s
from SciForgeTests.gui import direct_steps as d
from SciForgeTests.gui import harness as h
from SciForgeTests.gui import plane_input as pl

V = App.Vector
state = {}
FROM_CENTRE = V(60, 20, 80)
TO_CENTRE = V(0, 20, 20)
HOME = (0, -10, 0, 40, 50, 40)  # Body2 as the split left it
MOVED = (60, -10, 60, 100, 50, 100)  # Body2 after the Move


def body():
    return s.bodies()[0]


def body2():
    found = s.bodies()
    return found[1] if len(found) > 1 else None


def box_of(obj):
    bb = obj.Shape.BoundBox
    return (bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax)


def at(obj, expect, tol=1e-6):
    return obj is not None and all(abs(a - b) <= tol for a, b in zip(box_of(obj), expect))


def aligns():
    return s.steps_of_kind("Align")


def snaps():
    p = d.panel()
    return getattr(p, "snaps", None) if p is not None else None


def pixels_apart(a, b):
    pa, pb = h.screen_point(a), h.screen_point(b)
    return ((pa.x() - pb.x()) ** 2 + (pa.y() - pb.y()) ** 2) ** 0.5


def face_spot(centre, du, dv, u, v):
    return centre + u * du + v * dv


# -- A ------------------------------------------------------------------------------------------
def a_open():
    h.click_empty()
    h.fit()
    h.ribbon("Split Body")


def a_click_body():
    p = s.panel()
    h.check("Split Body dialog", p is not None and p.title == "Split Body", p)
    h.click(V(-20, 20, 40))


def a_click_yz():
    p = s.panel()
    h.check("Body picked", p is not None and p.options["body"] is body(), p and p.options)
    pl.click_square("YZ_Plane")


def a_ok():
    found = s.bodies()
    h.check("preview: two bodies", len(found) == 2, [x.Label for x in found])
    h.task_button("OK")


def a_done():
    h.check("dialog closed", s.panel() is None)
    h.check("Body keeps x < 0", at(body(), (-40, -10, 0, 0, 50, 40)), box_of(body()))
    h.check("Body2 is x > 0", at(body2(), HOME), body2() and box_of(body2()))
    h.check("96000 each", s.close(s.volume(body()), 96000) and s.close(s.volume(body2()), 96000))


# -- B ------------------------------------------------------------------------------------------
def b_press_m():
    h.click_empty()
    h.fit()
    h.press("m")


def b_click_body2():
    p = s.panel()
    h.check("Move/Copy dialog", p is not None and p.title == "Move/Copy", p)
    h.click(V(20, 20, 40))


def b_type():
    p = s.panel()
    if not h.check("Body2 picked", p is not None and p.options["bodies"] == [body2()], p):
        return
    s.type_value(p.distance_fields[0].widget, "60")
    s.type_value(p.distance_fields[2].widget, "60")


def b_ok():
    h.check("moved", at(body2(), MOVED), box_of(body2()))
    h.task_button("OK")


def b_done():
    h.check("dialog closed", s.panel() is None)
    h.check("Body2 moved", at(body2(), MOVED), box_of(body2()))


# -- C ------------------------------------------------------------------------------------------
def c_open():
    h.click_empty()
    h.fit()
    d.ribbon_menu("MODIFY", "Align")


def c_hover_from():
    p = d.panel()
    if not h.check("Align dialog", p is not None and p.title == "Align", p):
        return
    h.view().viewLeft()
    h.fit(iso=False)
    # on the cut face, between its centre and a corner: no dot within reach of the mouse
    spot = face_spot(FROM_CENTRE, -12, -9, V(0, 1, 0), V(0, 0, 1))
    state["from_spot"] = spot
    h.uncover(spot)
    h.move(h.screen_point(spot))


def c_lit():
    sn = snaps()
    hot = sn.hot if sn is not None else None
    h.check(
        "C the cut face's centre is lit",
        hot is not None and hot["kind"] == "centre" and (hot["point"] - FROM_CENTRE).Length < 1e-6,
        hot and (hot["kind"], hot["point"]),
    )


def c_click():
    h.click(state["from_spot"])


def c_taken():
    p = d.panel()
    frame = p.options.get("from_frame") if p is not None else None
    h.check(
        "C From = Body2's cut face at its centre, facing -X",
        frame is not None
        and (V(*frame["point"]) - FROM_CENTRE).Length < 1e-6
        and frame["oriented"]
        and abs(frame["axis"][0] + 1.0) < 1e-9,
        frame,
    )
    h.check("C To waits", p is not None and p.active == "to", p and p.active)


# -- D ------------------------------------------------------------------------------------------
def d_view_right():
    h.view().viewRight()
    h.fit(iso=False)


def d_overlap():
    """Spots of Body's cut face (x 0) that the YZ square covers too, away from the face's
    corners and edge middles."""
    picker = pl.picker()
    if not h.check("D the origin squares show", picker is not None):
        return
    pl.settle(picker)
    dots = [V(0, y, z) for y in (-10, 20, 50) for z in (0, 20, 40)]
    spots = []
    steps = [i / 4.0 for i in range(-3, 4)]
    for a in steps:
        for b in steps:
            point = picker.spot("YZ_Plane", a, b)
            if not (-9 < point.y < 49 and 1 < point.z < 39 and abs(point.x) < 1e-9):
                continue
            if min(pixels_apart(point, dot) for dot in dots if dot != TO_CENTRE) < 30:
                continue
            if h.covered(h.screen_point(point)):
                continue
            spots.append(point)
    state["spots"] = spots
    h.check("D the YZ square is over Body's cut face", len(spots) >= 4, spots)
    taken = []
    for point in spots:
        x, y = h.view().getPointOnViewport(point)
        role = picker.front_plane_at((int(round(x)), int(round(y))))
        if role is not None:
            taken.append((tuple(point), role))
    h.check("D the face takes every click there, not the square", not taken, taken)


def d_hover_to():
    spots = state.get("spots") or []
    if not spots:
        return
    # the spot nearest the square's middle (where a person aims at the face)
    picker = pl.picker()
    middle = picker.spot("YZ_Plane", 0, 0) if picker is not None else spots[0]
    spot = min(spots, key=lambda p: (p - middle).Length)
    state["to_spot"] = spot
    h.move(h.screen_point(spot))


def d_click():
    if state.get("to_spot") is not None:
        h.click(state["to_spot"])


def d_taken():
    p = d.panel()
    pick = p.options.get("to_pick") if p is not None else None
    frame = p.options.get("to_frame") if p is not None else None
    h.check(
        "D To = a face of Body (not the YZ plane)",
        pick is not None and str(pick[1]).startswith("Face"),
        pick and (pick[0].Label, pick[1]),
    )
    h.check(
        "D at the cut face's centre (0, 20, 20)",
        frame is not None and (V(*frame["point"]) - TO_CENTRE).Length < 1e-6,
        frame,
    )
    h.check("D the preview: Body2 back where it was", at(body2(), HOME), box_of(body2()))
    h.shot("D-preview")


# -- E ------------------------------------------------------------------------------------------
def e_ok():
    h.task_button("OK")


def e_done():
    h.check("dialog closed", d.panel() is None)
    h.check("one Align step", len(aligns()) == 1, aligns())
    h.check("E Body2 back where it was", at(body2(), HOME), box_of(body2()))
    h.check("E same volume", s.close(s.volume(body2()), 96000), s.volume(body2()))
    common = body().Shape.common(body2().Shape) if body2() is not None else None
    touching = body().Shape.section(body2().Shape) if body2() is not None else None
    h.check("E no overlap", common is not None and common.Volume < 1e-6, common and common.Volume)
    area = touching.BoundBox if touching is not None else None
    h.check(
        "E they meet along the whole cut (x 0, y -10..50, z 0..40)",
        area is not None
        and abs(area.XMin) < 1e-6
        and abs(area.XMax) < 1e-6
        and abs(area.YLength - 60) < 1e-6
        and abs(area.ZLength - 40) < 1e-6,
        area,
    )
    h.fit()
    h.shot("E-aligned")
    s.undo()


# -- F ------------------------------------------------------------------------------------------
def f_undone():
    h.check("F undo: no Align step", aligns() == [], aligns())
    h.check("F undo: Body2 moved away again", at(body2(), MOVED), box_of(body2()))


def f_open():
    c_open()


def f_hover_from():
    c_hover_from()


def f_click():
    c_lit()
    c_click()


def f_click_yz():
    c_taken()
    h.fit()
    pl.click_square("YZ_Plane")  # (where Body's cut face covers it: its row in the browser)


def f_taken():
    p = d.panel()
    pick = p.options.get("to_pick") if p is not None else None
    h.check(
        "F To = the YZ plane (not refused as on what moves)",
        pick is not None and getattr(pick[0], "Role", "").startswith("YZ"),
        (pick and pick[0].Label, p and p.message.text()),
    )
    h.check(
        "F onto the plane only: Body2 slides along X, x 0..40, y -10..50, z 60..100",
        at(body2(), (0, -10, 60, 40, 50, 100)),
        box_of(body2()),
    )
    h.shot("F-plane")
    h.press(QtCore.Qt.Key_Escape)


def f_cancelled():
    h.check("F Esc: no dialog", d.panel() is None)
    h.check("F Esc: Body2 where the Move put it", at(body2(), MOVED), box_of(body2()))
    h.check("F Esc: no Align step", aligns() == [], aligns())


h.run(
    "modify_align_split",
    [s.new_design("AlignSplit")]
    + s.box_steps("block", (-40, -10, 40, 50), 40, V(10, 10, 0))
    + [
        a_open,
        a_click_body,
        a_click_yz,
        a_ok,
        a_done,
        b_press_m,
        b_click_body2,
        b_type,
        b_ok,
        b_done,
        c_open,
        c_hover_from,
        c_lit,
        c_click,
        c_taken,
        d_view_right,
        d_overlap,
        d_hover_to,
        d_click,
        d_taken,
        e_ok,
        e_done,
        f_undone,
        f_open,
        f_hover_from,
        f_click,
        f_click_yz,
        f_taken,
        f_cancelled,
    ],
    paced_by="state",
)
