# SPDX-License-Identifier: LGPL-2.1-or-later
"""A sketch's redundant or conflicting constraints are named with get_sketch's numbers (from 0)
in the timeline's message and the AI tools' (bug report 2026-11-23: FreeCAD's own message,
counted from 1, was passed on and named a needed constraint): runs
Fission180Tests/headless/constraint_numbers_check.py in real FreeCAD without a window.
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
class ConstraintNumbers(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        code = (
            "import sys; sys.path.insert(0, %r); "
            "from Fission180Tests.headless import constraint_numbers_check as c; c.main()" % MODULE
        )
        run = subprocess.run(_command() + ["-c", code], capture_output=True, text=True, timeout=600)
        cls.output = (run.stdout + run.stderr).replace("\r", "\n")

    def test_every_case_ran(self):
        done = re.search(r"numbers check done (\d+)", self.output)
        self.assertIsNotNone(done, self.output[-2000:])
        self.assertGreaterEqual(int(done.group(1)), 40, self.output[-2000:])

    def test_every_check_passed(self):
        self.assertEqual(re.findall(r"numbers check BAD (.*)", self.output), [], self.output[-3000:])


if __name__ == "__main__":
    unittest.main()
