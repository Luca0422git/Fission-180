# SPDX-License-Identifier: LGPL-2.1-or-later
"""Modify > Scale on a sketch gives every dimension its new value without a solve that mixes
new and old values (wave 7, fix-7: a triangle 10 / 6 / 6 doubled, an ellipse scaled back, the
Scale step edited again as its OK does), in real FreeCAD. Runs
Fission180Tests/headless/sketch_scale_check.py without a window. Skipped when FreeCAD is not
found (run_tests.sh gives its command in FISSION180_FC_CMD)."""

import os
import re
import shlex
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE = os.path.dirname(os.path.dirname(HERE))


def _command():
    cmd = os.environ.get("FISSION180_FC_CMD", "").strip()
    return shlex.split(cmd) if cmd else None


@unittest.skipUnless(_command(), "FreeCAD not given (FISSION180_FC_CMD)")
class SketchScale(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        code = (
            "import sys; sys.path.insert(0, %r); "
            "from Fission180Tests.headless import sketch_scale_check as c; c.main()" % MODULE
        )
        run = subprocess.run(_command() + ["-c", code], capture_output=True, text=True, timeout=600)
        cls.output = (run.stdout + run.stderr).replace("\r", "\n")

    def test_every_case_ran(self):
        done = re.search(r"sketch scale check done (\d+)", self.output)
        self.assertIsNotNone(done, self.output[-2000:])
        self.assertGreaterEqual(int(done.group(1)), 25, self.output[-2000:])

    def test_every_check_passed(self):
        self.assertEqual(re.findall(r"sketch scale check BAD (.*)", self.output), [])


if __name__ == "__main__":
    unittest.main()
