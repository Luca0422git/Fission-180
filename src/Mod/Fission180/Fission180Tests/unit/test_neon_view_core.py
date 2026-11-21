# SPDX-License-Identifier: LGPL-2.1-or-later
"""neon_view_core: the body outlines' glow, Hologram's colours and when the rim light is used
(docs/fission180/neon-lights-design.md 6.6, plan task B6)."""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
from fission180 import neon_palette  # noqa: E402
from fission180 import neon_view_core as core  # noqa: E402


class Names(unittest.TestCase):
    def test_every_node_name_is_a_neon_name(self):
        for name in core.EDGE_NAMES + core.FLAT_NAMES:
            self.assertTrue(core.is_neon(name), name)
        for name in ("Edge", "FlatRoot", "LineMaterial", "", None, "Fission180Grid"):
            self.assertFalse(core.is_neon(name), name)

    def test_rim_node_is_the_shaders(self):
        from fission180 import neon_shader

        self.assertEqual(core.RIM_NODE, neon_shader.NODE)


class Glow(unittest.TestCase):
    def test_wider_than_the_edge(self):
        width, _t = core.glow_style(2, 70)
        self.assertEqual(width, 10.0)
        self.assertEqual(core.glow_style(1, 70)[0], core.GLOW_MIN_WIDTH)
        self.assertEqual(core.glow_style("bad", 70)[0], 10.0)

    def test_translucent_never_opaque(self):
        for strength in (-5, 0, 35, 70, 100, 400):
            _w, transparency = core.glow_style(2, strength)
            self.assertGreaterEqual(transparency, 0.4, strength)
            self.assertLessEqual(transparency, 1.0, strength)
        self.assertLess(core.glow_style(2, 100)[1], core.glow_style(2, 20)[1])

    def test_when_drawn(self):
        self.assertTrue(core.glow_wanted(True, True, False))
        self.assertFalse(core.glow_wanted(False, True, False))  # the effects' master switch
        self.assertFalse(core.glow_wanted(True, False, False))
        self.assertTrue(core.glow_wanted(False, False, True))  # Hologram edges always glow


class Colours(unittest.TestCase):
    def setUp(self):
        self.palette = neon_palette.derive(neon_palette.roles("v"))

    def test_outline_and_hologram_edges(self):
        normal = core.colours(self.palette)
        self.assertEqual(normal["edge"], self.palette["outline"])
        self.assertEqual(normal["glow"], self.palette["outline"])
        holo = core.colours(self.palette, hologram=True)
        self.assertNotEqual(holo["edge"], self.palette["outline"])  # brighter

    def test_glass_is_dark_and_tinted(self):
        c = core.colours(self.palette, hologram=True)
        glass = neon_palette.rgb01(c["glass"])
        outline = neon_palette.rgb01(self.palette["outline"])
        self.assertLess(sum(glass), sum(outline) / 2.0)
        self.assertNotEqual(c["glass"], self.palette["background"])
        for key in c:
            self.assertTrue(neon_palette.valid_hex(c[key]), key)

    def test_every_preset(self):
        for key in neon_palette.ORDER:
            palette = neon_palette.derive(neon_palette.roles(key))
            for hologram in (False, True):
                c = core.colours(palette, hologram)
                self.assertEqual(set(c), {"edge", "glow", "glass", "glass_glow", "rim"})


class RimLight(unittest.TestCase):
    def test_only_after_self_test_and_on_hologram(self):
        self.assertTrue(core.rim_wanted("auto", True, True))
        self.assertTrue(core.rim_wanted("on", True, True))
        self.assertFalse(core.rim_wanted("auto", True, False))  # flat glass fallback
        self.assertFalse(core.rim_wanted("on", True, False))
        self.assertFalse(core.rim_wanted("off", True, True))
        self.assertFalse(core.rim_wanted("auto", False, True))


def _row(edge, centre, size=64, background=(0, 0, 0)):
    """A middle row of the self-test picture: a sphere from x 8 to 55, `edge` at its rims."""
    row = [background] * size
    for x in range(8, 56):
        row[x] = centre
    for x in (8, 9, 54, 55):
        row[x] = edge
    return row


class ShaderJudge(unittest.TestCase):
    """neon_shader.judge: the rim must be brighter with the shader, and the middle (seen
    face-on) as drawn without it (the face colour reaches the shader)."""

    def setUp(self):
        from fission180 import neon_shader

        self.shader = neon_shader

    def test_passes_when_rim_lit_and_centre_kept(self):
        plain = _row((26, 26, 26), (26, 26, 26))
        lit = _row((136, 15, 15), (26, 26, 26))
        self.assertTrue(self.shader.judge(plain, lit)[0])

    def test_fails_without_rim(self):
        plain = _row((26, 26, 26), (26, 26, 26))
        self.assertFalse(self.shader.judge(plain, plain)[0])

    def test_fails_when_face_colour_lost(self):
        plain = _row((26, 26, 26), (26, 26, 26))
        for centre in ((60, 60, 60), (5, 5, 5), (26, 80, 26)):
            lit = _row((200, 15, 15), centre)
            ok, why = self.shader.judge(plain, lit)
            self.assertFalse(ok, centre)
            self.assertIn("face colour", why)
        lit = _row((200, 15, 15), (26 + self.shader.CENTRE_TOLERANCE, 26, 26))
        self.assertTrue(self.shader.judge(plain, lit)[0])

    def test_fails_when_nothing_drawn(self):
        self.assertFalse(self.shader.judge(None, _row((1, 1, 1), (1, 1, 1)))[0])
        empty = [(0, 0, 0)] * 64
        self.assertFalse(self.shader.judge(empty, empty)[0])


class FakeParams:
    def __init__(self):
        self.values = {}

    def GetString(self, name, default=""):
        return self.values.get(name, default)

    def SetString(self, name, value):
        self.values[name] = value

    def RemString(self, name):
        self.values.pop(name, None)


class ShaderSelfTest(unittest.TestCase):
    """The self-test runs behind a stored "testing" flag: a crash during it (the flag left
    over at the next start) means the shader is never tried again."""

    def setUp(self):
        from fission180 import neon_shader

        self.shader = neon_shader
        self.params = FakeParams()
        self.saved = {n: getattr(neon_shader, n) for n in ("_params", "_write", "check", "log")}
        self.flag_during = []
        neon_shader._params = lambda: self.params
        neon_shader._write = lambda: None
        neon_shader.log = lambda text: None

        def check():
            self.flag_during.append(self.params.values.get(neon_shader.FLAG))
            return True, "fine"

        neon_shader.check = check
        self.env = os.environ.pop("FISSION180_NEON_NO_SHADER", None)
        neon_shader.reset()

    def tearDown(self):
        for name, value in self.saved.items():
            setattr(self.shader, name, value)
        if self.env is not None:
            os.environ["FISSION180_NEON_NO_SHADER"] = self.env
        self.shader.reset()

    def test_flag_set_while_testing_then_cleared(self):
        self.assertEqual(self.shader.self_test(), (True, "fine"))
        self.assertEqual(self.flag_during, [self.shader.TESTING])
        self.assertNotIn(self.shader.FLAG, self.params.values)
        self.assertTrue(self.shader.tested())

    def test_runs_once_per_session(self):
        self.shader.self_test()
        self.shader.self_test()
        self.assertEqual(len(self.flag_during), 1)

    def test_leftover_flag_means_failed_and_never_again(self):
        self.params.values[self.shader.FLAG] = self.shader.TESTING  # crashed last time
        ok, why = self.shader.self_test()
        self.assertFalse(ok)
        self.assertIn("earlier session", why)
        self.assertEqual(self.flag_during, [])  # not drawn again
        self.assertEqual(self.params.values[self.shader.FLAG], self.shader.CRASHED)
        self.shader.reset()
        self.assertFalse(self.shader.self_test()[0])  # the next start too
        self.assertEqual(self.flag_during, [])
        self.shader.reset(forget_crash=True)
        self.assertTrue(self.shader.self_test()[0])

    def test_exception_clears_flag(self):
        def broken():
            raise RuntimeError("driver")

        self.shader.check = broken
        ok, why = self.shader.self_test()
        self.assertFalse(ok)
        self.assertIn("driver", why)
        self.assertNotIn(self.shader.FLAG, self.params.values)


if __name__ == "__main__":
    unittest.main()
