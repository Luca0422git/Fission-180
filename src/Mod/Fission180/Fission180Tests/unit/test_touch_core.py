# SPDX-License-Identifier: LGPL-2.1-or-later
"""The touchscreen's fingers read as orbit, pan, zoom and clicks (fission180/touch_core.py,
docs/fission180/touchscreen-design.md). Runs without FreeCAD."""

import math
import os
import sys
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, ROOT)

from fission180 import touch_core as tc  # noqa: E402


def kinds(actions):
    return [a[0] for a in actions]


def run(tracker, steps):
    """steps: (t, kind, points) with kind begin/update/end/tick; all actions in order."""
    out = []
    for t, kind, points in steps:
        if kind == "tick":
            out += tracker.tick(t)
        else:
            out += getattr(tracker, kind)(t, points)
    return out


def drag(start, end, t0=0.0, steps=10, dt=0.02, finger=1):
    (x0, y0), (x1, y1) = start, end
    seq = [(t0, "begin", {finger: (x0, y0)})]
    for i in range(1, steps + 1):
        f = i / steps
        seq.append((t0 + i * dt, "update", {finger: (x0 + (x1 - x0) * f, y0 + (y1 - y0) * f)}))
    seq.append((t0 + (steps + 1) * dt, "end", {}))
    return seq


class Taps(unittest.TestCase):
    def test_tap_is_a_click(self):
        actions = run(tc.Tracker(), [(0.0, "begin", {1: (100, 50)}), (0.1, "end", {})])
        self.assertEqual(actions, [("click", 100, 50)])

    def test_jitter_under_8_px_stays_a_tap(self):
        actions = run(
            tc.Tracker(),
            [(0.0, "begin", {1: (100, 50)}), (0.05, "update", {1: (105, 53)}), (0.1, "end", {})],
        )
        self.assertEqual(kinds(actions), ["click"])

    def test_two_taps_make_a_double_click(self):
        t = tc.Tracker()
        first = run(t, [(0.0, "begin", {1: (100, 50)}), (0.08, "end", {})])
        second = run(t, [(0.3, "begin", {1: (103, 52)}), (0.38, "end", {})])
        self.assertEqual(first, [("click", 100, 50)])
        self.assertEqual(kinds(second), ["double_click"])

    def test_taps_far_apart_are_two_clicks(self):
        t = tc.Tracker()
        run(t, [(0.0, "begin", {1: (100, 50)}), (0.08, "end", {})])
        second = run(t, [(0.3, "begin", {1: (300, 50)}), (0.38, "end", {})])
        self.assertEqual(kinds(second), ["click"])

    def test_long_press_is_a_right_click_and_the_release_does_nothing(self):
        t = tc.Tracker()
        actions = run(
            t,
            [
                (0.0, "begin", {1: (100, 50)}),
                (0.3, "tick", None),
                (0.55, "tick", None),
                (0.6, "update", {1: (102, 51)}),
                (0.9, "end", {}),
            ],
        )
        self.assertEqual(actions, [("right_click", 100, 50)])

    def test_two_finger_tap_is_a_right_click_between_them(self):
        actions = run(
            tc.Tracker(),
            [
                (0.0, "begin", {1: (100, 100)}),
                (0.03, "update", {1: (100, 100), 2: (200, 100)}),
                (0.2, "end", {2: (200, 100)}),
                (0.22, "end", {}),
            ],
        )
        self.assertEqual(actions, [("right_click", 150, 100)])

    def test_two_finger_tap_close_together_with_jitter_does_not_zoom(self):
        # (fingers 60 px apart: 3 px of jitter is 5 %, but under the 8 px a tap may move)
        actions = run(
            tc.Tracker(),
            [
                (0.0, "begin", {1: (100, 100)}),
                (0.02, "update", {1: (100, 100), 2: (160, 100)}),
                (0.08, "update", {1: (98, 100), 2: (161, 100)}),
                (0.15, "end", {}),
            ],
        )
        self.assertEqual(kinds(actions), ["right_click"])

    def test_a_cancelled_tap_does_nothing(self):
        t = tc.Tracker()
        self.assertEqual(run(t, [(0.0, "begin", {1: (100, 50)})]), [])
        self.assertEqual(t.cancel(0.1), [])
        self.assertEqual(t.state, tc.IDLE)


class Drags(unittest.TestCase):
    def test_one_finger_drag_orbits_after_8_px(self):
        actions = run(tc.Tracker(), drag((100, 100), (130, 100)))
        self.assertTrue(actions and set(kinds(actions)) == {"orbit"}, actions)
        self.assertAlmostEqual(sum(a[1] for a in actions), 30.0)
        self.assertAlmostEqual(sum(a[2] for a in actions), 0.0)

    def test_two_fingers_together_pan_by_the_midpoint(self):
        seq = [(0.0, "begin", {1: (100, 100)}), (0.01, "update", {1: (100, 100), 2: (200, 100)})]
        for i in range(1, 11):
            seq.append((0.01 + 0.02 * i, "update", {1: (100, 100 + 4 * i), 2: (200, 100 + 4 * i)}))
        seq.append((0.4, "end", {}))
        actions = run(tc.Tracker(), seq)
        self.assertEqual(set(kinds(actions)), {"pan"}, actions)
        self.assertAlmostEqual(sum(a[1] for a in actions), 0.0)
        self.assertAlmostEqual(sum(a[2] for a in actions), 40.0)

    def test_spread_zooms_about_the_midpoint(self):
        seq = [(0.0, "begin", {1: (100, 100)}), (0.01, "update", {1: (100, 100), 2: (200, 100)})]
        for i in range(1, 11):
            seq.append((0.01 + 0.02 * i, "update", {1: (100 - 2.5 * i, 100), 2: (200 + 2.5 * i, 100)}))
        seq.append((0.4, "end", {}))
        actions = run(tc.Tracker(), seq)
        zooms = [a for a in actions if a[0] == "zoom"]
        self.assertTrue(zooms, actions)
        self.assertTrue(all(a[1] > 0 for a in zooms), zooms)  # (apart: the model grows)
        # the spread 100 -> 150 px, less the last JITTER_PX (a wobble that small is ignored)
        self.assertAlmostEqual(sum(a[1] for a in zooms), math.log((150 - tc.JITTER_PX) / 100), places=6)
        self.assertEqual(zooms[-1][2], (150, 100))

    def test_two_finger_pan_with_wobbly_spacing_does_not_zoom(self):
        # Luca (2026-11-23, a real touchscreen): "When i pan with two fingers ... the whole
        # screen kinda shakes and zooms in and out super quickly": the fingers' distance
        # wobbles by some pixels while they move together
        wobble = [0, 9, -7, 11, -10, 6, -12, 8, -5, 12, -9, 4, -11, 10, -6]
        seq = [(0.0, "begin", {1: (100, 300)}), (0.01, "update", {1: (100, 300), 2: (260, 300)})]
        for i in range(1, 31):
            w = wobble[i % len(wobble)] / 2.0
            seq.append((0.01 + 0.016 * i, "update", {1: (100 - w, 300 - 5 * i), 2: (260 + w, 300 - 5 * i)}))
        seq.append((0.6, "end", {}))
        actions = run(tc.Tracker(), seq)
        self.assertNotIn("zoom", kinds(actions), actions)
        self.assertAlmostEqual(sum(a[2] for a in actions if a[0] == "pan"), -150.0)

    def test_holding_still_after_a_pinch_does_not_shake(self):
        seq = [(0.0, "begin", {1: (100, 100)}), (0.01, "update", {1: (100, 100), 2: (200, 100)})]
        for i in range(1, 11):  # spread 100 -> 200 px
            seq.append((0.01 + 0.02 * i, "update", {1: (100 - 5 * i, 100), 2: (200 + 5 * i, 100)}))
        for i, w in enumerate([3, -4, 5, -3, 4, -5, 2, -4, 5, -2]):  # held, wobbling
            seq.append((0.3 + 0.02 * i, "update", {1: (50 - w / 2.0, 100), 2: (250 + w / 2.0, 100)}))
        seq.append((0.6, "end", {}))
        actions = run(tc.Tracker(), seq)
        zooms = [a for a in actions if a[0] == "zoom"]
        self.assertTrue(zooms)
        self.assertTrue(all(a[1] > 0 for a in zooms), zooms)  # no zooming back and forth

    def test_no_zoom_under_4_percent(self):
        seq = [
            (0.0, "begin", {1: (100, 100)}),
            (0.01, "update", {1: (100, 100), 2: (200, 100)}),
            (0.1, "update", {1: (99, 100), 2: (202, 100)}),
            (0.3, "end", {}),
        ]
        self.assertNotIn("zoom", kinds(run(tc.Tracker(), seq)))

    def test_second_finger_after_orbit_switches_to_pan_without_a_jump(self):
        seq = drag((100, 100), (140, 100))[:-1]  # one finger orbiting, still down
        seq += [
            (0.3, "update", {1: (140, 100), 2: (240, 100)}),
            (0.32, "update", {1: (140, 110), 2: (240, 110)}),
            (0.34, "update", {1: (140, 120), 2: (240, 120)}),
            (0.36, "update", {1: (140, 130)}),  # one lifted: no orbit any more
            (0.38, "update", {1: (160, 150)}),
            (0.4, "end", {}),
        ]
        actions = run(tc.Tracker(), seq)
        after = actions[[i for i, a in enumerate(actions) if a[0] == "orbit"][-1] + 1 :]
        self.assertEqual(set(kinds(after)), {"pan"}, actions)
        self.assertAlmostEqual(sum(a[2] for a in after), 20.0)  # (no jump at the switch)


class MouseLike(unittest.TestCase):
    def test_drag_is_a_mouse_drag(self):
        actions = run(tc.Tracker(mouse_like=True), drag((100, 100), (140, 120)))
        self.assertEqual(actions[0], ("press", 100, 100))
        self.assertEqual(actions[-1], ("release", 140, 120))
        self.assertEqual(set(kinds(actions[1:-1])), {"move"})
        self.assertNotIn("orbit", kinds(actions))

    def test_tap_is_a_click(self):
        actions = run(tc.Tracker(mouse_like=True), [(0.0, "begin", {1: (10, 20)}), (0.1, "end", {})])
        self.assertEqual(actions, [("click", 10, 20)])

    def test_a_cancelled_drag_lets_go_of_the_button(self):
        t = tc.Tracker(mouse_like=True)
        run(t, drag((100, 100), (140, 120))[:-1])  # dragging, the finger still down
        self.assertEqual(t.cancel(0.5), [("release", 140, 120)])
        self.assertEqual(t.state, tc.IDLE)

    def test_a_new_touch_after_a_lost_end_lets_go_of_the_button_first(self):
        t = tc.Tracker(mouse_like=True)
        run(t, drag((100, 100), (140, 120))[:-1])  # its end never came
        self.assertEqual(t.begin(1.0, {1: (10, 10)}), [("release", 140, 120)])
        self.assertEqual(t.state, tc.ONE)

    def test_two_fingers_still_pan(self):
        seq = [(0.0, "begin", {1: (100, 100)}), (0.01, "update", {1: (100, 100), 2: (200, 100)})]
        seq += [(0.1, "update", {1: (130, 100), 2: (230, 100)}), (0.2, "end", {})]
        self.assertEqual(set(kinds(run(tc.Tracker(mouse_like=True), seq))), {"pan"})


if __name__ == "__main__":
    unittest.main()
