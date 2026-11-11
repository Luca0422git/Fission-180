# SPDX-License-Identifier: LGPL-2.1-or-later
"""The body patterns' drag handles and their Bodies default (Luca, 2026-11-09: "when working
with bodies, selections should always default to body. the pattern tools default to
feature" and "rectangular has arrows to change spacing, circular has angle dragger that
changes the spacing and how far you want it to revolve (360, 90, 180, etc)").

A 40 x 30 x 10 box (sketch, rectangle, E 10, OK).

R  Rectangular Pattern from the ribbon: Pattern Type Bodies. A click on the box's top face
   takes its body (not a feature). Direction: the X axis: a copy body. The arrow dragged
   10 mm on: the Distance in the panel follows and so does the copy. 50 typed: the arrow
   moves to 50. Quantity 3 (Extent 50: copies at 25 and 50). Distance Type Spacing: copies
   at 50 and 100; the arrow (at the first copy) dragged 20 mm back: Spacing about 30, the
   copies follow. 30 typed. OK: two copy bodies 30 apart; one undo step.
C  Circular Pattern from the ribbon: Pattern Type Bodies; the box clicked, the Z axis: Full,
   3 copies. The angle disc shows in Full too, at 360. Dragged round to 180: Type Angle,
   Total Angle 180 (the snap) in the panel; the copies turned 90 and 180. 90 typed: the disc
   moves to 90. Mirror and Pattern on Path start with Bodies too. Cancel / Esc.
"""

import math

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore

from Fission180Tests.gui import blend_steps as b
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import plane_input as pl
from Fission180Tests.gui import pattern_steps as ps

V = App.Vector
s = {}


def copies():
    """The copy bodies (every body but the first), by their lowest X."""
    found = [x for x in ps.bodies() if x.Name != "Body"]
    return sorted(found, key=lambda x: x.Shape.BoundBox.XMin)


def boxes():
    out = []
    for body in copies():
        bb = body.Shape.BoundBox
        out.append((round(bb.XMin, 3), round(bb.YMin, 3), round(bb.XMax, 3), round(bb.YMax, 3)))
    return sorted(out)


# -- R: Rectangular Pattern of the body -----------------------------------------------------------
def r_start():
    Gui.Selection.clearSelection()
    s["undo"] = App.ActiveDocument.UndoCount
    h.ribbon("Rectangular Pattern")


def r_waiting():
    p = ps.panel()
    h.check("R: Rectangular Pattern dialog open", p is not None and p.kind == "rectangular")
    h.check("R: Pattern Type starts as Bodies", p and p.pattern_type.currentText() == "Bodies",
            p and p.pattern_type.currentText())
    h.check("R: the hint asks for the body", p and "body" in p.info.text().lower(), p and p.info.text())
    h.fit()


def r_click_box():
    h.click(V(30, 20, 10))


def r_body_picked():
    p = ps.panel()
    objs = p.options["objects"] if p else []
    h.check("R: a click on a face takes the whole body", len(objs) == 1 and objs[0][0].TypeId == "PartDesign::Body"
            and objs[0][1] == "", objs)
    ps.click_box("direction")


def r_x_axis():
    h.fit()
    pl.click_on_plane(V(-12, 0, 0))


def r_preview():
    p = ps.panel()
    h.check("R: a copy body previewed", len(copies()) == 1, [x.Label for x in ps.bodies()])
    h.check("R: an arrow for the X direction", p and "distance" in p.handles, p and list(p.handles))
    s["d0"] = p.options["distance"] if p else 0
    h.shot("R-preview")


def r_drag():
    ps.drag_arrow("distance", 10.0)


def r_dragged():
    p = ps.panel()
    value = p.distance_field.value()
    h.check("R: the arrow dragged 10 mm on adds about 10 to the Distance", 8.5 < value - s["d0"] < 11.5,
            (s["d0"], value))
    # (the field keeps two decimals; the arrow stays where the hand let it go)
    h.check("R: the arrow stands at the Distance", abs(p.handles["distance"].distance() - value) < 0.006,
            (p.handles["distance"].distance(), value))
    h.caught_up(p)
    found = boxes()
    h.check("R: the copy body follows the dragged Distance", found and abs(found[0][0] - value) < 1e-3,
            (found, value))


def r_type_50():
    ps.type_value(ps.panel().distance_field.widget, "50")


def r_typed_50():
    p = ps.panel()
    h.check("R: 50 typed moves the arrow", abs(p.handles["distance"].distance() - 50.0) < 1e-6,
            p.handles["distance"].distance())


def r_quantity_3():
    ps.type_quantity(ps.panel().quantity, 3)


def r_three():
    h.caught_up(ps.panel())
    found = boxes()
    h.check("R: Extent 50, 3: copies at 25 and 50", [f[0] for f in found] == [25.0, 50.0], found)


def r_spacing():
    b.choose(ps.panel().distribution, "Spacing")


def r_spaced():
    p = ps.panel()
    h.caught_up(p)
    found = boxes()
    h.check("R: Spacing 50: copies at 50 and 100", [f[0] for f in found] == [50.0, 100.0], found)
    h.check("R: the arrow stands at the first copy (the Spacing)",
            abs(p.handles["distance"].distance() - 50.0) < 1e-6, p.handles["distance"].distance())


def r_drag_back():
    ps.drag_arrow("distance", -20.0)


def r_dragged_back():
    p = ps.panel()
    value = p.distance_field.value()
    h.check("R: dragged 20 mm back: Spacing about 30", 28.5 < value < 31.5, value)
    h.caught_up(p)
    found = boxes()
    h.check("R: the copies follow the dragged Spacing",
            len(found) == 2 and abs(found[0][0] - value) < 1e-3 and abs(found[1][0] - 2 * value) < 1e-3,
            (found, value))
    h.shot("R-dragged")


def r_type_30():
    ps.type_value(ps.panel().distance_field.widget, "30")


def r_ok():
    h.task_button("OK")


def r_made():
    h.settle("the pattern")
    found = boxes()
    h.check("R: two copy bodies exactly 30 apart",
            found == [(30.0, 0.0, 70.0, 30.0), (60.0, 0.0, 100.0, 30.0)], found)
    names = list(App.ActiveDocument.UndoNames)
    h.check("R: the dialog closed", not Gui.Control.activeDialog())
    h.check("R: one undo step", App.ActiveDocument.UndoCount == s["undo"] + 1,
            (App.ActiveDocument.UndoCount, s["undo"], names[:3]))


def r_undo():
    h.press("z", QtCore.Qt.ControlModifier)


def r_undone():
    h.settle("the undo")
    h.check("R: Ctrl+Z takes both copies back", not copies(), [x.Label for x in ps.bodies()])


# -- C: Circular Pattern of the body ----------------------------------------------------------------
def c_start():
    Gui.Selection.clearSelection()
    ps.menu("Circular Pattern")


def c_waiting():
    p = ps.panel()
    h.check("C: Circular Pattern dialog open", p is not None and p.kind == "circular")
    h.check("C: Pattern Type starts as Bodies", p and p.pattern_type.currentText() == "Bodies")
    h.fit()


def c_click_box():
    h.click(V(30, 20, 10))


def c_axis_box():
    p = ps.panel()
    objs = p.options["objects"] if p else []
    h.check("C: the body is the object", len(objs) == 1 and objs[0][0].TypeId == "PartDesign::Body", objs)
    ps.click_box("axis")


def c_z_axis():
    h.fit()
    pl.click_on_plane(V(0, 0, 22))


def c_full():
    p = ps.panel()
    h.caught_up(p)
    h.check("C: Full, 3: two copy bodies", len(copies()) == 2, [x.Label for x in ps.bodies()])
    handle = p.handles.get("angle") if p else None
    h.check("C: the angle disc shows in Full too", handle is not None, p and list(p.handles))
    h.check("C: at 360", handle is not None and abs(handle.angle() - 360.0) < 1e-3, handle and handle.angle())
    h.shot("C-full")


def c_drag_180():
    p = ps.panel()
    handle = p.handles.get("angle") if p else None
    if h.check("C: the disc to drag", handle is not None):
        ps.drag_turn(handle, 360.0, 180.0)


def c_at_180():
    p = ps.panel()
    h.check("C: dragged off 360: Type Angle", p.circular_type.currentText() == "Angle",
            p.circular_type.currentText())
    h.check("C: Total Angle 180 in the panel (the snap)", abs(p.angle_field.value() - 180.0) < 1e-9,
            p.angle_field.value())
    h.check("C: the Total Angle field shows", p.angle_field.widget.isVisible())
    h.caught_up(p)
    found = boxes()
    # the 40 x 30 box turned 90 deg: x -30..0, y 0..40; 180 deg: x -40..0, y -30..0
    h.check("C: the copies turned 90 and 180",
            found == [(-40.0, -30.0, 0.0, 0.0), (-30.0, 0.0, 0.0, 40.0)], found)
    h.shot("C-180")


def c_type_90():
    ps.type_value(ps.panel().angle_field.widget, "90")


def c_typed_90():
    p = ps.panel()
    handle = p.handles.get("angle")
    h.check("C: 90 typed moves the disc", handle is not None and abs(handle.angle() - 90.0) < 1e-3,
            handle and handle.angle())


def c_full_again():
    b.choose(ps.panel().circular_type, "Full")


def c_full_disc():
    p = ps.panel()
    h.caught_up(p)
    handle = p.handles.get("angle")
    h.check("C: Full again: the disc back at 360", handle is not None and abs(handle.angle() - 360.0) < 1e-3,
            handle and handle.angle())
    h.task_button("Cancel")


def c_cancelled():
    h.settle("Cancel")
    h.check("C: Cancel: no copies", not copies())


def m_start():
    h.ribbon("Mirror")


def m_bodies():
    p = ps.panel()
    h.check("M: Mirror starts with Pattern Type Bodies", p and p.pattern_type.currentText() == "Bodies")
    h.press(QtCore.Qt.Key_Escape)


def p_start():
    h.settle("Esc")
    ps.menu("Pattern on Path")


def p_bodies():
    p = ps.panel()
    h.check("P: Pattern on Path starts with Pattern Type Bodies", p and p.pattern_type.currentText() == "Bodies")
    h.press(QtCore.Qt.Key_Escape)


def end():
    h.settle("Esc")
    h.check("nothing left open", not Gui.Control.activeDialog())
    h.check("no copies left", not copies())


h.run(
    "pattern_handles_bodies",
    b.box_steps("PatternHandles")
    + [
        r_start, r_waiting, r_click_box, r_body_picked, r_x_axis, r_preview, r_drag, r_dragged,
        r_type_50, r_typed_50, r_quantity_3, r_three, r_spacing, r_spaced, r_drag_back,
        r_dragged_back, r_type_30, r_ok, r_made, r_undo, r_undone,
        c_start, c_waiting, c_click_box, c_axis_box, c_z_axis, c_full, c_drag_180, c_at_180,
        c_type_90, c_typed_90, c_full_again, c_full_disc, c_cancelled,
        m_start, m_bodies, p_start, p_bodies, end,
    ],
    paced_by="state",
)
