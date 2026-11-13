# SPDX-License-Identifier: LGPL-2.1-or-later
"""The headless runner's calls of the wave 8 ai-behaviour tools (Fission180Tests/headless/
runner.py runs SESSION): plan_approach on no design, a solid, a mesh and a study; list_tools by
goal and by workspace; the new help topics; ask_person without a form; show_workspace without
the window; inspect_design and get_design saying which workspace is shown (none headless)."""

import json


def _data(answer):
    text = answer["text"]
    start = text.find("\n{")
    return json.loads(text[start + 1 :] if start >= 0 else text[text.find("{") :])


def _check(fn):
    def check(answer, run):
        try:
            return fn(_data(answer), run)
        except Exception as exc:
            return "check raised %s: %s" % (exc, answer["text"][:300])

    return check


def _goals(*expected):
    def check(data, run):
        got = [g["id"] for g in data["goals"]]
        return None if got == list(expected) else "goals %s, not %s" % (got, list(expected))

    return check


def _mesh_plan(data, run):
    if [g["id"] for g in data["goals"]] != ["mesh_to_solid"]:
        return "goals %s" % data["goals"]
    about = data.get("about") or {}
    if about.get("kind") != "mesh" or not about.get("triangles"):
        return "about %s" % about
    if not data["ask_first"] or data["ask_first"][0]["id"] != "editable":
        return "questions %s" % data["ask_first"]
    if not data["design"]["meshes"]:
        return "the design's meshes are not in the facts: %s" % data["design"]
    if not any("facet" in line for line in data["avoid"]):
        return "no facet warning"
    return None


def _study_plan(data, run):
    tools = [r["tool"] for r in data["route"]]
    for name in ("create_study", "add_constraint", "add_load", "solve_study"):
        if name not in tools:
            return "%s missing from %s" % (name, tools)
    if "show_workspace" in tools:
        return "show_workspace offered without the window"
    if data["design"]["solids"][0]["faces"] != 6:
        return "facts %s" % data["design"]
    return None


def _first_is(name):
    def check(data, run):
        names = [r["name"] for r in data["tools"]]
        if not names or names[0] != name:
            return "first %s, not %s" % (names[:3], name)
        if not data["tools"][0].get("purpose"):
            return "no purpose"
        return None

    return check


def _all_simulation(data, run):
    rows = data["tools"]
    if not rows or any(r["workspace"] != "simulation" for r in rows):
        return "rows %s" % [(r["name"], r.get("workspace")) for r in rows]
    return None


def _no_window(data, run):
    return None if "workspace" in data and data["workspace"] is None else "workspace %s" % data


SESSION = [
    # --- wave 8, ai-behaviour ----------------------------------------------------------------
    {
        "tool": "plan_approach",
        "args": {"request": "make me a new 40 x 30 x 10 box with 3 mm rounded edges"},
        "contains": ["Plan: model a new part.", "examples_search"],
        "check": _check(_goals("new_part")),
    },
    {"tool": "list_tools", "args": {"goal": "make it hollow"}, "check": _check(_first_is("shell"))},
    {
        "tool": "list_tools",
        "args": {"goal": "round the edges"},
        "check": _check(_first_is("fillet")),
    },
    {"tool": "list_tools", "args": {"workspace": "simulation"}, "check": _check(_all_simulation)},
    {"tool": "get_help", "args": {"topic": "approach"}, "contains": ["plan_approach"]},
    {"tool": "get_help", "args": {"topic": "workspaces"}, "contains": ["any workspace"]},
    {"tool": "get_help", "args": {"topic": "tools"}, "contains": ["== SIMULATION =="]},
    {
        "tool": "ask_person",
        "args": {"questions": [{"question": "Which material?", "default": "PLA"}]},
        "contains": ["ask the questions in your reply"],
    },
    {"tool": "new_design", "args": {"name": "ApproachPlate"}},
    {
        "tool": "primitive",
        "args": {"kind": "box", "plane": "XY", "length": 60, "width": 40, "height": 10},
    },
    {
        "tool": "plan_approach",
        "args": {"request": "will this plate break if I hang 20 kg on it?"},
        "check": _check(_study_plan),
    },
    {
        "tool": "plan_approach",
        "args": {"request": "round the edges", "target": "NoSuchBody"},
        "expect": "error",
        "contains": ["NoSuchBody"],
    },
    {
        "tool": "show_workspace",
        "args": {"workspace": "simulation"},
        "expect": "error",
        "contains": ["needs the Fission 180 window"],
    },
    {"tool": "inspect_design", "args": {}, "check": _check(_no_window)},
    {"tool": "get_design", "args": {}, "check": _check(_no_window)},
    {"tool": "export", "args": {"format": "stl", "path": "{tmp}/approach_plate.stl"}},
    {"tool": "new_design", "args": {"name": "ApproachRelic"}},
    {"tool": "import_file", "args": {"path": "{tmp}/approach_plate.stl"}},
    {
        "tool": "plan_approach",
        "args": {"request": "make this mesh a solid", "target": "MeshBody"},
        "contains": ["Plan: turn the mesh into a solid", "triangles"],
        "check": _check(_mesh_plan),
    },
    {
        "tool": "plan_approach",
        "args": {"request": "make it editable"},
        "contains": ["start_rebuild"],
        "check": _check(_goals("editable")),
    },
]
