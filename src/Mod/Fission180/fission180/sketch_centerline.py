# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's third sketch line type: Centerline (Sketch Palette > Linetype).

Fusion (Autodesk help "Sketches in Fusion", forum "Make a diameter-dimension in a sketch",
"Very basic Revolve questions"): a line can be Normal, Construction or Centerline. A
centerline is drawn dashed; it still bounds profiles like a normal line (the half
profile of a turned part is closed by its centerline); a dimension between a centerline
and a point or line is the DIAMETER (twice the distance: the size across the turned part);
Revolve takes a profile sketch's one centerline as its axis by itself.

FreeCAD's sketch knows normal and construction curves only. Here a centerline is a normal
line (so profiles close as before) whose geometry id is listed in a hidden property of the
sketch (kept in the file), drawn dashed on FreeCAD's "discontinuous" visual layer.

The diameter: FreeCAD's solver has no "twice the distance". A dimension placed between a
point (or a line) and a centerline is replaced by a mirror image of that point across the
centerline (a hidden construction point held by a Symmetric constraint) and a Distance
between the point and its image: its value is the diameter, it is drawn across the
centerline, and typing a value into it sets the diameter.

No Qt here (the palette and the dimension hook are in sketch_palette.py / sketch_mode.py).
Every function works inside the caller's undo step.
"""

from . import log, warn

PROPERTY = "Fission180Centerlines"
LINE = "Part::GeomLineSegment"
NORMAL_LAYER, DASHED_LAYER = 0, 1
NO_GEO = -2000


# -- pure geometry (unit tested) ----------------------------------------------------------------
def mirror(point, a, b):
    """The mirror image of `point` across the line through a and b ((x, y) tuples)."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    length2 = dx * dx + dy * dy
    if length2 < 1e-18:
        return point
    t = ((point[0] - a[0]) * dx + (point[1] - a[1]) * dy) / length2
    foot = (a[0] + t * dx, a[1] + t * dy)
    return (2.0 * foot[0] - point[0], 2.0 * foot[1] - point[1])


def diameter_plan(kind, first, first_pos, second, second_pos, centerlines):
    """What a fresh dimension between something and a centerline becomes.

    Returns ((geo, pos) of the point to mirror, centerline geo), or None when the
    dimension is not a distance from a point or a line to a centerline. `centerlines`:
    the geometry indices of the sketch's centerlines. A point-to-line Distance has the
    point first and the line second (no point position); a line-to-line one names two
    lines: the start of the one that is no centerline is mirrored."""
    if kind != "Distance":
        return None
    centerlines = set(centerlines)
    if second in (NO_GEO, None) or first == second:
        return None  # a line's length, a point-to-point distance on one curve
    if first_pos != 0 and second_pos == 0 and second in centerlines:
        return (first, first_pos), second
    if first_pos == 0 and second_pos != 0 and first in centerlines:
        return (second, second_pos), first
    if first_pos == 0 and second_pos == 0:
        if second in centerlines and first not in centerlines:
            return (first, 1), second
        if first in centerlines and second not in centerlines:
            return (second, 1), first
    return None


# -- the sketch's centerlines -----------------------------------------------------------------
def _stored(sketch):
    try:
        return [int(i) for i in (getattr(sketch, PROPERTY, ()) or ())]
    except Exception:
        return []


def _store(sketch, ids):
    if PROPERTY not in sketch.PropertiesList:
        sketch.addProperty(
            "App::PropertyIntegerList",
            PROPERTY,
            "Fission180",
            "Geometry ids of the sketch's centerlines (Linetype: Centerline)",
        )
        sketch.setEditorMode(PROPERTY, 2)
    setattr(sketch, PROPERTY, sorted(set(int(i) for i in ids)))


def _geometry_ids(sketch):
    try:
        return [int(f.Id) for f in sketch.GeometryFacadeList]
    except Exception:
        return []


def lines(sketch):
    """The geometry indices of the sketch's centerlines (lines that still exist)."""
    stored = set(_stored(sketch))
    if not stored:
        return []
    found = []
    geometry = sketch.Geometry
    for i, ident in enumerate(_geometry_ids(sketch)):
        if ident in stored and i < len(geometry) and geometry[i].TypeId == LINE:
            found.append(i)
    return found


def is_centerline(sketch, geo):
    return geo in lines(sketch)


def axis(sketch):
    """The sketch's centerline when it has exactly one (Revolve's axis by itself), as a
    geometry index; None otherwise."""
    found = lines(sketch)
    return found[0] if len(found) == 1 else None


def set_centerline(sketch, geos, on):
    """Make the lines `geos` centerlines (or normal lines again). Only lines can be; a
    construction line becomes a normal one first (a centerline bounds profiles). Returns
    the indices changed."""
    from . import sketch_draw_helpers

    ids = _geometry_ids(sketch)
    stored = set(_stored(sketch))
    geometry = sketch.Geometry
    changed = []
    for geo in geos:
        if geo < 0 or geo >= len(geometry) or geometry[geo].TypeId != LINE:
            continue
        ident = ids[geo]
        if on and ident not in stored:
            stored.add(ident)
            changed.append(geo)
        elif not on and ident in stored:
            stored.discard(ident)
            changed.append(geo)
    if not changed:
        return []
    _store(sketch, stored)
    if on:
        for geo in changed:
            try:
                if sketch.getConstruction(geo):
                    sketch.setConstruction(geo, False)
            except Exception as exc:
                warn("centerline: %s" % exc)
    sketch_draw_helpers.set_layer(sketch, changed, DASHED_LAYER if on else NORMAL_LAYER)
    log(
        "sketch: %d line(s) %s"
        % (len(changed), "are centerlines" if on else "are normal lines again")
    )
    return changed


# -- the diameter dimension -------------------------------------------------------------------
def diameter(sketch, index):
    """The dimension constraint `index`, just placed, is the distance from a point or a
    line to a centerline: replace it by the diameter (see the module's text). Returns the
    new dimension's index, or None when it is no such dimension (nothing changed)."""
    import FreeCAD as App
    import Part
    import Sketcher

    from . import sketch_draw_helpers

    centerlines = lines(sketch)
    if not centerlines:
        return None
    constraints = sketch.Constraints
    if index < 0 or index >= len(constraints):
        return None
    c = constraints[index]
    plan = diameter_plan(c.Type, c.First, c.FirstPos, c.Second, c.SecondPos, centerlines)
    if plan is None:
        return None
    (geo, pos), line = plan
    point = sketch.getPoint(geo, pos)
    axis_line = sketch.Geometry[line]
    a = (axis_line.StartPoint.x, axis_line.StartPoint.y)
    b = (axis_line.EndPoint.x, axis_line.EndPoint.y)
    image = mirror((point.x, point.y), a, b)
    distance = ((image[0] - point.x) ** 2 + (image[1] - point.y) ** 2) ** 0.5
    if distance < 1e-9:
        return None  # the point is on the centerline: no diameter to speak of
    sketch.delConstraint(index)
    helper = sketch.addGeometry(Part.Point(App.Vector(image[0], image[1], 0)), True)
    symmetric = sketch.addConstraint(Sketcher.Constraint("Symmetric", geo, pos, helper, 1, line))
    new = sketch.addConstraint(Sketcher.Constraint("Distance", geo, pos, helper, 1, distance))
    sketch_draw_helpers.hide_constraints(sketch, [symmetric])
    sketch_draw_helpers.hide_curves(sketch, [helper])
    log("sketch: a dimension to the centerline is the diameter (%.6g mm)" % distance)
    return new


def revolve_axis(profiles):
    """(sketch, "EdgeN") of the centerline Revolve takes as its axis by itself: the picked
    profiles all come from one sketch and that sketch has exactly one centerline. None
    otherwise. `profiles`: the picked profile references (their first item is the object)."""
    sketches = []
    for ref in profiles or ():
        obj = ref[0] if isinstance(ref, (tuple, list)) else getattr(ref, "obj", None)
        if obj is None or getattr(obj, "TypeId", "") != "Sketcher::SketchObject":
            return None
        if obj not in sketches:
            sketches.append(obj)
    if len(sketches) != 1:
        return None
    sketch = sketches[0]
    geo = axis(sketch)
    if geo is None:
        return None
    # the line's edge in the sketch's shape (its edges are numbered apart from the
    # sketch's curves: construction curves are not in it)
    try:
        line = sketch.Geometry[geo]
        place = sketch.Placement
        a, b = place.multVec(line.StartPoint), place.multVec(line.EndPoint)
        for n, edge in enumerate(sketch.Shape.Edges):
            ends = [v.Point for v in edge.Vertexes]
            if len(ends) != 2:
                continue
            if ((ends[0] - a).Length < 1e-6 and (ends[1] - b).Length < 1e-6) or (
                (ends[0] - b).Length < 1e-6 and (ends[1] - a).Length < 1e-6
            ):
                return sketch, "Edge%d" % (n + 1)
    except Exception as exc:
        warn("centerline: %s" % exc)
    return None
