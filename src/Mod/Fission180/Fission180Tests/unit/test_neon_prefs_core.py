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

    def test_white_text_is_not_called_faint(self):
        """derive() nudges colours to keep them unique (#ffffff comes back #fbfafa): no note."""
        for key in neon_palette.ORDER:
            r = neon_palette.roles(key, {"text": "#ffffff"})
            self.assertFalse(core.lifted(r), key)
            r = neon_palette.roles(key, {"text": "#FFFFFF"})
            self.assertFalse(core.lifted(r), key)

    def test_faint_text_is_called_faint(self):
        r = neon_palette.roles("v", {"text": "#333333", "background": "#000000"})
        self.assertTrue(core.lifted(r))


class Inks(unittest.TestCase):
    """Review Focus: the page's coloured words stay readable whatever colours are chosen."""

    EXTREMES = (
        {"alert": "#1a0a10"},
        {"secondary": "#000000"},
        {"primary": "#000000", "secondary": "#000000", "alert": "#000000"},
        {"background": "#ffffff", "primary": "#ffffff", "secondary": "#ffffff", "alert": "#ffffff", "text": "#ffffff"},
        {"background": "#ffff00", "secondary": "#ffff00", "alert": "#ffff00"},
    )

    def test_every_ink_readable_on_its_ground(self):
        for preset in neon_palette.ORDER:
            for custom in ({},) + self.EXTREMES:
                p = neon_palette.derive(neon_palette.roles(preset, custom))
                inks = core.inks(p)
                self.assertEqual(sorted(inks), sorted(k for k, _c, _g in core.INKS))
                for key, _colour, ground in core.INKS:
                    self.assertGreaterEqual(
                        neon_palette.contrast(inks[key], p[ground]), 4.5, (preset, custom, key, inks[key])
                    )

    def test_readable_colours_are_kept(self):
        p = neon_palette.derive(neon_palette.roles("v"))
        inks = core.inks(p)
        if neon_palette.contrast(p["secondary"], p["chrome"]) >= 4.5:
            self.assertEqual(inks["secondary_ink"], p["secondary"])


if __name__ == "__main__":
    unittest.main()
