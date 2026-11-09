# SPDX-License-Identifier: LGPL-2.1-or-later
"""touchpad_core: two fingers pan, a pinch zooms, a mouse wheel still zooms (Luca,
2026-11-09: "2 fingers drag to pan, pinch to zoom")."""

import math
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fission180 import prefs_core  # noqa: E402
from fission180 import touchpad_core as core  # noqa: E402

NONE = (0, 0)


def look(device=False, phase=0, pixel=NONE, angle=NONE):
    return core.look(device, phase, pixel, angle)


class Look(unittest.TestCase):
    def test_mouse_wheel_notches(self):
        for y in (120, -120, 240, -360):
            self.assertEqual(look(angle=(0, y)), core.WHEEL, y)

    def test_touchpad_device(self):
        self.assertEqual(look(device=True, angle=(0, 120)), core.TOUCHPAD)

    def test_scroll_phase(self):
        self.assertEqual(look(phase=2, angle=(0, 120)), core.TOUCHPAD)
        self.assertEqual(look(phase=3), core.TOUCHPAD)  # the end of a scroll, no delta

    def test_pixel_delta(self):
        self.assertEqual(look(pixel=(0, 3), angle=(0, 120)), core.TOUCHPAD)

    def test_sideways(self):
        self.assertEqual(look(angle=(7, 0)), core.TOUCHPAD)
        self.assertEqual(look(angle=(-120, 0)), core.TOUCHPAD)
        self.assertEqual(look(angle=(4, 120)), core.TOUCHPAD)

    def test_odd_steps(self):
        for y in (1, 7, -23, 41, 119, 121, 202):
            self.assertEqual(look(angle=(0, y)), core.TOUCHPAD, y)

    def test_high_resolution_wheel_steps(self):
        for y in (15, 20, 24, 30, 40, 60, -45, 48, 80, 90, 105):
            self.assertEqual(look(angle=(0, y)), core.FINE, y)

    def test_nothing(self):
        self.assertEqual(look(), core.NOTHING)


class StreamTests(unittest.TestCase):
    def test_a_wheel_stays_a_wheel(self):
        stream = core.Stream()
        self.assertEqual(stream.judge(core.WHEEL, 0.0), core.WHEEL)
        self.assertEqual(stream.judge(core.WHEEL, 0.05), core.WHEEL)
        self.assertEqual(stream.judge(core.FINE, 0.1), core.WHEEL)

    def test_a_touchpad_scroll_keeps_panning(self):
        stream = core.Stream()
        self.assertEqual(stream.judge(core.TOUCHPAD, 0.0), core.TOUCHPAD)
        # a stray whole notch or fine step in the middle of it does not zoom
        self.assertEqual(stream.judge(core.WHEEL, 0.02), core.TOUCHPAD)
        self.assertEqual(stream.judge(core.FINE, 0.04), core.TOUCHPAD)
        self.assertEqual(stream.judge(core.NOTHING, 0.06), core.TOUCHPAD)

    def test_a_fine_first_step_then_touchpad(self):
        stream = core.Stream()
        self.assertEqual(stream.judge(core.FINE, 0.0), core.WHEEL)
        self.assertEqual(stream.judge(core.TOUCHPAD, 0.01), core.TOUCHPAD)
        self.assertEqual(stream.judge(core.FINE, 0.02), core.TOUCHPAD)

    def test_a_pause_starts_a_new_scroll(self):
        stream = core.Stream()
        stream.judge(core.TOUCHPAD, 0.0)
        self.assertEqual(stream.judge(core.WHEEL, 0.0 + core.STREAM_GAP + 0.01), core.WHEEL)
        stream.judge(core.WHEEL, 5.0)
        self.assertEqual(stream.judge(core.TOUCHPAD, 5.05), core.TOUCHPAD)

    def test_the_same_event_twice(self):
        # an event Qt hands from the drawing area on to the viewer is judged twice
        stream = core.Stream()
        self.assertEqual(stream.judge(core.WHEEL, 1.0), stream.judge(core.WHEEL, 1.0))
        stream = core.Stream()
        self.assertEqual(stream.judge(core.TOUCHPAD, 1.0), stream.judge(core.TOUCHPAD, 1.0))

    def test_clock_going_back(self):
        stream = core.Stream()
        stream.judge(core.TOUCHPAD, 10.0)
        self.assertEqual(stream.judge(core.WHEEL, 3.0), core.WHEEL)

    def test_nothing_first(self):
        self.assertIsNone(core.Stream().judge(core.NOTHING, 0.0))


class Action(unittest.TestCase):
    def test_auto(self):
        self.assertEqual(core.action("auto", core.TOUCHPAD, core.TOUCHPAD), core.PAN)
        self.assertEqual(core.action("auto", core.WHEEL, core.WHEEL), core.PASS)
        self.assertEqual(core.action("auto", core.FINE, core.WHEEL), core.PASS)
        self.assertEqual(core.action("auto", core.WHEEL, core.TOUCHPAD), core.PAN)

    def test_pinch_as_ctrl_wheel(self):
        self.assertEqual(core.action("auto", core.TOUCHPAD, core.TOUCHPAD, ctrl=True), core.ZOOM)
        # Ctrl + a mouse wheel: FreeCAD's wheel zoom as before
        self.assertEqual(core.action("auto", core.WHEEL, core.WHEEL, ctrl=True), core.PASS)

    def test_off_leaves_everything_to_freecad(self):
        for seen in (core.TOUCHPAD, core.WHEEL, core.FINE):
            self.assertEqual(core.action("off", seen, core.TOUCHPAD), core.PASS)
            self.assertEqual(core.action("off", seen, core.TOUCHPAD, ctrl=True), core.PASS)

    def test_on_pans_every_scroll(self):
        self.assertEqual(core.action("on", core.WHEEL, core.WHEEL), core.PAN)
        self.assertEqual(core.action("on", core.WHEEL, core.WHEEL, ctrl=True), core.ZOOM)
        self.assertEqual(core.action("on", core.NOTHING, None), core.PASS)

    def test_a_button_held(self):
        # a middle-drag pan with a tilted wheel: FreeCAD's as before
        self.assertEqual(core.action("auto", core.TOUCHPAD, core.TOUCHPAD, buttons=True), core.PASS)
        self.assertEqual(core.action("on", core.WHEEL, core.WHEEL, buttons=True), core.PASS)

    def test_unknown_mode_is_auto(self):
        self.assertEqual(core.action("Maybe", core.TOUCHPAD, core.TOUCHPAD), core.PAN)
        self.assertEqual(core.action(None, core.WHEEL, core.WHEEL), core.PASS)


class Modes(unittest.TestCase):
    def test_normalise(self):
        self.assertEqual(core.normalise_mode(" On "), "on")
        self.assertEqual(core.normalise_mode("OFF"), "off")
        self.assertEqual(core.normalise_mode(""), "auto")
        self.assertEqual(core.normalise_mode(None), "auto")
        self.assertEqual(core.normalise_mode("sometimes"), "auto")

    def test_preference(self):
        opt = prefs_core.option("touchpad")
        self.assertEqual(opt["kind"], "choice")
        self.assertEqual(opt["page"], "general")
        self.assertEqual(opt["group"], "Navigation")
        self.assertEqual(opt["default"], "auto")
        self.assertEqual(opt["store"][1:], ("String", "Touchpad"))
        self.assertEqual(prefs_core.choice_values(opt), ["auto", "off", "on"])
        self.assertEqual([c[1] for c in opt["choices"]], ["Auto", "Off", "On"])
        self.assertIn(("touchpad", "auto"), prefs_core.restore_plan())
        with self.assertRaises(prefs_core.PrefError):
            prefs_core.normalise(opt, "sometimes")


class Pan(unittest.TestCase):
    def test_system_pixels_win(self):
        self.assertEqual(core.pan_pixels((3, -5), (24, -40), "darwin"), (3.0, -5.0))

    def test_units_on_linux(self):
        self.assertEqual(core.pan_pixels(NONE, (0, 120), "linux"), (0.0, 15.0))
        self.assertEqual(core.pan_pixels(NONE, (-8, 16), "linux"), (-1.0, 2.0))

    def test_units_on_windows(self):
        self.assertEqual(core.pan_pixels(NONE, (0, 120), "win32"), (0.0, 60.0))
        self.assertEqual(core.pan_pixels(NONE, (-30, 0), "win32"), (-15.0, 0.0))


class Zoom(unittest.TestCase):
    def test_spread_zooms_in(self):
        self.assertLess(core.pinch_log(0.1), 0)  # the view gets smaller: zoomed in
        self.assertGreater(core.pinch_log(-0.1), 0)
        self.assertAlmostEqual(core.pinch_log(0.25), -math.log(1.25))
        self.assertEqual(core.pinch_log(0), 0)

    def test_silly_values(self):
        self.assertEqual(core.pinch_log(float("nan")), 0.0)
        self.assertEqual(core.pinch_log(None), 0.0)
        self.assertEqual(core.pinch_log(-5), core.MAX_LOG_STEP)  # (no log of a negative)
        self.assertEqual(core.pinch_log(1e9), -core.MAX_LOG_STEP)

    def test_ctrl_wheel(self):
        self.assertAlmostEqual(core.ctrl_wheel_log(120, 0.2), -0.2)
        self.assertAlmostEqual(core.ctrl_wheel_log(-30, 0.2), 0.05)

    def test_units_for_freecad(self):
        # FreeCAD with InvertZoom (its default): +120 units zoom in by exp(0.2)
        self.assertAlmostEqual(core.zoom_units(-0.2, 0.2, True), 120)
        self.assertAlmostEqual(core.zoom_units(0.2, 0.2, True), -120)
        # Reverse zoom direction ticked (InvertZoom off): the other sign, the same zoom
        self.assertAlmostEqual(core.zoom_units(-0.2, 0.2, False), -120)
        self.assertAlmostEqual(core.zoom_units(-0.1, 0.5, True), 24)
        self.assertAlmostEqual(core.zoom_units(-0.2, 0, True), 120)  # (no step: FreeCAD's 0.2)

    def test_a_pinch_spread_is_a_zoom_in_either_way(self):
        for invert in (True, False):
            units = core.zoom_units(core.pinch_log(0.3), 0.2, invert)
            freecad = 0.2 * units / 120.0 * (-1 if invert else 1)  # FreeCAD's log factor
            self.assertLess(freecad, 0, invert)

    def test_whole_units(self):
        units = core.Units()
        self.assertEqual(units.take(0.4), 0)
        self.assertEqual(units.take(0.4), 0)
        self.assertEqual(units.take(0.4), 1)  # 1.2: one, 0.2 kept
        self.assertEqual(units.take(-2.5), -2)  # -2.3
        units.reset()
        self.assertEqual(units.take(0.9), 0)
        self.assertEqual(units.take(130.2), 131)


if __name__ == "__main__":
    unittest.main()
