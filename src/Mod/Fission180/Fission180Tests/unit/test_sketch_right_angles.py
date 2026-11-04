# SPDX-License-Identifier: LGPL-2.1-or-later
"""Where the 90 degree marks go (fission180/sketch_right_angles.py; Luca, 2026-11-04:
"Sketch lines are still missing 90 degree markings where they connect at 90 degrees")."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fission180 import sketch_right_angles as ra  # noqa: E402

H = ("Horizontal", 0, None)
V = ("Vertical", 1, None)


def near(a, b, tol=1e-9):
    return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol


class Corners(unittest.TestCase):
    def test_an_l_held_by_horizontal_and_vertical(self):
        lines = {0: ((0, 0), (40, 0)), 1: ((40, 0), (40, 30))}
        found = ra.corners(lines, [H, V])
        self.assertEqual(len(found), 1)
        corner, u1, u2, reach = found[0]
        self.assertTrue(near(corner, (40, 0)))
        self.assertTrue(near(u1, (-1, 0)) and near(u2, (0, 1)), (u1, u2))
        self.assertAlmostEqual(reach, 30)

    def test_perpendicular_between_slanted_lines(self):
        lines = {3: ((0, 0), (10, 10)), 7: ((10, 10), (20, 0))}
        found = ra.corners(lines, [("Perpendicular", 7, 3)])
        self.assertEqual(len(found), 1)
        self.assertTrue(near(found[0][0], (10, 10)))

    def test_a_t_the_upright_line_ends_on_the_middle_of_the_level_one(self):
        # Luca's screenshot: a line drawn down at 90 degrees onto the bottom line
        lines = {0: ((0, 0), (60, 0)), 1: ((45, 47.63), (45, 0))}
        found = ra.corners(lines, [H, V])
        self.assertEqual(len(found), 1)
        corner, u1, u2, reach = found[0]
        self.assertTrue(near(corner, (45, 0)))
        # the mark on the longer side of the bottom line (45 mm to the left)
        self.assertTrue(near(u1, (-1, 0)) and near(u2, (0, 1)), (u1, u2))
        self.assertAlmostEqual(reach, 45)

    def test_no_mark_without_a_constraint_holding_the_angle(self):
        lines = {0: ((0, 0), (40, 0)), 1: ((40, 0), (40, 30))}
        self.assertEqual(ra.corners(lines, [H]), [])
        self.assertEqual(ra.corners(lines, []), [])

    def test_no_mark_when_the_lines_do_not_touch(self):
        lines = {0: ((0, 0), (40, 0)), 1: ((50, 5), (50, 30))}
        self.assertEqual(ra.corners(lines, [H, V]), [])

    def test_no_mark_when_the_angle_is_not_90_now(self):
        lines = {3: ((0, 0), (10, 10)), 7: ((10, 10), (20, 1))}
        self.assertEqual(ra.corners(lines, [("Perpendicular", 3, 7)]), [])

    def test_a_rectangle_has_four(self):
        lines = {0: ((0, 0), (40, 0)), 1: ((40, 0), (40, 20)), 2: ((40, 20), (0, 20)), 3: ((0, 20), (0, 0))}
        cons = [("Horizontal", 0, None), ("Horizontal", 2, None), ("Vertical", 1, None), ("Vertical", 3, None)]
        found = ra.corners(lines, cons)
        self.assertEqual(sorted((round(c[0][0]), round(c[0][1])) for c in found), [(0, 0), (0, 20), (40, 0), (40, 20)])

    def test_two_point_horizontal_is_not_a_line_direction(self):
        # FreeCAD's Horizontal between two points (second is a geometry) is left out
        pairs = ra.held_pairs([("Horizontal", 0, 5), ("Vertical", 1, None)])
        self.assertEqual(pairs, set())


class FromFreeCAD(unittest.TestCase):
    """directions(): FreeCAD's constraints (type, first, first_pos, second, second_pos)."""

    LINES = {0: ((0, 0), (40, 0)), 1: ((40, 0), (40, 30))}

    def test_whole_line_horizontal_and_vertical(self):
        raw = [("Horizontal", 0, 0, -2000, 0), ("Vertical", 1, 0, -2000, 0), ("Coincident", 0, 2, 1, 1)]
        self.assertEqual(sorted(ra.directions(raw, self.LINES)), [("Horizontal", 0, None), ("Vertical", 1, None)])

    def test_a_line_from_the_origin_along_the_x_axis(self):
        # FreeCAD: the start on the root point, the end on the X axis (no Horizontal)
        raw = [
            ("Coincident", 0, 1, -1, 1),
            ("PointOnObject", 0, 2, -1, 0),
            ("Coincident", 0, 2, 1, 1),
            ("Vertical", 1, 0, -2000, 0),
        ]
        found = ra.corners(self.LINES, ra.directions(raw, self.LINES))
        self.assertEqual(len(found), 1)
        self.assertTrue(near(found[0][0], (40, 0)))

    def test_a_line_up_the_y_axis(self):
        lines = {0: ((0, 0), (0, 30)), 1: ((0, 30), (20, 30))}
        raw = [("Coincident", 0, 1, -1, 1), ("PointOnObject", 0, 2, -2, 0), ("Horizontal", 1, 0, -2000, 0)]
        self.assertEqual(sorted(ra.directions(raw, lines)), [("Horizontal", 1, None), ("Vertical", 0, None)])

    def test_tangent_parallel_perpendicular_to_an_axis(self):
        raw = [("Tangent", 0, 0, -1, 0), ("Perpendicular", -1, 0, 1, 0)]
        self.assertEqual(sorted(ra.directions(raw, self.LINES)), [("Horizontal", 0, None), ("Vertical", 1, None)])

    def test_one_end_on_an_axis_is_not_a_direction(self):
        raw = [("PointOnObject", 0, 2, -1, 0)]
        self.assertEqual(ra.directions(raw, self.LINES), [])

    def test_perpendicular_between_lines_and_point_forms(self):
        raw = [("Perpendicular", 0, 2, 1, 1), ("Horizontal", 0, 1, 1, 2)]
        self.assertEqual(ra.directions(raw, self.LINES), [("Perpendicular", 0, 1)])


class Size(unittest.TestCase):
    def test_ten_pixels_but_never_more_than_a_share_of_the_line(self):
        self.assertAlmostEqual(ra.mark_size(0.2, 100.0), 2.0)
        self.assertAlmostEqual(ra.mark_size(0.2, 3.0), 1.2)

    def test_the_square(self):
        pts = ra.mark((40, 0), (-1, 0), (0, 1), 2.0)
        self.assertEqual(pts, [(38.0, 0.0), (38.0, 2.0), (40.0, 2.0)])


if __name__ == "__main__":
    unittest.main()
