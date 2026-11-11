# SPDX-License-Identifier: LGPL-2.1-or-later
"""Box and Cylinder the way the book places them (wave 7): pick the plane, click, type the
sizes on the canvas, Tab, Enter; a negative height; body names.

Keys are sent like a keyboard sends them: to whatever has the keyboard at that moment (after
a click in the 3D view that is the view; the report: "focus stays in the 3D view, typed
numbers go nowhere and Tab jumps into the dialog").

B1  The book's play brick: CREATE > Box, the XY plane's square, a click on the origin
    corner. Two size boxes show on the canvas, on the rectangle's sides (Length, Width).
    3 1 . 8 goes into the Length box; Tab moves to the Width box (not into the dialog);
    1 5 . 8 and Enter place the box 31.8 x 15.8. Then 9 . 6 goes into the Height arrow's box
    and Enter is OK: 31.8 x 15.8 x 9.6 at the origin, 4823.4 mm3. The body is Body1.
B2  The geocache's bottom: CREATE > Cylinder on XY, the centre at (60, 0), the Diameter box
    on the canvas takes 3 3, Enter places it; 1 6, Enter: z 0..16. A second cylinder on the
    same plane at (60, 40) with Height - 8 grows down, away from the first (z -8..0), and
    is a New Body named Body3.
B3  A cylinder on the first cylinder's top face: Height 5 stands on the face (z 16..21,
    Join); - 5 goes into the body: Cut by itself.
B4  Undo takes the last cylinder away, Redo brings it back; Esc in the middle of placing
    leaves nothing behind (no box on the canvas either).
"""
import math

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import primitive_input as pi

V = App.Vector
PI = math.pi
s = {}


def near(a, b, tol=1e-4):
    return abs(a - b) <= tol * max(1.0, abs(b))


def keyboard(text="", key=None):
    """Type like a keyboard: every key goes to the widget that has the keyboard then."""
    for char in text:
        target = QtWidgets.QApplication.focusWidget() or h.gl_widget()
        QtTest.QTest.keyClicks(target, char)
        QtWidgets.QApplication.processEvents()
        h.settle()
    if key is not None:
        target = QtWidgets.QApplication.focusWidget() or h.gl_widget()
        QtTest.QTest.keyClick(target, key)
        QtWidgets.QApplication.processEvents()


def focus_name():
    w = QtWidgets.QApplication.focusWidget()
    return "%s %s" % (type(w).__name__, w.objectName()) if w is not None else "nothing"


def placing_boxes(p):
    return {
        k[len(p.PLACING):]: b
        for k, b in p.value_boxes.boxes.items()
        if k.startswith(p.PLACING) and b.isVisible()
    }


def bodies():
    return sorted(App.ActiveDocument.findObjects("PartDesign::Body"), key=lambda o: o.ID)


def solid_bodies():
    return [b for b in bodies() if not b.Shape.isNull() and b.Shape.Solids]


def box_of(body):
    return pi.bbox(body.Shape)


def wide_view():
    """Fit, then zoom out so that there is room around the part to place the next shape
    (the wheel, in effect: setting the view up is not what is tested here)."""
    h.fit()
    camera = h.view().getCameraNode()
    try:
        camera.height.setValue(camera.height.getValue() * 4.0)
    except Exception:
        pass
    h.view_still()


# -- B1 ------------------------------------------------------------------------------------------
def b1_new():
    Gui.activateWorkbench("Fission180Workbench")
    App.newDocument("PrimBook")
    h.fit()
    pi.menu("Box")


b1_new.done = lambda: pi.panel("BoxPanel") is not None
b1_new.done_what = "the Box dialog is open"


def b1_plane():
    pl.click_square("XY_Plane")


def b1_corner():
    pl.click_on_plane(V(0, 0, 0))


def b1_boxes():
    p = pi.panel("BoxPanel")
    h.wait_for(lambda: len(placing_boxes(p)) == 2, "the Length and Width boxes on the canvas")
    h.check("B1 after the corner click the view has the keyboard", "Line" not in focus_name(),
            focus_name())
    h.check("B1 Length and Width boxes show on the canvas", sorted(placing_boxes(p)) ==
            ["length", "width"], sorted(placing_boxes(p)))
    keyboard("31.8")


def b1_length():
    p = pi.panel("BoxPanel")
    box = placing_boxes(p).get("length")
    h.check("B1 the digits went into the Length box on the canvas",
            box is not None and box.hasFocus() and box.text().strip() == "31.8",
            (focus_name(), box.text() if box is not None else None))
    keyboard(key=QtCore.Qt.Key_Tab)


def b1_width():
    p = pi.panel("BoxPanel")
    box = placing_boxes(p).get("width")
    h.check("B1 Tab went to the Width box on the canvas (not into the dialog)",
            box is not None and box.hasFocus(), focus_name())
    h.check("B1 Tab took the Length", near(p.length.value(), 31.8), p.length.value())
    keyboard("15.8")
    keyboard(key=QtCore.Qt.Key_Return)


def b1_placed():
    p = pi.panel("BoxPanel")
    h.check("B1 Enter placed the box (the dialog stays for the height)",
            p is not None and p.state == "ready", p and p.state)
    box = p.target
    h.check("B1 31.8 x 15.8 as typed",
            box is not None and near(box.Length.Value, 31.8) and near(box.Width.Value, 15.8),
            box and (box.Length.Value, box.Width.Value))
    h.check("B1 the placing boxes are gone", not placing_boxes(p), sorted(placing_boxes(p)))
    keyboard("9.6")  # (the mouse is where the corner was clicked: nobody moves it to type)


def b1_height():
    p = pi.panel("BoxPanel")
    box = p.value_boxes.boxes.get("height")
    h.check("B1 9.6 went into the Height arrow's box",
            box is not None and box.hasFocus() and box.text().strip() == "9.6",
            (focus_name(), box.text() if box is not None else None))
    keyboard(key=QtCore.Qt.Key_Return)


b1_height.done = pi.no_dialog
b1_height.done_what = "Enter finished the Box"


def b1_done():
    made = solid_bodies()
    h.check("B1 one body", len(made) == 1, [b.Label for b in bodies()])
    if made:
        h.check("B1 31.8 x 15.8 x 9.6", near(made[0].Shape.Volume, 31.8 * 15.8 * 9.6),
                made[0].Shape.Volume)
        h.check("B1 at the origin, upwards",
                all(near(a, b, 1e-3) for a, b in zip(box_of(made[0]), [0, 0, 0, 31.8, 15.8, 9.6])),
                box_of(made[0]))
        h.check("B1 the first body is called Body1", made[0].Label == "Body1", made[0].Label)
    wide_view()
    pi.menu("Cylinder")


b1_done.done = lambda: pi.panel("CylinderPanel") is not None
b1_done.done_what = "the Cylinder dialog is open"


# -- B2 ------------------------------------------------------------------------------------------
def cylinder_at(x, y, diameter, height):
    """Steps: the XY square, the centre, the diameter typed on the canvas, the height."""

    def plane():
        pl.click_square("XY_Plane")

    def centre():
        pl.click_on_plane(V(x, y, 0))

    def diameter_box():
        p = pi.panel("CylinderPanel")
        h.wait_for(lambda: "diameter" in placing_boxes(p), "the Diameter box on the canvas")
        keyboard(diameter)

    def place():
        p = pi.panel("CylinderPanel")
        box = placing_boxes(p).get("diameter")
        h.check("the digits went into the Diameter box on the canvas",
                box is not None and box.hasFocus() and box.text().strip() == diameter,
                (focus_name(), box.text() if box is not None else None))
        keyboard(key=QtCore.Qt.Key_Return)

    def high():
        p = pi.panel("CylinderPanel")
        h.check("Enter placed the cylinder", p is not None and p.state == "ready", p and p.state)
        h.check("its diameter as typed", near(p.diameter.value(), float(diameter)),
                p.diameter.value())
        keyboard(height)

    def typed():
        p = pi.panel("CylinderPanel")
        box = p.value_boxes.boxes.get("height")
        h.check("the height went into the Height arrow's box",
                box is not None and box.text().strip() == height,
                (focus_name(), box.text() if box is not None else None))
        s["operation"] = None

    def ok():
        p = pi.panel("CylinderPanel")
        h.caught_up(p)
        s["operation"] = p.operation.currentText()
        keyboard(key=QtCore.Qt.Key_Return)

    ok.done = pi.no_dialog
    ok.done_what = "Enter finished the Cylinder"
    tag = "%g_%g" % (x, y)
    found = [plane, centre, diameter_box, place, high, typed, ok]
    for fn in found:
        fn.__name__ = "cyl_%s_%s" % (tag.replace(".", "_"), fn.__name__)
    return found


def b2_first_done():
    made = solid_bodies()
    h.check("B2 a second body", len(made) == 2, [b.Label for b in bodies()])
    if len(made) == 2:
        h.check("B2 d 33 x 16", near(made[1].Shape.Volume, PI * 16.5**2 * 16), made[1].Shape.Volume)
        bb = box_of(made[1])
        h.check("B2 z 0..16", near(bb[2], 0.0, 1e-3) and near(bb[5], 16.0, 1e-3), bb)
        h.check("B2 it is called Body2", made[1].Label == "Body2", made[1].Label)
        s["first"] = made[1]
    wide_view()
    pi.menu("Cylinder")


b2_first_done.done = lambda: pi.panel("CylinderPanel") is not None
b2_first_done.done_what = "the Cylinder dialog is open"


def b2_second_done():
    made = solid_bodies()
    h.check("B2 Height -8 beside the first: a body of its own", len(made) == 3,
            [b.Label for b in bodies()])
    h.check("B2 away from every body: New Body", s.get("operation") == "New Body", s.get("operation"))
    if len(made) == 3:
        bb = box_of(made[2])
        h.check("B2 a negative height goes the other way: z -8..0",
                near(bb[2], -8.0, 1e-3) and near(bb[5], 0.0, 1e-3), bb)
        h.check("B2 it is called Body3", made[2].Label == "Body3", made[2].Label)
        h.check("B2 the first cylinder is untouched",
                near(s["first"].Shape.Volume, PI * 16.5**2 * 16), s["first"].Shape.Volume)
    wide_view()
    pi.menu("Cylinder")


b2_second_done.done = lambda: pi.panel("CylinderPanel") is not None
b2_second_done.done_what = "the Cylinder dialog is open"


# -- B3 ------------------------------------------------------------------------------------------
def b3_face():
    h.click(V(60, 5, 16))  # the first cylinder's top face


def b3_centre():
    p = pi.panel("CylinderPanel")
    h.check("B3 the top face is the plane", p is not None and p.state == "place", p and p.state)
    h.click(V(60, 0, 16))


def b3_diameter():
    p = pi.panel("CylinderPanel")
    h.wait_for(lambda: "diameter" in placing_boxes(p), "the Diameter box on the canvas")
    keyboard("10")
    keyboard(key=QtCore.Qt.Key_Return)


def b3_up():
    p = pi.panel("CylinderPanel")
    h.check("B3 placed", p is not None and p.state == "ready", p and p.state)
    keyboard("5")
    keyboard(key=QtCore.Qt.Key_Tab)  # (Tab takes the value and keeps the dialog open)


def b3_join():
    p = pi.panel("CylinderPanel")
    h.caught_up(p)
    h.check("B3 Height 5 on the face: Join", p.operation.currentText() == "Join",
            p.operation.currentText())
    bb = box_of(s["first"])
    h.check("B3 it stands on the face: z up to 21", near(bb[5], 21.0, 1e-3), bb)
    keyboard("-5")
    keyboard(key=QtCore.Qt.Key_Tab)


def b3_cut():
    p = pi.panel("CylinderPanel")
    h.caught_up(p)
    h.check("B3 Height -5 goes into the body: Cut by itself", p.operation.currentText() == "Cut",
            p.operation.currentText())
    want = PI * 16.5**2 * 16 - PI * 25 * 5
    h.check("B3 a pocket d 10 x 5", near(s["first"].Shape.Volume, want), s["first"].Shape.Volume)
    h.task_button("OK")


b3_cut.done = pi.no_dialog
b3_cut.done_what = "OK finished the Cylinder"


# -- B4 ------------------------------------------------------------------------------------------
def b4_undo():
    want = PI * 16.5**2 * 16 - PI * 25 * 5
    h.check("B3 kept", near(s["first"].Shape.Volume, want), s["first"].Shape.Volume)
    Gui.runCommand("Std_Undo")


def b4_redo():
    h.check("B4 Undo takes the pocket away",
            near(s["first"].Shape.Volume, PI * 16.5**2 * 16), s["first"].Shape.Volume)
    Gui.runCommand("Std_Redo")


def b4_box():
    want = PI * 16.5**2 * 16 - PI * 25 * 5
    h.check("B4 Redo brings it back", near(s["first"].Shape.Volume, want), s["first"].Shape.Volume)
    s["count"] = len(bodies())
    wide_view()
    pi.menu("Box")


b4_box.done = lambda: pi.panel("BoxPanel") is not None
b4_box.done_what = "the Box dialog is open"


def b4_plane():
    pl.click_square("XY_Plane")


def b4_corner():
    pl.click_on_plane(V(-40, -40, 0))


def b4_escape():
    p = pi.panel("BoxPanel")
    h.wait_for(lambda: len(placing_boxes(p)) == 2, "the size boxes on the canvas")
    s["boxes"] = list(p.value_boxes.boxes.values())
    h.press(QtCore.Qt.Key_Escape)


b4_escape.done = pi.no_dialog
b4_escape.done_what = "Esc closed the Box dialog"


def b4_nothing():
    h.check("B4 Esc while placing leaves no body", len(bodies()) == s["count"],
            [b.Label for b in bodies()])
    shown = []
    for box in s["boxes"]:
        try:
            if box.isVisible():
                shown.append(box)
        except RuntimeError:
            pass  # (deleted: gone)
    h.check("B4 and no size box on the canvas", not shown, len(shown))


steps = (
    [b1_new, b1_plane, b1_corner, b1_boxes, b1_length, b1_width, b1_placed, b1_height, b1_done]
    + cylinder_at(60, 0, "33", "16")
    + [b2_first_done]
    + cylinder_at(60, 40, "20", "-8")
    + [b2_second_done, b3_face, b3_centre, b3_diameter, b3_up, b3_join, b3_cut]
    + [b4_undo, b4_redo, b4_box, b4_plane, b4_corner, b4_escape, b4_nothing]
)

h.run("book_extrude_primitives", steps, paced_by="state")
