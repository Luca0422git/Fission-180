# SPDX-License-Identifier: LGPL-2.1-or-later
"""AI tools for the SURFACE tab, CONSTRUCT, ASSEMBLE and INSPECT. Pure Python (the work is
in fission180/ai/ops and fission180/ai/actions)."""

import copy

from . import kit
from .kit import (
    PICK_HELP,
    UNITS,
    angle,
    array,
    boolean,
    enum,
    length,
    number,
    obj,
    pick,
    schema,
    step_id,
    step_ids,
    string,
)
from .registry import define, example

# -- SURFACE ------------------------------------------------------------------------------------
SURFACE_KINDS = (
    "extrude",
    "revolve",
    "sweep",
    "loft",
    "patch",
    "ruled",
    "offset",
    "boundary_fill",
    "thicken",
    "trim",
    "untrim",
    "extend",
    "stitch",
    "unstitch",
    "reverse_normal",
)
SURFACE_OPTIONS = (
    "extrude: start, start_offset, direction one_side|two_sides|symmetric, measurement, "
    "extent distance|to_object|all, distance, distance2, taper, taper2, flip, operation "
    "new_body|new_component; revolve: type angle|to|full, direction, angle, angle2; sweep: "
    "type single|rail, distance, distance2, orientation, twist, taper, scaling; loft: guide, "
    "closed, merge, start_/end_condition, _weight, _angle; patch: continuity connected|"
    "tangent|curvature, weight, group_edges; ruled: ruled_type tangent|normal|direction, "
    "distance, angle, alternate, mitered; offset: distance; boundary_fill: remove_tools, "
    "operation join|cut|intersect|new_body; thicken: thickness, direction, thicken_type "
    "sharp|rounded, operation; untrim: loop_type all|internal|external, extend, distance; "
    "extend: distance, extend_type natural|perpendicular|tangent, alignment free|align; "
    "stitch: tolerance (mm), operation; every kind: chain (chain selection)."
)
_SURFACE_REF = kit.free_object(
    'one reference: {"sketch": id, "at": [x, y]} (a sketch curve, chained; "chain": false: '
    'alone; "tangent": true: through tangent joints only), {"sketch": id} (all its curves), '
    '{"plane": "XY"}, {"axis": "Z"}, {"step": id} (that step\'s body, whole), {"step": id, '
    '"faces": selector} or {"step": id, "edges": selector}'
)


def _check_surface_refs(specs, path, problems):
    for i, spec in enumerate(specs or []):
        where = "%s[%d]" % (path, i)
        if not isinstance(spec, dict):
            problems.append("%s must be an object" % where)
            continue
        kinds = [k for k in ("sketch", "plane", "axis", "step") if k in spec]
        if len(kinds) != 1:
            problems.append("%s needs exactly one of sketch, plane, axis, step" % where)
            continue
        for key, element in (("faces", "faces"), ("edges", "edges")):
            if key in spec:
                if "step" not in spec:
                    problems.append("%s.%s goes with step" % (where, key))
                kit.check_selector(spec[key], "%s.%s" % (where, key), element, problems)


def _extra_surface(args, problems):
    for key in ("refs", "refs2", "refs3"):
        _check_surface_refs(args.get(key), key, problems)
    kind = args.get("kind")
    if kind == "trim" and "remove" not in args:
        problems.append("trim needs remove: a point on each piece to take away")
    if kind == "boundary_fill" and "cells" not in args:
        problems.append("boundary_fill needs cells: a point inside each cell to keep")
    if kind == "reverse_normal" and "bodies" not in args:
        problems.append("reverse_normal needs bodies")


define(
    "surface",
    "Surface",
    "surface",
    "SURFACE > CREATE / MODIFY (Extrude, Revolve, Sweep, Loft, Patch, Ruled, Offset, "
    "Boundary Fill, Thicken, Trim, Untrim, Extend, Stitch, Unstitch, Reverse Normal)",
    "One of the SURFACE tab's tools (thin surface bodies with no volume; Thicken, Boundary "
    "Fill and Stitch make solids). kind picks the tool; refs / refs2 / refs3 are the dialog's "
    "selection boxes in order (profile, then path / axis / rails / tools...). options: the "
    "dialog's fields: " + SURFACE_OPTIONS + " remove (trim): [{step, at: [x, y, z]}] a point "
    "on each piece to take away; cells (boundary_fill): [[x, y, z], ...] a point in each cell "
    "kept; bodies (reverse_normal): step ids; target: the solid body a thicken / boundary "
    "fill joins or cuts. " + UNITS,
    schema(
        {
            "kind": enum(SURFACE_KINDS),
            "refs": array(_SURFACE_REF, "the first selection box", 1),
            "refs2": array(_SURFACE_REF, "the second selection box", 1),
            "refs3": array(_SURFACE_REF, "the third selection box", 1),
            "options": kit.free_object("the dialog's fields (see above)"),
            "remove": array(
                obj({"step": step_id(), "at": kit.point3()}, ["step", "at"]),
                "trim: the pieces to take away",
                1,
            ),
            "cells": array(kit.point3(), "boundary_fill: a point inside each cell", 1),
            "bodies": step_ids("reverse_normal: the bodies"),
            "target": step_id("thicken / boundary_fill: the solid body it joins or cuts"),
        },
        ["kind"],
    ),
    op="sf_surface",
    extra=_extra_surface,
    id_base="Surface",
    needs=(),
    title_fn=lambda a: "AI: Surface %s" % str(a.get("kind", "")).replace("_", " "),
    examples=[
        example(
            {
                "kind": "extrude",
                "refs": [{"sketch": "Sketch1", "at": [10, 0]}],
                "options": {"distance": 20},
            },
            "a 20 mm surface from a sketch curve",
        ),
        example(
            {"kind": "thicken", "refs": [{"step": "Surface1"}], "options": {"thickness": 2}},
            "turn the surface into a 2 mm solid",
        ),
    ],
)

# SURFACE > MODIFY on surface bodies (fission180/surfmod.py, the code its dialogs run): the
# tool's kind -> (the step's kind, what it picks, the options it takes)
SURFACE_MODIFY = {
    "fillet": (
        "surface_fillet",
        "edges",
        ("radius", "radius_type", "radius2", "tangent_chain"),
    ),
    "chamfer": (
        "surface_chamfer",
        "edges",
        ("chamfer_type", "distance", "distance2", "angle", "flip", "tangent_chain"),
    ),
    "press_pull": ("surface_press_pull", "faces", ("distance",)),
    "delete_face": ("surface_delete_face", "faces", ()),
    "merge": ("surface_merge", "faces", ()),
}
_SURFACE_MODIFY_VALUES = (
    "radius",
    "radius_type",
    "radius2",
    "tangent_chain",
    "chamfer_type",
    "distance",
    "distance2",
    "angle",
    "flip",
)


def _extra_surface_modify(args, problems):
    kind = args.get("kind")
    if kind not in SURFACE_MODIFY:
        return
    _step_kind, what, takes = SURFACE_MODIFY[kind]
    other = "faces" if what == "edges" else "edges"
    if what not in args:
        problems.append("kind %s needs %s (a selector)" % (kind, what))
    if other in args:
        problems.append("kind %s picks %s, not %s" % (kind, what, other))
    for key in _SURFACE_MODIFY_VALUES:
        if key in args and key not in takes:
            problems.append("%s is not a value of kind %s" % (key, kind))
    if kind == "press_pull" and "distance" not in args:
        problems.append("press_pull needs distance (mm: + pulls, - pushes)")
    if kind == "fillet" and args.get("radius_type") == "variable" and "radius2" not in args:
        problems.append("radius_type variable needs radius2 (the end radius)")
    if kind == "chamfer":
        ctype = args.get("chamfer_type", "equal")
        if ctype == "two" and "distance2" not in args:
            problems.append("chamfer_type two needs distance2")
        if ctype == "angle" and "angle" not in args:
            problems.append("chamfer_type angle needs angle")


def _steps_surface_modify(a, sid):
    step_kind, what, takes = SURFACE_MODIFY[a["kind"]]
    steps = []
    if "body" in a:
        steps.append({"op": "use_body", "step": a["body"]})
    step = {"op": "sf_surface_modify", "id": sid, "kind": step_kind}
    step[what] = copy.deepcopy(a[what])
    options = {k: a[k] for k in takes if k in a}
    if options:
        step["options"] = options
    return steps + [step]


define(
    "surface_modify",
    "Surface modify",
    "surface",
    "SURFACE > MODIFY (Fillet, Chamfer, Press Pull, Delete, Merge on surface bodies)",
    "The SURFACE tab's Fillet, Chamfer, Press Pull, Delete and Merge on a surface body (open "
    "faces, no volume, made with the surface tool; for a solid use fillet, chamfer, press_pull "
    "and delete_face). body: the surface body (a step in it; default the active body: the "
    "last one made or activated). kind fillet: edges (each "
    "between two faces of the body), radius (mm, default 1), radius_type constant | chord "
    "(radius is the chord's length) | variable (radius at each edge's start, radius2 at its "
    "end), tangent_chain (default true). kind chamfer: edges, chamfer_type equal | two "
    "(distance2 on the edge's second face) | angle (angle degrees), distance (mm, default 1), "
    "flip, tangent_chain. kind press_pull: faces, distance (mm; + pulls the face out along "
    "its normal, - pushes it in; the faces around it follow). kind delete_face: faces taken "
    "away without healing the hole. kind merge: faces of the body that lie on one surface "
    "become one face. Surface bodies have no volume: inspect_design and diff_design give "
    "their area_mm2 and faces to check the result.",
    schema(
        {
            "kind": enum(sorted(SURFACE_MODIFY)),
            "body": step_id("the surface body (default: the active body)"),
            "edges": kit.selector("fillet / chamfer: the edges", "edges"),
            "faces": kit.selector("press_pull / delete_face / merge: the faces"),
            "radius": kit.positive("fillet: mm", default=1),
            "radius_type": enum(["constant", "chord", "variable"], default="constant"),
            "radius2": kit.positive("fillet, variable: the end radius (mm)"),
            "tangent_chain": boolean("take the edges tangent to them too", default=True),
            "chamfer_type": enum(["equal", "two", "angle"], default="equal"),
            "distance": number("chamfer: mm (above 0); press_pull: mm, + pulls, - pushes"),
            "distance2": kit.positive("chamfer two: the second distance (mm)"),
            "angle": number("chamfer angle: degrees", above=0, maximum=89.999),
            "flip": boolean("chamfer: swap the two faces' distances", default=False),
        },
        ["kind"],
    ),
    ops=["sf_surface_modify", "use_body"],
    steps=_steps_surface_modify,
    extra=_extra_surface_modify,
    id_base="SurfaceModify",
    title_fn=lambda a: "AI: Surface %s" % str(a.get("kind", "")).replace("_", " "),
    examples=[
        example(
            {
                "kind": "fillet",
                "edges": {"parallel": [0, 0, 1], "count": 4},
                "radius": 3,
            },
            "round the four vertical corners of an open box of surfaces",
        ),
        example(
            {"kind": "press_pull", "faces": {"normal": [0, 0, 1], "count": 1}, "distance": -5},
            "push the box's floor 5 mm down (the walls grow)",
        ),
        example(
            {"kind": "merge", "faces": {"parallel": [0, 1, 0], "count": 2}},
            "two faces in one plane become one face",
        ),
    ],
)

# -- CONSTRUCT ----------------------------------------------------------------------------------
PLANE_PRESETS = (
    "OffsetPlane",
    "PlaneAtAngle",
    "TangentPlane",
    "Midplane",
    "PlaneTwoEdges",
    "PlaneThreePoints",
    "PlaneAtPoint",
    "PlaneAlongPath",
)
AXIS_PRESETS = ("AxisCylinder", "AxisNormal", "AxisTwoPlanes", "AxisTwoPoints", "AxisEdge")
POINT_PRESETS = (
    "PointVertex",
    "PointTwoEdges",
    "PointThreePlanes",
    "PointCenter",
    "PointEdgePlane",
    "PointAlongPath",
)
PRESET_REFS = {
    "OffsetPlane": "a plane or flat face (and, extent To Object, a point)",
    "PlaneAtAngle": "a line (edge, sketch line or axis)",
    "TangentPlane": "a round face",
    "Midplane": "two planes / flat faces",
    "PlaneTwoEdges": "two lines in one plane",
    "PlaneThreePoints": "three points",
    "PlaneAtPoint": "a face and a point",
    "PlaneAlongPath": "an edge or sketch curve",
    "AxisCylinder": "a round face or circular edge",
    "AxisNormal": "a face (and optionally a point)",
    "AxisTwoPlanes": "two planes / flat faces",
    "AxisTwoPoints": "two points",
    "AxisEdge": "a straight edge or sketch line",
    "PointVertex": "a corner or sketch point",
    "PointTwoEdges": "two edges that cross",
    "PointThreePlanes": "three planes / flat faces",
    "PointCenter": "a circular edge or a ball",
    "PointEdgePlane": "an edge and a plane it crosses",
    "PointAlongPath": "an edge or sketch curve",
}


def _construct_tool(name, title, ribbon, presets, what, base):
    def extra(args, problems):
        for i, spec in enumerate(args.get("refs") or []):
            kit.check_pick(spec, "refs[%d]" % i, problems)
        points = args.get("points")
        if points is not None and len(points) > len(args.get("refs") or []):
            problems.append("points has more entries than refs")

    def steps(a, sid):
        step = {
            "op": "construct",
            "id": sid,
            "preset": a["preset"],
            "refs": copy.deepcopy(a["refs"]),
        }
        values = {k: a[k] for k in ("distance", "angle", "fraction", "distance_type") if k in a}
        if values:
            step["values"] = values
        if "points" in a:
            step["points"] = copy.deepcopy(a["points"])
        return [step]

    lines = "; ".join("%s: %s" % (p, PRESET_REFS[p]) for p in presets)
    define(
        name,
        title,
        "construct",
        ribbon,
        "Make a construction %s (Fusion's CONSTRUCT menu) the way its dialog does; it follows "
        "what it is built on when the part changes and other tools can use it (sketch on a "
        'plane with create_sketch on, pick it with {"construct": id}). preset and its refs: '
        "%s. distance (mm, OffsetPlane), angle (degrees, PlaneAtAngle / TangentPlane), "
        "fraction (0..1 along the path), distance_type physical | proportional (along a "
        "path); points: where each face was clicked ([x, y, z] or null, per ref). %s"
        % (what, lines, PICK_HELP),
        schema(
            {
                "preset": enum(presets),
                "refs": array(pick("one reference"), "what it is built on, in order", 1, 3),
                "distance": length("OffsetPlane distance"),
                "angle": angle("PlaneAtAngle / TangentPlane"),
                "fraction": number("0..1 along a path", minimum=0, maximum=1),
                "distance_type": enum(["physical", "proportional"]),
                "points": array(
                    {"type": ["array", "null"], "items": {"type": "number"}},
                    "per ref: the point clicked on a face, or null",
                ),
            },
            ["preset", "refs"],
        ),
        ops=["construct"],
        steps=steps,
        extra=extra,
        id_base=base,
        title_fn=lambda a, t=title: "AI: %s" % t,
        examples=[
            example(*e)
            for e in {
                "construct_plane": [
                    (
                        {"preset": "OffsetPlane", "refs": [{"plane": "XY"}], "distance": 25},
                        "a plane 25 mm above XY",
                    )
                ],
                "construct_axis": [
                    (
                        {
                            "preset": "AxisCylinder",
                            "refs": [{"face": {"type": "cylinder", "count": 1}}],
                        },
                        "the axis of a round face",
                    )
                ],
                "construct_point": [
                    (
                        {
                            "preset": "PointCenter",
                            "refs": [{"edge": {"type": "circle", "count": 1}}],
                        },
                        "the centre of a circular edge",
                    )
                ],
            }[name]
        ],
    )


_construct_tool(
    "construct_plane",
    "Construction plane",
    "SOLID > CONSTRUCT > (planes)",
    PLANE_PRESETS,
    "plane",
    "Plane",
)
_construct_tool(
    "construct_axis",
    "Construction axis",
    "SOLID > CONSTRUCT > (axes)",
    AXIS_PRESETS,
    "axis",
    "Axis",
)
_construct_tool(
    "construct_point",
    "Construction point",
    "SOLID > CONSTRUCT > (points)",
    POINT_PRESETS,
    "point",
    "Point",
)

# -- ASSEMBLE -----------------------------------------------------------------------------------
define(
    "new_component",
    "New component",
    "assemble",
    "ASSEMBLE > New Component",
    "Make a new, empty component (Fusion's New Component) with its own body, inside parent "
    "(a component id) or at the top of the design; it becomes the active component, so the "
    "next sketches and features go into it. label names it.",
    schema({"label": string("its name"), "parent": step_id("the component it goes into")}),
    needs=(),
    id_base="Component",
    title_fn=lambda a: "AI: New component %s" % a.get("label", ""),
    examples=[example({"label": "Lid"}, "a component called Lid, active")],
)
define(
    "components_from_bodies",
    "Components from bodies",
    "assemble",
    "BROWSER > a body > Create Components from Bodies",
    "Put bodies into components of their own (one component per body), so joints can move "
    "them. bodies: step ids; label names the component (one body).",
    schema(
        {"bodies": step_ids("the bodies"), "label": string("the new component's name")}, ["bodies"]
    ),
    op="components_from_bodies",
    id_base="Component",
    title_fn=lambda a: "AI: Components from bodies",
    examples=[example({"bodies": ["Extrude1"], "label": "Base"}, "Extrude1's body as Base")],
)
define(
    "copy_component",
    "Copy / paste component",
    "assemble",
    "Copy (Ctrl+C) a component, then Paste / Paste New",
    "Copy a component and paste it: new false (default) makes a linked instance (it changes "
    "with the original, Fusion's Paste), new true an independent copy (Paste New); moved by "
    "dx / dy / dz (mm).",
    schema(
        {
            "component": step_id("the component"),
            "new": boolean("Paste New: an independent copy", default=False),
            "dx": length(default=0),
            "dy": length(default=0),
            "dz": length(default=0),
        },
        ["component"],
    ),
    op="component_paste",
    id_base="Copy",
    title_fn=lambda a: "AI: Paste%s %s" % (" New" if a.get("new") else "", a.get("component", "")),
    examples=[example({"component": "Bolt", "dx": 30}, "a linked copy of Bolt 30 mm along X")],
)
define(
    "activate",
    "Activate body / component",
    "assemble",
    "BROWSER > a body or component > Activate",
    "Make a body (by any step in it) or a component the one you work in: the next sketches "
    "and features go into it (Fusion's Activate Component). Not an undo step: activate the "
    "previous one again to go back (undo would take back the step before it).",
    schema({"target": step_id("a body, a step in it, or a component")}, ["target"]),
    ops=["use_body"],
    own_id=False,
    title_fn=lambda a: "AI: Activate %s" % a.get("target", ""),
    examples=[example({"target": "Extrude2"}, "work in Extrude2's body")],
)
define(
    "new_body",
    "New body",
    "assemble",
    "BROWSER > Bodies > New Body",
    "Make a new, empty body in the active component and make it the active body: the next "
    "sketch and extrude go into it. label names it.",
    schema({"label": string("its name")}),
    needs=(),
    id_base="Body",
    title_fn=lambda a: "AI: New body",
    examples=[example({"label": "Insert"}, "a new body called Insert")],
)

_JOINT_SIDE = obj(
    {
        "component": step_id("the component or body this side is on (a step in it works)"),
        "face": kit.selector("the face clicked (on that component)"),
        "edge": kit.selector("the edge clicked", "edges"),
        "vertex": kit.point3("the corner clicked"),
        "snap": enum(
            ["centre", "vertex", "midpoint", "circle", "point", "origin"],
            "which snap point of the element (default: the nearest to point, else " "its centre)",
        ),
        "point": kit.point3("where on the element (design coordinates)"),
    },
    ["component"],
    "one side of a joint: a component and an element of it with a snap point",
)


def _extra_joint(args, problems):
    for key in ("first", "second"):
        side = args.get(key)
        if not isinstance(side, dict):
            continue
        kinds = [k for k in ("face", "edge", "vertex") if k in side]
        if len(kinds) > 1:
            problems.append("%s: give one of face, edge, vertex" % key)
        if "face" in side:
            kit.check_selector(side["face"], key + ".face", "faces", problems)
        if "edge" in side:
            kit.check_selector(side["edge"], key + ".edge", "edges", problems)


define(
    "joint",
    "Joint",
    "assemble",
    "ASSEMBLE > Joint (J)",
    "Fusion's Joint: the first component moves so that its snap point meets the second's. "
    "type rigid | revolute | slider | cylindrical | pinslot | planar | ball; first / second: "
    "{component, face | edge | vertex, snap, point}: the element is found on that component "
    "with a selector, snap picks which of its snap points (centre of a circle or face, "
    "vertex, midpoint...). offset x / y / z (mm), angle (degrees), flip; rotate / slide: the "
    "motion axis x | y | z. Answers where the component went and whether the joint holds.",
    schema(
        {
            "type": enum(
                ["rigid", "revolute", "slider", "cylindrical", "pinslot", "planar", "ball"],
                default="rigid",
            ),
            "first": _JOINT_SIDE,
            "second": _JOINT_SIDE,
            "offset": kit.numbers(3, "[x, y, z] offset of the joint origin (mm)"),
            "angle": angle(default=0),
            "flip": boolean(default=False),
            "rotate": enum(["x", "y", "z"], "the rotation axis"),
            "slide": enum(["x", "y", "z"], "the slide axis"),
        },
        ["first", "second"],
    ),
    extra=_extra_joint,
    id_base="Joint",
    title_fn=lambda a: "AI: Joint (%s)" % a.get("type", "rigid"),
    examples=[
        example(
            {
                "type": "revolute",
                "first": {
                    "component": "Wheel",
                    "face": {"type": "cylinder", "count": 1},
                    "snap": "circle",
                },
                "second": {
                    "component": "Axle",
                    "face": {"type": "cylinder", "count": 1},
                    "snap": "circle",
                },
            },
            "the wheel turns on the axle",
        )
    ],
)


def _extra_drive(args, problems):
    if "angle" not in args and "slide" not in args:
        problems.append("give angle and / or slide")


define(
    "drive_joint",
    "Drive joint",
    "assemble",
    "ASSEMBLE > Drive Joints",
    "Put a joint at an angle (degrees) and / or slide distance (mm), within its limits; "
    "what hangs on it follows. joint: its id.",
    schema({"joint": step_id("the joint"), "angle": angle(), "slide": length()}, ["joint"]),
    extra=_extra_drive,
    own_id=False,
    title_fn=lambda a: "AI: Drive joint %s" % a.get("joint", ""),
    examples=[example({"joint": "Joint", "angle": 45}, "turn the first joint (id Joint) to 45 degrees")],
)
define(
    "ground",
    "Ground / unground",
    "assemble",
    "BROWSER > a component > Ground",
    "Ground a component (it never moves when joints solve) or unground it (ground: false).",
    schema(
        {"component": step_id("the component or body"), "ground": boolean(default=True)},
        ["component"],
    ),
    own_id=False,
    title_fn=lambda a: "AI: %s %s"
    % ("Ground" if a.get("ground", True) else "Unground", a.get("component", "")),
    examples=[example({"component": "Base"}, "the base stays put")],
)

# -- INSPECT ------------------------------------------------------------------------------------
define(
    "physical_properties",
    "Physical properties",
    "inspect",
    "BROWSER > a body > Properties (INSPECT)",
    "Physical properties of bodies, as Fusion's Properties: volume (mm3), area (mm2), "
    "material and density, mass (g), centre of mass and bounding box (mm), number of faces, "
    "edges and solids, and whether the solid is valid. bodies: step ids (default every body).",
    schema({"bodies": step_ids("the bodies (default: all)")}),
    changes=False,
    examples=[example({}, "every body's mass, volume and centre of mass")],
)
define(
    "center_of_mass",
    "Center of mass",
    "inspect",
    "INSPECT > Center of Mass",
    "The centre of mass of bodies together (Fusion's Center of Mass), weighted by their "
    "materials. bodies: step ids (default every body).",
    schema({"bodies": step_ids("the bodies (default: all)")}),
    changes=False,
    needs=("solid",),
    examples=[example({}, "where the whole design balances")],
)
define(
    "interference",
    "Interference",
    "inspect",
    "INSPECT > Interference",
    "Find where bodies overlap (Fusion's Interference): every pair that overlaps with the "
    "overlapping volume (mm3). bodies: step ids (default every body); include_coincident: "
    "count bodies that only touch.",
    schema(
        {
            "bodies": step_ids("the bodies (default: all)"),
            "include_coincident": boolean(default=False),
        }
    ),
    changes=False,
    needs=("solid",),
    examples=[example({}, "do any parts collide?")],
)
define(
    "section_analysis",
    "Section analysis",
    "inspect",
    "INSPECT > Section Analysis",
    "Cut the design with a plane to look inside (Fusion's Section Analysis): plane (a pick: "
    "an origin plane or a flat face), distance (offset, mm), x_angle / y_angle (tilt, "
    "degrees), flip. Answers the volume kept (on the side the plane's normal points away "
    "from) and the area of the cut faces; nothing is left in the design.",
    schema(
        {
            "plane": pick("the section plane"),
            "distance": length(default=0),
            "x_angle": angle(default=0),
            "y_angle": angle(default=0),
            "flip": boolean(default=False),
        },
        ["plane"],
    ),
    changes=False,
    needs=("solid",),
    examples=[example({"plane": {"plane": "XZ"}, "distance": 5}, "a cut 5 mm from XZ")],
)
