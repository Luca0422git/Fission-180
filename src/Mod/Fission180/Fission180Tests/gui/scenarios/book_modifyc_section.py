# SPDX-License-Identifier: LGPL-2.1-or-later
"""Section Analysis started with a construction plane selected, another plane picked in the
browser, and the command pressed again while its dialog is open (book parity report, line
1357: "Picking the plane in the browser while Plane 1 was selected first gave "Plane1"; the
second pick replaced it - fine, but two Section entries were created during the retry").

Reproduced before the fix: Section Analysis pressed again finished the open dialog (its
section is kept: Fusion also runs a command that another command ends) and the new dialog
took the first dialog's pick as its own selection, so a second section on the same plane
appeared at once, without a click.

A 40 x 30 x 20 block and an offset plane 5 mm above XY (the design-step builder); then real
input:

1. the plane's row clicked in the browser, INSPECT > Section Analysis: one section on that
   plane; the Origin folder opened, the XZ row clicked: the same section, now on XZ (one
   entry, one undo step so far).
2. Section Analysis pressed again: the first section is kept, the new dialog waits for a
   plane and has made nothing. Esc: still one section.
3. Section Analysis again, the XY row clicked, OK: two sections, as asked for. Ctrl+Z takes
   the second away, Ctrl+Z again the first.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import inspect_steps as s
from Fission180Tests.gui import timeline_input as t

V = App.Vector
S = {}
STEPS = [
    {"op": "sketch", "id": "s1", "plane": "XY", "geometry": [{"rect": [-20, -15, 40, 30]}]},
    {"op": "extrude", "id": "e1", "profile": "s1", "distance": 20},
    {
        "op": "construct",
        "id": "p1",
        "preset": "OffsetPlane",
        "refs": [{"plane": "XY"}],
        "values": {"distance": 5},
    },
]


def panel():
    from fission180 import section_ui, taskui

    p = taskui.current()
    return p if isinstance(p, section_ui.SectionPanel) else None


def analyses():
    from fission180 import section

    return [o.Label for o in section.sections(App.ActiveDocument)]


def normal(label):
    from fission180 import section

    for obj in section.sections(App.ActiveDocument):
        if obj.Label == label:
            return obj.CutPlacement.Rotation.multVec(V(0, 0, 1))
    return None


def undo_names():
    return list(App.ActiveDocument.UndoNames)


def setup():
    from Fission180Tests.golden.builder import Builder

    Gui.activateWorkbench("Fission180Workbench")
    doc = App.newDocument("Section")
    builder = Builder(doc)
    for step in STEPS:
        builder.run(step)
        doc.recompute()
    S["plane"] = builder.objects["p1"].Label
    doc.clearUndos()
    h.fit()


def select_plane():
    Gui.Selection.clearSelection()
    h.check("the offset plane's row", t.click_row(S["plane"]), t.labels())


def start():
    h.ribbon("Section Analysis")


start.done = lambda: panel() is not None
start.done_what = "the Section Analysis dialog is open"


def open_origin():
    p = panel()
    h.check("one section, on the selected plane", analyses() == ["Section1"], analyses())
    n = normal("Section1")
    h.check("it cuts along the offset plane", n is not None and abs(abs(n.z) - 1) < 1e-9, n)
    h.check("the box names the plane", S["plane"] in p.box.button.text(), p.box.button.text())
    s.expand_folder("Origin")


def pick_xz():
    h.check("the XZ row", t.click_row("XZ"), t.labels())


def again():
    p = panel()
    h.check("the second pick replaced the first", "XZ" in p.box.button.text(), p.box.button.text())
    h.check("still one section", analyses() == ["Section1"], analyses())
    n = normal("Section1")
    h.check("it cuts along XZ now", n is not None and abs(abs(n.y) - 1) < 1e-9, n)
    S["first"] = p
    h.ribbon("Section Analysis")


again.done = lambda: panel() is not None and panel() is not S.get("first")
again.done_what = "a new Section Analysis dialog is open"


def after_again():
    p = panel()
    h.check("the first section is kept", analyses() == ["Section1"], analyses())
    h.check("the new dialog has made nothing", p.analysis is None, p.analysis)
    h.check("its box waits for a plane", "XZ" not in p.box.button.text(), p.box.button.text())
    h.check("one undo step", undo_names() == ["Section Analysis"], undo_names())
    h.press(QtCore.Qt.Key_Escape)


after_again.done = lambda: panel() is None
after_again.done_what = "Esc closed the dialog"


def third():
    h.check("Esc leaves the one section", analyses() == ["Section1"], analyses())
    h.check("still one undo step", undo_names() == ["Section Analysis"], undo_names())
    h.ribbon("Section Analysis")


third.done = lambda: panel() is not None
third.done_what = "the Section Analysis dialog is open"


def pick_xy():
    h.check("nothing made before a plane is picked", analyses() == ["Section1"], analyses())
    h.check("the XY row", t.click_row("XY"), t.labels())


def ok():
    h.check("a second section, asked for", analyses() == ["Section1", "Section2"], analyses())
    h.task_button("OK")


def two():
    h.check("dialog closed", panel() is None)
    h.check("two sections", analyses() == ["Section1", "Section2"], analyses())
    n = normal("Section2")
    h.check("the second cuts along XY", n is not None and abs(abs(n.z) - 1) < 1e-9, n)
    h.check("two undo steps", undo_names() == ["Section Analysis"] * 2, undo_names())
    h.press(QtCore.Qt.Key_Z, QtCore.Qt.ControlModifier)


def undo_one():
    h.check("Ctrl+Z takes the second section away", analyses() == ["Section1"], analyses())
    h.press(QtCore.Qt.Key_Z, QtCore.Qt.ControlModifier)


def undo_two():
    h.check("Ctrl+Z again: none left", analyses() == [], analyses())
    h.shot("section-twice")


h.run(
    "book_modifyc_section",
    [
        setup,
        select_plane,
        start,
        open_origin,
        pick_xz,
        again,
        after_again,
        third,
        pick_xy,
        ok,
        two,
        undo_one,
        undo_two,
    ],
    paced_by="state",
)
