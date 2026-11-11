# SPDX-License-Identifier: LGPL-2.1-or-later
"""Deleting the Auto-projected edges of a sketch on a face sticks (wave 7, the book parity
report, Saturn V: "Deleting the auto-projected edges from that sketch does not stick: Finish
Sketch puts them back").

A 40 x 30 x 10 block. Create Sketch on its top face: the face's four edges are projected by
themselves (Auto project). A circle is drawn on the face.

  A  the four projected edges are selected (a click, then Ctrl+clicks, through the X
     server) and deleted with Del: the sketch has no projected curve left, the circle stays
  B  Finish Sketch: they are not put back; the block's later recomputes do not put them back
     either (the timeline's follow-up runs after every recompute)
  C  the sketch opened again from the browser and finished again: still none; saved, closed
     and opened: still none
  D  a second sketch on the same face still gets its four edges (the preference is on), and
     Finish Sketch keeps them
"""

import os
import tempfile

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import x_input as x

V = App.Vector
s = {}
Z = 10.0


def g(px, py):
    return V(px, py, Z)


def doc():
    return App.ActiveDocument


def projected(sketch):
    return len(sketch.ExternalGeo) - 2  # (the first two are the sketch's axes)


def new_design():
    Gui.activateWorkbench("Fission180Workbench")
    d = App.newDocument("BookSketchProject")
    body = d.addObject("PartDesign::Body", "Body")
    sk = body.newObject("Sketcher::SketchObject", "Sketch")
    sk.AttachmentSupport = [(d.getObject("XY_Plane"), "")]
    sk.MapMode = "FlatFace"
    h.draw_rectangle(sk, 0, 0, 40, 30)
    pad = body.newObject("PartDesign::Pad", "Extrude")
    pad.Profile = sk
    pad.Length = Z
    d.recompute()
    sk.Visibility = False
    h.fit()


def create_sketch():
    h.check("the X server takes test input (XTEST)", x.available())
    h.ribbon("Create Sketch")


def click_top():
    h.click(g(33, 24))


def ready():
    sk = h.in_sketch()
    s["sk"] = sk.Name if sk is not None else None
    h.check("sketch open on the top face", sk is not None)
    if sk is None:
        return
    h.check("the face's four edges are projected (Auto project)", projected(sk) == 4, projected(sk))
    import Part

    doc().openTransaction("circle")
    sk.addGeometry(Part.Circle(V(20, 15, 0), V(0, 0, 1), 6))
    doc().commitTransaction()
    doc().recompute()


def sketch():
    return doc().getObject(s["sk"])


# -- A ------------------------------------------------------------------------------------
def a_select():
    first = True
    for point in (g(20, 0), g(40, 15), g(20, 30), g(0, 15)):
        x.click(h.screen_point(point), held=() if first else ("ctrl",))
        h.settle()
        first = False
    names = sorted(
        n.rsplit(".", 1)[-1] for sel in Gui.Selection.getSelectionEx() for n in sel.SubElementNames
    )
    h.check(
        "A the four projected edges are selected",
        len(names) == 4 and all(n.startswith("ExternalEdge") for n in names),
        names,
    )


def a_delete():
    h.press(QtCore.Qt.Key_Delete)


def a_deleted():
    h.check("A Del removed the four projected edges", projected(sketch()) == 0, projected(sketch()))
    h.check("A the circle stays", len(sketch().Geometry) == 1, len(sketch().Geometry))


# -- B ------------------------------------------------------------------------------------
def finish():
    h.ribbon("Finish Sketch")


def b_finished():
    from fission180 import sketch_mode

    h.check("B the sketch is finished", sketch_mode.editing_sketch() is None)
    h.check("B Finish Sketch did not put them back", projected(sketch()) == 0, projected(sketch()))


def b_recompute():
    pad = doc().getObject("Extrude")
    doc().openTransaction("taller")
    pad.Length = 12
    doc().commitTransaction()
    doc().recompute()


def b_recomputed():
    h.check("B nor did a change of the block", projected(sketch()) == 0, projected(sketch()))
    h.check("B the circle is still there", len(sketch().Geometry) == 1)


# -- C ------------------------------------------------------------------------------------
def c_open():
    si.browser_double_click("Sketch 2")


c_open.done = lambda: h.in_sketch() is not None
c_open.done_what = "the sketch opened for editing"


def c_finished():
    h.check(
        "C opened and finished again: still none", projected(sketch()) == 0, projected(sketch())
    )


def c_save():
    path = os.path.join(tempfile.mkdtemp(prefix="f180-project-"), "project.FCStd")
    s["path"] = path
    doc().saveAs(path)
    App.closeDocument(doc().Name)


def c_reopen():
    App.openDocument(s["path"])


c_reopen.done = (
    lambda: App.ActiveDocument is not None and App.ActiveDocument.getObject("Extrude") is not None
)
c_reopen.done_what = "the saved design is open"


def c_reopened():
    doc().recompute()
    h.fit()
    h.check("C saved and opened: still none", projected(sketch()) == 0, projected(sketch()))


# -- D ------------------------------------------------------------------------------------
def d_create():
    h.ribbon("Create Sketch")


def d_click():
    h.click(V(33, 24, doc().getObject("Extrude").Length.Value))


def d_ready():
    sk = h.in_sketch()
    h.check("D a second sketch on the face", sk is not None and sk.Name != s["sk"])
    if sk is None:
        return
    s["sk2"] = sk.Name
    h.check("D ...gets its four projected edges", projected(sk) == 4, projected(sk))


def d_finished():
    sk = doc().getObject(s["sk2"])
    h.check("D Finish Sketch keeps them", projected(sk) == 4, projected(sk))
    h.check("D the first sketch is as it was", projected(sketch()) == 0)


h.run(
    "book_sketch_a_project",
    [
        new_design,
        create_sketch,
        click_top,
        ready,
        a_select,
        a_delete,
        a_deleted,
        finish,
        b_finished,
        b_recompute,
        b_recomputed,
        c_open,
        finish,
        c_finished,
        c_save,
        c_reopen,
        c_reopened,
        d_create,
        d_click,
        d_ready,
        finish,
        d_finished,
    ],
    paced_by="state",
)
