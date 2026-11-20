# SPDX-License-Identifier: LGPL-2.1-or-later
"""neon_scene_core (plan task B7): the 3D colours of Neon Lights, and the Live colour constants
that keep their exact Dark value outside it. Runs with a fake FreeCAD (no window)."""

import os
import sys
import types
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.dirname(__file__))
from test_smoke_fake_freecad import FakeParams  # noqa: E402


class _Console:
    def PrintMessage(self, text):
        pass

    PrintWarning = PrintError = PrintLog = PrintMessage


class NeonSceneCore(unittest.TestCase):
    def setUp(self):
        self.groups = {}
        fake = types.ModuleType("FreeCAD")
        fake.ParamGet = lambda path: self.groups.setdefault(path, FakeParams())
        fake.Console = _Console()
        self._saved = sys.modules.get("FreeCAD")
        sys.modules["FreeCAD"] = fake
        from fission180 import neon_palette, neon_scene_core, theme

        self.theme, self.core, self.np = theme, neon_scene_core, neon_palette
        theme._use("dark")

    def tearDown(self):
        self.theme.normal_look(False)
        self.theme._use("dark")
        if self._saved is None:
            sys.modules.pop("FreeCAD", None)
        else:
            sys.modules["FreeCAD"] = self._saved

    def test_live_is_its_dark_value_outside_neon(self):
        blue = self.core.Live((0.16, 0.50, 0.93), "arrow")
        for look in ("dark", "light"):
            self.theme._use(look)
            self.assertEqual(blue, (0.16, 0.50, 0.93))
            self.assertEqual(tuple(blue), (0.16, 0.50, 0.93))
            self.assertEqual(list(blue), [0.16, 0.50, 0.93])
            self.assertEqual(blue[0], 0.16)
            r, g, b = blue
            self.assertEqual((r, g, b), (0.16, 0.50, 0.93))
            self.assertEqual((lambda *a: a)(*blue), (0.16, 0.50, 0.93))
            self.assertEqual(repr(blue), "(0.16, 0.5, 0.93)")
            self.assertEqual(hash(blue), hash((0.16, 0.50, 0.93)))

    def test_live_reads_neon_in_neon(self):
        blue = self.core.Live((0.16, 0.50, 0.93), "arrow")
        self.theme._use("neon")
        want = self.np.rgb01(self.theme.palette()["arrow"])
        self.assertEqual(tuple(blue), want)
        self.assertEqual((lambda *a: a)(*blue), want)
        self.assertEqual(blue[2], want[2])
        # equality and repr stay the Dark value (tables keyed by colour keep working)
        self.assertEqual(blue, (0.16, 0.50, 0.93))
        self.assertEqual(blue.normal(), (0.16, 0.50, 0.93))
        # a saved preview picture is drawn in the normal colours
        self.theme.normal_look(True)
        self.assertEqual(tuple(blue), (0.16, 0.50, 0.93))
        self.theme.normal_look(False)
        self.theme._use("dark")
        self.assertEqual(tuple(blue), (0.16, 0.50, 0.93))

    def test_every_role_exists_for_every_preset(self):
        for key in self.np.ORDER:
            p = self.np.derive(self.np.roles(key))
            roles = self.core.roles3d(p)
            for role in list(self.core._RECIPES) + ["axis_x", "axis_y", "axis_z", "select"]:
                self.assertIn(role, roles, (key, role))
                self.assertEqual(len(roles[role]), 3)
                self.assertTrue(all(0.0 <= c <= 1.0 for c in roles[role]))

    def test_background_is_a_faint_dark_gradient(self):
        for key in self.np.ORDER:
            p = self.np.derive(self.np.roles(key))
            top, bottom = self.core.background(p)
            self.assertNotEqual(top, bottom)
            for colour in (top, bottom):
                self.assertLess(self.np._luminance(colour), 0.05, (key, colour))

    def test_sketch_colours_cover_the_light_table_and_stay_apart(self):
        try:
            from fission180 import sketch_mode
        except ImportError:
            self.skipTest("needs FreeCAD (run_tests.sh --only unit)")
        p = self.np.derive(self.np.roles("v"))
        neon = self.core.sketch(p)
        names = {name for _g, _k, name, _v in sketch_mode.PARAMS}
        self.assertTrue(set(sketch_mode.LIGHT) <= set(neon))
        self.assertTrue(set(neon) <= names, set(neon) - names)
        for key in self.np.ORDER:
            n = self.core.sketch(self.np.derive(self.np.roles(key)))
            # under-constrained, fully constrained, selected and hovered differ
            values = [n[k] for k in ("EditedEdgeColor", "FullyConstrainedColor", "SelectionColor", "HighlightColor")]
            self.assertEqual(len(set(values)), 4, key)

    def test_unknown_role_keeps_the_value(self):
        self.theme._use("neon")
        odd = self.core.Live((0.1, 0.2, 0.3), "no_such_role")
        self.assertEqual(tuple(odd), (0.1, 0.2, 0.3))
        self.assertEqual(self.core.shade((0.1, 0.2, 0.3), "no_such_role"), (0.1, 0.2, 0.3))


if __name__ == "__main__":
    unittest.main()
