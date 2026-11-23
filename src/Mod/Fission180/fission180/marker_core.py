# SPDX-License-Identifier: LGPL-2.1-or-later
"""How Measure's points and its distance look in the 3D view, and where the distance goes
(plain data and maths, no FreeCAD; unit tested in test_marker_core.py).

Luca, 2026-11-20: "the measure tools points are just a little too big ... zooming in on it
makes them massive. can we have them stay consistent with the zoom? and maybe not have it
light yellow? its impossible to see the text."

- A point Measure draws (a measured point, the ends of the distance, a snap point, the dot on
  a Center of Mass sign) is a marker of one size on the screen, whatever the part and however
  far the view is zoomed, as Fusion's are: a flat dot in pixels with a thin light rim, drawn
  under FreeCAD's SoShapeScale like the drag handles (handle_look). A little smaller than the
  dots were at a Fit before (12 to 14 px across); the balls other dialogs give to click (the
  origin point of Construct, a setup's box points) keep one size on the screen too.
- Its colour is a deep red-orange, no longer the amber that the lighting turned pale yellow:
  darker, strong against the colourless grey part, readable on the dark and the light
  background, and across the colour wheel from the blue of a picked face or edge. The light
  rim draws its edge on the part. Neon Lights keeps the preset's own light measure colour
  (neon_scene_core: a tint of the colour it draws the bodies' edges in, so a measured line
  along an edge still shows).
- The distance is in a box of its own (the look's text on the look's field colour, rimmed in
  the measure colour) beside the line, never on it: across the line from its middle, as far
  out as the dots are wide plus a gap, on the upper side (to the right of an upright line),
  or on the other side when the view's edge is in the way.
"""

import math

from .neon_scene_core import Live

# -- sizes, in pixels on the screen -------------------------------------------------------------
DOT_RADIUS_PX = 4.0  # a measured point (8 px, 11 px with its rim)
SNAP_RADIUS_PX = 4.0  # a snap point to click
COM_RADIUS_PX = 3.0  # the dot on a Center of Mass sign (the sign still shows round it)
RIM_PX = 1.5  # the light rim round a dot
BALL_RADIUS_PX = 5.0  # a ball another dialog draws to click (Construct, a manufacture setup)
LABEL_FONT_PX = 13.0
LABEL_PAD_X = 6.0
LABEL_PAD_Y = 3.0
LABEL_CORNER_PX = 3.0
LABEL_GAP_PX = 4.0  # between the dots' rim (and the line) and the label's box

# -- colours (RGB 0..1; Live: the neon colour of the role in Neon Lights) -------------------------
MEASURE = Live((0.85, 0.22, 0.12), "measure")  # the line and the dots
RIM = Live((0.97, 0.97, 0.97), "rim")  # the thin light rim round a dot

# The label goes on the side the line's normal points toward this direction (y up): mostly up,
# a little to the right. An upright line has its label on its right, a level one above it, and
# the lines an isometric view shows most (upright, 30 degrees each way) are far from the one
# direction (75 degrees) where the label changes side.
_UP = (math.cos(math.radians(75.0)), math.sin(math.radians(75.0)))
_EDGE_PX = 2.0  # how close to the view's edge a label may come


def disc(radius, steps=24):
    """The corners of a flat dot of `radius` in its own plane (x, y, 0)."""
    return [
        (
            radius * math.cos(2.0 * math.pi * i / steps),
            radius * math.sin(2.0 * math.pi * i / steps),
            0.0,
        )
        for i in range(steps)
    ]


def label_size(text_width, text_height):
    """The label's box (w, h) round text of that size (pixels)."""
    return (float(text_width) + 2.0 * LABEL_PAD_X, float(text_height) + 2.0 * LABEL_PAD_Y)


def label_colours(p, accent):
    """(backing, rim, text) hex colours of the distance's box in a look (`p`: theme.palette(),
    `accent`: the measure colour as hex): the look's text on its field colour, as its text
    boxes have it (readable in every look), rimmed in the measure colour."""
    return p.get("field", "#2f3540"), accent, p.get("text", "#f5f5f5")


def normal(a, b):
    """The unit normal (x, y; y up) of the line from screen point a to b that its label goes
    along (see _UP); straight up for a line of no length."""
    dx, dy = float(b[0]) - float(a[0]), float(b[1]) - float(a[1])
    length = math.hypot(dx, dy)
    if length < 1e-9:
        return 0.0, 1.0
    nx, ny = -dy / length, dx / length
    if nx * _UP[0] + ny * _UP[1] < 0.0:
        nx, ny = -nx, -ny
    return nx, ny


def _fits(centre, size, view):
    w, h = size
    return (
        centre[0] - w / 2.0 >= _EDGE_PX
        and centre[1] - h / 2.0 >= _EDGE_PX
        and centre[0] + w / 2.0 <= view[0] - _EDGE_PX
        and centre[1] + h / 2.0 <= view[1] - _EDGE_PX
    )


def label_offset(a, b, size, clear, view=None, gap=LABEL_GAP_PX):
    """Where the distance's label goes: the offset (dx, dy) in pixels (y up) from the middle
    of the line from screen point `a` to `b` to the middle of the label's box of `size` (w, h).

    The box goes across the line, so that no part of it comes nearer the line than `clear`
    (the dots' radius with their rim) plus `gap`: it never covers the dots or the line, however
    short the line is on the screen (zoomed far out), and stays just beside it. `view` (w, h):
    a box that would leave the view goes to the other side of the line when it fits there."""
    w, h = float(size[0]), float(size[1])
    nx, ny = normal(a, b)
    # how far the box reaches toward the line from its middle, along the normal
    reach = float(clear) + float(gap) + (abs(nx) * w + abs(ny) * h) / 2.0
    dx, dy = nx * reach, ny * reach
    if view is not None:
        mx = (float(a[0]) + float(b[0])) / 2.0
        my = (float(a[1]) + float(b[1])) / 2.0
        if not _fits((mx + dx, my + dy), (w, h), view) and _fits((mx - dx, my - dy), (w, h), view):
            dx, dy = -dx, -dy
    return dx, dy
