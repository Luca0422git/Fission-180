# SPDX-License-Identifier: LGPL-2.1-or-later
"""The solids of the hardware library, built from hardware_core's numbers (FreeCAD's Part, no
Qt). Each part is drawn simply and exactly: plain cylinders, cones, hexagons and one torus, so
every hole and shank has clean circular edges and cylinder faces (Joint snaps to their axis)
and the volume can be worked out by hand (hardware_core.volume). What is drawn simply, on
purpose: threads are a plain cylinder at the nominal diameter unless "Modeled threads" is on
(then the Thread tool's own code cuts them: thread.build), a Phillips recess is two crossed
slots, a retaining ring has no lugs, a bearing's shields are a flat ring between its two
rings, heads have no chamfers.

The frame of every part (hardware_core.extent): its axis is z; z = 0 is the face it is put
on. Screws have the head's bearing face at z = 0 (a countersunk head: its top), set screws,
pins, bearings, inserts and magnets go down from z = 0, everything else up from it.
"""

import math

import FreeCAD as App

from . import hardware_core as core
from .hardware_core import HardwareError

Z = App.Vector(0, 0, 1)


def _cylinder(radius, z0, z1):
    import Part

    return Part.makeCylinder(radius, z1 - z0, App.Vector(0, 0, z0), Z)


def _tube(r_out, r_in, z0, z1):
    return _cylinder(r_out, z0, z1).cut(_cylinder(r_in, z0 - 1.0, z1 + 1.0))


def _hex_prism(s, z0, z1):
    """A hexagon s across the flats (flats parallel to x) from z0 to z1."""
    import Part

    r = s / math.sqrt(3.0)  # the corner radius
    points = [
        App.Vector(r * math.cos(math.radians(60 * i)), r * math.sin(math.radians(60 * i)), z0)
        for i in range(6)
    ]
    wire = Part.makePolygon(points + [points[0]])
    return Part.Face(wire).extrude(App.Vector(0, 0, z1 - z0))


def _box(x, y, z0, z1):
    """A box x by y centred on the axis, from z0 to z1."""
    import Part

    return Part.makeBox(x, y, z1 - z0, App.Vector(-x / 2.0, -y / 2.0, z0))


def _cap(base_radius, height, z0):
    """A spherical cap (a button head): base radius, height, its flat side at z0."""
    import Part

    big = core.cap_radius(base_radius, height)
    sphere = Part.makeSphere(big, App.Vector(0, 0, z0 + height - big))
    box = Part.makeBox(4 * big, 4 * big, height, App.Vector(-2 * big, -2 * big, z0))
    return sphere.common(box)


def _cone(r_top, r_bottom, z_bottom, z_top):
    import Part

    return Part.makeCone(r_bottom, r_top, z_top - z_bottom, App.Vector(0, 0, z_bottom), Z)


def _rounded(radius, height, r):
    """A cylinder from z = 0 to `height` whose top edge is rounded with radius r (a pan
    head)."""
    shape = _cylinder(radius, 0.0, height)
    if r <= 1e-6:
        return shape
    top = [
        e
        for e in shape.Edges
        if getattr(e.Curve, "TypeId", "") == "Part::GeomCircle"
        and abs(e.Curve.Center.z - height) < 1e-9
    ]
    return shape.makeFillet(r, top)


def _one(shape):
    shape = shape.removeSplitter()
    return shape.Solids[0] if len(shape.Solids) == 1 else shape


# -- the families ----------------------------------------------------------------------------------
def _screw(o, dm):
    d, dk, k, head = dm["d"], dm["dk"], dm["k"], dm["head"]
    length = o["length"]
    if head == "flat":
        top = 0.0
        body = _cone(dk / 2.0, d / 2.0, -k, 0.0).fuse(_cylinder(d / 2.0, -length, -k))
    else:
        top = k
        if head == "button":
            top_part = _cap(dk / 2.0, k, 0.0)
        elif head == "hex":
            top_part = _hex_prism(dm["af"], 0.0, k)
        elif head in ("pan_ph", "pan_sl"):
            top_part = _rounded(dk / 2.0, k, dm["r"])
        else:
            top_part = _cylinder(dk / 2.0, 0.0, k)
        body = top_part.fuse(_cylinder(d / 2.0, -length, 0.0))
    if head == "hex":
        return _one(body)
    if head == "pan_ph":
        z0 = top - dm["q"]
        drive = _box(dm["m"], dm["b"], z0, top + 1.0).fuse(_box(dm["b"], dm["m"], z0, top + 1.0))
    elif head == "pan_sl":
        drive = _box(dk + 2.0, dm["n"], top - dm["t"], top + 1.0)
    else:
        drive = _hex_prism(dm["s"], top - dm["t"], top + 1.0)
    return _one(body.cut(drive))


def _setscrew(o, dm):
    r, length = dm["d"] / 2.0, o["length"]
    h = core.point_height(dm, length)
    point = dm["point"]
    if point == "cup":
        import Part

        body = _cylinder(r, -length, 0.0)
        body = body.cut(Part.makeCone(dm["dv"] / 2.0, 0.0, h, App.Vector(0, 0, -length), Z))
    elif point == "dog":
        body = _cylinder(r, -(length - h), 0.0).fuse(
            _cylinder(dm["dog"] / 2.0, -length, -(length - h))
        )
    else:
        tip = (dm["dp"] if point == "flat" else dm["dt"]) / 2.0
        body = _cylinder(r, -(length - h), 0.0).fuse(_cone(r, tip, -length, -(length - h)))
    return _one(body.cut(_hex_prism(dm["s"], -core.socket_depth(o), 1.0)))


def _shoulder(o, dm):
    length = o["length"]
    body = _cylinder(dm["dk"] / 2.0, 0.0, dm["k"])
    body = body.fuse(_cylinder(dm["d1"] / 2.0, -length, 0.0))
    body = body.fuse(_cylinder(dm["d"] / 2.0, -length - dm["b"], -length))
    return _one(body.cut(_hex_prism(dm["s"], dm["k"] - dm["t"], dm["k"] + 1.0)))


def _washer(dm):
    import Part

    ring = _tube(dm["d2"] / 2.0, dm["d1"] / 2.0, 0.0, dm["h"])
    if "gap" in dm:  # a split lock washer, drawn flat: one straight slit
        gap = dm["gap"]
        ring = ring.cut(Part.makeBox(dm["d2"], gap, dm["h"] + 2.0, App.Vector(0, -gap / 2.0, -1)))
    return _one(ring)


def _oring(dm):
    import Part

    r = dm["cs"] / 2.0
    return Part.makeTorus((dm["id"] + dm["cs"]) / 2.0, r, App.Vector(0, 0, r), Z)


def _bearing(o, dm):
    import Part

    d, big, width = dm["d"], dm["D"], dm["B"]
    ring, ball, count, recess = core.bearing_section(dm)
    if o["variant"] != "open":
        # rings and shields in one piece: a ring with a shallow groove in each face
        body = _tube(big / 2.0, d / 2.0, -width, 0.0)
        for z0, z1 in ((-recess, 1.0), (-width - 1.0, -width + recess)):
            body = body.cut(
                _cylinder(big / 2.0 - ring, z0, z1).cut(_cylinder(d / 2.0 + ring, z0 - 1, z1 + 1))
            )
        return _one(body)
    section = (big - d) / 2.0
    ball = max(ball, 0.45 * section)  # the balls dip into both rings: one solid
    outer = _tube(big / 2.0, big / 2.0 - ring, -width, 0.0)
    inner = _tube(d / 2.0 + ring, d / 2.0, -width, 0.0)
    pitch = (big + d) / 4.0
    balls = []
    for i in range(count):
        a = 2.0 * math.pi * i / count
        centre = App.Vector(pitch * math.cos(a), pitch * math.sin(a), -width / 2.0)
        balls.append(Part.makeSphere(ball / 2.0, centre))
    return _one(outer.fuse([inner] + balls))


def _ring(dm):
    import Part

    inner, outer = core.ring_diameters(dm)
    s = dm["s"]
    body = _tube(outer / 2.0, inner / 2.0, 0.0, s)
    wedge = Part.makeCylinder(outer, s + 2.0, App.Vector(0, 0, -1), Z, core.RING_GAP)
    wedge.rotate(App.Vector(), Z, -core.RING_GAP / 2.0)
    return _one(body.cut(wedge))


def _pin(o, dm):
    r, c, length = dm["d"] / 2.0, dm["c"], o["length"]
    body = _cylinder(r, -length + c, -c)
    body = body.fuse(_cone(r - c, r, -c, 0.0))
    body = body.fuse(_cone(r, r - c, -length, -length + c))
    return _one(body)


def _key(o, dm):
    b, h, length = dm["b"], dm["h"], o["length"]
    if not dm["round_ends"]:
        return _box(length, b, 0.0, h)
    straight = length - b
    ends = []
    for x in (-straight / 2.0, straight / 2.0):
        end = _cylinder(b / 2.0, 0.0, h)
        end.translate(App.Vector(x, 0, 0))
        ends.append(end)
    if straight <= 1e-9:
        return ends[0]
    return _one(_box(straight, b, 0.0, h).fuse(ends))


def raw_solid(options):
    """The part in its own frame before the seat, the offset and Flip, with cosmetic
    threads (plain cylinders)."""
    o = core.check(options)
    dm = core.dims(o["standard"], o["size"], o["variant"])
    kind = o["kind"]
    if kind == "screw":
        return _screw(o, dm)
    if kind == "setscrew":
        return _setscrew(o, dm)
    if kind == "shoulder":
        return _shoulder(o, dm)
    if kind == "nut":
        return _one(
            _hex_prism(dm["s"], 0.0, dm["m"]).cut(_cylinder(dm["d"] / 2.0, -1, dm["m"] + 1))
        )
    if kind == "washer":
        return _washer(dm)
    if kind == "oring":
        return _oring(dm)
    if kind == "bearing":
        return _bearing(o, dm)
    if kind == "ring":
        return _ring(dm)
    if kind == "pin":
        return _pin(o, dm)
    if kind == "key":
        return _key(o, dm)
    if kind == "standoff":
        length = o["length"]
        if "af" in dm:
            return _one(
                _hex_prism(dm["af"], 0.0, length).cut(_cylinder(dm["d"] / 2.0, -1, length + 1))
            )
        return _one(_tube(dm["d2"] / 2.0, dm["d1"] / 2.0, 0.0, length))
    if kind == "insert":
        return _one(_tube(dm["outside"] / 2.0, dm["d"] / 2.0, -dm["length"], 0.0))
    return _one(_cylinder(dm["diameter"] / 2.0, -dm["thickness"], 0.0))


# -- modeled threads -------------------------------------------------------------------------------
def can_thread(options):
    """True for the parts "Modeled threads" changes (the others have no thread to show)."""
    o = core.with_defaults(options)
    if o["kind"] in ("screw", "setscrew", "shoulder", "nut"):
        return True
    return o["standard"] == "standoff_hex"


def _thread_face(shape, radius, lowest):
    """The thread's cylinder: the face of this radius about the z axis (the lowest one of a
    screw: its shank; the only one of a nut)."""
    found = []
    for face in shape.Faces:
        surface = face.Surface
        if getattr(surface, "TypeId", "") != "Part::GeomCylinder":
            continue
        if abs(surface.Radius - radius) > 1e-6 or abs(abs(surface.Axis.z) - 1.0) > 1e-9:
            continue
        if abs(surface.Center.x) > 1e-9 or abs(surface.Center.y) > 1e-9:
            continue
        found.append(face)
    if not found:
        return None
    return min(found, key=lambda f: f.BoundBox.ZMin) if lowest else found[0]


def threaded(shape, options):
    """`shape` (raw_solid) with its thread modeled: cut by the Thread tool's own code
    (thread.build: the ISO 68-1 profile of thread_tables' pitch, the shank turned to the
    thread's size). A screw is threaded from its tip over hardware_core.thread_length, a nut
    and a standoff right through."""
    from . import thread

    o = core.with_defaults(options)
    chosen = core.designation(o)
    if not can_thread(o) or chosen is None:
        return shape
    dm = core.dims(o["standard"], o["size"])
    internal = o["kind"] in ("nut", "standoff")
    face = _thread_face(shape, dm["d"] / 2.0, lowest=not internal)
    if face is None:
        return shape
    try:
        cylinder = thread.Cylinder(face)
        z0, z1 = cylinder.z0, cylinder.z1
        if not internal:
            long = min(core.thread_length(o), cylinder.length)
            if cylinder.axis.z > 0:  # the tip is the cylinder's low end
                z1 = z0 + long
            else:
                z0 = z1 - long
        return thread.build(shape, [cylinder], chosen, [(z0, z1)])
    except thread.ThreadError as exc:
        raise HardwareError("The thread could not be modeled (%s) Untick Modeled threads." % exc)


def solid(options):
    """The part in its own frame, threads modeled when asked."""
    o = core.check(options)
    shape = raw_solid(o)
    if o["modeled"]:
        shape = threaded(shape, o)
    return shape
