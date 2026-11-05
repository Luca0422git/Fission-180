# SPDX-License-Identifier: LGPL-2.1-or-later
"""Which curves are a spline's loose points, and how its ends were joined
(fission180/sketch_spline.py; Luca, 2026-11-04: "the spline still disapears when i click the
checkmark. AND the orange dots are still there")."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fission180 import sketch_spline as sp  # noqa: E402

LINE = "Part::GeomLineSegment"
P, C = sp.POINT, sp.CIRCLE


class Pending(unittest.TestCase):
    # a rectangle (0-3), the user's own construction point (4), then a spline's fit points
    GEO = [(LINE, False)] * 4 + [(P, True), (P, True), (P, True), (P, True)]

    def test_the_points_since_the_first_click(self):
        self.assertEqual(sp.pending(self.GEO, set(), start=5), [5, 6, 7])

    def test_a_users_own_construction_point_before_it_is_never_taken(self):
        self.assertNotIn(4, sp.pending(self.GEO, set(), start=5))

    def test_points_a_curve_already_owns_are_not_loose(self):
        self.assertEqual(sp.pending(self.GEO, {6}, start=5), [5, 7])

    def test_a_three_point_splines_middle_point_is_the_splines(self):
        # FreeCAD 1.1: with three fit points the middle one is PointOnObject on the curve
        # (no knot there), the ends InternalAlignment (seen in a run on FreeCAD 1.1.4)
        geo = [(LINE, False)] * 4 + [(P, True)] * 3 + [(sp.BSPLINE, False)]
        cons = [("InternalAlignment", 4, 1, 7, 0), ("PointOnObject", 5, 1, 7, 0), ("InternalAlignment", 6, 1, 7, 0)]
        self.assertEqual(sp.pending(geo, {4, 6}, start=4, constraints=cons), [])

    def test_a_point_on_a_line_is_still_loose(self):
        geo = [(LINE, False)] * 4 + [(P, True)]
        self.assertEqual(sp.pending(geo, set(), start=4, constraints=[("PointOnObject", 4, 1, 0, 0)]), [4])

    def test_without_the_first_click_loose_points_are_not_guessed(self):
        self.assertEqual(sp.pending(self.GEO, set(), start=None), [])

    def test_without_the_first_click_freecads_control_circles_are_known(self):
        geo = [(LINE, False)] * 4 + [(C, True)] * 3
        cons = [("Weight", 4, 0, -2000, 0), ("Equal", 4, 0, 5, 0), ("Equal", 4, 0, 6, 0)]
        self.assertEqual(sp.pending(geo, set(), None, cons), [4, 5, 6])

    def test_construction_circles_without_freecads_signature_are_left_alone(self):
        geo = [(LINE, False)] * 4 + [(C, True)] * 3
        self.assertEqual(sp.pending(geo, set(), None, [("Equal", 4, 0, 5, 0)]), [])

    def test_kind(self):
        self.assertEqual(sp.kind_of(self.GEO, [5, 6]), "fit")
        geo = [(C, True), (C, True)]
        self.assertEqual(sp.kind_of(geo, [0, 1]), "poles")
        self.assertIsNone(sp.kind_of([(P, True), (C, True)], [0, 1]))


class Joins(unittest.TestCase):
    def test_the_ends_clicked_on_the_rectangles_corners(self):
        # fit points 4, 5, 6: the first on line 0's start, the last on line 1's end; the
        # middle one on line 2 (dropped: a curve through it needs no join)
        cons = [
            ("Coincident", 4, 1, 0, 1),
            ("PointOnObject", 5, 1, 2, 0),
            ("Coincident", 1, 2, 6, 1),
        ]
        self.assertEqual(
            sp.end_joins(cons, [4, 5, 6], "fit"),
            [(sp.START, "Coincident", 0, 1), (sp.END, "Coincident", 1, 2)],
        )

    def test_control_circles_join_by_their_centre(self):
        cons = [("Coincident", 4, 3, 0, 1), ("PointOnObject", 6, 3, 2, 0), ("Coincident", 4, 1, 9, 1)]
        self.assertEqual(
            sp.end_joins(cons, [4, 5, 6], "poles"),
            [(sp.START, "Coincident", 0, 1), (sp.END, "PointOnObject", 2, 0)],
        )

    def test_joins_between_its_own_points_are_dropped(self):
        self.assertEqual(sp.end_joins([("Coincident", 4, 1, 6, 1)], [4, 5, 6], "fit"), [])

    def test_degree(self):
        self.assertEqual([sp.degree_for(n) for n in (2, 3, 4, 9)], [1, 2, 3, 3])


if __name__ == "__main__":
    unittest.main()
