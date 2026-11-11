# SPDX-License-Identifier: LGPL-2.1-or-later
"""Offset Face on a modeled thread (book parity report, Project 7 Geocache, lines 1301-1305):

  "MODIFY > Offset Face -0.25 mm on the thread: Fission's modeled thread is 19 B-spline
   faces (Fusion: 4 faces); the Offset Face dialog shows 'Work in progress on complex shapes'
   and the clicks made no selection; nothing was offset."

The book's screw: a cylinder 33 mm across and 16 high with a modeled M33x3.5 thread (made by
the design-step builder). Then real input: MODIFY > Offset Face, one click on the thread,
-0.25 typed, OK.

A click on any face of the thread (a flank, a root, the crest) now means the whole thread,
as Fusion's four thread faces are picked together: the Thread step itself moves all its
faces by the distance (the crest and the root along the radius, the flanks apart), and stays
one step in the timeline. Checked: the dialog says so, the part loses the layer the faces
moved through (their area times 0.25 mm, 2,488 mm2: about 615 mm3), the thread is still one
step and holds -0.25, Ctrl+Z / Ctrl+Y, the same from Press Pull (Q), and a distance that
would leave nothing between the grooves (-0.5 mm) is refused with the reason in the dialog.
"""

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import direct_steps as d

V = App.Vector
CTRL = __import__("PySide").QtCore.Qt.ControlModifier
S = {}

STEPS = (
    {"op": "sketch", "id": "s1", "plane": "XY", "geometry": [{"circle": [0, 0, 16.5]}]},
    {"op": "extrude", "id": "e1", "profile": "s1", "distance": 16},
    {
        "op": "thread",
        "id": "t1",
        "faces": {"type": "cylinder", "radius": 16.5, "count": 1},
        "modeled": True,
    },
)
ON_THREAD = V(11.6, -11.6, 7.0)  # a point of the threaded surface, towards the camera


def vol():
    return h.solid_volume()


def panel():
    return b.active_panel()


def the_thread():
    from fission180 import thread

    return [o for o in App.ActiveDocument.Objects if thread.is_thread(o)][0]


def setup():
    from Fission180Tests.golden.builder import Builder

    Gui.activateWorkbench("Fission180Workbench")
    doc = App.newDocument("Geocache")
    builder = Builder(doc)
    for step in STEPS:
        builder.run(step)
        doc.recompute()
    h.fit()


setup.timeout_s = 120


def built():
    from fission180 import thread

    step = the_thread()
    shape = step.Shape
    own = [f for f in shape.Faces if thread.own_face(step, f)]
    S["v0"] = vol()
    S["area"] = sum(f.Area for f in own)
    S["steps"] = b.timeline_titles()
    h.check("the modeled M33x3.5 thread", shape.isValid() and len(own) >= 4, len(own))
    h.check("its faces: every face but the two ends", len(own) == len(shape.Faces) - 2, len(own))
    Gui.Selection.clearSelection()
    d.ribbon_menu("MODIFY", "Offset Face")


def click_thread():
    p = panel()
    if h.check("the Offset Face dialog is open", p is not None and p.title == "Offset Face", p):
        h.click(ON_THREAD)


def thread_taken():
    p = panel()
    if p is None:
        h.check("Offset Face dialog", False)
        return
    h.check(
        "the click took the thread (the report: no selection)", p.target is the_thread(), p.mode
    )
    text = p.what.text()
    h.check(
        "the dialog says that the whole thread moves",
        "all of the thread's faces move together" in text and "looser" in text,
        text,
    )
    b.type_into(p.field.widget, "-0.25")


thread_taken.timeout_s = 120


def looser():
    p = panel()
    if p is None:
        h.check("Offset Face dialog", False)
        return
    removed = S["v0"] - vol()
    first_order = S["area"] * 0.25
    h.check(
        "the preview: the thread's faces moved 0.25 mm into the part",
        0.97 * first_order < removed < 1.0 * first_order,
        (removed, first_order),
    )
    h.check("no error", "⚠" not in p.message.text(), p.message.text())
    h.shot("offset")
    h.task_button("OK")


looser.timeout_s = 120


def kept():
    from fission180 import thread

    h.check("dialog closed", panel() is None)
    step = the_thread()
    h.check("the thread holds -0.25 mm", abs(thread.face_offset(step) + 0.25) < 1e-9)
    h.check("and is still one step: nothing was added", b.timeline_titles() == S["steps"])
    shape = h.body().Shape
    h.check("a valid solid", shape.isValid() and len(shape.Solids) == 1)
    S["v1"] = vol()
    # the crest is 0.25 nearer the axis (a cylinder face of the thread)
    crests = [f for f in shape.Faces if f.Surface.__class__.__name__ == "Cylinder"]
    radius = crests[0].Surface.Radius if crests else 0.0
    S["crest"] = radius
    h.check("the crest came in", 16.0 < radius < 16.3, radius)
    h.press("z", CTRL)


kept.timeout_s = 120


def undone():
    h.check("Ctrl+Z: the thread as it was", abs(vol() - S["v0"]) < 1e-6, vol() - S["v0"])
    h.press("y", CTRL)


undone.timeout_s = 120


def redone():
    h.check("Ctrl+Y: the looser thread", abs(vol() - S["v1"]) < 1e-6, vol() - S["v1"])
    Gui.Selection.clearSelection()
    h.press("q")


redone.timeout_s = 120


def press_pull_click():
    p = panel()
    if h.check("Press Pull is open", p is not None and p.title == "Press Pull", p):
        h.click(ON_THREAD)


def press_pull_too_far():
    p = panel()
    if p is None:
        h.check("Press Pull dialog", False)
        return
    h.check("Press Pull on the thread: the same", p.target is the_thread(), p.mode)
    h.check("it shows the thread's -0.25", abs(p.field.value() + 0.25) < 1e-9, p.field.value())
    b.type_into(p.field.widget, "-0.5")


press_pull_too_far.timeout_s = 120


def refused():
    p = panel()
    if p is None:
        h.check("Press Pull dialog", False)
        return
    text = p.message.text()
    h.check(
        "-0.5 mm would leave nothing between the grooves: said in the dialog",
        "nothing would be left between its grooves" in text,
        text,
    )
    h.task_button("Cancel")


refused.timeout_s = 120


def cancelled():
    from fission180 import thread

    h.check("Cancel: still -0.25", abs(thread.face_offset(the_thread()) + 0.25) < 1e-9)
    h.check("and the same solid", abs(vol() - S["v1"]) < 1e-6, vol() - S["v1"])


cancelled.timeout_s = 120

h.run(
    "book_modifyb_thread_offset",
    [
        setup,
        built,
        click_thread,
        thread_taken,
        looser,
        kept,
        undone,
        redone,
        press_pull_click,
        press_pull_too_far,
        refused,
        cancelled,
    ],
    paced_by="state",
)
