# SPDX-License-Identifier: LGPL-2.1-or-later
# Wave 7 (book-components): the design's row when the design holds components, an assembly:
# three stacked blocks like the component icon without its plus (the book parity report: "the
# root row shows a single cube icon, not a stacked assembly icon").
# Run inside make_icons.py's namespace (block, poly, iso, ... are its helpers).
# Original artwork in the style of the existing icons.
# flake8: noqa


@icon("assembly")
def _():
    return (
        block(0, 0, 0, 10, 10, 9, GREY, 16, 38)
        + block(0, 0, 0, 10, 10, 9, GREY, 32, 38)
        + block(0, 0, 0, 10, 10, 9, BLUE, 24, 24)
    )
