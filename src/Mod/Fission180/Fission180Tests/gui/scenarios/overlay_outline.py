# SPDX-License-Identifier: LGPL-2.1-or-later
"""No outline of FreeCAD's right overlay panel over the 3D view, checked on the screen itself.

docs/fission180/known-issues.md listed "A thin outline frame on the right": while a panel was
open at the right (the AI panel, the Sketch Palette, a command's dialog), a thin empty
rectangle could show over the 3D view next to it. It was the 1-pixel frame of FreeCAD's
Tasks area, which FreeCAD keeps over the view (its right "overlay") even with nothing in
it; 0.1.0-beta.3.3.5 took that frame away (theme.py; ribbon_luca_linux checks its width).

Here the pixels say it: in each state below, once FreeCAD has placed its overlay again
(it does so 200 ms after the window's layout changes), a screen grab with the overlay and
one with the overlay hidden may differ only where the dialog's own boxes and buttons are.
A control first takes theme.py's rule out of the style sheet (the Tasks area gets its 1-pixel
frame back, as before 3.3.5): the same comparison must see that outline.

  A  the AI panel open on a new design (the empty overlay sits in the view beside it);
     the control
  B  the AI panel closed again
  C  a sketch: the Sketch Palette; then the AI panel opened beside it
  D  Extrude's dialog; then the AI panel opened beside it; then Cancel
Screen grabs: overlay_outline-<state>.png (with the overlay), to look at by eye.
"""

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import plane_input as pl

s = {}
# the overlay's own layers: anything else in it is a dialog's content
CONTAINERS = {
    "Gui::OverlayTabWidget",
    "QStackedWidget",
    "Gui::OverlaySplitter",
    "QDockWidget",
    "Gui::TaskView::TaskView",
    "QScrollArea",
    "Gui::TaskView::TaskPanel",
    "Gui::OverlayTitleBar",
    "Gui::OverlayToolButton",
    "QScrollBar",
}


def overlay():
    for w in Gui.getMainWindow().findChildren(QtWidgets.QWidget):
        if (
            w.metaObject().className() == "Gui::OverlayTabWidget"
            and w.objectName() == "OverlayRight"
        ):
            return w
    return None


def placed():
    """FreeCAD has placed its right overlay against the 3D view's right edge again."""
    main = Gui.getMainWindow()
    o, gl = overlay(), h.gl_widget()
    if o is None or gl is None or not o.isVisible():
        return True
    right = o.mapTo(main, QtCore.QPoint(o.width(), 0)).x()
    view_right = gl.mapTo(main, QtCore.QPoint(gl.width(), 0)).x()
    return abs(right - view_right) <= 2


def content(o):
    """Screen rectangles of what a dialog shows in the overlay (its boxes, its buttons)."""
    found = []
    for w in o.findChildren(QtWidgets.QWidget):
        name = w.metaObject().className()
        if not w.isVisible() or name in CONTAINERS or w.objectName() == "qt_scrollarea_viewport":
            continue
        if (
            name == "QWidget"
            and w.parentWidget() is not None
            and (w.parentWidget().metaObject().className() == "QStackedWidget")
        ):
            continue  # (the overlay's tab page)
        corner = w.mapToGlobal(QtCore.QPoint(0, 0))
        found.append(QtCore.QRect(corner.x() - 2, corner.y() - 2, w.width() + 4, w.height() + 4))
    return found


def grab():
    return QtWidgets.QApplication.primaryScreen().grabWindow(0).toImage()


def stray_pixels(label):
    """Pixels the overlay paints outside its dialog's content: [(x, y)] (none when nothing
    shows of an empty overlay). Also saves the screen grab."""
    o = overlay()
    if o is None or not o.isVisible():
        return []
    h.shot(label)
    with_it = grab()
    corner = o.mapToGlobal(QtCore.QPoint(0, 0))
    boxes = content(o)
    o.hide()
    QtWidgets.QApplication.processEvents()
    without = grab()
    o.show()
    QtWidgets.QApplication.processEvents()
    found = []
    for y in range(max(0, corner.y() - 3), min(with_it.height(), corner.y() + o.height() + 3)):
        for x in range(max(0, corner.x() - 3), min(with_it.width(), corner.x() + o.width() + 3)):
            if with_it.pixel(x, y) != without.pixel(x, y) and not any(
                b.contains(x, y) for b in boxes
            ):
                found.append((x, y))
    return found


def no_outline(label, what):
    found = stray_pixels(label)
    h.check(
        "no outline of FreeCAD's right panel: %s" % what,
        not found,
        "%d pixels differ, first %s" % (len(found), found[:8]),
    )


def ai_panel(show):
    from fission180 import ai_panel_ui

    if ai_panel_ui.is_shown() != show:
        ai_panel_ui.toggle()


# -- A ---------------------------------------------------------------------------------------
def new_design():
    App.newDocument("Outline")
    Gui.activateWorkbench("Fission180Workbench")
    h.fit()


def open_ai():
    ai_panel(True)


open_ai.done = placed
open_ai.done_what = "FreeCAD's right panel placed beside the AI panel"


def a_check():
    h.check(
        "FreeCAD keeps its right panel over the view (what could show)",
        overlay() is not None and overlay().isVisible(),
    )
    no_outline("ai", "beside the AI panel")


RULE = "Gui--TaskView--TaskView > QScrollArea"  # theme.py's rule: no frame on the Tasks area


def a_control():
    """The control: the style sheet without the 3.3.5 rule (as before 3.3.5): the Tasks area
    gets its 1-pixel frame back, and the comparison must see it."""
    app = QtWidgets.QApplication.instance()
    s["qss"] = app.styleSheet()
    h.check("the theme takes the frame off the Tasks area", RULE in s["qss"])
    app.setStyleSheet(s["qss"].replace(RULE, "Gui--TaskView--NotTheTaskView > QScrollArea"))


a_control.done = placed
a_control.done_what = "the style sheet applied again"


def a_control_seen():
    found = stray_pixels("control")
    o = overlay()
    edge = 2 * (o.width() + o.height()) if o is not None else 0
    h.check(
        "control: with its frame back, the outline is seen (%d pixels)" % len(found),
        len(found) > edge // 2,
        (len(found), edge, found[:4]),
    )
    QtWidgets.QApplication.instance().setStyleSheet(s["qss"])


a_control_seen.done = placed
a_control_seen.done_what = "the theme's style sheet back"


# -- B ---------------------------------------------------------------------------------------
def close_ai():
    ai_panel(False)


close_ai.done = placed
close_ai.done_what = "FreeCAD's right panel placed against the view's edge"


def b_check():
    no_outline("noai", "with the AI panel closed")


# -- C ---------------------------------------------------------------------------------------
def create_sketch():
    h.ribbon("Create Sketch")


def pick_xy():
    pl.click_square("XY_Plane")


pick_xy.done = lambda: h.in_sketch() is not None and placed()
pick_xy.done_what = "a sketch open on XY with its palette"


def c_draw():
    sk = h.in_sketch()
    h.draw_rectangle(sk, -30, -18, 30, 18)
    App.ActiveDocument.recompute()


def c_palette():
    no_outline("sketch", "beside the Sketch Palette")


def c_ai():
    ai_panel(True)


c_ai.done = placed
c_ai.done_what = "the Sketch Palette placed beside the AI panel"


def c_check():
    no_outline("sketch_ai", "the Sketch Palette beside the AI panel")


def c_finish():
    ai_panel(False)
    h.ribbon("Finish Sketch")


c_finish.done = lambda: h.in_sketch() is None and placed()
c_finish.done_what = "the sketch finished"


# -- D ---------------------------------------------------------------------------------------
def d_extrude():
    sketch = [o for o in App.ActiveDocument.Objects if o.TypeId == "Sketcher::SketchObject"][0]
    Gui.Selection.clearSelection()
    Gui.Selection.addSelection(sketch)
    h.ribbon("Extrude")


d_extrude.done = lambda: Gui.Control.activeDialog() and placed()
d_extrude.done_what = "Extrude's dialog open"


def d_check():
    no_outline("extrude", "beside Extrude's dialog")


def d_ai():
    ai_panel(True)


d_ai.done = placed
d_ai.done_what = "Extrude's dialog placed beside the AI panel"


def d_check_ai():
    no_outline("extrude_ai", "Extrude's dialog beside the AI panel")
    Gui.Control.closeDialog()


d_check_ai.done = lambda: not Gui.Control.activeDialog() and placed()
d_check_ai.done_what = "Extrude's dialog closed"


def d_after():
    no_outline("after", "after Extrude's dialog closed, beside the AI panel")
    ai_panel(False)


h.run(
    "overlay_outline",
    [
        new_design,
        open_ai,
        a_check,
        a_control,
        a_control_seen,
        close_ai,
        b_check,
        create_sketch,
        pick_xy,
        c_draw,
        c_palette,
        c_ai,
        c_check,
        c_finish,
        d_extrude,
        d_check,
        d_ai,
        d_check_ai,
        d_after,
    ],
    paced_by="state",
)
