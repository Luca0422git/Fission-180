# SPDX-License-Identifier: LGPL-2.1-or-later
"""The headless calls of wave 8's AI tools of the SIMULATION, MANUFACTURE and ANIMATION
workspaces, SHEET METAL and UTILITIES > MAKE (builder ai-workspaces; runner.py runs SESSION
after its own, so every tool of the catalogue is called). Each number is worked out by hand:
a 100 x 20 x 10 mm aluminium cantilever under 100 N at its free end (beam theory: the tip moves
F L^3 / 3 E I, half way along 5/16 of that; the bending stress at x is F (L - x) c / I), the
golden CAM plate (100 x 60 x 10 with two 6 mm holes), two components on a storyboard, a sheet
metal tray.

    freecadcmd -c "from Fission180Tests.headless import ai_workspaces; ai_workspaces.main()"

runs these calls alone (the report goes to FISSION180_HEADLESS_OUT like the runner's)."""

import json
import os

L, W, H = 100.0, 20.0, 10.0  # the cantilever (mm)
I_BEAM = W * H**3 / 12.0  # mm^4


def _json(answer):
    text = answer["text"]
    start = text.find("{")
    return json.loads(text[start:]) if start >= 0 else None


def _near(got, want, rel=0.05, absolute=0.0):
    return got is not None and abs(got - want) <= max(rel * abs(want), absolute)


def _youngs(run):
    from fission180 import simulation

    doc = run.doc()
    study = simulation.studies(doc)[0]
    body = simulation.study_bodies(study)[0]
    return simulation.study_material(study, body)[1]["youngs_mpa"]


def _tip(run, force=100.0):
    return force * L**3 / (3.0 * _youngs(run) * I_BEAM)


def _check(fn):
    def check(answer, run):
        try:
            problem = fn(_json(answer), run)
        except Exception as exc:  # (a missing key is a failed check, in words)
            return "check failed: %r on %s" % (exc, answer["text"][:300])
        return None if problem is None else str(problem)[:600]

    return check


def _probe_points(data, run):
    tip, mid = data["points"]
    want = _tip(run)
    if not (tip["inside"] and mid["inside"]):
        return "a point is not on the part: %s" % data["points"]
    if not _near(tip["values"]["displacement"], want, 0.05):
        return "tip moves %s, beam theory %s" % (tip["values"]["displacement"], want)
    ratio = mid["values"]["displacement"] / tip["values"]["displacement"]
    if not _near(ratio, 5.0 / 16.0, 0.06):
        return "half way it moves %s of the tip, beam theory 5/16" % ratio
    if not (tip["moved_mm"][2] < 0 and abs(tip["moved_mm"][2]) > 0.9 * want):
        return "the tip moves %s, expected down" % tip["moved_mm"]
    return None


def _probe_top(data, run):
    row = data["on"][0]
    if row["nodes"] < 20:
        return "only %s nodes on the top face" % row["nodes"]
    disp = row["values"]["displacement"]
    if not _near(disp["max"], _tip(run), 0.05) or disp["max_at"][0] < L - 1e-6:
        return "the top face's largest movement %s at %s" % (disp["max"], disp["max_at"])
    if disp["min"] > 1e-6 or disp["min_at"][0] > 1e-6:
        return "the top face's smallest movement %s at %s" % (disp["min"], disp["min_at"])
    vm = row["values"]["von_mises"]
    # (the top fibre near the fixed end: F (L - x) c / I, 30 MPa at x = 0 by beam theory; the
    # default mesh's nodes on the top face nearest the fixed end are a few mm from it)
    x = vm["max_at"][0]
    want = 100.0 * (L - x) * (H / 2.0) / I_BEAM
    if x > 15.0 or not (0.85 * want < vm["max"] < 2.5 * want):
        return "the top face's highest stress %s at %s, beam theory %s" % (
            vm["max"],
            vm["max_at"],
            want,
        )
    return None


def _probe_section(data, run):
    row = data["section"]
    if row["triangles"] < 4:
        return "the cut has %s triangles" % row["triangles"]
    stress = 100.0 * (L - 50.0) * (H / 2.0) / I_BEAM  # 15 MPa at the top and bottom fibres
    vm = row["values"]["von_mises"]
    if not _near(vm["max"], stress, 0.12):
        return "the cut at x = 50 has von Mises %s, beam theory %s" % (vm["max"], stress)
    if any(abs(p[0] - 50.0) > 1e-6 for p in (vm["max_at"], vm["min_at"])):
        return "the extremes are not on the cut: %s" % vm
    if vm["min"] > 0.3 * stress:
        return "the neutral axis carries %s MPa" % vm["min"]
    return None


def _setup_rows(kinds, held=True):
    def check(data, run):
        got = sorted((r["category"], r["kind"]) for r in data["items"])
        if got != sorted(kinds):
            return "items %s, expected %s" % (got, sorted(kinds))
        if held and data["free_motions"]:
            return "free motions %s" % data["free_motions"]
        if not held and not (data["free_motions"] and data["free_motions"][0]["held_by_nothing"]):
            return "nothing holds the beam, yet %s" % data["free_motions"]
        if data["materials"][0]["material"].lower().find("alumin") < 0:
            return "material %s" % data["materials"]
        return None

    return check


def _results_tip(force):
    def check(data, run):
        got = data["results"]["displacement"]["max"]
        if not _near(got, _tip(run, force), 0.05):
            return "tip %s, beam theory %s" % (got, _tip(run, force))
        solver = data.get("solver") or {}
        if solver.get("Mesh", {}).get("Nodes") is None or data.get("solve_seconds") is None:
            return "no Solver Data: %s, %s s" % (solver, data.get("solve_seconds"))
        return None

    return check


def _report_file(name, words):
    def check(answer, run):
        path = run.path(name)
        if not os.path.isfile(path):
            return "no %s" % path
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        missing = [w for w in words if w not in text]
        return "the report lacks %s" % missing if missing else None

    return check


def _mesh_counts(data, run):
    mesh = data["mesh"]
    if not (mesh.get("nodes", 0) > 100 and mesh.get("elements", 0) > 20):
        return "mesh %s" % mesh
    if data["seconds"] < 0 or data["shown"]:
        return "seconds %s, shown %s" % (data["seconds"], data["shown"])
    return None


def _copied(answer, run):
    from fission180 import simulation

    found = simulation.studies(run.doc())
    if len(found) != 2 or len(simulation.items(found[1])) != len(simulation.items(found[0])):
        return "studies %s" % [(s.Label, len(simulation.items(s))) for s in found]
    if simulation.summary(found[1]):
        return "the copy has results"
    return None


ON_TOP = [{"face": {"normal": [0, 0, 1], "count": 1}}]
SIM = [
    {"tool": "new_design", "args": {"name": "AiWsCantilever"}},
    {
        "tool": "primitive",
        "save": "ws_beam",
        "args": {"kind": "box", "plane": "XY", "length": L, "width": W, "height": H},
    },
    {"tool": "create_study", "args": {"label": "Beam"}, "save": "ws_study"},
    {"tool": "set_study_material", "args": {"body": "$ws_beam", "material": "aluminium"}},
    {
        "tool": "study_setup",
        "args": {},
        "contains": ["0 constraints", "can still move"],
        "check": _check(_setup_rows([], held=False)),
    },
    {
        "tool": "study_probe",
        "args": {"points": [[50, 10, 5]]},
        "expect": "error",
        "contains": ["not been solved"],
    },
    {
        "tool": "add_constraint",
        "args": {"kind": "fixed", "on": [{"face": {"normal": [-1, 0, 0], "count": 1}}]},
    },
    {
        "tool": "add_load",
        "args": {
            "kind": "force",
            "on": [{"face": {"normal": [1, 0, 0], "count": 1}}],
            "magnitude": 100,
            "direction": "vector",
            "vector": [0, 0, -1],
        },
    },
    {
        "tool": "study_setup",
        "args": {"contact_tolerance": 0.5},
        "contains": ["every body is held"],
        "check": _check(_setup_rows([("constraint", "fixed"), ("load", "force")])),
    },
    {"tool": "study_mesh", "args": {}, "contains": ["meshed (took"], "check": _check(_mesh_counts)},
    {"tool": "study_mesh", "args": {"show": True}, "contains": ["meshed (took"]},
    {"tool": "solve_study", "args": {}, "contains": ["; took", "study_probe"]},
    {
        "tool": "study_probe",
        "args": {"points": [[L, 10, 5], [50, 10, 5]], "results": ["displacement", "von_mises"]},
        "contains": ["2 of 2 points on the part"],
        "check": _check(_probe_points),
    },
    {
        "tool": "study_probe",
        "args": {"points": [[200, 10, 5]]},
        "contains": ["0 of 1 point"],
        "check": _check(lambda d, r: None if not d["points"][0]["inside"] else "inside?"),
    },
    {"tool": "study_probe", "args": {"on": ON_TOP}, "check": _check(_probe_top)},
    {
        "tool": "study_probe",
        "args": {"section": {"axis": "x", "offset": 50}, "results": ["von_mises"]},
        "check": _check(_probe_section),
    },
    {
        "tool": "study_probe",
        "args": {"section": {"axis": "x", "offset": 500}},
        "check": _check(lambda d, r: None if "does not cut" in d["section"]["note"] else d),
    },
    {"tool": "study_probe", "args": {}, "expect": "error", "contains": ["give points"]},
    {
        "tool": "study_probe",
        "args": {"section": {"axis": "w"}},
        "expect": "error",
        "contains": ["section.axis must be x, y or z"],
    },
    {
        "tool": "study_results",
        "args": {"results": ["displacement"]},
        "check": _check(_results_tip(100.0)),
    },
    {
        "tool": "study_report",
        "args": {"path": "{tmp}/beam report", "title": "Beam check", "author": "AI", "target": 2},
        "contains": ["Written", "beam report.html", "target of 2 to 6"],
        "check": _report_file("beam report.html", ["Beam check", "Fixed 1", "Force 1"]),
    },
    {
        "tool": "study_report",
        "args": {"path": "{tmp}/beam report.html"},
        "expect": "error",
        "contains": ["already exists"],
    },
    {
        "tool": "study_report",
        "args": {"path": "{tmp}/r.html", "pictures": True},
        "expect": "error",
        "contains": ["pictures need the Fission 180 window"],
    },
    {
        "tool": "show_study_results",
        "args": {"result": "von_mises"},
        "expect": "error",
        "contains": ["needs the Fission 180 window"],
    },
    {"tool": "create_study", "args": {"copy_of": "Beam", "label": "Beam 200 N"}, "check": _copied},
    {
        "tool": "edit_study_item",
        "args": {"study": "Beam 200 N", "item": "Force 2", "magnitude": 200},
        "contains": ["Force 200 N"],
    },
    {
        "tool": "edit_study_item",
        "args": {"item": "Force 2", "size": 2},
        "expect": "error",
        "contains": ["no size"],
    },
    {
        "tool": "edit_study_item",
        "args": {"item": "Nothing"},
        "expect": "error",
        "contains": ["no constraint, load or mesh control 'Nothing'"],
    },
    {"tool": "solve_study", "args": {"study": "Beam 200 N"}, "contains": ["; took"]},
    {
        "tool": "study_results",
        "args": {"study": "Beam 200 N", "results": ["displacement"]},
        "check": _check(_results_tip(200.0)),
    },
    {
        "tool": "edit_study_item",
        "args": {"study": "Beam 200 N", "item": "Fixed 2", "suppressed": True},
        "contains": ["(suppressed)"],
    },
    {
        "tool": "study_results",
        "args": {"study": "Beam 200 N"},
        "contains": ["OUT OF DATE"],
    },
    {
        "tool": "edit_study_item",
        "args": {"study": "Beam 200 N", "item": "Force 2", "delete": True},
        "contains": ["Force 2 deleted"],
    },
    {"tool": "undo", "args": {}, "contains": ["AI: Delete Force 2"]},
    {
        "tool": "create_study",
        "args": {"copy_of": "Beam", "bodies": ["$ws_beam"]},
        "expect": "error",
        "contains": ["not both"],
    },
]


# -- MANUFACTURE: the golden plate (100 x 60 x 10, two 6 mm holes) on a 104 x 64 x 11 stock -------
def _no_gouge(data, run):
    gouges, left = data["gouges"], data["stock_left_on_model"]
    if gouges["cells"]:
        return "gouges on a safe program: %s" % gouges
    # (facing takes the stock down to the part's top: nothing is left on it but the grid's
    # rounding along the outline)
    if left["max_mm"] is None or left["max_mm"] > 0.05:
        return "stock left on the part: %s" % left
    return None


def _gouged(data, run):
    gouges = data["gouges"]
    if not gouges["cells"] or not _near(gouges["deepest_mm"], 1.0, 0.02):
        return "the facing 1 mm into the part: %s" % gouges
    # (the whole top of the part, but the holes and a cell along the outline: about 96 x 56)
    if not 4500 < gouges["area_mm2"] < 6000:
        return "gouged area %s" % gouges["area_mm2"]
    if not _near(gouges["at"][2], -2.0, 0.02, 0.01):
        return "the deepest gouge at %s, expected the top cut to Z -2" % gouges["at"]
    rows = [r for r in data["operations"] if r.get("deepest_gouge_mm")]
    if [r["name"] for r in rows] != ["Face2"]:
        return "the gouge is put on %s" % data["operations"]
    return None


def _sheet(name, words):
    def check(answer, run):
        data = _json(answer)
        if not data["file"].endswith(name) or not os.path.isfile(data["file"]):
            return "file %s" % data["file"]
        with open(data["file"], encoding="utf-8") as handle:
            text = handle.read()
        missing = [w for w in words if w not in text]
        if missing:
            return "the sheet lacks %s" % missing
        if len(data["operations"]) != 3 or len(data["tools"]) != 3:
            return "operations %s, tools %s" % (data["operations"], data["tools"])
        return None

    return check


def _local_tool(diameter, flutes=None):
    def check(data, run):
        tool = data["tool"]
        if data["library"] != "local:Local" or not _near(tool["diameter"], diameter, 1e-6):
            return "tool %s in %s" % (tool, data["library"])
        if flutes is not None and tool["flutes"] != flutes:
            return "flutes %s" % tool["flutes"]
        run.ids["local_tool"] = tool["id"]
        return None

    return check


def _stale_contour(answer, run):
    from fission180 import manufacture as cam

    states = {o.Label: cam.state(o, s) for s in cam.setups(run.doc()) for o in cam.operations(s)}
    if states.get("2D Contour1") != "stale":
        return "the contour is %s after its tool changed" % states
    return None


TOOL_6 = {"library": "sample:mm", "id": "sample-mm-flat-6"}
HOLE = {"kind": "cylinder", "plane": "XY", "diameter": 6, "height": 10, "operation": "cut"}
CAM = [
    {"tool": "new_design", "args": {"name": "AiWsPlate"}},
    {
        "tool": "primitive",
        "args": {"kind": "box", "plane": "XY", "length": 100, "width": 60, "height": 10},
    },
    {"tool": "primitive", "args": dict(HOLE, x=20, y=30)},
    {"tool": "primitive", "args": dict(HOLE, x=80, y=30)},
    {
        "tool": "cam_setup",
        "args": {
            "stock": {"mode": "relative", "offset_mode": "sides_top_bottom", "side": 2, "top": 1},
            "wcs": {"origin": "stock_point", "box_point": [-1, -1, 1]},
            "post": {"program": "1001", "comment": "plate"},
        },
    },
    {
        "tool": "cam_setup_sheet",
        "args": {"path": "{tmp}"},
        "expect": "error",
        "contains": ["no operation yet"],
    },
    {
        "tool": "cam_operation",
        "args": {"kind": "face", "tool": {"type": "flat", "diameter": 10, "number": 1}},
    },
    {
        "tool": "cam_operation",
        "args": {
            "kind": "contour2d",
            "faces": {"normal": [0, 0, -1], "count": 1},
            "tool": TOOL_6,
            "options": {"passes": {"multiple_depths": True, "stepdown": 4}},
        },
    },
    {
        "tool": "cam_operation",
        "args": {
            "kind": "drill",
            "faces": {"type": "cylinder", "radius": 3, "count": 2},
            "tool": {"type": "drill", "diameter": 6, "number": 3},
        },
    },
    {"tool": "cam_simulate", "args": {}, "contains": ["No gouge"], "check": _check(_no_gouge)},
    {
        "tool": "cam_setup_sheet",
        "args": {"path": "{tmp}"},
        "contains": ["Setup1 setup sheet.html", "3 operations", "3 tools"],
        "check": _sheet("Setup1 setup sheet.html", ["1001", "2D Contour", "Drill", "G54"]),
    },
    {
        "tool": "cam_setup_sheet",
        "args": {"path": "{tmp}/Setup1 setup sheet.html"},
        "expect": "error",
        "contains": ["already exists"],
    },
    {
        "tool": "cam_operation",
        "args": {
            "kind": "face",
            "tool": {"type": "flat", "diameter": 10, "number": 1},
            "options": {"heights": {"bottom": {"from": "model_top", "offset": -1}}},
        },
    },
    {"tool": "cam_simulate", "args": {}, "contains": ["GOUGES"], "check": _check(_gouged)},
    {"tool": "cam_delete", "args": {"target": "Face2"}},
    {
        "tool": "cam_tool_library",
        "args": {"action": "copy", "from_library": "sample:mm", "id": "sample-mm-flat-6"},
        "contains": ["copied into local:Local"],
        "check": _check(_local_tool(6.0)),
    },
    {
        "tool": "cam_tool_library",
        "args": {"action": "edit", "id": "$local_tool", "tool": {"diameter": 6.35, "flutes": 3}},
        "check": _check(_local_tool(6.35, 3)),
    },
    {
        "tool": "cam_tool_library",
        "args": {"action": "add", "tool": {"type": "ball", "diameter": 4}},
        "contains": ["added to local:Local"],
    },
    {
        "tool": "cam_tools",
        "args": {"library": "local:Local", "type": "ball"},
        "check": _check(lambda d, r: None if len(d["tools"]) == 1 else d),
    },
    {
        "tool": "cam_tool_library",
        "args": {"action": "delete", "id": "$local_tool"},
        "contains": ["deleted"],
    },
    {
        "tool": "cam_tool_library",
        "args": {"action": "add", "library": "sample:mm", "tool": {"type": "flat", "diameter": 2}},
        "expect": "error",
        "contains": ["cannot be changed"],
    },
    {
        "tool": "cam_tool_library",
        "args": {"action": "edit", "id": "sample-mm-flat-6", "tool": {"type": "ball"}},
        "expect": "error",
        "contains": ["not its type"],
    },
    {
        "tool": "cam_tool_library",
        "args": {
            "action": "edit",
            "library": "document",
            "id": "sample-mm-flat-6",
            "tool": {"cutting": {"cutting_feed": 600}},
        },
        "contains": ["needs regenerating"],
        "check": _stale_contour,
    },
    {"tool": "undo", "args": {}, "contains": ["AI: Tool library edit"]},
    {
        "tool": "cam_tool_library",
        "args": {"action": "new_library", "name": "Router"},
        "contains": ["local:Router"],
    },
    {
        "tool": "cam_tool_library",
        "args": {"action": "delete_library", "library": "local:Router"},
        "expect": "error",
        "contains": ["did not allow"],
    },
]


# -- ANIMATION: two components, a View action, an action moved and deleted ----------------------
def _view_of(view, at, looks):
    def check(data, run):
        if not _near(data["at"], at, 1e-9, 1e-9):
            return "at %s" % data["at"]
        if any(abs(a - b) > 1e-4 for a, b in zip(data["looks_from"], looks)):
            return "looks from %s, expected %s (%s)" % (data["looks_from"], looks, view)
        box = data["fits_box"]
        middle = [(box[i] + box[i + 3]) / 2.0 for i in range(3)]
        if any(abs(a - b) > 1e-3 for a, b in zip(data["looks_at"], middle)):
            return "looks at %s, not the middle of %s" % (data["looks_at"], box)
        return None

    return check


def _board_times(expected):
    """{action id: (start, end)} of Explode's actions."""

    def check(data, run):
        got = {a["id"]: (a["start"], a["end"]) for a in data["actions"]}
        for ident, (start, end) in expected.items():
            if ident not in got or not _near(got[ident][0], start, 1e-6, 1e-6):
                return "actions %s, expected %s" % (got, expected)
            if (end is None) != (got[ident][1] is None) or (
                end is not None and not _near(got[ident][1], end, 1e-6, 1e-6)
            ):
                return "actions %s, expected %s" % (got, expected)
        return None

    return check


ROOT3 = 3.0**-0.5
ANIM = [
    {"tool": "new_design", "args": {"name": "AiWsBodies"}},
    {
        "tool": "primitive",
        "args": {"kind": "box", "plane": "XY", "length": 60, "width": 40, "height": 10},
    },
    {"tool": "anim_view", "args": {"at": 1}, "expect": "error", "contains": ["no components"]},
    {"tool": "new_design", "args": {"name": "AiWsWheel"}},
    {"tool": "new_component", "args": {"label": "Base"}},
    {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [-30, -30, 30, 30]}]}},
    {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 10}},
    {"tool": "new_component", "args": {"label": "Wheel"}},
    {
        "tool": "create_sketch",
        "args": {"plane": "XY", "offset": 20, "geometry": [{"circle": [0, 0, 15]}]},
    },
    {"tool": "extrude", "args": {"profile": "Sketch2", "distance": 5}},
    {"tool": "anim_storyboard", "args": {"name": "Explode"}},
    {
        "tool": "anim_view",
        "args": {"at": 0, "view": "iso"},
        "contains": ["starts with this view"],
        "check": _check(_view_of("iso", 0, [ROOT3, -ROOT3, ROOT3])),
    },
    {"tool": "anim_explode", "args": {"at": 2}},
    {
        "tool": "anim_view",
        "args": {"at": 4, "view": "front", "zoom": 1.5},
        "contains": ["a View action", "from 0 to 4 s"],
        "check": _check(_view_of("front", 4, [0.0, -1.0, 0.0])),
    },
    {
        "tool": "anim_view",
        "args": {"at": 5, "direction": [0, 0, 1], "view": "top"},
        "expect": "error",
        "contains": ["not both"],
    },
    {
        "tool": "anim_storyboards",
        "args": {"storyboard": "Explode"},
        "check": _check(_board_times({1: (0.0, 2.0), 2: (0.0, 4.0)})),
    },
    {
        "tool": "anim_action",
        "args": {"actions": [2], "start": 2.5, "end": 6},
        "contains": ["it is 6 s long now"],
    },
    {"tool": "anim_action", "args": {"actions": [1, 2], "shift": 1}, "contains": ["7 s long"]},
    {
        "tool": "anim_storyboards",
        "args": {"storyboard": "Explode"},
        "check": _check(_board_times({1: (1.0, 3.0), 2: (3.5, 7.0)})),
    },
    {
        "tool": "anim_action",
        "args": {"actions": [9], "delete": True},
        "expect": "error",
        "contains": ["no action 9"],
    },
    {
        "tool": "anim_action",
        "args": {"actions": [2], "delete": True},
        "contains": ["1 action deleted", "3 s long"],
    },
    {"tool": "undo", "args": {}, "contains": ["AI: Delete animation action"]},
    {
        "tool": "anim_action",
        "args": {"actions": [2], "start": 4, "end": 4.01},
        "expect": "error",
        "contains": ["at least"],
    },
]


# -- SHEET METAL: a rule swapped on a body, an unused rule deleted --------------------------------
def _tray_rule(rule, thickness):
    def check(data, run):
        body = data["sheet_metal_bodies"][0]
        if body["rule"] != rule:
            return "the tray follows %s, expected %s" % (body["rule"], rule)
        from fission180 import bodies

        found = [b for b in bodies.solid_bodies(run.doc())]
        box = found[0].Shape.BoundBox
        # (the 50 x 30 floor of the rule's thickness, its 15 mm walls standing on it)
        if not _near(box.ZLength, 15.0 + thickness, 1e-6) or not _near(box.XLength, 50.0, 1e-6):
            return "the tray is %s for a %s mm rule" % (box, thickness)
        run.ids.setdefault("tray_volumes", {})[thickness] = found[0].Shape.Volume
        volumes = run.ids["tray_volumes"]
        if len(volumes) == 2 and not 1.7 < volumes[2.0] / volumes[1.0] < 2.0:
            return "2 mm sheet gives %s mm3, 1 mm sheet %s mm3" % (volumes[2.0], volumes[1.0])
        return None

    return check


SM = [
    {"tool": "new_design", "args": {"name": "AiWsTray"}},
    {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 50, 30]}]}},
    {"tool": "flange", "args": {"kind": "base", "profile": "Sketch1"}, "save": "tray"},
    {
        "tool": "flange",
        "args": {
            "kind": "edge",
            "height": 15,
            "edges": {"type": "line", "at": {"axis": "z", "value": "max"}, "count": 4},
        },
    },
    {
        "tool": "sheet_metal_rule",
        "args": {"rule": "Steel 2", "from": "Steel (mm)", "set": {"thickness": 2}},
    },
    {
        "tool": "sheet_metal_rule",
        "args": {"rule": "Steel 2", "bodies": ["$tray"]},
        "check": _check(_tray_rule("Steel 2", 2.0)),
    },
    {
        "tool": "sheet_metal_rule",
        "args": {"rule": "Steel 2", "delete": True},
        "expect": "error",
        "contains": ["is used by"],
    },
    {
        "tool": "sheet_metal_rule",
        "args": {"rule": "Steel (mm)", "bodies": ["$tray"]},
        "check": _check(_tray_rule("Steel (mm)", 1.0)),
    },
    {"tool": "sheet_metal_rule", "args": {"rule": "Steel 2", "delete": True}, "contains": ["Done"]},
    {
        "tool": "sheet_metal_rule",
        "args": {"rule": "Steel 2", "delete": True},
        "expect": "error",
        "contains": ["no rule 'Steel 2'"],
    },
    {
        "tool": "sheet_metal_rule",
        "args": {"rule": "Steel (mm)", "delete": True, "active": True},
        "expect": "error",
        "contains": ["delete takes only rule"],
    },
]


# -- UTILITIES > MAKE ------------------------------------------------------------------------------
def _print_file(name, fmt, triangles_at_least=12):
    def check(data, run):
        if not data["file"].endswith(name) or not os.path.isfile(data["file"]):
            return "file %s" % data["file"]
        if data["format"] != fmt or data["triangles"] < triangles_at_least:
            return "format %s, %s triangles" % (data["format"], data["triangles"])
        if not all(data["watertight"].values()):
            return "not watertight: %s" % data["watertight"]
        return None

    return check


def _everything(data, run):
    want = {"step", "stl", "3mf", "obj", "readme"}
    if set(data["files"]) != want:
        return "files %s, expected %s (no picture without the window)" % (
            sorted(data["files"]),
            sorted(want),
        )
    if any(row["bytes"] <= 0 for row in data["files"].values()):
        return "an empty file: %s" % data["files"]
    return None


MAKE = [
    {"tool": "new_design", "args": {"name": "AiWsPrint"}},
    {
        "tool": "print_part",
        "args": {"path": "{tmp}"},
        "expect": "error",
        "contains": ["no solid body"],
    },
    {
        "tool": "primitive",
        "args": {"kind": "box", "plane": "XY", "length": 30, "width": 20, "height": 10},
    },
    {
        "tool": "print_part",
        "args": {"path": "{tmp}"},
        "contains": ["Saved", "Body1.3mf"],
        "check": _check(_print_file(".3mf", "3MF")),
    },
    {
        "tool": "print_part",
        "args": {"path": "{tmp}/box.stl", "format": "STL (Binary)", "unit": "Inch"},
        "contains": ["in in)"],
        "check": _check(_print_file("box.stl", "STL (Binary)")),
    },
    {
        "tool": "print_part",
        "args": {"send_to": "slicer"},
        "expect": "error",
        "contains": ["needs the Fission 180 window"],
    },
    {
        "tool": "print_part",
        "args": {"send_to": "file"},
        "expect": "error",
        "contains": ["needs path"],
    },
    {"tool": "export_everything", "args": {}, "expect": "error", "contains": ["never saved"]},
    {
        "tool": "export_everything",
        "args": {"folder": "{tmp}/handover"},
        "contains": ["Exported 5 files", "no picture"],
        "check": _check(_everything),
    },
    {
        "tool": "export_everything",
        "args": {"folder": "{tmp}/handover"},
        "expect": "error",
        "contains": ["already exist"],
    },
]

SESSION = SIM + CAM + ANIM + SM + MAKE


def main():
    """These calls alone, with the runner's report."""
    import tempfile

    import FreeCAD as App

    from Fission180Tests.headless import runner

    out_dir = os.environ.get("FISSION180_HEADLESS_OUT") or App.getUserAppDataDir()
    os.makedirs(out_dir, exist_ok=True)
    run = runner.Run(tempfile.mkdtemp(prefix="fission180-headless-"))
    runner.run_session(run, SESSION, os.environ.get("FISSION180_HEADLESS_FILTER", ""))
    failed = [r for r in run.results if r["status"] != "pass"]
    for r in run.results:
        App.Console.PrintMessage(
            "[Fission 180] ai-workspaces %s %s (%.1f s) %s\n"
            % (r["status"].upper(), r["label"], r["seconds"], "; ".join(r["problems"])[:900])
        )
    with open(os.path.join(out_dir, "ai-workspaces-report.json"), "w", encoding="utf-8") as h:
        json.dump({"passed": not failed, "results": run.results}, h, indent=2)
    App.Console.PrintMessage(
        "[Fission 180] ai-workspaces summary: %d calls, %d failed\n"
        % (len(run.results), len(failed))
    )
    return not failed
