# SPDX-License-Identifier: LGPL-2.1-or-later
"""Wave 7, replay-a: the pure logic behind the hitches found while replaying the book's
Basics, Classic Donut and Saturn V (docs/fission180/sessions/replay-a.md). Runs without
FreeCAD."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fission180 import origin_look  # noqa: E402
from fission180 import sketch_axes  # noqa: E402


class SketchAxisColours(unittest.TestCase):
    """A sketch's axis lines take the colours of the origin axes they lie along."""

    def test_axis_of(self):
        self.assertEqual(sketch_axes.axis_of((1, 0, 0)), "X")
        self.assertEqual(sketch_axes.axis_of((0, -1, 0)), "Y")
        self.assertEqual(sketch_axes.axis_of((0, 0, 2.5)), "Z")
        self.assertEqual(sketch_axes.axis_of((1e-9, 0, -1)), "Z")

    def test_slanted_is_no_axis(self):
        self.assertEqual(sketch_axes.axis_of((1, 1, 0)), "")
        self.assertEqual(sketch_axes.axis_of((0.999, 0.04, 0)), "")
        self.assertEqual(sketch_axes.axis_of((0, 0, 0)), "")

    def test_front_plane_upright_is_blue(self):
        level, upright = sketch_axes.colours((1, 0, 0), (0, 0, 1))
        self.assertEqual(level, origin_look.AXIS_RGB["X"])
        self.assertEqual(upright, origin_look.AXIS_RGB["Z"])

    def test_top_plane_is_red_and_green(self):
        level, upright = sketch_axes.colours((1, 0, 0), (0, 1, 0))
        self.assertEqual(level, origin_look.AXIS_RGB["X"])
        self.assertEqual(upright, origin_look.AXIS_RGB["Y"])

    def test_right_plane_is_green_and_blue(self):
        level, upright = sketch_axes.colours((0, 1, 0), (0, 0, 1))
        self.assertEqual(level, origin_look.AXIS_RGB["Y"])
        self.assertEqual(upright, origin_look.AXIS_RGB["Z"])

    def test_underside_keeps_the_axis_colours(self):
        # a sketch on a bottom face: its level line runs along -X, its upright one along Y
        level, upright = sketch_axes.colours((-1, 0, 0), (0, 1, 0))
        self.assertEqual(level, origin_look.AXIS_RGB["X"])
        self.assertEqual(upright, origin_look.AXIS_RGB["Y"])

    def test_slanted_face_keeps_freecads_colours(self):
        level, upright = sketch_axes.colours((1, 0, 0), (0, 0.6, 0.8))
        self.assertEqual(level, origin_look.AXIS_RGB["X"])
        self.assertEqual(upright, sketch_axes.FREECAD_V)

    def test_default_colour_is_replaced(self):
        blue = origin_look.AXIS_RGB["Z"]
        self.assertEqual(sketch_axes.shown((0.2, 0.8, 0.2), sketch_axes.FREECAD_V, blue), blue)

    def test_hovered_line_keeps_freecads_highlight(self):
        blue = origin_look.AXIS_RGB["Z"]
        hover = (1.0, 0.83, 0.0)
        self.assertEqual(sketch_axes.shown(hover, sketch_axes.FREECAD_V, blue), hover)


if __name__ == "__main__":
    unittest.main()
