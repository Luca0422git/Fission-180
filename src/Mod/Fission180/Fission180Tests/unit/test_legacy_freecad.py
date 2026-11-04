# SPDX-License-Identifier: LGPL-2.1-or-later
"""Designs saved by SciForge (the program's old name) open, rebuild and save again in real
FreeCAD with Fission 180 (fission180/legacy.py): runs Fission180Tests/headless/legacy_check.py
without a window. Skipped when FreeCAD is not found (run_tests.sh gives its command in
FISSION180_FC_CMD, with the module installed in a throw-away profile)."""

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
class DesignsSavedBySciForge(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        code = (
            "import sys; sys.path.insert(0, %r); "
            "from Fission180Tests.headless import legacy_check as c; c.main()" % MODULE
        )
        run = subprocess.run(_command() + ["-c", code], capture_output=True, text=True, timeout=600)
        cls.output = (run.stdout + run.stderr).replace("\r", "\n")

    def test_both_designs_were_checked(self):
        done = re.search(r"legacy check done (\d+)", self.output)
        self.assertIsNotNone(done, self.output[-2000:])
        self.assertEqual(int(done.group(1)), 2, self.output[-2000:])
        self.assertGreaterEqual(len(re.findall(r"legacy check OK ", self.output)), 14)

    def test_every_check_passed(self):
        bad = re.findall(r"legacy check BAD (.*)", self.output)
        self.assertEqual(bad, [])

    def test_no_import_was_refused(self):
        self.assertNotIn("not permitted", self.output)
        self.assertNotIn("blocked import", self.output)


if __name__ == "__main__":
    unittest.main()
