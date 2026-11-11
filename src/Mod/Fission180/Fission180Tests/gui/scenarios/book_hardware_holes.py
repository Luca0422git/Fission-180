# SPDX-License-Identifier: LGPL-2.1-or-later
"""Four screws into four holes in one go, and what the parts list makes of them (wave 7,
book-hardware). Real input on a component "Plate" (made by script): a 60 x 40 x 10 block with
four 3.4 mm holes near its corners and one 5.5 mm hole in the middle.

A  INSERT > Hardware... (Socket head cap screw M3 x 10). Click the rim of ONE corner hole:
   all four holes of that size on the face are filled (All holes like it: Fusion's Select
   Similar), the 5.5 hole is not. One component and three occurrences of it ("...:2",
   ":3", ":4"), no holes made, the heads on the face.
B  Untick All holes like it: only the clicked hole keeps its screw. Tick it: four again.
   A stray click on the plate's face keeps the four and says what to click. A click on
   one of the screws takes it away (three); the empty hole's rim fills it again (four).
C  OK: four rigid joints to the Plate, one undo step (Undo: nothing left; Redo: all back).
E  Double-click the Hardware step in the timeline: it shows "4 holes"; Length 16 mm: every
   occurrence grows, the names follow. OK. The joints stay and the assembly still solves.
F  Save, close, reopen: four screws, each on its hole; the step still knows its four places.
D  The parts list at the end (a drawing of the design, made by script as DRAWING > Table
   makes it): one row "M3 x 16 Socket Head Cap Screw", Qty 4, Description ISO 4762,
   Material Steel.
"""

import os
import tempfile

import FreeCAD as App

from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import book_hardware_steps as bh
from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h

V = App.Vector
S = {}
CORNERS = [(10.0, 10.0), (50.0, 10.0), (10.0, 30.0), (50.0, 30.0)]
MIDDLE = (30.0, 20.0)
NAME = "M3 x 10 Socket Head Cap Screw"
LONG = "M3 x 16 Socket Head Cap Screw"


def setup():
    from fission180 import components

    bh.new_design("BookHardwareHoles")
    body = bh.block("PlateBody", (60, 40, 10))
    for i, (x, y) in enumerate(CORNERS):
        bh.drill(body, "C%d" % i, x, y, 3.4, 0, 10)
    bh.drill(body, "Mid", MIDDLE[0], MIDDLE[1], 5.5, 0, 10)
    bh.doc().recompute()
    S["plate"] = components.from_bodies(bh.doc(), [body], label="Plate")[0]
    bh.done()
    S["body"] = body
    S["volume"] = body.Shape.Volume
    S["count"] = len(bh.doc().Objects)
    bh.open_hardware()


setup.done = bh.is_open
setup.done_what = "the Hardware dialog is open"


def places():
    """The (x, y) each occurrence of the part stands on, sorted."""
    p = bh.panel()
    feature = p.target if p is not None else S.get("feature")
    return sorted(bh.axis_of(c)[:2] for c in bh.hw().occurrences(feature))


def same_spots(found, wanted):
    return len(found) == len(wanted) and all(
        bh.near(a, b) for a, b in zip(sorted(found), sorted(wanted))
    )


# -- A --------------------------------------------------------------------------------------------
def a_click_one():
    p = bh.panel()
    h.check("M3 x 10 socket head", p.name.text() == NAME, p.name.text())
    h.check("All holes like it is ticked", p.similar.isChecked())
    h.fit()
    h.check(
        "one corner hole's rim", h.click_edge(bh.near_rim(CORNERS[0][0], CORNERS[0][1], 1.7, 10))
    )


def a_four():
    p = bh.panel()
    h.check("placed", p.target is not None, (p.last_click, p.message.text()))
    if p.target is None:
        return
    S["feature"] = p.target
    h.check("all four holes of that size are filled", same_spots(places(), CORNERS), places())
    h.check("the 5.5 hole is not", not any(bh.near(xy, MIDDLE) for xy in places()), places())
    h.check(
        "Place on counts them", p.place.button.text().startswith("4 holes"), p.place.button.text()
    )
    found = [c.Label for c in bh.hw().occurrences(p.target)]
    want = [NAME, NAME + ":2", NAME + ":3", NAME + ":4"]
    h.check("one component and three occurrences of it", found == want, found)
    h.check("no hole is made", not p.make_hole.isChecked() and not bh.hw().holes_of(p.target))
    v = S["body"].Shape.Volume
    h.check("the plate is not cut", abs(v - S["volume"]) < 1e-6, v)
    boxes = [bh.box_of(c) for c in bh.hw().occurrences(p.target)]
    h.check(
        "every head on the face, 10 down", all(bh.near(b[2::3], [0.0, 13.0]) for b in boxes), boxes
    )
    h.shot("A-four-holes")
    s.toggle(p.similar)


# -- B --------------------------------------------------------------------------------------------
def b_one():
    p = bh.panel()
    h.check("unticked: only the clicked hole", same_spots(places(), CORNERS[:1]), places())
    h.check("three occurrences gone", len(bh.hw().occurrences(p.target)) == 1)
    s.toggle(p.similar)


def b_four_again():
    h.check("ticked: four again", same_spots(places(), CORNERS), places())
    h.click(V(30, 34, 10))  # a stray click on the plate's face


def b_stray():
    p = bh.panel()
    h.check("a stray click on the face keeps the four", same_spots(places(), CORNERS), places())
    h.check("and the dialog says what to click", "4 holes are filled" in p.message.text())
    h.click(V(CORNERS[3][0] + 1.6, CORNERS[3][1] - 1.6, 13))  # the head of one of the screws


def b_emptied():
    h.check("a screw clicked: its hole is emptied", same_spots(places(), CORNERS[:3]), places())
    h.check("three screws", len(bh.hw().occurrences(bh.panel().target)) == 3)
    h.check(
        "the empty hole's rim", h.click_edge(bh.near_rim(CORNERS[3][0], CORNERS[3][1], 1.7, 10))
    )


def b_filled():
    h.check("filled again: four", same_spots(places(), CORNERS), places())
    h.task_button("OK")


# -- C --------------------------------------------------------------------------------------------
def c_kept():
    bh.no_dialog("OK")
    feature = S["feature"] = bh.part_named(NAME)
    h.check("the part", feature is not None, bh.labels())
    made = bh.joints_of(feature)
    h.check("four rigid joints to the Plate", len(made) == 4, [j.Label for j in made])
    S["after"] = len(bh.doc().Objects)
    s.undo()


def c_undone():
    h.check("Undo: no screws, no joints", len(bh.doc().Objects) == S["count"], bh.labels())
    s.redo()


def c_redone():
    feature = S["feature"] = bh.part_named(NAME)
    h.check("Redo: everything back", len(bh.doc().Objects) == S["after"], len(bh.doc().Objects))
    h.check(
        "Redo: four screws on their holes", feature is not None and same_spots(places(), CORNERS)
    )
    h.check("Redo: four joints", feature is not None and len(bh.joints_of(feature)) == 4)
    if feature is not None:
        s.timeline_double_click(feature)


c_redone.done = bh.is_open
c_redone.done_what = "the Hardware dialog opens on the screws"


# -- D --------------------------------------------------------------------------------------------
def d_parts_list():
    from fission180 import drawing

    d = bh.doc()
    solids = [b for b in d.Objects if b.TypeId == "PartDesign::Body" and b.Shape.Solids]
    page = drawing.create_drawing(d, solids)
    view = drawing.add_base_view(page, solids, 120, 150, orientation="Top")
    d.recompute()
    S["page"], S["view"] = page.Name, view.Name


def d_rows():
    from fission180 import drawing

    d = bh.doc()
    view = d.getObject(S["view"])
    made = drawing.add_parts_list(d.getObject(S["page"]), view, (20, 260), balloons=False)
    table = made[0] if isinstance(made, tuple) else made
    d.recompute()
    rows = drawing.parts_rows_for(view)
    short = [(r["PartNumber"], r["Qty"], r["Description"], r["Material"]) for r in rows]
    h.check("the parts list has two rows", len(rows) == 2, short)
    screws = [r for r in short if r[0] == LONG]
    h.check("one row for the screw", len(screws) == 1, short)
    if screws:
        h.check("Qty 4", screws[0][1] == 4, screws[0])
        h.check("Description: its standard", screws[0][2] == "ISO 4762", screws[0])
        h.check("Material: steel", screws[0][3].startswith("Steel"), screws[0])
    h.check("the Plate's row", any(r[0] == "Plate" and r[1] == 1 for r in short), short)
    on_sheet = drawing.parts_list_of(d.getObject(S["page"]))
    h.check("the table is on the sheet", table is not None and on_sheet.Name == table.Name)


# -- E --------------------------------------------------------------------------------------------
def e_editing():
    p = bh.panel()
    h.check("editing", p is not None and p.editing)
    h.check(
        "it shows its four places",
        p.place.button.text().startswith("4 holes"),
        p.place.button.text(),
    )
    h.check("M3, 10 mm as left", bh.shown()[3:] == ("M3", "10 mm"), bh.shown())
    h.check("Length 16 mm", ui.choose(p.length, "16 mm"))


def e_longer():
    p = bh.panel()
    h.settle("the occurrences to follow")
    boxes = [bh.box_of(c) for c in bh.hw().occurrences(p.target)]
    h.check(
        "every occurrence grows to 16", all(bh.near(b[2::3], [-6.0, 13.0]) for b in boxes), boxes
    )
    h.task_button("OK")


def e_kept():
    from fission180 import joints

    bh.no_dialog("OK")
    found = [c.Label for c in bh.hw().occurrences(S["feature"])]
    want = [LONG, LONG + ":2", LONG + ":3", LONG + ":4"]
    h.check("the names follow", found == want, found)
    h.check("still on their holes", same_spots(places(), CORNERS), places())
    h.check("the four joints stay", len(bh.joints_of(S["feature"])) == 4)
    h.check("the assembly solves", joints.solve(bh.doc()) == 0)
    h.check("and nothing moved", same_spots(places(), CORNERS), places())
    S["path"] = os.path.join(tempfile.mkdtemp(), "book_hardware_holes.FCStd")
    bh.doc().saveAs(S["path"])
    App.closeDocument(bh.doc().Name)


# -- F --------------------------------------------------------------------------------------------
def f_open():
    App.openDocument(S["path"])
    h.fit()


def f_reopened():
    feature = S["feature"] = bh.part_named(LONG)
    h.check("reopened: the part", feature is not None, bh.labels())
    if feature is None:
        return
    h.check("four screws on their holes", same_spots(places(), CORNERS), places())
    h.check("the step knows its four places", len(bh.hw().more_of(feature)) == 3)
    h.check("and its four joints", len(bh.joints_of(feature)) == 4)
    boxes = [bh.box_of(c) for c in bh.hw().occurrences(feature)]
    h.check("each a 16 mm screw", all(bh.near(b[2::3], [-6.0, 13.0]) for b in boxes), boxes)
    h.fit()
    h.shot("F-reopened")


h.run(
    "book_hardware_holes",
    [
        setup,
        a_click_one,
        a_four,
        b_one,
        b_four_again,
        b_stray,
        b_emptied,
        b_filled,
        c_kept,
        c_undone,
        c_redone,
        e_editing,
        e_longer,
        e_kept,
        f_open,
        f_reopened,
        d_parts_list,
        d_rows,
    ],
    paced_by="state",
)
