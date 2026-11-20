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


class _WithTheme(unittest.TestCase):
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


class NeonSceneCore(_WithTheme):
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
        want = self.core.coded(self.np.rgb01(self.theme.palette()["arrow"]), blue.code)
        self.assertEqual(tuple(blue), want)
        self.assertEqual((lambda *a: a)(*blue), want)
        self.assertEqual(blue[2], want[2])
        # the code is invisible: the colour on screen (0..255) is the role's
        role = self.np.rgb01(self.theme.palette()["arrow"])
        self.assertEqual([round(c * 255) for c in blue], [round(c * 255) for c in role])
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


class LiveOperations(_WithTheme):
    """What reads the look in use and what reads the stored Dark value (Live's doc)."""

    DARK = (0.16, 0.50, 0.93)

    def _blue(self):
        self.theme._use("neon")
        blue = self.core.Live(self.DARK, "arrow")
        return blue, blue.value()

    def test_these_read_the_look_in_use(self):
        blue, now = self._blue()
        self.assertNotEqual(now, self.DARK)
        self.assertEqual(tuple(blue), now)
        self.assertEqual(list(blue), list(now))
        self.assertEqual(blue[1], now[1])
        self.assertEqual(blue[:2], now[:2])
        self.assertEqual(blue[-1], now[-1])
        r, g, b = blue
        self.assertEqual((r, g, b), now)
        self.assertEqual(max(blue), max(now))
        self.assertEqual(min(blue), min(now))
        self.assertEqual(sum(blue), sum(now))
        self.assertEqual([c * 0.5 for c in blue], [c * 0.5 for c in now])
        self.assertEqual(blue + (1.0,), now + (1.0,))
        self.assertEqual((1.0,) + blue, (1.0,) + now)
        import json

        self.assertEqual(json.loads(json.dumps(blue)), list(now))  # saved values take normal()
        try:
            import numpy
        except ImportError:
            return
        self.assertEqual(tuple(numpy.array(blue)), now)

    def test_these_read_the_stored_dark_value(self):
        import copy
        import pickle

        blue, _now = self._blue()
        self.assertEqual(blue, self.DARK)
        self.assertEqual(hash(blue), hash(self.DARK))
        self.assertEqual(repr(blue), repr(self.DARK))
        self.assertEqual(str(blue), str(self.DARK))
        self.assertEqual(len(blue), 3)
        self.assertIn(0.16, blue)
        self.assertEqual("%s %s %s" % blue, "0.16 0.5 0.93")
        self.assertEqual(copy.copy(blue), self.DARK)
        self.assertIs(type(copy.copy(blue)), tuple)
        self.assertEqual(pickle.loads(pickle.dumps(blue)), self.DARK)
        self.assertIs(type(pickle.loads(pickle.dumps(blue))), tuple)
        self.assertEqual(blue.normal(), self.DARK)


class ColourMap(_WithTheme):
    """neon_scene.sweep's table: what is on screen, from one look to another."""

    def _roles(self, key):
        return self.core.roles3d(self.np.derive(self.np.roles(key)))

    def test_neon_values_of_different_constants_differ(self):
        roles = self._roles("v")
        values = [self.core.key(live.value_in(roles)) for live in self.core.LIVES]
        self.assertEqual(len(values), len(set(values)))

    def test_neon_back_to_dark_is_exact_even_when_roles_share_a_colour(self):
        a = self.core.Live((0.10, 0.20, 0.30), "marker")
        b = self.core.Live((0.40, 0.50, 0.60), "rail")  # marker and rail are both "primary"
        roles = self._roles("v")
        self.assertEqual(roles["marker"], roles["rail"])
        back = self.core.colour_map(roles, None, [a, b])
        self.assertEqual(back[self.core.key(a.value_in(roles))], a.normal())
        self.assertEqual(back[self.core.key(b.value_in(roles))], b.normal())
        # and what handle_look draws from them (shaded body, lit under the mouse, glow)
        for derived_a, derived_dark in zip(self.core._derived(a.value_in(roles)), self.core._derived(a.normal())):
            self.assertEqual(back[self.core.key(derived_a)], derived_dark)

    def test_dark_to_neon_and_preset_to_preset(self):
        a = self.core.Live((0.11, 0.22, 0.33), "arrow")
        v, johnny = self._roles("v"), self._roles("johnny")
        there = self.core.colour_map(None, v, [a])
        self.assertEqual(there[self.core.key(a.normal())], a.value_in(v))
        on = self.core.colour_map(v, johnny, [a])
        self.assertEqual(on[self.core.key(a.value_in(v))], a.value_in(johnny))

    def test_nothing_to_do_between_dark_and_light(self):
        self.assertEqual(self.core.colour_map(None, None), {})


if __name__ == "__main__":
    unittest.main()
