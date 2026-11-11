# SPDX-License-Identifier: LGPL-2.1-or-later
"""What a sketch shows of the helper curves and constraints its shapes are built with.

FreeCAD builds an ellipse, a regular polygon and a spline from a main curve plus helpers
(an ellipse's axes and focus points; a polygon's circles and a spoke with a dozen Equal,
Point-on-object and Tangent constraints; a spline's control circles, each Equal to the
first) and draws all of them: a fresh hexagon came with two dashed circles, a dashed line
and a cloud of "= 14, 15, 16..." labels, a fit point spline with its control polygon and
"= 37, 39, 41..." (the book parity report, 2026-11-10: "FreeCAD shows through"). Fusion
shows the shape: a polygon's lines, a spline's curve with its fit points (a control point
spline with its control frame), an ellipse with its two axes as construction lines.

Nothing is taken out of the sketch (the solver needs every helper); two things FreeCAD
already has are used, both saved with the design:

- a constraint can live in the sketch's "virtual space": it works as before and is not
  drawn (`setVirtualSpace`). The helpers' constraints go there.
- a curve can be on the sketch's hidden visual layer (layer 2 of the three FreeCAD gives
  every sketch): it is solved as before, not drawn and not clickable. A polygon's corner
  circle and spoke (circumscribed: the circle that touches the edges stays, it is the size
  one dimensions and its centre is the polygon's centre) and a fit point spline's control
  circles go there. Fission 180's own snapping leaves hidden curves out too (hidden()).

An ellipse's two focus points are deleted (FreeCAD allows it: they are only shown); its
axes stay. The layer needs FreeCAD's window (SketcherGui); without it (the golden models,
the AI tools) only the constraints are tidied.

Every function changes the sketch inside the caller's undo step and never raises: a shape
that could not be tidied is drawn as FreeCAD draws it.
"""

from . import warn

HIDDEN_LAYER = 2
LAYER_EXTENSION = "ViewProviderSketchGeometryExtension"
POINT, CIRCLE, LINE = "Part::GeomPoint", "Part::GeomCircle", "Part::GeomLineSegment"
BSPLINE, ELLIPSE = "Part::GeomBSplineCurve", "Part::GeomEllipse"


# -- pure rules (no FreeCAD: unit tested) -----------------------------------------------------
NO_GEO = -2000  # FreeCAD's "no geometry" (GeoEnum::GeoUndef)


def polygon_parts(ids, sides, circumscribed):
    """(lines, curves to hide, curve to keep) of sketch_polygon.add_polygon's indices.

    Inscribed: the circle through the corners is the one the person drew: it stays.
    Circumscribed: the circle touching the edges (the last) stays; the corner circle and
    the spoke from the centre to the middle of an edge are hidden."""
    ids = list(ids)
    lines = ids[:sides]
    if circumscribed and len(ids) >= sides + 3:
        return lines, [ids[sides], ids[sides + 1]], ids[sides + 2]
    return lines, [], ids[sides] if len(ids) > sides else None


# -- reading --------------------------------------------------------------------------------
def _triples(sketch):
    out = []
    for c in sketch.Constraints:
        third = getattr(c, "Third", NO_GEO)
        out.append((c.Type, c.First, c.Second, third))
    return out


def layer_of(facade):
    """The visual layer of a curve's facade (0 when it has none yet)."""
    try:
        for ext in facade.getExtensions():
            layer = getattr(ext, "VisualLayerId", None)
            if layer is not None:
                return int(layer)
    except Exception:
        pass
    return 0


def hidden(sketch):
    """The geometry indices of the curves on the hidden layer (not drawn, not clickable):
    Fission 180's snapping and picking leave them out as well."""
    # (one answer for both kinds of unseen helpers since wave 7's merge: sketch_helpers)
    from . import sketch_helpers

    return sketch_helpers.hidden(sketch)


def aligned_to(sketch, main):
    """{role: [geometry index]} of the helper curves FreeCAD aligns to curve `main`
    (InternalAlignment): "EllipseFocus1", "BSplineControlPoint", "BSplineKnotPoint"..."""
    roles = {}
    try:
        helpers = {
            c.First
            for c in sketch.Constraints
            if c.Type == "InternalAlignment" and c.Second == main and c.First >= 0
        }
        if not helpers:
            return roles
        facades = sketch.GeometryFacadeList
        for i in sorted(helpers):
            role = str(getattr(facades[i], "InternalType", "") or "")
            roles.setdefault(role, []).append(i)
    except Exception as exc:
        warn("sketch helpers: %s" % exc)
    return roles


# -- changing ---------------------------------------------------------------------------------
def hide_constraints(sketch, indices):
    """Constraints into the sketch's virtual space (they keep working, they are not drawn)."""
    count = 0
    for i in indices:
        try:
            if not sketch.getVirtualSpace(i):
                sketch.setVirtualSpace(i, True)
                count += 1
        except Exception as exc:
            warn("sketch helpers: constraint %d not hidden: %s" % (i + 1, exc))
    return count


def hide_curves(sketch, indices):
    """Curves onto the hidden visual layer. False without FreeCAD's window."""
    return set_layer(sketch, indices, HIDDEN_LAYER)


def set_layer(sketch, indices, wanted):
    """Curves onto visual layer `wanted` (0 normal, 1 dashed, 2 hidden). False without
    FreeCAD's window."""
    indices = [i for i in indices if i is not None and i >= 0]
    if not indices:
        return True
    try:
        import Sketcher
        import SketcherGui
    except Exception:
        return False
    try:
        facades = list(sketch.GeometryFacadeList)
        changed = False
        for i in indices:
            old = facades[i]
            if layer_of(old) == wanted:
                continue
            new = old.Geometry.copy()
            for ext in old.getExtensions():
                try:
                    new.setExtension(ext)
                except Exception:
                    pass
            layer = SketcherGui.ViewProviderSketchGeometryExtension()
            layer.VisualLayerId = wanted
            new.setExtension(layer)
            facades[i] = Sketcher.GeometryFacade(new)
            changed = True
        if changed:
            sketch.GeometryFacadeList = facades
        return True
    except Exception as exc:
        warn("sketch helpers: curves not moved to layer %d: %s" % (wanted, exc))
        return False


def tidy_polygon(sketch, ids, sides, circumscribed, first_constraint):
    """A polygon just added (sketch_polygon.add_polygon, or FreeCAD's own inscribed one):
    its helper constraints are not drawn; a circumscribed one's corner circle and spoke
    are not drawn either. `first_constraint`: the sketch's constraint count before the
    polygon (only the polygon's own constraints are touched)."""
    try:
        lines, hide, _keep = polygon_parts(ids, sides, circumscribed)
        helpers = set(ids[sides:])
        triples = _triples(sketch)
        mine = []
        for i in range(first_constraint, len(triples)):
            kind, first, second, third = triples[i]
            named = {g for g in (first, second, third) if g != NO_GEO}
            if kind == "Equal" and named <= set(lines):
                mine.append(i)  # equal sides
            elif kind == "Coincident" and named <= set(lines):
                continue  # the corners: drawn as points anyway, FreeCAD shows no glyph
            elif named & helpers and named <= (helpers | set(lines)):
                mine.append(i)
        hide_constraints(sketch, mine)
        hide_curves(sketch, hide)
    except Exception as exc:
        warn("polygon helpers: %s" % exc)


def tidy_spline(sketch, spline, fit):
    """A spline just made. Its control circles' constraints (each Equal to the first, the
    first's Weight) are not drawn; a fit point spline's control circles are not drawn
    either (its fit points are). A control point spline keeps its circles: they are what
    one drags."""
    try:
        roles = aligned_to(sketch, spline)
        poles = roles.get("BSplineControlPoint", [])
        if not poles:
            return
        triples = _triples(sketch)
        mine = []
        pole_set = set(poles)
        for i, (kind, first, second, third) in enumerate(triples):
            named = {g for g in (first, second, third) if g != NO_GEO}
            if kind in ("Equal", "Weight") and named and named <= pole_set:
                mine.append(i)
        hide_constraints(sketch, mine)
        if fit:
            hide_curves(sketch, poles)
    except Exception as exc:
        warn("spline helpers: %s" % exc)


def tidy_ellipse(sketch, ellipse):
    """An ellipse just drawn: its two focus points go (its axes stay, as construction
    lines, like Fusion's). Returns (major axis line, minor axis line) or (None, None).
    The focus points are the last curves of a fresh ellipse: deleting them renumbers
    nothing else."""
    try:
        roles = aligned_to(sketch, ellipse)
        foci = roles.get("EllipseFocus1", []) + roles.get("EllipseFocus2", [])
        if foci:
            sketch.delGeometries(sorted(foci))
        roles = aligned_to(sketch, ellipse)
        major = (roles.get("EllipseMajorDiameter") or [None])[0]
        minor = (roles.get("EllipseMinorDiameter") or [None])[0]
        return major, minor
    except Exception as exc:
        warn("ellipse helpers: %s" % exc)
        return None, None
