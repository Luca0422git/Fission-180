# SPDX-License-Identifier: LGPL-2.1-or-later
"""No body in the browser before there is anything solid (Luca, 2026-11-02: "when making a
sketch, a body appears in the browser. but there are no bodies?"). Fusion's design has no
body until the first solid feature (Extrude's New Body adds the Bodies folder); SciForge
makes a PartDesign Body to hold the first sketch, and the browser listed it at once. Now
such a body is not listed until it holds a solid step; its sketches are, under Sketches.
Only real input (saving and reopening through FreeCAD, as the other scenarios).

  A  A new design, Create Sketch ("Click a plane or a flat face"): the design holds the body
     SciForge made for the sketch, the browser shows Origin (the planes to click) but no
     Bodies folder. Esc: still none (the unlisted body stays and takes the next sketch).
  B  Create Sketch on XY, a rectangle, Finish Sketch: Sketches > Sketch 1, no Bodies, the
     same one body in the design.
  C  Undo back to before the sketch (no Sketches, no Bodies) and to the empty design (no
     body at all), Redo all of it: the sketch is back, still no Bodies.
  D  Saved, closed, opened again: the same (Origin, Sketches > Sketch 1, no Bodies).
  E  E, 10, OK: Bodies > Body, between Origin and Sketches (the box 40 x 30 x 10 = 12000).
     Ctrl+Z: no Bodies again; Ctrl+Y: back.
  F  The body hidden with its eye: still listed (it has a solid).
  G  A component (New Component, Arm): Origin only; a sketch in it: Origin, Sketches; an
     extrude: Bodies > Body1 (20 x 20 x 5 = 2000). The root's Body is still listed.
"""

import os
import tempfile

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from SciForgeTests.gui import arrow_input as arrows
from SciForgeTests.gui import component_steps as cs
from SciForgeTests.gui import harness as h
from SciForgeTests.gui import plane_input as pl
from SciForgeTests.gui import timeline_input as t

s = {}
BOX = 12000.0
SMALL = 2000.0


def doc():
    return App.ActiveDocument


def bodies():
    return sorted(doc().findObjects("PartDesign::Body"), key=lambda o: o.ID)


def top():
    return cs.top_labels()


def sketch_rows():
    return t.children("Sketches")


def no_body_rows(where):
    rows = top()
    h.check("%s: no Bodies folder" % where, "Bodies" not in rows, rows)
    h.check(
        "%s: no body row" % where,
        not any((t.tree().row(b.Label) is not None) for b in bodies()),
        t.labels(),
    )


def picker_open():
    return t.dialog_open()


# -- A: Create Sketch on a new design -------------------------------------------------------------
def a_new():
    Gui.activateWorkbench("SciForgeWorkbench")
    App.newDocument("EmptyBody")
    h.fit()


def a_create_sketch():
    h.check("A: a new design has no body", bodies() == [], [b.Name for b in bodies()])
    h.ribbon("Create Sketch")


a_create_sketch.done = picker_open
a_create_sketch.done_what = "Create Sketch to wait for a plane"


def a_picker():
    h.check("A: the design holds the body made for the sketch", len(bodies()) == 1)
    no_body_rows("A, Create Sketch open")
    h.check("A: the Origin is listed (planes to click)", "Origin" in top(), top())
    h.shot("A-create-sketch")
    h.press(QtCore.Qt.Key_Escape)


a_picker.done = lambda: not picker_open()
a_picker.done_what = "Esc to close Create Sketch"


def a_cancelled():
    no_body_rows("A, after Esc")
    s["body"] = bodies()[0].Name if bodies() else None
    h.check("A: the unlisted body is still there", s["body"] is not None)
    h.ribbon("Create Sketch")


a_cancelled.done = picker_open
a_cancelled.done_what = "Create Sketch to wait for a plane again"


# -- B: a sketch, no body ---------------------------------------------------------------------------
def b_pick():
    h.check("B: Create Sketch made no second body", len(bodies()) == 1, [b.Name for b in bodies()])
    pl.click_square("XY_Plane")


b_pick.done = lambda: h.in_sketch() is not None
b_pick.done_what = "the sketch to open"


def b_draw():
    sk = h.in_sketch()
    s["sketch"] = sk.Name
    h.check("B: the sketch went into that body", sk.getParentGeoFeatureGroup().Name == s["body"])
    no_body_rows("B, sketching")
    h.draw_rectangle(sk, 0, 0, 40, 30)


def b_finish():
    h.ribbon("Finish Sketch")


b_finish.done = lambda: h.in_sketch() is None
b_finish.done_what = "the sketch to close"


def sketch_only(where):
    no_body_rows(where)
    h.check(
        "%s: Origin, then Sketches" % where,
        top() == ["Document Settings", "Named Views", "Origin", "Sketches"],
        top(),
    )
    h.check("%s: Sketches > Sketch 1" % where, sketch_rows() == ["Sketch 1"], sketch_rows())
    h.check("%s: one body in the design" % where, len(bodies()) == 1, [b.Name for b in bodies()])


def b_sketch_only():
    sketch_only("B")
    h.check("B: the timeline has Sketch 1", t.titles() == ["Sketch 1"], t.titles())
    names = list(doc().UndoNames)
    # the undo steps of the sketch, and the body's own ("Add a Body") after them
    s["sketch_undos"] = names.index("Create Sketch") + 1 if "Create Sketch" in names else 0
    s["all_undos"] = len(names)
    h.check("B: the sketch's undo steps", s["sketch_undos"] > 0, names)
    h.shot("B-sketch-only")


# -- C: Undo and Redo ---------------------------------------------------------------------------------
def press_times(key, n):
    for _ in range(n):
        t.ctrl(key)
        h.settle("the app to settle after Ctrl+%s" % key.upper())


def c_undo_sketch():
    press_times("z", s["sketch_undos"])


def c_before_sketch():
    h.check("C: Undo took the sketch away", doc().getObject(s["sketch"]) is None)
    h.check("C: no Sketches folder", "Sketches" not in top(), top())
    no_body_rows("C, before the sketch")
    press_times("z", s["all_undos"] - s["sketch_undos"])


def c_empty_design():
    h.check("C: Undo to the empty design: no body", bodies() == [], [b.Name for b in bodies()])
    h.check("C: ... the browser as new", top() == ["Document Settings", "Named Views"], top())
    press_times("y", s["all_undos"])


def c_redone():
    h.check("C: Redo: the sketch is back", doc().getObject(s["sketch"]) is not None)
    sketch_only("C, Redo")


# -- D: saved and opened again ---------------------------------------------------------------------
def d_save():
    s["path"] = os.path.join(tempfile.mkdtemp(prefix="sciforge-empty-body-"), "EmptyBody.FCStd")
    doc().saveAs(s["path"])
    App.closeDocument(doc().Name)


def d_open():
    App.openDocument(s["path"])
    h.fit()


def d_reopened():
    sketch_only("D, opened again")


# -- E: the first solid makes the body -------------------------------------------------------------
def e_extrude():
    h.fit()
    h.press("e")


def e_distance():
    h.check("E: Extrude open", arrows.type_distance("10"))
    h.task_button("OK")


e_distance.done = lambda: not t.dialog_open()
e_distance.done_what = "the Extrude dialog to close"


def body_listed(where):
    body = doc().getObject(s["body"])
    h.check("%s: the box is in that body" % where, t.near(t.volume(body), BOX), t.volume(body))
    h.check(
        "%s: Origin, Bodies, Sketches" % where,
        top() == ["Document Settings", "Named Views", "Origin", "Bodies", "Sketches"],
        top(),
    )
    rows = cs.children_of(["Bodies"])
    h.check("%s: Bodies > %s" % (where, body.Label), rows == [body.Label], rows)


def e_body():
    body_listed("E")
    h.shot("E-extruded")
    t.ctrl("z")


def e_undone():
    body = doc().getObject(s["body"])
    h.check("E: Ctrl+Z takes the solid away", t.volume(body) == 0.0, t.volume(body))
    no_body_rows("E, Ctrl+Z")
    h.check("E: Sketch 1 still listed", sketch_rows() == ["Sketch 1"], sketch_rows())
    t.ctrl("y")


def e_redone():
    body_listed("E, Ctrl+Y")


# -- F: a hidden body with a solid stays listed -------------------------------------------------------
def f_hide():
    t.click_eye(doc().getObject(s["body"]).Label)


def f_hidden():
    body = doc().getObject(s["body"])
    h.check("F: the body is hidden", not t.shown(body))
    h.check("F: ... and still listed", cs.children_of(["Bodies"]) == [body.Label], cs.children_of(["Bodies"]))
    t.click_eye(body.Label)


def f_shown():
    h.check("F: shown again", t.shown(doc().getObject(s["body"])))
    h.click_empty()  # (nothing selected: New Component does not take the body along)


# -- G: a component ------------------------------------------------------------------------------------
def g_new():
    h.ribbon("New Component")


def g_dialog():
    panel = cs.new_component_panel()
    if h.check("G: New Component dialog", panel is not None):
        h.check("G: From Bodies off", not panel.from_bodies.isChecked())
        cs.type_name("Arm")


def g_ok():
    h.task_button("OK")


def g_made():
    h.check("G: Arm made and active", cs.active_label() == "Arm", cs.active_label())
    h.check("G: Arm holds its Origin only", cs.children_of(["Arm"]) == ["Origin"], cs.children_of(["Arm"]))
    s["count"] = len(bodies())
    h.fit()
    h.ribbon("Create Sketch")


g_made.done = picker_open
g_made.done_what = "Create Sketch to wait for a plane in Arm"


def g_pick():
    pl.click_square("XY_Plane")


g_pick.done = lambda: h.in_sketch() is not None
g_pick.done_what = "the sketch in Arm to open"


def g_draw():
    sk = h.in_sketch()
    h.check("G: the sketch is in Arm", cs.container_label(sk) == "Arm", cs.container_label(sk))
    h.draw_rectangle(sk, 50, 0, 70, 20)


def g_finish():
    h.ribbon("Finish Sketch")


g_finish.done = lambda: h.in_sketch() is None
g_finish.done_what = "the sketch in Arm to close"


def g_sketch_only():
    h.check("G: a body was made in Arm for the sketch", len(bodies()) == s["count"] + 1)
    rows = cs.children_of(["Arm"])
    h.check("G: Arm shows Origin and Sketches, no Bodies", rows == ["Origin", "Sketches"], rows)
    h.check("G: the root's Body is still listed", "Bodies" in top(), top())
    h.fit()
    h.press("e")


def g_distance():
    h.check("G: Extrude open", arrows.type_distance("5"))
    h.task_button("OK")


g_distance.done = lambda: not t.dialog_open()
g_distance.done_what = "the Extrude dialog to close"


def g_body():
    rows = cs.children_of(["Arm"])
    h.check("G: Arm shows Origin, Bodies, Sketches", rows == ["Origin", "Bodies", "Sketches"], rows)
    listed = cs.children_of(["Arm", "Bodies"]) or []
    h.check("G: Arm > Bodies > Body1", listed == ["Body1"], listed)
    arm_body = cs.body_labelled("Body1")
    h.check("G: 20 x 20 x 5", t.near(cs.volume(arm_body), SMALL), cs.volume(arm_body))
    root = cs.children_of(["Bodies"])
    h.check("G: the root's Body still listed", root == [doc().getObject(s["body"]).Label], root)
    t.no_popups("the end")
    h.shot("G-end")


STEPS = [
    a_new,
    a_create_sketch,
    a_picker,
    a_cancelled,
    b_pick,
    b_draw,
    b_finish,
    b_sketch_only,
    c_undo_sketch,
    c_before_sketch,
    c_empty_design,
    c_redone,
    d_save,
    d_open,
    d_reopened,
    e_extrude,
    e_distance,
    e_body,
    e_undone,
    e_redone,
    f_hide,
    f_hidden,
    f_shown,
    g_new,
    g_dialog,
    g_ok,
    g_made,
    g_pick,
    g_draw,
    g_finish,
    g_sketch_only,
    g_distance,
    g_body,
]


def watched(steps):
    """t.watched (the Report view and FreeCAD's balloons after each step), keeping each
    step's done / ready (t.watched's wrappers leave them out)."""
    wrapped = t.watched(steps)
    for one, run in zip(steps, wrapped):
        for attr in ("done", "done_what", "ready", "ready_what", "timeout_s"):
            if hasattr(one, attr):
                setattr(run, attr, getattr(one, attr))
    return wrapped


h.run("browser_empty_body", watched(STEPS), paced_by="state")
