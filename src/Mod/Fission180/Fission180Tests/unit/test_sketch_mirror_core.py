# SPDX-License-Identifier: LGPL-2.1-or-later
"""The maths of the sketch Mirror panel (fission180/sketch_mirror_core.py)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fission180 import sketch_mirror_core as mc  # noqa: E402


def near(a, b):
    return abs(a[0] - b[0]) < 1e-9 and abs(a[1] - b[1]) < 1e-9


class Reflect(unittest.TestCase):
    def test_about_the_y_axis(self):
        self.assertTrue(near(mc.reflect((3, 4), (0, 0), (0, 1)), (-3, 4)))

    def test_about_a_slanted_line(self):
        self.assertTrue(near(mc.reflect((1, 0), (0, 0), (1, 1)), (0, 1)))

    def test_a_point_on_the_line_stays(self):
        self.assertTrue(near(mc.reflect((5, 5), (0, 0), (2, 2)), (5, 5)))

    def test_inverted(self):
        # a line (1,0)-(1,2) mirrored about Y: (-1,0)-(-1,2) keeps its order
        self.assertFalse(mc.inverted((1, 0), (-1, 0), (-1, 2), (0, 0), (0, 1)))
        # ...stored the other way round: swapped
        self.assertTrue(mc.inverted((1, 0), (-1, 2), (-1, 0), (0, 0), (0, 1)))


class Ties(unittest.TestCase):
    def test_a_line_by_both_ends(self):
        self.assertEqual(
            mc.ties(mc.LINE, 0, 5, False),
            [("Symmetric", 0, mc.START, 5, mc.START), ("Symmetric", 0, mc.END, 5, mc.END)],
        )

    def test_a_swapped_arc_and_equal(self):
        self.assertEqual(
            mc.ties("Part::GeomArcOfCircle", 1, 6, True),
            [
                ("Equal", 1, 0, 6, 0),
                ("Symmetric", 1, mc.START, 6, mc.END),
                ("Symmetric", 1, mc.END, 6, mc.START),
            ],
        )

    def test_a_circle_by_its_centre(self):
        self.assertEqual(mc.ties(mc.CIRCLE, 2, 7, False), [("Equal", 2, 0, 7, 0), ("Symmetric", 2, mc.MID, 7, mc.MID)])

    def test_helpers_of_a_curve_are_not_tied_twice(self):
        self.assertEqual(mc.ties(mc.LINE, 3, 8, False, aligned=True), [])
        self.assertEqual(mc.ties(mc.POINT, 3, 8, False, aligned=True), [])
        self.assertEqual(mc.ties("Part::GeomBSplineCurve", 3, 8, False), [])


class Copied(unittest.TestCase):
    def test_only_corner_joins_and_helpers_stay(self):
        after = [
            ("Horizontal", 0, -2000),  # the user's own, before the mirror
            ("Coincident", 5, 6),  # copied: the copies' corner
            ("Horizontal", 5, -2000),  # copied: the symmetry holds the copy instead
            ("Distance", 6, -2000),
            ("InternalAlignment", 7, 8),
        ]
        self.assertEqual(mc.copied_constraints(1, after, [5, 6, 7, 8]), [2, 3])


class Box(unittest.TestCase):
    LINES = {
        0: [(10, 10), (30, 10)],  # inside the box below
        1: [(25, 15), (60, 15)],  # half in
        2: [(70, 70), (90, 90)],  # out
        3: [(0, 25), (60, 25)],  # passes through the box, no point inside
    }

    def test_left_to_right_takes_what_is_fully_inside(self):
        self.assertEqual(mc.boxed(self.LINES, (5, 5), (40, 30)), [0])

    def test_right_to_left_takes_what_it_touches(self):
        self.assertEqual(sorted(mc.boxed(self.LINES, (40, 30), (5, 5))), [0, 1, 3])

    def test_a_curve_partly_off_the_view_is_not_fully_inside(self):
        self.assertEqual(mc.boxed({0: [(10, 10), None]}, (5, 5), (40, 30)), [])


if __name__ == "__main__":
    unittest.main()
