# SPDX-License-Identifier: LGPL-2.1-or-later
"""The decisions of the Sketch Dimension tool (fission180/sketch_dimension_core.py)."""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fission180 import sketch_dimension_core as dc  # noqa: E402

A, B = (0.0, 0.0), (10.0, 10.0)  # a line at 45 degrees


class LinearKind(unittest.TestCase):
    def test_beside_a_slanted_line_is_aligned(self):
        # the report (Strandbeest): Fusion offers the aligned length of a slanted line
        self.assertEqual(dc.linear_kind(A, B, (8.0, 2.0)), dc.ALIGNED)
        self.assertEqual(dc.linear_kind(A, B, (2.0, 8.0)), dc.ALIGNED)

    def test_far_below_is_horizontal(self):
        self.assertEqual(dc.linear_kind(A, B, (5.0, -10.0)), dc.HORIZONTAL)
        self.assertEqual(dc.linear_kind(A, B, (5.0, 25.0)), dc.HORIZONTAL)

    def test_far_to_the_side_is_vertical(self):
        self.assertEqual(dc.linear_kind(A, B, (25.0, 5.0)), dc.VERTICAL)
        self.assertEqual(dc.linear_kind(A, B, (-12.0, 5.0)), dc.VERTICAL)

    def test_a_level_or_upright_line_is_always_aligned(self):
        for cursor in ((5.0, -30.0), (40.0, 3.0), (-9.0, -9.0)):
            self.assertEqual(dc.linear_kind((0, 0), (10, 0), cursor), dc.ALIGNED)
            self.assertEqual(dc.linear_kind((0, 0), (0, 10), cursor), dc.ALIGNED)

    def test_two_points_at_one_place(self):
        self.assertEqual(dc.linear_kind((1, 1), (1, 1), (5, 5)), dc.ALIGNED)

    def test_past_the_ends_in_a_corner_the_farther_side_wins(self):
        self.assertEqual(dc.linear_kind(A, B, (-3.0, -20.0)), dc.HORIZONTAL)
        self.assertEqual(dc.linear_kind(A, B, (-20.0, -3.0)), dc.VERTICAL)


class Measure(unittest.TestCase):
    def test_sizes(self):
        self.assertAlmostEqual(dc.measure(dc.ALIGNED, (0, 0), (3, 4)), 5.0)
        self.assertAlmostEqual(dc.measure(dc.HORIZONTAL, (0, 0), (-3, 4)), 3.0)
        self.assertAlmostEqual(dc.measure(dc.VERTICAL, (0, 9), (3, 4)), 5.0)

    def test_order_for_a_positive_value(self):
        self.assertTrue(dc.ordered(dc.HORIZONTAL, (0, 0), (3, -4)))
        self.assertFalse(dc.ordered(dc.HORIZONTAL, (5, 0), (3, 4)))
        self.assertFalse(dc.ordered(dc.VERTICAL, (0, 5), (3, 4)))
        self.assertTrue(dc.ordered(dc.ALIGNED, (9, 9), (0, 0)))


class Lines(unittest.TestCase):
    def test_parallel(self):
        self.assertTrue(dc.parallel((1, 0), (-5, 0)))
        self.assertTrue(dc.parallel((1, 1), (2, 2.0000001)))
        self.assertFalse(dc.parallel((1, 0), (1, 0.01)))

    def test_point_line_distance_and_foot(self):
        self.assertAlmostEqual(dc.point_line_distance((3, 4), (0, 0), (1, 0)), 4.0)
        f = dc.foot((3, 4), (0, 0), (2, 0))
        self.assertAlmostEqual(f[0], 3.0)
        self.assertAlmostEqual(f[1], 0.0)

    def test_crossing(self):
        c = dc.crossing((0, 0), (1, 0), (5, -5), (0, 1))
        self.assertAlmostEqual(c[0], 5.0)
        self.assertAlmostEqual(c[1], 0.0)
        self.assertIsNone(dc.crossing((0, 0), (1, 0), (0, 1), (2, 0)))

    def test_angle_follows_the_sector_the_pointer_is_in(self):
        # X axis and a line at 60 degrees through the origin
        d2 = (math.cos(math.radians(60)), math.sin(math.radians(60)))
        s1, s2, angle, corner = dc.angle_sector((0, 0), (1, 0), (0, 0), d2, (10, 3))
        self.assertEqual((s1, s2), (1, 1))
        self.assertAlmostEqual(math.degrees(angle), 60.0)
        s1, s2, angle, corner = dc.angle_sector((0, 0), (1, 0), (0, 0), d2, (-10, 3))
        self.assertEqual((s1, s2), (-1, 1))
        self.assertAlmostEqual(math.degrees(angle), 120.0)
        s1, s2, angle, corner = dc.angle_sector((0, 0), (1, 0), (0, 0), d2, (-10, -3))
        self.assertEqual((s1, s2), (-1, -1))
        self.assertAlmostEqual(math.degrees(angle), 60.0)
        self.assertIsNone(dc.angle_sector((0, 0), (1, 0), (0, 5), (1, 0), (1, 1)))

    def test_signed_angle(self):
        self.assertAlmostEqual(dc.signed_angle((1, 0), (0, 1)), math.pi / 2)
        self.assertAlmostEqual(dc.signed_angle((0, 1), (1, 0)), -math.pi / 2)


class Labels(unittest.TestCase):
    def test_linear_label_above_the_middle(self):
        distance, position = dc.linear_label(dc.ALIGNED, (0, 0), (10, 0), (7, 4))
        self.assertAlmostEqual(distance, 4.0)
        self.assertAlmostEqual(position, 2.0)

    def test_horizontal_label_uses_the_level_stretch(self):
        distance, position = dc.linear_label(dc.HORIZONTAL, (0, 0), (10, 6), (5, -3))
        self.assertAlmostEqual(distance, -3.0)
        self.assertAlmostEqual(position, 0.0)

    def test_radial_label(self):
        distance, angle = dc.radial_label((0, 0), 5.0, (0, 9))
        self.assertAlmostEqual(distance, 4.0)
        self.assertAlmostEqual(angle, math.pi / 2)

    def test_previews_are_lines(self):
        lines = dc.linear_preview(dc.ALIGNED, (0, 0), (10, 0), (5, 4))
        self.assertEqual(lines[2], [(0.0, 4.0), (10.0, 4.0)])
        lines = dc.linear_preview(dc.HORIZONTAL, (0, 0), (10, 6), (5, -3))
        self.assertEqual(lines[2], [(0, -3), (10, -3)])
        self.assertEqual(len(dc.radial_preview((0, 0), 5.0, (9, 0), True)[0]), 2)
        self.assertEqual(len(dc.angle_preview((0, 0), (1, 0), (0, 1), (3, 3))[0]), 25)


class Picks(unittest.TestCase):
    def test_the_first_click_on_a_thing_picks_it(self):
        for kind in (dc.POINT, dc.LINE, dc.CIRCLE, dc.ARC, dc.AXIS):
            self.assertTrue(dc.is_pick([], kind))
        self.assertFalse(dc.is_pick([], dc.OTHER))

    def test_with_two_picked_every_click_places(self):
        # the report (Drone): two parallel lines, then a click ON a third line placed
        # nothing and made Equal constraints
        for kind in (dc.POINT, dc.LINE, dc.CIRCLE, dc.ARC, dc.AXIS):
            self.assertFalse(dc.is_pick([dc.LINE, dc.LINE], kind))

    def test_a_second_line_is_a_pick(self):
        self.assertTrue(dc.is_pick([dc.LINE], dc.LINE))
        self.assertTrue(dc.is_pick([dc.POINT], dc.LINE))
        self.assertTrue(dc.is_pick([dc.CIRCLE], dc.POINT))

    def test_an_axis_after_a_line_places_the_dimension(self):
        # the report (Hot End): a line's length placed on top of the Y axis became an Angle
        self.assertFalse(dc.is_pick([dc.LINE], dc.AXIS))
        self.assertFalse(dc.is_pick([dc.CIRCLE], dc.AXIS))

    def test_an_axis_after_a_point_is_a_pick(self):
        self.assertTrue(dc.is_pick([dc.POINT], dc.AXIS))
        self.assertTrue(dc.is_pick([dc.AXIS], dc.LINE))
        self.assertFalse(dc.is_pick([dc.AXIS], dc.AXIS))

    def test_alone(self):
        self.assertTrue(dc.alone(dc.LINE))
        self.assertFalse(dc.alone(dc.POINT))
        self.assertFalse(dc.alone(dc.AXIS))


if __name__ == "__main__":
    unittest.main()
