# SPDX-License-Identifier: LGPL-2.1-or-later
"""The Carabiner's fillet (book parity report, lines 1190-1192): "Fillet top face + chamfer's
top edges at 4 mm: Fission silently capped it to 3.99 mm". Only real input.

A bar 60 x 8 x 8 (the carabiner's 8 x 8 section). Fillet, the two long top edges, 4 typed:
two 4 mm rounds use up the 8 mm face between them exactly. OpenCASCADE's own fillet cannot
build that (4.0 fails, 3.99 builds), so the size used to be held at 3.99. Since the second
builder's fillet_section.py it builds as typed: the two rounds meet in a line, no flat face
is left between them (Fusion builds it; the book's step uses 4 mm).

A size that truly does not fit is still held at the largest that does, and that is SAID
(Luca's decision of 2026-10-21): 5 typed reads "5 mm does not fit: limited to 4.00 mm" in
the visible blue note. And the edges of the top FACE picked as a face (its two short end
edges with it, where three rounds would meet in a ball corner): 4 mm is held just under 4,
and said. The book's own part, a closed ring without such ends, is the scenario
book_modifyb_carabiner.
"""

import math

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import harness as h

V = App.Vector
s = {}


def bar(sketch):
    h.draw_rectangle(sketch, 0, 0, 60, 8)


def panel():
    return b.blend_panel()


def note(p):
    return p.limit_label.text() if p is not None and p.limit_label.isVisible() else ""


def start():
    Gui.Selection.clearSelection()
    h.fit()
    h.ribbon("Fillet")


def edge_front():
    h.click_edge(V(30, 0, 8))


def edge_back():
    h.click_edge(V(30, 8, 8))


def type_4():
    p = panel()
    if h.check("two edges picked", p is not None and len(p.refs) == 2, p and p.refs):
        b.type_into(p.radius.widget, "4")


type_4.timeout_s = 120


def four_builds():
    p = panel()
    if p is None:
        h.check("Fillet dialog", False)
        return
    # (the box keeps what is being typed until it is left; the size built is the one held)
    r = p._value(p._row_key(), "radius")
    h.check("4 mm is taken as typed (the report: capped to 3.99)", abs(r - 4.0) < 1e-9, r)
    h.check("nothing says it does not fit", note(p) == "" and not p.error, (note(p), p.error))
    shape = h.body().Shape
    flat = [
        f
        for f in shape.Faces
        if f.Surface.__class__.__name__ == "Plane" and abs(f.CenterOfMass.z - 8.0) < 1e-6
    ]
    h.check("the two rounds meet: no flat top face is left", shape.isValid() and not flat, flat)
    # the bar less two corners of 4 x 4 less a quarter disc each, 60 long
    removed = 2 * (16.0 - math.pi * 4.0) * 60.0
    h.check("the preview is the full round", abs(3840.0 - h.solid_volume() - removed) < 1e-3)
    h.shot("full_round")
    b.type_into(p.radius.widget, "5")


four_builds.timeout_s = 120


def held_and_said():
    p = panel()
    if p is None:
        h.check("Fillet dialog", False)
        return
    r = p._value(p._row_key(), "radius")
    h.check("5 mm does not fit: held at the 4 mm that does", abs(r - 4.0) < 1e-6, r)
    text = note(p)
    h.check(
        "and it is said, in the visible blue note",
        text.startswith("5 mm does not fit: limited to 4") and text.endswith("mm"),
        (text, p.limit_label.isVisible()),
    )
    h.check("no error", not p.error and "⚠" not in p.message.text(), (p.error, p.message.text()))
    h.shot("note")
    h.task_button("OK")


held_and_said.timeout_s = 120


def kept():
    h.check("dialog closed", panel() is None)
    shape = h.body().Shape
    removed = 2 * (16.0 - math.pi * 4.0) * 60.0
    h.check(
        "a valid solid with the full round",
        shape.isValid() and abs(3840.0 - h.solid_volume() - removed) < 1e-3,
        h.solid_volume(),
    )
    s["v"] = h.solid_volume()
    h.press("z", __import__("PySide").QtCore.Qt.ControlModifier)


def undone():
    h.check("Ctrl+Z: the plain bar", abs(h.solid_volume() - 3840.0) < 1e-6, h.solid_volume())
    Gui.Selection.clearSelection()
    h.ribbon("Fillet")


def top_face():
    h.click(V(30, 4, 8))


def face_type_4():
    p = panel()
    if h.check("the top face picked", p is not None and len(p.refs) == 1, p and p.refs):
        b.type_into(p.radius.widget, "4")


face_type_4.timeout_s = 120


def face_held_and_said():
    p = panel()
    if p is None:
        h.check("Fillet dialog", False)
        return
    text = note(p)
    r = p._value(p._row_key(), "radius")
    h.check("the face's edges: held under 4 mm", 3.9 <= r < 4.0, r)
    h.check("and said", text.startswith("4 mm does not fit: limited to 3.9"), text)
    h.task_button("Cancel")


face_held_and_said.timeout_s = 120


def cancelled():
    h.check("Cancel: the plain bar", abs(h.solid_volume() - 3840.0) < 1e-6, h.solid_volume())


h.run(
    "book_modify_fillet_limit_note",
    b.box_steps("Carabiner", 8, bar)
    + [
        start,
        edge_front,
        edge_back,
        type_4,
        four_builds,
        held_and_said,
        kept,
        undone,
        top_face,
        face_type_4,
        face_held_and_said,
        cancelled,
    ],
    paced_by="state",
)
