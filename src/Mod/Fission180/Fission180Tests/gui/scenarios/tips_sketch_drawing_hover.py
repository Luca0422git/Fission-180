# SPDX-License-Identifier: LGPL-2.1-or-later
"""The expanded tooltips of the SKETCH, DRAWING and UTILITIES tabs (wave 8,
tips-sketch-drawing; texts fission180/tips/sketch.py, drawing.py, utilities.py), only real
input: the real pointer kept still on three ribbon buttons.

H1 A sketch open (the SKETCH tab): the pointer on CREATE's Line button shows its small tooltip
   (name, the sketch module's one line, its key L), then the expanded one with Line's picture
   (the PNG of fission180/icons/tips, 320 x 200, drawn on the screen), what it does, its steps
   and hints; the pointer into the view closes it.
H2 A drawing open (the DRAWING tab): Base View's button, the same, with its own texts and
   picture.
H3 The design's tab again, UTILITIES: 3D Print's button, the same.
"""

import os
import time

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtGui, QtWidgets

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import insert_steps as i
from Fission180Tests.gui import misc_steps as m

TOOLTIPS = "User parameter:BaseApp/Preferences/Mod/Fission180/Tooltips"
s = {}


def tips_ui():
    from fission180 import tips_ui as module

    return module


def mode():
    return tips_ui().state()["mode"]


def card():
    return tips_ui().card()


def button(label):
    name = "Fission180Big_" + label.replace(" ", "_")
    for b in h.ribbon_buttons():
        if b.objectName() == name and b.isVisible():
            return b
    return None


def hover(widget, pos=None):
    pos = widget.rect().center() if pos is None else pos
    h.pointer_to(widget, pos, fresh=True)


def wait_mode(want, what, timeout_s=None):
    h.wait_for(lambda: mode() == want, what, timeout_s)
    return time.monotonic()


def same_picture(label, path):
    """The card's picture is the PNG of the data module, and the screen shows it there."""
    pixmap = label.pixmap()
    if pixmap is None or pixmap.isNull() or not label.isVisible():
        return False
    want = QtGui.QImage(path).convertToFormat(QtGui.QImage.Format_RGB32)
    shown = pixmap.toImage().convertToFormat(QtGui.QImage.Format_RGB32)
    top = label.mapToGlobal(QtCore.QPoint(0, 0))
    screen = (
        QtWidgets.QApplication.primaryScreen()
        .grabWindow(0, top.x(), top.y(), label.width(), label.height())
        .toImage()
    )
    if (want.width(), want.height()) != (320, 200) or shown.size() != want.size():
        return False
    if screen.width() < 320 or screen.height() < 200:
        return False
    same = total = 0
    for x in range(5, 315, 15):
        for y in range(5, 195, 15):
            a = QtGui.QColor(want.pixel(x, y))
            b = QtGui.QColor(screen.pixel(x, y))
            c = QtGui.QColor(shown.pixel(x, y))
            total += 1
            close = max(
                abs(a.red() - b.red()), abs(a.green() - b.green()), abs(a.blue() - b.blue())
            )
            exact = max(
                abs(a.red() - c.red()), abs(a.green() - c.green()), abs(a.blue() - c.blue())
            )
            if close <= 12 and exact <= 2:
                same += 1
    return total > 0 and same >= 0.95 * total


def _gl():
    try:
        return h.gl_widget()
    except Exception:  # (a drawing's tab is active: no 3D view)
        return None


def _view_widget():
    """Where the pointer goes to leave the ribbon: the 3D view, or the drawing's sheet."""
    from fission180 import drawing_ui

    gl = _gl()
    if gl is not None and gl.isVisible():
        return gl
    page = drawing_ui.page_widget()
    if page is not None and page.isVisible():
        return page.viewport()
    return Gui.getMainWindow()


def expanded_steps(tag, label, command, module):
    """Steps: the pointer on the button, the small tooltip, the expanded one, the pointer away."""

    def small():
        from fission180 import tips

        b = button(label)
        h.check("%s the %s button is on the ribbon" % (tag, label), b is not None)
        if b is None:
            return
        s[tag] = tips.get(command)
        h.check(
            "%s %s has its tooltip in fission180/tips/%s.py" % (tag, label, module),
            bool(s[tag]) and tips.owner(command) == module,
            (tips.owner(command), s[tag]),
        )
        hover(b)
        wait_mode("small", "the small tooltip of %s" % label)
        c = card()
        h.check(
            "%s the small tooltip names %s" % (tag, label), c.title.text() == label, c.title.text()
        )
        h.check(
            "%s ... and says its one line" % tag,
            c.summary.isVisible() and c.summary.text() == s[tag]["summary"],
            c.summary.text(),
        )

    def expanded():
        if not s.get(tag):
            return
        wait_mode("expanded", "the expanded tooltip of %s" % label, timeout_s=10)
        c = card()
        tip = s[tag]
        path = tip.get("picture_path") or ""
        h.check(
            "%s its picture is %s" % (tag, tip["picture"]),
            os.path.basename(path) == tip["picture"] and os.path.isfile(path),
            path,
        )
        h.wait_for(
            lambda: same_picture(c.picture, path), "%s's picture to show on the screen" % label
        )
        h.check("%s what it does" % tag, c.what.isVisible() and c.what.text() == tip["what"])
        h.check(
            "%s its steps, numbered" % tag,
            c.steps.isVisible()
            and c.steps.text().split("\n")[0] == "1. " + tip["steps"][0]
            and len(c.steps.text().split("\n")) == len(tip["steps"]),
            c.steps.text(),
        )
        h.check(
            "%s its hints" % tag,
            c.hints.isVisible() == bool(tip["tips"])
            and all(t in c.hints.text() for t in tip["tips"]),
            c.hints.text(),
        )
        h.shot("%s-expanded" % tag.lower())

    expanded.timeout_s = 15

    def away():
        target = _view_widget()
        hover(target, QtCore.QPoint(target.width() // 2, target.height() // 2))
        wait_mode("", "the tooltip of %s to close" % label)
        h.check("%s the pointer away closes it" % tag, not card().isVisible())

    for step, name in ((small, "small"), (expanded, "expanded"), (away, "away")):
        step.__name__ = "%s_%s" % (tag.lower(), name)
    return [small, expanded, away]


# -- H1: a sketch open ---------------------------------------------------------------------------
def setup():
    from fission180 import commands, sketch_ui

    Gui.activateWorkbench("Fission180Workbench")
    App.ParamGet(TOOLTIPS).SetBool("Expanded", True)
    App.ParamGet(TOOLTIPS).SetInt("DelayMs", 1000)
    doc = App.newDocument("TipsSketch")
    body = commands.ensure_body()
    planes = sketch_ui.origin_planes(body)
    sk = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    doc.recompute()
    s["sketch"] = sk.Name
    Gui.ActiveDocument.setEdit(sk.Name)


def _sketch_open():
    from fission180 import sketch_mode

    return sketch_mode.current() is not None and button("Line") is not None


setup.done = _sketch_open
setup.done_what = "the sketch open with the SKETCH tab"


def finish_sketch():
    from fission180 import sketch_mode

    sketch_mode.finish_sketch()


finish_sketch.done = lambda: button("Line") is None
finish_sketch.done_what = "the sketch closed"


# -- H2: a drawing open --------------------------------------------------------------------------
def open_drawing():
    from fission180 import drawing, drawing_ui

    from Fission180Tests.gui import drawing_fixtures as fx

    doc = App.ActiveDocument
    fx.plate(doc)
    doc.recompute()
    page = drawing.create_drawing(doc, drawing.design_bodies(doc))
    doc.recompute()
    s["page"] = page.Name
    drawing_ui.open_drawing(page)


open_drawing.done = lambda: button("Base View") is not None
open_drawing.done_what = "the drawing open with the DRAWING tab"


def back_to_design():
    from fission180 import drawing_ui

    drawing_ui.show_design(App.ActiveDocument)


back_to_design.done = lambda: button("Base View") is None and _gl() is not None
back_to_design.done_what = "the design's tab again"


def utilities():
    i.ribbon_tab("UTILITIES")


utilities.done = lambda: button("3D Print") is not None
utilities.done_what = "the UTILITIES tab"


def cleanup():
    App.ParamGet(TOOLTIPS).RemBool("Expanded")
    App.ParamGet(TOOLTIPS).RemInt("DelayMs")
    m.close_all()
    h.new_errors()


h.run(
    "tips_sketch_drawing_hover",
    [setup]
    + expanded_steps("H1", "Line", "Fission180_SketchLine", "sketch")
    + [finish_sketch, open_drawing]
    + expanded_steps("H2", "Base View", "Fission180_DrawingBaseView", "drawing")
    + [back_to_design, utilities]
    + expanded_steps("H3", "3D Print", "Fission180_3DPrint", "utilities")
    + [cleanup],
    paced_by="state",
)
