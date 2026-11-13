# SPDX-License-Identifier: LGPL-2.1-or-later
"""The DRAWING AI tools' pure parts (wave 8, ai-drawing): the catalogue entries' rules and
their lists against the drawing code's own, the placements the actions work out when the AI
gives no place (fission180/ai/drawing_core_ai.py) and the sheet picture
(fission180/ai/drawing_picture.py). Plain Python (numpy for the picture)."""

import os
import struct
import sys
import unittest
import zlib

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from fission180.ai import catalog  # noqa: E402
from fission180.ai import drawing_core_ai as aicore  # noqa: E402
from fission180.ai.catalog import drawing_tools  # noqa: E402

DRAWING_TOOLS = (
    "create_drawing",
    "add_drawing_view",
    "edit_drawing_view",
    "modify_drawing",
    "edit_title_block",
    "drawing_sheet",
    "add_drawing_dimension",
    "edit_drawing_dimension",
    "add_drawing_annotation",
    "add_drawing_geometry",
    "add_drawing_symbol",
    "edit_balloons",
    "get_drawing",
    "export_drawing",
)


def _png_size(png):
    return struct.unpack(">II", png[16:24])


def _png_rgb(png):
    """The pixels of a PNG written by drawing_picture.png_bytes (RGB, filter 0)."""
    import numpy

    w, h = _png_size(png)
    pos = 8
    data = b""
    while pos < len(png):
        length = struct.unpack(">I", png[pos : pos + 4])[0]
        tag = png[pos + 4 : pos + 8]
        if tag == b"IDAT":
            data += png[pos + 8 : pos + 8 + length]
        pos += 12 + length
    raw = zlib.decompress(data)
    rows = [raw[y * (3 * w + 1) + 1 : (y + 1) * (3 * w + 1)] for y in range(h)]
    return numpy.frombuffer(b"".join(rows), dtype=numpy.uint8).reshape(h, w, 3)


class Catalogue(unittest.TestCase):
    def test_the_drawing_tools_and_their_order(self):
        names = [t["name"] for t in catalog.TOOLS if t["category"] == "drawing"]
        self.assertEqual(tuple(names), DRAWING_TOOLS)
        for name in DRAWING_TOOLS:
            entry = catalog.tool(name)
            self.assertLessEqual(len(entry["description"]), 900, name)
            # (create_drawing makes the drawing: it needs a solid; every other one a drawing)
            want = ("solid",) if name == "create_drawing" else ("drawing",)
            self.assertEqual(entry["needs"], want, name)

    def test_the_old_arguments_still_pass(self):
        """The six tools of before wave 8 take their old calls unchanged."""
        v = catalog.validate
        self.assertEqual(
            v("create_drawing", {"base_view": "Front", "projected": ["Top", "Right"]}), []
        )
        self.assertEqual(
            v(
                "add_drawing_view",
                {"kind": "section", "parent": "BaseView", "line": [[-30, 0], [30, 0]]},
            ),
            [],
        )
        self.assertEqual(
            v("add_drawing_view", {"kind": "detail", "parent": "B", "center": [1, 2], "radius": 3}),
            [],
        )
        self.assertEqual(
            v(
                "add_drawing_dimension",
                {"view": "BaseView", "picks": [{"kind": "line", "near": [0, 5]}]},
            ),
            [],
        )
        self.assertEqual(
            v("add_drawing_annotation", {"kind": "text", "text": "Hi", "at": [1, 2]}), []
        )
        self.assertEqual(
            v("add_drawing_annotation", {"kind": "center_marks", "view": "BaseView"}), []
        )
        self.assertEqual(v("get_drawing", {"edges": True}), [])
        self.assertEqual(v("export_drawing", {"format": "dxf", "path": "/a.dxf"}), [])

    def test_rules_say_what_is_missing(self):
        cases = [
            ("add_drawing_view", {"kind": "break", "parent": "V"}, "a break needs start and end"),
            ("add_drawing_view", {"kind": "breakout", "parent": "V"}, "a breakout needs boundary"),
            (
                "add_drawing_view",
                {
                    "kind": "breakout",
                    "parent": "V",
                    "boundary": [[0, 0], [1, 0], [1, 1]],
                    "depth": 2,
                    "through_all": True,
                },
                "depth or through_all",
            ),
            (
                "add_drawing_view",
                {"kind": "base", "orientation": "Top", "storyboard": "S"},
                "storyboard is for kind exploded",
            ),
            ("edit_drawing_view", {"view": "V"}, "at least one thing to change"),
            ("modify_drawing", {"kind": "move", "items": ["A"]}, "move needs by"),
            ("modify_drawing", {"kind": "move", "items": ["A", "B"], "to": [1, 2]}, "to moves one"),
            ("modify_drawing", {"kind": "rotate", "items": ["A"]}, "rotate needs angle"),
            (
                "modify_drawing",
                {"kind": "delete", "items": ["A"], "angle": 3},
                "angle is for rotate",
            ),
            ("edit_title_block", {"values": {"Colour": "red"}}, "values.Colour is no title block"),
            ("edit_title_block", {"values": {}}, "at least one field"),
            ("drawing_sheet", {"action": "rename", "drawing": "D"}, "rename needs name"),
            ("drawing_sheet", {"action": "delete"}, "delete needs drawing"),
            (
                "add_drawing_dimension",
                {"view": "V", "type": "ordinate", "picks": [{"kind": "vertex"}]},
                "ordinate needs origin",
            ),
            (
                "add_drawing_dimension",
                {"type": "chain", "picks": [{"kind": "vertex"}]},
                "chain needs from",
            ),
            (
                "add_drawing_dimension",
                {"view": "V", "type": "arc_length", "picks": [{"kind": "arc"}, {"kind": "arc"}]},
                "arc_length takes one pick",
            ),
            ("add_drawing_dimension", {"picks": [{"kind": "line"}]}, "view is needed"),
            ("add_drawing_dimension", {"view": "V", "picks": [{"radius": 2}]}, "needs near"),
            (
                "edit_drawing_dimension",
                {"dimensions": ["D"], "tolerance": "deviation", "upper": 1},
                "deviation tolerance needs upper and lower",
            ),
            (
                "edit_drawing_dimension",
                {"dimensions": ["D"], "tolerance": "fit"},
                "fit tolerance needs fit",
            ),
            (
                "edit_drawing_dimension",
                {"dimensions": ["D", "E"], "at": [1, 2]},
                "at moves one dimension",
            ),
            (
                "add_drawing_annotation",
                {"kind": "leader", "view": "V", "text": "x"},
                "leader needs pick",
            ),
            ("add_drawing_annotation", {"kind": "balloon", "view": "V"}, "balloon needs component"),
            ("add_drawing_annotation", {"kind": "parts_list"}, "parts_list needs view"),
            (
                "add_drawing_geometry",
                {"kind": "centerline", "view": "V", "picks": [{"kind": "line"}]},
                "centerline takes two picks",
            ),
            (
                "add_drawing_geometry",
                {"kind": "center_mark_pattern", "view": "V", "picks": [{"kind": "circle"}]},
                "two or more picks",
            ),
            (
                "add_drawing_symbol",
                {"kind": "datum_identifier", "at": [1, 2]},
                "needs view and pick",
            ),
            ("add_drawing_symbol", {"kind": "feature_control_frame"}, "a frame alone needs at"),
            (
                "add_drawing_symbol",
                {"kind": "datum_identifier", "view": "V", "pick": {"kind": "line"}, "letter": "1"},
                "letters",
            ),
            (
                "add_drawing_symbol",
                {
                    "kind": "datum_identifier",
                    "view": "V",
                    "pick": {"kind": "line"},
                    "value": "Ra 3.2",
                },
                "value is for surface_texture",
            ),
            (
                "edit_balloons",
                {"kind": "align", "balloons": ["1"], "at": [1, 2]},
                "align needs balloons (two or more)",
            ),
            ("edit_balloons", {"kind": "renumber", "balloon": "1"}, "renumber needs balloon"),
            ("export_drawing", {"format": "dwg", "path": "/a.dxf"}, "path must end in .dwg"),
            (
                "export_drawing",
                {"format": "dxf", "path": "/a.dxf", "table": "T"},
                "table is for format csv",
            ),
            ("create_drawing", {"bodies": ["A"], "flat_pattern": "F"}, "give one of bodies"),
        ]
        for tool, args, words in cases:
            with self.subTest(tool=tool, args=args):
                problems = catalog.validate(tool, args)
                self.assertTrue(any(words in p for p in problems), problems)

    def test_new_calls_pass(self):
        v = catalog.validate
        good = [
            ("add_drawing_view", {"kind": "break", "parent": "V", "start": [-1, 0], "end": [1, 0]}),
            (
                "add_drawing_view",
                {
                    "kind": "breakout",
                    "parent": "V",
                    "boundary": [[0, 0], [1, 0], [1, 1]],
                    "through_all": True,
                },
            ),
            ("add_drawing_view", {"kind": "exploded", "storyboard": "S"}),
            (
                "add_drawing_view",
                {
                    "kind": "section",
                    "parent": "V",
                    "line": [[0, 0], [1, 0], [1, 1]],
                    "depth_mode": "Slice",
                },
            ),
            ("edit_drawing_view", {"view": "V", "center_marks": {"holes": True}}),
            ("modify_drawing", {"kind": "delete", "items": ["A", "B"]}),
            ("drawing_sheet", {"action": "add"}),
            (
                "add_drawing_dimension",
                {
                    "view": "V",
                    "type": "ordinate",
                    "axis": "x",
                    "origin": {"kind": "vertex", "near": [0, 0]},
                    "picks": [{"kind": "circle", "near": [1, 1]}] * 5,
                },
            ),
            (
                "add_drawing_dimension",
                {"type": "baseline", "from": "D", "picks": [{"kind": "vertex", "near": [1, 1]}]},
            ),
            (
                "edit_drawing_dimension",
                {"dimensions": ["D"], "tolerance": "symmetric", "upper": 0.1},
            ),
            ("add_drawing_annotation", {"kind": "bend_note", "view": "V", "bends": [1, 2]}),
            ("add_drawing_geometry", {"kind": "center_mark", "view": "V"}),
            (
                "add_drawing_symbol",
                {
                    "kind": "feature_control_frame",
                    "at": [10, 10],
                    "second_row": {"tolerance": 0.02, "datums": ["A"]},
                },
            ),
            ("edit_balloons", {"kind": "renumber", "balloon": "2", "to": 1}),
            ("export_drawing", {"format": "csv", "path": "/p.csv", "table": "PartsList"}),
            ("get_drawing", {"picture": True, "width": 800}),
            ("create_drawing", {"automatic": True, "storyboard": "Explode"}),
            ("create_drawing", {"contents": "full_assembly"}),
        ]
        for tool, args in good:
            with self.subTest(tool=tool):
                self.assertEqual(v(tool, args), [])

    def test_lists_are_the_drawing_code_s(self):
        from fission180 import drawing_annot_core as ac
        from fission180 import drawing_core as core
        from fission180 import drawing_dims_core as dc

        self.assertEqual(drawing_tools.CHARACTERISTICS, ac.CHARACTERISTIC_NAMES)
        self.assertEqual(drawing_tools.TEXTURES, tuple(k for k, _n in ac.SURFACE_KINDS))
        self.assertEqual(drawing_tools.LAYS, ac.LAYS)
        self.assertEqual(drawing_tools.MATERIAL, tuple(m for m, _n in ac.MODIFIERS))
        self.assertEqual(drawing_tools.TITLE_KEYS, core.TITLE_KEYS)
        self.assertEqual(drawing_tools.STYLES, core.STYLES)
        self.assertEqual(drawing_tools.TANGENT_EDGES, core.TANGENT_EDGES)
        self.assertEqual(drawing_tools.ORIENTATIONS, core.ORIENTATION_NAMES)
        self.assertEqual(drawing_tools.PRECISIONS, dc.PRECISIONS)
        self.assertEqual(
            [aicore.TOLERANCE_NAMES[t] for t in drawing_tools.TOLERANCES], list(dc.TOLERANCES)
        )
        self.assertEqual(
            [aicore.FIT_DISPLAY_NAMES[t] for t in drawing_tools.FIT_DISPLAYS], list(dc.FIT_DISPLAYS)
        )
        self.assertEqual(set(drawing_tools.PROJECTED), set(aicore.SIDES))


class Placement(unittest.TestCase):
    def test_free_spot_keeps_clear(self):
        area = (0, 0, 200, 100)
        blocked = [(0, 0, 120, 100)]
        spot = aicore.free_spot(area, blocked, (40, 40), margin=5)
        self.assertIsNotNone(spot)
        self.assertGreaterEqual(spot[0] - 20, 125 - 1e-9)
        self.assertIsNone(aicore.free_spot(area, [(0, 0, 200, 100)], (40, 40)))
        self.assertIsNone(aicore.free_spot(area, [], (300, 10)))

    def test_projected_views_side_by_side(self):
        # third angle: Top above, Right to the right; first angle mirrored
        self.assertEqual(
            aicore.projected_offset((80, 40), (80, 10), "Top", "Third angle", 1, 20),
            (0.0, 25.0 + 20),
        )
        self.assertEqual(
            aicore.projected_offset((80, 40), (10, 40), "Right", "First angle", 2, 20),
            (-(90.0 + 20), -0.0),
        )
        dx, dy = aicore.projected_offset((80, 40), (60, 60), "FrontTopRight", "Third angle", 1, 10)
        self.assertEqual((dx, dy), (80.0, 60.0))

    def test_layout_fits_the_area_at_the_largest_scale(self):
        plan = aicore.layout_views(
            (100, 50),
            [("Top", (100, 20)), ("Right", (20, 50))],
            "Third angle",
            (0, 0, 300, 200),
            [4.0, 2.0, 1.0],
            gap=10,
        )
        self.assertEqual(plan["scale"], 2.0)  # (4:1: 400 + 10 + 80 wide; 2:1: 250 x 150)
        self.assertTrue(plan["fits"])
        bx, by = plan["base"]
        (tx, ty), (rx, ry) = plan["children"]
        self.assertAlmostEqual(tx, bx)
        self.assertGreater(ty, by)
        self.assertGreater(rx, bx)
        self.assertAlmostEqual(ry, by)
        # nothing outside the area
        self.assertGreaterEqual(bx - 50, 0)
        self.assertLessEqual(rx + 10, 300)
        self.assertLessEqual(ty + 10, 200)

    def test_layout_keeps_a_given_base_place(self):
        plan = aicore.layout_views(
            (10, 10),
            [("Right", (10, 10))],
            "Third angle",
            (0, 0, 100, 100),
            [1.0],
            gap=5,
            at=(30, 50),
        )
        self.assertEqual(plan["base"], (30, 50))
        self.assertEqual(plan["children"][0], (45.0, 50.0))

    def test_dimension_text_goes_outside_the_view(self):
        line = {"kind": "line", "p1": (-40, -20), "p2": (40, -20)}
        place = aicore.dimension_place("DistanceX", [line], (40, 20), 2.0)
        self.assertEqual(place, (0.0, -(20 + 4.0)))
        # a second one on that side goes one step further out
        again = aicore.dimension_place("DistanceX", [line], (40, 20), 2.0, taken=[place])
        self.assertEqual(again, (0.0, -(20 + 4.0 + 4.0)))
        side = {"kind": "line", "p1": (40, -20), "p2": (40, 20)}
        self.assertEqual(aicore.dimension_place("DistanceY", [side], (40, 20), 1.0), (48.0, 0.0))
        hole = {"kind": "circle", "center": (0, 0), "radius": 5}
        x, y = aicore.dimension_place("Diameter", [hole], (40, 20), 1.0)
        self.assertAlmostEqual(x, y)
        self.assertAlmostEqual(x * 2**0.5, 13.0)

    def test_linear_axis_follows_the_longer_spread(self):
        a = {"kind": "vertex", "point": (0, 0)}
        b = {"kind": "vertex", "point": (3, 10)}
        self.assertEqual(aicore.linear_axis([a, b]), "DistanceY")
        c = {"kind": "circle", "center": (10, 2), "radius": 1}
        self.assertEqual(aicore.linear_axis([a, c]), "DistanceX")

    def test_baseline_starts_at_the_far_end(self):
        self.assertEqual(aicore.baseline_start([(0, 0), (20, 0)], [(60, 0)]), 0)
        self.assertEqual(aicore.baseline_start([(60, 0), (20, 0)], [(0, 0), (5, 0)]), 0)
        self.assertEqual(aicore.baseline_start([(20, 0), (60, 0)], [(0, 0)]), 1)

    def test_ordinate_lines(self):
        rect = (10, 20, 110, 70)
        self.assertEqual(aicore.ordinate_lines(rect, "x"), 20 - aicore.GAP)
        self.assertEqual(aicore.ordinate_lines(rect, "y"), 10 - aicore.GAP)
        self.assertEqual(aicore.ordinate_lines(rect, "x", at=(5, 3)), 3)
        self.assertEqual(aicore.ordinate_lines(rect, "y", at=(5, 3)), 5)

    def test_outward(self):
        x, y = aicore.outward((0, 0, 10, 10), (10, 5), 3)
        self.assertAlmostEqual(x, 13)
        self.assertAlmostEqual(y, 5)

    def test_dimension_settings_from_arguments(self):
        from fission180 import drawing_dims_core as dc

        base = dc.settings({})
        got = aicore.dimension_settings({"tolerance": "symmetric", "upper": 0.1}, base)
        self.assertEqual((got["tolerance"], got["upper"], got["lower"]), ("Symmetric", 0.1, -0.1))
        self.assertEqual(dc.validate(got), "")
        hole = aicore.dimension_settings({"tolerance": "fit", "fit": "H7"}, base)
        self.assertEqual((hole["fit"], hole["fit_member"]), ("H7/h7", "Hole"))
        self.assertEqual(dc.validate(hole, 10.0), "")
        shaft = aicore.dimension_settings({"tolerance": "fit", "fit": "g6"}, base)
        self.assertEqual((shaft["fit"], shaft["fit_member"]), ("H6/g6", "Shaft"))
        both = aicore.dimension_settings(
            {"tolerance": "fit", "fit": "H7/g6", "fit_member": "shaft", "fit_display": "limits"},
            base,
        )
        self.assertEqual(
            (both["fit"], both["fit_member"], both["fit_display"]), ("H7/g6", "Shaft", "Limits")
        )
        text = aicore.dimension_settings({"override": "TYP", "basic": True}, base)
        self.assertEqual((text["override"], text["basic"]), ("TYP", True))
        self.assertEqual(dc.texts(10.0, "Distance", "mm", text)["framed"], True)

    def test_element_text(self):
        self.assertEqual(
            aicore.element_text({"kind": "line", "p1": (0, -0.0004), "p2": (3.25, 1)}),
            "line (0, 0)-(3.25, 1)",
        )
        self.assertEqual(
            aicore.element_text({"kind": "arc", "center": (1, 2), "radius": 6}), "arc R6 at (1, 2)"
        )
        self.assertEqual(aicore.scale_text(0.5), "1:2")
        self.assertEqual(aicore.scale_text(4), "4:1")


class Picture(unittest.TestCase):
    def _entities(self):
        from fission180 import drawing_core as core

        dxf = core.DxfWriter()
        dxf.line(10, 10, 110, 10, "VISIBLE")
        dxf.line(10, 40, 110, 40, "HIDDEN")
        dxf.circle(60, 25, 8, "CENTER")
        dxf.arc(60, 25, 12, 0, 90, "VISIBLE")
        dxf.text(60, 60, 5, "A-A 12.5", "TEXT", "center")
        dxf.solid([(0, 0), (4, 1), (0, 2)], "DIMENSIONS")
        return core.read_dxf_entities(dxf.to_text())

    def test_a_png_of_the_sheet_size(self):
        from fission180.ai import drawing_picture

        png = drawing_picture.render(self._entities(), (120, 80), width=600)
        self.assertEqual(png[:8], b"\x89PNG\r\n\x1a\n")
        self.assertEqual(_png_size(png), (600, 400))
        rgb = _png_rgb(png)
        k = 5.0  # px per mm
        # the visible line at y = 10 mm: ink across it, none above it
        self.assertGreater(
            drawing_picture.ink(rgb, (60, int((80 - 10) * k) - 2, 540, int((80 - 10) * k) + 3)), 400
        )
        self.assertEqual(drawing_picture.ink(rgb, (500, 100, 560, 150)), 0)  # empty paper
        # the hidden line is dashed: ink and gaps along it
        row = rgb[int((80 - 40) * k)]
        dark = (row[60:540] < 200).any(axis=1)
        self.assertTrue(dark.any() and not dark.all())
        # the text is drawn
        self.assertGreater(
            drawing_picture.ink(rgb, (200, int((80 - 66) * k), 400, int((80 - 59) * k))), 50
        )

    def test_shapes_by_layer(self):
        from fission180.ai import drawing_picture

        shapes = drawing_picture.shapes(self._entities())
        self.assertEqual(len(shapes["VISIBLE"]["lines"]), 2)
        self.assertEqual(len(shapes["DIMENSIONS"]["fills"]), 1)
        self.assertGreater(len(shapes["TEXT"]["lines"]), 8)
        circle = shapes["CENTER"]["lines"][0]
        self.assertAlmostEqual(circle[0][0], circle[-1][0])
        self.assertAlmostEqual(circle[0][1], circle[-1][1])

    def test_text_strokes_follow_alignment_and_rotation(self):
        from fission180.ai import drawing_picture as dp

        strokes = dp.text_strokes("10", 0, 0, 6, "right")
        xs = [p[0] for line in strokes for p in line]
        self.assertLessEqual(max(xs), 1e-9)
        self.assertAlmostEqual(dp.text_width("10", 6), 2 * dp.ADVANCE)
        turned = dp.text_strokes("1", 0, 0, 6, "left", 90)
        self.assertTrue(all(p[0] <= 1e-9 for line in turned for p in line))
        self.assertEqual(dp.glyph(" "), [])
        self.assertEqual(dp.glyph("a"), dp.GLYPHS["A"])
        self.assertTrue(dp.glyph("☃"))  # (an unknown character: a box)


if __name__ == "__main__":
    unittest.main()
