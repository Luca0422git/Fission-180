# SPDX-License-Identifier: LGPL-2.1-or-later
"""Runs one GUI scenario inside FreeCAD (tools/fission180/run_tests.sh starts FreeCAD with
this file; FISSION180_SCENARIO_FILE names the scenario).

A scenario that fails before its first step (an import error, a typo at the top) never
reaches harness.run, so nothing would close FreeCAD: the runner waited for its
15-minute timeout and then reported "no result". Here the error is written as a failed
result and FreeCAD quits at once."""
import json
import os
import runpy
import traceback

path = os.environ.get("FISSION180_SCENARIO_FILE", "")
try:
    runpy.run_path(path, run_name="__main__")
except Exception:
    text = traceback.format_exc()
    print("[Fission 180] scenario %s did not load:\n%s" % (path, text), flush=True)
    name = os.environ.get("FISSION180_SCENARIO", os.path.splitext(os.path.basename(path))[0])
    out = os.environ.get("FISSION180_SMOKE_OUT", ".")
    result = {
        "name": name,
        "file": name,
        "passed": False,
        "finished": True,
        "checks": [{"name": "the scenario file loads", "ok": False, "detail": text[-1500:]}],
    }
    with open(os.path.join(out, "%s-result.json" % name), "w", encoding="utf-8") as handle:
        json.dump(result, handle, indent=2)
    from PySide import QtCore, QtWidgets

    app = QtWidgets.QApplication.instance()
    QtCore.QMetaObject.invokeMethod(app, "quit", QtCore.Qt.QueuedConnection)
