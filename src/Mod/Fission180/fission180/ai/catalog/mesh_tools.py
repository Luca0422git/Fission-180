# SPDX-License-Identifier: LGPL-2.1-or-later
"""AI tools for the MESH tab (wave 8, builder ai-mesh): every command of MESH > CREATE,
PREPARE, MODIFY and CONVERT, built with the code its dialog runs (fission180/mesh.py, the step
each dialog adds; insert.py, Convert Mesh), in fission180/ai/actions/mesh_actions.py.

    inspect_mesh          a mesh body's numbers, the shapes it is made of, what to do with it
    convert_mesh          CONVERT > Convert Mesh: a solid body from a closed mesh body
    mesh_prepare          PREPARE > Repair, Make Closed Mesh, Generate / Create / Combine
                          Face Groups
    mesh_modify           MODIFY > Remesh, Reduce, Plane Cut, Shell, Smooth, Combine, Separate,
                          Reverse Normal, Erase and Fill, Delete Faces, Direct Edit
    tessellate            CREATE > Tessellate: a mesh body from a solid body
    mesh_section_sketch   CREATE > Create Mesh Section Sketch

CREATE > Insert Mesh is import_file (history_tools). Faces of a mesh are named with a face
pick (MESH_FACES below), never by a triangle's number. Pure Python (the MCP server imports it).
"""

from . import registry
from .kit import array, boolean, enum, integer, number, obj, positive, schema, string
from .registry import define, example

# The MESH tab's own category, entered here so the shared lists stay untouched (rebuild_tools
# does the same): after PLASTIC, where Fusion's ribbon has the MESH tab.
if "mesh" not in registry.CATEGORY_KEYS:
    _cats = list(registry.CATEGORIES)
    _at = (
        [k for k, _t in _cats].index("plastic") + 1
        if "plastic" in registry.CATEGORY_KEYS
        else len(_cats)
    )
    _cats.insert(_at, ("mesh", "Mesh"))
    registry.CATEGORIES = tuple(_cats)
    registry.CATEGORY_KEYS = tuple(k for k, _t in _cats)

MESH_BODY = (
    "the mesh body: its id (import_file answers it; any step of its history works) or name; "
    "default: the only mesh body of the design"
)
MESH_FACES_HELP = (
    "Faces of a mesh are its triangles, named by where they are, never by number: "
    '{"groups": [n, ...]} (face groups; inspect_mesh detail groups lists them), '
    '{"points": [[x, y, z], ...]} (the face at each point of the surface), {"ray": {"from": '
    '[x, y, z], "direction": [x, y, z]}} (the first face along it, like a click), {"box": [x0, '
    'y0, z0, x1, y1, z1]} (every face whose centre is inside) or {"all": true}; add "facing": '
    '{"normal": [x, y, z], "within": degrees} to keep only faces facing that way.'
)


PICK_KEYS = ("groups", "points", "ray", "box", "all")


def pick_problems(spec, path="faces"):
    """A face pick's shape in plain sentences ([] when fine); mesh_ai_core.picked_facets
    finds its faces on the mesh."""
    out = []
    if not isinstance(spec, dict):
        return ["%s must be an object with one of %s" % (path, ", ".join(PICK_KEYS))]
    keys = [k for k in PICK_KEYS if k in spec]
    extra = [k for k in spec if k not in PICK_KEYS and k != "facing"]
    if len(keys) != 1 or extra:
        return ["%s must have exactly one of %s (and maybe facing)" % (path, ", ".join(PICK_KEYS))]
    key = keys[0]
    value = spec[key]
    if key == "groups":
        if not isinstance(value, list) or not value or not all(_is_int(v) for v in value):
            out.append("%s.groups must be a list of face group numbers" % path)
    elif key == "points":
        if not isinstance(value, list) or not value or not all(_is_point(p) for p in value):
            out.append("%s.points must be a list of [x, y, z] points" % path)
    elif key == "ray":
        if (
            not isinstance(value, dict)
            or set(value) != {"from", "direction"}
            or not _is_point(value.get("from"))
            or not _is_point(value.get("direction"))
        ):
            out.append('%s.ray must be {"from": [x, y, z], "direction": [x, y, z]}' % path)
        elif all(abs(v) < 1e-12 for v in value["direction"]):
            out.append("%s.ray.direction must not be [0, 0, 0]" % path)
    elif key == "box":
        if not (
            isinstance(value, list)
            and len(value) == 6
            and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in value)
        ):
            out.append("%s.box must be [x0, y0, z0, x1, y1, z1]" % path)
    elif key == "all" and value is not True:
        out.append("%s.all must be true" % path)
    if "facing" in spec:
        face = spec["facing"]
        if (
            not isinstance(face, dict)
            or set(face) - {"normal", "within"}
            or not _is_point(face.get("normal"))
            or all(abs(v) < 1e-12 for v in face.get("normal") or [0])
        ):
            out.append('%s.facing must be {"normal": [x, y, z], "within": degrees}' % path)
        elif "within" in face and not (
            isinstance(face["within"], (int, float)) and 0 < face["within"] <= 180
        ):
            out.append("%s.facing.within must be degrees above 0, at most 180" % path)
    return out


def _is_int(value):
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _is_point(value):
    return (
        isinstance(value, list)
        and len(value) == 3
        and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in value)
    )


def _faces(description):
    return {"type": "object", "description": description + ". " + MESH_FACES_HELP}


def _check_faces(args, problems, key="faces"):
    if key in args:
        problems += pick_problems(args[key], key)


def _title(command, args):
    """The undo step's name: "AI: Repair Relic" (the body named), else "AI: Repair"."""
    body = args.get("body")
    return "AI: %s %s" % (command, body) if isinstance(body, str) and body else "AI: " + command


# -- inspect_mesh -------------------------------------------------------------------------------
define(
    "inspect_mesh",
    "Inspect mesh",
    "mesh",
    "MESH > PREPARE > Repair (its analysis), Properties of a mesh body",
    "Read a mesh body before changing it (an STL / OBJ / 3MF from import_file, a "
    "tessellated body or a MESH step). It answers triangles, size, closed or what is wrong "
    "(holes, flipped faces, "
    "edges with more than two faces, separate shells), volume, face groups, the shapes it is "
    "made of (overview: its big flat faces, and its small round or free-form details grouped, "
    "with a grid or ring of equal ones found: what to rebuild as features) and advice: the "
    "next call and how long it takes. Call it first on any mesh, then ask the person what "
    "they want (a solid to cut and print now, or an editable timeline). detail groups also "
    "lists every face group. Changes nothing; under a second for 10,000 triangles.",
    schema(
        {
            "body": string(MESH_BODY),
            "detail": enum(
                ("summary", "groups"),
                "summary: numbers, overview, advice; groups: also each face group",
                default="summary",
            ),
            "self_intersections": boolean(
                "also count where the mesh crosses itself (slow on big meshes)", default=False
            ),
        }
    ),
    changes=False,
    examples=[
        example({}, "the only mesh body: closed?, size, shapes, what to do next"),
        example({"body": "MeshBody", "detail": "groups"}, "with every face group"),
    ],
)


# -- convert_mesh -------------------------------------------------------------------------------
define(
    "convert_mesh",
    "Convert mesh",
    "mesh",
    "MESH > CONVERT > Convert Mesh",
    "Make a solid body from a closed mesh body (MESH > Convert Mesh). A new body whose first "
    "step builds the solid, so fillet, chamfer, hole, press_pull, combine work on it. "
    "method prismatic (default): triangles in one plane become one flat face, round or "
    "free-form areas stay many small flat faces (Fission 180 fits no cylinders: use the "
    "rebuild route for true round holes); faceted: one face per triangle. operation "
    "parametric (default: follows later MESH steps of the mesh) or base_feature (made once). "
    "The mesh body is hidden. Refused for a mesh that is not closed (mesh_prepare kind repair "
    "first) and when it would take more than a minute (about 0.25 s per 1,000 triangles: "
    "mesh_modify kind reduce first, or allow_slow). Answers faces, volume against the mesh's "
    "and seconds. No timeline of features: that is start_rebuild.",
    schema(
        {
            "body": string(MESH_BODY),
            "method": enum(("prismatic", "faceted"), "how the faces are made", default="prismatic"),
            "operation": enum(
                ("parametric", "base_feature"),
                "parametric follows the mesh; base_feature is made once",
                default="parametric",
            ),
            "allow_slow": boolean(
                "convert even when it is estimated to take more than a minute", default=False
            ),
            "name": string("the new solid body's name (default '<mesh> (solid)')"),
        }
    ),
    title_fn=lambda a: _title("Convert Mesh", a),
    examples=[
        example({}, "the only mesh body as a solid, flat faces merged"),
        example(
            {"body": "MeshBody", "method": "faceted", "name": "Scan solid"},
            "one face per triangle, named",
        ),
    ],
)


# -- mesh_prepare -------------------------------------------------------------------------------
PREPARE_KINDS = (
    "repair",
    "make_closed",
    "generate_face_groups",
    "create_face_group",
    "combine_face_groups",
)
REPAIR_TYPES = ("close_holes", "stitch_and_remove", "wrap", "rebuild")
REBUILD_TYPES = ("fast", "preserve_sharp_edges", "accurate", "blocky")


def _extra_prepare(args, problems):
    kind = args.get("kind")
    _check_faces(args, problems)
    if kind == "create_face_group" and "faces" not in args:
        problems.append("create_face_group needs faces (the faces of the new face group)")
    if kind == "combine_face_groups" and "faces" not in args and "groups" not in args:
        problems.append("combine_face_groups needs groups (or faces in the groups to join)")
    if kind == "combine_face_groups" and len(args.get("groups") or []) == 1:
        problems.append("combine_face_groups needs at least two groups")
    own = {
        "repair": ("repair_type", "rebuild_type", "density", "offset"),
        "make_closed": ("rebuild_type", "density", "offset"),
        "generate_face_groups": ("method", "angle", "min_size", "tolerance"),
        "create_face_group": ("faces",),
        "combine_face_groups": ("faces", "groups"),
    }.get(kind, ())
    for key in (
        "repair_type",
        "rebuild_type",
        "density",
        "offset",
        "method",
        "angle",
        "min_size",
        "tolerance",
        "faces",
        "groups",
    ):
        if key in args and key not in own:
            problems.append("%s does not apply to kind %s" % (key, kind))


define(
    "mesh_prepare",
    "Prepare mesh",
    "mesh",
    "MESH > PREPARE > Repair, Generate Face Groups, Create Face Group, Combine Face Groups; "
    "MESH > MODIFY > Make Closed Mesh",
    "Get a mesh body ready, as the PREPARE dialogs do (one undo step, a step in the "
    "timeline). kind repair: close holes and fix flipped faces (repair_type close_holes | "
    "stitch_and_remove, the default: also joins cracks and drops loose bits | wrap: also "
    "inner shells and crossings | rebuild: a new closed surface from voxels, density 8..256). "
    "kind make_closed: Make Closed Mesh (repair rebuild, accurate): always closed, sharp "
    "details softened. kind generate_face_groups: faces split into groups by angle (method "
    "fast, angle degrees) or by fitted plane / cylinder / sphere (accurate). kind "
    "create_face_group: the faces given become one group; combine_face_groups: groups that "
    "touch become one. The answer says closed or what is left, with the next call. "
    "inspect_mesh first says which repair fits.",
    schema(
        {
            "kind": enum(PREPARE_KINDS),
            "body": string(MESH_BODY),
            "repair_type": enum(
                REPAIR_TYPES, "repair: how far it goes", default="stitch_and_remove"
            ),
            "rebuild_type": enum(REBUILD_TYPES, "repair rebuild / make_closed"),
            "density": integer("rebuild: cells along the longest side", minimum=8, maximum=256),
            "offset": number("rebuild accurate: grow (+) or shrink (-) the surface (mm)"),
            "method": enum(("fast", "accurate"), "generate_face_groups", default="fast"),
            "angle": number(
                "generate_face_groups fast: degrees between groups", above=0, maximum=90
            ),
            "min_size": number(
                "generate_face_groups fast: smallest group as a share of the area (0..1)",
                minimum=0,
                maximum=1,
            ),
            "tolerance": number(
                "generate_face_groups accurate: as a share of the body's size (0..1)",
                above=0,
                maximum=1,
            ),
            "faces": _faces("create / combine face groups: the faces"),
            "groups": array(integer(minimum=0), "combine_face_groups: the groups joined", 1),
        },
        ["kind"],
    ),
    extra=_extra_prepare,
    title_fn=lambda a: _title(
        {
            "repair": "Repair",
            "make_closed": "Make Closed Mesh",
            "generate_face_groups": "Generate Face Groups",
            "create_face_group": "Create Face Group",
            "combine_face_groups": "Combine Face Groups",
        }.get(a.get("kind"), "Prepare Mesh"),
        a,
    ),
    examples=[
        example({"kind": "repair"}, "close the holes of the only mesh body, flipped faces turned"),
        example(
            {"kind": "repair", "body": "MeshBody", "repair_type": "rebuild", "density": 160},
            "a broken scan rebuilt closed",
        ),
        example({"kind": "generate_face_groups", "angle": 20}, "face groups by angle"),
        example(
            {"kind": "create_face_group", "faces": {"box": [0, 0, 4.9, 80, 60, 5.1]}},
            "the top faces become one face group",
        ),
    ],
)


# -- mesh_modify -------------------------------------------------------------------------------
MODIFY_KINDS = (
    "remesh",
    "reduce",
    "plane_cut",
    "shell",
    "smooth",
    "combine",
    "separate",
    "reverse_normal",
    "erase_and_fill",
    "delete_faces",
    "direct_edit",
)
_MODIFY_KEYS = {
    "remesh": (
        "remesh_type",
        "density",
        "shape_preservation",
        "preserve_sharp_edges",
        "preserve_boundaries",
    ),
    "reduce": ("target", "tolerance", "proportion", "face_count", "reduce_type"),
    "plane_cut": ("plane", "distance", "angle_x", "angle_y", "cut_type", "fill", "flip"),
    "shell": ("thickness",),
    "smooth": ("smoothness", "groups", "faces"),
    "combine": ("tools", "operation", "keep_tools"),
    "separate": ("separate_type", "groups", "faces", "keep_body"),
    "reverse_normal": ("groups", "faces"),
    "erase_and_fill": ("faces", "fill", "density"),
    "delete_faces": ("faces",),
    "direct_edit": ("edits",),
}
_ALL_MODIFY_KEYS = sorted({k for keys in _MODIFY_KEYS.values() for k in keys})
EDIT_OPS = ("delete", "erase_fill", "group", "reverse", "move", "smooth")


def _extra_modify(args, problems):
    kind = args.get("kind")
    own = _MODIFY_KEYS.get(kind, ())
    for key in _ALL_MODIFY_KEYS:
        if key in args and key not in own:
            problems.append("%s does not apply to kind %s" % (key, kind))
    _check_faces(args, problems)
    if kind in ("erase_and_fill", "delete_faces") and "faces" not in args:
        problems.append("%s needs faces (the faces to take away)" % kind)
    if kind == "plane_cut" and "plane" not in args:
        problems.append("plane_cut needs plane (XY, XZ, YZ or a construction plane's id)")
    if kind == "shell" and "thickness" not in args:
        problems.append("shell needs thickness (mm)")
    if kind == "combine" and not args.get("tools"):
        problems.append("combine needs tools (the other mesh bodies' ids)")
    if kind == "reduce":
        target = args.get("target", "tolerance")
        if target == "face_count" and "face_count" not in args:
            problems.append("reduce with target face_count needs face_count")
        if target == "proportion" and "proportion" not in args:
            problems.append("reduce with target proportion needs proportion (percent kept)")
    if kind == "separate" and args.get("separate_type") == "select_face_groups":
        if "groups" not in args and "faces" not in args:
            problems.append("separate select_face_groups needs groups (or faces in them)")
    if "groups" in args and "faces" in args:
        problems.append("give groups or faces, not both")
    if kind == "direct_edit":
        edits = args.get("edits")
        if not edits:
            problems.append("direct_edit needs edits (a list of {op, faces, ...})")
        for i, edit in enumerate(edits or []):
            where = "edits[%d]" % i
            if not isinstance(edit, dict):
                problems.append("%s must be an object" % where)
                continue
            if edit.get("op") == "move" and "distance" not in edit:
                problems.append("%s: move needs distance (mm)" % where)
            problems += pick_problems(edit.get("faces"), where + ".faces")


_EDIT = obj(
    {
        "op": enum(EDIT_OPS, "what the edit does to its faces"),
        "faces": {"type": "object", "description": "the faces (a face pick, see faces)"},
        "direction": enum(("normal", "x", "y", "z"), "move: along the faces' normal or an axis"),
        "distance": number("move: mm"),
        "smoothness": number("smooth: 0..1", minimum=0, maximum=1),
        "fill": enum(("uniform", "minimal"), "erase_fill: how the gap is closed"),
        "density": number("erase_fill uniform: 0 coarse .. 1 fine", minimum=0, maximum=1),
    },
    ["op", "faces"],
)

define(
    "mesh_modify",
    "Modify mesh",
    "mesh",
    "MESH > MODIFY > Remesh, Reduce, Plane Cut, Shell, Smooth, Combine, Separate, Reverse "
    "Normal, Direct Edit, Erase and Fill, Delete Faces",
    "Change a mesh body as a MODIFY dialog does (one undo and timeline step; the body keeps "
    "its name). kind remesh (density 0..1); reduce (target tolerance mm | proportion % kept | "
    "face_count: before a slow convert); plane_cut (plane XY | XZ | YZ or a construction "
    "plane, moved distance mm, tilted angle_x / angle_y; trim removes the side its normal "
    "points to, XY +Z, XZ -Y, YZ +X, flip the other; split_body; split_faces; fill uniform "
    "can be slow on a cut through many holes: minimal is quick); shell (thickness mm); "
    "smooth (scans: it rounds a CAD part's edges); combine (tools; join | cut | intersect | "
    "merge; bodies sharing a flat face: exact up to 5,000 faces, else refused); separate; "
    "reverse_normal; erase_and_fill / delete_faces (faces); direct_edit (edits: delete, "
    "erase_fill, group, reverse, move, smooth). groups / faces limit smooth, reverse_normal, "
    "separate. Answers triangles, closed or not, time.",
    schema(
        {
            "kind": enum(MODIFY_KINDS),
            "body": string(MESH_BODY),
            "remesh_type": enum(("adaptive", "uniform"), "remesh", default="adaptive"),
            "density": number("remesh / erase_and_fill: 0 coarse .. 1 fine", minimum=0, maximum=1),
            "shape_preservation": number("remesh adaptive: 0..1", minimum=0, maximum=1),
            "preserve_sharp_edges": boolean("remesh", default=False),
            "preserve_boundaries": boolean("remesh: keep open edges", default=False),
            "target": enum(
                ("tolerance", "proportion", "face_count"), "reduce", default="tolerance"
            ),
            "tolerance": positive("reduce tolerance: largest deviation (mm)"),
            "proportion": number(
                "reduce proportion: percent of the faces kept", above=0, maximum=100
            ),
            "face_count": integer("reduce face_count: faces kept", minimum=4),
            "reduce_type": enum(("adaptive", "uniform"), "reduce", default="adaptive"),
            "plane": string("plane_cut: XY, XZ, YZ or the id of a construction plane"),
            "distance": number("plane_cut: move the plane along its normal (mm)"),
            "angle_x": number("plane_cut: tilt about the plane's x axis (degrees)"),
            "angle_y": number("plane_cut: tilt about the plane's y axis (degrees)"),
            "cut_type": enum(("trim", "split_body", "split_faces"), "plane_cut", default="trim"),
            "fill": enum(
                ("uniform", "minimal", "no_fill"),
                "plane_cut: how the cut is closed; erase_and_fill: uniform | minimal",
            ),
            "flip": boolean("plane_cut: remove the other side", default=False),
            "thickness": positive("shell: wall thickness (mm)"),
            "smoothness": number("smooth: 0..1", minimum=0, maximum=1),
            "tools": array(string(), "combine: the other mesh bodies' ids", 1),
            "operation": enum(("join", "cut", "intersect", "merge"), "combine", default="join"),
            "keep_tools": boolean("combine: keep the tool bodies", default=False),
            "separate_type": enum(
                ("mesh_shells", "all_face_groups", "select_face_groups"),
                "separate",
                default="mesh_shells",
            ),
            "keep_body": boolean("separate: keep the original body too", default=False),
            "groups": array(
                integer(minimum=0), "smooth / reverse_normal / separate: face groups", 1
            ),
            "faces": _faces("the faces (erase_and_fill, delete_faces; or the groups they are in)"),
            "edits": array(_EDIT, "direct_edit: the edits, in order", 1),
        },
        ["kind"],
    ),
    extra=_extra_modify,
    title_fn=lambda a: _title(
        {
            "remesh": "Remesh",
            "reduce": "Reduce",
            "plane_cut": "Plane Cut",
            "shell": "Shell",
            "smooth": "Smooth",
            "combine": "Combine",
            "separate": "Separate",
            "reverse_normal": "Reverse Normal",
            "erase_and_fill": "Erase and Fill",
            "delete_faces": "Delete Faces",
            "direct_edit": "Mesh Base Feature",
        }.get(a.get("kind"), "Modify Mesh"),
        a,
    ),
    examples=[
        example(
            {"kind": "reduce", "target": "face_count", "face_count": 5000},
            "fewer faces before a slow conversion",
        ),
        example(
            {"kind": "plane_cut", "plane": "XY", "distance": 2.5},
            "trim away everything above z = 2.5, the cut closed",
        ),
        example({"kind": "shell", "thickness": 1.5}, "hollow it with 1.5 mm walls"),
        example(
            {"kind": "erase_and_fill", "faces": {"points": [[40, 30, 5]]}},
            "remove the face at a point and fill the gap",
        ),
        example(
            {
                "kind": "direct_edit",
                "edits": [
                    {
                        "op": "move",
                        "faces": {"box": [0, 0, 4.9, 80, 60, 5.1]},
                        "direction": "z",
                        "distance": 1,
                    }
                ],
            },
            "Direct Edit: the top faces moved up 1 mm",
        ),
    ],
)


# -- tessellate ---------------------------------------------------------------------------------
def _extra_tessellate(args, problems):
    custom = ("surface_deviation", "normal_deviation", "max_edge_length")
    if args.get("refinement", "medium") != "custom" and any(k in args for k in custom[:2]):
        problems.append("surface_deviation and normal_deviation need refinement custom")


define(
    "tessellate",
    "Tessellate",
    "mesh",
    "MESH > CREATE > Tessellate",
    "Make a mesh body from a solid body (MESH > Tessellate). One undo step; each face of the "
    "solid becomes a face group. refinement low | medium (default) | high | custom "
    "(surface_deviation mm, normal_deviation degrees); max_edge_length (mm) splits longer "
    "edges. The solid body is used up (hidden: the mesh body takes its place, as in Fusion; "
    "undo brings it back). Use it to reach the MESH tools from a design (shell, remesh for "
    "printing); to export an STL, export does it without changing the design.",
    schema(
        {
            "body": string("the solid body (or a step in it)"),
            "refinement": enum(("low", "medium", "high", "custom"), default="medium"),
            "surface_deviation": positive("custom: largest gap to the surface (mm)"),
            "normal_deviation": number(
                "custom: largest angle between faces (degrees)", minimum=0.5, maximum=90
            ),
            "max_edge_length": number("split edges longer than this (mm); 0: no limit", minimum=0),
            "name": string("the new mesh body's name (default: the solid's)"),
        },
        ["body"],
    ),
    extra=_extra_tessellate,
    title_fn=lambda a: "AI: Tessellate %s" % a.get("body", "a body"),
    examples=[
        example({"body": "Body"}, "the body as a mesh body, medium refinement"),
        example(
            {"body": "Body", "refinement": "high", "name": "Print mesh"}, "a finer mesh, named"
        ),
    ],
)


# -- mesh_section_sketch ----------------------------------------------------------------------
define(
    "mesh_section_sketch",
    "Mesh section sketch",
    "mesh",
    "MESH > CREATE > Create Mesh Section Sketch",
    "Make a sketch of where a plane cuts a mesh body (Create Mesh Section Sketch). Fixed "
    "lines in a new sketch of the active body (made if there is none), on plane XY | "
    "XZ | YZ (or a construction plane's id) moved distance mm along its normal. Use it to "
    "trace a mesh's outline for a rebuild by hand: then redraw the outline with add_to_sketch "
    "lines, arcs and circles (a few clean curves, never the section's hundreds of segments) "
    "and extrude that. Answers the section's loops and segments and their box.",
    schema(
        {
            "body": string(MESH_BODY),
            "plane": string("XY, XZ, YZ or the id of a construction plane", default="XY"),
            "distance": number("move the plane along its normal (mm)", default=0),
            "name": string("the sketch's name (default 'Mesh Section <body>')"),
        }
    ),
    id_base="Sketch",
    title_fn=lambda a: _title("Mesh Section Sketch", a),
    examples=[
        example({"plane": "XY", "distance": 2.5}, "the outline 2.5 mm up the only mesh body"),
        example({"body": "MeshBody", "plane": "XZ", "name": "Side section"}, "a side section"),
    ],
)
