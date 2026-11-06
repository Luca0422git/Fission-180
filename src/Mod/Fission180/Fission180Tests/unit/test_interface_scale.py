# SPDX-License-Identifier: LGPL-2.1-or-later
"""interface_scale: Preferences > General > Appearance > Interface size (Luca, 2026-11-06:
"GUI scale. in the settings ... smaller GUI, bigger build area")."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from fission180 import interface_scale as scale  # noqa: E402
from fission180 import prefs_core  # noqa: E402


class InterfaceSize(unittest.TestCase):
    def test_factor(self):
        self.assertEqual(scale.factor("85"), 0.85)
        self.assertEqual(scale.factor("150"), 1.5)
        self.assertEqual(scale.factor("100"), 1.0)
        self.assertEqual(scale.factor("85 %"), 0.85)

    def test_nonsense_is_the_systems_size(self):
        for value in ("", "abc", None, "5", "900"):
            self.assertEqual(scale.factor(value), 1.0, value)

    def test_environment(self):
        self.assertEqual(scale.environment("75", {}), {"QT_SCALE_FACTOR": "0.75", scale.MINE: "1"})
        self.assertEqual(scale.environment("100", {}), {})
        self.assertEqual(scale.environment("125", {}), {"QT_SCALE_FACTOR": "1.25", scale.MINE: "1"})

    def test_a_scale_fission_180_set_before_is_set_again(self):
        # a Fission 180 restarted by itself (after an update) inherits the old run's variables
        mine = {"QT_SCALE_FACTOR": "0.75", scale.MINE: "1"}
        self.assertEqual(scale.environment("125", mine), {"QT_SCALE_FACTOR": "1.25", scale.MINE: "1"})
        self.assertEqual(scale.environment("100", mine), {"QT_SCALE_FACTOR": None, scale.MINE: None})

    def test_a_scale_set_by_the_person_is_kept(self):
        self.assertEqual(scale.environment("75", {"QT_SCALE_FACTOR": "2"}), {})

    def test_in_preferences(self):
        opt = prefs_core.option("interface_size")
        self.assertEqual(opt["page"], "general")
        self.assertTrue(opt["restart"])
        self.assertEqual(opt["store"], (prefs_core.FISSION180, "String", "InterfaceSize"))
        self.assertIn("100", [c[0] for c in opt["choices"]])
        self.assertEqual(opt["default"], scale.DEFAULT)


if __name__ == "__main__":
    unittest.main()
