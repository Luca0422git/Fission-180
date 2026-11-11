# SPDX-License-Identifier: LGPL-2.1-or-later
"""SpurGear: opens Fission 180's Gear tool (SOLID > CREATE > Gear).

Fusion ships a "SpurGear" sample under UTILITIES > ADD-INS > Scripts and Add-Ins, and
tutorials start it from there ("Mastering Autodesk Fusion", the Gear Train). Fission 180's
gear is a tool of its own with a live preview; this entry is the same door to it. The tool
starts once this script has ended (its dialog makes one undo step of its own).
"""

import FreeCADGui as Gui
from PySide import QtCore

QtCore.QTimer.singleShot(0, lambda: Gui.runCommand("Fission180_Gear"))
