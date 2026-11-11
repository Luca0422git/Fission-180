# SPDX-License-Identifier: LGPL-2.1-or-later
"""What a click on a sketch area does to the profiles of an open Extrude dialog (pure
logic, unit-tested; the dialog is extrude_ui.ExtrudePanel._toggle).

A click on an area that is picked drops it, on one that is not adds it (Fusion). One
exception: Extrude takes by itself, when it opens, the pieces of a shape drawn over a
projected edge (a circle drawn on a face's rim is split by the rim into two areas:
extrude.taken_by_itself, Fission 180's own rule, so a disc on a face is extruded as drawn).
Fusion takes nothing by itself when a sketch has several areas, and its users click each
piece they want: the book's Saturn V thruster says "click both halves of the circle". With
the pieces already picked, the first click dropped the piece it meant to take (wave 7
replay). So while the pieces are as the dialog took them, a click on one of them starts
the person's own choice with that piece; any other click works as always."""


def toggled(keys, key, auto=()):
    """(the new list of picked keys, the automatic pieces still standing) after a click on
    the area `key`. `keys`: the picked areas in order; `auto`: the pieces the dialog took
    by itself that the person has not touched yet (empty once they did)."""
    keys = list(keys)
    auto = set(auto)
    if len(auto) > 1 and key in auto and set(keys) == auto:
        return [key], set()
    if key in keys:
        return [k for k in keys if k != key], set()
    return keys + [key], set()
