# SPDX-License-Identifier: LGPL-2.1-or-later
"""The maths of the sketch Rectangular and Circular Pattern (sketch_pattern_tool.py), no
FreeCAD, no Qt: unit tested (Fission180Tests/unit/test_sketch_pattern_core.py).

The spacing rules are the body patterns' (pattern_core): Quantity counts the original,
Distance is the Extent (original to last copy) or the Spacing (copy to copy) as the Distance
Type says; a circular pattern is Full (evenly round the whole circle) or Angle (from the
original to Total Angle). Here they work on sketch points (x, y).

Symmetric (wave 7, the book parity report): Quantity is the number of instances IN ALL,
spread to both sides of the original, which stays in the middle (the book: Rectangular
Pattern, Symmetric, Quantity 5: five holes; until wave 7 Quantity counted each side, 5 gave
9). An even Quantity cannot be symmetric about the original: the extra copy goes to the
positive side. The Distance (Extent) and the Total Angle span the whole pattern, first
instance to last.

Also here: what a drag of a handle makes of the value (the arrow of a direction, the disc of
the total angle), and which constraints a copy gets (see copied_constraints).
"""

import math

from . import pattern_core as pcore
from .pattern_core import PatternError  # noqa: F401  (the tool says its text)

GEO_UNDEF = -2000  # FreeCAD's "no curve" in a constraint (GeoEnum::GeoUndef)
ANGLE_LIMIT = 360.0
MIN_ANGLE = 1.0  # a dragged Total Angle never goes nearer 0 (0 is no pattern)


# -- plane vectors ----------------------------------------------------------------------------
def unit(v):
    x, y = float(v[0]), float(v[1])
    n = math.hypot(x, y)
    if n < 1e-12:
        raise PatternError("The direction has no length.")
    return (x / n, y / n)


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1]


def perpendicular(v):
    """`v` turned a quarter turn anticlockwise (the sketch's Y from its X)."""
    return (-v[1], v[0])


def rotate(p, centre, degrees):
    """The point p turned `degrees` anticlockwise about `centre`."""
    a = math.radians(float(degrees))
    c, s = math.cos(a), math.sin(a)
    dx, dy = p[0] - centre[0], p[1] - centre[1]
    return (centre[0] + c * dx - s * dy, centre[1] + s * dx + c * dy)


def apply(move, p):
    """A copy's move applied to the point p: ("move", (dx, dy)) or ("turn", centre, deg)."""
    if move[0] == "move":
        return (p[0] + move[1][0], p[1] + move[1][1])
    return rotate(p, move[1], move[2])


def apply_all(move, points):
    return [apply(move, p) for p in points]


# -- where the copies go ----------------------------------------------------------------------
def _both_sides(quantity, step):
    """Offsets of `quantity` instances spread to both sides of the original (0, first):
    half of the copies after it, the others before it (one more after when they cannot be
    shared evenly)."""
    quantity = int(quantity)
    after = quantity // 2
    before = quantity - 1 - after
    return (
        [0.0] + [step * k for k in range(1, after + 1)] + [-step * k for k in range(1, before + 1)]
    )


def linear_offsets(quantity, distance, distribution="extent", direction_type="one"):
    """Signed offsets of the instances from the original, the original (0) first."""
    if direction_type != "symmetric":
        return pcore.linear_offsets(quantity, distance, distribution, "one")
    quantity = int(quantity)
    if quantity < 1:
        raise PatternError("The quantity must be at least 1.")
    return _both_sides(quantity, pcore.step_of(quantity, distance, distribution))


def circular_angles(quantity, angle=360.0, kind="full"):
    """Angles (degrees) of the instances, the original (0) first."""
    if kind != "symmetric":
        return pcore.circular_angles(quantity, angle, kind)
    quantity = int(quantity)
    if quantity < 1:
        raise PatternError("The quantity must be at least 1.")
    if quantity == 1:
        return [0.0]
    if abs(float(angle)) < 1e-9:
        raise PatternError("The total angle must not be 0.")
    if abs(abs(float(angle)) - 360.0) < 1e-9:
        step = 360.0 / quantity  # the whole circle: the last copy does not land on the first
    else:
        step = float(angle) / (quantity - 1)
    return _both_sides(quantity, step)


def rect_moves(d1, q1, dist1, d2, q2, dist2, distribution="extent", type1="one", type2="one"):
    """[("move", (dx, dy))] of every copy (the original not included), in rows along
    direction d1 and columns along d2 (unit vectors; d2 None: one direction only)."""
    u1 = unit(d1)
    offsets1 = linear_offsets(q1, dist1, distribution, type1)
    offsets2 = [0.0]
    u2 = (0.0, 0.0)
    if d2 is not None and int(q2) > 1:
        u2 = unit(d2)
        offsets2 = linear_offsets(q2, dist2, distribution, type2)
    out = []
    for a, b in pcore.grid(offsets1, offsets2)[1:]:
        out.append(("move", (u1[0] * a + u2[0] * b, u1[1] * a + u2[1] * b)))
    return out


def rect_count(q1, type1="one", q2=1, type2="one"):
    """Instances of a rectangular pattern, the original included (Symmetric or not: the
    Quantity is the number of instances)."""
    return max(1, int(q1)) * max(1, int(q2))


def circular_moves(centre, quantity, angle=360.0, kind="full"):
    """[("turn", centre, degrees)] of every copy (the original not included)."""
    angles = circular_angles(quantity, angle, kind)
    return [("turn", (float(centre[0]), float(centre[1])), a) for a in angles[1:]]


def unique_moves(moves, tolerance=1e-7):
    """`moves` without the ones that put a copy exactly on the original or on an earlier
    copy (a turn of 360 degrees, two turns a whole turn apart, a move of nothing): two
    curves on one spot cannot be told apart or clicked (the book parity report: overlapping
    arcs left behind), and split the sketch's areas into slivers."""
    seen = [("move", 0.0, 0.0)]
    out = []
    for move in moves:
        if move[0] == "move":
            key = ("move", float(move[1][0]), float(move[1][1]))
            same = [
                k
                for k in seen
                if k[0] == "move" and math.hypot(k[1] - key[1], k[2] - key[2]) <= tolerance
            ]
            if not same and abs(key[1]) <= tolerance and abs(key[2]) <= tolerance:
                same = [key]
        else:
            turn = float(move[2]) % 360.0
            key = ("turn", turn, 0.0)
            same = [
                k
                for k in seen
                if (k[0] == "turn" and min(abs(k[1] - turn), 360.0 - abs(k[1] - turn)) <= tolerance)
                or (
                    k[0] == "move"
                    and k[1] == 0.0
                    and k[2] == 0.0
                    and min(turn, 360.0 - turn) <= tolerance
                )
            ]
        if same:
            continue
        seen.append(key)
        out.append(move)
    return out


def circular_count(quantity, kind="full"):
    return max(1, int(quantity))


def check_rect(q1, dist1, q2, dist2, type1="one", type2="one"):
    """Raise PatternError for values Fusion's dialog refuses (the text says what to change)."""
    for q, d, which in ((q1, dist1, "1"), (q2, dist2, "2")):
        if int(q) < 1:
            raise PatternError("The quantity must be at least 1.")
        if int(q) > 1 and abs(float(d)) < 1e-9:
            raise PatternError("The distance of direction %s must not be 0." % which)
    pcore.check_total(rect_count(q1, type1, q2, type2))


def check_circular(quantity, angle, kind):
    if int(quantity) < 1:
        raise PatternError("The quantity must be at least 1.")
    if kind != "full":
        if abs(float(angle)) < 1e-9:
            raise PatternError("The total angle must not be 0.")
        if abs(float(angle)) > ANGLE_LIMIT + 1e-9:
            raise PatternError("The total angle can be at most 360 deg.")
    pcore.check_total(circular_count(quantity, kind))


# -- the picked curves ------------------------------------------------------------------------
def bounds(polylines):
    """(xmin, ymin, xmax, ymax) of the polylines' points, or None."""
    xs, ys = [], []
    for poly in polylines:
        for p in poly:
            xs.append(p[0])
            ys.append(p[1])
    if not xs:
        return None
    return (min(xs), min(ys), max(xs), max(ys))


def middle(box):
    return ((box[0] + box[2]) / 2.0, (box[1] + box[3]) / 2.0)


def size_along(polylines, direction):
    """How far the polylines reach along `direction` (mm)."""
    u = unit(direction)
    values = [dot(p, u) for poly in polylines for p in poly]
    return (max(values) - min(values)) if values else 0.0


def default_distance(size, quantity, distribution="extent"):
    """The Distance a direction starts with: copies that clear the original, as the body
    patterns (pattern_core.default_distance); a Spacing is one step."""
    if distribution == "spacing":
        return pcore.default_distance(size, 2)
    return pcore.default_distance(size, max(int(quantity), 2))


# -- the handles ------------------------------------------------------------------------------
def arrow_value(start_value, press, pointer, direction):
    """The distance an arrow dragged from `press` to `pointer` (sketch points) gives: the
    value it had plus how far the hand went along the arrow's line (a drag across it changes
    nothing; past the start it goes negative: the copies go the other way)."""
    u = unit(direction)
    return float(start_value) + dot((pointer[0] - press[0], pointer[1] - press[1]), u)


def angle_at(centre, point):
    """The direction from centre to point, degrees anticlockwise from the sketch's X."""
    return math.degrees(math.atan2(point[1] - centre[1], point[0] - centre[0]))


def wrap180(degrees):
    """The same turn as `degrees`, between -180 and 180."""
    return (float(degrees) + 180.0) % 360.0 - 180.0


def turned(value, last_raw, raw, limit=ANGLE_LIMIT):
    """The Total Angle a disc dragged on from `last_raw` to `raw` (directions, degrees) gives:
    the value goes on past half a turn the short way round each step (a hand going round
    the centre counts up to 360), never past +-limit."""
    step = wrap180(float(raw) - float(last_raw))
    return max(-limit, min(limit, float(value) + step))


def settle_angle(value):
    """A dragged angle as the field takes it: one decimal, never nearer 0 than MIN_ANGLE."""
    value = round(float(value), 1)
    if abs(value) < MIN_ANGLE:
        value = MIN_ANGLE if value >= 0 else -MIN_ANGLE
    return value


def type_after_drag(kind, value):
    """The circular Type after the disc was dragged to `value`: a Full pattern dragged off the
    whole circle becomes an Angle pattern (Fusion); the others stay."""
    if kind == "full" and abs(abs(float(value)) - ANGLE_LIMIT) > 1e-9:
        return "angle"
    return kind


def segment_distance(p, a, b):
    """Distance (pixels) from the point p to the segment a-b."""
    ax, ay = a
    bx, by = b
    dx, dy = bx - ax, by - ay
    n = dx * dx + dy * dy
    t = 0.0 if n < 1e-12 else max(0.0, min(1.0, ((p[0] - ax) * dx + (p[1] - ay) * dy) / n))
    return math.hypot(ax + t * dx - p[0], ay + t * dy - p[1])


def nearest_handle(pointer, handles, reach):
    """The key of the handle under `pointer` (screen pixels): handles {key: (a, b)}, a
    segment (an arrow from its foot to its tip) or a == b (a disc), within reach[kind]
    pixels; the nearest wins. None when none is."""
    best = None
    for key, (a, b, kind) in handles.items():
        if a is None or b is None:
            continue
        d = segment_distance(pointer, a, b)
        if d <= reach.get(kind, 10.0) and (best is None or d < best[1]):
            best = (key, d)
    return best[0] if best else None


# -- the constraints of a copy ------------------------------------------------------------------
# The copies are exact copies of the picked curves, placed by the pattern. They keep the
# shape the originals have, the way FreeCAD's own array does with its "clone" option:
#   * the constraints among the picked curves that still hold where the copy is are copied
#     (corners joined, tangent, parallel, perpendicular, equal, a point on a curve,
#     symmetric; level and upright only for a rectangular pattern, where nothing turns);
#   * a size dimension of an original (a radius, a diameter, a line's length) becomes Equal
#     between the original and each copy, a line's angle dimension Parallel (rectangular
#     only): change the original's dimension and every copy follows, and no dimension is
#     shown twice;
#   * other dimensions (between two curves) and anything tied to curves that were not
#     picked are left out: the copy is free there.
# Every copy constraint stands for one constraint of the original, so none is redundant.
SAME_EVERYWHERE = (
    "Coincident",
    "Tangent",
    "Perpendicular",
    "Parallel",
    "Equal",
    "PointOnObject",
    "Symmetric",
)
LEVEL = ("Horizontal", "Vertical")
SIZES = ("Radius", "Diameter")


def _mapped(geo, mapping):
    if geo == GEO_UNDEF:
        return GEO_UNDEF
    return mapping.get(geo)


def _args(kind, first, first_pos, second, second_pos, third, third_pos):
    """The arguments of Sketcher.Constraint for a non-dimensional constraint, or None when
    this form is not one Fission 180 copies."""
    one, two, three = first != GEO_UNDEF, second != GEO_UNDEF, third != GEO_UNDEF
    if kind == "Coincident":
        return (first, first_pos, second, second_pos) if one and two else None
    if kind in ("Tangent", "Perpendicular"):
        if three or not (one and two):
            return None  # via a point: not copied
        if first_pos == 0 and second_pos == 0:
            return (first, second)
        if second_pos == 0:
            return (first, first_pos, second)
        return (first, first_pos, second, second_pos)
    if kind in ("Parallel", "Equal"):
        return (first, second) if one and two else None
    if kind == "PointOnObject":
        return (first, first_pos, second) if one and two else None
    if kind in LEVEL:
        if one and not two:
            return (first,)
        if one and two:
            return (first, first_pos, second, second_pos)
        return None
    if kind == "Symmetric":
        if not (one and two and three):
            return None
        if third_pos == 0:
            return (first, first_pos, second, second_pos, third)
        return (first, first_pos, second, second_pos, third, third_pos)
    return None


def copied_constraints(constraints, mapping, turns=False):
    """(copied, ties) for one copy. constraints: [(type, first, first_pos, second, second_pos,
    third, third_pos, curve_type_of_first)] of the sketch; mapping {original: copy} of the
    picked curves. copied: [(type, args)] among the copy's curves; ties: [(type, (original,
    copy))] to the originals. turns: a circular pattern (level/upright and angles do not
    hold where the copy is turned)."""
    copied, ties, tied = [], [], set()
    for item in constraints:
        kind, first, first_pos, second, second_pos, third, third_pos = item[:7]
        curve = item[7] if len(item) > 7 else ""
        refs = [g for g in (first, second, third) if g != GEO_UNDEF]
        if not refs or any(g not in mapping for g in refs):
            continue  # tied to something that is not copied (an axis, another curve)
        if kind in SAME_EVERYWHERE or (kind in LEVEL and not turns):
            args = _args(kind, first, first_pos, second, second_pos, third, third_pos)
            if args is None:
                continue
            out = []
            for i, a in enumerate(args):
                geo_slot = _is_geo_slot(kind, len(args), i)
                out.append(_mapped(a, mapping) if geo_slot else a)
            copied.append((kind, tuple(out)))
            continue
        single = second == GEO_UNDEF and third == GEO_UNDEF
        if not single:
            continue
        tie = None
        if kind in SIZES:
            tie = "Equal"
        elif kind == "Distance" and first_pos == 0 and curve == "Part::GeomLineSegment":
            tie = "Equal"  # a line's length
        elif kind == "Angle" and first_pos == 0 and not turns:
            tie = "Parallel"  # a line's angle to the sketch's X
        if tie is not None and (tie, first) not in tied:
            tied.add((tie, first))
            ties.append((tie, (first, mapping[first])))
    return copied, ties


def _is_geo_slot(kind, count, index):
    """Is argument `index` of a constraint's argument tuple a curve (not a point position)?"""
    if kind in ("Parallel", "Equal"):
        return True
    if kind in ("Tangent", "Perpendicular"):
        if count == 2:
            return True
        if count == 3:
            return index in (0, 2)
        return index in (0, 2)
    if kind == "Coincident":
        return index in (0, 2)
    if kind == "PointOnObject":
        return index in (0, 2)
    if kind in LEVEL:
        return index == 0 if count == 1 else index in (0, 2)
    if kind == "Symmetric":
        return index in (0, 2, 4)
    return False


# -- tying the copies to the originals ---------------------------------------------------------
# Fusion's sketch pattern keeps its copies where the pattern puts them: they follow the
# original and the sketch stays fully constrained (the book parity report: Fission 180's
# copies were only Equal to the original, 25 to 79 loose degrees of freedom, they drifted by
# micrometres and later dimensions did not move them). FreeCAD has no pattern constraint;
# each copy is tied point by point (sketch_pattern_ties.py):
#   a line by its two ends, a circle by its centre and Equal, an arc by its two ends and
#   Equal, a point by itself;
#   points the originals share (a Coincident between picked curves) are tied once: the
#   copies get that Coincident too, and one of the joined points carries the tie.
LINE, CIRCLE, ARC, POINT = (
    "Part::GeomLineSegment",
    "Part::GeomCircle",
    "Part::GeomArcOfCircle",
    "Part::GeomPoint",
)
TIED_TYPES = (LINE, CIRCLE, ARC, POINT)


def tie_points(kind):
    """((pos, ...), equal) for a curve of that type: the points that carry its ties and
    whether it also needs Equal with its copy."""
    if kind == LINE:
        return (1, 2), False
    if kind == CIRCLE:
        return (3,), True
    if kind == ARC:
        return (1, 2), True
    if kind == POINT:
        return (1,), False
    return (), False


def tie_plan(types, coincidents):
    """What ties a copy of the picked curves: (points, equals, joins).
    types {geo: TypeId} of the picked curves that can be tied; coincidents [(g1, p1, g2, p2)]
    the point-to-point Coincidents among them. points: the (geo, pos) to tie to the original
    (one per group of joined points); equals: the curves that need Equal with their copy;
    joins: the coincidents to repeat among the copy's curves."""
    parent = {}

    def find(x):
        parent.setdefault(x, x)
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    order = []
    equals = []
    for geo in types:
        positions, equal = tie_points(types[geo])
        for pos in positions:
            order.append((geo, pos))
            find((geo, pos))
        if equal:
            equals.append(geo)
    joins = []
    for g1, p1, g2, p2 in coincidents:
        if g1 not in types or g2 not in types or p1 == 0 or p2 == 0:
            continue
        joins.append((g1, p1, g2, p2))
        a, b = (g1, p1), (g2, p2)
        if a in parent and b in parent:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[rb] = ra
    seen = set()
    points = []
    for point in order:
        root = find(point)
        if root in seen:
            continue
        seen.add(root)
        points.append(point)
    return points, equals, joins


def wrap_turn(degrees):
    """A turn as the angle FreeCAD's Angle constraint takes: radians in (-pi, pi]."""
    d = (float(degrees) + 180.0) % 360.0 - 180.0
    if d <= -180.0 + 1e-12:
        d = 180.0
    return math.radians(d)


def nearest_copy(point, copies, tolerance):
    """The index of the copy (a list of polylines each) nearest to `point` within
    `tolerance`, or None: the instance a Suppression click means."""
    best = None
    for index, polylines in enumerate(copies):
        for poly in polylines:
            for a, b in zip(poly, poly[1:]):
                d = segment_distance(point, a, b)
                if d <= tolerance and (best is None or d < best[0]):
                    best = (d, index)
            if len(poly) == 1:
                d = math.hypot(poly[0][0] - point[0], poly[0][1] - point[1])
                if d <= tolerance and (best is None or d < best[0]):
                    best = (d, index)
    return best[1] if best else None
