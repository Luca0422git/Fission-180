# SPDX-License-Identifier: LGPL-2.1-or-later
# The VIEW workspace (fission180/view_ui.py: nothing but the visible bodies on black, for
# see-through XR glasses). Run inside make_icons.py's namespace (block, rect, path, ... are its
# helpers). Original artwork in the style of the existing icons.
# flake8: noqa


@icon("workspace_view")
def _():
    # a part floating in front of a pair of XR glasses
    rim = 'stroke="%s" stroke-width="2.0"' % WHITE
    return (
        block(0, 0, 0, 10, 10, 9, BLUE, 24, 21)
        + rect(4.5, 28, 17, 12, DARK, 4.5, rim)
        + rect(26.5, 28, 17, 12, DARK, 4.5, rim)
        + path("M21.5 32.5 Q24 29.5 26.5 32.5", WHITE, 2.0)
        + line(4.5, 31, 2.5, 29, WHITE, 2.0)
        + line(43.5, 31, 45.5, 29, WHITE, 2.0)
    )
