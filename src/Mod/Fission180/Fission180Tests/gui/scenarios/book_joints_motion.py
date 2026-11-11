# SPDX-License-Identifier: LGPL-2.1-or-later
"""A screw (Motion Link > Link with Same Joint), a four-bar loop that follows a drag, and
Fusion's two animations of a joint (the book parity report: Pizza Cutter, Tesla Turbine,
Strandbeest), with real input (docs/fission180/parity/joints.md).

A Screw standing in a Nut (grounded) on an as-built Cylindrical joint, and a four-bar
linkage: a grounded bar, a crank (40), a rocker (60) and a coupler, on four as-built
Revolute joints (the parts and these joints are made by script with the dialogs' own
functions; everything tested is real input).

  A  ASSEMBLE > Motion Link, the Cylindrical joint's browser row, Link with Same Joint
     ticked: its rotation and its slide get a value each; 360 deg and 2 mm typed (a 2 mm
     pitch). Animate: the screw turns and climbs, 2 mm a turn, at every frame. OK.
  B  Drive Joints, Rotation 720: the Screw stands 4 mm higher. Cancel puts it back.
  C  Edit Motion Link, Reverse, OK: a turn now screws it down. Ctrl+Z / Ctrl+Y.
  D  The crank dragged in the top view: the whole loop follows (the rocker swings, every
     joint still holds), one undo step; Ctrl+Z puts all four bars back.
  E  Right-click the crank's joint > Animate Joint: the crank swings alone (the rocker
     stands still); Esc. Animate Joint Relationships: the rocker swings with it; Esc:
     everything stands where it was.
  F  A motion link refused: Link with Same Joint ticked for a Revolute joint (one motion).
  G  Save, reopen: the screw still climbs 2 mm a turn (reversed), the loop still holds.
"""

import os
import tempfile

import FreeCAD as App
from PySide import QtCore

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import book_joints_steps as bj
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import joints_steps as j
from Fission180Tests.gui import timeline_input as t
from Fission180Tests.gui import widget_input as w

V = App.Vector
S = {}
Y0 = 60.0  # the four-bar's ground line


def jm():
    return bj.jm()


def screw_joint():
    return bj.joint("Cylindrical 1")


def bars():
    return [bj.part(name) for name in ("Crank", "Coupler", "Rocker")]


def as_built(kind, a, b_part, element_test, at):
    """An as-built joint between two components with its position at the snap of `a`
    nearest `at` on the element `element_test` picks (the dialog's own function)."""
    body = [o for o in a.Group if o.TypeId == "PartDesign::Body"][0]
    shape = body.Shape
    names = ["Face%d" % (i + 1) for i in range(len(shape.Faces))]
    names += ["Edge%d" % (i + 1) for i in range(len(shape.Edges))]
    best = None
    for name in names:
        if not element_test(name, shape.getElement(name)):
            continue
        pick = jm().Pick(a, body, name)
        for snap in jm().snap_candidates(pick):
            d = (snap["point"] - at).Length
            if best is None or d < best[0]:
                best = (d, pick, snap)
    made = jm().create_as_built_joint(bj.doc(), kind, a, b_part, best[1], best[2])
    return made, best[0]


def setup():
    bj.new_design("BookJointsMotion")
    nut = bj.cylinder("Nut", 8, 6, hole=4)
    screw = bj.cylinder("Screw", 4, 12)
    ground = bj.box("Ground Bar", (100, 10, 5), V(0, Y0 - 5, 0))
    crank = bj.box("Crank", (10, 40, 5), V(-5, Y0, 6))
    rocker = bj.box("Rocker", (10, 60, 5), V(95, Y0, 6))
    coupler = bj.box("Coupler", (110, 10, 5), V(-5, Y0 + 35, 12))
    d = bj.doc()
    jm().ground(nut)
    jm().ground(ground)

    def top_rim(name, el):
        return name.startswith("Edge") and el.Curve.TypeId == "Part::GeomCircle"

    def top_face(name, el):
        return name.startswith("Face") and abs(el.CenterOfMass.z - 11) < 1e-6

    _made, off = as_built("cylindrical", screw, nut, top_rim, V(0, 0, 12))
    S["offs"] = [off]
    for a, c, at in (
        (crank, ground, V(0, Y0, 11)),
        (crank, coupler, V(0, Y0 + 40, 11)),
        (rocker, ground, V(100, Y0, 11)),
        (rocker, coupler, V(100, Y0 + 60, 11)),
    ):
        _made, off = as_built("revolute", a, c, top_face, at)
        S["offs"].append(off)
    d.recompute()
    from fission180 import joints_ui

    joints_ui.attach_views(d)
    jm().save_baseline(d)
    h.fit()


def made():
    h.check("the positions are where they were meant", max(S["offs"]) < 1e-6, S["offs"])
    h.check(
        "one Cylindrical and four Revolute joints",
        bj.labels() == ["Cylindrical 1", "Revolute 1", "Revolute 2", "Revolute 3", "Revolute 4"],
        bj.labels(),
    )
    h.check("the solver is happy", jm().solve(bj.doc()) == 0, jm().broken_joints(bj.doc()))
    S["screw"] = bj.place(bj.part("Screw"))
    S["bars"] = [bj.place(x) for x in bars()]


# -- A ------------------------------------------------------------------------------------------
def a_command():
    j.menu("Motion Link")


def a_pick():
    p = j.panel()
    h.check("Motion Link open", p is not None and p.title == "Motion Link", p and p.title)
    t.click_row("Cylindrical 1")


def a_same():
    p = j.panel()
    h.check("the joint is taken", p.picked == [screw_joint()], p.picked)
    s.toggle(p.same)


def a_values():
    p = j.panel()
    h.check("the joint is linked with itself", p._same(), p.picked)
    captions = [row["caption"].text() for row in p.rows]
    h.check(
        "its rotation and its slide each get a value",
        captions == ["Cylindrical 1: its rotation", "Cylindrical 1: its slide"],
        captions,
    )
    h.check("Reverse and Animate are there", p.reverse.isVisible() and p.animate.isVisible())
    s.type_value(p.rows[1]["field"].widget, "2")


def a_animate():
    p = j.panel()
    h.check("a link is previewed", p.link is not None, p.message.text())
    h.check(
        "the note says 2 mm a turn", "slides 2 mm for each turn" in p.note.text(), p.note.text()
    )
    w.click(p.animate)
    S["samples"] = bj.sample(lambda: j.panel().animator, screw_joint(), [bj.part("Screw")])


def a_watched():
    samples = S.get("samples") or []
    h.check("the animation plays", len(samples) >= 5, len(samples))
    h.check("the screw turns", bj.spread(r["angle"] for r in samples) > 40)
    off = [r for r in samples if abs(r["slide"] - r["angle"] * 2.0 / 360.0) > 1e-6]
    h.check("and climbs 2 mm a turn at every frame", not off, off[:3])
    w.click(j.panel().animate)


a_animate.while_busy = a_watched.while_busy = True


def a_ok():
    p = j.panel()
    h.check("Animate stopped", p.animator is None)
    h.check("the Screw stands where it was", not bj.moved(bj.place(bj.part("Screw")), S["screw"]))
    j.ok()


def a_done():
    j.no_dialog("Motion Link OK")
    links = jm().motion_links(bj.doc())
    h.check(
        "Motion Link 1 ties the joint to itself",
        len(links) == 1 and links[0].Joint1 is screw_joint() and links[0].Joint2 is screw_joint(),
        links,
    )
    h.check("it is in the browser's Joints folder", "Motion Link 1" in (t.children("Joints") or []))
    bj.no_open_step("Motion Link OK")


# -- B ------------------------------------------------------------------------------------------
def b_drive():
    j.browser_menu("Cylindrical 1", "Drive Joints")


def b_type():
    p = j.panel()
    h.check("Drive Joints open", p is not None and p.title == "Drive Joints", p and p.title)
    s.type_value(p.angle.widget, "720")


def b_driven():
    angle, slide = jm().value(screw_joint())
    h.check("two turns", abs(angle - 720) < 1e-6, angle)
    h.check("the screw climbed 4 mm", abs(slide - 4) < 1e-6, slide)
    now = bj.place(bj.part("Screw"))
    h.check("the Screw stands 4 mm higher", abs(now[2] - S["screw"][2] - 4) < 1e-5, now)
    j.cancel()


def b_cancelled():
    j.no_dialog("Drive Joints Cancel")
    h.check("Cancel put the Screw back", not bj.moved(bj.place(bj.part("Screw")), S["screw"]))
    bj.no_open_step("Drive Joints Cancel")


# -- C ------------------------------------------------------------------------------------------
def c_edit():
    j.browser_menu("Motion Link 1", "Edit Motion Link")


def c_reverse():
    p = j.panel()
    h.check(
        "the link's dialog shows Link with Same Joint ticked",
        p is not None and p.editing and p.same.isChecked() and p._same(),
        p and p.title,
    )
    h.check("and 2 mm", abs(p.rows[1]["field"].value() - 2) < 1e-9, p.rows[1]["field"].value())
    s.toggle(p.reverse)


def c_ok():
    j.ok()


def c_reversed():
    j.no_dialog("Edit Motion Link OK")
    h.check("reversed", jm().link_data(jm().motion_links(bj.doc())[0])["reverse"] is True)
    got = jm().tie_own_motions(screw_joint(), angle=360.0)
    h.check("a turn now screws it down 2 mm", abs(got[1] + 2) < 1e-9, got)
    bj.no_open_step("Edit Motion Link OK")


def c_undo():
    s.undo()


def c_undone():
    h.check(
        "Ctrl+Z: not reversed", jm().link_data(jm().motion_links(bj.doc())[0])["reverse"] is False
    )


def c_redo():
    s.redo()


def c_redone():
    h.check("Ctrl+Y: reversed", jm().link_data(jm().motion_links(bj.doc())[0])["reverse"] is True)


# -- D ------------------------------------------------------------------------------------------
def d_drag():
    h.view().viewTop()
    h.fit(iso=False)
    S["undos"] = bj.doc().UndoCount
    h.drag(h.screen_point(V(0, Y0 + 33, 11)), h.screen_point(V(14, Y0 + 30, 11)), steps=16)
    h.settle("the drag to be applied")


def d_followed():
    from fission180 import joints_drag

    crank = jm().value(bj.joint("Revolute 1"))[0]
    rocker = jm().value(bj.joint("Revolute 3"))[0]
    h.check("the crank turned", abs(crank) > 8, crank)
    h.check("the rocker swung with it", abs(rocker) > 3, rocker)
    h.check("the coupler moved", bj.moved(bj.place(bj.part("Coupler")), S["bars"][1]))
    h.check(
        "every joint of the loop still holds",
        not jm().broken_joints(bj.doc()),
        jm().broken_joints(bj.doc()),
    )
    last = joints_drag.last() or {}
    h.check(
        "it was a drag along the crank's joint",
        last.get("joint") == bj.joint("Revolute 1").Name,
        last,
    )
    h.check("one undo step", bj.doc().UndoCount == S["undos"] + 1, (S["undos"], bj.doc().UndoCount))
    bj.no_open_step("the drag")
    S["dragged"] = (crank, rocker)
    h.shot("D-loop-dragged")


def d_undo():
    s.undo()


def d_undone():
    now = [bj.place(x) for x in bars()]
    h.check(
        "Ctrl+Z: all the bars are back",
        not any(bj.moved(a, c) for a, c in zip(now, S["bars"])),
        now,
    )
    h.check("the loop holds", not jm().broken_joints(bj.doc()))


# -- E ------------------------------------------------------------------------------------------
def e_animate():
    h.fit()
    j.browser_menu("Revolute 1", "Animate Joint")
    S["alone"] = bj.sample(bj.standalone_animator, bj.joint("Revolute 1"), bars())


def e_alone():
    samples = S.get("alone") or []
    h.check("Animate Joint plays", len(samples) >= 5, len(samples))
    h.check("the crank swings", bj.spread(r["angle"] for r in samples) > 40)
    still = all(not bj.moved(r["places"][2], S["bars"][2]) for r in samples)
    h.check("alone: the rocker stands still", still)
    animator = bj.standalone_animator()
    h.check("it is the joint alone", animator is not None and animator.alone)
    b.press_guarded(QtCore.Qt.Key_Escape)


def e_stopped():
    now = [bj.place(x) for x in bars()]
    h.check(
        "Esc: everything stands where it was",
        not any(bj.moved(a, c) for a, c in zip(now, S["bars"])),
    )
    h.check("the loop holds", not jm().broken_joints(bj.doc()))
    entries = [e[0] for e in t.row_menu_entries("Revolute 1")]
    h.check(
        "the menu has both animations",
        "Animate Joint" in entries and "Animate Joint Relationships" in entries,
        entries,
    )


def e_animate_all():
    j.browser_menu("Revolute 1", "Animate Joint Relationships")
    S["all"] = bj.sample(bj.standalone_animator, bj.joint("Revolute 1"), bars())


def e_all():
    samples = S.get("all") or []
    h.check("Animate Joint Relationships plays", len(samples) >= 5, len(samples))
    h.check("the crank swings", bj.spread(r["angle"] for r in samples) > 10)
    swung = any(bj.moved(r["places"][2], S["bars"][2]) for r in samples)
    h.check("the rocker swings with it", swung)
    animator = bj.standalone_animator()
    h.check("with its relationships", animator is not None and not animator.alone)
    b.press_guarded(QtCore.Qt.Key_Escape)


e_animate.while_busy = e_alone.while_busy = True
e_animate_all.while_busy = e_all.while_busy = True


def e_stopped_all():
    now = [bj.place(x) for x in bars()]
    h.check(
        "Esc: everything stands where it was",
        not any(bj.moved(a, c) for a, c in zip(now, S["bars"])),
    )
    h.check("the loop holds", not jm().broken_joints(bj.doc()))
    bj.no_open_step("the animations")


# -- F ------------------------------------------------------------------------------------------
def f_command():
    h.click_empty()  # (the joint's row is still selected from its menu: nothing preselected)
    j.menu("Motion Link")


def f_pick():
    t.click_row("Revolute 1")


def f_same():
    p = j.panel()
    h.check("the Revolute joint is taken", p.picked == [bj.joint("Revolute 1")], p.picked)
    s.toggle(p.same)


def f_refused():
    p = j.panel()
    h.check(
        "Link with Same Joint is not ticked for a joint with one motion", not p.same.isChecked()
    )
    h.check("and it says why", "one motion only" in p.message.text(), p.message.text())
    j.cancel()


def f_cancelled():
    j.no_dialog("Motion Link Cancel")
    h.check("still one motion link", len(jm().motion_links(bj.doc())) == 1)
    bj.no_open_step("Motion Link Cancel")


# -- G ------------------------------------------------------------------------------------------
def g_save_close():
    S["path"] = os.path.join(tempfile.mkdtemp(), "book_joints_motion.FCStd")
    bj.doc().saveAs(S["path"])
    App.closeDocument(bj.doc().Name)


def g_open():
    App.openDocument(S["path"])
    h.fit()


def g_drive():
    links = jm().motion_links(bj.doc())
    h.check(
        "the link with the same joint is back",
        len(links) == 1 and links[0].Joint1 is screw_joint() and links[0].Joint2 is screw_joint(),
        links,
    )
    h.check("the loop holds", jm().solve(bj.doc()) == 0 and not jm().broken_joints(bj.doc()))
    j.browser_menu("Cylindrical 1", "Drive Joints")


def g_type():
    p = j.panel()
    s.type_value(p.angle.widget, "360")


def g_driven():
    angle, slide = jm().value(screw_joint())
    h.check(
        "a turn screws it 2 mm down (reversed)",
        abs(angle - 360) < 1e-6 and abs(slide + 2) < 1e-6,
        (angle, slide),
    )
    j.cancel()


def g_done():
    j.no_dialog("Drive Joints Cancel")
    bj.no_open_step("reopening and driving")


steps = [setup, made, a_command, a_pick, a_same, a_values, a_animate, a_watched, a_ok, a_done]
steps += [b_drive, b_type, b_driven, b_cancelled]
steps += [c_edit, c_reverse, c_ok, c_reversed, c_undo, c_undone, c_redo, c_redone]
steps += [d_drag, d_followed, d_undo, d_undone]
steps += [e_animate, e_alone, e_stopped, e_animate_all, e_all, e_stopped_all]
steps += [f_command, f_pick, f_same, f_refused, f_cancelled]
steps += [g_save_close, g_open, g_drive, g_type, g_driven, g_done]

h.run("book_joints_motion", steps, paced_by="state")
