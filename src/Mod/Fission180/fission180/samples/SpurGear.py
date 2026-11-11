# SPDX-License-Identifier: LGPL-2.1-or-later
"""SpurGear: opens Fission 180's Gear tool (SOLID > CREATE > Gear).

Fusion ships a "SpurGear" sample under UTILITIES > ADD-INS > Scripts and Add-Ins, and
tutorials start it from there ("Mastering Autodesk Fusion", the Gear Train). Fission 180's
gear is a tool of its own with a live preview; this entry is the same door to it. The tool
starts once this script has ended (its dialog makes one undo step of its own).
"""

import FreeCADGui as Gui
from PySide import QtCore


def _start():
    # Fusion's sample always makes a new component named "Spur Gear (N teeth)": the Gear
    # dialog started from here proposes Operation New Component (gear_ui.GearPanel)
    gear_ui = None
    try:
        from fission180 import gear_ui

        gear_ui.GearPanel.as_sample = True
    except Exception:
        pass
    try:
        Gui.runCommand("Fission180_Gear")
    finally:
        if gear_ui is not None:
            gear_ui.GearPanel.as_sample = False  # (also when the dialog did not open)


QtCore.QTimer.singleShot(0, _start)
