# SPDX-License-Identifier: LGPL-2.1-or-later
"""Which way a distance goes (wave 7; the book report: "-6 went AWAY from the front view
(book: towards you)", "the sign of a negative distance isn't consistent").

The rule (parity/extrude-presspull.md, "Direction and sign"): a positive distance goes along
the profile's normal, a negative one against it, always. The normal is: up from the Top
plane (+Z), away from the front viewer from the Front plane (+Y: Fusion's Front plane looks
the other way than FreeCAD's), to the right from the Right plane (+X), and out of the solid
from a face (a sketch on it, or the face picked itself).

N1  Top plane: +5 is z 0..5, -5 is z -5..0.
N2  Front plane, a new sketch: +6 is y 0..6 (away from the front), -6 is y -6..0 (towards
    you, the book's Strandbeest pins). OK at -6; edit from the timeline: -6 shows again.
N3  Right plane: +5 is x 0..5, -5 is x -5..0.
N4  A sketch on a block's top face: +5 stands on the face (z 20..25, Join), -5 goes into the
    block (Cut).
N5  A sketch on the block's bottom face: +5 goes down, away from the block (z -5..0), -5
    into it (Cut).
N6  The block's side face (x = 30) picked itself: +5 goes out (x up to 35), -5 into it (Cut).
N7  A sketch on the Front plane that an extrude already used before wave 7 (no mark) keeps
    the old way: +6 is y -6..0. Save, reopen: the new sketch still goes Fusion's way.
"""
import os
import tempfile

import FreeCAD as App
import FreeCADGui as Gui
import Part

from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h

V = App.Vector
s = {}


def panel():
    from fission180 import extrude_ui

    p = extrude_ui.ExtrudePanel.last
    return p if p is not None and not p._closed else None


def near(a, b, tol=1e-6):
    return abs(a - b) <= tol * max(1.0, abs(b))


def press_e():
    h.click_empty()
    h.press("e")


press_e.done = lambda: panel() is not None
press_e.done_what = "the Extrude dialog is open"


def closed():
    return panel() is None


def cancel():
    h.task_button("Cancel")


cancel.done = closed
cancel.done_what = "the dialog is closed"


def typed(text):
    ui.type_into(panel().distance.widget, text)
    h.caught_up(panel())


def box_of(obj):
    b = obj.Shape.BoundBox
    return [round(v, 4) for v in (b.XMin, b.YMin, b.ZMin, b.XMax, b.YMax, b.ZMax)]


def preview_box():
    """The bounding box of the body the preview is in."""
    target = panel().target
    body = target.getParentGeoFeatureGroup() if target is not None else None
    return box_of(body) if body is not None and not body.Shape.isNull() else None


def op():
    return panel().operation.currentText()


def fresh(name, plane, draw=None):
    from fission180 import commands, sketch_ui

    Gui.activateWorkbench("Fission180Workbench")
    doc = App.newDocument(name)
    body = commands.ensure_body()
    planes = sketch_ui.origin_planes(body)
    sk = sketch_ui.create_sketch(body, (planes[plane], ""))
    if draw is None:
        sk.addGeometry(Part.Circle(V(10, 10, 0), V(0, 0, 1), 4), False)
    else:
        draw(sk)
    doc.recompute()
    s.update(body=body, planes=planes, sk=sk)
    Gui.Selection.clearSelection()
    h.fit()
    return sk


def along(axis, lo, hi, what):
    """Check that the preview spans lo..hi on `axis` (0 x, 1 y, 2 z)."""
    box = preview_box()
    ok = box is not None and near(box[axis], lo) and near(box[axis + 3], hi)
    h.check(what, ok, box)


# -- N1 ------------------------------------------------------------------------------------------
def n1_setup():
    fresh("DirTop", "XY_Plane")


def n1_both():
    h.check("N1 the one area is picked", len(panel().profiles) == 1, panel().profiles)
    typed("5")
    along(2, 0.0, 5.0, "N1 Top plane, +5: up (z 0..5)")
    typed("-5")
    along(2, -5.0, 0.0, "N1 Top plane, -5: down (z -5..0)")


# -- N2 ------------------------------------------------------------------------------------------
def n2_setup():
    fresh("DirFront", "XZ_Plane")


def n2_both():
    from fission180 import extrude

    h.check("N2 the one area is picked", len(panel().profiles) == 1, panel().profiles)
    h.check("N2 the new sketch goes Fusion's way on the Front plane",
            extrude.fusion_side(s["sk"]) == -1.0, extrude.fusion_side(s["sk"]))
    typed("6")
    along(1, 0.0, 6.0, "N2 Front plane, +6: away from the front (y 0..6)")
    arrow = panel().draggers.get("distance")
    if arrow is not None:
        tip = arrow.anchor()
        h.check("N2 the arrow stands where the extrusion ends (y 6)", near(tip.y, 6.0, 1e-3), tip)
    typed("-6")
    along(1, -6.0, 0.0, "N2 Front plane, -6: towards you (y -6..0)")
    h.task_button("OK")


n2_both.done = closed
n2_both.done_what = "OK finished the extrude"


def n2_edit():
    h.check("N2 made towards the front", near(box_of(s["body"])[1], -6.0), box_of(s["body"]))
    ui.double_click_timeline(ui.timeline_titles()[-1])


n2_edit.done = lambda: panel() is not None and panel().editing
n2_edit.done_what = "the extrude is open for editing"


def n2_editing():
    p = panel()
    h.check("N2 the edit shows -6 again", near(p.distance.value(), -6.0), p.distance.value())
    typed("-8")
    along(1, -8.0, 0.0, "N2 edited to -8: y -8..0")
    h.task_button("OK")


n2_editing.done = closed
n2_editing.done_what = "OK finished the edit"


def n2_undo():
    Gui.runCommand("Std_Undo")


def n2_redo():
    h.check("N2 Undo: -6 again", near(box_of(s["body"])[1], -6.0), box_of(s["body"]))
    Gui.runCommand("Std_Redo")


def n2_redone():
    h.check("N2 Redo: -8", near(box_of(s["body"])[1], -8.0), box_of(s["body"]))


# -- N3 ------------------------------------------------------------------------------------------
def n3_setup():
    fresh("DirRight", "YZ_Plane")


def n3_both():
    h.check("N3 the one area is picked", len(panel().profiles) == 1, panel().profiles)
    typed("5")
    along(0, 0.0, 5.0, "N3 Right plane, +5: to the right (x 0..5)")
    typed("-5")
    along(0, -5.0, 0.0, "N3 Right plane, -5: x -5..0")


# -- N4 / N5 / N6: the block -----------------------------------------------------------------------
def block(name):
    from fission180 import commands, extrude, sketch_ui

    Gui.activateWorkbench("Fission180Workbench")
    doc = App.newDocument(name)
    body = commands.ensure_body()
    planes = sketch_ui.origin_planes(body)
    sk = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    h.draw_rectangle(sk, -30, -20, 30, 20)
    doc.recompute()
    extrude.build([(sk, "")], {"distance": 20.0, "operation": "new_body"})
    doc.recompute()
    s.update(body=body, planes=planes)
    return body


def face_at(z):
    tip = s["body"].Tip
    for i, f in enumerate(tip.Shape.Faces, 1):
        if f.Surface.TypeId == "Part::GeomPlane" and abs(f.CenterOfMass.z - z) < 1e-6:
            if abs(f.normalAt(0, 0).z) > 0.9:
                return (tip, "Face%d" % i)
    raise RuntimeError("no face at z %s" % z)


def square_at(z):
    def draw(sk):
        a = h.to_sketch(sk, V(-5, -5, z))
        b = h.to_sketch(sk, V(5, 5, z))
        h.draw_rectangle(sk, min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))

    return draw


def n4_setup():
    from fission180 import sketch_ui

    block("DirFace")
    sk = sketch_ui.create_sketch(s["body"], face_at(20.0))
    square_at(20.0)(sk)
    App.ActiveDocument.recompute()
    s["sk"] = sk
    Gui.Selection.clearSelection()
    h.fit()


def n4_both():
    if not panel().profiles:
        h.click(V(0, 0, 20))
        h.settle()
    typed("5")
    h.check("N4 a sketch on the top face, +5: Join", op() == "Join", op())
    along(2, 0.0, 25.0, "N4 +5 stands on the face (z up to 25)")
    typed("-5")
    h.check("N4 -5: Cut by itself", op() == "Cut", op())
    along(2, 0.0, 20.0, "N4 -5 goes into the block (it stays 20 high)")
    h.check("N4 100 x 5 taken out", near(s["body"].Shape.Volume, 48000.0 - 500.0),
            s["body"].Shape.Volume)


def n5_setup():
    from fission180 import sketch_ui

    block("DirBottom")
    sk = sketch_ui.create_sketch(s["body"], face_at(0.0))
    square_at(0.0)(sk)
    App.ActiveDocument.recompute()
    s["sk"] = sk
    Gui.Selection.clearSelection()
    h.fit()
    normal = sk.getGlobalPlacement().Rotation.multVec(V(0, 0, 1))
    h.check("N5 a sketch on the bottom face looks down (out of the solid)", near(normal.z, -1.0),
            normal)


def n5_both():
    if not panel().profiles:
        from fission180 import extrude

        # the bottom cannot be seen from here: its one area, picked like the browser does
        Gui.Selection.addSelection(
            App.ActiveDocument.Name, s["body"].Name,
            s["sk"].Name + "." + extrude.profile_regions(s["sk"])[0][0]
        )
        h.settle()
    h.check("N5 the area is picked", len(panel().profiles) == 1, panel().profiles)
    typed("5")
    h.check("N5 +5 on the bottom face: Join", op() == "Join", op())
    along(2, -5.0, 20.0, "N5 +5 goes down, away from the block (z from -5)")
    typed("-5")
    h.check("N5 -5: Cut by itself", op() == "Cut", op())
    along(2, 0.0, 20.0, "N5 -5 goes up into the block")


def n6_setup():
    block("DirSide")
    Gui.Selection.clearSelection()
    h.fit()


def n6_face():
    h.click(V(30, 2, 10))  # the side face x = 30


def n6_both():
    p = panel()
    h.check("N6 the side face is the profile", len(p.profiles) == 1 and
            p.profiles[0][1].startswith("Face"), p.profiles)
    typed("5")
    h.check("N6 the face picked itself, +5: Join", op() == "Join", op())
    along(0, -30.0, 35.0, "N6 +5 goes out of the face (x up to 35)")
    typed("-5")
    h.check("N6 -5: Cut by itself", op() == "Cut", op())
    along(0, -30.0, 25.0, "N6 -5 goes into the block (x up to 25)")


# -- N7 ------------------------------------------------------------------------------------------
def n7_setup():
    from fission180 import extrude

    def draw(sk):
        sk.addGeometry(Part.Circle(V(10, 10, 0), V(0, 0, 1), 4), False)
        sk.addGeometry(Part.Circle(V(30, 10, 0), V(0, 0, 1), 4), False)

    sk = fresh("DirOld", "XZ_Plane", draw)
    first = extrude.profile_regions(sk)[0][0]
    # as a design made before wave 7: an extrude of this sketch, counted FreeCAD's way
    extrude.build([(sk, first)], {"distance": 3.0, "operation": "new_body"})
    App.ActiveDocument.recompute()
    sk.ViewObject.Visibility = True
    s["old_box"] = box_of(s["body"])
    Gui.Selection.clearSelection()
    h.fit()


def n7_old_way():
    from fission180 import extrude

    h.check("N7 the old extrude went FreeCAD's way (y -3..0)",
            near(s["old_box"][1], -3.0) and near(s["old_box"][4], 0.0), s["old_box"])
    p = panel()
    if not p.profiles:
        h.click(V(30, 0, 10))
        h.settle()
    h.check("N7 the second area is picked", len(panel().profiles) == 1, panel().profiles)
    h.check("N7 the sketch keeps the old way", extrude.fusion_side(s["sk"]) == 1.0)
    ui.choose(panel().operation, "New Body")


def n7_typed():
    typed("6")
    box = preview_box()
    h.check("N7 +6 goes the way the sketch's first extrude went (y -6..0)",
            box is not None and near(box[1], -6.0) and near(box[4], 0.0), box)
    h.task_button("Cancel")


n7_typed.done = closed
n7_typed.done_what = "the dialog is closed"


def n7_save():
    fresh("DirKeep", "XZ_Plane")


def n7_make():
    typed("6")
    along(1, 0.0, 6.0, "N7 a new sketch: +6 away from the front")
    h.task_button("OK")


n7_make.done = closed
n7_make.done_what = "OK finished the extrude"


def n7_reopen():
    doc = App.ActiveDocument
    path = os.path.join(tempfile.mkdtemp(prefix="fission180_dir_"), "DirKeep.FCStd")
    doc.saveAs(path)
    App.closeDocument(doc.Name)
    App.openDocument(path)
    App.ActiveDocument.recompute()


def n7_reopened():
    from fission180 import extrude

    doc = App.ActiveDocument
    body = doc.findObjects("PartDesign::Body")[0]
    h.check("N7 reopened and rebuilt: still y 0..6",
            near(box_of(body)[1], 0.0) and near(box_of(body)[4], 6.0), box_of(body))
    sketch = [o for o in doc.Objects if o.isDerivedFrom("Sketcher::SketchObject")][0]
    h.check("N7 the sketch kept its mark", extrude.fusion_side(sketch) == -1.0)
    pads = [o for o in doc.Objects if o.TypeId == "PartDesign::Pad"]
    h.check("N7 the edit would show +6",
            pads and near(extrude.read(pads[-1])[1]["distance"], 6.0),
            pads and extrude.read(pads[-1])[1]["distance"])


steps = [
    n1_setup, press_e, n1_both, cancel,
    n2_setup, press_e, n2_both, n2_edit, n2_editing, n2_undo, n2_redo, n2_redone,
    n3_setup, press_e, n3_both, cancel,
    n4_setup, press_e, n4_both, cancel,
    n5_setup, press_e, n5_both, cancel,
    n6_setup, press_e, n6_face, n6_both, cancel,
    n7_setup, press_e, n7_old_way, n7_typed,
    n7_save, press_e, n7_make, n7_reopen, n7_reopened,
]

h.run("book_extrude_direction", steps, paced_by="state")
