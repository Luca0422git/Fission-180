# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights at Interface size 150 % and 75 % (plan task B1, Review Focus: "Interface size
150 % (and 75 %) with the techy font: no clipped labels in the ribbon, tabs, task dialogs,
Preferences").

Interface size shows only after a restart (interface_scale: Qt takes its scale when it
starts), so this scenario chooses the size in Preferences' setting, keeps a copy of its
profile with Neon Lights chosen, and starts FreeCAD again with that profile, once per size
(the run's own QT_SCALE_FACTOR=1 removed, so Fission 180 sets the scale itself, as at a
person's restart). That FreeCAD (Fission180Tests/gui/neon_sizes_child.py) measures every
label of the ribbon, the Extrude dialog and each Preferences page in Neon Lights and in Dark;
its checks come back here."""

import json
import os
import shutil
import tempfile

import FreeCAD as App
from PySide import QtCore

from Fission180Tests.gui import harness as h

SIZES = ("150", "75")
s = {}
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _freecad():
    """The FreeCAD (or Fission 180) program this one is."""
    names = ("Fission180", "fission180", "FreeCAD", "freecad")
    folders = []
    if os.environ.get("PREFIX"):
        folders.append(os.path.join(os.environ["PREFIX"], "bin"))  # the AppImage's own
    folders.append(os.path.join(App.getHomePath(), "bin"))
    for folder in folders:
        for name in names:
            path = os.path.join(folder, name)
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
    return None


def setup():
    from fission180 import interface_scale, neon_settings, preferences_ui

    neon_settings.put("Preset", "v")
    preferences_ui.save({"theme": "neon"})
    s["program"] = _freecad()
    h.check("the FreeCAD program is found", s["program"] is not None, App.getHomePath())
    s["profile"] = os.environ.get("FREECAD_USER_HOME") or os.path.dirname(App.getUserAppDataDir().rstrip("/"))
    s["key"] = interface_scale.KEY


def _start(size):
    """FreeCAD again at Interface size `size` with a copy of this profile."""
    from fission180 import interface_scale

    App.ParamGet(interface_scale.PARAMS).SetString(interface_scale.KEY, size)
    App.saveParameter()
    copy = tempfile.mkdtemp(prefix="neon-sizes-")
    shutil.copytree(s["profile"], copy, dirs_exist_ok=True)
    App.ParamGet(interface_scale.PARAMS).RemString(interface_scale.KEY)
    name = "neon_sizes_%s" % size
    out = os.environ.get("FISSION180_SMOKE_OUT") or tempfile.gettempdir()
    result = os.path.join(out, "%s-result.json" % name)
    if os.path.exists(result):
        os.remove(result)
    env = QtCore.QProcessEnvironment.systemEnvironment()
    for var in ("QT_SCALE_FACTOR", "FISSION180_SET_QT_SCALE"):
        env.remove(var)
    env.insert("FREECAD_USER_HOME", copy)
    env.insert("FISSION180_SCENARIO", name)
    env.insert("FISSION180_SCENARIO_FILE", os.path.join(HERE, "neon_sizes_child.py"))
    env.insert("FISSION180_SMOKE_OUT", out)
    env.insert("FISSION180_NEON_SIZES_FACTOR", str(int(size) / 100.0))
    process = QtCore.QProcess()
    process.setProcessEnvironment(env)
    process.setProcessChannelMode(QtCore.QProcess.MergedChannels)
    process.setStandardOutputFile(os.path.join(out, "scenario-%s.log" % name))
    process.start(s["program"], [os.path.join(HERE, "scenario_launcher.py")])
    s[size] = {"process": process, "result": result, "profile": copy}


def _finished(size):
    job = s.get(size)
    return job is not None and job["process"].state() == QtCore.QProcess.NotRunning


def _report(size):
    job = s[size]
    try:
        with open(job["result"], "r", encoding="utf-8") as handle:
            result = json.load(handle)
    except (OSError, ValueError) as exc:
        h.check("Interface size %s %%: FreeCAD started again and gave its result" % size, False,
                "%s (log: scenario-neon_sizes_%s.log)" % (exc, size))
        result = None
    if result is not None:
        h.check("Interface size %s %%: FreeCAD started again and finished" % size, bool(result.get("finished")))
        for item in result.get("checks", []):
            h.check("[%s %%] %s" % (size, item.get("name")), item.get("ok"), item.get("detail", ""))
    shutil.rmtree(job["profile"], ignore_errors=True)


def start_150():
    _start("150")


start_150.done = lambda: _finished("150")
start_150.done_what = "FreeCAD at Interface size 150 % to finish its checks"
start_150.timeout_s = 600


def report_150():
    _report("150")


def start_75():
    _start("75")


start_75.done = lambda: _finished("75")
start_75.done_what = "FreeCAD at Interface size 75 % to finish its checks"
start_75.timeout_s = 600


def report_75():
    _report("75")


def back_to_dark():
    from fission180 import preferences_ui

    preferences_ui.save({"theme": "dark"})


h.run("neon_sizes", [setup, start_150, report_150, start_75, report_75, back_to_dark], paced_by="state")
