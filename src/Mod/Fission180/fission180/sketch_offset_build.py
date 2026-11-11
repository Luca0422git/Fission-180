# SPDX-License-Identifier: LGPL-2.1-or-later
"""Puts an offset into the sketch (FreeCAD App only, no GUI).

The offset curves come from sketch_offset_core (sharp corners). They stay tied to the
curves they were made from, so the offset distance can be changed afterwards, as in
Fusion (Autodesk: after OK the offset curves, an offset dimension and an offset constraint
appear; editing the dimension moves the offset):

- an offset line is Parallel to its original, an offset arc or circle shares its centre;
- the distance: short construction lines square to the originals, as long as the offset
  (FreeCAD's own sketch offset uses such lines too), all Equal to the first, whose length
  is the one offset dimension shown. Changing it moves the whole offset at once (the
  solver does it; no recompute needed);
- neighbouring offset curves meet at their corners; where the originals run smoothly into
  each other (a slot, rounded corners) both offset curves end on the square line there;
- an open chain's two ends stay square to the original's ends.

So the offset is fully defined by its originals and the one dimension. Only the dimension
is shown: the other constraints are put in FreeCAD's "virtual space" (they work, unseen;
Fusion shows an offset as one glyph and one dimension). A constraint the solver still finds
redundant is left out (one by one, so the others stay).
"""

import math

import FreeCAD as App

from . import log
from . import sketch_offset_core as core

LINE_T = "Part::GeomLineSegment"
ARC_T = "Part::GeomArcOfCircle"
CIRCLE_T = "Part::GeomCircle"
KINDS = (LINE_T, ARC_T, CIRCLE_T)


def _v(p):
    return App.Vector(p[0], p[1], 0)


def _xy(v):
    return (v.x, v.y)


def curve_of(geometry):
    """A sketch curve as sketch_offset_core's tuple, or None (not a line, arc or circle)."""
    kind = geometry.TypeId
    if kind == LINE_T:
        return (core.LINE, _xy(geometry.StartPoint), _xy(geometry.EndPoint))
    if kind == ARC_T:
        c = geometry.Center
        s, e = geometry.StartPoint, geometry.EndPoint
        a1 = math.atan2(s.y - c.y, s.x - c.x)
        a2 = math.atan2(e.y - c.y, e.x - c.x)
        while a2 <= a1:
            a2 += 2 * math.pi
        return (core.ARC, _xy(c), geometry.Radius, a1, a2)
    if kind == CIRCLE_T:
        return (core.CIRCLE, _xy(geometry.Center), geometry.Radius)
    return None


def part_geometry(curve):
    """The Part geometry of a core curve."""
    import Part

    kind = curve[0]
    if kind == core.LINE:
        return Part.LineSegment(_v(curve[1]), _v(curve[2]))
    circle = Part.Circle(_v(curve[1]), App.Vector(0, 0, 1), curve[2])
    if kind == core.ARC:
        return Part.ArcOfCircle(circle, curve[3], curve[4])
    return circle


def _start_pos(rev):
    """The sketch's point position (1 start, 2 end) where an item starts along its chain."""
    return 2 if rev else 1


def _end_pos(rev):
    return 1 if rev else 2


def _foot(original, rev, moved, at_end=False):
    """Where the square from the original's travel start (end) meets the moved curve."""
    start, end = core.travel_ends(original, rev)
    p = end if at_end else start
    if original[0] == core.LINE:
        u = core._unit(core._sub(original[2], original[1]))
        n = core._right(u)
        t = core._dot(core._sub(moved[1], p), n)
        return core._add(p, core._mul(n, t))
    c, r = moved[1], moved[2]
    return core._polar(c, r, core._angle(c, p))


def add_offset(sketch, chains, curves, results, distance, construction=False):
    """Add the offset curves and their constraints. chains: sketch_offset_core chains of
    the picked sketch curves (their keys are geometry indices, projected ones negative);
    curves: {geo: core curve}; results: [(chain, [offset curves in the chain's order])];
    distance: the offset (> 0). Returns {"curves": new curve ids, "helpers": construction
    line ids, "dimension": the dimension's index or None, "dropped": constraints left out}.

    What ties what (an offset line has three unknowns once it is parallel: how far, where
    it starts, where it ends; an arc: its radius and two angles):
    - a corner: the two offset curves meet (Coincident);
    - a smooth joint (the originals run tangentially into each other): a square line at
      the original joint, as long as the offset; the next curve starts at its end, the
      curve before ends on it (a coincidence at a tangent point is a double root: the
      solver would call it redundant);
    - a curve that starts at a corner, or a chain's first curve: a square line at its
      start, as long as the offset, ending on it (on its start, for an open chain);
    - an open chain's last end: a square line from the original's end to the offset's end;
    - a lone circle: a level line from the circle to its offset, square to both."""
    import Part
    import Sketcher

    new_curves = []
    helpers = []
    plans = []
    for chain, moved in results:
        ids = [sketch.addGeometry(part_geometry(c), bool(construction)) for c in moved]
        new_curves += ids
        plans.append((chain, ids, moved))

    joints, relations, ties, pins, equals = [], [], [], [], []
    state = {"leader": None}

    def helper(a, b):
        h = sketch.addGeometry(Part.LineSegment(_v(a), _v(b)), True)
        helpers.append(h)
        return h

    def sized(h):
        """A square line as long as the offset (the first one carries the dimension)."""
        if state["leader"] is None:
            state["leader"] = h
        else:
            equals.append(Sketcher.Constraint("Equal", state["leader"], h))

    for chain, ids, moved in plans:
        items = chain.items
        n = len(items)
        originals = [curves[k] for k, _r in items]
        for i, (key, _rev) in enumerate(items):
            if originals[i][0] == core.LINE:
                relations.append(Sketcher.Constraint("Parallel", key, ids[i]))
            else:
                relations.append(Sketcher.Constraint("Coincident", key, 3, ids[i], 3))
        if n == 1 and originals[0][0] == core.CIRCLE:
            key = items[0][0]
            c, r = originals[0][1], originals[0][2]
            h = helper((c[0] + r, c[1]), (c[0] + moved[0][2], c[1]))
            ties += [
                Sketcher.Constraint("PointOnObject", h, 1, key),
                Sketcher.Constraint("PointOnObject", h, 2, ids[0]),
                Sketcher.Constraint("Perpendicular", h, key),
                Sketcher.Constraint("Horizontal", h),
            ]
            sized(h)
            continue
        count = n if chain.closed else n - 1
        smooth_start = [False] * n  # item i starts at a smooth joint
        for i in range(count):
            j = (i + 1) % n
            (key_i, r_i), r_j = items[i], items[j][1]
            if chain.smooth[i]:
                smooth_start[j] = True
                corner = core.travel_ends(originals[i], r_i)[1]
                foot = core.travel_ends(moved[j], r_j)[0]
                h = helper(corner, foot)
                ties += [
                    Sketcher.Constraint("Coincident", h, 1, key_i, _end_pos(r_i)),
                    Sketcher.Constraint("Perpendicular", h, key_i),
                    Sketcher.Constraint("Coincident", h, 2, ids[j], _start_pos(r_j)),
                    Sketcher.Constraint("PointOnObject", ids[i], _end_pos(r_i), h),
                ]
                sized(h)
            else:
                joints.append(
                    Sketcher.Constraint(
                        "Coincident", ids[i], _end_pos(r_i), ids[j], _start_pos(r_j)
                    )
                )
        for i in range(n):
            if smooth_start[i]:
                continue
            key, rev = items[i]
            start = core.travel_ends(originals[i], rev)[0]
            h = helper(start, _foot(originals[i], rev, moved[i]))
            ties += [
                Sketcher.Constraint("Coincident", h, 1, key, _start_pos(rev)),
                Sketcher.Constraint("Perpendicular", h, key),
            ]
            if not chain.closed and i == 0:
                ties.append(Sketcher.Constraint("Coincident", h, 2, ids[i], _start_pos(rev)))
            else:
                ties.append(Sketcher.Constraint("PointOnObject", h, 2, ids[i]))
            sized(h)
        if not chain.closed:
            key, rev = items[n - 1]
            end = core.travel_ends(originals[n - 1], rev)[1]
            h = helper(end, _foot(originals[n - 1], rev, moved[n - 1], at_end=True))
            pins += [
                Sketcher.Constraint("Coincident", h, 1, key, _end_pos(rev)),
                Sketcher.Constraint("Coincident", h, 2, ids[n - 1], _end_pos(rev)),
                Sketcher.Constraint("Perpendicular", h, key),
            ]

    leader = state["leader"]
    dimension = None
    ordered = joints + relations + ties + pins + equals
    if leader is not None:
        ordered.append(Sketcher.Constraint("Distance", leader, float(distance)))
    blocked = _blocked(sketch, [k for chain in chains for k in chain.keys()])
    if blocked:
        ordered = _absolute(sketch, ordered, blocked)
    first_constraint = len(sketch.Constraints)
    dropped = add_clean(sketch, ordered)
    added = list(range(first_constraint, len(sketch.Constraints)))
    if leader is not None and added:
        last = sketch.Constraints[added[-1]]
        if last.Type == "Distance" and last.First == leader:
            dimension = added[-1]
    hidden = [i for i in added if i != dimension]
    if hidden:
        try:
            # Fusion shows an offset as one dimension: the rest work unseen
            sketch.setVirtualSpace(hidden, True)
        except Exception:
            pass
    if dimension is not None:
        try:
            # its value just beyond the offset, along the square line (not in the gap)
            sketch.setLabelDistance(dimension, 0.0)
            sketch.setLabelPosition(dimension, distance / 2.0 + max(2.0, 0.5 * distance))
        except Exception:
            pass
    try:
        # the square lines work unseen (wave 7, the book parity report: "besides the offset
        # lines it adds short connector lines"; Fusion's offset shows the parallel curve only)
        from . import sketch_helpers

        sketch_helpers.hide(sketch, helpers)
    except Exception as exc:
        log("Offset: the helper lines stay visible (%s)" % exc)
    return {
        "curves": new_curves,
        "helpers": helpers,
        "dimension": dimension,
        "dropped": dropped,
    }


def _blocked(sketch, keys):
    """The picked curves that are fixed with FreeCAD's Block (Fission 180's Fix/Unfix)."""
    wanted = {k for k in keys if k >= 0}
    return {c.First for c in sketch.Constraints if c.Type == "Block" and c.First in wanted}


def _point(sketch, geo, pos):
    g = sketch.Geometry[geo]
    if pos == 3:
        return g.Center
    return g.StartPoint if pos == 1 else g.EndPoint


def _at(geo, pos, point):
    """Constraints that hold point `pos` of `geo` where `point` is (from the sketch origin;
    a zero coordinate: on the axis)."""
    import Sketcher

    out = []
    for value, kind, axis in ((point.x, "DistanceX", -2), (point.y, "DistanceY", -1)):
        if abs(value) < 1e-9:
            out.append(Sketcher.Constraint("PointOnObject", geo, pos, axis))
        else:
            out.append(Sketcher.Constraint(kind, -1, 1, geo, pos, value))
    return out


def _angle_of(g):
    d = g.EndPoint - g.StartPoint
    return math.atan2(d.y, d.x)


def _absolute(sketch, constraints, blocked):
    """The constraints with every mention of a fixed (blocked) original replaced by where that
    original is: FreeCAD 1.1.4 calls a sketch over-constrained when a constraint names a
    blocked curve (whichever comes first, the Block or the constraint; checked), and a fixed
    curve cannot move anyway. A parallel line gets the original's angle, a shared centre or
    a point on the original its position, a square line its angle."""
    import Sketcher

    out = []
    for c in constraints:
        first, second = c.First, c.Second
        if first not in blocked and second not in blocked:
            out.append(c)
            continue
        kind = c.Type
        if kind == "Parallel":  # Parallel(original, offset line)
            out.append(Sketcher.Constraint("Angle", second, _angle_of(sketch.Geometry[first])))
        elif kind == "Coincident" and first in blocked:  # (original, 3, offset, 3)
            out += _at(second, c.SecondPos, _point(sketch, first, c.FirstPos))
        elif kind == "Coincident":  # (square line, 1, original, pos)
            out += _at(first, c.FirstPos, _point(sketch, second, c.SecondPos))
        elif kind == "Perpendicular":  # (square line, original): its angle now
            out.append(Sketcher.Constraint("Angle", first, _angle_of(sketch.Geometry[first])))
        elif kind == "PointOnObject":  # (square line, 1, circle): the point where it is
            out += _at(first, c.FirstPos, _point(sketch, first, c.FirstPos))
        else:
            out.append(c)
    return out


def _bad(sketch):
    return set(sketch.RedundantConstraints) | set(sketch.ConflictingConstraints)


def add_clean(sketch, constraints):
    """Add the constraints; those the solver finds redundant or conflicting are left out, the
    others kept (all at once first: one solve). Returns the types left out. A sketch that
    was not clean before (the user's own redundant constraints) is judged against itself:
    only what the new constraints add counts."""
    if not constraints:
        return []
    failed_before = sketch.solve() == -1
    before = _bad(sketch)

    def clean(code):
        if code == -1 and not failed_before:
            return False  # the solver found no solution
        return _bad(sketch) <= before

    first = len(sketch.Constraints)
    sketch.addConstraint(constraints)
    if clean(sketch.solve()):
        return []
    # one by one, in the order given (the corners first): each kept when the sketch stays clean
    sketch.delConstraints(list(range(first, len(sketch.Constraints))), True, True)
    sketch.solve()
    dropped = []
    for c in constraints:
        index = sketch.addConstraint(c)
        if not clean(sketch.solve()):
            sketch.delConstraint(index)
            sketch.solve()
            dropped.append(c.Type)
    if dropped:
        log("Offset: left out (already given by the others): %s" % ", ".join(dropped))
    return dropped
