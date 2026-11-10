# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's sketch Fillet between lines, arcs and circles: the arc, the fit, the pointer's
radius (no FreeCAD)."""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fission180 import sketch_fillet_core as core  # noqa: E402

BOTTOM = ("line", (0.0, 0.0), (40.0, 0.0))
RIGHT = ("line", (40.0, 0.0), (40.0, 30.0))
# a quarter arc from (55, 15) to (40, 0) about (55, 0): it leaves (40, 0) straight up
ARC = ("arc", (55.0, 0.0), 15.0, math.pi / 2, math.pi)


def near(a, b, tol=1e-7):
    return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol


class TwoLines(unittest.TestCase):
    def test_square_corner(self):
        centre, t1, t2 = core.fillet(BOTTOM, RIGHT, 5.0, (20.0, 0.0), (40.0, 15.0))
        self.assertTrue(near(centre, (35.0, 5.0)))
        self.assertTrue(near(t1, (35.0, 0.0)))
        self.assertTrue(near(t2, (40.0, 5.0)))

    def test_too_big_is_refused(self):
        with self.assertRaises(core.FilletError):
            core.check(BOTTOM, RIGHT, 45.0, (20.0, 0.0), (40.0, 15.0))

    def test_parallel_lines_make_none(self):
        top = ("line", (0.0, 10.0), (40.0, 10.0))
        with self.assertRaises(core.FilletError):
            core.fillet(BOTTOM, top, 5.0, (20.0, 0.0), (20.0, 10.0))

    def test_pointer_radius(self):
        # the arc passes as far from the corner as the pointer is: r (sqrt 2 - 1) = d
        r = core.radius_through(BOTTOM, RIGHT, (20.0, 0.0), (40.0, 15.0), (37.0, 3.0), 30.0)
        d = math.hypot(3.0, 3.0)
        self.assertAlmostEqual(r * (math.sqrt(2.0) - 1.0), d, places=6)

    def test_lines_that_do_not_touch(self):
        right = ("line", (40.0, 5.0), (40.0, 30.0))
        centre, t1, t2 = core.check(BOTTOM, right, 4.0, (20.0, 0.0), (40.0, 15.0))
        self.assertTrue(near(centre, (36.0, 4.0)))
        self.assertTrue(near(t2, (40.0, 4.0)))  # past the line's end: FreeCAD extends it


class LineAndArc(unittest.TestCase):
    def test_arc_touches_both(self):
        centre, t1, t2 = core.check(BOTTOM, ARC, 4.0, (20.0, 0.0), (44.4, 10.6))
        # 4 from the line and 15 + 4 from the arc's centre
        self.assertAlmostEqual(centre[1], 4.0)
        self.assertAlmostEqual(math.hypot(centre[0] - 55.0, centre[1]), 19.0)
        self.assertAlmostEqual(math.hypot(t2[0] - 55.0, t2[1]), 15.0)
        self.assertAlmostEqual(math.hypot(t2[0] - centre[0], t2[1] - centre[1]), 4.0)
        self.assertTrue(near(t1, (centre[0], 0.0)))

    def test_order_of_the_picks_does_not_matter(self):
        a = core.fillet(BOTTOM, ARC, 4.0, (20.0, 0.0), (44.4, 10.6))
        b = core.fillet(ARC, BOTTOM, 4.0, (44.4, 10.6), (20.0, 0.0))
        self.assertTrue(near(a[0], b[0]))

    def test_corner(self):
        self.assertTrue(near(core.corner_of(BOTTOM, ARC, (20.0, 0.0), (44.4, 10.6)), (40.0, 0.0)))

    def test_bigger_than_the_line(self):
        with self.assertRaises(core.FilletError):
            core.check(BOTTOM, ARC, 100.0, (20.0, 0.0), (44.4, 10.6))  # past (0, 0)

    def test_preview_arc_ends_on_the_touch_points(self):
        centre, t1, t2 = core.fillet(BOTTOM, ARC, 4.0, (20.0, 0.0), (44.4, 10.6))
        points = core.arc_points(centre, t1, t2)
        self.assertTrue(near(points[0], t1, 1e-9))
        self.assertTrue(near(points[-1], t2, 1e-9))


class Largest(unittest.TestCase):
    """Luca's limits (2026-10-21): the largest fillet runs to the far end of a curve and
    takes it whole: found exactly, so no sliver of the curve is left."""

    def test_square_corner_the_shorter_line(self):
        refs = ((20.0, 0.0), (40.0, 15.0))
        r = core.largest_radius(BOTTOM, RIGHT, refs[0], refs[1], 5.0)
        self.assertAlmostEqual(r, 30.0, places=9)  # the 30 mm line runs out
        self.assertEqual(core.takes_whole(BOTTOM, RIGHT, r, *refs), (False, True))
        rest1, rest2 = core.leftovers(BOTTOM, RIGHT, r, *refs)
        self.assertAlmostEqual(rest1, 10.0, places=6)
        self.assertGreaterEqual(rest2, 0.0)
        self.assertLess(rest2, 1e-9)
        # from a radius too big, the same limit
        self.assertAlmostEqual(core.largest_radius(BOTTOM, RIGHT, refs[0], refs[1], 80.0), r)

    def test_reaching_the_end_fits(self):
        refs = ((20.0, 0.0), (40.0, 15.0))
        core.check(BOTTOM, RIGHT, 30.0, *refs)  # the whole 30 mm line
        with self.assertRaises(core.FilletError):
            core.check(BOTTOM, RIGHT, 30.01, *refs)
        self.assertEqual(core.takes_whole(BOTTOM, RIGHT, 29.0, *refs), (False, False))

    def test_line_and_arc(self):
        refs = ((20.0, 0.0), (44.4, 10.6))
        r = core.largest_radius(BOTTOM, ARC, refs[0], refs[1], 4.0)
        self.assertIsNotNone(r)
        self.assertEqual(core.takes_whole(BOTTOM, ARC, r, *refs), (True, False))
        core.check(BOTTOM, ARC, r, *refs)
        with self.assertRaises(core.FilletError):
            core.check(BOTTOM, ARC, r * 1.001, *refs)

    def test_a_short_arc_runs_out(self):
        short = ("arc", (55.0, 0.0), 15.0, math.pi * 0.8, math.pi)
        refs = (
            (20.0, 0.0),
            (55.0 + 15.0 * math.cos(math.pi * 0.9), 15.0 * math.sin(math.pi * 0.9)),
        )
        r = core.largest_radius(BOTTOM, short, refs[0], refs[1], 4.0)
        self.assertEqual(core.takes_whole(BOTTOM, short, r, *refs), (False, True))
        self.assertAlmostEqual(core.leftovers(BOTTOM, short, r, *refs)[1], 0.0, places=9)

    def test_circles_have_no_limit_from_their_length(self):
        a = ("circle", (0.0, 0.0), 10.0)
        self.assertEqual(core.leftover(a, (10.0, 0.0), (10.0, 0.0)), None)


class Circles(unittest.TestCase):
    def test_two_circles(self):
        a = ("circle", (0.0, 0.0), 10.0)
        b = ("circle", (30.0, 0.0), 10.0)
        centre, t1, t2 = core.fillet(a, b, 8.0, (8.0, 6.0), (22.0, 6.0))
        self.assertAlmostEqual(math.hypot(*centre), 18.0)
        self.assertAlmostEqual(math.hypot(centre[0] - 30.0, centre[1]), 18.0)
        self.assertGreater(centre[1], 0.0)  # on the side of the picks

    def test_suggested_radius(self):
        self.assertAlmostEqual(core.suggested(BOTTOM, RIGHT), 6.0)


class SeveralCorners(unittest.TestCase):
    """Several corners filleted at once (Luca, 2026-11-02): two fillets on one line must
    leave a piece of it between them."""

    B = ("line", (0.0, 0.0), (40.0, 0.0))  # a 40 x 30 rectangle's bottom
    R = ("line", (40.0, 0.0), (40.0, 30.0))
    L = ("line", (0.0, 30.0), (0.0, 0.0))
    T = ("line", (40.0, 30.0), (0.0, 30.0))

    @staticmethod
    def mid(line):
        return ((line[1][0] + line[2][0]) / 2.0, (line[1][1] + line[2][1]) / 2.0)

    def corners(self, *pairs):
        sides = {"b": self.B, "r": self.R, "l": self.L, "t": self.T}
        return [
            (sides[a], sides[b], self.mid(sides[a]), self.mid(sides[b]), (a, b)) for a, b in pairs
        ]

    def test_two_corners_on_the_bottom_share_it(self):
        both = self.corners(("b", "l"), ("b", "r"))
        self.assertTrue(core.shared_fit(both, 10.0))
        self.assertFalse(core.shared_fit(both, 20.0))  # 20 + 20 would use the bottom up
        self.assertAlmostEqual(core.largest_shared(both, 25.0), 40.0 * 0.99 / 2.0, places=5)

    def test_corners_with_nothing_shared_keep_their_own_limit(self):
        apart = self.corners(("b", "l"), ("t", "r"))
        self.assertEqual(core.largest_shared(apart, 25.0), 25.0)

    def test_a_single_corner_is_not_limited_here(self):
        self.assertEqual(core.largest_shared(self.corners(("b", "l")), 28.0), 28.0)

    def test_three_corners_the_shorter_shared_side_rules(self):
        three = self.corners(("b", "l"), ("b", "r"), ("r", "t"))  # right side (30) shared too
        self.assertAlmostEqual(core.largest_shared(three, 25.0), 30.0 * 0.99 / 2.0, places=5)


class RadiusHandle(unittest.TestCase):
    """The arrow that drags the radius (Luca, 2026-11-10: the pointer no longer sizes it)."""

    REFS = ((20.0, 0.0), (40.0, 15.0))

    def test_it_stands_on_the_arc_middle(self):
        foot, d = core.handle(BOTTOM, RIGHT, 6.0, *self.REFS)
        # the arc about (34, 6): its middle 6 from the centre towards the corner (40, 0)
        k = 6.0 / math.sqrt(2.0)
        self.assertTrue(near(foot, (34.0 + k, 6.0 - k)))
        self.assertTrue(near(foot, core.arc_middle(BOTTOM, RIGHT, 6.0, *self.REFS)))

    def test_it_points_the_way_the_radius_grows(self):
        _foot, d = core.handle(BOTTOM, RIGHT, 6.0, *self.REFS)
        self.assertTrue(near(d, (-1.0 / math.sqrt(2.0), 1.0 / math.sqrt(2.0)), 1e-9))

    def test_dragged_along_it(self):
        foot, d = core.handle(BOTTOM, RIGHT, 6.0, *self.REFS)
        # the middle moves sqrt 2 - 1 per mm of radius in a square corner: 4 more of radius
        r = core.radius_along(
            BOTTOM, RIGHT, *self.REFS, foot, d, 4.0 * (math.sqrt(2.0) - 1.0), 1e-3, 30.0
        )
        self.assertAlmostEqual(r, 10.0, places=9)

    def test_not_dragged_stays(self):
        foot, d = core.handle(BOTTOM, RIGHT, 6.0, *self.REFS)
        r = core.radius_along(BOTTOM, RIGHT, *self.REFS, foot, d, 0.0, 1e-3, 30.0)
        self.assertAlmostEqual(r, 6.0, places=9)

    def test_past_the_ends_it_stops_there(self):
        foot, d = core.handle(BOTTOM, RIGHT, 6.0, *self.REFS)
        self.assertEqual(core.radius_along(BOTTOM, RIGHT, *self.REFS, foot, d, 500.0, 1e-3, 30.0), 30.0)
        self.assertEqual(core.radius_along(BOTTOM, RIGHT, *self.REFS, foot, d, -500.0, 0.5, 30.0), 0.5)

    def test_line_and_arc(self):
        refs = ((20.0, 0.0), (44.4, 10.6))
        foot, d = core.handle(BOTTOM, ARC, 4.0, *refs)
        r = core.radius_along(BOTTOM, ARC, *refs, foot, d, 0.0, 1e-3, 10.0)
        self.assertAlmostEqual(r, 4.0, places=7)
        # a little further along the arrow: a bigger radius, its middle where the arrow went
        r2 = core.radius_along(BOTTOM, ARC, *refs, foot, d, 0.5, 1e-3, 10.0)
        self.assertGreater(r2, 4.0)
        m = core.arc_middle(BOTTOM, ARC, r2, *refs)
        self.assertAlmostEqual((m[0] - foot[0]) * d[0] + (m[1] - foot[1]) * d[1], 0.5, places=7)

    def test_no_range_no_radius(self):
        foot, d = core.handle(BOTTOM, RIGHT, 6.0, *self.REFS)
        self.assertIsNone(core.radius_along(BOTTOM, RIGHT, *self.REFS, foot, d, 0.0, 5.0, 5.0))


if __name__ == "__main__":
    unittest.main()
