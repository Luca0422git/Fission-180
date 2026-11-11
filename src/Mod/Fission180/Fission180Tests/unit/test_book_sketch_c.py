# SPDX-License-Identifier: LGPL-2.1-or-later
"""Wave 7, sketch-c: the pure rules (no FreeCAD)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fission180 import sketch_dimension_signs as signs  # noqa: E402
from fission180 import sketch_first_dimension as first  # noqa: E402
from fission180 import sketch_infer_core as core  # noqa: E402
from fission180 import sketch_named_dimensions as named  # noqa: E402

NO = -2000


class DiameterSign(unittest.TestCase):
    def test_the_sign_goes_in_front_once(self):
        self.assertEqual(signs.with_sign("20 mm"), "⌀ 20 mm")
        self.assertEqual(signs.with_sign("⌀ 20 mm"), "⌀ 20 mm")


class NamedDimension(unittest.TestCase):
    def test_the_dimension_that_made_the_name_is_the_parameter(self):
        formulas = {3: "Width", 7: "Width", 8: "Width / 2"}
        self.assertEqual(named.owner_of(3, formulas, ["Width"], ["Width", "Other"]), "Width")

    def test_a_later_dimension_only_uses_it(self):
        formulas = {3: "Width", 7: "Width"}
        self.assertIsNone(named.owner_of(7, formulas, ["Width"], ["Width"]))

    def test_a_formula_is_not_the_parameter(self):
        self.assertIsNone(named.owner_of(8, {8: "Width / 2"}, ["Width"], ["Width"]))

    def test_a_parameter_made_elsewhere_is_only_used(self):
        # Arm_Length was made in Change Parameters: typing a number unlinks, as in Fusion
        self.assertIsNone(named.owner_of(2, {2: "Arm_Length"}, [], ["Arm_Length"]))

    def test_a_deleted_parameter_owns_nothing(self):
        self.assertIsNone(named.owner_of(2, {2: "Width"}, ["Width"], []))

    def test_no_formula(self):
        self.assertIsNone(named.owner_of(5, {2: "Width"}, ["Width"], ["Width"]))


class FirstDimension(unittest.TestCase):
    def cons(self, *more):
        return [
            ("Coincident", 0, 1, NO),
            ("Horizontal", 0, NO, NO),
            ("Distance", 0, NO, NO),
        ] + list(more)

    def test_the_only_size_is_the_first(self):
        self.assertTrue(first.first_size(2, self.cons(), 0))

    def test_an_angle_does_not_count_as_a_size(self):
        self.assertTrue(first.first_size(2, self.cons(("Angle", 0, 1, NO)), 0))

    def test_a_second_size_is_not_the_first(self):
        self.assertFalse(first.first_size(2, self.cons(("Radius", 4, NO, NO)), 0))

    def test_an_angle_itself_never_scales(self):
        self.assertFalse(first.first_size(3, self.cons(("Angle", 0, 1, NO)), 0))

    def test_nothing_fixed_or_projected(self):
        self.assertFalse(first.first_size(2, self.cons(("Block", 1, NO, NO)), 0))
        self.assertFalse(first.first_size(2, self.cons(), 1))
        self.assertFalse(first.first_size(2, self.cons(("PointOnObject", 1, -3, NO)), 0))
        # a spline's control points carry weights in their circles
        self.assertFalse(first.first_size(2, self.cons(("Weight", 5, NO, NO)), 0))

    def test_a_formula_is_no_first_value(self):
        self.assertFalse(first.first_size(2, self.cons(), 0, {2}))

    def test_the_origin_and_axes_are_fine(self):
        self.assertTrue(first.first_size(2, self.cons(("PointOnObject", 0, -1, NO)), 0))

    def test_factor(self):
        self.assertAlmostEqual(first.factor(30.0, 60.0), 2.0)
        self.assertAlmostEqual(first.factor(-30.0, 15.0), 0.5)
        self.assertIsNone(first.factor(30.0, 30.0))
        self.assertIsNone(first.factor(0.0, 30.0))


class FullGridSnap(unittest.TestCase):
    def test_every_free_coordinate_goes_to_its_nearest_line(self):
        # 4.9 mm off a 10 mm line: FreeCAD's rule (a fifth) leaves it, Fusion's snaps it
        self.assertEqual(core.grid_snap(14.9, 10.0), 14.9)
        self.assertEqual(core.grid_snap(14.9, 10.0, core.FULL), 10.0)
        self.assertEqual(core.grid_snap(15.1, 10.0, core.FULL), 20.0)
        self.assertEqual(core.grid_snap(-14.9, 10.0, core.FULL), -10.0)

    def test_a_free_point_lands_on_a_crossing(self):
        result = core.grid_capped((-25.9, 13.3), 10.0, core.FULL)
        self.assertIsNotNone(result)
        self.assertEqual(result.point, (-30.0, 10.0))
        self.assertEqual(sorted(result.grid), [(0, -30.0), (1, 10.0)])

    def test_where_freecad_agrees_it_places_the_point(self):
        self.assertIsNone(core.grid_capped((-29.5, 10.4), 10.0, core.FULL))

    def test_no_grid_no_snap(self):
        self.assertEqual(core.grid_snap(14.9, None, core.FULL), 14.9)
        self.assertIsNone(core.grid_capped((1.0, 2.0), 0, core.FULL))

    def test_the_screen_reach_is_unchanged(self):
        self.assertEqual(core.grid_snap(11.0, 10.0, 1.2), 10.0)
        self.assertEqual(core.grid_snap(11.5, 10.0, 1.2), 11.5)


if __name__ == "__main__":
    unittest.main()
