# SPDX-License-Identifier: LGPL-2.1-or-later
"""A B-spline curve's definition as the AI tools read and write it.

Luca's NREAL AIR HMD benchmark (2026-11-23): there was no way to read a spline's definition
(get_sketch and query_geometry gave no control points or knots) and create_sketch only made
splines through points, so an imported spline wall's curves were recovered by sampling 76
points with construction points and measure, then fitting them offline. Now get_sketch and
query_geometry give a spline's definition, and create_sketch / add_to_sketch take one back
({"control_spline": ...}): the same curve, exactly.

    {"degree": 3, "control_points": [[x, y], ...], "knots": [...], "multiplicities": [...],
     "weights": [...] (only when they are not all 1), "periodic": false}

Without knots and multiplicities a control_spline is clamped (it starts on its first control
point and ends on its last) with evenly spaced knots, as Fusion's control point spline.
Needs FreeCAD (Part).
"""

MAX_POLES = 400  # (a bigger definition is summed up, not listed)
DIGITS = 9  # (a copy is exact to well below a micrometre)


class SplineError(ValueError):
    pass


def _r(value):
    return round(float(value), DIGITS)


def definition(curve, to_point=None):
    """The definition of a Part.BSplineCurve (a Bezier is made one first). to_point maps a
    3D point to the list written (a sketch's own [x, y]); else [x, y, z]. A curve of more than
    MAX_POLES control points gives only its degree and their number."""
    if type(curve).__name__ == "BezierCurve":
        curve = curve.toBSpline()
    poles = curve.getPoles()
    out = {"degree": int(curve.Degree), "periodic": bool(curve.isPeriodic())}
    if len(poles) > MAX_POLES:
        out["control_point_count"] = len(poles)
        out["note"] = "%d control points: too many to list" % len(poles)
        return out
    write = to_point or (lambda p: [_r(p.x), _r(p.y), _r(p.z)])
    out["control_points"] = [write(p) for p in poles]
    out["knots"] = [_r(k) for k in curve.getKnots()]
    out["multiplicities"] = [int(m) for m in curve.getMultiplicities()]
    weights = [float(w) for w in curve.getWeights()]
    if any(abs(w - 1.0) > 1e-12 for w in weights):
        out["weights"] = [_r(w) for w in weights]
    return out


def of_edge(edge, to_point=None):
    """The definition of the part of a B-spline edge's curve that the edge uses (an edge
    may use only a piece of its curve), or None for another kind of edge."""
    try:
        curve = edge.Curve
    except Exception:
        return None
    if type(curve).__name__ not in ("BSplineCurve", "BezierCurve"):
        return None
    if type(curve).__name__ == "BezierCurve":
        curve = curve.toBSpline()
    else:
        curve = curve.copy()
    first, last = edge.ParameterRange
    try:
        if first > curve.FirstParameter + 1e-12 or last < curve.LastParameter - 1e-12:
            curve.segment(first, last)
    except Exception:
        pass
    return definition(curve, to_point)


def build(spec, make_point):
    """The Part.BSplineCurve of a definition. make_point turns one control point (a list) into
    a FreeCAD vector. Raises SplineError with what is wrong."""
    import Part

    if not isinstance(spec, dict):
        raise SplineError("a control_spline is an object: {control_points, degree, ...}")
    points = spec.get("control_points")
    if not isinstance(points, list) or len(points) < 2:
        raise SplineError("control_spline: give at least 2 control_points")
    poles = [make_point(p) for p in points]
    periodic = bool(spec.get("periodic", False))
    degree = int(spec.get("degree", 3))
    if degree < 1:
        raise SplineError("control_spline: the degree must be 1 or more")
    knots = spec.get("knots")
    mults = spec.get("multiplicities")
    weights = spec.get("weights")
    if weights is not None and len(weights) != len(poles):
        raise SplineError(
            "control_spline: %d weights for %d control points" % (len(weights), len(poles))
        )
    curve = Part.BSplineCurve()
    if knots is None and mults is None:
        if periodic:
            raise SplineError("control_spline: a periodic spline needs its knots and multiplicities")
        degree = min(degree, len(poles) - 1)
        inner = len(poles) - degree - 1  # (clamped, evenly spaced)
        knots = [float(i) / (inner + 1) for i in range(inner + 2)]
        mults = [degree + 1] + [1] * inner + [degree + 1]
    elif knots is None or mults is None or len(knots) != len(mults):
        raise SplineError("control_spline: give knots and multiplicities together, one each")
    try:
        curve.buildFromPolesMultsKnots(
            poles,
            [int(m) for m in mults],
            [float(k) for k in knots],
            periodic,
            degree,
            [float(w) for w in weights] if weights is not None else None,
        )
    except Exception as exc:
        raise SplineError("control_spline: these do not make a spline (%s)" % exc)
    return curve
