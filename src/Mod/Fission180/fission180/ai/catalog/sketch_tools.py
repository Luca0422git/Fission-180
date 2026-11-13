# SPDX-License-Identifier: LGPL-2.1-or-later
"""AI tools for the SKETCH tab: sketches of open curves, adding to and reading an existing
sketch, constraints and dimensions (with Fusion's names: Collinear, Concentric, Midpoint...),
Polygon, Trim, Text. Pure Python (the work is in fission180/ai/actions/sketch_actions.py and
the design steps of fission180/ai/ops/sketch_ops.py)."""

from . import kit
from .core_tools import GEOMETRY_ITEM, check_geometry
from .kit import UNITS, array, boolean, enum, integer, number, obj, point2, positive, schema
from .kit import string
from .registry import define, example

_CURVE_ITEM = obj(
    {
        "line": kit.numbers(4, "[x1, y1, x2, y2]"),
        "arc": kit.numbers(5, "[cx, cy, r, a0, a1]: counter-clockwise from a0 to a1 degrees"),
        "circle": kit.numbers(3, "[cx, cy, r]"),
        "point": kit.numbers(2, "[x, y]: a sketch point"),
        "polyline": array(kit.numbers(2), "[[x, y], ...] an open chain of lines", 2),
    },
    description="exactly one of line, arc, circle, point, polyline",
)
CURVE_KINDS = ("line", "arc", "circle", "point", "polyline")


def _check_curves(items, problems, path="curves"):
    for i, item in enumerate(items if isinstance(items, list) else []):
        if isinstance(item, dict) and len([k for k in CURVE_KINDS if k in item]) != 1:
            problems.append(
                "%s[%d] must have exactly one of %s" % (path, i, ", ".join(CURVE_KINDS))
            )
        elif isinstance(item, dict) and "arc" in item:
            arc = item["arc"]
            if kit.is_type(arc[2], "number") and arc[2] <= 0:
                problems.append("%s[%d].arc radius must be above 0" % (path, i))


def _extra_curve_sketch(args, problems):
    _check_curves(args.get("curves"), problems)


define(
    "create_curve_sketch",
    "Create sketch of curves",
    "sketch",
    "SOLID > CREATE > Create Sketch (lines, arcs, points)",
    "Create a sketch of open curves and points: the paths, rails, guide curves and rib / web "
    "curves that sweep, loft, pipe, rib, web, pattern_on_path and split_body use, and points "
    "for holes and lofts. Arcs run counter-clockwise from a0 to a1 (degrees); a polyline "
    "stays open. Closed shapes (areas) are made with create_sketch. "
    + kit.SKETCH_HELP
    + " "
    + UNITS,
    schema(
        {
            "plane": enum(["XY", "XZ", "YZ"]),
            "offset": number("mm along the plane's normal", default=0),
            "curves": array(_CURVE_ITEM, "the curves and points", 1),
        },
        ["plane", "curves"],
    ),
    op="sf_curves",
    extra=_extra_curve_sketch,
    needs=(),
    id_base="Sketch",
    title_fn=lambda a: "AI: Sketch of curves on %s" % a.get("plane", ""),
    examples=[
        example(
            {"plane": "XZ", "curves": [{"line": [0, 0, 0, 40]}, {"arc": [20, 40, 20, 90, 180]}]},
            "a sweep path: a straight line up, then a quarter arc",
        ),
        example(
            {"plane": "XY", "curves": [{"point": [10, 10]}, {"point": [30, 10]}]},
            "two sketch points (hole centres)",
        ),
    ],
)


def _extra_add_to_sketch(args, problems):
    if not args.get("geometry") and not args.get("curves"):
        problems.append("give geometry (closed shapes) and / or curves (open curves, points)")
    check_geometry(args.get("geometry"), problems)
    _check_curves(args.get("curves"), problems)


define(
    "add_to_sketch",
    "Add to sketch",
    "sketch",
    "SKETCH > CREATE (Line, Rectangle, Circle, Arc, Polygon, Slot, Spline, Point)",
    "Draw more in an existing sketch (Fusion: edit the sketch and draw): closed shapes "
    "(geometry, the same items as create_sketch, with their named dimensions) and open curves "
    "or points (curves, the same items as create_curve_sketch). construction: true draws "
    "construction geometry (dashed, it makes no area: guides for constraints and axes). "
    "Coordinates are the sketch's own x / y (see get_sketch). Everything built from the "
    "sketch updates. " + kit.GEOMETRY_HELP + " " + UNITS,
    schema(
        {
            "sketch": kit.step_id("the sketch to draw in"),
            "geometry": array(GEOMETRY_ITEM, "closed shapes", 1),
            "curves": array(_CURVE_ITEM, "open curves and points", 1),
            "construction": boolean("construction geometry", default=False),
        },
        ["sketch"],
    ),
    extra=_extra_add_to_sketch,
    own_id=False,
    title_fn=lambda a: "AI: Draw in %s" % a.get("sketch", "sketch"),
    examples=[
        example(
            {"sketch": "Sketch1", "geometry": [{"circle": [20, 10, 4], "name": "bore"}]},
            "a circle (bore.diameter) added to Sketch1",
        ),
        example(
            {"sketch": "Sketch1", "curves": [{"line": [0, -5, 0, 25]}], "construction": True},
            "a construction line (for example a revolve axis)",
        ),
    ],
)

define(
    "get_sketch",
    "Get sketch",
    "sketch",
    "BROWSER > Sketches (and the Sketch Palette)",
    "Read a sketch: its plane and placement, every curve by index (type, points, radius, "
    "construction or not), every constraint by index (type, name, the curves it ties, its "
    "value for dimensions, driving or not), how many degrees of freedom are left (0: fully "
    "constrained, Fusion's padlock), the constraints that conflict or are redundant, and its "
    "closed areas (with a point inside each, for regions). Use the indexes in "
    "sketch_constraint, sketch_dimension, set_sketch_dimension and sketch_delete.",
    schema({"sketch": kit.step_id("the sketch to read")}, ["sketch"]),
    changes=False,
    examples=[example({"sketch": "Sketch1"}, "curves, constraints and areas of Sketch1")],
)

CONSTRAINTS = (
    "coincident",
    "horizontal",
    "vertical",
    "parallel",
    "perpendicular",
    "tangent",
    "equal",
    "symmetric",
    "concentric",
    "collinear",
    "midpoint",
    "fix",
    "point_on",
    "smooth",
    "curvature",  # (wave 8) Fusion's Curvature: the SKETCH tab's own G2 join
    "unfix",  # (wave 8) Fix/Unfix on something fixed
)
_POINT_REF = obj(
    {
        "curve": integer(
            "the curve's index (get_sketch); -1 the sketch's x axis, -2 its y "
            "axis; the origin is curve -1 point start",
            minimum=-2,
        ),
        "point": enum(
            ["start", "end", "center", "whole"],
            "which point of it (whole: the " "curve itself)",
            default="whole",
        ),
    },
    ["curve"],
    "a curve, or one of its points",
)


def _extra_constraint(args, problems):
    kind = args.get("kind")
    items = args.get("items") or []
    need = {
        "horizontal": (1, 2),
        "vertical": (1, 2),
        "fix": (1, 1),
        "unfix": (1, 1),
        "symmetric": (3, 3),
        "midpoint": (2, 2),
    }.get(kind, (2, 2))
    if not need[0] <= len(items) <= need[1]:
        if need[0] == need[1]:
            problems.append("%s takes %d item(s)" % (kind, need[0]))
        else:
            problems.append("%s takes %d or %d items" % (kind, need[0], need[1]))


define(
    "sketch_constraint",
    "Sketch constraint",
    "sketch",
    "SKETCH > CONSTRAINTS",
    "Add a geometric constraint to a sketch, as Fusion's Constraints panel: coincident (two "
    "points, or a point on a curve), horizontal / vertical (a line, or two points), parallel, "
    "perpendicular, tangent, equal, collinear (two lines), concentric (two circles or arcs), "
    "midpoint (a point and a line or arc), symmetric (two points or curves and the line they "
    "mirror about, third), fix / unfix (lock or free a curve or point), point_on (a point "
    "on a curve), curvature (Fusion's Curvature: a spline and a line join with matching "
    "curvature, G2; with an arc or spline G1 and the answer says so; smooth: plain tangent). "
    "items are curves by index (get_sketch) with the point that matters. A constraint that "
    "conflicts with the sketch is not added: the answer names the constraints it fights with.",
    schema(
        {
            "sketch": kit.step_id("the sketch"),
            "kind": enum(CONSTRAINTS),
            "items": array(_POINT_REF, "the curves / points it ties, in order", 1, 3),
        },
        ["sketch", "kind", "items"],
    ),
    extra=_extra_constraint,
    own_id=False,
    title_fn=lambda a: "AI: %s constraint" % str(a.get("kind", "")).capitalize(),
    examples=[
        example(
            {"sketch": "Sketch1", "kind": "horizontal", "items": [{"curve": 0}]},
            "make line 0 horizontal",
        ),
        example(
            {
                "sketch": "Sketch1",
                "kind": "coincident",
                "items": [{"curve": 4, "point": "center"}, {"curve": -1, "point": "start"}],
            },
            "put circle 4's centre on the sketch origin",
        ),
    ],
)

DIMENSIONS = ("distance", "distance_x", "distance_y", "radius", "diameter", "angle")


def _extra_dimension(args, problems):
    kind = args.get("kind")
    items = args.get("items") or []
    if kind in ("radius", "diameter") and len(items) != 1:
        problems.append("%s takes one circle or arc" % kind)
    if kind == "angle" and len(items) not in (1, 2):
        problems.append("angle takes one line (to the sketch x axis) or two lines")
    if ("value" in args) == ("expression" in args):
        problems.append("give value (a number) or expression (a formula), one of them")
    name = args.get("name")
    if isinstance(name, str) and not kit.NAME.match(name.replace(".", "_")):
        problems.append("name may only use letters, digits, _ and .")


define(
    "sketch_dimension",
    "Sketch dimension",
    "sketch",
    "SKETCH > CREATE > Sketch Dimension (D)",
    "Add a driving dimension to a sketch, like Fusion's Sketch Dimension: distance (between "
    "two points, a point and a line, or one line's length), distance_x / distance_y "
    "(horizontal / vertical), radius, diameter, angle (between two lines, or of one line to "
    "the x axis). value in mm or degrees, or expression: a formula with parameters "
    '("width / 2"). name names it for set_sketch_dimension and expressions. A dimension '
    "that over-constrains the sketch is refused with the constraints it conflicts with.",
    schema(
        {
            "sketch": kit.step_id("the sketch"),
            "kind": enum(DIMENSIONS),
            "items": array(_POINT_REF, "the curves / points measured", 1, 2),
            "value": number("mm (lengths) or degrees (angles)"),
            "expression": string("a formula instead of value, e.g. width / 2"),
            "name": string("a name, e.g. slot.width"),
        },
        ["sketch", "kind", "items"],
    ),
    extra=_extra_dimension,
    own_id=False,
    title_fn=lambda a: "AI: %s dimension" % str(a.get("kind", "")).replace("_", " ").capitalize(),
    examples=[
        example(
            {
                "sketch": "Sketch1",
                "kind": "diameter",
                "items": [{"curve": 4}],
                "value": 8,
                "name": "bore.diameter",
            },
            "circle 4 is 8 mm across",
        ),
        example(
            {
                "sketch": "Sketch1",
                "kind": "distance_x",
                "items": [{"curve": -1, "point": "start"}, {"curve": 4, "point": "center"}],
                "expression": "width / 2",
            },
            "the circle's centre at half the width",
        ),
    ],
)


def _extra_set_dimension(args, problems):
    if ("constraint" in args) == ("index" in args):
        problems.append("give constraint (its name) or index, one of them")
    if ("value" in args) == ("expression" in args):
        problems.append("give value (a number) or expression (a formula), one of them")


define(
    "set_sketch_dimension",
    "Set sketch dimension",
    "sketch",
    "SKETCH > double-click a dimension (or MODIFY > Change Parameters, Model Parameters)",
    "Change a sketch dimension: by its name (rectangles made by create_sketch with a name "
    "have <name>.width, <name>.height, <name>.x, <name>.y; circles <name>.diameter, "
    "<name>.x, <name>.y) or by its index (get_sketch). value in mm / degrees, or expression "
    "(a formula with parameters; an empty expression removes the formula). Everything built "
    "from the sketch updates; steps that break are named in the answer.",
    schema(
        {
            "sketch": kit.step_id("the sketch"),
            "constraint": string("the dimension's name, e.g. base.width"),
            "index": integer("the constraint's index (get_sketch)", minimum=0),
            "value": number("mm or degrees"),
            "expression": string("a formula, e.g. width * 2"),
        },
        ["sketch"],
    ),
    ops=["edit"],
    extra=_extra_set_dimension,
    own_id=False,
    title_fn=lambda a: "AI: %s = %s"
    % (a.get("constraint", "dimension"), a.get("value", a.get("expression", ""))),
    examples=[
        example(
            {"sketch": "Sketch1", "constraint": "base.width", "value": 60},
            "make the rectangle 60 mm wide",
        ),
    ],
)


def _extra_sketch_delete(args, problems):
    if not args.get("curves") and not args.get("constraints"):
        problems.append("give curves and / or constraints (indexes from get_sketch)")


define(
    "sketch_delete",
    "Delete in sketch",
    "sketch",
    "SKETCH > select > Delete",
    "Delete curves and / or constraints of a sketch by their indexes (get_sketch). Deleting "
    "a curve deletes the constraints on it too. Indexes after the deleted ones move down: "
    "call get_sketch again before the next edit.",
    schema(
        {
            "sketch": kit.step_id("the sketch"),
            "curves": array(integer(minimum=0), "curve indexes", 1),
            "constraints": array(integer(minimum=0), "constraint indexes", 1),
        },
        ["sketch"],
    ),
    extra=_extra_sketch_delete,
    own_id=False,
    destructive=True,
    examples=[example({"sketch": "Sketch1", "curves": [3]}, "delete curve 3")],
)

define(
    "sketch_polygon",
    "Polygon",
    "sketch",
    "SKETCH > CREATE > Polygon > Circumscribed / Inscribed Polygon",
    "Add a regular polygon to a sketch, Fusion's way: center and point, where point is the "
    "middle of an edge (circumscribed, default) or a corner (inscribed). diameter dimensions "
    "it (across flats when circumscribed, across corners when inscribed), named "
    "<name>.diameter. " + UNITS,
    schema(
        {
            "sketch": kit.step_id("the sketch"),
            "center": point2(),
            "point": point2("the middle of an edge (circumscribed) or a corner (inscribed)"),
            "sides": integer("number of sides", minimum=3),
            "circumscribed": boolean("point is the middle of an edge", default=True),
            "diameter": positive("across flats / corners, mm"),
            "name": string("names its dimension <name>.diameter"),
        },
        ["sketch", "center", "point", "sides"],
    ),
    op="sketch_polygon",
    own_id=False,
    title_fn=lambda a: "AI: Polygon",
    examples=[
        example(
            {
                "sketch": "Sketch1",
                "center": [0, 0],
                "point": [5, 0],
                "sides": 6,
                "diameter": 10,
                "name": "nut",
            },
            "a hexagon 10 mm across flats",
        )
    ],
)
define(
    "sketch_trim",
    "Trim",
    "sketch",
    "SKETCH > MODIFY > Trim (T)",
    "Trim sketch curves, as clicking Trim at each point in turn: the curve nearest the point "
    "loses the piece between its neighbouring intersections. Points are [x, y] in the sketch's "
    "coordinates, on the piece to remove.",
    schema(
        {
            "sketch": kit.step_id("the sketch"),
            "points": array(point2(), "one Trim click each", 1),
        },
        ["sketch", "points"],
    ),
    op="sketch_trim",
    own_id=False,
    title_fn=lambda a: "AI: Trim",
    examples=[
        example(
            {"sketch": "Sketch1", "points": [[20, 0]]}, "remove the piece of curve through (20, 0)"
        )
    ],
)


def _extra_text(args, problems):
    if not str(args.get("text", "")).strip():
        problems.append("text must not be empty")


define(
    "sketch_text",
    "Text",
    "sketch",
    "SKETCH > CREATE > Text",
    "Write text in a sketch (Fusion's sketch Text): its letters become areas you can "
    "extrude (profile: the text's id) or emboss. corner is the frame's top-left corner in "
    "sketch coordinates, height the letter height (mm); font a font family installed on the "
    "computer (default: Fission 180's), bold, italic, angle (degrees), h_align left | center | "
    "right, v_align top | middle | bottom, width / frame_height: the text frame (0: fits the "
    "text), spacing (extra letter spacing).",
    schema(
        {
            "sketch": kit.step_id("the sketch to write in"),
            "text": string("the text"),
            "height": positive("letter height (mm)", default=5),
            "corner": point2("the frame's top-left corner [x, y]"),
            "font": string("a font family"),
            "bold": boolean(default=False),
            "italic": boolean(default=False),
            "angle": number("degrees", default=0),
            "h_align": enum(["left", "center", "right"], default="left"),
            "v_align": enum(["top", "middle", "bottom"], default="top"),
            "width": number("frame width (mm, 0: fits the text)", minimum=0),
            "frame_height": number("frame height (mm, 0: fits the text)", minimum=0),
            "spacing": number("extra letter spacing"),
        },
        ["sketch", "text"],
    ),
    extra=_extra_text,
    id_base="Text",
    title_fn=lambda a: "AI: Text %r" % a.get("text", ""),
    examples=[
        example(
            {"sketch": "Sketch2", "text": "Fission180", "height": 6, "corner": [2, 18]},
            "a 6 mm high text; extrude it with profile = the text's id",
        )
    ],
)


# -- wave 8 (ai-design): the rest of the SKETCH tab ------------------------------------------------
DRAW_POINTS = {  # kind -> (fewest points, most points, what they are)
    "midpoint_line": (2, 2, "[middle, end]"),
    "rectangle_3point": (3, 3, "[corner, corner, a point on the far side]"),
    "circle_2point": (2, 2, "[a, b]: the ends of a diameter"),
    "circle_3point": (3, 3, "three points on it"),
    "circle_2tangent": (1, 1, "[a point on the side it goes] with lines (2)"),
    "circle_3tangent": (1, 1, "[a point near the circle wanted] with lines (3)"),
    "arc_3point": (3, 3, "[start, a point on it, end]"),
    "tangent_arc": (1, 1, "[its end] with from (the curve end it leaves)"),
    "edge_polygon": (3, 3, "[edge start, edge end, a point on its side] with sides"),
    "slot_center_to_center": (2, 2, "[centre, centre] with width"),
    "slot_overall": (2, 2, "[end, end] with width"),
    "slot_center_point": (2, 2, "[middle, an end centre] with width"),
    "arc_slot": (3, 3, "[end centre, a point on the centre arc, end centre] with width"),
    "conic": (3, 3, "[start, end, apex] with rho"),
    "ellipse": (3, 3, "[centre, major axis end, minor axis end]"),
    "control_point_spline": (3, 64, "the control points"),
    "fit_point_spline": (2, 64, "the points it passes through"),
}
DRAW_KINDS = tuple(DRAW_POINTS)
DRAW_TITLES = {  # the SKETCH tab's names (the undo / timeline titles)
    "midpoint_line": "Midpoint Line",
    "rectangle_3point": "3-Point Rectangle",
    "circle_2point": "2-Point Circle",
    "circle_3point": "3-Point Circle",
    "circle_2tangent": "2-Tangent Circle",
    "circle_3tangent": "3-Tangent Circle",
    "arc_3point": "3-Point Arc",
    "tangent_arc": "Tangent Arc",
    "edge_polygon": "Edge Polygon",
    "slot_center_to_center": "Center to Center Slot",
    "slot_overall": "Overall Slot",
    "slot_center_point": "Center Point Slot",
    "arc_slot": "Three Point Arc Slot",
    "conic": "Conic Curve",
    "ellipse": "Ellipse",
    "control_point_spline": "Control Point Spline",
    "fit_point_spline": "Fit Point Spline",
}


def _extra_draw(args, problems):
    kind = args.get("kind")
    if kind not in DRAW_POINTS:
        return
    low, high, words = DRAW_POINTS[kind]
    count = len(args.get("points") or [])
    if not low <= count <= high:
        want = str(low) if low == high else "%d to %d" % (low, high)
        problems.append("%s takes %s points: %s" % (kind, want, words))
    lines = args.get("lines")
    if kind in ("circle_2tangent", "circle_3tangent"):
        need = 2 if kind == "circle_2tangent" else 3
        if not isinstance(lines, list) or len(lines) != need:
            problems.append("%s needs lines: %d line indexes (get_sketch)" % (kind, need))
    elif lines is not None:
        problems.append("lines is for circle_2tangent / circle_3tangent")
    if kind == "tangent_arc" and "from" not in args:
        problems.append('tangent_arc needs from: {"curve": index, "point": "start" | "end"}')
    if kind == "edge_polygon" and "sides" not in args:
        problems.append("edge_polygon needs sides")
    if (kind.startswith("slot_") or kind == "arc_slot") and "width" not in args:
        problems.append("%s needs width (mm)" % kind)


define(
    "sketch_draw",
    "Sketch tools",
    "sketch",
    "SKETCH > CREATE (Midpoint Line, 3-Point Rectangle, 2-Point / 3-Point / 2-Tangent / "
    "3-Tangent Circle, 3-Point / Tangent Arc, Edge Polygon, Slots, Ellipse, Conic Curve, "
    "Control / Fit Point Spline)",
    "The SKETCH tab's drawing tools beyond add_to_sketch's plain shapes, with the tools' own "
    "code and constraints (a slot stays a slot). points: the clicks in order, [x, y] in the "
    "sketch: midpoint_line [middle, end]; rectangle_3point [corner, corner, far side]; "
    "circle_2point [a, b]; circle_3point 3 points; circle_2tangent / circle_3tangent: lines "
    "(indexes) + [a point near it]; arc_3point [start, on it, end]; tangent_arc: from "
    "{curve, point} + [end]; edge_polygon [p1, p2, side] + sides; slot_* [first, second] + "
    "width; arc_slot [end, on the centre arc, end] + width; conic [start, end, apex] + rho "
    "(0..1; 0.5 a parabola); ellipse [centre, major end, minor end]; control_point_spline / "
    "fit_point_spline: the points. length, angle (degrees), width, diameter, radius become "
    "dimensions, as typed in the tool. Answers the new curve indexes.",
    schema(
        {
            "sketch": kit.step_id("the sketch to draw in"),
            "kind": enum(DRAW_KINDS),
            "points": array(point2(), "the clicks, in order", 1),
            "lines": array(
                integer(minimum=-2), "tangent circles: line indexes (-1 / -2: axes)", 2, 3
            ),
            "from": obj(
                {
                    "curve": integer("the line or arc it leaves", minimum=0),
                    "point": enum(["start", "end"]),
                },
                ["curve", "point"],
                "tangent_arc: the end it starts from",
            ),
            "sides": integer("edge_polygon: sides", minimum=3, maximum=64),
            "length": positive("the line's / first side's / slot's length: a dimension (mm)"),
            "angle": number("its angle to the sketch x axis: a dimension (degrees)"),
            "width": positive("rectangle / slot width (mm)"),
            "diameter": positive("circle_2point: a diameter dimension (mm)"),
            "radius": positive("tangent circle / arc: a radius dimension (mm)"),
            "rho": number("conic: 0.01 .. 0.99 (0.5 a parabola)", minimum=0.01, maximum=0.99),
            "construction": boolean("construction geometry (dashed)", default=False),
        },
        ["sketch", "kind", "points"],
    ),
    extra=_extra_draw,
    own_id=False,
    title_fn=lambda a: "AI: %s" % DRAW_TITLES.get(a.get("kind"), "Sketch"),
    examples=[
        example(
            {
                "sketch": "Sketch1",
                "kind": "conic",
                "points": [[0, 0], [40, 0], [20, 30]],
                "rho": 0.4,
            },
            "a conic curve from (0, 0) to (40, 0) pulled towards (20, 30)",
        ),
        example(
            {
                "sketch": "Sketch1",
                "kind": "slot_center_to_center",
                "points": [[0, 0], [30, 0]],
                "width": 8,
            },
            "an 8 mm wide slot with its end centres 30 mm apart",
        ),
    ],
)

MODIFY_KINDS = ("fillet", "chamfer", "extend", "break", "offset", "toggle_construction")


def _extra_modify(args, problems):
    kind = args.get("kind")
    if kind in ("fillet", "chamfer", "extend", "break") and not args.get("points"):
        problems.append("%s needs points" % kind)
    if kind in ("offset", "toggle_construction") and not args.get("curves"):
        problems.append("%s needs curves (indexes)" % kind)
    if kind == "fillet" and "radius" not in args:
        problems.append("fillet needs radius (mm)")
    if kind in ("chamfer", "offset") and "distance" not in args:
        problems.append("%s needs distance (mm)" % kind)
    if kind == "chamfer" and "distance2" in args and "angle" in args:
        problems.append("chamfer takes distance2 or angle, not both")


define(
    "sketch_modify",
    "Sketch modify",
    "sketch",
    "SKETCH > MODIFY (Fillet, Chamfer, Offset, Extend, Break) and FINISH SKETCH > Toggle "
    "Construction (X)",
    "The SKETCH tab's MODIFY tools by their own code: fillet / chamfer: points at corners "
    "(where two curves meet), radius (fillet) or distance (chamfer; distance2 or angle "
    "(degrees) for unequal sides), each a dimension; extend: points on curves near the end "
    "to grow until it meets another curve; break: points on the pieces to split at their "
    "nearest crossings (trim removes a piece: sketch_trim); offset: curves (a chain of "
    "indexes), distance (mm; + on the side the chain turns to, - the other side), "
    "both_sides; toggle_construction: curves become construction (or back). Indexes after "
    "the change can move: get_sketch again.",
    schema(
        {
            "sketch": kit.step_id("the sketch"),
            "kind": enum(MODIFY_KINDS),
            "points": array(point2(), "fillet / chamfer: corners; extend / break: on curves", 1),
            "curves": array(integer(minimum=0), "offset / toggle_construction: curve indexes", 1),
            "radius": positive("fillet (mm)"),
            "distance": number("chamfer setback (mm, above 0); offset (mm, signed)"),
            "distance2": positive("chamfer: the second setback (mm)"),
            "angle": number(
                "chamfer: the angle from the first line (degrees)", above=0, maximum=179
            ),
            "both_sides": boolean("offset: on both sides", default=False),
        },
        ["sketch", "kind"],
    ),
    extra=_extra_modify,
    own_id=False,
    title_fn=lambda a: "AI: Sketch %s" % str(a.get("kind", "")).replace("_", " "),
    examples=[
        example(
            {"sketch": "Sketch1", "kind": "fillet", "points": [[0, 0]], "radius": 3},
            "round the corner at the origin with 3 mm",
        ),
        example(
            {"sketch": "Sketch1", "kind": "break", "points": [[10, 0]]},
            "split the curve through (10, 0) where it crosses the others",
        ),
    ],
)

PATTERN_KINDS = ("mirror", "rectangular", "circular", "move_copy")


def _extra_pattern(args, problems):
    kind = args.get("kind")
    if kind == "mirror" and "line" not in args:
        problems.append("mirror needs line (an index; -1 the x axis, -2 the y axis)")
    if kind == "circular" and "center" not in args:
        problems.append("circular needs center: a point of the sketch {curve, point}")
    if kind in ("rectangular", "circular") and "quantity" not in args:
        problems.append("%s needs quantity" % kind)
    if kind == "rectangular" and "distance" not in args:
        problems.append("rectangular needs distance (mm)")


_CENTER = obj(
    {
        "curve": integer("its curve (index; -1 with point start: the origin)", minimum=-2),
        "point": enum(["start", "end", "center"]),
    },
    ["curve", "point"],
    "a point of the sketch",
)
define(
    "sketch_pattern",
    "Sketch mirror / pattern / move",
    "sketch",
    "SKETCH > CREATE > Mirror / Circular Pattern / Rectangular Pattern, MODIFY > Move/Copy",
    "Repeat sketch curves with the SKETCH tab's own code; the copies stay tied to the "
    "originals (change one, they follow). curves: the indexes to repeat. mirror: line (index; "
    "-1 x axis, -2 y axis). rectangular: quantity, distance (mm) along direction (a line "
    "index, default -1), quantity2, distance2 along direction2 (default -2), distribution "
    "extent (distance is the whole span) | spacing (between copies). circular: center "
    "{curve, point}, quantity, angle (degrees, default 360), circular_type full | angle | "
    "symmetric. move_copy: dx, dy (mm), rotate (degrees about about [x, y]), copy (keep the "
    "originals). Answers the new curve indexes.",
    schema(
        {
            "sketch": kit.step_id("the sketch"),
            "kind": enum(PATTERN_KINDS),
            "curves": array(integer(minimum=0), "the curves", 1),
            "line": integer("mirror: the mirror line", minimum=-2),
            "quantity": integer("how many in all (with the originals)", minimum=1, maximum=500),
            "distance": number("mm"),
            "direction": integer("rectangular: a line index (-1 x axis)", minimum=-2),
            "quantity2": integer("rectangular: across", minimum=1, maximum=500, default=1),
            "distance2": number("mm", default=20),
            "direction2": integer("a line index (-2 y axis)", minimum=-2),
            "distribution": enum(["extent", "spacing"], default="extent"),
            "center": _CENTER,
            "angle": number("circular: degrees", default=360),
            "circular_type": enum(["full", "angle", "symmetric"], default="full"),
            "dx": number("move_copy: mm", default=0),
            "dy": number("move_copy: mm", default=0),
            "rotate": number("move_copy: degrees", default=0),
            "about": point2("move_copy: the point it turns about"),
            "copy": boolean("move_copy: keep the originals", default=False),
        },
        ["sketch", "kind", "curves"],
    ),
    extra=_extra_pattern,
    own_id=False,
    title_fn=lambda a: "AI: Sketch %s" % str(a.get("kind", "")).replace("_", " "),
    examples=[
        example(
            {"sketch": "Sketch1", "kind": "mirror", "curves": [0, 1], "line": -2},
            "mirror curves 0 and 1 about the sketch's y axis",
        ),
        example(
            {
                "sketch": "Sketch1",
                "kind": "circular",
                "curves": [4],
                "center": {"curve": -1, "point": "start"},
                "quantity": 6,
            },
            "six of circle 4 round the origin",
        ),
    ],
)

PROJECT_KINDS = ("project", "include_3d", "intersect", "project_to_surface", "isoparametric")


def _extra_project(args, problems):
    kind = args.get("kind")
    if kind in ("project", "include_3d") and not ({"edges", "faces", "body"} & set(args)):
        problems.append("%s needs edges, faces or body" % kind)
    if kind == "intersect" and not ({"faces", "edges", "body"} & set(args)):
        problems.append("intersect needs faces, edges or body")
    if kind == "project_to_surface" and not ("faces" in args and "curves" in args):
        problems.append("project_to_surface needs faces (to land on) and curves (indexes)")
    if kind == "isoparametric" and "faces" not in args:
        problems.append("isoparametric needs faces (one face)")


define(
    "sketch_project",
    "Project / Include",
    "sketch",
    "SKETCH > CREATE > Project / Include (Project, Intersect, Include 3D Geometry, Project to "
    "Surface, Isoparametric Curve)",
    "Bring model geometry into a sketch; it follows the model. project: edges / faces (their "
    "outline) / body (every edge) of body of (default: the sketch's body; another body or "
    "component works too) flattened onto the sketch (purple, they make profiles); "
    "include_3d: the same as reference curves (no profiles); intersect: where the sketch "
    "plane cuts faces / edges / body; project_to_surface: the sketch's curves (indexes) "
    "landed on faces as 3D curves (along closest | normal); isoparametric: U or V curves "
    "of one face (direction, fraction 0..1 or count spread evenly). Answers what came in.",
    schema(
        {
            "sketch": kit.step_id("the sketch"),
            "kind": enum(PROJECT_KINDS),
            "of": kit.step_id("the body the selectors look at (default: the sketch's body)"),
            "edges": kit.selector("model edges", "edges"),
            "faces": kit.selector("model faces"),
            "body": boolean("every edge of the body", default=False),
            "curves": array(integer(minimum=0), "project_to_surface: sketch curve indexes", 1),
            "along": enum(["closest", "normal"], "project_to_surface", default="closest"),
            "direction": enum(["U", "V"], "isoparametric", default="U"),
            "fraction": number("isoparametric: 0..1 across the face", minimum=0, maximum=1),
            "count": integer("isoparametric: curves spread evenly", minimum=1, maximum=50),
        },
        ["sketch", "kind"],
    ),
    extra=_extra_project,
    own_id=False,
    title_fn=lambda a: "AI: Sketch %s" % str(a.get("kind", "")).replace("_", " "),
    examples=[
        example(
            {
                "sketch": "Sketch2",
                "kind": "project",
                "faces": {"normal": [0, 0, 1], "at": {"axis": "z", "value": "max"}, "count": 1},
            },
            "the top face's outline into Sketch2, to extrude from it",
        )
    ],
)
