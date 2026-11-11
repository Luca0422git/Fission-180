# SPDX-License-Identifier: LGPL-2.1-or-later
"""The timeline's Delete on a step that made a component takes the component with it, and
Ctrl+Z brings everything back in one step (wave 7: the hardware builder found that deleting
only the Hardware step left an empty component and its occurrences behind).

The designs are made by the design-step builder (the code the AI tools run); Delete is real
input: right-click the step in the timeline > Delete, then Ctrl+Z.

A  Hardware: a 40 x 30 x 10 plate, an M4 button head screw put on its top (the Hardware
   step, its component, the clearance Hole it made in the plate, the joint that holds it).
   Delete on the Hardware step: the part's component, its hole and its joint are gone, the
   plate is whole again. Ctrl+Z: all back, the hole too.
B  Create Components from Bodies, Paste (a second occurrence; it has no step of its own)
   and a Rectangular Pattern of the component. Delete on the pattern step takes its two
   copies. Delete on the component's step takes the steps that built it; the pasted
   occurrence keeps the component alive (Fusion keeps a component while an occurrence
   remains) and the pattern that repeated it is marked. Each undone with one Ctrl+Z.
"""

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import timeline_input as t

V = App.Vector
S = {}
PLATE = 40 * 30 * 10.0
HARDWARE = [
    {"op": "sketch", "id": "s1", "plane": "XY", "geometry": [{"rect": [0, 0, 40, 30]}]},
    {"op": "extrude", "id": "e1", "profile": "s1", "distance": 10},
    {
        "op": "sf_hardware",
        "id": "hw1",
        "face": {"normal": [0, 0, 1], "count": 1},
        "at": [20, 15, 10],
        "standard": "iso7380",
        "size": "4",
        "length": 10,
    },
]
COMPONENTS = [
    {"op": "sketch", "id": "s1", "plane": "XY", "geometry": [{"rect": [0, 0, 20, 10]}]},
    {"op": "extrude", "id": "e1", "profile": "s1", "distance": 5},
    {"op": "components_from_bodies", "id": "k1", "bodies": ["e1"], "label": "Bracket"},
    {"op": "component_paste", "id": "i1", "component": "k1", "dx": 0, "dy": 40},
    {
        "op": "component_pattern",
        "id": "p1",
        "component": "k1",
        "kind": "rectangular",
        "direction": "X",
        "quantity": 3,
        "distance": 30,
        "distribution": "spacing",
    },
]


def doc():
    return App.ActiveDocument


def parts():
    from fission180 import components

    return sorted(o.Label for o in doc().Objects if components.is_component(o))


def snapshot():
    from fission180 import joints

    volumes = []
    for body in doc().findObjects("PartDesign::Body"):
        shape = body.Shape
        volumes.append((body.Name, 0.0 if shape.isNull() else round(shape.Volume, 3)))
    return {
        "components": parts(),
        "volumes": sorted(volumes),
        "joints": sorted(o.Label for o in doc().Objects if joints.is_joint(o)),
        "holes": sorted(o.Name for o in doc().Objects if o.TypeId == "PartDesign::Hole"),
        "timeline": list(t.titles()),
    }


def red():
    return {k: v for k, v in t.states().items() if v[1] not in ("ok", "")}


def build(name, steps):
    from Fission180Tests.golden.builder import Builder

    d = App.newDocument(name)
    builder = Builder(d)
    for step in steps:
        builder.run(step)
        d.recompute()
    d.clearUndos()
    h.fit()
    return builder


def titled(start):
    found = [x for x in t.titles() if x.startswith(start)]
    h.check("a %s step in the timeline" % start, bool(found), t.titles())
    return found[0] if found else start


# -- A: Hardware ----------------------------------------------------------------------------------
def a_setup():
    Gui.activateWorkbench("Fission180Workbench")
    builder = build("Hardware", HARDWARE)
    S["plate"] = builder.objects["e1"].Name


def a_delete():
    S["a"] = snapshot()
    h.check("the screw's component", len(S["a"]["components"]) == 1, S["a"]["components"])
    h.check("the hole it made", len(S["a"]["holes"]) == 1, S["a"]["holes"])
    plate = [v for n, v in S["a"]["volumes"] if 0 < v < PLATE and v > PLATE / 2]
    h.check("the plate has the hole", len(plate) == 1, S["a"]["volumes"])
    t.menu(titled("Hardware"), "Delete")


def a_deleted():
    now = snapshot()
    h.check("the part's component is gone", now["components"] == [], now["components"])
    h.check("its hole is gone", now["holes"] == [], now["holes"])
    h.check("its joint is gone", now["joints"] == [], now["joints"])
    solid = [v for _n, v in now["volumes"] if v > 0]
    h.check("the plate alone, whole again", solid == [PLATE], now["volumes"])
    h.check("no Hardware step left", not [x for x in now["timeline"] if x.startswith("Hardware")])
    h.check("nothing is red", not red(), red())
    h.check("one undo step", len(doc().UndoNames) == 1, list(doc().UndoNames))
    t.ctrl("z")


def a_undone():
    now = snapshot()
    diff = {k: (now[k], S["a"][k]) for k in now if now[k] != S["a"][k]}
    h.check("Ctrl+Z brings everything back", not diff, diff)
    h.check("nothing is red", not red(), red())
    h.check("nothing left to undo", len(doc().UndoNames) == 0, list(doc().UndoNames))


# -- B: components from bodies, a pasted occurrence, a pattern of the component -------------------
def b_setup():
    build("Brackets", COMPONENTS)


def b_delete_pattern():
    S["b"] = snapshot()
    h.check(
        "the bracket, its pasted occurrence and two pattern copies",
        len(S["b"]["components"]) == 4,
        S["b"]["components"],
    )
    t.menu(titled("Rectangular Pattern"), "Delete")


def b_pattern_deleted():
    now = snapshot()
    h.check("the pattern's copies went with it", len(now["components"]) == 2, now["components"])
    h.check("nothing is red", not red(), red())
    h.check("one undo step", len(doc().UndoNames) == 1, list(doc().UndoNames))
    t.ctrl("z")


def b_pattern_back():
    now = snapshot()
    diff = {k: (now[k], S["b"][k]) for k in now if now[k] != S["b"][k]}
    h.check("Ctrl+Z brings the pattern and its copies back", not diff, diff)
    t.menu(titled("Bracket"), "Delete")


def b_component_deleted():
    now = snapshot()
    # Fusion keeps a component while one of its occurrences remains: the pasted occurrence
    # takes the name over (components.remove), the steps that built the original go, and
    # the pattern that repeated it says so in the timeline (Fusion marks the steps that
    # depended on what was deleted).
    h.check(
        "the steps that built the component are gone",
        "Extrude 1" not in now["timeline"] and "Sketch 1" not in now["timeline"],
        now["timeline"],
    )
    h.check(
        "one component fewer",
        len(now["components"]) == len(S["b"]["components"]) - 1,
        now["components"],
    )
    flagged = sorted(red())
    h.check(
        "the pattern that repeated it is marked in the timeline",
        len(flagged) == 1 and flagged[0].startswith("Rectangular Pattern"),
        red(),
    )
    h.check("one undo step", len(doc().UndoNames) == 1, list(doc().UndoNames))
    t.ctrl("z")


def b_component_back():
    now = snapshot()
    diff = {k: (now[k], S["b"][k]) for k in now if now[k] != S["b"][k]}
    h.check("Ctrl+Z brings the component and all that used it back", not diff, diff)
    h.check("nothing is red", not red(), red())
    h.shot("delete-component-steps")


h.run(
    "book_modifyc_delete_component_steps",
    [
        a_setup,
        a_delete,
        a_deleted,
        a_undone,
        b_setup,
        b_delete_pattern,
        b_pattern_deleted,
        b_pattern_back,
        b_component_deleted,
        b_component_back,
    ],
    paced_by="state",
)
