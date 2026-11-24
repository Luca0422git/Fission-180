# SPDX-License-Identifier: LGPL-2.1-or-later
"""Model edges copied into a sketch as its own curves: Fusion's Project with Projection Link
off (the curves do not follow the model afterwards).

Luca's NREAL AIR HMD benchmark (2026-11-23): an imported spline wall's curves could only be
recovered by sampling points and fitting them offline ("copy edge as sketch curve" was one of
his fix ideas). Flattening onto the sketch's plane is an affine map, so a B-spline's flattened
control points (and weights) make the flattened curve exactly; lines stay lines, and circles
and arcs whose axis is the sketch's normal stay circles and arcs. Every other curve goes in as
its exact B-spline. Needs FreeCAD (Part).
"""


def _flat(point):
    import FreeCAD as App

    return App.Vector(point.x, point.y, 0.0)


def _curve(edge):
    """The sketch geometry of one edge already in the sketch's own coordinates, or None."""
    import FreeCAD as App
    import Part

    try:
        if edge.isDegenerated() if hasattr(edge, "isDegenerated") else edge.Length < 1e-12:
            return None
    except Exception:
        pass
    curve = edge.Curve
    name = type(curve).__name__
    first, last = edge.ParameterRange
    if name in ("Line", "LineSegment"):
        a, b = _flat(edge.valueAt(first)), _flat(edge.valueAt(last))
        if (b - a).Length < 1e-9:
            return None
        return Part.LineSegment(a, b)
    if name == "Circle" and abs(abs(curve.Axis.z) - 1.0) < 1e-9:
        circle = Part.Circle(_flat(curve.Center), App.Vector(0, 0, 1), curve.Radius)
        if edge.isClosed():
            return circle
        # (the arc's ends where the edge's are, counter-clockwise about +Z)
        start, end = _flat(edge.valueAt(first)), _flat(edge.valueAt(last))
        if curve.Axis.z < 0:
            start, end = end, start
        centre = circle.Center
        import math

        a0 = math.atan2(start.y - centre.y, start.x - centre.x)
        a1 = math.atan2(end.y - centre.y, end.x - centre.x)
        if a1 <= a0:
            a1 += 2 * math.pi
        return Part.ArcOfCircle(circle, a0, a1)
    # any other curve: its exact B-spline, flattened by its control points
    if name == "BSplineCurve":
        spline = curve.copy()
        try:
            if first > spline.FirstParameter + 1e-12 or last < spline.LastParameter - 1e-12:
                spline.segment(first, last)
        except Exception:
            pass
    elif name == "BezierCurve":
        spline = curve.toBSpline()
    else:
        spline = edge.toNurbs().Edges[0].Curve
    poles = [_flat(p) for p in spline.getPoles()]
    flat = Part.BSplineCurve()
    flat.buildFromPolesMultsKnots(
        poles,
        list(spline.getMultiplicities()),
        list(spline.getKnots()),
        bool(spline.isPeriodic()),
        int(spline.Degree),
        list(spline.getWeights()),
    )
    return flat


def copy_into(sketch, shapes):
    """Add the edges (and corners) of `shapes` (in design coordinates) to `sketch` as its own
    curves, flattened onto its plane. Returns the new geometry indexes."""
    import Part

    to_local = sketch.getGlobalPlacement().inverse().toMatrix()
    added = []
    for shape in shapes:
        local = shape.copy()
        local.transformShape(to_local, True)
        if local.ShapeType == "Vertex":
            p = _flat(local.Point)
            added.append(sketch.addGeometry(Part.Point(p)))
            continue
        for edge in local.Edges:
            geo = _curve(edge)
            if geo is not None:
                added.append(sketch.addGeometry(geo))
    return added
