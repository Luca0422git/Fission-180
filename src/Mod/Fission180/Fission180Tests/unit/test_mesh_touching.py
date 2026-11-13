# SPDX-License-Identifier: LGPL-2.1-or-later
"""MESH > Combine's check for touching bodies (fission180/mesh_core.py touching): faces of
both in one plane crash FreeCAD's mesh booleans, a corner on the other's face gives wrong
bodies, so mesh.py combines those as exact solids. Runs without FreeCAD; the real booleans
are checked by test_mesh_touching_freecad.py."""

import os
import random
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fission180 import mesh_core as mc  # noqa: E402

TOL = 1e-4


def box(x0, y0, z0, x1, y1, z1):
    """A closed box, facets facing out (12 triangles)."""
    pts = [
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
    facets = []
    for a, b, c, d in quads:
        facets += [(a, b, c), (a, c, d)]
    return pts, facets


def pyramid(cx, cy, apex_z, base_z, half):
    """A square pyramid pointing down: its apex at (cx, cy, apex_z), its base above."""
    pts = [
        (cx - half, cy - half, base_z),
        (cx + half, cy - half, base_z),
        (cx + half, cy + half, base_z),
        (cx - half, cy + half, base_z),
        (cx, cy, apex_z),
    ]
    facets = [(0, 1, 2), (0, 2, 3), (1, 0, 4), (2, 1, 4), (3, 2, 4), (0, 3, 4)]
    return pts, facets


def wedge(x0, x1, cy, z, half, height):
    """A prism lying on one edge: the edge from (x0, cy, z) to (x1, cy, z), opening upwards."""
    pts = [
        (x0, cy, z),
        (x0, cy - half, z + height),
        (x0, cy + half, z + height),
        (x1, cy, z),
        (x1, cy - half, z + height),
        (x1, cy + half, z + height),
    ]
    facets = [
        (0, 2, 1),
        (3, 4, 5),
        (0, 1, 4),
        (0, 4, 3),
        (1, 2, 5),
        (1, 5, 4),
        (2, 0, 3),
        (2, 3, 5),
    ]
    return pts, facets


def subdivided(points, facets, times):
    """Every facet split into four, `times` times (a denser mesh of the same shape)."""
    for _ in range(times):
        pts = list(points)
        index = {}

        def middle(a, b):
            key = (min(a, b), max(a, b))
            if key not in index:
                p, q = pts[a], pts[b]
                pts.append(((p[0] + q[0]) / 2, (p[1] + q[1]) / 2, (p[2] + q[2]) / 2))
                index[key] = len(pts) - 1
            return index[key]

        out = []
        for a, b, c in facets:
            ab, bc, ca = middle(a, b), middle(b, c), middle(c, a)
            out += [(a, ab, ca), (ab, b, bc), (ca, bc, c), (ab, bc, ca)]
        points, facets = pts, out
    return points, facets


def touching(first, second, tolerance=TOL):
    return mc.touching(first[0], first[1], second[0], second[1], tolerance)


class Touching(unittest.TestCase):
    def test_far_apart(self):
        self.assertIsNone(touching(box(0, 0, 0, 10, 10, 10), box(20, 0, 0, 30, 10, 10)))

    def test_crossing_bodies_do_not_touch(self):
        # a bar poking into a cube (fix-2's pair): faces cross, none lies on another
        self.assertIsNone(touching(box(0, 0, 0, 10, 10, 10), box(5, 2, 2, 15, 8, 8)))

    def test_one_inside_the_other_does_not_touch(self):
        self.assertIsNone(touching(box(0, 0, 0, 10, 10, 10), box(2, 2, 2, 8, 8, 8)))

    def test_one_floor(self):
        # Luca's case in boxes: two bodies standing on z = 0, overlapping
        self.assertEqual(touching(box(0, 0, 0, 30, 20, 10), box(25, 5, 0, 40, 15, 14)), "plane")

    def test_stacked(self):
        # a top face on a bottom face (opposite directions, one plane)
        self.assertEqual(touching(box(0, 0, 0, 10, 10, 10), box(3, 3, 10, 13, 13, 15)), "plane")

    def test_side_by_side(self):
        self.assertEqual(touching(box(0, 0, 0, 10, 10, 10), box(10, 0, 0, 20, 10, 10)), "plane")

    def test_flush_pocket(self):
        # a tool flush with the target's top, inside it: a pocket cut
        self.assertEqual(touching(box(0, 0, 0, 20, 20, 10), box(5, 5, 5, 15, 15, 10)), "plane")

    def test_identical(self):
        self.assertEqual(touching(box(0, 0, 0, 10, 10, 10), box(0, 0, 0, 10, 10, 10)), "plane")

    def test_crossing_in_one_plane_without_a_corner_inside(self):
        # two bars on one floor crossing like a plus sign: no corner of either lies on the
        # other's bottom, the faces still overlap (the separating-axes path)
        self.assertEqual(touching(box(0, 10, 0, 30, 20, 5), box(10, 0, 0, 20, 30, 7)), "plane")

    def test_corner_on_a_face(self):
        self.assertEqual(touching(box(0, 0, 0, 10, 10, 10), pyramid(5, 5, 10, 14, 3)), "touch")

    def test_corner_on_an_edge_of_a_facet(self):
        # the apex on the diagonal that splits the top face into two facets
        self.assertEqual(touching(box(0, 0, 0, 10, 10, 10), pyramid(4, 4, 10, 14, 2)), "touch")

    def test_edge_on_a_face(self):
        # a prism resting on one edge that runs across the top face, its ends outside it
        self.assertEqual(touching(box(0, 0, 0, 10, 10, 10), wedge(-5, 15, 5, 10, 3, 4)), "touch")

    def test_hovering_corner_does_not_touch(self):
        self.assertIsNone(touching(box(0, 0, 0, 10, 10, 10), pyramid(5, 5, 10.5, 14, 3)))

    def test_corner_just_beside_the_face_does_not_touch(self):
        # in the top face's plane, but outside it
        self.assertIsNone(touching(box(0, 0, 0, 10, 10, 10), pyramid(10.5, 5, 10, 14, 0.2)))

    def test_within_the_tolerance(self):
        # single precision's rounding: still one plane
        self.assertEqual(
            touching(box(0, 0, 0, 30, 20, 10), box(25, 5, 0.5 * TOL, 40, 15, 14)), "plane"
        )

    def test_beyond_the_tolerance(self):
        self.assertIsNone(touching(box(0, 0, 0, 30, 20, 10), box(25, 5, 20 * TOL, 40, 15, 14)))

    def test_corner_counts_within_a_tenth_of_the_tolerance(self):
        near = pyramid(5, 5, 10 + 0.05 * TOL, 14, 3)
        self.assertEqual(touching(box(0, 0, 0, 10, 10, 10), near), "touch")
        nearly = pyramid(5, 5, 10 + 0.5 * TOL, 14, 3)
        self.assertIsNone(touching(box(0, 0, 0, 10, 10, 10), nearly))

    def test_plane_is_reported_before_touch(self):
        # a pyramid resting on the box and a floor-sharing slab, together in one body
        pts, facets = pyramid(5, 5, 10, 14, 3)
        slab_pts, slab_facets = box(-5, -5, 0, 2, 2, 3)
        offset = len(pts)
        moved = [(a + offset, b + offset, c + offset) for a, b, c in slab_facets]
        both = (pts + slab_pts, facets + moved)
        self.assertEqual(touching(box(0, 0, 0, 10, 10, 10), both), "plane")

    def test_either_order(self):
        cases = [
            (box(0, 0, 0, 30, 20, 10), box(25, 5, 0, 40, 15, 14), "plane"),
            (box(0, 0, 0, 10, 10, 10), pyramid(5, 5, 10, 14, 3), "touch"),
            (box(0, 0, 0, 10, 10, 10), box(5, 2, 2, 15, 8, 8), None),
        ]
        for first, second, want in cases:
            self.assertEqual(touching(first, second), want)
            self.assertEqual(touching(second, first), want)

    def test_facet_order_and_density_do_not_matter(self):
        rng = random.Random(3)
        target = subdivided(*box(0, 0, 0, 30, 20, 10), times=3)
        # (off the target's grid lines: x every 3.75, y every 2.5, z every 1.25)
        tool = subdivided(*box(26, 6, 0, 41, 16, 14), times=2)
        for _ in range(5):
            facets = list(tool[1])
            rng.shuffle(facets)
            self.assertEqual(touching(target, (tool[0], facets)), "plane")
        lifted = ([(x, y, z + 2.0) for x, y, z in tool[0]], tool[1])
        self.assertIsNone(touching(target, lifted))

    def test_degenerate_facets_are_ignored(self):
        pts, facets = box(25, 5, 0.5, 40, 15, 14)
        pts = pts + [(26, 6, 0), (26, 6, 0)]
        facets = facets + [(8, 9, 9)]  # no area, on the floor
        self.assertIsNone(touching(box(0, 0, 0, 30, 20, 10), (pts, facets)))

    def test_empty(self):
        self.assertIsNone(touching(([], []), box(0, 0, 0, 1, 1, 1)))


class Tolerance(unittest.TestCase):
    def test_grows_with_size_and_distance(self):
        small = mc.contact_tolerance(40.0, 30.0)
        self.assertGreater(mc.contact_tolerance(400.0, 30.0), small)
        self.assertGreater(mc.contact_tolerance(40.0, 3000.0), small)

    def test_above_single_precision(self):
        # single precision keeps about 7 digits: the tolerance is well above its rounding
        for diag, far in ((40.0, 30.0), (40.0, 5000.0), (2000.0, 1000.0)):
            self.assertGreater(mc.contact_tolerance(diag, far), far * 6e-8 * 5)

    def test_never_zero(self):
        self.assertGreater(mc.contact_tolerance(0.0, 0.0), 0.0)

    def test_words(self):
        self.assertIn("flat face", mc.contact_words("plane"))
        self.assertIn("touch", mc.contact_words("touch"))


if __name__ == "__main__":
    unittest.main()
