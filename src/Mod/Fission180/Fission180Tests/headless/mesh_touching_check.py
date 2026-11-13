# SPDX-License-Identifier: LGPL-2.1-or-later
"""MESH > Combine on bodies that touch, in real FreeCAD without a window; run in a FreeCAD
process of its own by Fission180Tests/unit/test_mesh_touching_freecad.py, so a crash fails
that test instead of killing the runner. Prints "mesh touching start <case>" before each
case (the last one shown is the one that crashed), "mesh touching ok|BAD <what>" for each
check and "mesh touching done <n>" at the end.

Before the fix a box and a cylinder standing on one floor crashed Fission 180 (a segfault in
FreeCAD's mesh booleans: MeshCore's Delaunay step), and other touching pairs gave wrong
bodies (a pyramid resting on a box: "Join gave nothing"; two identical boxes: Intersect of
volume 0). Volumes by hand; round bodies are polygons, so theirs are compared within 0.6 %."""

import math

import FreeCAD as App
import Mesh
import Part

from fission180 import mesh
from fission180.mesh_core import MeshError

V = App.Vector
_count = [0]


def _print(ok, what):
    _count[0] += 1
    print("mesh touching %s %s" % ("ok" if ok else "BAD", what), flush=True)


def tri(shape):
    found, _groups = mesh.tessellate_shape(shape, 0.08, 12.0)
    return found


def box(x, y, z, dx, dy, dz):
    return tri(Part.makeBox(dx, dy, dz, V(x, y, z)))


def cylinder(x, y, z, r, h):
    return tri(Part.makeCylinder(r, h, V(x, y, z)))


HALF_CYL = 0.5 * math.pi * 49 * 10  # the half of the r 7 cylinder inside the box, 10 high
CYL = math.pi * 49 * 14
CORE = math.pi * 16 * 10  # r 4, 10 high
CONE = math.pi * 9 * 4 / 3.0
NOTHING = None  # Combine refuses: nothing is left

# name: (target, tool, {operation: volume, or NOTHING})
CASES = {
    "cylinder on the box's floor (the crash)": (
        lambda: box(0, 0, 0, 30, 20, 10),
        lambda: cylinder(30, 10, 0, 7, 14),
        {"Join": 6000 + CYL - HALF_CYL, "Cut": 6000 - HALF_CYL, "Intersect": HALF_CYL},
    ),
    "cylinder flush through the box": (
        lambda: box(0, 0, 0, 30, 20, 10),
        lambda: cylinder(15, 10, 0, 4, 10),
        {"Join": 6000.0, "Cut": 6000 - CORE, "Intersect": CORE},
    ),
    "box stacked on a box": (
        lambda: box(0, 0, 0, 10, 10, 10),
        lambda: box(3, 3, 10, 10, 10, 5),
        {"Join": 1500.0, "Cut": 1000.0, "Intersect": NOTHING},
    ),
    "bar flush with a side": (
        lambda: box(0, 0, 0, 10, 10, 10),
        lambda: box(5, 0, 2, 10, 6, 6),
        {"Join": 1180.0, "Cut": 820.0, "Intersect": 180.0},
    ),
    "identical boxes": (
        lambda: box(0, 0, 0, 10, 10, 10),
        lambda: box(0, 0, 0, 10, 10, 10),
        {"Join": 1000.0, "Cut": NOTHING, "Intersect": 1000.0},
    ),
    "pocket flush with the top": (
        lambda: box(0, 0, 0, 20, 20, 10),
        lambda: box(5, 5, 5, 10, 10, 5),
        {"Join": 4000.0, "Cut": 3500.0, "Intersect": 500.0},
    ),
    "cone resting on its tip": (
        lambda: box(0, 0, 0, 10, 10, 10),
        lambda: tri(Part.makeCone(0, 3, 4, V(5, 5, 10))),
        {"Join": 1000 + CONE, "Cut": 1000.0, "Intersect": NOTHING},
    ),
    "box resting on an edge": (
        lambda: box(0, 0, 0, 10, 10, 10),
        lambda: tri(Part.makeBox(5, 5, 5, V(5, 2, 10)).rotated(V(5, 2, 10), V(1, 0, 0), 45)),
        {"Join": 1125.0, "Cut": 1000.0, "Intersect": NOTHING},
    ),
    "FreeCAD's own boxes, overlapping by half": (
        lambda: Mesh.createBox(10, 10, 10),
        lambda: _moved(Mesh.createBox(10, 10, 10), 5, 0, 0),
        {"Join": 1500.0, "Cut": 500.0, "Intersect": 500.0},
    ),
    "the crash, far from the origin": (
        lambda: _moved(box(0, 0, 0, 30, 20, 10), 1500, -2500, 800),
        lambda: _moved(cylinder(30, 10, 0, 7, 14), 1500, -2500, 800),
        {"Join": 6000 + CYL - HALF_CYL},
    ),
}


def _moved(m, x, y, z):
    m = m.copy()
    m.translate(x, y, z)
    return m


def _volume(m):
    """The volume measured near the origin: FreeCAD's Mesh.Volume adds up tetrahedra from the
    origin in single precision, so far away it is off (a 6,000 mm3 box at x = 1500 reads
    5,888) while the body is right."""
    m = m.copy()
    centre = m.BoundBox.Center
    m.translate(-centre.x, -centre.y, -centre.z)
    return m.Volume


def _check(name, target, tool, operation, want):
    print("mesh touching start %s %s" % (name, operation), flush=True)
    try:
        result = mesh.combine_meshes(target, [tool], operation)
        got = (round(_volume(result), 3), result.isSolid())
    except MeshError as exc:
        result, got = None, str(exc)
    except Exception as exc:  # anything else is a bug too
        _print(False, "%s %s raised %r" % (name, operation, exc))
        return
    if want is NOTHING:
        ok = result is None and ("nothing" in got or "covers the whole" in got)
    else:
        ok = (
            result is not None
            and result.isSolid()
            and abs(_volume(result) - want) <= max(1e-3, 0.006 * want)
        )
    _print(ok, "%s %s gives %r (want %r)" % (name, operation, got, want))


def main():
    # the reproduction as found (builder tips-workspaces, wave 8), word for word
    print("mesh touching start the reproduction", flush=True)
    b = tri(Part.makeBox(30, 20, 10))
    c = tri(Part.makeCylinder(7, 14, App.Vector(30, 10, 0)))
    r = mesh.combine_meshes(b, [c], "Join")
    _print(r.isSolid() and r.CountFacets > 0, "the reproduction gives a closed body")

    for name, (target, tool, wants) in CASES.items():
        a, t = target(), tool()
        for operation, want in wants.items():
            _check(name, a, t, operation, want)

    # too big for the exact way: refused in plain words, at once, never a crash
    print("mesh touching start a big plate and a cylinder on its floor", flush=True)
    plate = mesh.tessellate_shape(Part.makeBox(60, 60, 4), 0.08, 12.0, max_edge=0.8)[0]
    post = cylinder(30, 30, 0, 5, 10)
    try:
        mesh.combine_meshes(plate, [post], "Cut")
        _print(False, "a big floor-sharing Cut is refused (it was computed)")
    except MeshError as exc:
        _print(
            "share a flat face" in str(exc) and "Merge" in str(exc),
            "a big floor-sharing Cut is refused in plain words (%d faces): %s"
            % (plate.CountFacets + post.CountFacets, exc),
        )

    # bodies that do not touch still go through FreeCAD's mesh booleans, unchanged
    print("mesh touching start crossing bodies", flush=True)
    r = mesh.combine_meshes(box(0, 0, 0, 10, 10, 10), [box(5, 2, 2, 10, 6, 6)], "Join")
    _print(abs(r.Volume - 1180.0) < 1e-6 and r.isSolid(), "crossing bodies Join 1180")

    # Merge never combines faces: touching bodies are kept as they are
    print("mesh touching start Merge", flush=True)
    a, t = box(0, 0, 0, 30, 20, 10), cylinder(30, 10, 0, 7, 14)
    r = mesh.combine_meshes(a, [t], "Merge")
    _print(r.CountFacets == a.CountFacets + t.CountFacets, "Merge keeps both bodies' faces")
    print("mesh touching done %d" % _count[0], flush=True)
