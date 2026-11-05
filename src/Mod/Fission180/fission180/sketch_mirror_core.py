# SPDX-License-Identifier: LGPL-2.1-or-later
"""The maths of the sketch Mirror (sketch_mirror_tool.py), no FreeCAD: where a point lands
mirrored about a line, and which Symmetric / Equal constraints tie each mirrored copy to
its original (the same pairs FreeCAD's SketchObject::addSymmetric makes when asked for
symmetry constraints, which its Python binding cannot ask for)."""

LINE = "Part::GeomLineSegment"
CIRCLE = "Part::GeomCircle"
ELLIPSE = "Part::GeomEllipse"
ARCS = (
    "Part::GeomArcOfCircle",
    "Part::GeomArcOfEllipse",
    "Part::GeomArcOfHyperbola",
    "Part::GeomArcOfParabola",
)
POINT = "Part::GeomPoint"
START, END, MID = 1, 2, 3


def reflect(p, a, b):
    """The point p mirrored about the line through a and b (2D tuples)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    n2 = dx * dx + dy * dy
    if n2 < 1e-24:
        return (2 * a[0] - p[0], 2 * a[1] - p[1])  # a point: mirrored through it
    t = ((p[0] - a[0]) * dx + (p[1] - a[1]) * dy) / n2
    fx, fy = a[0] + dx * t, a[1] + dy * t
    return (2 * fx - p[0], 2 * fy - p[1])


def reflect_all(points, a, b):
    return [reflect(p, a, b) for p in points]


def inverted(orig_start, new_start, new_end, a, b, tol=1e-6):
    """True when the mirror of the original's start is the copy's end (FreeCAD's
    isStartEndInverted: arcs always swap, lines keep their order)."""
    m = reflect(orig_start, a, b)
    d_start = (m[0] - new_start[0]) ** 2 + (m[1] - new_start[1]) ** 2
    d_end = (m[0] - new_end[0]) ** 2 + (m[1] - new_end[1]) ** 2
    return d_end + tol < d_start


def ties(kind, orig, new, swapped, aligned=False):
    """[(type, first, first_pos, second, second_pos)] tying the copy `new` to `orig`:
    Symmetric (about the mirror line, added by the caller) or Equal. As FreeCAD: lines by
    both ends (not the axes of an ellipse: `aligned`), circles and ellipses by the centre
    and Equal, arcs by both ends and Equal, points by themselves (not a spline's knots);
    a spline is tied by its control circles."""
    if kind == LINE:
        if aligned:
            return []
        return [
            ("Symmetric", orig, START, new, END if swapped else START),
            ("Symmetric", orig, END, new, START if swapped else END),
        ]
    if kind in (CIRCLE, ELLIPSE):
        return [("Equal", orig, 0, new, 0), ("Symmetric", orig, MID, new, MID)]
    if kind in ARCS:
        return [
            ("Equal", orig, 0, new, 0),
            ("Symmetric", orig, START, new, END if swapped else START),
            ("Symmetric", orig, END, new, START if swapped else END),
        ]
    if kind == POINT and not aligned:
        return [("Symmetric", orig, START, new, START)]
    return []


KEPT = ("InternalAlignment", "Coincident")


def copied_constraints(before, after_types, new_ids):
    """Indices (from `before`, the constraint count before the mirror) of the constraints
    FreeCAD copied onto the copies that go: the symmetry ties hold the copies instead
    (FreeCAD drops them too when it adds symmetry constraints). Kept: InternalAlignment (a
    spline's control circles) and Coincident (the copies' corners stay joined, for Trim,
    Fillet and chain selection; a tie they make redundant is not added).
    after_types: [(type, first, second)] of every constraint after the mirror."""
    new = set(new_ids)
    out = []
    for index in range(before, len(after_types)):
        kind, first, second = after_types[index]
        if kind in KEPT:
            continue
        if first in new or second in new:
            out.append(index)
    return out


# -- box selection (Fusion: left to right takes what is fully inside, right to left what the
# box touches); in screen pixels, so it is the box the user sees -----------------------------
def _inside(p, box):
    x0, y0, x1, y1 = box
    return x0 <= p[0] <= x1 and y0 <= p[1] <= y1


def _segments_cross(a, b, c, d):
    def orient(p, q, r):
        return (q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0])

    o1, o2, o3, o4 = orient(a, b, c), orient(a, b, d), orient(c, d, a), orient(c, d, b)
    return (o1 > 0) != (o2 > 0) and (o3 > 0) != (o4 > 0)


def boxed(polylines, start, end):
    """The keys of the polylines {key: [screen points]} the box from `start` to `end` (screen
    pixels) takes: dragged left to right (window) the ones fully inside, right to left
    (crossing) the ones it touches. A point off the view (None) is outside."""
    box = (min(start[0], end[0]), min(start[1], end[1]), max(start[0], end[0]), max(start[1], end[1]))
    window = end[0] >= start[0]
    x0, y0, x1, y1 = box
    edges = [((x0, y0), (x1, y0)), ((x1, y0), (x1, y1)), ((x1, y1), (x0, y1)), ((x0, y1), (x0, y0))]
    out = []
    for key, points in polylines.items():
        if not points:
            continue
        if window:
            if all(p is not None and _inside(p, box) for p in points):
                out.append(key)
            continue
        seen = [p for p in points if p is not None]
        if any(_inside(p, box) for p in seen):
            out.append(key)
            continue
        hit = False
        for a, b in zip(points, points[1:]):
            if a is None or b is None:
                continue
            if any(_segments_cross(a, b, c, d) for c, d in edges):
                hit = True
                break
        if hit:
            out.append(key)
    return out
