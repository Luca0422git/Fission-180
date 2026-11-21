# SPDX-License-Identifier: LGPL-2.1-or-later
"""Dark and Light must not change (docs/fission180/neon-lights-design.md, section 3): the
fingerprint of their style sheet, colour tables, translations, icon strokes, viewer settings,
every ribbon icon and (with FreeCAD) the sketch colours equals the one taken on develop before
the Neon Lights work (tools/fission180/theme_identity.py). A failure means Dark or Light
changed: fix the code, never this fixture."""

import json
import os
import shlex
import subprocess
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, "..", "..", "..", "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "fission180"))
import theme_identity  # noqa: E402

MESSAGE = (
    "Dark/Light must not change (neon-lights-design.md section 3); fix the code, never "
    "Fission180Tests/fixtures/theme_identity.json. Changed: %s"
)


def _saved():
    with open(theme_identity.FIXTURE, "r", encoding="utf-8") as handle:
        return json.load(handle)


class DarkAndLightUnchanged(unittest.TestCase):
    def test_dark_and_light_unchanged(self):
        changed = theme_identity.compare(theme_identity.pure_fingerprint(), _saved())
        self.assertEqual(changed, [], MESSAGE % ", ".join(changed))


def _command():
    cmd = os.environ.get("FISSION180_FC_CMD", "").strip()
    return shlex.split(cmd) if cmd else None


@unittest.skipUnless(_command(), "FreeCAD not given (FISSION180_FC_CMD)")
class SketchColoursUnchanged(unittest.TestCase):
    def test_sketch_colours_unchanged(self):
        code = (
            "import sys, json; sys.path.insert(0, %r); import theme_identity as t; "
            "print('IDENTITY ' + json.dumps(t.freecad_fingerprint()))"
            % os.path.join(ROOT, "tools", "fission180")
        )
        run = subprocess.run(_command() + ["-c", code], capture_output=True, text=True, timeout=300)
        lines = [ln for ln in (run.stdout + run.stderr).splitlines() if ln.startswith("IDENTITY ")]
        self.assertTrue(lines, (run.stdout + run.stderr)[-2000:])
        now = json.loads(lines[-1][len("IDENTITY "):])
        self.assertTrue(now, "FreeCAD could not import sketch_mode")
        changed = theme_identity.compare(now, _saved())
        self.assertEqual(changed, [], MESSAGE % ", ".join(changed))


if __name__ == "__main__":
    unittest.main()
