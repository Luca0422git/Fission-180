# SPDX-License-Identifier: LGPL-2.1-or-later
"""How many big icons each ribbon group shows so the ribbon fits its window (Luca,
2026-11-06: "the toolbar doesnt scale very well with smaller screens. the tools are bunched
up. can we set it up so it dynamically chooses how many tools to show based on the window
size?"). Fusion's toolbar does the same: when the window narrows, panels show fewer icons;
every command stays in its panel's drop-down.

Pure (no Qt): the ribbon (ribbon_ui.RibbonWidget._fit) gives each group's width for every
number of icons and the room there is, and gets back how many icons each group shows.
"""


def fit(widths, room, fixed=0):
    """widths: per group, the list of its widths with 0, 1, 2 ... icons (widths[g][n]);
    room: the pixels there are; fixed: pixels taken anyway (separators, spacing). Returns the
    number of icons per group: all of them when they fit; else icons come off one at a time,
    always from the group showing the most (the rightmost of those first), from the end of
    its row, until it fits or no group shows any."""
    counts = [len(w) - 1 for w in widths]

    def total():
        return fixed + sum(w[c] for w, c in zip(widths, counts))

    while total() > room:
        best = None
        for i, count in enumerate(counts):
            if count > 0 and (best is None or count >= counts[best]):
                best = i
        if best is None:
            break
        counts[best] -= 1
    return counts
