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


class BootOnlyAtStart(unittest.TestCase):
    """The boot screen is for Fission 180 starting in Neon Lights, not for a switch to it
    during the run (theme.set_theme marks that)."""

    def setUp(self):
        from fission180 import theme

        self.theme = theme
        self.saved = (dict(theme._state), dict(neon_boot._state), os.environ.get("FISSION180_SCENARIO_FILE"))
        os.environ["FISSION180_SCENARIO_FILE"] = "unit"  # enable() never starts it here

    def tearDown(self):
        self.theme._state.clear()
        self.theme._state.update(self.saved[0])
        neon_boot._state.clear()
        neon_boot._state.update(self.saved[1])
        if self.saved[2] is None:
            os.environ.pop("FISSION180_SCENARIO_FILE", None)
        else:
            os.environ["FISSION180_SCENARIO_FILE"] = self.saved[2]

    def test_switched_in_during_the_run_means_no_boot_screen(self):
        self.theme._state.pop("switched", None)
        neon_boot._state["shown"] = False
        self.assertFalse(neon_boot._switched_in())
        neon_boot.enable()
        self.assertFalse(neon_boot._state["shown"], "started in Neon Lights: still to come")
        self.theme._state["switched"] = True
        self.assertTrue(neon_boot._switched_in())
        neon_boot.enable()
        self.assertTrue(neon_boot._state["shown"], "switched to it: never this run")
        neon_boot.disable()

    def test_set_theme_marks_the_switch(self):
        import inspect

        source = inspect.getsource(self.theme.set_theme)
        self.assertIn('_state["switched"] = True', source)
        self.assertNotIn("switched", inspect.getsource(self.theme.apply), "the start is not a switch")


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
        self.assertLessEqual(neon_home.FPS, 12, "about 2% of a core at most (design 6.13)")

    def test_frame_cap_holds_whatever_the_timer_does(self):
        # a timer that fires every millisecond for 10 s (or early, or twice in a row)
        for step in (1, 7, 40, 83):
            last, frames = None, 0
            for now in range(0, 10000, step):
                if neon_home.due(last, now):
                    last, frames = now, frames + 1
            self.assertLessEqual(frames / 10.0, neon_home.FPS + 1, step)
        self.assertTrue(neon_home.due(None, 0))
        self.assertTrue(neon_home.due(0, 1000.0 / neon_home.FPS), "a timer on time is never skipped")

    def test_drop_bands_cover_each_character_once(self):
        for length in range(1, 20):
            seen = []
            for k0, k1, alpha in neon_home._bands(length):
                self.assertTrue(0 < alpha <= 255)
                seen.extend(range(k0, k1 + 1))
            self.assertEqual(seen, list(range(length)))

    def test_follow_all_never_raises(self):
        class Broken:
            def follow(self):
                raise ValueError("a broken backdrop")

        saved = dict(neon_home._state)
        try:
            neon_home._state["backdrops"] = {1: Broken()}
            neon_home._state["pages"] = []
            neon_home.follow_all()  # logs a [Fission 180] warning, never raises
            neon_home._state["pages"] = None  # even its own bookkeeping going wrong
            neon_home.follow_all()
        finally:
            neon_home._state.clear()
            neon_home._state.update(saved)


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

    def test_qt_failing_falls_back_to_the_next_way(self):
        """A way that fails while playing (Qt Multimedia's module missing a piece, a player
        gone) gives the sound to the next way, and is skipped from then on."""
        import types

        class Effect:
            def __init__(self):
                raise RuntimeError("no Qt Multimedia backend")

        broken = types.ModuleType("fakeqt.QtMultimedia")
        broken.QSoundEffect = Effect

        def qt_probe():
            neon_sound._state["qt"] = broken
            return ("qt", "")

        true = "/bin/true" if os.path.exists("/bin/true") else sys.executable
        neon_sound.BACKENDS = (qt_probe, lambda: None, lambda: ("cmd", true))
        self.assertEqual(neon_sound.play("click", force=True), "cmd", "the click still plays")
        self.assertEqual(neon_sound.backend(), ("cmd", true))
        self.assertIn(("qt", ""), neon_sound._state["failed"])
        neon_sound._state["last"] = {}
        self.assertEqual(neon_sound.play("menu", force=True), "cmd", "and every sound after")
        self.assertEqual([k for _n, k in neon_sound.played()][-2:], ["cmd", "cmd"])
        for proc in neon_sound._state["procs"]:
            proc.wait()

    def test_qt_plays_with_the_module_the_probe_found(self):
        import types

        made = []

        class Url:
            @staticmethod
            def fromLocalFile(path):  # noqa: N802
                return path

        class Effect:
            def __init__(self):
                made.append(self)
                self.played = 0

            def setSource(self, url):  # noqa: N802
                self.url = url

            def setVolume(self, v):  # noqa: N802
                self.volume = v

            def play(self):
                self.played += 1

        package = types.ModuleType("fakeqt")
        core = types.ModuleType("fakeqt.QtCore")
        core.QUrl = Url
        media = types.ModuleType("fakeqt.QtMultimedia")
        media.QSoundEffect = Effect
        sys.modules.update({"fakeqt": package, "fakeqt.QtCore": core, "fakeqt.QtMultimedia": media})
        try:
            def qt_probe():
                neon_sound._state["qt"] = media
                return ("qt", "")

            neon_sound.BACKENDS = (qt_probe,)
            neon_sound.prepare()  # when Sounds comes on: the effects made then, not on a click
            self.assertEqual(len(made), len(neon_sound.NAMES))
            self.assertEqual(neon_sound.play("done", force=True), "qt")
            self.assertEqual(len(made), len(neon_sound.NAMES), "no new effect on a click")
            self.assertEqual(sum(e.played for e in made), 1)
        finally:
            for name in ("fakeqt", "fakeqt.QtCore", "fakeqt.QtMultimedia"):
                sys.modules.pop(name, None)

    def test_sounds_on_chooses_the_way_before_the_first_click(self):
        calls = []
        neon_sound.BACKENDS = (lambda: calls.append(1),)
        neon_sound._prepare_soon()  # outside Qt: at once (in FreeCAD: on the event loop)
        self.assertEqual(calls, [1])
        neon_sound._prepare_soon()
        self.assertEqual(calls, [1], "chosen once")

    @unittest.skipUnless(sys.platform.startswith("linux"), "processes")
    def test_finished_players_are_reaped(self):
        import subprocess

        proc = subprocess.Popen(["/bin/sh", "-c", "exit 0"])
        neon_sound._state["procs"] = [proc]
        proc.wait()  # stands for the time passing
        neon_sound._reap_tick()  # what the timer runs
        self.assertEqual(neon_sound._state["procs"], [])

    def test_scaled_copy_is_private(self):
        target = neon_sound._scaled("click", 37)
        folder = os.path.dirname(target)
        self.assertFalse(folder.startswith(os.path.join(tempfile.gettempdir(), "fission180-sounds", "")),
                         "not the shared temporary folder")
        if os.name == "posix":
            self.assertEqual(os.stat(folder).st_mode & 0o077, 0, "only the person can write there")
        self.assertEqual([f for f in os.listdir(folder) if f.endswith(".part")], [])

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
