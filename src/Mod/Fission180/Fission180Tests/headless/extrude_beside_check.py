# SPDX-License-Identifier: LGPL-2.1-or-later
"""A Join of a solid that only lies against the body along a curve (the book's surfboard
fin under the board) is the two solids side by side in one body; any other Join is their
union, and the tests that tell them apart use points only (fission180/extrude_bodies.py:
beside, join_shape, _curve_contact, _same_surface). Real FreeCAD, no window; run by
Fission180Tests/unit/test_extrude_beside_freecad.py. Prints "beside check BAD <what>" for
every failed check and "beside check done <n>" at the end."""

import FreeCAD as App
import Part

from fission180 import extrude_bodies as eb

V = App.Vector
_count = [0]


def _print(ok, what):
    _count[0] += 1
    print("beside check %s %s" % ("ok" if ok else "BAD", what), flush=True)


def _box(x, y, z, size=10.0):
    return Part.makeBox(size, size, size, V(x, y, z))


def main():
    base = _box(0, 0, 0)
    cases = (
        ("only an edge in common", _box(10, 10, 0), True),
        ("a face in common", _box(0, 0, 10), False),
        ("overlapping", _box(5, 5, 5), False),
        ("apart", _box(20, 0, 0), False),
        ("a corner in common", _box(10, 10, 10), False),
    )
    for name, tool, want in cases:
        _print(eb.beside(base, tool) == want, "beside, %s: %s" % (name, want))
        joined = eb.join_shape(base, tool)
        if want:
            _print(
                len(joined.Solids) == 2 and abs(joined.Volume - 2000.0) < 1e-6,
                "join, %s: the two solids side by side" % name,
            )
        elif name in ("a face in common", "overlapping"):
            _print(len(joined.Solids) == 1, "join, %s: one solid (their union)" % name)
    _print(eb._curve_contact(base, _box(10, 10, 0)), "curve contact along a shared edge")
    _print(not eb._curve_contact(base, _box(20, 0, 0)), "no curve contact when apart")
    # a curve given (a symmetric extrude's profile, inside the solid it sweeps) on the body:
    # a rod lying on the box's top touches it along a line that is no edge of the rod
    rod = Part.makeCylinder(1.0, 10.0, V(0, 5, 11), V(1, 0, 0))
    line = Part.LineSegment(V(0, 5, 10), V(10, 5, 10)).toShape()
    _print(not eb._curve_contact(base, rod), "a rod on the box: none of its edges on it")
    _print(eb._curve_contact(base, rod, [line]), "...the line it lies on, given: contact")
    _print(eb.beside(base, rod, [line]), "...so the rod lies beside the box")
    # two faces that only meet along a line are not on one surface; two that overlap are
    top = base.Faces[5]  # z = 10
    lid = _box(0, 0, 10).Faces[4]  # z = 10 too
    side = _box(10, 0, 0).Faces[0]  # x = 10, meets the base's x = 10 face: same plane
    far = _box(0, 0, 20).Faces[4]
    _print(eb._same_surface(top, lid, 1e-6), "same surface: two faces on z = 10")
    _print(not eb._same_surface(top, far, 1e-6), "not the same surface: z = 10 and z = 20")
    _print(eb._same_surface(base.Faces[1], side, 1e-6), "same surface: two faces on x = 10")
    sphere = Part.makeSphere(5, V(0, 0, 0)).Faces[0]
    ball = Part.makeSphere(5, V(10, 0, 0)).Faces[0]
    _print(
        not eb._same_surface(sphere, ball, 1e-6), "two balls touching at a point: not one surface"
    )
    print("beside check done %d" % _count[0], flush=True)


if __name__ == "__main__":
    main()
