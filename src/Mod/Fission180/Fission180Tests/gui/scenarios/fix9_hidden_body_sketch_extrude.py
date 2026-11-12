# SPDX-License-Identifier: LGPL-2.1-or-later
"""Luca's very first steps with the release candidate (wave 7, fix-9), by real input only, with
a person's defaults (Home > New Design, grid snap, scale at first dimension, the layout grid, an
undo step left open fails it):

  1  Create Sketch on the XY (top) plane, a 2-point rectangle 100 x 100 from the origin,
     Finish Sketch.
  2  Extrude it: a cube, Body1.
  3  Hide Body1 (its eye in the browser).
  4  Create Sketch on the XY plane again, a larger square 600 x 600 from the origin (it holds
     the cube's footprint), Finish Sketch. Bug A: Sketch 2 did not show, its eye open.
  5  Show Body1: Sketch 2 showed. Hide Body1 again: Sketch 2 stayed.
  6  Extrude Sketch 2's square. Bug B: the dialog proposed Cut, listed Body1 under Bodies to
     Cut (ticked) and drew the hidden Body1 being cut, red. Fusion leaves a hidden body alone:
     not proposed, not listed, not drawn, not changed. Expected: New Body, no Bodies to Cut
     row, Body1 stays hidden and as it was. Cut picked by hand: nothing is cut, the dialog
     says that hidden bodies are not cut and names Body1 (wave 7, fix-10); New Body again.

Then the same design a person goes on with: undo / redo of the extrude and of a hide, save,
close and reopen (the hidden body stays hidden, the sketch keeps its eye).
"""

import os
import tempfile

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import book_components_steps as k
from Fission180Tests.gui.fix9_steps import (
    body,
    body_hidden,
    drawn,
    eye,
    ok,
    one_extrude,
    owner,
    rectangle,
    sketch,
    sketch_seen,
    where,
    zoom_out,
)
from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import replay_f_steps as r
from Fission180Tests.gui import timeline_input as ti

V = App.Vector
S = {}
CUBE = 100.0
BIG = 600.0
HIGH = 50.0


def s1_start():
    h.check("1 the sketch is in the design", r.sk() is not None)


def e1_check():
    p = r.extrude_panel()
    h.check(
        "2 the first extrude proposes New Body",
        p.operation.currentText() == "New Body",
        (p.operation.currentText(), p.message.text()),
    )


def cube_made():
    b = body("Body1")
    h.check("2 Body1 is made", b is not None, [x.Label for x in k.bodies_of("")])
    if b is None:
        return
    h.check("2 Body1 is a 100 x 100 x 100 cube", r.near(k.volume(b), CUBE**3), k.volume(b))
    S["cube"] = k.volume(b)
    S["tip"] = b.Tip.Name
    h.check("2 Body1 is shown", eye("Body1") is True and drawn(b))
    h.check("3 Body1's eye", ti.click_eye("Body1"))


def hidden():
    b = body("Body1")
    body_hidden("3", b)
    h.shot("3-body1-hidden")


def s2_in():
    sk = r.sk()
    S["s2"] = sk.Label if sk is not None else None
    h.check("4 Sketch 2 is open", sk is not None, where(sk))
    S["s2_where"] = where(sk)
    h.check("4 Sketch 2 is not in the hidden Body1", owner(sk) is not body("Body1"), where(sk))


def bug_a():
    """Finish Sketch: Sketch 2 shows, eye open, Body1 still hidden."""
    sk = sketch("Sketch 2")
    h.check("4 Sketch 2 exists", sk is not None)
    if sk is None:
        return
    h.check("4 the Sketches folder's eye is open", eye("Sketches") is True, eye("Sketches"))
    sketch_seen("4 (bug A)", "Sketch 2", V(BIG * 0.6, BIG * 0.6, 0))
    body_hidden("4", body("Body1"))
    h.shot("4-sketch2-finished")


def show_body1():
    h.check("5 Body1's eye", ti.click_eye("Body1"))


show_body1.done = lambda: drawn(body("Body1"))
show_body1.done_what = "Body1 is shown"


def body1_shown():
    h.check("5 Body1's eye is open", eye("Body1") is True, eye("Body1"))
    sketch_seen("5 Body1 shown", "Sketch 2", V(BIG * 0.6, BIG * 0.6, 0))
    h.shot("5-body1-shown")
    h.check("5 Body1's eye again", ti.click_eye("Body1"))


body1_shown.done = lambda: not drawn(body("Body1"))
body1_shown.done_what = "Body1 is hidden again"


def body1_hidden_again():
    body_hidden("5 hidden again", body("Body1"))
    sketch_seen("5 hidden again", "Sketch 2", V(BIG * 0.6, BIG * 0.6, 0))
    h.shot("5-body1-hidden-again")


def bug_b():
    """The dialog with Sketch 2's square picked and a distance: New Body, nothing to cut,
    Body1 neither listed nor drawn."""
    p = r.extrude_panel()
    b = body("Body1")
    h.check(
        "6 (bug B) Extrude proposes New Body, not Cut",
        p.operation.currentText() == "New Body",
        (p.operation.currentText(), p.message.text()),
    )
    h.check(
        "6 (bug B) no Bodies to Cut row",
        not p.bodies_label.isVisible() and not p.fields["bodies"].widget.isVisible(),
        (p.bodies_label.text(), p.fields["bodies"].button.text(), p.bodies_names.text()),
    )
    boxes = [
        x.text()
        for x in p.bodies_checks.findChildren(__import__("PySide").QtWidgets.QCheckBox)
        if x.isVisible()
    ]
    h.check("6 (bug B) Body1 is not in a list of bodies", not boxes, boxes)
    h.check("6 (bug B) Body1 stays hidden", eye("Body1") is False and not drawn(b), eye("Body1"))
    h.check(
        "6 (bug B) Body1 still ends with its cube (nothing built in it)",
        b.Tip is not None and b.Tip.Name == S["tip"],
        b.Tip.Label if b.Tip is not None else None,
    )
    h.check(
        "6 (bug B) the preview is not in Body1",
        p.target is None or owner(p.target) is not b,
        p.target.Label if p.target is not None else None,
    )
    h.shot("6-extrude-sketch2")
    h.check("6 Cut chosen by hand", ui.choose(p.operation, "Cut"))


def cut_by_hand():
    """Sketch 2 is in an empty body beside the hidden Body1 (fix-9): a Cut picked by hand
    reaches only the hidden Body1. Nothing is cut and the dialog says why, naming Body1, in
    the words every tool uses (wave 7, fix-10: Revolve said "There is no solid to cut yet"
    in the same place)."""
    p = r.extrude_panel()
    h.caught_up(p)
    b = body("Body1")
    text = p.message.text()
    h.check(
        "6 Cut: hidden bodies are not cut, naming Body1",
        "Hidden bodies are not cut (Body1 is hidden)" in text,
        text,
    )
    h.check(
        "6 Cut: nothing built in Body1",
        b.Tip is not None and b.Tip.Name == S["tip"],
        b.Tip.Label if b.Tip is not None else None,
    )
    h.check("6 Cut: Body1 stays hidden", eye("Body1") is False and not drawn(b), eye("Body1"))
    h.check("6 Cut: Body1 is unchanged", r.near(k.volume(b), S["cube"]), k.volume(b))
    h.shot("6-cut-refused")
    h.check("6 New Body chosen again", ui.choose(p.operation, "New Body"))


def new_body_again():
    p = r.extrude_panel()
    h.caught_up(p)
    h.check("6 New Body: the message is gone", not p.message.text(), p.message.text())


def new_body_made():
    b = body("Body1")
    h.check("6 Body1 is unchanged", r.near(k.volume(b), S["cube"]), k.volume(b))
    h.check("6 Body1 stays hidden", eye("Body1") is False and not drawn(b), eye("Body1"))
    b2 = body("Body2")
    h.check("6 a new body, Body2", b2 is not None, [x.Label for x in k.bodies_of("")])
    if b2 is not None:
        h.check(
            "6 Body2 is the 600 x 600 x 50 slab",
            r.near(k.volume(b2), BIG * BIG * HIGH),
            k.volume(b2),
        )
        h.check("6 Body2 is shown", eye("Body2") is True and drawn(b2))
    h.check("6 Sketch 2 hides with its extrude (Fusion)", eye("Sketch 2") is False)
    r.no_open_step("Extrude")
    h.shot("6-new-body")


def undo_extrude():
    r.undo()


undo_extrude.done = lambda: body("Body2") is None
undo_extrude.done_what = "Body2 is gone"


def after_undo():
    body_hidden("7 after undo", body("Body1"))
    sketch_seen("7 after undo", "Sketch 2", V(BIG * 0.6, BIG * 0.6, 0))
    r.redo()


after_undo.done = lambda: body("Body2") is not None
after_undo.done_what = "Body2 is back"


def after_redo():
    body_hidden("7 after redo", body("Body1"))
    h.check("7 after redo: Body2 shown", drawn(body("Body2")))
    h.check("7 Body1's eye (show it)", ti.click_eye("Body1"))


after_redo.done = lambda: drawn(body("Body1"))
after_redo.done_what = "Body1 is shown"


def shown_again():
    """Body1 shown with its eye: the cube and the slab, Sketch 2 hidden by its extrude."""
    h.check("7 Body1's eye is open", eye("Body1") is True, eye("Body1"))
    h.check("7 Body1 is the cube, untouched", r.near(k.volume(body("Body1")), S["cube"]))
    h.check("7 Body2 shown too", drawn(body("Body2")))
    h.check("7 Sketch 2 hidden by its extrude", eye("Sketch 2") is False, eye("Sketch 2"))
    h.shot("7-body1-shown")
    h.check("7 Body1's eye again (hide it)", ti.click_eye("Body1"))


shown_again.done = lambda: not drawn(body("Body1"))
shown_again.done_what = "Body1 is hidden again"


def save_close():
    body_hidden("8 before saving", body("Body1"))
    S["path"] = os.path.join(tempfile.mkdtemp(prefix="fission180-fix9-"), "Luca.FCStd")
    d = App.ActiveDocument
    d.saveAs(S["path"])
    S["name"] = d.Name
    App.closeDocument(d.Name)


save_close.done = lambda: S.get("name") not in App.listDocuments()
save_close.done_what = "the design is closed"


def reopen():
    App.openDocument(S["path"])


reopen.done = lambda: App.ActiveDocument is not None and body("Body1") is not None
reopen.done_what = "the design is open again"


def reopened():
    h.settle()
    body_hidden("8 reopened", body("Body1"))
    h.check("8 reopened: Body2 shown", drawn(body("Body2")))
    h.check("8 reopened: Body1 is the cube", r.near(k.volume(body("Body1")), S["cube"]))
    h.shot("8-reopened")
    Gui.getDocument(App.ActiveDocument.Name).Modified = False


steps = list(r.START)
steps += r.create_sketch("XY_Plane", "", "s1")
steps += [s1_start]
steps += rectangle("s1", V(0, 0, 0), V(CUBE, CUBE, 0), [0, 0, CUBE, CUBE])
steps += [r.named(r.finish_sketch, "s1_finish")]
steps += one_extrude("e1", V(CUBE * 0.5, CUBE * 0.5, 0), CUBE)
steps += [e1_check, r.named(ok, "e1_ok"), cube_made, hidden]
steps += r.create_sketch("XY_Plane", "", "s2")
steps += [s2_in, zoom_out(V(BIG, BIG, 0))]
steps += rectangle("s2", V(0, 0, 0), V(BIG, BIG, 0), [0, 0, BIG, BIG])
steps += [r.named(r.finish_sketch, "s2_finish"), bug_a]
steps += [show_body1, body1_shown, body1_hidden_again]
steps += one_extrude("e2", V(BIG * 0.6, BIG * 0.6, 0), HIGH)
steps += [bug_b, cut_by_hand, new_body_again, r.named(ok, "e2_ok"), new_body_made]
steps += [undo_extrude, after_undo, after_redo, shown_again, save_close, reopen, reopened]

h.run("fix9_hidden_body_sketch_extrude", steps, paced_by="state")
