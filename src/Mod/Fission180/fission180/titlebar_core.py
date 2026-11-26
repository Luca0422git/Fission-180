# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fission 180's own title bar, the parts without Qt (titlebar_ui.py does the window).

Luca (2026-11-23): "on my laptop screen where there is less real estate, That top bar that
says Fission 180 with the minimize and close button is kinda annoying. Is there a way to
integrate the top bar into the program? for both windows and linux". Like Fusion's: no title
bar from the system; the minimize, maximize and close buttons at the right end of Fission
180's top row; that row moves the window; thin grips along the edges resize it.

Preferences > General > Appearance > Title bar: Fission 180's (the default) or the system's.
"""

OWN, SYSTEM = "own", "system"
DEFAULT_MODE = OWN
CHOICES = [(OWN, "Fission 180's (more room)"), (SYSTEM, "The system's")]

GRIP = 5  # px: the band along each edge that resizes the window (it has no frame then)
CORNER = 10  # px: the square at each corner that resizes two edges at once

# which edges each grip moves
EDGES = {
    "top": ("top",),
    "bottom": ("bottom",),
    "left": ("left",),
    "right": ("right",),
    "top_left": ("top", "left"),
    "top_right": ("top", "right"),
    "bottom_left": ("bottom", "left"),
    "bottom_right": ("bottom", "right"),
}


def mode_of(text):
    """The stored choice, or the default for anything else."""
    return text if text in (OWN, SYSTEM) else DEFAULT_MODE


def grips(width, height, grip=GRIP, corner=CORNER):
    """{name: (x, y, w, h)} of the resize grips of a window `width` x `height` pixels: a band
    `grip` wide along each edge between the corners, a `corner` square at each corner."""
    w, h = max(0, int(width)), max(0, int(height))
    c = min(corner, w // 2, h // 2)
    e = min(grip, c) if c else min(grip, w, h)
    mid_w, mid_h = max(0, w - 2 * c), max(0, h - 2 * c)
    return {
        "top": (c, 0, mid_w, e),
        "bottom": (c, h - e, mid_w, e),
        "left": (0, c, e, mid_h),
        "right": (w - e, c, e, mid_h),
        "top_left": (0, 0, c, c),
        "top_right": (w - c, 0, c, c),
        "bottom_left": (0, h - c, c, c),
        "bottom_right": (w - c, h - c, c, c),
    }


# -- Windows: the window keeps its frame, Fission 180 answers what is under the mouse ---------------
TOP_BAND = 5  # px: along the top edge (the frame's own border is gone there), it resizes
TOP_CORNER = 12  # px: at the top band's ends, it resizes two edges at once
AUTOHIDE_GAP = 2  # px: kept free where the taskbar hides itself (titlebar_win)

CLIENT, CAPTION, TOP, TOP_LEFT, TOP_RIGHT = "client", "caption", "top", "top_left", "top_right"


def hit_test(x, y, width, maximized, empty_row, band=TOP_BAND, corner=TOP_CORNER):
    """What the point (x, y) of the window's inside is, `width` wide: the top band resizes
    (not when maximized), an empty part of the top row is the window's caption (Windows moves
    the window from it), anything else is the program's. empty_row: the point is on the top
    row where no button, tab or field is."""
    if not maximized and 0 <= y < band:
        if x < corner:
            return TOP_LEFT
        if x >= width - corner:
            return TOP_RIGHT
        return TOP
    return CAPTION if empty_row else CLIENT


def autohide_gaps(monitor, work, hidden_edges, gap=AUTOHIDE_GAP):
    """The maximized window's rectangle (left, top, right, bottom) on a monitor whose taskbar
    hides itself on `hidden_edges` ("left", "top", "right", "bottom"): the work area, `gap`
    pixels short of each such edge, so the mouse at that edge still brings the taskbar out (a
    window that covers the whole screen is taken for a full screen program and the taskbar
    stays hidden). None when nothing hides on this monitor's edges."""
    if not hidden_edges:
        return None
    left, top, right, bottom = work
    if "left" in hidden_edges and left <= monitor[0]:
        left += gap
    if "top" in hidden_edges and top <= monitor[1]:
        top += gap
    if "right" in hidden_edges and right >= monitor[2]:
        right -= gap
    if "bottom" in hidden_edges and bottom >= monitor[3]:
        bottom -= gap
    if (left, top, right, bottom) == tuple(work):
        return None
    return (left, top, right, bottom)
