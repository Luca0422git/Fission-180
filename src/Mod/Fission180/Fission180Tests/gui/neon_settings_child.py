# SPDX-License-Identifier: LGPL-2.1-or-later
"""The second FreeCAD of scenario neon_settings (scenarios/neon_settings.py starts it with a
copy of its profile after saving the colour set "Mine"; not a scenario of its own).

A real restart: this FreeCAD read the copied user.cfg when it started. It must open in Neon
Lights with Mine's colours, and Preferences > Neon Lights must show "Mine" chosen and
"Custom (based on Johnny)"."""

import os

from PySide import QtCore, QtWidgets

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import widget_input as wi

MINE = {"primary": "#00ff88", "outline": "#ff00ff"}


def preferences():
    for w in QtWidgets.QApplication.topLevelWidgets():
        if w.objectName() == "Fission180Preferences" and w.isVisible():
            return w
    return None


def started():
    from fission180 import neon, neon_palette, neon_settings, theme

    h.check("the look after the restart is Neon Lights", theme.is_neon() and neon.active(), theme.name())
    h.check("... preset Johnny with the own colours", neon_settings.get("Preset") == "johnny"
            and neon_settings.custom() == MINE, (neon_settings.get("Preset"), neon_settings.custom()))
    chrome = neon_palette.derive(neon_palette.roles("johnny", MINE))["chrome"]
    h.check("... the window has Mine's colours", chrome in QtWidgets.QApplication.instance().styleSheet())


def open_preferences():
    import FreeCADGui as Gui

    Gui.runCommand("Fission180_Preferences")


open_preferences.done = lambda: preferences() is not None
open_preferences.done_what = "the Preferences to open"


def open_neon_page():
    tree = preferences().findChild(QtWidgets.QTreeWidget, "Fission180PreferencesPages")

    def row():
        found = tree.findItems("Neon Lights", QtCore.Qt.MatchExactly | QtCore.Qt.MatchRecursive)
        return found[0] if found else None

    wi.click_item(tree, row, what="the Neon Lights page")


open_neon_page.done = lambda: preferences() is not None and preferences().current_page() == "neon"
open_neon_page.done_what = "the Neon Lights page to show"


def mine_chosen():
    page = getattr(preferences(), "neon", None)
    line = preferences().findChild(QtWidgets.QLabel, "Fission180NeonPresetName")
    h.check("after a real restart Mine is still chosen", page is not None and page.chosen_set() == "Mine",
            page.chosen_set() if page else None)
    h.check("... Custom (based on Johnny)", line is not None and "Custom (based on Johnny)" in line.text(),
            line.text() if line else None)
    wi.click(preferences().findChild(QtWidgets.QPushButton, "Fission180PreferencesCancel"))


mine_chosen.done = lambda: preferences() is None
mine_chosen.done_what = "the Preferences to close"


h.run(
    os.environ.get("FISSION180_SCENARIO", "neon_settings_restart"),
    [started, open_preferences, open_neon_page, mine_chosen],
    paced_by="state",
)
