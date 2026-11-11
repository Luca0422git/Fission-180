# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's "Scale entire sketch at first dimension" (Preferences > General > Design; wave 7,
sketch-c; the book parity report: "does not exist").

Fusion (Autodesk API: `isSketchScaledWithFirstDimension`, "the sketch geometry is
automatically scaled when the first dimension is added"; forum, "Tip: scaling SVG import to
precise dimensions"): a shape is drawn by eye, the first dimension is placed and a value
typed: everything in the sketch grows or shrinks by the same factor, so the proportions
drawn stay. Later dimensions change only what they measure.

Here: the value typed into the box of a dimension that Sketch Dimension has just placed
scales every curve of the sketch about the sketch's origin by new / old, when that dimension
is the sketch's first size (first_size, unit tested):
- it is a length, a radius or a diameter (an angle does not change with size);
- no other dimension of a size exists (angles do not count), driving or hidden;
- nothing in the sketch is fixed (Fix/Unfix) and nothing is projected: those cannot grow.
Every other constraint (coincident, parallel, tangent, equal, on the origin or an axis...)
holds as before after a scale about the origin, so the sketch solves to exactly the scaled
shape.

The default: on. Autodesk documents no default; the forum threads are from people surprised
by it ("No auto-fit after first dimension", "Dimension entry zoom out": the answer is to
untick this preference), a 2019 course switches it on by hand (parity/sketch.md).
"""

from . import log

PARAM = (
    "User parameter:BaseApp/Preferences/Mod/Fission180/SketchInference",
    "ScaleAtFirstDimension",
)
SIZES = ("Distance", "DistanceX", "DistanceY", "Radius", "Diameter")
# what cannot simply grow: a fixed curve, and a spline's control points (the circles FreeCAD
# draws round them carry the points' weights in their radius)
FIXED = ("Block", "Weight")
NO_GEO = -2000


def enabled():
    """Preferences > Design > "Scale entire sketch at first dimension"."""
    try:
        import FreeCAD as App

        return App.ParamGet(PARAM[0]).GetBool(PARAM[1], True)
    except Exception:
        return True


# -- pure rule (unit tested) ------------------------------------------------------------------
def first_size(index, constraints, projected, formulas=()):
    """True when dimension `index` is the sketch's first size and the whole sketch can be
    scaled with it. constraints: (Type, First, Second, Third) of every constraint;
    projected: how many projected curves the sketch has; formulas: indices of the
    constraints that follow a formula."""
    if index < 0 or index >= len(constraints):
        return False
    if constraints[index][0] not in SIZES or projected:
        return False
    if index in formulas:
        return False
    for i, (kind, first, second, third) in enumerate(constraints):
        if kind in FIXED:
            return False
        if i != index and kind in SIZES:
            return False
        if any(g != NO_GEO and g <= -3 for g in (first, second, third)):
            return False  # tied to something projected
    return True


def factor(old, new):
    """The scale that takes a size from `old` to `new` (mm), or None when there is none."""
    old, new = abs(float(old)), abs(float(new))
    if old <= 1e-9 or new <= 1e-9 or abs(new - old) <= 1e-9 * max(old, new):
        return None
    return new / old


# -- on a sketch ------------------------------------------------------------------------------
def applies(sketch, index):
    if not enabled():
        return False
    try:
        from . import sketch_named_dimensions

        triples = [
            (c.Type, c.First, c.Second, getattr(c, "Third", NO_GEO)) for c in sketch.Constraints
        ]
        projected = max(0, len(sketch.ExternalGeo) - 2)
        return first_size(index, triples, projected, set(sketch_named_dimensions.formulas(sketch)))
    except Exception:
        return False


def scale(sketch, k):
    """Scale every curve and point of the sketch about its origin by `k` (inside the
    caller's undo step). The curves keep their marks (construction, hidden layers, a
    spline's or an ellipse's helpers): only their geometry is replaced."""
    import FreeCAD as App
    import Sketcher

    origin = App.Vector(0, 0, 0)
    facades = list(sketch.GeometryFacadeList)
    for i, old in enumerate(facades):
        geo = old.Geometry.copy()
        geo.scale(origin, k)
        for ext in old.getExtensions():
            try:
                geo.setExtension(ext)
            except Exception:
                pass
        facades[i] = Sketcher.GeometryFacade(geo)
    sketch.GeometryFacadeList = facades
    # a dimension's text sits a distance (mm) off its curve: it keeps its place on the
    # screen's picture of the shape
    for i, c in enumerate(sketch.Constraints):
        try:
            if c.Type in SIZES and abs(c.LabelDistance) > 1e-9:
                sketch.setLabelDistance(i, c.LabelDistance * k)
        except Exception:
            pass
    log("sketch: the whole sketch scaled by %.6g at its first dimension" % k)
