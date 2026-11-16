# SPDX-License-Identifier: LGPL-2.1-or-later
"""Faces and bodies still light up under the mouse after a handle was dragged (Luca,
2026-11-16, on 0.1.0-beta.4.0.3: "the faces on bodies and whole bodies dont highlight when
hovering over them anymore").

While a handle is dragged FreeCAD's preselection is off (handles3d.hold_preselection, move-speed:
nothing lights under a dragged manipulator, and no ray is shot through the part on every
move). 0.1.0-beta.4.0.3 could not switch it on again: after the first drag of a Move arrow (or
any handle watched by handles3d.watch_release) nothing lit in that design until Fission 180 was
started again. Only real input; the highlight is read from FreeCAD's preselection, the
switch from the 3D view itself.

Box 40 x 30 x 10 from the origin.

  A  Before anything: the pointer on the top face lights it; off the part nothing is lit.
  B  M, click the body, press the X arrow and drag: while the button is down nothing is lit
     and the switch is off; let go: the switch is back as it was; the pointer on the body
     lights it, with the dialog still open. OK.
  C  After OK: the top face of the moved body lights; off the part nothing.
  D  M again, click the body, drag the Z arrow, let go, Esc: the face lights as before.
  E  Double-click the Move in the timeline, drag the X arrow twice, Cancel: it lights.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui, QtWidgets
from PySide6 import QtTest

from Fission180Tests.gui import bodies_steps as s
from Fission180Tests.gui import harness as h
from Fission180Tests.gui import selection_input as si

V = App.Vector
state = {}
AXES = [V(1, 0, 0), V(0, 1, 0), V(0, 0, 1)]


def body():
    return s.bodies()[0]


def mode():
    """The 3D view's preselection switch, as its name ("AUTO", "ON", "OFF"), read from the view
    itself (not through the code under test)."""
    value = Gui.ActiveDocument.ActiveView.getSceneGraph().getField("preselectionMode").get()
    return str(value.getString() if hasattr(value, "getString") else value)


def top():
    """A point on the body's top face, away from its middle (where the manipulator is)."""
    box = body().Shape.BoundBox
    return V(box.XMin + 0.2 * box.XLength, box.YMin + 0.25 * box.YLength, box.ZMax)


def hover(point):
    """The pointer onto a 3D point, coming from a pixel beside it (a hand's move)."""
    pos = h.screen_point(point)
    h.move(QtCore.QPoint(pos.x() + 3, pos.y()))
    h.move(pos)


def off_part():
    h.move(QtCore.QPoint(12, h.gl_widget().height() - 12))


def lights(tag):
    """The pointer on the top face lights something of the body; off the part nothing."""
    hover(top())
    h.wait_for(lambda: si.preselected() is not None, "%s: the top face to light" % tag, timeout_s=5)
    found = si.preselected()
    h.check("%s: the pointer on the top face lights it" % tag, found is not None, (found, mode()))
    off_part()
    h.wait_for(lambda: si.preselected() is None, "%s: nothing lit off the part" % tag, timeout_s=5)
    h.check("%s: off the part nothing is lit" % tag, si.preselected() is None, si.preselected())


def triad():
    return getattr(s.panel(), "triad", None)


def drag_arrow(tag, index, along):
    """Press arrow `index`, drag it `along` mm with the button held, look, let go, look."""
    t = triad()
    if not h.check("%s: the manipulator is shown" % tag, t is not None, s.panel()):
        return
    before = mode()
    widget = h.gl_widget()
    start = t.center + AXES[index] * (0.75 * t.size)
    a, b = h.screen_point(start), h.screen_point(start + AXES[index] * along)
    h.move(a)
    QtTest.QTest.mousePress(widget, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, a)
    for i in range(1, 9):
        pixel = QtCore.QPoint(a.x() + (b.x() - a.x()) * i // 8, a.y() + (b.y() - a.y()) * i // 8)
        event = QtGui.QMouseEvent(
            QtCore.QEvent.MouseMove,
            QtCore.QPointF(pixel),
            QtCore.QPointF(widget.mapToGlobal(pixel)),
            QtCore.Qt.NoButton,
            QtCore.Qt.LeftButton,
            QtCore.Qt.NoModifier,
        )
        QtWidgets.QApplication.sendEvent(widget, event)
        QtWidgets.QApplication.processEvents()
    h.wait_for(lambda: mode() == "OFF", "%s: the switch off while dragging" % tag, timeout_s=5)
    h.check("%s: while the arrow is dragged the switch is off" % tag, mode() == "OFF", mode())
    h.check("%s: ... and nothing is lit" % tag, si.preselected() is None, si.preselected())
    QtTest.QTest.mouseRelease(widget, QtCore.Qt.LeftButton, QtCore.Qt.NoModifier, b)
    QtWidgets.QApplication.processEvents()
    h.wait_for(lambda: mode() == before, "%s: the switch back after the release" % tag, timeout_s=5)
    h.check(
        "%s: let go: the switch is back as it was (%s)" % (tag, before),
        mode() == before and before != "OFF",
        (before, mode()),
    )


# -- A --------------------------------------------------------------------------------------------
def a_before():
    h.click_empty()
    h.fit()
    state["mode"] = mode()
    h.check("A: the hover highlight is on in a new design", state["mode"] in ("AUTO", "ON"), mode())
    lights("A")


# -- B --------------------------------------------------------------------------------------------
def b_move():
    h.press("m")


b_move.done = lambda: s.panel() is not None
b_move.done_what = "the Move/Copy dialog is open"


def b_pick():
    h.click(V(20, 15, 10))


b_pick.done = lambda: triad() is not None
b_pick.done_what = "the manipulator is shown"


def b_drag():
    drag_arrow("B", 0, 15)


def b_dialog_open():
    p = s.panel()
    h.check("B: the drag moved the body", p is not None and abs(p.options["dx"]) > 1.0, p)
    hover(top())
    h.wait_for(
        lambda: si.preselected() is not None, "B: the body to light, dialog open", timeout_s=5
    )
    h.check(
        "B: with the dialog still open the pointer on the body lights it",
        si.preselected() is not None,
        (si.preselected(), mode()),
    )
    off_part()
    h.task_button("OK")


b_dialog_open.done = lambda: s.panel() is None
b_dialog_open.done_what = "OK closed Move/Copy"


# -- C --------------------------------------------------------------------------------------------
def c_after_ok():
    h.check("C: one Move step", len(s.steps_of_kind("MoveCopy")) == 1)
    h.check("C: the switch is as at the start", mode() == state["mode"], (state["mode"], mode()))
    lights("C")


# -- D --------------------------------------------------------------------------------------------
def d_move():
    h.click_empty()
    h.press("m")


d_move.done = b_move.done
d_move.done_what = b_move.done_what


def d_pick():
    h.click(top())


d_pick.done = b_pick.done
d_pick.done_what = b_pick.done_what


def d_drag():
    drag_arrow("D", 2, 12)


def d_esc():
    h.press(QtCore.Qt.Key_Escape)


d_esc.done = lambda: s.panel() is None
d_esc.done_what = "Esc closed Move/Copy"


def d_after_esc():
    h.check("D: still one Move step", len(s.steps_of_kind("MoveCopy")) == 1)
    h.check("D: the switch is as at the start", mode() == state["mode"], (state["mode"], mode()))
    lights("D")


# -- E --------------------------------------------------------------------------------------------
def e_edit():
    s.timeline_double_click(s.steps_of_kind("MoveCopy")[0])


e_edit.done = lambda: triad() is not None
e_edit.done_what = "the Move is open again with its manipulator"


def e_drag_1():
    drag_arrow("E1", 0, 10)


def e_drag_2():
    drag_arrow("E2", 0, -6)


def e_cancel():
    h.task_button("Cancel")


e_cancel.done = lambda: s.panel() is None
e_cancel.done_what = "Cancel closed the Move"


def e_after_cancel():
    h.check("E: the switch is as at the start", mode() == state["mode"], (state["mode"], mode()))
    lights("E")


h.run(
    "hover_after_drag",
    [s.new_design("HoverAfterDrag")]
    + s.box_steps("body", (0, 0, 40, 30), 10, V(6, -6, 0))
    + [a_before]
    + [b_move, b_pick, b_drag, b_dialog_open]
    + [c_after_ok]
    + [d_move, d_pick, d_drag, d_esc, d_after_esc]
    + [e_edit, e_drag_1, e_drag_2, e_cancel, e_after_cancel],
    paced_by="state",
)
