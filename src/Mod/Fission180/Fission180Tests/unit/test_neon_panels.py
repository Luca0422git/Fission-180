# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights on the command dialogs and Fission 180's panels (neon-lights-design.md 6.3,
plan task B3): the pieces neon_qss_panels draws, the rules each panel gets, and style()
leaving Dark and Light exactly as before."""

import os
import re
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from fission180 import neon_frames, neon_palette, neon_qss_panels, theme  # noqa: E402


def _palette(key="v"):
    return neon_palette.derive(neon_palette.roles(key))


class _Widget:
    """Enough of a QWidget for style()."""

    def __init__(self, name=""):
        self.sheet = None
        self.props = {}
        self.name = name

    def setStyleSheet(self, text):
        self.sheet = text

    def setProperty(self, key, value):
        self.props[key] = value

    def property(self, key):
        return self.props.get(key)

    def objectName(self):
        return self.name


def _values(block):
    return re.findall(
        r"(?:^|[;{\s])(?:background|color|background-color|selection-[a-z-]+|"
        r"alternate-background-color|border-color)\s*:\s*([^;]+);",
        re.sub(r"/\*.*?\*/", "", block, flags=re.S),
    )


COLOUR = re.compile(r"^(#[0-9a-f]{6}|transparent|rgba\([0-9, .]+\))$")


class Pieces(unittest.TestCase):
    def test_every_piece_renders_in_the_palette(self):
        for key in ("v", "johnny"):
            p = _palette(key)
            for piece in neon_qss_panels.PIECES:
                text = neon_qss_panels.svg(piece, p)
                self.assertTrue(ET.fromstring(text).tag.endswith("svg"), piece)
                own = {p[k] for k in ("primary", "primary_dim", "primary_hot")}
                self.assertTrue(own & set(re.findall(r"#[0-9a-f]{6}", text)), (key, piece))

    def test_no_svg_filters(self):
        for piece in neon_qss_panels.PIECES:
            text = neon_qss_panels.svg(piece, _palette())
            self.assertNotIn("<filter", text, piece)
            self.assertNotIn("feGaussianBlur", text, piece)

    def test_slices_fit(self):
        for piece, (w, h, s, b) in neon_qss_panels.SIZES.items():
            self.assertLessEqual(2 * s, min(w, h), piece)
            self.assertLessEqual(b, s, piece)

    def test_no_name_shared_with_the_palette(self):
        """A frame rule named like a palette key once landed in a background: and Qt dropped
        every rule after it (neon-common.md)."""
        p = _palette()
        for piece in neon_qss_panels.PIECES:
            self.assertNotIn(piece, p, piece)

    def test_text_on_primary_is_readable(self):
        for key in neon_palette.ORDER:
            p = _palette(key)
            self.assertGreaterEqual(
                neon_palette.contrast(neon_qss_panels.ink(p), p["primary"]), 4.5, key
            )
        own = neon_palette.derive(neon_palette.roles("v", {"primary": "#202040"}))
        self.assertGreaterEqual(neon_palette.contrast(neon_qss_panels.ink(own), own["primary"]), 4.5)


class Rules(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.p = _palette()
        frames = neon_frames.write(self.p, self.folder.name)
        mine = neon_qss_panels.write(self.p, os.path.join(self.folder.name, "panels"))
        self.v = neon_qss_panels.values(self.p, frames, ("Chakra Petch", "Orbitron"), mine)

    def tearDown(self):
        self.folder.cleanup()

    def _all(self):
        out = {}
        for part, make in neon_qss_panels.BLOCKS.items():
            out[part] = make(self.v, _Widget("Fission180HomeWelcome"))
        frames = neon_frames.write(self.p, self.folder.name)
        out["app"] = neon_qss_panels.qss(self.p, frames, ("Chakra Petch", "Orbitron"), True)
        return out

    def test_colour_properties_hold_colours(self):
        for part, text in self._all().items():
            bad = [v for v in _values(text) if not COLOUR.match(v.strip())]
            self.assertEqual(bad, [], part)
            self.assertEqual(text.count("{"), text.count("}"), part)

    def test_no_dark_colour_in_the_rules(self):
        for part, text in self._all().items():
            for name, value in theme.DARK.items():
                if value not in ("#ffffff", "#000000"):
                    self.assertNotIn(value, text.lower(), (part, name))

    def test_titles_in_caps_and_the_display_face(self):
        app = self._all()["app"]
        self.assertIn("text-transform: uppercase", app)
        self.assertIn('font-family: "Orbitron"', app)
        self.assertIn('QPushButton[text="OK"]', app)

    def test_every_panel_part_has_rules(self):
        for part, text in self._all().items():
            self.assertTrue(text.strip(), part)


class Style(unittest.TestCase):
    def setUp(self):
        self._name = theme._state["name"]

    def tearDown(self):
        theme._state["name"] = self._name

    def test_dark_and_light_get_the_text_exactly(self):
        text = "#Fission180Home { background: #2a2a2a; }"
        for look in ("dark", "light"):
            theme._state["name"] = look
            widget = _Widget()
            neon_qss_panels.style(widget, text, "home")
            self.assertEqual(widget.sheet, text, look)
            self.assertEqual(widget.property(neon_qss_panels.PROP_TEXT), text)
            self.assertEqual(widget.property(neon_qss_panels.PROP_PART), "home")

    def test_every_part_is_known(self):
        self.assertEqual(
            sorted(neon_qss_panels.BLOCKS),
            sorted(
                [
                    "home", "home_update", "home_notice", "ai", "sketch_palette",
                    "measure_in_sketch", "measure_results", "marking", "arrow_value",
                    "data_upload", "dim_label", "caption",
                ]
            ),
        )

    def test_listed_as_a_listener(self):
        for module in ("neon_qss_panels", "data_panel_ui", "ai_panel_ui", "home_ui"):
            self.assertIn(module, theme.LISTENERS)
        self.assertEqual(theme.LISTENERS[-1], "neon_qss_panels")  # after the panels' own


if __name__ == "__main__":
    unittest.main()
