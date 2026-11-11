# SPDX-License-Identifier: LGPL-2.1-or-later
"""A hardware part shows its cosmetic thread (wave 7, library-2, item 3). Fusion's fasteners
carry the Thread feature, cosmetic unless modeled: the thread is seen on the part. Until now
a Fission 180 screw with cosmetic threads was a plain cylinder with nothing drawn on it (the
Thread tool's dashed helix was drawn for Thread steps and tapped holes only).

The part the screws go into (by script): a component "Plate", 60 x 40 x 10, with two 6.6 mm
holes.

A  INSERT > Hardware... (Socket head cap screw), the rim of one hole clicked: both holes get
   an M6 screw, and two dashed helices are drawn: on each screw's shank, 6 mm wide, pitch 1,
   over the standard thread length from the tip.
B  Modeled threads ticked: the real thread is cut, no helix is drawn. Unticked: two again.
   Length 40 mm: the helices follow the tip. OK.
C  Undo: no screws, no helix. Redo: two again.
D  Save, close, reopen: the two helices are drawn again.
E  A hex nut on the plate's top face (no hole made): one helix more, inside the nut.
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
HOLES = [(15.0, 20.0), (45.0, 20.0)]


def drawn():
    """How many cosmetic threads the 3D view draws now."""
    from fission180 import thread_ui

    return thread_ui.CosmeticThreads.count(bh.doc().Name)


def spots():
    """[(x, y, radius, pitch, low z, high z)] of the cosmetic threads to draw (design
    coordinates), sorted."""
    from fission180 import thread_ui

    found = []
    for place, radius, pitch, z0, z1, _left, _circles in thread_ui.cosmetic_spots(bh.doc()):
        a, b = place.multVec(V(0, 0, z0)), place.multVec(V(0, 0, z1))
        found.append(
            (
                round(a.x, 3),
                round(a.y, 3),
                round(radius, 2),
                pitch,
                round(min(a.z, b.z), 3),
                round(max(a.z, b.z), 3),
            )
        )
    return sorted(found)


def setup():
    from fission180 import components

    bh.new_design("BookLibrary2Thread")
    body = bh.block("PlateBody", (60, 40, 10))
    for i, (x, y) in enumerate(HOLES):
        bh.drill(body, "H%d" % i, x, y, 6.6, 0, 10)
    bh.doc().recompute()
    components.from_bodies(bh.doc(), [body], label="Plate")
    bh.done()
    S["count"] = len(bh.doc().Objects)
    bh.open_hardware()


setup.done = bh.is_open
setup.done_what = "the Hardware dialog is open"


# -- A --------------------------------------------------------------------------------------------
def a_click():
    h.check("nothing is drawn yet", drawn() == 0, drawn())
    h.fit()
    h.check("one hole's rim", h.click_edge(bh.near_rim(HOLES[0][0], HOLES[0][1], 3.3, 10)))


def a_length():
    p = bh.panel()
    h.check("placed", p is not None and p.target is not None, p and p.message.text())
    h.check("M6 from the hole", bh.shown()[3] == "M6", bh.shown())
    h.check("Length 25 mm", ui.choose(p.length, "25 mm"))


def a_helices():
    p = bh.panel()
    h.check("cosmetic threads (Modeled threads is off)", not p.modeled.isChecked())
    h.wait_for(lambda: drawn() == 2, "two helices drawn")
    found = spots()
    h.check("two dashed helices are drawn", drawn() == 2 and len(found) == 2, (drawn(), found))
    xy = [f[:2] for f in found]
    h.check("one on each screw's axis", xy == [HOLES[0], HOLES[1]], xy)
    # the screw: head on the face (z 10), shank 25 down to z -15; thread 2 d + 6 = 18 from
    # the tip
    for f in found:
        h.check("M6: 3 mm radius (a hair outside the shank)", 3.0 < f[2] < 3.05, f)
        h.check("pitch 1", f[3] == 1.0, f)
        h.check("from the tip (z -15) 18 mm up", (f[4], f[5]) == (-15.0, 3.0), f)
    h.shot("A-cosmetic-threads")
    s.toggle(p.modeled)


# -- B --------------------------------------------------------------------------------------------
def b_modeled():
    p = bh.panel()
    h.check("Modeled threads is on", p.modeled.isChecked())
    h.wait_for(lambda: drawn() == 0, "no helix on a modeled thread")
    h.check("the real thread: no helix is drawn", drawn() == 0 and spots() == [], spots())
    s.toggle(p.modeled)


def b_cosmetic_again():
    p = bh.panel()
    h.wait_for(lambda: drawn() == 2, "two helices again")
    h.check("unticked: two helices again", drawn() == 2, drawn())
    h.check("Length 40 mm", ui.choose(p.length, "40 mm"))


def b_longer():
    h.wait_for(lambda: [f[4] for f in spots()] == [-30.0, -30.0], "the helices to follow the tip")
    found = spots()
    h.check(
        "the helices follow the tip", [(f[4], f[5]) for f in found] == [(-30.0, -12.0)] * 2, found
    )
    h.task_button("OK")


# -- C --------------------------------------------------------------------------------------------
def c_ok():
    bh.no_dialog("OK")
    h.check("two helices after OK", drawn() == 2, drawn())
    S["after"] = len(bh.doc().Objects)
    s.undo()


c_ok.done = lambda: len(bh.doc().Objects) == S["count"]
c_ok.done_what = "Undo took the screws away"


def c_undone():
    h.wait_for(lambda: drawn() == 0, "no helix after Undo")
    h.check("Undo: no helix", drawn() == 0, drawn())
    s.redo()


c_undone.done = lambda: len(bh.doc().Objects) == S["after"]
c_undone.done_what = "Redo brought the screws back"


def c_redone():
    h.wait_for(lambda: drawn() == 2, "two helices after Redo")
    h.check("Redo: two helices", drawn() == 2, drawn())
    S["path"] = os.path.join(tempfile.mkdtemp(), "book_library2_thread.FCStd")
    bh.doc().saveAs(S["path"])
    App.closeDocument(bh.doc().Name)


# -- D --------------------------------------------------------------------------------------------
def d_open():
    App.openDocument(S["path"])
    h.fit()


def d_reopened():
    h.wait_for(lambda: drawn() == 2, "two helices after reopening")
    h.check("reopened: two helices", drawn() == 2 and len(spots()) == 2, (drawn(), spots()))
    bh.open_hardware()


d_reopened.done = bh.is_open
d_reopened.done_what = "the Hardware dialog is open"


# -- E --------------------------------------------------------------------------------------------
def e_nut():
    bh.search("hex nut m6")


def e_result():
    h.check("a hex nut is found", any("Hex Nut" in r for r in bh.results()), bh.results())
    bh.click_result(0)


def e_face():
    p = bh.panel()
    h.check("M6 hex nut", "M6" in p.name.text() and "Nut" in p.name.text(), p.name.text())
    if p.make_hole.isChecked():
        s.toggle(p.make_hole)
    h.click(V(30, 34, 10))


def e_placed():
    p = bh.panel()
    h.check("the nut is placed", p.target is not None, p.message.text())
    h.wait_for(lambda: drawn() == 3, "the nut's helix")
    found = spots()
    inside = [f for f in found if abs(f[0] - 30) < 0.6 and abs(f[1] - 34) < 0.6]
    h.check("one helix more, in the nut", drawn() == 3 and len(inside) == 1, found)
    if inside:
        h.check("inside the thread (a hair under 3 mm)", 2.95 < inside[0][2] < 3.0, inside[0])
    h.shot("E-nut")
    h.task_button("OK")


def e_ok():
    bh.no_dialog("OK")
    h.check("three helices at the end", drawn() == 3, drawn())


h.run(
    "book_library2_thread_look",
    [
        setup,
        a_click,
        a_length,
        a_helices,
        b_modeled,
        b_cosmetic_again,
        b_longer,
        c_ok,
        c_undone,
        c_redone,
        d_open,
        d_reopened,
        e_nut,
        e_result,
        e_face,
        e_placed,
        e_ok,
    ],
    paced_by="state",
)
