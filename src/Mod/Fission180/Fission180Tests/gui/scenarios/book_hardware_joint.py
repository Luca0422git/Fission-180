# SPDX-License-Identifier: LGPL-2.1-or-later
"""An inserted screw jointed into a hole by hand, the way the book does it with a
McMaster-Carr part (insert, Move out of the way, then ASSEMBLE > Joint on two round edges).
Real input. The parts of the hardware library are drawn with plain circles and cylinders so
Joint's snap finds their axis (wave 7: "a round edge offers its centre as the joint snap").

A component "Plate" (made by script): a 60 x 40 x 10 block with a 5.5 mm hole at (30, 20).

A  INSERT > Hardware..., Size M5 (a socket head cap screw). Nothing clicked: OK. The screw
   comes in at the origin, its head's bearing face on the origin plane (no counterbore to
   sit in), and the Move dialog opens: X Distance -20, OK.
B  J. The pointer on the round edge of the screw's head: the only dot is the edge's centre,
   on the screw's axis. Click. The pointer on the rim of the Plate's hole: its centre.
   Click: the screw stands on the hole's axis. OK: one joint, no undo step left open.
C  Ctrl+Z puts the screw back beside the plate; Ctrl+Y onto the hole's axis again.
"""

import FreeCAD as App

from Fission180Tests.gui import book_hardware_steps as bh
from Fission180Tests.gui import book_joints_steps as bj
from Fission180Tests.gui import component2_steps as c2
from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import joints_steps as j

V = App.Vector
S = {}
HOLE = (30.0, 20.0)
BESIDE = (-20.0, 0.0)
NAME = "M5 x 10 Socket Head Cap Screw"


def setup():
    from fission180 import components

    bh.new_design("BookHardwareJoint")
    body = bh.block("PlateBody", (60, 40, 10))
    bh.drill(body, "Hole", HOLE[0], HOLE[1], 5.5, 0, 10)
    bh.doc().recompute()
    S["plate"] = components.from_bodies(bh.doc(), [body], label="Plate")[0]
    bh.done()
    bh.open_hardware()


setup.done = bh.is_open
setup.done_what = "the Hardware dialog is open"


def screw():
    part = bh.part_named(NAME)
    return bh.hw().component_of(part) if part is not None else None


# -- A --------------------------------------------------------------------------------------------
def a_size():
    h.check("M5", ui.choose(bh.panel().size, "M5"))


def a_ok():
    p = bh.panel()
    h.check("the name", p.name.text() == NAME, p.name.text())
    h.task_button("OK")


a_ok.done = lambda: c2.component_panel() is not None
a_ok.done_what = "the Move dialog opens on the screw"


def a_move():
    comp = screw()
    h.check("the screw's component", comp is not None, bh.labels())
    box = bh.box_of(comp)
    # the head (8.5 x 5) above the origin plane, the shank 10 below it
    h.check(
        "at the origin, its head's bearing face on the plane",
        bh.near(box, [-4.25, -4.25, -10, 4.25, 4.25, 5]),
        box,
    )
    c2.type_value(c2.component_panel(), "dx", "-20")


def a_move_ok():
    h.task_button("OK")


def a_beside():
    bh.no_dialog("Move OK")
    at = bh.axis_of(screw())
    h.check("moved beside the plate", bh.near(at, (BESIDE[0], BESIDE[1], 0.0)), at)
    S["beside"] = at
    S["joints"] = len(bj.jm().joints(bh.doc()))
    j.press_j()


a_beside.done = lambda: j.joint_panel() is not None
a_beside.done_what = "the Joint dialog is open"


# -- B --------------------------------------------------------------------------------------------
def b_hover_head():
    bj.hover_edge(bj.rim(BESIDE, 4.25, 5, 250))


def b_head_centre():
    p = j.panel()
    hov = bj.hover_of(p)
    h.check(
        "the pointer is on the head's round edge",
        hov is not None and hov.pick is not None and hov.pick.element.startswith("Edge"),
        hov and hov.pick,
    )
    h.check("its only dot is its centre", bj.kinds(p) == ["circle"], bj.kinds(p))
    spot = bj.hot(p)
    h.check(
        "the centre is lit, on the screw's axis",
        spot is not None and (spot["point"] - V(BESIDE[0], BESIDE[1], 5)).Length < 1e-6,
        spot and spot["point"],
    )
    h.click_edge(bj.rim(BESIDE, 4.25, 5, 250))


def b_hover_hole():
    p = j.panel()
    h.check(
        "the screw is component 1", p.snaps["comp1"] is not None and p.active == "comp2", p.active
    )
    bj.hover_edge(bj.rim(HOLE, 2.75, 10, 250))


def b_hole_centre():
    spot = bj.hot(j.panel())
    h.check(
        "on the rim of the hole its centre is lit",
        spot is not None and (spot["point"] - V(HOLE[0], HOLE[1], 10)).Length < 1e-6,
        spot and (spot["kind"], spot["point"]),
    )
    h.click_edge(bj.rim(HOLE, 2.75, 10, 250))


def b_joined():
    made = bj.jm().joints(bh.doc())
    h.check("one joint more", len(made) == S["joints"] + 1, [x.Label for x in made])
    box = bh.box_of(screw())
    centre = ((box[0] + box[3]) / 2.0, (box[1] + box[4]) / 2.0)
    h.check("the screw stands on the hole's axis", bh.near(centre, HOLE, 1e-3), box)
    h.check(
        "the plate did not move", bh.near(bh.axis_of(S["plate"]), (0, 0, 0)), bh.axis_of(S["plate"])
    )
    p = j.panel()
    h.check("no problem shown", p is not None and p.message.text() == "", p and p.message.text())
    h.shot("B-screw-jointed")
    j.ok()


def b_done():
    j.no_dialog("Joint OK")
    bj.no_open_step("Joint OK")
    S["on"] = bh.box_of(screw())
    s.undo()


# -- C --------------------------------------------------------------------------------------------
def c_undone():
    h.check(
        "Undo: beside the plate again",
        bh.near(bh.axis_of(screw()), S["beside"]),
        bh.axis_of(screw()),
    )
    h.check("Undo: the joint is gone", len(bj.jm().joints(bh.doc())) == S["joints"])
    s.redo()


def c_redone():
    h.check(
        "Redo: on the hole's axis again",
        bh.near(bh.box_of(screw()), S["on"], 1e-3),
        bh.box_of(screw()),
    )
    h.check("Redo: the joint", len(bj.jm().joints(bh.doc())) == S["joints"] + 1)
    h.check("the solver is happy", bj.jm().solve(bh.doc()) == 0)
    h.fit()
    h.shot("C-end")


h.run(
    "book_hardware_joint",
    [
        setup,
        a_size,
        a_ok,
        a_move,
        a_move_ok,
        a_beside,
        b_hover_head,
        b_head_centre,
        b_hover_hole,
        b_hole_centre,
        b_joined,
        b_done,
        c_undone,
        c_redone,
    ],
    paced_by="state",
)
