# SPDX-License-Identifier: LGPL-2.1-or-later
"""Replay of part of the book's Project 11, "3D Printer Hot End" (Mastering Autodesk Fusion,
2nd ed., pp 124-141), the way the book parity report lists it (lines 1758-1947), in ONE
design, with a user's defaults and real input only. The steps and their checks are in
Fission180Tests/gui/replay_11_steps.py.
"""

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import replay_11_steps as p11

h.run("replay_11_hot_end", p11.steps(), paced_by="state")
