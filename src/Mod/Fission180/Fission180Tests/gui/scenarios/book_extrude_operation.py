# SPDX-License-Identifier: LGPL-2.1-or-later
"""The Extrude Operation rule as a table, each row a path with real input (wave 7, the book
parity report's pattern 3: "The Extrude Operation keeps changing").

The rule (parity/extrude-presspull.md, "The Operation rule"): until the person picks an
operation the dialog shows Cut when the extrusion overlaps a body of the active component,
Join when it only touches one, New Body otherwise; once the person picked one it never
changes by itself; Enter in the distance box commits what the dialog shows; an OK that cannot
finish says why, and so does an edit another command had to drop.

The block is 60 x 40 x 20 (x -30..30, y -20..20, z 0..20) = 48000 mm3.

R1  first solid of a design: New Body.
R2  a 10 x 10 square on the block's top face: +5 is a Join (48500), -5 a Cut (47500), back to
    +5 a Join again: the automatic choice follows the geometry.
R3  the book's donut bite: a circle r 6 at (28, 10) on the XZ plane (inside the block, partly
    past its side): Cut by itself; Direction Symmetric keeps Cut (it turned it into Join);
    5 typed and Enter in the distance box commits the Cut the dialog shows.
R4  the surfboard hole: a circle on the XY plane under a block made downward (z -20..0):
    Extent All goes up, away from the block ("No faces found in this direction"); Flip turns
    it into the block and the operation is Cut by itself.
R5  the pizza cutter: a circle on the mid plane, Symmetric + All: Cut by itself, OK cuts
    through (it was a Join that added nothing and OK closed on it).
R6  the hot end flat: a revolved part (a base r 15, a post r 5 on it), a rectangle sketched
    on the post's top face beside the post, To Object the underside: the extrusion starts in
    the air and reaches into the base: Cut by itself (it was a Join).
R7  the person picks Join for R2's square going down: it stays Join through Symmetric, a
    typed distance, One Side again and -5 (where the automatic choice is Cut).
R8  OK that cannot finish says why next to the mouse; starting another command with an edit
    that cannot be built says that the change was not kept (it was dropped without a word).
R9  a new, empty component is active: a circle over the root's block is a New Body both
    ways (bug 10: it was a Cut of the other component's block, and -5 a Join into it); the
    component's own second extrude into its own body is a Cut.
R10 edit from the timeline: the saved operation shows and stays while the distance changes
    sign; undo / redo; save / reopen reads the operation back.
"""
import math
import os
import tempfile

import FreeCAD as App
import FreeCADGui as Gui
import Part
from PySide import QtCore
from PySide6 import QtTest

from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h

V = App.Vector
PI = math.pi
BLOCK = 48000.0
s = {}


def panel():
    from fission180 import extrude_ui

    p = extrude_ui.ExtrudePanel.last
    return p if p is not None and not p._closed else None


def op():
    p = panel()
    return p.operation.currentText() if p is not None else None


def near(a, b, tol=1e-4):
    return abs(a - b) <= tol * max(1.0, abs(b))


def bodies():
    return sorted(App.ActiveDocument.findObjects("PartDesign::Body"), key=lambda o: o.ID)


def vol(body=None):
    if body is None:
        body = s["body"]
    try:
        return 0.0 if body.Shape.isNull() else body.Shape.Volume
    except Exception:
        return 0.0


def told():
    from fission180 import commands

    return commands._TOLD.get("msg") or ""


def new_block(name, down=False, height=20.0):
    """A design with the block, made through the same code the dialog uses."""
    from fission180 import commands, extrude, sketch_ui

    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument(name)
    body = commands.ensure_body()
    planes = sketch_ui.origin_planes(body)
    sk = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    h.draw_rectangle(sk, -30, -20, 30, 20)
    App.ActiveDocument.recompute()
    extrude.build([(sk, "")], {"distance": -height if down else height, "operation": "new_body"})
    App.ActiveDocument.recompute()
    s["body"], s["planes"] = body, planes
    return body, planes


def sketch_on(support, draw):
    from fission180 import sketch_ui

    sk = sketch_ui.create_sketch(s["body"], support)
    draw(sk)
    App.ActiveDocument.recompute()
    Gui.Selection.clearSelection()
    h.fit()
    return sk


def circle(x, y, r):
    return lambda sk: sk.addGeometry(Part.Circle(V(x, y, 0), V(0, 0, 1), r), False)


def press_e():
    h.click_empty()
    h.press("e")


press_e.done = lambda: panel() is not None
press_e.done_what = "the Extrude dialog is open"


def type_distance(text):
    ui.type_into(panel().distance.widget, text)
    h.caught_up(panel())


def enter_distance(text):
    """Type in the Distance box and press Enter there (Fusion: Enter is OK)."""
    w = panel().distance.widget
    QtTest.QTest.mouseClick(w, QtCore.Qt.LeftButton)
    QtTest.QTest.keyClick(w, QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
    QtTest.QTest.keyClicks(w, text)
    QtTest.QTest.keyClick(w, QtCore.Qt.Key_Return)


def named(name, fn, done=None, what=""):
    fn.__name__ = name
    if done is not None:
        fn.done = done
        fn.done_what = what
    return fn


def closed():
    return panel() is None


# -- R1 ------------------------------------------------------------------------------------------
def r1_setup():
    from fission180 import commands, sketch_ui

    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("OpFirst")
    body = commands.ensure_body()
    planes = sketch_ui.origin_planes(body)
    sk = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    h.draw_rectangle(sk, 0, 0, 20, 10)
    App.ActiveDocument.recompute()
    s["body"] = body
    Gui.Selection.clearSelection()
    h.fit()


def r1_first():
    h.check("R1 the sketch's one area is picked by itself", len(panel().profiles) == 1)
    type_distance("5")
    h.check("R1 the first solid is a New Body", op() == "New Body", op())
    h.task_button("OK")


def r1_done():
    h.check("R1 made", near(vol(), 1000.0), vol())


# -- R2 / R7 ---------------------------------------------------------------------------------------
def top_face():
    tip = s["body"].Tip
    for i, f in enumerate(tip.Shape.Faces, 1):
        if f.Surface.TypeId == "Part::GeomPlane" and abs(f.CenterOfMass.z - 20) < 1e-6:
            return (tip, "Face%d" % i)
    raise RuntimeError("no top face")


def square_on_top(sk):
    a = h.to_sketch(sk, V(10, -5, 20))
    b = h.to_sketch(sk, V(20, 5, 20))
    h.draw_rectangle(sk, min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1]))


def r2_setup():
    new_block("OpFace")
    s["sk"] = sketch_on(top_face(), square_on_top)


def r2_out():
    p = panel()
    if not p.profiles:
        h.click(V(15, 0, 20))
        h.settle()
    h.check("R2 the square is the profile", len(panel().profiles) == 1, panel().profiles)
    type_distance("5")
    h.check("R2 +5 away from the face: Join", op() == "Join", op())
    h.check("R2 the preview adds 500", near(vol(), BLOCK + 500.0), vol())


def r2_in():
    type_distance("-5")
    h.check("R2 -5 into the block: Cut by itself", op() == "Cut", op())
    h.check("R2 the preview takes 500 away", near(vol(), BLOCK - 500.0), vol())
    box = s["body"].Shape.BoundBox
    h.check("R2 a negative distance goes against the arrow, into the face", near(box.ZMax, 20.0))


def r2_out_again():
    type_distance("5")
    h.check("R2 +5 again: Join again", op() == "Join", op())
    h.check("R2 not locked by the automatic choice", not panel().user_picked_operation)
    h.task_button("Cancel")


def r7_setup():
    h.check("R2 Cancel left the block", closed() and near(vol(), BLOCK), vol())


def r7_pick_join():
    if not panel().profiles:
        h.click(V(15, 0, 20))
        h.settle()
    type_distance("-5")
    h.check("R7 -5: Cut by itself", op() == "Cut", op())
    h.check("R7 the person picks Join", ui.choose(panel().operation, "Join"))


def r7_symmetric():
    h.caught_up(panel())
    h.check("R7 Join stays", op() == "Join" and panel().user_picked_operation, op())
    ui.choose(panel().direction, "Symmetric")


def r7_typed():
    h.caught_up(panel())
    h.check("R7 Symmetric: still Join", op() == "Join", op())
    type_distance("4")
    h.check("R7 a typed distance: still Join", op() == "Join", op())
    ui.choose(panel().direction, "One Side")


def r7_one_side():
    h.caught_up(panel())
    type_distance("-5")
    h.check("R7 One Side -5 (where the automatic choice is Cut): still Join", op() == "Join", op())
    h.check("R7 a Join into the block changes nothing", near(vol(), BLOCK), vol())
    h.task_button("Cancel")


# -- R3 ------------------------------------------------------------------------------------------
def r3_setup():
    h.check("R7 cancelled", closed())
    new_block("OpBite")
    s["sk"] = sketch_on((s["planes"]["XZ_Plane"], ""), circle(28, 10, 6))


def r3_cut():
    if not panel().profiles:
        h.click(V(26, 0, 10))
        h.settle()
    h.check("R3 a profile inside the block: Cut by itself, before any distance", op() == "Cut", op())
    ui.choose(panel().direction, "Symmetric")


def r3_symmetric():
    h.caught_up(panel())
    h.check("R3 Symmetric keeps Cut (it turned it into Join)", op() == "Cut", op())
    h.check("R3 nothing was picked by the person", not panel().user_picked_operation)
    enter_distance("5")


r3_symmetric.done = closed
r3_symmetric.done_what = "Enter in the distance box finished the extrude"


def r3_done():
    # r 6 over 10 mm, less what hangs past the block's side at x 30
    r, d = 6.0, 2.0
    segment = r * r * math.acos(d / r) - d * math.sqrt(r * r - d * d)
    expect = BLOCK - (PI * r * r - segment) * 10.0
    h.check("R3 Enter committed the Cut the dialog showed", near(vol(), expect), (vol(), expect))
    h.check("R3 still one body", len(bodies()) == 1, [b.Label for b in bodies()])


# -- R4 ------------------------------------------------------------------------------------------
def r4_setup():
    new_block("OpFlip", down=True)
    s["sk"] = sketch_on((s["planes"]["XY_Plane"], ""), circle(0, 0, 5))


def r4_all():
    if not panel().profiles:
        h.click(V(0, 0, 0))
        h.settle()
    ui.choose(panel().extent, "All")


def r4_flip():
    h.caught_up(panel())
    h.check("R4 All away from the block reaches nothing, and says so",
            "direction" in panel().message.text().lower(), panel().message.text())
    ui.click(panel().flip)


def r4_cut():
    h.caught_up(panel())
    h.check("R4 after Flip the extrusion goes into the block: Cut by itself", op() == "Cut", op())
    h.check("R4 through all", near(vol(), BLOCK - PI * 25.0 * 20.0), vol())
    h.task_button("OK")


def r4_done():
    h.check("R4 made", closed() and near(vol(), BLOCK - PI * 25.0 * 20.0), vol())


# -- R5 ------------------------------------------------------------------------------------------
def r5_setup():
    new_block("OpSymAll")
    s["sk"] = sketch_on((s["planes"]["XZ_Plane"], ""), circle(0, 10, 5))


def r5_symmetric():
    if not panel().profiles:
        h.click(V(0, 0, 10))
        h.settle()
    ui.choose(panel().direction, "Symmetric")


def r5_all():
    h.caught_up(panel())
    ui.choose(panel().extent, "All")


def r5_ok():
    h.caught_up(panel())
    h.check("R5 Symmetric + All inside the block: Cut by itself", op() == "Cut", op())
    h.task_button("OK")


def r5_done():
    h.check("R5 OK cut through both ways", closed() and near(vol(), BLOCK - PI * 25.0 * 40.0), vol())


# -- R6 ------------------------------------------------------------------------------------------
def r6_setup():
    from fission180 import commands, sketch_ui

    Gui.activateWorkbench("Fission180Workbench")
    doc = App.newDocument("OpFlat")
    body = commands.ensure_body()
    planes = sketch_ui.origin_planes(body)
    sk = sketch_ui.create_sketch(body, (planes["XZ_Plane"], ""))
    pts = [V(0, 0, 0), V(15, 0, 0), V(15, 10, 0), V(5, 10, 0), V(5, 30, 0), V(0, 30, 0)]
    for a, b in zip(pts, pts[1:] + pts[:1]):
        sk.addGeometry(Part.LineSegment(a, b), False)
    doc.recompute()
    rev = body.newObject("PartDesign::Revolution", "Revolution")
    rev.Profile = sk
    z_axis = [o for o in body.Origin.OutList if getattr(o, "Role", "") == "Z_Axis"][0]
    rev.ReferenceAxis = (z_axis, [""])
    rev.Angle = 360
    body.Tip = rev
    doc.recompute()
    sk.ViewObject.Visibility = False
    s["body"] = body
    s["start"] = vol()
    faces = list(enumerate(rev.Shape.Faces, 1))
    flat = [(i, f) for i, f in faces if f.Surface.TypeId == "Part::GeomPlane"]
    top = [i for i, f in flat if abs(f.CenterOfMass.z - 30) < 1e-6][0]
    s["bottom"] = "Face%d" % [i for i, f in flat if abs(f.CenterOfMass.z) < 1e-6][0]

    def beside(sketch):
        a = h.to_sketch(sketch, V(6, -4, 30))
        b = h.to_sketch(sketch, V(12, 4, 30))
        h.draw_rectangle(
            sketch, min(a[0], b[0]), min(a[1], b[1]), max(a[0], b[0]), max(a[1], b[1])
        )

    s["sk"] = sketch_on((rev, "Face%d" % top), beside)


def r6_to_object():
    if not panel().profiles:
        h.click(V(9, 0, 30))
        h.settle()
    h.check("R6 the rectangle beside the post is the profile", len(panel().profiles) == 1)
    ui.choose(panel().extent, "To Object")


def r6_underside():
    h.caught_up(panel())
    h.check("R6 the Object box waits", panel().active == "extent_object", panel().active)
    # the underside cannot be seen from here: picked the way the browser picks it
    doc = App.ActiveDocument
    Gui.Selection.addSelection(doc.Name, s["body"].Name, s["body"].Tip.Name + "." + s["bottom"])


def r6_cut():
    h.caught_up(panel())
    h.check("R6 reaching down into the base: Cut by itself (it was a Join)", op() == "Cut", op())
    # the 6 x 8 rectangle through the 10 mm base, x 6..12 inside r 15
    h.check("R6 the base is cut", near(vol(), s["start"] - 480.0), (vol(), s["start"]))
    h.task_button("OK")


def r6_done():
    h.check("R6 made", closed() and near(vol(), s["start"] - 480.0), vol())


# -- R8 ------------------------------------------------------------------------------------------
def r8_setup():
    new_block("OpSays")
    s["sk"] = sketch_on(top_face(), square_on_top)


def r8_zero_ok():
    if not panel().profiles:
        h.click(V(15, 0, 20))
        h.settle()
    h.task_button("OK")


def r8_said_zero():
    h.check("R8 OK at 0 keeps the dialog open", panel() is not None)
    h.check("R8 and says why next to the mouse",
            "Extrude is not finished" in told() and "zero" in told(), told())
    type_distance("5")
    h.task_button("OK")


def r8_edit():
    h.check("R8 +5 made", closed() and near(vol(), BLOCK + 500.0), vol())
    h.check("R8 edit from the timeline", ui.double_click_timeline(ui.timeline_titles()[-1]),
            ui.timeline_titles())


r8_edit.done = lambda: panel() is not None and panel().editing
r8_edit.done_what = "the extrude is open for editing"


def r8_edit_to_cut_all():
    h.check("R8 the saved Join shows", op() == "Join", op())
    h.check("R8 the person picks Cut", ui.choose(panel().operation, "Cut"))


def r8_cut_refused():
    h.caught_up(panel())
    # +5 from the top face goes through no body
    h.check("R8 the Cut stays shown (it went back to Join)", op() == "Cut", op())
    h.check("R8 with the reason in the dialog", "does not go through any body" in panel().message.text(),
            panel().message.text())
    h.task_button("OK")


def r8_ok_said():
    h.check("R8 OK is refused: the dialog stays", panel() is not None)
    h.check("R8 and says so next to the mouse",
            "Extrude is not finished" in told() and "does not go through any body" in told(), told())
    h.check("R8 nothing changed meanwhile", op() == "Cut", op())
    h.press("q")  # another command (Press Pull): the open dialog must end first


def r8_dropped():
    h.check("R8 the edit could not be kept: the dialog is gone", closed())
    h.check("R8 and that was said, with the reason",
            "The change to Extrude was not kept" in told() and "any body" in told(), told())
    h.check("R8 the extrude is the Join it was", near(vol(), BLOCK + 500.0), vol())
    h.press(QtCore.Qt.Key_Escape)  # Press Pull, which the key started, is not wanted here


r8_dropped.ready = closed
r8_dropped.ready_what = "the Extrude dialog ended when Press Pull started"


# -- R9 ------------------------------------------------------------------------------------------
def r9_setup():
    from fission180 import commands, components, sketch_ui

    new_block("OpComponent")
    doc = App.ActiveDocument
    s["root_body"] = s["body"]
    comp = components.new_component(doc)
    components.set_active(comp, doc)
    own = commands.ensure_body()
    s["own"] = own
    planes = sketch_ui.origin_planes(own)
    sk = sketch_ui.create_sketch(own, (planes["XY_Plane"], ""))
    sk.addGeometry(Part.Circle(V(0, 0, 0), V(0, 0, 1), 5), False)
    doc.recompute()
    s["sk"], s["own_planes"] = sk, planes
    Gui.Selection.clearSelection()
    h.fit()
    h.check("R9 the new component is active and empty",
            components.active_component(doc) is comp and vol(own) == 0.0)


def r9_first():
    if not panel().profiles:
        h.click(V(0, 0, 0))
        h.settle()
    h.check("R9 over another component's block, nothing typed: New Body", op() == "New Body", op())
    type_distance("5")
    h.check("R9 +5 into the other component's block: New Body (it was a Cut)", op() == "New Body", op())
    h.check("R9 the block is untouched", near(vol(s["root_body"]), BLOCK), vol(s["root_body"]))
    type_distance("-5")
    h.check("R9 -5 away, touching it: New Body (it was a Join into the block)",
            op() == "New Body", op())
    h.check("R9 the block is still untouched", near(vol(s["root_body"]), BLOCK), vol(s["root_body"]))
    type_distance("8")
    h.task_button("OK")


def r9_second_setup():
    from fission180 import components, sketch_ui

    doc = App.ActiveDocument
    h.check("R9 the component's first solid", closed() and near(vol(s["own"]), PI * 25.0 * 8.0),
            vol(s["own"]))
    h.check("R9 it lives in the component", components.container_of(s["own"]) is not None)
    sk = sketch_ui.create_sketch(s["own"], (s["own_planes"]["XY_Plane"], ""))
    sk.addGeometry(Part.Circle(V(0, 0, 0), V(0, 0, 1), 2), False)
    doc.recompute()
    Gui.Selection.clearSelection()
    h.fit()


def r9_second():
    if not panel().profiles:
        h.click(V(0, 0, 0))
        h.settle()
    type_distance("8")
    h.check("R9 into the component's own body: Cut by itself", op() == "Cut", op())
    names = panel()._participant_names(compute=False) or []
    h.check("R9 the row lists what the cut goes through, the other component's block too "
            "(Fusion's Objects To Cut)", s["own"].Name in names, names)
    h.task_button("Cancel")


# -- R10 -----------------------------------------------------------------------------------------
def r10_setup():
    h.check("R9 cancelled", closed())
    new_block("OpEdit")
    s["sk"] = sketch_on(top_face(), square_on_top)


def r10_make():
    if not panel().profiles:
        h.click(V(15, 0, 20))
        h.settle()
    type_distance("-5")
    h.check("R10 Cut by itself", op() == "Cut", op())
    h.task_button("OK")


def r10_edit():
    h.check("R10 made", closed() and near(vol(), BLOCK - 500.0), vol())
    ui.double_click_timeline(ui.timeline_titles()[-1])


r10_edit.done = lambda: panel() is not None and panel().editing
r10_edit.done_what = "the extrude is open for editing"


def r10_editing():
    h.check("R10 the saved Cut shows", op() == "Cut", op())
    type_distance("5")
    h.check("R10 +5 (where a new extrude would be a Join): the saved Cut stays", op() == "Cut", op())
    type_distance("-8")
    h.check("R10 -8: Cut", op() == "Cut" and near(vol(), BLOCK - 800.0), (op(), vol()))
    h.task_button("OK")


def r10_undo():
    h.check("R10 the edit is kept", closed() and near(vol(), BLOCK - 800.0), vol())
    Gui.runCommand("Std_Undo")


def r10_redo():
    h.check("R10 Undo: 5 deep again", near(vol(), BLOCK - 500.0), vol())
    Gui.runCommand("Std_Redo")


def r10_save():
    h.check("R10 Redo: 8 deep", near(vol(), BLOCK - 800.0), vol())
    doc = App.ActiveDocument
    path = os.path.join(tempfile.mkdtemp(prefix="fission180_op_"), "OpEdit.FCStd")
    doc.saveAs(path)
    name = doc.Name
    App.closeDocument(name)
    App.openDocument(path)


def r10_reopened():
    from fission180 import extrude

    doc = App.ActiveDocument
    s["body"] = bodies()[0]
    h.check("R10 reopened", near(vol(), BLOCK - 800.0), vol())
    pockets = [o for o in doc.Objects if o.TypeId == "PartDesign::Pocket"]
    h.check("R10 the operation is read back", pockets and extrude.read(pockets[-1])[1]["operation"] == "cut")


steps = [
    r1_setup, press_e, r1_first, r1_done,
    r2_setup, press_e, r2_out, r2_in, r2_out_again,
    r7_setup, press_e, r7_pick_join, r7_symmetric, r7_typed, r7_one_side,
    r3_setup, press_e, r3_cut, r3_symmetric, r3_done,
    r4_setup, press_e, r4_all, r4_flip, r4_cut, r4_done,
    r5_setup, press_e, r5_symmetric, r5_all, r5_ok, r5_done,
    r6_setup, press_e, r6_to_object, r6_underside, r6_cut, r6_done,
    r8_setup, press_e, r8_zero_ok, r8_said_zero, r8_edit, r8_edit_to_cut_all, r8_cut_refused,
    r8_ok_said, r8_dropped,
    r9_setup, press_e, r9_first, r9_second_setup, press_e, r9_second,
    r10_setup, press_e, r10_make, r10_edit, r10_editing, r10_undo, r10_redo, r10_save,
    r10_reopened,
]

h.run("book_extrude_operation", steps, paced_by="state")
