# SPDX-License-Identifier: LGPL-2.1-or-later
"""The book's knurl (Geocache top, Fire Piston): a short Coil cut, its Mirror, and a Circular
Pattern of both, 25 times around. Book parity report, lines 1310-1315: "computed for more
than 10 minutes, used 5.8 GB of RAM and never finished"; the preview of a 6x one kept the
app busy for more than 30 s.

The disc d40 x 10 with its Coil groove and the groove's Mirror are made by the design-step
builder (the code the AI tools and the golden models run); the pattern is real input:

  CREATE > Circular Pattern, Coil 1 and Mirror 1 clicked in the timeline, the Axis box, the
  Z axis, Quantity 25 typed (the keys 2 and 5), OK.

Checked: 25 crossing pairs of grooves are cut (the volume of 25 times what one pair cut, less
where grooves cross), the solid is valid; the pattern is built once for each value shown (3
copies, 2, 25) and not again by OK; and the whole of it, from the first click to the closed
dialog, takes less than LIMIT_S on this machine (the kernel cuts 50 swept grooves in about
half a minute here; the time is printed).
"""

import time

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import pattern_steps as ps
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import timeline_input as t

V = App.Vector
S = {"builds": []}
LIMIT_S = 240.0

STEPS = (
    {"op": "sketch", "id": "s1", "plane": "XY", "geometry": [{"circle": [0, 0, 20]}]},
    {"op": "extrude", "id": "e1", "profile": "s1", "distance": 10},
    {
        "op": "sf_coil",
        "id": "c1",
        "plane": "XY",
        "diameter": 40,
        "revolutions": 0.1,
        "height": 10,
        "section": "tri_int",
        "section_position": "inside",
        "section_size": 1,
        "operation": "cut",
    },
    {"op": "fusion_mirror", "id": "m1", "features": ["c1"], "plane": "XZ"},
)


def vol():
    return h.solid_volume()


def setup():
    from Fission180Tests.golden.builder import Builder
    from fission180 import pattern

    Gui.activateWorkbench("Fission180Workbench")
    doc = App.newDocument("Knurl")
    builder = Builder(doc)
    for step in STEPS:
        builder.run(step)
        doc.recompute()
    h.fit()
    # count how often a pattern step is built, and how long each build takes
    original = pattern.PatternFeature.execute

    def counted(self, obj):
        start = time.time()
        try:
            return original(self, obj)
        finally:
            try:
                quantity = int(obj.Quantity)
            except Exception:
                quantity = 0
            if pattern.kind_of(obj) == "circular":
                S["builds"].append((quantity, round(time.time() - start, 2)))

    pattern.PatternFeature.execute = counted
    S["restore"] = lambda: setattr(pattern.PatternFeature, "execute", original)


def built():
    S["disc"] = 3.141592653589793 * 400 * 10
    S["pair"] = S["disc"] - vol()
    h.check("the disc with a groove and its mirror", 5.0 < S["pair"] < 12.0, S["pair"])
    h.check(
        "Coil 1 and Mirror 1 in the timeline", t.titles()[-2:] == ["Coil 1", "Mirror 1"], t.titles()
    )
    S["start"] = time.time()
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
    pl.click_on_plane(V(0, 0, 12))


def quantity():
    p = ps.panel()
    axis = p.options["axis"] if p else None
    h.check("the Z axis", axis is not None and getattr(axis[0], "Role", "") == "Z_Axis", axis)
    ps.type_quantity(p.quantity, 25)


quantity.timeout_s = 900


def previewed():
    removed = S["disc"] - vol()
    S["removed"] = removed
    # 25 pairs, less where grooves cross each other (they do: a knurl)
    h.check(
        "25 pairs of grooves are cut",
        20.0 * S["pair"] < removed < 25.0 * S["pair"] + 1e-6,
        (removed, S["pair"]),
    )
    h.task_button("OK")


previewed.timeout_s = 900


def done():
    took = time.time() - S["start"]
    S["restore"]()
    h.check("dialog closed", ps.panel() is None)
    shape = h.body().Shape
    h.check("a valid solid", shape.isValid() and len(shape.Solids) == 1)
    h.check("the knurl is kept", abs((S["disc"] - vol()) - S["removed"]) < 1e-6, vol())
    counts = [q for q, _s in S["builds"]]
    App.Console.PrintMessage(
        "[Fission 180] KNURL: %.1f s from the first click to the closed dialog; pattern "
        "builds (copies, seconds): %s\n" % (took, S["builds"])
    )
    h.check("the 25x pattern is built once, not again by OK", counts.count(25) == 1, S["builds"])
    h.check("no build for a value never shown", len(counts) <= 4, S["builds"])
    h.check("nothing is red", all(v[1] == "ok" for v in t.states().values()), t.states())
    h.check("it took less than %d s" % LIMIT_S, took < LIMIT_S * h.SLOWDOWN, took)
    h.shot("knurl")


done.timeout_s = 900

h.run(
    "book_modify_knurl",
    [setup, built, click_coil, click_mirror, axis_box, z_axis, quantity, previewed, done],
    paced_by="state",
)
