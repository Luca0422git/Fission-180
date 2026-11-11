# SPDX-License-Identifier: LGPL-2.1-or-later
"""A step keeps its sketch areas when the sketch changes, in real FreeCAD
(fission180/sketch_area_id.py): runs Fission180Tests/headless/sketch_area_id_check.py without a
window (the book report's parametric drone: "Sub shape not found: Sketch.InternalFace56").
Skipped when FreeCAD is not found (run_tests.sh gives its command in FISSION180_FC_CMD)."""

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
class SketchAreasFollow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        code = (
            "import sys; sys.path.insert(0, %r); "
            "from Fission180Tests.headless import sketch_area_id_check as c; c.main()" % MODULE
        )
        run = subprocess.run(_command() + ["-c", code], capture_output=True, text=True, timeout=900)
        cls.output = (run.stdout + run.stderr).replace("\r", "\n")

    def test_every_case_ran(self):
        done = re.search(r"areas check done (\d+)", self.output)
        self.assertIsNotNone(done, self.output[-2000:])
        self.assertGreaterEqual(int(done.group(1)), 90, self.output[-2000:])

    def test_every_check_passed(self):
        self.assertEqual(re.findall(r"areas check BAD (.*)", self.output), [])


if __name__ == "__main__":
    unittest.main()
