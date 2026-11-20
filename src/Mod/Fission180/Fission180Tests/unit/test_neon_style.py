# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights' frames and style sheet (neon-lights-design.md 6.3, plan task A5)."""

import os
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from fission180 import (  # noqa: E402
    neon_frames,
    neon_palette,
    neon_qss_chrome,
    neon_qss_panels,
    neon_qss_shell,
    theme,
)


def _palette(key="v"):
    return neon_palette.derive(neon_palette.roles(key))


def _selectors(qss):
    """Every selector of a style sheet, whitespace squeezed."""
    text = re.sub(r"/\*.*?\*/", "", qss, flags=re.S)
    out = set()
    for rule in text.split("}"):
        if "{" not in rule:
            continue
        head = rule.split("{")[0]
        for sel in head.split(","):
            sel = " ".join(sel.split())
            if sel:
                out.add(sel)
    return out


def _neon_qss(p, translucent=True):
    with tempfile.TemporaryDirectory() as folder:
        frames = neon_frames.write(p, folder)
        return "\n".join(
            part.qss(p, frames, ("Chakra Petch", "Orbitron"), translucent)
            for part in (neon_qss_chrome, neon_qss_shell, neon_qss_panels)
        )


class Frames(unittest.TestCase):
    def test_every_piece_renders(self):
        p = _palette()
        for piece in neon_frames.PIECES:
            text = neon_frames.svg(piece, p)
            root = ET.fromstring(text)
            self.assertTrue(root.tag.endswith("svg"), piece)
            colours = set(re.findall(r"#[0-9a-f]{6}", text))
            self.assertTrue(colours & {p[k] for k in ("primary", "primary_hot", "primary_dim", "secondary", "alert", "line", "check_line")}, piece)

    def test_no_svg_filters(self):
        p = _palette()
        for piece in neon_frames.PIECES:
            text = neon_frames.svg(piece, p)
            self.assertNotIn("<filter", text, piece)
            self.assertNotIn("feGaussianBlur", text, piece)

    def test_slices_fit(self):
        for piece, (w, h, s, b) in neon_frames.SIZES.items():
            self.assertLessEqual(2 * s, min(w, h), piece)
            self.assertLessEqual(b, s, piece)

    def test_write_once_per_folder(self):
        with tempfile.TemporaryDirectory() as folder:
            paths = neon_frames.write(_palette(), folder)
            self.assertEqual(set(paths), set(neon_frames.PIECES))
            for path in paths.values():
                self.assertTrue(os.path.isfile(path))


class StyleSheet(unittest.TestCase):
    def test_qss_covers_every_dark_selector(self):
        dark = _selectors(theme._QSS.format(**theme.DARK))
        neon = _selectors(_neon_qss(_palette()))
        self.assertEqual(sorted(dark - neon), [])

    def test_each_dark_selector_in_exactly_one_part(self):
        p = _palette()
        with tempfile.TemporaryDirectory() as folder:
            frames = neon_frames.write(p, folder)
            parts = [
                _selectors(part.qss(p, frames, ("", ""), True))
                for part in (neon_qss_chrome, neon_qss_shell, neon_qss_panels)
            ]
        for sel in _selectors(theme._QSS.format(**theme.DARK)):
            owners = [i for i, part in enumerate(parts) if sel in part]
            self.assertEqual(len(owners), 1, (sel, owners))

    def test_qss_has_no_dark_colours(self):
        for key in ("v", "johnny", "red_pill"):
            qss = _neon_qss(_palette(key)).lower()
            for name, value in theme.DARK.items():
                if value not in ("#ffffff", "#000000"):
                    self.assertNotIn(value, qss, (key, name))

    def test_colour_properties_hold_colours(self):
        """A frame rule landing where a colour belongs made Qt drop the rest of the style
        sheet (the ribbon came out white, 2026-11-20)."""
        qss = _neon_qss(_palette())
        values = re.findall(
            r"(?:^|[;{\s])(?:background|color|background-color|selection-[a-z-]+|"
            r"alternate-background-color)\s*:\s*([^;]+);",
            re.sub(r"/\*.*?\*/", "", qss, flags=re.S),
        )
        colour = re.compile(r"^(#[0-9a-f]{6}|transparent|rgba\([0-9, .]+\))$")
        bad = [v for v in values if not colour.match(v.strip())]
        self.assertEqual(bad, [])
        self.assertEqual(qss.count("{"), qss.count("}"))

    def test_solid_popups_without_a_compositor(self):
        p = _palette()
        see_through = _neon_qss(p, translucent=True)
        solid = _neon_qss(p, translucent=False)
        self.assertIn("QMenu {{ background: transparent;".replace("{{", "{"), see_through)
        self.assertIn("QMenu { background: %s;" % p["menu"], solid)


if __name__ == "__main__":
    unittest.main()
