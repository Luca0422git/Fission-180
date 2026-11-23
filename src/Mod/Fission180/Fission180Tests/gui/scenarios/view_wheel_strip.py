# SPDX-License-Identifier: LGPL-2.1-or-later
"""The mouse wheel zooms over the whole 3D view (Luca, 2026-11-23: "in the area circled red, i
cant zoom in and out with my scroll wheel. so when my cursor is anywhere else, it works": a
strip on the right of the view, from the ViewCube down).

The cause: FreeCAD's Tasks panel floats over the right of the 3D view (its "overlay"), empty
and see-through when no command is open, but it still took the mouse, so a wheel turn there
went to the empty panel. Now (shell.empty_panel_lets_mouse_through):
1. no command open: the strip is the 3D view's, for the wheel and the clicks;
2. a command's dialog open (Extrude): the dialog takes the mouse where it is (its OK button);
   a wheel turn on the panel's empty part below it zooms the 3D view (passed on to it);
3. the dialog closed: the whole strip is the 3D view's again.
What gets the wheel is the widget under the mouse (QApplication.widgetAt), as Qt sends it.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui, QtWidgets

from Fission180Tests.gui import harness as h

s = {}
STRIP = ((0.85, 0.45), (0.9, 0.7), (0.96, 0.92))  # (of the view's width, height)


def view_point(fx, fy):
    gl = h.gl_widget()
    corner = gl.mapToGlobal(QtCore.QPoint(0, 0))
    return QtCore.QPoint(corner.x() + int(gl.width() * fx), corner.y() + int(gl.height() * fy))


def under(point):
    return QtWidgets.QApplication.widgetAt(point)


def is_view(widget):
    return widget is not None and widget is h.gl_widget()


def strip_is_view():
    return all(is_view(under(view_point(fx, fy))) for fx, fy in STRIP)


def name(widget):
    return widget.metaObject().className() if widget is not None else None


def setup():
    App.newDocument("WheelStrip")
    from fission180 import commands, sketch_ui

    body = commands.ensure_body()
    planes = sketch_ui.origin_planes(body)
    s["sketch"] = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    h.draw_rectangle(s["sketch"], 0, 0, 40, 30)
    App.ActiveDocument.recompute()
    Gui.Selection.clearSelection()
    h.fit()


setup.done = strip_is_view
setup.done_what = "the right of the 3D view to be the view's (no command open)"


def no_command():
    for fx, fy in STRIP:
        widget = under(view_point(fx, fy))
        h.check(
            "no command: the wheel at %.2f, %.2f goes to the 3D view" % (fx, fy),
            is_view(widget),
            name(widget),
        )


def open_extrude():
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(App.ActiveDocument.Name, s["sketch"].Name)
    Gui.runCommand("Fission180_Extrude")


def _ok_button():
    for button in Gui.getMainWindow().findChildren(QtWidgets.QPushButton):
        if button.isVisible() and button.text().replace("&", "").strip().upper() == "OK":
            return button
    return None


def _below_dialog():
    """(the point, the panel's empty part under it) at the bottom right of the view."""
    point = view_point(0.9, 0.97)
    return point, under(point)


def _dialog_ready():
    from fission180 import shell

    forward = shell._state.get("panel_forward")
    _point, widget = _below_dialog()
    return (
        bool(Gui.Control.activeDialog())
        and _ok_button() is not None
        and forward is not None
        and any(w is widget for w in forward.watched)
    )


open_extrude.done = _dialog_ready
open_extrude.done_what = "the Extrude dialog to open over an empty panel part below it"


def dialog_open():
    button = _ok_button()
    centre = button.mapToGlobal(button.rect().center())
    widget = under(centre)
    h.check(
        "the dialog's OK button still takes the mouse",
        widget is button or (widget is not None and button.isAncestorOf(widget)),
        name(widget),
    )


def wheel_below_dialog():
    """A wheel turn as Qt gives it to the widget under the mouse: the panel's empty part."""
    point, widget = _below_dialog()
    s["camera"] = Gui.ActiveDocument.ActiveView.getCamera()
    turn = QtGui.QWheelEvent(
        QtCore.QPointF(widget.mapFromGlobal(point)),
        QtCore.QPointF(point),
        QtCore.QPoint(0, 0),
        QtCore.QPoint(0, 120),
        QtCore.Qt.NoButton,
        QtCore.Qt.NoModifier,
        QtCore.Qt.NoScrollPhase,
        False,
    )
    QtWidgets.QApplication.sendEvent(widget, turn)


wheel_below_dialog.done = lambda: Gui.ActiveDocument.ActiveView.getCamera() != s["camera"]
wheel_below_dialog.done_what = "a wheel turn below the dialog to zoom the 3D view"


def zoomed():
    h.check("below the dialog the wheel zoomed the 3D view", True)
    h.check("the dialog is still open", bool(Gui.Control.activeDialog()))


def close_dialog():
    Gui.Control.closeDialog()


close_dialog.done = lambda: not Gui.Control.activeDialog() and strip_is_view()
close_dialog.done_what = "the dialog to close and the strip to be the view's again"


def closed():
    h.check("after the dialog: the whole strip is the 3D view's", strip_is_view())


h.run(
    "view_wheel_strip",
    [setup, no_command, open_extrude, dialog_open, wheel_below_dialog, zoomed, close_dialog, closed],
    paced_by="state",
)
