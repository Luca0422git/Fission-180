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


if __name__ == "__main__":
    unittest.main()
