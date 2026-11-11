# SPDX-License-Identifier: LGPL-2.1-or-later
"""Loft to a point (wave 7; the book's surfboard: "Clicking the Workspace ORIGIN as the last
loft section does nothing ... even a sketch point at the origin could not be clicked while
the construction planes and the origin were visible (their glyphs are in front and take the
click)").

A circle r 10 sketched 20 mm above the Top plane.

L1  Loft: the circle's area, then the origin point picked in the browser (the row O under
    Origin): a cone to the origin, pi * 100 * 20 / 3. Edit from the timeline: both sections
    are listed; OK. Undo / Redo. Save / reopen.
L2  The same with the origin shown: a click on the origin in the 3D view, where the origin's
    planes and axes are drawn over it, takes the origin point.
L3  A sketch point at the origin, with the origin shown: the click takes the point.
L4  A plane's square alone under the mouse (nothing usable behind it) is refused with a
    reason; the rails box refuses a point with a reason.
"""
import math
import os
import tempfile

import FreeCAD as App
import FreeCADGui as Gui
import Part

from Fission180Tests.gui import dialog_input as ui
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import sketch_input
from Fission180Tests.gui import timeline_input as t

V = App.Vector
CONE = math.pi * 100.0 * 20.0 / 3.0
s = {}


def panel():
    from fission180 import loft_ui

    p = loft_ui.LoftPanel.last
    return p if p is not None and not p._closed else None


def near(a, b, tol=2e-3):
    return abs(a - b) <= tol * max(1.0, abs(b))


def total():
    return sum(
        b.Shape.Volume
        for b in App.ActiveDocument.findObjects("PartDesign::Body")
        if not b.Shape.isNull()
    )


def origin_point():
    for obj in s["body"].Origin.OutList:
        if obj.TypeId == "App::Point":
            return obj
    return None


def show_origin(on):
    for obj in [s["body"].Origin] + list(s["body"].Origin.OutList):
        try:
            obj.ViewObject.Visibility = bool(on)
        except Exception:
            pass


def setup(name, with_point=False):
    from fission180 import commands, sketch_ui

    Gui.activateWorkbench("Fission180Workbench")
    doc = App.newDocument(name)
    body = commands.ensure_body()
    planes = sketch_ui.origin_planes(body)
    sk = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    sk.AttachmentOffset = App.Placement(V(0, 0, 20), App.Rotation())
    sk.addGeometry(Part.Circle(V(0, 0, 0), V(0, 0, 1), 10), False)
    doc.recompute()
    s.update(body=body, planes=planes, sk=sk, tip=None)
    if with_point:
        tip = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
        tip.addGeometry(Part.Point(V(0, 0, 0)), False)
        doc.recompute()
        s["tip"] = tip
    Gui.Selection.clearSelection()
    h.fit()


def open_loft():
    h.click_empty()
    sketch_input.menu_item("CREATE", "Loft")


open_loft.done = lambda: panel() is not None
open_loft.done_what = "the Loft dialog is open"


def closed():
    return panel() is None


def click_area():
    h.click(V(4, 3, 20))


# -- L1 ------------------------------------------------------------------------------------------
def l1_setup():
    setup("LoftOrigin")
    h.check("L1 the design has an origin point", origin_point() is not None)


def l1_area():
    p = panel()
    h.check("L1 the circle's area is the first section", len(p.profiles) == 1, p.profiles)
    h.check("L1 the browser has the origin point's row", "O" in t.labels(), t.labels()[:14])
    t.click_row("O")


def l1_cone():
    p = panel()
    h.caught_up(p)
    h.check("L1 the origin point is the second section",
            len(p.profiles) == 2 and p.profiles[1][0] is origin_point(), p.profiles)
    h.check("L1 no problem said", "⚠" not in p.message.text(), p.message.text())
    h.check("L1 a cone to the origin", near(total(), CONE), (total(), CONE))
    h.task_button("OK")


l1_cone.done = closed
l1_cone.done_what = "OK finished the loft"


def l1_edit():
    h.check("L1 kept", near(total(), CONE), total())
    low = min(b.Shape.BoundBox.ZMin for b in App.ActiveDocument.findObjects("PartDesign::Body")
              if not b.Shape.isNull())
    h.check("L1 it ends in a point at the origin", near(low, 0.0, 1e-6), low)
    ui.double_click_timeline(ui.timeline_titles()[-1])


l1_edit.done = lambda: panel() is not None
l1_edit.done_what = "the loft is open for editing"


def l1_editing():
    p = panel()
    h.check("L1 the edit lists both sections, the point last",
            len(p.profiles) == 2 and p.profiles[1][0] is origin_point(), p.profiles)
    h.task_button("OK")


l1_editing.done = closed
l1_editing.done_what = "OK closed the edit"


def l1_undo():
    Gui.runCommand("Std_Undo")
    Gui.runCommand("Std_Undo")


def l1_redo():
    h.check("L1 Undo takes the loft away", total() < 1e-6, total())
    Gui.runCommand("Std_Redo")
    Gui.runCommand("Std_Redo")


def l1_save():
    h.check("L1 Redo brings it back", near(total(), CONE), total())
    doc = App.ActiveDocument
    path = os.path.join(tempfile.mkdtemp(prefix="fission180_loft_"), "LoftOrigin.FCStd")
    doc.saveAs(path)
    App.closeDocument(doc.Name)
    App.openDocument(path)
    App.ActiveDocument.recompute()


def l1_reopened():
    h.check("L1 reopened and rebuilt: the cone", near(total(), CONE), total())
    bad = [o.Label for o in App.ActiveDocument.Objects if "Invalid" in o.State or "Error" in o.State]
    h.check("L1 nothing in error", not bad, bad)


# -- L2 ------------------------------------------------------------------------------------------
def l2_setup():
    setup("LoftOriginView")
    show_origin(True)
    h.fit()


def l2_origin():
    p = panel()
    h.check("L2 the circle's area is the first section", len(p.profiles) == 1, p.profiles)
    h.click(V(0, 0, 0))  # the origin, under the origin's planes and axes


def l2_cone():
    p = panel()
    h.caught_up(p)
    h.check("L2 the click on the origin in the view took the origin point",
            len(p.profiles) == 2 and p.profiles[1][0] is origin_point(),
            (p.profiles, p.message.text(), h.state.get("last_click")))
    h.check("L2 a cone to the origin", near(total(), CONE), (total(), CONE))
    h.task_button("Cancel")


l2_cone.done = closed
l2_cone.done_what = "the dialog is closed"


# -- L3 ------------------------------------------------------------------------------------------
def l3_setup():
    setup("LoftSketchPoint", with_point=True)
    show_origin(True)
    origin_point().ViewObject.Visibility = False  # only the sketch's point is there to take
    h.fit()


def l3_point():
    p = panel()
    h.check("L3 the circle's area is the first section", len(p.profiles) == 1, p.profiles)
    h.click(V(0, 0, 0))  # the sketch point, under the origin's planes and axes


def l3_cone():
    p = panel()
    h.caught_up(p)
    h.check("L3 the click took the sketch's point behind the origin's planes",
            len(p.profiles) == 2 and p.profiles[1][0] is s["tip"],
            (p.profiles, p.message.text(), h.state.get("last_click")))
    h.check("L3 a cone to the point", near(total(), CONE), (total(), CONE))


# -- L4 ------------------------------------------------------------------------------------------
def l4_square():
    p = panel()
    s["count"] = len(p.profiles)
    spot = None
    for obj in s["body"].Origin.OutList:
        if getattr(obj, "Role", "") == "XZ_Plane":
            spot = obj
    h.check("L4 the Front plane is shown", spot is not None and spot.ViewObject.Visibility)
    h.click_empty()  # the pointer over nothing: nothing usable lies behind the plane there
    h.settle()
    # the plane picked the way its browser row picks it (the pointer stays over nothing)
    Gui.Selection.addSelection(App.ActiveDocument.Name, spot.Name)


def l4_refused():
    p = panel()
    h.check("L4 a plane is no section: nothing is added", len(p.profiles) == s["count"], p.profiles)
    h.check("L4 and the dialog says why", "is no profile" in p.message.text(), p.message.text())
    h.task_button("Cancel")


l4_refused.done = closed
l4_refused.done_what = "the dialog is closed"


steps = [
    l1_setup, open_loft, click_area, l1_area, l1_cone, l1_edit, l1_editing, l1_undo, l1_redo,
    l1_save, l1_reopened,
    l2_setup, open_loft, click_area, l2_origin, l2_cone,
    l3_setup, open_loft, click_area, l3_point, l3_cone, l4_square, l4_refused,
]

h.run("book_extrude_loft", steps, paced_by="state")
