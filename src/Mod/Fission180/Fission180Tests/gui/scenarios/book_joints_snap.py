# SPDX-License-Identifier: LGPL-2.1-or-later
"""Snapping a joint to the centre of a round edge, as Fusion does (the book parity report:
Fire Piston, Hot End, Pizza Cutter: "clicking a round edge gives (corner), the seam vertex,
never the edge's centre"; "the loop centre on threaded geometry is 0.37 mm off the axis").
Real input (docs/fission180/parity/joints.md, "Snap points").

A Tube (r 10, h 30, a hole r 4 through it) at the origin, a Cap (r 6, h 8) beside it, and a
Nut: a block whose hole is round but for a notch that runs out through its rim (what a
modelled thread leaves), so the centre of area of the hole's outline is off its axis.

  A  J. The pointer on the Cap's top round edge, anywhere on it: the only dot is the edge's
     centre, and it is lit (no "corner" at the seam, no "midpoint" opposite it). Click: the
     joint origin is the centre.
  B  The pointer on the Tube's round outside face: its dots are on the axis only (the middle
     and the two end circles' centres), no seam corner. On the rim of its hole: the hole's
     centre. Click: the Cap stands on the Tube's axis. OK; no undo step left open.
  C  Ctrl+Z puts the Cap back, Ctrl+Y on the axis again.
  D  J again, the pointer on the Nut's top beside its notched hole: the lit dot is the
     hole's centre, on the hole's axis, not at the outline's centre of area. Click: the
     joint origin stands on the axis. Esc.
  E  Two parts on top of each other in the view: a long press lists what is under the
     pointer (Select Other); the part behind is taken from the list by its row.
  F  Save, reopen: the Cap is still on the Tube's axis and the solver is happy.
"""

import os
import tempfile

import FreeCAD as App

from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import book_joints_steps as bj
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import joints_steps as j
from Fission180Tests.gui import selection_input as si

V = App.Vector
S = {}
CAP = (40.0, 0.0)
NUT = (-45.0, 0.0)  # the axis of the Nut's hole
NUT_TOP = 6.0


def jm():
    return bj.jm()


def nut_solid():
    """A 30 x 30 x 6 block with a hole of radius 5 about NUT that is round over 300 degrees
    and notched outwards over the rest (up to radius 7.5)."""
    import Part

    cx, cy = NUT
    corners = [(-15, -15), (15, -15), (15, 15), (-15, 15), (-15, -15)]
    outer = Part.makePolygon([V(cx + x, cy + y, 0) for x, y in corners])
    a = bj.rim(NUT, 5.0, 0, 30)
    m = bj.rim(NUT, 5.0, 0, 180)
    c = bj.rim(NUT, 5.0, 0, 330)
    arc = Part.Arc(a, m, c).toShape()
    notch = Part.BSplineCurve()
    notch.interpolate([c, bj.rim(NUT, 7.5, 0, 0), a])
    inner = Part.Wire([arc, notch.toShape()])
    face = Part.Face([outer, inner])
    return face.extrude(V(0, 0, NUT_TOP))


def setup():
    bj.new_design("BookJointsSnap")
    bj.cylinder("Tube", 10, 30, hole=4)
    bj.cylinder("Cap", 6, 8, V(CAP[0], CAP[1], 0))
    nut = bj.doc().addObject("Part::Feature", "Nut")
    nut.Shape = nut_solid()
    bj.box("Link A", (40, 10, 3), V(0, 40, 0))
    bj.box("Link B", (40, 10, 3), V(10, 40, -3))  # under Link A, behind it from above
    bj.doc().recompute()
    h.fit()
    S["cap_home"] = bj.place(bj.part("Cap"))


# -- A ------------------------------------------------------------------------------------------
def a_press_j():
    j.press_j()


def a_hover_rim():
    bj.hover_edge(bj.rim(CAP, 6, 8, 250))


def a_rim_centre():
    p = j.panel()
    hov = bj.hover_of(p)
    h.check(
        "the pointer is on the Cap's round edge",
        hov is not None and hov.pick is not None and hov.pick.element.startswith("Edge"),
        hov and hov.pick,
    )
    h.check("its only dot is its centre", bj.kinds(p) == ["circle"], bj.kinds(p))
    spot = bj.hot(p)
    h.check(
        "the centre is lit, on the Cap's axis",
        spot is not None and (spot["point"] - V(CAP[0], CAP[1], 8)).Length < 1e-6,
        spot and spot["point"],
    )
    bj.hover_edge(bj.rim(CAP, 6, 8, 200))  # elsewhere on the edge: the same


def a_rim_centre_again():
    spot = bj.hot(j.panel())
    h.check(
        "anywhere on the edge the centre is lit",
        spot is not None
        and spot["kind"] == "circle"
        and (spot["point"] - V(CAP[0], CAP[1], 8)).Length < 1e-6,
        spot and (spot["kind"], spot["point"]),
    )
    h.shot("A-round-edge-centre")
    h.click_edge(bj.rim(CAP, 6, 8, 200))


def a_taken():
    p = j.panel()
    snap = p.snaps["comp1"]
    h.check(
        "the click took the edge's centre",
        snap is not None
        and snap["kind"] == "circle"
        and (snap["point"] - V(CAP[0], CAP[1], 8)).Length < 1e-6,
        snap and (snap["kind"], snap["point"]),
    )
    h.check("component 2 waits", p.active == "comp2", p.active)


# -- B ------------------------------------------------------------------------------------------
def b_hover_side():
    bj.hover_point(bj.rim((0, 0), 10, 15, 290))


def b_side_dots():
    p = j.panel()
    hov = bj.hover_of(p)
    h.check(
        "the pointer is on the Tube's round face",
        hov is not None and hov.pick is not None and hov.pick.element.startswith("Face"),
        hov and hov.pick,
    )
    kinds = bj.kinds(p)
    h.check("no seam corner, no seam middle", set(kinds) <= {"centre", "circle"}, kinds)
    off = [c["point"] for c in hov.candidates if bj.xy_length(c["point"]) > 1e-6]
    h.check("every dot is on the Tube's axis", not off, off)
    bj.hover_edge(bj.rim((0, 0), 4, 30, 250))


def b_hole_centre():
    spot = bj.hot(j.panel())
    h.check(
        "on the rim of the hole its centre is lit",
        spot is not None and (spot["point"] - V(0, 0, 30)).Length < 1e-6,
        spot and (spot["kind"], spot["point"]),
    )
    h.click_edge(bj.rim((0, 0), 4, 30, 250))


def b_joined():
    made = jm().joints(bj.doc())
    h.check("one joint", len(made) == 1, made)
    centre = bj.box_centre(bj.part("Cap"))
    h.check("the Cap stands on the Tube's axis", bj.xy_length(centre) < 1e-4, centre)
    box = jm().part_shape(bj.part("Cap")).BoundBox
    h.check("on the Tube's top", abs(box.ZMin - 30) < 1e-4 or abs(box.ZMax - 30) < 1e-4, box)
    p = j.panel()
    h.check("no problem shown", p is not None and p.message.text() == "", p and p.message.text())
    j.ok()


def b_done():
    j.no_dialog("Joint OK")
    bj.no_open_step("Joint OK")
    S["cap_on"] = bj.place(bj.part("Cap"))


# -- C ------------------------------------------------------------------------------------------
def c_undo():
    s.undo()


def c_undone():
    h.check("Ctrl+Z: no joint", not jm().joints(bj.doc()))
    h.check("the Cap is back", not bj.moved(bj.place(bj.part("Cap")), S["cap_home"]))


def c_redo():
    s.redo()


def c_redone():
    h.check("Ctrl+Y: the joint is back", len(jm().joints(bj.doc())) == 1)
    h.check("the Cap is on the axis", not bj.moved(bj.place(bj.part("Cap")), S["cap_on"]))
    bj.no_open_step("undo and redo")


# -- D ------------------------------------------------------------------------------------------
def d_command():
    j.press_j()


def d_hover_hole():
    bj.hover_point(bj.rim(NUT, 6.5, NUT_TOP, 120))  # on the top face, beside the hole


def d_on_axis():
    from fission180 import hole_snaps

    p = j.panel()
    hov = bj.hover_of(p)
    spot = bj.hot(p)
    axis = V(NUT[0], NUT[1], NUT_TOP)
    h.check(
        "beside the hole the lit dot is the hole's centre, on its axis",
        spot is not None and (spot["point"] - axis).Length < 1e-6,
        spot and (spot["kind"], spot["point"]),
    )
    nut = bj.doc().getObject("Nut")
    element = hov.pick.element if hov is not None and hov.pick is not None else ""
    raw = [x for x in hole_snaps.snaps(nut.Shape, element) if x["kind"] == "loop"]
    h.check(
        "the outline's centre of area is elsewhere (the notch pulls it)",
        bool(raw) and (raw[0]["point"] - axis).Length > 0.05,
        raw and raw[0]["point"],
    )
    h.click(bj.rim(NUT, 6.5, NUT_TOP, 120))


def d_taken():
    p = j.panel()
    snap = p.snaps["comp1"] if p is not None else None
    h.check(
        "the click took the hole's centre on its axis",
        snap is not None and (snap["point"] - V(NUT[0], NUT[1], NUT_TOP)).Length < 1e-6,
        snap and (snap["kind"], snap["point"]),
    )
    j.cancel()


def d_done():
    j.no_dialog("Joint Cancel")
    bj.no_open_step("Joint Cancel")
    h.check("still one joint", len(jm().joints(bj.doc())) == 1)


# -- E ------------------------------------------------------------------------------------------
def e_command():
    h.view().viewTop()
    h.fit(iso=False)
    j.menu("As-built Joint")


def e_hold():
    S["pos"] = si.hold(V(25, 45, 3))  # Link A on top, Link B under it


def e_list():
    menu = si.select_other_menu()
    h.check("a long press opens the Select Other list", menu is not None)
    si.let_go(S["pos"])
    if menu is None:
        return
    rows = si.rows(menu)
    S["rows"] = rows
    behind = [r for r in rows if "Link_B" in r or "Link B" in r]
    h.check("the part behind is listed", bool(behind), rows)
    if behind:
        si.click_row(menu, behind[0])


e_list.ready = lambda: si.select_other_menu() is not None
e_list.ready_what = "the Select Other list to open after the long press"


def e_taken():
    p = j.panel()
    h.check(
        "the part behind was taken from the list",
        p is not None and [x.Label for x in p.parts] == ["Link B"],
        (p and p.parts, S.get("rows")),
    )
    j.cancel()


def e_cancelled():
    j.no_dialog("As-built Joint Cancel")
    bj.no_open_step("As-built Joint Cancel")
    h.fit()


# -- F ------------------------------------------------------------------------------------------
def f_save_close():
    S["path"] = os.path.join(tempfile.mkdtemp(), "book_joints_snap.FCStd")
    bj.doc().saveAs(S["path"])
    App.closeDocument(bj.doc().Name)


def f_open():
    App.openDocument(S["path"])
    h.fit()


def f_reopened():
    h.check("the joint is back", len(jm().joints(bj.doc())) == 1)
    h.check("the Cap is on the axis", not bj.moved(bj.place(bj.part("Cap")), S["cap_on"]))
    h.check("the solver is happy", jm().solve(bj.doc()) == 0)
    h.check("nothing needs solving", not jm().needs_solve(bj.doc()))
    bj.no_open_step("reopening")


steps = [setup, a_press_j, a_hover_rim, a_rim_centre, a_rim_centre_again, a_taken]
steps += [b_hover_side, b_side_dots, b_hole_centre, b_joined, b_done]
steps += [c_undo, c_undone, c_redo, c_redone]
steps += [d_command, d_hover_hole, d_on_axis, d_taken, d_done]
steps += [e_command, e_hold, e_list, e_taken, e_cancelled]
steps += [f_save_close, f_open, f_reopened]

h.run("book_joints_snap", steps, paced_by="state")
