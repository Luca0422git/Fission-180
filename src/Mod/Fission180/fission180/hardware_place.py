# SPDX-License-Identifier: LGPL-2.1-or-later
"""Where a click puts a hardware part (INSERT > Hardware...). No Qt.

Fusion's Insert Fastener takes "a circular edge, a cylindrical or conical face" (Autodesk's
Insert Fastener reference); for a countersunk fastener the edge of the cone. So does this:

  a round edge       of a hole (its rim, the edge between a countersink and the hole, the
                     edge of a counterbore's floor) or of a boss / shaft end
  a hole's wall      the cylinder of a hole, a counterbore or a tapped hole
  a countersink or a chamfer on a hole's rim   (the cone)
  a shaft's side     the part goes to the shaft's end nearest the click
  a flat face        the part goes where it was clicked, square to the face

Whatever part of a hole was clicked, the whole hole is read: every round face on its axis,
from the opening nearest the click inwards (its "stack": countersink, counterbore, the hole
itself). The part goes on the axis at that opening, out of the part is +z, and the caller
learns the hole's own diameter (the size is taken from it: Fusion's Size Automatic), how
deep a counterbore is and how wide and steep a countersink is (the head seats in it).

The report this fixes (book parity report, Hot End): "my attempt to place an M3x20
countersunk screw on the chamfered rim did not pick the rim": only the top edge of a rim on
a flat face was taken; a click that landed on the chamfer's face, on its lower edge or on
the hole's wall was refused.
"""

import math

import FreeCAD as App

from . import bodies, hole
from .hardware_core import HardwareError

TOL = 1e-6
PROBE = 0.05  # mm beside a rim where the material is looked for
ROUND = ("Part::GeomCylinder", "Part::GeomCone")
WAITING = (
    "Click a hole (its rim, its wall or its countersink), a round edge, a shaft or a flat "
    "face of the part."
)


def global_shape(obj):
    shape = obj.Shape.copy()
    parent = obj.getParentGeoFeatureGroup()
    if parent is not None:
        place = parent.getGlobalPlacement()
        if not place.isIdentity():
            shape.transformShape(place.toMatrix())
    return shape


def _perpendicular(axis):
    other = App.Vector(1, 0, 0) if abs(axis.x) < 0.9 else App.Vector(0, 1, 0)
    side = axis.cross(other)
    side.normalize()
    return side


def _inside(shape, point):
    try:
        return shape.isInside(point, 1e-7, False)
    except Exception:
        return False


def _on_face(shape, point, normal, tol=1e-6):
    """True when `point` lies on a flat face of `shape` square to `normal`."""
    import Part

    vertex = Part.Vertex(point)
    for face in shape.Faces:
        try:
            if face.Surface.TypeId != "Part::GeomPlane":
                continue
            if abs(hole.face_normal_at(face, point).dot(normal)) < 1.0 - 1e-9:
                continue
            box = face.BoundBox
            box.enlarge(1e-3)
            if box.isInside(point) and face.distToShape(vertex)[0] <= tol:
                return True
        except Exception:
            continue
    return False


def _type(thing, attr):
    return getattr(getattr(thing, attr, None), "TypeId", "")


def _axis_of(surface):
    """(a point on the axis, its direction) of a cylinder or a cone."""
    axis = App.Vector(surface.Axis)
    axis.normalize()
    if surface.TypeId == "Part::GeomCone":
        return App.Vector(surface.Apex), axis
    return App.Vector(surface.Center), axis


def _on_line(point, origin, axis, tol=1e-6):
    return (point - origin).cross(axis).Length <= tol


def _internal(face):
    """True for the wall of a hole: the face's normal points towards its axis."""
    origin, axis = _axis_of(face.Surface)
    u0, u1, v0, v1 = face.ParameterRange
    u, v = (u0 + u1) / 2.0, (v0 + v1) / 2.0
    point = face.valueAt(u, v)
    out = point - (origin + axis * (point - origin).dot(axis))
    return face.normalAt(u, v).dot(out) < 0


def _rings(face, origin, axis):
    """[(position along the axis, radius)] of the round edges of a face, lowest first."""
    found = []
    for edge in face.Edges:
        if _type(edge, "Curve") != "Part::GeomCircle":
            continue
        centre = App.Vector(edge.Curve.Center)
        if not _on_line(centre, origin, axis, 1e-5):
            continue
        found.append(((centre - origin).dot(axis), float(edge.Curve.Radius)))
    if face.Surface.TypeId == "Part::GeomCone" and len({round(z, 6) for z, _r in found}) < 2:
        found.append(((App.Vector(face.Surface.Apex) - origin).dot(axis), 0.0))  # a pointed end
    return sorted(found)


class _Piece:
    """One round face (or the two halves of one) on a hole's axis: from z0 (radius r0) to z1
    (radius r1) along the axis."""

    def __init__(self, face, name, origin, axis):
        rings = _rings(face, origin, axis)
        self.face, self.name = face, name
        self.cone = face.Surface.TypeId == "Part::GeomCone"
        self.ok = len(rings) >= 2 and rings[-1][0] - rings[0][0] > TOL
        if self.ok:
            (self.z0, self.r0), (self.z1, self.r1) = rings[0], rings[-1]


def _stack(shape, origin, axis, internal):
    """The round faces on this axis (holes' walls when `internal`, else shafts' sides)."""
    found = []
    for i, face in enumerate(shape.Faces):
        if _type(face, "Surface") not in ROUND:
            continue
        base, direction = _axis_of(face.Surface)
        if abs(abs(direction.dot(axis)) - 1.0) > 1e-9 or not _on_line(base, origin, axis, 1e-5):
            continue
        try:
            if _internal(face) != internal:
                continue
        except Exception:
            continue
        piece = _Piece(face, "Face%d" % (i + 1), origin, axis)
        if piece.ok:
            found.append(piece)
    return found


def _chain(pieces, seed):
    """The pieces that touch end to end with `seed` (one hole; another hole further along
    the same axis is another chain)."""
    chain = [seed]
    lo, hi = seed.z0, seed.z1
    rest = [p for p in pieces if p is not seed]
    grown = True
    while grown:
        grown = False
        for p in list(rest):
            if p.z0 <= hi + 1e-5 and p.z1 >= lo - 1e-5:
                chain.append(p)
                rest.remove(p)
                lo, hi = min(lo, p.z0), max(hi, p.z1)
                grown = True
    return chain, lo, hi


def _flat_beside(shape, centre, axis, radius, normal):
    """A point on the flat face around an opening (just outside its rim), or None."""
    side = _perpendicular(axis)
    other = axis.cross(side)
    for k in range(8):
        a = math.pi / 4.0 * k
        point = centre + (side * math.cos(a) + other * math.sin(a)) * (radius + PROBE)
        if _on_face(shape, point, normal):
            return point
    return None


def _hole_place(shape, body, seed, ref):
    """The place a click on a hole gives (seed: one of its walls; ref: where it was
    clicked)."""
    origin, axis = _axis_of(seed.Surface)
    pieces = _stack(shape, origin, axis, True)
    mine = [p for p in pieces if p.face.isSame(seed)]
    if not mine:
        raise HardwareError("That hole could not be read. Click its rim on a flat face.")
    chain, lo, hi = _chain(pieces, mine[0])
    ends = []
    for z, out in ((lo, axis * -1.0), (hi, axis)):
        point = origin + axis * z
        if not _inside(shape, point + out * PROBE):  # open: no material beyond it
            ends.append((abs((ref - origin).dot(axis) - z), z, out))
    if not ends:
        raise HardwareError("That hole is closed at both ends: nothing can be put into it.")
    _gap, z_open, normal = min(ends, key=lambda e: e[0])
    centre = origin + axis * z_open

    def depth(z):
        return abs(z - z_open)

    # the pieces from the opening inwards: (depth at the top, depth at the bottom, radius at
    # the top, radius at the bottom, a cone?)
    steps = {}
    for p in chain:
        top = (p.z0, p.r0) if depth(p.z0) < depth(p.z1) else (p.z1, p.r1)
        bottom = (p.z1, p.r1) if top[0] == p.z0 else (p.z0, p.r0)
        key = (round(depth(top[0]), 5), round(depth(bottom[0]), 5))
        steps[key] = (depth(top[0]), depth(bottom[0]), top[1], bottom[1], p.cone, p.name)
    order = [steps[k] for k in sorted(steps)]
    first = order[0]
    if first[0] > 1e-5:
        raise HardwareError("That hole could not be read. Click its rim on a flat face.")
    top_diameter = 2.0 * first[2]
    place = {
        "center": centre,
        "normal": normal,
        "body": body,
        "rim": True,
        "diameter": top_diameter,
        "is_hole": True,
        "face_point": _flat_beside(shape, centre, axis, first[2], normal),
        "hole_diameter": top_diameter,
        "cbore_depth": None,
        "cone": None,
        "face": first[5],
    }
    after = order[1] if len(order) > 1 else None
    if first[4]:  # a countersink or a chamfer: the hole is what comes below it
        height = first[1] - first[0]
        place["cone"] = {
            "top_diameter": top_diameter,
            "bottom_diameter": 2.0 * first[3],
            "depth": height,
            "half_angle": math.degrees(math.atan2(first[2] - first[3], height)),
        }
        place["hole_diameter"] = 2.0 * first[3]
        if after is not None and not after[4] and after[2] < first[3] - 1e-6:
            place["hole_diameter"] = 2.0 * after[2]
    elif after is not None and not after[4] and after[2] < first[2] - 1e-6:
        place["cbore_depth"] = first[1] - first[0]  # a counterbore over a narrower hole
        place["hole_diameter"] = 2.0 * after[2]
    return place


def _shaft_place(shape, body, seed, ref):
    """A click on a shaft's side: the part goes to the shaft's end nearest the click (a free
    end: out of the shaft; an end at a shoulder: away from the shoulder)."""
    origin, axis = _axis_of(seed.Surface)
    piece = _Piece(seed, "", origin, axis)
    if not piece.ok or piece.cone:
        raise HardwareError("Click a round edge, a hole or the side of a round shaft.")
    radius = piece.r0
    ends = []
    for z, out in ((piece.z0, axis * -1.0), (piece.z1, axis)):
        point = origin + axis * z + _perpendicular(axis) * (radius - PROBE)
        free = not _inside(shape, point + out * PROBE)
        ends.append((abs((ref - origin).dot(axis) - z), z, out if free else out * -1.0, free))
    _gap, z_end, normal, free = min(ends, key=lambda e: e[0])
    centre = origin + axis * z_end
    side = _perpendicular(axis)
    face_point = None
    for r in (radius - PROBE, radius + PROBE):
        if _on_face(shape, centre + side * r, normal):
            face_point = centre + side * r
            break
    return {
        "center": centre,
        "normal": normal,
        "body": body,
        "rim": True,
        "diameter": 2.0 * radius,
        "is_hole": False,
        "face_point": face_point,
        "hole_diameter": 2.0 * radius,
        "cbore_depth": None,
        "cone": None,
        "face": "",
        "shoulder": not free,
    }


def _edge_place(shape, body, edge):
    """A round edge without a hole's wall beside it (a boss's or a shaft's edge, a rim cut
    by a fillet): on its axis, out of the part the side with no material."""
    curve = edge.Curve
    center = App.Vector(curve.Center)
    axis = App.Vector(curve.Axis)
    axis.normalize()
    r = curve.Radius
    side = _perpendicular(axis)
    rim = center + side * r
    outside = rim + side * PROBE
    inside = rim - side * PROBE
    if _inside(shape, outside - axis * PROBE) or _inside(shape, inside - axis * PROBE):
        normal = axis
    else:
        normal = axis * -1.0
    # a hole's rim has material outside the circle (under the face) and none inside it; the
    # foot of a boss has material on both sides (and the boss above): a shaft at a shoulder
    below_out = _inside(shape, outside - normal * PROBE)
    below_in = _inside(shape, inside - normal * PROBE)
    is_hole = below_out and not below_in
    face_point = None
    for point in (outside, inside):
        if _on_face(shape, point, normal):
            face_point = point
            break
    return {
        "center": center,
        "normal": normal,
        "body": body,
        "rim": True,
        "diameter": 2.0 * r,
        "is_hole": is_hole,
        "face_point": face_point,
        "hole_diameter": 2.0 * r,
        "cbore_depth": None,
        "cone": None,
        "face": "",
        "shoulder": below_out and below_in,
    }


def spot(obj, sub, point=None):
    """Where a click puts the part: {"center", "normal" (out of the part), "body", "rim"
    (round: a hole, a shaft or a round edge), "diameter" (of the opening), "is_hole",
    "face_point" (a point on the flat face the hole is drilled from, None when there is
    none), "hole_diameter" (of the hole itself, below a counterbore or a countersink),
    "cbore_depth", "cone" ({"top_diameter", "bottom_diameter", "depth", "half_angle"}),
    "face" (a wall of the hole, to find it again)}, all in design coordinates. Raises
    HardwareError when the click is nothing a part can go on."""
    import Part

    if obj is None or not sub:
        raise HardwareError(WAITING)
    body = bodies.body_of(obj)
    if body is None or obj.Shape.isNull() or not obj.Shape.Solids:
        raise HardwareError("Click a hole, a round edge or a flat face of a solid body.")
    shape = global_shape(obj)
    try:
        element = shape.getElement(sub)
    except Exception:
        raise HardwareError("That edge or face is gone. Click the part again.")
    if sub.startswith("Edge"):
        if _type(element, "Curve") != "Part::GeomCircle":
            raise HardwareError(
                "That edge is not round. Click a hole, a round edge or a flat face."
            )
        ref = App.Vector(element.Curve.Center)
        walls = []
        for face in shape.ancestorsOfType(element, Part.Face):
            if _type(face, "Surface") in ROUND and _on_line(ref, *_axis_of(face.Surface), 1e-5):
                walls.append(face)
        holes = [f for f in walls if _internal(f)]
        if holes:
            try:
                return _hole_place(shape, body, holes[0], ref)
            except HardwareError:
                pass  # a hole cut into by something else: its rim alone, as a round edge
        return _edge_place(shape, body, element)
    if not sub.startswith("Face"):
        raise HardwareError(WAITING)
    kind = _type(element, "Surface")
    if kind in ROUND:
        ref = App.Vector(point) if point is not None else element.CenterOfMass
        if _internal(element):
            return _hole_place(shape, body, element, ref)
        if kind == "Part::GeomCylinder":
            return _shaft_place(shape, body, element, ref)
        raise HardwareError(
            "That cone is not a hole's countersink. Click a hole, a round edge or a flat face."
        )
    if kind != "Part::GeomPlane":
        raise HardwareError("That face is curved. Click a hole, a round edge or a flat face.")
    if point is None:
        point = element.CenterOfMass
    point = hole.snap_to_face(element, point)
    normal = hole.face_normal_at(element, point)
    return {
        "center": App.Vector(point),
        "normal": normal,
        "body": body,
        "rim": False,
        "diameter": None,
        "is_hole": False,
        "face_point": App.Vector(point),
        "hole_diameter": None,
        "cbore_depth": None,
        "cone": None,
        "face": "",
    }


def _same(a, b, tol=1e-4):
    if (a is None) != (b is None):
        return False
    return a is None or abs(a - b) <= tol


def similar(obj, place):
    """Fusion's Select Similar: every other hole like the one clicked that opens on the same
    face: [(sub, centre)] (a wall of each hole and where it opens), in a steady order."""
    if not place.get("is_hole") or not place.get("face"):
        return []
    shape = global_shape(obj)
    normal = place["normal"]
    centre = place["center"]
    seen = [centre]
    found = []
    for i, face in enumerate(shape.Faces):
        if _type(face, "Surface") not in ROUND:
            continue
        try:
            origin, axis = _axis_of(face.Surface)
            if abs(abs(axis.dot(normal)) - 1.0) > 1e-9 or not _internal(face):
                continue
            at = origin + axis * (centre - origin).dot(axis)  # its axis in the opening's plane
            if any((at - p).Length < 1e-5 for p in seen):
                continue
            other = _hole_place(shape, place["body"], face, at)
        except HardwareError:
            continue
        except Exception:
            continue
        if abs((other["center"] - centre).dot(normal)) > 1e-5:
            continue  # it opens on another level
        if other["normal"].dot(normal) < 1.0 - 1e-9:
            continue
        if not _same(other["diameter"], place["diameter"]):
            continue
        if not _same(other["hole_diameter"], place["hole_diameter"]):
            continue
        if not _same(other["cbore_depth"], place["cbore_depth"]):
            continue
        if (other["cone"] is None) != (place["cone"] is None):
            continue
        seen.append(other["center"])
        found.append((other["face"] or "Face%d" % (i + 1), other["center"]))
    found.sort(key=lambda f: (round(f[1].x, 5), round(f[1].y, 5), round(f[1].z, 5)))
    return found
