# SPDX-License-Identifier: LGPL-2.1-or-later
"""Wave 7 (the book parity report), params: a parametric plate survives a parameter change.

The book's Prototype Drone ends with "experiment by changing parameters". In Fission 180:
"Change Parameters Arm_Length 53 -> 60 is refused live: Not changed: with Arm_Length = 60,
Extrude 1 would break: Sub shape not found: Sketch.InternalFace56. The extrude stores sketch
areas by number and the numbers change. The parametric drone, the point of this project,
does not work in Fission."

The plate here is the same case, small: a hub circle (r 12) inside a rim circle whose radius
is the user parameter Arm_Length (30), and 8 spokes between them at every 45 degrees: 9
closed areas (the hub and 8 sectors). The sketch is drawn by script (the drawing tools have
their own scenarios); everything after it is real input.

  A  Finish Sketch; the hub and every other sector (5 areas) clicked (Ctrl+click adds), E,
     Distance 5, OK: one body, the hub with four blades.
  B  MODIFY > Change Parameters: Arm_Length typed 40, then 25, then 34, then 30. Each time
     the change is accepted (no "would break"), and the body is the hub and the SAME four
     sectors at the new radius: its volume, a point inside each picked sector, a point in
     each sector that was not picked. (With the rim at 25 the sectors are smaller than the
     hub, at 40 larger: FreeCAD numbers a sketch's areas anew.)
  C  OK; Ctrl+Z puts the 30 back in one step; Ctrl+Y brings the last value; the design
     saved, closed and opened again still follows Arm_Length (typed 36 in Change Parameters).

The area references are the extrude builder's (sketch_area*.py): this scenario is the
acceptance test named in book-params.md, item 13.
"""

import math
import os
import tempfile

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import arrow_input as arrows
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import sketch_input as si
from Fission180Tests.gui import widget_input as w

V = App.Vector
CTRL = QtCore.Qt.ControlModifier
HUB = 12.0
DEPTH = 5.0
PICKED = (0, 2, 4, 6)  # the sectors extruded (sector k is between the spokes k and k + 1)
s = {}


def doc():
    return App.ActiveDocument


def rim():
    from fission180 import parameters

    return parameters.container(doc()).Arm_Length.Value


def sector_point(k, radius=None, z=0.0):
    """A point in the middle of sector k (between 45 k and 45 (k + 1) degrees)."""
    radius = (HUB + rim()) / 2.0 if radius is None else radius
    angle = math.radians(45.0 * k + 22.5)
    return V(radius * math.cos(angle), radius * math.sin(angle), z)


def expected_volume(radius):
    hub = math.pi * HUB**2
    sector = math.pi * (radius**2 - HUB**2) / 8.0
    return (hub + len(PICKED) * sector) * DEPTH


def bodies():
    return [o for o in doc().Objects if o.TypeId == "PartDesign::Body" and not o.Shape.isNull()]


def solid():
    found = [b.Shape for b in bodies() if b.Shape.Volume > 1e-6]
    return found[0] if len(found) == 1 else None


def shape_checks(tag, radius):
    """The body is the hub and the four picked sectors at `radius`."""
    shape = solid()
    h.check("%s: one body" % tag, shape is not None, [b.Label for b in bodies()])
    if shape is None:
        return
    want = expected_volume(radius)
    h.check(
        "%s: the hub and four sectors at radius %g" % (tag, radius),
        abs(shape.Volume - want) < 1e-6 * want,
        (shape.Volume, want),
    )
    mid = DEPTH / 2.0
    inside = [
        k for k in range(8) if shape.isInside(sector_point(k, (HUB + radius) / 2, mid), 1e-6, True)
    ]
    h.check("%s: the same four sectors as picked" % tag, inside == list(PICKED), inside)
    h.check("%s: the hub is solid" % tag, shape.isInside(V(3, 2, mid), 1e-6, True))
    broken = [o.Label for o in doc().Objects if "Invalid" in o.State or "Error" in o.State]
    h.check("%s: nothing is broken" % tag, not broken, broken)


def dialog():
    from fission180 import parameters_ui

    d = parameters_ui.ParametersDialog.last
    return d if d is not None and d.isVisible() else None


# == the plate =====================================================================================
def new_design():
    from fission180 import parameters

    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("BookDrone")
    parameters.add_user(doc(), "Arm_Length", "mm", "30")
    doc().recompute()
    h.fit()
    h.ribbon("Create Sketch")


def pick_xy():
    pl.click_square("XY_Plane")


def draw():
    import Part
    import Sketcher

    from fission180 import parameters

    sk = h.in_sketch()
    h.check("the sketch is open on XY", sk is not None)
    if sk is None:
        return
    s["sketch"] = sk
    radius = 30.0
    inner = sk.addGeometry(Part.Circle(V(0, 0, 0), V(0, 0, 1), HUB))
    outer = sk.addGeometry(Part.Circle(V(0, 0, 0), V(0, 0, 1), radius))
    sk.addConstraint(Sketcher.Constraint("Coincident", inner, 3, -1, 1))
    sk.addConstraint(Sketcher.Constraint("Coincident", outer, 3, -1, 1))
    sk.addConstraint(Sketcher.Constraint("Radius", inner, HUB))
    rim_dim = sk.addConstraint(Sketcher.Constraint("Radius", outer, radius))
    for k in range(8):
        angle = math.radians(45.0 * k)
        u = V(math.cos(angle), math.sin(angle), 0)
        line = sk.addGeometry(Part.LineSegment(u * HUB, u * radius))
        sk.addConstraint(Sketcher.Constraint("PointOnObject", line, 1, inner))
        sk.addConstraint(Sketcher.Constraint("PointOnObject", line, 2, outer))
        sk.addConstraint(Sketcher.Constraint("PointOnObject", -1, 1, line))
        if k % 4 == 0:
            sk.addConstraint(Sketcher.Constraint("Horizontal", line))
        elif k % 4 == 2:
            sk.addConstraint(Sketcher.Constraint("Vertical", line))
        else:
            turn = angle if angle <= math.pi else angle - 2 * math.pi
            sk.addConstraint(Sketcher.Constraint("Angle", line, turn))
    parameters.set_expression(sk, ".Constraints[%d]" % rim_dim, "Parameters.Arm_Length")
    doc().recompute()
    h.check("the sketch solves", sk.solve() == 0 and not sk.ConflictingConstraints, sk.solve())
    h.check("the sketch is fully constrained", sk.solve() == 0, sk.solve())


def finish():
    h.ribbon("Finish Sketch")


def finished():
    sk = s["sketch"]
    faces = len(sk.InternalShape.Faces) if not sk.InternalShape.isNull() else 0
    h.check("the sketch has its 9 areas (the hub and 8 sectors)", faces == 9, faces)
    h.fit(iso=False)


# == A: five areas, one extrude ====================================================================
def a_hub():
    h.click(V(3, 2, 0))


def a_sector(k):
    def step():
        h.click(sector_point(k), CTRL)

    step.__name__ = "a_sector_%d" % k
    return step


def a_selected():
    picked = sum((list(x.SubElementNames) for x in Gui.Selection.getSelectionEx()), [])
    h.check("A: five areas are selected", len(picked) == 5, picked)
    h.press("e")


def a_distance():
    arrows.give_distance("%g" % DEPTH)
    h.task_button("OK")


def a_made():
    shape_checks("A", 30.0)
    h.fit()
    h.shot("A-plate")


# == B: the parameter changes ======================================================================
def b_open():
    si.menu_item("MODIFY", "Change Parameters")


b_open.done = lambda: dialog() is not None
b_open.done_what = "the Parameters dialog is open"


def type_arm(text):
    d = dialog()
    row = [
        r
        for r in range(d.user.rowCount())
        if d.user.item(r, 0).data(QtCore.Qt.UserRole) == "Arm_Length"
    ]
    h.check("Arm_Length is in the table", bool(row))
    if not row:
        return
    rect = d.user.visualItemRect(d.user.item(row[0], 2))
    d.window().activateWindow()
    w.double_click(d.user.viewport(), rect.center())
    editors = [e for e in d.user.findChildren(QtWidgets.QLineEdit) if e.isVisible()]
    h.check("an editor opened for Arm_Length", bool(editors))
    if editors:
        QtTest.QTest.keyClick(editors[0], QtCore.Qt.Key_A, QtCore.Qt.ControlModifier)
        QtTest.QTest.keyClicks(editors[0], text)
        QtTest.QTest.keyClick(editors[0], QtCore.Qt.Key_Return)


def changed(radius):
    def type_it():
        type_arm("%g" % radius)

    type_it.__name__ = "b_type_%g" % radius
    type_it.timeout_s = 120

    def check_it():
        d = dialog()
        text = d.message.text() if d is not None else ""
        h.check("B %g: the change is accepted (no 'would break')" % radius, text == "", text)
        h.check("B %g: Arm_Length is %g" % (radius, radius), abs(rim() - radius) < 1e-9, rim())
        shape_checks("B %g" % radius, radius)
        h.new_errors() if text else None

    check_it.__name__ = "b_check_%g" % radius
    return [type_it, check_it]


# == C: OK, undo, redo, save and reopen ============================================================
def c_ok():
    d = dialog()
    w.click(
        [x for x in d.findChildren(QtWidgets.QPushButton) if x.text().replace("&", "") == "OK"][0]
    )


c_ok.done = lambda: dialog() is None
c_ok.done_what = "the Parameters dialog closed"


def c_change_again():
    si.menu_item("MODIFY", "Change Parameters")


c_change_again.done = lambda: dialog() is not None
c_change_again.done_what = "the Parameters dialog is open"


def c_undo():
    h.press(QtCore.Qt.Key_Z, QtCore.Qt.ControlModifier)


def c_undone():
    h.check("C: Ctrl+Z puts Arm_Length back to 30", abs(rim() - 30) < 1e-9, rim())
    shape_checks("C undo", 30.0)


def c_redo():
    h.press(QtCore.Qt.Key_Y, QtCore.Qt.ControlModifier)


def c_redone():
    h.check("C: Ctrl+Y brings 42 again", abs(rim() - 42) < 1e-9, rim())
    shape_checks("C redo", 42.0)


def c_save():
    path = os.path.join(tempfile.mkdtemp(prefix="fission180-book-drone-"), "book_drone.FCStd")
    s["path"] = path
    name = doc().Name
    doc().saveAs(path)
    App.closeDocument(name)


def c_open():
    App.openDocument(s["path"])
    h.fit()


def c_reopened():
    shape_checks("C reopened", 42.0)
    si.menu_item("MODIFY", "Change Parameters")


c_reopened.done = lambda: dialog() is not None
c_reopened.done_what = "the Parameters dialog is open"


steps = [new_design, pick_xy, draw, finish, finished]
steps += [a_hub] + [a_sector(k) for k in PICKED] + [a_selected, a_distance, a_made]
steps += [b_open]
for radius in (40.0, 25.0, 34.0, 30.0):
    steps += changed(radius)
steps += [c_ok, c_change_again] + changed(42.0) + [c_ok, c_undo, c_undone, c_redo, c_redone]
steps += [c_save, c_open, c_reopened] + changed(36.0) + [c_ok]

h.run("book_params_drone", steps, paced_by="state")
