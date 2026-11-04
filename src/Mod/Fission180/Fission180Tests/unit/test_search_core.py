import os
import sys
import unittest

# The module root (src/Mod/Fission180) holds the fission180 package.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fission180 import search_core  # noqa: E402

ENTRIES = [
    {"name": "PartDesign_Fillet", "text": "Fillet", "shortcut": ""},
    {"name": "PartDesign_Pad", "text": "Pad", "shortcut": ""},
    {"name": "Sketcher_CreateFillet", "text": "Sketch fillet", "shortcut": ""},
    {"name": "Std_ViewFitAll", "text": "Fit all", "shortcut": ""},
    {"name": "PartDesign_Chamfer", "text": "Chamfer", "shortcut": ""},
]


class SearchTests(unittest.TestCase):
    def names(self, query):
        return [e["name"] for e in search_core.rank(query, ENTRIES)]

    def test_exact_prefix_wins(self):
        self.assertEqual(self.names("fillet")[0], "PartDesign_Fillet")

    def test_subsequence_match(self):
        self.assertIn("PartDesign_Fillet", self.names("flt"))

    def test_all_tokens_must_match(self):
        self.assertEqual(self.names("sketch fillet"), ["Sketcher_CreateFillet"])

    def test_no_match(self):
        self.assertEqual(self.names("zzzz"), [])

    def test_empty_query_is_alphabetical(self):
        texts = [e["text"] for e in search_core.rank("", ENTRIES)]
        self.assertEqual(texts, sorted(texts, key=str.lower))

    def test_the_menu_name_typed_in_full_comes_first(self):
        # Luca, 2026-11-04: "Control Point Spline" ran FreeCAD's pole weight toggle
        entries = [
            {"name": "Sketcher_BSplinePoleWeight", "text": "Toggle B-Spline Control Point Weight", "shortcut": ""},
            {"name": "Sketcher_CreateBSpline", "text": "B-spline by control points", "shortcut": ""},
            {"name": "Sketcher_CreateBSpline", "text": "Control Point Spline", "shortcut": "", "ribbon": True},
        ]
        first = search_core.rank("Control Point Spline", entries)[0]
        self.assertEqual((first["name"], first["text"]), ("Sketcher_CreateBSpline", "Control Point Spline"))
        self.assertEqual(search_core.rank("control point", entries)[0]["text"], "Control Point Spline")

    def test_limit(self):
        self.assertEqual(len(search_core.rank("", ENTRIES, limit=2)), 2)


if __name__ == "__main__":
    unittest.main()
