# SPDX-License-Identifier: LGPL-2.1-or-later
"""AI tools for the DESIGN workspace's commands that had none before wave 8 (builder
ai-design): ASSEMBLE (As-built Joint, Joint Origin, Rigid Group, Duplicate With Joints,
Motion Link, contact sets, Motion Study, Capture / Revert Position), INSERT (Decal, Canvas,
Insert SVG, Derive / Insert Derive), CONSTRUCT (User Coordinate System), SOLID (Create /
Finish Base Feature, Compute All) and INSPECT (the eight surface analyses with numbers,
Display Component Colors). Pure Python: the work is in fission180/ai/actions
(assemble_actions, design2_actions, analysis_actions), which call the same Fission 180 code
as the dialogs (joints.py, decal.py, insert.py, derive.py, direct.py, surface_analysis.py)."""

from . import kit
from .kit import (
    angle,
    array,
    boolean,
    either,
    enum,
    integer,
    length,
    number,
    obj,
    pick,
    positive,
    schema,
    step_id,
    step_ids,
    string,
)
from .more_tools import _JOINT_SIDE
from .registry import define, example

JOINT_TYPES = ("rigid", "revolute", "slider", "cylindrical", "pinslot", "planar", "ball")


def _check_side(side, path, problems):
    if not isinstance(side, dict):
        return
    if len([k for k in ("face", "edge", "vertex", "joint_origin") if k in side]) > 1:
        problems.append("%s: give one of face, edge, vertex, joint_origin" % path)
    if "face" in side:
        kit.check_selector(side["face"], path + ".face", "faces", problems)
    if "edge" in side:
        kit.check_selector(side["edge"], path + ".edge", "edges", problems)


# -- ASSEMBLE -----------------------------------------------------------------------------------
def _extra_as_built(args, problems):
    comps = args.get("components") or []
    if len(comps) == 2 and comps[0] == comps[1]:
        problems.append("components must be two different components")
    if args.get("type", "rigid") != "rigid" and "position" not in args:
        problems.append(
            "type %s needs position: a snap point on one of the two components (the axis of "
            "the motion goes through it)" % args.get("type")
        )
    _check_side(args.get("position"), "position", problems)


define(
    "as_built_joint",
    "As-built joint",
    "assemble",
    "ASSEMBLE > As-built Joint",
    "Join two components WHERE THEY STAND NOW (nothing moves), Fusion's As-built Joint: "
    "for parts already modelled in place. For parts that must be brought together, use "
    "joint. type rigid | revolute | slider | cylindrical | pinslot | planar | ball; "
    "components: the two (a body or step in each works); position (every type but rigid): "
    "{component, face | edge | vertex, snap, point} on one of the two, the joint's origin and "
    "axis (a revolute turns about the axis of the round face or circle picked). Answers the "
    "joint's id and whether it holds; drive_joint moves it.",
    schema(
        {
            "type": enum(JOINT_TYPES, default="rigid"),
            "components": array(step_id(), "the two components, as they stand", 2, 2),
            "position": _JOINT_SIDE,
        },
        ["components"],
    ),
    extra=_extra_as_built,
    id_base="Joint",
    title_fn=lambda a: "AI: As-built joint (%s)" % a.get("type", "rigid"),
    examples=[
        example(
            {
                "type": "revolute",
                "components": ["Lid", "Box"],
                "position": {
                    "component": "Box",
                    "edge": {"type": "circle", "count": 1},
                    "snap": "circle",
                },
            },
            "the lid hinges on the box's round hinge pin, where it is",
        ),
        example({"components": ["Bracket", "Base"]}, "lock the bracket to the base as it is"),
    ],
)


def _extra_joint_origin(args, problems):
    _check_side(args.get("at"), "at", problems)


define(
    "joint_origin",
    "Joint origin",
    "assemble",
    "SOLID > CREATE > Joint Origin (and ASSEMBLE > Joint Origin)",
    "Put a joint origin on a component (Fusion's Joint Origin): a saved snap point with axes "
    "that moves with its geometry, for a joint where no edge or face gives the right point. "
    "at: {component, face | edge | vertex, snap, point} as in joint; offset [x, y, z] (mm) "
    "and angle (degrees about its Z) move it from the snap; flip turns its Z over. Answers "
    "its id and where it is (design coordinates).",
    schema(
        {
            "at": _JOINT_SIDE,
            "offset": kit.numbers(3, "[x, y, z] moved from the snap point (mm)"),
            "angle": angle("turned about its Z", default=0),
            "flip": boolean("its Z the other way", default=False),
        },
        ["at"],
    ),
    extra=_extra_joint_origin,
    id_base="JointOrigin",
    title_fn=lambda a: "AI: Joint origin",
    examples=[
        example(
            {
                "at": {"component": "Base", "face": {"normal": [0, 0, 1], "count": 1}},
                "offset": [0, 0, 5],
            },
            "a joint origin 5 mm above the centre of the base's top face",
        )
    ],
)


def _extra_members(args, problems):
    comps = args.get("components") or []
    if len(set(c for c in comps if isinstance(c, str))) != len(comps):
        problems.append("components lists a component twice")


define(
    "rigid_group",
    "Rigid group",
    "assemble",
    "ASSEMBLE > Rigid Group",
    "Lock two or more components together where they stand (Fusion's Rigid Group): they move "
    "as one when joints or drags move any of them. Quicker than a rigid joint per pair. "
    "include_children: the components inside them are locked too (default true).",
    schema(
        {
            "components": array(step_id(), "the components to lock together", 2),
            "include_children": boolean("their sub-components too", default=True),
        },
        ["components"],
    ),
    extra=_extra_members,
    id_base="RigidGroup",
    title_fn=lambda a: "AI: Rigid group",
    examples=[example({"components": ["Screw", "Nut"]}, "the screw and its nut move as one")],
)


def _extra_motion_link(args, problems):
    values = args.get("values") or []
    if len(values) == 2 and kit.is_type(values[0], "number") and abs(values[0]) < 1e-12:
        problems.append("values[0] cannot be 0: how far the first joint moves")


define(
    "motion_link",
    "Motion link",
    "assemble",
    "ASSEMBLE > Motion Link",
    "Tie two joints' motions (Fusion's Motion Link): when the first moves values[0], the "
    "second moves values[1] (degrees for turning joints, mm for sliding ones): a gear pair "
    "[360, -720], a rack and pinion [360, 62.83]. The same joint twice ties its turn to its "
    "slide (a screw: [360, 1.5] for a 1.5 mm pitch, on a cylindrical or pin-slot joint). "
    "motions: which motion of each joint (angle | slide; default its own: a slider's slide, "
    "else its angle); reverse flips the second. Check it with drive_joint on the first.",
    schema(
        {
            "joints": array(
                step_id(), "the two joints (the same id twice: Link with Same Joint)", 2, 2
            ),
            "values": array(kit.number(), "[first, second] (degrees or mm)", 2, 2),
            "reverse": boolean("the second moves the other way", default=False),
            "motions": array(enum(["angle", "slide"]), "[first, second]", 2, 2),
        },
        ["joints", "values"],
    ),
    extra=_extra_motion_link,
    id_base="MotionLink",
    title_fn=lambda a: "AI: Motion link",
    examples=[
        example(
            {"joints": ["Joint1", "Joint2"], "values": [360, -720]},
            "the second gear turns twice as fast, the other way",
        )
    ],
)


def _extra_contact(args, problems):
    if "mode" not in args and "new_set" not in args:
        problems.append("give mode and / or new_set")
    _extra_members({"components": args.get("new_set") or []}, problems)


define(
    "contact",
    "Contact sets",
    "assemble",
    "ASSEMBLE > Enable Contact Sets / Enable All Contact / Disable Contact / New Contact Set",
    "Fusion's contact: with contact on, components stop where they touch when a joint is "
    "driven or dragged. mode off (Disable Contact) | sets (Enable Contact Sets: only "
    "components in a set stop on each other) | all (Enable All Contact: every component; slow "
    "on big assemblies); new_set: two or more components that stop on each other (New Contact "
    "Set; it acts while mode is sets). Answers the mode and the sets. drive_joint then stops "
    "at the touching point.",
    schema(
        {
            "mode": enum(["off", "sets", "all"]),
            "new_set": array(step_id(), "components that stop on each other", 2),
        }
    ),
    extra=_extra_contact,
    own_id=False,
    title_fn=lambda a: "AI: Contact %s" % (a.get("mode") or "set"),
    examples=[
        example(
            {"mode": "sets", "new_set": ["Arm", "Stop"]},
            "the arm stops when it hits the stop",
        )
    ],
)
define(
    "position",
    "Capture / revert position",
    "assemble",
    "ASSEMBLE > Capture Position / Revert Position",
    "After components were moved by drive_joint or move_copy: capture keeps them where they "
    "are now (a Position step in the timeline, Fusion's Capture Position); revert puts them "
    "back where the last capture (or the joints) left them. Answers where each component "
    "stands.",
    schema({"action": enum(["capture", "revert"])}, ["action"]),
    own_id=False,
    title_fn=lambda a: "AI: %s position" % str(a.get("action", "")).capitalize(),
    examples=[example({"action": "capture"}, "keep the assembly as it stands now")],
)


def _extra_duplicate(args, problems):
    for i, side in enumerate(args.get("at") or []):
        _check_side(side, "at[%d]" % i, problems)


define(
    "duplicate_with_joints",
    "Duplicate with joints",
    "assemble",
    "ASSEMBLE > Duplicate With Joints",
    "Copy jointed components to new places, joined there (Fusion's Duplicate With Joints): a "
    "screw (and its nut) into more holes. components: the jointed ones to copy (linked "
    "copies); joint: the open joint (from them to something outside; default: the only one); "
    "at: one place per copy, {component, face | edge | vertex, snap, point} as joint's second "
    "side (the hole's circular edge, snap circle). Joints and rigid groups between the copied "
    "components are copied too. Answers the copies' ids and where they went.",
    schema(
        {
            "components": array(step_id(), "the jointed components to copy", 1),
            "joint": step_id("the open joint the copies are joined with"),
            "at": array(_JOINT_SIDE, "one new place per copy", 1),
        },
        ["components", "at"],
    ),
    extra=_extra_duplicate,
    id_base="Duplicate",
    title_fn=lambda a: "AI: Duplicate with joints",
    examples=[
        example(
            {
                "components": ["Screw"],
                "at": [
                    {
                        "component": "Plate",
                        "edge": {"type": "circle", "at": {"axis": "x", "value": 30}, "count": 1},
                        "snap": "circle",
                    }
                ],
            },
            "a second screw in the hole at x = 30",
        )
    ],
)

_KEY = obj(
    {
        "joint": step_id("the joint"),
        "step": number("0 .. 100", minimum=0, maximum=100),
        "value": number("degrees (turns) or mm (slides)"),
    },
    ["joint", "step", "value"],
    "one point: the joint's value at a step",
)


def _extra_study(args, problems):
    names = set(args.get("joints") or [])
    for i, key in enumerate(args.get("keys") or []):
        if isinstance(key, dict) and key.get("joint") not in names:
            problems.append("keys[%d].joint must be one of joints" % i)


define(
    "motion_study",
    "Motion study",
    "assemble",
    "ASSEMBLE > Motion Study",
    "Fusion's Motion Study: joints driven together over steps 0..100 by key values, kept in "
    "the design to play back (browser). joints: the joints; keys: [{joint, step, value}] "
    "(degrees or mm; between keys the value goes straight from one to the next; a joint "
    "without a key at 0 starts where it is); mode once | loop | pingpong, speed. report: the "
    "steps whose component positions the answer gives (default [0, 50, 100]); after it the "
    "assembly is put back as it was. Checks a mechanism's travel without moving it.",
    schema(
        {
            "joints": array(step_id(), "the joints it drives", 1),
            "keys": array(_KEY, "the key values", 1),
            "mode": enum(["once", "loop", "pingpong"], default="once"),
            "speed": positive("playback speed (1: 4 s for 100 steps)", default=1),
            "report": array(number(minimum=0, maximum=100), "steps to report (0..100)", 1, 11),
        },
        ["joints", "keys"],
    ),
    extra=_extra_study,
    id_base="MotionStudy",
    title_fn=lambda a: "AI: Motion study",
    examples=[
        example(
            {
                "joints": ["Joint1"],
                "keys": [
                    {"joint": "Joint1", "step": 0, "value": 0},
                    {"joint": "Joint1", "step": 100, "value": 90},
                ],
            },
            "turn Joint1 from 0 to 90 degrees",
        )
    ],
)

# -- INSERT -------------------------------------------------------------------------------------
_PLANE = either(
    'where it goes: "XY" | "XZ" | "YZ" (an origin plane), {"face": selector} (a flat face '
    'of the active body; "of": a step id for another body) or {"construct": id} (a '
    "construction plane)"
)


def _check_plane(spec, path, problems):
    if spec is None:
        return
    if isinstance(spec, str):
        if spec not in kit.PLANES:
            problems.append('%s must be XY, XZ, YZ, {"face": selector} or {"construct": id}' % path)
        return
    if not isinstance(spec, dict):
        return
    keys = set(spec)
    if keys in ({"face"}, {"face", "of"}):
        kit.check_selector(spec["face"], path + ".face", "faces", problems)
        if "of" in spec and not isinstance(spec["of"], str):
            problems.append("%s.of must be a step id" % path)
    elif keys == {"construct"}:
        if not isinstance(spec["construct"], str):
            problems.append("%s.construct must be the id of a construction plane" % path)
    else:
        problems.append('%s must be XY, XZ, YZ, {"face": selector} or {"construct": id}' % path)


def _extra_decal(args, problems):
    if "scale" in args and ("scale_x" in args or "scale_y" in args):
        problems.append("give scale or scale_x / scale_y, not both")
    if "width" in args and ("scale" in args or "scale_x" in args):
        problems.append("give width or a scale, not both")


_IMAGE = string("full path of a PNG, JPEG, BMP, GIF or TIFF image")
define(
    "decal",
    "Decal",
    "import_export",
    "INSERT > Decal",
    "Stick a picture on a face (Fusion's Decal): a label, a logo. It follows the face when "
    "the part changes and wraps onto tangent faces (chain_faces). Only the look changes: no "
    "geometry, no volume (use emboss or sketch_text + extrude for raised letters). image: a "
    "full path; face: a selector of one face of body (default the active body); point: where "
    "on the face its middle goes ([x, y, z], default the face's centre); width (mm, height "
    "follows) or scale / scale_x / scale_y; dx / dy (mm), angle (degrees), opacity (0..100), "
    "flip_h / flip_v. Answers its id, size and the face it is on.",
    schema(
        {
            "image": _IMAGE,
            "face": kit.selector("the face it goes on"),
            "body": step_id("the body (default: the active body)"),
            "point": kit.point3("where on the face its middle goes"),
            "width": positive("its width (mm); the height keeps the picture's proportions"),
            "scale": positive("both directions"),
            "scale_x": positive("width factor"),
            "scale_y": positive("height factor"),
            "dx": length("moved along the face", default=0),
            "dy": length("moved across the face", default=0),
            "angle": angle("turned on the face", default=0),
            "opacity": integer("0 (clear) .. 100 (solid)", 100, 0, 100),
            "chain_faces": boolean("wraps onto tangent faces", default=True),
            "flip_h": boolean(default=False),
            "flip_v": boolean(default=False),
            "name": string("its name in the browser"),
        },
        ["image", "face"],
    ),
    extra=_extra_decal,
    id_base="Decal",
    title_fn=lambda a: "AI: Decal %s" % str(a.get("image", "")).replace("\\", "/").split("/")[-1],
    examples=[
        example(
            {"image": "/home/me/logo.png", "face": {"normal": [0, 0, 1], "count": 1}, "width": 30},
            "a 30 mm wide logo on the top face",
        )
    ],
)


def _extra_canvas(args, problems):
    _check_plane(args.get("plane"), "plane", problems)


define(
    "canvas",
    "Canvas",
    "import_export",
    "INSERT > Canvas",
    "Put a reference picture on a plane (Fusion's Canvas): a photo or drawing to sketch over. "
    "It is not part of the model (no geometry, not in the timeline). plane: XY | XZ | YZ, "
    '{"face": selector} or {"construct": id}; width: its width in mm (calibrate a photo: '
    "the real size of what it shows); dx / dy (mm) move it on the plane, angle (degrees); "
    "opacity (0..100, default 50), display_through (seen through bodies, default true), "
    "flip_h / flip_v. Answers its id and size; create_sketch on the same plane draws over it.",
    schema(
        {
            "image": _IMAGE,
            "plane": _PLANE,
            "width": positive("its width (mm); the height keeps the picture's proportions"),
            "dx": length(default=0),
            "dy": length(default=0),
            "angle": angle(default=0),
            "opacity": integer("0 (clear) .. 100 (solid)", 50, 0, 100),
            "display_through": boolean("seen through the bodies in front", default=True),
            "flip_h": boolean(default=False),
            "flip_v": boolean(default=False),
            "name": string("its name in the browser"),
        },
        ["image", "plane"],
    ),
    extra=_extra_canvas,
    id_base="Canvas",
    title_fn=lambda a: "AI: Canvas %s" % str(a.get("image", "")).replace("\\", "/").split("/")[-1],
    examples=[
        example(
            {"image": "/home/me/side_photo.jpg", "plane": "XZ", "width": 180, "opacity": 40},
            "a side photo, 180 mm wide, behind the XZ plane",
        )
    ],
)


def _extra_svg(args, problems):
    if ("plane" in args) == ("sketch" in args):
        problems.append("give plane (a new sketch there) or sketch (an existing one), one of them")
    _check_plane(args.get("plane"), "plane", problems)
    path = args.get("path")
    if isinstance(path, str) and not path.lower().endswith((".svg", ".dxf")):
        problems.append("path must be an .svg or .dxf file")


define(
    "insert_svg",
    "Insert SVG / DXF",
    "import_export",
    "INSERT > Insert SVG (and Insert DXF with its placement)",
    "Bring the curves of an SVG (or DXF) file into a sketch (Fusion's Insert SVG / Insert "
    "DXF), ready to extrude, emboss or cut: logos, outlines from a drawing program. plane "
    '(XY | XZ | YZ | {"face": sel} | {"construct": id}: a new sketch there) or sketch (an '
    "existing one); an SVG is centred on the sketch origin, a DXF keeps its own origin; dx / "
    "dy (mm), angle (degrees), scale, flip_h / flip_v; unit (DXF: the file's unit). The "
    "curves are fixed. Answers the sketch, the curve count, its size and its closed areas.",
    schema(
        {
            "path": string("full path of the .svg or .dxf file"),
            "plane": _PLANE,
            "sketch": step_id("an existing sketch to add the curves to"),
            "dx": length(default=0),
            "dy": length(default=0),
            "angle": angle(default=0),
            "scale": positive("size factor", default=1),
            "flip_h": boolean(default=False),
            "flip_v": boolean(default=False),
            "unit": enum(["mm", "cm", "m", "in", "ft"], "DXF: the file's unit"),
            "name": string("the new sketch's name"),
        },
        ["path"],
    ),
    extra=_extra_svg,
    id_base="Sketch",
    title_fn=lambda a: "AI: Insert %s" % str(a.get("path", "")).replace("\\", "/").split("/")[-1],
    examples=[
        example(
            {"path": "/home/me/logo.svg", "plane": {"face": {"normal": [0, 0, 1], "count": 1}}},
            "a logo's outline on the top face",
        )
    ],
)


def _extra_derive(args, problems):
    if "into" in args and "source" in args:
        problems.append("give source (Insert Derive into this design) or into (Derive from it)")
    if not args.get("list") and not args.get("items"):
        problems.append("give items (what to derive) or list: true (see what there is)")


define(
    "derive",
    "Derive",
    "import_export",
    "SOLID > CREATE > Derive / INSERT > Insert Derive",
    "Fusion's Derive: copies of another design's bodies, sketches, construction planes, "
    "parameters or components that stay linked and update when that design is saved again "
    "(a part made from a master design). source: a saved design (Insert Derive: into this "
    "design, which must be saved); without source the open design is derived into a new "
    'design (into: new) or into a saved one (into: its path). items: labels or ids ("Body1", '
    '"width", "Lid") or a kind: "bodies", "sketches", "construction", "parameters", '
    '"components", "all". list: true answers what can be derived (nothing is made). '
    "place_at_origin: bodies at the origin. For a copy that is NOT linked use import_file.",
    schema(
        {
            "source": string("full path of the saved design to derive from"),
            "into": string('"new" (a new design) or the full path of a saved design'),
            "items": array(string(), "what to derive", 1),
            "list": boolean("only list what can be derived", default=False),
            "place_at_origin": boolean(default=False),
        }
    ),
    extra=_extra_derive,
    id_base="Derive",
    title_fn=lambda a: "AI: %s" % ("Insert Derive" if a.get("source") else "Derive"),
    examples=[
        example(
            {"source": "/home/me/designs/Master.FCStd", "items": ["Housing", "width"]},
            "the Housing body and the width parameter of the master, linked",
        ),
        example({"source": "/home/me/designs/Master.FCStd", "list": True}, "what can be derived"),
    ],
)

# -- CONSTRUCT ----------------------------------------------------------------------------------


def _extra_ucs(args, problems):
    if "on" in args:
        kit.check_pick(args["on"], "on", problems, ("plane", "face", "vertex", "construct"))
    for key in ("x_axis", "z_axis"):
        v = args.get(key)
        if isinstance(v, list) and len(v) == 3 and all(kit.is_type(c, "number") for c in v):
            if all(abs(c) < 1e-12 for c in v):
                problems.append("%s must not be [0, 0, 0]" % key)


define(
    "coordinate_system",
    "User coordinate system",
    "construct",
    "SOLID > CONSTRUCT > User Coordinate System",
    "A user coordinate system (origin point and X / Y / Z axes) in the active body: a frame "
    "to sketch on (its XY plane), to measure from, or to attach things to. origin [x, y, z] "
    "(mm), z_axis and x_axis directions (default the design's); on: a pick it follows when "
    'the part changes ({"face": selector}: on that flat face, {"plane": "XY"}, {"vertex": '
    '[x, y, z]}, {"construct": id}); origin and axes are then measured in that frame. '
    "Answers its id and its frame in design coordinates.",
    schema(
        {
            "origin": kit.point3("its origin (mm)"),
            "z_axis": kit.vector3("its Z direction"),
            "x_axis": kit.vector3("its X direction (made square to Z)"),
            "on": pick("what it follows"),
            "name": string("its name"),
        }
    ),
    extra=_extra_ucs,
    id_base="CoordinateSystem",
    title_fn=lambda a: "AI: User coordinate system",
    examples=[
        example(
            {"origin": [50, 0, 20], "z_axis": [1, 0, 0]},
            "a frame at (50, 0, 20) whose Z points along X",
        )
    ],
)

# -- SOLID: base features, Compute All ----------------------------------------------------------
define(
    "base_feature",
    "Base feature",
    "timeline",
    "SOLID > CREATE > Create Base Feature / Finish Base Feature",
    "Fusion's base feature: start: the bodies made next (new_body first, or a tool with "
    "operation new_body) are NOT recorded step by step; finish: each becomes one base feature "
    "in the timeline (no parameters to edit later). For a quick direct-modelling stretch in "
    "a parametric design. For the whole design without history use capture_design_history.",
    schema({"action": enum(["start", "finish"])}, ["action"]),
    own_id=False,
    title_fn=lambda a: "AI: %s base feature"
    % ("Create" if a.get("action") == "start" else "Finish"),
    examples=[example({"action": "start"}, "direct edits from here, one step per body")],
)
define(
    "compute_all",
    "Compute all",
    "timeline",
    "SOLID > MODIFY > Compute All (Ctrl+B)",
    "Compute every parameter and step of the design again from the start (Fusion's Compute "
    "All): after a design was opened with stale steps, or to find the steps that fail. "
    "Answers how many steps, how long it took, and each step that failed or warns with the "
    "reason (fix them with get_step / edit_step). Takes about as long as opening the design "
    "(seconds; a minute for a big assembly).",
    schema({}),
    own_id=False,
    title_fn=lambda a: "AI: Compute all",
    examples=[example({}, "recompute everything and list the failing steps")],
)

# -- INSPECT ------------------------------------------------------------------------------------
ANALYSES = (
    "draft",
    "minimum_radius",
    "curvature_map",
    "accessibility",
    "zebra",
    "environment_map",
    "curvature_comb",
    "isocurve",
)


def _extra_analysis(args, problems):
    kind = args.get("kind")
    if kind == "curvature_comb" and "edges" not in args:
        problems.append("curvature_comb needs edges (a selector)")
    if kind == "isocurve" and "faces" not in args:
        problems.append("isocurve needs faces (a selector)")
    if kind != "curvature_comb" and "edges" in args:
        problems.append("edges is for curvature_comb")
    if "direction" in args:
        spec = args["direction"]
        if isinstance(spec, str):
            if spec not in kit.AXES + kit.PLANES:
                problems.append("direction must be X, Y, Z, XY, XZ, YZ, [x, y, z] or a pick")
        elif isinstance(spec, list):
            if len(spec) != 3 or not all(kit.is_type(v, "number") for v in spec):
                problems.append("direction as a list must be [x, y, z]")
            elif all(abs(v) < 1e-12 for v in spec):
                problems.append("direction must not be [0, 0, 0]")
        elif isinstance(spec, dict):
            kit.check_axis_or_pick(spec, "direction", problems)
        if kind not in ("draft", "accessibility"):
            problems.append("direction is for draft and accessibility")


define(
    "analysis",
    "Surface analysis",
    "inspect",
    "INSPECT > Draft / Minimum Radius / Curvature Map / Accessibility / Zebra / "
    "Environmental Map / Curvature Comb / Isocurve Analysis",
    "INSPECT's analyses as numbers (nothing is left in the design). draft: each face's draft "
    "angle against direction (pull, default Z), the faces under draft_min (degrees, default "
    "1) with refs; minimum_radius: the tightest inner round and where, faces under "
    "min_radius (mm); curvature_map: the tightest bends (under min_radius flagged); "
    "accessibility: the share of area a tool along direction reaches, blocked faces; zebra / "
    "environment_map: edges where faces meet with a crease or a curvature jump (what stripes "
    "show); curvature_comb (edges): curvature along them; isocurve (faces): along U / V. "
    "bodies (default every visible one), faces. picture: true adds a render with the faces "
    "found in orange. On a 1,500-face part about 2 s; accessibility 14 s; a picture 25 s.",
    schema(
        {
            "kind": enum(ANALYSES),
            "bodies": step_ids("the bodies (default: every visible solid)"),
            "faces": kit.selector("only these faces (isocurve: the faces)"),
            "edges": kit.selector("curvature_comb: the edges", "edges"),
            "direction": {
                "type": ["string", "array", "object"],
                "items": {"type": "number"},
                "description": "draft / accessibility: the pull or tool direction: X, Y, Z, "
                '[x, y, z], an origin plane (its normal) or {"face": sel} / {"edge": sel}',
            },
            "flip": boolean("the direction the other way", default=False),
            "draft_min": angle("below this draft a face is flagged", default=1, minimum=0),
            "draft_ok": angle("from this draft on a face is fine", default=3, minimum=0),
            "min_radius": positive("minimum_radius: rounds tighter are flagged (mm)", default=1),
            "tool_radius": positive("minimum_radius: a cutter of this radius fits (mm)", default=5),
            "include_sharp": boolean("minimum_radius: sharp inner edges count", default=False),
            "access": enum(["direction", "opposite", "both"], default="direction"),
            "iso_count": integer("isocurve: lines per direction", 5, 1, 50),
            "picture": boolean("add a picture with the flagged faces in orange", default=False),
            "limit": integer("most rows per list", 20, 1, 200),
        },
        ["kind"],
    ),
    extra=_extra_analysis,
    changes=False,
    examples=[
        example(
            {"kind": "draft", "direction": "Z", "draft_min": 1},
            "which faces lack 1 degree of draft for a mould opening along Z",
        ),
        example(
            {"kind": "minimum_radius", "min_radius": 3}, "inner rounds a 3 mm cutter cannot cut"
        ),
    ],
)
define(
    "component_colors",
    "Component colors",
    "inspect",
    "INSPECT > Display Component Colors (Shift+N) / Component Color Swatch",
    "Each component's colour for telling them apart (Fusion's Display Component Colors): on "
    "draws every component in its colour in the window (false: their own looks again); "
    "swatch shows the colour marks in the browser and timeline; cycle: components that take "
    "the next colour. Only the display changes. Always answers each component's colour, so "
    "a render or screenshot can be read.",
    schema(
        {
            "on": boolean("colours drawn in the window"),
            "swatch": boolean("colour marks in the browser and timeline"),
            "cycle": step_ids("components that take the next colour"),
        }
    ),
    own_id=False,
    title_fn=lambda a: "AI: Component colors",
    examples=[example({"on": True}, "show each component in its own colour")],
)


# -- coverage: every command of the DESIGN workspace's groups -> the tool that reaches it ----------
# (ribbon group id of fission180/ribbon_config.py -> {its label: "tool (kind)" or "no tool: why"});
# test_ai_catalog checks it against the ribbon, and docs/fission180/parity/ai.md shows it.
_PATTERNS = {
    "Rectangular Pattern": "rectangular_pattern",
    "Circular Pattern": "circular_pattern",
    "Pattern on Path": "pattern_on_path",
    "Mirror": "mirror",
}
_BODY_TOOLS = {
    "Replace Face": "replace_face",
    "Split Face": "split_face",
    "Split Body": "split_body",
    "Silhouette Split": "silhouette_split",
    "Scale": "scale",
    "Combine": "combine",
    "Move/Copy": "move_copy",
    "Align": "align",
    "Physical Material": "physical_material",
    "Appearance": "appearance",
    "Manage Materials": "list_materials (reading the libraries); physical_material / appearance "
    "assign from them; no tool for the person's favourites and own looks (their settings, not "
    "the design)",
    "Change Parameters": "set_parameter / list_parameters / set_model_parameter / "
    "delete_parameter",
    "Compute All": "compute_all",
}
COVERAGE = {
    "create": dict(
        {
            "Create Sketch": "create_sketch / create_curve_sketch",
            "Derive": "derive (into: new or a saved design)",
            "Extrude": "extrude",
            "Revolve": "revolve",
            "Sweep": "sweep",
            "Loft": "loft",
            "Rib": "rib",
            "Web": "web",
            "Emboss": "emboss",
            "Text": "create_sketch (face) + sketch_text",
            "Hole": "hole",
            "Thread": "thread",
            "Box": "primitive (box)",
            "Cylinder": "primitive (cylinder)",
            "Sphere": "primitive (sphere)",
            "Torus": "primitive (torus)",
            "Coil": "coil",
            "Gear": "gear",
            "Pipe": "pipe",
            "Thicken": "surface (thicken)",
            "Boundary Fill": "surface (boundary_fill)",
            "Create Base Feature": "base_feature (start)",
            "Finish Base Feature": "base_feature (finish)",
            "Joint Origin": "joint_origin",
        },
        **_PATTERNS
    ),
    "modify": dict(
        {
            "Press Pull": "press_pull",
            "Fillet": "fillet / fillet_sets / rule_fillet / full_round_fillet",
            "Chamfer": "chamfer / fillet_sets (chamfer)",
            "Shell": "shell",
            "Draft": "draft",
            "Offset Face": "press_pull (offset_face)",
            "Delete": "delete_face / delete_bodies / delete_step",
            "Remove": "remove_bodies",
            "Texture Map Controls": "appearance (texture_map)",
        },
        **_BODY_TOOLS
    ),
    "construct": {
        "User Coordinate System": "coordinate_system",
        "Offset Plane": "construct_plane (OffsetPlane)",
        "Plane at Angle": "construct_plane (PlaneAtAngle)",
        "Tangent Plane": "construct_plane (TangentPlane)",
        "Midplane": "construct_plane (Midplane)",
        "Plane Tangent to Face at Point": "construct_plane (PlaneAtPoint)",
        "Plane Through Two Edges": "construct_plane (PlaneTwoEdges)",
        "Plane Through Three Points": "construct_plane (PlaneThreePoints)",
        "Plane Along Path": "construct_plane (PlaneAlongPath)",
        "Axis Through Cylinder/Cone/Torus": "construct_axis (AxisCylinder)",
        "Axis Perpendicular to Face at Point": "construct_axis (AxisNormal)",
        "Axis Through Two Planes": "construct_axis (AxisTwoPlanes)",
        "Axis Through Two Points": "construct_axis (AxisTwoPoints)",
        "Axis Through Edge": "construct_axis (AxisEdge)",
        "Point at Vertex": "construct_point (PointVertex)",
        "Point Through Two Edges": "construct_point (PointTwoEdges)",
        "Point Through Three Planes": "construct_point (PointThreePlanes)",
        "Point at Center of Circle/Sphere/Torus": "construct_point (PointCenter)",
        "Point at Edge and Plane": "construct_point (PointEdgePlane)",
        "Point Along Path": "construct_point (PointAlongPath)",
    },
    "inspect": {
        "Measure": "measure / query_geometry",
        "Interference": "interference",
        "Curvature Comb Analysis": "analysis (curvature_comb)",
        "Zebra Analysis": "analysis (zebra)",
        "Draft Analysis": "analysis (draft)",
        "Curvature Map Analysis": "analysis (curvature_map)",
        "Isocurve Analysis": "analysis (isocurve)",
        "Accessibility Analysis": "analysis (accessibility)",
        "Minimum Radius Analysis": "analysis (minimum_radius)",
        "Environmental Map Analysis": "analysis (environment_map)",
        "Section Analysis": "section_analysis",
        "Center of Mass": "center_of_mass",
        "Display Component Colors": "component_colors (on)",
        "Component Color Swatch": "component_colors (swatch)",
        "Properties": "physical_properties",
    },
    "insert": {
        "Decal": "decal",
        "Canvas": "canvas",
        "Insert SVG": "insert_svg",
        "Insert DXF": "import_file (.dxf) / insert_svg (.dxf, placed)",
        "Insert Mesh": "import_file (.stl / .obj / .3mf)",
        "Insert Component": "import_file (.FCStd: a linked component)",
        "Insert Derive": "derive (source)",
        "Insert STEP": "import_file (.step / .iges)",
        "Hardware...": "insert_hardware",
        "Insert Catalogue Part...": "no tool: it opens a supplier's website in the person's "
        "browser; the STEP file they download comes in with import_file",
    },
    "assemble": {
        "New Component": "new_component",
        "Joint": "joint",
        "As-built Joint": "as_built_joint",
        "Joint Origin": "joint_origin",
        "Rigid Group": "rigid_group",
        "Duplicate With Joints": "duplicate_with_joints",
        "Drive Joints": "drive_joint",
        "Motion Link": "motion_link",
        "Enable Contact Sets": "contact (mode sets)",
        "Enable All Contact": "contact (mode all)",
        "Disable Contact": "contact (mode off)",
        "New Contact Set": "contact (new_set)",
        "Motion Study": "motion_study",
        "Capture Position": "position (capture)",
        "Revert Position": "position (revert)",
    },
    "s_create": dict(
        {
            "New Component": "new_component",
            "Create Sketch": "create_sketch / create_curve_sketch",
            "Create Base Feature": "base_feature (start)",
            "Derive": "derive",
            "Extrude": "surface (extrude)",
            "Revolve": "surface (revolve)",
            "Sweep": "surface (sweep)",
            "Loft": "surface (loft)",
            "Patch": "surface (patch)",
            "Ruled": "surface (ruled)",
            "Offset": "surface (offset)",
            "Thicken": "surface (thicken)",
            "Boundary Fill": "surface (boundary_fill)",
        },
        **_PATTERNS
    ),
    "s_modify": dict(
        _BODY_TOOLS,
        **{
            "Press Pull": "surface_modify (press_pull)",
            "Fillet": "surface_modify (fillet)",
            "Chamfer": "surface_modify (chamfer)",
            "Trim": "surface (trim)",
            "Untrim": "surface (untrim)",
            "Extend": "surface (extend)",
            "Stitch": "surface (stitch)",
            "Unstitch": "surface (unstitch)",
            "Reverse Normal": "surface (reverse_normal)",
            "Merge": "surface_modify (merge)",
            "Delete": "surface_modify (delete_face) / delete_bodies",
        }
    ),
    "k_create": {
        "Line": "add_to_sketch (curves: line) / create_curve_sketch",
        "Midpoint Line": "sketch_draw (midpoint_line)",
        "2-Point Rectangle": "create_sketch / add_to_sketch (rect)",
        "3-Point Rectangle": "sketch_draw (rectangle_3point)",
        "Center Rectangle": "create_sketch / add_to_sketch (center_rect)",
        "Center Diameter Circle": "create_sketch / add_to_sketch (circle)",
        "2-Point Circle": "sketch_draw (circle_2point)",
        "3-Point Circle": "sketch_draw (circle_3point)",
        "2-Tangent Circle": "sketch_draw (circle_2tangent)",
        "3-Tangent Circle": "sketch_draw (circle_3tangent)",
        "3-Point Arc": "sketch_draw (arc_3point)",
        "Center Point Arc": "add_to_sketch (curves: arc)",
        "Tangent Arc": "sketch_draw (tangent_arc)",
        "Circumscribed Polygon": "sketch_polygon",
        "Inscribed Polygon": "sketch_polygon (circumscribed: false)",
        "Edge Polygon": "sketch_draw (edge_polygon)",
        "Ellipse": "sketch_draw (ellipse) / add_to_sketch (ellipse)",
        "Center to Center Slot": "sketch_draw (slot_center_to_center)",
        "Overall Slot": "sketch_draw (slot_overall)",
        "Center Point Slot": "sketch_draw (slot_center_point)",
        "Three Point Arc Slot": "sketch_draw (arc_slot)",
        "Center Point Arc Slot": "sketch_draw (arc_slot_center_point)",
        "Fit Point Spline": "sketch_draw (fit_point_spline)",
        "Control Point Spline": "sketch_draw (control_point_spline)",
        "Conic Curve": "sketch_draw (conic)",
        "Point": "add_to_sketch (curves: point)",
        "Text": "sketch_text",
        "Mirror": "sketch_pattern (mirror)",
        "Circular Pattern": "sketch_pattern (circular)",
        "Rectangular Pattern": "sketch_pattern (rectangular)",
        "Project": "sketch_project (project)",
        "Intersect": "sketch_project (intersect)",
        "Include 3D Geometry": "sketch_project (include_3d)",
        "Project to Surface": "sketch_project (project_to_surface)",
        "Isoparametric Curve": "sketch_project (isoparametric)",
        "Sketch Dimension": "sketch_dimension",
    },
    "k_modify": {
        "Fillet": "sketch_modify (fillet)",
        "Chamfer": "sketch_modify (chamfer)",
        "Offset": "sketch_modify (offset)",
        "Trim": "sketch_trim",
        "Extend": "sketch_modify (extend)",
        "Break": "sketch_modify (break)",
        "Sketch Scale": "scale (sketch)",
        "Move/Copy": "sketch_pattern (move_copy)",
        "Change Parameters": "set_parameter / set_sketch_dimension",
    },
    "k_constraints": {
        "Coincident": "sketch_constraint (coincident)",
        "Collinear": "sketch_constraint (collinear)",
        "Concentric": "sketch_constraint (concentric)",
        "Midpoint": "sketch_constraint (midpoint)",
        "Fix/Unfix": "sketch_constraint (fix / unfix)",
        "Parallel": "sketch_constraint (parallel)",
        "Perpendicular": "sketch_constraint (perpendicular)",
        "Horizontal/Vertical": "sketch_constraint (horizontal / vertical)",
        "Tangent": "sketch_constraint (tangent)",
        "Curvature": "sketch_constraint (curvature)",
        "Equal": "sketch_constraint (equal)",
        "Symmetry": "sketch_constraint (symmetric)",
    },
    "k_finish": {
        "Finish Sketch": "no tool: the AI's sketch tools never leave a sketch open (each call "
        "draws and closes)",
        "Toggle Construction": "sketch_modify (toggle_construction)",
    },
}
GROUP_TITLES = {
    "create": "SOLID > CREATE",
    "modify": "SOLID > MODIFY",
    "construct": "SOLID > CONSTRUCT",
    "inspect": "SOLID > INSPECT",
    "insert": "SOLID > INSERT",
    "assemble": "SOLID > ASSEMBLE",
    "s_create": "SURFACE > CREATE",
    "s_modify": "SURFACE > MODIFY",
    "k_create": "SKETCH > CREATE",
    "k_modify": "SKETCH > MODIFY",
    "k_constraints": "SKETCH > CONSTRAINTS",
    "k_finish": "SKETCH > FINISH SKETCH",
}


def coverage_tools(text):
    """The tool names a coverage entry names ([] for "no tool: ...")."""
    import re

    if text.startswith("no tool:"):
        return []
    head = re.sub(r"\([^)]*\)", "", text.split(";")[0])
    return [w for w in re.findall(r"[a-z][a-z_]*[a-z]", head) if "_" in w or w in _SINGLE]


_SINGLE = {
    "extrude", "revolve", "sweep", "loft", "rib", "web", "emboss", "hole", "thread",
    "primitive", "coil", "gear", "pipe", "mirror", "surface", "joint", "fillet", "chamfer",
    "shell", "draft", "scale", "combine", "align", "appearance", "measure", "interference",
    "decal", "canvas", "derive", "analysis", "position", "contact",
}  # fmt: skip
