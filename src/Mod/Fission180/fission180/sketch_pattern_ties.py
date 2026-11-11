# SPDX-License-Identifier: LGPL-2.1-or-later
"""Tying the copies of a sketch pattern to their originals (wave 7, the book parity report).

Fusion's sketch pattern keeps its copies where the pattern puts them: they follow the
original, and a sketch that was fully constrained stays so. Fission 180's copies were only
Equal to the original: 25 to 79 loose degrees of freedom, copies that drifted by micrometres
(profiles did not close) and later dimensions that did not move them (the report: Tensegrity,
Drone, Hot End, Tesla).

FreeCAD's solver has no pattern constraint. Each copy is tied point by point, with ordinary
constraints kept out of sight (FreeCAD's "virtual space"):

- a copy that is MOVED (Rectangular Pattern): its point is a horizontal and a vertical
  distance from the original's point (Horizontal / Vertical between the two points where
  that distance is 0);
- a copy that is TURNED (Circular Pattern): a construction line from the centre to the
  original's point and one to the copy's point (the "spokes"), Equal in length and at the
  pattern's angle to each other. The spokes are hidden helper lines (sketch_helpers.py). A
  point on the centre itself stays on its original;
- lines by both ends, circles by their centre plus Equal, arcs by both ends plus Equal,
  points by themselves; points the originals share are tied once
  (sketch_pattern_core.tie_plan, unit tested).

Splines, ellipses and conic curves cannot be tied this way (the solver has no handle on
their shape): their copies keep the old behaviour (shape constraints, free position), and
the tool says so.
"""

import math

from . import log
from . import sketch_pattern_core as core

ZERO = 1e-9
AT_CENTRE = 1e-7


def _con(*args):
    import Sketcher

    return Sketcher.Constraint(*args)


def _point(sketch, geo, pos):
    """The sketch point (x, y) of (geo, pos); the origin for (-1, 1)."""
    if geo == -1 and pos == 1:
        return (0.0, 0.0)
    from .sketch_build import geometry

    g = geometry(sketch, geo)
    if g.TypeId == core.POINT:
        return (g.X, g.Y)
    if pos == 1:
        p = g.StartPoint
    elif pos == 2:
        p = g.EndPoint
    else:
        p = g.Center
    return (p.x, p.y)


def supported(sketch, geo):
    try:
        return sketch.Geometry[geo].TypeId in core.TIED_TYPES
    except Exception:
        return False


def plan(sketch, picked):
    """sketch_pattern_core.tie_plan for the picked curves that can be tied."""
    types = {g: sketch.Geometry[g].TypeId for g in picked if supported(sketch, g)}
    coincidents = []
    for c in sketch.Constraints:
        if c.Type == "Coincident" and c.First in types and c.Second in types:
            coincidents.append((c.First, c.FirstPos, c.Second, c.SecondPos))
    return types, core.tie_plan(types, coincidents)


def moved_ties(sketch, original, copy, offset):
    """The constraints that keep point `copy` (geo, pos) at `offset` (dx, dy) from point
    `original`."""
    out = []
    for value, level, distance in (
        (offset[0], "Vertical", "DistanceX"),
        (offset[1], "Horizontal", "DistanceY"),
    ):
        # (same x: FreeCAD's "Vertical" between two points; same y: "Horizontal")
        if abs(value) < ZERO:
            out.append(_con(level, original[0], original[1], copy[0], copy[1]))
        elif value > 0:
            out.append(_con(distance, original[0], original[1], copy[0], copy[1], value))
        else:
            out.append(_con(distance, copy[0], copy[1], original[0], original[1], -value))
    return out


class Spokes:
    """The hidden lines from a circular pattern's centre: one to each tied point of the
    originals (made when first needed), one to each tied point of each copy."""

    def __init__(self, sketch, centre_item, centre):
        self.sketch = sketch
        self.centre_item = tuple(centre_item)
        self.centre = centre
        self.of_original = {}
        self.lines = []

    def _line(self, to_item):
        import FreeCAD as App
        import Part

        p = _point(self.sketch, to_item[0], to_item[1])
        line = Part.LineSegment(
            App.Vector(self.centre[0], self.centre[1], 0), App.Vector(p[0], p[1], 0)
        )
        index = self.sketch.addGeometry(line, True)
        self.lines.append(index)
        return index

    def _ends(self, spoke, item):
        c = self.centre_item
        return [
            _con("Coincident", spoke, 1, c[0], c[1]),
            _con("Coincident", spoke, 2, item[0], item[1]),
        ]

    def at_centre(self, item):
        p = _point(self.sketch, item[0], item[1])
        return math.hypot(p[0] - self.centre[0], p[1] - self.centre[1]) <= AT_CENTRE

    def ties(self, original, copy, degrees):
        """The constraints that keep point `copy` at `original` turned by `degrees`."""
        if self.at_centre(original):
            return [_con("Coincident", copy[0], copy[1], original[0], original[1])]
        out = []
        base = self.of_original.get(original)
        if base is None:
            base = self.of_original[original] = self._line(original)
            out += self._ends(base, original)
        spoke = self._line(copy)
        out += self._ends(spoke, copy)
        out.append(_con("Equal", base, spoke))
        out.append(_con("Angle", base, 1, spoke, 1, core.wrap_turn(degrees)))
        return out


def build(sketch, picked, moves, mappings, centre_item=None):
    """The tie constraints of the copies: (constraints, helper lines, tied, untied).
    moves: the copies' moves (sketch_pattern_core); mappings: per move {original: copy} of
    the picked curves; centre_item: the circular pattern's centre (geo, pos). Adds the
    spokes to the sketch (the caller hides them and adds the constraints)."""
    types, (points, equals, joins) = plan(sketch, picked)
    constraints = []
    spokes = None
    for move, mapping in zip(moves, mappings):
        for g1, p1, g2, p2 in joins:
            constraints.append(_con("Coincident", mapping[g1], p1, mapping[g2], p2))
        for geo in equals:
            constraints.append(_con("Equal", geo, mapping[geo]))
        for geo, pos in points:
            original, copy = (geo, pos), (mapping[geo], pos)
            if move[0] == "move":
                constraints += moved_ties(sketch, original, copy, move[1])
            else:
                if spokes is None:
                    spokes = Spokes(sketch, centre_item, move[1])
                constraints += spokes.ties(original, copy, move[2])
    tied = sorted(types)
    untied = [g for g in picked if g not in types]
    lines = spokes.lines if spokes is not None else []
    if tied:
        log(
            "pattern ties: %d curve(s) per copy tied by %d point(s), %d constraint(s), "
            "%d hidden line(s)" % (len(tied), len(points), len(constraints), len(lines))
        )
    return constraints, lines, tied, untied
