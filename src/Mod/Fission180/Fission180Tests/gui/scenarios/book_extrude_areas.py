# SPDX-License-Identifier: LGPL-2.1-or-later
"""A parametric plate of 37 sketch areas survives its parameters (wave 7; the book report's
drone: "Change Parameters Arm_Length 53 -> 60 is refused: Extrude 1 would break: Sub shape
not found: Sketch.InternalFace56 ... the parametric drone does not work in Fission").

The plate: a 6 x 6 grid of squares whose lines all follow the user parameter Pitch (10 mm),
and a hole r 2 placed by HoleX / HoleY (25, 25: inside the square (2, 2)). 36 squares and the
hole's disc: 37 areas.

A1  E on the sketch: 37 areas are offered, none is picked by itself; the dialog is there
    within a few seconds. The 18 squares of a checkerboard are clicked one by one, 3 mm,
    New Body, OK: 18 squares less the hole, 5362.3 mm3.
A2  Pitch 12, 8, 15, 10: each time Change Parameters' own check finds nothing broken, and the
    solid is the same 18 squares at the new size.
A3  HoleX 20 (the hole on the line between a picked square and one that is not), HoleY 30
    (on a corner), back to 25 / 25: plain FreeCAD loses a square here without a word; the
    extrude keeps its 18 squares, less the part of the hole that lies in them.
A4  Edit from the timeline: the 18 squares are listed. Cancel.
A5  A Pitch change undone and redone; save, reopen, Pitch 14.
"""
import math
import os
import tempfile
import time

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h
from Fission180Tests.headless import sketch_area_id_check as plate

V = App.Vector
s = {}
HEIGHT = 3.0


def panel():
    from fission180 import extrude_ui

    p = extrude_ui.ExtrudePanel.last
    return p if p is not None and not p._closed else None


def near(a, b, tol=1e-6):
    return abs(a - b) <= tol * max(1.0, abs(b))


def feature():
    return App.ActiveDocument.getObject(s["feature"])


def sketch():
    return App.ActiveDocument.getObject(s["sketch"])


def valid():
    f = feature()
    return f is not None and plate._valid(f)


def broken():
    from fission180 import parameters

    return parameters.broken_steps(App.ActiveDocument)


def set_parameter(name, text):
    from fission180 import parameters

    doc = App.ActiveDocument
    parameters.set_user(doc, name, text)
    doc.recompute()


def squares_volume(pitch, hole_share=1.0):
    return (18 * pitch * pitch - hole_share * math.pi * plate.HOLE_R**2) * HEIGHT


def check_plate(tag, pitch, hole_share=1.0):
    ok = h.check("%s: nothing is broken (Change Parameters' own check)" % tag, not broken(), broken())
    f = feature()
    if not h.check("%s: the extrude is valid" % tag, valid(), f and f.getStatusString()):
        return
    want = squares_volume(pitch, hole_share)
    h.check("%s: 18 squares, %.1f mm3" % (tag, want), near(f.Shape.Volume, want),
            (f.Shape.Volume, want))
    cells = plate._cells(f.Shape, pitch)
    h.check("%s: the same 18 squares" % tag, cells == plate.WANTED, sorted(cells ^ plate.WANTED)[:4])
    return ok


# -- A1 ------------------------------------------------------------------------------------------
def a1_setup():
    from fission180 import parameters

    Gui.activateWorkbench("Fission180Workbench")
    doc, body, sk = plate._plate("AreasPlate")
    parameters.add_user(doc, "Pitch", "mm", "10")
    parameters.add_user(doc, "HoleX", "mm", "25")
    parameters.add_user(doc, "HoleY", "mm", "25")
    sk.setExpression("Constraints.pitch", "Parameters.Pitch")
    dims = plate._hole_dims(sk)
    sk.setExpression("Constraints[%d]" % dims[0], "Parameters.HoleX")
    sk.setExpression("Constraints[%d]" % dims[1], "Parameters.HoleY")
    doc.recompute()
    from fission180 import commands, components

    components.activate_body(body)
    s.update(sketch=sk.Name, body=body.Name)
    h.check("A1 the sketch follows its parameters", near(sk.getDatum("pitch").Value, 10.0))
    h.check("A1 the active body is the plate's", commands.find_body() is body)
    Gui.Selection.clearSelection()
    h.fit(iso=False)


def a1_open():
    h.click_empty()
    s["t0"] = time.monotonic()
    h.press("e")
    h.wait_for(lambda: panel() is not None, "the Extrude dialog to open")
    s["opened_in"] = time.monotonic() - s["t0"]


def a1_offered():
    p = panel()
    offered = {(sk.Name, sub) for sk, sub, _f, _m in p.picker.regions}
    h.check("A1 37 areas are offered", len(offered) == 37, len(offered))
    h.check("A1 none is picked by itself", not p.profiles, p.profiles)
    h.check("A1 the dialog with 37 areas opens quickly (%.2f s)" % s["opened_in"],
            s["opened_in"] < 4.0 * h.SLOWDOWN, s["opened_in"])


def click_squares(rows):
    def click():
        started = time.monotonic()
        count = 0
        for i, j in sorted(plate.WANTED):
            if j in rows:
                h.click(V(i * 10 + 2.5, j * 10 + 2.5, 0))  # (off the hole in the middle of one)
                count += 1
        s["click_time"] = s.get("click_time", 0.0) + (time.monotonic() - started)
        s["clicks"] = s.get("clicks", 0) + count

    click.__name__ = "a1_click_rows_%s" % "_".join(str(r) for r in rows)
    return click


def a1_picked():
    p = panel()
    h.check("A1 18 squares are picked, one click each", len(p.profiles) == 18, len(p.profiles))
    each = s["click_time"] / max(1, s["clicks"])
    h.check("A1 a click on an area is answered quickly (%.2f s a click, the hand's pace "
            "included)" % each, each < 3.0 * h.SLOWDOWN, each)
    h.check("A1 New Body (the first solid)", ui.choose(p.operation, "New Body"))
    ui.type_into(p.distance.widget, "3")
    h.caught_up(p)
    h.task_button("OK")


a1_picked.done = lambda: panel() is None
a1_picked.done_what = "OK finished the extrude"


def a1_made():
    doc = App.ActiveDocument
    found = [o for o in doc.Objects if o.TypeId == "PartDesign::Pad"]
    h.check("A1 the extrude is made", len(found) == 1, [o.Name for o in found])
    if found:
        s["feature"] = found[0].Name
    check_plate("A1", 10.0)


# -- A2 ------------------------------------------------------------------------------------------
def pitch_step(value):
    def change():
        set_parameter("Pitch", "%g" % value)
        # the hole stays in its square: it follows the pitch by hand, like a designer would
        set_parameter("HoleX", "%g" % (2.5 * value))
        set_parameter("HoleY", "%g" % (2.5 * value))
        check_plate("A2 Pitch %g" % value, value)

    change.__name__ = "a2_pitch_%g" % value
    return change


# -- A3 ------------------------------------------------------------------------------------------
def a3_on_line():
    set_parameter("HoleX", "20")
    check_plate("A3 the hole on a line (FreeCAD alone: 5100 mm3, a square lost)", 10.0, 0.5)


def a3_on_corner():
    set_parameter("HoleY", "30")
    set_parameter("HoleX", "30")
    check_plate("A3 the hole on a corner", 10.0, 0.5)


def a3_back():
    set_parameter("HoleX", "25")
    set_parameter("HoleY", "25")
    check_plate("A3 the hole back in its square", 10.0)


# -- A4 ------------------------------------------------------------------------------------------
def a4_edit():
    ui.double_click_timeline(ui.timeline_titles()[-1])


a4_edit.done = lambda: panel() is not None and panel().editing
a4_edit.done_what = "the extrude is open for editing"


def a4_listed():
    p = panel()
    h.check("A4 the edit lists the 18 squares", len(p.profiles) == 18, len(p.profiles))
    names = {sub for _o, sub in p.profiles}
    now = set(plate._checker(sketch(), 10.0))
    h.check("A4 under the numbers they have now", names == now, sorted(names ^ now)[:4])
    h.task_button("Cancel")


a4_listed.done = lambda: panel() is None
a4_listed.done_what = "the dialog is closed"


# -- A5 ------------------------------------------------------------------------------------------
def a5_change():
    doc = App.ActiveDocument
    check_plate("A4 Cancel changed nothing", 10.0)
    doc.openTransaction("Change Parameters")
    set_parameter("Pitch", "14")
    set_parameter("HoleX", "35")
    set_parameter("HoleY", "35")
    doc.commitTransaction()
    check_plate("A5 Pitch 14", 14.0)
    Gui.runCommand("Std_Undo")


def a5_undone():
    App.ActiveDocument.recompute()
    check_plate("A5 Undo: Pitch 10 again", 10.0)
    Gui.runCommand("Std_Redo")


def a5_redone():
    App.ActiveDocument.recompute()
    check_plate("A5 Redo: Pitch 14", 14.0)
    doc = App.ActiveDocument
    path = os.path.join(tempfile.mkdtemp(prefix="fission180_areas_"), "AreasPlate.FCStd")
    doc.saveAs(path)
    App.closeDocument(doc.Name)
    App.openDocument(path)


def a5_reopened():
    check_plate("A5 reopened", 14.0)
    set_parameter("Pitch", "9")
    set_parameter("HoleX", "22.5")
    set_parameter("HoleY", "22.5")
    check_plate("A5 reopened, Pitch 9", 9.0)
    set_parameter("HoleX", "18")
    check_plate("A5 reopened, the hole on a line", 9.0, 0.5)


steps = (
    [a1_setup, a1_open, a1_offered]
    + [click_squares((0, 1)), click_squares((2, 3)), click_squares((4, 5))]
    + [a1_picked, a1_made]
    + [pitch_step(v) for v in (12.0, 8.0, 15.0, 10.0)]
    + [a3_on_line, a3_on_corner, a3_back, a4_edit, a4_listed]
    + [a5_change, a5_undone, a5_redone, a5_reopened]
)

h.run("book_extrude_areas", steps, paced_by="state")
