# SPDX-License-Identifier: LGPL-2.1-or-later
"""Thread geometry without FreeCAD: the groove a modeled thread cuts, the length it covers,
and the volume it removes. Pure Python (unit tested); fission180/thread.py turns these numbers
into OpenCASCADE shapes.

The thread profile is ISO 68-1's basic profile (the same 60 degree profile serves the
Unified threads, ASME B1.1). With H = sqrt(3)/2 * P (P = pitch) and the major radius R:

  external thread (a bolt, a shaft): the groove between two ridges has a flat root P/4 wide
      at R - 5H/8 and opens at 60 degrees to P/8-wide crests at R. The groove is carried a
      little past R (to R + H/16, 15P/16 wide) so it cleanly breaks out of the surface.
  internal thread (a nut, a tapped hole): the groove cut into the hole wall has a flat root
      P/8 wide at R and opens towards the hole to 7P/8 at R - 3H/4, inside the drilled hole
      (a tap drill is R - P/2 or more, so R - 3H/4 = R - 0.65 P is in the empty hole).

A groove is a trapezoid in a plane through the thread's axis: (radius, axial position)
corners. Swept along a helix it makes a screw-shaped cutter; inside the thread's length every
cross section across the axis has the same area, so the material it removes is

    removed = length * (2 * pi / P) * integral over r of r * w(r) dr

where w(r) is the groove's width along the axis at radius r (only where there was material).
"""

import math

TAN30 = math.tan(math.radians(30.0))


def fundamental_height(pitch):
    """H: the height of the sharp 60 degree triangle of the thread form."""
    return math.sqrt(3.0) / 2.0 * pitch


# Thread forms. "iso": ISO 68-1 / ASME B1.1, 60 degrees. "whitworth": the 55 degree form of the
# ISO pipe threads (ISO 228-1 G, ISO 7-1 R / Rc): H = 0.960491 P, thread depth 0.640327 P; its
# rounded crests and roots (r = 0.137329 P) are cut as flats P/6 wide (the truncation of H/6 the
# rounding replaces). "npt": ASME B1.20.1, 60 degrees, thread depth 0.8 P (flats 0.038 P).
FORMS = ("iso", "whitworth", "npt")
WHITWORTH_DEPTH = 0.640327
NPT_DEPTH = 0.8
TAN27_5 = math.tan(math.radians(27.5))


def thread_depth(pitch, form="iso", internal=False):
    """How deep the thread is cut on the radius (major radius - minor radius)."""
    if form == "whitworth":
        return WHITWORTH_DEPTH * pitch
    if form == "npt":
        return NPT_DEPTH * pitch
    return (5.0 / 8.0) * fundamental_height(pitch)


def groove(major_radius, pitch, internal, form="iso"):
    """The groove trapezoid as [(radius, z), ...] (closed, counter-clockwise in r-z), centred
    on z = 0. See the module text for the shape."""
    h = fundamental_height(pitch)
    r = float(major_radius)
    p = float(pitch)
    if form in ("whitworth", "npt"):
        # a symmetric truncated V: flats `flat` wide at the crests and at the roots, flanks at
        # `slope` (axial per radial); carried a little past the surface it breaks out of
        depth = thread_depth(p, form)
        if form == "whitworth":
            flat, slope = p / 6.0, TAN27_5
        else:
            flat, slope = 0.038 * p, TAN30
        wide = flat + 2.0 * depth * slope  # the opening on the far side of the flat root
        over = h / 16.0
        if internal:  # root (narrow) at the major radius, opens towards the hole
            inner, outer = r - depth - over, r
            inner_half, outer_half = wide / 2.0 + over * slope, flat / 2.0
        else:  # root (narrow) at the minor radius, opens outwards
            inner, outer = r - depth, r + over
            inner_half, outer_half = flat / 2.0, wide / 2.0 + over * slope
        limit = 0.499 * p  # neighbouring turns never touch
        inner_half, outer_half = min(inner_half, limit), min(outer_half, limit)
        return [
            (inner, -inner_half),
            (outer, -outer_half),
            (outer, outer_half),
            (inner, inner_half),
        ]
    if internal:
        inner, outer = r - 0.75 * h, r
        inner_half, outer_half = 7.0 * p / 16.0, p / 16.0
    else:
        inner, outer = r - 5.0 * h / 8.0, r + h / 16.0
        inner_half, outer_half = p / 8.0, 15.0 * p / 32.0
    return [
        (inner, -inner_half),
        (outer, -outer_half),
        (outer, outer_half),
        (inner, inner_half),
    ]


def moved_groove(corners, distance):
    """The groove (groove(): a closed, counter-clockwise polygon in r-z) with every side
    moved `distance` out of the groove, square to itself (negative: into it). Offset Face on a
    modeled thread moves the thread's faces: the faces of the groove are the flanks and the
    root, so the groove grows by what the thread's faces move into the material. Raises
    ValueError when the groove closes up (its root's width is used up)."""
    count = len(corners)
    lines = []  # (point on the moved side, its direction)
    for i in range(count):
        (r0, z0), (r1, z1) = corners[i], corners[(i + 1) % count]
        dr, dz = r1 - r0, z1 - z0
        length = math.hypot(dr, dz)
        if length < 1e-12:
            raise ValueError("a side of the groove has no length")
        # counter-clockwise: the outside is to the right of the direction of travel
        nr, nz = dz / length, -dr / length
        lines.append(((r0 + nr * distance, z0 + nz * distance), (dr, dz)))
    moved = []
    for i in range(count):
        (p, d), (q, e) = lines[i - 1], lines[i]
        cross = d[0] * e[1] - d[1] * e[0]
        if abs(cross) < 1e-12:
            raise ValueError("two sides of the groove are parallel")
        t = ((q[0] - p[0]) * e[1] - (q[1] - p[1]) * e[0]) / cross
        moved.append((p[0] + d[0] * t, p[1] + d[1] * t))
    for i in range(count):  # every side still runs the way it did
        (r0, z0), (r1, z1) = corners[i], corners[(i + 1) % count]
        (m0, w0), (m1, w1) = moved[i], moved[(i + 1) % count]
        if (r1 - r0) * (m1 - m0) + (z1 - z0) * (w1 - w0) <= 1e-12:
            raise ValueError("the groove closes up")
    return moved


def fitted_groove(corners, pitch, crest):
    """The groove (after moved_groove()) with its open side put where it has to be: a little
    past the thread's crest (the cylinder of radius `crest` the grooves are cut into), along
    its flanks, so that the groove breaks through the crest; but never where it is a pitch
    wide: wider, neighbouring turns of the swept groove would run into each other. Raises
    ValueError when the grooves would meet on the crest or before it: nothing is left
    between them."""
    (r_in, z_in), (r_out, z_out) = corners[0], corners[1]
    half_in, half_out = abs(z_in), abs(z_out)
    if abs(half_out - half_in) < 1e-12 or abs(r_out - r_in) < 1e-12:
        raise ValueError("the groove's flanks do not open")
    slope = (half_out - half_in) / (r_out - r_in)  # half width gained per radius
    limit = 0.499 * pitch
    over = fundamental_height(pitch) / 16.0

    def half(r):
        return half_in + (r - r_in) * slope

    r_cap = r_in + (limit - half_in) / slope  # where it is `limit` wide to each side
    if slope > 0:  # opens outwards (a shaft's thread)
        r_open = min(crest + over, r_cap)
        if r_open <= crest + 1e-6 or r_open <= r_in:
            raise ValueError("the grooves meet")
        return [corners[0], (r_open, -half(r_open)), (r_open, half(r_open)), corners[3]]
    r_open = max(crest - over, r_cap)  # opens towards the axis (a hole's thread)
    if r_open >= crest - 1e-6 or r_open >= r_out:
        raise ValueError("the grooves meet")
    return [(r_open, -half(r_open)), corners[1], corners[2], (r_open, half(r_open))]


def groove_width(major_radius, pitch, internal, radius, form="iso"):
    """w(r): the groove's width along the axis at `radius` (0 outside the groove)."""
    corners = groove(major_radius, pitch, internal, form)
    inner, outer = corners[0][0], corners[1][0]
    if radius < inner - 1e-12 or radius > outer + 1e-12:
        return 0.0
    w_inner, w_outer = 2.0 * corners[0][1] * -1.0, 2.0 * corners[1][1] * -1.0
    t = (radius - inner) / (outer - inner)
    return w_inner + (w_outer - w_inner) * t


def _integral_rw(major_radius, pitch, internal, a, b, form="iso"):
    """Integral of r * w(r) dr from a to b (w linear between the groove's radii)."""
    corners = groove(major_radius, pitch, internal, form)
    inner, outer = corners[0][0], corners[1][0]
    a, b = max(a, inner), min(b, outer)
    if b <= a:
        return 0.0
    w_inner, w_outer = -2.0 * corners[0][1], -2.0 * corners[1][1]
    slope = (w_outer - w_inner) / (outer - inner)
    # w(r) = w_inner + slope * (r - inner) = c0 + slope * r
    c0 = w_inner - slope * inner

    def f(r):
        return c0 * r * r / 2.0 + slope * r**3 / 3.0

    return f(b) - f(a)


def removed_area(major_radius, pitch, internal, face_radius, limit=None, form="iso"):
    """Area of one cross section (across the axis) of the material a modeled thread removes
    from a cylinder of radius `face_radius`: a shaft (external) or a hole (internal). The
    thread has its standard size whatever the cylinder was, as Fusion's modeled thread has
    (Autodesk: "Fusion will adjust the diameter of a threaded hole to the minor diameter of
    the thread"; a shaft gets the thread's major diameter): a shaft wider than the thread is
    turned down to the major diameter and a narrower one built up to it, a hole narrower
    than the minor diameter is bored up to it and a wider one filled in to it. Material that
    is added counts as negative. `limit`: the radius the shaft gets / the hole gets
    (default: the profile's own major radius / minor radius; a tolerance class sets them,
    see class_radii)."""
    r = float(major_radius)
    face = float(face_radius)
    two_pi_over_p = 2.0 * math.pi / pitch
    if internal:
        minor = r - thread_depth(pitch, form, True) if limit is None else float(limit)
        bore = math.pi * (minor**2 - face**2)  # negative: the hole is filled in to the minor
        return bore + two_pi_over_p * _integral_rw(r, pitch, True, minor, r, form)
    outer = r if limit is None else float(limit)
    turn = math.pi * (face**2 - outer**2)  # negative: the shaft is built up to the major
    return turn + two_pi_over_p * _integral_rw(r, pitch, False, 0.0, outer, form)


def removed_volume(major_radius, pitch, internal, face_radius, length, limit=None, form="iso"):
    return removed_area(major_radius, pitch, internal, face_radius, limit, form) * float(length)


def class_radii(diameter, internal, zone):
    """(profile major radius, turned / bored radius) of a modeled thread whose tolerance
    class puts it where `zone` says (thread_tables.class_zone): the profile moves out by
    half the zone's shift; a shaft is turned to the middle of the class's major diameter,
    a hole bored to the middle of its minor diameter."""
    radius = (float(diameter) + zone["shift"]) / 2.0
    limit = zone["minor"] / 2.0 if internal else zone["major"] / 2.0
    return radius, limit


def span(face_start, face_end, full_length=True, length=0.0, offset=0.0, from_end=False):
    """(z0, z1) the thread covers along a cylinder that runs from face_start to face_end
    (positions along its axis). Full length: all of it. Otherwise `length` long, starting
    `offset` in from the start (or from the end when from_end: the end nearer the click),
    and never past the face."""
    lo, hi = min(face_start, face_end), max(face_start, face_end)
    if full_length:
        return lo, hi
    length = max(0.0, float(length))
    offset = max(0.0, float(offset))
    if from_end:
        z1 = hi - offset
        z0 = z1 - length
    else:
        z0 = lo + offset
        z1 = z0 + length
    return max(lo, z0), min(hi, z1)


def helix_points(radius, pitch, z0, z1, per_turn=24, left_hand=False, phase=0.0):
    """Points (x, y, z) of a helix around the z axis from z0 to z1 (for drawing a cosmetic
    thread). Right-handed: it turns counter-clockwise going up."""
    if z1 <= z0 or pitch <= 0:
        return []
    turns = (z1 - z0) / pitch
    count = max(2, int(math.ceil(turns * per_turn)) + 1)
    sign = -1.0 if left_hand else 1.0
    points = []
    for i in range(count):
        t = i / float(count - 1)
        z = z0 + (z1 - z0) * t
        angle = phase + sign * 2.0 * math.pi * (z - z0) / pitch
        points.append((radius * math.cos(angle), radius * math.sin(angle), z))
    return points


def class_removed_volume(designation, thread_class, internal, face_radius, length):
    """removed_volume for a modeled thread of a tolerance class (thread_tables.class_zone):
    what Fission 180's Thread cuts, worked out by hand (tests compare with it)."""
    from . import thread_tables

    zone = thread_tables.class_zone(designation, thread_class, internal)
    radius, limit = class_radii(designation.diameter, internal, zone)
    form = getattr(designation, "form", "iso")
    return removed_volume(radius, designation.pitch, internal, face_radius, length, limit, form)
