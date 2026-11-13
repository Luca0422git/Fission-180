# SPDX-License-Identifier: LGPL-2.1-or-later
"""AI tools for drawings: Fusion's DRAWING workspace. File > New Drawing (From Design, From
Animation), the DRAWING tab's CREATE, MODIFY, GEOMETRY, DIMENSIONS, TEXT, SYMBOLS, TABLES and
EXPORT groups and the sheet bar, every command through the code its dialog runs
(fission180/ai/actions/drawing_actions.py: drawing.py, drawing_annot.py, drawing_tools.py,
drawing_sheets.py, drawing_breakout.py, drawing_exploded.py, drawing_export.py,
flatpattern_drawing.py). Wave 8, builder ai-drawing (the first six tools were in
history_tools.py; their names and argument shapes are kept). Pure Python."""

from . import kit
from .kit import array, boolean, enum, integer, number, obj, positive, schema, step_id, string
from .registry import define, example

ORIENTATIONS = ("Front", "Back", "Top", "Bottom", "Left", "Right", "Home")
PROJECTED = (
    "Top",
    "Bottom",
    "Left",
    "Right",
    "FrontTopRight",
    "FrontTopLeft",
    "FrontBottomRight",
    "FrontBottomLeft",
)
STYLES = ("Visible Edges", "Visible and Hidden Edges", "Shaded", "Shaded with Hidden Edges")
TANGENT_EDGES = ("Full Length", "Off")  # drawing_core.TANGENT_EDGES
DEPTH_MODES = ("Full", "Slice", "Distance")  # drawing.DEPTH_MODES
VIEW_KINDS = ("base", "projected", "section", "detail", "break", "breakout", "exploded")
DIMENSION_TYPES = (
    "linear",
    "aligned",
    "radius",
    "diameter",
    "angular",
    "arc_length",
    "ordinate",
    "baseline",
    "chain",
)
ANNOTATION_KINDS = (
    "text",
    "leader",
    "bend_note",
    "parts_list",
    "bend_table",
    "balloon",
    "center_marks",
)
GEOMETRY_KINDS = ("center_mark", "centerline", "center_mark_pattern", "edge_extension")
SYMBOL_KINDS = ("surface_texture", "feature_control_frame", "datum_identifier")
# drawing_annot_core.CHARACTERISTIC_NAMES, SURFACE_KINDS, LAYS, MODIFIERS (a unit test checks)
CHARACTERISTICS = (
    "position",
    "concentricity",
    "symmetry",
    "parallelism",
    "perpendicularity",
    "angularity",
    "cylindricity",
    "flatness",
    "circularity",
    "straightness",
    "profile_surface",
    "profile_line",
    "circular_runout",
    "total_runout",
)
TEXTURES = ("basic", "removal", "no_removal")
LAYS = ("", "=", "⊥", "X", "M", "C", "R", "P")
MATERIAL = ("", "M", "L")
# drawing_dims_core.TOLERANCES, PRECISIONS, FIT_DISPLAYS (lower case here)
TOLERANCES = ("none", "symmetric", "deviation", "limits", "fit")
PRECISIONS = ("Default", "0", "0.1", "0.12", "0.123", "0.1234")
FIT_DISPLAYS = ("class", "class_and_tolerances", "limits", "fit")
# drawing_core.TITLE_KEYS
TITLE_KEYS = (
    "Title",
    "PartNumber",
    "Description",
    "Material",
    "DrawnBy",
    "Date",
    "CheckedBy",
    "ApprovedBy",
    "Scale",
    "Size",
    "Sheet",
    "Units",
    "Revision",
)

VIEW_MM = (
    "in the view's own mm: model size (not scaled) from the view's centre, x right, y up, as "
    "get_drawing with edges true lists its elements"
)
SHEET_MM = "[x, y] on the sheet (mm from its bottom left corner)"


def _element(description="an element of the view"):
    return obj(
        {
            "kind": enum(["line", "circle", "arc", "vertex"]),
            "near": kit.numbers(2, "[x, y] %s" % VIEW_MM),
            "radius": positive("circles / arcs: the radius (model mm)"),
        },
        description=description,
    )


def _check_element(item, path, problems):
    if isinstance(item, dict) and not ({"near", "kind"} & set(item)):
        problems.append("%s needs near (a point of the view) and / or kind" % path)


def _point_list(description, minimum=None, maximum=None):
    return array(kit.numbers(2), description, minimum, maximum)


# -- CREATE: the drawing --------------------------------------------------------------------------
def _extra_create(args, problems):
    given = [k for k in ("bodies", "flat_pattern", "contents") if k in args]
    if len(given) > 1:
        problems.append("give one of bodies, flat_pattern or contents")
    if args.get("automatic") and ("projected" in args or "at" in args):
        problems.append("automatic lays out its own views: leave out projected and at")


define(
    "create_drawing",
    "Create drawing",
    "drawing",
    "File > New Drawing > From Design / From Animation",
    "Make a 2D drawing of the design, kept in the design and updated with it. What it shows: "
    "bodies (step ids; default every visible body), contents full_assembly (every body, also "
    "ones made later), flat_pattern (a sheet metal body or its flat pattern: drawn from the "
    "top, for bend_table / bend_note) or storyboard (From Animation: the views show that "
    "storyboard's end, exploded). standard ISO | ASME, sheet (A4..A0 ISO, A..E ASME), units "
    "mm | in, title_block. automatic true: base Front, Top, Right and an isometric laid out at "
    "the largest standard scale that fits. Else a base view (base_view orientation, at [x, y] "
    "sheet mm, scale, style) and projected views (Top, Right, FrontTopRight...). Answers the "
    "ids and the scale. About 1 s per view for a 1,000-face assembly.",
    schema(
        {
            "bodies": kit.step_ids("the bodies to draw (default: every visible body)"),
            "contents": enum(
                ["full_assembly", "visible_only"],
                "full_assembly: every body, and ones made later come in (instead of bodies)",
            ),
            "flat_pattern": step_id("a sheet metal body (or its flat pattern) to draw flat"),
            "storyboard": string("an animation storyboard: every view shows its end, exploded"),
            "standard": enum(["ISO", "ASME"], default="ISO"),
            "sheet": string("A4, A3, A2, A1, A0 (ISO) or A, B, C, D, E (ASME)"),
            "units": enum(["mm", "in"], default="mm"),
            "title_block": boolean(default=True),
            "label": string("the drawing's name"),
            "automatic": boolean("base, two projected and an isometric view, laid out to fit"),
            "base_view": enum(ORIENTATIONS, "the base view's orientation", default="Front"),
            "at": kit.numbers(2, "%s of the base view" % SHEET_MM),
            "scale": positive("view scale, 0.5 for 1:2 (default: fits the sheet)"),
            "style": enum(STYLES, default="Visible and Hidden Edges"),
            "projected": array(enum(PROJECTED), "projected views to add"),
        },
    ),
    extra=_extra_create,
    needs=("solid",),
    id_base="Drawing",
    title_fn=lambda a: "AI: New drawing",
    examples=[
        example(
            {"base_view": "Front", "projected": ["Top", "Right", "FrontTopRight"]},
            "the classic three views plus an isometric",
        ),
        example({"automatic": True, "sheet": "A3"}, "Fusion's automatic views on an A3 sheet"),
    ],
)


# -- CREATE: views --------------------------------------------------------------------------------
def _extra_drawing_view(args, problems):
    kind = args.get("kind")
    if kind in ("projected", "section", "detail", "break", "breakout") and "parent" not in args:
        problems.append("a %s view needs parent (a view id)" % kind)
    if kind == "projected" and "direction" not in args:
        problems.append("a projected view needs parent (a view id) and direction")
    if kind == "section" and "line" not in args:
        problems.append("a section view needs parent and line [[x1, y1], [x2, y2]]")
    if kind == "detail" and ("center" not in args or "radius" not in args):
        problems.append("a detail view needs parent, center and radius")
    if kind == "base" and "orientation" not in args:
        problems.append("a base view needs orientation")
    if kind == "break" and ("start" not in args or "end" not in args):
        problems.append("a break needs start and end [x, y] (%s)" % VIEW_MM)
    if kind == "breakout" and "boundary" not in args:
        problems.append("a breakout needs boundary: 3 or more points [x, y] around the area")
    if "depth" in args and "through_all" in args:
        problems.append("give depth or through_all, not both")
    if kind not in ("section", "breakout") and ("depth" in args or "depth_mode" in args):
        problems.append("depth / depth_mode are for section and breakout views")
    if kind != "exploded" and "storyboard" in args:
        problems.append("storyboard is for kind exploded")
    if kind not in ("base", "exploded") and ("bodies" in args or "flat_pattern" in args):
        problems.append("bodies / flat_pattern are for a base view")


define(
    "add_drawing_view",
    "Add drawing view",
    "drawing",
    "DRAWING > CREATE > Base / Projected / Section / Detail / Break / Breakout Section / "
    "Exploded View",
    "Add a view. kind base (orientation, scale, style; bodies or flat_pattern, default what "
    "the drawing shows), projected (parent, direction Top, Right... FrontTopRight), section "
    "(parent, line: 2 points cut straight, more bend the cut (half, offset, aligned), side "
    "1 | -1, depth_mode Full | Slice | Distance + depth), detail (parent, center, radius; "
    "scale default 2x the parent's), break (parent, start, end: the part between is left out, "
    "across the longer way of the two points; gap mm), breakout (parent, boundary: 3+ points "
    "round what to open, depth mm from the front, default half way, or through_all) or "
    "exploded (a base view of a storyboard's end, default the front one). Points on a view "
    "are in its own mm (model size from its centre, y up: get_drawing edges). at: where on "
    "the sheet [x, y] mm.",
    schema(
        {
            "drawing": step_id("the drawing or sheet (default: the newest drawing)"),
            "kind": enum(VIEW_KINDS),
            "parent": step_id("the view it is made from"),
            "orientation": enum(ORIENTATIONS),
            "direction": enum(PROJECTED),
            "line": _point_list("section line [[x1, y1], [x2, y2], ...]", 2, 12),
            "side": integer(
                "section: 1 looks from the left of the line's direction, -1 "
                "from the right (default: from where the view is placed)"
            ),
            "center": kit.numbers(2, "detail centre [x, y]"),
            "radius": positive("detail circle radius (mm)"),
            "start": kit.numbers(2, "break: one end of the part left out [x, y]"),
            "end": kit.numbers(2, "break: the other end [x, y]"),
            "gap": positive("break: the gap between the two ends on the sheet (mm)", default=10),
            "boundary": _point_list("breakout: the boundary's corners [[x, y], ...]", 3, 64),
            "depth": positive("breakout: how deep from the front (mm); section: Distance (mm)"),
            "depth_mode": enum(DEPTH_MODES, "section depth", default="Full"),
            "through_all": boolean("breakout: cut through everything"),
            "storyboard": string("exploded: the storyboard (default: the front one)"),
            "bodies": kit.step_ids("base: the bodies it shows (default: the drawing's)"),
            "flat_pattern": step_id("base: a sheet metal body or flat pattern drawn flat"),
            "at": kit.numbers(2, SHEET_MM),
            "scale": positive("0.5 for 1:2"),
            "style": enum(STYLES),
            "label": string("section / detail letter"),
        },
        ["kind"],
    ),
    extra=_extra_drawing_view,
    needs=("drawing",),
    id_base="View",
    title_fn=lambda a: "AI: %s view" % str(a.get("kind", "")).capitalize(),
    examples=[
        example(
            {"kind": "section", "parent": "BaseView", "line": [[-50, 0], [50, 0]]},
            "a section through the middle of the base view",
        ),
        example(
            {"kind": "break", "parent": "BaseView", "start": [-20, 0], "end": [20, 0], "gap": 8},
            "leave out the middle 40 mm of a long part",
        ),
        example(
            {"kind": "breakout", "parent": "BaseView", "boundary": [[-5, -5], [5, -5], [5, 5]]},
            "open up a corner half way through",
        ),
    ],
)


# -- MODIFY ---------------------------------------------------------------------------------------
def _extra_edit_view(args, problems):
    keys = set(args) - {"view"}
    if not keys:
        problems.append("give at least one thing to change (style, scale, label...)")
    if "remove_breakout" in args and "depth" in args:
        problems.append("give depth or remove_breakout, not both")
    if "depth" in args and "through_all" in args:
        problems.append("give depth or through_all, not both")
    marks = args.get("center_marks")
    if isinstance(marks, dict) and not marks:
        problems.append("center_marks needs holes, extrudes and / or cuts")


define(
    "edit_drawing_view",
    "Edit drawing view",
    "drawing",
    "DRAWING > MODIFY > Edit View (or double-click a view)",
    "Change a view as its dialog does: orientation (a base view; its projected views turn "
    "with it), style, tangent_edges, scale (its projected views follow; the title block's "
    "Scale follows the first base view), label (its text) and show_label, center_marks "
    "{holes, extrudes, cuts: true | false} (automated centre marks and lines that follow the "
    "design), storyboard (a base view's Representation: a storyboard's name, or Model for the "
    "design as it is), a section's depth_mode Full | Slice | Distance with depth and hatch, a "
    "broken view's gap, a breakout's depth / through_all or remove_breakout. To move or turn "
    "a view: modify_drawing. One undo step.",
    schema(
        {
            "view": step_id("the view"),
            "orientation": enum(ORIENTATIONS),
            "style": enum(STYLES),
            "tangent_edges": enum(TANGENT_EDGES),
            "scale": positive("0.5 for 1:2"),
            "label": string("the view label's text"),
            "show_label": boolean("show the view label under the view"),
            "center_marks": obj(
                {
                    "holes": boolean(),
                    "extrudes": boolean("round extrudes"),
                    "cuts": boolean("round cuts"),
                },
                description="automated centre marks and centre lines on these rounds",
            ),
            "storyboard": string('a storyboard\'s name, or "Model"'),
            "depth_mode": enum(DEPTH_MODES, "a section's depth"),
            "depth": positive("section Distance / breakout depth (mm)"),
            "through_all": boolean("a breakout through everything"),
            "hatch": boolean("a section's hatching"),
            "gap": positive("a broken view's gap (mm on the sheet)"),
            "remove_breakout": boolean("take the breakout away"),
        },
        ["view"],
    ),
    extra=_extra_edit_view,
    needs=("drawing",),
    own_id=False,
    title_fn=lambda a: "AI: Edit %s" % a.get("view", "view"),
    examples=[
        example(
            {"view": "BaseView", "scale": 0.5, "center_marks": {"holes": True}},
            "1:2 with a centre mark on every hole",
        )
    ],
)


def _extra_modify(args, problems):
    kind = args.get("kind")
    if kind == "move" and ("by" in args) == ("to" in args):
        problems.append("move needs by [dx, dy] or to [x, y] (one of them)")
    if kind == "move" and "to" in args and len(args.get("items") or []) != 1:
        problems.append("to moves one item; give by to move several")
    if kind == "rotate" and "angle" not in args:
        problems.append("rotate needs angle (degrees, counter-clockwise)")
    if kind != "move" and ("by" in args or "to" in args):
        problems.append("by / to are for move")
    if kind != "rotate" and "angle" in args:
        problems.append("angle is for rotate")


define(
    "modify_drawing",
    "Move, rotate or delete on a drawing",
    "drawing",
    "DRAWING > MODIFY > Move / Rotate / Delete (and Delete of a drawing in the browser)",
    "kind move: items (views, the parts list or bend table, text notes, balloons, symbols "
    "and dimensions' text) by [dx, dy] mm on the sheet, or one item to [x, y]; a view takes "
    "its dimensions, marks and balloons along, a projected view slides along its line from "
    "its parent. kind rotate: views by angle degrees, counter-clockwise about their middle. "
    "kind delete: the items (a view takes its dimensions, balloons, sections, details and "
    "projected views with it; a broken view brings back the view it stood in for; a "
    "drawing's id deletes the whole drawing, every sheet). Ids from get_drawing. One undo "
    "step.",
    schema(
        {
            "kind": enum(["move", "rotate", "delete"]),
            "items": kit.step_ids("ids of what to change (get_drawing lists them)"),
            "by": kit.numbers(2, "move: [dx, dy] mm on the sheet"),
            "to": kit.numbers(2, "move: %s (one item)" % SHEET_MM),
            "angle": number("rotate: degrees, counter-clockwise"),
        },
        ["kind", "items"],
    ),
    extra=_extra_modify,
    needs=("drawing",),
    own_id=False,
    destructive=True,
    title_fn=lambda a: "AI: Drawing %s" % a.get("kind", "change"),
    examples=[
        example({"kind": "move", "items": ["BaseView"], "by": [-20, 0]}, "a view 20 mm left"),
        example({"kind": "rotate", "items": ["ProjectedView"], "angle": 90}, "a view turned"),
    ],
)


def _extra_title(args, problems):
    values = args.get("values")
    if isinstance(values, dict):
        if not values:
            problems.append("values needs at least one field")
        for key, value in values.items():
            if key not in TITLE_KEYS:
                problems.append(
                    "values.%s is no title block field (%s)" % (key, ", ".join(TITLE_KEYS))
                )
            elif not isinstance(value, str):
                problems.append("values.%s must be text" % key)


define(
    "edit_title_block",
    "Edit title block",
    "drawing",
    "DRAWING > MODIFY > Title Block (or double-click the title block)",
    "Type into the title block: values {field: text} with the fields Title, PartNumber, "
    "Description, Material, DrawnBy, Date, CheckedBy, ApprovedBy, Scale, Size, Sheet, Units, "
    "Revision. Fission 180 fills Title, PartNumber, Material, Scale, Size, Sheet and Units from "
    "the design until a field is typed: a typed field keeps its text on every sheet of the "
    "drawing. A sheet made with title_block false has none (refused).",
    schema(
        {
            "drawing": step_id("the drawing or one of its sheets (default: the newest)"),
            "values": kit.free_object('{field: text}, e.g. {"Description": "Bracket"}'),
        },
        ["values"],
    ),
    extra=_extra_title,
    needs=("drawing",),
    own_id=False,
    title_fn=lambda a: "AI: Title block",
    examples=[
        example(
            {"values": {"Description": "Mounting bracket", "Revision": "B", "CheckedBy": "LS"}},
            "describe the part and its revision",
        )
    ],
)


def _extra_sheet(args, problems):
    action = args.get("action")
    if action == "rename" and not str(args.get("name", "")).strip():
        problems.append("rename needs name")
    if action == "move" and "index" not in args:
        problems.append("move needs index (0 = the first place)")
    if action in ("rename", "move", "delete") and "drawing" not in args:
        problems.append("%s needs drawing: the sheet's id (get_drawing lists the sheets)" % action)


define(
    "drawing_sheet",
    "Drawing sheet",
    "drawing",
    "DRAWING > the Sheet Bar (+, right-click a sheet: New Sheet, Rename, Delete, Move)",
    "A drawing's sheets: action add (a new empty sheet with the same size, standard and "
    "title block: at the end, or at index; it numbers its title block 2 / 2...), rename "
    "(name), move (to index, 0 = first) or delete (the sheet and everything on it; the last "
    "sheet of a drawing stays: delete the drawing with modify_drawing). Each sheet has its "
    "own id: give it as drawing to add_drawing_view and the other tools to work on it. "
    "Answers the sheets in order.",
    schema(
        {
            "action": enum(["add", "rename", "move", "delete"]),
            "drawing": step_id("the drawing (add) or the sheet (rename, move, delete)"),
            "name": string("rename: the sheet's new name"),
            "index": integer("add / move: its place, 0 = first", minimum=0),
        },
        ["action"],
    ),
    extra=_extra_sheet,
    needs=("drawing",),
    title_fn=lambda a: "AI: %s sheet" % str(a.get("action", "")).capitalize(),
    id_base="Sheet",
    examples=[example({"action": "add"}, "a second sheet for the details")],
)


# -- DIMENSIONS -----------------------------------------------------------------------------------
def _extra_dimension(args, problems):
    kind = args.get("type")
    picks = args.get("picks") or []
    if kind in ("ordinate", "baseline", "chain"):
        if not picks:
            problems.append("%s needs picks: the points to dimension" % kind)
    elif not 1 <= len(picks) <= 2:
        problems.append("picks takes one or two elements of the view")
    if kind == "arc_length" and len(picks) != 1:
        problems.append("arc_length takes one pick: the arc")
    if kind == "ordinate" and "origin" not in args:
        problems.append("ordinate needs origin: the point whose value is 0")
    if kind in ("baseline", "chain") and "from" not in args:
        problems.append("%s needs from: a horizontal or vertical dimension's id" % kind)
    if kind not in ("baseline", "chain") and "from" in args:
        problems.append("from is for baseline and chain")
    if kind != "ordinate" and ("origin" in args or "axis" in args):
        problems.append("origin and axis are for ordinate")
    if kind in ("baseline", "chain") and "view" in args:
        pass  # (the view is the dimension's own; checked when it runs)
    if kind not in ("baseline", "chain") and "view" not in args:
        problems.append("view is needed (the view the picks are on)")
    for i, item in enumerate(picks):
        _check_element(item, "picks[%d]" % i, problems)
    if "origin" in args:
        _check_element(args["origin"], "origin", problems)


define(
    "add_drawing_dimension",
    "Add drawing dimension",
    "drawing",
    "DRAWING > DIMENSIONS > Dimension, Linear, Aligned, Angular, Radius, Diameter, Arc "
    "Length, Ordinate, Baseline, Chain",
    "Dimension a drawing view. Without type, as Fusion's Dimension command infers it from "
    "picks: one line (its length), one circle (diameter) or arc (radius), two lines / points "
    "(distance or angle). type forces linear, aligned, radius, diameter, angular, or: "
    "arc_length (picks: one arc); ordinate (origin: the 0 point, picks: the points, axis x | "
    "y | both, at: [x, y] sheet mm the values' lines go through); baseline / chain (from: a "
    "horizontal or vertical dimension's id, picks: more points; baseline measures each from "
    "that dimension's start, stacked 8 mm apart, chain each from the one before). A pick is "
    "{kind: line | circle | arc | vertex, near: [x, y] in the view's own mm (get_drawing "
    "edges), radius}; a circle given as a point is its centre. at: the text on the sheet. "
    "Isometric views cannot be dimensioned. Answers each value.",
    schema(
        {
            "view": step_id("the view"),
            "picks": array(
                _element(),
                "the elements (one or two; more for ordinate, " "baseline, chain)",
                1,
                40,
            ),
            "type": enum(DIMENSION_TYPES),
            "origin": _element("ordinate: the point the values count from"),
            "axis": enum(["x", "y", "both"], "ordinate: which values", default="both"),
            "from": step_id("baseline / chain: the dimension to go on from"),
            "at": kit.numbers(2, "text position (ordinate: the values' lines) %s" % SHEET_MM),
        },
        ["picks"],
    ),
    extra=_extra_dimension,
    needs=("drawing",),
    id_base="Dimension",
    title_fn=lambda a: "AI: Drawing dimension",
    examples=[
        example(
            {"view": "BaseView", "picks": [{"kind": "circle", "radius": 3}]},
            "the diameter of the 6 mm hole",
        ),
        example(
            {
                "view": "BaseView",
                "type": "ordinate",
                "origin": {"kind": "vertex", "near": [-30, -20]},
                "picks": [{"kind": "circle", "near": [0, 0]}],
                "axis": "x",
            },
            "the hole's x from the bottom left corner",
        ),
    ],
)


def _extra_edit_dimension(args, problems):
    keys = set(args) - {"dimensions"}
    if not keys:
        problems.append("give at least one thing to change (override, tolerance, at...)")
    tol = args.get("tolerance")
    if tol in ("deviation", "limits") and ("upper" not in args or "lower" not in args):
        problems.append("%s tolerance needs upper and lower (mm)" % tol)
    if tol == "symmetric" and "upper" not in args:
        problems.append("symmetric tolerance needs upper (the value after ±)")
    if tol == "fit" and "fit" not in args:
        problems.append('fit tolerance needs fit, like "H7/g6"')
    if "at" in args and len(args.get("dimensions") or []) != 1:
        problems.append("at moves one dimension's text")


define(
    "edit_drawing_dimension",
    "Edit drawing dimension",
    "drawing",
    "DRAWING > DIMENSIONS > Edit Dimension (or double-click a dimension)",
    "Change dimensions' text as the Dimension dialog does: override (text instead of the "
    'value; "" gives the value back), prefix / suffix ("4x ", " THRU"), precision, '
    "tolerance none | symmetric | deviation | limits | fit with upper / lower (mm) or fit "
    '(ISO 286 "H7/g6", or one class "H7"), fit_member hole | shaft, fit_display class | '
    "class_and_tolerances | limits | fit, tol_precision, basic (boxed), reference (in "
    "parentheses); at moves one dimension's text to [x, y] on the sheet. dimensions: ids "
    "(get_drawing). A wrong entry (upper under lower, an unknown class, a fit over 500 mm) is "
    "refused with the reason. Answers the text each now shows.",
    schema(
        {
            "dimensions": kit.step_ids("the dimensions"),
            "override": string("text shown instead of the value"),
            "prefix": string("text before the value"),
            "suffix": string("text after the value"),
            "precision": enum(PRECISIONS),
            "tolerance": enum(TOLERANCES),
            "upper": number("upper tolerance (mm, or degrees on an angle)"),
            "lower": number("lower tolerance"),
            "fit": string('an ISO 286 fit "H7/g6" or one class "H7" / "g6"'),
            "fit_member": enum(["hole", "shaft"], "this dimension is the hole or the shaft"),
            "fit_display": enum(FIT_DISPLAYS),
            "tol_precision": enum(PRECISIONS, "the tolerance's decimals"),
            "basic": boolean("a basic (theoretically exact) dimension: boxed"),
            "reference": boolean("a reference dimension: in parentheses"),
            "at": kit.numbers(2, "the text's place %s" % SHEET_MM),
        },
        ["dimensions"],
    ),
    extra=_extra_edit_dimension,
    needs=("drawing",),
    own_id=False,
    title_fn=lambda a: "AI: Edit dimension",
    examples=[
        example(
            {"dimensions": ["Dimension"], "tolerance": "fit", "fit": "H7/g6"},
            "a fit on the hole's diameter",
        ),
        example(
            {"dimensions": ["Dimension001"], "tolerance": "symmetric", "upper": 0.1},
            "± 0.1",
        ),
    ],
)


# -- TEXT and TABLES ------------------------------------------------------------------------------
def _extra_annotation(args, problems):
    kind = args.get("kind")
    if kind in ("text", "leader") and not args.get("text"):
        problems.append("%s needs text" % kind)
    if kind != "text" and kind is not None and "view" not in args:
        problems.append("%s needs view" % kind)
    if kind == "leader" and "pick" not in args:
        problems.append("leader needs pick: the edge the arrow goes on")
    if kind == "balloon" and "component" not in args:
        problems.append("balloon needs component (a parts-list part number or a body id)")
    if "pick" in args:
        _check_element(args["pick"], "pick", problems)
    if kind != "bend_note" and "bends" in args:
        problems.append("bends is for bend_note")


define(
    "add_drawing_annotation",
    "Add drawing annotation",
    "drawing",
    "DRAWING > TEXT (Text, Leader, Bend Note) and TABLES (Table / Parts List, Bend Table, "
    "Balloon), GEOMETRY > Center Mark on every circle",
    "Add to a drawing: kind text (text lines at [x, y], size mm), leader (view, pick: the "
    "edge its arrow goes on, at: where the text goes, text), bend_note (a flat pattern view: "
    "direction, angle and radius along bends, numbers 1.. as the bend table, default all), "
    "parts_list (a table of the view's components with balloons, at = its top-left corner; "
    "balloons false: none), bend_table (a flat pattern view: its bends, with identifiers on "
    "the view), balloon (view, component: a parts-list part number or body id; its arrow on "
    "an edge of that part, at: the balloon) or center_marks (a centre mark on every circle of "
    "a view that has none). Answers the ids.",
    schema(
        {
            "drawing": step_id("the drawing or sheet (default: the view's, or the newest)"),
            "kind": enum(ANNOTATION_KINDS),
            "text": string("text (new lines split it)"),
            "size": positive("text height (mm)", default=3.5),
            "view": step_id("the view it belongs to"),
            "pick": _element("leader: the edge the arrow goes on"),
            "component": string("balloon: a parts-list part number (component name) or body id"),
            "bends": array(integer(minimum=1), "bend_note: bend numbers (B1 = 1)"),
            "at": kit.numbers(2, SHEET_MM),
            "balloons": boolean("parts list: balloons on the view", default=True),
        },
        ["kind"],
    ),
    extra=_extra_annotation,
    needs=("drawing",),
    id_base="Annotation",
    title_fn=lambda a: "AI: Drawing %s" % str(a.get("kind", "")).replace("_", " "),
    examples=[
        example(
            {"kind": "text", "text": "Break all sharp edges", "at": [20, 40]}, "a note on the sheet"
        ),
        example(
            {
                "kind": "leader",
                "view": "BaseView",
                "pick": {"kind": "line", "near": [0, 5]},
                "at": [60, 60],
                "text": "Polished",
            },
            "a leader note on an edge",
        ),
    ],
)


# -- GEOMETRY -------------------------------------------------------------------------------------
def _extra_geometry(args, problems):
    kind = args.get("kind")
    picks = args.get("picks") or []
    need = {"centerline": 2, "edge_extension": 2}
    if kind in need and len(picks) != 2:
        problems.append("%s takes two picks: straight edges" % kind)
    if kind == "center_mark_pattern" and len(picks) < 2:
        problems.append("center_mark_pattern needs two or more picks: holes of one pattern")
    for i, item in enumerate(picks):
        _check_element(item, "picks[%d]" % i, problems)


define(
    "add_drawing_geometry",
    "Add drawing geometry",
    "drawing",
    "DRAWING > GEOMETRY > Center Mark, Centerline, Center Mark Pattern, Edge Extension",
    "Construction lines on a view, as GEOMETRY's commands make them: center_mark (picks: "
    "circles / arcs; none: every circle without a mark), centerline (two parallel straight "
    "edges: a dash-dot line midway), center_mark_pattern (2+ holes of one pattern: a mark on "
    "each and the line or bolt circle through their centres) or edge_extension (two straight "
    "edges: thin lines to where they would meet, a point there that takes dimensions: a "
    "rounded corner's sharp corner). A pick is {kind: line | circle | arc, near: [x, y] in "
    "the view's own mm (get_drawing edges), radius}. They follow the design.",
    schema(
        {
            "kind": enum(GEOMETRY_KINDS),
            "view": step_id("the view"),
            "picks": array(_element(), "the edges or circles", 1, 60),
        },
        ["kind", "view"],
    ),
    extra=_extra_geometry,
    needs=("drawing",),
    own_id=False,
    title_fn=lambda a: "AI: Drawing %s" % str(a.get("kind", "")).replace("_", " "),
    examples=[
        example(
            {
                "kind": "centerline",
                "view": "BaseView",
                "picks": [{"kind": "line", "near": [-30, 0]}, {"kind": "line", "near": [30, 0]}],
            },
            "a centre line between the two sides",
        )
    ],
)


# -- SYMBOLS --------------------------------------------------------------------------------------
def _extra_symbol(args, problems):
    kind = args.get("kind")
    if kind != "feature_control_frame" and ("view" not in args or "pick" not in args):
        problems.append("%s needs view and pick: the edge it stands on" % kind)
    if ("view" in args) != ("pick" in args):
        problems.append("give view and pick together (or neither, for a frame alone)")
    if "pick" in args:
        _check_element(args["pick"], "pick", problems)
    if "at" not in args:
        problems.append("at is needed: %s" % SHEET_MM)
    fields = {
        "surface_texture": ("texture", "value", "lay", "all_around"),
        "feature_control_frame": (
            "characteristic",
            "tolerance",
            "diameter_zone",
            "material",
            "datums",
            "second_row",
        ),
        "datum_identifier": ("letter",),
    }
    for other, keys in fields.items():
        if other != kind:
            for key in keys:
                if key in args and key not in fields.get(kind, ()):
                    problems.append("%s is for %s" % (key, other))
    letter = args.get("letter")
    if isinstance(letter, str) and not letter.strip().isalpha():
        problems.append("a datum letter is letters (A, B, C...)")


ROW = obj(
    {
        "tolerance": positive("the row's tolerance (mm)"),
        "diameter_zone": boolean("a round zone (⌀)"),
        "material": enum(MATERIAL, "M maximum / L least material condition"),
        "datums": array(string(), 'datum letters, e.g. ["A", "B"]', 0, 3),
    },
    ["tolerance"],
    "a composite frame's second row",
)
define(
    "add_drawing_symbol",
    "Add drawing symbol",
    "drawing",
    "DRAWING > SYMBOLS > Surface Texture, Feature Control Frame, Datum Identifier",
    "A symbol on a view's edge (pick: {kind, near} in the view's own mm), placed at [x, y] on "
    "the sheet (on the edge, or away with a leader): surface_texture (texture basic | "
    'removal | no_removal, value "Ra 3.2", lay, all_around), feature_control_frame (GD&T: '
    "characteristic position, flatness, perpendicularity..., tolerance mm, diameter_zone, "
    'material M | L, datums ["A", "B"], second_row for a composite frame; without view and '
    "pick it stands alone) or datum_identifier (letter, default the next free one). One undo "
    "step each.",
    schema(
        {
            "kind": enum(SYMBOL_KINDS),
            "view": step_id("the view"),
            "pick": _element("the edge it stands on"),
            "at": kit.numbers(2, SHEET_MM),
            "texture": enum(TEXTURES, "the symbol", default="removal"),
            "value": string('roughness, e.g. "Ra 3.2"'),
            "lay": enum(LAYS, "lay direction symbol"),
            "all_around": boolean(),
            "characteristic": enum(CHARACTERISTICS, default="position"),
            "tolerance": positive("the zone (mm)", default=0.1),
            "diameter_zone": boolean("a round zone (⌀)"),
            "material": enum(MATERIAL, "M maximum / L least material condition"),
            "datums": array(string(), 'datum letters, e.g. ["A", "B"]', 0, 3),
            "second_row": ROW,
            "letter": string("the datum's letter"),
        },
        ["kind"],
    ),
    extra=_extra_symbol,
    needs=("drawing",),
    id_base="Symbol",
    title_fn=lambda a: "AI: Drawing %s" % str(a.get("kind", "")).replace("_", " "),
    examples=[
        example(
            {
                "kind": "datum_identifier",
                "view": "BaseView",
                "pick": {"kind": "line", "near": [0, -5]},
                "at": [120, 120],
            },
            "datum A on the bottom edge",
        ),
        example(
            {
                "kind": "feature_control_frame",
                "characteristic": "flatness",
                "tolerance": 0.05,
                "at": [80, 60],
            },
            "a flatness frame on its own",
        ),
    ],
)


# -- TABLES: balloons -----------------------------------------------------------------------------
def _extra_balloons(args, problems):
    kind = args.get("kind")
    if kind == "renumber" and ("balloon" not in args or "to" not in args):
        problems.append("renumber needs balloon (its id or number) and to (the new number)")
    if kind == "align" and (len(args.get("balloons") or []) < 2 or "at" not in args):
        problems.append("align needs balloons (two or more) and at [x, y]")


define(
    "edit_balloons",
    "Edit balloons",
    "drawing",
    "DRAWING > TABLES > Renumber, Align Balloons",
    "kind renumber: the balloon (its id or the number it shows) gets item number to; the row "
    "that had it takes the old one, the parts list sorts and every balloon of both rows "
    "shows its new number. kind align: balloons (ids or numbers) line up through at [x, y] "
    "on the sheet: on one level line when they spread more sideways than up, else on one "
    "upright line. One undo step.",
    schema(
        {
            "kind": enum(["renumber", "align"]),
            "drawing": step_id("the drawing or sheet (default: the newest)"),
            "balloon": string("renumber: the balloon's id or number"),
            "to": integer("renumber: the new item number", minimum=1),
            "balloons": array(string(), "align: the balloons' ids or numbers"),
            "at": kit.numbers(2, "align: where their line goes %s" % SHEET_MM),
        },
        ["kind"],
    ),
    extra=_extra_balloons,
    needs=("drawing",),
    own_id=False,
    title_fn=lambda a: "AI: %s balloons" % ("Align" if a.get("kind") == "align" else "Renumber"),
    examples=[
        example({"kind": "renumber", "balloon": "2", "to": 1}, "balloon 2 becomes item 1"),
        example(
            {"kind": "align", "balloons": ["1", "2", "3"], "at": [60, 250]},
            "the balloons on one line",
        ),
    ],
)


# -- reading and EXPORT ---------------------------------------------------------------------------
define(
    "get_drawing",
    "Get drawing",
    "drawing",
    "BROWSER > Drawings (and what the sheets show)",
    "Describe drawings so you can check your work without a picture: each drawing's sheets "
    "(size, standard, units, title block) and on each: views (id, kind, orientation, scale, "
    "place and size on the sheet, label, style, what they show: bodies, flat pattern, "
    "storyboard; section line and depth, break, breakout, rotation), dimensions (type, value, "
    "the text written, what they measure), annotations (leaders, symbols, ordinates: kind "
    "and text), balloons (number, component), tables (rows), centre marks, centre lines. "
    "edges true: each view's lines, circles and points (view's own mm) for picks. picture "
    "true: a PNG of one sheet (frame, title block, views, dimensions, text) drawn from its "
    "DXF.",
    schema(
        {
            "drawing": step_id("one drawing or sheet (default: all)"),
            "edges": boolean("list each view's lines and circles", default=False),
            "picture": boolean("a PNG of the sheet (the drawing's first, or the given sheet)"),
            "width": integer("picture width in pixels", default=1200, minimum=200, maximum=4000),
        }
    ),
    changes=False,
    needs=("drawing",),
    examples=[
        example({"edges": True}, "views and their lines and circles"),
        example({"picture": True, "width": 800}, "a picture of the sheet"),
    ],
)


def _extra_export_drawing(args, problems):
    path, fmt = str(args.get("path", "")), args.get("format")
    if fmt and not path.lower().endswith("." + fmt):
        problems.append("path must end in .%s for format %s" % (fmt, fmt))
    if fmt != "csv" and "table" in args:
        problems.append("table is for format csv")


define(
    "export_drawing",
    "Export drawing",
    "drawing",
    "DRAWING > EXPORT > Export PDF / DXF / DWG / CSV",
    "Export a drawing: pdf (sheets all: every sheet in one PDF, or current: the given sheet; "
    "needs the Fission 180 window), dxf (the sheet: frame, views on their own layers, "
    'dimensions, text; sheets all: one file per sheet, "name - Sheet 2.dxf"), dwg (each '
    "sheet's DXF turned into DWG by a converter on this computer: LibreDWG, the ODA File "
    "Converter or QCAD; without one it is refused: export dxf) or csv (a table as a "
    "spreadsheet file: table its id, default the parts list, else the bend table). Replacing "
    "a file must be confirmed by the person. The answer lists what the file does not keep "
    '("Not kept in this file:"), as the drawing\'s Export message does.',
    schema(
        {
            "drawing": step_id("the drawing or sheet (default: the newest drawing)"),
            "format": enum(["pdf", "dxf", "dwg", "csv"]),
            "path": string("full path"),
            "sheets": enum(["all", "current"], "pdf: all; dxf / dwg: current (the given sheet)"),
            "table": step_id("csv: the table (default: the parts list)"),
        },
        ["format", "path"],
    ),
    changes=False,
    writes_files=True,
    confirm_overwrite=True,
    extra=_extra_export_drawing,
    needs=("drawing",),
    examples=[
        example({"format": "pdf", "path": "/home/me/bracket.pdf"}, "a PDF of the drawing"),
        example(
            {"format": "csv", "path": "/home/me/parts.csv"}, "the parts list for a spreadsheet"
        ),
    ],
)
