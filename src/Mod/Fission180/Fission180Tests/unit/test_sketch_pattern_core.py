# SPDX-License-Identifier: LGPL-2.1-or-later
"""The maths of the sketch Rectangular / Circular Pattern (fission180/sketch_pattern_core.py):
where the copies go, what a drag of a handle makes of the value, which constraints a copy
gets. Runs without FreeCAD."""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fission180 import sketch_pattern_core as core  # noqa: E402

U = core.GEO_UNDEF


def near(a, b, tol=1e-9):
    return abs(a[0] - b[0]) < tol and abs(a[1] - b[1]) < tol


def offsets(moves):
    return sorted((round(m[1][0], 9), round(m[1][1], 9)) for m in moves)


class RectMoves(unittest.TestCase):
    def test_extent_along_x(self):
        moves = core.rect_moves((1, 0), 3, 20.0, (0, 1), 1, 15.0)
        self.assertEqual(offsets(moves), [(10.0, 0.0), (20.0, 0.0)])

    def test_spacing_two_directions(self):
        moves = core.rect_moves((1, 0), 4, 10.0, (0, 1), 2, 15.0, "spacing")
        expect = sorted((10.0 * i, 15.0 * j) for i in range(4) for j in range(2))[1:]
        self.assertEqual(offsets(moves), expect)

    def test_extent_two_directions(self):
        moves = core.rect_moves((1, 0), 3, 20.0, (0, 1), 3, 30.0, "extent")
        expect = sorted((10.0 * i, 15.0 * j) for i in range(3) for j in range(3))[1:]
        self.assertEqual(offsets(moves), expect)

    def test_symmetric_quantity_is_the_number_of_instances(self):
        # the book (wave 7): Rectangular Pattern, Symmetric, Quantity 5: five holes, the
        # original in the middle (it used to count each side: 9)
        moves = core.rect_moves((1, 0), 5, 2.0, (0, 1), 1, 1.0, "spacing", "symmetric")
        self.assertEqual(offsets(moves), [(-4.0, 0.0), (-2.0, 0.0), (2.0, 0.0), (4.0, 0.0)])
        moves = core.rect_moves((1, 0), 3, 7.0, (0, 1), 1, 1.0, "spacing", "symmetric")
        self.assertEqual(offsets(moves), [(-7.0, 0.0), (7.0, 0.0)])

    def test_symmetric_extent_spans_the_whole_pattern(self):
        moves = core.rect_moves((1, 0), 5, 20.0, (0, 1), 1, 1.0, "extent", "symmetric")
        self.assertEqual(offsets(moves), [(-10.0, 0.0), (-5.0, 0.0), (5.0, 0.0), (10.0, 0.0)])

    def test_symmetric_even_quantity_puts_the_extra_copy_after(self):
        moves = core.rect_moves((1, 0), 4, 3.0, (0, 1), 1, 1.0, "spacing", "symmetric")
        self.assertEqual(offsets(moves), [(-3.0, 0.0), (3.0, 0.0), (6.0, 0.0)])
        moves = core.rect_moves((1, 0), 2, 7.0, (0, 1), 1, 1.0, "spacing", "symmetric")
        self.assertEqual(offsets(moves), [(7.0, 0.0)])

    def test_slanted_direction_is_made_unit(self):
        moves = core.rect_moves((3, 4), 2, 10.0, None, 1, 0.0)
        self.assertTrue(near(moves[0][1], (6.0, 8.0)))

    def test_negative_distance_goes_the_other_way(self):
        moves = core.rect_moves((1, 0), 2, -12.0, (0, 1), 1, 5.0)
        self.assertTrue(near(moves[0][1], (-12.0, 0.0)))

    def test_direction_two_with_quantity_one_adds_nothing(self):
        self.assertEqual(len(core.rect_moves((1, 0), 3, 20.0, (1, 0), 1, 5.0)), 2)

    def test_checks(self):
        with self.assertRaises(core.PatternError):
            core.check_rect(3, 0.0, 1, 10.0)
        with self.assertRaises(core.PatternError):
            core.check_rect(2, 10.0, 2, 0.0)
        core.check_rect(1, 0.0, 1, 0.0)  # nothing to space
        with self.assertRaises(core.PatternError):
            core.check_rect(60, 10.0, 60, 10.0)  # 3600 instances: too many

    def test_count(self):
        self.assertEqual(core.rect_count(3, "symmetric", 2, "one"), 6)
        self.assertEqual(core.rect_count(3, "one", 2, "one"), 6)
        self.assertEqual(core.circular_count(3, "symmetric"), 3)


class CircularMoves(unittest.TestCase):
    def test_full(self):
        moves = core.circular_moves((1.0, 2.0), 4)
        self.assertEqual([m[2] for m in moves], [90.0, 180.0, 270.0])
        self.assertEqual(moves[0][1], (1.0, 2.0))

    def test_angle(self):
        moves = core.circular_moves((0, 0), 3, 90.0, "angle")
        self.assertEqual([m[2] for m in moves], [45.0, 90.0])

    def test_symmetric_quantity_is_the_number_of_instances(self):
        # the report (Carabiner): Symmetric, Quantity 3, 90 degrees gave 5 slots over 180
        moves = core.circular_moves((0, 0), 3, 90.0, "symmetric")
        self.assertEqual(sorted(m[2] for m in moves), [-45.0, 45.0])
        moves = core.circular_moves((0, 0), 5, 120.0, "symmetric")
        self.assertEqual(sorted(m[2] for m in moves), [-60.0, -30.0, 30.0, 60.0])
        self.assertEqual(core.circular_moves((0, 0), 1, 90.0, "symmetric"), [])

    def test_symmetric_whole_circle(self):
        moves = core.circular_moves((0, 0), 4, 360.0, "symmetric")
        self.assertEqual(sorted(m[2] for m in moves), [-90.0, 90.0, 180.0])

    def test_turned_point_exact(self):
        self.assertTrue(near(core.apply(("turn", (10, 0), 90.0), (20, 0)), (10, 10)))
        self.assertTrue(near(core.apply(("turn", (0, 0), 180.0), (5, 3)), (-5, -3)))

    def test_checks(self):
        with self.assertRaises(core.PatternError):
            core.check_circular(3, 0.0, "angle")
        with self.assertRaises(core.PatternError):
            core.check_circular(3, 400.0, "angle")
        core.check_circular(3, 0.0, "full")  # Full: the angle is not used


class Picked(unittest.TestCase):
    def test_bounds_and_middle(self):
        box = core.bounds([[(0, 0), (10, 4)], [(2, -2)]])
        self.assertEqual(box, (0, -2, 10, 4))
        self.assertEqual(core.middle(box), (5.0, 1.0))
        self.assertIsNone(core.bounds([]))

    def test_size_along(self):
        self.assertAlmostEqual(core.size_along([[(0, 0), (10, 4)]], (1, 0)), 10.0)
        self.assertAlmostEqual(core.size_along([[(0, 0), (10, 4)]], (0, 2)), 4.0)

    def test_default_distance_clears_the_original(self):
        # a 6 mm curve: 9 mm per step (1.5 x, rounded up), extent of 3 = 18
        self.assertEqual(core.default_distance(6.0, 3), 18.0)
        self.assertEqual(core.default_distance(6.0, 3, "spacing"), 9.0)
        self.assertEqual(core.default_distance(6.0, 1), 9.0)  # as for 2 (a second row later)


class Handles(unittest.TestCase):
    def test_arrow_follows_the_hand_along_its_line(self):
        self.assertAlmostEqual(core.arrow_value(20.0, (25, 3), (31, 50), (1, 0)), 26.0)
        self.assertAlmostEqual(core.arrow_value(20.0, (25, 3), (5, 3), (1, 0)), 0.0)
        self.assertAlmostEqual(core.arrow_value(20.0, (25, 3), (0, 3), (1, 0)), -5.0)
        self.assertAlmostEqual(core.arrow_value(10.0, (0, 0), (3, 4), (0, 2)), 14.0)

    def test_turned_counts_past_half_a_turn(self):
        value, raw = 90.0, 90.0
        for to in (135.0, 179.0, -170.0, -100.0):  # round past 180
            value, raw = core.turned(value, raw, to), to
        self.assertAlmostEqual(value, 260.0)

    def test_turned_stops_at_a_full_turn(self):
        self.assertEqual(core.turned(350.0, 0.0, 30.0), 360.0)
        self.assertEqual(core.turned(-350.0, 0.0, -30.0), -360.0)

    def test_turned_back_from_full(self):
        self.assertAlmostEqual(core.turned(360.0, 10.0, -80.0), 270.0)

    def test_angle_at(self):
        self.assertAlmostEqual(core.angle_at((1, 1), (1, 5)), 90.0)
        self.assertAlmostEqual(core.angle_at((0, 0), (-1, 0)), 180.0)

    def test_settle_angle(self):
        self.assertEqual(core.settle_angle(90.04), 90.0)
        self.assertEqual(core.settle_angle(0.2), 1.0)
        self.assertEqual(core.settle_angle(-0.2), -1.0)

    def test_full_dragged_becomes_angle(self):
        self.assertEqual(core.type_after_drag("full", 180.0), "angle")
        self.assertEqual(core.type_after_drag("full", 360.0), "full")
        self.assertEqual(core.type_after_drag("symmetric", 90.0), "symmetric")

    def test_nearest_handle(self):
        handles = {
            "distance": ((100, 100), (100, 68), "arrow"),
            "distance2": ((200, 100), (232, 100), "arrow"),
            "angle": ((300, 300), (300, 300), "disc"),
        }
        reach = {"arrow": 11.0, "disc": 15.0}
        self.assertEqual(core.nearest_handle((103, 80), handles, reach), "distance")
        self.assertEqual(core.nearest_handle((240, 104), handles, reach), "distance2")
        self.assertEqual(core.nearest_handle((310, 300), handles, reach), "angle")
        self.assertIsNone(core.nearest_handle((150, 150), handles, reach))
        self.assertIsNone(core.nearest_handle((100, 80), {"x": (None, None, "arrow")}, reach))


class Constraints(unittest.TestCase):
    """Two lines joined at a corner (0 and 1), a circle (2) with a radius, a line (3) not
    picked; picked: 0, 1, 2 -> copies 10, 11, 12."""

    MAP = {0: 10, 1: 11, 2: 12}
    LINE = "Part::GeomLineSegment"

    def items(self):
        return [
            ("Coincident", 0, 2, 1, 1, U, 0, self.LINE),
            ("Horizontal", 0, 0, U, 0, U, 0, self.LINE),
            ("Perpendicular", 0, 0, 1, 0, U, 0, self.LINE),
            ("Radius", 2, 0, U, 0, U, 0, "Part::GeomCircle"),
            ("Distance", 0, 0, U, 0, U, 0, self.LINE),  # line 0's length
            ("DistanceX", 0, 1, 2, 3, U, 0, self.LINE),  # between two curves
            ("Coincident", 1, 2, 3, 1, U, 0, self.LINE),  # to a curve not picked
            ("PointOnObject", 2, 3, -1, 0, U, 0, "Part::GeomCircle"),  # on the X axis
            ("Angle", 1, 0, U, 0, U, 0, self.LINE),  # line 1's angle
            ("Tangent", 0, 0, 2, 0, U, 0, self.LINE),
            ("InternalAlignment", 2, 1, 0, 0, U, 0, "Part::GeomCircle"),
        ]

    def test_moved_copy(self):
        copied, ties = core.copied_constraints(self.items(), self.MAP)
        self.assertIn(("Coincident", (10, 2, 11, 1)), copied)
        self.assertIn(("Horizontal", (10,)), copied)
        self.assertIn(("Perpendicular", (10, 11)), copied)
        self.assertIn(("Tangent", (10, 12)), copied)
        self.assertEqual(len(copied), 4)  # nothing tied to the line not picked or the axis
        self.assertEqual(
            sorted(ties), sorted([("Equal", (2, 12)), ("Equal", (0, 10)), ("Parallel", (1, 11))])
        )

    def test_turned_copy(self):
        copied, ties = core.copied_constraints(self.items(), self.MAP, turns=True)
        kinds = [k for k, _a in copied]
        self.assertNotIn("Horizontal", kinds)  # level does not hold where it is turned
        self.assertIn(("Perpendicular", (10, 11)), copied)
        self.assertEqual(sorted(ties), [("Equal", (0, 10)), ("Equal", (2, 12))])

    def test_point_forms(self):
        items = [
            ("Tangent", 0, 2, 1, 1, U, 0, self.LINE),
            ("PointOnObject", 0, 1, 2, 0, U, 0, self.LINE),
            ("Symmetric", 0, 1, 0, 2, 1, 0, self.LINE),
            ("Symmetric", 0, 1, 1, 2, 2, 3, self.LINE),
            ("Vertical", 0, 1, 1, 2, U, 0, self.LINE),
        ]
        copied, ties = core.copied_constraints(items, self.MAP)
        self.assertEqual(
            copied,
            [
                ("Tangent", (10, 2, 11, 1)),
                ("PointOnObject", (10, 1, 12)),
                ("Symmetric", (10, 1, 10, 2, 11)),
                ("Symmetric", (10, 1, 11, 2, 12, 3)),
                ("Vertical", (10, 1, 11, 2)),
            ],
        )
        self.assertEqual(ties, [])

    def test_one_tie_per_curve(self):
        items = [
            ("Radius", 2, 0, U, 0, U, 0, "Part::GeomCircle"),
            ("Diameter", 2, 0, U, 0, U, 0, "Part::GeomCircle"),
        ]
        _copied, ties = core.copied_constraints(items, self.MAP)
        self.assertEqual(ties, [("Equal", (2, 12))])

    def test_arc_length_is_no_line(self):
        items = [("Distance", 2, 0, U, 0, U, 0, "Part::GeomArcOfCircle")]
        self.assertEqual(core.copied_constraints(items, self.MAP), ([], []))


class Vectors(unittest.TestCase):
    def test_unit_and_perpendicular(self):
        self.assertTrue(near(core.unit((0, 5)), (0, 1)))
        self.assertTrue(near(core.perpendicular((1, 0)), (0, 1)))
        with self.assertRaises(core.PatternError):
            core.unit((0, 0))

    def test_rotate_full_turn(self):
        p = core.rotate((3.0, 4.0), (1.0, 1.0), 360.0)
        self.assertTrue(near(p, (3.0, 4.0), 1e-12))
        self.assertAlmostEqual(math.hypot(*core.rotate((3, 4), (0, 0), 37.0)), 5.0)


class Ties(unittest.TestCase):
    L, C, A, P = core.LINE, core.CIRCLE, core.ARC, core.POINT

    def test_a_line_alone_is_tied_by_both_ends(self):
        points, equals, joins = core.tie_plan({4: self.L}, [])
        self.assertEqual(points, [(4, 1), (4, 2)])
        self.assertEqual(equals, [])
        self.assertEqual(joins, [])

    def test_a_circle_by_its_centre_and_equal(self):
        points, equals, joins = core.tie_plan({2: self.C}, [])
        self.assertEqual(points, [(2, 3)])
        self.assertEqual(equals, [2])

    def test_an_arc_by_its_ends_and_equal(self):
        points, equals, joins = core.tie_plan({2: self.A}, [])
        self.assertEqual(points, [(2, 1), (2, 2)])
        self.assertEqual(equals, [2])

    def test_a_triangle_is_tied_by_three_corners(self):
        # three lines joined end to start: each corner is tied once, the joins are repeated
        types = {0: self.L, 1: self.L, 2: self.L}
        joined = [(0, 2, 1, 1), (1, 2, 2, 1), (2, 2, 0, 1)]
        points, equals, joins = core.tie_plan(types, joined)
        self.assertEqual(points, [(0, 1), (0, 2), (1, 2)])
        self.assertEqual(joins, joined)

    def test_joins_to_curves_that_are_not_picked_do_not_count(self):
        points, equals, joins = core.tie_plan({0: self.L}, [(0, 2, 9, 1)])
        self.assertEqual(points, [(0, 1), (0, 2)])
        self.assertEqual(joins, [])

    def test_a_point_on_a_curve_is_no_join(self):
        points, equals, joins = core.tie_plan({0: self.L, 1: self.L}, [(0, 2, 1, 0)])
        self.assertEqual(len(points), 4)
        self.assertEqual(joins, [])

    def test_points_that_cannot_be_tied(self):
        self.assertEqual(core.tie_points("Part::GeomBSplineCurve"), ((), False))
        self.assertEqual(core.tie_points(core.POINT), ((1,), False))

    def test_wrap_turn(self):
        self.assertAlmostEqual(core.wrap_turn(90.0), math.pi / 2)
        self.assertAlmostEqual(core.wrap_turn(270.0), -math.pi / 2)
        self.assertAlmostEqual(core.wrap_turn(180.0), math.pi)
        self.assertAlmostEqual(core.wrap_turn(-180.0), math.pi)
        self.assertAlmostEqual(core.wrap_turn(-45.0), -math.pi / 4)

    def test_nearest_copy(self):
        copies = [[[(10, 0), (20, 0)]], [[(10, 10), (20, 10)]], [[(0, 30)]]]
        self.assertEqual(core.nearest_copy((15, 0.4), copies, 1.0), 0)
        self.assertEqual(core.nearest_copy((15, 9.5), copies, 1.0), 1)
        self.assertEqual(core.nearest_copy((0.2, 30), copies, 1.0), 2)
        self.assertIsNone(core.nearest_copy((15, 5), copies, 1.0))


if __name__ == "__main__":
    unittest.main()
