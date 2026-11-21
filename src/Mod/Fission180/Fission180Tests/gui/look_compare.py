# SPDX-License-Identifier: LGPL-2.1-or-later
"""Pictures of the window compared with the ones taken before the Neon Lights work
(Fission180Tests/fixtures/look_baseline/): used by look_unchanged and neon_switch to prove Dark
and Light look exactly as before (neon-lights-design.md 6.11). FISSION180_RECORD_LOOK=1
records instead."""

import contextlib
import os

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtGui, QtWidgets

from Fission180Tests.gui import harness as h

HERE = os.path.dirname(os.path.abspath(__file__))
BASELINE = os.path.join(os.path.dirname(HERE), "fixtures", "look_baseline")
RECORD = os.environ.get("FISSION180_RECORD_LOOK") == "1"
TOLERANCE = 8  # of 255, in any channel
SHARE = 0.002  # of the pixels
s = {}


def _differing(a, b):
    """Share of pixels of two same-size images that differ by more than TOLERANCE."""
    a = a.convertToFormat(QtGui.QImage.Format_RGB32)
    b = b.convertToFormat(QtGui.QImage.Format_RGB32)
    width, height = a.width(), a.height()
    bits_a = bytes(a.constBits())[: a.sizeInBytes()]
    bits_b = bytes(b.constBits())[: b.sizeInBytes()]
    stride = a.bytesPerLine()
    bad = 0
    for y in range(height):
        row = y * stride
        for x in range(0, width * 4, 4):
            i = row + x
            if (
                abs(bits_a[i] - bits_b[i]) > TOLERANCE
                or abs(bits_a[i + 1] - bits_b[i + 1]) > TOLERANCE
                or abs(bits_a[i + 2] - bits_b[i + 2]) > TOLERANCE
            ):
                bad += 1
    return bad / float(max(1, width * height))


def compare(name, image):
    """Record or compare one picture."""
    path = os.path.join(BASELINE, name + ".png")
    if RECORD:
        os.makedirs(BASELINE, exist_ok=True)
        image.save(path)
        h.check("recorded %s" % name, os.path.isfile(path), path)
        return
    saved = QtGui.QImage(path)
    if saved.isNull():
        h.check("%s: a baseline exists" % name, False, path)
        return
    if saved.size() != image.size():
        h.check("%s: same size as before" % name, False, (saved.size(), image.size()))
        return
    share = _differing(saved, image)
    if share > SHARE:
        image.save(os.path.join(h.OUT_DIR, "look_unchanged-%s-now.png" % name))
    h.check("%s looks as before" % name, share <= SHARE, "%.4f%% of pixels differ" % (share * 100))


@contextlib.contextmanager
def no_effects():
    """Neon Lights' screen effects (scan lines, corner shade, glow) hidden while a test samples
    colours from the window's or a 3D view's picture; nothing else changes (no setting, no
    repaint of the window). Outside Neon Lights it does nothing."""
    try:
        from fission180 import neon_effects
    except Exception:
        neon_effects = None
    if neon_effects is None or (neon_effects.overlay() is None and not neon_effects.view_parts()):
        yield
        return
    with neon_effects.hidden_for_sampling():
        yield


def grab(widget, rect=None):
    """widget.grab() (of `rect`) as a person sees the widget, without the screen effects: use it
    for the main window and the 3D view when a check samples colours."""
    with no_effects():
        return widget.grab() if rect is None else widget.grab(rect)


def window_image():
    return grab(Gui.getMainWindow()).toImage()


def set_look(name):
    from fission180 import preferences_ui, theme

    if theme.current() != name or theme.name() != name:
        preferences_ui.save({"theme": name})
    QtWidgets.QApplication.processEvents()


def group_label(group_id):
    from fission180 import ribbon_ui, shell

    for widget in shell.ribbon().findChildren(ribbon_ui.GroupWidget):
        if widget.group["id"] == group_id and widget.isVisible():
            return widget.label
    return None


def task_open():
    return bool(Gui.Control.activeDialog())


# -- the design ---------------------------------------------------------------------------
def setup():
    """The design every picture shows (its name is in the document tab)."""
    Gui.activateWorkbench("Fission180Workbench")
    set_look("dark")
    App.newDocument("LookUnchanged")
    from fission180 import commands, extrude, sketch_ui

    body = commands.ensure_body()
    planes = sketch_ui.origin_planes(body)
    sk = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    h.draw_rectangle(sk, 0, 0, 40, 30)
    extrude.make(body, sk, {"distance": 10.0})
    s["sketch2"] = sketch_ui.create_sketch(body, (planes["XY_Plane"], ""))
    h.draw_rectangle(s["sketch2"], 50, 0, 20, 20)
    App.ActiveDocument.recompute()
    Gui.Selection.clearSelection()
    h.fit()


def make_round(look, prefix=""):
    """The steps of one round in `look` (step names start with `prefix`)."""

    def to_look():
        set_look(look)

    def window():
        h.view_drawn()
        compare("%s-window" % look, window_image())

    def menu():
        label = group_label("create")
        h.check("CREATE's drop-down is there", label is not None)
        if label is None:
            return

        def read(shown):
            compare("%s-menu" % look, shown.grab().toImage())

        h.choose_from(label.click, [], "CREATE's drop-down", read=read)
        h.wait_for(lambda: h.open_menu() is None, "the menu to close")

    def extrude_open():
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(App.ActiveDocument.Name, s["sketch2"].Name)
        Gui.runCommand("Fission180_Extrude")

    extrude_open.done = task_open
    extrude_open.done_what = "the Extrude dialog to open"

    def extrude_shown():
        h.caught_up(what="the Extrude dialog's preview")
        h.view_drawn()
        compare("%s-extrude" % look, window_image())

    def extrude_closed():
        h.task_button("Cancel")
        Gui.Selection.clearSelection()

    extrude_closed.done = lambda: not task_open()
    extrude_closed.done_what = "the Extrude dialog to close"

    for step in (to_look, window, menu, extrude_open, extrude_shown, extrude_closed):
        step.__name__ = "%s%s_%s" % (prefix, look, step.__name__)
    return [to_look, window, menu, extrude_open, extrude_shown, extrude_closed]
