# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's sketch Offset: chains of picked curves, sharp corners, the pointer's distance and
side, the furthest an inner offset can go (no FreeCAD)."""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fission180 import sketch_offset_core as core  # noqa: E402


def near(a, b, tol=1e-7):
    return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol


def line(a, b):
    return ("line", a, b)


def rectangle(x0=0.0, y0=0.0, x1=30.0, y1=20.0):
    """Four lines drawn clockwise (as a hand might), keys 0-3."""
    return {
        0: line((x0, y0), (x0, y1)),
        1: line((x0, y1), (x1, y1)),
        2: line((x1, y1), (x1, y0)),
        3: line((x1, y0), (x0, y0)),
    }


def box_of(curves):
    xs = [p[0] for c in curves for p in core.points(c, 16)]
    ys = [p[1] for c in curves for p in core.points(c, 16)]
    return (min(xs), min(ys), max(xs), max(ys))


def slot():
    """A slot: two lines and two half circles, joined smoothly (keys 0-3)."""
    return {
        0: line((0.0, 0.0), (20.0, 0.0)),
        1: ("arc", (20.0, 5.0), 5.0, -math.pi / 2, math.pi / 2),
        2: line((20.0, 10.0), (0.0, 10.0)),
        3: ("arc", (0.0, 5.0), 5.0, math.pi / 2, 3 * math.pi / 2),
    }


class Chains(unittest.TestCase):
    def test_rectangle_is_one_closed_anticlockwise_chain(self):
        curves = rectangle()
        found = core.chains(curves)
        self.assertEqual(len(found), 1)
        chain = found[0]
        self.assertTrue(chain.closed)
        self.assertEqual(sorted(chain.keys()), [0, 1, 2, 3])
        self.assertGreater(core._signed_area(chain, curves), 0)  # turned anticlockwise
        self.assertEqual(chain.smooth, [False] * 4)

    def test_single_line_is_an_open_chain(self):
        found = core.chains({7: line((0.0, 0.0), (10.0, 0.0))})
        self.assertEqual(len(found), 1)
        self.assertFalse(found[0].closed)
        self.assertEqual(found[0].items, [(7, False)])

    def test_open_chain_in_any_pick_order(self):
        curves = {
            "b": line((10.0, 0.0), (10.0, 10.0)),
            "a": line((0.0, 0.0), (10.0, 0.0)),
            "c": line((20.0, 10.0), (10.0, 10.0)),
        }
        found = core.chains(curves, order=["b", "c", "a"])
        self.assertEqual(len(found), 1)
        chain = found[0]
        self.assertFalse(chain.closed)
        self.assertEqual([k for k, _r in chain.items][1], "b")  # b in the middle
        # walked end to end: each item starts where the one before ends
        for (k1, r1), (k2, r2) in zip(chain.items, chain.items[1:]):
            end = core.travel_ends(curves[k1], r1)[1]
            start = core.travel_ends(curves[k2], r2)[0]
            self.assertTrue(near(end, start))

    def test_separate_curves_are_separate_chains(self):
        curves = {1: line((0.0, 0.0), (10.0, 0.0)), 2: line((0.0, 5.0), (10.0, 5.0))}
        self.assertEqual(len(core.chains(curves)), 2)

    def test_circle_is_a_chain_of_its_own(self):
        found = core.chains({1: ("circle", (0.0, 0.0), 5.0)})
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0].closed)

    def test_slot_joints_are_smooth(self):
        found = core.chains(slot())
        self.assertEqual(len(found), 1)
        self.assertTrue(found[0].closed)
        self.assertEqual(found[0].smooth, [True] * 4)

    def test_branches_split_chains(self):
        # a T: three lines meeting at (10, 0)
        curves = {
            1: line((0.0, 0.0), (10.0, 0.0)),
            2: line((10.0, 0.0), (20.0, 0.0)),
            3: line((10.0, 0.0), (10.0, 10.0)),
        }
        found = core.chains(curves)
        self.assertEqual(sorted(sorted(c.keys()) for c in found), [[1], [2], [3]])


class Offsets(unittest.TestCase):
    def test_rectangle_outwards_has_sharp_corners(self):
        curves = rectangle()
        found = core.chains(curves)
        out = core.offset(found[0], curves, 3.0)
        self.assertEqual([c[0] for c in out], ["line"] * 4)
        self.assertTrue(near(box_of(out), (-3.0, -3.0, 33.0, 23.0)))
        # corners meet exactly (a closed outline)
        pts = [p for c in out for p in (c[1], c[2])]
        for corner in ((-3.0, -3.0), (33.0, -3.0), (33.0, 23.0), (-3.0, 23.0)):
            self.assertEqual(sum(1 for p in pts if near(p, corner)), 2, corner)

    def test_rectangle_inwards(self):
        curves = rectangle()
        out = core.offset(core.chains(curves)[0], curves, -4.0)
        self.assertTrue(near(box_of(out), (4.0, 4.0, 26.0, 16.0)))

    def test_too_far_inwards_is_refused(self):
        curves = rectangle()
        with self.assertRaises(core.OffsetError):
            core.offset(core.chains(curves)[0], curves, -11.0)

    def test_each_offset_line_keeps_its_original_direction(self):
        curves = rectangle()
        chain = core.chains(curves)[0]
        out = core.offset(chain, curves, 2.0)
        for (k, _r), moved in zip(chain.items, out):
            a, b = curves[k][1], curves[k][2]
            u = (b[0] - a[0], b[1] - a[1])
            v = (moved[2][0] - moved[1][0], moved[2][1] - moved[1][1])
            self.assertGreater(u[0] * v[0] + u[1] * v[1], 0)

    def test_single_line_both_sides(self):
        curves = {1: line((0.0, 0.0), (10.0, 0.0))}
        chain = core.chains(curves)[0]
        right = core.offset(chain, curves, 2.0)[0]
        left = core.offset(chain, curves, -2.0)[0]
        self.assertTrue(near(right[1], (0.0, -2.0)) and near(right[2], (10.0, -2.0)))
        self.assertTrue(near(left[1], (0.0, 2.0)) and near(left[2], (10.0, 2.0)))

    def test_open_l_keeps_its_ends_square(self):
        curves = {1: line((0.0, 0.0), (10.0, 0.0)), 2: line((10.0, 0.0), (10.0, 10.0))}
        chain = core.chains(curves)[0]
        # the side away from the inside of the L
        d = 2.0 if chain.items[0][0] == 1 else -2.0
        out = core.offset(chain, curves, d)
        pts = sorted({(round(p[0], 9), round(p[1], 9)) for c in out for p in (c[1], c[2])})
        self.assertEqual(pts, [(0.0, -2.0), (12.0, -2.0), (12.0, 10.0)])

    def test_circle(self):
        curves = {1: ("circle", (5.0, 5.0), 4.0)}
        chain = core.chains(curves)[0]
        self.assertAlmostEqual(core.offset(chain, curves, 3.0)[0][2], 7.0)
        self.assertAlmostEqual(core.offset(chain, curves, -3.0)[0][2], 1.0)
        with self.assertRaises(core.OffsetError):
            core.offset(chain, curves, -4.0)

    def test_single_arc(self):
        arc = ("arc", (0.0, 0.0), 10.0, 0.0, math.pi / 2)
        chain = core.chains({1: arc})[0]
        out = core.offset(chain, {1: arc}, 2.0)[0]
        self.assertEqual(out[0], "arc")
        self.assertAlmostEqual(abs(out[2] - 10.0), 2.0)
        self.assertAlmostEqual(out[3], 0.0)
        self.assertAlmostEqual(out[4], math.pi / 2)

    def test_slot_stays_smooth(self):
        curves = slot()
        chain = core.chains(curves)[0]
        out = core.offset(chain, curves, 1.0)
        self.assertTrue(near(box_of(out), (-6.0, -1.0, 26.0, 11.0), 1e-3))
        radii = sorted(c[2] for c in out if c[0] == "arc")
        self.assertAlmostEqual(radii[0], 6.0)
        self.assertAlmostEqual(radii[1], 6.0)

    def test_line_and_arc_corner(self):
        # a line into a quarter arc that turns back on it (a corner, not smooth)
        curves = {
            1: line((0.0, 0.0), (10.0, 0.0)),
            2: ("arc", (10.0, 10.0), 10.0, -math.pi / 2, 0.0),
            3: line((20.0, 10.0), (0.0, 0.0)),
        }
        chain = core.chains(curves)[0]
        self.assertTrue(chain.closed)
        out = core.offset(chain, curves, 1.0)
        self.assertEqual(len(out), 3)
        # the outline is still closed: every curve ends where the next one starts
        revs = [r for _k, r in chain.items]
        for i in range(3):
            end = core.travel_ends(out[i], revs[i])[1]
            start = core.travel_ends(out[(i + 1) % 3], revs[(i + 1) % 3])[0]
            self.assertTrue(near(end, start, 1e-6), (i, end, start))
        # the arc moved out by 1 (its centre stays)
        arc = [c for c in out if c[0] == "arc"][0]
        self.assertAlmostEqual(arc[2], 11.0)

    def test_largest_inner_offset_of_a_rectangle(self):
        curves = rectangle()
        found = core.chains(curves)
        limit = core.largest(found, curves, -1, 30.0)
        self.assertAlmostEqual(limit, 10.0, places=6)

    def test_outer_side_has_no_limit(self):
        curves = rectangle()
        self.assertTrue(core.works(core.chains(curves), curves, 500.0))


class Pointer(unittest.TestCase):
    def test_outside_a_rectangle(self):
        curves = rectangle()
        found = core.chains(curves)
        d, side, _ci = core.pointer(found, curves, (15.0, -4.0))
        self.assertAlmostEqual(d, 4.0)
        self.assertEqual(side, 1)

    def test_inside_a_rectangle(self):
        curves = rectangle()
        found = core.chains(curves)
        d, side, _ci = core.pointer(found, curves, (15.0, 3.0))
        self.assertAlmostEqual(d, 3.0)
        self.assertEqual(side, -1)

    def test_the_offset_runs_through_the_pointer(self):
        curves = rectangle()
        found = core.chains(curves)
        d, side, _ci = core.pointer(found, curves, (34.0, 10.0))
        out = core.offset(found[0], curves, side * d)
        self.assertTrue(near(box_of(out), (-4.0, -4.0, 34.0, 24.0)))

    def test_either_side_of_a_line(self):
        curves = {1: line((0.0, 0.0), (10.0, 0.0))}
        found = core.chains(curves)
        d1, s1, _ = core.pointer(found, curves, (5.0, 3.0))
        d2, s2, _ = core.pointer(found, curves, (5.0, -3.0))
        self.assertAlmostEqual(d1, 3.0)
        self.assertAlmostEqual(d2, 3.0)
        self.assertNotEqual(s1, s2)
        out = core.offset(found[0], curves, s2 * d2)[0]
        self.assertAlmostEqual(out[1][1], -3.0)

    def test_circle_inside_and_out(self):
        curves = {1: ("circle", (0.0, 0.0), 10.0)}
        found = core.chains(curves)
        d, side, _ = core.pointer(found, curves, (13.0, 0.0))
        self.assertEqual((round(d, 9), side), (3.0, 1))
        d, side, _ = core.pointer(found, curves, (0.0, 6.0))
        self.assertEqual((round(d, 9), side), (4.0, -1))


class Defaults(unittest.TestCase):
    def test_nice(self):
        self.assertEqual(core.nice(3.2), 5.0)
        self.assertEqual(core.nice(1.1), 1.0)
        self.assertEqual(core.nice(0.3), 0.2)
        self.assertEqual(core.nice(14.0), 10.0)


if __name__ == "__main__":
    unittest.main()
