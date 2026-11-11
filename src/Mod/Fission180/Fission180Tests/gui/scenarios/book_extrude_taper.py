# SPDX-License-Identifier: LGPL-2.1-or-later
"""Profiles that touch are tapered as one outline (wave 7; the book's Saturn V thruster: the
rocket's projected edge splits the thruster's circle in two, "Fusion extrudes both profiles
together as one cone", Fission 180 tapered each half by itself and held the taper at -6.8
degrees where the cone needs -11).

T1  A circle r 12.5 cut in two by a line. E, both halves clicked, 52, Taper -11: one cone,
    12.5 at the bottom and 2.39 at the top, 10448 mm3; the taper is not held back.
T2  Two circles that do not touch (r 5, 30 apart), Taper -10 over 10: two cones, each its own.
T3  On a block's top face: a circle r 5 cut in two, both halves, 10, Taper -10, Join: the
    block with one cone on it. Edit from the timeline: the taper is back; changed to -5.
    Undo / Redo. Save / reopen.
"""
import math
import os
import tempfile

import FreeCAD as App
import FreeCADGui as Gui
import Part

from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h

V = App.Vector
PI = math.pi
s = {}


def panel():
    from fission180 import extrude_ui

    p = extrude_ui.ExtrudePanel.last
    return p if p is not None and not p._closed else None


def near(a, b, tol=2e-3):
    return abs(a - b) <= tol * max(1.0, abs(b))


def cone(r0, height, taper_deg):
    r1 = r0 + height * math.tan(math.radians(taper_deg))
    return PI * height / 3.0 * (r0 * r0 + r0 * r1 + r1 * r1), r1


def total():
    return sum(
        b.Shape.Volume
        for b in App.ActiveDocument.findObjects("PartDesign::Body")
        if not b.Shape.isNull()
    )


def press_e():
    h.click_empty()
    h.press("e")


press_e.done = lambda: panel() is not None
press_e.done_what = "the Extrude dialog is open"


def closed():
    return panel() is None


def new_sketch(name, draw):
    from fission180 import commands, sketch_ui

    Gui.activateWorkbench("Fission180Workbench")
    doc = App.newDocument(name)
    body = commands.ensure_body()
    planes = sketch_ui.origin_planes(body)
    sk = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    draw(sk)
    doc.recompute()
    s.update(body=body, planes=planes, sk=sk)
    Gui.Selection.clearSelection()
    h.fit()


# -- T1 ------------------------------------------------------------------------------------------
def t1_setup():
    def draw(sk):
        sk.addGeometry(Part.Circle(V(0, 0, 0), V(0, 0, 1), 12.5), False)
        sk.addGeometry(Part.LineSegment(V(0, -20, 0), V(0, 20, 0)), False)

    new_sketch("TaperHalves", draw)


def t1_left():
    h.click(V(-6, 0, 0))


def t1_right():
    h.click(V(6, 0, 0))


def t1_values():
    p = panel()
    h.check("T1 both halves are picked", len(p.profiles) == 2, p.profiles)
    ui.type_into(p.distance.widget, "52")
    ui.type_into(p.taper.widget, "-11")
    h.caught_up(p)


def t1_cone():
    p = panel()
    h.caught_up(p)
    want, top = cone(12.5, 52.0, -11.0)
    h.check("T1 the taper is taken as typed (it was held at -6.8)", near(p.taper.value(), -11.0),
            (p.taper.value(), p.message.text(), p.limit_label.text()))
    h.check("T1 one cone, r 12.5 to r %.2f" % top, near(total(), want), (total(), want))
    solids = sum(len(b.Shape.Solids) for b in App.ActiveDocument.findObjects("PartDesign::Body")
                 if not b.Shape.isNull())
    h.check("T1 one solid", solids == 1, solids)
    h.check("T1 no problem said", "⚠" not in p.message.text(), p.message.text())
    h.task_button("OK")


t1_cone.done = closed
t1_cone.done_what = "OK finished the extrude"


def t1_done():
    want, _top = cone(12.5, 52.0, -11.0)
    h.check("T1 kept", near(total(), want), total())
    top = max(b.Shape.BoundBox.ZMax for b in App.ActiveDocument.findObjects("PartDesign::Body")
              if not b.Shape.isNull())
    h.check("T1 52 high", near(top, 52.0), top)


# -- T2 ------------------------------------------------------------------------------------------
def t2_setup():
    def draw(sk):
        sk.addGeometry(Part.Circle(V(0, 0, 0), V(0, 0, 1), 5), False)
        sk.addGeometry(Part.Circle(V(30, 0, 0), V(0, 0, 1), 5), False)

    new_sketch("TaperApart", draw)


def t2_first():
    h.click(V(0, 0, 0))


def t2_second():
    h.click(V(30, 0, 0))


def t2_values():
    p = panel()
    h.check("T2 both circles are picked", len(p.profiles) == 2, p.profiles)
    ui.type_into(p.distance.widget, "10")
    ui.type_into(p.taper.widget, "-10")
    h.caught_up(p)


def t2_two_cones():
    p = panel()
    h.caught_up(p)
    want, _top = cone(5.0, 10.0, -10.0)
    h.check("T2 two cones, each its own", near(total(), 2 * want), (total(), 2 * want))
    h.task_button("OK")


t2_two_cones.done = closed
t2_two_cones.done_what = "OK finished the extrude"


# -- T3 ------------------------------------------------------------------------------------------
def t3_setup():
    from fission180 import commands, extrude, sketch_ui

    Gui.activateWorkbench("Fission180Workbench")
    doc = App.newDocument("TaperJoin")
    body = commands.ensure_body()
    planes = sketch_ui.origin_planes(body)
    sk = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    h.draw_rectangle(sk, -30, -20, 30, 20)
    doc.recompute()
    extrude.build([(sk, "")], {"distance": 20.0, "operation": "new_body"})
    doc.recompute()
    top = [i for i, f in enumerate(body.Tip.Shape.Faces, 1)
           if f.Surface.TypeId == "Part::GeomPlane" and abs(f.CenterOfMass.z - 20) < 1e-6][0]
    sk2 = sketch_ui.create_sketch(body, (body.Tip, "Face%d" % top))
    c = h.to_sketch(sk2, V(0, 0, 20))
    a = h.to_sketch(sk2, V(0, -8, 20))
    b = h.to_sketch(sk2, V(0, 8, 20))
    sk2.addGeometry(Part.Circle(V(c[0], c[1], 0), V(0, 0, 1), 5), False)
    sk2.addGeometry(Part.LineSegment(V(a[0], a[1], 0), V(b[0], b[1], 0)), False)
    doc.recompute()
    s.update(body=body, sk=sk2)
    Gui.Selection.clearSelection()
    h.fit()


def t3_left():
    h.click(V(-2.5, 0, 20))


def t3_right():
    h.click(V(2.5, 0, 20))


def t3_values():
    p = panel()
    mine = [pr for pr in p.profiles if pr[0] is s["sk"]]
    h.check("T3 both halves are picked", len(mine) == 2 and len(p.profiles) == 2, p.profiles)
    ui.type_into(p.distance.widget, "10")
    ui.type_into(p.taper.widget, "-10")
    h.caught_up(p)


def t3_joined():
    p = panel()
    h.caught_up(p)
    want, _top = cone(5.0, 10.0, -10.0)
    h.check("T3 on the face going away: Join", p.operation.currentText() == "Join",
            p.operation.currentText())
    h.check("T3 the block with one cone on it", near(total(), 48000.0 + want, 1e-4),
            (total(), 48000.0 + want))
    h.task_button("OK")


t3_joined.done = closed
t3_joined.done_what = "OK finished the extrude"


def t3_edit():
    want, _top = cone(5.0, 10.0, -10.0)
    h.check("T3 kept", near(total(), 48000.0 + want, 1e-4), total())
    h.check("T3 one body, one solid", len(s["body"].Shape.Solids) == 1, len(s["body"].Shape.Solids))
    ui.double_click_timeline(ui.timeline_titles()[-1])


t3_edit.done = lambda: panel() is not None and panel().editing
t3_edit.done_what = "the extrude is open for editing"


def t3_editing():
    p = panel()
    h.check("T3 the taper is back", near(p.taper.value(), -10.0), p.taper.value())
    h.check("T3 both halves are back", len(p.profiles) == 2, p.profiles)
    ui.type_into(p.taper.widget, "-5")
    h.caught_up(p)


def t3_changed():
    p = panel()
    h.caught_up(p)
    want, _top = cone(5.0, 10.0, -5.0)
    h.check("T3 -5: a steeper cone", near(total(), 48000.0 + want, 1e-4), (total(), 48000.0 + want))
    h.task_button("OK")


t3_changed.done = closed
t3_changed.done_what = "OK finished the edit"


def t3_undo():
    Gui.runCommand("Std_Undo")


def t3_redo():
    want, _top = cone(5.0, 10.0, -10.0)
    h.check("T3 Undo: -10 again", near(total(), 48000.0 + want, 1e-4), total())
    Gui.runCommand("Std_Redo")


def t3_save():
    want, _top = cone(5.0, 10.0, -5.0)
    h.check("T3 Redo: -5", near(total(), 48000.0 + want, 1e-4), total())
    doc = App.ActiveDocument
    path = os.path.join(tempfile.mkdtemp(prefix="fission180_taper_"), "TaperJoin.FCStd")
    doc.saveAs(path)
    App.closeDocument(doc.Name)
    App.openDocument(path)
    App.ActiveDocument.recompute()


def t3_reopened():
    want, _top = cone(5.0, 10.0, -5.0)
    h.check("T3 reopened and rebuilt: the same cone", near(total(), 48000.0 + want, 1e-4), total())
    bad = [o.Label for o in App.ActiveDocument.Objects if "Invalid" in o.State or "Error" in o.State]
    h.check("T3 nothing in error", not bad, bad)


steps = [
    t1_setup, press_e, t1_left, t1_right, t1_values, t1_cone, t1_done,
    t2_setup, press_e, t2_first, t2_second, t2_values, t2_two_cones,
    t3_setup, press_e, t3_left, t3_right, t3_values, t3_joined, t3_edit, t3_editing,
    t3_changed, t3_undo, t3_redo, t3_save, t3_reopened,
]

h.run("book_extrude_taper", steps, paced_by="state")
