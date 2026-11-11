# SPDX-License-Identifier: LGPL-2.1-or-later
"""The spacing of a sketch's grid lines (no Qt: unit tested).

Fusion's Grid Settings (navigation bar > Grid and Snaps) give a Major Grid Spacing and the
Minor Subdivisions between two major lines: Fixed, 50 mm and 5 draw a line every 10 mm, every
fifth one stronger, and the pointer snaps to the 10 mm lines. FreeCAD's sketch grid takes
the distance between two LINES (`GridSize`) and draws every n-th one stronger (its
"GridNumberSubdivision"). Fission 180 handed it the major spacing as it was: the book's grid
came out as lines 50 mm apart, and FreeCAD's snap (a coordinate within a fifth of the spacing
of a line lands on it) pulled a click 8 mm off the X axis onto it (the book parity report,
2026-11-10: "snap is far too strong").

An adaptive grid has no spacing of its own: FreeCAD starts from `GridSize` and multiplies or
divides by the subdivisions until the lines are far enough apart on the screen. In a design
in inches (or feet) it starts from one inch, so the lines and the snap are 1 in, 0.2 in, 5 in
... apart instead of 10 mm, 2 mm, 50 mm (the report: "in an inch design the sketch grid and
snap stay metric").
"""

INCH = 25.4
# the adaptive grid's starting spacing (mm) for a design whose length unit is not metric
ADAPTIVE_BASE = {"in": INCH, "ft": INCH}


def length_unit(sketch):
    """The design's length unit ("mm", "cm", "m", "in", "ft")."""
    try:
        from . import browser_core

        return browser_core.doc_length_unit(sketch.Document)
    except Exception:
        return "mm"


def spacing_for(unit, adaptive, major, subdivisions):
    """The distance (mm) between two grid lines for FreeCAD's `GridSize`."""
    major = float(major)
    if adaptive:
        return ADAPTIVE_BASE.get(unit, major)
    return major / max(1, int(subdivisions))


def line_spacing(sketch, adaptive, major, subdivisions):
    return spacing_for(length_unit(sketch), adaptive, major, subdivisions)
