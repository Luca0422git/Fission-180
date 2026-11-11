# SPDX-License-Identifier: LGPL-2.1-or-later
"""Rectangular Pattern and Mirror with Pattern Type Components (book parity report: "Mirror
of components is not built yet", "Mirror needs a solid to repeat" with a subassembly or
the design active, "Rectangular Pattern of components made nothing, no message"; the Tesla
Turbine's Steam Side Wall and bolts, the Robotic Hand's fingers). Only real input for what
is tested.

Setup (through the modules): the subassembly "Stator" holding "Housing" (a 40 x 30 x 10
block) and "Bolt" (a cylinder, radius 3, height 15, axis through x 10, y 10); "Wall" at
the root (a 10 x 30 x 20 block from x 60). The design's row is active and the root has no
solid of its own.

  A  CREATE > Rectangular Pattern: the dialog opens (it said "needs a solid to repeat")
     with Pattern Type Components. Click the Bolt in the window: the Bolt is picked, not
     the Stator around it. Direction: the X axis; Quantity 3, Distance 40, OK: Bolt:2 and
     Bolt:3 stand 20 and 40 mm along X; one Rectangular Pattern step.
  B  Undo: the copies are gone. Redo: back.
  C  CREATE > Mirror: opens with Pattern Type Components (not "not built yet"). Click the
     Wall, Mirror Plane: the YZ origin square, OK: a mirrored copy of the Wall at
     x -70..-60; one Mirror step.
  D  The Wall made taller (its extrude, through the module): the mirrored copy follows.
  E  Mirror again: the Stator's browser row (the whole subassembly), Mirror Plane XZ, OK:
     a copy holding the housing and the bolt mirrored to y -30..0.
  F  The first Mirror step deleted in the timeline: its copy goes with it. Undo: back.
  G  Save, close, reopen: the copies are there.
"""

import os
import tempfile

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import book_components_steps as k
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import pattern_steps as ps
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import timeline_input as t

V = App.Vector
state = {}


def new_design():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("BookComponentsPattern")
    stator = k.new_component("Stator")
    housing = k.new_component("Housing", parent=stator)
    k.add_box(housing, (0, 0, 40, 30), 10)
    bolt = k.new_component("Bolt", parent=stator)
    k.add_cylinder(bolt, (10, 10), 3, 15)
    wall = k.new_component("Wall")
    state["wall_body"] = k.add_box(wall, (60, 0, 70, 30), 20).Name
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


def closed():
    return ps.panel() is None


# -- A ---------------------------------------------------------------------------------------------
def a_open():
    Gui.Selection.clearSelection()
    h.click_empty()
    h.fit()
    ps.menu("Rectangular Pattern")


a_open.done = lambda: ps.panel() is not None
a_open.done_what = "the Rectangular Pattern dialog is open"


def a_type():
    p = ps.panel()
    if h.check(
        "Rectangular Pattern open (the root has no solid of its own)",
        p is not None and p.kind == "rectangular",
        p,
    ):
        h.check(
            "Pattern Type reads Components",
            p.options["pattern_type"] == "components",
            p.options["pattern_type"],
        )
        if p.options["pattern_type"] != "components":
            b.choose(p.pattern_type, "Components")


def a_click_bolt():
    h.click(V(10, 10, 15))  # the Bolt's top


def a_picked():
    p = ps.panel()
    h.check(
        "the Bolt is picked, not the Stator around it",
        p is not None and p.options["objects"] == [(k.part("Bolt"), "")],
        [(o.Label, s_) for o, s_ in (p.options["objects"] if p else [])],
    )
    ps.click_box("direction")


def a_click_x():
    h.fit()
    pl.click_on_plane(V(50, 0, 0))  # the X axis, beside the parts


def a_values():
    p = ps.panel()
    d = p.options["direction"] if p else None
    h.check("the X axis is direction 1", d is not None and d[0].Role == "X_Axis", d)
    ps.type_quantity(p.quantity, 3)
    ps.type_value(p.distance_field.widget, "40")


def ok():
    p = ps.panel()
    if p is not None:
        h.caught_up(p)
    h.task_button("OK")


ok.done = closed
ok.done_what = "the dialog closed"


def a_done():
    found = steps("rectangular")
    if not h.check("one Rectangular Pattern step", len(found) == 1, found):
        return
    state["rect"] = found[0].Name
    made = copies(found[0])
    h.check(
        "two copies: Bolt:2 and Bolt:3",
        [x.Label for x in made] == ["Bolt:2", "Bolt:3"],
        [x.Label for x in made],
    )
    if len(made) == 2:
        k.box_is("Bolt:2 stands 20 mm along X", made[0], [27, 7, 0, 33, 13, 15])
        k.box_is("Bolt:3 stands 40 mm along X", made[1], [47, 7, 0, 53, 13, 15])
    k.box_is("the Bolt itself stayed", k.part("Bolt"), [7, 7, 0, 13, 13, 15])
    h.check(
        "the Stator was not copied",
        [x for x in k.labels() if x.startswith("Stator")] == ["Stator"],
        k.labels(),
    )
    h.shot("A-pattern")


# -- B ---------------------------------------------------------------------------------------------
def undo():
    t.undo()


def redo():
    t.redo()


def b_undone():
    h.check(
        "Undo takes the pattern and its copies",
        not steps("rectangular") and k.part("Bolt:2") is None,
        k.labels(),
    )


def b_redone():
    h.check(
        "Redo brings them back",
        len(steps("rectangular")) == 1 and k.part("Bolt:3") is not None,
        k.labels(),
    )


# -- C ---------------------------------------------------------------------------------------------
def c_open():
    Gui.Selection.clearSelection()
    h.click_empty()
    h.fit()
    ps.menu("Mirror")


c_open.done = lambda: ps.panel() is not None
c_open.done_what = "the Mirror dialog is open"


def c_type():
    p = ps.panel()
    if h.check("Mirror open", p is not None and p.kind == "mirror", p):
        h.check(
            "Pattern Type reads Components (it was 'not built yet')",
            p.options["pattern_type"] == "components",
            p.options["pattern_type"],
        )
        if p.options["pattern_type"] != "components":
            b.choose(p.pattern_type, "Components")


def c_click_wall():
    h.click(V(65, 15, 20))  # the Wall's top


def c_plane_box():
    p = ps.panel()
    h.check(
        "the Wall is picked",
        p is not None and p.options["objects"] == [(k.part("Wall"), "")],
        [(o.Label, s_) for o, s_ in (p.options["objects"] if p else [])],
    )
    ps.click_box("plane")


def c_click_yz():
    h.fit()
    pl.click_square("YZ_Plane")


def c_preview():
    p = ps.panel()
    plane = p.options["plane"] if p else None
    h.check(
        "the YZ plane is the mirror plane", plane is not None and plane[0].Role == "YZ_Plane", plane
    )


def c_done():
    found = steps("mirror")
    if not h.check("one Mirror step", len(found) == 1, found):
        return
    state["mirror"] = found[0].Name
    made = copies(found[0])
    if h.check("one mirrored copy", len(made) == 1, [x.Label for x in made]):
        state["wall_copy"] = made[0].Name
        # (wave 7, components-2) a mirrored component is the other hand of the part: a
        # component of its own in name, not "Wall:2" (which made the original "Wall:1")
        h.check("named Wall (Mirror)", made[0].Label == "Wall (Mirror)", made[0].Label)
        k.box_is("the Wall mirrored across YZ: x -70..-60", made[0], [-70, 0, 0, -60, 30, 20])
        h.check(
            "the same volume", k.close(sum(k.volume(x) for x in k.bodies_of(made[0].Label)), 6000.0)
        )
    k.box_is("the Wall itself stayed", k.part("Wall"), [60, 0, 0, 70, 30, 20])
    h.check("the timeline shows a Mirror step", any("Mirror" in x for x in t.titles()), t.titles())
    h.shot("C-mirror")


# -- D ---------------------------------------------------------------------------------------------
def d_taller():
    from fission180 import extrude

    doc = k.doc()
    body = doc.getObject(state["wall_body"])
    feature = body.Tip
    doc.openTransaction("Edit Extrude")
    extrude.apply(feature, {"distance": 25.0})
    doc.commitTransaction()
    doc.recompute()


def d_followed():
    k.box_is("the Wall is 25 tall", k.part("Wall"), [60, 0, 0, 70, 30, 25])
    copy = k.doc().getObject(state.get("wall_copy", ""))
    if h.check("the mirrored copy is there", copy is not None):
        k.box_is("the mirrored copy followed", copy, [-70, 0, 0, -60, 30, 25])


# -- E ---------------------------------------------------------------------------------------------
def e_row():
    t.click_row("Stator")


def e_plane_box():
    p = ps.panel()
    h.check(
        "the Stator is picked from its row",
        p is not None and p.options["objects"] == [(k.part("Stator"), "")],
        [(o.Label, s_) for o, s_ in (p.options["objects"] if p else [])],
    )
    ps.click_box("plane")


def e_click_xz():
    h.fit()
    pl.click_square("XZ_Plane")


def e_done():
    found = [x for x in steps("mirror") if x.Name != state.get("mirror")]
    if not h.check("a second Mirror step", len(found) == 1, found):
        return
    made = copies(found[0])
    if h.check("one mirrored copy of the subassembly", len(made) == 1, [x.Label for x in made]):
        box = k.box(made[0])
        ok_box = box is not None and abs(box[1] + 30) < 1e-4 and abs(box[4]) < 1e-4
        h.check("the housing and the bolts mirrored across XZ: y -30..0", ok_box, box)
        # (wave 7, components-2) the copy of a subassembly keeps its structure (it came in
        # flat: two bodies straight in the copy) and is a component of its own in name
        from fission180 import components

        rows = {c.Label: c for c in made[0].Group if components.is_component(c)}
        h.check(
            "its rows: the Housing and the Bolt, as in the original",
            sorted(rows) == ["Bolt", "Housing"],
            sorted(rows),
        )
        h.check(
            "one body in each",
            all(len(components.bodies_in(k.doc(), c)) == 1 for c in rows.values()),
            {name: len(components.bodies_in(k.doc(), c)) for name, c in rows.items()},
        )
        h.check("no body straight in the copy", not components.bodies_in(k.doc(), made[0]))
        h.check("named Stator (Mirror)", made[0].Label == "Stator (Mirror)", made[0].Label)


# -- F ---------------------------------------------------------------------------------------------
def f_delete():
    step = k.doc().getObject(state["mirror"])
    from Fission180Tests.gui import component2_steps as c

    t.menu(c.timeline_title(step), "Delete")


def f_deleted():
    h.check("the first Mirror step is gone", k.doc().getObject(state["mirror"]) is None)
    h.check("its copy went with it", k.doc().getObject(state.get("wall_copy", "")) is None)
    k.box_is("the Wall stays", k.part("Wall"), [60, 0, 0, 70, 30, 25])


def f_undone():
    h.check(
        "Undo: the Mirror step and its copy are back",
        k.doc().getObject(state["mirror"]) is not None
        and k.doc().getObject(state.get("wall_copy", "")) is not None,
    )


# -- G ---------------------------------------------------------------------------------------------
def g_save():
    path = os.path.join(tempfile.mkdtemp(prefix="fission180_bookcomp_"), "pattern.FCStd")
    state["path"] = path
    doc = k.doc()
    doc.saveAs(path)
    App.closeDocument(doc.Name)


def g_reopen():
    App.openDocument(state["path"])
    h.fit()


def g_reopened():
    k.doc().recompute()
    h.check("two Mirror steps", len(steps("mirror")) == 2, steps("mirror"))
    h.check("one Rectangular Pattern", len(steps("rectangular")) == 1)
    copy = k.doc().getObject(state.get("wall_copy", ""))
    if h.check("the mirrored Wall is there", copy is not None):
        k.box_is("where it was", copy, [-70, 0, 0, -60, 30, 25])
    k.no_empty_invalid_bodies("no invalid body after reopening")


h.run(
    "book_components_pattern",
    [
        new_design,
        a_open,
        a_type,
        a_click_bolt,
        a_picked,
        a_click_x,
        a_values,
        ok,
        a_done,
        undo,
        b_undone,
        redo,
        b_redone,
        c_open,
        c_type,
        c_click_wall,
        c_plane_box,
        c_click_yz,
        c_preview,
        ok,
        c_done,
        d_taller,
        d_followed,
        c_open,
        c_type,
        e_row,
        e_plane_box,
        e_click_xz,
        ok,
        e_done,
        f_delete,
        f_deleted,
        undo,
        f_undone,
        g_save,
        g_reopen,
        g_reopened,
    ],
    paced_by="state",
)
