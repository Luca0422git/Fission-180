# SPDX-License-Identifier: LGPL-2.1-or-later
"""The book parity report, Hot End: "my attempt to place an M3x20 countersunk screw on the
chamfered rim did not pick the rim", and "no set screws or Phillips pan heads". Real input
on a 60 x 40 x 10 block (made by script) with four holes:

  H1 (12, 12)  6.6 through, a 90 degree countersink 13.44 wide (an M6 countersunk head's)
  H2 (36, 12)  3.4 through, its rim chamfered 0.8 (5.0 wide at the face)
  H3 (12, 30)  6.6 through, a counterbore 11 x 6.4
  H4 (36, 30)  4.5 through, plain

A  INSERT > Hardware... Type "m3x20 countersunk" into Search: the list offers "M3 x 20
   Countersunk Screw"; click it: Standard, Size and Length follow. Click the chamfered rim
   of H2 (the edge between the chamfer and the hole's wall, which was refused before): the
   screw goes on the hole's axis, no second hole is made, and its cone rests in the chamfer
   (0.86 proud: the head is wider than the chamfer). OK: a component named like the part, a
   rigid joint to the block, one undo step.
B  Undo removes the screw and its joint, Redo brings both back.
C  Hardware... (it remembers Countersunk). Click the countersink's FACE of H1 (a cone: it
   was "That face is curved" before): Size goes to M6 by itself (Fusion's Size Automatic,
   from the 6.6 hole), the head lies flush in the countersink. Length 16 mm. OK.
D  Hardware..., Socket head cap screw, click the WALL of H3's counterbore (a cylinder): M6,
   the head on the counterbore's floor. OK.
E  Hardware..., Type Set screw: cup, flat, cone and dog points are there; Pan head screws
   (Phillips and slotted) are in the Screw list. Click a straight edge of the block: the
   dialog says why nothing happens; Esc: nothing changed.
F  Hardware..., Heat-set insert, click the rim of H4 (4.5 wide: no insert's hole): the part
   is put in and the dialog says that no size fits and that the size stayed. Cancel.
"""

import FreeCAD as App
from PySide6 import QtCore

from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import book_hardware_steps as bh
from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h

V = App.Vector
S = {}
H1, H2, H3, H4 = (12.0, 12.0), (36.0, 12.0), (12.0, 30.0), (36.0, 30.0)
M3_SCREW = "M3 x 20 Countersunk Screw"
M6_SCREW = "M6 x 16 Countersunk Screw"
M6_CAP = "M6 x 16 Socket Head Cap Screw"


def setup():
    bh.new_design("BookHardwareCountersunk")
    body = bh.block("Block", (60, 40, 10))
    bh.drill(body, "D1", H1[0], H1[1], 6.6, 0, 10)
    bh.countersink(body, "C1", H1[0], H1[1], 6.6, 13.44, 10)
    bh.drill(body, "D2", H2[0], H2[1], 3.4, 0, 10)
    bh.countersink(body, "C2", H2[0], H2[1], 3.4, 5.0, 10)
    bh.drill(body, "D3", H3[0], H3[1], 6.6, 0, 10)
    bh.drill(body, "B3", H3[0], H3[1], 11.0, 3.6, 10)
    bh.drill(body, "D4", H4[0], H4[1], 4.5, 0, 10)
    bh.done()
    S["block"] = body
    S["volume"] = body.Shape.Volume
    S["count"] = len(bh.doc().Objects)


def block_same(where):
    v = S["block"].Shape.Volume
    h.check("the block is not cut (%s)" % where, abs(v - S["volume"]) < 1e-6, (v, S["volume"]))


# -- A --------------------------------------------------------------------------------------------
def a_open():
    bh.open_hardware()


a_open.done = bh.is_open
a_open.done_what = "the Hardware dialog is open"


def a_search():
    p = bh.panel()
    h.check(
        "the dialog starts in Metric", p.system.currentText() == "Metric", p.system.currentText()
    )
    h.check("nothing placed yet, and it says where OK would put it", p.hint.isVisible())
    bh.search("m3x20 countersunk")


def a_found():
    found = bh.results()
    h.check("Search offers the screw", found[:1] == [M3_SCREW], found)
    h.check("the list is shown", bh.panel().results.isVisible())
    bh.click_result(0)


def a_chosen():
    want = ("Metric", "Screw", "Countersunk screw (ISO 10642)", "M3", "20 mm")
    h.check("the result set Standard, Size and Length", bh.shown() == want, bh.shown())
    h.check("the name", bh.panel().name.text() == M3_SCREW, bh.panel().name.text())
    h.check("nothing made yet", not bh.parts())
    h.fit()
    # the edge between the chamfer and the wall of H2, on the far side of the hole
    h.click_edge(bh.far_wall(H2[0], H2[1], 1.7, 9.2))


def a_placed():
    p = bh.panel()
    h.check("the chamfered rim was taken", p.target is not None, (p.last_click, p.message.text()))
    if p.target is None:
        return
    h.check("the click was on an edge", p.last_click[1].startswith("Edge"), p.last_click)
    h.check("Place on says a hole", p.place.button.text().startswith("Hole"), p.place.button.text())
    h.check("no second hole", not p.make_hole.isChecked())
    h.check("the size stays M3 (a 3.4 hole)", p.size.currentText() == "M3", p.size.currentText())
    h.check("no problem shown", p.message.text() == "", p.message.text())
    block_same("a screw in a hole that is there")
    comp = bh.hw().component_of(p.target)
    h.check("on the hole's axis", bh.near(bh.axis_of(comp), (H2[0], H2[1], 10.0)), bh.axis_of(comp))
    box = bh.box(p.target)
    # the M3 head (6.72) is wider than the chamfer (5.0): it stands (6.72 - 5.0) / 2 proud
    h.check("its cone rests in the chamfer", bh.near(box[2::3], [10.86 - 20, 10.86]), box)
    h.shot("A-chamfered-rim")
    h.task_button("OK")


def a_kept():
    bh.no_dialog("OK")
    h.check("a component named like the part", M3_SCREW in bh.labels(), bh.labels())
    part = bh.part_named(M3_SCREW)
    comp = bh.hw().component_of(part)
    h.check("its standard is its description", comp.Label2 == "ISO 10642", comp.Label2)
    made = bh.joints_of(part)
    h.check("a rigid joint holds it to the block", len(made) == 1, made)
    h.check(
        "the screw has a mass (steel)",
        0.5e-3 < (bh.hw().mass(part) or 0) < 2e-3,
        bh.hw().mass(part),
    )
    titles = ui.timeline_titles()
    h.check("Hardware step in the timeline", any(t.startswith("Hardware") for t in titles), titles)
    S["after_a"] = len(bh.doc().Objects)
    s.undo()


# -- B --------------------------------------------------------------------------------------------
def b_undone():
    h.check("Undo: no screw", not bh.parts() and M3_SCREW not in bh.labels(), bh.labels())
    h.check("Undo: nothing left over", len(bh.doc().Objects) == S["count"], len(bh.doc().Objects))
    s.redo()


def b_redone():
    part = bh.part_named(M3_SCREW)
    h.check("Redo: the screw", part is not None, bh.labels())
    h.check("Redo: its joint", part is not None and len(bh.joints_of(part)) == 1)
    h.check("Redo: everything", len(bh.doc().Objects) == S["after_a"], len(bh.doc().Objects))
    bh.open_hardware()


b_redone.done = bh.is_open
b_redone.done_what = "the Hardware dialog is open"


# -- C --------------------------------------------------------------------------------------------
def c_click_cone():
    p = bh.panel()
    h.check(
        "it remembers Countersunk, M3",
        bh.shown()[2:4] == ("Countersunk screw (ISO 10642)", "M3"),
        bh.shown(),
    )
    h.fit()
    # the countersink's own face (a cone), half way down, on the far side
    h.click(bh.far_wall(H1[0], H1[1], 5.0, 8.3))
    S["cone_panel"] = p


def c_on_cone():
    p = bh.panel()
    h.check(
        "the countersink's face was taken", p.target is not None, (p.last_click, p.message.text())
    )
    if p.target is None:
        return
    name = p.last_click[1]
    face = S["block"].Shape.getElement(name) if name.startswith("Face") else None
    h.check(
        "the click was on the cone",
        face is not None and face.Surface.TypeId == "Part::GeomCone",
        p.last_click,
    )
    h.check(
        "Size Automatic: M6 from the 6.6 hole", p.size.currentText() == "M6", p.size.currentText()
    )
    h.check("no second hole", not p.make_hole.isChecked())
    h.check("Head sunk in", p.sink.isChecked())
    h.check("Length 16 mm", ui.choose(p.length, "16 mm"))


def c_seated():
    p = bh.panel()
    box = bh.box(p.target)
    h.check("the head lies flush in the countersink", bh.near(box[2::3], [-6.0, 10.0]), box)
    h.check("as wide as the countersink", bh.near([box[3] - box[0]], [13.44]), box)
    block_same("C")
    h.shot("C-countersink-face")
    h.task_button("OK")


def c_kept():
    bh.no_dialog("OK")
    h.check("M6 countersunk kept", M6_SCREW in bh.labels(), bh.labels())
    bh.open_hardware()


c_kept.done = bh.is_open
c_kept.done_what = "the Hardware dialog is open"


# -- D --------------------------------------------------------------------------------------------
def d_socket():
    p = bh.panel()
    h.check("Socket head", ui.choose(p.standard, "Socket head cap screw (ISO 4762)"))


def d_click_wall():
    h.fit()
    h.click(bh.far_wall(H3[0], H3[1], 5.5, 7.5))  # the counterbore's wall


def d_on_floor():
    p = bh.panel()
    h.check(
        "the counterbore's wall was taken", p.target is not None, (p.last_click, p.message.text())
    )
    if p.target is None:
        return
    name = p.last_click[1]
    face = S["block"].Shape.getElement(name) if name.startswith("Face") else None
    h.check(
        "the click was on the cylinder",
        face is not None and face.Surface.TypeId == "Part::GeomCylinder",
        p.last_click,
    )
    h.check(
        "M6 from the hole under the counterbore", p.size.currentText() == "M6", p.size.currentText()
    )
    h.check("Head sunk in (it fits the counterbore)", p.sink.isChecked())
    box = bh.box(p.target)
    # the floor is at 3.6, the head 6 high, the screw 16 long
    h.check("the head stands on the counterbore's floor", bh.near(box[2::3], [3.6 - 16, 9.6]), box)
    block_same("D")
    h.shot("D-counterbore-wall")
    h.task_button("OK")


def d_kept():
    bh.no_dialog("OK")
    h.check("M6 cap screw kept", M6_CAP in bh.labels(), bh.labels())
    h.check("three parts", len(bh.parts()) == 3, len(bh.parts()))
    S["after_d"] = len(bh.doc().Objects)
    bh.open_hardware()


d_kept.done = bh.is_open
d_kept.done_what = "the Hardware dialog is open"


# -- E --------------------------------------------------------------------------------------------
def e_lists():
    p = bh.panel()
    screws = [p.standard.itemText(i) for i in range(p.standard.count())]
    h.check(
        "Phillips and slotted pan heads are in the list",
        "Pan head screw, Phillips (ISO 7045)" in screws
        and "Pan head screw, slotted (ISO 1580)" in screws,
        screws,
    )
    h.check("Set screw", ui.choose(p.kind, "Set screw"))


def e_set_screws():
    p = bh.panel()
    points = [p.standard.itemText(i).split(" ")[0] for i in range(p.standard.count())]
    h.check("cup, flat, cone and dog points", points == ["Cup", "Flat", "Cone", "Dog"], points)
    h.check("a set screw has a length", p.length.isVisible() and p.length.count() > 3)
    h.check("and no Head sunk in", not p.sink.isVisible())
    h.click_edge(V(30, 0, 10))  # a straight edge of the block's top


def e_refused():
    p = bh.panel()
    h.check("nothing is made on a straight edge", p.target is None)
    h.check("and the dialog says why", "not round" in p.message.text(), p.message.text())
    h.press(QtCore.Qt.Key_Escape)


e_refused.done = lambda: not bh.is_open()
e_refused.done_what = "Esc closed the Hardware dialog"


def e_escaped():
    h.check("Esc changed nothing", len(bh.doc().Objects) == S["after_d"], len(bh.doc().Objects))
    bh.open_hardware()


e_escaped.done = bh.is_open
e_escaped.done_what = "the Hardware dialog is open"


# -- F --------------------------------------------------------------------------------------------
def f_insert():
    p = bh.panel()
    h.check("Heat-set insert", ui.choose(p.kind, "Heat-set insert"))


def f_click_rim():
    h.check(
        "the rim of H4",
        h.click_edge(bh.near_rim(H4[0], H4[1], 2.25, 10)),
        h.state.get("last_click"),
    )


def f_no_size():
    p = bh.panel()
    h.check("the insert is put in", p.target is not None, p.message.text())
    text = p.message.text()
    h.check("the dialog says no size fits a 4.5 mm hole", "No" in text and "4.5" in text, text)
    h.check("and that the size stayed", p.size.currentText() in text, (p.size.currentText(), text))
    h.task_button("Cancel")


f_no_size.done = lambda: not bh.is_open()
f_no_size.done_what = "Cancel closed the Hardware dialog"


def f_cancelled():
    h.check("Cancel changed nothing", len(bh.doc().Objects) == S["after_d"], len(bh.doc().Objects))
    block_same("the end")
    h.fit()
    h.shot("F-end")


h.run(
    "book_hardware_countersunk",
    [
        setup,
        a_open,
        a_search,
        a_found,
        a_chosen,
        a_placed,
        a_kept,
        b_undone,
        b_redone,
        c_click_cone,
        c_on_cone,
        c_seated,
        c_kept,
        d_socket,
        d_click_wall,
        d_on_floor,
        d_kept,
        e_lists,
        e_set_screws,
        e_refused,
        e_escaped,
        f_insert,
        f_click_rim,
        f_no_size,
        f_cancelled,
    ],
    paced_by="state",
)
