# SPDX-License-Identifier: LGPL-2.1-or-later
"""The Draft dialog's two selection boxes (book parity report, Project 6 Play Brick, lines
1226-1230 and 1263-1264):

  "The two selection boxes are fiddly: after picking the pull face, clicking the Faces box
   and a face sometimes did nothing, and an OK refused for missing faces cleared the pull
   direction."
  "Draft with many faces ... some of my clicks toggled faces off."

The book's brick: a box 31.8 x 15.8 x 9.6 with a stud 4.8 across and 1.8 high on top (the
design-step builder). Then only real input: MODIFY > Draft, the top face as the pull
direction, the Faces box clicked (it is the active one already: Fusion's box stays active
when it is clicked again), a side face, OK with no face (refused: the reason is said and the
pull direction STAYS), a click on the pull direction's own face while faces are picked
(this was the report's trouble: it dropped the pull direction and made its box the active
one, so the next face clicked became the pull direction instead of a face to draft; now it
stays and the reason is said next to the pointer), a picked face clicked again (dropped, as
in Fusion: that is how a face is taken out), 1 degree, OK. Checked on the model: the volume
of the drafted brick.
"""

import math

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import shell_draft_steps as sd
from Fission180Tests.gui import widget_input as w

V = App.Vector
CTRL = __import__("PySide").QtCore.Qt.ControlModifier
S = {}
L, W, H = 31.8, 15.8, 9.6
BOX = L * W * H
STUD = math.pi * 2.4**2 * 1.8
TOP = V(20.0, 10.0, H)
FRONT = V(16.0, 0.0, 5.0)
RIGHT = V(L, 8.0, 5.0)

STEPS = (
    {"op": "sketch", "id": "s1", "plane": "XY", "geometry": [{"rect": [0, 0, L, W]}]},
    {"op": "extrude", "id": "e1", "profile": "s1", "distance": H},
    {
        "op": "sketch",
        "id": "s2",
        "plane": "XY",
        "offset": H,
        "geometry": [{"circle": [3.9, 3.9, 2.4]}],
    },
    {"op": "extrude", "id": "e2", "profile": "s2", "distance": 1.8, "operation": "join"},
)


def tan(a):
    return math.tan(math.radians(a))


def vol():
    return h.solid_volume()


def panel():
    return sd.draft_panel()


def setup():
    from Fission180Tests.golden.builder import Builder

    Gui.activateWorkbench("Fission180Workbench")
    doc = App.newDocument("PlayBrick")
    builder = Builder(doc)
    for step in STEPS:
        builder.run(step)
        doc.recompute()
    h.fit()


def built():
    h.check("the brick with its stud", abs(vol() - BOX - STUD) < 1e-6, vol())
    Gui.Selection.clearSelection()
    sd.modify_menu("Draft")


def click_top():
    p = panel()
    if h.check("Draft waits for the pull direction", p is not None and p.active == "plane", p):
        h.click(TOP)


def pull_taken():
    p = panel()
    if p is None:
        h.check("Draft dialog", False)
        return
    h.check("the top face is the pull direction", p.plane_ref is not None, p.plane_ref)
    h.check("the Faces box takes the clicks now", p.active == "faces", p.active)
    S["pull"] = p.plane_box.button.text()
    # the report's step: click the Faces box (already the active one), then a face
    w.click(p.faces_box.button)


def faces_box_clicked():
    p = panel()
    if p is None:
        h.check("Draft dialog", False)
        return
    h.check("the Faces box is still the active one", p.active == "faces", p.active)
    h.check("and shows it (pressed in)", p.faces_box.button.isChecked())
    h.check("the pull direction is still there", p.plane_ref is not None, p.plane_ref)
    h.click(FRONT)


def front_picked():
    p = panel()
    if p is None:
        h.check("Draft dialog", False)
        return
    h.check("the face clicked after the Faces box is picked", len(p.names()) == 1, p.names())
    h.click(TOP)  # the pull direction's own face, while faces are picked


def pull_face_clicked_again():
    from fission180 import commands, draft_ui

    p = panel()
    if p is None:
        h.check("Draft dialog", False)
        return
    h.check(
        "a click on the pull face does NOT clear the pull direction (it did)",
        p.plane_ref is not None and p.plane_box.button.text() == S["pull"],
        (p.plane_ref, p.plane_box.button.text()),
    )
    h.check("the Faces box stays the active one", p.active == "faces", p.active)
    h.check("the picked face stays", len(p.names()) == 1, p.names())
    h.check("why is said next to the pointer", commands._TOLD["msg"] == draft_ui.PULL_KEPT)
    h.click(FRONT)  # again: dropped (Fusion: click a picked face to take it out)


def front_dropped():
    p = panel()
    if p is None:
        h.check("Draft dialog", False)
        return
    h.check("clicked again: dropped", len(p.names()) == 0, p.names())
    h.check("the pull direction stays", p.plane_ref is not None, p.plane_ref)
    h.check("the brick is as it was", abs(vol() - BOX - STUD) < 1e-6, vol())
    h.task_button("OK")  # with no face: refused


def refused_keeps_pull():
    p = panel()
    if not h.check("OK with no face: the dialog stays open", p is not None):
        return
    text = p.message.text()
    h.check("and says what is missing", "Pick the faces to draft" in text, text)
    h.check(
        "the pull direction is NOT cleared (the report: it was)",
        p.plane_ref is not None and p.plane_box.button.text() == S["pull"],
        (p.plane_ref, p.plane_box.button.text()),
    )
    h.check("the Faces box is the active one", p.active == "faces", p.active)
    h.click(FRONT)


def front_again():
    p = panel()
    if p is None:
        h.check("Draft dialog", False)
        return
    h.check("the next click picks the face", len(p.names()) == 1, p.names())
    h.click(RIGHT)


def two_faces():
    p = panel()
    if p is None:
        h.check("Draft dialog", False)
        return
    h.check("a second face right after it", len(p.names()) == 2, p.names())
    h.check("still the same pull direction", p.plane_box.button.text() == S["pull"])
    h.check("the angle is 1 degree", abs(p.angle.value() - 1.0) < 1e-9, p.angle.value())
    h.shot("two_faces")
    h.task_button("OK")


two_faces.timeout_s = 120


def drafted():
    h.check("dialog closed", panel() is None)
    shape = h.body().Shape
    h.check("a valid solid", shape.isValid() and len(shape.Solids) == 1)
    # the two walls lean out 1 degree about their top edges (the pull face is the top):
    # each adds a wedge H^2 tan / 2 along its length, and the corner between the two
    # wedges is filled by a pyramid H^3 tan^2 / 3
    t = tan(1.0)
    wedge = (L + W) * H * H * t / 2.0 + H**3 * t * t / 3.0
    change = abs(vol() - BOX - STUD)
    h.check("the two walls are drafted 1 degree", abs(change - wedge) < 1e-3, (change, wedge))
    h.check("one Draft step", len(sd.drafts()) == 1, sd.drafts())
    S["v1"] = vol()
    h.press("z", CTRL)


drafted.timeout_s = 120


def undone():
    h.check("Ctrl+Z: the plain brick", abs(vol() - BOX - STUD) < 1e-6, vol())
    h.press("y", CTRL)


def redone():
    h.check("Ctrl+Y: drafted again", abs(vol() - S["v1"]) < 1e-6, vol() - S["v1"])


h.run(
    "book_modifyb_draft",
    [
        setup,
        built,
        click_top,
        pull_taken,
        faces_box_clicked,
        front_picked,
        pull_face_clicked_again,
        front_dropped,
        refused_keeps_pull,
        front_again,
        two_faces,
        drafted,
        undone,
        redone,
    ],
    paced_by="state",
)
