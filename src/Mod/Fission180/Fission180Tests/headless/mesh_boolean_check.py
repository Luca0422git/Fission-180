# SPDX-License-Identifier: LGPL-2.1-or-later
"""Mesh Combine gives the right closed body whatever the order of the facets (fix-2), in
real FreeCAD without a window; run by Fission180Tests/unit/test_mesh_boolean_freecad.py.
Prints "mesh boolean BAD <what>" for every failed check and "mesh boolean done <n>".

FreeCAD's mesh booleans depend on the facets' order: a 10 mm cube and a 10 x 6 x 6 bar
that pokes 5 mm into it, their facets shuffled, gave Intersect 120 (not 180) or Cut 880
(not 820), open, about once in a hundred (the GitHub flake of mesh_separate_combine D).
Numbers by hand: Join 1000 + 360 - 180 = 1180, Cut 820, Intersect 5 x 6 x 6 = 180."""

import random

import Mesh

from fission180 import mesh

WANT = {"Join": 1180.0, "Cut": 820.0, "Intersect": 180.0}
_count = [0]


def _print(ok, what):
    _count[0] += 1
    print("mesh boolean %s %s" % ("ok" if ok else "BAD", what), flush=True)


def box(x0, y0, z0, x1, y1, z1):
    p = [
        (x0, y0, z0),
        (x1, y0, z0),
        (x1, y1, z0),
        (x0, y1, z0),
        (x0, y0, z1),
        (x1, y0, z1),
        (x1, y1, z1),
        (x0, y1, z1),
    ]
    quads = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    tris = []
    for a, b, c, d in quads:
        tris.append([p[a], p[b], p[c]])
        tris.append([p[a], p[c], p[d]])
    return tris


def shuffled(tris, rng):
    tris = list(tris)
    rng.shuffle(tris)
    return Mesh.Mesh([t[k:] + t[:k] for t, k in ((t, rng.randrange(3)) for t in tris)])


def main():
    rng = random.Random(1)  # (seed 1: two of these 300 orders broke Intersect, six Cut)
    cube, bar = box(0, 0, 0, 10, 10, 10), box(5, 2, 2, 15, 8, 8)
    bad = {}
    for _ in range(300):
        a, b = shuffled(cube, rng), shuffled(bar, rng)
        for op, want in WANT.items():
            try:
                r = mesh.combine_meshes(a, [b], op)
                ok = abs(r.Volume - want) < 1e-6 and r.isSolid()
                got = (round(r.Volume, 3), r.isSolid())
            except Exception as exc:
                ok, got = False, str(exc)
            if not ok:
                bad.setdefault(op, []).append(got)
    for op in WANT:
        _print(op not in bad, "%s right and closed for 300 facet orders %r" % (op, bad.get(op)))
    print("mesh boolean done %d" % _count[0], flush=True)
