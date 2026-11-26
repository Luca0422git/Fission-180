# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fission 180's own title bar (fission180/titlebar_core.py; Luca, 2026-11-23: "on my laptop
screen where there is less real estate, That top bar that says Fission 180 with the minimize and
close button is kinda annoying. Is there a way to integrate the top bar into the program? for
both windows and linux"). Runs without FreeCAD."""

import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from fission180 import titlebar_core as core  # noqa: E402


class Mode(unittest.TestCase):
    def test_own_title_bar_by_default(self):
        self.assertEqual(core.DEFAULT_MODE, core.OWN)
        self.assertEqual([v for v, _label in core.CHOICES], [core.OWN, core.SYSTEM])

    def test_unknown_text_is_the_default(self):
        self.assertEqual(core.mode_of("system"), core.SYSTEM)
        self.assertEqual(core.mode_of("own"), core.OWN)
        self.assertEqual(core.mode_of(""), core.OWN)
        self.assertEqual(core.mode_of("nonsense"), core.OWN)


class Grips(unittest.TestCase):
    def test_eight_grips_hug_the_edges(self):
        g = core.grips(1000, 600)
        self.assertEqual(
            sorted(g),
            sorted(["top", "bottom", "left", "right", "top_left", "top_right", "bottom_left", "bottom_right"]),
        )
        e, c = core.GRIP, core.CORNER
        self.assertEqual(g["top"], (c, 0, 1000 - 2 * c, e))
        self.assertEqual(g["bottom"], (c, 600 - e, 1000 - 2 * c, e))
        self.assertEqual(g["left"], (0, c, e, 600 - 2 * c))
        self.assertEqual(g["right"], (1000 - e, c, e, 600 - 2 * c))
        self.assertEqual(g["top_left"], (0, 0, c, c))
        self.assertEqual(g["bottom_right"], (1000 - c, 600 - c, c, c))

    def test_grips_do_not_overlap(self):
        rects = list(core.grips(800, 500).values())
        for i, (ax, ay, aw, ah) in enumerate(rects):
            for bx, by, bw, bh in rects[i + 1 :]:
                overlap = ax < bx + bw and bx < ax + aw and ay < by + bh and by < ay + ah
                self.assertFalse(overlap, ((ax, ay, aw, ah), (bx, by, bw, bh)))

    def test_each_grip_resizes_its_edges(self):
        self.assertEqual(core.EDGES["top"], ("top",))
        self.assertEqual(core.EDGES["bottom_left"], ("bottom", "left"))
        self.assertEqual(set(core.EDGES), set(core.grips(100, 100)))

    def test_a_tiny_window_gets_no_negative_sizes(self):
        for _name, (_x, _y, w, h) in core.grips(10, 10).items():
            self.assertGreaterEqual(w, 0)
            self.assertGreaterEqual(h, 0)



class WindowsHitTest(unittest.TestCase):
    """Windows keeps the window's frame; Fission 180 says what is under the mouse inside it
    (titlebar_win, Luca 2026-11-26: the frameless window broke moving, resizing, maximize and
    the hidden taskbar on Windows)."""

    def test_the_top_band_resizes(self):
        self.assertEqual(core.hit_test(500, 0, 1000, False, True), core.TOP)
        self.assertEqual(core.hit_test(500, core.TOP_BAND - 1, 1000, False, True), core.TOP)

    def test_the_top_band_ends_resize_two_edges(self):
        self.assertEqual(core.hit_test(2, 1, 1000, False, False), core.TOP_LEFT)
        self.assertEqual(core.hit_test(999, 1, 1000, False, False), core.TOP_RIGHT)

    def test_an_empty_part_of_the_top_row_is_the_caption(self):
        self.assertEqual(core.hit_test(500, core.TOP_BAND, 1000, False, True), core.CAPTION)
        self.assertEqual(core.hit_test(500, 20, 1000, False, True), core.CAPTION)

    def test_buttons_and_the_rest_are_the_programs(self):
        self.assertEqual(core.hit_test(500, 20, 1000, False, False), core.CLIENT)
        self.assertEqual(core.hit_test(500, 400, 1000, False, False), core.CLIENT)

    def test_maximized_has_no_top_band(self):
        # (a maximized window does not resize: its top row is caption up to the screen's edge)
        self.assertEqual(core.hit_test(500, 0, 1000, True, True), core.CAPTION)
        self.assertEqual(core.hit_test(2, 0, 1000, True, False), core.CLIENT)


class AutohideGaps(unittest.TestCase):
    MON = (0, 0, 1920, 1080)

    def test_a_hiding_taskbar_at_the_bottom_keeps_two_pixels(self):
        self.assertEqual(core.autohide_gaps(self.MON, self.MON, ["bottom"]), (0, 0, 1920, 1078))

    def test_each_hiding_edge(self):
        self.assertEqual(core.autohide_gaps(self.MON, self.MON, ["left"]), (2, 0, 1920, 1080))
        self.assertEqual(core.autohide_gaps(self.MON, self.MON, ["top"]), (0, 2, 1920, 1080))
        self.assertEqual(core.autohide_gaps(self.MON, self.MON, ["right"]), (0, 0, 1918, 1080))

    def test_no_hiding_taskbar_changes_nothing(self):
        self.assertIsNone(core.autohide_gaps(self.MON, (0, 0, 1920, 1040), []))

    def test_an_edge_the_work_area_already_leaves_free(self):
        # (a taskbar that stays at the bottom, another that hides at the top)
        self.assertEqual(core.autohide_gaps(self.MON, (0, 0, 1920, 1040), ["top"]), (0, 2, 1920, 1040))
        self.assertIsNone(core.autohide_gaps(self.MON, (0, 0, 1920, 1040), ["bottom"]))


if __name__ == "__main__":
    unittest.main()
