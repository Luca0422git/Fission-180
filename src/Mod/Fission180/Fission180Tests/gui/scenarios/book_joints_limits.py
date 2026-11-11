# SPDX-License-Identifier: LGPL-2.1-or-later
"""Joint limits like Fusion's (the book parity report: Fire Piston, Pizza Cutter, Tesla
Turbine: "no Preview Limits and no Flip", "Rest does nothing after a drag"), with real input
(docs/fission180/parity/joints.md, "Joint limits").

A Base plate (grounded) with an Arm lying on it; the Arm turns about the middle of its end.

  A  ASSEMBLE > As-built Joint, Arm + Base, Type Revolute, the position clicked at the middle
     of the Arm's end edge. Angle limits: Maximum ticked (it shows the joint's value now, 0),
     60 typed; Flip: the limit is on the other side (Minimum -60, Maximum off); Flip again.
     Minimum ticked, -20 typed: Flip gives -60 .. 20; again 60 .. -20 back as -20 .. 60.
  B  Preview Motion: the Arm swings between its limits, alone (the Base stays, the button is
     down); With All Limits: it plays with everything tied to it; pressed again: it stops
     and the Arm stands where it was. OK: "Revolute 1" with -20 .. 60.
  C  Edit Joint Limits (browser): Rest ticked (it shows 0), OK. In the top view the Arm is
     dragged round: it follows the pointer, and let go it returns to its rest (Fusion). The
     Arm is where it was; nothing is left open. Ctrl+Z / Ctrl+Y of the limits.
  D  Edit Joint Limits, Rest 30, OK: the Arm goes to 30; dragged to another angle and let
     go, it is back at 30.
  E  Save, reopen: limits and rest are kept, a drag still returns to rest.
  F  An animation stopped at any moment of its swing, also where it is a few hundredths of
     a degree from its start: the Arm is put back exactly, and a tick that was already on
     its way moves nothing (the cause of CI's vex_shaft flake).
"""

import os
import tempfile

import FreeCAD as App

from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import book_joints_steps as bj
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import joints_steps as j
from Fission180Tests.gui import widget_input as w

V = App.Vector
S = {}
PIVOT = V(10, 20, 9)  # the middle of the Arm's end edge, on its top
ARM_TOP = V(30, 21, 9)
BASE_TOP = V(50, 5, 5)
TIP = V(38, 20, 9)  # near the Arm's free end


def jm():
    return bj.jm()


def joint():
    return bj.joint("Revolute 1")


def angle():
    return jm().value(joint())[0]


def limits():
    return jm().limits(joint())["angle"]


def rows(p):
    return p.angle_limits.rows


def shown(p):
    out = {}
    for key, (check, field) in rows(p).items():
        out[key] = round(field.value(), 6) if check.isChecked() else None
    return out


def setup():
    bj.new_design("BookJointsLimits")
    bj.box("Base", (60, 40, 5))
    bj.box("Arm", (30, 6, 4), V(10, 17, 5))
    jm().ground(bj.part("Base"))
    bj.doc().recompute()
    h.fit()
    S["arm"] = bj.place(bj.part("Arm"))
    S["base"] = bj.place(bj.part("Base"))


# -- A ------------------------------------------------------------------------------------------
def a_command():
    j.menu("As-built Joint")


def a_arm():
    h.click(ARM_TOP)


def a_base():
    h.click(BASE_TOP)


def a_revolute():
    p = j.panel()
    h.check("Arm and Base taken", [x.Label for x in p.parts] == ["Arm", "Base"], p.parts)
    j.choose_type(p, "Revolute")


def a_position():
    h.view().viewTop()
    h.fit(iso=False)
    bj.hover_point(V(11.5, 20, 9))


def a_position_click():
    spot = bj.hot(j.panel())
    h.check(
        "the middle of the Arm's end edge is lit",
        spot is not None and (spot["point"] - PIVOT).Length < 1e-6,
        spot and (spot["kind"], spot["point"]),
    )
    h.click(V(11.5, 20, 9))


def a_maximum():
    p = j.panel()
    h.check("Revolute 1 previewed", joint() is not None, bj.labels())
    h.check("Flip is greyed while no limit is on", not p.angle_limits.flip.isEnabled())
    s.toggle(rows(p)["max"][0])


def a_maximum_shows_now():
    p = j.panel()
    h.check("Maximum shows the joint's value now (0)", shown(p)["max"] == 0, shown(p))
    h.check("Flip can be pressed now", p.angle_limits.flip.isEnabled())
    s.type_value(rows(p)["max"][1].widget, "60")


def a_flip():
    p = j.panel()
    h.check("Maximum 60 on the joint", limits()["max"] == 60, limits())
    w.click(p.angle_limits.flip)


def a_flipped():
    p = j.panel()
    h.check(
        "Flip: Minimum -60, no Maximum",
        shown(p) == {"min": -60, "max": None, "rest": None},
        shown(p),
    )
    h.check("on the joint too", limits()["min"] == -60 and limits()["max"] is None, limits())
    w.click(p.angle_limits.flip)


def a_flipped_back():
    p = j.panel()
    h.check("Flip again: Maximum 60", shown(p) == {"min": None, "max": 60, "rest": None}, shown(p))
    s.toggle(rows(p)["min"][0])
    s.type_value(rows(p)["min"][1].widget, "-20")


def a_both():
    p = j.panel()
    h.check("-20 .. 60", limits()["min"] == -20 and limits()["max"] == 60, limits())
    w.click(p.angle_limits.flip)


def a_both_flipped():
    p = j.panel()
    h.check("Flip: -60 .. 20", shown(p) == {"min": -60, "max": 20, "rest": None}, shown(p))
    w.click(p.angle_limits.flip)


def a_both_back():
    h.check("Flip again: -20 .. 60", limits()["min"] == -20 and limits()["max"] == 60, limits())


# -- B ------------------------------------------------------------------------------------------
def b_preview():
    p = j.panel()
    w.click(p.angle_limits.preview)
    S["samples"] = bj.sample(lambda: j.panel().animator, joint(), [bj.part("Arm")])


def b_previewed():
    p = j.panel()
    samples = S.get("samples") or []
    h.check("the preview plays", len(samples) >= 5, len(samples))
    angles = [r["angle"] for r in samples]
    h.check("the Arm swings", j.spread(angles) > 40, j.spread(angles))
    h.check(
        "between its limits",
        bool(angles) and min(angles) >= -20 - 1e-6 and max(angles) <= 60 + 1e-6,
        (min(angles), max(angles)) if angles else None,
    )
    animator = p.animator
    h.check("alone: nothing else is asked to follow", animator is not None and animator.alone)
    h.check("only this motion", animator is not None and animator.motions == ("angle",))
    h.check("the button is down", p.angle_limits.preview.isChecked())
    h.check("the Base stays", not bj.moved(bj.place(bj.part("Base")), S["base"]))
    s.toggle(p.angle_limits.all_limits)


def b_with_all():
    p = j.panel()
    animator = p.animator
    h.check(
        "With All Limits: the joint plays with everything tied to it",
        animator is not None
        and animator.running
        and not animator.alone
        and animator.motions is None,
        animator and (animator.alone, animator.motions),
    )
    w.click(p.angle_limits.preview)


b_preview.while_busy = b_previewed.while_busy = b_with_all.while_busy = True


def b_stopped():
    p = j.panel()
    h.check("pressed again: the preview stopped", p.animator is None)
    h.check("the button is up", not p.angle_limits.preview.isChecked())
    h.check("the Arm stands where it was", not bj.moved(bj.place(bj.part("Arm")), S["arm"]))
    h.check("the limits are still -20 .. 60", limits()["min"] == -20 and limits()["max"] == 60)
    j.ok()


def b_done():
    j.no_dialog("As-built Joint OK")
    h.check("Revolute 1 made", joint() is not None and joint().JointType == "Revolute")
    h.check("-20 .. 60 kept", limits()["min"] == -20 and limits()["max"] == 60, limits())
    bj.no_open_step("As-built Joint OK")


# -- C ------------------------------------------------------------------------------------------
def c_limits():
    j.browser_menu("Revolute 1", "Edit Joint Limits")


def c_rest():
    p = j.panel()
    h.check(
        "the limits dialog shows -20 .. 60",
        shown(p) == {"min": -20, "max": 60, "rest": None},
        shown(p),
    )
    s.toggle(rows(p)["rest"][0])


def c_rest_ok():
    p = j.panel()
    h.check("Rest shows the joint's value now (0)", shown(p)["rest"] == 0, shown(p))
    j.ok()


def c_drag():
    j.no_dialog("Edit Joint Limits OK")
    h.check("Rest 0 stored", limits()["rest"] == 0, limits())
    S["undos"] = bj.doc().UndoCount
    S["seen"] = []
    watch_drag()
    h.drag(h.screen_point(TIP), h.screen_point(V(30, 40, 9)), steps=14)
    h.settle("the drag to be applied")


def watch_drag():
    """Note the joint's angle at every move of the drag (it must follow the pointer before
    it goes back to rest)."""
    from fission180 import joints_drag

    original = joints_drag.DragSession.follow

    def follow(self, pos):
        original(self, pos)
        try:
            S["seen"].append(jm().value(joint())[0])
        except Exception:
            pass

    joints_drag.DragSession.follow = follow
    S["unwatch"] = lambda: setattr(joints_drag.DragSession, "follow", original)


def c_rested():
    from fission180 import joints_drag

    S["unwatch"]()
    seen = S["seen"]
    h.check("while dragged the Arm followed the pointer", bool(seen) and max(seen) > 25, seen[-3:])
    h.check("let go, it is back at its rest", abs(angle()) < 1e-6, angle())
    h.check("the Arm is where it was", not bj.moved(bj.place(bj.part("Arm")), S["arm"]))
    last = joints_drag.last() or {}
    h.check("the drag says it went back to rest", last.get("rested") == [joint().Name], last)
    h.check("no drag left running", joints_drag.active() is None)
    bj.no_open_step("a drag that returned to rest")
    h.check(
        "nothing to undo of it", bj.doc().UndoCount == S["undos"], (S["undos"], bj.doc().UndoCount)
    )


def c_undo():
    s.undo()


def c_undone():
    h.check(
        "Ctrl+Z: the rest is gone, the limits stay",
        limits() == {"min": -20, "max": 60, "rest": None},
        limits(),
    )


def c_redo():
    s.redo()


def c_redone():
    h.check("Ctrl+Y: the rest is back", limits()["rest"] == 0, limits())
    bj.no_open_step("undo and redo")


# -- D ------------------------------------------------------------------------------------------
def d_limits():
    j.browser_menu("Revolute 1", "Edit Joint Limits")


def d_rest_30():
    p = j.panel()
    s.type_value(rows(p)["rest"][1].widget, "30")


def d_ok():
    j.ok()


def d_at_30():
    j.no_dialog("Edit Joint Limits OK")
    h.check("OK put the Arm at its rest, 30", abs(angle() - 30) < 1e-6, angle())
    S["arm30"] = bj.place(bj.part("Arm"))
    tip = jm().global_placement(bj.part("Arm")).multVec(V(38, 20, 9))
    h.drag(h.screen_point(tip), h.screen_point(V(40, 22, 9)), steps=12)
    h.settle("the drag to be applied")


def d_back_at_30():
    h.check("dragged away and let go: back at 30", abs(angle() - 30) < 1e-6, angle())
    h.check("the Arm is where its rest puts it", not bj.moved(bj.place(bj.part("Arm")), S["arm30"]))
    bj.no_open_step("the second drag")


# -- E ------------------------------------------------------------------------------------------
def e_save_close():
    S["path"] = os.path.join(tempfile.mkdtemp(), "book_joints_limits.FCStd")
    bj.doc().saveAs(S["path"])
    App.closeDocument(bj.doc().Name)


def e_open():
    App.openDocument(S["path"])
    h.view().viewTop()
    h.fit(iso=False)


def e_reopened():
    h.check(
        "the limits and the rest are kept",
        limits() == {"min": -20, "max": 60, "rest": 30},
        limits(),
    )
    h.check("still at 30", abs(angle() - 30) < 1e-6, angle())
    tip = jm().global_placement(bj.part("Arm")).multVec(V(38, 20, 9))
    h.drag(h.screen_point(tip), h.screen_point(V(40, 22, 9)), steps=12)
    h.settle("the drag to be applied")


def e_rest_again():
    h.check("a drag still returns to rest", abs(angle() - 30) < 1e-6, angle())
    h.check("the solver is happy", jm().solve(bj.doc()) == 0)
    bj.no_open_step("reopening and dragging")


# -- F: an animation stopped at any moment leaves nothing turned -----------------------------------
def f_stopped_anywhere():
    """The preview stopped where its swing is a few hundredths of a degree from where it
    began (its first and last frames, where a slow machine's last tick may land) and in
    mid-swing: the Arm is put back exactly each time, and a tick that was already on its way
    when it stopped moves nothing. (CI's vex_shaft found the part turned 0.0175 to 0.03
    degrees after OK: the restore skipped a placement FreeCAD's isSame called the same.)"""
    import time

    from fission180 import joints_ui

    arm = bj.part("Arm")
    home = App.Placement(arm.Placement)
    seen = []
    for alone in (True, False):
        for seconds in (0.0003, 0.0009, 0.45, 0.9, 1.7991, 1.7997):
            animator = joints_ui.Animator(joint(), loop=True, alone=alone)
            animator.start()
            animator.started = time.perf_counter() - seconds  # as if it had played that long
            animator._tick()
            away = abs(angle() - 30)
            animator.stop()
            exact = jm().same_place(arm.Placement, home)
            animator._tick()  # the tick that was already queued when it stopped
            late = jm().same_place(arm.Placement, home)
            seen.append((alone, seconds, round(away, 5), exact, late))
    tiny = [x for x in seen if 0 < x[2] < 0.036]
    h.check(
        "some frames stood within a few hundredths of a degree of the start", len(tiny) >= 2, seen
    )
    h.check("stopped there, the Arm is put back exactly", all(x[3] for x in seen), seen)
    h.check("a tick after the stop moves nothing", all(x[4] for x in seen), seen)
    h.check("the joint reads its rest again", abs(angle() - 30) < 1e-9, angle())


def f_exact_restore():
    arm = bj.part("Arm")
    home = jm().placements(bj.doc())
    was = App.Placement(arm.Placement)
    # turned 0.02 degrees where it stands (about its own origin, as a shaft turns about its
    # axis): only the rotation differs, by less than isSame's 1e-7 can tell
    spin = App.Rotation(V(0, 0, 1), 0.02)
    arm.Placement = App.Placement(was.Base, spin.multiply(was.Rotation))
    h.check("the Arm is turned", not jm().same_place(arm.Placement, was))
    h.check("FreeCAD calls a 0.02 degree turn the same placement", arm.Placement.isSame(was, 1e-7))
    jm().apply_placements(bj.doc(), home)
    h.check("the positions are put back exactly all the same", jm().same_place(arm.Placement, was))
    h.check("the solver is happy", jm().solve(bj.doc()) == 0)


steps = [setup, a_command, a_arm, a_base, a_revolute, a_position, a_position_click]
steps += [a_maximum, a_maximum_shows_now, a_flip, a_flipped, a_flipped_back, a_both]
steps += [a_both_flipped, a_both_back, b_preview, b_previewed, b_with_all, b_stopped, b_done]
steps += [c_limits, c_rest, c_rest_ok, c_drag, c_rested, c_undo, c_undone, c_redo, c_redone]
steps += [
    d_limits,
    d_rest_30,
    d_ok,
    d_at_30,
    d_back_at_30,
    e_save_close,
    e_open,
    e_reopened,
    e_rest_again,
]

steps += [f_stopped_anywhere, f_exact_restore]

h.run("book_joints_limits", steps, paced_by="state")
