# SPDX-License-Identifier: LGPL-2.1-or-later
"""How the origin planes and axes look (sciforge/origin_look.py): one colour per axis, a
plane in the colour of the axis it faces, small squares, labels away from the part. Runs
without FreeCAD."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from sciforge import origin_look as look  # noqa: E402


class Colours(unittest.TestCase):
    def test_plane_takes_the_colour_of_its_normal(self):
        self.assertEqual(look.plane_colour("XY_Plane"), look.AXIS_RGB["Z"])
        self.assertEqual(look.plane_colour("XZ_Plane001"), look.AXIS_RGB["Y"])
        self.assertEqual(look.plane_colour("YZ_Plane"), look.AXIS_RGB["X"])

    def test_red_green_blue(self):
        r, g, b = (look.AXIS_RGB[k] for k in "XYZ")
        self.assertEqual(max(range(3), key=lambda i: r[i]), 0)
        self.assertEqual(max(range(3), key=lambda i: g[i]), 1)
        self.assertEqual(max(range(3), key=lambda i: b[i]), 2)

    def test_keys(self):
        self.assertEqual(look.plane_key("XZ_Plane002"), "XZ")
        self.assertEqual(look.plane_key("Sketch"), "")
        self.assertEqual(look.axis_key("Y_Axis"), "Y")
        self.assertEqual(look.axis_key("construction"), "")
        self.assertEqual(look.plane_key_of_normal((0, -1, 0)), "XZ")
        self.assertEqual(look.plane_key_of_normal((0.1, 0.2, -0.9)), "XY")
        self.assertEqual(look.plane_key_of_normal((1, 0, 0)), "YZ")

    def test_hover_is_brighter_and_less_see_through(self):
        idle = look.look("XY_Plane", False)
        lit = look.look("XY_Plane", True)
        self.assertGreater(sum(lit[0]), sum(idle[0]))
        self.assertLess(lit[1], idle[1])
        self.assertGreater(lit[3], idle[3])


class Size(unittest.TestCase):
    def test_smaller_than_the_part(self):
        self.assertAlmostEqual(look.square_size(100.0), 60.0)

    def test_minimum_and_empty(self):
        self.assertEqual(look.square_size(5.0), look.MIN_SIZE)
        self.assertEqual(look.square_size(0.0, empty=True), look.EMPTY_SIZE)


class SquareCorner(unittest.TestCase):
    """Fusion's layout: each square in the + quarter of its plane, a little off the axes,
    and it stays there (Luca 2026-10-19: squares that moved round the part confused)."""

    def test_plus_quarter_with_a_gap(self):
        for key in ("XY", "XZ_Plane", "YZ"):
            self.assertEqual(look.square_corner(key, 20.0), (2.0, 2.0))

    def test_the_gap_follows_the_side(self):
        self.assertEqual(look.square_corner("XY", 50.0), (5.0, 5.0))

    def test_part_size_for_the_pick_tolerances(self):
        self.assertAlmostEqual(look.part_size((0, 100, 0, 60, 0, 20)), 60.0)
        self.assertEqual(look.part_size(None), look.EMPTY_SIZE)


class AxisLabel(unittest.TestCase):
    def test_on_the_plus_half_near_the_middle(self):
        spot = look.axis_label_spot((-100, 0, 0), (100, 0, 0))
        self.assertAlmostEqual(spot[0], 40.0)
        self.assertEqual(spot[1:], (0.0, 0.0))


class LabelCorner(unittest.TestCase):
    CORNERS = [(-1, -1, 0), (1, -1, 0), (1, 1, 0), (-1, 1, 0)]

    def test_default_corner(self):
        self.assertEqual(look.label_corner(self.CORNERS), 2)

    def test_away_from_the_part(self):
        # a part in the +x +y quadrant: the label goes to the -x -y corner
        self.assertEqual(look.label_corner(self.CORNERS, (5, 5, 3)), 0)
        self.assertEqual(look.label_corner(self.CORNERS, (-5, 5, 3)), 1)


class PartOrSquare(unittest.TestCase):
    """Who takes a click over an origin square: the part (in front, or lying in the square's
    plane) or the square (Luca, beta 3.2: the cut face of a split made with YZ lost its
    clicks to the YZ square in Align, both at the same depth)."""

    def test_no_part_the_square(self):
        self.assertFalse(look.part_takes_click(None, 30.0))

    def test_part_in_front_takes_it(self):
        self.assertTrue(look.part_takes_click(12.0, 30.0))

    def test_part_behind_leaves_it_to_the_square(self):
        self.assertFalse(look.part_takes_click(45.0, 30.0, 100.0))

    def test_a_face_in_the_plane_takes_it(self):
        # measured in the 3D view: both depths 30.00000762939453 (the old rule wanted the
        # part strictly in front)
        self.assertTrue(look.part_takes_click(30.00000762939453, 30.00000762939453, 60.0))
        # single precision noise either way
        self.assertTrue(look.part_takes_click(30.0 + 4e-6, 30.0, 60.0))
        self.assertTrue(look.part_takes_click(30.0 - 4e-6, 30.0, 60.0))

    def test_a_face_a_little_behind_the_plane_does_not(self):
        self.assertFalse(look.part_takes_click(30.05, 30.0, 60.0))


if __name__ == "__main__":
    unittest.main()
