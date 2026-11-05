# SPDX-License-Identifier: LGPL-2.1-or-later
"""A spline being drawn with FreeCAD's spline tool is never lost and never leaves its
points behind (Luca, 2026-11-04, after patch 0.1.0-beta.3.3.1: "the spline still
disapears when i click the checkmark. AND the orange dots are still there").

FreeCAD's spline tool (Fusion's Fit Point / Control Point Spline) puts a construction point
(fit point) or a construction circle (control point) in the sketch at each click and makes
the spline only when it is told to finish (Esc or its right click: rightButtonOrEsc). Until
then those points are loose: nothing ties them to a curve. Fission 180 finishes it for the
green check, OK, Enter and Finish Sketch by handing FreeCAD an Esc. Whether that worked is
now checked: when no new spline came of it, Fission 180 makes the spline from the loose
points itself (plan, build), with the ends joined where they were clicked. And when the
spline is cancelled (Esc, another tool), its loose points go (remove_points).

Which points are the spline's: the construction points / circles added since the spline's
first click (`start`, the sketch's curve count then) that nothing aligns to a curve yet
(no InternalAlignment, and not a three-point spline's middle point: on_a_spline), in the
order they were clicked. Without that count (the first click
was not seen) only FreeCAD's control-point signature is trusted: a run of loose
construction circles at the end of the sketch, the first with a Weight constraint and the
others Equal to it (FreeCAD's tool makes them so), never a user's own construction points.

Pure functions first (no FreeCAD: unit tested), then the parts that change the sketch.
"""

from . import log, warn

POINT, CIRCLE = "Part::GeomPoint", "Part::GeomCircle"
BSPLINE = "Part::GeomBSplineCurve"
START, END, MID = 1, 2, 3  # FreeCAD's PointPos


# -- which curves are the spline's -----------------------------------------------------------
def pending(geometry, aligned, start=None, constraints=()):
    """The indices of the spline's loose points, in click order.

    geometry     [(TypeId, construction)] of the sketch's curves
    aligned      the indices some InternalAlignment ties to a curve
    start        the sketch's curve count at the spline's first click, or None
    constraints  [(type, first, first_pos, second, second_pos)] (for the signature check)
    """
    if start is not None:
        held = aligned | on_a_spline(geometry, constraints)
        out = []
        for i in range(max(0, start), len(geometry)):
            kind, construction = geometry[i]
            if construction and kind in (POINT, CIRCLE) and i not in held:
                out.append(i)
        return out
    # no first click seen: only FreeCAD's control circles (Weight on the first, Equal to it)
    run = []
    for i in range(len(geometry) - 1, -1, -1):
        kind, construction = geometry[i]
        if kind != CIRCLE or not construction or i in aligned:
            break
        run.append(i)
    run.reverse()
    if not run:
        return []
    first = run[0]
    weighted = any(c[0] == "Weight" and c[1] == first for c in constraints)
    equal = {c[3] for c in constraints if c[0] == "Equal" and c[1] == first}
    equal |= {c[1] for c in constraints if c[0] == "Equal" and c[3] == first}
    if not weighted or any(i not in equal for i in run[1:]):
        return []
    return run


def on_a_spline(geometry, constraints):
    """Construction points a spline holds without an InternalAlignment: with exactly three
    fit points FreeCAD's tool ties the middle one to the curve with PointOnObject (the
    curve it makes has no knot there). It is the spline's own fit point, not a loose one."""
    out = set()
    for kind_c, first, _fpos, second, _spos in constraints:
        if kind_c != "PointOnObject" or not (0 <= first < len(geometry)) or not (0 <= second < len(geometry)):
            continue
        if geometry[first][0] == POINT and geometry[second][0] == BSPLINE:
            out.add(first)
    return out


def kind_of(geometry, points):
    """"fit" (fit points: construction points), "poles" (control circles), or None (mixed
    or nothing)."""
    kinds = {geometry[i][0] for i in points}
    if kinds == {POINT}:
        return "fit"
    if kinds == {CIRCLE}:
        return "poles"
    return None


def end_joins(constraints, points, kind):
    """How the spline's first and last clicked points were joined to other curves (FreeCAD
    puts those on the points when they are clicked on an end, a middle or a curve):
    [(end, type, other, other_pos)] with end START or END of the new spline, type
    "Coincident" or "PointOnObject" (other_pos 0 then: on the curve). Joins between the
    spline's own points and on the points in between are dropped (they are not needed for
    a curve through or along them)."""
    if not points:
        return []
    own = set(points)
    pos = START if kind == "fit" else MID
    ends = [(points[0], START)]
    if len(points) > 1:
        ends.append((points[-1], END))
    out = []
    for geo, end in ends:
        for kind_c, first, fpos, second, spos in constraints:
            if kind_c == "Coincident":
                if first == geo and fpos == pos and second not in own:
                    out.append((end, "Coincident", second, spos))
                elif second == geo and spos == pos and first not in own:
                    out.append((end, "Coincident", first, fpos))
            elif kind_c == "PointOnObject":
                if first == geo and fpos == pos and second not in own:
                    out.append((end, "PointOnObject", second, 0))
    return out


def degree_for(count):
    """FreeCAD's spline tool: degree 3, lower for fewer control points."""
    return max(1, min(3, count - 1))


# -- in a sketch -----------------------------------------------------------------------------
def describe(sketch):
    """(geometry, aligned, constraints) of a sketch for the functions above."""
    geometry = []
    for i, g in enumerate(sketch.Geometry):
        try:
            geometry.append((g.TypeId, bool(sketch.getConstruction(i))))
        except Exception:
            geometry.append((g.TypeId, False))
    aligned, constraints = set(), []
    for c in sketch.Constraints:
        try:
            if c.Type == "InternalAlignment":
                aligned.add(c.First)
            constraints.append((c.Type, c.First, int(c.FirstPos), c.Second, int(c.SecondPos)))
        except Exception:
            continue
    return geometry, aligned, constraints


def points_of(sketch, start=None):
    """The spline's loose points in the sketch now (see pending)."""
    geometry, aligned, constraints = describe(sketch)
    return pending(geometry, aligned, start, constraints)


def plan(sketch, points):
    """What the spline from these loose points is: {"kind", "where" (the points' places, in
    click order), "joins" (end_joins)}, or None. Read before FreeCAD's tool is stopped
    (stopping it may take its points away)."""
    import FreeCAD as App

    geometry, _aligned, constraints = describe(sketch)
    kind = kind_of(geometry, points)
    if kind is None or len(points) < 2:
        return None
    if kind == "fit":
        where = [App.Vector(sketch.Geometry[i].X, sketch.Geometry[i].Y, 0) for i in points]
    else:
        where = [App.Vector(sketch.Geometry[i].Center) for i in points]
    joins = end_joins(constraints, points, kind)
    # the curves the ends are joined to, by what they are (their index may move)
    keyed = []
    for end, kind_c, other, other_pos in joins:
        keyed.append((end, kind_c, other, other_pos, _key(sketch, other)))
    return {"kind": kind, "where": where, "joins": keyed, "count": len(sketch.Geometry)}


def _key(sketch, geo):
    try:
        if geo < 0:
            return ("external", geo)
        g = sketch.Geometry[geo]
        return (g.TypeId, round(g.StartPoint.x, 9), round(g.StartPoint.y, 9)) if hasattr(
            g, "StartPoint"
        ) else (g.TypeId,)
    except Exception:
        return None


def _find(sketch, geo, key, removed):
    """Where a joined curve is now (the spline's points before it went: one down each)."""
    if geo < 0:
        return geo
    guess = geo - sum(1 for r in removed if r < geo)
    if 0 <= guess < len(sketch.Geometry) and _key(sketch, guess) == key:
        return guess
    if 0 <= geo < len(sketch.Geometry) and _key(sketch, geo) == key:
        return geo
    return None


def build(sketch, made, remove=(), construction=False):
    """Make the spline of plan() `made`, taking the loose points in `remove` away first;
    the ends are joined where they were clicked. Runs inside the caller's undo step.
    Returns the new spline's index, or None."""
    import Part
    import Sketcher

    if not made:
        return None
    where = made["where"]
    curve = Part.BSplineCurve()
    if made["kind"] == "fit":
        curve.interpolate(where)
    else:
        curve.buildFromPoles(where, False, degree_for(len(where)))
    gone = sorted(remove)
    if gone:
        sketch.delGeometries(gone)
    new = sketch.addGeometry(curve, bool(construction))
    added = []
    for end, kind_c, other, other_pos, key in made["joins"]:
        at = _find(sketch, other, key, gone)
        if at is None or at == new:
            continue
        try:
            if kind_c == "Coincident":
                added.append(Sketcher.Constraint("Coincident", new, end, at, other_pos))
            else:
                added.append(Sketcher.Constraint("PointOnObject", new, end, at))
        except Exception as exc:
            warn("spline: join of an end not kept: %s" % exc)
    if added:
        sketch.addConstraint(added)
    try:
        sketch.exposeInternalGeometry(new)
    except Exception as exc:
        warn("spline: control points not shown: %s" % exc)
    sketch.solve()
    log(
        "spline: made by Fission 180 from %d %s (FreeCAD's tool did not make it), %d end join(s)"
        % (len(where), "fit points" if made["kind"] == "fit" else "control points", len(added))
    )
    return new


def remove_points(sketch, points):
    """A cancelled spline's loose points go (Fusion leaves nothing behind)."""
    if not points:
        return 0
    sketch.delGeometries(sorted(points))
    sketch.solve()
    log("spline: %d loose point(s) of a cancelled spline removed" % len(points))
    return len(points)
