# SPDX-License-Identifier: LGPL-2.1-or-later
"""The heavy boolean of a pattern, in a command-line FreeCAD of its own.

Started by pattern_progress.build_outside as `freecadcmd pattern_worker.py` with the job's
folder in FISSION180_PATTERN_JOB. The folder holds job.json ({"refine": bool}), base.brep
(the part before the pattern), and adds.brep / cuts.brep when there are copies to join / to
cut (each a compound of the copies). It writes result.brep and then done.json ({"ok": true}
or {"ok": false, "error": "..."}); done.json comes last, so a result is whole when it is
there.

It runs alone (not as part of the fission180 package): only FreeCAD's Part is used, and the
same two booleans as fission180.pattern.combine.
"""

import json
import os
import sys


def _read(folder, name):
    import Part

    path = os.path.join(folder, name)
    if not os.path.isfile(path):
        return None
    shape = Part.Shape()
    shape.importBrep(path)
    return shape


def run(folder):
    with open(os.path.join(folder, "job.json"), "r", encoding="utf-8") as handle:
        job = json.load(handle)
    result = _read(folder, "base.brep")
    adds = _read(folder, "adds.brep")
    cuts = _read(folder, "cuts.brep")
    if adds is not None:
        result = result.fuse(list(adds.SubShapes))
    if cuts is not None:
        result = result.cut(list(cuts.SubShapes))
    if job.get("refine", True):
        try:
            result = result.removeSplitter()
        except Exception:
            pass
    result.exportBrep(os.path.join(folder, "result.brep"))


def main():
    folder = os.environ.get("FISSION180_PATTERN_JOB", "")
    if not folder:
        return
    done = {"ok": True}
    try:
        run(folder)
    except Exception as exc:
        done = {"ok": False, "error": str(exc)}
    temp = os.path.join(folder, "done.json.part")
    with open(temp, "w", encoding="utf-8") as handle:
        json.dump(done, handle)
    os.replace(temp, os.path.join(folder, "done.json"))
    sys.stdout.flush()
    os._exit(0)  # no slow shutdown of the application for a finished job


if os.environ.get("FISSION180_PATTERN_JOB"):
    main()
