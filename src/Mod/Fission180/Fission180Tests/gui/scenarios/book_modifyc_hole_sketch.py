# SPDX-License-Identifier: LGPL-2.1-or-later
"""Hole > From Sketch (Multiple Holes) with five circles on the end of the Tesla Turbine's
inlet tube (book parity report, line 2192: "click the circles, Simple 1/16 x 1.25 -> holes
cut (very slow, ~60 s)").

What made it slow: the Hole dialog starts with the settings of the last hole (as Fusion's
does). After a Tapped + Modeled hole, every click on a circle and every key cut all the
modeled threads again (1.3 s of kernel time for each thread here, far more on the report's
machine). Now a Hole step with several modeled threads previews the drilled holes, says so,
and cuts the threads once, by OK.

The design is the report's as far as its text gives it: an inch design, "Stator Subassembly"
with the housing's component inside, the housing ring (bore 9.18 in, 2.25 in wide), the
inlet tube d1.3 in with its bore d0.84 in, tangent to the housing's bore, and a sketch of
five d1/16 in circles on the tube's end, three of them over the open bore. Those parts are
made by the design-step builder; the holes are real input:

1. H, a click on the housing's flat face, Hole Tap Type Tapped, Modeled ticked, OK: one
   modeled thread (the dialog remembers these settings).
2. H, Placement From Sketch (Multiple Holes): Tapped + Modeled are still set. The five
   circles clicked: after each the preview shows the holes drilled, no thread is cut, and
   the dialog says the threads come with OK.
3. Hole Tap Type Simple, 1/16 typed as the diameter and 1.25 as the depth (inches), OK: the
   two holes in the tube's wall are cut 1.25 in deep (the three over the bore cut air).
4. Ctrl+Z takes the five holes away in one step, Ctrl+Y brings them back.
5. Edit Feature on that step: Tapped, Modeled, 0.2 in deep: again the holes only; OK cuts
   the threads, once.

Counted throughout: how often FreeCAD builds a Hole step with a modeled thread.
"""

import math

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import hole_steps as hs
from Fission180Tests.gui import timeline_input as t

V = App.Vector
IN = 25.4
S = {"modeled": 0, "plain": 0}
X_END = 150.0
Y_TUBE = 100.1
HALF = 2.25 * IN / 2.0
STEPS = [
    {
        "op": "sketch",
        "id": "s1",
        "plane": "XY",
        "geometry": [{"circle": [0, 0, 130]}, {"circle": [0, 0, 9.18 * IN / 2.0]}],
    },
    {"op": "extrude", "id": "e1", "profile": "s1", "distance": 2.25 * IN, "symmetric": True},
    {
        "op": "sketch",
        "id": "s2",
        "plane": "YZ",
        "offset": X_END,
        "geometry": [{"circle": [Y_TUBE, 0, 16.5]}],
    },
    {"op": "extrude", "id": "e2", "profile": "s2", "distance": -X_END, "operation": "join"},
    {
        "op": "sketch",
        "id": "s3",
        "plane": "YZ",
        "offset": X_END,
        "geometry": [{"circle": [Y_TUBE, 0, 0.84 * IN / 2.0]}],
    },
    {"op": "extrude", "id": "e3", "profile": "s3", "distance": -X_END, "operation": "cut"},
    {
        "op": "sketch",
        "id": "s4",
        "plane": "YZ",
        "offset": X_END,
        "geometry": [{"circle": [Y_TUBE + 6.5 * k, 0, IN / 32.0]} for k in (-2, -1, 0, 1, 2)],
    },
]
CENTRES = [V(X_END, Y_TUBE + 6.5 * k, 0) for k in (-2, -1, 0, 1, 2)]
ON_RING = V(0, -123.0, HALF)  # on the housing's flat front face
NOTE = "threads are modeled when you press OK"


class Counter:
    """Counts the builds of Hole steps, with and without a modeled thread."""

    def slotRecomputedObject(self, obj):
        try:
            if obj.TypeId != "PartDesign::Hole":
                return
            key = "modeled" if (obj.Threaded and obj.ModelThread) else "plain"
            S[key] += 1
        except Exception:
            pass


def vol():
    return h.solid_volume()


def setup():
    from Fission180Tests.golden.builder import Builder
    from fission180 import components, design_units

    Gui.activateWorkbench("Fission180Workbench")
    doc = App.newDocument("Housing")
    builder = Builder(doc)
    design_units.set_units(doc, 3)  # an inch design, like the book's
    sub = components.new_component(doc, "Stator Subassembly")
    inner = components.new_component(doc, "Housing", parent=sub)
    inner.addObject(builder.body)
    doc.recompute()
    components.activate_body(builder.body)
    for step in STEPS:
        builder.run(step)
        doc.recompute()
    S["sketch"] = builder.objects["s4"].Name
    builder.objects["s4"].ViewObject.Visibility = True
    S["before"] = vol()
    S["counter"] = Counter()
    App.addDocumentObserver(S["counter"])
    Gui.ActiveDocument.ActiveView.viewIsometric()
    h.fit()


def first_hole():
    Gui.Selection.clearSelection()
    h.ribbon("Hole")


first_hole.done = lambda: hs.hole_panel() is not None
first_hole.done_what = "the Hole dialog is open"


def first_face():
    h.click(ON_RING)


def first_tapped():
    p = hs.hole_panel()
    h.check("a hole on the housing's face", p is not None and p.target is not None, hs.message(p))
    b.choose(p.tap_type, "Tapped")


def first_size():
    p = hs.hole_panel()
    sizes = [p.size.itemText(i) for i in range(p.size.count())]
    S["standard"] = p.standard.currentText()
    wanted = "1/4" if "1/4" in sizes else "6"
    if p.size.currentText() != wanted:
        b.choose(p.size, wanted)


def first_modeled():
    p = hs.hole_panel()
    S["size"] = p.size.currentText()
    if not p.modeled.isChecked():
        hs.click_checkbox(p.modeled)


def first_ok():
    p = hs.hole_panel()
    h.check("Modeled is ticked", p.modeled.isChecked())
    h.check("a single modeled thread is previewed as it is", NOTE not in hs.message(p))
    h.check("the thread is cut in the preview", S["modeled"] >= 1, S)
    h.task_button("OK")


first_ok.timeout_s = 120


def second_hole():
    h.check("dialog closed", hs.hole_panel() is None)
    S["one"] = vol()
    shape = h.body().Shape
    h.check(
        "one sound solid with the first modeled thread",
        shape.isValid() and len(shape.Solids) == 1,
        (shape.isValid(), len(shape.Solids), S.get("size"), S.get("standard")),
    )
    h.check("the first hole is cut", S["one"] < S["before"] - 1.0, (S["before"], S["one"]))
    S["modeled"] = S["plain"] = 0
    # zoom in on the tube's end, as a person does before clicking 1.6 mm circles
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(App.ActiveDocument.getObject(S["sketch"]))
    Gui.SendMsgToActiveView("ViewSelection")
    Gui.Selection.clearSelection()
    h.view_still()
    h.ribbon("Hole")


second_hole.done = lambda: hs.hole_panel() is not None
second_hole.done_what = "the Hole dialog is open"


def from_sketch():
    p = hs.hole_panel()
    b.choose(p.placement, "From Sketch (Multiple Holes)")


def remembered():
    p = hs.hole_panel()
    h.check(
        "the dialog starts with the last hole's Tapped + Modeled",
        p.tap_type.currentData() == "tapped" and p.modeled.isChecked(),
        (p.tap_type.currentData(), p.modeled.isChecked()),
    )


def click_n(i):
    def step():
        h.click_edge(CENTRES[i] + V(0, IN / 32.0, 0))

    def check():
        p = hs.hole_panel()
        count = len(hs.centres_all(p.target)) if p.target is not None else 0
        h.check("%d point(s) picked" % (i + 1), count == i + 1, (count, hs.message(p)))
        if i >= 1:
            h.check(
                "%d holes: the dialog says the threads come with OK" % (i + 1),
                NOTE in hs.message(p),
                hs.message(p),
            )
        h.check("no modeled thread built for %d points" % (i + 1), S["modeled"] <= 1, S)

    step.__name__ = "click_%d" % i
    check.__name__ = "picked_%d" % i
    return [step, check]


def simple():
    p = hs.hole_panel()
    h.check("still Modeled in the dialog", p.modeled.isChecked())
    # only the very first point (one hole) may have been built with its thread
    h.check("five clicks cut at most one modeled thread", S["modeled"] <= 1, S)
    S["during"] = S["modeled"]
    b.choose(p.tap_type, "Simple")


def diameter():
    p = hs.hole_panel()
    hs.type_into(p.diameter.widget, "1/16")


def depth():
    p = hs.hole_panel()
    hs.type_into(p.depth.widget, "1.25")


def ok_simple():
    p = hs.hole_panel()
    h.check("1/16 in", abs(p.diameter.value() - IN / 16.0) < 1e-6, p.diameter.value())
    h.check("1.25 in", abs(p.depth.value() - 1.25 * IN) < 1e-6, p.depth.value())
    h.check("no note for simple holes", NOTE not in hs.message(p), hs.message(p))
    S["dialog"] = hs.message(p)
    h.task_button("OK")


def holes_cut():
    h.check("dialog closed", hs.hole_panel() is None, S.get("dialog"))
    removed = S["one"] - vol()
    r = IN / 32.0
    lo = 2 * math.pi * r * r * 1.25 * IN  # the two holes in the tube's wall, flat bottoms
    hi = lo + 2 * math.pi * r * r * r  # or with drill points
    S["five"] = vol()
    S["faces"] = len(h.body().Shape.Faces)
    shape = h.body().Shape
    h.check(
        "one sound solid with the five holes",
        shape.isValid() and len(shape.Solids) == 1,
        (shape.isValid(), len(shape.Solids)),
    )
    h.check(
        "two holes 1.25 in deep in the wall, three in the air", lo - 0.5 <= removed <= hi, removed
    )
    holes = [o for o in App.ActiveDocument.Objects if o.TypeId == "PartDesign::Hole"]
    h.check("two Hole steps", len(holes) == 2, [o.Label for o in holes])
    h.check("no thread was modeled for the simple holes", S["modeled"] == S["during"], S)
    h.check("nothing is red", all(v[1] == "ok" for v in t.states().values()), t.states())
    h.press(QtCore.Qt.Key_Z, QtCore.Qt.ControlModifier)


def undone():
    h.check("Ctrl+Z takes the five holes away", abs(vol() - S["one"]) < 1e-6, vol())
    holes = [o for o in App.ActiveDocument.Objects if o.TypeId == "PartDesign::Hole"]
    h.check("one Hole step left", len(holes) == 1, [o.Label for o in holes])
    h.press(QtCore.Qt.Key_Y, QtCore.Qt.ControlModifier)


def redone():
    h.check("Ctrl+Y brings them back", abs(vol() - S["five"]) < 1e-6, vol())
    S["modeled"] = S["plain"] = 0
    t.menu("Hole 2", "Edit Feature")


redone.done = lambda: hs.hole_panel() is not None
redone.done_what = "the Hole dialog is open on Hole 2"


def edit_tapped():
    p = hs.hole_panel()
    h.check("the dialog edits Hole 2", p.editing and p.tap_type.currentData() == "simple")
    b.choose(p.tap_type, "Tapped")


def edit_modeled():
    p = hs.hole_panel()
    if not p.modeled.isChecked():
        hs.click_checkbox(p.modeled)


def edit_depth():
    # 0.2 in deep: a dozen turns of the #0-80 thread in each hole (1.25 in would be 100)
    p = hs.hole_panel()
    hs.type_into(p.depth.widget, "0.2")


def edit_ok():
    p = hs.hole_panel()
    h.check("Modeled is ticked", p.modeled.isChecked())
    h.check("the dialog says the threads come with OK", NOTE in hs.message(p), hs.message(p))
    h.check("no modeled thread while the dialog is open", S["modeled"] == 0, S)
    h.task_button("OK")


edit_ok.timeout_s = 300


def threads_cut():
    h.check("dialog closed", hs.hole_panel() is None)
    h.check("the modeled threads are built once, by OK", S["modeled"] == 1, S)
    hole = [o for o in App.ActiveDocument.Objects if o.TypeId == "PartDesign::Hole"][-1]
    h.check("Hole 2 is tapped and modeled", hole.Threaded and hole.ModelThread)
    shape = h.body().Shape
    h.check(
        "the threads are cut (many more faces than the plain holes)",
        len(shape.Faces) > S["faces"] + 10,
        (len(shape.Faces), S["faces"]),
    )
    h.check(
        "a valid solid",
        shape.isValid() and len(shape.Solids) == 1,
        (shape.isValid(), len(shape.Solids)),
    )
    h.check("nothing is red", all(v[1] == "ok" for v in t.states().values()), t.states())
    App.removeDocumentObserver(S["counter"])
    h.shot("hole-sketch-threads")


steps = [
    setup,
    first_hole,
    first_face,
    first_tapped,
    first_size,
    first_modeled,
    first_ok,
    second_hole,
]
steps += [from_sketch, remembered]
for index in range(5):
    steps += click_n(index)
steps += [simple, diameter, depth, ok_simple, holes_cut, undone, redone]
steps += [edit_tapped, edit_modeled, edit_depth, edit_ok, threads_cut]
h.run("book_modifyc_hole_sketch", steps, paced_by="state")
