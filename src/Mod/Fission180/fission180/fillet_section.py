# SPDX-License-Identifier: LGPL-2.1-or-later
"""A fillet or chamfer built from its cross-section, where OpenCASCADE's own blend gives up.
No Qt.

OpenCASCADE walks a blend along its edge on the two faces and stops where one of them ends
under it: the book's 20 mm chamfer in the inner corner of the Tensegrity Tower's arm was
"limited to 1.79 mm", the spot where the frame's top face narrows to the width of the arm
(wave 7, book parity report). The bevel itself is plain geometry there: a triangle, 20 mm
along each face, swept along the edge. That is what this module builds:

  the section   in the plane across the edge: the corner, 'size 1' along the first face,
                'size 2' along the second; a chamfer joins the two points with a line, a
                fillet with the arc that is tangent to both faces (fillet_core.section).
                The corner point is pushed a hair out of the part (into it for an inside
                corner) so that the tool crosses the part's faces and never lies in them.
  the sweep     along a straight edge between two flat faces: an extrusion. Along a circle
                between a flat face and a cylinder or cone about the same axis (or two of
                those): a revolution. A chain of such edges that run into each other
                smoothly is one tool.
  the ends      an open end is cut off by the flat faces that meet the edge there, on the
                edge's side of each (the wall an outside edge runs into; the side of the
                arm an inside corner ends at).
  the part      an outside (convex) edge: the tool is cut away. An inside (concave) corner:
                the tool is added.

It only builds what is certain: both strips the blend lands on must lie on the edge's own
two faces everywhere (so nothing hangs in the air and nothing is cut that the faces do not
cover), the result must be one sound solid and its volume must have changed by the
section's area times the edge's length, no more. Anything else (other curves, other faces,
corners where picked edges meet, a radius that changes along the edge, an end on a curved
face): None, and the caller refuses as before.

build() is called by fillet_robust for a group of touching edges that OpenCASCADE's own
blend could not build.
"""

import math

from . import blend, fillet_core

TOL = 1e-6
ANGLE_TOL = math.radians(0.05)
ON_FACE = 1e-5  # a landing point is on its face when it is this near (mm)
ACROSS = (0.02, 0.35, 0.7, 1.0)  # where along the strip's width it is probed
ALONG = 7  # and at how many places along the edge


def _unit(vector):
    length = vector.Length
    if length < 1e-12:
        return None
    return vector * (1.0 / length)


def _axis_of(surface):
    """(point, unit direction) of a flat face's normal line / a cylinder's or cone's axis,
    with the kind ("plane", "cylinder", "cone"), or None."""
    name = surface.__class__.__name__
    try:
        if name == "Plane":
            return "plane", surface.Position, _unit(surface.Axis)
        if name == "Cylinder":
            return "cylinder", surface.Center, _unit(surface.Axis)
        if name == "Cone":
            return "cone", surface.Center, _unit(surface.Axis)
    except Exception:
        return None
    return None


def _about(surface, center, axis):
    """True when `surface` is turned about the line (center, axis): a plane across it, a
    cylinder or cone around it."""
    found = _axis_of(surface)
    if found is None:
        return False
    kind, point, direction = found
    if direction is None or abs(abs(direction.dot(axis)) - 1.0) > 1e-9:
        return False
    if kind == "plane":
        return True
    offset = point - center
    return (offset - axis * offset.dot(axis)).Length < 1e-6


class _Piece:
    """One edge of the group: what it is swept along and its section."""

    def __init__(self, shape, item, edges=None):
        self.index, self.a, self.b = item
        self.edge = (edges if edges is not None else shape.Edges)[self.index - 1]
        self.ok = False
        self.frame = None
        self.faces = blend.faces_of(shape, self.edge)
        if len(self.faces) != 2:
            return
        self.frame = blend.frame(shape, self.edge, self.faces)
        if self.frame is None:
            return
        curve = self.edge.Curve
        name = curve.__class__.__name__
        first, last = self.edge.FirstParameter, self.edge.LastParameter
        self.start, self.end = self.edge.valueAt(first), self.edge.valueAt(last)
        self.closed = False
        if name == "Line":
            if any(f.Surface.__class__.__name__ != "Plane" for f in self.faces):
                return
            self.kind = "line"
            self.direction = _unit(self.end - self.start)
            if self.direction is None:
                return
            self.length = (self.end - self.start).Length
        elif name == "Circle":
            self.center, self.axis = curve.Center, _unit(curve.Axis)
            if self.axis is None:
                return
            if not all(_about(f.Surface, self.center, self.axis) for f in self.faces):
                return
            self.kind = "circle"
            self.angle = last - first
            self.closed = abs(self.angle - 2.0 * math.pi) < 1e-9
            self.length = self.angle * curve.Radius
            # the edge runs with the parameter: about +axis
            self.out_start = _unit(self.axis.cross(self.start - self.center)) * -1.0
            self.out_end = _unit(self.axis.cross(self.end - self.center))
        else:
            return
        if self.kind == "line":
            self.out_start, self.out_end = self.direction * -1.0, self.direction
        self.ok = True

    def marks(self, kind):
        """The section's points across the middle of the edge (blend.frame's place):
        {"p1", "p2": where the blend lands on the two faces, "middle" (fillet), "area"},
        or None."""
        frame = self.frame
        u1, u2 = frame["into"]
        point = frame["point"]
        try:
            flat = fillet_core.section(kind, frame["gamma"], self.a, self.b)
        except fillet_core.SetError:
            return None
        # the 2D section has the corner at (0, 0), face 1 along +x, face 2 at gamma
        # (fillet_core.section): 3D = corner + x * u1 + y * (the direction across u1,
        # in the section's plane, on face 2's side)
        across = _unit(u2 - u1 * u2.dot(u1))
        if across is None:
            return None

        def at(xy):
            return point + u1 * xy[0] + across * xy[1]

        found = {"p1": at(flat["p1"]), "p2": at(flat["p2"]), "area": flat["area"]}
        if kind == "fillet":
            found["middle"] = at(flat["middle"])
        return found

    def section(self, kind, hair):
        """(face, area, landing points) of the section across the middle of the edge, or
        None. `hair`: how far the corner point is pushed out of (into) the part."""
        import Part

        marks = self.marks(kind)
        if marks is None:
            return None
        frame = self.frame
        n1, n2 = frame["normals"]
        push = _unit(n1 + n2)
        if push is None:
            return None
        corner = frame["point"] + push * (hair if frame["convex"] else -hair)
        p1, p2 = marks["p1"], marks["p2"]
        try:
            if kind == "fillet":
                edges = [
                    Part.makeLine(corner, p1),
                    Part.Arc(p1, marks["middle"], p2).toShape(),
                    Part.makeLine(p2, corner),
                ]
            else:
                edges = [
                    Part.makeLine(corner, p1),
                    Part.makeLine(p1, p2),
                    Part.makeLine(p2, corner),
                ]
            face = Part.Face(Part.Wire(edges))
        except Exception:
            return None
        return face, marks["area"], (p1, p2)

    def tool(self, kind, hair, before, after):
        """The swept section, `before` / `after` longer than the edge at its two ends (mm
        for a line, radians for a circle), with the section's area. None when it cannot
        be made."""
        made = self.section(kind, hair)
        if made is None:
            return None
        face, area, _landing = made
        try:
            if self.kind == "line":
                half = self.length / 2.0
                face.translate(self.direction * -(half + before))
                solid = face.extrude(self.direction * (self.length + before + after))
            elif self.closed:
                solid = face.revolve(self.center, self.axis, 360.0)
            else:
                face.rotate(self.center, self.axis, -math.degrees(self.angle / 2.0 + before))
                solid = face.revolve(
                    self.center, self.axis, math.degrees(self.angle + before + after)
                )
        except Exception:
            return None
        if solid is None or solid.isNull() or not solid.Solids:
            return None
        return solid, area

    def landing(self, kind, along=ALONG, across=ACROSS):
        """Points on the two strips the blend lands on, each with its face (0 / 1):
        `along` places along the edge, at the fractions `across` of the strip's width."""
        marks = self.marks(kind)
        if marks is None:
            return None
        corner = self.frame["point"]
        points = []
        for which, far in ((0, marks["p1"]), (1, marks["p2"])):
            for part in across:
                spot = corner + (far - corner) * part
                for k in range(along):
                    fraction = (k + 0.5) / along - 0.5  # -0.5 .. 0.5 along the edge
                    points.append((which, self._moved(spot, fraction)))
        return points

    def _moved(self, point, fraction):
        if self.kind == "line":
            return point + self.direction * (self.length * fraction)
        import FreeCAD as App

        turn = App.Rotation(self.axis, math.degrees(self.angle * fraction))
        return self.center + turn.multVec(point - self.center)


def _joined(pieces):
    """The pieces in the order they run into each other, each with (free start?, free
    end?), or None when they are not one smooth chain. A closed circle is a chain of one."""
    if len(pieces) == 1:
        piece = pieces[0]
        return [(piece, not piece.closed, not piece.closed)]
    ends = []  # (point, outward direction, piece, "start" / "end")
    for piece in pieces:
        if piece.closed:
            return None
        ends.append((piece.start, piece.out_start, piece, "start"))
        ends.append((piece.end, piece.out_end, piece, "end"))
    free = {(id(p), s): True for _pt, _d, p, s in ends}
    for i, (point, out, piece, side) in enumerate(ends):
        partners = [
            other
            for j, other in enumerate(ends)
            if j != i and (other[0] - point).Length < TOL and other[2] is not piece
        ]
        if not partners:
            continue
        if len(partners) > 1:
            return None  # three picked edges at one point: a corner patch, not a sweep
        other = partners[0]
        if out.getAngle(other[1] * -1.0) > ANGLE_TOL:
            return None  # a real corner between two picked edges
        free[(id(piece), side)] = False
    if sum(1 for value in free.values() if value) not in (0, 2):
        return None
    return [(p, free[(id(p), "start")], free[(id(p), "end")]) for p in pieces]


def _same_sections(kind, chain):
    """True when, wherever two pieces of the chain meet, their sections meet the two faces
    in the same two points (the same corner angle, the sizes on the same sides)."""
    if len(chain) < 2:
        return True
    ends = []  # (the piece, the chain point, the two landing points there)
    for piece, _fs, _fe in chain:
        marks = piece.marks(kind)
        if marks is None:
            return False
        landing = (marks["p1"], marks["p2"])
        for point, fraction in ((piece.start, -0.5), (piece.end, 0.5)):
            ends.append((piece, point, [piece._moved(p, fraction) for p in landing]))
    for i, (piece, point, landing) in enumerate(ends):
        for other, other_point, other_landing in ends[i + 1 :]:
            if other is piece or (other_point - point).Length > TOL:
                continue
            for spot in landing:
                if min((spot - o).Length for o in other_landing) > 1e-6:
                    return False
    return True


def _end_faces(shape, point, own):
    """The faces of `shape` that meet at `point`, without the edge's own two."""
    found = []
    for face in shape.Faces:
        if any(face.isSame(o) for o in own):
            continue
        try:
            if any((v.Point - point).Length < TOL for v in face.Vertexes):
                found.append(face)
        except Exception:
            continue
    return found


def _half_space(point, normal, size):
    """A block of side `size` whose one face lies in the plane through `point` across
    `normal`, on the side `normal` points AWAY from."""
    import FreeCAD as App
    import Part

    box = Part.makeBox(size, size, size, App.Vector(-size / 2.0, -size / 2.0, -size))
    box.Placement = App.Placement(point, App.Rotation(App.Vector(0, 0, 1), normal))
    return box


def _clip(shape, tool, point, out, own, size):
    """`tool` cut off at the open end `point` (the edge leaves it along `out`) by the flat
    faces that meet there, keeping the edge's side of each. None when no flat face ends
    it (a curved face, or faces the edge runs along)."""
    faces = _end_faces(shape, point, own)
    if not faces:
        return None
    cut = 0
    for face in faces:
        if face.Surface.__class__.__name__ != "Plane":
            return None
        try:
            u, v = face.Surface.parameter(point)
            normal = _unit(face.normalAt(u, v))
        except Exception:
            return None
        if normal is None:
            return None
        along = normal.dot(out)
        if abs(along) < math.sin(math.radians(1.0)):
            continue  # the edge runs along this face: it does not end the blend
        keep_away_from = normal if along > 0 else normal * -1.0
        try:
            tool = tool.common(_half_space(point, keep_away_from, size))
        except Exception:
            return None
        if tool.isNull() or not tool.Solids:
            return None
        cut += 1
    return tool if cut else None


def _lands(piece, kind):
    """True when both strips the blend lands on lie on the edge's own two faces."""
    import Part

    points = piece.landing(kind)
    if not points:
        return False
    for which, point in points:
        try:
            if piece.faces[which].distToShape(Part.Vertex(point))[0] > ON_FACE:
                return False
        except Exception:
            return False
    return True


def misses(kind, shape, item, edges=None):
    """True when it is certain that the blend of `item` ((edge index, size 1, size 2)) has
    nowhere to land: across the middle of the edge, a point of the strip it would cover
    lies off the edge's face, and the face ends there in a sharp edge (the rim of a hole,
    a wall, the face's end). OpenCASCADE builds no such blend, and takes seconds to say so
    (or to hand back a solid that is not one); nor does build(). False whenever that is
    not certain: other curves and faces than build()'s, a face that goes on smoothly."""
    import Part

    if kind == "fillet" and abs(item[1] - item[2]) > 1e-12:
        return False
    try:
        piece = _Piece(shape, item, edges)
        if not piece.ok:
            return False
        points = piece.landing(kind, along=1, across=(0.35, 0.7, 1.0))
        if not points:
            return False
        for which, point in points:
            face = piece.faces[which]
            vertex = Part.Vertex(point)
            if face.distToShape(vertex)[0] <= ON_FACE:
                continue
            nearest = None
            for edge in face.Edges:
                gap = edge.distToShape(vertex)[0]
                if nearest is None or gap < nearest[0]:
                    nearest = (gap, edge)
            if nearest is not None and blend.frame(shape, nearest[1]) is not None:
                return True
    except Exception:
        return False
    return False


def _splits(shape):
    """True when the part has faces an earlier step left split on purpose or not: then
    nothing is merged here either."""
    try:
        return len(shape.removeSplitter().Faces) < len(shape.Faces)
    except Exception:
        return True


def build(kind, shape, items):
    """`shape` with the fillet / chamfer of `items` ((edge index, size 1, size 2): one group
    of touching edges) built from its swept section, or None when this is not a case for
    it (see the module's text)."""
    if not items:
        return None
    if kind == "fillet" and any(abs(a - b) > 1e-12 for _i, a, b in items):
        return None
    every = shape.Edges
    pieces = [_Piece(shape, item, every) for item in items]
    if not all(p.ok for p in pieces):
        return None
    if len({p.frame["convex"] for p in pieces}) != 1:
        return None
    chain = _joined(pieces)
    if chain is None or not _same_sections(kind, chain):
        return None
    if not all(_lands(piece, kind) for piece in pieces):
        return None
    convex = pieces[0].frame["convex"]
    size = max(max(p.a, p.b) for p in pieces)
    hair = max(0.01, min(0.05, 0.01 * size))
    reach = 4.0 * (shape.BoundBox.DiagonalLength + size) + 10.0
    tool, expected = None, 0.0
    for piece, free_start, free_end in chain:
        if piece.kind == "line":
            margin = size + 1.0
        else:
            # a little further round, never past the other end
            margin = min(math.radians(10.0), (2.0 * math.pi - piece.angle) / 3.0)
        made = piece.tool(kind, hair, margin if free_start else 0.0, margin if free_end else 0.0)
        if made is None:
            return None
        solid, area = made
        own = piece.faces
        if free_start:
            solid = _clip(shape, solid, piece.start, piece.out_start, own, reach)
            if solid is None:
                return None
        if free_end:
            solid = _clip(shape, solid, piece.end, piece.out_end, own, reach)
            if solid is None:
                return None
        expected += area * piece.length
        try:
            tool = solid if tool is None else tool.fuse(solid)
        except Exception:
            return None
    try:
        result = shape.cut(tool) if convex else shape.fuse(tool)
    except Exception:
        return None
    if result is None or result.isNull() or not result.Solids:
        return None
    if not convex and not _splits(shape):
        try:
            tidy = result.removeSplitter()
            if not tidy.isNull() and tidy.Solids and tidy.isValid():
                result = tidy
        except Exception:
            pass
    try:
        change = result.Volume - shape.Volume
    except Exception:
        return None
    if convex:
        change = -change
    # the section's area times the edge's length (exact for a straight edge; a circle's
    # section sweeps a little more or less than its corner does, and the ends may be cut
    # at a slant): the right sign and never much more
    if change <= 0 or change > expected * 1.5 + 1e-6:
        return None
    return result
