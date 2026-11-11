# SPDX-License-Identifier: LGPL-2.1-or-later
"""Inch hardware in an inch design (the book parity report: "INSERT > Hardware... has only
metric screws ... no inch sizes", "no set screws or Phillips pan heads"). Real input on a
2 x 1.5 x 0.5 in block (made by script) with a 1/4-20 tapped hole (Fission 180's own Hole
step, cosmetic thread: the tap drill's diameter) at (0.5, 0.5) in.

A  The design is in inches: INSERT > Hardware... opens on Units Inch by itself (Socket head
   cap screw ASME B18.3, 1/4). Type Set screw: the inch cup point is first, lengths are in
   inches. Click the rim of the tapped hole: the set screw takes the hole's thread size
   (1/4, from the tap drill), no second hole, its top flush with the face. Thread offers
   1/4-20 UNC and 1/4-28 UNF. Length 1/4 in: "1/4-20 x 1/4 in Cup Point Set Screw".
B  Modeled threads: the real thread is cut (the Thread tool's code): less material than
   the plain cylinder, still one solid. OK: the component, its joint, steel.
C  Hardware..., Type Screw, Pan head screw Phillips, #6, 1/2 in. Click the block's top face:
   "Make the hole too" is on for a flat face: a #6 clearance hole (ASME B18.2.8, normal:
   4.3 mm) through the block, the pan head on the face. OK.
D  Save, close, reopen: both parts are there. Double-click the pan screw's Hardware step:
   the dialog shows it as left (Inch, #6, 1/2 in); Length 3/4 in: the screw grows and is
   renamed, its hole stays. OK. Undo puts 1/2 in back.
"""

import math
import os
import tempfile

import FreeCAD as App

from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import book_hardware_steps as bh
from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h

V = App.Vector
S = {}
IN = 25.4
TOP = 0.5 * IN
HOLE = (0.5 * IN, 0.5 * IN)
SET_SCREW = "1/4-20 x 1/4 in Cup Point Set Screw"
PAN = "#6-32 x 1/2 in Phillips Pan Head Screw"
PAN_LONG = "#6-32 x 3/4 in Phillips Pan Head Screw"
SPOT = (1.4 * IN, 0.9 * IN)  # where the pan screw goes


def setup():
    from fission180 import hole

    bh.new_design("BookHardwareInch", inch=True)
    body = bh.block("Block", (2 * IN, 1.5 * IN, TOP))
    base = body.Tip
    point = V(HOLE[0], HOLE[1], TOP)
    face = hole.base_face_at(base, point, V(0, 0, 1))
    hole.make_single(
        body,
        base,
        face,
        point,
        {
            "tap_type": "tapped",
            "standard": "ansi",
            "size": "1/4",
            "designation": "",
            "hole_type": "simple",
            "extent": "distance",
            "depth": 10.0,
            "drill_point": "flat",
        },
        name="Hole",
    )
    bh.done()
    S["block"] = body
    S["volume"] = body.Shape.Volume
    walls = [f for f in body.Shape.Faces if f.Surface.TypeId == "Part::GeomCylinder"]
    S["drill"] = 2.0 * walls[0].Surface.Radius if walls else 0.0
    h.check("the design is in inches", bh.doc().UnitSystem.startswith("Imperial decimal"))
    h.check("a tapped hole at its tap drill", 4.9 < S["drill"] < 5.4, S["drill"])


# -- A --------------------------------------------------------------------------------------------
def a_open():
    bh.open_hardware()


a_open.done = bh.is_open
a_open.done_what = "the Hardware dialog is open"


def a_inch():
    p = bh.panel()
    shown = bh.shown()
    h.check("Units Inch by itself in an inch design", shown[0] == "Inch", shown)
    h.check(
        "inch socket head, 1/4", shown[2:4] == ("Socket head cap screw (ASME B18.3)", "1/4"), shown
    )
    h.check("an inch length", shown[4].endswith(" in"), shown)
    h.check("Set screw", ui.choose(p.kind, "Set screw"))


def a_set_screw():
    p = bh.panel()
    shown = bh.shown()
    h.check("still Inch", shown[0] == "Inch", shown)
    h.check("the inch cup point", shown[2] == "Cup point set screw (ASME B18.3)", shown)
    h.fit()
    h.check(
        "the tapped hole's rim", h.click_edge(bh.near_rim(HOLE[0], HOLE[1], S["drill"] / 2.0, TOP))
    )
    S["first_length"] = p.length.currentText()


def a_placed():
    p = bh.panel()
    h.check("placed in the tapped hole", p.target is not None, (p.last_click, p.message.text()))
    if p.target is None:
        return
    h.check(
        "Size Automatic: 1/4 from the tap drill",
        p.size.currentText() == "1/4",
        p.size.currentText(),
    )
    h.check("no second hole", not p.make_hole.isChecked())
    threads = [p.thread.itemText(i) for i in range(p.thread.count())]
    h.check("Thread offers UNC and UNF", threads[:2] == ["1/4-20 UNC", "1/4-28 UNF"], threads)
    h.check("Length 1/4 in", ui.choose(p.length, "1/4 in"))


def a_flush():
    p = bh.panel()
    h.check("the name", p.name.text() == SET_SCREW, p.name.text())
    box = bh.box(p.target)
    h.check("top flush with the face, 1/4 in down", bh.near(box[2::3], [TOP - 0.25 * IN, TOP]), box)
    comp = bh.hw().component_of(p.target)
    h.check("on the hole's axis", bh.near(bh.axis_of(comp)[:2], HOLE), bh.axis_of(comp))
    v = S["block"].Shape.Volume
    h.check("the block is not cut again", abs(v - S["volume"]) < 1e-6, (v, S["volume"]))
    S["plain"] = p.target.Shape.Volume
    want = bh.core().volume(p.options)
    h.check("the plain screw's volume", abs(S["plain"] - want) < 1e-6 * want, (S["plain"], want))
    s.toggle(p.modeled)


# -- B --------------------------------------------------------------------------------------------
def b_threaded():
    p = bh.panel()
    h.check("Modeled threads is ticked", p.modeled.isChecked())
    shape = p.target.Shape
    h.check(
        "the thread is cut: less material",
        0.6 * S["plain"] < shape.Volume < 0.95 * S["plain"],
        (shape.Volume, S["plain"]),
    )
    h.check("still one valid solid", shape.isValid() and len(shape.Solids) == 1)
    h.check("no problem shown", p.message.text() == "", p.message.text())
    h.shot("B-set-screw-threaded")
    h.task_button("OK")


b_threaded.timeout_s = 120


def b_kept():
    bh.no_dialog("OK")
    part = bh.part_named(SET_SCREW)
    h.check("the set screw's component", part is not None, bh.labels())
    if part is None:
        return
    h.check("a rigid joint to the block", len(bh.joints_of(part)) == 1)
    from fission180 import material

    name = material.effective(bh.hw().body_of(part))[0]
    h.check("made of steel", name.startswith("Steel"), name)
    S["set"] = part.Name
    bh.open_hardware()


b_kept.done = bh.is_open
b_kept.done_what = "the Hardware dialog is open"


# -- C --------------------------------------------------------------------------------------------
def c_screw():
    p = bh.panel()
    h.check("it remembers the set screw", p.kind.currentText() == "Set screw", p.kind.currentText())
    h.check("Modeled threads stays as chosen", p.modeled.isChecked())
    h.check("Type Screw", ui.choose(p.kind, "Screw"))


def c_pan():
    p = bh.panel()
    h.check("Pan head, Phillips", ui.choose(p.standard, "Pan head screw, Phillips (ASME B18.6.3)"))


def c_size():
    h.check("#6", ui.choose(bh.panel().size, "#6"))


def c_length():
    p = bh.panel()
    h.check("1/2 in", ui.choose(p.length, "1/2 in"))
    if p.modeled.isChecked():
        s.toggle(p.modeled)  # a cosmetic thread for this one


def c_click_face():
    p = bh.panel()
    h.check("the name", p.name.text() == PAN, p.name.text())
    h.check("Make the hole too is on for a new place", p.make_hole.isChecked())
    h.check("a pan head sits on the face", not p.sink.isChecked())
    h.check("the hole it will get", "Clearance 4.3 mm" in p.hole_info.text(), p.hole_info.text())
    h.fit()
    h.click(V(SPOT[0], SPOT[1], TOP))


def c_placed():
    p = bh.panel()
    h.check("placed on the face", p.target is not None, p.message.text())
    if p.target is None:
        return
    comp = bh.hw().component_of(p.target)
    at = bh.axis_of(comp)
    S["at"] = at
    h.check("where the click was", abs(at[0] - SPOT[0]) < 0.6 and abs(at[1] - SPOT[1]) < 0.6, at)
    cut = math.pi * 2.15**2 * TOP
    v = S["block"].Shape.Volume
    h.check(
        "a #6 clearance hole through the block",
        abs(S["volume"] - v - cut) < 1e-6 * cut,
        (S["volume"] - v, cut),
    )
    box = bh.box(p.target)
    h.check("the pan head on the face", bh.near(box[2::3], [TOP - 0.5 * IN, TOP + 0.097 * IN]), box)
    wide = max(
        f.Surface.Radius for f in p.target.Shape.Faces if f.Surface.TypeId == "Part::GeomCylinder"
    )
    h.check("as wide as a #6 pan head", abs(2 * wide - 0.270 * IN) < 1e-6, 2 * wide)
    want = bh.core().volume(p.options)
    h.check(
        "its volume (the head rounded, the recess cut)",
        abs(p.target.Shape.Volume - want) < 1e-6 * want,
    )
    h.shot("C-pan-head")
    h.task_button("OK")


def c_kept():
    bh.no_dialog("OK")
    h.check("both parts", PAN in bh.labels() and SET_SCREW in bh.labels(), bh.labels())
    S["cut_volume"] = S["block"].Shape.Volume
    S["path"] = os.path.join(tempfile.mkdtemp(), "book_hardware_inch.FCStd")
    bh.doc().saveAs(S["path"])
    App.closeDocument(bh.doc().Name)


# -- D --------------------------------------------------------------------------------------------
def d_open():
    App.openDocument(S["path"])
    h.fit()


def d_reopened():
    h.check(
        "reopened: both parts",
        sorted(c for c in bh.labels()) == sorted([PAN, SET_SCREW]),
        bh.labels(),
    )
    part = bh.part_named(PAN)
    h.check("the pan screw's step", part is not None)
    setscrew = bh.part_named(SET_SCREW)
    h.check(
        "the set screw kept its modeled thread",
        setscrew is not None and setscrew.Shape.Volume < 0.95 * S["plain"],
        setscrew and setscrew.Shape.Volume,
    )
    h.check("still in inches", bh.doc().UnitSystem.startswith("Imperial decimal"))
    if part is not None:
        s.timeline_double_click(part)


d_reopened.done = bh.is_open
d_reopened.done_what = "the Hardware dialog opens on the pan screw"


def d_editing():
    p = bh.panel()
    h.check("editing", p is not None and p.editing)
    want = ("Inch", "Screw", "Pan head screw, Phillips (ASME B18.6.3)", "#6", "1/2 in")
    h.check("shows it as left", bh.shown() == want, bh.shown())
    h.check("its hole is on", p.make_hole.isChecked())
    h.check("Length 3/4 in", ui.choose(p.length, "3/4 in"))


def d_longer():
    p = bh.panel()
    box = bh.box(p.target)
    h.check("the screw grows", bh.near(box[2::3], [TOP - 0.75 * IN, TOP + 0.097 * IN]), box)
    h.check("renamed", PAN_LONG in bh.labels(), bh.labels())
    h.task_button("OK")


def d_kept():
    bh.no_dialog("OK")
    block = [b for b in bh.doc().Objects if b.TypeId == "PartDesign::Body" and b.Label == "Block"][
        0
    ]
    h.check("its hole stays", abs(block.Shape.Volume - S["cut_volume"]) < 1e-6, block.Shape.Volume)
    h.check("still two parts", len(bh.parts()) == 2, len(bh.parts()))
    s.undo()


def d_undone():
    h.check("Undo: 1/2 in again", PAN in bh.labels() and PAN_LONG not in bh.labels(), bh.labels())
    part = bh.part_named(PAN)
    if part is not None:
        box = bh.box(part)
        h.check("and as long as before", bh.near(box[2:3], [TOP - 0.5 * IN]), box)
    h.fit()
    h.shot("D-end")


h.run(
    "book_hardware_inch",
    [
        setup,
        a_open,
        a_inch,
        a_set_screw,
        a_placed,
        a_flush,
        b_threaded,
        b_kept,
        c_screw,
        c_pan,
        c_size,
        c_length,
        c_click_face,
        c_placed,
        c_kept,
        d_open,
        d_reopened,
        d_editing,
        d_longer,
        d_kept,
        d_undone,
    ],
    paced_by="state",
)
