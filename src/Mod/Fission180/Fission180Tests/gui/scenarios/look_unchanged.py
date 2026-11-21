# SPDX-License-Identifier: LGPL-2.1-or-later
"""Dark and Light look exactly as they did before the Neon Lights work (Luca, 2026-11-20: "I
like the current look of Fission. Dont change any of that. Only make changes to the NEW
themes"; docs/fission180/neon-lights-design.md, section 6.11).

In Dark, then Light, then Dark again: the window with a body, the CREATE drop-down, and the
window with the Extrude dialog open are grabbed and compared with the pictures taken on
develop before the work (Fission180Tests/fixtures/look_baseline/). A part passes when at most
0.2% of its pixels differ by more than 8 of 255 in any channel. The last Dark round shows that
going to another look and back leaves nothing behind.

FISSION180_RECORD_LOOK=1 writes the pictures instead (only on develop's look!).
"""

from Fission180Tests.gui import harness as h
from Fission180Tests.gui import look_compare as lc

ROUNDS = lc.make_round("dark") + lc.make_round("light")
if not lc.RECORD:
    # back to Dark: the same pictures as the first round (a look switch leaves no trace)
    ROUNDS += lc.make_round("dark", "again_")

h.run("look_unchanged", [lc.setup] + ROUNDS, paced_by="state")
