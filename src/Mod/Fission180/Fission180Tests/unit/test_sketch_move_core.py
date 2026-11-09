# SPDX-License-Identifier: LGPL-2.1-or-later
"""The maths of the sketch Move/Copy and Sketch Scale tools (fission180/sketch_move_core.py)."""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fission180 import sketch_move_core as mc  # noqa: E402

U = mc.GEO_UNDEF


def near(a, b, tol=1e-9):
    return abs(a[0] - b[0]) < tol and abs(a[1] - b[1]) < tol


def con(kind, first, fpos=0, second=U, spos=0, third=U, tpos=0):
    return (kind, first, fpos, second, spos, third, tpos)


class Points(unittest.TestCase):
    def test_shift(self):
        self.assertTrue(near(mc.move_point((1, 2), (0, 0), (10, -5)), (11, -3)))

    def test_turn_then_shift(self):
        # (1, 0) turned 90 degrees about (0, 0) is (0, 1), then shifted by (2, 3)
        self.assertTrue(near(mc.move_point((1, 0), (0, 0), (2, 3), 90.0), (2, 4)))

    def test_turn_about_a_pivot(self):
        self.assertTrue(near(mc.rotate((3, 1), (2, 1), 180.0), (1, 1)))

    def test_scale_about_a_base(self):
        self.assertTrue(near(mc.scale_point((4, 6), (2, 2), 0.5), (3, 4)))
        self.assertEqual(mc.scale_all([(2, 2)], (2, 2), 3.0), [(2.0, 2.0)])

    def test_centre_of_polylines(self):
        self.assertEqual(mc.centre([[(0, 0), (10, 0)], [(10, 0), (10, 20)]]), (5.0, 10.0))
        self.assertIsNone(mc.centre([]))

    def test_unwrap_follows_the_hand_past_half_a_turn(self):
        self.assertAlmostEqual(mc.unwrap(-170.0, 175.0), 190.0)
        self.assertAlmostEqual(mc.unwrap(10.0, 0.0), 10.0)

    def test_quarter_turns(self):
        self.assertEqual(mc.quarter_turns(0.0), 0)
        self.assertEqual(mc.quarter_turns(90.0), 1)
        self.assertEqual(mc.quarter_turns(270.0), 3)
        self.assertEqual(mc.quarter_turns(360.0), 0)
        self.assertIsNone(mc.quarter_turns(30.0))

    def test_round_value(self):
        self.assertEqual(mc.round_value(0.1 + 0.2), 0.3)
        self.assertEqual(mc.round_value(-1e-12), 0.0)


class Manipulator(unittest.TestCase):
    def test_parts(self):
        parts = mc.triad_parts((10, 5), 20.0)
        self.assertTrue(near(parts["x"][1], (30, 5)))
        self.assertTrue(near(parts["y"][1], (10, 25)))
        self.assertTrue(near(parts["x"][0], (10 + mc.GAP * 20, 5)))
        disc = parts["turn"][1]
        r = mc.RING * 20.0
        self.assertTrue(
            near(disc, (10 + r * math.cos(math.radians(45)), 5 + r * math.sin(math.radians(45))))
        )

    def _screen(self):
        # one mm is one pixel, the manipulator at (100, 100), 96 px arrows
        return mc.triad_parts((100, 100), 96.0)

    def test_the_x_arrow(self):
        self.assertEqual(mc.handle_at((180, 101), self._screen()), "x")

    def test_the_y_arrow(self):
        self.assertEqual(mc.handle_at((99, 170), self._screen()), "y")

    def test_the_turn_disc(self):
        disc = self._screen()["turn"][1]
        self.assertEqual(mc.handle_at((disc[0] + 2, disc[1] - 1), self._screen()), "turn")

    def test_the_middle(self):
        self.assertEqual(mc.handle_at((101, 101), self._screen()), "free")

    def test_nothing_far_away(self):
        self.assertIsNone(mc.handle_at((300, 300), self._screen()))

    def test_rotate_only_shows_no_arrows(self):
        self.assertIsNone(mc.handle_at((180, 101), self._screen(), turns=True, arrows=False))
        disc = self._screen()["turn"][1]
        self.assertEqual(mc.handle_at(disc, self._screen(), turns=True, arrows=False), "turn")

    def test_translate_has_no_turn_handle(self):
        disc = self._screen()["turn"][1]
        self.assertNotEqual(mc.handle_at(disc, self._screen(), turns=False), "turn")

    def test_dragged(self):
        self.assertEqual(mc.dragged("x", (1, 2), (0, 0), (5, 7)), (6, 2))
        self.assertEqual(mc.dragged("y", (1, 2), (0, 0), (5, 7)), (1, 9))
        self.assertEqual(mc.dragged("free", (1, 2), (0, 0), (5, 7)), (6, 9))


class ScaleFactor(unittest.TestCase):
    def test_a_factor(self):
        self.assertEqual(mc.parse_factor("0.5"), 0.5)
        self.assertEqual(mc.parse_factor(" 2 "), 2.0)
        self.assertEqual(mc.parse_factor("1,5"), 1.5)

    def test_a_percentage(self):
        self.assertEqual(mc.parse_factor("50%"), 0.5)
        self.assertEqual(mc.parse_factor("150 %"), 1.5)
        self.assertEqual(mc.parse_percent("150"), 1.5)
        self.assertEqual(mc.parse_percent("25 %"), 0.25)

    def test_times(self):
        self.assertEqual(mc.parse_factor("2x"), 2.0)
        self.assertEqual(mc.parse_factor("x3"), 3.0)

    def test_refused(self):
        for text in ("", "abc", "0", "-2", "0%"):
            with self.assertRaises(ValueError):
                mc.parse_factor(text)
        with self.assertRaises(ValueError):
            mc.parse_percent("-5")

    def test_texts(self):
        self.assertEqual(mc.factor_text(1.5), "1.5")
        self.assertEqual(mc.percent_text(1.5), "150 %")
        self.assertEqual(mc.percent_text(0.333333333), "33.3333 %")

    def test_the_arrow(self):
        self.assertEqual(mc.reference_length([(3, 4), (1, 0)], (0, 0)), 5.0)
        self.assertEqual(mc.reference_length([(0, 0)], (0, 0)), 1.0)
        self.assertEqual(mc.arrow_factor((0, 0), (10, 3), 5.0), 2.0)
        self.assertEqual(mc.arrow_factor((0, 0), (12, 0), 5.0, offset=2.0), 2.0)
        self.assertEqual(mc.arrow_factor((0, 0), (-5, 0), 5.0), mc.MIN_FACTOR)


class Helpers(unittest.TestCase):
    def test_helpers_come_along(self):
        self.assertEqual(mc.with_helpers([3], [(4, 3), (5, 3), (9, 8)]), [3, 4, 5])


class Where(unittest.TestCase):
    def test_outside_inside_tie(self):
        self.assertEqual(mc.where(con("Coincident", 5, 1, 6, 2), {0, 1}), "outside")
        self.assertEqual(mc.where(con("Coincident", 0, 2, 1, 1), {0, 1}), "inside")
        self.assertEqual(mc.where(con("Coincident", 0, 2, 7, 1), {0, 1}), "tie")

    def test_the_axes_and_the_origin_stay(self):
        self.assertEqual(mc.where(con("PointOnObject", 0, 1, -1), {0}), "tie")
        self.assertEqual(mc.where(con("Coincident", 0, 1, -1, 1), {0}), "tie")

    def test_a_point_measured_from_the_origin_is_a_tie(self):
        self.assertEqual(mc.where(con("DistanceX", 0, 1), {0}), "tie")
        # a line's own horizontal size is not
        self.assertEqual(mc.where(con("DistanceX", 0), {0}), "inside")


RECT = [
    con("Coincident", 0, 2, 1, 1),
    con("Coincident", 1, 2, 2, 1),
    con("Coincident", 2, 2, 3, 1),
    con("Coincident", 3, 2, 0, 1),
    con("Horizontal", 0),
    con("Horizontal", 2),
    con("Vertical", 1),
    con("Vertical", 3),
    con("DistanceX", 0),  # 8: its width
    con("DistanceY", 1),  # 9: its height
    con("Coincident", 0, 1, -1, 1),  # 10: its corner on the origin
    con("DistanceX", 4, 3),  # 11: a circle's centre measured from the origin (not moved)
]


def corners(geo, pos):
    """The rectangle (0,0)-(20,10) drawn as lines 0..3 before the move."""
    pts = {
        (0, 1): (0, 0),
        (0, 2): (20, 0),
        (1, 1): (20, 0),
        (1, 2): (20, 10),
        (2, 1): (20, 10),
        (2, 2): (0, 10),
        (3, 1): (0, 10),
        (3, 2): (0, 0),
    }
    return pts.get((geo, pos))


class MovePlan(unittest.TestCase):
    def test_a_shift_keeps_the_shape_and_checks_the_ties(self):
        plan = mc.move_plan(RECT, [0, 1, 2, 3], 0.0, corners)
        self.assertEqual(plan["keep"], list(range(10)) + [11])
        self.assertEqual(plan["check"], [10])  # the corner on the origin: kept if it still is
        self.assertEqual(plan["measure"], [])
        self.assertEqual(plan["replace"], {})

    def test_a_tie_dimension_is_measured_again(self):
        cons = [con("Distance", 0, 1, 7, 1), con("DistanceX", 0, 1)]
        plan = mc.move_plan(cons, [0], 0.0)
        self.assertEqual(plan["measure"], [0, 1])

    def test_half_a_turn_keeps_level_lines_and_measures_the_sizes(self):
        plan = mc.move_plan(RECT, [0, 1, 2, 3], 180.0, corners)
        for i in (4, 5, 6, 7):
            self.assertIn(i, plan["keep"])
        self.assertIn(8, plan["measure"])
        self.assertIn(9, plan["measure"])

    def test_a_quarter_turn_swaps_level_and_upright(self):
        plan = mc.move_plan(RECT, [0, 1, 2, 3], 90.0, corners)
        self.assertEqual(plan["replace"][4], [("Vertical", 0, 0, U, 0, None)])
        self.assertEqual(plan["replace"][6], [("Horizontal", 1, 0, U, 0, None)])
        self.assertEqual(plan["replace"][8], [("DistanceY", 0, 0, U, 0, "measure")])
        self.assertEqual(plan["replace"][9], [("DistanceX", 1, 0, U, 0, "measure")])

    def test_another_turn_keeps_the_shape_square(self):
        plan = mc.move_plan(RECT, [0, 1, 2, 3], 30.0, corners)
        replace = plan["replace"]
        # the first level line is the reference, the other is parallel to it ...
        self.assertEqual(replace[4], [])
        self.assertEqual(replace[5], [("Parallel", 0, 0, 2, 0, None)])
        # ... the same for the upright ones, and they stay square to the level ones
        self.assertEqual(replace[6], [("Perpendicular", 1, 0, 0, 0, None)])
        self.assertEqual(replace[7], [("Parallel", 1, 0, 3, 0, None)])
        # the width and the height of level / upright lines become plain lengths
        self.assertEqual(replace[8], [("Distance", 0, 0, U, 0, "measure")])
        self.assertEqual(replace[9], [("Distance", 1, 0, U, 0, "measure")])
        self.assertEqual(plan["check"], [10])
        self.assertIn(11, plan["keep"])

    def test_a_slanted_horizontal_size_is_measured_again(self):
        cons = [con("DistanceX", 0, 1, 0, 2)]

        def before(geo, pos):
            return {(0, 1): (0, 0), (0, 2): (10, 5)}[(geo, pos)]

        plan = mc.move_plan(cons, [0], 30.0, before)
        self.assertEqual(plan["measure"], [0])

    def test_a_line_angle_is_measured_again_when_turned(self):
        plan = mc.move_plan([con("Angle", 0)], [0], 15.0)
        self.assertEqual(plan["measure"], [0])
        plan = mc.move_plan([con("Angle", 0)], [0], 0.0)
        self.assertEqual(plan["keep"], [0])

    def test_two_level_points_lose_their_rule_when_turned(self):
        plan = mc.move_plan([con("Horizontal", 0, 1, 1, 2)], [0, 1], 30.0)
        self.assertEqual(plan["delete"], [0])


class ScalePlan(unittest.TestCase):
    def test_lengths_are_measured_again(self):
        plan = mc.scale_plan(
            RECT + [con("Radius", 4), con("Angle", 0, 0, 1, 0)], [0, 1, 2, 3, 4], 2.0
        )
        self.assertIn(8, plan["measure"])
        self.assertIn(9, plan["measure"])
        self.assertIn(12, plan["measure"])  # the radius
        self.assertIn(13, plan["keep"])  # the angle
        self.assertIn(4, plan["keep"])  # level stays level
        self.assertEqual(plan["check"], [10])
        self.assertIn(11, plan["measure"])  # the circle's centre from the origin

    def test_a_factor_of_one_measures_nothing_inside(self):
        plan = mc.scale_plan(RECT, [0, 1, 2, 3], 1.0)
        self.assertNotIn(8, plan["measure"])


class SpecValue(unittest.TestCase):
    def test_values(self):
        def point(geo, pos):
            return {(0, 1): (0, 0), (0, 2): (3, 4), (1, 1): (1, 1)}[(geo, pos)]

        self.assertEqual(mc.spec_value(("Distance", 0, 0, U, 0, "measure"), point), 5.0)
        self.assertEqual(mc.spec_value(("DistanceX", 0, 0, U, 0, "measure"), point), 3.0)
        self.assertEqual(mc.spec_value(("DistanceY", 0, 2, 1, 1, "measure"), point), -3.0)


class TieHolds(unittest.TestCase):
    def setUp(self):
        self.points = {
            (0, 1): (5, 0),
            (0, 2): (15, 0),
            (1, 1): (5, 0),
            (2, 3): (0, 0),
            (-1, 1): (0, 0),
        }
        self.curves = {
            -1: ("line", (0, 0), (1, 0)),
            -2: ("line", (0, 0), (0, 1)),
            0: ("line", (5, 0), (15, 0)),
            2: ("circle", (0, 0), 5.0),
            3: ("line", (0, 3), (10, 3)),
            4: ("line", (0, 0), (0, 10)),
            5: ("circle", (9, 9), 5.0),
        }

    def holds(self, c):
        return mc.tie_holds(c, lambda g, p: self.points[(g, p)], lambda g: self.curves[g])

    def test_coincident(self):
        self.assertTrue(self.holds(con("Coincident", 0, 1, 1, 1)))
        self.assertFalse(self.holds(con("Coincident", 0, 2, 1, 1)))

    def test_point_on_a_line_or_an_axis(self):
        self.assertTrue(self.holds(con("PointOnObject", 0, 2, -1)))
        self.assertFalse(self.holds(con("PointOnObject", 0, 2, -2)))

    def test_point_on_a_circle(self):
        self.assertTrue(self.holds(con("PointOnObject", 0, 1, 2)))
        self.assertFalse(self.holds(con("PointOnObject", 0, 2, 2)))

    def test_parallel_and_perpendicular(self):
        self.assertTrue(self.holds(con("Parallel", 0, 0, 3)))
        self.assertTrue(self.holds(con("Perpendicular", 0, 0, 4)))
        self.assertFalse(self.holds(con("Parallel", 0, 0, 4)))

    def test_equal(self):
        self.assertTrue(self.holds(con("Equal", 2, 0, 5)))
        self.assertTrue(self.holds(con("Equal", 0, 0, 3)))
        self.assertFalse(self.holds(con("Equal", 0, 0, 2)))

    def test_level_points(self):
        self.assertTrue(self.holds(con("Horizontal", 0, 1, 0, 2)))
        self.assertFalse(self.holds(con("Vertical", 0, 1, 0, 2)))

    def test_anything_else_goes(self):
        self.assertFalse(self.holds(con("Tangent", 0, 0, 2)))
        self.assertFalse(self.holds(con("Symmetric", 0, 1, 0, 2, -2)))


class Measure(unittest.TestCase):
    def setUp(self):
        self.points = {
            (0, 1): (10, 5),
            (0, 2): (30, 5),
            (4, 3): (50, 5),
            (7, 1): (0, 20),
            (-1, 1): (0, 0),
        }
        self.curves = {8: ("line", (0, 0), (100, 0))}

    def value(self, c, old, change):
        return mc.measure(
            c, old, change, lambda g, p: self.points[(g, p)], lambda g: self.curves[g]
        )

    def test_a_centre_measured_from_the_origin(self):
        c = con("DistanceX", -1, 1, 4, 3)
        self.assertEqual(self.value(c, 40.0, ("move", 0.0, {4})), 50.0)
        self.assertEqual(self.value(con("DistanceY", 4, 3), 0.0, ("move", 0.0, {4})), 5.0)

    def test_distances(self):
        self.assertEqual(self.value(con("Distance", 0), 1.0, ("move", 0.0, {0})), 20.0)
        self.assertAlmostEqual(
            self.value(con("Distance", 0, 1, 7, 1), 1.0, ("move", 0.0, {0})), math.hypot(10, 15)
        )
        self.assertEqual(self.value(con("Distance", 0, 1, 8), 1.0, ("move", 0.0, {0})), 5.0)
        self.assertIsNone(self.value(con("Distance", 4, 0, 9, 0), 1.0, ("move", 0.0, {4})))

    def test_scaled_lengths_grow(self):
        self.assertEqual(self.value(con("Radius", 4), 3.0, ("scale", 2.0, {4})), 6.0)
        self.assertEqual(self.value(con("DistanceX", 0), 20.0, ("scale", 0.5, {0})), 10.0)

    def test_angles_turn_with_the_line(self):
        a = math.radians(30)
        self.assertAlmostEqual(self.value(con("Angle", 0), 0.1, ("move", 30.0, {0})), 0.1 + a)
        self.assertAlmostEqual(self.value(con("Angle", 0, 0, 8), 0.5, ("move", 30.0, {0})), 0.5 - a)
        self.assertAlmostEqual(self.value(con("Angle", 8, 0, 0), 0.5, ("move", 30.0, {0})), 0.5 + a)
        self.assertEqual(self.value(con("Angle", 0, 0, 8), 0.5, ("scale", 2.0, {0})), 0.5)

    def test_a_shift_or_a_scale_keeps_angle_ties(self):
        c = con("Angle", 0, 0, 8)
        self.assertEqual(mc.move_plan([c], [0], 0.0)["keep"], [0])
        self.assertEqual(mc.move_plan([c], [0], 20.0)["measure"], [0])
        self.assertEqual(mc.scale_plan([c], [0], 2.0)["keep"], [0])


class Positive(unittest.TestCase):
    def test_a_line_size_below_0_is_written_the_other_way(self):
        self.assertEqual(
            mc.positive("DistanceX", 1, 0, U, 0, -10.0), (1, mc.END, 1, mc.START, 10.0)
        )

    def test_two_points_are_swapped(self):
        self.assertEqual(mc.positive("DistanceY", 1, 1, 2, 2, -3.0), (2, 2, 1, 1, 3.0))

    def test_a_point_left_of_the_origin(self):
        self.assertEqual(mc.positive("DistanceX", 4, 3, U, 0, -7.0), (4, 3, -1, 1, 7.0))

    def test_others_unchanged(self):
        self.assertEqual(mc.positive("DistanceX", 1, 0, U, 0, 10.0), (1, 0, U, 0, 10.0))
        self.assertEqual(mc.positive("Angle", 1, 0, U, 0, -1.0), (1, 0, U, 0, -1.0))


if __name__ == "__main__":
    unittest.main()
