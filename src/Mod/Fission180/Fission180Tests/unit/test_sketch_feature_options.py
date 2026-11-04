# SPDX-License-Identifier: LGPL-2.1-or-later
"""Feature Options: the running tool's family and type (fission180/sketch_feature_options.py)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fission180 import ribbon_config as cfg  # noqa: E402
from fission180 import sketch_feature_options as fo  # noqa: E402


class Families(unittest.TestCase):
    def setUp(self):
        self.f = fo.families(cfg.SKETCH_CREATE["items"])

    def test_the_create_submenus(self):
        self.assertEqual(set(self.f), set(fo.FAMILIES))
        self.assertEqual([m[0] for m in self.f["Rectangle"]], ["2-Point Rectangle", "3-Point Rectangle", "Center Rectangle"])
        self.assertEqual(len(self.f["Circle"]), 5)

    def test_short_names(self):
        self.assertEqual([m[2] for m in self.f["Rectangle"]], ["2-Point", "3-Point", "Center"])
        self.assertEqual(fo.short("Fit Point Spline", "Spline"), "Fit Point")
        self.assertEqual(fo.short("Edge Polygon", "Polygon"), "Edge")

    def test_running_tool(self):
        self.assertEqual(fo.running(self.f, ["Sketcher_CreateRectangle_Center"]), ("Rectangle", "Center Rectangle"))
        # Fission 180's own 3-point rectangle (its DrawTool's command)
        self.assertEqual(fo.running(self.f, [None, "Fission180_SketchRectangle3Point"]), ("Rectangle", "3-Point Rectangle"))
        # the Fit Point Spline records FreeCAD's command when it runs FreeCAD's tool
        self.assertEqual(fo.running(self.f, ["Sketcher_CreateBSplineByInterpolation"]), ("Spline", "Fit Point Spline"))
        self.assertEqual(fo.running(self.f, ["Fission180_SketchLine"]), (None, None))


if __name__ == "__main__":
    unittest.main()
