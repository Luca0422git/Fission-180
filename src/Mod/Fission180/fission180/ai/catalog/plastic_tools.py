# SPDX-License-Identifier: LGPL-2.1-or-later
"""AI tools for the PLASTIC tab: Assign Plastic Rule (with Manage Plastic Rules' edit), Boss
(and its fastener), Rest, Snap Fit, Lip and Groove, and Design Advice (read only). Each one
builds the design step of fission180/ai/ops (plastic_ops.py, plastic2_ops.py) that runs the same
code as the Fusion-style dialog, with the dialog's option names; Design Advice reads the
design with the same checks as its panel (fission180/plastic_advice.py). Rib, Web, Rule Fillet,
Shell and Draft are the SOLID tools of the same names. Pure Python."""

import copy

from . import kit
from .kit import angle, array, boolean, enum, length, number, obj, point2, positive, schema
from .kit import step_id, step_ids, string
from .registry import define, example

LIBRARY_RULES = (
    "Default (mm)",
    "Default (in)",
    "ABS 2 mm",
    "ABS 1.5 mm",
    "PC 2 mm",
    "PC/ABS 2 mm",
    "PP 1.5 mm",
    "PA66 1.5 mm",
    "POM 1.5 mm",
    "HIPS 2 mm",
    "HDPE 2 mm",
    "PBT 1.8 mm",
    "PMMA 2.5 mm",
    "TPE 1.5 mm",
    "FDM PLA 2 mm",
    "FDM PETG 2 mm",
)
RULE_HELP = (
    "Sizes left out follow the plastic rule assigned to the design (plastic_rule; Default (mm): "
    "2 mm walls, 1 degree draft, 0.1 mm clearance) and keep following it when it changes."
)
_PLANE = enum(["XY", "XZ", "YZ"], "the sketch plane (an origin plane)", default="XY")
_OFFSET = length("the plane moved along its normal", default=0)


def _copy(args, keys, into):
    for key in keys:
        if key in args:
            into[key] = copy.deepcopy(args[key])
    return into


# -- Assign Plastic Rule ---------------------------------------------------------------------------
_RULE_VALUE = {
    "type": ["number", "string"],
    "description": "a number (mm or degrees, a percentage for thickness_variation), or an "
    "expression in Thickness for a length",
}
_PLASTIC_FIELDS = obj(
    {
        "material": string("the material's name"),
        "thickness": _RULE_VALUE,
        "draft_angle": _RULE_VALUE,
        "nominal_radius": _RULE_VALUE,
        "reveal_height": _RULE_VALUE,
        "clearance": _RULE_VALUE,
        "minimum_thickness": _RULE_VALUE,
        "maximum_thickness": _RULE_VALUE,
        "thickness_variation": _RULE_VALUE,
        "minimum_draft_angle": _RULE_VALUE,
        "knife_edge_threshold": _RULE_VALUE,
    },
    description="the design's copy of the rule: fields to change",
)
define(
    "plastic_rule",
    "Assign plastic rule",
    "plastic",
    "PLASTIC > SETUP > Assign Plastic Rule / Manage Plastic Rules",
    "Assign a plastic rule to the design (Fusion's Assign Plastic Rule): the wall thickness, "
    "draft, radii, clearance and limits that Boss, Snap Fit, Lip, Rest and Design Advice "
    "start from, and the material the bodies get. rule: a library rule (%s) or one of the "
    "design's (a library rule is copied into the design). set: change the design's copy "
    "(Manage Plastic Rules > Edit): material, thickness, draft_angle, nominal_radius, "
    "reveal_height, clearance, minimum_thickness, maximum_thickness, thickness_variation (%%), "
    "minimum_draft_angle, knife_edge_threshold; lengths in mm or text in Thickness "
    '("Thickness / 2"). Bosses, snap fits, lips and rests whose sizes follow the rule '
    "update. Answers the rule's values." % ", ".join(LIBRARY_RULES),
    schema({"rule": string("the rule's name"), "set": _PLASTIC_FIELDS}, ["rule"]),
    ops=["sf_plastic_rule"],
    own_id=False,
    title_fn=lambda a: "AI: Plastic rule %s" % a.get("rule", ""),
    examples=[
        example({"rule": "PC 2 mm"}, "polycarbonate, 2 mm walls"),
        example(
            {"rule": "ABS 2 mm", "set": {"thickness": 2.5, "clearance": 0.15}},
            "ABS with 2.5 mm walls and 0.15 mm clearance",
        ),
    ],
)


# -- Boss ------------------------------------------------------------------------------------------
_SIDE_NUMBERS = (
    "diameter",
    "wall",
    "draft",
    "hole_diameter",
    "hole_draft",
    "hole_depth",
    "major_diameter",
    "major_depth",
    "major_draft",
    "countersink_angle",
    "step_diameter",
    "step_depth",
    "step_draft",
    "clearance",
    "root_radius",
    "tip_radius",
    "hole_start_radius",
    "hole_end_radius",
    "step_tip_radius",
    "step_root_radius",
    "major_tip_radius",
    "major_root_radius",
    "rib_count",
    "rib_total_angle",
    "rib_rotation",
    "rib_cut",
    "rib_chamfer_angle",
    "rib_thickness",
    "rib_draft",
    "rib_outer_draft",
    "rib_length",
    "rib_offset",
)
_SIDE_CHOICES = {
    "shape": ("blank", "constant_diameter", "constant_thickness"),
    "hole": ("simple", "counterbore", "countersink"),
    "extent": ("through", "from_top", "from_bottom"),
    "step": ("none", "in", "out"),
    "rib_profile": ("none", "chamfer", "fillet"),
    "rib_extent": ("length", "to_next"),
}
_SIDE = kit.free_object(
    "one side's settings (mm, degrees): shape blank | constant_diameter | constant_thickness, "
    "diameter, wall, draft; hole simple | counterbore | countersink, hole_diameter, "
    "hole_depth, hole_draft, extent through | from_top | from_bottom, major_diameter / "
    "major_depth / major_draft (counterbore), countersink_angle; step none | in | out "
    "(alignment step), step_diameter, step_depth, step_draft; clearance, root_radius, "
    "tip_radius; enabled; ribs (true / false), rib_count, rib_total_angle, rib_rotation, "
    "rib_thickness, rib_draft, rib_length, rib_extent length | to_next, rib_offset, "
    "rib_profile none | chamfer | fillet, rib_cut, rib_chamfer_angle, rib_outer_draft"
)
FASTENER_HEADS = ("pan", "round", "flat", "hex", "hex_washer")


def _check_side(value, path, problems):
    if not isinstance(value, dict):
        return
    for key, item in value.items():
        if key in _SIDE_CHOICES:
            if item not in _SIDE_CHOICES[key]:
                words = ", ".join(_SIDE_CHOICES[key])
                problems.append("%s.%s must be one of %s" % (path, key, words))
        elif key in ("enabled", "ribs"):
            if not isinstance(item, bool):
                problems.append("%s.%s must be true or false" % (path, key))
        elif key in _SIDE_NUMBERS:
            if not kit.is_type(item, "number"):
                problems.append("%s.%s must be a number" % (path, key))
        else:
            problems.append("%s.%s is not a boss setting" % (path, key))


def _check_points(points, problems):
    if isinstance(points, list) and not points:
        problems.append("points must have at least one [x, y]")


def _extra_boss(args, problems):
    _check_points(args.get("points"), problems)
    for side in ("side1", "side2"):
        _check_side(args.get(side), side, problems)
    if not args.get("fastener"):
        for key in ("head", "length"):
            if key in args:
                problems.append("%s is for the screws: give fastener: true too" % key)


def _steps_boss(a, sid):
    step = _copy(a, ("plane", "offset", "points", "screw", "flip", "position", "side1", "side2"),
                 {"op": "sf_boss", "id": sid})
    fastener = a.get("fastener")
    if fastener:
        step["fastener"] = {"create": True}
        _copy(a, ("head", "length"), step["fastener"])
    return [step]


define(
    "boss",
    "Boss",
    "plastic",
    "PLASTIC > CREATE > Boss",
    "Fusion's Boss: screw bosses joining two halves of a plastic part (an enclosure and its "
    "lid). points: [[x, y], ...] the boss centres in a sketch on plane (XY | XZ | YZ) moved "
    "offset mm along its normal: put it on the parting plane between the halves. Side 1 (the "
    "head side, the screw head's counterbored hole, through) grows along the plane's normal, "
    "Side 2 (the thread side, a pilot hole) against it; flip swaps them; each side finds the "
    "body behind it. screw: the screw's size in mm (3 = M3, default) sizes both sides; "
    "position: moves the parting plane (mm). side1 / side2: any of the dialog's settings for "
    "that side. fastener: true adds a simple screw at every boss in a component of its own "
    "(head pan | round | flat | hex | hex_washer, length mm, 0 = to the pilot hole's "
    "bottom). " + RULE_HELP,
    schema(
        {
            "points": array(point2("[x, y] a boss centre in the sketch"), "the boss centres", 1),
            "plane": _PLANE,
            "offset": _OFFSET,
            "screw": positive("the screw's diameter (mm): 3 = M3", default=3),
            "flip": boolean(default=False),
            "position": length("moves the parting plane", default=0),
            "side1": _SIDE,
            "side2": _SIDE,
            "fastener": boolean("add the screws (a component of their own)", default=False),
            "head": enum(FASTENER_HEADS, "fastener: the head", default="pan"),
            "length": number("fastener: the screw's length (mm), 0 = auto", minimum=0),
        },
        ["points"],
    ),
    ops=["sf_boss"],
    steps=_steps_boss,
    extra=_extra_boss,
    needs=("solid",),
    id_base="Boss",
    title_fn=lambda a: "AI: Boss",
    examples=[
        example(
            {"points": [[10, 10], [50, 30]], "plane": "XY", "offset": 20, "screw": 3},
            "M3 bosses at two corners where a lid sits on a box at z = 20",
        )
    ],
)
define(
    "boss_fastener",
    "Boss fastener",
    "plastic",
    "PLASTIC > CREATE > Boss > Fastener: Create Component",
    "Add the screws to an existing boss (the Boss dialog's Fastener > Create Component): a "
    "simple screw at every boss point in a component of its own, following the boss when it "
    "changes. boss: the boss step; head pan | round | flat | hex | hex_washer; length (mm, 0 "
    "= to the pilot hole's bottom).",
    schema(
        {
            "boss": step_id("the boss step (either side)"),
            "head": enum(FASTENER_HEADS, default="pan"),
            "length": number("the screw's length (mm), 0 = auto", minimum=0, default=0),
        },
        ["boss"],
    ),
    op="sf_boss_fastener",
    needs=("solid",),
    id_base="Fastener",
    title_fn=lambda a: "AI: Boss fastener",
    examples=[example({"boss": "Boss1", "head": "pan"}, "pan head screws in Boss1's holes")],
)


# -- Rest ------------------------------------------------------------------------------------------
define(
    "rest",
    "Rest",
    "plastic",
    "PLASTIC > CREATE > Rest",
    "Fusion's Rest: a flat landing on a curved or sloping plastic wall (for a label, a "
    "switch, a PCB standoff). rect: [x0, y0, x1, y1] the landing's rectangle in a sketch on "
    "plane (XY | XZ | YZ) moved offset mm along its normal: the plane cuts the active body's "
    "wall where the landing goes. Inside the rectangle the body is cut back to the plane "
    "where it bulges past it, and a pedestal thickness mm thick (drafted by draft degrees) "
    "fills where it lies below; flip turns which side is inside. " + RULE_HELP,
    schema(
        {
            "rect": kit.numbers(4, "[x0, y0, x1, y1] in the sketch (mm)"),
            "plane": _PLANE,
            "offset": _OFFSET,
            "thickness": positive("the wall under the landing (mm)"),
            "draft": angle("the pedestal walls' draft", minimum=0),
            "flip": boolean(default=False),
        },
        ["rect"],
    ),
    op="sf_rest",
    needs=("solid",),
    id_base="Rest",
    title_fn=lambda a: "AI: Rest",
    examples=[
        example(
            {"rect": [20, 10, 40, 30], "plane": "XY", "offset": -3, "thickness": 2, "draft": 0},
            "a pad 3 mm below the floor of a hollow box",
        )
    ],
)


# -- Snap Fit --------------------------------------------------------------------------------------
_SNAP_OPTIONS = (
    "type",
    "rotation",
    "angle",
    "angles",
    "flip",
    "hook",
    "groove",
    "extent",
    "extent_distance",
    "length",
    "width",
    "thickness",
    "tip_thickness",
    "catch_depth",
    "catch_length",
    "insertion_angle",
    "retention_angle",
    "draft",
    "fillet",
    "clearance",
    "loop_thickness",
    "align_point",
    "align_inward",
)


def _extra_snap(args, problems):
    _check_points(args.get("points"), problems)
    if args.get("rotation") == "independent" and "angles" in args:
        if len(args["angles"]) != len(args.get("points") or []):
            problems.append("angles needs one angle per point")
    if args.get("rotation") == "aligned" and "align_point" not in args:
        problems.append("rotation aligned needs align_point")


def _steps_snap(a, sid):
    step = _copy(a, ("plane", "offset", "points"), {"op": "sf_snap_fit", "id": sid})
    if "hook_body" in a:
        step["hook"] = a["hook_body"]
    if "groove_body" in a:
        step["other"] = a["groove_body"]
    options = _copy(a, _SNAP_OPTIONS, {})
    if options:
        step["options"] = options
    return [step]


define(
    "snap_fit",
    "Snap fit",
    "plastic",
    "PLASTIC > CREATE > Snap Fit",
    "Fusion's Snap Fit: a cantilever hook at each point between two bodies (a lid and its "
    "box) and the part it catches on the other body. points: [[x, y], ...] in a sketch on "
    "plane (XY | XZ | YZ) moved offset mm along its normal: the parting plane, each point the "
    "middle of the beam's catch-side face at its root. type parallel (Hook and Groove: the "
    "catch goes into a groove cut in a wall along the beam, default) | perpendicular (the "
    "beam passes a slot and hooks under the wall) | loop (Hook and Loop: a frame on the other "
    "body). The beam: length, width, thickness, tip_thickness, draft (degrees), fillet (base "
    "fillet); the catch: catch_depth, catch_length, insertion_angle, retention_angle; "
    "clearance, loop_thickness; extent to_next (base block to the body, default) | distance "
    "(extent_distance); rotation uniform (angle) | independent (angles, one per point) | "
    "aligned (align_point [x, y, z], align_inward); flip; hook / groove (make each, default "
    "true). hook_body / groove_body: a step of the body that gets the hooks / the grooves "
    "(default: found as the dialog finds them). All mm and degrees. " + RULE_HELP,
    schema(
        {
            "points": array(point2("[x, y] a hook's root"), "the hooks' points", 1),
            "plane": _PLANE,
            "offset": _OFFSET,
            "type": enum(["parallel", "perpendicular", "loop"], default="parallel"),
            "rotation": enum(["uniform", "independent", "aligned"], default="uniform"),
            "angle": angle("rotation uniform: the catch direction from the sketch's x axis"),
            "angles": array(number(), "rotation independent: one angle per point (degrees)"),
            "align_point": kit.point3("rotation aligned: the catches face this point"),
            "align_inward": boolean("rotation aligned: toward the point (else away)"),
            "flip": boolean(default=False),
            "hook": boolean("make the hooks", default=True),
            "groove": boolean("make the grooves / loops", default=True),
            "extent": enum(["to_next", "distance"], default="to_next"),
            "extent_distance": positive("extent distance: the base block's depth (mm)"),
            "length": positive("the beam's length (mm)"),
            "width": positive("the beam's width (mm)"),
            "thickness": positive("the beam's thickness at its root (mm)"),
            "tip_thickness": positive("the beam's thickness at its tip (mm)"),
            "catch_depth": positive("mm"),
            "catch_length": positive("mm"),
            "insertion_angle": angle(),
            "retention_angle": angle(),
            "draft": angle(minimum=0),
            "fillet": number("the base fillet's radius (mm)", minimum=0),
            "clearance": number("mm", minimum=0),
            "loop_thickness": positive("type loop (mm)"),
            "hook_body": step_id("the body that gets the hooks (a step in it)"),
            "groove_body": step_id("the body that gets the grooves (a step in it)"),
        },
        ["points"],
    ),
    ops=["sf_snap_fit"],
    steps=_steps_snap,
    extra=_extra_snap,
    needs=("solid",),
    id_base="SnapFit",
    title_fn=lambda a: "AI: Snap fit (%s)" % a.get("type", "parallel"),
    examples=[
        example(
            {"points": [[58, 20]], "plane": "XY", "offset": 20, "length": 12, "width": 6},
            "a hook under a lid at z = 20, catching in the box's right-hand wall",
        )
    ],
)


# -- Lip -------------------------------------------------------------------------------------------
_LIP_OPTIONS = (
    "type",
    "guide",
    "swap",
    "lip_width",
    "lip_height",
    "clearance",
    "clearance_height",
    "groove_width",
    "groove_depth",
    "inner_draft",
    "outer_draft",
    "tip_radius",
    "root_radius",
)


def _steps_lip(a, sid):
    step = _copy(a, ("edges", "of", "mate"), {"op": "sf_lip", "id": sid})
    options = _copy(a, _LIP_OPTIONS, {})
    if options:
        step["options"] = options
    return [step]


define(
    "lip",
    "Lip",
    "plastic",
    "PLASTIC > CREATE > Lip",
    "Fusion's Lip (Lip, Groove or Lip And Groove): a lip on the rim of one half of a plastic "
    "part and the matching groove in the other half, so the two locate and seal. edges: the "
    "rim's edges (a closed or open chain of edges round the flat parting face, on the body of "
    "of: a step id, default the active body); type lip_and_groove (default: the lip here, the "
    "groove in the touching body, mate: a step of that body, default found) | lip | groove; "
    "swap (the groove here, the lip on the mate); guide pull (the rim face's normal, default) "
    "| face. lip_width, lip_height, groove_width, groove_depth, clearance, clearance_height, "
    "inner_draft / outer_draft (degrees), tip_radius, root_radius (mm). " + RULE_HELP,
    schema(
        {
            "edges": kit.selector("the rim's edges", "edges"),
            "of": step_id("the body the edges are on (a step in it)"),
            "mate": step_id("lip_and_groove: the touching body (a step in it)"),
            "type": enum(["lip_and_groove", "lip", "groove"], default="lip_and_groove"),
            "guide": enum(["pull", "face"], default="pull"),
            "swap": boolean(default=False),
            "lip_width": positive("mm"),
            "lip_height": positive("mm"),
            "clearance": number("mm", minimum=0),
            "clearance_height": number("mm", minimum=0),
            "groove_width": positive("mm"),
            "groove_depth": positive("mm"),
            "inner_draft": angle(minimum=0),
            "outer_draft": angle(minimum=0),
            "tip_radius": number("mm", minimum=0),
            "root_radius": number("mm", minimum=0),
        },
        ["edges"],
    ),
    ops=["sf_lip"],
    steps=_steps_lip,
    selectors={"edges": "edges"},
    needs=("solid",),
    id_base="Lip",
    title_fn=lambda a: "AI: Lip (%s)" % a.get("type", "lip_and_groove"),
    examples=[
        example(
            {
                "edges": {"type": "circle", "at": {"axis": "z", "value": "max"}, "count": 1},
                "type": "lip",
                "lip_width": 1,
                "lip_height": 1,
            },
            "a 1 x 1 mm lip on the round top rim of a cylinder",
        )
    ],
)


# -- Design Advice ---------------------------------------------------------------------------------
ADVICE_CHECKS = ("thickness", "variation", "draft", "knife", "undercut")
define(
    "design_advice",
    "Design advice",
    "plastic",
    "PLASTIC > INSPECT > Design Advice",
    "Fusion's Design Advice, read only: check plastic bodies for moulding problems against "
    "their plastic rule and say where: walls too thin or too thick (thickness), thickness "
    "that varies too much (variation), faces with too little draft for the pull direction "
    "(draft), knife edges (knife) and undercuts (undercut). bodies: step ids (default: the "
    "visible bodies of components with a plastic rule, else every visible solid body); "
    "pull: [x, y, z] the mould's pull direction (default +Z), flip: the other way; checks: "
    "which checks (default all). Answers per body the rule, how many faces / edges each "
    "check found, and the issues (face or edge, with a ref selector, its centre and the "
    "value) up to limit. Nothing is added to the design.",
    schema(
        {
            "bodies": step_ids("the bodies (default: see above)"),
            "pull": kit.vector3("the pull direction (default [0, 0, 1])"),
            "flip": boolean("pull the other way", default=False),
            "checks": array(enum(ADVICE_CHECKS), "the checks to run (default all)", 1),
            "limit": kit.integer("the most issues listed", default=40, minimum=1, maximum=500),
        }
    ),
    changes=False,
    needs=("solid",),
    examples=[
        example({}, "every moulding issue of the design's plastic bodies"),
        example({"checks": ["draft"], "pull": [0, 0, 1]}, "faces without enough draft"),
    ],
)
