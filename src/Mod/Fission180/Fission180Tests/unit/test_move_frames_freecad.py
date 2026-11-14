# SPDX-License-Identifier: LGPL-2.1-or-later
"""A Move or Create Copy step stands at no placement of its own, so sketches on its faces keep
their origin and designs saved before recompute as they were (move-speed, found at the merge,
2026-11-14): runs Fission180Tests/headless/move_frames_check.py in real FreeCAD without a
window and compares every object's fingerprint with what 0.1.0-beta.4.0.2 built (the lines
below are that version's output, the fixture move_frames_v1.FCStd is the design it saved).
Skipped when FreeCAD is not found (run_tests.sh gives its command in FISSION180_FC_CMD)."""

import os
import re
import shlex
import subprocess
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE = os.path.dirname(os.path.dirname(HERE))

# name, shape, own placement (position | angle), box, volume, state: as 0.1.0-beta.4.0.2
RELEASED = """\
Body Compound P(0.000 0.000 0.000|0.00) box(6.000 -11.061 1.000 40.995 12.158 17.000) vol 4875.398 ok
Sketch0 Wire P(3.000 4.000 2.000|20.00) box(-2.472 4.000 2.000 31.191 29.296 2.000) vol 0.000 ok
Pad0 Solid P(0.000 0.000 0.000|0.00) box(-2.472 4.000 2.000 31.191 29.296 12.000) vol 4800.000 ok
Move Solid P(0.000 0.000 0.000|0.00) box(7.876 -11.061 1.000 40.995 12.158 11.000) vol 4800.000 ok
Sketch Wire P(0.000 0.000 11.000|0.00) box(6.000 2.000 11.000 10.000 6.000 11.000) vol 0.000 ok
Pad Compound P(0.000 0.000 0.000|0.00) box(6.000 -11.061 1.000 40.995 12.158 17.000) vol 4875.398 ok
Body2 Compound P(0.000 0.000 0.000|0.00) box(1.500 -3.938 0.000 31.213 19.383 12.000) vol 1948.274 ok
Move001 Solid P(0.000 0.000 0.000|0.00) box(10.821 -3.938 0.000 31.213 19.383 8.000) vol 1920.000 ok
SketchB Wire P(0.000 0.000 8.000|0.00) box(1.500 0.500 8.000 4.500 3.500 8.000) vol 0.000 ok
PadB Compound P(0.000 0.000 0.000|0.00) box(1.500 -3.938 0.000 31.213 19.383 12.000) vol 1948.274 ok
Move002 Compound P(0.000 0.000 0.000|0.00) box(-49.158 -1.000 1.000 -25.939 33.995 17.000) vol 4875.398 ok
Body001 Compound P(0.000 0.000 0.000|0.00) box(-56.000 -1.000 1.000 -25.939 33.995 20.000) vol 4884.823 ok
BaseFeature Compound P(0.000 0.000 0.000|0.00) box(-49.158 -1.000 1.000 -25.939 33.995 17.000) vol 4875.398 ok
SketchC Wire P(0.000 0.000 17.000|0.00) box(-56.000 4.000 17.000 -54.000 6.000 17.000) vol 0.000 ok
PadC Compound P(0.000 0.000 0.000|0.00) box(-56.000 -1.000 1.000 -25.939 33.995 20.000) vol 4884.823 ok
""".splitlines()  # noqa: E501


def _command():
    cmd = os.environ.get("FISSION180_FC_CMD", "").strip()
    return shlex.split(cmd) if cmd else None


@unittest.skipUnless(_command(), "FreeCAD not given (FISSION180_FC_CMD)")
class MoveStepsKeepTheFramesOfWhatIsBuiltOnThem(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        code = (
            "import sys; sys.path.insert(0, %r); "
            "from Fission180Tests.headless import move_frames_check as c; c.main()" % MODULE
        )
        run = subprocess.run(_command() + ["-c", code], capture_output=True, text=True, timeout=600)
        cls.output = (run.stdout + run.stderr).replace("\r", "\n")

    def _lines(self, kind):
        return re.findall(r"\[Fission 180\] move frames %s (.+)" % kind, self.output)

    def test_it_ran(self):
        self.assertNotIn("move frames ERROR", self.output)
        done = re.search(r"move frames done (\d+)", self.output)
        self.assertIsNotNone(done, self.output[-2000:])
        self.assertEqual(int(done.group(1)), 2 * len(RELEASED))

    def test_a_new_design_is_built_as_the_released_version_built_it(self):
        self.assertEqual(self._lines("built"), RELEASED)

    def test_a_design_saved_before_recomputes_as_it_was(self):
        self.assertEqual(self._lines("saved"), RELEASED)

    def test_move_and_copy_steps_stand_at_no_placement(self):
        steps = [line for line in self._lines("built") if line.startswith(("Move", "BaseFeature"))]
        self.assertEqual(len(steps), 4)
        for line in steps:
            self.assertIn(" P(0.000 0.000 0.000|0.00) ", line)


if __name__ == "__main__":
    unittest.main()
