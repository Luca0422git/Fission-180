# SPDX-License-Identifier: LGPL-2.1-or-later
"""Closing the undo step of a command that has no dialog (Break Link, Rename, Insert Design,
a script...).

FreeCAD's `doc.commitTransaction()` / `doc.abortTransaction()` only close a step the design
has changes in. A command that opened a step and then changed nothing (it was refused, or
there was nothing to change) left the step's name the application's open one: the next
change anywhere was filed under it, joined to whatever came after, and one Undo took both
(the book parity report's bug 11 class; found in these commands by the test harness's check
after every step, wave 7). `close(doc, abort)` closes the pending name too, as
`preview.end_transaction` does for the dialogs.
"""

import FreeCAD as App


def close(doc, abort=False):
    """Keep (or, abort=True, take back) what the open undo step holds, and leave none open."""
    try:
        if abort:
            doc.abortTransaction()
        else:
            doc.commitTransaction()
    finally:
        try:
            App.closeActiveTransaction(abort)
        except Exception:
            pass
