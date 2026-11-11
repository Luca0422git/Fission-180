# SPDX-License-Identifier: LGPL-2.1-or-later
"""New things go into the ACTIVE component, whatever was clicked (book parity report, bugs
5, 6, 7 and 8; the Hot End's PTFE Tube, the Tesla Turbine's gaskets and side wall, the
Robotic Hand's Axle). Only real input for what is tested.

Setup (through the modules): the component "Nozzle" with a 20 x 20 x 10 block, standing
30 mm along X (so the two components' own coordinates differ); "Pins" with a cylinder
(radius 5, height 20, its axis through x 0, y 40); the empty components "PTFE Tube",
"Gaskets", "Wall" and "Axle".

  A  (bug 5) PTFE Tube made active (its ring), Create Sketch, click the Nozzle's top face:
     PTFE Tube stays the active component, the sketch is in PTFE Tube and lies on the
     face (z 10, on the block). A circle (r 3) at the face's middle, Finish Sketch, E:
     the operation starts as New Body (the active component has no body yet: bug 10),
     5 mm, OK: the tube's body is in PTFE Tube, where it was drawn; the Nozzle is unchanged.
  B  Undo / Redo of the extrude, and of the sketch.
  C  (bug 6) Gaskets active, E, click the Nozzle's +X face, 2 mm, New Body, OK: the new
     body is in Gaskets (it was made in the Nozzle), 20 x 10 x 2 on that face.
  D  (bug 7) Wall active, CONSTRUCT > Offset Plane, click the gasket's outer face, 4 mm,
     OK: the plane is in Wall, 4 mm off the face.
  E  (bug 8) Axle active, CONSTRUCT > Axis Through Cylinder/Cone/Torus, click the pin's
     wall, OK: the axis is in Axle, along the pin's axis; Axle has no body row.
     Then, Axle still active, Create Sketch and the Wall's Plane1 clicked in the browser
     (a plane of another component): the sketch is in Axle, lies on that plane (x 56) and
     hangs on a hidden reference; no "Reference" row shows.
  H  (bug 10, as the report saw it) Axle still active (no solid in it yet), a sketch on the
     Nozzle's top face, a circle (r 2) beside the tube, E. 25 mm down (two fifths of it
     inside the Nozzle): New Body, the Nozzle untouched (it came up as Cut and silently cut
     the other component). 4 mm down (wholly inside the Nozzle): Cut by itself, the Nozzle
     listed under Bodies to Cut (Fusion's rule, extrude-2). New Body chosen by hand, OK: a
     body in Axle, the Nozzle unchanged.
  F  The Nozzle moved 15 mm along Y (its Placement): the tube's sketch, the gasket and
     the axis' plane follow as far as FreeCAD links allow (the sketch stays on the face).
  G  Save, close, reopen: everything is where it was, in the same components.
"""

import os
import tempfile

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import book_components_steps as k
from Fission180Tests.gui import component_steps as cs
from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import inspect_steps as ist
from Fission180Tests.gui import timeline_input as t

V = App.Vector
state = {}
NOZZLE = 20 * 20 * 10.0


def xpanel():
    from fission180 import extrude_ui

    p = extrude_ui.ExtrudePanel.last
    return p if p is not None and not p._closed else None


def new_design():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("BookComponentsActive")
    nozzle = k.new_component("Nozzle", at=(30, 0, 0))
    state["nozzle_body"] = k.add_box(nozzle, (0, 0, 20, 20), 10).Name
    pins = k.new_component("Pins")
    state["pin_body"] = k.add_cylinder(pins, (0, 40), 5, 20).Name
    for label in ("PTFE Tube", "Gaskets", "Wall", "Axle"):
        k.new_component(label)
    k.settle_design()


def nozzle_body():
    return k.doc().getObject(state["nozzle_body"])


def setup_done():
    h.check("six components", len(k.labels()) == 6, k.labels())
    k.box_is("the Nozzle stands 30 mm along X", k.part("Nozzle"), [30, 0, 0, 50, 20, 10])
    h.check("the root is active", k.active_label() == "", k.active_label())


# -- A: a sketch on another component's face ---------------------------------------------------
def a_activate():
    cs.click_radio("PTFE Tube")


a_activate.done = lambda: k.active_label() == "PTFE Tube"
a_activate.done_what = "PTFE Tube is the active component"


def a_sketch():
    h.fit()
    h.ribbon("Create Sketch")


def a_face():
    h.click(V(40, 10, 10))  # the Nozzle's top face


a_face.done = lambda: h.in_sketch() is not None
a_face.done_what = "a sketch opened on the Nozzle's face"


def a_in_tube():
    sk = h.in_sketch()
    if not h.check("sketch open", sk is not None):
        return
    state["sketch"] = sk.Name
    h.check(
        "PTFE Tube is still the active component", k.active_label() == "PTFE Tube", k.active_label()
    )
    h.check(
        "the sketch is in PTFE Tube", k.container_label(sk) == "PTFE Tube", k.container_label(sk)
    )
    place = sk.getGlobalPlacement()
    h.check("the sketch lies on the face (z 10)", abs(place.Base.z - 10) < 1e-6, place)
    normal = place.Rotation.multVec(V(0, 0, 1))
    h.check("flat on it", abs(abs(normal.z) - 1) < 1e-6, normal)
    # the circle at the face's middle (40, 10): the sketch's own coordinates
    local = place.inverse().multVec(V(40, 10, 10))
    state["centre"] = (local.x, local.y)
    h.draw_circle(sk, local.x, local.y, 3)


def a_finish():
    h.ribbon("Finish Sketch")


a_finish.done = lambda: h.in_sketch() is None
a_finish.done_what = "the sketch closed"


def a_extrude():
    h.fit()
    h.check(
        "still PTFE Tube after Finish Sketch", k.active_label() == "PTFE Tube", k.active_label()
    )
    h.press("e")


a_extrude.done = lambda: xpanel() is not None
a_extrude.done_what = "the Extrude dialog is open"


def a_profile():
    p = xpanel()
    if p is not None and not p.profiles:
        h.click(V(40, 10, 10))


def a_distance():
    p = xpanel()
    if not h.check("extrude dialog open", p is not None):
        return
    h.check("a profile is picked", bool(p.profiles), p.profiles)
    b.type_into(p.distance.widget, "5")


def a_operation():
    p = xpanel()
    if p is None:
        return
    h.caught_up(p)
    h.check(
        "the first extrude of an empty component starts as New Body (bug 10)",
        p.operation.currentText() == "New Body",
        p.operation.currentText(),
    )
    h.shot("A-extrude")


def a_ok():
    h.task_button("OK")


a_ok.done = lambda: xpanel() is None
a_ok.done_what = "the Extrude dialog closed"


def a_made():
    tube = k.bodies_of("PTFE Tube")
    if h.check(
        "one body in PTFE Tube", len(tube) == 1, [x.Label for x in k.all_bodies_of("PTFE Tube")]
    ):
        state["tube"] = tube[0].Name
        h.check(
            "the tube: pi * 9 * 5",
            k.close(k.volume(tube[0]), 3.141592653589793 * 9 * 5),
            k.volume(tube[0]),
        )
        k.box_is("where it was drawn, on the face", tube[0], [37, 7, 10, 43, 13, 15])
    h.check(
        "the Nozzle has one body",
        len(k.bodies_of("Nozzle")) == 1,
        [x.Label for x in k.all_bodies_of("Nozzle")],
    )
    h.check(
        "the Nozzle is unchanged", k.close(k.volume(nozzle_body()), NOZZLE), k.volume(nozzle_body())
    )
    h.check(
        "no sketch went into the Nozzle",
        len(k.sketches_in("Nozzle")) == 1,
        [s.Label for s in k.sketches_in("Nozzle")],
    )
    h.check("PTFE Tube is still active", k.active_label() == "PTFE Tube", k.active_label())
    k.no_empty_invalid_bodies()


# -- B: undo / redo ----------------------------------------------------------------------------
def b_undo():
    t.undo()


def b_undone():
    h.check("Undo takes the tube's body away", len(k.bodies_of("PTFE Tube")) == 0)
    h.check("the sketch stays in PTFE Tube", len(k.sketches_in("PTFE Tube")) == 1)
    h.check("the Nozzle is unchanged", k.close(k.volume(nozzle_body()), NOZZLE))


def b_redo():
    t.redo()


def b_redone():
    h.check("Redo brings the tube back", len(k.bodies_of("PTFE Tube")) == 1)
    tube = k.bodies_of("PTFE Tube")
    if tube:
        k.box_is("in place", tube[0], [37, 7, 10, 43, 13, 15])


# -- C: Extrude of a face with New Body --------------------------------------------------------
def c_activate():
    cs.click_radio("Gaskets")


c_activate.done = lambda: k.active_label() == "Gaskets"
c_activate.done_what = "Gaskets is the active component"


def c_extrude():
    h.fit()
    h.press("e")


c_extrude.done = lambda: xpanel() is not None
c_extrude.done_what = "the Extrude dialog is open"


def c_face():
    h.click(V(50, 10, 5))  # the Nozzle's +X face


def c_distance():
    p = xpanel()
    if not h.check("extrude dialog open", p is not None):
        return
    h.check("the face is the profile", bool(p.profiles), p.profiles)
    b.type_into(p.distance.widget, "2")


def c_operation():
    p = xpanel()
    if p is None:
        return
    h.caught_up(p)
    if p.operation.currentText() != "New Body":
        b.choose(p.operation, "New Body")


def c_ok():
    p = xpanel()
    if p is not None:
        h.caught_up(p)
        h.check(
            "Operation reads New Body",
            p.operation.currentText() == "New Body",
            p.operation.currentText(),
        )
    h.task_button("OK")


c_ok.done = lambda: xpanel() is None
c_ok.done_what = "the Extrude dialog closed"


def c_made():
    gasket = k.bodies_of("Gaskets")
    if h.check(
        "the new body is in Gaskets (bug 6)",
        len(gasket) == 1,
        [x.Label for x in k.all_bodies_of("Gaskets")],
    ):
        state["gasket"] = gasket[0].Name
        h.check("20 x 10 x 2", k.close(k.volume(gasket[0]), 400.0), k.volume(gasket[0]))
        k.box_is("on the Nozzle's +X face", gasket[0], [50, 0, 0, 52, 20, 10])
    h.check(
        "the Nozzle still has one body",
        len(k.bodies_of("Nozzle")) == 1,
        [x.Label for x in k.all_bodies_of("Nozzle")],
    )
    h.check(
        "the Nozzle is unchanged", k.close(k.volume(nozzle_body()), NOZZLE), k.volume(nozzle_body())
    )
    h.check("Gaskets is still active", k.active_label() == "Gaskets", k.active_label())


# -- D: Offset Plane ---------------------------------------------------------------------------
def d_activate():
    cs.click_radio("Wall")


d_activate.done = lambda: k.active_label() == "Wall"
d_activate.done_what = "Wall is the active component"


def d_offset():
    h.click_empty()
    h.fit()
    ist.menu("CONSTRUCT", "Offset Plane")


d_offset.done = lambda: ist.construct_panel() is not None
d_offset.done_what = "the Offset Plane dialog is open"


def d_face():
    h.click(V(52, 10, 5))  # the gasket's outer face


def d_distance():
    p = ist.construct_panel()
    if not h.check("Offset Plane open", p is not None):
        return
    h.check("the face is picked", p.picks[0] is not None, p.picks)
    ist.type_into(p.distance.widget, "4")


def d_ok():
    p = ist.construct_panel()
    if p is not None:
        h.caught_up(p)
    h.task_button("OK")


d_ok.done = lambda: ist.construct_panel() is None
d_ok.done_what = "the Offset Plane dialog closed"


def d_made():
    planes = k.datums_in("Wall", "PartDesign::Plane")
    every = [o for o in k.doc().Objects if o.TypeId == "PartDesign::Plane"]
    if h.check(
        "the plane is in Wall (bug 7)",
        len(planes) == 1 and len(every) == 1,
        [(o.Label, k.container_label(o)) for o in every],
    ):
        state["plane"] = planes[0].Name
        place = planes[0].getGlobalPlacement()
        normal = place.Rotation.multVec(V(0, 0, 1))
        h.check("4 mm off the gasket's face (x 56)", abs(place.Base.x - 56) < 1e-6, place)
        h.check("parallel to it", abs(abs(normal.x) - 1) < 1e-6, normal)
    h.check("Wall is still active", k.active_label() == "Wall", k.active_label())
    h.check("nothing went into Gaskets", len(k.datums_in("Gaskets", "PartDesign::Plane")) == 0)


# -- E: Axis Through Cylinder ------------------------------------------------------------------
def e_activate():
    cs.click_radio("Axle")


e_activate.done = lambda: k.active_label() == "Axle"
e_activate.done_what = "Axle is the active component"


def e_axis():
    h.click_empty()
    h.fit()
    ist.menu("CONSTRUCT", "Axis Through Cylinder/Cone/Torus")


e_axis.done = lambda: ist.construct_panel() is not None
e_axis.done_what = "the Axis dialog is open"


def e_wall():
    h.click(V(5 * 0.7071, 40 - 5 * 0.7071, 10))  # the pin's round wall, towards the camera


def e_ok():
    p = ist.construct_panel()
    if h.check("Axis open", p is not None):
        h.check("the wall is picked", p.picks[0] is not None, p.picks)
    h.task_button("OK")


e_ok.done = lambda: ist.construct_panel() is None
e_ok.done_what = "the Axis dialog closed"


def e_made():
    axes = k.datums_in("Axle", "PartDesign::Line")
    every = [o for o in k.doc().Objects if o.TypeId == "PartDesign::Line"]
    if h.check(
        "the axis is in Axle (bug 8)",
        len(axes) == 1 and len(every) == 1,
        [(o.Label, k.container_label(o)) for o in every],
    ):
        state["axis"] = axes[0].Name
        place = axes[0].getGlobalPlacement()
        direction = place.Rotation.multVec(V(0, 0, 1))
        h.check("along the pin (Z)", abs(abs(direction.z) - 1) < 1e-6, direction)
        h.check(
            "through the pin's centre (0, 40)",
            abs(place.Base.x) < 1e-6 and abs(place.Base.y - 40) < 1e-6,
            place,
        )
    h.check("Axle holds no solid body", len(k.bodies_of("Axle")) == 0)
    h.check("Pins got no axis", len(k.datums_in("Pins", "PartDesign::Line")) == 0)
    rows = t.children("Axle")
    h.check(
        "Axle's rows: no Bodies folder, a Construction folder",
        "Bodies" not in rows and "Construction" in rows,
        rows,
    )
    k.no_empty_invalid_bodies()
    h.shot("E-axis")


# -- E2: a sketch on another component's construction plane ------------------------------------
def e2_sketch():
    h.click_empty()
    h.fit()
    h.ribbon("Create Sketch")


def e2_plane_row():
    plane = k.doc().getObject(state["plane"])
    t.click_row(plane.Label)


e2_plane_row.done = lambda: h.in_sketch() is not None
e2_plane_row.done_what = "a sketch opened on the Wall's plane"


def e2_opened():
    sk = h.in_sketch()
    if not h.check("sketch open", sk is not None):
        return
    h.check(
        "the sketch is in Axle, the active component",
        k.container_label(sk) == "Axle",
        k.container_label(sk),
    )
    h.check("Axle is still active", k.active_label() == "Axle", k.active_label())
    place = sk.getGlobalPlacement()
    normal = place.Rotation.multVec(V(0, 0, 1))
    h.check("it lies on the Wall's plane (x 56)", abs(place.Base.x - 56) < 1e-6, place)
    h.check("flat on it", abs(abs(normal.x) - 1) < 1e-6, normal)
    h.check("no plane was added to Wall", len(k.datums_in("Wall", "PartDesign::Plane")) == 1)


def e2_finish():
    h.ribbon("Finish Sketch")


e2_finish.done = lambda: h.in_sketch() is None
e2_finish.done_what = "the sketch closed"


def e2_rows():
    rows = t.children("Axle") or []
    shown = []
    for folder in rows:
        shown += t.children(folder) or []
    h.check(
        "no reference shows in Axle's folders",
        not any("Reference" in r for r in shown),
        (rows, shown),
    )
    h.check(
        "no reference is a timeline step", not any("Reference" in x for x in t.titles()), t.titles()
    )
    k.no_empty_invalid_bodies("no invalid body after the sketch on the plane")


# -- H: the first extrude of a component into another component's body ------------------------
def h_activate():
    h.check(
        "Axle is the active component, without a solid",
        k.active_label() == "Axle" and not k.bodies_of("Axle"),
        k.active_label(),
    )


def h_sketch():
    h.fit()
    h.ribbon("Create Sketch")


def h_face():
    h.click(V(34, 4, 10))  # the Nozzle's top face, beside the tube


h_face.done = lambda: h.in_sketch() is not None
h_face.done_what = "a sketch opened on the Nozzle's face"


def h_draw():
    sk = h.in_sketch()
    if not h.check("sketch open", sk is not None):
        return
    state["slot_sketch"] = sk.Name
    h.check("the sketch is in Axle", k.container_label(sk) == "Axle", k.container_label(sk))
    edges = [g for g in list(sk.ExternalGeo)[2:] if g.TypeId == "Part::GeomLineSegment"]
    h.check(
        "Auto project shows the face's four edges (another component's face)",
        len(edges) == 4,
        len(edges),
    )
    local = sk.getGlobalPlacement().inverse().multVec(V(34, 4, 10))
    h.draw_circle(sk, local.x, local.y, 2)


def h_extrude():
    h.fit()
    h.press("e")


h_extrude.done = lambda: xpanel() is not None
h_extrude.done_what = "the Extrude dialog is open"


def h_profile():
    p = xpanel()
    if p is not None and not p.profiles:
        h.click(V(34, 4, 10))


def h_distance():
    p = xpanel()
    if not h.check("extrude dialog open", p is not None):
        return
    h.check("a profile is picked", bool(p.profiles), p.profiles)
    b.type_into(p.distance.widget, "-25")


def h_small_overlap():
    # Bug 10 as the book report met it (the Strandbeest link overlapped another component's
    # pin by about 6 % and came up as a Cut that silently cut the pin): a new part that only
    # overlaps a body of another component is a New Body. 25 down through the Nozzle's 10 mm
    # is two fifths inside it.
    p = xpanel()
    if p is None:
        return
    h.caught_up(p)
    h.check(
        "two fifths inside another component's body: New Body, not Cut (bug 10)",
        p.operation.currentText() == "New Body",
        p.operation.currentText(),
    )
    h.check(
        "the Nozzle is untouched in that preview",
        k.close(k.volume(nozzle_body()), NOZZLE),
        k.volume(nozzle_body()),
    )
    b.type_into(p.distance.widget, "-4")


def h_operation():
    # The other side of the rule (extrude-2, book-extrude-2.md item 3; Autodesk's J. Strater
    # on the forum, "Tool behaviour - unexpected": mostly inside a shown body, of whichever
    # component: Cut): 4 down is wholly inside the Nozzle, so Fusion proposes Cut, and not
    # silently: the Nozzle's body is listed under Bodies to Cut. (This check expected New
    # Body here until extrude-2 built the rule; the first fix for bug 10 had let only bodies
    # of the active component decide. The one-half threshold is a Guess.)
    p = xpanel()
    if p is None:
        return
    h.caught_up(p)
    h.check(
        "wholly inside another component's body: Cut by itself",
        p.operation.currentText() == "Cut",
        p.operation.currentText(),
    )
    names = p._participant_names(compute=False) or []
    h.check("the Nozzle's body is under Bodies to Cut", names == [state["nozzle_body"]], names)
    # the Axle's pin is wanted as a body of its own here: New Body chosen by hand
    ui.choose(p.operation, "New Body")


def h_new_body():
    p = xpanel()
    if p is None:
        return
    h.caught_up(p)
    h.check(
        "New Body chosen by hand stays",
        p.operation.currentText() == "New Body",
        p.operation.currentText(),
    )


def h_made():
    slot = k.bodies_of("Axle")
    if h.check("one body in Axle", len(slot) == 1, [x.Label for x in k.all_bodies_of("Axle")]):
        state["slot"] = slot[0].Name
        h.check(
            "pi * 4 * 4", k.close(k.volume(slot[0]), 3.141592653589793 * 4 * 4), k.volume(slot[0])
        )
        k.box_is("inside the Nozzle's top", slot[0], [32, 2, 6, 36, 6, 10])
    h.check(
        "the Nozzle was not cut", k.close(k.volume(nozzle_body()), NOZZLE), k.volume(nozzle_body())
    )


# -- F: the Nozzle moves -----------------------------------------------------------------------
def f_move():
    cs.click_radio("BookComponentsActive")


f_move.done = lambda: k.active_label() == ""
f_move.done_what = "the root is active again"


def f_moved():
    from fission180 import component_move

    nozzle = k.part("Nozzle")
    doc = k.doc()
    doc.openTransaction("Move")
    movement = App.Placement(V(0, 15, 0), App.Rotation())
    component_move.place(nozzle, component_move.moved(nozzle, nozzle.Placement, movement))
    doc.commitTransaction()
    doc.recompute()


def f_followed():
    k.box_is("the Nozzle moved 15 mm along Y", k.part("Nozzle"), [30, 15, 0, 50, 35, 10])
    sk = k.doc().getObject(state.get("sketch", ""))
    if h.check("the tube's sketch is still there", sk is not None):
        place = sk.getGlobalPlacement()
        h.check("still flat on the face's plane (z 10)", abs(place.Base.z - 10) < 1e-6, place)
        h.check("the sketch has no error", "Invalid" not in sk.State, sk.State)
    k.no_empty_invalid_bodies("no invalid body after the move")


# -- G: save / reopen --------------------------------------------------------------------------
def g_save():
    path = os.path.join(tempfile.mkdtemp(prefix="fission180_bookcomp_"), "active.FCStd")
    state["path"] = path
    doc = k.doc()
    doc.saveAs(path)
    App.closeDocument(doc.Name)


def g_reopen():
    App.openDocument(state["path"])
    h.fit()


def g_reopened():
    doc = k.doc()
    doc.recompute()
    h.check("six components", len(k.labels()) == 6, k.labels())
    h.check("the tube's body is in PTFE Tube", len(k.bodies_of("PTFE Tube")) == 1)
    h.check("the gasket is in Gaskets", len(k.bodies_of("Gaskets")) == 1)
    h.check("the plane is in Wall", len(k.datums_in("Wall", "PartDesign::Plane")) == 1)
    h.check("the axis is in Axle", len(k.datums_in("Axle", "PartDesign::Line")) == 1)
    h.check("the Nozzle has one body", len(k.bodies_of("Nozzle")) == 1)
    k.no_empty_invalid_bodies("no invalid body after reopening")


h.run(
    "book_components_active",
    [
        new_design,
        setup_done,
        a_activate,
        a_sketch,
        a_face,
        a_in_tube,
        a_finish,
        a_extrude,
        a_profile,
        a_distance,
        a_operation,
        a_ok,
        a_made,
        b_undo,
        b_undone,
        b_redo,
        b_redone,
        c_activate,
        c_extrude,
        c_face,
        c_distance,
        c_operation,
        c_ok,
        c_made,
        d_activate,
        d_offset,
        d_face,
        d_distance,
        d_ok,
        d_made,
        e_activate,
        e_axis,
        e_wall,
        e_ok,
        e_made,
        e2_sketch,
        e2_plane_row,
        e2_opened,
        e2_finish,
        e2_rows,
        h_activate,
        h_sketch,
        h_face,
        h_draw,
        a_finish,
        h_extrude,
        h_profile,
        h_distance,
        h_small_overlap,
        h_operation,
        h_new_body,
        a_ok,
        h_made,
        f_move,
        f_moved,
        f_followed,
        g_save,
        g_reopen,
        g_reopened,
    ],
    paced_by="state",
)
