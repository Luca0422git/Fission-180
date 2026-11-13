# SPDX-License-Identifier: LGPL-2.1-or-later
"""AI tools for the MANUFACTURE workspace (wave 7, builder workspaces-2): a setup, the milling
and drilling operations, their toolpaths, Simulate and Post Process, with the numbers an AI
checks its work by. cam_setup, cam_operation, cam_edit, cam_delete, cam_generate,
cam_simulate, cam_post, cam_setups, cam_tools. The work is in
fission180/ai/actions/manufacture_actions.py, on the same code as the workspace's dialogs
(fission180/manufacture.py, manufacture_core.py, manufacture_tools.py). Pure Python."""

from . import kit
from .kit import boolean, enum, free_object, selector, schema, step_id, step_ids, string
from .registry import define, example

# (the same lists as manufacture_core.OPERATIONS / POSTS / TOOL_TYPES: a unit test compares
# them, so the catalogue stays free of FreeCAD and of the workspace's modules)
KINDS = (
    "face",
    "adaptive2d",
    "pocket2d",
    "contour2d",
    "slot",
    "trace",
    "engrave",
    "chamfer2d",
    "bore",
    "circular",
    "drill",
    "adaptive3d",
    "pocket3d",
    "parallel",
    "contour3d",
)
POSTS = (
    "grbl",
    "linuxcnc",
    "mach3_mach4",
    "fanuc",
    "marlin",
    "centroid",
    "smoothie",
    "rrf",
    "refactored_masso_g3",
)
TOOL_TYPES = ("flat", "ball", "bull", "face", "chamfer", "drill", "spot")

SAFETY = (
    " A program must be checked before it runs on a machine: simulate it, read the G-code, "
    "make the first run above the part."
)
SETUP_HELP = "setup: the setup's id or name (cam_setup answers it; default: the newest setup)."
STOCK_HELP = (
    'stock: {"mode": "relative" (the model\'s box plus offsets; offset_mode none | '
    "sides_top_bottom with side / top / bottom (mm) | all_sides with all {xn, xp, yn, yp, zn, "
    'zp}; round_up) | "fixed" (width, depth, height along X, Y, Z of the setup; x_position / '
    "y_position / z_position min | center | max with x_offset / y_offset / z_offset) | "
    '"solid" (stock_body: the id of the body that is the stock) | "preceding" (what the setup '
    "before this one leaves: its stock, for the second side of a part)}."
)
WCS_HELP = (
    'wcs (the work coordinate system): {"orientation": "model" (the design\'s Z is up, '
    'default) | "z_x" | "z_y" | "x_y" with picks z / x ({"face": selector} whose normal, or '
    '{"edge": selector} whose direction is the axis; "of": the body), flip_z, flip_x; '
    '"origin": "stock_point" (default) | "model_point" with box_point [x, y, z] each -1 | 0 | '
    "1 (the box's low side, middle, high side: [-1, -1, 1] is the top corner at low X and Y, "
    '[0, 0, 1] the top centre) | "model_origin" | "selected" with point {"vertex": [x, y, z]}}.'
)
TOOL_HELP = (
    'tool: either a tool of a library, {"library": "sample:mm" | "sample:in" | "local:<name>" '
    '| "document", "id": its id (cam_tools lists them)}, or one described here, {"type": flat '
    '| ball | bull | face | chamfer | drill | spot, "diameter": mm} with anything else to '
    "set (number, flutes, corner_radius, flute_length, cutting {spindle_speed rpm, "
    "cutting_feed, leadin_feed, plunge_feed, ramp_feed mm/min, stepdown, stepover mm}); "
    "sizes left out follow from the diameter, speeds and feeds from the tool's size."
)
OPTIONS_HELP = (
    "options: the dialog's tabs as nested objects, only what differs from the defaults: "
    "feeds {spindle_speed, cutting_feed, leadin_feed, plunge_feed, ramp_feed} over the "
    "tool's own; geometry {flip_side, same_diameter (drill: every hole of the picked "
    "diameter), tabs {on, shape rectangular | triangular, width, height, positioning "
    "distance | count | points, distance, count, points [[x, y, z], ...]}}; heights "
    '{clearance | retract | feed | top | bottom: {"from": model_top | model_bottom | '
    "stock_top | stock_bottom | selection | origin | (a higher one of) retract | feed | top "
    '| bottom, "offset": mm}}; passes {tolerance, direction climb | conventional, '
    "compensation computer | off, stepover, optimal_load, multiple_depths, stepdown, "
    "finishing_passes, finishing_stepover, stock_to_leave, radial_stock, axial_stock, "
    "pass_angle, pass_extension, both_ways, chamfer_width, chamfer_tip_offset, cycle "
    "drilling | counterboring | chip_breaking | deep_drilling, peck_depth, dwell, "
    "tip_through, break_through, pitch}; linking {lead_in, lead_out, lead_radius, ramp "
    "plunge | helix | profile | zigzag, ramp_angle, helix_diameter, keep_down}."
)


def _setup():
    return string("the setup's id or name (default: the newest setup)")


def _extra_setup(args, problems):
    stock = args.get("stock") or {}
    if isinstance(stock, dict) and stock.get("mode") == "solid" and not stock.get("stock_body"):
        problems.append('stock mode "solid" needs stock_body: the id of the body that is the stock')
    wcs = args.get("wcs") or {}
    if isinstance(wcs, dict):
        for key in ("z", "x"):
            pick = wcs.get(key)
            if pick is not None and not (
                isinstance(pick, dict) and ("face" in pick or "edge" in pick)
            ):
                problems.append('wcs.%s must be a pick: {"face": selector} or {"edge": ...}' % key)
        point = wcs.get("point")
        if point is not None and not (isinstance(point, dict) and "vertex" in point):
            problems.append('wcs.point must be {"vertex": [x, y, z]}')


def _extra_tool(args, problems):
    tool = args.get("tool")
    if tool is None:
        return
    if not isinstance(tool, dict):
        problems.append("tool must be an object (see the tool's description)")
        return
    if "library" in tool:
        if not tool.get("id"):
            problems.append('a library tool needs "id": cam_tools lists the tools of a library')
    elif "type" not in tool or "diameter" not in tool:
        problems.append(
            'tool needs "type" and "diameter" (mm), or "library" and "id" of a library tool'
        )
    elif tool["type"] not in TOOL_TYPES:
        problems.append("tool.type must be one of %s" % ", ".join(TOOL_TYPES))
    elif not kit.is_type(tool["diameter"], "number") or tool["diameter"] <= 0:
        problems.append("tool.diameter must be a number above 0 (mm)")


def _extra_operation(args, problems):
    _extra_tool(args, problems)
    if "chain" in args and "edges" not in args:
        problems.append("chain only applies to edges")


def _extra_edit(args, problems):
    _extra_tool(args, problems)
    _extra_setup(args, problems)
    keys = ("options", "tool", "stock", "wcs", "post", "bodies", "suppressed", "label")
    keys += ("faces", "edges", "move")
    if not any(k in args for k in keys):
        problems.append(
            "give what to change: options / tool / faces / edges / suppressed / move / label "
            "(an operation), stock / wcs / post / bodies / suppressed / label (a setup)"
        )


define(
    "cam_setup",
    "New setup",
    "manufacture",
    "MANUFACTURE > MILLING > SETUP > New Setup",
    "Make a manufacturing setup (Fusion's New Setup): how the part sits on the milling "
    "machine and what stock it is cut from. Every operation belongs to a setup; a part "
    "machined from two sides has two. bodies: the bodies to machine (default: every solid "
    "body). " + STOCK_HELP + " " + WCS_HELP + " post: {program: its name or number, comment, "
    "wcs_offset: 1 = G54 ... 6 = G59}. Defaults: a relative stock 1 mm larger on the sides "
    "and the top, the origin at the stock's top centre, Z up as in the design. Answers the "
    "setup's id, and its stock and model boxes in the setup's own coordinates (origin and "
    "axes of the work coordinate system: toolpath numbers are in these). The design's bodies "
    "are never changed by anything in MANUFACTURE.",
    schema(
        {
            "bodies": step_ids(
                "the bodies to machine, or components (all their bodies); default: every "
                "solid body"
            ),
            "stock": free_object("the stock (see the description)"),
            "wcs": free_object("the work coordinate system (see the description)"),
            "post": free_object("program name / number, comment, wcs_offset"),
            "label": string('its name (default "Setup1", "Setup2"...)'),
        }
    ),
    ops=["cam_setup"],
    extra=_extra_setup,
    needs=("solid",),
    id_base="CamSetup",
    title_fn=lambda a: "AI: New Setup",
    examples=[
        example({}, "a setup of every body with the default stock"),
        example(
            {
                "stock": {"mode": "relative", "side": 2, "top": 1, "bottom": 0},
                "wcs": {"origin": "stock_point", "box_point": [-1, -1, 1]},
                "post": {"program": "1001", "comment": "plate"},
            },
            "2 mm of stock around, 1 mm on top; the origin on the stock's top, low X and Y",
        ),
        example(
            {"stock": {"mode": "preceding"}, "wcs": {"orientation": "model", "flip_z": True}},
            "the second side: the part turned over, cut from what the first setup left",
        ),
    ],
)

define(
    "cam_operation",
    "New operation",
    "manufacture",
    "MANUFACTURE > MILLING > 2D / 3D / DRILLING",
    "Add a milling or drilling operation to a setup and make its toolpath. kind: face (the "
    "stock's top down to the model's top; no pick needed), adaptive2d / pocket2d (clear a "
    "pocket: pick its floor face), contour2d (cut along an outline: pick a face, its outer "
    "edge is followed outside the material, or edges with chain), slot, trace (the tool's "
    "centre along picked edges), engrave, chamfer2d (chamfer mill along edges), bore / "
    "circular (helix a round hole: pick its wall), drill (pick hole walls; "
    "options.geometry.same_diameter takes every hole of that size), adaptive3d / pocket3d "
    "(3D roughing), parallel / contour3d (3D finishing; they need OpenCAMLib, the answer "
    "says when FreeCAD has none). faces / edges: selectors on the body `of` (default: the "
    "active body); chain: each picked edge stands for the closed loop it is in. "
    + TOOL_HELP
    + " "
    + OPTIONS_HELP
    + " generate false: add it without a toolpath (cam_generate makes it later). Answers the "
    "operation's id, its state and the toolpath's numbers: cutting and rapid lengths (mm), "
    "machining time, lowest cut Z and the box of every move, in the setup's coordinates. "
    + SETUP_HELP,
    schema(
        {
            "setup": _setup(),
            "kind": enum(KINDS, "the strategy"),
            "faces": selector("the faces picked for it", "faces"),
            "edges": selector("the edges picked for it", "edges"),
            "of": step_id("the body the picks are on (default: the active body)"),
            "chain": boolean("edges: the whole closed loop of each picked edge"),
            "tool": free_object("the tool (see the description)"),
            "options": free_object("the dialog's tabs (see the description)"),
            "generate": boolean("make the toolpath now", default=True),
            "label": string("its name (default: the strategy's, numbered)"),
        },
        ["kind"],
    ),
    ops=["cam_operation"],
    extra=_extra_operation,
    needs=("solid",),
    id_base="CamOp",
    title_fn=lambda a: "AI: New operation (%s)" % a.get("kind", ""),
    examples=[
        example(
            {"kind": "face", "tool": {"type": "flat", "diameter": 10}},
            "face the stock down to the top of the part",
        ),
        example(
            {
                "kind": "contour2d",
                "faces": {"normal": [0, 0, -1], "count": 1},
                "tool": {"library": "sample:mm", "id": "sample-mm-flat-6"},
                "options": {
                    "passes": {"multiple_depths": True, "stepdown": 3},
                    "geometry": {"tabs": {"on": True, "positioning": "count", "count": 4}},
                },
            },
            "cut the part out along its bottom outline in 3 mm steps, held by four tabs",
        ),
        example(
            {
                "kind": "drill",
                "faces": {"type": "cylinder", "radius": 3, "count": 2},
                "tool": {"type": "drill", "diameter": 6},
                "options": {"passes": {"cycle": "chip_breaking", "peck_depth": 2}},
            },
            "drill two 6 mm holes with pecks",
        ),
    ],
)

define(
    "cam_edit",
    "Edit setup or operation",
    "manufacture",
    "MANUFACTURE > browser > right-click > Edit / Suppress",
    "Change a setup or an operation (what a double-click on its browser row opens). target: "
    "its id or name. An operation: options (laid over what it has: give only what changes), "
    "tool, faces / edges / of / chain (picked again: these replace the old picks), "
    "suppressed (true: left out of generate, simulate and post), move (up | down in the "
    "machining order), label; its toolpath is made again unless generate is false. A setup: "
    "stock / wcs / post (laid over what it has), bodies, suppressed, label; its operations "
    'then read "needs regenerating" (cam_generate). '
    + STOCK_HELP
    + " "
    + WCS_HELP
    + " "
    + TOOL_HELP
    + " "
    + OPTIONS_HELP,
    schema(
        {
            "target": step_id("the setup's or the operation's id or name"),
            "options": free_object("an operation's options to change"),
            "tool": free_object("an operation's new tool"),
            "faces": selector("an operation's faces, picked again", "faces"),
            "edges": selector("an operation's edges, picked again", "edges"),
            "of": step_id("the body the new picks are on (default: the active body)"),
            "chain": boolean("edges: the whole closed loop of each picked edge"),
            "stock": free_object("a setup's stock values to change"),
            "wcs": free_object("a setup's work coordinate system values to change"),
            "post": free_object("a setup's program name / number, comment, wcs_offset"),
            "bodies": step_ids("a setup's bodies to machine"),
            "suppressed": boolean("leave it out (true) or bring it back (false)"),
            "move": enum(("up", "down"), "an operation one place up or down in its setup"),
            "label": string("its new name"),
            "generate": boolean("an operation: make its toolpath again", default=True),
        },
        ["target"],
    ),
    ops=["cam_edit"],
    extra=_extra_edit,
    needs=("solid",),
    own_id=False,
    title_fn=lambda a: "AI: Edit %s" % a.get("target", ""),
    examples=[
        example(
            {"target": "2D Contour1", "options": {"passes": {"stepdown": 2}}},
            "a smaller step down; the toolpath is made again",
        ),
        example({"target": "Setup1", "stock": {"top": 2}}, "2 mm of stock on top"),
        example({"target": "Drill1", "suppressed": True}, "leave the drilling out"),
    ],
)

define(
    "cam_delete",
    "Delete setup or operation",
    "manufacture",
    "MANUFACTURE > browser > right-click > Delete",
    "Delete an operation, or a setup with all its operations (one undo step). target: its id "
    "or name. The design's bodies are not touched.",
    schema({"target": step_id("the setup's or the operation's id or name")}, ["target"]),
    destructive=True,
    needs=("design",),
    own_id=False,
    title_fn=lambda a: "AI: Delete %s" % a.get("target", ""),
    examples=[example({"target": "Face1"}, "delete the facing operation")],
)

define(
    "cam_generate",
    "Generate toolpaths",
    "manufacture",
    "MANUFACTURE > MILLING > ACTIONS > Generate",
    "Make the toolpaths that are missing or out of date (Fusion's Generate): after the "
    'design, a setup or an operation changed, cam_setups shows them as "stale" (needs '
    "regenerating). operations: only these; all true: every operation of the setup, the "
    "valid ones too. Fission 180 waits until FreeCAD's CAM engine is done (seconds; an "
    "adaptive clearing can take a minute). Toolpaths are not undo steps. Answers each "
    "operation's state and numbers, and the reason for one that could not be made. " + SETUP_HELP,
    schema(
        {
            "setup": _setup(),
            "operations": step_ids("only these operations (ids or names)"),
            "all": boolean("the up-to-date ones too", default=False),
        }
    ),
    ops=["cam_generate"],
    needs=("solid",),
    own_id=False,
    title_fn=lambda a: "AI: Generate toolpaths",
    examples=[
        example({}, "every toolpath of the newest setup that needs it"),
        example({"setup": "Setup1", "all": True}, "all of Setup1's toolpaths again"),
    ],
)

define(
    "cam_simulate",
    "Simulate",
    "manufacture",
    "MANUFACTURE > MILLING > ACTIONS > Simulate",
    "Play a setup's toolpaths against its stock and answer the numbers (Fusion's Simulate "
    "without the pictures): machining time (s), cutting and rapid distances (mm), the stock's "
    "volume and the volume removed (mm3, within a few percent: a grid of columns), "
    "collisions (rapid moves into material: operation, G-code line, place in setup "
    "coordinates, depth mm), and the stock compared with the model: gouges (the tool cut into "
    "the part: area, deepest, where, the operation) and stock_left_on_model (most and mean "
    "left above the part: a finishing pass needed?). Empty collisions and no gouge is what a "
    "safe program has. operations: only these; each needs an up-to-date toolpath "
    "(cam_generate). Only the cutter is checked, not the holder or clamps. 1 to 10 s (a 3D "
    "finishing toolpath of 100,000 moves: a minute). Changes nothing. " + SETUP_HELP,
    schema(
        {
            "setup": _setup(),
            "operations": step_ids("only these operations (ids or names)"),
        }
    ),
    changes=False,
    needs=("solid",),
    title_fn=lambda a: "AI: Simulate",
    examples=[example({}, "simulate the newest setup")],
)

define(
    "cam_post",
    "Post process",
    "manufacture",
    "MANUFACTURE > MILLING > ACTIONS > Post Process",
    "Write a setup's toolpaths as a G-code program for a controller (Fusion's Post Process) "
    "and check it. post: grbl (default) | linuxcnc | mach3_mach4 | fanuc | marlin | centroid "
    "| smoothie | rrf | refactored_masso_g3; units mm | in; path: the file to write (a full "
    "path; a folder: the program's name with the post's extension is added); program / "
    "comment: over the setup's own; operations: only these. Toolpaths that are missing or "
    "out of date are generated first. Answers the file's path, the operations in it, and "
    "the checker's result: problems (sentences: no units, spindle not started before "
    "cutting, a sideways rapid below the safe height, a move below the lowest cut or outside "
    "the toolpaths' box, no spindle stop), notes, units, lowest and highest Z, the X / Y "
    "box, the tools and the number of lines. An empty problems list does not make a program "
    "safe for a particular machine." + SAFETY + " A file that exists is not replaced unless "
    "the person agrees. " + SETUP_HELP,
    schema(
        {
            "setup": _setup(),
            "path": string("the G-code file to write, or the folder for it (a full path)"),
            "post": enum(POSTS, "the controller's dialect", default="grbl"),
            "units": enum(("mm", "in"), "the program's units", default="mm"),
            "program": string("the program's name or number (default: the setup's)"),
            "comment": string("the program's comment (default: the setup's)"),
            "operations": step_ids("only these operations (ids or names)"),
        },
        ["path"],
    ),
    ops=["cam_post"],
    changes=False,
    writes_files=True,
    confirm_overwrite=True,
    needs=("solid",),
    title_fn=lambda a: "AI: Post Process",
    examples=[
        example({"path": "~/cnc/plate.nc"}, "the newest setup as Grbl G-code"),
        example(
            {"setup": "Setup1", "path": "~/cnc", "post": "linuxcnc", "units": "in"},
            "Setup1 for LinuxCNC in inches, named after its program number",
        ),
    ],
)

define(
    "cam_setups",
    "Setups and operations",
    "manufacture",
    "MANUFACTURE > browser > Setups",
    "Read the MANUFACTURE browser: every setup (id, name, stock and model boxes in its own "
    "coordinates, where its origin is in the design, warnings) with its operations in "
    "machining order: id, name, kind, tool, state (valid | stale: needs regenerating | "
    "empty: no toolpath yet | error | suppressed), the reason of an error, and the "
    "toolpath's numbers (cut_length, rapid_length mm, time_s, min_cut_z, bounds). details "
    "true adds every option of each setup and operation as cam_edit takes them, and the "
    "heights in mm. setup: only this one. Changes nothing.",
    schema(
        {
            "setup": string("only this setup (id or name; default: all)"),
            "details": boolean("add every option and the heights", default=False),
        }
    ),
    changes=False,
    needs=("design",),
    title_fn=lambda a: "AI: Read setups",
    examples=[
        example({}, "every setup and operation with its state"),
        example({"setup": "Setup1", "details": True}, "Setup1 with every option"),
    ],
)

define(
    "cam_tools",
    "Tool library",
    "manufacture",
    "MANUFACTURE > MILLING > MANAGE > Tool Library",
    "Read the Tool Library. Without library: the libraries (key, title, how many tools): "
    "document (the tools this design's operations use), local:<name> (the person's own, on "
    "this computer), sample:mm and sample:in (Fission 180's sample end mills, ball mills, "
    "bull nose mills, face mills, chamfer mills, spot drills and drills). With library: its "
    "tools: id (what cam_operation's tool takes), name, number, type, diameter and lengths "
    "(mm), flutes, and the cutting data (spindle_speed rpm, feeds mm/min, stepdown, stepover "
    "mm). type / diameter (mm, within 0.01) narrow the list. Changes nothing "
    "(cam_tool_library adds, edits and copies tools).",
    schema(
        {
            "library": string("a library's key (default: list the libraries)"),
            "type": enum(TOOL_TYPES, "only tools of this type"),
            "diameter": kit.positive("only tools of this diameter (mm)"),
        }
    ),
    changes=False,
    needs=(),
    title_fn=lambda a: "AI: Read tool library",
    examples=[
        example({}, "the libraries"),
        example({"library": "sample:mm", "type": "flat"}, "the metric sample end mills"),
    ],
)


# == wave 8, ai-workspaces: the Setup Sheet and the Tool Library's changes ======================
define(
    "cam_setup_sheet",
    "Setup sheet",
    "manufacture",
    "MANUFACTURE > MILLING > ACTIONS > Setup Sheet",
    "Write a setup's Setup Sheet (Fusion's): one HTML page for the person at the machine with "
    "the program, the work coordinate system and its origin, the stock and model sizes, every "
    "tool (number, type, diameter, flute length, flutes) and every operation in machining "
    "order (strategy, tool, spindle speed, feeds, stepdown, stepover, lowest Z, cutting "
    'length and time). path: a full path (.html added; a folder: "<setup> setup '
    'sheet.html" in it). Operations without an up-to-date toolpath have no numbers (the '
    "answer names them: cam_generate first). A file that exists is not replaced unless the "
    "person agrees. " + SETUP_HELP,
    schema(
        {"setup": _setup(), "path": string("the HTML file to write, or its folder (a full path)")},
        ["path"],
    ),
    changes=False,
    writes_files=True,
    confirm_overwrite=True,
    needs=("solid",),
    title_fn=lambda a: "AI: Setup Sheet",
    examples=[example({"path": "~/cnc"}, "the newest setup's sheet in ~/cnc")],
)

TOOL_LIBRARY_ACTIONS = ("add", "edit", "delete", "copy", "new_library", "delete_library")


def _extra_tool_library(args, problems):
    what = args.get("action")
    needs = {
        "add": ("tool",),
        "edit": ("id", "tool"),
        "delete": ("id",),
        "copy": ("id",),
        "new_library": ("name",),
        "delete_library": ("library",),
    }.get(what, ())
    for key in needs:
        if key not in args:
            problems.append("%s needs %s" % (what, key))
    allowed = {
        "add": {"library", "tool"},
        "edit": {"library", "id", "tool"},
        "delete": {"library", "id"},
        "copy": {"from_library", "to_library", "id"},
        "new_library": {"name"},
        "delete_library": {"library"},
    }.get(what, set())
    for key in args:
        if key != "action" and key not in allowed:
            problems.append("%s is not for action %s" % (key, what))
    tool = args.get("tool")
    if what == "add" and isinstance(tool, dict):
        _extra_tool({"tool": tool}, problems)
    if what == "edit" and isinstance(tool, dict) and ("type" in tool or "library" in tool):
        problems.append("edit changes a tool's values (diameter, cutting...), not its type")


define(
    "cam_tool_library",
    "Change tool library",
    "manufacture",
    "MANUFACTURE > MILLING > MANAGE > Tool Library (New Tool, Edit, Copy, Delete, New Library)",
    "Change the Tool Library (Fusion's Tool Library dialog). action add: a new tool in "
    "library (default local:Local) from tool {type, diameter, ...} as cam_operation takes it "
    "(number: the next free one unless given); edit: the tool id's values laid over (tool: "
    'only what changes, e.g. {"cutting": {"spindle_speed": 18000}}; in library document it '
    "changes every operation using it, one undo step, and their toolpaths need regenerating); "
    "delete: tool id from a library; copy: tool id from from_library (a sample library too) "
    "into to_library (default local:Local); new_library: an empty local library called name; "
    "delete_library: a local library with its tools (the person is asked first). The sample "
    "libraries never change. Local libraries are FreeCAD tool files on this computer, shared "
    "by every design. Answers the tool with its id (what cam_operation's tool takes).",
    schema(
        {
            "action": enum(TOOL_LIBRARY_ACTIONS, "what to do"),
            "library": string("the library's key (cam_tools lists them; default local:Local)"),
            "id": string("the tool's id (cam_tools lists it)"),
            "tool": free_object("add: the new tool; edit: the values to change"),
            "from_library": string("copy: the library the tool is in"),
            "to_library": string("copy: a local library (default local:Local)"),
            "name": string("new_library: its name"),
        },
        ["action"],
    ),
    extra=_extra_tool_library,
    writes_files=True,
    destructive=True,
    needs=(),
    own_id=False,
    title_fn=lambda a: "AI: Tool library %s" % str(a.get("action", "")).replace("_", " "),
    examples=[
        example(
            {"action": "add", "tool": {"type": "flat", "diameter": 3.175, "flutes": 1}},
            "a 1/8 in single-flute end mill in the Local library",
        ),
        example(
            {
                "action": "copy",
                "from_library": "sample:mm",
                "id": "sample-mm-flat-6",
                "to_library": "local:Local",
            },
            "copy the sample 6 mm end mill to change it",
        ),
        example(
            {
                "action": "edit",
                "library": "document",
                "id": "sample-mm-flat-6",
                "tool": {"cutting": {"cutting_feed": 600}},
            },
            "slower feed for every operation of this design using that end mill",
        ),
    ],
)
