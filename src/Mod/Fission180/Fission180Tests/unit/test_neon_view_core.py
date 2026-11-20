# SPDX-License-Identifier: LGPL-2.1-or-later
"""neon_view_core: the body outlines' glow, Hologram's colours and when the rim light is used
(docs/fission180/neon-lights-design.md 6.6, plan task B6)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from fission180 import neon_palette  # noqa: E402
from fission180 import neon_view_core as core  # noqa: E402


class Names(unittest.TestCase):
    def test_every_node_name_is_a_neon_name(self):
        for name in core.EDGE_NAMES + core.FLAT_NAMES:
            self.assertTrue(core.is_neon(name), name)
        for name in ("Edge", "FlatRoot", "LineMaterial", "", None, "Fission180Grid"):
            self.assertFalse(core.is_neon(name), name)

    def test_rim_node_is_the_shaders(self):
        from fission180 import neon_shader

        self.assertEqual(core.RIM_NODE, neon_shader.NODE)


class Glow(unittest.TestCase):
    def test_wider_than_the_edge(self):
        width, _t = core.glow_style(2, 70)
        self.assertEqual(width, 10.0)
        self.assertEqual(core.glow_style(1, 70)[0], core.GLOW_MIN_WIDTH)
        self.assertEqual(core.glow_style("bad", 70)[0], 10.0)

    def test_translucent_never_opaque(self):
        for strength in (-5, 0, 35, 70, 100, 400):
            _w, transparency = core.glow_style(2, strength)
            self.assertGreaterEqual(transparency, 0.4, strength)
            self.assertLessEqual(transparency, 1.0, strength)
        self.assertLess(core.glow_style(2, 100)[1], core.glow_style(2, 20)[1])

    def test_when_drawn(self):
        self.assertTrue(core.glow_wanted(True, True, False))
        self.assertFalse(core.glow_wanted(False, True, False))  # the effects' master switch
        self.assertFalse(core.glow_wanted(True, False, False))
        self.assertTrue(core.glow_wanted(False, False, True))  # Hologram edges always glow


class Colours(unittest.TestCase):
    def setUp(self):
        self.palette = neon_palette.derive(neon_palette.roles("v"))

    def test_outline_and_hologram_edges(self):
        normal = core.colours(self.palette)
        self.assertEqual(normal["edge"], self.palette["outline"])
        self.assertEqual(normal["glow"], self.palette["outline"])
        holo = core.colours(self.palette, hologram=True)
        self.assertNotEqual(holo["edge"], self.palette["outline"])  # brighter

    def test_glass_is_dark_and_tinted(self):
        c = core.colours(self.palette, hologram=True)
        glass = neon_palette.rgb01(c["glass"])
        outline = neon_palette.rgb01(self.palette["outline"])
        self.assertLess(sum(glass), sum(outline) / 2.0)
        self.assertNotEqual(c["glass"], self.palette["background"])
        for key in c:
            self.assertTrue(neon_palette.valid_hex(c[key]), key)

    def test_every_preset(self):
        for key in neon_palette.ORDER:
            palette = neon_palette.derive(neon_palette.roles(key))
            for hologram in (False, True):
                c = core.colours(palette, hologram)
                self.assertEqual(set(c), {"edge", "glow", "glass", "glass_glow", "rim"})


class RimLight(unittest.TestCase):
    def test_only_after_self_test_and_on_hologram(self):
        self.assertTrue(core.rim_wanted("auto", True, True))
        self.assertTrue(core.rim_wanted("on", True, True))
        self.assertFalse(core.rim_wanted("auto", True, False))  # flat glass fallback
        self.assertFalse(core.rim_wanted("on", True, False))
        self.assertFalse(core.rim_wanted("off", True, True))
        self.assertFalse(core.rim_wanted("auto", False, True))


if __name__ == "__main__":
    unittest.main()
