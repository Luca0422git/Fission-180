# SPDX-License-Identifier: LGPL-2.1-or-later
"""Where a textured look's pattern lands on a body: Fusion's Texture Map Controls as plain
arithmetic. Pure Python (no FreeCAD, no Qt), unit tested (test_appearance_mapping.py).

Points and directions are (x, y, z) tuples in the body's own coordinates, lengths in mm. A
texture coordinate (u, v) counts repeats of the pattern: 1.0 is one whole repeat.

Projections (Fusion's list; "3D Texture" needs a solid texture and is not offered):
  automatic    a flat face is mapped flat on its own plane, a cylinder face round its own
               axis with the grain along the axis, any other face like Box
  box          each triangle is mapped flat along the design axis it faces most
  planar       everything is mapped flat along one axis (stretched on the faces beside it)
  cylindrical  wrapped round one axis through the body's middle
  spherical    wrapped round the body's middle like a globe
"""

import math

PROJECTIONS = ["automatic", "box", "planar", "cylindrical", "spherical"]
PROJECTION_LABELS = {
    "automatic": "Automatic",
    "box": "Box",
    "planar": "Planar",
    "cylindrical": "Cylindrical",
    "spherical": "Spherical",
}
AXES = {"x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0), "z": (0.0, 0.0, 1.0)}
DEFAULTS = {
    "projection": "automatic",
    "axis": "z",
    "offset_u": 0.0,  # mm along the pattern's own u
    "offset_v": 0.0,
    "rotation": 0.0,  # degrees, on top of the look's own Rotation
    "scale": 100.0,  # per cent, times the look's own Scale
}
TWO_PI = 2.0 * math.pi


def with_defaults(options):
    merged = dict(DEFAULTS)
    for key, value in (options or {}).items():
        if key in DEFAULTS and value is not None:
            merged[key] = value
    if merged["projection"] not in PROJECTIONS:
        merged["projection"] = "automatic"
    if merged["axis"] not in AXES:
        merged["axis"] = "z"
    return merged


def is_default(options):
    merged = with_defaults(options)
    return all(merged[key] == DEFAULTS[key] for key in DEFAULTS)


def repeat_mm(tile_mm, look_scale=100.0, map_scale=100.0):
    """Millimetres one repeat covers: the pattern's own size times the look's Scale times the
    map's Scale (both in per cent; 50 makes the pattern half as big)."""
    factor = max(0.01, float(look_scale) / 100.0) * max(0.01, float(map_scale) / 100.0)
    return max(1e-6, float(tile_mm) * factor)


# -- small vector helpers --------------------------------------------------------------------------
def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _unit(a):
    length = math.sqrt(_dot(a, a))
    if length < 1e-12:
        return (0.0, 0.0, 1.0)
    return (a[0] / length, a[1] / length, a[2] / length)


def triangle_normal(a, b, c):
    return _unit(_cross(_sub(b, a), _sub(c, a)))


def snapped(normal):
    """The design axis (signed) a direction points along most."""
    index = max(range(3), key=lambda i: abs(normal[i]))
    out = [0.0, 0.0, 0.0]
    out[index] = 1.0 if normal[index] >= 0 else -1.0
    return tuple(out)


def plane_frame(normal):
    """(u direction, v direction) on the plane with this outward normal: v points up the
    design's Z where it can (Y on a face that looks along Z), and u runs to the right seen
    from outside, so a pattern is never mirrored."""
    normal = _unit(normal)
    up = (0.0, 0.0, 1.0) if abs(normal[2]) < 0.9 else (0.0, 1.0, 0.0)
    u = _unit(_cross(up, normal))
    v = _cross(normal, u)
    return u, v


def rotated(u, v, degrees):
    if not degrees:
        return u, v
    angle = math.radians(degrees)
    c, s = math.cos(angle), math.sin(angle)
    return u * c - v * s, u * s + v * c


def _finish(pairs, size, options, rotation):
    """mm pairs -> repeats: the offset, the rotation (the look's plus the map's), the size."""
    out = []
    for u, v in pairs:
        u, v = rotated(u + options["offset_u"], v + options["offset_v"], rotation)
        out.append((u / size, v / size))
    return out


def _flat(points, normal):
    u_dir, v_dir = plane_frame(normal)
    return [(_dot(p, u_dir), _dot(p, v_dir)) for p in points]


def _unwrapped(angles):
    """Angles of one triangle's corners made continuous across the seam at +-180 degrees."""
    if max(angles) - min(angles) > math.pi:
        return [a + TWO_PI if a < 0 else a for a in angles]
    return list(angles)


def _round_axis(points, origin, axis):
    """(angle round the axis, height along it, distance from it) of each point."""
    axis = _unit(axis)
    u_dir, v_dir = plane_frame(axis)
    out = []
    for p in points:
        rel = _sub(p, origin)
        x, y = _dot(rel, u_dir), _dot(rel, v_dir)
        out.append((math.atan2(y, x), _dot(rel, axis), math.hypot(x, y)))
    return out


def _around(points, origin, axis, radius, size, along_u):
    """Wrapped round an axis: a whole number of repeats round the circumference (no seam),
    the height in mm. along_u: the pattern's u runs along the axis (a turned handle's grain)."""
    polar = _round_axis(points, origin, axis)
    angles = _unwrapped([p[0] for p in polar])
    turns = max(1, int(round(TWO_PI * max(radius, 1e-6) / size)))
    pairs = []
    for angle, (_a, height, _r) in zip(angles, polar):
        round_mm = angle / TWO_PI * turns * size
        pairs.append((height, round_mm) if along_u else (round_mm, height))
    return pairs


def _globe(points, origin, axis, radius, size):
    axis = _unit(axis)
    polar = _round_axis(points, origin, axis)
    angles = _unwrapped([p[0] for p in polar])
    turns = max(1, int(round(TWO_PI * max(radius, 1e-6) / size)))
    rows = max(1, int(round(math.pi * max(radius, 1e-6) / size)))
    pairs = []
    for angle, (_a, height, dist) in zip(angles, polar):
        latitude = math.atan2(height, dist)  # -90..90 degrees
        pairs.append((angle / TWO_PI * turns * size, (latitude / math.pi + 0.5) * rows * size))
    return pairs


def triangle_uvs(points, options, size, rotation=0.0, face=None, middle=(0.0, 0.0, 0.0), reach=1.0):
    """The texture coordinates of one triangle's three corners.

    points    the corners (body coordinates, counter-clockwise seen from outside)
    options   the body's map (with_defaults)
    size      mm one repeat covers (repeat_mm)
    rotation  the look's own Rotation, degrees
    face      what the triangle's face is, for Automatic: ("plane", normal), ("cylinder",
              point on the axis, axis direction, radius) or None
    middle    the middle of the body's box; reach: half its diagonal (cylindrical, spherical)
    """
    options = with_defaults(options)
    turn = float(rotation or 0.0) + float(options["rotation"] or 0.0)
    kind = options["projection"]
    axis = AXES[options["axis"]]
    if kind == "planar":
        return _finish(_flat(points, axis), size, options, turn)
    if kind == "cylindrical":
        return _finish(_around(points, middle, axis, reach, size, False), size, options, turn)
    if kind == "spherical":
        return _finish(_globe(points, middle, axis, reach, size), size, options, turn)
    normal = triangle_normal(*points)
    if kind == "automatic" and face is not None:
        if face[0] == "plane":
            return _finish(_flat(points, face[1]), size, options, turn)
        if face[0] == "cylinder":
            pairs = _around(points, face[1], face[2], face[3], size, True)
            return _finish(pairs, size, options, turn)
    return _finish(_flat(points, snapped(normal)), size, options, turn)
