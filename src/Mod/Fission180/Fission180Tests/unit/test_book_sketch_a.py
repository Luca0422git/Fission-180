# SPDX-License-Identifier: LGPL-2.1-or-later
"""Wave 7 (the book parity report), sketch-a: the pure rules behind drawing, snapping and
selecting in a sketch. Runs without FreeCAD."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fission180 import sketch_centerline as centerline  # noqa: E402
from fission180 import sketch_draw_helpers as helpers  # noqa: E402
from fission180 import sketch_grid  # noqa: E402
from fission180 import sketch_infer_core as core  # noqa: E402
from fission180 import sketch_select_core as select  # noqa: E402


class GridReach(unittest.TestCase):
    """A grid line pulls within a distance on the screen, never a share of a coarse grid."""

    def test_freecads_rule_without_a_reach(self):
        # a fifth of the spacing: 8 mm off a 50 mm line lands on it (the report's bug)
        self.assertEqual(core.grid_snap(8.0, 50.0), 0.0)
        self.assertEqual(core.grid_snap(-8.0, 50.0), 0.0)
        self.assertEqual(core.grid_snap(11.0, 50.0), 11.0)

    def test_a_reach_ends_the_pull(self):
        # 8 pixels at 0.18 mm per pixel
        reach = 8 * 0.18
        self.assertEqual(core.grid_snap(8.0, 50.0, reach), 8.0)
        self.assertEqual(core.grid_snap(6.0, 50.0, reach), 6.0)
        self.assertEqual(core.grid_snap(1.2, 50.0, reach), 0.0)
        self.assertEqual(core.grid_snap(48.9, 50.0, reach), 50.0)

    def test_a_fine_grid_keeps_its_fifth(self):
        # lines 15 pixels apart: a fifth of the spacing (3 pixels) is less than the reach
        self.assertEqual(core.grid_snap(0.5, 2.0, 8 * 0.133), 0.5)
        self.assertEqual(core.grid_snap(0.3, 2.0, 8 * 0.133), 0.0)

    def test_no_grid(self):
        self.assertEqual(core.grid_snap(8.0, None, 1.0), 8.0)
        self.assertEqual(core.grid_snap(8.0, 0.0), 8.0)

    def test_capped_point_only_where_the_rules_differ(self):
        reach = 8 * 0.18
        # both rules leave it: FreeCAD's own snap may place it
        self.assertIsNone(core.grid_capped((23.0, 31.0), 50.0, reach))
        # both rules snap y: FreeCAD's own snap places it exactly
        self.assertIsNone(core.grid_capped((23.0, 1.0), 50.0, reach))
        # FreeCAD would pull y = 8 onto the axis, the reach does not
        result = core.grid_capped((23.0, 8.0), 50.0, reach)
        self.assertEqual(result.point, (23.0, 8.0))
        self.assertEqual(result.grid, [])
        # x within the reach still lands on its line, y stays
        result = core.grid_capped((49.5, 8.0), 50.0, reach)
        self.assertEqual(result.point, (50.0, 8.0))
        self.assertEqual(result.grid, [(0, 50.0)])

    def test_capped_needs_a_coarser_grid_than_the_reach(self):
        self.assertIsNone(core.grid_capped((0.3, 0.5), 2.0, 8 * 0.133))
        self.assertIsNone(core.grid_capped((8.0, 8.0), 50.0, None))
        self.assertIsNone(core.grid_capped((8.0, 8.0), None, 1.0))

    def test_freecads_grid_is_off_for_a_capped_point(self):
        result = core.grid_capped((49.5, 8.0), 50.0, 1.44)
        self.assertTrue(core.grid_off(result, 50.0, 0.18))

    def test_exact_after_the_click(self):
        result = core.grid_capped((49.5, 8.0), 50.0, 1.44)
        # FreeCAD placed the pixel nearest to (50, 8)
        self.assertEqual(core.exact_point(result, (50.07, 8.05), 0.18), (50.0, 8.05))
        # placed somewhere else (a typed value): left alone
        self.assertIsNone(core.exact_point(result, (55.0, 8.0), 0.18))

    def test_a_guides_free_coordinate_keeps_the_reach(self):
        # a point level with an acquired point: y is the guide's, x is free. 8 mm from the
        # 50 mm line it stays where the pointer is
        opt = core.Options(grid=50.0, grid_reach=1.44)
        acquired = [((0, 1), (20.0, 30.0))]
        result = core.infer((58.0, 30.2), None, acquired, [], [], [], 0.18, opt, [], [])
        self.assertIsNotNone(result)
        self.assertAlmostEqual(result.point[1], 30.0)
        self.assertAlmostEqual(result.point[0], 58.0)
        # ...and FreeCAD's own grid snap must then be off for it (it would pull x to 50)
        self.assertTrue(core.grid_off(result, 50.0, 0.18))


class GridSpacing(unittest.TestCase):
    def test_fixed_is_major_over_subdivisions(self):
        self.assertAlmostEqual(sketch_grid.spacing_for("mm", False, 50.0, 5), 10.0)
        self.assertAlmostEqual(sketch_grid.spacing_for("in", False, 25.4, 4), 6.35)
        self.assertAlmostEqual(sketch_grid.spacing_for("mm", False, 50.0, 0), 50.0)

    def test_adaptive_metric_starts_from_the_setting(self):
        self.assertAlmostEqual(sketch_grid.spacing_for("mm", True, 10.0, 5), 10.0)
        self.assertAlmostEqual(sketch_grid.spacing_for("cm", True, 10.0, 5), 10.0)

    def test_adaptive_inch_starts_from_an_inch(self):
        self.assertAlmostEqual(sketch_grid.spacing_for("in", True, 10.0, 5), 25.4)
        self.assertAlmostEqual(sketch_grid.spacing_for("ft", True, 10.0, 5), 25.4)


class ClickRule(unittest.TestCase):
    def test_plans(self):
        self.assertEqual(select.click_plan(False, False, False), "replace")
        self.assertEqual(select.click_plan(True, False, False), "add")
        self.assertEqual(select.click_plan(False, True, False), "toggle")
        self.assertEqual(select.click_plan(True, True, False), "toggle")
        # a command collecting curves: a plain click adds or drops, as FreeCAD's does
        self.assertEqual(select.click_plan(False, False, True), "toggle")

    def test_plain_click_replaces(self):
        self.assertEqual(select.after_click(["Edge1", "Edge2"], ["Edge3"], "replace"), ["Edge3"])
        self.assertEqual(select.after_click(["Edge1", "Edge2"], ["Edge1"], "replace"), ["Edge1"])

    def test_shift_only_adds(self):
        self.assertEqual(select.after_click(["Edge1"], ["Edge3"], "add"), ["Edge1", "Edge3"])
        self.assertEqual(
            select.after_click(["Edge1", "Edge3"], ["Edge3"], "add"), ["Edge1", "Edge3"]
        )

    def test_ctrl_toggles(self):
        self.assertEqual(select.after_click(["Edge1"], ["Edge3"], "toggle"), ["Edge1", "Edge3"])
        self.assertEqual(select.after_click(["Edge1", "Edge3"], ["Edge3"], "toggle"), ["Edge1"])

    def test_dimensions_on_one_another(self):
        got = select.after_click(
            ["Edge1"], ["Constraint2", "Constraint3", "Constraint2"], "replace"
        )
        self.assertEqual(got, ["Constraint2", "Constraint3"])


class Centerline(unittest.TestCase):
    def test_mirror_across_a_level_line(self):
        self.assertEqual(centerline.mirror((30.0, 10.0), (0.0, 0.0), (30.0, 0.0)), (30.0, -10.0))

    def test_mirror_across_a_slanted_line(self):
        x, y = centerline.mirror((0.0, 2.0), (0.0, 0.0), (5.0, 5.0))
        self.assertAlmostEqual(x, 2.0)
        self.assertAlmostEqual(y, 0.0)

    # (wave 7's merge, sketch-c: the diameter is made by the one Dimension tool,
    # sketch_dimension_tool.py; what counts as one is read back from the constraints)
    def test_a_distance_to_the_mirror_image_is_a_diameter(self):
        no = centerline.NO_GEO
        cons = [
            ("Coincident", 0, 2, 1, 1, no),
            ("Symmetric", 2, 1, 5, 1, 0),  # point 5 mirrors corner (2, 1) across line 0
            ("Distance", 2, 1, 5, 1, no),  # the diameter
            ("Distance", 2, 1, 3, 1, no),  # another distance
        ]
        self.assertEqual(centerline.diameter_dimensions(cons, [0]), [2])
        # ...whichever way round the dimension names its two points
        cons[2] = ("Distance", 5, 1, 2, 1, no)
        self.assertEqual(centerline.diameter_dimensions(cons, [0]), [2])

    def test_what_is_no_diameter(self):
        no = centerline.NO_GEO
        cons = [
            ("Symmetric", 2, 1, 5, 1, 4),  # mirrored across a line that is no centerline
            ("Distance", 2, 1, 5, 1, no),
            ("DistanceX", 2, 1, 5, 1, no),
        ]
        self.assertEqual(centerline.diameter_dimensions(cons, [0]), [])
        self.assertEqual(centerline.diameter_dimensions(cons, []), [])
        # the same sketch with line 4 a centerline: the Distance is one, the DistanceX not
        self.assertEqual(centerline.diameter_dimensions(cons, [4]), [1])


class PolygonParts(unittest.TestCase):
    def test_circumscribed_hides_the_corner_circle_and_the_spoke(self):
        ids = list(range(10, 19))  # 6 lines, corner circle, spoke, edge circle
        lines, hide, keep = helpers.polygon_parts(ids, 6, True)
        self.assertEqual(lines, [10, 11, 12, 13, 14, 15])
        self.assertEqual(hide, [16, 17])
        self.assertEqual(keep, 18)

    def test_inscribed_keeps_its_circle(self):
        ids = list(range(0, 7))
        lines, hide, keep = helpers.polygon_parts(ids, 6, False)
        self.assertEqual(lines, [0, 1, 2, 3, 4, 5])
        self.assertEqual(hide, [])
        self.assertEqual(keep, 6)


if __name__ == "__main__":
    unittest.main()
