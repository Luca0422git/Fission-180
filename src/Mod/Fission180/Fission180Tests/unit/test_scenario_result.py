# SPDX-License-Identifier: LGPL-2.1-or-later
"""tools/fission180/scenario_result.py: a scenario whose FreeCAD crashed when it closed fails,
although its checks passed (2026-11-23: the first title bar crashed FreeCAD at every exit and
every scenario still passed: the crash came after the results were written)."""

import importlib.util
import io
import json
import os
import tempfile
import unittest
from contextlib import redirect_stdout

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "..", "..", "..", "..", "..", "tools", "fission180", "scenario_result.py")


def _load():
    spec = importlib.util.spec_from_file_location("scenario_result", os.path.abspath(SCRIPT))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class CrashAtExit(unittest.TestCase):
    def run_with(self, log_text):
        out = tempfile.mkdtemp(prefix="fission180_result_")
        with open(os.path.join(out, "demo-result.json"), "w", encoding="utf-8") as handle:
            json.dump(
                {"file": "demo", "name": "demo", "checks": [{"name": "fine", "ok": True, "detail": ""}],
                 "passed": True, "finished": True},
                handle,
            )
        with open(os.path.join(out, "scenario-demo.log"), "w", encoding="utf-8") as handle:
            handle.write(log_text)
        env = os.environ.pop("GITHUB_ACTIONS", None)
        try:
            buf = io.StringIO()
            with redirect_stdout(buf):
                code = _load().main(["scenario_result.py", out, "demo"])
        finally:
            if env is not None:
                os.environ["GITHUB_ACTIONS"] = env
        return code, buf.getvalue()

    def test_a_clean_exit_passes(self):
        code, _out = self.run_with("[Fission 180] interface off\n")
        self.assertEqual(code, 0)

    def test_a_crash_at_exit_fails(self):
        code, out = self.run_with(
            "[Fission 180] interface off\nProgram received signal SIGSEGV, Segmentation fault.\n#0 ...\n"
        )
        self.assertEqual(code, 1)
        self.assertIn("crashed", out)


if __name__ == "__main__":
    unittest.main()
