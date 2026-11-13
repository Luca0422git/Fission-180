# SPDX-License-Identifier: LGPL-2.1-or-later
"""What the AI's drawing tools work out before they call the drawing code (wave 8,
ai-drawing; fission180/ai/actions/drawing_actions.py): where a thing goes when the AI gave no
place (a free spot on the sheet, a dimension's text just outside its view, an ordinate's
line), which end a baseline starts from, how a drawing's elements are described back to the
AI. A person decides these with the mouse; an AI without a picture needs sensible defaults.

Pure Python: no FreeCAD, no Qt (unit tests: Fission180Tests/unit/test_ai_drawing_tools.py).
Coordinates: "page" = mm on the sheet from its bottom left corner; "local" = a view's own
mm (model size, from the view's centre, y up), as drawing.page_to_local gives them.
"""

import math

GAP = 8.0  # mm on the sheet between a view's outline and a dimension's text placed for it
STACK = 8.0  # mm between dimensions stacked on one side (Fusion's Baseline spacing)
FREE_MARGIN = 10.0  # mm kept free round a view placed on a free spot


# -- rectangles ------------------------------------------------------------------------------------
def overlaps(a, b, margin=0.0):
    """Two rectangles (x0, y0, x1, y1) overlap (closer than margin)."""
    return not (
        a[2] + margin <= b[0]
        or b[2] + margin <= a[0]
        or a[3] + margin <= b[1]
        or b[3] + margin <= a[1]
    )


def free_spot(area, blocked, size, prefer=None, step=5.0, margin=FREE_MARGIN):
    """The centre of a free place for a w x h rectangle inside `area` (x0, y0, x1, y1), away
    from every `blocked` rectangle by `margin`; the free place nearest `prefer` (default the
    area's top left), or None when there is none."""
    w, h = size
    x0, y0, x1, y1 = area
    if w > x1 - x0 or h > y1 - y0:
        return None
    if prefer is None:
        prefer = (x0 + w / 2.0, y1 - h / 2.0)
    best = None
    nx = int((x1 - x0 - w) / step) + 1
    ny = int((y1 - y0 - h) / step) + 1
    for i in range(nx + 1):
        cx = min(x0 + w / 2.0 + i * step, x1 - w / 2.0)
        for j in range(ny + 1):
            cy = min(y0 + h / 2.0 + j * step, y1 - h / 2.0)
            rect = (cx - w / 2.0, cy - h / 2.0, cx + w / 2.0, cy + h / 2.0)
            if any(overlaps(rect, b, margin) for b in blocked):
                continue
            d = math.hypot(cx - prefer[0], cy - prefer[1])
            if best is None or d < best[0]:
                best = (d, (cx, cy))
    return best[1] if best else None


# -- laying out views ----------------------------------------------------------------------------
VIEW_GAP = 20.0  # mm of paper between a view and the views projected from it
# a projected view's side of its parent in third angle projection (first angle: mirrored)
SIDES = {
    "Top": (0, 1),
    "Bottom": (0, -1),
    "Right": (1, 0),
    "Left": (-1, 0),
    "FrontTopRight": (1, 1),
    "FrontTopLeft": (-1, 1),
    "FrontBottomRight": (1, -1),
    "FrontBottomLeft": (-1, -1),
}


def side_of(kind, projection):
    sx, sy = SIDES.get(kind, (1, 0))
    if projection == "First angle":
        return -sx, -sy
    return sx, sy


def projected_offset(parent_size, child_size, kind, projection, scale, gap=VIEW_GAP):
    """(dx, dy) on the sheet from a parent view's centre to a projected view's, both sizes
    (w, h) at 1:1: side by side with `gap` mm of paper between them."""
    sx, sy = side_of(kind, projection)
    dx = sx * ((parent_size[0] + child_size[0]) / 2.0 * scale + gap)
    dy = sy * ((parent_size[1] + child_size[1]) / 2.0 * scale + gap)
    return dx, dy


def layout_views(base_size, children, projection, area, scales, gap=VIEW_GAP, at=None):
    """A base view and its projected views on the sheet. base_size and each child's size
    (w, h) at 1:1; children [(kind, size)]; scales: the scales to try, largest first (the
    first one at which the block fits `area` is taken, else the last); at: where the base
    view must stay (None: the block is centred in the area). Returns {"scale", "base":
    (x, y), "children": [(x, y)], "fits"}."""
    x0, y0, x1, y1 = area
    chosen = None
    for scale in scales:
        offsets = [
            projected_offset(base_size, size, kind, projection, scale, gap)
            for kind, size in children
        ]
        rects = [
            (
                -base_size[0] * scale / 2.0,
                -base_size[1] * scale / 2.0,
                base_size[0] * scale / 2.0,
                base_size[1] * scale / 2.0,
            )
        ]
        for (dx, dy), (_kind, size) in zip(offsets, children):
            w, h = size[0] * scale / 2.0, size[1] * scale / 2.0
            rects.append((dx - w, dy - h, dx + w, dy + h))
        bx0 = min(r[0] for r in rects)
        by0 = min(r[1] for r in rects)
        bx1 = max(r[2] for r in rects)
        by1 = max(r[3] for r in rects)
        if at is not None:
            fits = at[0] + bx0 >= x0 and at[0] + bx1 <= x1 and at[1] + by0 >= y0
            fits = fits and at[1] + by1 <= y1
            base = tuple(at)
        else:
            fits = bx1 - bx0 <= x1 - x0 and by1 - by0 <= y1 - y0
            base = ((x0 + x1) / 2.0 - (bx0 + bx1) / 2.0, (y0 + y1) / 2.0 - (by0 + by1) / 2.0)
        chosen = {
            "scale": scale,
            "base": base,
            "children": [(base[0] + dx, base[1] + dy) for dx, dy in offsets],
            "fits": fits,
        }
        if fits:
            break
    return chosen


# -- dimensions ------------------------------------------------------------------------------------
def element_point(info):
    """A representative local point of an element (a line's middle, a circle's centre)."""
    kind = info.get("kind")
    if kind == "line":
        (x1, y1), (x2, y2) = info["p1"], info["p2"]
        return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)
    if kind in ("circle", "arc"):
        return tuple(info["center"])
    if kind == "vertex":
        return tuple(info["point"])
    return (0.0, 0.0)


def _sign(v):
    return -1.0 if v < 0 else 1.0


def linear_axis(infos, use_centers=()):
    """DistanceX or DistanceY for a 'linear' dimension between two points or of one line:
    the axis along which they are farther apart (Fusion follows the mouse; an AI without
    one gets the plain reading)."""
    pts = []
    for i, info in enumerate(infos):
        if info.get("kind") == "line" and len(infos) == 1:
            pts = [tuple(info["p1"]), tuple(info["p2"])]
            break
        pts.append(element_point(info))
    if len(pts) < 2:
        return "DistanceX"
    dx, dy = abs(pts[1][0] - pts[0][0]), abs(pts[1][1] - pts[0][1])
    return "DistanceX" if dx >= dy else "DistanceY"


def dimension_place(dim_type, infos, extent, scale, taken=()):
    """Where a dimension's text goes when the AI gave no place: just outside the view (its
    half extent `extent` in local mm) on the side of what it measures, 8 mm on the sheet
    away, one more step out for each text already on that line (`taken`: local points of
    the view's other dimension texts). Returns a local point."""
    hw, hh = extent
    s = scale or 1.0
    gap = GAP / s
    step = STACK / s
    pts = [element_point(i) for i in infos] or [(0.0, 0.0)]
    mx = sum(p[0] for p in pts) / len(pts)
    my = sum(p[1] for p in pts) / len(pts)
    if dim_type in ("Diameter", "Radius"):
        info = infos[0]
        r = float(info.get("radius", 0.0))
        cx, cy = info.get("center", (mx, my))
        d = math.hypot(cx, cy)
        ux, uy = (cx / d, cy / d) if d > 1e-9 else (math.sqrt(0.5), math.sqrt(0.5))
        place = [cx + ux * (r + gap), cy + uy * (r + gap)]
        axis = None
    elif dim_type == "DistanceX":
        side = _sign(my) if abs(my) > 1e-9 else -1.0
        place = [mx, side * (hh + gap)]
        axis = 1
    elif dim_type == "DistanceY":
        side = _sign(mx) if abs(mx) > 1e-9 else 1.0
        place = [side * (hw + gap), my]
        axis = 0
    else:
        d = math.hypot(mx, my)
        ux, uy = (mx / d, my / d) if d > 1e-9 else (0.0, 1.0)
        place = [mx + ux * gap * 1.5, my + uy * gap * 1.5]
        axis = None
    if axis is not None:
        out = _sign(place[axis])
        for _ in range(40):
            near = any(abs(t[axis] - place[axis]) < step * 0.5 for t in taken)
            if not near:
                break
            place[axis] += out * step
    return tuple(place)


def baseline_start(points, targets):
    """Which end of a base dimension Baseline measures from: the one farther from the new
    points (so each new dimension spans the old one); Chain goes on from the nearer one.
    points: the base dimension's two ends; targets: the new points. Returns 0 or 1."""
    if not targets:
        return 0
    tx = sum(t[0] for t in targets) / len(targets)
    ty = sum(t[1] for t in targets) / len(targets)
    d0 = math.hypot(points[0][0] - tx, points[0][1] - ty)
    d1 = math.hypot(points[1][0] - tx, points[1][1] - ty)
    return 0 if d0 >= d1 else 1


def ordinate_lines(view_rect, axis, at=None, gap=GAP):
    """Where the values of an ordinate set go (page mm): x values on a level line below
    the view (its y), y values on an upright line left of it (its x); `at` [x, y] puts them
    through that point instead."""
    x0, y0, x1, y1 = view_rect
    if axis == "x":
        return at[1] if at is not None else y0 - gap
    return at[0] if at is not None else x0 - gap


def outward(view_rect, point, distance):
    """A page point `distance` mm from `point`, away from the middle of the view's
    rectangle (where a leader's text or a symbol goes by default)."""
    cx = (view_rect[0] + view_rect[2]) / 2.0
    cy = (view_rect[1] + view_rect[3]) / 2.0
    dx, dy = point[0] - cx, point[1] - cy
    d = math.hypot(dx, dy)
    if d < 1e-9:
        dx, dy, d = 1.0, 1.0, math.sqrt(2.0)
    return (point[0] + dx / d * distance, point[1] + dy / d * distance)


# -- describing -----------------------------------------------------------------------------------
def r(value, digits=3):
    """A number rounded for an answer (no -0)."""
    out = round(float(value), digits)
    return 0.0 if out == 0 else out


def element_text(info):
    """One line naming an element the way an AI picks it again."""
    kind = info.get("kind")
    if kind == "line":
        (x1, y1), (x2, y2) = info["p1"], info["p2"]
        return "line (%g, %g)-(%g, %g)" % (r(x1), r(y1), r(x2), r(y2))
    if kind in ("circle", "arc"):
        cx, cy = info["center"]
        return "%s R%g at (%g, %g)" % (kind, r(info["radius"]), r(cx), r(cy))
    if kind == "vertex":
        return "point (%g, %g)" % (r(info["point"][0]), r(info["point"][1]))
    return kind or "?"


def scale_text(scale):
    try:
        if scale >= 1:
            return "%g:1" % scale
        return "1:%g" % round(1.0 / scale, 6)
    except Exception:
        return str(scale)


TOLERANCE_NAMES = {
    "none": "None",
    "symmetric": "Symmetric",
    "deviation": "Deviation",
    "limits": "Limits",
    "fit": "Fit",
}
FIT_DISPLAY_NAMES = {
    "class": "Class",
    "class_and_tolerances": "Class and tolerances",
    "limits": "Limits",
    "fit": "Fit",
}


def dimension_settings(args, current):
    """The Dimension dialog's settings (drawing_dims_core.DEFAULTS keys) after an
    edit_drawing_dimension call: `current` changed by the AI's arguments."""
    out = dict(current)
    for key in ("override", "prefix", "suffix", "precision", "tol_precision"):
        if key in args:
            out[key] = args[key]
    if "tolerance" in args:
        out["tolerance"] = TOLERANCE_NAMES[args["tolerance"]]
    for key in ("upper", "lower"):
        if key in args:
            out[key] = float(args[key])
    if out.get("tolerance") == "Symmetric" and "upper" in args and "lower" not in args:
        out["lower"] = -abs(float(args["upper"]))
    if "fit" in args:
        fit = str(args["fit"]).strip().replace(" ", "")
        if "/" not in fit and fit:
            # one class: the dimension is that member (H7: a hole; g6: a shaft); the
            # dialog's fit always names both, the other side is the basic one of that grade
            grade = "".join(c for c in fit if c.isdigit())
            if fit[:1].isupper():
                fit, out["fit_member"] = "%s/h%s" % (fit, grade), "Hole"
            else:
                fit, out["fit_member"] = "H%s/%s" % (grade, fit), "Shaft"
        out["fit"] = fit
    if "fit_member" in args:
        out["fit_member"] = args["fit_member"].capitalize()
    if "fit_display" in args:
        out["fit_display"] = FIT_DISPLAY_NAMES[args["fit_display"]]
    for key in ("basic", "reference"):
        if key in args:
            out[key] = bool(args[key])
    return out
