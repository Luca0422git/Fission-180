# SPDX-License-Identifier: LGPL-2.1-or-later
"""The decisions of Fission 180's Sketch Dimension tool (sketch_dimension_tool.py), without
FreeCAD: pure Python, unit tested.

Fusion's Sketch Dimension (D): pick one or two things, move the pointer, click to place the
dimension, type its value. What dimension it is follows from what was picked and from where
the pointer is:

- one line: its length. A slanted line: the ALIGNED length while the pointer is beside the
  line, the horizontal distance when it is past the line's ends above or below, the vertical
  one when it is past them to the left or right (Autodesk blog "Quick tip: aligned
  dimensions"; the exact zones are Fission 180's);
- a circle: its diameter; an arc: its radius;
- two points (or a point and a circle's centre): aligned / horizontal / vertical the same way;
- a point and a line, two parallel lines: the distance between them;
- two lines that are not parallel: the angle of the sector the pointer is in;
- a line (or point) and a CENTERLINE: the diameter (twice the distance), as Fusion does for
  revolve profiles (Autodesk blog "Mastering Sketch Dimensions").

A point is (x, y); a line (origin, direction).
"""

import math

ALIGNED, HORIZONTAL, VERTICAL = "Distance", "DistanceX", "DistanceY"
EPS = 1e-9
PARALLEL_DEG = 0.01  # lines this close in direction are parallel (a distance, not an angle)
ZERO = 1e-7  # mm: a dimension smaller than this is no dimension (Fusion refuses 0)


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1])


def _len(v):
    return math.hypot(v[0], v[1])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def _cross(a, b):
    return a[0] * b[1] - a[1] * b[0]


def linear_kind(a, b, cursor):
    """ALIGNED, HORIZONTAL or VERTICAL for the distance between points a and b with the
    pointer at `cursor`. Points level with or upright above each other: always ALIGNED (it
    is the same number). Else ALIGNED while the pointer is beside the stretch between the
    two points (between the two perpendiculars through them), HORIZONTAL when it is past
    them and above or below their box, VERTICAL when left or right of it."""
    d = _sub(b, a)
    length = _len(d)
    if length < EPS:
        return ALIGNED
    if abs(d[0]) <= 1e-7 * max(1.0, length) or abs(d[1]) <= 1e-7 * max(1.0, length):
        return ALIGNED
    u = (d[0] / length, d[1] / length)
    mid = ((a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0)
    along = _dot(_sub(cursor, mid), u)
    if abs(along) <= length / 2.0:
        return ALIGNED
    out_x = max(min(a[0], b[0]) - cursor[0], cursor[0] - max(a[0], b[0]), 0.0)
    out_y = max(min(a[1], b[1]) - cursor[1], cursor[1] - max(a[1], b[1]), 0.0)
    if out_x == 0.0 and out_y == 0.0:
        return ALIGNED
    return HORIZONTAL if out_y >= out_x else VERTICAL


def measure(kind, a, b):
    """The size of the dimension of that kind between two points."""
    if kind == HORIZONTAL:
        return abs(b[0] - a[0])
    if kind == VERTICAL:
        return abs(b[1] - a[1])
    return _len(_sub(b, a))


def ordered(kind, a, b):
    """True when (a, b) is the order FreeCAD wants for a positive value: left to right for
    a horizontal distance, bottom to top for a vertical one (it keeps the direction in the
    sign). Aligned: any."""
    if kind == HORIZONTAL:
        return b[0] >= a[0]
    if kind == VERTICAL:
        return b[1] >= a[1]
    return True


def parallel(d1, d2, tolerance_deg=PARALLEL_DEG):
    """Two directions are parallel (either way round)."""
    n = _len(d1) * _len(d2)
    if n < EPS:
        return True
    sine = abs(_cross(d1, d2)) / n
    return sine <= math.sin(math.radians(tolerance_deg))


def point_line_distance(p, origin, direction):
    n = _len(direction)
    if n < EPS:
        return _len(_sub(p, origin))
    return abs(_cross(direction, _sub(p, origin))) / n


def foot(p, origin, direction):
    """The point of the line nearest to p."""
    n2 = _dot(direction, direction)
    if n2 < EPS:
        return origin
    t = _dot(_sub(p, origin), direction) / n2
    return (origin[0] + t * direction[0], origin[1] + t * direction[1])


def crossing(o1, d1, o2, d2):
    """Where two lines cross, or None when they are parallel."""
    den = _cross(d1, d2)
    if abs(den) < EPS:
        return None
    t = _cross(_sub(o2, o1), d2) / den
    return (o1[0] + t * d1[0], o1[1] + t * d1[1])


def angle_sector(o1, d1, o2, d2, cursor):
    """The angle between two crossing lines in the sector the pointer is in:
    (s1, s2, angle, corner): s1, s2 are +1 / -1 (the rays from the corner along s1 * d1 and
    s2 * d2 bound the sector), angle in radians (0..pi). None for parallel lines."""
    corner = crossing(o1, d1, o2, d2)
    if corner is None:
        return None
    c = _sub(cursor, corner)
    den = _cross(d1, d2)
    a = _cross(c, d2) / den  # c = a * d1 + b * d2
    b = _cross(d1, c) / den
    s1 = 1 if a >= 0 else -1
    s2 = 1 if b >= 0 else -1
    r1 = (s1 * d1[0], s1 * d1[1])
    r2 = (s2 * d2[0], s2 * d2[1])
    cosine = _dot(r1, r2) / (_len(r1) * _len(r2))
    return s1, s2, math.acos(max(-1.0, min(1.0, cosine))), corner


def signed_angle(r1, r2):
    """The angle from direction r1 to r2, counter-clockwise positive (-pi..pi)."""
    return math.atan2(_cross(r1, r2), _dot(r1, r2))


# -- where the label goes -------------------------------------------------------------------------
def linear_label(kind, p1, p2, cursor):
    """(LabelDistance, LabelPosition) that put a length dimension's text at the pointer, the
    way FreeCAD places it: off the middle of the measured stretch p1 -> p2 (for a horizontal
    or vertical dimension: of its level or upright stretch)."""
    q = p2
    if kind == HORIZONTAL:
        q = (p2[0], p1[1])
    elif kind == VERTICAL:
        q = (p1[0], p2[1])
    d = _sub(q, p1)
    length = _len(d)
    if length < EPS:
        return 10.0, 0.0
    u = (d[0] / length, d[1] / length)
    normal = (-u[1], u[0])
    mid = ((p1[0] + q[0]) / 2.0, (p1[1] + q[1]) / 2.0)
    v = _sub(cursor, mid)
    return _dot(v, normal), _dot(v, u)


def radial_label(centre, radius, cursor):
    """(LabelDistance, LabelPosition) for a radius or diameter: how far beyond the circle,
    at which angle."""
    v = _sub(cursor, centre)
    return _len(v) - radius, math.atan2(v[1], v[0])


# -- the preview ----------------------------------------------------------------------------------
def linear_preview(kind, a, b, cursor):
    """Polylines of a length dimension being placed: the two extension lines and the
    dimension line through the pointer."""
    if kind == HORIZONTAL:
        a2, b2 = (a[0], cursor[1]), (b[0], cursor[1])
    elif kind == VERTICAL:
        a2, b2 = (cursor[0], a[1]), (cursor[0], b[1])
    else:
        d = _sub(b, a)
        length = _len(d)
        if length < EPS:
            return []
        normal = (-d[1] / length, d[0] / length)
        h = _dot(_sub(cursor, a), normal)
        a2 = (a[0] + h * normal[0], a[1] + h * normal[1])
        b2 = (b[0] + h * normal[0], b[1] + h * normal[1])
    return [[a, a2], [b, b2], [a2, b2]]


def radial_preview(centre, radius, cursor, diameter):
    """The leader of a radius (from the centre) or diameter (across the circle) dimension
    through the pointer."""
    v = _sub(cursor, centre)
    n = _len(v)
    if n < EPS:
        return []
    u = (v[0] / n, v[1] / n)
    far = max(n, radius)
    start = (centre[0] - radius * u[0], centre[1] - radius * u[1]) if diameter else centre
    return [[start, (centre[0] + far * u[0], centre[1] + far * u[1])]]


def angle_preview(corner, r1, r2, cursor, steps=24):
    """The arc of an angle dimension through the pointer, between the rays r1 and r2 from
    the corner."""
    radius = _len(_sub(cursor, corner))
    if radius < EPS:
        return []
    a1 = math.atan2(r1[1], r1[0])
    sweep = signed_angle(r1, r2)
    arc = [
        (
            corner[0] + radius * math.cos(a1 + sweep * i / steps),
            corner[1] + radius * math.sin(a1 + sweep * i / steps),
        )
        for i in range(steps + 1)
    ]
    return [arc]


# -- which click is a pick ------------------------------------------------------------------------
POINT, LINE, CIRCLE, ARC, AXIS, OTHER = "point", "line", "circle", "arc", "axis", "other"


def alone(kind):
    """A thing that has a dimension by itself (a line's length, a circle's diameter, an
    arc's radius). A point or an axis needs a second thing."""
    return kind in (LINE, CIRCLE, ARC)


def pairs(first, second):
    """Two kinds of things can be dimensioned to each other."""
    usable = (POINT, LINE, CIRCLE, ARC, AXIS)
    if first not in usable or second not in usable:
        return False
    return not (first == AXIS and second == AXIS)


def is_pick(picked, clicked):
    """Is a click on a thing of kind `clicked` a PICK (True) or the click that places the
    dimension (False), with the kinds `picked` picked so far? Fusion: once two things are
    picked the next click places the dimension wherever it lands, also on a line (the
    report: it was taken as a third pick and became Equal constraints). With one thing
    picked a click on another one picks it, except on an axis when the first has a
    dimension by itself: Fusion's sketch axes cannot be picked there, the click places the
    dimension (the report: placing a line's length on top of the Y axis made an Angle). A
    point's or an axis's first pick makes the axis a pick (the distance to it)."""
    if len(picked) >= 2:
        return False
    if not picked:
        return clicked in (POINT, LINE, CIRCLE, ARC, AXIS)
    first = picked[0]
    if not pairs(first, clicked):
        return False
    if clicked == AXIS and alone(first):
        return False
    return True
