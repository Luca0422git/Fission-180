# SPDX-License-Identifier: LGPL-2.1-or-later
"""The Carabiner's 4 mm fillet (book parity report, Project 5, lines 1189-1192):

  "MODIFY > Chamfer, click the bottom face (all its edges), 2 mm. OK."
  "Fillet top face + chamfer's top edges at 4 mm: Fission silently capped it to 3.99 mm
   ('1: 3 picks - 3.99 mm')."

The book's part: an 8 x 8 mm square swept round the carabiner's closed outline (two lines
and two half circles here), its bottom face chamfered 2 mm; both made by the design-step
builder. The fillet is real input: the F key, a click on the top face, a click on each of the
chamfer's two top edges (Tangent Chain takes the whole loop), 4 typed, OK.

Two 4 mm rounds use up the 8 mm top face exactly. OpenCASCADE's fillet cannot build that
(4.0 fails, 3.99 builds), which is where the 3.99 came from. Fission 180 builds the second
round from its cross-section swept along the edge loop (fillet_section.py): the size is 4 mm
as typed, nothing is said to be limited, no flat strip is left on top, and the rounds of the
chamfer's edges are there too. Then undo / redo, and Edit Feature shows 4 mm.
"""

import math

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import harness as h

V = App.Vector
CTRL = __import__("PySide").QtCore.Qt.ControlModifier
S = {}

STEPS = (
    {
        "op": "sketch",
        "id": "s1",
        "plane": "XY",
        # the outline's middle line is a slot 40 wide; the 8 mm section is 4 to each side
        "geometry": [{"slot": [-30, 0, 30, 0, 48]}, {"slot": [-30, 0, 30, 0, 32]}],
    },
    {"op": "extrude", "id": "e1", "profile": "s1", "distance": 8},
    {
        "op": "blend_chamfer",
        "id": "c1",
        "distance": 2,
        "faces": {"type": "plane", "normal": [0, 0, -1], "count": 1},
    },
)


def vol():
    return h.solid_volume()


def panel():
    return b.blend_panel()


def note(p):
    return p.limit_label.text() if p is not None and p.limit_label.isVisible() else ""


def flat_top(shape):
    return [
        f
        for f in shape.Faces
        if f.Surface.__class__.__name__ == "Plane" and abs(f.CenterOfMass.z - 8.0) < 1e-6
    ]


def setup():
    from Fission180Tests.golden.builder import Builder

    Gui.activateWorkbench("Fission180Workbench")
    doc = App.newDocument("Carabiner")
    builder = Builder(doc)
    for step in STEPS:
        builder.run(step)
        doc.recompute()
    h.fit()


def built():
    shape = h.body().Shape
    S["v0"] = vol()
    # the ring: (the 48 wide slot - the 32 wide slot) x 8, less the 2 mm chamfer's two rings
    ring = (60.0 * 48.0 + math.pi * 24.0**2 - 60.0 * 32.0 - math.pi * 16.0**2) * 8.0
    h.check("the swept 8 x 8 ring", abs(ring - 15722.48) < 0.01 and shape.isValid(), ring)
    h.check("with the 2 mm chamfer round its bottom", 14700.0 < S["v0"] < 14780.0, S["v0"])
    h.check("its top face is 8 mm wide all round", len(flat_top(shape)) == 1)
    Gui.Selection.clearSelection()
    h.press("f")


def pick_top_face():
    h.click(V(0, 20, 8))


def pick_outer_chamfer_edge():
    h.click_edge(V(0, -24, 2))


def pick_inner_chamfer_edge():
    h.click_edge(V(0, 16, 2))


def type_4():
    p = panel()
    if h.check("the top face and the chamfer's two edge loops", p and len(p.refs) == 3, p.refs):
        b.type_into(p.radius.widget, "4")


type_4.timeout_s = 240


def four_as_typed():
    p = panel()
    if p is None:
        h.check("Fillet dialog", False)
        return
    r = p._value(p._row_key(), "radius")
    h.check("4 mm is taken as typed (the report: capped to 3.99)", abs(r - 4.0) < 1e-9, r)
    h.check("nothing says it does not fit", note(p) == "" and not p.error, (note(p), p.error))
    rows = [p.rows.item(i).text() for i in range(p.rows.count())]
    h.check("the set reads 4 mm", any("4 mm" in row for row in rows), rows)
    h.shot("four")
    h.task_button("OK")


four_as_typed.timeout_s = 240


def kept():
    h.check("dialog closed", panel() is None)
    shape = h.body().Shape
    h.check("a valid solid in one piece", shape.isValid() and len(shape.Solids) == 1)
    h.check("no flat strip is left on top: the two rounds meet", not flat_top(shape))
    # the two top rounds: (4 x 4 - a quarter disc) along each loop; a round's section
    # sweeps a little more on the outside of a bend and less on the inside
    removed = S["v0"] - vol()
    h.check("the rounds are 4 mm", 1800.0 < removed < 1900.0, removed)
    S["v1"] = vol()
    h.press("z", CTRL)


kept.timeout_s = 120


def undone():
    h.check("Ctrl+Z: the chamfered ring", abs(vol() - S["v0"]) < 1e-6, vol() - S["v0"])
    h.check("its flat top is back", len(flat_top(h.body().Shape)) == 1)
    h.press("y", CTRL)


def redone():
    h.check("Ctrl+Y: the rounds again", abs(vol() - S["v1"]) < 1e-6, vol() - S["v1"])
    titles = b.timeline_titles()
    S["step"] = [t for t in titles if t.startswith("Fillet")]
    if h.check("a Fillet step in the timeline", len(S["step"]) == 1, titles):
        b.timeline_double_click(S["step"][0])


redone.timeout_s = 120


def edit_shows_4():
    p = panel()
    if not h.check("double-click: the Fillet dialog opens again", p is not None):
        return
    r = p._value(p._row_key(), "radius")
    h.check("it shows 4 mm", abs(r - 4.0) < 1e-9, r)
    h.check("and no limit", note(p) == "" and not p.error, (note(p), p.error))
    h.task_button("Cancel")


edit_shows_4.timeout_s = 120


def unchanged():
    h.check("Cancel: unchanged", abs(vol() - S["v1"]) < 1e-6, vol() - S["v1"])
    h.check("still valid", h.body().Shape.isValid())


h.run(
    "book_modifyb_carabiner",
    [
        setup,
        built,
        pick_top_face,
        pick_outer_chamfer_edge,
        pick_inner_chamfer_edge,
        type_4,
        four_as_typed,
        kept,
        undone,
        redone,
        edit_shows_4,
        unchanged,
    ],
    paced_by="state",
)
