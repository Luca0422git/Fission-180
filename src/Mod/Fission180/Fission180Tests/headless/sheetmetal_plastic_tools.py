# SPDX-License-Identifier: LGPL-2.1-or-later
"""The headless calls of the SHEET METAL, PLASTIC and SURFACE > MODIFY AI tools (runner.py runs
SESSION after its own, so every tool of the catalogue is called): each tool builds a part whose
volume, area, faces or bounding box are known (the golden models of the same steps: their
numbers are quoted), edits it where a double-click would, and gets a refusal it can act on.
Parts sit apart from each other (shifted along X or Y) so no body gets in another's way.

The edge picks are given both ways the tools take them: selectors (turned into the middle of
each edge by the executor) and points [x, y, z] on the edges."""

import math
import os

TOP_Z_MIN = {"type": "plane", "normal": [0, 0, 1], "at": {"axis": "z", "value": "min"}, "count": 1}
# a 100 x 40 plate bent 90 degrees on the line x = 450 (Bend Line Center): the bend zone is
# the allowance pi / 2 (R + K T) = 2.262 mm wide, centred on the line; the plate up to it stays,
# the bend (inside radius 1, outside 2) turns, the rest stands up from its end
HALF_ZONE = math.pi / 4 * (1 + 0.44 * 1)
BENT_VOLUME = 2 * (50 - HALF_ZONE) * 40 + math.pi / 2 * (2**2 - 1**2) / 2 * 40
BENT_BOX = [400, 0, 0, 450 - HALF_ZONE + 2, 40, 2 + 50 - HALF_ZONE]


def _body(run, name):
    from fission180 import bodies

    obj = run.obj(name)
    if obj is None:
        return None
    return obj if bodies.is_body(obj) else bodies.body_of(obj)


def _shape(run, name):
    body = _body(run, name)
    return None if body is None or body.Shape.isNull() else body.Shape


def _near(got, expected, rel=1e-5, abs_tol=1e-3):
    return got is not None and abs(got - expected) <= max(abs_tol, rel * abs(expected))


def volume(name, expected, rel=1e-5):
    def check(answer, run):
        shape = _shape(run, name)
        got = shape.Volume if shape is not None else None
        return None if _near(got, expected, rel) else "volume %s, expected %.7g" % (got, expected)

    return check


def area(name, expected, faces=None, rel=1e-5):
    """A surface body's area (and number of faces)."""

    def check(answer, run):
        shape = _shape(run, name)
        if shape is None:
            return "no shape for %s" % name
        if not _near(shape.Area, expected, rel):
            return "area %.7g, expected %.7g" % (shape.Area, expected)
        if faces is not None and len(shape.Faces) != faces:
            return "%d faces, expected %d" % (len(shape.Faces), faces)
        if shape.Solids:
            return "a surface body with a solid: %d solids" % len(shape.Solids)
        return None

    return check


def bbox(name, expected, tol=1e-3):
    def check(answer, run):
        shape = _shape(run, name)
        if shape is None:
            return "no shape for %s" % name
        b = shape.BoundBox
        got = [b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax]
        if any(abs(g - e) > tol for g, e in zip(got, expected)):
            return "bounding box %s, expected %s" % ([round(v, 4) for v in got], expected)
        return None

    return check


def faces(name, expected):
    def check(answer, run):
        shape = _shape(run, name)
        got = len(shape.Faces) if shape is not None else None
        return None if got == expected else "%s faces, expected %d" % (got, expected)

    return check


def remember_volume(name, key):
    def check(answer, run):
        shape = _shape(run, name)
        if shape is None:
            return "no shape for %s" % name
        run.ids[key] = shape.Volume
        return None

    return check


def volume_change(name, key, expected, tol=1e-3):
    """The body's volume changed by `expected` since remember_volume(key)."""

    def check(answer, run):
        shape = _shape(run, name)
        before = run.ids.get(key)
        if shape is None or before is None:
            return "nothing to compare (%s)" % key
        got = shape.Volume - before
        if abs(got - expected) > tol:
            return "the volume changed by %.6g, expected %.6g" % (got, expected)
        return None

    return check


def grows(name, key):
    def check(answer, run):
        shape = _shape(run, name)
        before = run.ids.get(key)
        if shape is None or before is None or not shape.Volume > before + 1e-6:
            return "the volume did not grow: %s -> %s" % (before, shape and shape.Volume)
        return None

    return check


def all_of(*checks):
    def check(answer, run):
        for fn in checks:
            problem = fn(answer, run)
            if problem:
                return problem
        return None

    return check


def json_of(answer):
    import json

    text = answer["text"]
    start = text.find("{")
    return json.loads(text[start:]) if start >= 0 else None


def data(fn):
    def check(answer, run):
        got = json_of(answer)
        if got is None:
            return "no JSON in the answer"
        return fn(got, run)

    return check


def file_written(name, contains=None):
    def check(answer, run):
        path = run.path(name)
        if not os.path.isfile(path) or os.path.getsize(path) < 10:
            return "%s was not written" % path
        if contains is not None:
            with open(path, encoding="ascii", errors="replace") as handle:
                text = handle.read()
            missing = [c for c in contains if c not in text]
            if missing:
                return "%s lacks %s" % (name, missing)
        return None

    return check


def unchanged_design(key):
    """A read-only tool left the design as it was: no undo step, no object, no change."""

    def remember(answer, run):
        doc = run.doc()
        run.ids[key] = (len(doc.UndoNames), len(doc.Objects), doc.isTouched())
        return None

    def compare(answer, run):
        doc = run.doc()
        now = (len(doc.UndoNames), len(doc.Objects), doc.isTouched())
        if now != run.ids.get(key):
            return "the design changed: %s -> %s" % (run.ids.get(key), now)
        return None

    return remember, compare


_REMEMBER_ADVICE, _SAME_AFTER_ADVICE = unchanged_design("advice_state")


# -- the flat pattern's answer ---------------------------------------------------------------------
def _tray_flat(d, run):
    if len(d["bends"]) != 4 or any(abs(b["angle_deg"] - 90) > 1e-6 for b in d["bends"]):
        return "bends %s" % d["bends"]
    if abs(d["thickness_mm"] - 1) > 1e-9 or abs(d["k_factor"] - 0.44) > 1e-9:
        return "thickness %s, K %s" % (d["thickness_mm"], d["k_factor"])
    folded = _shape(run, "sm_tray").Volume
    if not 0.97 * folded < d["volume_mm3"] < folded:
        return "the flat holds %s mm3, the folded part %s" % (d["volume_mm3"], folded)
    # each wall: 12 mm up from the floor (Inner datum: 12 - R tan(45) = 11 straight) plus the
    # bend's 90 degrees at R + K T = 1.44: the flat is the floor plus two of them each way
    reach = 11.0 + math.pi / 2 * 1.44
    want = [50 - 2 * 2 + 2 * reach, 30 - 2 * 2 + 2 * reach]
    if any(abs(g - w) > 1e-3 for g, w in zip(d["flat_size_mm"], want)):
        return "flat %s, expected %s" % (d["flat_size_mm"], [round(w, 4) for w in want])
    return None


def _bent_flat(d, run):
    if d["flat_size_mm"] != [100.0, 40.0] or len(d["bends"]) != 1:
        return "flat %s, bends %s" % (d["flat_size_mm"], d["bends"])
    return None


def _rule(field, value):
    def check(d, run):
        got = d["rule"].get(field)
        if str(got) == str(value):
            return None
        return "rule %s is %r, expected %r" % (field, got, value)

    return check


def _advice(d, run):
    if not d["counts"].get("draft") or not d["issues"]:
        return "no draft issue found on the cylinder: %s" % d
    issue = d["issues"][0]
    if issue["check"] != "Draft" or not issue.get("ref") or not issue.get("center_mm"):
        return "the issue %s" % issue
    return None


def _edit_reads(field, value):
    def check(d, run):
        definition = d.get("definition") or {}
        options = definition.get("options", definition)
        got = options.get(field)
        return None if got == value else "get_step shows %s = %r: %s" % (field, got, definition)

    return check


def _new_body_with_volume(answer, run):
    """The fastener made a body of screws (two simple screws: two solids)."""
    from fission180 import bodies

    before = run.ids.get("pl_before", ())
    made = [b for b in bodies.solid_bodies(run.doc()) if b.Name not in before]
    if len(made) != 1 or len(made[0].Shape.Solids) != 2 or made[0].Shape.Volume < 1:
        return "no body of two screws made: %s" % [(b.Label, b.Shape.Volume) for b in made]
    return None


def mark_undo(answer, run):
    """Remember how many undo steps the design has (one_undo_step checks the next call)."""
    run.ids["undo_mark"] = len(run.doc().UndoNames)
    return None


def one_undo_step(title):
    """The call added exactly one undo step, named title."""

    def check(answer, run):
        names = list(run.doc().UndoNames)
        if len(names) != run.ids.get("undo_mark", -1) + 1 or not names or names[0] != title:
            return "undo steps %s (before: %s)" % (names[:3], run.ids.get("undo_mark"))
        return None

    return check


def label(name, expected):
    def check(answer, run):
        body = _body(run, name)
        got = body.Label if body is not None else None
        return None if got == expected else "the body is called %r, expected %r" % (got, expected)

    return check


def _bodies_now(answer, run):
    from fission180 import bodies

    run.ids["pl_before"] = [b.Name for b in bodies.solid_bodies(run.doc())]
    return None


SESSION = [
    # == SHEET METAL ===============================================================================
    {"tool": "new_design", "args": {"name": "SheetMetalTools"}, "check": mark_undo},
    {
        "tool": "sheet_metal_rule",
        "args": {"rule": "Thin", "from": "Steel (mm)", "set": {"thickness": 0.5}},
        "contains": ["Done", "Sheet metal rule Thin"],
        "check": all_of(
            data(
                lambda d, r: _rule("thickness", "0.5")(d, r)
                or (None if d["rule"]["in_mm"]["bend_radius"] == 0.5 else "radius %s" % d["rule"])
                or (None if d["active_rule"] == "Steel (mm)" else "active %s" % d["active_rule"])
            ),
            one_undo_step("AI: Sheet metal rule Thin"),
        ),
    },
    {
        "tool": "sheet_metal_rule",
        "args": {"rule": "Thin", "set": {"k_factor": 2}},
        "expect": "error",
        "contains": ["k_factor must be between 0 and 1"],
    },
    # a 50 x 30 plate (golden sheetmetal_base_flange_rect: 1500 mm3, 6 faces), then walls on its
    # four top edges picked with a selector (golden sheetmetal_edge_flange_tray: 2893.718336)
    {
        "tool": "create_sketch",
        "save": "sm_s_plate",
        "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 50, 30]}]},
        "check": mark_undo,
    },
    {
        "tool": "flange",
        "save": "sm_plate",
        "args": {"kind": "base", "profile": "$sm_s_plate"},
        "contains": ["Done: AI: Flange (base)"],
        "check": all_of(volume("sm_plate", 1500.0), bbox("sm_plate", [0, 0, 0, 50, 30, 1]),
                        faces("sm_plate", 6), one_undo_step("AI: Flange (base)")),
    },
    {
        "tool": "flange",
        "args": {"kind": "edge", "edges": {"type": "line", "at": {"axis": "z", "value": "min"},
                                           "count": 9}, "height": 10},
        "expect": "error",
        "contains": ["Not done"],
    },
    {
        "tool": "flange",
        "save": "sm_tray",
        "args": {
            "kind": "edge",
            "edges": {"type": "line", "at": {"axis": "z", "value": "max"}, "count": 4},
            "height": 10,
        },
        "check": all_of(volume("sm_tray", 2893.718336), bbox("sm_tray", [0, 0, 0, 50, 30, 11])),
    },
    {"tool": "get_step", "args": {"step": "$sm_tray"}, "check": data(_edit_reads("height", 10))},
    {"tool": "get_design", "args": {}, "check": mark_undo},
    {
        "tool": "edit_step",
        "args": {"step": "$sm_tray", "set": {"height": 12}},
        "contains": ["Done"],
        "check": all_of(bbox("sm_tray", [0, 0, 0, 50, 30, 13]), one_undo_step("AI: Edit Flange2"),
                        mark_undo),
    },
    {
        "tool": "edit_step",
        "args": {"step": "$sm_tray", "set": {"heigth": 12}},
        "expect": "error",
        "contains": ["no option 'heigth'", "height"],
    },
    {
        "tool": "flat_pattern",
        "save": "sm_flat",
        "args": {"face": TOP_Z_MIN},
        "contains": ["Done: AI: Create flat pattern", "4 bends"],
        "check": all_of(data(_tray_flat), one_undo_step("AI: Create flat pattern")),
    },
    {
        "tool": "export_flat_pattern",
        "args": {"path": "{tmp}/tray-flat.dxf"},
        "contains": ["Exported", "4 bends"],
        "check": file_written("tray-flat.dxf", ["SECTION", "LINE"]),
    },
    {
        "tool": "export_flat_pattern",
        "args": {"path": "{tmp}/tray-flat"},
        "expect": "error",
        "contains": ["already exists"],
    },
    # a hem on the top edge of a 20 mm wall (golden sheetmetal_smm_hem_on_flange, moved 100 mm
    # along X: 2196.3717 mm3, 14 faces), the edge picked with a selector, then edited
    {"tool": "new_component", "args": {"label": "Hemmed"}},
    {
        "tool": "create_sketch",
        "save": "sm_s_hem",
        "args": {"plane": "XY", "geometry": [{"rect": [100, 0, 150, 30]}]},
    },
    {"tool": "flange", "save": "sm_hem_plate", "args": {"kind": "base", "profile": "$sm_s_hem"}},
    {
        "tool": "flange",
        "args": {"kind": "edge", "edges": [[150, 15, 1]], "height": 20},
        "check": volume("sm_hem_plate", 1500 - 30 * 2 + 30 * 20.0, 0.05),
    },
    {
        "tool": "hem",
        "save": "sm_hem",
        "args": {
            "edges": {
                "type": "line",
                "parallel": [0, 1, 0],
                "at": [{"axis": "z", "value": "max"}, {"axis": "x", "value": "max"}],
                "count": 1,
            },
            "type": "open",
        },
        "check": all_of(volume("sm_hem", 2196.3717), faces("sm_hem", 14),
                        bbox("sm_hem", [100, 0, 0, 151.5, 30, 21])),
    },
    {"tool": "get_step", "args": {"step": "$sm_hem"}, "check": data(_edit_reads("type", "open"))},
    {"tool": "edit_step", "args": {"step": "$sm_hem", "set": {"type": "rolled"}}},
    {"tool": "get_step", "args": {"step": "$sm_hem"}, "check": data(_edit_reads("type", "rolled"))},
    {
        "tool": "hem",
        "args": {"edges": [[125, 15, 7]]},
        "expect": "error",
        "contains": ["no edge through"],
    },
    # the sheet metal Fillet (two radius sets, points) and Chamfer (a selector) on a plate's
    # corners (golden sheetmetal_smm_fillet_chamfer moved 200 mm along X: 5957.17477 mm3)
    {"tool": "new_component", "args": {"label": "Rounded"}},
    {
        "tool": "create_sketch",
        "save": "sm_s_round",
        "args": {"plane": "XY", "geometry": [{"rect": [200, 0, 300, 60]}]},
    },
    {"tool": "flange", "save": "sm_round", "args": {"kind": "base", "profile": "$sm_s_round"}},
    {
        "tool": "sheet_metal_fillet",
        "args": {"sets": [{"edges": [[200, 0, 0.5]], "radius": 5},
                          {"edges": [[300, 0, 0.5]], "radius": 10}]},
        "check": volume("sm_round", 6000 - (25 - 25 * math.pi / 4) - (100 - 100 * math.pi / 4)),
    },
    {
        "tool": "sheet_metal_chamfer",
        "args": {
            "edges": {"type": "line", "parallel": [0, 0, 1], "at": {"axis": "y", "value": "max"},
                      "count": 2},
            "distance": 4,
        },
        "check": volume("sm_round", 5957.17477),
    },
    {
        "tool": "sheet_metal_fillet",
        "args": {"edges": {"type": "line", "parallel": [1, 0, 0], "count": 2}, "radius": 1},
        "expect": "error",
        "contains": ["Not done"],
    },
    # Bend a plate 90 degrees along a sketch line, then lay it flat again (golden
    # sm_flat_bend_roundtrip: the 100 x 40 plate it was)
    {"tool": "new_component", "args": {"label": "Bent"}},
    {
        "tool": "create_sketch",
        "save": "sm_s_bend",
        "args": {"plane": "XY", "geometry": [{"rect": [400, 0, 500, 40]}]},
    },
    {"tool": "flange", "save": "sm_bent", "args": {"kind": "base", "profile": "$sm_s_bend"}},
    {
        "tool": "create_sketch",
        "save": "sm_s_line",
        "args": {"plane": "XY", "offset": 1, "geometry": [{"line": [450, -5, 450, 45]}]},
    },
    {
        "tool": "bend",
        "save": "sm_bend",
        "args": {"lines": "$sm_s_line", "stationary": [410, 20, 1], "angle": 90},
        "contains": ["Done: AI: Bend 90 deg"],
        "check": all_of(volume("sm_bend", BENT_VOLUME), bbox("sm_bend", BENT_BOX)),
    },
    {
        "tool": "flat_pattern",
        "args": {"face": TOP_Z_MIN, "body": "$sm_bent"},
        "check": data(_bent_flat),
    },
    {
        "tool": "flat_pattern",
        "args": {"face": TOP_Z_MIN, "body": "$sm_bent"},
        "expect": "error",
        "contains": ["already has a flat pattern"],
    },
    # Join by Bend (golden sheetmetal_smm_join_bend_overlap moved 100 mm along Y: 3887.12389 mm3)
    {"tool": "new_component", "args": {"label": "Joined"}},
    {
        "tool": "create_sketch",
        "save": "sm_s_j1",
        "args": {"plane": "XY", "geometry": [{"rect": [0, 100, 50, 140]}]},
    },
    {"tool": "flange", "save": "sm_j1", "args": {"kind": "base", "profile": "$sm_s_j1"}},
    {
        "tool": "create_sketch",
        "save": "sm_s_j2",
        "args": {"plane": "YZ", "offset": 60, "geometry": [{"rect": [120, 5, 160, 45]}]},
    },
    {
        "tool": "flange",
        "save": "sm_j2",
        "args": {"kind": "base", "profile": "$sm_s_j2", "name": "Standing plate"},
        "check": label("sm_j2", "Standing plate"),
    },
    {
        "tool": "join_by_bend",
        "args": {"first": [60, 140, 5], "other": "$sm_j1",
                 "second": {"type": "line", "parallel": [0, 1, 0]}},
        "expect": "error",
        "contains": ["second must pick one edge; its selector picked 4"],
    },
    {
        "tool": "join_by_bend",
        "save": "sm_join",
        "args": {"first": [60, 140, 5], "other": "$sm_j1", "second": [50, 120, 1]},
        "check": all_of(volume("sm_join", 3887.12389),
                        bbox("sm_join", [0, 100, 0, 61, 160, 45])),
    },
    # Corner Closure (golden sheetmetal_smm_corner_closure moved 200 mm along Y: 9041.4421)
    {"tool": "new_component", "args": {"label": "Closed corner"}},
    {
        "tool": "create_sketch",
        "save": "sm_s_cc",
        "args": {
            "plane": "XY",
            "geometry": [{"polyline": [[0, 200], [100, 200], [100, 255], [95, 255], [95, 260],
                                       [0, 260]]}],
        },
    },
    {"tool": "flange", "save": "sm_cc", "args": {"kind": "base", "profile": "$sm_s_cc"}},
    {"tool": "flange", "args": {"kind": "edge", "edges": [[100, 220, 1]], "height": 20}},
    {"tool": "flange", "args": {"kind": "edge", "edges": [[50, 260, 1]], "height": 20}},
    {
        "tool": "corner_closure",
        "save": "sm_closure",
        "args": {"dominant": [100, 255, 12], "submissive": [95, 260, 12], "gap": 1},
        "check": all_of(volume("sm_closure", 9041.4421), faces("sm_closure", 24)),
    },
    {
        "tool": "edit_step",
        "args": {"step": "$sm_closure", "set": {"gap": 2}},
        "check": lambda a, r: None
        if _shape(r, "sm_closure").Volume < 9041.4421 - 1e-3
        else "a wider gap kept %s" % _shape(r, "sm_closure").Volume,
    },
    # Lofted Flange, Brake Form (golden sheetmetal_smm_lofted_brake moved 300 mm along X)
    {"tool": "new_component", "args": {"label": "Hopper"}},
    {
        "tool": "create_sketch",
        "save": "sm_s_l1",
        "args": {"plane": "XY", "geometry": [{"rect": [280, -20, 320, 20]}]},
    },
    {
        "tool": "create_sketch",
        "save": "sm_s_l2",
        "args": {"plane": "XY", "offset": 30, "geometry": [{"circle": [300, 0, 15]}]},
    },
    {
        "tool": "lofted_flange",
        "save": "sm_loft",
        "args": {"profile1": "$sm_s_l1", "profile2": "$sm_s_l2", "rule": "Steel (mm)",
                 "value": 0.5, "name": "Square to round"},
        "check": all_of(volume("sm_loft", 3867.852), faces("sm_loft", 38),
                        label("sm_loft", "Square to round")),
    },
    # Convert to Sheet Metal, Unfold, a cut across the flat bend, Refold (golden
    # sm_flat_unfold_cut_refold moved 600 mm along X: 1956.7072 mm3)
    {"tool": "new_component", "args": {"label": "Bracket"}},
    {
        "tool": "create_sketch",
        "save": "sm_s_l",
        "args": {"plane": "XZ", "geometry": [{"polyline": [[600, 0], [650, 0], [650, 50],
                                                           [649, 50], [649, 1], [600, 1]]}]},
    },
    {"tool": "extrude", "save": "sm_l", "args": {"profile": "$sm_s_l", "distance": 20}},
    {
        "tool": "fillet",
        "args": {"edges": {"type": "line", "parallel": [0, 1, 0],
                           "at": [{"axis": "x", "value": 650}, {"axis": "z", "value": 0}],
                           "count": 1}, "radius": 2},
    },
    {
        "tool": "fillet",
        "args": {"edges": {"type": "line", "parallel": [0, 1, 0],
                           "at": [{"axis": "x", "value": 649}, {"axis": "z", "value": 1}],
                           "count": 1}, "radius": 1},
    },
    {
        "tool": "convert_to_sheet_metal",
        "args": {"face": TOP_Z_MIN},
        "contains": ["Done: AI: Convert to sheet metal"],
    },
    {"tool": "unfold", "args": {"face": TOP_Z_MIN}, "expect": "error",
     "contains": ["give bends"]},
    {"tool": "unfold", "save": "sm_unfold", "args": {"face": TOP_Z_MIN, "all": True}},
    {
        "tool": "create_sketch",
        "save": "sm_s_slot",
        "args": {"plane": "XY", "geometry": [{"rect": [648.630973, -15, 649.630973, -5]}]},
    },
    {
        "tool": "extrude",
        "args": {"profile": "$sm_s_slot", "distance": 5, "operation": "cut",
                 "direction": "symmetric"},
    },
    {
        "tool": "refold",
        "save": "sm_refold",
        "args": {"unfold": "$sm_unfold"},
        "check": all_of(
            volume("sm_refold", 1956.7072), bbox("sm_refold", [600, -20, 0, 650, 0, 50])
        ),
    },
    # Rip one round corner out of a converted tube: the quarter ring of the bend (inside
    # radius 1, outside 2, 20 high) goes
    {"tool": "new_component", "args": {"label": "Tube"}},
    {
        "tool": "create_sketch",
        "save": "sm_s_tube",
        "args": {"plane": "XY", "geometry": [{"rect": [800, 0, 840, 30]}]},
    },
    {"tool": "extrude", "save": "sm_tube", "args": {"profile": "$sm_s_tube", "distance": 20}},
    {"tool": "fillet", "args": {"edges": {"type": "line", "parallel": [0, 0, 1], "count": 4},
                                "radius": 2}},
    {
        "tool": "shell",
        "args": {"faces": {"any_of": [{"type": "plane", "normal": [0, 0, 1], "count": 1},
                                      {"type": "plane", "normal": [0, 0, -1], "count": 1}]},
                 "thickness": 1},
    },
    {
        "tool": "convert_to_sheet_metal",
        "args": {"face": {"type": "plane", "normal": [0, -1, 0],
                          "at": {"axis": "y", "value": "min"}, "count": 1}, "rule": "Steel (mm)"},
        "check": remember_volume("sm_tube", "tube_volume"),
    },
    {
        "tool": "rip",
        "args": {"type": "face", "edge": {"all": True}},
        "expect": "error",
        "contains": ["type face needs face", "edge is not for type face"],
    },
    {
        "tool": "rip",
        "args": {
            "type": "face",
            "face": {"type": "cylinder", "radius": 2,
                     "at": [{"axis": "x", "value": "max"}, {"axis": "y", "value": "max"}],
                     "count": 1},
        },
        "check": volume_change("sm_tube", "tube_volume", -math.pi / 4 * (4 - 1) * 20),
    },
    # == PLASTIC ===================================================================================
    {"tool": "new_design", "args": {"name": "PlasticTools"}},
    {
        "tool": "plastic_rule",
        "args": {"rule": "ABS 2 mm", "set": {"clearance": 0.1}},
        "contains": ["Done: AI: Plastic rule ABS 2 mm"],
        "check": data(
            lambda d, r: _rule("thickness", "2.0")(d, r) or _rule("clearance", "0.1")(d, r)
        ),
    },
    {
        "tool": "plastic_rule",
        "args": {"rule": "No such rule"},
        "expect": "error",
        "contains": ["no plastic rule named 'No such rule'"],
    },
    # bosses joining a box and its lid (golden plastic_boss_enclosure: the box 13197.936411 mm3,
    # the lid 8481.881309), then their screws
    {
        "tool": "create_sketch",
        "save": "pl_s_box",
        "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 60, 40]}]},
    },
    {"tool": "extrude", "save": "pl_box", "args": {"profile": "$pl_s_box", "distance": 20}},
    {"tool": "shell", "args": {"faces": {"normal": [0, 0, 1], "count": 1}, "thickness": 2}},
    {
        "tool": "create_sketch",
        "save": "pl_s_lid",
        "args": {"plane": "XY", "offset": 20, "geometry": [{"rect": [0, 0, 60, 40]}]},
    },
    {
        "tool": "extrude",
        "save": "pl_lid",
        "args": {"profile": "$pl_s_lid", "distance": 10, "operation": "new_body"},
    },
    {"tool": "shell", "args": {"faces": {"normal": [0, 0, -1], "count": 1}, "thickness": 2}},
    {
        "tool": "boss",
        "save": "pl_boss",
        "args": {
            "points": [[10, 10], [50, 30]],
            "plane": "XY",
            "offset": 20,
            "side1": {"draft": 0, "step_draft": 0, "root_radius": 0},
            "side2": {"draft": 0, "step_draft": 0, "root_radius": 0},
            "name": "Corner bosses",
        },
        "check": all_of(volume("pl_box", 13197.936411), volume("pl_lid", 8481.881309),
                        lambda a, r: None if r.obj("Corner bosses sketch") is not None
                        else "the boss's sketch was not named"),
    },
    {
        "tool": "boss",
        "args": {"points": [[10, 10]], "side1": {"hole": "drilled"}},
        "expect": "error",
        "contains": ["side1.hole must be one of simple, counterbore, countersink"],
    },
    {"tool": "get_design", "args": {}, "check": _bodies_now},
    {
        "tool": "boss_fastener",
        "args": {"boss": "$pl_boss", "head": "pan"},
        "contains": ["Done: AI: Boss fastener"],
        "check": _new_body_with_volume,
    },
    # a Rest under the floor of a closed hollow box (golden plastic_rest_closed_box moved 100 mm
    # along X: 16176 mm3)
    {
        "tool": "create_sketch",
        "save": "pl_s_rbox",
        "args": {"plane": "XY", "geometry": [{"rect": [100, 0, 160, 40]}]},
    },
    {
        "tool": "extrude",
        "save": "pl_rbox",
        "args": {"profile": "$pl_s_rbox", "distance": 20, "operation": "new_body"},
    },
    {
        "tool": "create_sketch",
        "save": "pl_s_cavity",
        "args": {"plane": "XY", "offset": 2, "geometry": [{"rect": [102, 2, 158, 38]}]},
    },
    {
        "tool": "extrude",
        "args": {"profile": "$pl_s_cavity", "distance": 16, "operation": "cut"},
    },
    {
        "tool": "rest",
        "args": {"rect": [120, 10, 140, 30], "plane": "XY", "offset": -3, "thickness": 2,
                 "draft": 0},
        "check": all_of(volume("pl_rbox", 16176.0), bbox("pl_rbox", [100, 0, -3, 160, 40, 20])),
    },
    # a Snap Fit (golden plastic2_snap_parallel moved 200 mm along X: the hook body 4956.80385,
    # the box with its groove 11690.176)
    {
        "tool": "create_sketch",
        "save": "pl_s_sbox",
        "args": {"plane": "XY", "geometry": [{"rect": [200, 0, 260, 40]}]},
    },
    {
        "tool": "extrude",
        "save": "pl_sbox",
        "args": {"profile": "$pl_s_sbox", "distance": 20, "operation": "new_body"},
    },
    {"tool": "shell", "args": {"faces": {"normal": [0, 0, 1], "count": 1}, "thickness": 2}},
    {
        "tool": "create_sketch",
        "save": "pl_s_slid",
        "args": {"plane": "XY", "offset": 20, "geometry": [{"rect": [200, 0, 260, 40]}]},
    },
    {
        "tool": "extrude",
        "save": "pl_slid",
        "args": {"profile": "$pl_s_slid", "distance": 2, "operation": "new_body"},
    },
    {
        "tool": "snap_fit",
        "save": "pl_snap",
        "args": {
            "points": [[258, 20]],
            "plane": "XY",
            "offset": 20,
            "fillet": 0,
            "draft": 0,
            "thickness": 2,
            "tip_thickness": 2,
            "clearance": 0.1,
            "loop_thickness": 2,
            "length": 12,
            "width": 6,
            "catch_depth": 1,
            "catch_length": 3,
        },
        "check": all_of(volume("pl_slid", 4956.803847577294), volume("pl_sbox", 11690.176),
                        bbox("pl_slid", [200, 0, 8, 260, 40, 22])),
    },
    {
        "tool": "edit_step",
        "args": {"step": "$pl_snap", "set": {"length": 14}},
        "check": bbox("pl_slid", [200, 0, 6, 260, 40, 22]),
    },
    {"tool": "get_step", "args": {"step": "$pl_snap"}, "check": data(_edit_reads("length", 14.0))},
    # a Lip on the round rim of a cylinder (golden plastic2_lip_round_rim moved 300 mm along X:
    # 2057.7431881)
    {
        "tool": "primitive",
        "save": "pl_cyl",
        "args": {"kind": "cylinder", "plane": "XY", "x": 300, "y": 0, "diameter": 16,
                 "height": 10, "operation": "new_body"},
    },
    {
        "tool": "lip",
        "save": "pl_lip",
        "args": {
            "edges": {"type": "circle", "at": {"axis": "z", "value": "max"}, "count": 1},
            "type": "lip",
            "lip_width": 1,
            "lip_height": 1,
            "clearance": 0.1,
            "clearance_height": 0.1,
            "inner_draft": 0,
            "outer_draft": 0,
        },
        "check": all_of(volume("pl_lip", 2057.7431881013144),
                        bbox("pl_lip", [292, -8, 0, 308, 8, 11])),
    },
    {
        "tool": "edit_step",
        "args": {"step": "$pl_lip", "set": {"lip_height": 2}},
        "check": bbox("pl_lip", [292, -8, 0, 308, 8, 12]),
    },
    # Design Advice reads the design and changes nothing: the cylinder's straight side has no
    # draft along Z
    {"tool": "get_design", "args": {}, "check": _REMEMBER_ADVICE},
    {
        "tool": "design_advice",
        "args": {"bodies": ["$pl_cyl"], "checks": ["draft"], "pull": [0, 0, 1]},
        "check": all_of(data(_advice), _SAME_AFTER_ADVICE),
    },
    {
        "tool": "design_advice",
        "args": {"bodies": ["$pl_rbox"], "pull": [0, 0, 0]},
        "expect": "error",
        "contains": ["pull must not be [0, 0, 0]"],
    },
    # == SURFACE > MODIFY =========================================================================
    # an open box of surfaces (golden surface4_*: four 10 high walls round a 30 x 20 floor, area
    # 1600, 5 faces): Press Pull of its floor (-5: area 2100), edited to +3 (area 1300)
    {"tool": "new_design", "args": {"name": "SurfaceTools"}},
    {
        "tool": "create_curve_sketch",
        "save": "sf_s_box",
        "args": {"plane": "XY", "curves": [{"polyline": [[0, 0], [30, 0], [30, 20], [0, 20],
                                                         [0, 0]]}]},
    },
    {
        "tool": "surface",
        "save": "sf_walls",
        "args": {"kind": "extrude", "refs": [{"sketch": "$sf_s_box", "at": [15, 0]}],
                 "options": {"distance": 10}},
    },
    {
        "tool": "surface",
        "save": "sf_floor",
        "args": {"kind": "patch", "refs": [{"sketch": "$sf_s_box", "at": [15, 0]}]},
    },
    {
        "tool": "surface",
        "save": "sf_box",
        "args": {"kind": "stitch", "refs": [{"step": "$sf_walls"}, {"step": "$sf_floor"}]},
        "check": area("sf_box", 1600.0, 5),
    },
    {
        "tool": "surface_modify",
        "args": {"kind": "press_pull", "faces": {"normal": [0, 0, 1], "count": 1}},
        "expect": "error",
        "contains": ["press_pull needs distance"],
        "check": None,
    },
    {"tool": "get_design", "args": {}, "check": mark_undo},
    {
        "tool": "surface_modify",
        "save": "sf_pp",
        "args": {"kind": "press_pull", "body": "$sf_box",
                 "faces": {"normal": [0, 0, 1], "count": 1}, "distance": -5},
        "contains": ["Done: AI: Surface press pull"],
        "check": all_of(area("sf_box", 2100.0, 5), bbox("sf_box", [0, 0, -5, 30, 20, 10]),
                        one_undo_step("AI: Surface press pull")),
    },
    {
        "tool": "edit_step",
        "args": {"step": "$sf_pp", "set": {"distance": 3}},
        "check": all_of(area("sf_box", 1300.0, 5), bbox("sf_box", [0, 0, 3, 30, 20, 10])),
    },
    {"tool": "get_step", "args": {"step": "$sf_pp"}, "check": data(_edit_reads("distance", 3.0))},
    # a second box 50 mm along X: a variable Fillet of one corner (golden surface4_fillet_variable:
    # 1591.448088), a Chamfer of another (two distances 2 and 4: 19.2786 less, golden
    # surface4_chamfer_delete) and the floor deleted (the floor's area goes, one face less)
    {
        "tool": "create_curve_sketch",
        "save": "sf_s_box2",
        "args": {"plane": "XY", "curves": [{"polyline": [[50, 0], [80, 0], [80, 20], [50, 20],
                                                         [50, 0]]}]},
    },
    {
        "tool": "surface",
        "save": "sf_walls2",
        "args": {"kind": "extrude", "refs": [{"sketch": "$sf_s_box2", "at": [65, 0]}],
                 "options": {"distance": 10}},
    },
    {
        "tool": "surface",
        "save": "sf_floor2",
        "args": {"kind": "patch", "refs": [{"sketch": "$sf_s_box2", "at": [65, 0]}]},
    },
    {
        "tool": "surface",
        "save": "sf_box2",
        "args": {"kind": "stitch", "refs": [{"step": "$sf_walls2"}, {"step": "$sf_floor2"}]},
    },
    {
        "tool": "surface_modify",
        "args": {
            "kind": "fillet",
            "body": "$sf_box2",
            "edges": {"parallel": [0, 0, 1],
                      "at": [{"axis": "x", "value": 50}, {"axis": "y", "value": 0}], "count": 1},
            "radius": 1,
            "radius_type": "variable",
            "radius2": 3,
        },
        "check": area("sf_box2", 1591.4480880397077, 6),
    },
    {
        "tool": "surface_modify",
        "args": {
            "kind": "chamfer",
            "edges": {"parallel": [0, 0, 1],
                      "at": [{"axis": "x", "value": 80}, {"axis": "y", "value": 0}], "count": 1},
            "chamfer_type": "two",
            "distance": 2,
            "distance2": 4,
        },
        "check": area("sf_box2", 1591.4480880397077 - (60 - math.sqrt(20) * 10 + 4), 7),
    },
    {
        "tool": "surface_modify",
        "args": {"kind": "delete_face", "faces": {"normal": [0, 0, 1], "count": 1}},
        "check": faces("sf_box2", 6),
    },
    # Merge: two faces in one plane of an extruded polyline become one (golden surface4_merge)
    {
        "tool": "create_curve_sketch",
        "save": "sf_s_merge",
        "args": {"plane": "XY", "curves": [{"polyline": [[100, 0], [110, 0], [120, 0],
                                                         [120, 10]]}]},
    },
    {
        "tool": "surface",
        "save": "sf_merge_body",
        "args": {"kind": "extrude", "refs": [{"sketch": "$sf_s_merge", "at": [105, 0]}],
                 "options": {"distance": 10}},
        "check": area("sf_merge_body", 300.0, 3),
    },
    {
        "tool": "surface_modify",
        "args": {"kind": "merge", "faces": {"parallel": [0, 1, 0], "count": 2}},
        "check": all_of(area("sf_merge_body", 300.0, 2),
                        bbox("sf_merge_body", [100, 0, 0, 120, 10, 10])),
    },
]
