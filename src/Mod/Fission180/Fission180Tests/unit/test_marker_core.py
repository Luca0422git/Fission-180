# SPDX-License-Identifier: LGPL-2.1-or-later
"""How Measure's points and its distance look and where the distance goes (fission180/
marker_core.py). Luca, 2026-11-20: "the measure tools points are just a little too big ...
zooming in on it makes them massive ... maybe not have it light yellow? its impossible to see
the text." Runs with a fake FreeCAD (no window)."""

import colorsys
import math
import os
import sys
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.dirname(__file__))
from test_smoke_fake_freecad import FakeParams  # noqa: E402

from fission180 import marker_core as core  # noqa: E402
from fission180 import neon_palette as np  # noqa: E402
from fission180 import neon_scene_core as nsc  # noqa: E402

DARK_VIEW = "#2a2a2a"  # theme.DARK["view"]: the 3D view's background in Dark
LIGHT_VIEW = "#f7f8fa"  # theme.LIGHT["view"]
# the default steel part's three faces in an isometric view (read off a screenshot)
STEEL = ("#555a5f", "#808082", "#8a8b8d")
SELECTED = "#3b5bdb"  # sketch_mode.SELECT: a picked face or edge
OLD_AMBER = (0.98, 0.78, 0.25)  # what the dots were (lit to a pale yellow)


def hex_of(rgb):
    return "#%02x%02x%02x" % tuple(int(round(float(c) * 255)) for c in rgb)


def hue(rgb):
    return colorsys.rgb_to_hsv(*[float(c) for c in rgb])[0] * 360.0


def rect_disc_gap(box, centre, radius):
    """How far the rectangle (x, y, w, h) stays from the disc (negative: they overlap)."""
    x, y, w, h = box
    dx = max(x - centre[0], 0.0, centre[0] - (x + w))
    dy = max(y - centre[1], 0.0, centre[1] - (y + h))
    return math.hypot(dx, dy) - radius


def rect_line_gap(box, a, b):
    """How far the rectangle stays from the infinite line through a and b (0: it touches)."""
    x, y, w, h = box
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy)
    nx, ny = -dy / length, dx / length
    sides = [(cx - a[0]) * nx + (cy - a[1]) * ny for cx in (x, x + w) for cy in (y, y + h)]
    if min(sides) < 0 < max(sides):
        return 0.0
    return min(abs(s) for s in sides)


class Sizes(unittest.TestCase):
    def test_a_point_is_a_small_marker_of_fixed_pixels(self):
        # It was 12-14 px across at a Fit and "just a little too big": a bit smaller now.
        across = 2 * (core.DOT_RADIUS_PX + core.RIM_PX)
        self.assertTrue(8.0 <= across <= 12.0, across)
        self.assertTrue(8.0 <= 2 * (core.SNAP_RADIUS_PX + core.RIM_PX) <= 12.0)
        # the Center of Mass dot leaves its sign showing round it, and is still easy to see
        self.assertLess(core.COM_RADIUS_PX, core.DOT_RADIUS_PX)
        self.assertGreaterEqual(2 * (core.COM_RADIUS_PX + core.RIM_PX), 7.0)

    def test_the_rim_is_thin(self):
        self.assertTrue(1.0 <= core.RIM_PX <= 2.0)

    def test_disc_points(self):
        points = core.disc(4.0, 20)
        self.assertEqual(len(points), 20)
        for x, y, z in points:
            self.assertAlmostEqual(math.hypot(x, y), 4.0)
            self.assertEqual(z, 0.0)

    def test_label_size(self):
        self.assertEqual(
            core.label_size(50.0, 16.0), (50.0 + 2 * core.LABEL_PAD_X, 16.0 + 2 * core.LABEL_PAD_Y)
        )


class Colours(unittest.TestCase):
    def test_not_yellow_and_darker(self):
        rgb = core.MEASURE.normal()
        self.assertFalse(35.0 <= hue(rgb) <= 75.0, hue(rgb))
        self.assertLess(np._luminance(hex_of(rgb)), 0.5 * np._luminance(hex_of(OLD_AMBER)))

    def test_reads_on_both_backgrounds(self):
        dot = hex_of(core.MEASURE.normal())
        for ground in (DARK_VIEW, LIGHT_VIEW):
            self.assertGreaterEqual(np.contrast(dot, ground), 3.0, ground)

    def test_reads_on_the_part_and_a_selected_face(self):
        # On the grey part a strong colour against no colour at all, with the light rim
        # drawing its edge on every grey; on a selected face or edge, the far side of the
        # colour wheel from its blue.
        rgb = core.MEASURE.normal()
        self.assertGreaterEqual(colorsys.rgb_to_hsv(*rgb)[1], 0.7)
        rim = hex_of(core.RIM.normal())
        for grey in STEEL:
            self.assertGreaterEqual(np.contrast(rim, grey), 3.0, grey)
        self.assertGreaterEqual(np.contrast(rim, DARK_VIEW), 7.0)
        blue = [c / 255.0 for c in np._rgb(SELECTED)]
        apart = abs(hue(rgb) - hue(blue)) % 360.0
        self.assertGreaterEqual(min(apart, 360.0 - apart), 120.0)

    def test_reads_on_every_neon_background(self):
        # Neon Lights: the dots take the preset's own light measure colour, with the light rim;
        # not the colour Neon Lights draws the bodies' edges in, as the line often runs on one.
        for key in np.ORDER:
            p = np.derive(np.roles(key))
            roles = nsc.roles3d(p)
            dot, rim = hex_of(roles[core.MEASURE.role]), hex_of(roles[core.RIM.role])
            best = max(np.contrast(dot, p["view"]), np.contrast(rim, p["view"]))
            self.assertGreaterEqual(best, 3.0, key)
            self.assertNotEqual(dot, p["outline"].lower(), key)


class _WithTheme(unittest.TestCase):
    def setUp(self):
        fake = types.ModuleType("FreeCAD")
        groups = {}
        fake.ParamGet = lambda path: groups.setdefault(path, FakeParams())
        fake.Console = types.SimpleNamespace(
            PrintMessage=lambda text: None,
            PrintWarning=lambda text: None,
            PrintError=lambda text: None,
            PrintLog=lambda text: None,
        )
        self._saved = sys.modules.get("FreeCAD")
        sys.modules["FreeCAD"] = fake
        from fission180 import theme

        self.theme = theme

    def tearDown(self):
        if self._saved is None:
            sys.modules.pop("FreeCAD", None)
        else:
            sys.modules["FreeCAD"] = self._saved


class LabelColours(_WithTheme):
    def test_text_reads_on_its_box_in_every_look(self):
        accent = hex_of(core.MEASURE.normal())
        palettes = [("dark", self.theme.DARK), ("light", self.theme.LIGHT)]
        palettes += [(key, np.derive(np.roles(key))) for key in np.ORDER]
        for name, p in palettes:
            backing, rim, text = core.label_colours(p, accent)
            self.assertGreaterEqual(np.contrast(text, backing), 4.5, name)
            self.assertEqual(rim, accent)

    def test_the_box_follows_the_look(self):
        accent = "#d9381f"
        self.assertEqual(core.label_colours(self.theme.DARK, accent)[0], self.theme.DARK["field"])
        self.assertEqual(core.label_colours(self.theme.LIGHT, accent)[0], self.theme.LIGHT["field"])


class LabelPlace(unittest.TestCase):
    SIZE = (78.0, 22.0)
    CLEAR = core.DOT_RADIUS_PX + core.RIM_PX

    def box(self, a, b, size=None, view=None):
        size = size or self.SIZE
        dx, dy = core.label_offset(a, b, size, self.CLEAR, view=view)
        mx, my = (a[0] + b[0]) / 2.0, (a[1] + b[1]) / 2.0
        return (mx + dx - size[0] / 2.0, my + dy - size[1] / 2.0, size[0], size[1])

    def test_above_a_level_line(self):
        x, y, w, h = self.box((100.0, 300.0), (160.0, 300.0))
        self.assertAlmostEqual(y, 300.0 + self.CLEAR + core.LABEL_GAP_PX)  # its lower edge
        self.assertAlmostEqual(x + w / 2.0, 130.0)  # over the middle

    def test_beside_an_upright_line(self):
        x, y, w, h = self.box((400.0, 200.0), (400.0, 260.0))
        self.assertAlmostEqual(x, 400.0 + self.CLEAR + core.LABEL_GAP_PX)  # on its right
        self.assertAlmostEqual(y + h / 2.0, 230.0)

    def test_never_on_the_dots_or_the_line(self):
        # Every direction, a line from a few pixels (zoomed far out) to long: the box stays
        # off both dots (with their rim) and off the line by the gap.
        for length in (0.5, 3.0, 12.0, 40.0, 300.0):
            for step in range(72):
                angle = math.radians(step * 5.0)
                a = (500.0, 400.0)
                b = (a[0] + length * math.cos(angle), a[1] + length * math.sin(angle))
                box = self.box(a, b)
                for centre in (a, b):
                    gap = rect_disc_gap(box, centre, self.CLEAR)
                    self.assertGreaterEqual(gap, core.LABEL_GAP_PX - 1e-6, (length, step))
                self.assertGreaterEqual(
                    rect_line_gap(box, a, b), self.CLEAR + core.LABEL_GAP_PX - 1e-6, (length, step)
                )

    def test_close_to_the_line(self):
        # Beside the line, not far off: the box's near side is just the gap past the dots.
        for step in range(72):
            angle = math.radians(step * 5.0 + 1.0)
            a = (500.0, 400.0)
            b = (a[0] + 80.0 * math.cos(angle), a[1] + 80.0 * math.sin(angle))
            gap = rect_line_gap(self.box(a, b), a, b)
            self.assertAlmostEqual(gap, self.CLEAR + core.LABEL_GAP_PX, places=6)

    def test_same_place_either_way_round(self):
        pairs = (((10.0, 20.0), (90.0, 70.0)), ((5.0, 5.0), (5.0, 80.0)), ((0.0, 0.0), (60.0, -30.0)))
        for a, b in pairs:
            self.assertEqual(
                tuple(round(v, 9) for v in core.label_offset(a, b, self.SIZE, self.CLEAR)),
                tuple(round(v, 9) for v in core.label_offset(b, a, self.SIZE, self.CLEAR)),
            )

    def test_one_point(self):
        x, y, w, h = self.box((200.0, 200.0), (200.0, 200.0))
        self.assertGreaterEqual(y, 200.0 + self.CLEAR)  # above it

    def test_isometric_edges_keep_their_side(self):
        # The edges of an isometric view (upright, 30 degrees each way) are far from the
        # direction where the label changes side: a slight turn does not make it jump.
        def n(degrees):
            angle = math.radians(degrees)
            return core.normal((0.0, 0.0), (math.cos(angle), math.sin(angle)))

        for degrees in (90.0, 30.0, -30.0, 150.0, 0.0, 180.0, 270.0):
            here = n(degrees)
            for nudge in (-4.0, 4.0):
                there = n(degrees + nudge)
                self.assertGreater(here[0] * there[0] + here[1] * there[1], 0.9, (degrees, nudge))
        self.assertGreater(n(90.0)[0], 0.99)  # an upright line: on its right
        self.assertGreater(n(0.0)[1], 0.99)  # a level one: above

    def test_other_side_at_the_edge_of_the_view(self):
        view = (800.0, 600.0)
        x, y, w, h = self.box((300.0, 590.0), (360.0, 590.0), view=view)  # a line at the top
        self.assertLessEqual(y + h, 590.0 - self.CLEAR)  # below it instead
        x, y, w, h = self.box((300.0, 300.0), (360.0, 300.0), view=view)  # room above
        self.assertGreaterEqual(y, 300.0)

    def test_stays_put_when_neither_side_fits(self):
        view = (60.0, 30.0)
        above = self.box((10.0, 15.0), (50.0, 15.0))
        self.assertEqual(self.box((10.0, 15.0), (50.0, 15.0), view=view), above)


if __name__ == "__main__":
    unittest.main()
