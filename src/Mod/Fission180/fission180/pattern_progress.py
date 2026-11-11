# SPDX-License-Identifier: LGPL-2.1-or-later
"""A heavy pattern build that says so, can be stopped and gives its memory back.

The book's knurl (a Coil groove, its Mirror, a Circular Pattern of both, 25 around) takes
the geometry kernel half a minute and 830 MB in one boolean nothing can interrupt; the
parity report's tester saw a frozen window for ten minutes, 5.8 GB in use, and killed the
app. build_outside (pattern.BUILDER) runs that boolean in a command-line FreeCAD of its own
(pattern_worker.py), as the toolpaths and the simulations do: the window stays alive, a
small window says what is being built and for how long, Cancel stops it at once (only when
a dialog's OK started the build: pattern.CANCELLABLE), and the kernel's memory goes back to
the system with that program. While the small window is up nothing else in Fission 180
takes clicks or keys (it is modal), so the design cannot be changed under the build.

Returns None when the build cannot run there (no command-line program, it crashed): the
caller then builds in the window's own process, as before.
"""

import json
import os
import shutil
import subprocess
import tempfile
import time

import FreeCAD as App
import Part
from .compat import QtCore, QtWidgets

from . import log, warn
from .pattern import Cancelled

TIMEOUT_S = 3600.0
STATE = {"open": None, "runs": 0, "cancelled": 0, "last_s": 0.0}  # what the tests look at


def _freecad_cmd():
    """The command-line FreeCAD next to this one, or None."""
    home = App.getHomePath()
    names = ("Fission180Cmd", "fission180cmd", "FreeCADCmd", "freecadcmd")
    for folder in ("bin", "", os.path.join("..", "MacOS")):
        for name in names:
            candidate = os.path.join(home, folder, name + (".exe" if os.name == "nt" else ""))
            if os.path.isfile(candidate):
                return candidate
    for name in names:
        found = shutil.which(name)
        if found:
            return found
    return None


def _worker_file():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "pattern_worker.py")


class _Window:
    """The small modal window of a running build."""

    def __init__(self, title, copies, can_cancel):
        import FreeCADGui as Gui

        self.title = title
        self.copies = copies
        self.main = Gui.getMainWindow()
        self.focus = QtWidgets.QApplication.focusWidget()  # it gets the keys back afterwards
        dialog = QtWidgets.QProgressDialog(self.main)
        dialog.setObjectName("Fission180PatternProgress")
        dialog.setWindowTitle("Fission 180")
        dialog.setRange(0, 0)  # how far a boolean is cannot be known: a busy bar
        dialog.setWindowModality(QtCore.Qt.ApplicationModal)
        dialog.setMinimumDuration(0)
        dialog.setAutoClose(False)
        dialog.setAutoReset(False)
        if can_cancel:
            dialog.setCancelButtonText("Cancel")
        else:
            dialog.setCancelButton(None)
        self.dialog = dialog
        self.can_cancel = can_cancel
        self.tell(0.0)
        dialog.show()

    def tell(self, seconds):
        self.dialog.setLabelText(
            "Building %s: %d %s ... %d s"
            % (self.title, self.copies, "copy" if self.copies == 1 else "copies", int(seconds))
        )

    def cancelled(self):
        return self.can_cancel and self.dialog.wasCanceled()

    def close(self):
        try:
            self.dialog.reset()
            self.dialog.close()
            self.dialog.deleteLater()
        except Exception:
            pass
        try:
            # The main window takes the keys again (without this the next Ctrl+Z went
            # nowhere where no window manager hands the focus back).
            self.main.activateWindow()
            if self.focus is not None:
                self.focus.setFocus()
        except Exception:
            pass


def build_outside(base_shape, adds, cuts, refine, title, can_cancel):
    """base_shape with `adds` joined and `cuts` cut (pattern.combine), worked out by a
    command-line FreeCAD while this window stays alive. None when that could not be done;
    raises pattern.Cancelled when the person stopped it."""
    if QtWidgets.QApplication.instance() is None or not App.GuiUp:
        return None
    command = _freecad_cmd()
    if command is None:
        log("pattern: no command-line program found; the copies are built in the window")
        return None
    folder = tempfile.mkdtemp(prefix="fission180_pattern_")
    process = None
    window = None
    out = None
    started = time.time()
    try:
        base_shape.exportBrep(os.path.join(folder, "base.brep"))
        if adds:
            Part.makeCompound(adds).exportBrep(os.path.join(folder, "adds.brep"))
        if cuts:
            Part.makeCompound(cuts).exportBrep(os.path.join(folder, "cuts.brep"))
        with open(os.path.join(folder, "job.json"), "w", encoding="utf-8") as handle:
            json.dump({"refine": bool(refine)}, handle)
        env = dict(os.environ)
        env["FISSION180_PATTERN_JOB"] = folder
        out = open(os.path.join(folder, "worker.log"), "w")
        process = subprocess.Popen(
            [command, _worker_file()],
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=out,
            stderr=subprocess.STDOUT,
            cwd=folder,
        )
        STATE["runs"] += 1
        window = _Window(title, len(adds) + len(cuts), can_cancel)
        STATE["open"] = window
        done = os.path.join(folder, "done.json")
        while not os.path.isfile(done):
            if process.poll() is not None and not os.path.isfile(done):
                log("pattern: the command-line build ended without a result")
                return None
            seconds = time.time() - started
            if seconds > TIMEOUT_S:
                return None
            window.tell(seconds)
            QtWidgets.QApplication.processEvents(QtCore.QEventLoop.AllEvents, 50)
            if window.cancelled():
                STATE["cancelled"] += 1
                raise Cancelled("Cancelled: the copies were not built. Press OK to build them.")
            time.sleep(0.05)  # on purpose: the pace of looking whether the other program is done
        with open(done, "r", encoding="utf-8") as handle:
            answer = json.load(handle)
        if not answer.get("ok"):
            log("pattern: the command-line build failed: %s" % answer.get("error"))
            return None  # built here instead: the kernel's own message then reaches the step
        result = Part.Shape()
        result.importBrep(os.path.join(folder, "result.brep"))
        STATE["last_s"] = time.time() - started
        return result
    except Cancelled:
        raise
    except Exception as exc:
        warn("pattern: the command-line build could not run: %s" % exc)
        return None
    finally:
        if process is not None and process.poll() is None:
            try:
                process.kill()
                process.wait(5)
            except Exception:
                pass
        if window is not None:
            window.close()
        STATE["open"] = None
        if out is not None:
            try:
                out.close()
            except Exception:
                pass
        shutil.rmtree(folder, ignore_errors=True)


def install():
    from . import pattern

    pattern.BUILDER = build_outside
