# SPDX-License-Identifier: LGPL-2.1-or-later
"""Parameters in real FreeCAD without a window (wave 7, the book parity report): runs
Fission180Tests/headless/parameters_check.py and checks every case: a negative length
(bug 4), every unit, the book's min / max limits, names FreeCAD reads as units, rename and
delete, favourites through save and reopen, Name = value, a deleted sketch constraint
(bug 3), the formulas of a design made before, a design held to its units (bug 2).
Skipped when FreeCAD is not found (run_tests.sh gives its command in FISSION180_FC_CMD)."""

import os
import re
import shlex
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE = os.path.dirname(os.path.dirname(HERE))
CASES = 17


def _command():
    cmd = os.environ.get("FISSION180_FC_CMD", "").strip()
    return shlex.split(cmd) if cmd else None


@unittest.skipUnless(_command(), "FreeCAD not given (FISSION180_FC_CMD)")
class ParametersInFreeCAD(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        code = (
            "import sys; sys.path.insert(0, %r); "
            "from Fission180Tests.headless import parameters_check as c; c.main()" % MODULE
        )
        run = subprocess.run(_command() + ["-c", code], capture_output=True, text=True, timeout=600)
        cls.output = (run.stdout + run.stderr).replace("\r", "\n")

    def test_every_case_ran(self):
        done = re.search(r"params check done (\d+)", self.output)
        self.assertIsNotNone(done, self.output[-3000:])
        self.assertEqual(int(done.group(1)), CASES)

    def test_every_case_passed(self):
        failed = re.findall(r"params check (\w+): FAIL (.*)", self.output)
        self.assertEqual(failed, [])
        self.assertEqual(len(re.findall(r"params check \w+: ok", self.output)), CASES)


if __name__ == "__main__":
    unittest.main()
