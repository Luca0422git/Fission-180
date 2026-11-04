# SPDX-License-Identifier: LGPL-2.1-or-later
"""The window title without FreeCAD's version (fission180/window_title.py; Luca, 2026-11-04:
"the top title of Fission 180 shows 1.1.4")."""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from fission180 import window_title as wt  # noqa: E402


class Titles(unittest.TestCase):
    def test_the_bare_title(self):
        self.assertEqual(wt.without_version("Fission 180 1.1.4", "Fission 180 1.1.4", "Fission 180"), "Fission 180")

    def test_with_a_design_open(self):
        self.assertEqual(
            wt.without_version("[*] Bracket - Fission 180 1.1.4", "Fission 180 1.1.4", "Fission 180"),
            "[*] Bracket - Fission 180",
        )

    def test_safe_mode_kept(self):
        self.assertEqual(
            wt.without_version("Fission 180 1.1.4 (Safe Mode)", "Fission 180 1.1.4", "Fission 180"),
            "Fission 180 (Safe Mode)",
        )

    def test_a_title_already_right_or_unknown_is_left(self):
        self.assertEqual(wt.without_version("Fission 180", "Fission 180 1.1.4", "Fission 180"), "Fission 180")
        self.assertEqual(wt.without_version("Something else", "Fission 180 1.1.4", "Fission 180"), "Something else")
        self.assertEqual(wt.without_version("", "Fission 180 1.1.4", "Fission 180"), "")
        self.assertEqual(wt.without_version("Fission 180 1.1.4", "", "Fission 180"), "Fission 180 1.1.4")


class Program(unittest.TestCase):
    def test_only_the_fission180_program(self):
        self.assertTrue(wt.is_own_program("Fission 180", "Fission180"))
        self.assertTrue(wt.is_own_program("", "Fission180"))
        self.assertFalse(wt.is_own_program("FreeCAD", "FreeCAD"))
        self.assertFalse(wt.is_own_program(None, None))


if __name__ == "__main__":
    unittest.main()
