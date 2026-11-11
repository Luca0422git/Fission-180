# SPDX-License-Identifier: LGPL-2.1-or-later
"""A construction plane built on another component keeps its place when that component is
moved later, like a sketch's reference; New Component shows Fusion's Internal / External
choice (wave 7, components-2: what the first components builder left open). Only real
input for what is tested.

Fusion works a construction out where the parts stood at its place in the timeline: a
plane offset from a face of another component does not jump when that component is moved
by a later Move or joint (a guess from the timeline model; a sketch's projection behaves
so). Before, the plane was worked out from where both components stand NOW at every
recompute: it followed the other component's later moves, and everything modelled on it
reshaped, while a sketch put on the same face stayed.

Setup (through the modules): "Nozzle" with a 20 x 20 x 10 block, standing 30 mm along X;
the empty component "Wall".

  A  Wall active (its ring), CONSTRUCT > Offset Plane, the Nozzle's top face, 4 mm, OK: the
     plane is in Wall, at z 14.
  B  The Nozzle moved 15 mm up (its Placement, as Move does) and the design recomputed:
     the plane stays at z 14 (it jumped to z 29).
  C  The Nozzle's block made 2 mm taller (its extrude): the plane follows the CHANGE of the
     part: 2 mm up, z 16.
  D  Wall itself moved 7 mm along X: the plane moves with its own component.
  E  Ctrl+Z three times, Ctrl+Y three times: the same places.
  F  Save, close, reopen, recompute: the plane is where it was.
  G  ASSEMBLE > New Component: "Internal" is chosen, "External" is greyed and says why and
     what to do instead; a click on it changes nothing; Cancel.
  H  Right-click the Nozzle's body row > Properties: the Properties dialog opens for that
     body; the Nozzle's own row > Properties: for the component.
"""

import os
import tempfile

import FreeCAD as App
import FreeCADGui as Gui

from Fission180Tests.gui import book_components_steps as k
from Fission180Tests.gui import component_steps as cs
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import inspect_steps as ist
from Fission180Tests.gui import timeline_input as t
from Fission180Tests.gui import widget_input as w

V = App.Vector
state = {}


def new_design():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("BookComponents2Refs")
    nozzle = k.new_component("Nozzle", at=(30, 0, 0))
    state["nozzle_body"] = k.add_box(nozzle, (0, 0, 20, 20), 10).Name
    k.new_component("Wall")
    k.settle_design()


def plane():
    return k.doc().getObject(state.get("plane", ""))


def plane_at(name, x, z):
    p = plane()
    if not h.check("%s: the plane is there" % name, p is not None):
        return
    place = p.getGlobalPlacement()
    normal = place.Rotation.multVec(V(0, 0, 1))
    h.check(
        "%s: the plane at z %g" % (name, z),
        abs(place.Base.z - z) < 1e-6 and abs(abs(normal.z) - 1) < 1e-6,
        (place, normal),
    )
    h.check("%s: its origin at x %g" % (name, x), abs(place.Base.x - x) < 1e-6, place.Base)
    h.check("%s: no error on it" % name, "Invalid" not in p.State and "Error" not in p.State)


# -- A ---------------------------------------------------------------------------------------------
def a_activate():
    cs.click_radio("Wall")


a_activate.done = lambda: k.active_label() == "Wall"
a_activate.done_what = "Wall is the active component"


def a_offset():
    h.click_empty()
    h.fit()
    ist.menu("CONSTRUCT", "Offset Plane")


a_offset.done = lambda: ist.construct_panel() is not None
a_offset.done_what = "the Offset Plane dialog is open"


def a_face():
    h.click(V(40, 10, 10))  # the Nozzle's top face


def a_distance():
    p = ist.construct_panel()
    if h.check("Offset Plane open with the face picked", p is not None and p.picks[0] is not None):
        ist.type_into(p.distance.widget, "4")


def a_ok():
    p = ist.construct_panel()
    if p is not None:
        h.caught_up(p)
    h.task_button("OK")


a_ok.done = lambda: ist.construct_panel() is None
a_ok.done_what = "the Offset Plane dialog closed"


def a_made():
    planes = k.datums_in("Wall", "PartDesign::Plane")
    if h.check("one plane, in Wall (the active component)", len(planes) == 1, planes):
        state["plane"] = planes[0].Name
        state["x0"] = planes[0].getGlobalPlacement().Base.x
        plane_at("A", state["x0"], 14)
    h.check("Wall is still active", k.active_label() == "Wall", k.active_label())


# -- B ---------------------------------------------------------------------------------------------
def move(label, vector, name):
    from fission180 import component_move

    part = k.part(label)
    doc = k.doc()
    doc.openTransaction(name)
    movement = App.Placement(V(*vector), App.Rotation())
    component_move.place(part, component_move.moved(part, part.Placement, movement))
    doc.commitTransaction()
    doc.recompute()


def b_move_nozzle():
    move("Nozzle", (0, 0, 15), "Move")


def b_stays():
    k.box_is("the Nozzle moved 15 mm up", k.part("Nozzle"), [30, 0, 15, 50, 20, 25])
    plane_at("B (the Nozzle moved later)", state["x0"], 14)


# -- C ---------------------------------------------------------------------------------------------
def c_taller():
    from fission180 import extrude

    doc = k.doc()
    body = doc.getObject(state["nozzle_body"])
    doc.openTransaction("Edit Extrude")
    extrude.apply(body.Tip, {"distance": 12.0})
    doc.commitTransaction()
    doc.recompute()


def c_follows():
    k.box_is("the Nozzle's block is 12 tall", k.part("Nozzle"), [30, 0, 15, 50, 20, 27])
    plane_at("C (the part changed: 2 mm taller)", state["x0"], 16)


# -- D ---------------------------------------------------------------------------------------------
def d_move_wall():
    move("Wall", (7, 0, 0), "Move")


def d_with_its_component():
    plane_at("D (its own component moved 7 mm along X)", state["x0"] + 7, 16)


# -- E ---------------------------------------------------------------------------------------------
def undo():
    t.undo()


def redo():
    t.redo()


def e_undone_wall():
    plane_at("Ctrl+Z (the Wall's move)", state["x0"], 16)


def e_undone_taller():
    plane_at("Ctrl+Z (taller)", state["x0"], 14)


def e_undone_move():
    k.box_is("Ctrl+Z: the Nozzle back down", k.part("Nozzle"), [30, 0, 0, 50, 20, 10])
    plane_at("Ctrl+Z (the Nozzle's move)", state["x0"], 14)


def e_redone():
    k.box_is("Ctrl+Y: the Nozzle up and taller", k.part("Nozzle"), [30, 0, 15, 50, 20, 27])
    plane_at("Ctrl+Y three times", state["x0"] + 7, 16)


# -- F ---------------------------------------------------------------------------------------------
def f_save():
    path = os.path.join(tempfile.mkdtemp(prefix="fission180_c2_refs_"), "refs.FCStd")
    state["path"] = path
    k.doc().saveAs(path)
    App.closeDocument(k.doc().Name)


def f_reopen():
    App.openDocument(state["path"])
    Gui.activateWorkbench("Fission180Workbench")
    h.fit()


def f_reopened():
    doc = k.doc()
    for obj in doc.Objects:
        obj.touch()
    doc.recompute()
    plane_at("reopened and recomputed", state["x0"] + 7, 16)
    h.check("the plane is in Wall", k.container_label(plane()) == "Wall")


# -- G ---------------------------------------------------------------------------------------------
def g_open():
    Gui.Selection.clearSelection()
    h.ribbon("New Component")


g_open.done = lambda: cs.new_component_panel() is not None
g_open.done_what = "the New Component dialog is open"


def g_choice():
    p = cs.new_component_panel()
    if not h.check("New Component open", p is not None):
        return
    h.check("Internal is chosen", p.internal.isChecked() and p.internal.isVisible())
    h.check("External is shown, greyed", p.external.isVisible() and not p.external.isEnabled())
    tip = p.external.toolTip()
    h.check(
        "External says why it is greyed and what to do instead",
        "one design per file" in tip and "Insert into Current Design" in tip,
        tip,
    )
    w.click(p.external)  # a person tries it


def g_unchanged():
    p = cs.new_component_panel()
    if p is not None:
        h.check("a click on External changes nothing", p.internal.isChecked())
        h.check("External still not chosen", not p.external.isChecked())
    count = len(k.labels())
    h.task_button("Cancel")
    state["count"] = count


g_unchanged.done = lambda: cs.new_component_panel() is None
g_unchanged.done_what = "the New Component dialog closed"


def g_cancelled():
    h.check("Cancel made no component", len(k.labels()) == state["count"], k.labels())


# -- H: Properties from the browser (the looks builder's dialog, the orchestrator's menu line) --
def props():
    from fission180 import properties_ui

    return properties_ui.dialog()


def h_body_menu():
    body = k.doc().getObject(state["nozzle_body"])
    state["body_label"] = body.Label
    h.check(
        "the body's menu offers Properties",
        "Properties" in t.row_menu_entries(body.Label),
        t.row_menu_entries(body.Label),
    )
    t.row_menu(body.Label, "Properties")


h_body_menu.done = lambda: props() is not None
h_body_menu.done_what = "the Properties dialog is open"


def h_body_props():
    p = props()
    if not h.check("Properties opened from the body's row", p is not None):
        return
    body = k.doc().getObject(state["nozzle_body"])
    h.check(
        "it is about that body (one body counted: the Nozzle's)",
        [x.Name for x in p.counted] == [body.Name],
        [x.Label for x in p.counted],
    )
    h.check("its title names the body", state["body_label"] in p.title.text(), p.title.text())
    w.click(p.close_button)


h_body_props.done = lambda: props() is None
h_body_props.done_what = "the Properties dialog closed"


def h_component_menu():
    h.check(
        "the component's menu offers Properties",
        "Properties" in t.row_menu_entries("Nozzle"),
        t.row_menu_entries("Nozzle"),
    )
    t.row_menu("Nozzle", "Properties")


h_component_menu.done = lambda: props() is not None
h_component_menu.done_what = "the Properties dialog is open"


def h_component_props():
    p = props()
    if not h.check("Properties opened from the component's row", p is not None):
        return
    body = k.doc().getObject(state["nozzle_body"])
    h.check(
        "it is about that component (its body counted)",
        [x.Name for x in p.counted] == [body.Name],
        [x.Label for x in p.counted],
    )
    h.check("its title names the component", "Nozzle" in p.title.text(), p.title.text())
    w.click(p.close_button)


h_component_props.done = lambda: props() is None
h_component_props.done_what = "the Properties dialog closed"


h.run(
    "book_components2_refs",
    [
        new_design,
        a_activate,
        a_offset,
        a_face,
        a_distance,
        a_ok,
        a_made,
        b_move_nozzle,
        b_stays,
        c_taller,
        c_follows,
        d_move_wall,
        d_with_its_component,
        undo,
        e_undone_wall,
        undo,
        e_undone_taller,
        undo,
        e_undone_move,
        redo,
        redo,
        redo,
        e_redone,
        f_save,
        f_reopen,
        f_reopened,
        g_open,
        g_choice,
        g_unchanged,
        g_cancelled,
        h_body_menu,
        h_body_props,
        h_component_menu,
        h_component_props,
    ],
    paced_by="state",
)
