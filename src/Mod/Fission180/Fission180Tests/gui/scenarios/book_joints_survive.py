# SPDX-License-Identifier: LGPL-2.1-or-later
"""Joints that survive edits of the parts they were made on (the book parity report's bug
14, Pizza Cutter: "Broken link in Reference1", "?Face5", "?Edge41", "the joints cannot all be
satisfied together" after later edits), with real input for the joints
(docs/fission180/parity/joints.md, "References that survive edits").

A Handle (grounded), a Bracket (a block with a round hole through it) and a Bolt. The two
joints are made with the dialog: J, the Bracket's top onto the Handle's top (Rigid: the
Bracket turns over onto the Handle); J, the Bolt's end onto the rim of the Bracket's hole that
now faces up (Revolute). Then the earlier steps are edited
(by script: the edits are not what is tested) and after each one the joints are looked at.

  A  The two joints, by clicks.
  B  A fillet on the Bracket's corner edges (its faces and edges are numbered anew): both
     joints find their faces again, nothing moves, nothing is lost.
  C  The Bracket made higher (the face the Bolt sits on moves up): the Bolt goes up with it.
  D  The hole made wider and moved: the Bolt follows the hole.
  E  A chamfer moved before the fillet in the Bracket's history, the body renamed: nothing
     is lost, nothing moves.
  F  The Bolt's body moved into another component: its joint follows it there.
  G  The history marker rolled back before the hole (the rim is not there): the joints say
     nothing and are not "broken"; rolled forward, all is as before.
  H  The hole deleted (with the fillet and the chamfer after it): the Revolute joint lost
     what it was made on. It says so on its step
     and next to the mouse, the Bolt stays exactly where it was (no jump onto another
     face), the other joint goes on working, and nothing is printed in the Report view.
  I  Edit Joint on it: the dialog says which side to pick again; a click on the Bracket's
     top, OK: the joint works again and the note is gone. Ctrl+Z / Ctrl+Y. Save, reopen.
"""

import os
import tempfile

import FreeCAD as App

from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import book_joints_steps as bj
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import joints_steps as j
from Fission180Tests.gui import timeline_input as t

V = App.Vector
S = {}
HOLE = (60.0, 15.0)  # the hole's axis in the Bracket as it is made (beside the Handle)


def jm():
    return bj.jm()


def d():
    return bj.doc()


def obj(name):
    return d().getObject(name)


def rigid():
    return bj.joint("Rigid 1")


def revolute():
    return bj.joint("Revolute 1")


def fine(where):
    """Every joint holds, none is lost, the solver has nothing to do."""
    lost = [x.Label for x in jm().lost_joints(d())]
    broken = [x.Label for x in jm().broken_joints(d())]
    h.check("%s: no joint lost what it was made on" % where, not lost, lost)
    h.check("%s: every joint holds" % where, not broken, broken)
    refs = [sub for x in jm().joints(d()) for r in (x.Reference1, x.Reference2) for sub in r[1]]
    h.check("%s: no reference is marked lost" % where, not any("?" in x for x in refs), refs)


def bolt_part():
    return bj.part("Fasteners") or bj.part("Bolt")


def bolt_on_hole(where):
    """The Bolt's axis is on the hole's axis, wherever the Bracket and its hole are now."""
    bracket = bj.part("Bracket")
    hole = obj("BracketHole")
    centre = jm().global_placement(bracket).multVec(hole.Placement.Base)
    bolt = bj.box_centre(bolt_part())
    off = ((bolt.x - centre.x) ** 2 + (bolt.y - centre.y) ** 2) ** 0.5
    return h.check("%s: the Bolt is on the hole's axis" % where, off < 1e-4, (bolt, centre))


def settle_joints():
    """What the app does by itself a moment after a recompute (the joints' watch)."""
    d().recompute()
    h.settle("the joints to follow the edit")


def setup():
    bj.new_design("BookJointsSurvive")
    bj.box("Handle", (40, 30, 10))
    bj.cylinder("Bolt", 3, 16, V(100, 15, 0))
    doc = d()
    body = doc.addObject("PartDesign::Body", "BracketBody")
    block = doc.addObject("PartDesign::AdditiveBox", "BracketBox")
    body.addObject(block)
    block.Length, block.Width, block.Height = 30, 30, 8
    block.Placement.Base = V(45, 0, 0)
    hole = doc.addObject("PartDesign::SubtractiveCylinder", "BracketHole")
    body.addObject(hole)
    hole.Radius, hole.Height = 4, 8
    hole.Placement.Base = V(HOLE[0], HOLE[1], 0)
    doc.recompute()
    from fission180 import components

    components.from_bodies(doc, [body], label="Bracket")
    jm().ground(bj.part("Handle"))
    doc.recompute()
    h.fit()


# -- A ------------------------------------------------------------------------------------------
def a_press_j():
    j.press_j()


def a_bracket_bottom():
    h.click(V(50, 5, 8))  # the Bracket's top: it mates onto the Handle's top (turned over)


def a_handle_top():
    h.click(V(20, 14, 10))


def a_ok():
    p = j.panel()
    h.check("a joint is previewed", p is not None and p.joint is not None, p and p.info.text())
    j.ok()


def a_press_j2():
    j.no_dialog("Joint OK")
    h.fit()
    j.press_j()


def a_bolt_end():
    h.click_edge(bj.rim((100, 15), 3, 16, 250))


def a_hole_rim():
    bracket = bj.part("Bracket")
    # the Bracket lies turned over on the Handle: the end of its hole that faces up now
    S["rim"] = jm().global_placement(bracket).multVec(V(HOLE[0], HOLE[1], 0))
    h.check(
        "the Bracket lies on the Handle, its hole facing up", abs(S["rim"].z - 18) < 1e-4, S["rim"]
    )
    bj.hover_edge(S["rim"] + bj.rim((0, 0), 4, 0, 250))


def a_hole_click():
    spot = bj.hot(j.panel())
    h.check(
        "the rim of the hole offers the hole's centre",
        spot is not None and (spot["point"] - S["rim"]).Length < 1e-5,
        spot and (spot["kind"], spot["point"]),
    )
    h.click_edge(S["rim"] + bj.rim((0, 0), 4, 0, 250))


def a_revolute():
    p = j.panel()
    j.click_tab(p, "Motion")
    j.choose_type(p, "Revolute")


def a_ok2():
    j.ok()


def a_made():
    j.no_dialog("Joint OK")
    h.check("Rigid 1 and Revolute 1", bj.labels() == ["Rigid 1", "Revolute 1"], bj.labels())
    bj.no_open_step("the two joints")
    settle_joints()
    fine("made")
    bolt_on_hole("made")
    S["bracket"] = bj.place(bj.part("Bracket"))
    S["bolt"] = bj.place(bj.part("Bolt"))
    S["names"] = [list(x.Reference1[1]) + list(x.Reference2[1]) for x in jm().joints(d())]


# -- B ------------------------------------------------------------------------------------------
def b_fillet():
    doc = d()
    body = obj("BracketBody")
    tip = body.Tip
    upright = [
        "Edge%d" % (i + 1)
        for i, e in enumerate(tip.Shape.Edges)
        if e.Curve.TypeId == "Part::GeomLine"
        and abs(e.tangentAt(e.FirstParameter).z) > 0.99
        and e.Length > 7.9
        and (e.valueAt(e.FirstParameter) - V(HOLE[0], HOLE[1], 0)).Length > 10
    ]
    doc.openTransaction("Fillet")
    fillet = body.newObject("PartDesign::Fillet", "BracketFillet")
    fillet.Base = (tip, upright)
    fillet.Radius = 3
    body.Tip = fillet
    doc.commitTransaction()
    settle_joints()


def b_survived():
    names = [list(x.Reference1[1]) + list(x.Reference2[1]) for x in jm().joints(d())]
    S["renamed"] = names != S["names"]
    fine("after the fillet")
    h.check(
        "the fillet is there",
        not obj("BracketFillet").Shape.isNull() and len(obj("BracketBody").Shape.Faces) > 8,
    )
    h.check("the Bracket did not move", not bj.moved(bj.place(bj.part("Bracket")), S["bracket"]))
    h.check("the Bolt did not move", not bj.moved(bj.place(bj.part("Bolt")), S["bolt"]))
    bolt_on_hole("after the fillet")


# -- C ------------------------------------------------------------------------------------------
def c_higher():
    S["bolt_z"] = bj.box_centre(bj.part("Bolt")).z
    doc = d()
    doc.openTransaction("Edit Box")
    obj("BracketBox").Height = 12
    obj("BracketHole").Height = 12
    doc.commitTransaction()
    settle_joints()


def c_followed():
    fine("after the Bracket was made higher")
    z = bj.box_centre(bj.part("Bolt")).z
    h.check(
        "the Bolt went up with the face it sits on (4)",
        abs(z - S["bolt_z"] - 4) < 1e-4,
        z - S["bolt_z"],
    )
    bolt_on_hole("after the Bracket was made higher")


# -- D ------------------------------------------------------------------------------------------
def d_hole():
    doc = d()
    doc.openTransaction("Edit Hole")
    hole = obj("BracketHole")
    hole.Radius = 5
    hole.Placement.Base = V(HOLE[0] + 3, HOLE[1] - 2, 0)
    doc.commitTransaction()
    settle_joints()


def d_followed():
    fine("after the hole was widened and moved")
    bolt_on_hole("after the hole was widened and moved")
    S["bolt"] = bj.place(bj.part("Bolt"))
    S["bracket"] = bj.place(bj.part("Bracket"))


# -- E ------------------------------------------------------------------------------------------
def e_reorder_rename():
    doc = d()
    body = obj("BracketBody")
    tip = body.Tip
    doc.openTransaction("Chamfer")
    side = [
        "Edge%d" % (i + 1)
        for i, e in enumerate(tip.Shape.Edges)
        if e.Curve.TypeId == "Part::GeomLine"
        and abs(e.tangentAt(e.FirstParameter).x) > 0.99
        and abs(e.valueAt(e.FirstParameter).z) < 1e-6
    ][:1]
    chamfer = body.newObject("PartDesign::Chamfer", "BracketChamfer")
    chamfer.Base = (tip, side)
    chamfer.Size = 1
    body.Tip = chamfer
    body.Label = "Plate"
    doc.commitTransaction()
    settle_joints()


def e_survived():
    h.check("the body is renamed", obj("BracketBody").Label == "Plate")
    fine("after a chamfer and a rename")
    h.check("the Bolt did not move", not bj.moved(bj.place(bj.part("Bolt")), S["bolt"]))
    bolt_on_hole("after a chamfer and a rename")


# -- F ------------------------------------------------------------------------------------------
def f_move_body():
    from fission180 import components

    doc = d()
    doc.openTransaction("Move to Component")
    target = components.new_component(doc, "Fasteners")
    components.place(obj("BoltBody"), target)
    doc.commitTransaction()
    settle_joints()


def f_followed():
    joint = revolute()
    parts = [jm().part1(joint).Label, jm().part2(joint).Label]
    h.check("the joint follows the Bolt's body into Fasteners", "Fasteners" in parts, parts)
    h.check("it is still on", not joint.Suppressed)
    fine("after the body moved to another component")
    centre = bj.box_centre(bj.part("Fasteners"))
    hole = jm().global_placement(bj.part("Bracket")).multVec(obj("BracketHole").Placement.Base)
    off = ((centre.x - hole.x) ** 2 + (centre.y - hole.y) ** 2) ** 0.5
    h.check("the Bolt is still on the hole's axis", off < 1e-4, (centre, hole))
    S["fasteners"] = bj.place(bolt_part())


# -- G ------------------------------------------------------------------------------------------
def g_roll_back():
    from fission180 import timeline_ops

    doc = d()
    body = obj("BracketBody")
    S["tips"] = {body.Name: body.Tip.Name}
    timeline_ops.roll(doc, {body.Name: "BracketBox"})
    h.settle("the joints to see the marker")


def g_rolled():
    h.check("the Bracket is rolled back to its block", obj("BracketBody").Tip.Name == "BracketBox")
    h.check("the Revolute joint is rolled back with it", jm().rolled_back(revolute()))
    h.check("it is left out", revolute() not in jm().active_links(d()))
    h.check("nothing is called broken", not jm().broken_joints(d()), jm().broken_joints(d()))
    h.check("the Bolt stays", not bj.moved(bj.place(bolt_part()), S["fasteners"]))


def g_roll_forward():
    from fission180 import timeline_ops

    timeline_ops.roll(d(), S["tips"])
    settle_joints()


def g_forward():
    h.check("rolled forward: the joint is back", not jm().rolled_back(revolute()))
    fine("after rolling back and forward")
    h.check("the Bolt did not move", not bj.moved(bj.place(bolt_part()), S["fasteners"]))


# -- H ------------------------------------------------------------------------------------------
def h_delete_hole():
    doc = d()
    doc.openTransaction("Delete Hole")
    for name in ("BracketChamfer", "BracketFillet", "BracketHole"):
        doc.removeObject(name)
    obj("BracketBody").Tip = obj("BracketBox")
    obj("BracketBox").ViewObject.Visibility = True  # (the Tip is what a body shows)
    doc.commitTransaction()
    settle_joints()


def h_lost():
    joint = revolute()
    h.check("the Revolute joint lost what it was made on", jm().lost_reference(joint))
    h.check("it is listed as lost", [x.Label for x in jm().lost_joints(d())] == ["Revolute 1"])
    note = getattr(joint, "Fission180Warning", "")
    h.check("it says so on its step", "lost the face or edge" in note and "Bracket" in note, note)
    h.check("and next to the mouse", "Revolute 1 lost the face or edge" in bj.told(), bj.told())
    h.check(
        "the Bolt stays exactly where it was",
        not bj.moved(bj.place(bolt_part()), S["fasteners"]),
    )
    h.check("it is left out of the solver", joint not in jm().active_links(d()))
    h.check(
        "the other joint goes on working",
        not jm().broken_joints(d()) and rigid() in jm().active_links(d()),
    )
    state = t.states().get("Revolute 1")
    h.check(
        "the timeline shows a warning on it", state is not None and state[1] == "warning", state
    )
    h.check("the solver is happy with the rest", jm().solve(d()) == 0)


# -- I ------------------------------------------------------------------------------------------
def i_edit():
    j.browser_menu("Revolute 1", "Edit Joint")


def i_says():
    p = j.panel()
    h.check("the Joint dialog opened on it", p is not None and p.editing and p.joint is revolute())
    text = p.message.text() if p is not None else ""
    h.check(
        "it says which side to pick again",
        "pick that side again" in text and "Bracket" in text,
        text,
    )
    h.check(
        "that side's box waits", p is not None and p.active in ("comp1", "comp2"), p and p.active
    )
    S["side"] = p.active
    # the Bracket's face that is up, towards a corner; from above, so that the Bolt
    # standing on it hides nothing but its own foot
    h.view().viewTop()
    h.fit(iso=False)


def i_click():
    bolt = bj.box_centre(bolt_part())
    point = bj.top_of(bj.part("Bracket"), inset=1.5)
    if ((point.x - bolt.x) ** 2 + (point.y - bolt.y) ** 2) ** 0.5 < 5:
        point = bj.top_of(bj.part("Bracket"), inset=-1.5)
    h.click(point)


def i_ok():
    p = j.panel()
    h.check(
        "the side is picked again",
        p.snaps[S["side"]] is not None and p.message.text() == "",
        p.message.text(),
    )
    j.ok()


def i_works():
    j.no_dialog("Edit Joint OK")
    fine("after picking it again")
    h.check("the note is gone", getattr(revolute(), "Fission180Warning", "") == "")
    h.check("the joint works again", revolute() in jm().active_links(d()))
    bj.no_open_step("Edit Joint OK")


def i_undo():
    s.undo()


def i_undone():
    h.check("Ctrl+Z: lost again", jm().lost_reference(revolute()))


def i_redo():
    s.redo()


def i_redone():
    h.check("Ctrl+Y: it works again", not jm().lost_reference(revolute()))
    fine("after undo and redo")


def i_save_close():
    S["path"] = os.path.join(tempfile.mkdtemp(), "book_joints_survive.FCStd")
    d().saveAs(S["path"])
    App.closeDocument(d().Name)


def i_open():
    App.openDocument(S["path"])
    h.fit()


def i_reopened():
    settle_joints()
    fine("reopened")
    h.check("both joints are there", bj.labels() == ["Rigid 1", "Revolute 1"], bj.labels())
    h.check("the solver is happy", jm().solve(d()) == 0)
    bj.no_open_step("reopening")


steps = [setup, a_press_j, a_bracket_bottom, a_handle_top, a_ok, a_press_j2, a_bolt_end]
steps += [a_hole_rim, a_hole_click, a_revolute, a_ok2, a_made]
steps += [b_fillet, b_survived, c_higher, c_followed, d_hole, d_followed]
steps += [e_reorder_rename, e_survived, f_move_body, f_followed]
steps += [g_roll_back, g_rolled, g_roll_forward, g_forward, h_delete_hole, h_lost]
steps += [i_edit, i_says, i_click, i_ok, i_works, i_undo, i_undone, i_redo, i_redone]
steps += [i_save_close, i_open, i_reopened]

h.run("book_joints_survive", steps, paced_by="state")
