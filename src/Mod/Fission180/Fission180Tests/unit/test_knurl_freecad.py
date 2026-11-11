# SPDX-License-Identifier: LGPL-2.1-or-later
"""The Fire Piston's knurl (a Coil after a sketch on the YZ plane, its Mirror, a Circular
Pattern of both about X) built in the window's process, by the code of the command-line
program OK starts for a heavy pattern (pattern_worker), and by hand from what each feature
took away: one and the same solid (wave 7, fix-6), in real FreeCAD. Runs
Fission180Tests/headless/knurl_check.py without a window. Skipped when FreeCAD is not found
(run_tests.sh gives its command in FISSION180_FC_CMD)."""

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
class Knurl(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        code = (
            "import sys; sys.path.insert(0, %r); "
            "from Fission180Tests.headless import knurl_check as c; c.main()" % MODULE
        )
        run = subprocess.run(_command() + ["-c", code], capture_output=True, text=True, timeout=900)
        cls.output = (run.stdout + run.stderr).replace("\r", "\n")

    def test_every_case_ran(self):
        done = re.search(r"knurl check done (\d+)", self.output)
        self.assertIsNotNone(done, self.output[-2000:])
        self.assertGreaterEqual(int(done.group(1)), 8, self.output[-2000:])

    def test_every_check_passed(self):
        self.assertEqual(re.findall(r"knurl check BAD (.*)", self.output), [])


if __name__ == "__main__":
    unittest.main()
