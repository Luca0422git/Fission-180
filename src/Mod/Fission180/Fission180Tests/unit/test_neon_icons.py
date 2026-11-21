# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights icons (neon-lights-design.md 6.5, plan task A6): one neon drawing per icon, only
colour tokens in it, and a recoloured copy with no token left."""

import os
import re
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from fission180 import neon_icons, neon_palette  # noqa: E402

HEX = re.compile(r"#[0-9a-fA-F]{6}\b")


class NeonIcons(unittest.TestCase):
    def test_every_ui_icon_has_a_neon_twin(self):
        ui = {n for n in os.listdir(neon_icons.UI) if n.endswith(".svg")}
        neon = {n for n in os.listdir(neon_icons.NEON) if n.endswith(".svg")}
        self.assertEqual(sorted(ui - neon), [], "run tools/fission180/make_icons.py")
        self.assertEqual(sorted(neon - ui), [])

    def test_tokens_only(self):
        for name in sorted(os.listdir(neon_icons.NEON)):
            with open(os.path.join(neon_icons.NEON, name), encoding="utf-8") as handle:
                text = handle.read()
            self.assertEqual(HEX.findall(text), [], name)
            self.assertTrue(set(re.findall(r"#n3000\d", text)) <= set(neon_icons.TOKENS), name)

    def test_recolour_leaves_no_token(self):
        p = neon_palette.derive(neon_palette.roles("johnny"))
        with open(os.path.join(neon_icons.NEON, "extrude.svg"), encoding="utf-8") as handle:
            text = neon_icons.recolour(handle.read(), p)
        self.assertNotIn("#n3000", text)
        self.assertIn(p["primary"], text)


if __name__ == "__main__":
    unittest.main()
