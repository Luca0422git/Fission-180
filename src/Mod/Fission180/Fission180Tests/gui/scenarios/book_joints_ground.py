# SPDX-License-Identifier: LGPL-2.1-or-later
"""Joints with a first component that is grounded to its parent, as every design has since
wave 7 ("First component Ground to Parent", on by default; the test harness switches it off,
this scenario switches it on before making its components), with real input
(docs/fission180/parity/joints.md, "A grounded first component").

Fusion (help, Joint): "when you create a joint with a component that is grounded to parent,
if it is the first component that you select, it is automatically ungrounded from parent.
The second component you select maintains its current ground to parent status."

Three components made with Create Components from Bodies: Frame (the first: grounded by
itself), Wheel and Pin.

  A  The Frame is grounded, the others are not. Dragged, it does not move and says why (and
     how to free it); so does Move's own check.
  B  J, the Frame first (the one that moves), then the Wheel: the Frame is ungrounded, it
     moves onto the Wheel, the dialog says so; the Wheel did not move. Cancel: the Frame is
     grounded again and back where it was.
  C  The same with OK: one undo step; Ctrl+Z grounds the Frame again and puts it back,
     Ctrl+Y redoes both.
  D  The Wheel grounded from the browser (Ground to Parent). J, the Pin first, then the
     Wheel: the Wheel keeps its ground and stays, the Pin moves onto it.
  E  As-built Joint between the grounded Wheel and the Frame: nothing is ungrounded, nothing
     moves.
"""

import FreeCAD as App

from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import book_joints_steps as bj
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import joints_steps as j

V = App.Vector
S = {}


def jm():
    return bj.jm()


def grounded(label):
    return jm().is_grounded(bj.part(label))


def setup():
    from fission180 import components_ui, prefs_core

    App.ParamGet(prefs_core.PREFS).SetBool("FirstComponentGrounded", True)
    bj.new_design("BookJointsGround")
    d = bj.doc()
    for name, size, at in (
        ("Frame", (40, 30, 10), None),
        ("Wheel", (20, 20, 8), V(60, 0, 0)),
        ("Pin", (8, 8, 12), V(60, 40, 0)),
    ):
        body = bj.box(name, size, at, component=False)
        d.openTransaction("Create Components from Bodies")
        components_ui.create_from_bodies(d, [body], label=name)
        d.commitTransaction()
    d.recompute()
    h.fit()
    for name in ("Frame", "Wheel", "Pin"):
        S[name] = bj.place(bj.part(name))


# -- A ------------------------------------------------------------------------------------------
def a_grounded():
    h.check("the first component is grounded by itself", grounded("Frame"))
    h.check("the others are not", not grounded("Wheel") and not grounded("Pin"))
    h.view().viewTop()
    h.fit(iso=False)


def a_drag():
    h.drag(h.screen_point(V(20, 15, 10)), h.screen_point(V(30, 25, 10)), steps=10)
    h.settle("the drag to be refused")


def a_refused():
    from fission180 import component_move, joints_drag

    h.check("the grounded Frame did not move", not bj.moved(bj.place(bj.part("Frame")), S["Frame"]))
    said = bj.told()
    h.check(
        "the drag says why, and how to free it",
        "Frame is grounded to its parent" in said and "Unground From Parent" in said,
        said,
    )
    last = joints_drag.last() or {}
    h.check("it was held", last.get("kind") == "held", last)
    why = component_move.refusal(bj.part("Frame"))
    h.check("Move says why too", "grounded" in why and "cannot move" in why, why)
    bj.no_open_step("a refused drag")
    h.fit()


# -- B ------------------------------------------------------------------------------------------
def b_press_j():
    j.press_j()


def b_frame_first():
    h.click(V(20, 14, 10))


def b_wheel():
    h.click(V(69, 9, 8))


def b_joined():
    p = j.panel()
    h.check("a joint is previewed", p is not None and p.joint is not None, p and p.message.text())
    h.check("the Frame is ungrounded (it is the first component picked)", not grounded("Frame"))
    h.check("the Frame moved onto the Wheel", bj.moved(bj.place(bj.part("Frame")), S["Frame"]))
    h.check("the Wheel did not move", not bj.moved(bj.place(bj.part("Wheel")), S["Wheel"]))
    note = p.note.text() if p is not None else ""
    h.check(
        "the dialog says the Frame was ungrounded",
        "Frame was grounded" in note and "ungrounded" in note,
        note,
    )
    h.check("no problem shown", p is not None and p.message.text() == "", p and p.message.text())
    j.cancel()


def b_cancelled():
    j.no_dialog("Joint Cancel")
    h.check("Cancel: the Frame is grounded again", grounded("Frame"))
    h.check("and back where it was", not bj.moved(bj.place(bj.part("Frame")), S["Frame"]))
    h.check("no joint", not jm().joints(bj.doc()))
    bj.no_open_step("Joint Cancel")
    S["undos"] = bj.doc().UndoCount


# -- C ------------------------------------------------------------------------------------------
def c_ok():
    j.ok()


def c_done():
    j.no_dialog("Joint OK")
    h.check("one joint", len(jm().joints(bj.doc())) == 1)
    h.check("the Frame is ungrounded", not grounded("Frame"))
    h.check("the Frame sits on the Wheel", bj.moved(bj.place(bj.part("Frame")), S["Frame"]))
    h.check("the Wheel did not move", not bj.moved(bj.place(bj.part("Wheel")), S["Wheel"]))
    h.check("one undo step", bj.doc().UndoCount == S["undos"] + 1, (S["undos"], bj.doc().UndoCount))
    h.check("the solver is happy", jm().solve(bj.doc()) == 0)
    bj.no_open_step("Joint OK")
    S["frame_on"] = bj.place(bj.part("Frame"))


def c_undo():
    s.undo()


def c_undone():
    h.check("Ctrl+Z: no joint", not jm().joints(bj.doc()))
    h.check("the Frame is grounded again", grounded("Frame"))
    h.check("and back where it was", not bj.moved(bj.place(bj.part("Frame")), S["Frame"]))


def c_redo():
    s.redo()


def c_redone():
    h.check("Ctrl+Y: the joint is back", len(jm().joints(bj.doc())) == 1)
    h.check(
        "the Frame is ungrounded and on the Wheel",
        not grounded("Frame") and not bj.moved(bj.place(bj.part("Frame")), S["frame_on"]),
    )
    bj.no_open_step("undo and redo")


# -- D ------------------------------------------------------------------------------------------
def d_ground_wheel():
    j.browser_menu("Wheel", "Ground to Parent")


def d_press_j():
    h.check("the Wheel is grounded", grounded("Wheel"))
    bj.no_open_step("Ground to Parent")
    S["wheel"] = bj.place(bj.part("Wheel"))
    j.press_j()


def d_pin_first():
    h.click(V(63, 43, 12))


def d_wheel_side():
    # the Wheel's top is under the Frame now: its front face (seen in the isometric view)
    box = jm().part_shape(bj.part("Wheel")).BoundBox
    h.click(V(0.5 * (box.XMin + box.XMax) + 3, box.YMin, 0.5 * (box.ZMin + box.ZMax) - 1))


def d_joined():
    p = j.panel()
    h.check(
        "a second joint is previewed", p is not None and p.joint is not None, p and p.info.text()
    )
    h.check("the second component keeps its ground", grounded("Wheel"))
    h.check("the Wheel did not move", not bj.moved(bj.place(bj.part("Wheel")), S["wheel"]))
    h.check("the Pin moved onto it", bj.moved(bj.place(bj.part("Pin")), S["Pin"]))
    h.check("nothing is said about ungrounding", "ungrounded" not in p.note.text(), p.note.text())
    j.ok()


def d_done():
    j.no_dialog("Joint OK")
    h.check("two joints", len(jm().joints(bj.doc())) == 2)
    h.check("the Wheel is still grounded", grounded("Wheel"))
    h.check("the solver is happy", jm().solve(bj.doc()) == 0)
    bj.no_open_step("Joint OK")


# -- E ------------------------------------------------------------------------------------------
def e_undo_first():
    s.undo()  # the Pin's joint
    s.undo()  # the Wheel's ground


def e_as_built():
    s.undo()  # the Frame's joint: the Frame is grounded and back
    h.check("the Frame is grounded again", grounded("Frame") and not jm().joints(bj.doc()))
    h.fit()
    j.menu("As-built Joint")


def e_frame():
    h.click(V(20, 14, 10))


def e_wheel():
    h.click(V(69, 9, 8))


def e_ok():
    p = j.panel()
    h.check("Frame and Wheel taken", [x.Label for x in p.parts] == ["Frame", "Wheel"], p.parts)
    j.ok()


def e_done():
    j.no_dialog("As-built Joint OK")
    h.check("an as-built joint", len(jm().joints(bj.doc())) == 1)
    h.check("the Frame keeps its ground (nothing has to move)", grounded("Frame"))
    h.check(
        "nothing moved",
        not bj.moved(bj.place(bj.part("Frame")), S["Frame"])
        and not bj.moved(bj.place(bj.part("Wheel")), S["Wheel"]),
    )
    bj.no_open_step("As-built Joint OK")


steps = [setup, a_grounded, a_drag, a_refused, b_press_j, b_frame_first, b_wheel, b_joined]
steps += [b_cancelled, b_press_j, b_frame_first, b_wheel, c_ok, c_done, c_undo, c_undone]
steps += [c_redo, c_redone, d_ground_wheel, d_press_j, d_pin_first, d_wheel_side, d_joined, d_done]
steps += [e_undo_first, e_as_built, e_frame, e_wheel, e_ok, e_done]

h.run("book_joints_ground", steps, paced_by="state")
