# SPDX-License-Identifier: LGPL-2.1-or-later
"""Replay of the book's Project 10, "Fire Piston" (Mastering Autodesk Fusion, 2nd ed.,
pp 112-123), the way the book parity report lists it (lines 1644-1747), in ONE design, from
its first step to its last, with a user's defaults and real input only. The steps and their
checks are in Fission180Tests/gui/replay_10_steps.py.
"""

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import replay_10_steps as p10

h.run("replay_10_fire_piston", p10.steps(), paced_by="state")
