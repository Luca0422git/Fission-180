# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights' extras (neon-lights-design.md 6.8, 6.9): the boot screen's timeline, the UI
sounds never raising or blocking whatever the computer has, the Home floor's perspective."""

import os
import sys
import tempfile
import unittest
import wave

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from fission180 import neon_boot, neon_home, neon_sound  # noqa: E402


class Boot(unittest.TestCase):
    def test_text_types_out_in_order_and_completely(self):
        self.assertEqual(neon_boot.typed(0), [])
        middle = neon_boot.typed((neon_boot.TEXT[0] + neon_boot.TEXT[1]) / 2)
        self.assertTrue(0 < len(middle) <= len(neon_boot.LINES))
        for shown, full in zip(middle, neon_boot.LINES):
            self.assertTrue(full.startswith(shown))
        self.assertEqual(neon_boot.typed(neon_boot.TEXT[1]), list(neon_boot.LINES))

    def test_bar_fills_and_screen_fades_within_about_two_and_a_half_seconds(self):
        self.assertEqual(neon_boot.segments(0), 0)
        lit = [neon_boot.segments(t) for t in range(0, neon_boot.DURATION + 1, 50)]
        self.assertEqual(lit, sorted(lit), "the bar never goes back")
        self.assertEqual(neon_boot.segments(neon_boot.BAR[1]), neon_boot.SEGMENTS)
        self.assertEqual(neon_boot.opacity(0), 1.0)
        self.assertEqual(neon_boot.opacity(neon_boot.DURATION), 0.0)
        self.assertTrue(2000 <= neon_boot.DURATION <= 3000)

    def test_wording_is_uppercase_and_fits_one_line(self):
        widths = {len(line) for line in neon_boot.LINES}
        self.assertEqual(len(widths), 1, "the dots line up")
        for line in neon_boot.LINES:
            self.assertEqual(line, line.upper())


class Home(unittest.TestCase):
    def test_rows_are_in_perspective_and_move_toward_the_viewer(self):
        a = neon_home.rows(0.0)
        b = neon_home.rows(0.25)
        self.assertTrue(all(0 < d <= 1 for d in a + b))
        gaps = [y - x for x, y in zip(a, a[1:])]
        self.assertEqual(gaps, sorted(gaps), "wider apart toward the viewer")
        self.assertGreater(b[-2], a[-2], "rows come closer as time goes on")
        self.assertEqual(neon_home.rows(1.0), neon_home.rows(0.0), "it loops seamlessly")

    def test_frame_rate_is_capped(self):
        self.assertLessEqual(neon_home.FPS, 30)


class Sound(unittest.TestCase):
    def setUp(self):
        self.saved = (neon_sound.BACKENDS, dict(neon_sound._state))
        neon_sound.reset()
        neon_sound._state["last"] = {}
        neon_sound._state["volume_override"] = None
        self._volume = neon_sound.volume
        neon_sound.volume = lambda: 60

    def tearDown(self):
        neon_sound.BACKENDS = self.saved[0]
        neon_sound._state.clear()
        neon_sound._state.update(self.saved[1])
        neon_sound.volume = self._volume
        neon_sound.reset()

    def test_every_sound_file_is_there(self):
        for name in neon_sound.NAMES:
            self.assertTrue(os.path.exists(neon_sound.path(name)), name)

    def test_every_backend_missing_is_silent(self):
        neon_sound.BACKENDS = (lambda: None, lambda: None, lambda: None)
        for name in neon_sound.NAMES:
            self.assertIsNone(neon_sound.play(name, force=True))
        self.assertEqual(neon_sound.backend(), ("none", ""))

    def test_a_backend_that_raises_never_escapes(self):
        def boom():
            raise OSError("no sound card")

        neon_sound.BACKENDS = (boom, lambda: ("cmd", "/nonexistent/player"))
        self.assertIsNone(neon_sound.play("click", force=True))  # Popen fails: caught
        self.assertEqual(neon_sound.backend(), ("none", ""), "and it stays silent after")

    def test_off_means_no_probing(self):
        calls = []
        neon_sound.BACKENDS = (lambda: calls.append(1),)
        self.assertIsNone(neon_sound.play("click"))
        self.assertEqual(calls, [], "sounds off (the default): nothing is even looked for")

    def test_quiet_and_unknown_names(self):
        neon_sound.BACKENDS = (lambda: ("cmd", sys.executable),)
        with neon_sound.quiet():
            self.assertIsNone(neon_sound.play("done", force=True))
        self.assertIsNone(neon_sound.play("nope", force=True))

    @unittest.skipUnless(sys.platform.startswith("linux"), "a shell-script player")
    def test_player_started_without_waiting(self):
        # a "player" that would take 5 s: play() returns at once
        import time

        script = os.path.join(tempfile.mkdtemp(), "aplay")
        with open(script, "w") as f:
            f.write("#!/bin/sh\nsleep 5\n")
        os.chmod(script, 0o755)
        neon_sound.BACKENDS = (lambda: ("cmd", script),)
        start = time.monotonic()
        self.assertEqual(neon_sound.play("menu", force=True), "cmd")
        self.assertLess(time.monotonic() - start, 1.0)
        self.assertIsNone(neon_sound.play("menu", force=True), "the same sound at once: skipped")
        for proc in neon_sound._state["procs"]:
            proc.kill()
            proc.wait()

    def test_scaled_copy_is_quieter(self):
        target = neon_sound._scaled("click", 25)
        with wave.open(target, "rb") as w, wave.open(neon_sound.path("click"), "rb") as o:
            import array

            quiet = array.array("h", w.readframes(w.getnframes()))
            loud = array.array("h", o.readframes(o.getnframes()))
        self.assertEqual(len(quiet), len(loud))
        self.assertLess(max(map(abs, quiet)), max(map(abs, loud)) * 0.3)


if __name__ == "__main__":
    unittest.main()
