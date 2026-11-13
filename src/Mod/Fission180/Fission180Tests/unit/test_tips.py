# SPDX-License-Identifier: LGPL-2.1-or-later
"""fission180/tips: every ribbon command has a complete Fusion-style tooltip and its picture
(wave 8, tips-ui; the merger's yardstick).

One test per data module (test_module_solid ... test_module_animation): a content builder
runs the ones of their own modules, e.g.

    python3 -m unittest Fission180Tests.unit.test_tips.Coverage.test_module_solid

While no data module is written yet (the tips-ui branch alone) the coverage tests are skipped
with the list of what waits; once any is written every module is checked, and a module not
written yet fails with the commands it still owes. The loader's own rules and the picture
helpers' pure parts are tested here too.
"""

import importlib.util
import io
import os
import struct
import sys
import tempfile
import unittest
import zlib

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fission180 import ribbon_config as cfg  # noqa: E402
from fission180 import tips  # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
REPO = os.path.abspath(os.path.join(ROOT, "..", "..", ".."))
TOOLS = os.path.join(REPO, "tools", "fission180")
IN_SOURCE_TREE = os.path.isdir(TOOLS)


def _png(width, height, extra=0):
    """A tiny valid PNG of a size (pure Python), padded with `extra` bytes of text chunk."""

    def chunk(kind, data):
        body = kind + data
        return (
            struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
        )

    raw = b"".join(b"\x00" + b"\x2a" * (width * 3) for _ in range(height))
    data = b"\x89PNG\r\n\x1a\n"
    data += chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
    if extra:
        data += chunk(b"tEXt", b"pad\x00" + b"x" * extra)
    data += chunk(b"IDAT", zlib.compress(raw))
    data += chunk(b"IEND", b"")
    return data


GOOD = {
    "summary": "Rounds the edges you pick with a radius you set.",
    "what": "Fillet makes sharp edges round. Use it to soften a part or to make it stronger.",
    "steps": ["Select the edges to round.", "Type or drag the radius.", "Click OK."],
    "tips": ["Hold Ctrl to pick more edges."],
    "picture": "fillet.png",
}


def written():
    """The data modules that exist (tips/<name>.py)."""
    folder = os.path.dirname(tips.__file__)
    return [m for m in tips.MODULES if os.path.isfile(os.path.join(folder, m + ".py"))]


class Loader(unittest.TestCase):
    def test_command_id(self):
        self.assertEqual(tips.command_id({"command": "Fission180_Fillet"}), "Fission180_Fillet")
        self.assertEqual(
            tips.command_id({"command": ("Fission180_Revolve", "PartDesign_Revolution")}),
            "Fission180_Revolve",
        )
        self.assertEqual(tips.command_id({"command": "PartDesign_X#2"}), "PartDesign_X")
        self.assertIsNone(tips.command_id({"command": None}))
        self.assertIsNone(tips.command_id({"command": "__repeat__"}))
        self.assertIsNone(tips.command_id(None))

    def test_ribbon_commands_once_each_in_its_first_tab(self):
        rows = tips.ribbon_commands()
        ids = [r[0] for r in rows]
        self.assertEqual(len(ids), len(set(ids)))
        by_id = {r[0]: r for r in rows}
        # Measure is in SOLID's INSPECT and in every other tab: filed under solid
        self.assertEqual(by_id["Fission180_Measure"][3], "solid")
        self.assertEqual(by_id["Fission180_Fillet"][2], "solid")
        # every tab has a data module
        self.assertEqual({t["id"] for t in cfg.TABS} - set(tips.TAB_MODULES), set())
        self.assertTrue(all(r[3] in tips.MODULES for r in rows))
        # greyed items (no command) are not counted
        self.assertTrue(all(r[0] for r in rows))

    def test_a_complete_entry_has_no_problems(self):
        with tempfile.TemporaryDirectory() as folder:
            old = tips.PICTURE_DIR
            tips.PICTURE_DIR = folder
            try:
                with open(os.path.join(folder, "fillet.png"), "wb") as handle:
                    handle.write(_png(320, 200))
                self.assertEqual(tips.problems("Fission180_Fillet", GOOD), [])
            finally:
                tips.PICTURE_DIR = old

    def test_problems_name_what_is_wrong(self):
        bad = dict(GOOD)
        bad["summary"] = "x" * 111
        bad["steps"] = ["Only one."]
        bad["tips"] = ["a", "b", "c", "d"]
        bad["extra"] = 1
        del bad["what"]
        text = "\n".join(tips.problems("Fission180_Fillet", bad, check_picture=False))
        self.assertIn("missing what", text)
        self.assertIn("unknown keys extra", text)
        self.assertIn("summary has 111 characters", text)
        self.assertIn("1 steps (2 to 6)", text)
        self.assertIn("4 tips (0 to 3)", text)

    def test_long_steps_and_too_many_sentences(self):
        bad = dict(GOOD)
        bad["steps"] = ["Select it.", "y" * 121]
        bad["what"] = "One. Two. Three. Four."
        bad["summary"] = "One. Two."
        text = "\n".join(tips.problems("X", bad, check_picture=False))
        self.assertIn("steps 2 has 121 characters", text)
        self.assertIn("what is 4 sentences", text)
        self.assertIn("summary is 2 sentences", text)

    def test_sentences_do_not_count_decimals_or_eg(self):
        self.assertEqual(tips._sentences("Set 0.5 mm, e.g. for a lip."), 1)
        self.assertEqual(tips._sentences("Pick a face. Drag the arrow!"), 2)

    def test_pictures_wrong_size_too_big_or_missing(self):
        with tempfile.TemporaryDirectory() as folder:
            old = tips.PICTURE_DIR
            tips.PICTURE_DIR = folder
            try:
                with open(os.path.join(folder, "small.png"), "wb") as handle:
                    handle.write(_png(160, 100))
                with open(os.path.join(folder, "big.png"), "wb") as handle:
                    handle.write(_png(320, 200, extra=tips.PICTURE_BYTES))
                entry = dict(GOOD, picture="small.png")
                self.assertIn("is 160x100 (320x200)", "\n".join(tips.problems("X", entry)))
                entry = dict(GOOD, picture="big.png")
                self.assertIn("bytes (at most", "\n".join(tips.problems("X", entry)))
                entry = dict(GOOD, picture="none.png")
                self.assertIn("is missing", "\n".join(tips.problems("X", entry)))
                entry = dict(GOOD, picture="../x.png")
                self.assertIn("plain .png file name", "\n".join(tips.problems("X", entry)))
            finally:
                tips.PICTURE_DIR = old

    def test_picture_info_reads_the_header(self):
        with tempfile.TemporaryDirectory() as folder:
            path = os.path.join(folder, "a.png")
            with open(path, "wb") as handle:
                handle.write(_png(320, 200))
            width, height, size = tips.picture_info(path)
            self.assertEqual((width, height), (320, 200))
            self.assertGreater(size, 50)
            with open(path, "wb") as handle:
                handle.write(b"not a png at all, sorry")
            self.assertIsNone(tips.picture_info(path))
            self.assertIsNone(tips.picture_info(os.path.join(folder, "missing.png")))

    def test_get_gives_a_copy_with_the_picture_path(self):
        saved = dict(tips._STATE)
        try:
            tips._STATE.update(tips={"Fission180_Fillet": dict(GOOD)}, errors=[], owners={})
            tip = tips.get("Fission180_Fillet")
            self.assertEqual(tip["summary"], GOOD["summary"])
            tip["summary"] = "changed"
            self.assertEqual(tips.get("Fission180_Fillet")["summary"], GOOD["summary"])
            self.assertIn("picture_path", tip)
            self.assertIsNone(tips.get("Fission180_Nothing"))
            entry = {"label": "Fillet", "command": "Fission180_Fillet"}
            self.assertEqual(tips.for_entry(entry)["what"], GOOD["what"])
            self.assertIn("Fission180_Fillet", tips.all())
        finally:
            tips._STATE.clear()
            tips._STATE.update(saved)

    def test_a_broken_module_is_reported_not_raised(self):
        folder = os.path.dirname(tips.__file__)
        name = "zz_broken_for_test"
        path = os.path.join(folder, name + ".py")
        saved_modules = tips.MODULES
        try:
            with open(path, "w", encoding="utf-8") as handle:
                handle.write("TIPS = {\n")  # a syntax error
            tips.MODULES = (name,)
            tips.reload()
            self.assertEqual(tips.all(), {})
            self.assertIn("did not load", " ".join(tips.load_errors()))
        finally:
            tips.MODULES = saved_modules
            os.remove(path)
            tips.reload()


class Placement(unittest.TestCase):
    """Where the card goes (tips_ui uses tips.place) and how it writes steps and hints."""

    SCREEN = (0, 0, 1920, 1200)

    def test_under_a_ribbon_button(self):
        self.assertEqual(tips.place((600, 80, 48, 48), (300, 60), self.SCREEN), (600, 132))

    def test_above_when_no_room_below(self):
        x, y = tips.place((600, 1150, 48, 48), (340, 400), self.SCREEN)
        self.assertEqual(y, 1150 - 4 - 400)

    def test_kept_inside_the_right_edge(self):
        x, _y = tips.place((1880, 80, 48, 48), (340, 400), self.SCREEN)
        self.assertEqual(x, 1920 - 340)

    def test_beside_a_menu_then_left_of_it(self):
        menu_row = (100, 300, 220, 24)
        self.assertEqual(tips.place(menu_row, (340, 400), self.SCREEN, beside=True), (324, 300))
        right_menu = (1700, 300, 200, 24)
        x, _y = tips.place(right_menu, (340, 400), self.SCREEN, beside=True)
        self.assertEqual(x, 1700 - 4 - 340)  # the menu stays uncovered

    def test_beside_low_in_the_screen_moves_up(self):
        _x, y = tips.place((100, 1100, 220, 24), (340, 400), self.SCREEN, beside=True)
        self.assertEqual(y, 1200 - 400)

    def test_a_second_screen(self):
        screen = (1920, 0, 1280, 1024)
        x, y = tips.place((3150, 80, 48, 48), (340, 400), screen)
        self.assertEqual((x, y), (1920 + 1280 - 340, 132))

    def test_numbered_steps_and_hints(self):
        self.assertEqual(tips.numbered(["Pick.", "Drag."]), "1. Pick.\n2. Drag.")
        self.assertEqual(tips.numbered([]), "")
        self.assertEqual(tips.bulleted(["Hold Ctrl."]), "• Hold Ctrl.")


class Coverage(unittest.TestCase):
    """Every ribbon command of a data module's tabs has a complete entry and its picture."""

    def check_module(self, module):
        have = written()
        commands = [c for c in tips.ribbon_commands() if c[3] == module]
        if not have:
            self.skipTest(
                "no tooltip data written yet; %d commands of tips/%s.py wait"
                % (len(commands), module)
            )
        report = tips.report()
        lines = []
        if module not in have:
            lines.append("tips/%s.py is not written yet" % module)
        missing = [c for c in report["missing"] if c[3] == module]
        if missing:
            lines.append(
                "%d of %d commands have no tooltip: %s"
                % (
                    len(missing),
                    len(commands),
                    ", ".join("%s (%s)" % (c[0], c[1]) for c in missing),
                )
            )
        ids = {c[0] for c in commands}
        lines += [p for p in report["problems"] if p.split(":")[0] in ids]
        lines += [
            "%s is in tips/%s.py, it belongs in tips/%s.py" % m
            for m in report["misplaced"]
            if m[2] == module
        ]
        own_unknown = [i for i in report["unknown"] if tips.owner(i) == module]
        if own_unknown:
            lines.append("entries no ribbon command has: %s" % ", ".join(own_unknown))
        lines += [e for e in report["errors"] if "tips/%s.py" % module in e]
        if IN_SOURCE_TREE and module in have:
            script = os.path.join(TOOLS, "tip_pictures_%s.py" % module)
            if not os.path.isfile(script):
                lines.append("no picture script tools/fission180/tip_pictures_%s.py" % module)
        self.assertEqual(lines, [], "\n".join(lines))


def _module_test(module):
    def test(self):
        self.check_module(module)

    test.__name__ = "test_module_" + module
    return test


for _module in tips.MODULES:
    setattr(Coverage, "test_module_" + _module, _module_test(_module))


class Folder(unittest.TestCase):
    def test_every_picture_is_used(self):
        if not written():
            self.skipTest("no tooltip data written yet")
        folder = tips.PICTURE_DIR
        files = (
            sorted(f for f in os.listdir(folder) if f.endswith(".png"))
            if os.path.isdir(folder)
            else []
        )
        used = {tip.get("picture") for tip in tips.all().values()}
        unused = [f for f in files if f not in used]
        self.assertEqual(unused, [], "pictures no tooltip shows: %s" % ", ".join(unused))

    def test_no_entry_twice(self):
        twice = [e for e in tips.load_errors() if "has entries in" in e]
        self.assertEqual(twice, [], "\n".join(twice))


def _helpers():
    path = os.path.join(TOOLS, "tip_pictures.py")
    spec = importlib.util.spec_from_file_location("tip_pictures_for_test", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@unittest.skipUnless(IN_SOURCE_TREE, "tools/fission180 is not here (an installed copy)")
class PictureHelpers(unittest.TestCase):
    """The pure parts of tools/fission180/tip_pictures.py (framing, layout, saving)."""

    @classmethod
    def setUpClass(cls):
        try:
            import PIL  # noqa: F401
        except ImportError:
            raise unittest.SkipTest("Pillow is not installed")
        cls.tp = _helpers()

    def shot(self, box, color=(200, 200, 200)):
        from PIL import Image, ImageDraw

        images = {}
        for width in self.tp.LEVELS:
            height = int(round(width / self.tp.ASPECT))
            image = Image.new("RGB", (width, height), self.tp.BACKGROUND)
            ImageDraw.Draw(image).rectangle(
                (box[0] * width, box[1] * height, box[2] * width, box[3] * height), fill=color
            )
            images[width] = image
        return self.tp.Shot(images, box, [])

    def test_crop_box_has_the_pictures_shape(self):
        x, y, w, h = self.tp._crop_box((0.25, 0.25, 0.75, 0.75), (320, 200), 0.1)
        self.assertAlmostEqual(w / h, 1.6, places=6)
        x, y, w, h = self.tp._crop_box((0.4, 0.1, 0.6, 0.9), (145, 200), 0.1)
        self.assertAlmostEqual(w / h, 145 / 200.0, places=6)

    def test_finish_and_before_after_are_320_by_200(self):
        a = self.shot((0.3, 0.3, 0.6, 0.7))
        b = self.shot((0.3, 0.3, 0.7, 0.7), color=(59, 91, 219))
        self.assertEqual(self.tp.finish(a).size, (320, 200))
        pair = self.tp.before_after(a, b)
        self.assertEqual(pair.size, (320, 200))
        # the arrow in the middle is the accent blue
        middle = pair.getpixel((160, 100))
        self.assertEqual(middle, self.tp.ACCENT)
        self.assertEqual(self.tp.side_by_side([a, b, a], ["Join", "Cut", "New"]).size, (320, 200))

    def test_one_scale_for_before_and_after(self):
        # the smaller "before" keeps its size next to the larger "after"
        small = self.shot((0.45, 0.45, 0.55, 0.55))
        large = self.shot((0.2, 0.2, 0.8, 0.8))
        pair = self.tp.before_after(small, large, labels=None)

        def lit(area):
            return (
                pair.crop(area).convert("L").point(lambda v: 255 if v > 150 else 0).histogram()[255]
            )

        self.assertLess(lit((0, 0, 145, 200)) * 10, lit((175, 0, 320, 200)))

    def test_encode_keeps_pictures_small(self):
        import random

        from PIL import Image

        rng = random.Random(4)
        image = Image.new("RGB", (320, 200))
        image.putdata(
            [(rng.randrange(256), rng.randrange(256), rng.randrange(256)) for _ in range(64000)]
        )
        data = self.tp.encode(image)
        self.assertEqual(Image.open(io.BytesIO(data)).size, (320, 200))
        with self.assertRaises(ValueError):
            self.tp.encode(Image.new("RGB", (100, 100)))
        flat = self.tp.encode(Image.new("RGB", (320, 200), self.tp.BACKGROUND))
        self.assertLess(len(flat), tips.PICTURE_BYTES)

    def test_dialog_picture_fits(self):
        from PIL import Image

        tall = Image.new("RGB", (300, 900), (59, 68, 83))
        self.assertEqual(self.tp.dialog_picture(tall).size, (320, 200))
        wide = Image.new("RGB", (900, 120), (59, 68, 83))
        self.assertEqual(self.tp.dialog_picture(wide).size, (320, 200))

    def test_picture_names(self):
        with self.assertRaises(ValueError):
            self.tp.picture("fillet")
        with self.assertRaises(ValueError):
            self.tp.picture("a/b.png")


if __name__ == "__main__":
    unittest.main()
