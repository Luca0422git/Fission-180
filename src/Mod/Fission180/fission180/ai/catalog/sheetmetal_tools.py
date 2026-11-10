# SPDX-License-Identifier: LGPL-2.1-or-later
"""AI tools for the SHEET METAL tab: Sheet Metal Rules, Flange (base, contour, edge), Lofted
Flange, Bend, Hem, Join by Bend, Corner Closure, the sheet metal Fillet / Chamfer, Convert to
Sheet Metal, Unfold / Refold, Rip, Create Flat Pattern and its Export DXF. Each one builds the
design step of fission180/ai/ops (sheetmetal_ops.py, flatpattern_ops.py) that runs the same code
as the Fusion-style dialog, with the dialog's option names. Pure Python.

The sheet metal steps take an edge as a point on it; these tools also take a selector there,
like every other tool: fission180/ai/executor.py turns it into the middle point of each edge
it picks just before the step is built (_picked_points)."""

import copy

from . import kit
from .kit import angle, array, boolean, enum, length, number, obj, point2, positive, schema
from .kit import step_id, string
from .registry import define, example
from .registry import mm as reg_mm

LIBRARY_RULES = (
    "Steel (mm)",
    "Stainless Steel (mm)",
    "Aluminum (mm)",
    "Copper (mm)",
    "Steel (in)",
    "Stainless Steel (in)",
    "Aluminum (in)",
    "Copper (in)",
)
RULES_HELP = (
    "Fission 180's library rules: %s (Steel (mm): 1 mm thick, Aluminum (mm): 1.5 mm; bend radius "
    "= Thickness, K factor 0.44), plus the design's own (sheet_metal_rule makes them)."
    % ", ".join(LIBRARY_RULES)
)
EDGE_PICKS_HELP = (
    "an edge selector (get_help topic selectors; give count) or a list of points [x, y, z] "
    "(mm, design coordinates), one on each edge (query_geometry's center_mm of a straight edge "
    "lies on it)"
)
EDGE_PICK_HELP = (
    "an edge selector that picks exactly one edge, or a point [x, y, z] on it (mm, design "
    "coordinates)"
)
SHEET_EDGE_HELP = (
    "A sheet edge is a straight edge where the sheet's top or bottom face meets a side face as "
    "thick as the sheet (on a 1 mm plate on XY, the top face's four edges at z = 1)."
)


def edges_pick(description):
    return {"type": ["object", "array"], "description": "%s: %s" % (description, EDGE_PICKS_HELP)}


def edge_pick(description):
    return {"type": ["object", "array"], "description": "%s: %s" % (description, EDGE_PICK_HELP)}


def _is_point(value):
    return (
        isinstance(value, list) and len(value) == 3 and all(kit.is_type(v, "number") for v in value)
    )


def check_edges(value, path, problems, one=False):
    """An edge pick: a selector, or points ([x, y, z]; one point when `one`)."""
    if isinstance(value, dict):
        kit.check_selector(value, path, "edges", problems)
        return
    if one:
        if not _is_point(value):
            problems.append("%s must be an edge selector or a point [x, y, z] on the edge" % path)
        return
    if not isinstance(value, list) or not value or not all(_is_point(p) for p in value):
        problems.append(
            "%s must be an edge selector or a list of points [x, y, z], one on each edge" % path
        )


def _not_with(args, keys, why, problems):
    for key in keys:
        if key in args:
            problems.append("%s %s" % (key, why))


def _copy(args, keys, into):
    for key in keys:
        if key in args:
            into[key] = copy.deepcopy(args[key])
    return into


def _with_options(args, step, keys, option_keys):
    """The step with `keys` copied from the arguments and `option_keys` in its options."""
    _copy(args, keys, step)
    options = _copy(args, option_keys, {})
    if options:
        step["options"] = options
    return step


# -- Sheet Metal Rules --------------------------------------------------------------------------
_RULE_VALUE = {
    "type": ["number", "string"],
    "description": "a number in the rule's units, or an expression in Thickness",
}
_RULE_FIELDS = obj(
    {
        "units": enum(["mm", "in"], "only for a new rule"),
        "thickness": _RULE_VALUE,
        "bend_radius": _RULE_VALUE,
        "k_factor": number("0..1: where the neutral fibre lies in the thickness"),
        "miter_gap": _RULE_VALUE,
        "bend_relief_shape": enum(["straight", "tear", "round"]),
        "bend_relief_width": _RULE_VALUE,
        "bend_relief_depth": _RULE_VALUE,
        "bend_relief_remnant": _RULE_VALUE,
        "corner_relief_2bend_shape": enum(
            ["round", "square", "tear", "trim_to_bend", "linear_weld", "arc_weld", "laser_weld"]
        ),
        "corner_relief_2bend_placement": enum(["intersection", "tangent"]),
        "corner_relief_2bend_size": _RULE_VALUE,
        "corner_relief_3bend_shape": enum(
            ["no_replacement", "intersection", "full_round", "round_with_radius"]
        ),
        "corner_relief_3bend_radius": _RULE_VALUE,
    },
    description="the rule's fields to set",
)


def _extra_rule(args, problems):
    if not isinstance(args.get("rule"), str) or not args.get("rule", "").strip():
        problems.append("rule must be the rule's name")
    k = (args.get("set") or {}).get("k_factor")
    if kit.is_type(k, "number") and not 0 <= k <= 1:
        problems.append("set.k_factor must be between 0 and 1")


define(
    "sheet_metal_rule",
    "Sheet metal rule",
    "sheet_metal",
    "SHEET METAL > MODIFY > Sheet Metal Rules",
    "Add or change a sheet metal rule In This Design (Fusion's Sheet Metal Rules): the "
    "thickness, bend radius, K factor, miter / rip / seam gap and the reliefs that every "
    "flange, bend and flat pattern of a body following it uses. rule: its name. from: start "
    "it from another rule (a library rule or one of the design's); without from the design's "
    "rule of that name is changed (or a new one made with Steel (mm)'s values). set: {field: "
    "value}: thickness, bend_radius, k_factor (0..1), miter_gap, bend_relief_shape / width / "
    "depth / remnant, corner_relief_2bend_shape / placement / size, corner_relief_3bend_shape "
    '/ radius, units (a new rule only); lengths are numbers in the rule\'s units or text in '
    'Thickness ("Thickness * 2"). active: true makes it the rule new flanges start with. '
    "Editing a rule that bodies follow rebuilds them. " + RULES_HELP + " Answers the rule's "
    "values and the design's rules.",
    schema(
        {
            "rule": string("the rule's name"),
            "from": string("start from this rule (library or design)"),
            "set": _RULE_FIELDS,
            "active": boolean("make it the active rule", default=False),
        },
        ["rule"],
    ),
    ops=["sf_sheet_rule"],
    extra=_extra_rule,
    own_id=False,
    title_fn=lambda a: "AI: Sheet metal rule %s" % a.get("rule", ""),
    examples=[
        example(
            {
                "rule": "Steel 0.5",
                "from": "Steel (mm)",
                "set": {"thickness": 0.5, "bend_radius": "Thickness"},
                "active": True,
            },
            "a 0.5 mm steel rule, active for the next flanges",
        )
    ],
)


# -- Flange ---------------------------------------------------------------------------------------
_FLANGE_OPTIONS = (
    "orientation",
    "direction",
    "distance",
    "distance2",
    "flip",
    "extent",
    "height",
    "datum",
    "position",
    "angle",
    "width_type",
    "width",
    "distance1",
    "width2",
    "target_offset",
)
_OVERRIDES = (
    ("override_bend_radius", ("bend_radius",)),
    ("override_bend_relief", ("relief_shape", "relief_width", "relief_depth", "relief_remnant")),
    ("override_corner_relief", ("corner_shape", "corner_placement", "corner_size")),
    ("override_corner3_relief", ("corner3_shape", "corner3_radius")),
)
_PLANE_AT = obj(
    {"plane": enum(["XY", "XZ", "YZ"]), "offset": length("along its normal", default=0)},
    ["plane"],
    "an origin plane moved along its normal",
)


def _extra_flange(args, problems):
    kind = args.get("kind")
    if kind in ("base", "contour"):
        if "profile" not in args:
            problems.append("a %s flange needs profile (a sketch id)" % kind)
        _not_with(args, ("edges", "target", "offset_refs"), "is for kind edge", problems)
    elif kind == "edge":
        if "edges" not in args:
            problems.append("an edge flange needs edges (the sheet edges it stands on)")
        else:
            check_edges(args["edges"], "edges", problems)
        _not_with(args, ("profile", "at", "rule", "operation"), "is not for kind edge", problems)
    if args.get("extent") == "to_object" and "target" not in args:
        problems.append("extent to_object needs target (the plane the flange runs to)")
    refs = args.get("offset_refs")
    if refs is not None and args.get("width_type", "two_offsets") != "two_offsets":
        problems.append("offset_refs only apply to width_type two_offsets")
    a = args.get("angle")
    if kit.is_type(a, "number") and not 0 < a <= 180:
        problems.append("angle must be above 0 and at most 180")


def _steps_flange(a, sid):
    step = {"op": "sf_flange", "id": sid, "kind": a["kind"]}
    _copy(a, ("profile", "at", "edges", "rule", "operation", "target", "offset_refs"), step)
    options = _copy(a, _FLANGE_OPTIONS, {})
    if "target" in a:
        options["extent"] = "to_object"
    for flag, keys in _OVERRIDES:
        if any(k in a for k in keys):
            options[flag] = True
            _copy(a, keys, options)
    if options:
        step["options"] = options
    return [step]


define(
    "flange",
    "Flange",
    "sheet_metal",
    "SHEET METAL > CREATE > Flange",
    "Fusion's Flange, the sheet metal body maker, in the active sheet metal rule's thickness. "
    "kind base: the closed areas of a sketch (profile; at: [[x, y], ...] a point in each area "
    "to use) become a flat plate; orientation side1 (up from the sketch, default) | side2 | "
    "centered. kind contour: an open chain of sketch lines and arcs (profile; at: a point on "
    "each curve to use, default all) becomes a bent strip, every sharp corner bent with the "
    "rule's radius; distance (mm, default 10), direction one_side | symmetric | two_sides "
    "(distance2), flip. Base and contour: operation new_body (default) | new_component (a "
    "Sheet Metal component) | join (into the active sheet metal body), rule (a new body's "
    "rule; default the active one). kind edge: a wall bent up from each sheet edge of the "
    "active sheet metal body (edges); height (mm, default 10), angle (degrees, default 90), "
    "flip (bend the other way), datum inner | outer | tangent (what height measures to), "
    "position inside | outside | adjacent | tangent (where the bend sits against the edge), "
    "width_type full | symmetric (width) | two_sides (distance1 before the edge's middle, "
    "width2 after it) | two_offsets (distance1 in from the edge's start, width2 from its end, "
    "or between offset_refs: two planes); extent to_object with target (a plane the wall runs "
    "up to) and target_offset. Edges that meet at a corner are mitred with the rule's gap. "
    "Rule overrides (the dialog's check boxes, ticked by giving a value): bend_radius, "
    "relief_shape straight | tear | round / relief_width / relief_depth / relief_remnant, "
    "corner_shape / corner_placement / corner_size, corner3_shape / corner3_radius. "
    + SHEET_EDGE_HELP
    + " "
    + RULES_HELP,
    schema(
        {
            "kind": enum(["base", "contour", "edge"]),
            "profile": step_id("base / contour: the sketch"),
            "at": array(point2(), "base: a point in each area; contour: a point on each curve", 1),
            "edges": edges_pick("edge: the sheet edges"),
            "rule": string("base / contour, new body: its sheet metal rule"),
            "operation": enum(["new_body", "new_component", "join"], default="new_body"),
            "orientation": enum(["side1", "side2", "centered"], default="side1"),
            "direction": enum(["one_side", "symmetric", "two_sides"], default="one_side"),
            "distance": positive("contour: how far the strip runs (mm)", default=10),
            "distance2": positive("contour, two_sides: the other side (mm)"),
            "flip": boolean(default=False),
            "extent": enum(["distance", "to_object"], default="distance"),
            "height": positive("edge: the wall's height (mm)", default=10),
            "datum": enum(["inner", "outer", "tangent"], default="inner"),
            "position": enum(["inside", "outside", "adjacent", "tangent"], default="inside"),
            "angle": angle("edge: the bend angle", default=90),
            "width_type": enum(["full", "symmetric", "two_sides", "two_offsets"], default="full"),
            "width": positive("width_type symmetric: the wall's width (mm)"),
            "distance1": number("two_sides / two_offsets: the first distance (mm)", minimum=0),
            "width2": number("two_sides / two_offsets: the second distance (mm)", minimum=0),
            "target": _PLANE_AT,
            "target_offset": length("extent to_object: the offset from target"),
            "offset_refs": array(_PLANE_AT, "two_offsets: the two reference planes", 2, 2),
            "bend_radius": number("override: the bend's inside radius (mm)", minimum=0),
            "relief_shape": enum(["straight", "tear", "round"]),
            "relief_width": positive("override: bend relief width (mm)"),
            "relief_depth": positive("override: bend relief depth (mm)"),
            "relief_remnant": positive("override: bend relief remnant (mm)"),
            "corner_shape": enum(
                ["round", "square", "tear", "trim_to_bend", "linear_weld", "arc_weld", "laser_weld"]
            ),
            "corner_placement": enum(["intersection", "tangent"]),
            "corner_size": positive("override: 2-bend corner relief size (mm)"),
            "corner3_shape": enum(
                ["no_replacement", "intersection", "full_round", "round_with_radius"]
            ),
            "corner3_radius": positive("override: 3-bend corner relief radius (mm)"),
        },
        ["kind"],
    ),
    ops=["sf_flange"],
    steps=_steps_flange,
    extra=_extra_flange,
    id_base="Flange",
    title_fn=lambda a: "AI: Flange (%s)" % a.get("kind", ""),
    examples=[
        example({"kind": "base", "profile": "Sketch1"}, "a 1 mm plate from Sketch1's rectangle"),
        example(
            {
                "kind": "edge",
                "edges": {"type": "line", "at": {"axis": "z", "value": "max"}, "count": 4},
                "height": 15,
            },
            "15 mm walls on the plate's four top edges: an open tray with mitred corners",
        ),
        example(
            {"kind": "contour", "profile": "Sketch2", "distance": 30, "rule": "Aluminum (mm)"},
            "an aluminium bracket bent along an L drawn in Sketch2, 30 mm wide",
        ),
    ],
)


# -- Lofted Flange --------------------------------------------------------------------------------
define(
    "lofted_flange",
    "Lofted flange",
    "sheet_metal",
    "SHEET METAL > CREATE > Lofted Flange",
    "Fusion's lofted flange: a sheet of the rule's thickness lofted between two profiles on "
    "separate planes (both open or both closed, lines and arcs only), like a square-to-round "
    "transition. profile1 / profile2: the sketches. forming brake (press-brake facets, "
    "default) | die (one smooth surface: it cannot be laid flat); control chord_tolerance "
    "(default, value 0.1 mm) | facet_angle (degrees) | facet_distance (mm) | facet_number, "
    "value; orientation side1 | side2 | center (which side of the profiles the thickness "
    "goes); operation new_body (default) | join (into the active sheet metal body); rule (a "
    "new body's rule). " + RULES_HELP,
    schema(
        {
            "profile1": step_id("the first profile's sketch"),
            "profile2": step_id("the second profile's sketch"),
            "rule": string("new body: its sheet metal rule"),
            "operation": enum(["new_body", "join"], default="new_body"),
            "forming": enum(["brake", "die"], default="brake"),
            "control": enum(
                ["chord_tolerance", "facet_angle", "facet_distance", "facet_number"],
                default="chord_tolerance",
            ),
            "value": positive("the facet control's value (mm, degrees or a number of facets)"),
            "orientation": enum(["side1", "side2", "center"], default="side1"),
        },
        ["profile1", "profile2"],
    ),
    ops=["sf_sm_lofted_flange"],
    steps=lambda a, sid: [
        _with_options(
            a,
            {"op": "sf_sm_lofted_flange", "id": sid},
            ("profile1", "profile2", "rule", "operation"),
            ("forming", "control", "value", "orientation"),
        )
    ],
    id_base="LoftedFlange",
    title_fn=lambda a: "AI: Lofted flange",
    examples=[
        example(
            {"profile1": "Sketch1", "profile2": "Sketch2", "value": 0.5},
            "a square-to-round hopper, facets within 0.5 mm",
        )
    ],
)


# -- Bend ------------------------------------------------------------------------------------------
def _extra_bend(args, problems):
    point = args.get("stationary")
    if point is not None and not _is_point(point):
        problems.append("stationary must be a point [x, y, z] on the sheet's top or bottom face")
    a = args.get("angle")
    if kit.is_type(a, "number") and not 0 < a <= 180:
        problems.append("angle must be above 0 and at most 180")


def _steps_bend(a, sid):
    step = {"op": "sf_sm_bend", "id": sid, "face": list(a["stationary"]), "lines": a["lines"]}
    _copy(a, ("at",), step)
    options = _copy(a, ("angle", "position", "flip", "bend_relief", "corner_relief"), {})
    if "bend_radius" in a:
        options.update(override_radius=True, radius=a["bend_radius"])
    if options:
        step["options"] = options
    return [step]


define(
    "bend",
    "Bend",
    "sheet_metal",
    "SHEET METAL > CREATE > Bend",
    "Fusion's Bend: bend the active flat sheet metal body along sketch lines that lie across "
    "its top or bottom face (draw them in a sketch on that face, or on its plane). lines: the "
    "sketch (every line in it; at: [[x, y], ...] sketch points to use only the lines through "
    "them); stationary: a point [x, y, z] (mm) on that top or bottom face, on the side of the "
    "lines that stays where it is. angle (degrees, default 90), position start | center | "
    "end (where the bend zone lies against the line, default center), flip (bend the other "
    "way), bend_relief / corner_relief (default true), bend_radius (overrides the rule's). "
    "Several lines are bent farthest from the stationary side first; holes in a bend zone "
    "come through bent.",
    schema(
        {
            "lines": step_id("the sketch with the bend lines"),
            "at": array(point2(), "sketch points: only the lines through them", 1),
            "stationary": kit.point3("a point on the face's side that stays"),
            "angle": angle("the bend angle", default=90),
            "position": enum(["start", "center", "end"], default="center"),
            "flip": boolean(default=False),
            "bend_relief": boolean(default=True),
            "corner_relief": boolean(default=True),
            "bend_radius": number("override: the inside radius (mm)", minimum=0),
        },
        ["lines", "stationary"],
    ),
    ops=["sf_sm_bend"],
    steps=_steps_bend,
    extra=_extra_bend,
    needs=("solid",),
    id_base="Bend",
    title_fn=lambda a: "AI: Bend%s" % (
        " %s deg" % kit.fmt(a["angle"]) if kit.is_type(a.get("angle"), "number") else ""
    ),
    examples=[
        example(
            {"lines": "Sketch2", "stationary": [10, 20, 1], "angle": 90},
            "fold a 1 mm plate up 90 degrees along Sketch2's line, the left part staying",
        )
    ],
)


# -- Hem -------------------------------------------------------------------------------------------
_HEM_OPTIONS = ("type", "length", "gap", "radius", "angle", "setback", "position", "flip", "miter")


def _extra_hem(args, problems):
    check_edges(args.get("edges"), "edges", problems)


def _steps_hem(a, sid):
    step = {"op": "sf_sm_hem", "id": sid, "edges": copy.deepcopy(a["edges"])}
    options = _copy(a, _HEM_OPTIONS, {})
    if "bend_radius" in a:
        options.update(override=True, radius_override=a["bend_radius"])
    if options:
        step["options"] = options
    return [step]


define(
    "hem",
    "Hem",
    "sheet_metal",
    "SHEET METAL > CREATE > Hem",
    "Fusion's Hem: fold sheet edges of the active sheet metal body back on themselves (safe "
    "edges, stiffening). edges: the sheet edges (a flange's top edge, say). type flat | open "
    "(default) | rolled | teardrop | rope | double, and the values each type uses: flat: "
    "length; open: length, gap; rolled: radius, angle (degrees); teardrop: radius, length, "
    "gap; rope: length, gap, radius; double: gap, length, setback (mm; defaults from the "
    "thickness T: length 4 T, gap T / 2, radius 2 T, angle 270). position inside | outside "
    "| adjacent | tangent, flip (curl to the other side), miter (default true: two hems "
    "meeting at a corner are mitred), bend_radius (overrides the rule's). " + SHEET_EDGE_HELP,
    schema(
        {
            "edges": edges_pick("the sheet edges"),
            "type": enum(["flat", "open", "rolled", "teardrop", "rope", "double"], default="open"),
            "length": positive("mm"),
            "gap": positive("mm"),
            "radius": positive("the hem's radius (mm)"),
            "angle": angle("rolled: how far it rolls"),
            "setback": number("double: mm", minimum=0),
            "position": enum(["inside", "outside", "adjacent", "tangent"], default="inside"),
            "flip": boolean(default=False),
            "miter": boolean(default=True),
            "bend_radius": number("override: the bend's inside radius (mm)", minimum=0),
        },
        ["edges"],
    ),
    ops=["sf_sm_hem"],
    steps=_steps_hem,
    extra=_extra_hem,
    needs=("solid",),
    id_base="Hem",
    title_fn=lambda a: "AI: Hem (%s)" % a.get("type", "open"),
    examples=[
        example(
            {"edges": [[50, 15, 21]], "type": "open"},
            "an open hem on the top edge of a 20 mm flange standing at x = 50",
        )
    ],
)


# -- Join by Bend ----------------------------------------------------------------------------------
def _extra_join(args, problems):
    check_edges(args.get("first"), "first", problems, one=True)
    check_edges(args.get("second"), "second", problems, one=True)


def _steps_join(a, sid):
    step = {"op": "sf_sm_join_bend", "id": sid}
    _copy(a, ("first", "other", "second"), step)
    if "bend_radius" in a:
        step["options"] = {"use_rule_radius": False, "radius": a["bend_radius"]}
    return [step]


define(
    "join_by_bend",
    "Join by bend",
    "sheet_metal",
    "SHEET METAL > CREATE > Join by Bend",
    "Fusion's Join by Bend: one bend joins two sheet metal bodies of the same thickness into "
    "one (the active body keeps the step; the other is used up). first: a sheet edge of the "
    "active body; other: the other body (any step in it); second: a sheet edge of the other "
    "body. Both plates are extended or trimmed so a bend of the rule's radius (or "
    "bend_radius) meets each; the bend runs where the two edges overlap. Refused with the "
    "reason for different thicknesses, parallel sheets or edges that do not overlap.",
    schema(
        {
            "first": edge_pick("the active body's sheet edge"),
            "other": step_id("the other sheet metal body (a step in it)"),
            "second": edge_pick("the other body's sheet edge"),
            "bend_radius": number("instead of the rule's: the inside radius (mm)", minimum=0),
        },
        ["first", "other", "second"],
    ),
    ops=["sf_sm_join_bend"],
    steps=_steps_join,
    extra=_extra_join,
    needs=("solid",),
    id_base="JoinByBend",
    title_fn=lambda a: "AI: Join by bend",
    examples=[
        example(
            {"first": [60, 40, 5], "other": "Flange1", "second": [50, 20, 1]},
            "join a standing plate at x = 60 to the flat plate Flange1 with one bend",
        )
    ],
)


# -- Corner Closure --------------------------------------------------------------------------------
_CLOSURE_OPTIONS = (
    "alignment",
    "gap",
    "overlap",
    "flip_overlap",
    "extend_aligned",
    "relief",
    "relief_size",
    "placement",
)


def _extra_closure(args, problems):
    check_edges(args.get("dominant"), "dominant", problems, one=True)
    check_edges(args.get("submissive"), "submissive", problems, one=True)


define(
    "corner_closure",
    "Corner closure",
    "sheet_metal",
    "SHEET METAL > MODIFY > Corner Closure",
    "Fusion's Corner Closure: close the open corner where two flanges of the active sheet "
    "metal body meet. dominant / submissive: an edge of each flange's end at the corner (the "
    "end faces that face each other). alignment symmetric (default: both stop gap / 2 from "
    "the corner's bisector) | overlap (the dominant runs over the other's end: overlap 0..1 "
    "of the thickness, flip_overlap swaps); gap (mm, default the rule's miter gap); "
    "extend_aligned (default true); relief trim_to_bend (default) | tear | round | square "
    "with relief_size (mm) and placement intersection | tangent | vertex.",
    schema(
        {
            "dominant": edge_pick("an edge of the first flange's end"),
            "submissive": edge_pick("an edge of the second flange's end"),
            "alignment": enum(["symmetric", "overlap"], default="symmetric"),
            "gap": number("mm", minimum=0),
            "overlap": number("0..1 of the thickness", minimum=0, maximum=1),
            "flip_overlap": boolean(default=False),
            "extend_aligned": boolean(default=True),
            "relief": enum(["round", "square", "tear", "trim_to_bend"], default="trim_to_bend"),
            "relief_size": positive("mm"),
            "placement": enum(["intersection", "tangent", "vertex"], default="intersection"),
        },
        ["dominant", "submissive"],
    ),
    ops=["sf_sm_corner_closure"],
    steps=lambda a, sid: [
        _with_options(
            a,
            {"op": "sf_sm_corner_closure", "id": sid},
            ("dominant", "submissive"),
            _CLOSURE_OPTIONS,
        )
    ],
    extra=_extra_closure,
    needs=("solid",),
    id_base="CornerClosure",
    title_fn=lambda a: "AI: Corner closure",
    examples=[
        example(
            {"dominant": [100, 55, 12], "submissive": [95, 60, 12], "gap": 1},
            "close the corner between two 20 mm flanges with a 1 mm gap",
        )
    ],
)


# -- sheet metal Fillet / Chamfer ------------------------------------------------------------------
def _round_tool(kind):
    size = "radius" if kind == "fillet" else "distance"

    def extra(args, problems):
        rows = args.get("sets")
        if ("edges" in args) == bool(rows):
            problems.append("give edges and %s, or sets (one or the other)" % size)
        if "edges" in args:
            check_edges(args["edges"], "edges", problems)
            if size not in args:
                problems.append("%s is missing" % size)
        for i, row in enumerate(rows or []):
            if isinstance(row, dict) and "edges" in row:
                check_edges(row["edges"], "sets[%d].edges" % i, problems)

    def steps(a, sid):
        rows = a.get("sets") or [{"edges": a["edges"], size: a[size]}]
        sets = [{"edges": copy.deepcopy(r["edges"]), "value": r[size]} for r in rows]
        return [{"op": "sf_sm_" + kind, "id": sid, "sets": sets}]

    title = "Sheet metal %s" % kind
    row = obj(
        {"edges": edges_pick("this set's corner edges"), size: positive("mm")},
        ["edges", size],
        "one set: edges with their own %s" % size,
    )
    define(
        "sheet_metal_" + kind,
        title,
        "sheet_metal",
        "SHEET METAL > MODIFY > %s" % kind.capitalize(),
        "Fusion's sheet metal %s: %s the corners of the active sheet metal body's plates, "
        "i.e. only edges that run straight through the sheet's thickness (the part can still "
        "be laid flat; any other edge is refused with the reason). edges and %s (mm), or "
        "sets: [{edges, %s}, ...] with a size each. The corner edges of a 1 mm plate on XY "
        'are its 4 edges parallel to Z: {"type": "line", "parallel": [0, 0, 1], "count": 4}.'
        % (kind, "round" if kind == "fillet" else "chamfer", size, size),
        schema(
            {
                "edges": edges_pick("the corner edges"),
                size: positive("mm"),
                "sets": array(row, "several sets, each with its own %s" % size, 1),
            }
        ),
        ops=["sf_sm_" + kind],
        steps=steps,
        extra=extra,
        needs=("solid",),
        id_base="SheetMetal" + kind.capitalize(),
        title_fn=lambda a, t=title: "AI: " + t + reg_mm(a, size),
        examples=[
            example(
                {
                    "edges": {"type": "line", "parallel": [0, 0, 1], "count": 4},
                    size: 5 if kind == "fillet" else 3,
                },
                "%s the four corners of a plate" % ("round" if kind == "fillet" else "chamfer"),
            )
        ],
    )


_round_tool("fillet")
_round_tool("chamfer")


# -- Convert to Sheet Metal ------------------------------------------------------------------------
def _steps_convert(a, sid):
    rule = a.get("rule", "template")
    if rule != "template":
        rule = "In This Design|%s" % rule  # (the design's rule of that name, else the library's)
    return [{"op": "sf_sm_convert", "id": sid, "face": copy.deepcopy(a["face"]), "rule": rule}]


define(
    "convert_to_sheet_metal",
    "Convert to sheet metal",
    "sheet_metal",
    "SHEET METAL > MODIFY > Convert to Sheet Metal",
    "Fusion's Convert to Sheet Metal: the active solid body, one sheet of even thickness "
    "(made with Shell, Extrude, or imported) with flat walls and round bends, becomes a sheet "
    "metal body (its walls the flanges, its round faces the bends) that unfold, rip and the "
    "flat pattern work on. face: one flat face of a wall, where the thickness is measured. "
    'rule: "template" (default: a new rule from the measured thickness and bend radius) or a '
    "rule's name (copied with the measured thickness). Sharp inside corners are refused: "
    "fillet them first (an inside radius r needs the outside r + thickness).",
    schema(
        {
            "face": kit.selector("one flat face of a wall"),
            "rule": string('"template" or a rule\'s name', default="template"),
        },
        ["face"],
    ),
    ops=["sf_sm_convert"],
    steps=_steps_convert,
    selectors={"face": "faces"},
    needs=("solid",),
    id_base="ConvertToSheetMetal",
    title_fn=lambda a: "AI: Convert to sheet metal",
    examples=[
        example(
            {"face": {"type": "plane", "normal": [0, 0, 1], "at": {"axis": "z", "value": "min"},
                      "count": 1}},
            "an even 1 mm U channel becomes sheet metal, measured at its floor",
        )
    ],
)


# -- Unfold / Refold -------------------------------------------------------------------------------
def _extra_unfold(args, problems):
    if bool(args.get("all")) == ("bends" in args):
        problems.append("give bends (the bend faces to lay flat) or all: true, one of them")


define(
    "unfold",
    "Unfold",
    "sheet_metal",
    "SHEET METAL > MODIFY > Unfold",
    "Fusion's Unfold: lay some or all bends of the active sheet metal body flat in the "
    "timeline (the stationary face stays put), to cut holes and slots across the bends while "
    "they are flat; refold folds them back carrying the cuts. face: the stationary face (a "
    "top or bottom face of a wall); bends: a face selector of the bends' round faces to lay "
    "flat, or all: true.",
    schema(
        {
            "face": kit.selector("the stationary face (one)"),
            "bends": kit.selector("the bends' round faces"),
            "all": boolean("every bend", default=False),
        },
        ["face"],
    ),
    op="sf_unfold",
    extra=_extra_unfold,
    selectors={"face": "faces", "bends": "faces"},
    needs=("solid",),
    id_base="Unfold",
    title_fn=lambda a: "AI: Unfold",
    examples=[
        example(
            {"face": {"type": "plane", "normal": [0, 0, 1], "at": {"axis": "z", "value": "min"},
                      "count": 1}, "all": True},
            "lay every bend flat, the floor staying where it is",
        )
    ],
)
define(
    "refold",
    "Refold",
    "sheet_metal",
    "SHEET METAL > MODIFY > Refold",
    "Fusion's Refold: fold the bends an unfold laid flat back up, carrying the holes and "
    "slots cut while flat onto the walls and bends. unfold: the Unfold step (default: the one "
    "with no refold yet).",
    schema({"unfold": step_id("the Unfold step")}),
    op="sf_refold",
    needs=("solid",),
    id_base="Refold",
    title_fn=lambda a: "AI: Refold",
    examples=[example({"unfold": "Unfold1"}, "fold Unfold1's bends back")],
)


# -- Rip -------------------------------------------------------------------------------------------
_RIP_NEEDS = {"face": ("face",), "edge": ("edge",), "points": ("point1", "point2")}


def _extra_rip(args, problems):
    kind = args.get("type", "edge")
    need = _RIP_NEEDS.get(kind, ())
    for key in need:
        if key not in args:
            problems.append("type %s needs %s" % (kind, key))
    allowed = set(need) | ({"offset1", "offset2"} if kind == "points" else set())
    for key in ("face", "edge", "point1", "point2", "offset1", "offset2"):
        if key in args and key not in allowed:
            problems.append("%s is not for type %s" % (key, kind))


define(
    "rip",
    "Rip",
    "sheet_metal",
    "SHEET METAL > MODIFY > Rip",
    "Fusion's Rip: open a closed or overlapping sheet (a tube, a box) of the active sheet "
    "metal body so it can be laid flat. type face: face (one face: a bend's round face or a "
    "corner face) is cut away through the thickness; edge (default): a gap gap mm wide along "
    "edge (a sharp edge where two walls meet); points: a straight slot gap mm wide between "
    "two points on one face, each offset1 / offset2 mm along an edge (point1 / point2) from "
    "its start. gap: mm (default 1).",
    schema(
        {
            "type": enum(["face", "edge", "points"], default="edge"),
            "face": kit.selector("type face: the face to cut away (one)"),
            "edge": kit.selector("type edge: the edge to rip along (one)", "edges"),
            "point1": kit.selector("type points: the edge the first point is on (one)", "edges"),
            "point2": kit.selector("type points: the edge the second point is on (one)", "edges"),
            "offset1": number("mm along point1's edge from its start", minimum=0, default=0),
            "offset2": number("mm along point2's edge from its start", minimum=0, default=0),
            "gap": positive("the rip's width (mm)", default=1),
        }
    ),
    steps=lambda a, sid: [dict(copy.deepcopy(a), op="sf_rip", id=sid, type=a.get("type", "edge"))],
    ops=["sf_rip"],
    extra=_extra_rip,
    selectors={"face": "faces", "edge": "edges", "point1": "edges", "point2": "edges"},
    needs=("solid",),
    id_base="Rip",
    title_fn=lambda a: "AI: Rip (%s)" % a.get("type", "edge"),
    examples=[
        example(
            {"type": "face", "face": {"type": "cylinder", "radius": 2,
                                      "at": [{"axis": "x", "value": "max"},
                                             {"axis": "y", "value": "max"}], "count": 1}},
            "cut one round corner out of a converted tube",
        )
    ],
)


# -- Flat Pattern ----------------------------------------------------------------------------------
define(
    "flat_pattern",
    "Create flat pattern",
    "sheet_metal",
    "SHEET METAL > CREATE > Create Flat Pattern",
    "Fusion's Create Flat Pattern: lay a sheet metal body (body; default the active one) "
    "flat from a stationary face, every bend developed with the rule's K factor; the flat "
    "pattern follows later changes of the folded part (one per component). face: a top or "
    "bottom face of a wall (it lies on XY facing up, the sheet below z = 0). Answers the "
    "flat size (mm), thickness, K factor and every bend (angle, inside radius, up / down, "
    "allowance, its centre line in the flat's XY). export_flat_pattern writes it as DXF.",
    schema(
        {
            "face": kit.selector("the stationary face (one)"),
            "body": step_id("the sheet metal body (default: the active one)"),
        },
        ["face"],
    ),
    ops=["sf_flat_pattern"],
    selectors={"face": "faces"},
    needs=("solid",),
    title_fn=lambda a: "AI: Create flat pattern",
    examples=[
        example(
            {"face": {"type": "plane", "normal": [0, 0, 1], "at": {"axis": "z", "value": "min"},
                      "count": 1}},
            "the folded tray laid flat from its floor",
        )
    ],
)
define(
    "export_flat_pattern",
    "Export flat pattern DXF",
    "sheet_metal",
    "FLAT PATTERN > EXPORT > Export DXF",
    "Write a flat pattern as DXF for a laser or water-jet cutter (Fusion's Export DXF on the "
    "FLAT PATTERN tab): the outline and holes on their layers, the bend centre lines (up / "
    "down) and extent lines on theirs, with notes. path: a full path (.dxf added); "
    "flat_pattern: its id (default: the active body's, or the design's only one); "
    "center_lines / extent_lines (default true); splines_to_polylines with tolerance (mm, "
    "default 0.1). A file that exists is not replaced unless the person agrees.",
    schema(
        {
            "path": string("the DXF file to write (a full path)"),
            "flat_pattern": step_id("the flat pattern (or its body)"),
            "center_lines": boolean(default=True),
            "extent_lines": boolean(default=True),
            "splines_to_polylines": boolean(default=False),
            "tolerance": positive("splines_to_polylines: mm", default=0.1),
        },
        ["path"],
    ),
    changes=False,
    writes_files=True,
    confirm_overwrite=True,
    needs=("solid",),
    title_fn=lambda a: "AI: Export flat pattern",
    examples=[
        example({"path": "~/parts/tray-flat.dxf"}, "the tray's flat pattern for the laser cutter")
    ],
)
