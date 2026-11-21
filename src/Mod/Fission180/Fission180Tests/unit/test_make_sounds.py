# SPDX-License-Identifier: LGPL-2.1-or-later
"""tools/fission180/make_sounds.py: Neon Lights' UI sounds (neon-lights-design.md 6.9) are
synthesized, always the same, small, and the committed files are the script's output."""

import importlib.util
import os
import struct
import sys
import tempfile
import unittest
import wave

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, "..", "..", "..", "..", ".."))
TOOL = os.path.join(REPO, "tools", "fission180", "make_sounds.py")
SOUNDS = os.path.join(HERE, "..", "..", "fission180", "sounds")
sys.path.insert(0, os.path.join(HERE, "..", ".."))
from fission180 import neon_sound  # noqa: E402


def _load_tool():
    if not os.path.exists(TOOL):
        raise unittest.SkipTest("tools/ is not here (an installed Fission 180)")
    spec = importlib.util.spec_from_file_location("make_sounds", TOOL)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _samples(path):
    with wave.open(path, "rb") as w:
        data = w.readframes(w.getnframes())
        return w.getparams(), struct.unpack("<%dh" % (len(data) // 2), data)


class MakeSounds(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tool = _load_tool()

    def test_names_match_the_player(self):
        self.assertEqual(tuple(self.tool.NAMES), tuple(neon_sound.NAMES))

    def test_deterministic_small_and_clean(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            first = self.tool.make(a)
            second = self.tool.make(b)
            for p, q in zip(first, second):
                with open(p, "rb") as f, open(q, "rb") as g:
                    self.assertEqual(f.read(), g.read(), os.path.basename(p))
                size = os.path.getsize(p)
                self.assertLess(size, 60 * 1024, os.path.basename(p))
                params, values = _samples(p)
                self.assertEqual((params.nchannels, params.sampwidth), (1, 2))
                self.assertGreater(len(values), 100)
                self.assertLess(abs(values[0]), 2000, "starts softly: %s" % p)
                self.assertLess(abs(values[-1]), 200, "ends in silence (no click): %s" % p)
                self.assertGreater(max(abs(v) for v in values), 3000, "audible: %s" % p)
                self.assertLess(max(abs(v) for v in values), 32767, "not clipped: %s" % p)

    def test_committed_files_are_the_scripts_output(self):
        for name in self.tool.NAMES:
            committed = os.path.join(SOUNDS, name + ".wav")
            self.assertTrue(os.path.exists(committed), "run tools/fission180/make_sounds.py")
            _params, values = _samples(committed)
            fresh = self.tool.samples(name)
            self.assertEqual(len(values), len(fresh), name)
            # +-1: the last bit of a sample may round differently on another libm
            self.assertTrue(all(abs(x - y) <= 1 for x, y in zip(values, fresh)), name)


if __name__ == "__main__":
    unittest.main()
