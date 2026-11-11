# SPDX-License-Identifier: LGPL-2.1-or-later
"""Picking profiles the way the book does (wave 7, the parity report's items on Extrude and
Revolve picks). Only real clicks and keys; the parts are made through the same code the
dialogs use.

The tube: a ring r 15 / r 6 sketched on the XZ plane (centre x 0, z 20), extruded 5 each
way (y -5..5). Its sketch is shown again, like the book's "Show Sketch 1".

K1  E with the used sketch shown: the sketch stays shown (it was reported hidden again), and
    a click where the tube's front face is in front of the ring area picks the AREA (Fusion
    prefers the profile; it picked the face). A click on it again, where the face is in front
    of the now picked area, goes to the face: the extrusion ends there (Distance 5).
K2  The first click right after E, in the same breath, is not lost.
K3  The tube hidden (its eye): the areas of its sketch can be clicked, in Extrude and in
    Revolve (nothing could be clicked: the hidden body still counted as "in front").
K4  Revolve: after the first profile the Axis box waits (Fusion); a click inside a second,
    narrow area that runs along the Z axis adds it (it went to the axis); a click right on
    the axis sets the axis.
K5  Profiles over a void: three small circles sketched on the tube's front face (y = -5) over its
    bore; each click picks its circle (not the bore's wall behind).
K6  Start: Offset chosen first, then a profile clicked: it is picked, the offset arrow shows.
K7  A slot 0.4 mm wide: a click 3 pixels beside it picks it.
K8  A small round boss (r 1.5): a click on the edge of its top picks the top face.
K9  An offset plane's square in front of a face: the click takes the face behind it.
K10 Two half discs side by side: after the first is picked, its value box does not cover the
    second, and a click on the second picks it.
K11 One profile in view, in another component than the active one: picked by itself (Fusion:
    the one visible profile), in Extrude and in Revolve.
"""
import math

import FreeCAD as App
import FreeCADGui as Gui
import Part
from PySide import QtCore
from PySide6 import QtTest

from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_input

V = App.Vector
s = {}


def panel():
    from fission180 import extrude_ui

    p = extrude_ui.ExtrudePanel.last
    return p if p is not None and not p._closed else None


def rpanel():
    from fission180 import revolve_ui

    p = revolve_ui.RevolvePanel.last
    return p if p is not None and not p._closed else None


def near(a, b, tol=1e-4):
    return abs(a - b) <= tol * max(1.0, abs(b))


def keys(p):
    return sorted((o.Name, sub) for o, sub in p.profiles)


def area_of(p, index=-1):
    """The area (mm2) of a picked sketch profile."""
    from fission180 import extrude

    obj, sub = p.profiles[index]
    return sum(f.Area for f in extrude.local_faces(obj, sub))


def press_e():
    h.click_empty()
    h.press("e")


press_e.done = lambda: panel() is not None
press_e.done_what = "the Extrude dialog is open"


def open_revolve():
    h.click_empty()
    sketch_input.menu_item("CREATE", "Revolve")


open_revolve.done = lambda: rpanel() is not None
open_revolve.done_what = "the Revolve dialog is open"


def cancel():
    h.task_button("Cancel")


cancel.done = lambda: panel() is None and rpanel() is None
cancel.done_what = "the dialog is closed"


def new_tube(name="PickTube"):
    from fission180 import commands, extrude, sketch_ui

    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument(name)
    body = commands.ensure_body()
    planes = sketch_ui.origin_planes(body)
    sk = sketch_ui.create_sketch(body, (planes["XZ_Plane"], ""))
    sk.addGeometry(Part.Circle(V(0, 20, 0), V(0, 0, 1), 15), False)
    sk.addGeometry(Part.Circle(V(0, 20, 0), V(0, 0, 1), 6), False)
    App.ActiveDocument.recompute()
    ring = [n for n, f in extrude.regions(sk) if f.Area > 200][0]
    extrude.build(
        [(sk, ring)], {"distance": 10.0, "direction": "symmetric", "operation": "new_body"}
    )
    App.ActiveDocument.recompute()
    s.update(body=body, planes=planes, sk=sk, ring=ring)
    s["ring_area"] = math.pi * (15**2 - 6**2)
    s["disc_area"] = math.pi * 36.0
    Gui.Selection.clearSelection()
    h.fit()
    return body


# -- K1 ------------------------------------------------------------------------------------------
def k1_setup():
    new_tube()
    h.check("K1 the used sketch is hidden after the extrude", not s["sk"].ViewObject.Visibility)
    s["sk"].ViewObject.Visibility = True  # the browser's eye: Show


def k1_open():
    p = panel()
    h.check("K1 starting Extrude leaves the shown sketch shown", s["sk"].ViewObject.Visibility)
    h.check("K1 nothing is picked yet (two areas)", not p.profiles, p.profiles)
    h.click(V(10, -5, 20))  # on the tube's front face; the ring area is 5 mm behind it


def k1_area():
    p = panel()
    h.check("K1 the click picked the area behind the face, not the face",
            len(p.profiles) == 1 and p.profiles[0][0] is s["sk"], p.profiles)
    if p.profiles:
        h.check("K1 the ring area", near(area_of(p), s["ring_area"]), area_of(p))
    h.click(V(10, -5, 20))  # again: the picked area leaves the click to the face in front


def k1_face():
    p = panel()
    h.check("K1 the area stays picked", len(p.profiles) == 1 and p.profiles[0][0] is s["sk"],
            p.profiles)
    h.check("K1 the click on the face in front ends the extrusion there",
            near(abs(p.distance.value()), 5.0), (p.distance.value(), p.info.text()))


# -- K2 ------------------------------------------------------------------------------------------
def k2_at_once():
    h.click_empty()
    h.press("e")
    h.wait_for(lambda: panel() is not None, "the Extrude dialog to open")
    h.click(V(10, -5, 20))  # at once, without waiting for anything else


def k2_taken():
    p = panel()
    h.check("K2 the first click right after E is taken", len(p.profiles) == 1, p.profiles)


# -- K3 ------------------------------------------------------------------------------------------
def k3_hide():
    s["body"].ViewObject.Visibility = False  # the body's eye
    h.check("K3 the sketch of the hidden body is still shown", s["sk"].ViewObject.Visibility)


def k3_extrude():
    h.click(V(10, 0, 20))  # the ring area itself (nothing is in front: the tube is hidden)


def k3_extrude_picked():
    p = panel()
    h.check("K3 Extrude: the area of the hidden body's sketch is picked",
            len(p.profiles) == 1 and near(area_of(p), s["ring_area"]), p.profiles)


def k3_revolve():
    h.click(V(10, 0, 20))


def k3_revolve_picked():
    p = rpanel()
    h.check("K3 Revolve: the area of the hidden body's sketch is picked",
            len(p.profiles) == 1 and near(area_of(p), s["ring_area"]), p.profiles)
    h.check("K3 Revolve moves on to the Axis box (Fusion)", p.active == "axis", p.active)


def k3_show():
    s["body"].ViewObject.Visibility = True
    s["sk"].ViewObject.Visibility = False


# -- K4 ------------------------------------------------------------------------------------------
def k4_setup():
    from fission180 import commands, sketch_ui

    Gui.activateWorkbench("Fission180Workbench")
    doc = App.newDocument("PickNozzle")
    body = commands.ensure_body()
    planes = sketch_ui.origin_planes(body)
    sk = sketch_ui.create_sketch(body, (planes["XZ_Plane"], ""))
    # a rectangle next to the Z axis and a bore 0.25 wide along the axis
    for pts in (
        [V(0.25, 0, 0), V(6, 0, 0), V(6, 20, 0), V(0.25, 20, 0)],
        [V(0, 0, 0), V(0.25, 0, 0), V(0.25, 20, 0), V(0, 20, 0)],
    ):
        for i in range(4):
            a, b = pts[i], pts[(i + 1) % 4]
            if (a - b).Length > 1e-9:
                sk.addGeometry(Part.LineSegment(a, b), False)
    doc.recompute()
    s.update(body=body, sk=sk)
    Gui.Selection.clearSelection()
    h.fit()


def k4_first():
    p = rpanel()
    h.check("K4 two areas: nothing picked by itself", not p.profiles, p.profiles)
    h.check("K4 the sketch stays shown while Revolve waits for its picks",
            s["sk"].ViewObject.Visibility)
    h.click(V(3, 0, 10))  # the wide area


def k4_narrow():
    p = rpanel()
    h.check("K4 the wide area is picked", len(p.profiles) == 1 and near(area_of(p), 5.75 * 20),
            p.profiles)
    h.check("K4 the Axis box waits (Fusion moves on)", p.active == "axis", p.active)
    width = (h.screen_point(V(0.25, 0, 10)) - h.screen_point(V(0, 0, 10))).manhattanLength()
    h.check("K4 the bore is only a few pixels wide on the screen", width < 16, width)
    h.click(V(0.125, 0, 10))  # inside the bore, a few pixels from the Z axis at most


def k4_added():
    p = rpanel()
    h.check("K4 the narrow area along the axis is added (the click went to the axis)",
            len(p.profiles) == 2, p.profiles)
    h.check("K4 no axis yet", p.axis is None, p.axis)
    h.click(V(0, 0, 30))  # right on the Z axis, above the sketch


def k4_axis():
    p = rpanel()
    h.check("K4 a click on the axis sets the axis", p.axis is not None, p.axis)
    h.check("K4 both areas still picked", len(p.profiles) == 2, p.profiles)
    vol = sum(b.Shape.Volume for b in App.ActiveDocument.findObjects("PartDesign::Body")
              if not b.Shape.isNull())
    h.check("K4 the preview is the full cylinder r 6 x 20", near(vol, math.pi * 36 * 20, 1e-3), vol)


# -- K5 ------------------------------------------------------------------------------------------
def k5_setup():
    from fission180 import sketch_ui

    new_tube("PickBore")
    tip = s["body"].Tip
    front = None
    for i, f in enumerate(tip.Shape.Faces, 1):
        if f.Surface.TypeId == "Part::GeomPlane" and abs(f.CenterOfMass.y + 5) < 1e-6:
            front = "Face%d" % i
    sk = sketch_ui.create_sketch(s["body"], (tip, front))
    for x, z in ((-3, 20), (0, 20), (3, 20)):
        p = h.to_sketch(sk, V(x, -5, z))
        sk.addGeometry(Part.Circle(V(p[0], p[1], 0), V(0, 0, 1), 1.0), False)
    App.ActiveDocument.recompute()
    s["holes"] = sk
    Gui.Selection.clearSelection()
    h.fit()


def k5_click(x):
    def click():
        h.click(V(x, -5, 20))

    click.__name__ = "k5_click_%s" % str(x).replace("-", "m")
    return click


def k5_picked():
    p = panel()
    mine = [pr for pr in p.profiles if pr[0] is s["holes"]]
    h.check("K5 the three circles over the bore are picked, one by one", len(mine) == 3,
            p.profiles)
    h.check("K5 nothing else (no face of the bore behind them)", len(p.profiles) == 3, p.profiles)
    if len(mine) == 3:
        total = sum(area_of(p, i) for i in range(3))
        h.check("K5 three r 1 discs", near(total, 3 * math.pi, 1e-3), total)


# -- K6 ------------------------------------------------------------------------------------------
def k6_setup():
    from fission180 import commands, sketch_ui

    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("PickOffset")
    body = commands.ensure_body()
    planes = sketch_ui.origin_planes(body)
    sk = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    h.draw_rectangle(sk, 0, 0, 20, 10)
    h.draw_rectangle(sk, 30, 0, 50, 10)
    # a slot 0.4 wide, 12 long, for K7
    h.draw_rectangle(sk, 0, 20, 12, 20.4)
    App.ActiveDocument.recompute()
    s.update(body=body, sk=sk)
    Gui.Selection.clearSelection()
    h.fit(iso=False)


def k6_offset_first():
    p = panel()
    h.check("K6 three areas: nothing picked by itself", not p.profiles, p.profiles)
    h.check("K6 choose Start: Offset before any profile", ui.choose(p.start, "Offset"))


def k6_click():
    h.click(V(10, 5, 0))


def k6_picked():
    p = panel()
    h.check("K6 with Start: Offset the profile is picked", len(p.profiles) == 1, p.profiles)
    h.check("K6 the offset arrow is there", "offset" in p.draggers, list(p.draggers))
    ui.choose(p.start, "Profile Plane")


# -- K7 ------------------------------------------------------------------------------------------
def k7_beside():
    p = panel()
    spot = h.screen_point(V(6, 20.2, 0))
    width = (h.screen_point(V(6, 20.4, 0)) - h.screen_point(V(6, 20.0, 0))).manhattanLength()
    h.check("K7 the slot is thinner than 8 pixels on the screen", width < 8, width)
    s["before"] = len(p.profiles)
    pos = QtCore.QPoint(spot.x(), spot.y() - (width // 2 + 3))  # 3 pixels beside it
    h.pointer_to(h.gl_widget(), pos)
    h.view_drawn()
    QtTest.QTest.mouseClick(h.gl_widget(), QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, pos)


def k7_picked():
    p = panel()
    h.check("K7 a click 3 pixels beside the thin slot picks it", len(p.profiles) == s["before"] + 1,
            p.profiles)
    if len(p.profiles) == s["before"] + 1:
        h.check("K7 the slot (0.4 x 12)", near(area_of(p), 4.8, 1e-3), area_of(p))


# -- K8 / K9 ---------------------------------------------------------------------------------------
def k8_setup():
    from fission180 import commands, extrude, sketch_ui

    Gui.activateWorkbench("Fission180Workbench")
    doc = App.newDocument("PickSmall")
    body = commands.ensure_body()
    planes = sketch_ui.origin_planes(body)
    sk = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    h.draw_rectangle(sk, -30, -20, 30, 20)
    doc.recompute()
    extrude.build([(sk, "")], {"distance": 20.0, "operation": "new_body"})
    doc.recompute()
    top = [(i, f) for i, f in enumerate(body.Tip.Shape.Faces, 1)
           if f.Surface.TypeId == "Part::GeomPlane" and abs(f.CenterOfMass.z - 20) < 1e-6][0][0]
    sk2 = sketch_ui.create_sketch(body, (body.Tip, "Face%d" % top))
    p = h.to_sketch(sk2, V(20, 10, 20))
    sk2.addGeometry(Part.Circle(V(p[0], p[1], 0), V(0, 0, 1), 1.5), False)
    doc.recompute()
    name = [n for n, f in extrude.regions(sk2) if f.Area < 10][0]
    extrude.build([(sk2, name)], {"distance": 4.0, "operation": "join"})
    doc.recompute()
    s.update(body=body, planes=planes)
    Gui.Selection.clearSelection()
    h.fit()


def k8_edge():
    width = (h.screen_point(V(21.5, 10, 24)) - h.screen_point(V(18.5, 10, 24))).manhattanLength()
    h.check("K8 the boss's top is small on the screen", width < 40, width)
    r = 1.5 / math.sqrt(2.0)
    h.click_edge(V(20 - r, 10 + r, 24))  # the rim of the boss's top (not at its seam)


def k8_face():
    p = panel()
    h.check("K8 a click on the rim of a small flat face picks the face", len(p.profiles) == 1,
            (p.profiles, p.message.text()))
    if p.profiles:
        obj, sub = p.profiles[0]
        face = obj.Shape.getElement(sub)
        h.check("K8 the boss's top (r 1.5)", near(face.Area, math.pi * 2.25, 1e-3), face.Area)


def k9_plane():
    from fission180 import construct

    doc = App.ActiveDocument
    try:
        plane = construct.offset_plane(s["body"], (s["planes"]["XY_Plane"], ""), 30.0)
    except Exception:
        plane = None
    if plane is None:  # (the construct code's own entry point may differ: a plain datum)
        plane = s["body"].newObject("PartDesign::Plane", "OffsetPlane")
        plane.AttachmentSupport = [(s["planes"]["XY_Plane"], "")]
        plane.MapMode = "FlatFace"
        plane.AttachmentOffset = App.Placement(V(0, 0, 30), App.Rotation())
    doc.recompute()
    plane.ViewObject.Visibility = True
    s["plane"] = plane
    Gui.Selection.clearSelection()
    h.fit()


def k9_click_through():
    # the plane's square is over the block's top (10 mm above it): click its middle
    h.click(V(-10, -5, 30))


def k9_face():
    p = panel()
    under = h.state.get("last_click")
    h.check("K9 the click on the plane's square takes the face behind it",
            len(p.profiles) == 1 and not p.profiles[0][0].isDerivedFrom("PartDesign::Plane"),
            (p.profiles, p.message.text(), under))
    if p.profiles:
        obj, sub = p.profiles[0]
        h.check("K9 the block's top face", near(obj.Shape.getElement(sub).CenterOfMass.z, 20.0))


# -- K10 -----------------------------------------------------------------------------------------
def k10_setup():
    from fission180 import commands, sketch_ui

    Gui.activateWorkbench("Fission180Workbench")
    doc = App.newDocument("PickHalves")
    body = commands.ensure_body()
    planes = sketch_ui.origin_planes(body)
    sk = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    sk.addGeometry(Part.Circle(V(0, 0, 0), V(0, 0, 1), 12.5), False)
    sk.addGeometry(Part.LineSegment(V(0, -20, 0), V(0, 20, 0)), False)
    doc.recompute()
    s.update(body=body, sk=sk)
    Gui.Selection.clearSelection()
    h.fit()


def k10_first():
    p = panel()
    h.check("K10 two halves: nothing picked by itself", not p.profiles, p.profiles)
    h.click(V(-6, 0, 0))


def k10_second():
    from Fission180Tests.gui import arrow_input as arrows

    p = panel()
    h.check("K10 the first half is picked", len(p.profiles) == 1, p.profiles)
    spot = h.screen_point(V(6, 0, 0))
    boxes = [b for b in arrows.value_boxes() if b.isVisible()]
    covering = [b for b in boxes if b.geometry().contains(spot)]
    h.check("K10 no value box lies over the other half's middle", not covering,
            [(b.geometry().x(), b.geometry().y(), b.geometry().width()) for b in covering])
    h.click(V(6, 0, 0))


def k10_both():
    p = panel()
    h.check("K10 the second half is picked too", len(p.profiles) == 2, p.profiles)


# -- K11 -----------------------------------------------------------------------------------------
def k11_setup():
    from fission180 import commands, components, extrude, sketch_ui

    Gui.activateWorkbench("Fission180Workbench")
    doc = App.newDocument("PickOther")
    body = commands.ensure_body()
    planes = sketch_ui.origin_planes(body)
    sk = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    h.draw_rectangle(sk, 0, 0, 20, 10)
    doc.recompute()
    extrude.build([(sk, "")], {"distance": 5.0, "operation": "new_body"})
    doc.recompute()
    # a sketch with one area in the root's body, shown; then another component is active
    sk2 = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    sk2.addGeometry(Part.Circle(V(40, 5, 0), V(0, 0, 1), 4), False)
    doc.recompute()
    comp = components.new_component(doc)
    components.set_active(comp, doc)
    commands.ensure_body()
    s.update(sk=sk2)
    Gui.Selection.clearSelection()
    h.fit()
    h.check("K11 the sketch is not in the active component's body",
            commands.find_body() is not body)


def k11_extrude():
    p = panel()
    h.check("K11 Extrude: the one profile in view is picked by itself",
            keys(p) == [(s["sk"].Name, "InternalFace1")], p.profiles)


def k11_revolve():
    p = rpanel()
    h.check("K11 Revolve: the one profile in view is picked by itself",
            keys(p) == [(s["sk"].Name, "InternalFace1")], p.profiles)
    h.check("K11 and the Axis box waits", p.active == "axis", p.active)


steps = [
    k1_setup, press_e, k1_open, k1_area, k1_face, cancel,
    k2_at_once, k2_taken, cancel,
    k3_hide, press_e, k3_extrude, k3_extrude_picked, cancel,
    open_revolve, k3_revolve, k3_revolve_picked, cancel, k3_show,
    k4_setup, open_revolve, k4_first, k4_narrow, k4_added, k4_axis, cancel,
    k5_setup, press_e, k5_click(-3), k5_click(0), k5_click(3), k5_picked, cancel,
    k6_setup, press_e, k6_offset_first, k6_click, k6_picked, k7_beside, k7_picked, cancel,
    k8_setup, press_e, k8_edge, k8_face, cancel,
    k9_plane, press_e, k9_click_through, k9_face, cancel,
    k10_setup, press_e, k10_first, k10_second, k10_both, cancel,
    k11_setup, press_e, k11_extrude, cancel, open_revolve, k11_revolve, cancel,
]

h.run("book_extrude_picking", steps, paced_by="state")
