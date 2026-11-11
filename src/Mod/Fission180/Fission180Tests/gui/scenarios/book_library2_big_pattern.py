# SPDX-License-Identifier: LGPL-2.1-or-later
"""A pattern on a finely meshed part (wave 7, library-2, item 12). A part drawn with more
than 6,000 triangles gets its pattern 0.4 s after its last change instead of at once
(working it out takes a moment); that path had no scenario. What must hold: the pattern
arrives, it is worked out ONCE per change (never per frame of an orbit, never per step of a
drag), and it follows the part.

The part (by script): the book's donut, a torus (R 30, r 10) drawn finely.

A  MODIFY > Appearance, "Oak" dragged onto the donut: the pattern was put off and then laid
   once; it covers more than 6,000 triangles and shows on screen. OK.
B  The view orbited by a real drag (Shift + middle button, 20 moves): the pattern is not
   worked out again, and is still drawn.
C  Move/Copy (M), the donut clicked, the X arrow dragged 40 mm in 24 moves: while it is
   dragged the pattern is put off again and again, and worked out once at the end; it lies
   on the moved donut. OK.
D  Undo: the donut is back where it was, with its pattern.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import looks_steps as k

V = App.Vector
S = {}
TOP = V(30, 0, 10)


def draw():
    from fission180 import appearance_draw

    return appearance_draw


def doc():
    return App.ActiveDocument


def body():
    return doc().getObject("Donut")


def counts():
    return dict(draw().COUNTS)


def since(key):
    return counts()[key] - S["counts"][key]


def mark():
    S["counts"] = counts()


def setup():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("BookLibrary2BigPattern")
    d = doc()
    donut = d.addObject("PartDesign::Body", "Donut")
    ring = d.addObject("PartDesign::AdditiveTorus", "Ring")
    donut.addObject(ring)
    ring.Radius1, ring.Radius2 = 30, 10
    d.recompute()
    for obj in (ring, donut):
        view = obj.ViewObject
        view.Deviation = 0.02
        view.AngularDeflection = 2.0
    d.recompute()
    h.fit()
    mark()
    k.open_appearance()


setup.done = lambda: k.panel() is not None
setup.done_what = "the Appearance dialog is open"


# -- A --------------------------------------------------------------------------------------------
def a_drop():
    h.check("no pattern yet", draw().drawn(body().Tip) == (0, 0), draw().drawn(body().Tip))
    h.check("the 3D view takes the look", k.drop_look("Oak", TOP))


def a_laid():
    groups, triangles = draw().drawn(body().Tip)
    h.check("the pattern is drawn", groups == 1, (groups, triangles))
    h.check("a fine part: more than 6,000 triangles", triangles > draw().BIG, triangles)
    h.check("it was put off first (the big-part path)", since("later") >= 1, counts())
    h.check("and worked out once", since("laid") == 1, counts())
    h.click_empty()
    h.pointer_to(h.gl_widget(), h.screen_point(V(-60, -60, 0)))
    rough = k.roughness(TOP)
    h.check("it shows on screen (not a flat colour)", rough > 1.0, rough)
    h.shot("A-oak-on-a-fine-donut")
    h.task_button("OK")


a_laid.done = lambda: k.panel() is None
a_laid.done_what = "the Appearance dialog is closed"


# -- B --------------------------------------------------------------------------------------------
def b_orbit():
    mark()
    gl = h.gl_widget()
    start = QtCore.QPoint(gl.width() // 2 - 120, gl.height() // 2 + 40)
    end = QtCore.QPoint(gl.width() // 2 + 160, gl.height() // 2 - 60)
    S["camera"] = Gui.ActiveDocument.ActiveView.getCameraOrientation().Q
    h.drag(start, end, steps=20, button=QtCore.Qt.MiddleButton, modifiers=QtCore.Qt.ShiftModifier)


def b_orbited():
    now = Gui.ActiveDocument.ActiveView.getCameraOrientation().Q
    h.check("the view turned", any(abs(a - b) > 1e-3 for a, b in zip(now, S["camera"])), now)
    h.check("orbiting never works the pattern out again", since("laid") == 0, counts())
    h.check("nor puts it off", since("later") == 0, counts())
    h.check("the pattern is still drawn", draw().drawn(body().Tip)[0] == 1)
    h.fit()
    h.press("m")


b_orbited.done = lambda: s.panel() is not None
b_orbited.done_what = "the Move/Copy dialog is open"


# -- C --------------------------------------------------------------------------------------------
def c_pick():
    h.click(TOP)


def c_drag():
    p = s.panel()
    triad = getattr(p, "triad", None)
    if not h.check("the donut is picked, the manipulator shown", triad is not None, p.options):
        return
    mark()
    axis = V(1, 0, 0)
    start = triad.center + axis * (0.75 * triad.size)
    h.drag(h.screen_point(start), h.screen_point(start + axis * 40), steps=24)


def c_dragged():
    p = s.panel()
    dx = p.options["dx"] if p is not None else 0
    h.check("dragged about 40 in X", abs(dx - 40) < 4.0, dx)
    S["dx"] = dx
    tip = body().Tip
    h.check("the donut moved", abs(tip.Shape.BoundBox.Center.x - dx) < 1e-3, tip.Shape.BoundBox)
    h.check("while dragged, the pattern was put off", since("later") >= 1, counts())
    h.check("and worked out once at the end, not at every move", since("laid") == 1, counts())
    groups, triangles = draw().drawn(tip)
    h.check("the pattern lies on the moved donut", groups == 1 and triangles > draw().BIG)
    h.shot("C-moved")
    h.task_button("OK")


c_dragged.done = lambda: s.panel() is None
c_dragged.done_what = "the Move/Copy dialog is closed"


# -- D --------------------------------------------------------------------------------------------
def d_undo():
    h.check("after OK: the pattern is drawn", draw().drawn(body().Tip)[0] == 1)
    s.undo()


d_undo.done = lambda: abs(body().Tip.Shape.BoundBox.Center.x) < 1e-6
d_undo.done_what = "Undo moved the donut back"


def d_undone():
    h.settle("the pattern after Undo")
    groups, triangles = draw().drawn(body().Tip)
    h.check("Undo: the donut has its pattern", groups == 1 and triangles > draw().BIG, groups)
    look = k.body_look_label(body())
    h.check("Undo: still oak", look == "Oak", look)


h.run(
    "book_library2_big_pattern",
    [setup, a_drop, a_laid, b_orbit, b_orbited, c_pick, c_drag, c_dragged, d_undo, d_undone],
    paced_by="state",
)
