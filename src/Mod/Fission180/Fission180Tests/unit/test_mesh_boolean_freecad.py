# SPDX-License-Identifier: LGPL-2.1-or-later
"""Mesh Combine gives the right closed body whatever the order of the facets
(fission180/mesh.py _boolean, fix-2), in real FreeCAD: runs
Fission180Tests/headless/mesh_boolean_check.py without a window. Skipped when FreeCAD is
not found (run_tests.sh gives its command in FISSION180_FC_CMD)."""

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
class MeshBooleanOrder(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        code = (
            "import sys; sys.path.insert(0, %r); "
            "from Fission180Tests.headless import mesh_boolean_check as c; c.main()" % MODULE
        )
        run = subprocess.run(_command() + ["-c", code], capture_output=True, text=True, timeout=900)
        cls.output = (run.stdout + run.stderr).replace("\r", "\n")

    def test_every_case_ran(self):
        done = re.search(r"mesh boolean done (\d+)", self.output)
        self.assertIsNotNone(done, self.output[-2000:])
        self.assertEqual(int(done.group(1)), 3, self.output[-2000:])

    def test_every_check_passed(self):
        self.assertEqual(re.findall(r"mesh boolean BAD (.*)", self.output), [])


if __name__ == "__main__":
    unittest.main()
