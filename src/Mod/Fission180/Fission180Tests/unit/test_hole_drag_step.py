# SPDX-License-Identifier: LGPL-2.1-or-later
"""A dragged hole position lands on clean values (hole_snaps_core.drag_step / drag_value)."""

import unittest

from fission180 import hole_snaps_core as core


class DragStep(unittest.TestCase):
    def test_step_is_at_least_two_pixels(self):
        self.assertEqual(core.drag_step(0.2), 0.5)  # 0.4 mm on the screen: 0.5 mm steps
        self.assertEqual(core.drag_step(0.05), 0.1)
        self.assertEqual(core.drag_step(0.004), 0.01)
        self.assertEqual(core.drag_step(3.0), 10.0)

    def test_zoomed_far_out_and_in(self):
        self.assertEqual(core.drag_step(1000.0), 100.0)  # never coarser than the last step
        self.assertEqual(core.drag_step(0.0), 0.01)  # never finer than the first

    def test_inch_design_steps_are_inch_values(self):
        self.assertAlmostEqual(core.drag_step(0.2, inch=True), 0.05 * 25.4)
        self.assertAlmostEqual(core.drag_step(0.01, inch=True), 0.001 * 25.4)

    def test_the_reports_drag(self):
        # dragged back to the axis, 0.055 mm short of it, a pixel being 0.2 mm
        self.assertEqual(core.drag_value(-0.055, 0.2), 0.0)
        self.assertEqual(str(core.drag_value(-0.055, 0.2)), "0.0")  # no -0.0
        self.assertEqual(core.drag_value(12.26, 0.2), 12.5)
        self.assertEqual(core.drag_value(-7.74, 0.2), -7.5)

    def test_fine_when_zoomed_in(self):
        self.assertEqual(core.drag_value(1.234, 0.004), 1.23)

    def test_inch_values(self):
        self.assertAlmostEqual(core.drag_value(25.0, 0.2, inch=True), 25.4)  # 1 in


if __name__ == "__main__":
    unittest.main()
