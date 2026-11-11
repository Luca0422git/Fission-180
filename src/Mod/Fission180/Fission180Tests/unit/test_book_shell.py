# SPDX-License-Identifier: LGPL-2.1-or-later
"""Wave 7, shell: the pure logic behind the book parity report's shell items (names on
buttons, the search listing a command once, the Data Panel's folders, the layout grid's
numbers, dialogs kept on the screen, USDZ). Runs without FreeCAD."""

import os
import shutil
import sys
import tempfile
import unittest
import zipfile

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fission180 import browser_core  # noqa: E402
from fission180 import data_panel_core as dp  # noqa: E402
from fission180 import export_usd as usd  # noqa: E402
from fission180 import nav_core  # noqa: E402
from fission180 import search_core  # noqa: E402
from fission180 import shown_names  # noqa: E402


def measure(text):
    return 7 * len(text)  # (a font of 7 pixels a letter)


class NamesTest(unittest.TestCase):
    def test_ampersand_stays(self):
        self.assertEqual(shown_names.shown_name("Housing & Inlet Tube"), "Housing && Inlet Tube")
        self.assertEqual(shown_names.shown_name("Body"), "Body")

    def test_short_list_as_it_is(self):
        self.assertEqual(shown_names.fit_names("Arm, Base", 200, measure), "Arm, Base")

    def test_long_list_counts_the_rest(self):
        names = ", ".join("Component %d" % i for i in range(1, 8))
        short = shown_names.fit_names(names, 250, measure)
        self.assertLessEqual(measure(short), 250)
        self.assertTrue(short.startswith("Component 1"))
        self.assertTrue(short.endswith("more"), short)
        shown = short.split(" + ")[0].split(", ")
        self.assertEqual(int(short.split(" + ")[1].split()[0]), 7 - len(shown))

    def test_one_long_name_is_cut(self):
        short = shown_names.fit_names("A" * 100, 70, measure)
        self.assertLessEqual(measure(short), 70)
        self.assertTrue(short.endswith("…"))

    def test_long_first_name_of_many(self):
        short = shown_names.fit_names("A" * 100 + ", B, C", 140, measure)
        self.assertLessEqual(measure(short), 140)
        self.assertTrue(short.endswith("+ 2 more"), short)


class SearchOnceTest(unittest.TestCase):
    def test_a_menu_entry_hides_its_command(self):
        entries = [
            {"name": "Fission180_ChangeParameters", "text": "Change Parameters", "ribbon": True},
            {"name": "Fission180_ChangeParameters", "text": "Change Parameters", "shortcut": ""},
            {"name": "Std_Parameters", "text": "Edit parameters", "shortcut": ""},
        ]
        found = search_core.rank("change parameters", entries)
        self.assertEqual([e["text"] for e in found].count("Change Parameters"), 1)
        self.assertTrue(found[0].get("ribbon"))

    def test_the_same_words_twice_are_one_row(self):
        entries = [
            {"name": "Fission180_Fillet", "text": "Fillet", "ribbon": True, "shortcut": "F"},
            {"name": "PartDesign_Fillet", "text": "Fillet", "shortcut": "F"},
            {"name": "Part_Fillet", "text": "Fillet", "shortcut": ""},
        ]
        found = search_core.rank("fillet", entries)
        self.assertEqual([e["name"] for e in found], ["Fission180_Fillet", "Part_Fillet"])

    def test_two_labels_of_one_command_both_stay(self):
        entries = [
            {"name": "Fission180_Extrude", "text": "Extrude", "ribbon": True},
            {"name": "Fission180_Extrude", "text": "Extrude (Cut)", "ribbon": True},
        ]
        self.assertEqual(len(search_core.rank("extrude", entries)), 2)

    def test_empty_query_lists_once_too(self):
        entries = [
            {"name": "A", "text": "Alpha", "ribbon": True},
            {"name": "A", "text": "Alpha"},
        ]
        self.assertEqual(len(search_core.rank("", entries)), 1)


class BrowserWhileCommandTest(unittest.TestCase):
    def test_only_the_safe_entries(self):
        kept = browser_core.while_command(list(browser_core.MENUS["body"]))
        self.assertIn("Show/Hide", kept)
        self.assertIn("Find in Window", kept)
        for gone in ("Rename", "Delete", "Remove", "Copy", "Activate Body", "Save As Mesh"):
            self.assertNotIn(gone, kept)
        self.assertNotEqual(kept[0], "-")
        self.assertNotEqual(kept[-1], "-")
        self.assertNotIn(("-", "-"), list(zip(kept, kept[1:])))

    def test_a_row_without_safe_entries_has_no_menu(self):
        self.assertEqual(browser_core.while_command(["Rename", "-", "Delete"]), [])


class GridNumbersTest(unittest.TestCase):
    def test_every_major_line_but_the_origin(self):
        self.assertEqual(nav_core.grid_numbers(-25, 25, 10), [-20, -10, 10, 20])

    def test_thinned_when_many(self):
        values = nav_core.grid_numbers(-1000, 1000, 10, limit=40)
        self.assertLessEqual(len(values), 41)
        self.assertNotIn(0, values)
        self.assertIn(50, values)
        self.assertNotIn(10, values)

    def test_text(self):
        self.assertEqual(nav_core.number_text(50.0), "50")
        self.assertEqual(nav_core.number_text(-2.5), "-2.5")
        self.assertEqual(nav_core.number_text(-0.0), "0")

    def test_major_lines_alone_when_zoomed_far_out(self):
        majors, minors = nav_core.grid_lines((0, 0), 5000, 10, 5)
        self.assertTrue(majors)  # (the whole grid was dropped)
        self.assertEqual(minors, [])


class DialogFitTest(unittest.TestCase):
    def setUp(self):
        # dialog_fit imports FreeCADGui at the top: only its pure function is read here
        import importlib.util

        path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "fission180",
            "dialog_fit.py",
        )
        with open(path, encoding="utf-8") as handle:
            source = handle.read()
        start = source.index("def fitted(")
        end = source.index("def _limit(")
        scope = {}
        exec(source[start:end], scope)
        self.fitted = scope["fitted"]
        del importlib

    def test_inside_stays(self):
        self.assertEqual(self.fitted((100, 100, 400, 300), (0, 0, 1920, 1080)), (100, 100, 400, 300))

    def test_off_the_right_edge_comes_back(self):
        self.assertEqual(self.fitted((1800, 100, 400, 300), (0, 0, 1920, 1080)), (1520, 100, 400, 300))

    def test_too_wide_is_narrowed(self):
        self.assertEqual(self.fitted((0, 0, 2400, 300), (0, 0, 1920, 1080)), (0, 0, 1920, 300))

    def test_too_tall_and_above_the_screen(self):
        self.assertEqual(self.fitted((10, -50, 400, 1500), (0, 0, 1920, 1080)), (10, 0, 400, 1080))

    def test_second_screen(self):
        got = self.fitted((1900, 20, 400, 300), (1920, 0, 1280, 1024))
        self.assertEqual(got, (1920, 20, 400, 300))


class DataPanelFoldersTest(unittest.TestCase):
    def setUp(self):
        self.root = tempfile.mkdtemp(prefix="fission180-dp-")

    def tearDown(self):
        shutil.rmtree(self.root, ignore_errors=True)

    def make(self, *parts, text=None):
        path = os.path.join(self.root, *parts)
        if text is None:
            os.makedirs(path, exist_ok=True)
        else:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w") as handle:
                handle.write(text)
        return path

    def test_project_is_a_top_folder(self):
        book = self.make("Book")
        chapter = self.make("Book", "1 - Fundamentals")
        self.assertTrue(dp.is_project(self.root, book))
        self.assertFalse(dp.is_project(self.root, chapter))

    def test_name_refusals(self):
        self.make("Taken")
        self.assertEqual(dp.name_refusal(self.root, "Fresh"), "")
        self.assertIn("Type a name", dp.name_refusal(self.root, "  "))
        self.assertIn("there already", dp.name_refusal(self.root, "Taken"))
        self.assertIn("cannot hold", dp.name_refusal(self.root, "a/b"))
        self.assertEqual(dp.name_refusal(self.root, "Taken", old="Taken"), "")
        self.assertEqual(dp.name_refusal(self.root, "taken", old="Taken"), "")  # a new case
        self.assertEqual(dp.name_refusal(self.root, "Two  Spaces"), "")

    def test_a_folder_never_goes_into_itself(self):
        a = self.make("A")
        inner = self.make("A", "Inner")
        b = self.make("B")
        self.assertIn("itself", dp.folder_refusal(a, a))
        self.assertIn("itself", dp.folder_refusal(a, inner))
        self.assertIn("already", dp.folder_refusal(inner, a))
        self.assertEqual(dp.folder_refusal(a, b), "")
        self.make("B", "A")
        self.assertIn("already in B", dp.folder_refusal(a, b))
        self.assertEqual(dp.folder_refusal(a, b, "copy"), "")  # (a copy gets a new name)

    def test_tree_plan(self):
        a = self.make("A")
        self.make("A", "Gear.FCStd", text="design")
        self.make("A", "Gear.versions", "v0001.FCStd", text="old")
        self.make("A", "Inner", "notes.txt", text="n")
        self.make("A", "Inner", "Pin.FCStd", text="design")
        self.make("A", ".fission180-trash", "Old.FCStd", text="gone")
        b = self.make("B")
        plan = dp.tree_plan(a, b)
        new = os.path.join(b, "A")
        self.assertEqual(plan["root"], new)
        self.assertEqual(plan["folders"], [new, os.path.join(new, "Inner")])
        self.assertEqual(
            sorted(plan["designs"]),
            sorted(
                [
                    (os.path.join(a, "Gear.FCStd"), new),
                    (os.path.join(a, "Inner", "Pin.FCStd"), os.path.join(new, "Inner")),
                ]
            ),
        )
        self.assertEqual(
            plan["files"],
            [(os.path.join(a, "Inner", "notes.txt"), os.path.join(new, "Inner", "notes.txt"))],
        )
        self.assertEqual(dp.tree_plan(a, b, "A 2")["root"], os.path.join(b, "A 2"))
        self.assertEqual(len(dp.designs_under(a)), 2)

    def test_crumbs_fit(self):
        labels = ["Project", "Mastering Autodesk Fusion Edt. 2", "1 - Fundamentals", "Parts"]
        self.assertEqual(dp.fit_crumbs(labels, 2000, measure), [0, 1, 2, 3])
        self.assertEqual(dp.fit_crumbs(labels, 300, measure), [0, None, 2, 3])
        self.assertEqual(dp.fit_crumbs(labels, 150, measure), [0, None, 3])
        self.assertEqual(dp.fit_crumbs(labels, 60, measure), [None, 3])
        self.assertEqual(dp.fit_crumbs(["Project"], 10, measure), [0])

    def test_remembered_folder(self):
        inner = self.make("Book", "1")
        self.assertEqual(dp.remembered_folder(self.root, inner), inner)
        self.assertEqual(dp.remembered_folder(self.root, ""), os.path.abspath(self.root))
        self.assertEqual(
            dp.remembered_folder(self.root, os.path.join(self.root, "Gone")),
            os.path.abspath(self.root),
        )
        elsewhere = tempfile.mkdtemp(prefix="fission180-else-")
        try:
            self.assertEqual(dp.remembered_folder(self.root, elsewhere), os.path.abspath(self.root))
        finally:
            shutil.rmtree(elsewhere, ignore_errors=True)


CUBE_POINTS = [
    (0, 0, 0),
    (10, 0, 0),
    (10, 20, 0),
    (0, 20, 0),
    (0, 0, 30),
    (10, 0, 30),
    (10, 20, 30),
    (0, 20, 30),
]
CUBE_TRIANGLES = [
    (0, 2, 1),
    (0, 3, 2),
    (4, 5, 6),
    (4, 6, 7),
    (0, 1, 5),
    (0, 5, 4),
    (1, 2, 6),
    (1, 6, 5),
    (2, 3, 7),
    (2, 7, 6),
    (3, 0, 4),
    (3, 4, 7),
]


class UsdzTest(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp(prefix="fission180-usdz-")
        self.path = os.path.join(self.folder, "Saturn V.usdz")

    def tearDown(self):
        shutil.rmtree(self.folder, ignore_errors=True)

    def parts(self):
        return [
            {
                "name": "Housing & Inlet Tube",
                "points": CUBE_POINTS,
                "triangles": CUBE_TRIANGLES,
                "color": (1.0, 0.435, 0.71),
            },
            {
                "name": "2 Body",
                "points": [(x + 20, y, z) for x, y, z in CUBE_POINTS],
                "triangles": CUBE_TRIANGLES,
                "color": (0.2, 0.4, 0.9),
                "opacity": 0.5,
            },
        ]

    def test_written_and_read_back(self):
        count = usd.write_usdz(self.path, self.parts(), "Saturn V")
        self.assertEqual(count, 24)
        info = usd.read_usdz(self.path)
        self.assertEqual(info["files"], ["design.usda"])
        self.assertTrue(info["stored"])
        self.assertTrue(info["aligned"])
        self.assertEqual(info["meters_per_unit"], 1.0)
        self.assertEqual(info["up"], "Y")
        self.assertEqual([m["name"] for m in info["meshes"]], ["Housing & Inlet Tube", "2 Body"])
        first, second = info["meshes"]
        self.assertEqual((first["points"], first["triangles"]), (8, 12))
        # 10 x 20 x 30 mm, Z up -> 0.01 x 0.03 x 0.02 m, Y up
        lo, hi = first["extent"]
        self.assertEqual([round(h - l, 6) for l, h in zip(lo, hi)], [0.01, 0.03, 0.02])
        self.assertEqual(first["color"], (1.0, 0.435, 0.71))
        self.assertNotEqual(first["look"], second["look"])
        self.assertEqual(info["looks"][second["look"]]["opacity"], 0.5)
        self.assertEqual(info["looks"][first["look"]]["opacity"], 1.0)

    def test_any_zip_reader_takes_it(self):
        usd.write_usdz(self.path, self.parts(), "Saturn V")
        with zipfile.ZipFile(self.path) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(archive.namelist(), ["design.usda"])
            info = archive.getinfo("design.usda")
            self.assertEqual(info.compress_type, zipfile.ZIP_STORED)
            text = archive.read("design.usda").decode("utf-8")
        self.assertTrue(text.startswith("#usda 1.0"))
        self.assertIn('defaultPrim = "Saturn_V"', text)
        self.assertIn("UsdPreviewSurface", text)

    def test_every_file_starts_at_a_multiple_of_64(self):
        data = usd.pack_usdz([("a.usda", b"#usda 1.0\n"), ("textures/long name.png", b"x" * 77)])
        entries = usd._entries(data)
        self.assertEqual([e[0] for e in entries], ["a.usda", "textures/long name.png"])
        self.assertTrue(all(e[2] % 64 == 0 for e in entries), entries)

    def test_prim_names(self):
        used = set()
        self.assertEqual(usd.prim_name("Body 1", used), "Body_1")
        self.assertEqual(usd.prim_name("Body-1", used), "Body_1_2")
        self.assertEqual(usd.prim_name("2 Body", used), "_2_Body")
        self.assertEqual(usd.prim_name("&&&", used), "Body")

    def test_same_colour_shares_a_look(self):
        parts = self.parts()
        parts[1]["color"] = parts[0]["color"]
        parts[1].pop("opacity")
        usd.write_usdz(self.path, parts, "Two")
        info = usd.read_usdz(self.path)
        self.assertEqual(len(info["looks"]), 1)

    def test_nothing_to_write_is_refused(self):
        with self.assertRaises(usd.UsdError):
            usd.write_usdz(self.path, [{"name": "Empty", "points": [], "triangles": []}])
        self.assertFalse(os.path.exists(self.path))

    def test_a_bad_triangle_is_refused(self):
        with self.assertRaises(usd.UsdError):
            usd.usda_text([{"name": "B", "points": CUBE_POINTS, "triangles": [(0, 1, 99)]}])

    def test_not_a_usdz(self):
        other = os.path.join(self.folder, "plain.usdz")
        with open(other, "wb") as handle:
            handle.write(b"not a zip")
        with self.assertRaises(usd.UsdError):
            usd.read_usdz(other)


if __name__ == "__main__":
    unittest.main()
