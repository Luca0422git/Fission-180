# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights on Fission 180's own bars, the parts that are plain logic (plan task B2 and its
fix round): the document tabs' close buttons and the workspace button's style values. What
needs the window (labels fitting their button, the ViewCube's speed, the Hologram tick, the
browser's tint) is checked by the GUI scenario neon_shell."""

import os
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from fission180 import neon_frames, neon_palette, neon_qss_shell  # noqa: E402


def _palette(key="v"):
    return neon_palette.derive(neon_palette.roles(key))


class CloseButton(unittest.TestCase):
    def test_pictures_are_tiny_svg_in_palette_colours(self):
        for key in ("v", "johnny"):
            p = _palette(key)
            for hover in (False, True):
                text = neon_qss_shell.close_svg(p, hover)
                root = ET.fromstring(text)
                self.assertTrue(root.tag.endswith("svg"))
                self.assertNotIn("<filter", text)
                colours = set(re.findall(r"#[0-9a-f]{6}", text))
                self.assertTrue(colours <= set(p.values()), (key, hover, colours))
            self.assertIn(p["alert"], neon_qss_shell.close_svg(p, True))
            self.assertNotIn(p["alert"], neon_qss_shell.close_svg(p, False))

    def test_rules_only_for_fission180_document_tabs(self):
        p = _palette()
        with tempfile.TemporaryDirectory() as folder:
            frames = neon_frames.write(p, folder)
            qss = neon_qss_shell.qss(p, frames, ("", "Orbitron"), True)
            rules = [line for line in qss.splitlines() if "close-button" in line]
            self.assertEqual(len(rules), 2, rules)
            for rule in rules:
                self.assertTrue(rule.startswith("#Fission180DocumentTabs::close-button"), rule)
                path = re.search(r"url\(([^)]+)\)", rule).group(1)
                self.assertTrue(os.path.isfile(path), path)
        # (no frames, no pictures: no rule)
        self.assertNotIn("close-button", neon_qss_shell.qss(p, {}, ("", ""), True))


class WorkspaceButton(unittest.TestCase):
    def test_style_uses_the_fitting_size(self):
        p = _palette()
        qss = neon_qss_shell.qss(p, {}, ("", "Orbitron"), True)
        rule = qss[qss.index('QToolButton[role="workspace"] {'):]
        rule = rule[: rule.index("}")]
        self.assertIn("font-size: %dpx;" % neon_qss_shell.WORKSPACE_FONT_PX, rule)
        self.assertIn("letter-spacing: %dpx;" % neon_qss_shell.WORKSPACE_SPACING, rule)
        self.assertIn("padding: 0px %dpx;" % neon_qss_shell.WORKSPACE_PAD, rule)
        self.assertLessEqual(neon_qss_shell.WORKSPACE_FONT_PX, 10)
        self.assertLessEqual(neon_qss_shell.WORKSPACE_SPACING, 1)


if __name__ == "__main__":
    unittest.main()
