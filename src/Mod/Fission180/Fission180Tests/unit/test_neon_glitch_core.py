# SPDX-License-Identifier: LGPL-2.1-or-later
"""neon_glitch_core: when Neon Lights' glitch may show (neon-lights-design.md 6.7): every 40-120 s,
for 80-150 ms, and never while a person is busy, in the tests, or with the effects off."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from fission180 import neon_glitch_core as g  # noqa: E402


class Timing(unittest.TestCase):
    def test_delay_bounds(self):
        self.assertAlmostEqual(g.next_delay(0.0), 40.0)
        self.assertAlmostEqual(g.next_delay(1.0), 120.0)
        self.assertAlmostEqual(g.next_delay(0.5), 80.0)
        for i in range(101):
            self.assertTrue(40.0 <= g.next_delay(i / 100.0) <= 120.0)

    def test_duration_bounds(self):
        self.assertAlmostEqual(g.duration(0.0), 0.08)
        self.assertAlmostEqual(g.duration(1.0), 0.15)
        for i in range(101):
            self.assertTrue(0.08 <= g.duration(i / 100.0) <= 0.15)

    def test_out_of_range_numbers_clamp(self):
        self.assertAlmostEqual(g.next_delay(-3), 40.0)
        self.assertAlmostEqual(g.next_delay(7), 120.0)
        self.assertAlmostEqual(g.duration(float("nan")), 0.08)
        self.assertAlmostEqual(g.duration(None), 0.08)
        self.assertAlmostEqual(g.duration("x"), 0.08)


class MayFire(unittest.TestCase):
    def test_free_when_nothing_is_going_on(self):
        self.assertTrue(g.may_fire({}))
        self.assertTrue(g.may_fire(None))
        self.assertTrue(g.may_fire({key: False for key in g.BLOCKERS}))

    def test_every_busy_flag_blocks(self):
        expected = {
            "mouse_down", "dragging", "text_focus", "task_dialog", "recomputing",
            "testing", "inactive", "effects_off", "glitch_off",
        }
        self.assertEqual(set(g.BLOCKERS), expected)
        for key in g.BLOCKERS:
            state = {other: False for other in g.BLOCKERS}
            state[key] = True
            self.assertFalse(g.may_fire(state), key)
            self.assertEqual(g.why_not(state), [key])

    def test_several_flags(self):
        state = {"mouse_down": True, "testing": True, "unknown": True}
        self.assertFalse(g.may_fire(state))
        self.assertEqual(g.why_not(state), ["mouse_down", "testing"])


if __name__ == "__main__":
    unittest.main()
