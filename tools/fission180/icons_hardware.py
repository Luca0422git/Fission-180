# SPDX-License-Identifier: LGPL-2.1-or-later
# Wave 7 (book-hardware): INSERT > Insert Catalogue Part... (the stand-in for Fusion's Insert
# McMaster-Carr Component): a catalogue page with a hexagon nut on it and an arrow coming
# down into the design.
# Run inside make_icons.py's namespace (rect, line, poly, ellipse, path ... are its helpers).
# Original artwork in the style of the existing icons.
# flake8: noqa


@icon("catalogue_part")
def _():
    page = (
        rect(6, 5, 24, 32, GREY[0], 2)
        + line(10, 11, 26, 11, GREY[2], 1.6)
        + line(10, 16, 26, 16, GREY[2], 1.6)
        + line(10, 21, 18, 21, GREY[2], 1.6)
    )
    nut = (
        poly([(12, 28), (17, 25.5), (22, 28), (22, 33), (17, 35.5), (12, 33)], BLUE[1])
        + ellipse(17, 30.5, 2.4, 2.4, DARK)
    )
    arrow = path("M37 16 V36 M30 30 L37 37 L44 30", BLUE[1], 3.2)
    tray = path("M28 42 H45", GREY[1], 2.4)
    return page + nut + arrow + tray
