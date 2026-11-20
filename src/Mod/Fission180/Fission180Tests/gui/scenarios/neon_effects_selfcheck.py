# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fission 180 > Diagnostics > Neon self-check (neon-lights-design.md 6.13, plan task B8).

In Neon Lights, the Diagnostics window's "Neon self-check" button orbits a sample part of about
3,000 faces with the effects off, on, with Sounds and with Hologram (in turns of 20 frames),
measures the idle CPU, and puts a report in the window to copy: processor and clock time per
frame, the effects layer's paints, a verdict in plain words, idle CPU, the rim-light shader's
self-test, the failed Neon parts and the platform/graphics card. The designs open before stay as they were, and so do the
effect and Hologram settings. The sandbox draws in software, so its numbers are printed only;
the speed budget is judged on Luca's machines.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import look_compare as lc
from Fission180Tests.gui import widget_input as wi

s = {}


def diagnostics():
    for w in QtWidgets.QApplication.topLevelWidgets():
        if w.windowTitle() == "Fission 180 Diagnostics" and w.isVisible():
            return w
    return None


def setup():
    from fission180 import neon_settings

    lc.setup()
    neon_settings.put("Hologram", False)
    lc.set_look("neon")
    s["docs"] = sorted(App.listDocuments())


setup.done = lambda: __import__("fission180.neon_effects", fromlist=["x"]).overlay() is not None
setup.done_what = "Neon Lights' effects layer"


def run_check():
    from fission180 import diagnostics as diag

    def press():
        dialog = diagnostics()
        button = dialog.findChild(QtWidgets.QPushButton, "Fission180NeonSelfCheck")
        h.check("Diagnostics has a Neon self-check button", button is not None)
        if button is None:
            dialog.reject()
            return
        wi.click(button)
        box = dialog.findChild(QtWidgets.QPlainTextEdit)
        s["report"] = box.toPlainText()
        dialog.reject()

    h.when(lambda: diagnostics() is not None, press, "the Diagnostics window", timeout_s=600)
    diag.show()


run_check.done = lambda: "report" in s and diagnostics() is None
run_check.done_what = "the self-check's report and the Diagnostics window closed"
run_check.timeout_s = 600


def report():
    from fission180 import neon_effects, neon_settings

    text = s.get("report", "")
    print("[Fission 180] neon self-check report:\n%s" % text, flush=True)
    for needle in (
        "Neon self-check",
        "Sample part: 3000 faces",
        "effects off",
        "every effect on",
        "effects + Sounds on",
        "+ the rolling band",
        "The rolling band (Settings > Neon Lights > Moving scan band",
        "effects + Hologram on",
        "Effects over the 3D view: skipped",
        "3D-view part forced on",
        "Processor time per frame against effects off",
        "VERDICT: the effects",
        "Idle CPU",
        "Rim-light shader self-test:",
        "Neon parts switched off: none",
        "Platform:",
        "Graphics:",
    ):
        h.check("the report says %r" % needle, needle in text, text[-400:])
    h.check("the graphics card is named", "Graphics: unknown" not in text, text)
    h.check("the report has 120-frame runs (off, on, band, Sounds, Hologram, 3D-view part forced)",
            text.count("(120 frames)") == 6, text.count("(120 frames)"))
    import re

    on = [line for line in text.splitlines()
          if line.strip().startswith(("every effect on", "+ the rolling band", "effects + Sounds on"))
          and "frames)" in line]
    extra = []
    for line in on:
        paints = re.search(r"layer (\d+) paints", line)
        band = re.search(r"rolling band (\d+) frames", line)
        if paints:
            extra.append(int(paints.group(1)) - (int(band.group(1)) if band else 0))
    # (at most one repaint per block of 20 frames: the one that shows the effects switched on)
    h.check("orbiting never repaints the layer, except for the rolling band's own frames",
            len(extra) == 3 and all(e <= 6 for e in extra), on)
    h.check("Sounds are as set again", not neon_settings.get("Sounds"))
    h.check("the sample design is closed", sorted(App.listDocuments()) == s["docs"], App.listDocuments())
    h.check("the design is active again", App.ActiveDocument and App.ActiveDocument.Name == "LookUnchanged")
    h.check("Hologram is off again", not neon_settings.get("Hologram"))
    h.check("the effects layer is back as set", neon_effects.overlay() is not None
            and not neon_effects._state["force_active"])


def back_to_dark():
    lc.set_look("dark")


h.run("neon_effects_selfcheck", [setup, run_check, report, back_to_dark], paced_by="state")
