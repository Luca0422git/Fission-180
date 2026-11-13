# SPDX-License-Identifier: LGPL-2.1-or-later
"""AI tools for the timeline (history), parameters, design files, import, the view and help
(the drawing tools are in drawing_tools.py). Pure Python (the work is in fission180/ai/actions)."""

from . import kit
from .kit import (
    boolean,
    enum,
    number,
    schema,
    step_id,
    step_ids,
    string,
)
from .registry import define, example

# -- TIMELINE -----------------------------------------------------------------------------------
define(
    "get_timeline",
    "Get timeline",
    "timeline",
    "TIMELINE (the bar at the bottom)",
    "List the timeline in order: every step with its id, its name as the timeline shows it "
    '("Extrude 2"), its kind, the body / component it belongs to, whether it is before the '
    "history marker (done) or after it (rolled_back), suppressed, its status (ok, warning, "
    "error, with the reason in plain words) and its main values (distance, radius, "
    "quantity...); plus where the history marker stands.",
    schema({}),
    changes=False,
    examples=[example({}, "the steps, their state and the marker")],
)
define(
    "get_step",
    "Get step",
    "timeline",
    "TIMELINE > double-click a step (the dialog's fields)",
    "Read one step's definition, the way its dialog shows it when you double-click it: its "
    "kind and every option (distances, angles, operation, what it is built on), the "
    "formulas that drive values, its status and what it uses. The names of the options are "
    "the ones edit_step takes.",
    schema({"step": step_id("the step")}, ["step"]),
    changes=False,
    examples=[example({"step": "Extrude1"}, "Extrude1's options")],
)


def _extra_edit_step(args, problems):
    if not args.get("set") and not args.get("add_edges") and not args.get("add_faces"):
        problems.append("give set (the options to change) or add_edges / add_faces (fillets)")
    for key, element in (("add_edges", "edges"), ("add_faces", "faces")):
        if key in args:
            kit.check_selector(args[key], key, element, problems)


define(
    "edit_step",
    "Edit step",
    "timeline",
    "TIMELINE > double-click a step > change its fields > OK",
    "Change an existing step's options, as double-clicking it in the timeline: set {option: "
    "value} with the names get_step shows (extrude: distance, distance2, taper, direction, "
    "operation, through_all...; revolve: angle, type, direction, operation; fillet / chamfer: "
    "radius, distance...; hole: diameter, depth, extent, hole_type...; patterns: quantity, "
    "distance, angle...; shell, draft, scale, sweep, loft, rib, primitives, coil, pipe, gear, "
    "hardware, emboss, thread, surface, combine, split, move, align, construction planes...; "
    "sheet metal flange: height, angle, distance, position, datum, width_type...; bend, hem, "
    "corner closure, lofted flange, snap fit, lip, surface modify: the options get_step "
    "lists). "
    "A fillet or chamfer also takes add_edges / add_faces (more edges). The steps after it "
    "update and keep their faces and edges; steps that break are named in the answer. An "
    "option name the step does not have is refused with the names it has (get_step's values "
    "spellings, like Radius, are taken too; a shell takes thickness); an edit that changes "
    "nothing says so and adds no Undo step. An extrude's distance keeps the side it goes "
    "to: flip: true reverses it.",
    schema(
        {
            "step": step_id("the step to change"),
            "set": kit.free_object("{option: value}"),
            "add_edges": kit.selector("fillet / chamfer: more edges", "edges"),
            "add_faces": kit.selector("fillet / chamfer: every edge around more faces"),
        },
        ["step"],
    ),
    extra=_extra_edit_step,
    own_id=False,
    ops=[
        "edit",
        "sf_revolve_edit",
        "pattern_edit",
        "sf_shell_edit",
        "sf_draft_edit",
        "sf_draft2_edit",
        "sf_scale_edit",
        "sf_scale_sketch_edit",
        "body_tool_edit",
        "blend_edit",
        "sf_primitive_edit",
        "sf_sweep_edit",
        "sf_loft_edit",
        "sf_rib_edit",
        "sf_surface_edit",
        "modify_edit",
        "move_face_edit",
        "sf_gear_edit",
        "sf_hardware_edit",
        "sf_flange_edit",
        "sf_sm_more_edit",
        "sf_snap_fit_edit",
        "sf_lip_edit",
        "sf_surface_modify_edit",
    ],
    title_fn=lambda a: "AI: Edit %s" % a.get("step", "step"),
    examples=[
        example({"step": "Extrude1", "set": {"distance": 15}}, "make the extrude 15 mm"),
        example({"step": "Fillet1", "set": {"radius": 2}}, "change the fillet to 2 mm"),
    ],
)


def _extra_roll(args, problems):
    kit.exactly_one(args, ("to", "after", "before"), problems, "where the marker goes")


define(
    "roll_timeline",
    "Move history marker",
    "timeline",
    "TIMELINE > drag the history marker (and the playback buttons)",
    "Move the timeline's history marker: to start (an empty design), end, previous / next "
    "(one step), or after / before a step. Steps after the marker are rolled back (not "
    "computed); a new feature goes in at the marker, as in Fusion. Move it back to the end "
    "when you are done.",
    schema(
        {
            "to": enum(["start", "end", "previous", "next"]),
            "after": step_id("put the marker right after this step"),
            "before": step_id("put the marker right before this step"),
        },
    ),
    ops=["roll"],
    extra=_extra_roll,
    own_id=False,
    title_fn=lambda a: "AI: Roll history marker",
    examples=[
        example({"after": "Extrude1"}, "roll back to just after Extrude1"),
        example({"to": "end"}, "roll forward to the end"),
    ],
)
define(
    "suppress_step",
    "Suppress / unsuppress",
    "timeline",
    "TIMELINE > right-click a step > Suppress Features",
    "Suppress steps (they stay in the timeline but are skipped, as if they were not there) "
    "or bring them back (suppress: false). Steps that depend on them are suppressed with "
    "them; the answer names them.",
    schema({"steps": step_ids("the steps"), "suppress": boolean(default=True)}, ["steps"]),
    ops=["suppress", "unsuppress"],
    own_id=False,
    title_fn=lambda a: "AI: %s" % ("Suppress" if a.get("suppress", True) else "Unsuppress"),
    examples=[example({"steps": ["Fillet1"]}, "try the part without the fillet")],
)
define(
    "delete_step",
    "Delete step",
    "timeline",
    "TIMELINE > right-click a step > Delete",
    "Delete steps from the timeline (Fusion asks the same: steps that depend on them may "
    "break and are named in the answer). Undo brings them back.",
    schema({"steps": step_ids("the steps")}, ["steps"]),
    ops=["delete"],
    own_id=False,
    destructive=True,
    title_fn=lambda a: "AI: Delete steps",
    examples=[example({"steps": ["Chamfer1"]}, "delete the chamfer")],
)


def _extra_move_step(args, problems):
    kit.exactly_one(args, ("before", "after"), problems)


define(
    "move_step",
    "Reorder step",
    "timeline",
    "TIMELINE > drag a step",
    "Move a step before or after another one in the timeline. A step can never move before "
    "what it is built on: the refusal says why.",
    schema({"step": step_id("the step"), "before": step_id(), "after": step_id()}, ["step"]),
    ops=["move"],
    extra=_extra_move_step,
    own_id=False,
    title_fn=lambda a: "AI: Move %s" % a.get("step", "step"),
    examples=[example({"step": "Fillet1", "after": "Extrude2"}, "fillet after the boss")],
)
define(
    "rename",
    "Rename",
    "timeline",
    "TIMELINE / BROWSER > right-click > Rename",
    "Rename a timeline step, a body, a component, a sketch or a drawing (what the timeline "
    "and browser show). The id stays the same.",
    schema(
        {"target": step_id("the thing to rename"), "name": string("the new name")},
        ["target", "name"],
    ),
    own_id=False,
    title_fn=lambda a: "AI: Rename %s" % a.get("target", ""),
    examples=[example({"target": "Extrude1", "name": "Base plate"}, "name the first extrude")],
)


def _extra_group(args, problems):
    if args.get("ungroup"):
        if "group" not in args:
            problems.append("ungroup needs group (the group's id from get_timeline)")
    elif len(args.get("steps") or []) < 2:
        problems.append("a group needs at least 2 steps next to each other")


define(
    "group_steps",
    "Group steps",
    "timeline",
    "TIMELINE > select steps > right-click > Group",
    "Group neighbouring timeline steps under one name (Fusion's timeline groups), or "
    "ungroup (ungroup: true with the group's id).",
    schema(
        {
            "steps": step_ids("the steps (next to each other)", 2),
            "name": string("the group's name"),
            "ungroup": boolean(default=False),
            "group": string("ungroup: the group's id (get_timeline)"),
        },
    ),
    extra=_extra_group,
    own_id=False,
    title_fn=lambda a: "AI: %s" % ("Ungroup" if a.get("ungroup") else "Group steps"),
    examples=[example({"steps": ["Sketch2", "Extrude2"], "name": "Boss"}, "group the boss")],
)

# -- PARAMETERS ---------------------------------------------------------------------------------
define(
    "list_parameters",
    "List parameters",
    "parameters",
    "MODIFY > Change Parameters",
    "List the design's parameters, as Change Parameters shows them: user parameters (name, "
    "unit, formula, value, comment), parameters brought in by a Derive (read-only), and "
    "model parameters: every dimension in the design (each step's values and each sketch "
    "dimension: the step id, its label, value, unit and formula).",
    schema({"model": boolean("include the model parameters", default=True)}),
    changes=False,
    examples=[example({}, "every parameter and dimension")],
)
define(
    "delete_parameter",
    "Delete parameter",
    "parameters",
    "MODIFY > Change Parameters > a user parameter > Delete",
    "Delete a user parameter. Refused, with the names, while formulas still use it.",
    schema({"name": string("the parameter")}, ["name"]),
    own_id=False,
    destructive=True,
    title_fn=lambda a: "AI: Delete parameter %s" % a.get("name", ""),
    examples=[example({"name": "gap"}, "delete the unused parameter gap")],
)


def _extra_model_parameter(args, problems):
    if ("value" in args) == ("expression" in args):
        problems.append("give value or expression, one of them")


define(
    "set_model_parameter",
    "Set model parameter",
    "parameters",
    "MODIFY > Change Parameters > Model Parameters",
    "Change a model parameter: one value of a step (label as list_parameters shows it: "
    '"Distance", "Radius", "Set 1 Size", "Quantity"...) or a sketch dimension (its '
    "name or label). value (mm / degrees / a count) or expression (a formula with user "
    "parameters, kept as a link). Everything after it updates.",
    schema(
        {
            "step": step_id("the step or sketch"),
            "label": string("which of its values (from list_parameters)"),
            "value": number(),
            "expression": string("a formula"),
        },
        ["step", "label"],
    ),
    extra=_extra_model_parameter,
    own_id=False,
    title_fn=lambda a: "AI: %s %s" % (a.get("step", ""), a.get("label", "")),
    examples=[
        example(
            {"step": "Extrude1", "label": "Distance", "expression": "height"},
            "Extrude1's distance follows the parameter height",
        )
    ],
)

# -- DESIGNS AND FILES --------------------------------------------------------------------------
define(
    "new_design",
    "New design",
    "document",
    "File > New Design",
    "Start a new, empty design (with one body) and make it the active one. name: its name.",
    schema({"name": string("the design's name", default="Untitled")}),
    needs=(),
    title_fn=lambda a: "AI: New design",
    examples=[example({"name": "Bracket"}, "a new design called Bracket")],
)


def _extra_open(args, problems):
    path = args.get("path")
    if isinstance(path, str) and not path.lower().endswith(
        (".fcstd", ".step", ".stp", ".igs", ".iges")
    ):
        problems.append("path must be a design (.FCStd) or a STEP / IGES file")


define(
    "open_design",
    "Open design",
    "document",
    "File > Open",
    "Open a design (.FCStd) or a STEP / IGES file as a new design (its components and bodies "
    "kept). A design that is already open comes to the front. It becomes the active design. "
    "For a STEP / IGES file the answer also lists what the file had that did not come in or "
    'came in changed ("Not brought in, or changed:" and one line each: loose faces, '
    "curves and points, surface bodies, bodies with geometry errors).",
    schema({"path": string("full path of the file")}, ["path"]),
    needs=(),
    changes=False,
    extra=_extra_open,
    examples=[example({"path": "/home/me/designs/bracket.FCStd"}, "open a saved design")],
)
define(
    "save_as",
    "Save as",
    "document",
    "File > Save As",
    "Save the design under a new name (a full path ending in .FCStd); the design then lives "
    "there. Replacing another existing file must be confirmed by the person in Fission 180.",
    schema({"path": string("full path ending in .FCStd")}, ["path"]),
    changes=False,
    writes_files=True,
    confirm_overwrite=True,
    extra=lambda a, p: (
        None
        if str(a.get("path", "")).lower().endswith(".fcstd")
        else p.append("path must end in .FCStd")
    ),
    examples=[example({"path": "/home/me/designs/bracket-v2.FCStd"}, "a copy under a new name")],
)


def _extra_close(args, problems):
    if "design" in args and not isinstance(args["design"], str):
        problems.append("design must be a design's name")


define(
    "close_design",
    "Close design",
    "document",
    "File > Close",
    "Close a design (default: the active one). Unsaved changes are refused unless "
    "discard_changes is true (the person in Fission 180 is asked first). A design text that "
    "fits several open designs (one's id is another's name) is refused with their ids. "
    "Another open design becomes the active one.",
    schema(
        {
            "design": string("the design's id or name (list_designs)"),
            "discard_changes": boolean("close even with unsaved changes", default=False),
        }
    ),
    destructive=True,
    own_id=False,
    needs=(),  # (design names one: no active design needed)
    title_fn=lambda a: "AI: Close design",
    extra=_extra_close,
    examples=[example({}, "close the active design (it must be saved)")],
)
define(
    "list_designs",
    "List designs",
    "document",
    "the design tabs",
    "List the open designs: name, label, file, whether it has unsaved changes and which one "
    "is active.",
    schema({}),
    changes=False,
    needs=(),
    examples=[example({}, "which designs are open")],
)
define(
    "switch_design",
    "Switch design",
    "document",
    "click a design tab",
    "Make another open design the active one (the tools then work on it). A text that fits "
    "several open designs (one's id is another's name) is refused with their ids.",
    schema({"design": string("its id or name (list_designs)")}, ["design"]),
    changes=False,
    needs=(),
    examples=[example({"design": "Bracket"}, "work on Bracket")],
)


def _extra_import(args, problems):
    path = args.get("path")
    if isinstance(path, str) and not path.lower().endswith(
        (".step", ".stp", ".igs", ".iges", ".stl", ".obj", ".3mf", ".dxf", ".fcstd")
    ):
        problems.append("path must be STEP, IGES, STL, OBJ, 3MF, DXF or FCStd")
    if "sketch_plane" in args and not str(path).lower().endswith(".dxf"):
        problems.append("sketch_plane is only used for DXF files")


define(
    "import_file",
    "Insert file",
    "import_export",
    "INSERT > Insert Mesh / Insert DXF / Insert STEP, and Insert into Current Design",
    "Bring a file into the active design: STEP / IGES (one component with the file's "
    "structure, its bodies and colours), STL / OBJ / 3MF (a mesh body; unit: the file's "
    "unit), DXF (its curves into a new sketch on sketch_plane XY | XZ | YZ, ready to "
    "extrude), FCStd (another design's bodies as a component). label names what is made. "
    "The answer also lists what the file had that did not come in or came in changed "
    '("Not brought in, or changed:" and one line each, as INSERT\'s message says: an '
    "open mesh, a 3MF's unit or colours, DXF texts, hatches and points, loose faces of a "
    "STEP...); a mesh whose file says another unit can be inserted again with unit.",
    schema(
        {
            "path": string("full path of the file"),
            "unit": enum(
                ["mm", "cm", "m", "in", "ft"], "mesh / DXF files: the file's unit", default="mm"
            ),
            "sketch_plane": enum(["XY", "XZ", "YZ"], "DXF: the plane", default="XY"),
            "label": string("the name of what is made"),
        },
        ["path"],
    ),
    extra=_extra_import,
    needs=(),
    id_base="Insert",
    title_fn=lambda a: "AI: Insert %s" % str(a.get("path", "")).replace("\\", "/").split("/")[-1],
    examples=[
        example({"path": "/home/me/parts/motor.step"}, "a motor model as a component"),
        example({"path": "/home/me/logo.dxf", "sketch_plane": "XY"}, "a DXF outline as a sketch"),
    ],
)

# -- DRAWINGS: drawing_tools.py (wave 8, ai-drawing: every command of the DRAWING workspace)

# -- VIEW ---------------------------------------------------------------------------------------
define(
    "set_view",
    "Set view",
    "view",
    "NAVIGATION BAR and VIEWCUBE (Home, Fit, Orbit, Look At)",
    "Turn the 3D view: orientation iso | home | front | back | top | bottom | left | right, "
    "fit (zoom so everything shows, default true), projection perspective | orthographic, "
    "or camera (a camera string get_view returned), or look_at: a face selector (the view "
    "looks straight at that face, Fusion's Look At).",
    schema(
        {
            "orientation": enum(["iso", "home", "front", "back", "top", "bottom", "left", "right"]),
            "fit": boolean(default=True),
            "projection": enum(["perspective", "orthographic"]),
            "camera": string("a camera description from get_view"),
            "look_at": kit.selector("look straight at this face"),
        },
    ),
    changes=False,
    needs=("design", "gui"),
    examples=[example({"orientation": "top"}, "look from the top, fitted")],
)
define(
    "get_view",
    "Get view",
    "view",
    "(the 3D view's camera)",
    "The 3D view's camera now (a string set_view takes back), its projection, and the saved "
    "named views of the design.",
    schema({}),
    changes=False,
    needs=("design", "gui"),
    examples=[example({}, "the camera and the named views")],
)


def _extra_named_view(args, problems):
    if args.get("action") in ("save", "go", "delete") and not args.get("name"):
        problems.append("%s needs name" % args.get("action"))


define(
    "named_view",
    "Named view",
    "view",
    "BROWSER > Named Views (New Named View, go to, delete)",
    "Named views kept in the design (Fusion's Named Views): action save (the current camera "
    "under name), go (turn the view to it), delete, list.",
    schema(
        {
            "action": enum(["save", "go", "delete", "list"]),
            "name": string("the view's name"),
        },
        ["action"],
    ),
    extra=_extra_named_view,
    own_id=False,
    title_fn=lambda a: "AI: Named view %s" % a.get("name", ""),
    examples=[example({"action": "save", "name": "Assembly view"}, "remember this camera")],
)
define(
    "show_hide",
    "Show / hide",
    "view",
    "BROWSER > the eye icon (Show / Hide)",
    "Show or hide bodies, components, sketches, construction geometry or drawings in the 3D "
    "view (they stay in the design). targets: ids; visible: true shows, false hides. Not an "
    "undo step: call it again to reverse it (undo would take back the step before it).",
    schema(
        {"targets": step_ids("what to show or hide"), "visible": boolean()}, ["targets", "visible"]
    ),
    own_id=False,
    title_fn=lambda a: "AI: %s" % ("Show" if a.get("visible") else "Hide"),
    examples=[example({"targets": ["Sketch1"], "visible": False}, "hide Sketch1")],
)

# -- HELP ---------------------------------------------------------------------------------------
HELP_TOPICS = (
    "overview",
    "selectors",
    "picks",
    "body_picks",
    "sketches",
    "geometry",
    "curves",
    "steps",
    "expressions",
    "workflow",
    "checking",
    "docs",
    "tools",
)
define(
    "get_help",
    "Get help",
    "help",
    "(Fission 180's documentation for AI models)",
    "Read Fission 180's rules for AI tools: overview, selectors (how to pick faces and edges), "
    "picks (planes, axes, faces, edges, corners), body_picks, sketches (planes and "
    "coordinates), geometry (sketch shapes), curves (paths and rails), steps (ids), "
    "expressions (parameters in fields), workflow (how to build and check a part), checking "
    "(the tools that check your work with numbers and pictures), docs (where the documentation "
    "is and how to search it), tools (every tool by category with its Fusion command). "
    "Without topic: overview.",
    schema({"topic": enum(HELP_TOPICS, default="overview")}),
    changes=False,
    needs=(),
    examples=[example({"topic": "selectors"}, "how selectors pick faces and edges")],
)
define(
    "list_tools",
    "List tools",
    "help",
    "(Fission 180's command list)",
    "List every tool by category with its Fusion command, whether it changes the design, "
    "and whether it can run right now (and why not: no design open, no solid yet, needs the "
    "Fission 180 window...). category: only that category.",
    schema(
        {
            "category": enum(
                [
                    c
                    for c in (
                        "help",
                        "document",
                        "inspect",
                        "sketch",
                        "create",
                        "modify",
                        "surface",
                        "construct",
                        "assemble",
                        "timeline",
                        "parameters",
                        "import_export",
                        "drawing",
                        "view",
                        "simulate",
                        "rebuild",
                        "sheet_metal",
                        "plastic",
                    )
                ]
            )
        }
    ),
    changes=False,
    needs=(),
    examples=[example({"category": "modify"}, "the Modify tools and which can run now")],
)
