# SPDX-License-Identifier: LGPL-2.1-or-later
"""MESH > Combine on bodies that touch never crashes and gives the right body (fission180/
mesh.py _boolean / _exact_boolean), in real FreeCAD: runs
Fission180Tests/headless/mesh_touching_check.py in a FreeCAD process of its own, so a crash
fails this test instead of killing the runner. Skipped when FreeCAD is not found
(run_tests.sh gives its command in FISSION180_FC_CMD)."""

import os
import re
import shlex
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE = os.path.dirname(os.path.dirname(HERE))
CHECKS = 32  # the reproduction + 28 cases + the big refusal + crossing bodies + Merge


def _command():
    cmd = os.environ.get("FISSION180_FC_CMD", "").strip()
    return shlex.split(cmd) if cmd else None


@unittest.skipUnless(_command(), "FreeCAD not given (FISSION180_FC_CMD)")
class MeshTouching(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        code = (
            "import sys; sys.path.insert(0, %r); "
            "from Fission180Tests.headless import mesh_touching_check as c; c.main()" % MODULE
        )
        run = subprocess.run(_command() + ["-c", code], capture_output=True, text=True, timeout=900)
        cls.code = run.returncode
        cls.output = (run.stdout + run.stderr).replace("\r", "\n")

    def test_no_crash(self):
        started = re.findall(r"mesh touching start (.*)", self.output)
        done = re.search(r"mesh touching done (\d+)", self.output)
        self.assertIsNotNone(
            done,
            "FreeCAD stopped (exit %s) during: %s\n%s"
            % (self.code, started[-1] if started else "?", self.output[-2000:]),
        )

    def test_every_case_ran(self):
        done = re.search(r"mesh touching done (\d+)", self.output)
        self.assertIsNotNone(done, self.output[-2000:])
        self.assertEqual(int(done.group(1)), CHECKS, self.output[-2000:])

    def test_every_check_passed(self):
        self.assertEqual(re.findall(r"mesh touching BAD (.*)", self.output), [])


if __name__ == "__main__":
    unittest.main()
