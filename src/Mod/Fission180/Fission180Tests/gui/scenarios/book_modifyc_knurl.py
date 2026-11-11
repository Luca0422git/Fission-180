# SPDX-License-Identifier: LGPL-2.1-or-later
"""The book's knurls (book parity report, lines 1312-1320 and 1411).

Geocache Hide (pp 76-84): "Circular Pattern of Coil 1 + Mirror 1, Axis Z, Quantity 25 (the
knurl): Fission computed for more than 10 minutes, used 5.8 GB of RAM and never finished; I
had to kill it." The part is the report's: the bottom screw d33 x 16 with its 3 mm chamfer
and modeled M33 thread, the knob d40 x 8 below it, the Coil groove (0.1 revolutions, 10 mm,
Triangular (Internal), Inside, 1 mm, Cut) and its Mirror about XZ, made by the design-step
builder. The pattern is real input:

  CREATE > Circular Pattern, Coil 1 and Mirror 1 clicked in the timeline, the Axis box, the
  Z axis, Quantity 25 typed.

What is checked:
* while the dialog is open no copy is built for 25 (the kernel needs half a minute for the
  50 crossing grooves): the dialog shows 24 shaded copies of the grooves, says that they
  are built by OK, and the part is unchanged;
* OK builds them once, outside the window's process, with a window that says so; Cancel in
  that window stops the build, the dialog stays with "Cancelled" and the light preview;
* OK again builds the knurl: 25 pairs of grooves, one valid solid, nothing red; Ctrl+Z and
  Ctrl+Y do not build anything again; Edit Feature and Cancel leave it as it is, without a
  rebuild.

Metric Bolt (pp 86-93): the 40 straight knurls on the head: a V groove cut along the head
d8.5 x 5 and a Circular Pattern of it, Z axis, 40: FreeCAD's own pattern step, built live.

The times are printed ([Fission 180] KNURL ...).
"""

import math
import time

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import pattern_steps as ps
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import timeline_input as t
from Fission180Tests.gui import widget_input as w
from Fission180Tests.headless import pattern_benchmark as bench

V = App.Vector
S = {"builds": []}
LIMIT_S = 300.0


def vol():
    return h.solid_volume()


def progress():
    from fission180 import pattern_progress

    return pattern_progress.STATE


def build(case, name):
    from Fission180Tests.golden.builder import Builder

    steps, _pattern = bench.CASES[case]()
    doc = App.newDocument(name)
    builder = Builder(doc)
    for step in steps:
        builder.run(step)
        doc.recompute()
    doc.clearUndos()
    h.fit()
    return builder


def setup():
    from fission180 import pattern

    Gui.activateWorkbench("Fission180Workbench")
    build("geocache", "Geocache")
    original = pattern.apply_tools

    def counted(base_shape, tools, moves, kind, **kwargs):
        start = time.time()
        row = [len(moves), None, "stopped"]
        S["builds"].append(row)
        result = original(base_shape, tools, moves, kind, **kwargs)
        row[1], row[2] = round(time.time() - start, 1), "built"
        return result

    pattern.apply_tools = counted
    S["restore"] = lambda: setattr(pattern, "apply_tools", original)


def built():
    S["before"] = vol()
    S["faces"] = len(h.body().Shape.Faces)
    titles = t.titles()
    h.check("Coil 1 and Mirror 1 end the timeline", titles[-2:] == ["Coil 1", "Mirror 1"], titles)
    Gui.Selection.clearSelection()
    ps.menu("Circular Pattern")


def click_coil():
    ps.timeline_click("Coil 1")


def click_mirror():
    ps.timeline_click("Mirror 1")


def axis_box():
    p = ps.panel()
    h.check(
        "two features picked",
        p is not None and len(p.options["objects"]) == 2,
        p and p.options["objects"],
    )
    ps.click_box("axis")


def z_axis():
    h.fit()
    pl.click_on_plane(V(0, 0, 24))


def quantity():
    p = ps.panel()
    axis = p.options["axis"] if p else None
    h.check("the Z axis", axis is not None and getattr(axis[0], "Role", "") == "Z_Axis", axis)
    S["three"] = vol()
    h.check("3 copies are built live", S["three"] < S["before"] - 1.0, (S["three"], S["before"]))
    S["typed"] = time.time()
    ps.type_quantity(p.quantity, 25)


def light():
    p = ps.panel()
    took = time.time() - S["typed"]
    h.check("Quantity 25", p.options["quantity"] == 25, p.options["quantity"])
    h.check("the 25 copies are previewed light", p.light, p.info.text())
    h.check(
        "24 shaded copies of the grooves",
        p.ghosts is not None and p.ghosts.count == 24,
        p.ghosts and p.ghosts.count,
    )
    h.check(
        "the dialog says OK builds them", "Built when you press OK" in p.info.text(), p.info.text()
    )
    h.check("the part is as before the pattern", abs(vol() - S["before"]) < 1e-6, vol())
    big = [row for row in S["builds"] if row[0] >= 20]
    h.check("no build of 25 copies while typing", not big, S["builds"])
    h.speed_check("the dialog answered within 8 s", took < 8.0 * h.SLOWDOWN, took)
    App.Console.PrintMessage(
        "[Fission 180] KNURL geocache: light preview of 25 after %.1f s; builds so far "
        "(copies, seconds, result): %s\n" % (took, S["builds"])
    )
    h.shot("knurl-light")
    S["runs"] = progress()["runs"]

    def press_cancel():
        window = progress()["open"]
        button = window.dialog.findChild(QtWidgets.QPushButton)
        h.check("the progress window has a Cancel button", button is not None)
        S["label"] = window.dialog.labelText()
        w.click(button)

    h.when(lambda: progress()["open"] is not None, press_cancel, "the progress window to show")
    h.task_button("OK")


light.timeout_s = 600


def cancelled():
    p = ps.panel()
    h.check("the build ran outside the window's process", progress()["runs"] == S["runs"] + 1)
    h.check("the window named what is built", "Building" in S.get("label", ""), S.get("label"))
    h.check("Cancel stopped it", progress()["cancelled"] == 1, progress())
    h.check("the dialog is still open", p is not None)
    h.check("it says Cancelled", "Cancelled" in p.message.text(), p.message.text())
    h.check("back to the light preview", p.light and p.ghosts.count == 24, p.ghosts.count)
    h.check("the part is as before the pattern", abs(vol() - S["before"]) < 1e-6, vol())
    h.check("nothing is red", all(v[1] == "ok" for v in t.states().values()), t.states())
    S["ok_pressed"] = time.time()
    h.task_button("OK")


cancelled.timeout_s = 900


def knurled():
    took = time.time() - S["ok_pressed"]
    h.check("dialog closed", ps.panel() is None)
    shape = h.body().Shape
    removed = S["before"] - vol()
    pair = (S["before"] - S["three"]) / 2.0  # what one more groove and its mirror cut
    h.check(
        "24 more pairs of grooves, less where they cross",
        18.0 * pair < removed < 24.0 * pair + 1e-6,
        (removed, pair),
    )
    h.check("a valid solid", shape.isValid() and len(shape.Solids) == 1)
    h.check("many more faces", len(shape.Faces) > S["faces"] + 400, len(shape.Faces))
    done = [row for row in S["builds"] if row[0] >= 20 and row[2] == "built"]
    h.check("the 25 copies are built once", len(done) == 1, S["builds"])
    h.check("nothing is red", all(v[1] == "ok" for v in t.states().values()), t.states())
    h.check("it took less than %d s" % LIMIT_S, took < LIMIT_S * h.SLOWDOWN, took)
    App.Console.PrintMessage(
        "[Fission 180] KNURL geocache: OK to closed dialog %.1f s (the build outside: %.1f s); "
        "builds (copies, seconds, result): %s\n" % (took, progress()["last_s"], S["builds"])
    )
    S["knurl"] = vol()
    S["undo"] = list(App.ActiveDocument.UndoNames)
    h.check("the pattern is one undo step", S["undo"] == ["Circular Pattern"], S["undo"])
    S["count"] = len(S["builds"])
    h.shot("knurl-built")
    h.press(QtCore.Qt.Key_Z, QtCore.Qt.ControlModifier)


knurled.timeout_s = 900


def undone():
    doc = App.ActiveDocument
    h.check(
        "Ctrl+Z takes the pattern away",
        abs(vol() - S["before"]) < 1e-6,
        (vol(), S["undo"], list(doc.UndoNames), list(doc.RedoNames)),
    )
    h.press(QtCore.Qt.Key_Y, QtCore.Qt.ControlModifier)


def redone():
    h.check("Ctrl+Y brings the knurl back", abs(vol() - S["knurl"]) < 1e-6, vol())
    h.check("undo and redo built nothing", len(S["builds"]) == S["count"], S["builds"])
    t.menu("Circular Pattern 1", "Edit Feature")


redone.done = lambda: ps.panel() is not None
redone.done_what = "the pattern's dialog is open"


def edit_cancel():
    p = ps.panel()
    h.check("the dialog shows 25", p.options["quantity"] == 25, p.options["quantity"])
    h.task_button("Cancel")


def edit_cancelled():
    h.check("dialog closed", ps.panel() is None)
    h.check("the knurl is as it was", abs(vol() - S["knurl"]) < 1e-6, vol())
    h.check("Edit and Cancel built nothing", len(S["builds"]) == S["count"], S["builds"])
    h.check("nothing is red", all(v[1] == "ok" for v in t.states().values()), t.states())


# -- the Metric Bolt's 40 straight knurls -------------------------------------------------
def bolt():
    build("bolt", "Bolt")
    S["bolt"] = vol()
    S["groove"] = math.pi * 4.25**2 * 5 - S["bolt"]
    h.check("one groove along the head", 0.05 < S["groove"] < 0.5, S["groove"])
    Gui.Selection.clearSelection()
    ps.menu("Circular Pattern")


def bolt_groove():
    ps.timeline_click(t.titles()[-1])


def bolt_axis_box():
    ps.click_box("axis")


def bolt_axis():
    h.fit()
    pl.click_on_plane(V(0, 0, 8))


def bolt_quantity():
    p = ps.panel()
    axis = p.options["axis"] if p else None
    h.check("the Z axis", axis is not None and getattr(axis[0], "Role", "") == "Z_Axis", axis)
    S["typed"] = time.time()
    ps.type_quantity(p.quantity, 40)


def bolt_ok():
    p = ps.panel()
    took = time.time() - S["typed"]
    h.check("plain copies are built live", not p.light, p.info.text())
    removed = S["bolt"] - vol()
    h.check("40 grooves", abs(removed - 39 * S["groove"]) < 1e-3, (removed, S["groove"]))
    App.Console.PrintMessage("[Fission 180] KNURL bolt: 40 grooves shown after %.1f s\n" % took)
    h.task_button("OK")


def bolt_done():
    h.check("dialog closed", ps.panel() is None)
    shape = h.body().Shape
    h.check("a valid solid", shape.isValid() and len(shape.Solids) == 1)
    h.check("40 grooves kept", abs(S["bolt"] - vol() - 39 * S["groove"]) < 1e-3, vol())
    h.check("nothing is red", all(v[1] == "ok" for v in t.states().values()), t.states())
    S["restore"]()
    h.shot("knurl-bolt")


h.run(
    "book_modifyc_knurl",
    [
        setup,
        built,
        click_coil,
        click_mirror,
        axis_box,
        z_axis,
        quantity,
        light,
        cancelled,
        knurled,
        undone,
        redone,
        edit_cancel,
        edit_cancelled,
        bolt,
        bolt_groove,
        bolt_axis_box,
        bolt_axis,
        bolt_quantity,
        bolt_ok,
        bolt_done,
    ],
    paced_by="state",
)
