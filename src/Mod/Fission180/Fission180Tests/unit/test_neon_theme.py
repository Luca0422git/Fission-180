# SPDX-License-Identifier: LGPL-2.1-or-later
"""theme.py's third look, Neon Lights (neon-lights-design.md 6.1, plan task A4): switching,
the helpers that keep Dark and Light exact, translations that come back, and the parts that
are switched off when they fail. Runs with a fake FreeCAD (no window)."""

import os
import sys
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.dirname(__file__))
from test_smoke_fake_freecad import FakeParams  # noqa: E402


class _Console:
    def PrintMessage(self, text):
        pass

    def PrintWarning(self, text):
        pass

    def PrintError(self, text):
        pass

    def PrintLog(self, text):
        pass


class NeonLook(unittest.TestCase):
    def setUp(self):
        self.groups = {}
        fake = types.ModuleType("FreeCAD")
        fake.ParamGet = lambda path: self.groups.setdefault(path, FakeParams())
        fake.Console = _Console()
        self._saved = sys.modules.get("FreeCAD")
        sys.modules["FreeCAD"] = fake
        from fission180 import neon, theme

        self.theme, self.neon = theme, neon
        self._listeners = theme.LISTENERS
        theme.LISTENERS = ()  # no window here
        theme._use("dark")

    def tearDown(self):
        self.theme.set_theme("dark")
        self.theme.LISTENERS = self._listeners
        self.neon._state["failed"] = {}
        if self._saved is None:
            sys.modules.pop("FreeCAD", None)
        else:
            sys.modules["FreeCAD"] = self._saved

    def test_neon_is_a_look(self):
        self.assertEqual(self.theme.set_theme("neon"), "neon")
        self.assertEqual(self.theme.name(), "neon")
        self.assertTrue(self.theme.is_neon())
        self.assertFalse(self.theme.is_light())
        self.assertNotEqual(self.theme.CHROME, self.theme.DARK["chrome"])
        self.assertTrue(self.neon.active())
        self.theme.set_theme("dark")
        self.assertFalse(self.neon.active())
        self.assertEqual(self.theme.CHROME, self.theme.DARK["chrome"])

    def test_neon_helpers_leave_dark_and_light_alone(self):
        for look in ("dark", "light"):
            self.theme.set_theme(look)
            self.assertEqual(self.theme.neon("primary", "#e8e8e8"), "#e8e8e8")
            self.assertEqual(self.theme.neon3d((0.1, 0.2, 0.3), "arrow"), (0.1, 0.2, 0.3))
        self.theme.set_theme("neon")
        self.assertEqual(self.theme.neon("marker", "#e8e8e8"), self.theme.palette()["marker"])
        self.assertNotEqual(self.theme.neon3d((0.1, 0.2, 0.3), "arrow"), (0.1, 0.2, 0.3))

    def test_translate_round_trip(self):
        from fission180 import neon_settings

        original = (
            "#Panel { background: #3b4453; color: #f5f5f5; border: 1px solid #56606f; }"
            " QLabel { color: #ff8a80; } QLabel[role='link'] { color: #8cc4ff; }"
            " QFrame { background: #343a46; } QToolButton { color: #ffffff; }"
        )
        self.theme.set_theme("neon")
        in_v = self.theme.translate(original)
        self.assertNotEqual(in_v, original)
        self.assertNotIn("#3b4453", in_v)
        self.assertIn("#ffffff", in_v)  # white is never swapped
        self.groups[neon_settings.PARAMS].SetString("Preset", "johnny")
        self.theme.refresh_neon()
        in_johnny = self.theme.translate(in_v)  # a panel styled under V, now Johnny
        self.assertEqual(in_johnny, self.theme.translate(original))
        self.theme.set_theme("dark")
        self.assertEqual(self.theme.translate(in_johnny), original)
        self.theme.set_theme("light")
        self.assertEqual(self.theme.translate(in_johnny), self.theme.translate(original))

    def test_failed_part_is_switched_off(self):
        from fission180 import neon_boot

        calls = []
        original_enable, original_disable = neon_boot.enable, neon_boot.disable

        def broken():
            raise RuntimeError("boom")

        neon_boot.enable = broken
        neon_boot.disable = lambda: calls.append("disable")
        try:
            self.theme.set_theme("neon")
            self.assertIn("neon_boot", self.neon.failed())
            self.assertIn("disable", calls)
            self.assertTrue(self.neon.active())
        finally:
            neon_boot.enable, neon_boot.disable = original_enable, original_disable


if __name__ == "__main__":
    unittest.main()
