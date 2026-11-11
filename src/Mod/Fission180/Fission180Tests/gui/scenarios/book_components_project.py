# SPDX-License-Identifier: LGPL-2.1-or-later
"""Project (P) of faces, edges and corners of ANOTHER component (book parity report: "Project
from another component projects nothing, no message"; the Hot End's Heat Break and Heat
Sink, the Pizza Cutter's Inner Body, the Tesla Turbine). Only real input for what is tested.

Setup (through the modules): "Nozzle" with a 20 x 20 x 10 block, standing 30 mm along X;
"Pins" with a cylinder (radius 5, height 20, axis through x 0, y 40); the empty component
"Heat Break".

  A  Heat Break active, Create Sketch on its XY plane. P (Project), click the Nozzle's top
     front edge: one projected line from (30, 0) to (50, 0) in the sketch, though the
     Nozzle is another component (nothing happened before). Click the pin's top edge: a
     projected circle, centre (0, 40), radius 5. Click a corner of the Nozzle: a point.
     Click the Nozzle's top face: its four edges. Click the face again: "projected
     already", nothing added. Esc ends the tool.
  B  Ctrl+Z takes the last projection (the face's four edges: one click, one undo step)
     and leaves the sketch open; Ctrl+Y brings it back.
  C  A circle drawn in the sketch is made concentric with the projected pin (a constraint
     to the projected circle's centre): it jumps onto the pin's axis: the projection is a
     real reference.
  D  Finish Sketch. The Nozzle moved 15 mm along Y, the Pins 10 mm along -X (their
     Placements): the projected line and circle follow in the sketch.
  E  Save, close, reopen: the projections are there and still follow.
"""

import os
import tempfile

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import book_components_steps as k
from Fission180Tests.gui import component_steps as cs
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import inspect_steps as ist
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import timeline_input as t

V = App.Vector
state = {}


def new_design():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("BookComponentsProject")
    nozzle = k.new_component("Nozzle", at=(30, 0, 0))
    k.add_box(nozzle, (0, 0, 20, 20), 10)
    pins = k.new_component("Pins")
    k.add_cylinder(pins, (0, 40), 5, 20)
    k.new_component("Heat Break")
    k.settle_design()


def sketch():
    return k.doc().getObject(state.get("sketch", "")) if state.get("sketch") else None


def externals(sk=None):
    """The projected curves of the sketch (without its two axes)."""
    sk = sk or sketch()
    return list(sk.ExternalGeo)[2:] if sk is not None else []


def lines(sk=None):
    return [g for g in externals(sk) if g.TypeId == "Part::GeomLineSegment"]


def circles(sk=None):
    return [g for g in externals(sk) if g.TypeId in ("Part::GeomCircle", "Part::GeomArcOfCircle")]


def points(sk=None):
    return [g for g in externals(sk) if g.TypeId == "Part::GeomPoint"]


def has_line(a, b, sk=None, tol=1e-4):
    a, b = V(*a), V(*b)
    for g in lines(sk):
        s, e = g.StartPoint, g.EndPoint
        if ((s - a).Length < tol and (e - b).Length < tol) or (
            (s - b).Length < tol and (e - a).Length < tol
        ):
            return True
    return False


def describe(sk=None):
    out = []
    for g in externals(sk):
        if g.TypeId == "Part::GeomLineSegment":
            out.append(("line", tuple(round(v, 3) for v in (*g.StartPoint, *g.EndPoint))))
        elif "Circle" in g.TypeId:
            out.append(("circle", tuple(round(v, 3) for v in (*g.Center, g.Radius))))
        elif g.TypeId == "Part::GeomPoint":
            out.append(("point", (round(g.X, 3), round(g.Y, 3))))
        else:
            out.append((g.TypeId,))
    return out


def project_tool():
    from fission180 import sketch_tools_ui

    tool = sketch_tools_ui.watched_tool()
    return tool if tool is not None and tool.title == "Project" else None


# -- A ---------------------------------------------------------------------------------------------
def a_activate():
    cs.click_radio("Heat Break")


a_activate.done = lambda: k.active_label() == "Heat Break"
a_activate.done_what = "Heat Break is active"


def a_sketch():
    h.fit()
    h.ribbon("Create Sketch")


def a_plane():
    pl.click_square("XY_Plane")


a_plane.done = lambda: h.in_sketch() is not None
a_plane.done_what = "the sketch is open"


def a_opened():
    sk = h.in_sketch()
    if not h.check("sketch open", sk is not None):
        return
    state["sketch"] = sk.Name
    h.check(
        "the sketch is in Heat Break", k.container_label(sk) == "Heat Break", k.container_label(sk)
    )
    h.check("nothing projected yet", len(externals()) == 0, describe())
    h.fit(iso=False)


def press_p():
    h.press("p")


press_p.done = lambda: project_tool() is not None
press_p.done_what = "the Project tool runs"


def a_edge():
    h.click_edge(V(40, 0, 10))  # the Nozzle's top front edge


def a_edge_projected():
    h.check(
        "an edge of another component is projected (nothing happened before)",
        len(lines()) == 1,
        describe(),
    )
    h.check(
        "where the Nozzle's edge is: (30, 0) - (50, 0)",
        has_line((30, 0, 0), (50, 0, 0)),
        describe(),
    )
    h.check("Heat Break is still active", k.active_label() == "Heat Break", k.active_label())
    h.check("the Project tool still runs", project_tool() is not None)


def a_circle():
    h.click_edge(V(0, 35, 20))  # the pin's top edge


def a_circle_projected():
    found = circles()
    if h.check("the pin's edge is projected as a circle", len(found) == 1, describe()):
        c = found[0]
        h.check(
            "centre (0, 40), radius 5",
            (c.Center - V(0, 40, 0)).Length < 1e-4 and abs(c.Radius - 5) < 1e-4,
            describe(),
        )


def a_corner():
    ist.click_vertex(V(50, 20, 10))


def a_corner_projected():
    found = points()
    if h.check("a corner of the Nozzle is projected as a point", len(found) == 1, describe()):
        h.check(
            "at (50, 20)", abs(found[0].X - 50) < 1e-4 and abs(found[0].Y - 20) < 1e-4, describe()
        )


def a_face():
    state["before_face"] = len(externals())
    h.click(V(44, 13, 10))  # the Nozzle's top face


def a_face_projected():
    h.check(
        "the face gives its four edges", len(externals()) == state["before_face"] + 4, describe()
    )
    for a, b in (
        ((30, 0, 0), (50, 0, 0)),
        ((50, 0, 0), (50, 20, 0)),
        ((50, 20, 0), (30, 20, 0)),
        ((30, 20, 0), (30, 0, 0)),
    ):
        h.check("edge %s - %s" % (a[:2], b[:2]), has_line(a, b), describe())
    h.shot("A-projected")


def a_face_again():
    state["before_again"] = len(externals())
    h.click(V(44, 13, 10))


def a_not_twice():
    h.check(
        "projected already: nothing added", len(externals()) == state["before_again"], describe()
    )


def escape():
    h.press(QtCore.Qt.Key_Escape)


escape.done = lambda: project_tool() is None
escape.done_what = "the Project tool ended"


def a_still_open():
    h.check("the sketch is still open after Esc", h.in_sketch() is not None)
    state["count"] = len(externals())
    state["undo"] = list(k.doc().UndoNames)[:6]


# -- B ---------------------------------------------------------------------------------------------
def b_circle():
    sk = h.in_sketch()
    if sk is not None:
        h.draw_circle(sk, 20, 60, 2)


def b_concentric():
    import Sketcher

    sk = sketch()
    if not h.check(
        "the drawn circle is there",
        sk is not None and sk.GeometryCount == 1,
        sk.GeometryCount if sk is not None else None,
    ):
        return
    ext = list(sk.ExternalGeo)
    index = [i for i, g in enumerate(ext) if "Circle" in g.TypeId][0]
    doc = sk.Document
    doc.openTransaction("Coincident")
    sk.addConstraint(Sketcher.Constraint("Coincident", 0, 3, -1 - index, 3))
    doc.commitTransaction()
    sk.solve()


def b_on_axis():
    sk = sketch()
    c = sk.Geometry[0]
    h.check(
        "the circle sits on the projected pin's centre (0, 40)",
        (c.Center - V(0, 40, 0)).Length < 1e-4,
        c.Center,
    )


# -- C ---------------------------------------------------------------------------------------------
def undo_key():
    t.ctrl("z")


def c_face_gone():
    h.check(
        "Undo takes the face's four edges, one click's worth",
        len(externals()) == state["count"] - 4,
        (describe(), state.get("undo"), list(k.doc().UndoNames)[:6], list(k.doc().RedoNames)[:3]),
    )
    h.check("the sketch is still open", h.in_sketch() is not None)


def redo_key():
    t.ctrl("y")


def c_face_back():
    h.check("Redo brings them back", len(externals()) == state["count"], describe())


# -- D ---------------------------------------------------------------------------------------------
def d_finish():
    h.ribbon("Finish Sketch")


d_finish.done = lambda: h.in_sketch() is None
d_finish.done_what = "the sketch closed"


def d_move():
    from fission180 import component_move

    doc = k.doc()
    doc.openTransaction("Move")
    for label, shift in (("Nozzle", V(0, 15, 0)), ("Pins", V(-10, 0, 0))):
        part = k.part(label)
        movement = App.Placement(shift, App.Rotation())
        component_move.place(part, component_move.moved(part, part.Placement, movement))
    doc.commitTransaction()
    doc.recompute()


def d_followed():
    k.box_is("the Nozzle moved", k.part("Nozzle"), [30, 15, 0, 50, 35, 10])
    h.check(
        "the projected edge followed the Nozzle: (30, 15) - (50, 15)",
        has_line((30, 15, 0), (50, 15, 0)),
        describe(),
    )
    found = circles()
    if h.check("the projected circle is there", len(found) == 1, describe()):
        h.check(
            "it followed the Pins: centre (-10, 40)",
            (found[0].Center - V(-10, 40, 0)).Length < 1e-4,
            describe(),
        )
    sk = sketch()
    h.check("the sketch has no error", sk is not None and "Invalid" not in sk.State, sk.State)
    k.no_empty_invalid_bodies()
    rows = t.children("Heat Break")
    h.check("no reference shows in the browser", not any("Reference" in r for r in rows), rows)
    h.check(
        "no reference is a timeline step", not any("Reference" in x for x in t.titles()), t.titles()
    )


# -- E ---------------------------------------------------------------------------------------------
def e_save():
    path = os.path.join(tempfile.mkdtemp(prefix="fission180_bookcomp_"), "project.FCStd")
    state["path"] = path
    doc = k.doc()
    doc.saveAs(path)
    App.closeDocument(doc.Name)


def e_reopen():
    App.openDocument(state["path"])
    h.fit()


def e_reopened():
    doc = k.doc()
    doc.recompute()
    sk = sketch()
    if not h.check("the sketch is there", sk is not None):
        return
    h.check("the projections are there", len(externals()) == state["count"], describe())
    part = k.part("Nozzle")
    part.Placement = App.Placement(V(30, 0, 0), App.Rotation())
    doc.recompute()
    h.check(
        "still following after reopening: the edge back at (30, 0) - (50, 0)",
        has_line((30, 0, 0), (50, 0, 0)),
        describe(),
    )


h.run(
    "book_components_project",
    [
        new_design,
        a_activate,
        a_sketch,
        a_plane,
        a_opened,
        press_p,
        a_edge,
        a_edge_projected,
        a_circle,
        a_circle_projected,
        a_corner,
        a_corner_projected,
        a_face,
        a_face_projected,
        a_face_again,
        a_not_twice,
        escape,
        a_still_open,
        undo_key,
        c_face_gone,
        redo_key,
        c_face_back,
        b_circle,
        b_concentric,
        b_on_axis,
        d_finish,
        d_move,
        d_followed,
        e_save,
        e_reopen,
        e_reopened,
    ],
    paced_by="state",
)
