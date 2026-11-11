# SPDX-License-Identifier: LGPL-2.1-or-later
"""INSERT > Insert Catalogue Part... without Qt or FreeCAD (fission180/hardware_catalog.py):
the supplier list, the address a part number makes, the newest downloaded STEP file; and the
golden models' list of hardware standards kept like the library's."""

import os
import sys
import tempfile
import time
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fission180 import hardware_catalog as cat  # noqa: E402
from fission180 import hardware_core as core  # noqa: E402


class SupplierTests(unittest.TestCase):
    def test_defaults(self):
        rows = cat.load_suppliers("")
        self.assertEqual([name for name, _a in rows], ["McMaster-Carr", "MISUMI", "TraceParts"])
        self.assertTrue(all(a.startswith("https://") for _n, a in rows))
        self.assertEqual(cat.load_suppliers("not json"), list(cat.DEFAULT_SUPPLIERS))
        self.assertEqual(cat.load_suppliers("[]"), list(cat.DEFAULT_SUPPLIERS))

    def test_saved_list_round_trip(self):
        rows = [("My Shop", "example.org/find?q={}"), ("Other", "https://other.example/")]
        text = cat.dump_suppliers(rows)
        self.assertEqual(
            cat.load_suppliers(text),
            [("My Shop", "https://example.org/find?q={}"), ("Other", "https://other.example/")],
        )

    def test_unusable_rows_are_dropped(self):
        rows = [("", "https://a.example"), ("A", "ftp://a.example"), ("B", ""), ("C", "c.example")]
        rows += [("c", "https://again.example"), ("D",), "junk"]
        self.assertEqual(cat.clean_suppliers(rows), [("C", "https://c.example")])

    def test_only_web_addresses(self):
        self.assertEqual(cat.clean_address(" mcmaster.com "), "https://mcmaster.com")
        self.assertEqual(cat.clean_address("http://a.example/x"), "http://a.example/x")
        for bad in ("", "file:///etc/passwd", "javascript://x", "https://a b.example"):
            with self.assertRaises(cat.CatalogueError):
                cat.clean_address(bad)

    def test_address_for_a_part_number(self):
        mcmaster = "https://www.mcmaster.com/{}"
        self.assertEqual(cat.address_for(mcmaster, "91390A098"), "https://www.mcmaster.com/91390A098")
        self.assertEqual(cat.address_for(mcmaster, ""), "https://www.mcmaster.com/")
        search = "https://shop.example/result/?Keyword={}"
        self.assertEqual(
            cat.address_for(search, "m3 set screw"),
            "https://shop.example/result/?Keyword=m3%20set%20screw",
        )
        self.assertEqual(cat.address_for(search, "  "), "https://shop.example/result/")
        self.assertEqual(cat.address_for("plain.example", "ignored"), "https://plain.example")
        self.assertEqual(cat.address_for(mcmaster, "a/b?c"), "https://www.mcmaster.com/a%2Fb%3Fc")

    def test_the_one_line(self):
        self.assertIn("supplier's own website", cat.INFO)
        self.assertNotIn("\n", cat.INFO)


class DownloadTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.mkdtemp()

    def write(self, name, age=0.0, text="ISO-10303-21;"):
        path = os.path.join(self.folder, name)
        with open(path, "w") as handle:
            handle.write(text)
        then = time.time() - age
        os.utime(path, (then, then))
        return path

    def test_newest_first_and_only_cad_files(self):
        old = self.write("old.step", age=3600)
        new = self.write("NEW PART.STP", age=5)
        iges = self.write("mid.igs", age=600)
        self.write("notes.txt")
        self.write("half.step.crdownload")
        self.write("empty.step", text="")
        found = [p for p, _t in cat.downloaded_files(self.folder)]
        self.assertEqual(found, [new, iges, old])
        self.assertEqual(len(cat.downloaded_files(self.folder, limit=2)), 2)

    def test_no_folder(self):
        self.assertEqual(cat.downloaded_files(os.path.join(self.folder, "missing")), [])

    def test_which_folder(self):
        other = tempfile.mkdtemp()
        self.assertEqual(
            cat.downloads_folder({"FISSION180_DOWNLOADS": self.folder}, other, other), self.folder
        )
        self.assertEqual(cat.downloads_folder({}, other, self.folder), other)
        self.assertEqual(cat.downloads_folder({}, "", self.folder), self.folder)
        self.assertEqual(cat.downloads_folder({}, "/no/such/folder", self.folder), self.folder)
        self.assertTrue(cat.downloads_folder({}, "", "").endswith("Downloads"))

    def test_age(self):
        self.assertEqual(cat.age_text(3), "just now")
        self.assertEqual(cat.age_text(300), "5 min ago")
        self.assertEqual(cat.age_text(3 * 3600), "3 h ago")
        self.assertEqual(cat.age_text(3 * 86400), "3 days ago")
        self.assertEqual(cat.file_label("/x/part.step", 100.0, 400.0), "part.step  (5 min ago)")


class GoldenListTests(unittest.TestCase):
    def test_golden_models_know_every_standard(self):
        from Fission180Tests.golden import hardware_schema

        self.assertEqual(tuple(hardware_schema.CHOICES["standard"]), tuple(core.STANDARD_ORDER))
        self.assertEqual(
            tuple(v for v, _label in core.VARIANTS), tuple(hardware_schema.CHOICES["variant"])
        )


if __name__ == "__main__":
    unittest.main()
