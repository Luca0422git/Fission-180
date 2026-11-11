# SPDX-License-Identifier: LGPL-2.1-or-later
"""The book parity report's joint bugs 11, 12 and 13 (Pizza Cutter, Fire Piston), with real
input (docs/fission180/parity/joints.md, "Joints follow the history marker").

The Pizza Cutter's order: two components and an as-built Rigid joint between them first,
then more components and a joint between those. Editing the first joint rolls the history
marker to it (Fusion), so the later components are not there while its dialog is open.

  A  ASSEMBLE > As-built Joint, End Cap + Handle, OK: "Rigid 1", no undo step left open.
     Handle grounded (browser).
  B  Later: Bracket and Bolt (two more components), J bolt onto bracket: "Rigid 2".
  C  Bug 11. Right-click Rigid 1 > Edit Joint: the dialog opens on it; the later joint is
     rolled back with the marker (greyed in the timeline), says nothing and fights nothing.
     Type Cylindrical: the Position box waits; click the End Cap's top; OK: the dialog closes,
     "Cylindrical 1", no undo step left open, the later joint is back and satisfied.
  D  Bug 12. Right-click > Edit Joint Limits: the as-built dialog on the same joint showing
     Cylindrical with its limit rows; Slide Maximum 5, OK. Again: Angle Minimum -30, Cancel:
     only that goes; Maximum 5 stays.
  E  Three other commands and a save: Rigid Group (opened, cancelled), Capture Position
     refused (nothing moved), Ctrl+S with its version prompt: the joint is still
     Cylindrical with Maximum 5 and the file holds it.
  F  Ctrl+Z twice: the limits go, then the type is Rigid again; Ctrl+Y twice brings both back.
  G  Bug 13. As-built Joint, Bolt + Handle, Type Slider, nothing picked for its axis: no
     joint stands in the browser meanwhile, OK is refused and says what to pick (in the
     dialog and next to the mouse). Another command started: the dialog is cancelled and
     says so; nothing was made. Then with the position picked: "Slider 1".
  H  The design closed while a joint dialog is open: no dialog and no undo step are left.
  I  Reopened: the joints are as saved and the solver is happy.
"""

import os
import tempfile

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import book_joints_steps as bj
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import joints_steps as j
from Fission180Tests.gui import timeline_input as t
from Fission180Tests.gui import versions_input as vi

V = App.Vector
S = {}
CAP_TOP = V(58, 6, 20)  # near the End Cap's top centre (60, 5, 20)
HANDLE_TOP = V(5, 5, 10)
BRACKET_TOP = V(5, 45, 10)
BOLT_TOP = V(34, 44, 8)


def jm():
    return bj.jm()


def kinds():
    return [(x.Label, x.JointType) for x in jm().joints(bj.doc())]


def setup():
    bj.new_design("BookJointsEdit")
    bj.box("Handle", (40, 30, 10))
    bj.box("End Cap", (20, 10, 20), V(50, 0, 0))
    h.fit()


# -- A ------------------------------------------------------------------------------------------
def a_command():
    j.menu("As-built Joint")


def a_cap():
    h.click(CAP_TOP)


def a_handle():
    h.click(HANDLE_TOP)


def a_ok():
    p = j.panel()
    h.check(
        "End Cap and Handle taken",
        p is not None and [x.Label for x in p.parts] == ["End Cap", "Handle"],
        p and p.parts,
    )
    j.ok()


def a_done():
    j.no_dialog("As-built Joint OK")
    h.check("Rigid 1 made", kinds() == [("Rigid 1", "Fixed")], kinds())
    bj.no_open_step("As-built Joint OK")


def a_ground():
    j.browser_menu("Handle", "Ground")


def a_grounded():
    h.check("Handle grounded", jm().is_grounded(bj.part("Handle")))
    bj.no_open_step("Ground")


# -- B ------------------------------------------------------------------------------------------
def b_more_parts():
    d = bj.doc()
    d.openTransaction("More components")
    bj.box("Bracket", (10, 10, 10), V(0, 40, 0))
    bj.box("Bolt", (8, 8, 8), V(30, 40, 0))
    d.commitTransaction()
    h.fit()


def b_press_j():
    j.press_j()


def b_bolt():
    h.click(BOLT_TOP)


def b_bracket():
    h.click(BRACKET_TOP)


def b_ok():
    j.ok()


def b_done():
    j.no_dialog("Joint OK")
    h.check("Rigid 2 made", [k[0] for k in kinds()] == ["Rigid 1", "Rigid 2"], kinds())
    bj.no_open_step("Joint OK")
    S["bolt"] = bj.place(bj.part("Bolt"))
    S["cap"] = bj.place(bj.part("End Cap"))
    order = t.titles()
    h.check(
        "the timeline: Rigid 1 before the later components and Rigid 2",
        order.index("Rigid 1") < order.index("Bracket") < order.index("Rigid 2"),
        order,
    )


# -- C: bug 11 ------------------------------------------------------------------------------------
def c_edit():
    j.browser_menu("Rigid 1", "Edit Joint")


def c_open():
    p = j.panel()
    h.check(
        "the as-built dialog opened on Rigid 1",
        p is not None
        and p.title == "As-Built Joint"
        and p.editing
        and p.joint is bj.joint("Rigid 1"),
        p and p.title,
    )
    states = t.states()
    h.check(
        "the later joint is rolled back with the marker",
        states.get("Rigid 2", ("",))[0] == "rolled_back",
        states.get("Rigid 2"),
    )
    h.check(
        "Rigid 1 itself is not", states.get("Rigid 1", ("",))[0] == "done", states.get("Rigid 1")
    )
    h.check(
        "a rolled-back joint does nothing",
        jm().rolled_back(bj.joint("Rigid 2"))
        and bj.joint("Rigid 2") not in jm().active_links(bj.doc()),
    )
    h.check("nothing fights", p is not None and "cannot" not in p.message.text(), p.message.text())
    j.choose_type(p, "Cylindrical")


def c_waits():
    p = j.panel()
    h.check("the Position box waits", p.active == "position", p.active)
    h.check("the joint is not changed yet", kinds()[0] == ("Rigid 1", "Fixed"), kinds())
    h.click(CAP_TOP)


def c_picked():
    p = j.panel()
    h.check(
        "the position is the End Cap's top centre",
        p.position_snap is not None and (p.position_snap["point"] - V(60, 5, 20)).Length < 1e-6,
        p.position_snap,
    )
    h.check("no problem shown", p.message.text() == "", p.message.text())
    j.ok()


def c_done():
    j.no_dialog("Edit Joint OK")
    h.check(
        "the joint is Cylindrical now",
        kinds()[0] == ("Cylindrical 1", "Cylindrical"),
        kinds(),
    )
    bj.no_open_step("Edit Joint OK")
    h.check(
        "one undo step: Edit As-Built Joint",
        bj.undo_names(1) == ["Edit As-Built Joint"],
        bj.undo_names(),
    )
    states = t.states()
    h.check(
        "the later joint is back", states.get("Rigid 2", ("",))[0] == "done", states.get("Rigid 2")
    )
    h.check("nothing is broken", not jm().broken_joints(bj.doc()), jm().broken_joints(bj.doc()))
    h.check("no joint lost its reference", not jm().lost_joints(bj.doc()))
    h.check("the bolt stayed on its bracket", not bj.moved(bj.place(bj.part("Bolt")), S["bolt"]))
    h.check("the End Cap stayed", not bj.moved(bj.place(bj.part("End Cap")), S["cap"]))


# -- D: bug 12 ------------------------------------------------------------------------------------
def d_limits():
    j.browser_menu("Cylindrical 1", "Edit Joint Limits")


def d_open():
    p = j.panel()
    h.check(
        "the joint's own dialog, on the same joint",
        p is not None and p.editing and p.joint is bj.joint("Cylindrical 1"),
        p and p.title,
    )
    if p is None:
        return
    h.check(
        "it shows Cylindrical", p.type_box.currentText() == "Cylindrical", p.type_box.currentText()
    )
    h.check(
        "with both kinds of limits",
        p.angle_limits.caption.isVisible() and p.slide_limits.caption.isVisible(),
    )
    s.toggle(p.slide_limits.rows["max"][0])
    s.type_value(p.slide_limits.rows["max"][1].widget, "5")


def d_ok():
    j.ok()


def d_done():
    j.no_dialog("Edit Joint Limits OK")
    lim = jm().limits(bj.joint("Cylindrical 1"))
    h.check("Slide Maximum 5 stored", lim["slide"]["max"] == 5 and lim["slide"]["min"] is None, lim)
    h.check("still Cylindrical", kinds()[0] == ("Cylindrical 1", "Cylindrical"), kinds())
    bj.no_open_step("Edit Joint Limits OK")


def d_again():
    j.browser_menu("Cylindrical 1", "Edit Joint Limits")


def d_change():
    p = j.panel()
    h.check(
        "Maximum 5 is shown",
        p is not None
        and p.slide_limits.rows["max"][0].isChecked()
        and abs(p.slide_limits.rows["max"][1].value() - 5) < 1e-9,
    )
    s.toggle(p.angle_limits.rows["min"][0])
    s.type_value(p.angle_limits.rows["min"][1].widget, "-30")


def d_changed():
    lim = jm().limits(bj.joint("Cylindrical 1"))
    h.check("Angle Minimum -30 previewed", lim["angle"]["min"] == -30, lim)
    j.cancel()


def d_cancelled():
    j.no_dialog("Edit Joint Limits Cancel")
    lim = jm().limits(bj.joint("Cylindrical 1"))
    h.check(
        "Cancel took only that back", lim["angle"]["min"] is None and lim["slide"]["max"] == 5, lim
    )
    h.check("still Cylindrical", kinds()[0] == ("Cylindrical 1", "Cylindrical"), kinds())
    bj.no_open_step("Edit Joint Limits Cancel")


# -- E: three other commands and a save ----------------------------------------------------------
def e_save_first():
    S["path"] = os.path.join(tempfile.mkdtemp(), "book_joints_edit.FCStd")
    bj.doc().saveAs(S["path"])


def e_rigid_group():
    j.menu("Rigid Group")


def e_rigid_group_cancel():
    p = j.panel()
    h.check("Rigid Group open", p is not None and p.title == "Rigid Group", p and p.title)
    j.cancel()


def e_capture():
    from fission180 import joints_ui

    joints_ui.CapturePositionCommand().Activated()  # the menu entry is greyed: nothing moved


def e_ctrl_s():
    h.check("Capture Position says nothing moved", "Nothing moved" in bj.told(), bj.told())
    bj.no_open_step("Rigid Group Cancel and Capture Position")
    S["mtime"] = os.path.getmtime(S["path"])
    h.press(QtCore.Qt.Key_S, QtCore.Qt.ControlModifier)


def e_describe():
    h.check("the Save dialog asks for a version description", vi.version_dialog() is not None)
    vi.accept_save()


def e_saved():
    h.check("saved", not Gui.ActiveDocument.Modified)
    h.check("the file was written", os.path.getmtime(S["path"]) >= S["mtime"])
    lim = jm().limits(bj.joint("Cylindrical 1"))
    h.check(
        "the edit is kept after three commands and a save",
        kinds()[0] == ("Cylindrical 1", "Cylindrical") and lim["slide"]["max"] == 5,
        (kinds(), lim),
    )
    bj.no_open_step("Ctrl+S")


# -- F: undo / redo -------------------------------------------------------------------------------
def f_undo():
    s.undo()


def f_undone_limits():
    lim = jm().limits(bj.joint("Cylindrical 1"))
    h.check("Ctrl+Z: the limit is gone", lim["slide"]["max"] is None, lim)
    h.check("still Cylindrical", kinds()[0] == ("Cylindrical 1", "Cylindrical"), kinds())


def f_undone_type():
    h.check("Ctrl+Z again: Rigid 1", kinds()[0] == ("Rigid 1", "Fixed"), kinds())
    h.check("nothing is broken", not jm().broken_joints(bj.doc()))


def f_redo():
    s.redo()


def f_redone():
    lim = jm().limits(bj.joint("Cylindrical 1")) if bj.joint("Cylindrical 1") else None
    h.check(
        "Ctrl+Y twice: Cylindrical with Maximum 5",
        kinds()[0] == ("Cylindrical 1", "Cylindrical") and lim and lim["slide"]["max"] == 5,
        (kinds(), lim),
    )
    bj.no_open_step("undo and redo")


# -- G: bug 13 ------------------------------------------------------------------------------------
def g_command():
    h.fit()
    j.menu("As-built Joint")


def g_bolt():
    h.click(bj.top_of(bj.part("Bolt")))  # it stands on the bracket now


def g_handle():
    h.click(HANDLE_TOP)


def g_slider():
    p = j.panel()
    h.check("Bolt and Handle taken", [x.Label for x in p.parts] == ["Bolt", "Handle"], p.parts)
    h.check("the preview shows a Rigid joint", "Rigid 2" in bj.labels() and len(bj.labels()) == 3)
    j.choose_type(p, "Slider")


def g_waiting():
    p = j.panel()
    h.check(
        "no joint stands in the design while the Slider waits for its axis",
        bj.labels() == ["Cylindrical 1", "Rigid 2"],
        bj.labels(),
    )
    h.check("the Position box waits", p.active == "position", p.active)
    j.ok()


def g_refused():
    p = j.panel()
    h.check("OK is refused: the dialog stays", p is not None and not p._closed)
    text = p.message.text() if p is not None else ""
    h.check("it says a Slider needs a position", "Slider needs a position" in text, text)
    h.check("and says it next to the mouse", "Slider needs a position" in bj.told(), bj.told())
    h.check("still no joint made", bj.labels() == ["Cylindrical 1", "Rigid 2"], bj.labels())


def g_other_command():
    j.menu("Rigid Group")


def g_cancelled():
    p = j.panel()
    h.check("the other command opened", p is not None and p.title == "Rigid Group", p and p.title)
    h.check(
        "the unfinished joint was cancelled, and said so",
        "As-Built Joint was cancelled" in bj.told(),
        bj.told(),
    )
    h.check("nothing was made", bj.labels() == ["Cylindrical 1", "Rigid 2"], bj.labels())
    j.cancel()


def g_again():
    bj.no_open_step("a cancelled As-built Joint")
    j.menu("As-built Joint")


def g_slider2():
    p = j.panel()
    j.choose_type(p, "Slider")


def g_position():
    h.click(bj.top_of(bj.part("Bolt")))


def g_ok():
    p = j.panel()
    h.check("position taken", p.position_snap is not None, p.info.text())
    j.ok()


def g_made():
    j.no_dialog("As-built Slider OK")
    made = bj.joint("Slider 1")
    h.check("Slider 1 made", made is not None and made.JointType == "Slider", kinds())
    bj.no_open_step("As-built Slider OK")


# -- H: the design closed under a dialog ---------------------------------------------------------
def h_save():
    bj.doc().save()


def h_open_dialog():
    j.browser_menu("Slider 1", "Edit Joint")


def h_close_design():
    p = j.panel()
    h.check("a joint dialog is open", p is not None and p.editing, p and p.title)
    App.closeDocument(bj.doc().Name)


def h_closed():
    h.check("the dialog went with its design", not Gui.Control.activeDialog())
    h.check(
        "no undo step left open", App.getActiveTransaction() is None, App.getActiveTransaction()
    )


# -- I: reopen -----------------------------------------------------------------------------------
def i_open():
    App.openDocument(S["path"])
    h.fit()


def i_reopened():
    h.check(
        "the joints are as saved",
        kinds() == [("Cylindrical 1", "Cylindrical"), ("Rigid 2", "Fixed"), ("Slider 1", "Slider")],
        kinds(),
    )
    lim = jm().limits(bj.joint("Cylindrical 1"))
    h.check("the limit is kept", lim["slide"]["max"] == 5, lim)
    h.check("the solver is happy", jm().solve(bj.doc()) == 0)
    h.check("nothing lost", not jm().lost_joints(bj.doc()))
    bj.no_open_step("reopening")


steps = [setup, a_command, a_cap, a_handle, a_ok, a_done, a_ground, a_grounded]
steps += [b_more_parts, b_press_j, b_bolt, b_bracket, b_ok, b_done]
steps += [c_edit, c_open, c_waits, c_picked, c_done]
steps += [d_limits, d_open, d_ok, d_done, d_again, d_change, d_changed, d_cancelled]
steps += [
    e_save_first,
    e_rigid_group,
    e_rigid_group_cancel,
    e_capture,
    e_ctrl_s,
    e_describe,
    e_saved,
]
steps += [f_undo, f_undone_limits, f_undo, f_undone_type, f_redo, f_redo, f_redone]
steps += [g_command, g_bolt, g_handle, g_slider, g_waiting, g_refused, g_other_command]
steps += [g_cancelled, g_again, g_bolt, g_handle, g_slider2, g_position, g_ok, g_made]
steps += [h_save, h_open_dialog, h_close_design, h_closed, i_open, i_reopened]

h.run("book_joints_edit", steps, paced_by="state")
