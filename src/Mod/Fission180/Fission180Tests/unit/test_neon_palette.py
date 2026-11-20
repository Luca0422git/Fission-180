# SPDX-License-Identifier: LGPL-2.1-or-later
"""neon_palette: the Neon Lights colours (docs/fission180/neon-lights-design.md, 6.2): 17
presets, six roles, the shades derived from them, and text that always stays readable."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from fission180 import neon_palette  # noqa: E402
from fission180 import theme  # noqa: E402


class Presets(unittest.TestCase):
    def test_presets_match_design(self):
        self.assertEqual(neon_palette.ORDER[:2], ("johnny", "v"))
        self.assertEqual(len(neon_palette.ORDER), 17)
        self.assertEqual(set(neon_palette.ORDER), set(neon_palette.PRESETS))
        self.assertEqual(neon_palette.PRESETS["johnny"]["primary"], "#fcee0a")
        self.assertEqual(neon_palette.PRESETS["johnny"]["secondary"], "#00c2ff")
        self.assertEqual(neon_palette.PRESETS["v"]["primary"], "#ff003c")
        self.assertEqual(neon_palette.PRESETS["v"]["secondary"], "#00e5ff")
        self.assertEqual(neon_palette.DEFAULT, "v")
        for key in neon_palette.ORDER:
            preset = neon_palette.PRESETS[key]
            self.assertTrue(preset["name"] and preset["after"], key)
            for role in ("primary", "secondary", "alert", "background", "text"):
                self.assertTrue(neon_palette.valid_hex(preset[role]), (key, role))


class Roles(unittest.TestCase):
    def test_roles_fill_outline_and_ignore_bad_custom(self):
        r = neon_palette.roles("v", {"secondary": "nope", "text": "#ffffff"})
        self.assertEqual(set(r), set(neon_palette.ROLES))
        self.assertEqual(r["outline"], r["primary"])
        self.assertEqual(r["secondary"], neon_palette.PRESETS["v"]["secondary"])
        self.assertEqual(r["text"], "#ffffff")
        self.assertEqual(
            neon_palette.roles("unknown")["primary"], neon_palette.PRESETS["v"]["primary"]
        )

    def test_custom_outline_kept(self):
        r = neon_palette.roles("johnny", {"outline": "#00FF00"})
        self.assertEqual(r["outline"], "#00ff00")

    def test_digest_is_stable_and_changes_with_colours(self):
        a = neon_palette.digest(neon_palette.roles("v"))
        self.assertEqual(a, neon_palette.digest(neon_palette.roles("v")))
        self.assertEqual(len(a), 8)
        self.assertNotEqual(a, neon_palette.digest(neon_palette.roles("johnny")))


class Colour(unittest.TestCase):
    def test_helpers(self):
        self.assertTrue(neon_palette.valid_hex("#A0b1c2"))
        self.assertFalse(neon_palette.valid_hex("#12345"))
        self.assertFalse(neon_palette.valid_hex("red"))
        self.assertEqual(neon_palette.mix("#000000", "#ffffff", 0.5), "#808080")
        self.assertEqual(neon_palette.rgba("#ff0000", 0.5), "rgba(255, 0, 0, 0.5)")
        self.assertEqual(neon_palette.rgb01("#ff0000"), (1.0, 0.0, 0.0))
        self.assertAlmostEqual(neon_palette.contrast("#000000", "#ffffff"), 21.0, places=3)

    def test_readable(self):
        fg = neon_palette.readable("#222222", "#111111")
        self.assertGreaterEqual(neon_palette.contrast(fg, "#111111"), 4.5)
        fg = neon_palette.readable("#eeeeee", "#ffffff")
        self.assertGreaterEqual(neon_palette.contrast(fg, "#ffffff"), 4.5)


class Derived(unittest.TestCase):
    def test_derive_has_every_theme_key_and_reads(self):
        for key in neon_palette.ORDER:
            p = neon_palette.derive(neon_palette.roles(key))
            self.assertTrue(set(theme.DARK) <= set(p), key)
            self.assertTrue(set(neon_palette.NEON_KEYS) <= set(p), key)
            for name, value in p.items():
                self.assertTrue(neon_palette.valid_hex(value), (key, name, value))
            for fg, bg in (("text", "chrome"), ("text", "menu"), ("text", "field"), ("text", "view")):
                self.assertGreaterEqual(neon_palette.contrast(p[fg], p[bg]), 4.5, (key, fg, bg))
            self.assertGreaterEqual(neon_palette.contrast(p["text_dim"], p["chrome"]), 3.0, key)

    def test_extreme_custom_colours_stay_readable(self):
        r = neon_palette.roles(
            "v", {"background": "#ffffff", "text": "#ffffff", "primary": "#ffffff"}
        )
        p = neon_palette.derive(r)
        for ground in ("chrome", "menu", "field", "view"):
            self.assertGreaterEqual(neon_palette.contrast(p["text"], p[ground]), 4.5, ground)

    def test_neon_values_never_collide_with_dark_or_light(self):
        taken = set(theme.DARK.values()) | set(theme.LIGHT.values())
        taken |= set(theme._EXTRA) | set(theme._EXTRA.values())
        taken -= {"#ffffff", "#000000"}
        for key in neon_palette.ORDER:
            p = neon_palette.derive(neon_palette.roles(key))
            mine = [p[k] for k in theme.DARK]
            self.assertFalse(set(mine) & taken, key)
            self.assertEqual(len(mine), len(set(mine)), key)  # one value per key


if __name__ == "__main__":
    unittest.main()
