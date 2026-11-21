# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights showcase (plan task A8, extended in C2): screenshots of the main surfaces in a few
presets, for Luca to look at. Not a check of colours (the other neon_* scenarios do that): it
fails only if a step fails. FISSION180_SHOWCASE_OUT=<folder> also copies the pictures there.

Each preset: the design with the CREATE drop-down open, the Extrude dialog, sketch mode.
"""

import os
import shutil

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtWidgets

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import look_compare as lc

PRESETS = [p for p in os.environ.get("FISSION180_SHOWCASE_PRESETS", "v,johnny").split(",") if p]
OUT = os.environ.get("FISSION180_SHOWCASE_OUT", "")
s = {}


def keep(label):
    """A screenshot of the whole screen (menus included), also copied to OUT."""
    h.shot(label)
    if OUT:
        os.makedirs(OUT, exist_ok=True)
        name = "neon_showcase-%s.png" % label
        source = os.path.join(h.OUT_DIR, name)
        if os.path.isfile(source):
            shutil.copy(source, os.path.join(OUT, name))


def setup():
    lc.setup()
    lc.set_look("neon")


def make_round(preset):
    def choose():
        from fission180 import neon_settings, preferences_ui

        neon_settings.put("Preset", preset)
        preferences_ui._apply("neon")
        QtWidgets.QApplication.processEvents()
        Gui.Selection.clearSelection()

    def window():
        h.view_drawn()
        keep("%s-window" % preset)

    def menu():
        label = lc.group_label("create")
        if label is None:
            h.check("CREATE's drop-down is there", False)
            return

        def read(shown):
            h.wait_for(lambda: shown.windowOpacity() > 0.99, "the menu to fade in")
            keep("%s-menu" % preset)

        h.choose_from(label.click, [], "CREATE's drop-down", read=read)
        h.wait_for(lambda: h.open_menu() is None, "the menu to close")

    def extrude_open():
        Gui.Selection.clearSelection()
        Gui.Selection.addSelection(App.ActiveDocument.Name, lc.s["sketch2"].Name)
        Gui.runCommand("Fission180_Extrude")

    extrude_open.done = lc.task_open
    extrude_open.done_what = "the Extrude dialog to open"

    def extrude_shown():
        h.caught_up(what="the Extrude dialog's preview")
        h.view_drawn()
        keep("%s-extrude" % preset)

    def extrude_closed():
        h.task_button("Cancel")
        Gui.Selection.clearSelection()

    extrude_closed.done = lambda: not lc.task_open()
    extrude_closed.done_what = "the Extrude dialog to close"

    steps = [choose, window, menu, extrude_open, extrude_shown, extrude_closed]
    for step in steps:
        step.__name__ = "%s_%s" % (preset, step.__name__)
    return steps


def back_to_dark():
    lc.set_look("dark")


steps = [setup]
for _preset in PRESETS:
    steps += make_round(_preset)
steps.append(back_to_dark)
h.run("neon_showcase", steps, paced_by="state")
