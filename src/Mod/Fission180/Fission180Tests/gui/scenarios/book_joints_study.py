# SPDX-License-Identifier: LGPL-2.1-or-later
"""Motion Study's graph and Enter, and the browser rows of components inside a subassembly
(the book parity report: Strandbeest, "no line graph", "Enter in the Step / Angle box closes
the dialog"; bug 15, Tesla Turbine, "clicking a nested component's row does not pick it"),
with real input (docs/fission180/parity/joints.md).

A Base (grounded) with an Arm on an as-built Revolute joint (made by script), and a
subassembly Sub holding two components, Inner A and Inner B.

  A  ASSEMBLE > Motion Study, the joint's browser row: the graph shows its line. Step 50,
     the angle 90 typed, Enter in the value box: the dialog stays open, the point is set
     and the model stands at 90. A click on the joint's line at step 100: Step is 100 and
     the value box takes the typing; 180, Enter: a third point. Play: the Arm goes to 180.
     OK: "Motion Study 1"; the Arm stands where it was; no undo step left open.
  B  Edit Motion Study: the graph shows the three points. Enter in the Step box sets a
     point too (it does not press OK). Cancel leaves the study as it was.
  C  As-built Joint: the browser rows of Inner A (inside Sub) and of Base: Inner A itself is
     taken, not its parent. OK: the joint is on Inner A. Rigid Group with the rows of Inner
     B and Base. Ctrl+Z twice.
"""

import FreeCAD as App
from PySide import QtCore
from PySide6 import QtTest

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import book_joints_steps as bj
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import joints_steps as j
from Fission180Tests.gui import timeline_input as t
from Fission180Tests.gui import widget_input as w

V = App.Vector
S = {}


def jm():
    return bj.jm()


def joint():
    return bj.joint("Revolute 1")


def angle():
    return jm().value(joint())[0]


def keys(p):
    return [list(k) for k in p.data["keys"].get(joint().Name, [])]


def enter(widget):
    QtTest.QTest.keyClick(widget, QtCore.Qt.Key_Return)
    h.settle("the Enter key to be handled")


def setup():
    from fission180 import components, joints_ui

    bj.new_design("BookJointsStudy")
    d = bj.doc()
    base = bj.box("Base", (60, 40, 5))
    arm = bj.box("Arm", (30, 6, 4), V(10, 17, 5))
    sub = components.new_component(d, "Sub")
    for name, at in (("Inner A", V(80, 0, 0)), ("Inner B", V(80, 25, 0))):
        body = d.addObject("PartDesign::Body", name.replace(" ", "") + "Body")
        feature = d.addObject("PartDesign::AdditiveBox", name.replace(" ", "") + "Box")
        body.addObject(feature)
        feature.Length, feature.Width, feature.Height = 10, 10, 10
        feature.Placement.Base = at
        d.recompute()
        inner = components.new_component(d, name, parent=sub)
        inner.addObject(body)
    jm().ground(base)
    body = [o for o in arm.Group if o.TypeId == "PartDesign::Body"][0]
    best = None
    for i, face in enumerate(body.Shape.Faces):
        if abs(face.CenterOfMass.z - 9) > 1e-6:
            continue
        pick = jm().Pick(arm, body, "Face%d" % (i + 1))
        for snap in jm().snap_candidates(pick):
            gap = (snap["point"] - V(10, 20, 9)).Length
            if best is None or gap < best[0]:
                best = (gap, pick, snap)
    jm().create_as_built_joint(d, "revolute", arm, base, best[1], best[2])
    d.recompute()
    joints_ui.attach_views(d)
    jm().save_baseline(d)
    h.fit()
    S["arm"] = bj.place(bj.part("Arm"))


# -- A ------------------------------------------------------------------------------------------
def a_command():
    j.menu("Motion Study")


def a_pick():
    t.click_row("Revolute 1")


def a_step_50():
    p = j.panel()
    h.check("Motion Study open on the joint", p is not None and p.data["joints"] == [joint().Name])
    h.check("the graph shows the joint's line", [x[0] for x in p.graph.lanes] == [joint().Name])
    h.check("one point: where it stands now", keys(p) == [[0.0, 0.0]], keys(p))
    b.type_into(p.step, "50")
    b.type_into(p.value_field.widget, "90")
    enter(p.value_field.widget)


def a_point_set():
    p = j.panel()
    h.check(
        "Enter did not close the dialog",
        p is not None and not p._closed and p.title == "Motion Study",
    )
    h.check("it set the point (50, 90)", keys(p) == [[0.0, 0.0], [50.0, 90.0]], keys(p))
    h.check("the list shows two points", p.table.rowCount() == 2, p.table.rowCount())
    h.check("the graph has both", len(p.graph.lanes[0][2]) == 2, p.graph.lanes)
    h.check("the model stands at step 50: 90", abs(angle() - 90) < 1e-6, angle())
    h.check("the playhead is at 50", p.slider.value() == 50 and p.graph.playhead == 50)
    h.shot("A-study-graph")
    w.click(p.graph, p.graph.point_of(joint().Name, 100))


def a_graph_clicked():
    p = j.panel()
    h.check("a click on the line at step 100 sets Step", p.step.value() == 100, p.step.value())
    h.check("the value box shows the line's value there", abs(p.value_field.value() - 90) < 1e-6)
    h.check(
        "and takes the typing",
        p.value_field.widget.hasFocus()
        or any(
            c.hasFocus()
            for c in p.value_field.widget.findChildren(QtCore.QObject)
            if hasattr(c, "hasFocus")
        ),
    )
    QtTest.QTest.keyClick(p.value_field.widget, QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
    QtTest.QTest.keyClicks(p.value_field.widget, "180")
    enter(p.value_field.widget)


def a_third_point():
    p = j.panel()
    h.check("still open", p is not None and not p._closed)
    h.check("three points", keys(p) == [[0.0, 0.0], [50.0, 90.0], [100.0, 180.0]], keys(p))
    h.check("the model stands at 180", abs(angle() - 180) < 1e-6, angle())
    w.click(p.play)


a_third_point.done = lambda: j.panel() is not None and not j.panel().playing
a_third_point.done_what = "the study to play to its end"
a_third_point.timeout_s = 60


def a_played():
    p = j.panel()
    h.check("the Play button is up again", p is not None and not p.play.isChecked())
    h.check("played to the end: 180", abs(angle() - 180) < 1e-4, angle())
    j.ok()


def a_done():
    j.no_dialog("Motion Study OK")
    studies = jm().motion_studies(bj.doc())
    h.check("Motion Study 1 kept", len(studies) == 1 and studies[0].Label == "Motion Study 1")
    data = jm().study_data(studies[0]) if studies else {}
    h.check(
        "with its three points",
        data.get("keys", {}).get(joint().Name) == [[0.0, 0.0], [50.0, 90.0], [100.0, 180.0]],
        data.get("keys"),
    )
    h.check("the Arm stands where it was", not bj.moved(bj.place(bj.part("Arm")), S["arm"]))
    bj.no_open_step("Motion Study OK")


# -- B ------------------------------------------------------------------------------------------
def b_edit():
    j.browser_menu("Motion Study 1", "Edit Motion Study")


def b_enter_in_step():
    p = j.panel()
    h.check("the study's dialog", p is not None and p.editing, p and p.title)
    h.check("the graph shows the three points", len(p.graph.lanes[0][2]) == 3, p.graph.lanes)
    b.type_into(p.value_field.widget, "45")
    b.type_into(p.step, "25")
    enter(p.step)


def b_cancel():
    p = j.panel()
    h.check("Enter in the Step box did not close the dialog", p is not None and not p._closed)
    h.check("it set the point (25, 45)", [25.0, 45.0] in keys(p), keys(p))
    j.cancel()


def b_cancelled():
    j.no_dialog("Edit Motion Study Cancel")
    data = jm().study_data(jm().motion_studies(bj.doc())[0])
    h.check("Cancel left the study as it was", len(data["keys"][joint().Name]) == 3, data["keys"])
    h.check("the Arm stands where it was", not bj.moved(bj.place(bj.part("Arm")), S["arm"]))
    bj.no_open_step("Edit Motion Study Cancel")


# -- C ------------------------------------------------------------------------------------------
def c_command():
    h.click_empty()
    j.menu("As-built Joint")


def c_inner_row():
    t.click_row("Inner A")


def c_base_row():
    p = j.panel()
    h.check(
        "the nested component's row takes that component, not its parent",
        p is not None and [x.Label for x in p.parts] == ["Inner A"],
        p and [x.Label for x in p.parts],
    )
    t.click_row("Base")


def c_ok():
    p = j.panel()
    h.check("Inner A and Base", [x.Label for x in p.parts] == ["Inner A", "Base"], p.parts)
    j.ok()


def c_made():
    j.no_dialog("As-built Joint OK")
    made = bj.joint("Rigid 1")
    h.check(
        "the joint is on Inner A",
        made is not None
        and jm().part1(made) is bj.part("Inner A")
        and jm().part2(made) is bj.part("Base"),
        made and (jm().part1(made).Label, jm().part2(made).Label),
    )
    bj.no_open_step("As-built Joint OK")
    h.click_empty()
    j.menu("Rigid Group")


def c_group_rows():
    t.click_row("Inner B")


def c_group_base():
    p = j.panel()
    h.check("Inner B taken by its row", [x.Label for x in p.members] == ["Inner B"], p.members)
    t.click_row("Base")


def c_group_ok():
    p = j.panel()
    h.check("Inner B and Base", [x.Label for x in p.members] == ["Inner B", "Base"], p.members)
    j.ok()


def c_group_made():
    j.no_dialog("Rigid Group OK")
    groups = jm().rigid_groups(bj.doc())
    h.check(
        "the rigid group holds Inner B and Base",
        len(groups) == 1 and [m.Label for m in groups[0].Members] == ["Inner B", "Base"],
        groups,
    )
    h.check("the solver is happy", jm().solve(bj.doc()) == 0)
    bj.no_open_step("Rigid Group OK")


def c_undo():
    s.undo()


def c_undone():
    h.check(
        "Ctrl+Z twice: the group and the joint are gone",
        not jm().rigid_groups(bj.doc()) and bj.joint("Rigid 1") is None,
    )
    h.check(
        "the study and its joint stay",
        len(jm().motion_studies(bj.doc())) == 1 and joint() is not None,
    )
    bj.no_open_step("undo")


steps = [setup, a_command, a_pick, a_step_50, a_point_set, a_graph_clicked, a_third_point]
steps += [a_played, a_done, b_edit, b_enter_in_step, b_cancel, b_cancelled]
steps += [c_command, c_inner_row, c_base_row, c_ok, c_made, c_group_rows, c_group_base]
steps += [c_group_ok, c_group_made, c_undo, c_undo, c_undone]

h.run("book_joints_study", steps, paced_by="state")
