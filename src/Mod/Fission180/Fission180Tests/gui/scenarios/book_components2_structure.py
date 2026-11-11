# SPDX-License-Identifier: LGPL-2.1-or-later
"""A copy of a subassembly keeps its structure; a mirrored component is a component of its
own in name; Cancel after a Paste takes the paste away (wave 7, components-2: what the
first components builder left open). Only real input for what is tested.

Fusion: the copies a Pattern of components makes are occurrences of the component, with
the components inside it (the Robotic Hand's fingers); Mirror makes "the other hand" of a
component, a new part ("always new part numbers"); Paste "pastes the new component in
place, then immediately invokes Move", and cancelling that Move cancels the Paste.
Before: a patterned, mirrored or pasted subassembly came in flat (bodies straight in the
copy, no rows for the parts inside), a mirrored component was called "Name:2" (and made
the original "Name:1"), and Esc after a paste left the copy standing on the original.

Setup (through the modules): the subassembly "Stator" holding "Housing" (a 40 x 30 x 10
block) and "Bolt" (a cylinder, radius 3, height 15, at x 10, y 10). The design is active.

  A  CREATE > Rectangular Pattern, Pattern Type Components, the Stator's browser row,
     direction X, Quantity 2, Distance 100, OK: "Stator:2" holds the rows "Housing" and
     "Bolt" (one body each, nothing straight in the copy), 100 mm along X.
  B  The original's Bolt moved 5 mm along Y (its Placement): the copy's Bolt follows.
  C  M (Move), Move Object Components, a click on the copy's bolt: refused, with the
     reason (it stands where the original's bolt stands). Cancel.
  D  CREATE > Mirror, the Stator's row, plane XZ, OK: "Stator (Mirror)" with the same rows,
     mirrored to y -30..0; the original is not counted as "Stator:1" because of it.
  E  The Stator's row, Ctrl+C, Ctrl+V: "Stator:3" with its rows, Move/Copy open on it; Esc:
     the paste is gone again, said next to the mouse. Ctrl+V, OK: it stays, on the original.
  F  Undo (the paste), Undo (the mirror), Redo twice.
  G  The pattern step deleted in the timeline: Stator:2 and its rows are gone. Undo.
  H  Save, close, reopen: the copies and their rows are there.
"""

import os
import tempfile

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import book_components_steps as k
from Fission180Tests.gui import component2_steps as c
from Fission180Tests.gui import direct_steps as d
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import pattern_steps as ps
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import timeline_input as t

V = App.Vector
state = {}


def new_design():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("BookComponents2Structure")
    stator = k.new_component("Stator")
    housing = k.new_component("Housing", parent=stator)
    k.add_box(housing, (0, 0, 40, 30), 10)
    bolt = k.new_component("Bolt", parent=stator)
    k.add_cylinder(bolt, (10, 10), 3, 15)
    state["bolt"] = bolt.Name
    k.settle_design()


def steps(kind):
    from fission180 import component_pattern, pattern

    return [
        o
        for o in k.doc().Objects
        if component_pattern.is_component_pattern(o) and pattern.kind_of(o) == kind
    ]


def copies(step):
    from fission180 import component_pattern

    return component_pattern.copies(step)


def rows(part):
    """{label: component} of the components directly inside a component."""
    from fission180 import components

    return {x.Label: x for x in part.Group if components.is_component(x)}


def has_structure(name, part):
    from fission180 import components

    found = rows(part)
    ok = h.check(
        "%s: its rows are Housing and Bolt, as in the original" % name,
        sorted(found) == ["Bolt", "Housing"],
        sorted(found),
    )
    h.check(
        "%s: one body in each" % name,
        all(len(components.bodies_in(k.doc(), x)) == 1 for x in found.values()),
        {label: len(components.bodies_in(k.doc(), x)) for label, x in found.items()},
    )
    h.check(
        "%s: no body straight in the copy" % name,
        not components.bodies_in(k.doc(), part),
        [x.Label for x in components.bodies_in(k.doc(), part)],
    )
    return ok


def closed():
    return ps.panel() is None


def ok():
    p = ps.panel()
    if p is not None:
        h.caught_up(p)
    h.task_button("OK")


ok.done = closed
ok.done_what = "the dialog closed"


def components_type():
    p = ps.panel()
    if h.check("the dialog is open", p is not None, p):
        if p.options["pattern_type"] != "components":
            b.choose(p.pattern_type, "Components")


def stator_row():
    t.click_row("Stator")


# -- A: a pattern of the subassembly ---------------------------------------------------------------
def a_open():
    Gui.Selection.clearSelection()
    h.click_empty()
    h.fit()
    ps.menu("Rectangular Pattern")


a_open.done = lambda: ps.panel() is not None
a_open.done_what = "the Rectangular Pattern dialog is open"


def a_direction_box():
    p = ps.panel()
    h.check(
        "the Stator is picked from its row",
        p is not None and p.options["objects"] == [(k.part("Stator"), "")],
        [(o.Label, s_) for o, s_ in (p.options["objects"] if p else [])],
    )
    ps.click_box("direction")


def a_click_x():
    h.fit()
    pl.click_on_plane(V(50, 0, 0))  # the X axis, beside the parts


def a_values():
    p = ps.panel()
    dirn = p.options["direction"] if p else None
    h.check("the X axis is direction 1", dirn is not None and dirn[0].Role == "X_Axis", dirn)
    ps.type_quantity(p.quantity, 2)
    ps.type_value(p.distance_field.widget, "100")


def a_done():
    found = steps("rectangular")
    if not h.check("one Rectangular Pattern step", len(found) == 1, found):
        return
    state["rect"] = found[0].Name
    made = copies(found[0])
    if not h.check("one copy: Stator:2", [x.Label for x in made] == ["Stator:2"], made):
        return
    state["copy"] = made[0].Name
    has_structure("Stator:2", made[0])
    k.box_is("Stator:2 stands 100 mm along X", made[0], [100, 0, 0, 140, 30, 15])
    k.box_is("its Bolt", rows(made[0]).get("Bolt"), [107, 7, 0, 113, 13, 15])
    k.box_is("its Housing", rows(made[0]).get("Housing"), [100, 0, 0, 140, 30, 10])
    k.box_is("the Stator itself stayed", k.part("Stator"), [0, 0, 0, 40, 30, 15])
    labels = t.tree().labels()
    h.check("the browser shows the copy's rows", labels.count("Bolt") >= 1, labels)
    k.no_empty_invalid_bodies()
    h.shot("A-pattern")


# -- B: the copy follows a part moved inside the original ---------------------------------------
def b_move_bolt():
    bolt = k.doc().getObject(state["bolt"])
    bolt.Placement = App.Placement(V(0, 5, 0), App.Rotation())
    k.doc().recompute()


def b_followed():
    copy = k.doc().getObject(state["copy"])
    k.box_is("the original's Bolt moved 5 mm along Y", k.part("Bolt"), [7, 12, 0, 13, 18, 15])
    k.box_is("the copy's Bolt followed", rows(copy).get("Bolt"), [107, 12, 0, 113, 18, 15])
    k.box_is("the copy's Housing stayed", rows(copy).get("Housing"), [100, 0, 0, 140, 30, 10])


# -- C: a part of the copy cannot be moved on its own ----------------------------------------------
def c_move():
    h.click_empty()
    h.fit()
    h.press("m")


c_move.done = lambda: c.panel() is not None
c_move.done_what = "the Move dialog is open"


def c_components():
    p = c.panel()
    if p is not None and getattr(p, "object_type", "") != "components":
        c.choose(p.move_object, "Components", closes=True)


c_components.done = lambda: c.component_panel() is not None
c_components.done_what = "Move Object reads Components"


def c_click_bolt():
    h.click(V(110, 15, 15))  # the copy's bolt, its top


def c_refused():
    p = c.component_panel()
    if not h.check("component Move open", p is not None, c.panel()):
        return
    text = p.message.text() + " " + p.info.text()
    h.check(
        "a part of the copy is refused, with the reason and what to do",
        "is part of the copy Stator:2" in text and "in the original" in text,
        text,
    )
    h.check("nothing is picked", not p.options.get("components"), p.options.get("components"))
    h.task_button("Cancel")


c_refused.done = lambda: c.panel() is None
c_refused.done_what = "the Move dialog closed"


# -- D: a mirror of the subassembly ----------------------------------------------------------------
def d_open():
    Gui.Selection.clearSelection()
    h.click_empty()
    h.fit()
    ps.menu("Mirror")


d_open.done = lambda: ps.panel() is not None
d_open.done_what = "the Mirror dialog is open"


def d_plane_box():
    p = ps.panel()
    h.check(
        "the Stator is picked from its row",
        p is not None and p.options["objects"] == [(k.part("Stator"), "")],
        [(o.Label, s_) for o, s_ in (p.options["objects"] if p else [])],
    )
    ps.click_box("plane")


def d_click_xz():
    h.fit()
    pl.click_square("XZ_Plane")


def d_done():
    from fission180 import instances

    found = steps("mirror")
    if not h.check("one Mirror step", len(found) == 1, found):
        return
    state["mirror"] = found[0].Name
    made = copies(found[0])
    if not h.check("one mirrored copy", len(made) == 1, [x.Label for x in made]):
        return
    state["mirrored"] = made[0].Name
    h.check("it is named Stator (Mirror)", made[0].Label == "Stator (Mirror)", made[0].Label)
    has_structure("Stator (Mirror)", made[0])
    box = k.box(made[0])
    h.check(
        "mirrored across XZ: y -30..0",
        box is not None and abs(box[1] + 30) < 1e-4 and abs(box[4]) < 1e-4,
        box,
    )
    k.box_is(
        "its Bolt (the original's stands at y 12..18)",
        rows(made[0]).get("Bolt"),
        [7, -18, 0, 13, -12, 15],
    )
    h.check(
        "it is no numbered occurrence of the Stator (only Stator:2 is)",
        [x.Label for x in instances.occurrences_of(k.part("Stator"))] == ["Stator:2"],
        [x.Label for x in instances.occurrences_of(k.part("Stator"))],
    )
    h.shot("D-mirror")


# -- E: paste, cancel, paste, OK ---------------------------------------------------------------
def e_select():
    h.click_empty()
    t.click_row("Stator")


def e_copy():
    t.ctrl("c")


def e_paste():
    t.ctrl("v")


e_paste.done = lambda: c.component_panel() is not None
e_paste.done_what = "Move/Copy opened on the paste"


def e_pasted():
    copy = k.part("Stator:3")
    if h.check("Stator:3 exists", copy is not None, k.labels()):
        has_structure("Stator:3", copy)
        k.box_is("it stands on the original (pasted in place)", copy, [0, 0, 0, 40, 30, 15])
    p = c.component_panel()
    h.check(
        "Move/Copy is open with the paste picked",
        p is not None and [x.Label for x in p.options.get("components", [])] == ["Stator:3"],
        p and [x.Label for x in p.options.get("components", [])],
    )
    h.press(QtCore.Qt.Key_Escape)


e_pasted.done = lambda: c.panel() is None
e_pasted.done_what = "Esc closed Move/Copy"


def e_cancelled():
    h.check("Esc takes the paste away again", k.part("Stator:3") is None, k.labels())
    h.check(
        "no row of the paste is left",
        sum(1 for x in k.labels() if x == "Bolt") == 3,
        k.labels(),
    )
    h.check("said next to the mouse", "Paste cancelled" in d.told(), d.told())
    t.ctrl("v")


e_cancelled.done = lambda: c.component_panel() is not None
e_cancelled.done_what = "Move/Copy opened on the second paste"


def e_ok():
    h.task_button("OK")


e_ok.done = lambda: c.panel() is None
e_ok.done_what = "Move/Copy closed on OK"


def e_kept():
    copy = k.part("Stator:3")
    if h.check("OK keeps the paste", copy is not None, k.labels()):
        k.box_is("on the original", copy, [0, 0, 0, 40, 30, 15])
        has_structure("Stator:3 (kept)", copy)


# -- F: undo / redo ------------------------------------------------------------------------------
def undo():
    t.undo()


def redo():
    t.redo()


def f_no_paste():
    h.check("Undo takes the paste", k.part("Stator:3") is None, k.labels())
    h.check("the mirror is still there", k.part("Stator (Mirror)") is not None, k.labels())


def f_no_mirror():
    h.check("Undo takes the mirror", k.part("Stator (Mirror)") is None, k.labels())
    h.check("with its rows", sum(1 for x in k.labels() if x == "Bolt") == 2, k.labels())


def f_redone():
    h.check("Redo: the mirror is back", k.part("Stator (Mirror)") is not None, k.labels())
    h.check("Redo: the paste is back", k.part("Stator:3") is not None, k.labels())
    mirrored = k.part("Stator (Mirror)")
    if mirrored is not None:
        has_structure("Stator (Mirror) after Redo", mirrored)


# -- G: the pattern step deleted -------------------------------------------------------------------
def g_delete():
    step = k.doc().getObject(state["rect"])
    t.menu(c.timeline_title(step), "Delete")


def g_deleted():
    h.check("the pattern step is gone", k.doc().getObject(state["rect"]) is None)
    h.check("Stator:2 went with it", k.part("Stator:2") is None, k.labels())
    h.check(
        "and its rows (the Stator's, the mirror's and the paste's are left)",
        sum(1 for x in k.labels() if x == "Bolt") == 3,
        k.labels(),
    )
    k.no_empty_invalid_bodies()


def g_undone():
    copy = k.part("Stator:2")
    if h.check("Undo: Stator:2 is back", copy is not None, k.labels()):
        has_structure("Stator:2 after Undo", copy)
        k.box_is("in place", copy, [100, 0, 0, 140, 30, 15])


# -- H: save, reopen -------------------------------------------------------------------------------
def h_save():
    path = os.path.join(tempfile.mkdtemp(prefix="fission180_c2_structure_"), "structure.FCStd")
    state["path"] = path
    k.doc().saveAs(path)
    App.closeDocument(k.doc().Name)


def h_reopen():
    App.openDocument(state["path"])
    Gui.activateWorkbench("Fission180Workbench")
    h.fit()


def h_reopened():
    from fission180 import instances

    for label, box in (
        ("Stator:2", [100, 0, 0, 140, 30, 15]),
        ("Stator:3", [0, 0, 0, 40, 30, 15]),
    ):
        part = k.part(label)
        if h.check("reopened: %s is there" % label, part is not None, k.labels()):
            has_structure("reopened %s" % label, part)
            k.box_is("reopened: %s in place" % label, part, box)
    mirrored = k.part("Stator (Mirror)")
    if h.check("reopened: Stator (Mirror) is there", mirrored is not None, k.labels()):
        has_structure("reopened Stator (Mirror)", mirrored)
        h.check("reopened: still a mirrored copy", instances.is_mirrored(mirrored))
    k.no_empty_invalid_bodies("reopened: no invalid body")


h.run(
    "book_components2_structure",
    [
        new_design,
        a_open,
        components_type,
        stator_row,
        a_direction_box,
        a_click_x,
        a_values,
        ok,
        a_done,
        b_move_bolt,
        b_followed,
        c_move,
        c_components,
        c_click_bolt,
        c_refused,
        d_open,
        components_type,
        stator_row,
        d_plane_box,
        d_click_xz,
        ok,
        d_done,
        e_select,
        e_copy,
        e_paste,
        e_pasted,
        e_cancelled,
        e_ok,
        e_kept,
        undo,
        f_no_paste,
        undo,
        f_no_mirror,
        redo,
        redo,
        f_redone,
        g_delete,
        g_deleted,
        undo,
        g_undone,
        h_save,
        h_reopen,
        h_reopened,
    ],
    paced_by="state",
)
