# SPDX-License-Identifier: LGPL-2.1-or-later
"""What the body glow costs (plan task B6, Global Constraints: the effects may cost at most
10% of a frame; design 6.6).

A part of 3,000 faces and 6,000 edges, in Neon Lights, is orbited 60 frames at a time with
Glow on and with Glow off, three rounds each; each frame is drawn at once (QWidget.grab draws
the 3D view) and its CPU time measured with time.thread_time. The middle frame time with Glow
on may be at most 10% above the one with it off (the lowest of the three rounds of each, so a
busy moment of the machine does not count). The numbers are printed as notes.
"""

import time

import FreeCAD as App
import FreeCADGui as Gui
import Part
from PySide import QtGui

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import look_compare as lc

BUDGET = 1.10
s = {}


def setup():
    from fission180 import neon_settings

    Gui.activateWorkbench("Fission180Workbench")
    lc.set_look("dark")
    neon_settings.put("Hologram", False)
    neon_settings.put("Glow", True)
    neon_settings.put("Effects", True)
    doc = App.newDocument("GlowSpeed")
    boxes = []
    for i in range(25):
        for j in range(20):
            boxes.append(Part.makeBox(3, 3, 2 + (i * j) % 5, App.Vector(i * 4, j * 4, 0)))
    part = doc.addObject("Part::Feature", "Many")
    part.Shape = Part.makeCompound(boxes)
    doc.recompute()
    h.note("info", "faces %d, edges %d" % (len(part.Shape.Faces), len(part.Shape.Edges)))
    Gui.ActiveDocument.ActiveView.viewIsometric()
    h.fit()


def to_neon():
    lc.set_look("neon")


to_neon.done = lambda: __import__("fission180.theme").theme.is_neon()
to_neon.done_what = "Neon Lights to be on"


def orbit(frames=60):
    """(mean, middle) CPU seconds per frame over `frames` frames of a slow orbit."""
    from pivy import coin

    widget = h.gl_widget()
    camera = h.view().getCameraNode()
    step = coin.SbRotation(coin.SbVec3f(0, 0, 1), 0.01)
    for _ in range(5):
        widget.grab()
    times = []
    for _ in range(frames):
        camera.orientation = camera.orientation.getValue() * step
        start = time.thread_time()
        widget.grab()
        times.append(time.thread_time() - start)
    times.sort()
    return sum(times) / frames, times[frames // 2]


def measure():
    from fission180 import neon, neon_settings, neon_view

    rounds = {True: [], False: []}
    for _ in range(3):
        for glow in (True, False):
            neon_settings.put("Glow", glow)
            neon.refresh()
            QtGui.QGuiApplication.processEvents()
            if glow:
                found = neon_view.neon_nodes(h.view().getSceneGraph())
                h.check("(the glow is drawn)", neon_view.GLOW_NODE in found, found)
            rounds[glow].append(orbit())
    for glow in (True, False):
        h.note(
            "info",
            "Glow %s: CPU per frame, mean/middle (ms): %s"
            % ("on" if glow else "off", ", ".join("%.2f/%.2f" % (a * 1000, b * 1000) for a, b in rounds[glow])),
        )
    on = min(r[1] for r in rounds[True])
    off = min(r[1] for r in rounds[False])
    ratio = on / max(off, 1e-6)
    h.note("info", "Glow on/off: %.3f (%.2f vs %.2f ms)" % (ratio, on * 1000, off * 1000))
    h.speed_check("the glow costs at most 10%% of a frame (%.3f)" % ratio, ratio <= BUDGET, (on, off))
    neon_settings.put("Glow", True)
    neon.refresh()


def back_to_dark():
    lc.set_look("dark")


def dark_measured():
    mean, middle = orbit()
    h.note("info", "Dark: CPU per frame, mean/middle (ms): %.2f/%.2f" % (mean * 1000, middle * 1000))


h.run("neon_glow_speed", [setup, to_neon, measure, back_to_dark, dark_measured], paced_by="state")
