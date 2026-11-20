# SPDX-License-Identifier: LGPL-2.1-or-later
"""neon_prefs_core: the Neon Lights page of Preferences as data (neon-lights-design.md 6.10,
plan task B10): preset titles, typed colours refused with a reason, saved colour sets."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.dirname(__file__))
from fission180 import neon_palette, neon_prefs_core as core, neon_settings  # noqa: E402
from test_smoke_fake_freecad import FakeParams  # noqa: E402


class Page(unittest.TestCase):
    def test_colour_rows_cover_every_role_once(self):
        roles = [r for r, _l, _t in core.COLOUR_ROWS + core.MORE_ROWS]
        self.assertEqual(sorted(roles), sorted(neon_palette.ROLES))
        self.assertEqual([r for r, _l, _t in core.MORE_ROWS], ["alert"])
        self.assertIn("outline", [r for r, _l, _t in core.COLOUR_ROWS])

    def test_every_setting_has_a_part_and_a_default(self):
        for switch, strength, label, tip in core.EFFECTS:
            self.assertIn(switch, neon_settings.DEFAULTS)
            self.assertIn(strength, neon_settings.DEFAULTS)
            self.assertTrue(label and tip)
        for key, part in core.PART_OF.items():
            self.assertIn(key, neon_settings.DEFAULTS, key)
            self.assertTrue(part.startswith("neon_"), part)

    def test_preset_title(self):
        self.assertEqual(core.preset_title("johnny", {}), "Johnny")
        self.assertEqual(core.preset_title("johnny", {"primary": "#123456"}), "Custom (based on Johnny)")
        self.assertEqual(core.preset_title("nothing", {}), "V")


class TypedColours(unittest.TestCase):
    def test_good(self):
        self.assertEqual(core.parse_hex("#FF003C"), ("#ff003c", ""))
        self.assertEqual(core.parse_hex("  00e5ff "), ("#00e5ff", ""))

    def test_refused_with_a_reason(self):
        for text in ("#12345", "#1234567", "red", "#gg0000", "#fff"):
            colour, why = core.parse_hex(text)
            self.assertIsNone(colour, text)
            self.assertIn(text.strip(), why)
            self.assertIn("#ff003c", why)
        colour, why = core.parse_hex("")
        self.assertIsNone(colour)
        self.assertTrue(why)


class Sets(unittest.TestCase):
    SETS = [
        {"name": "Mine", "preset": "johnny", "custom": {"primary": "#123456"}},
        {"name": "Plain", "preset": "v", "custom": {}},
    ]

    def test_matching_set(self):
        self.assertEqual(core.matching_set(self.SETS, "johnny", {"primary": "#123456"}), "Mine")
        self.assertEqual(core.matching_set(self.SETS, "johnny", {"primary": "#123457"}), None)
        self.assertEqual(core.matching_set(self.SETS, "v", {}), "Plain")
        self.assertEqual(core.matching_set([], "v", {}), None)

    def test_renamed(self):
        out = core.renamed(self.SETS, "Mine", " Yours ")
        self.assertEqual([s["name"] for s in out], ["Yours", "Plain"])
        self.assertEqual(out[0]["custom"], {"primary": "#123456"})
        self.assertEqual([s["name"] for s in self.SETS], ["Mine", "Plain"])  # not changed
        for old, new in (("Mine", ""), ("Gone", "X"), ("Mine", "Plain")):
            with self.assertRaises(ValueError):
                core.renamed(self.SETS, old, new)
        self.assertEqual(core.renamed(self.SETS, "Mine", "Mine")[0]["name"], "Mine")

    def test_rename_stored(self):
        params = FakeParams()
        original = neon_settings._params
        neon_settings._params = lambda: params
        try:
            neon_settings.put("Preset", "judy")
            neon_settings.save_set("Mine")
            neon_settings.rename_set("Mine", "Pink")
            self.assertEqual([s["name"] for s in neon_settings.saved_sets()], ["Pink"])
            with self.assertRaises(ValueError):
                neon_settings.rename_set("Mine", "Other")
        finally:
            neon_settings._params = original


class Readable(unittest.TestCase):
    def test_lifted_text(self):
        r = neon_palette.roles("v")
        self.assertFalse(core.lifted(r))
        r["text"] = r["background"]
        self.assertTrue(core.lifted(r))


if __name__ == "__main__":
    unittest.main()
