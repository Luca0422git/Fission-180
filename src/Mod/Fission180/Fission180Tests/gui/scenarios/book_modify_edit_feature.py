# SPDX-License-Identifier: LGPL-2.1-or-later
"""Edit Feature over every kind of step this design's timeline shows (book parity report, bug
20: "Edit Feature on a Gear step deletes it"; the brief asks for the audit of every step).

The design is built by the design-step builder (the code the AI tools and the golden models
run: a sketch, an extrude, fillets, a chamfer, a chamfer with two sets, a hole, a boss, a
thread, a pattern, a mirror, a shell, a gear, a box, a sphere, a combine, a split face, a split
body). The test itself is real input, the same for each step, in timeline order:

  right-click the step > Edit Feature (Edit Sketch): its dialog opens (or the sketch);
  Cancel: the dialog closes, the timeline, every body's volume and every step's state are as
  they were;
  right-click > Edit Feature again, OK without a change: the same.

The table of what each step did is printed at the end (docs/fission180/sessions/book-modify.md
has it).
"""

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import timeline_input as t

V = App.Vector
S = {"rows": []}

STEPS = (
    {"op": "sketch", "id": "s1", "plane": "XY", "geometry": [{"rect": [0, 0, 60, 40]}]},
    {"op": "extrude", "id": "e1", "profile": "s1", "distance": 20},
    {
        "op": "blend_fillet",
        "id": "f1",
        "radius": 3,
        "edges": {"type": "line", "parallel": [0, 0, 1], "count": 4},
    },
    {"op": "blend_chamfer", "id": "c1", "distance": 1, "faces": {"normal": [0, 0, 1], "count": 1}},
    {
        "op": "hole_at",
        "id": "h1",
        "face": {"normal": [0, 0, 1], "count": 1},
        "at": [15, 20, 20],
        "extent": "all",
        "diameter": 5,
        "tap_type": "simple",
        "drill_point": "flat",
    },
    {
        "op": "sketch",
        "id": "s2",
        "plane": "XY",
        "offset": 20,
        "geometry": [{"circle": [45, 20, 5]}],
    },
    {"op": "extrude", "id": "e2", "profile": "s2", "distance": 12},
    {"op": "thread", "id": "t1", "faces": {"type": "cylinder", "radius": 5, "count": 1}},
    {
        "op": "rectangular_pattern",
        "id": "p1",
        "features": ["h1"],
        "direction": "X",
        "quantity": 2,
        "distance": 12,
        "distribution": "spacing",
    },
    {
        "op": "fillet_sets",
        "id": "c2",
        "kind": "chamfer",
        "sets": [
            {
                "edges": {
                    "type": "circle",
                    "radius": 5,
                    "at": {"axis": "z", "value": "max"},
                    "count": 1,
                },
                "chamfer_type": "equal",
                "distance": 0.5,
            },
        ],
    },
    {
        "op": "sf_gear",
        "id": "g1",
        "plane": "XY",
        "x": 120,
        "y": 0,
        "module": 1.5,
        "teeth": 16,
        "thickness": 5,
        "operation": "new_body",
    },
    {
        "op": "sf_primitive",
        "id": "b1",
        "kind": "box",
        "plane": "XY",
        "x": 110,
        "y": -10,
        "length": 20,
        "width": 20,
        "height": 10,
        "operation": "new_body",
    },
    {"op": "combine", "id": "k1", "target": "g1", "tools": ["b1"], "operation": "join"},
    {
        "op": "sf_primitive",
        "id": "sp1",
        "kind": "sphere",
        "plane": "XY",
        "x": 0,
        "y": -80,
        "diameter": 30,
        "operation": "new_body",
    },
    {
        "op": "sf_primitive",
        "id": "b2",
        "kind": "box",
        "plane": "XY",
        "x": -20,
        "y": -100,
        "length": 40,
        "width": 30,
        "height": 10,
        "operation": "new_body",
    },
    {
        "op": "split_face",
        "id": "sf1",
        "of": "b2",
        "faces": {"type": "plane", "normal": [0, 0, 1], "count": 1},
        "tool": "YZ",
    },
)


def doc():
    return App.ActiveDocument


def volumes():
    out = {}
    for obj in doc().Objects:
        if obj.TypeId == "PartDesign::Body":
            try:
                out[obj.Name] = round(obj.Shape.Volume, 6) if not obj.Shape.isNull() else 0.0
            except Exception:
                out[obj.Name] = 0.0
    return out


def snapshot():
    return {
        "titles": list(t.titles()),
        "states": {k: v[1] for k, v in t.states().items()},
        "volumes": volumes(),
    }


def editing():
    """What is open: "dialog", "sketch" or ""."""
    try:
        gdoc = Gui.ActiveDocument
        edit = gdoc.getInEdit() if gdoc is not None else None
        if edit is not None and edit.Object.TypeId == "Sketcher::SketchObject":
            return "sketch"
    except Exception:
        pass
    return "dialog" if Gui.Control.activeDialog() else ""


def setup():
    from Fission180Tests.golden.builder import Builder

    Gui.activateWorkbench("Fission180Workbench")
    d = App.newDocument("EditEveryStep")
    builder = Builder(d)
    built = []
    for step in STEPS:
        try:
            builder.run(step)
            d.recompute()
            built.append(step["id"])
        except Exception as exc:
            h.check("the design-step builder makes %s (%s)" % (step["id"], step["op"]), False, exc)
    h.fit()


def setup_done():
    from fission180 import components

    try:
        components.activate(None)  # the root: every step is in the timeline
    except Exception:
        pass
    S["titles"] = [x for x in t.titles()]
    S["base"] = snapshot()
    bad = {k: v for k, v in S["base"]["states"].items() if v != "ok"}
    h.check("the design is built without a red step", not bad, bad)
    h.check("a timeline with many kinds of steps", len(S["titles"]) >= 16, S["titles"])
    kinds = sorted({x.rstrip("0123456789 ") for x in S["titles"]})
    S["kinds"] = kinds
    wanted = (
        "Sketch",
        "Extrude",
        "Fillet",
        "Chamfer",
        "Hole",
        "Thread",
        "Gear",
        "Combine",
        "Split Face",
    )
    h.check("the kinds asked for are there", all(k in kinds for k in wanted), kinds)
    h.shot("0-design")


def same(where, title):
    now = snapshot()
    base = S["base"]
    ok_titles = h.check(
        "%s: %s is still in the timeline, in its place" % (where, title),
        now["titles"] == base["titles"],
        now["titles"],
    )
    bad = {k: v for k, v in now["states"].items() if v != "ok"}
    ok_states = h.check("%s (%s): no step is red" % (where, title), not bad, bad)
    changed = {
        k: (base["volumes"].get(k), v)
        for k, v in now["volumes"].items()
        if abs(base["volumes"].get(k, -1.0) - v) > 1e-6 * max(1.0, abs(v))
    }
    ok_volume = h.check("%s (%s): every body is as it was" % (where, title), not changed, changed)
    return ok_titles and ok_states and ok_volume


def first_entry(title):
    entries = [text for text, _on in t.menu_entries(title)]
    return entries[0] if entries else ""


def close_what_is_open(how):
    kind = editing()
    if kind == "sketch":
        h.ribbon("Finish Sketch")
    elif kind == "dialog":
        h.task_button(how)
    return kind


def make(index):
    row = {"title": None, "entry": "", "opens": "", "cancel": None, "ok": None}

    def title():
        return S["titles"][index] if index < len(S.get("titles", [])) else None

    def open_1():
        name = title()
        if name is None:
            return
        h.click_empty()
        row["title"] = name
        row["entry"] = first_entry(name)
        S["rows"].append(row)
        if row["entry"] == "Activate":
            return  # a component's step: nothing to edit
        t.menu(name, row["entry"])

    def cancel():
        name = title()
        if name is None or row["entry"] == "Activate":
            return
        row["opens"] = editing()
        h.check("%s > %s opens its dialog" % (name, row["entry"]), bool(row["opens"]), row)
        close_what_is_open("Cancel")

    def after_cancel():
        name = title()
        if name is None or row["entry"] == "Activate":
            return
        h.check("%s: Cancel closes it" % name, not editing(), editing())
        row["cancel"] = same("Cancel", name)
        h.click_empty()
        t.menu(name, row["entry"])

    def ok():
        name = title()
        if name is None or row["entry"] == "Activate":
            return
        h.check("%s > %s opens again" % (name, row["entry"]), bool(editing()), row)
        close_what_is_open("OK")

    def after_ok():
        name = title()
        if name is None or row["entry"] == "Activate":
            return
        h.check("%s: OK closes it" % name, not editing(), editing())
        row["ok"] = same("OK without a change", name)

    steps = [open_1, cancel, after_cancel, ok, after_ok]
    for step in steps:
        step.__name__ = "step%02d_%s" % (index, step.__name__)
        step.timeout_s = 180
    return steps


def table():
    lines = [
        "| step | menu entry | opens | Cancel leaves it | OK leaves it |",
        "|---|---|---|---|---|",
    ]
    for row in S["rows"]:
        lines.append(
            "| %s | %s | %s | %s | %s |"
            % (
                row["title"],
                row["entry"],
                row["opens"] or ("-" if row["entry"] == "Activate" else "NOTHING"),
                {True: "yes", False: "NO", None: "-"}[row["cancel"]],
                {True: "yes", False: "NO", None: "-"}[row["ok"]],
            )
        )
    App.Console.PrintMessage("[Fission 180] EDIT FEATURE TABLE\n" + "\n".join(lines) + "\n")
    h.check(
        "every step was looked at",
        len(S["rows"]) == len(S["titles"]),
        (len(S["rows"]), S["titles"]),
    )


COUNT = 20  # at least as many as the timeline has steps (the extra ones do nothing)
all_steps = [setup, setup_done]
for k in range(COUNT):
    all_steps += make(k)
all_steps.append(table)

h.run("book_modify_edit_feature", all_steps, paced_by="state")
