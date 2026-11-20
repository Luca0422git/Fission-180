# SPDX-License-Identifier: LGPL-2.1-or-later
"""neon_settings: Neon Lights' stored choices (neon-lights-design.md 6.2, 6.10)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.dirname(__file__))
from fission180 import neon_palette, neon_settings  # noqa: E402
from test_smoke_fake_freecad import FakeParams  # noqa: E402


class Settings(unittest.TestCase):
    def setUp(self):
        self.params = FakeParams()
        self._original = neon_settings._params
        neon_settings._params = lambda: self.params

    def tearDown(self):
        neon_settings._params = self._original

    def test_defaults(self):
        for name, value in neon_settings.DEFAULTS.items():
            self.assertEqual(neon_settings.get(name), value, name)
        self.assertEqual(neon_settings.get("Preset"), "v")
        self.assertFalse(neon_settings.get("Sounds"))
        self.assertFalse(neon_settings.get("Hologram"))

    def test_put_keeps_kinds(self):
        neon_settings.put("Glow", 0)
        neon_settings.put("Volume", "35")
        self.assertIs(neon_settings.get("Glow"), False)
        self.assertEqual(neon_settings.get("Volume"), 35)

    def test_custom_round_trip(self):
        neon_settings.set_custom("primary", "#00FF00")
        self.assertEqual(neon_settings.current_roles()["primary"], "#00ff00")
        self.assertEqual(neon_settings.current_roles()["outline"], "#00ff00")
        neon_settings.set_custom("primary", "")
        self.assertEqual(
            neon_settings.current_roles()["primary"], neon_palette.PRESETS["v"]["primary"]
        )
        neon_settings.set_custom("text", "#ffffff")
        neon_settings.clear_custom()
        self.assertEqual(neon_settings.custom(), {})

    def test_invalid_custom_refused(self):
        with self.assertRaises(ValueError):
            neon_settings.set_custom("primary", "#12345")
        with self.assertRaises(ValueError):
            neon_settings.set_custom("nope", "#123456")
        self.assertEqual(neon_settings.custom(), {})

    def test_saved_sets(self):
        neon_settings.put("Preset", "johnny")
        neon_settings.set_custom("secondary", "#123456")
        neon_settings.save_set("Mine")
        neon_settings.put("Preset", "outrun")
        neon_settings.clear_custom()
        self.assertEqual([s["name"] for s in neon_settings.saved_sets()], ["Mine"])
        self.assertTrue(neon_settings.load_set("Mine"))
        self.assertEqual(neon_settings.get("Preset"), "johnny")
        self.assertEqual(neon_settings.custom(), {"secondary": "#123456"})
        neon_settings.delete_set("Mine")
        self.assertEqual(neon_settings.saved_sets(), [])
        self.assertFalse(neon_settings.load_set("Mine"))
        with self.assertRaises(ValueError):
            neon_settings.save_set("  ")


if __name__ == "__main__":
    unittest.main()
