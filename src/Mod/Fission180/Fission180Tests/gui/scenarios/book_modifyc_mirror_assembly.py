# SPDX-License-Identifier: LGPL-2.1-or-later
"""Mirror of a body and of a feature inside an assembly (book parity report: Mirror "needs a
solid to repeat" when the active component is a subassembly; the first modify builder's
open item 10).

The design: the root holds no solid of its own; component "Frame" holds component "Arm",
whose body is a 20 x 10 x 5 block (x 10..30, y -5..5) with a hole d3 at (15, 2.5). Made by
the design-step builder; then real input:

A  Arm active (its body the active one). CREATE > Mirror: Pattern Type Bodies, the block
   clicked, the Mirror Plane box, the YZ plane, OK: a second body, the mirror image
   (x -30..-10), in the Arm. Then Mirror with Pattern Type Features: the hole's step
   clicked in the timeline, the XZ plane, OK: a second hole at (15, -2.5) in the block.
B  The root active (only components hold solids). CREATE > Mirror starts (it used to say
   "needs a solid"): Pattern Type Bodies, the block clicked, the Mirror Plane box, the XZ
   plane (the block lies across it: its mirror image is the block turned over), OK: one
   more body. Ctrl+Z takes it away again.
"""

import math

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import pattern_steps as ps
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import timeline_input as t

V = App.Vector
S = {}
HOLE = math.pi * 1.5**2 * 5
BLOCK = 20 * 10 * 5.0 - HOLE
STEPS = [
    {"op": "sketch", "id": "s1", "plane": "XY", "geometry": [{"rect": [10, -5, 30, 5]}]},
    {"op": "extrude", "id": "e1", "profile": "s1", "distance": 5},
    {
        "op": "sketch",
        "id": "s2",
        "plane": "XY",
        "offset": 5,
        "geometry": [{"circle": [15, 2.5, 1.5]}],
    },
    {"op": "extrude", "id": "c1", "profile": "s2", "distance": -5, "operation": "cut"},
]


def doc():
    return App.ActiveDocument


def solids():
    from fission180 import bodies

    found = []
    for body in doc().findObjects("PartDesign::Body"):
        try:
            if not body.Shape.isNull() and body.Shape.Solids:
                found.append((body, bodies.global_shape(body)))
        except Exception:
            continue
    return found


def home(body):
    from fission180 import components

    part = components.container_of(body)
    return part.Label if part is not None else "(root)"


def red():
    return {k: v for k, v in t.states().items() if v[1] not in ("ok", "")}


def setup():
    from Fission180Tests.golden.builder import Builder
    from fission180 import components

    Gui.activateWorkbench("Fission180Workbench")
    d = App.newDocument("Assembly")
    builder = Builder(d)
    frame = components.new_component(d, "Frame")
    arm = components.new_component(d, "Arm", parent=frame)
    arm.addObject(builder.body)
    d.recompute()
    for step in STEPS:
        builder.run(step)
        d.recompute()
    S["body"] = builder.body.Name
    S["arm"] = arm.Name
    components.activate_body(builder.body)
    d.clearUndos()
    h.fit()


def a_mirror():
    found = solids()
    h.check("one block with a hole", len(found) == 1 and abs(found[0][1].Volume - BLOCK) < 1e-6)
    Gui.Selection.clearSelection()
    h.ribbon("Mirror")


a_mirror.done = lambda: ps.panel() is not None
a_mirror.done_what = "the Mirror dialog is open"


def click_block():
    p = ps.panel()
    h.check("Pattern Type Bodies", p.options["pattern_type"] == "bodies", p.options["pattern_type"])
    h.click(V(25, 0, 5))


def plane_box():
    p = ps.panel()
    h.check(
        "one object picked", len(p.options["objects"]) == 1, (p.options["objects"], p.info.text())
    )
    ps.click_box("plane")


def yz_plane():
    h.fit()
    pl.click_on_plane(V(0, 3, 3))


def a_ok():
    p = ps.panel()
    plane = p.options["plane"]
    h.check(
        "the YZ plane", plane is not None and getattr(plane[0], "Role", "") == "YZ_Plane", plane
    )
    h.check("no complaint", not p.message.text(), p.message.text())
    h.task_button("OK")


def a_mirrored():
    h.check("dialog closed", ps.panel() is None)
    found = solids()
    h.check("two bodies", len(found) == 2, [x[0].Label for x in found])
    new = [x for x in found if x[0].Name != S["body"]]
    if h.check("the mirror image is a body of its own", len(new) == 1):
        body, shape = new[0]
        box = shape.BoundBox
        h.check(
            "it is the block mirrored across YZ",
            abs(box.XMin + 30) < 1e-6 and abs(box.XMax + 10) < 1e-6,
            box,
        )
        h.check("the same volume", abs(shape.Volume - BLOCK) < 1e-6, shape.Volume)
        h.check("it is in the Arm", home(body) == "Arm", home(body))
        S["mirror_body"] = body.Name
    h.check("nothing is red", not red(), red())
    from fission180 import components

    components.activate_body(doc().getObject(S["body"]))
    Gui.Selection.clearSelection()
    h.ribbon("Mirror")


a_mirrored.done = lambda: ps.panel() is not None
a_mirrored.done_what = "the Mirror dialog is open"


def click_hole_step():
    ps.timeline_click("Extrude 2")


def f_plane_box():
    p = ps.panel()
    h.check(
        "the step switched the type to Features",
        p.options["pattern_type"] == "features" and len(p.options["objects"]) == 1,
        (p.options["pattern_type"], p.options["objects"]),
    )
    ps.click_box("plane")


def xz_plane():
    h.fit()
    pl.click_on_plane(V(4, 0, 3))


def f_ok():
    p = ps.panel()
    plane = p.options["plane"]
    h.check(
        "the XZ plane", plane is not None and getattr(plane[0], "Role", "") == "XZ_Plane", plane
    )
    h.check("no complaint", not p.message.text(), p.message.text())
    h.task_button("OK")


def f_mirrored():
    h.check("dialog closed", ps.panel() is None)
    block = doc().getObject(S["body"]).Shape
    h.check("two holes in the block", abs(block.Volume - (BLOCK - HOLE)) < 1e-6, block.Volume)
    centres = ps.circle_centres(block, 1.5, z=5)
    h.check("the second hole at (15, -2.5)", (15.0, -2.5) in centres, centres)
    h.check("nothing is red", not red(), red())
    from fission180 import components

    components.set_active(None, doc())
    Gui.Selection.clearSelection()
    S["count"] = len(solids())
    S["undo"] = len(doc().UndoNames)
    h.ribbon("Mirror")


f_mirrored.done = lambda: ps.panel() is not None
f_mirrored.done_what = "Mirror starts with the root active and solids only in components"


def b_type():
    from fission180 import commands

    h.check(
        "nothing said about a missing solid",
        "needs a solid" not in (commands._TOLD.get("msg") or ""),
    )
    p = ps.panel()
    if p.options["pattern_type"] != "bodies":
        b.choose(p.pattern_type, "Bodies")


def b_click_block():
    p = ps.panel()
    h.check("Pattern Type Bodies", p.options["pattern_type"] == "bodies", p.options["pattern_type"])
    h.click(V(25, 0, 5))


def b_ok():
    p = ps.panel()
    plane = p.options["plane"]
    h.check(
        "the XZ plane", plane is not None and getattr(plane[0], "Role", "") == "XZ_Plane", plane
    )
    h.check("no complaint", not p.message.text(), p.message.text())
    h.task_button("OK")


def b_mirrored():
    h.check("dialog closed", ps.panel() is None)
    found = solids()
    h.check("one more body", len(found) == S["count"] + 1, [x[0].Label for x in found])
    known = (S["body"], S.get("mirror_body"))
    new = [x for x in found if x[0].Name not in known]
    if h.check("the new body", len(new) == 1):
        body, shape = new[0]
        h.check(
            "the block's mirror image (the same volume)",
            abs(shape.Volume - (BLOCK - HOLE)) < 1e-6,
            shape.Volume,
        )
        box = shape.BoundBox
        h.check(
            "it lies where the block lies (mirrored across XZ)",
            abs(box.XMin - 10) < 1e-6 and abs(box.YMin + 5) < 1e-6,
            box,
        )
        App.Console.PrintMessage(
            "[Fission 180] MIRROR ASSEMBLY: the new body is in %s\n" % home(body)
        )
    h.check("nothing is red", not red(), red())
    h.check("one undo step", len(doc().UndoNames) == S["undo"] + 1, list(doc().UndoNames))
    t.ctrl("z")


def b_undone():
    h.check("Ctrl+Z takes the mirror image away", len(solids()) == S["count"], len(solids()))
    h.check("nothing is red", not red(), red())
    h.shot("mirror-assembly")


h.run(
    "book_modifyc_mirror_assembly",
    [
        setup,
        a_mirror,
        click_block,
        plane_box,
        yz_plane,
        a_ok,
        a_mirrored,
        click_hole_step,
        f_plane_box,
        xz_plane,
        f_ok,
        f_mirrored,
        b_type,
        b_click_block,
        plane_box,
        xz_plane,
        b_ok,
        b_mirrored,
        b_undone,
    ],
    paced_by="state",
)
