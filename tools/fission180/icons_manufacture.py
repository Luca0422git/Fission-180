# SPDX-License-Identifier: LGPL-2.1-or-later
# MANUFACTURE workspace icons (wave 7, cam): the workspace, Setup, the milling operations,
# Simulate, Post Process, Setup Sheet, the Tool Library and its tool types. Run inside
# make_icons.py's namespace (block, poly, iso, ... are its helpers). Original artwork in the
# style of the existing icons.
# flake8: noqa


def _cam_plate(h=6, ox=24, oy=33, colors=None):
    return block(0, 0, 0, 24, 24, h, colors or GREY, ox, oy)


def _cam_tool(cx, top, tip_y, r=3.4, kind="flat", color=None):
    """An end mill standing upright: a shaft and its cutting end at (cx, tip_y)."""
    c = color or GOLD
    body = rect(cx - r, top, 2 * r, tip_y - top - (r if kind == "ball" else 0), c[1], 0.6, 'stroke="%s" stroke-width="0.6"' % DARK)
    if kind == "ball":
        end = path("M%.2f %.2f A%.2f %.2f 0 0 0 %.2f %.2f Z" % (cx - r, tip_y - r, r, r, cx + r, tip_y - r), DARK, 0.6, c[2])
    elif kind == "drill":
        end = poly([(cx - r, tip_y - 0.1), (cx + r, tip_y - 0.1), (cx, tip_y + r * 0.9)], c[2], 'stroke="%s" stroke-width="0.6"' % DARK)
    elif kind == "chamfer":
        end = poly([(cx - r, tip_y - r), (cx + r, tip_y - r), (cx, tip_y)], c[2], 'stroke="%s" stroke-width="0.6"' % DARK)
        body = rect(cx - r * 0.6, top, 2 * r * 0.6, tip_y - top - r, c[1], 0.6, 'stroke="%s" stroke-width="0.6"' % DARK)
    else:
        end = ellipse(cx, tip_y, r, r * 0.4, c[2], DARK, 0.6)
    flutes = line(cx - r * 0.5, tip_y - 7, cx + r * 0.5, tip_y - 3.5, DARK, 0.8) if kind in ("flat", "drill") else ""
    return body + end + flutes


def _on_top(points, color=None, w=1.8, h=6, ox=24, oy=33):
    """A toolpath drawn on the plate's top face: points are (x, y) on the plate."""
    pts = [iso(x, y, h, ox, oy) for x, y in points]
    d = "M%.2f %.2f " % pts[0] + " ".join("L%.2f %.2f" % p for p in pts[1:])
    return path(d, color or BLUE[2], w)


@icon("workspace_manufacture")
def _():
    # a plate being milled: the tool, and the path it has cut
    return (
        _cam_plate()
        + _on_top([(4, 4), (20, 4), (20, 10), (4, 10), (4, 16), (20, 16)])
        + _cam_tool(30, 4, 26, 3.6)
    )


@icon("cam_setup")
def _():
    # the part inside its see-through stock, with the origin's three axes on a corner
    ox, oy = 24, 34
    o = iso(0, 24, 9, ox, oy)
    return (
        block(2, 2, 0, 20, 20, 6, GREY, ox, oy)
        + poly([iso(0, 0, 9, ox, oy), iso(24, 0, 9, ox, oy), iso(24, 24, 9, ox, oy), iso(0, 24, 9, ox, oy)], "none", 'stroke="%s" stroke-width="1.1" stroke-dasharray="2.5 2"' % BLUE[2])
        + line(o[0], o[1], o[0], o[1] - 11, BLUE[2], 2.0)
        + line(o[0], o[1], o[0] + 9.5, o[1] - 5.5, RED, 2.0)
        + line(o[0], o[1], o[0] + 9.5, o[1] + 5.5, GREEN, 2.0)
        + circle(o[0], o[1], 2.0, WHITE, DARK, 0.6)
    )


@icon("cam_face")
def _():
    # a wide cutter sweeping the whole top in straight passes
    return (
        _cam_plate()
        + _on_top([(3, 4), (21, 4)], w=2.2)
        + _on_top([(3, 10), (21, 10)], w=2.2)
        + _on_top([(3, 16), (21, 16)], w=2.2)
        + rect(22, 12, 16, 6, GOLD[1], 1.2, 'stroke="%s" stroke-width="0.6"' % DARK)
        + rect(27.5, 3, 5, 9, GOLD[2], 0.6, 'stroke="%s" stroke-width="0.6"' % DARK)
    )


@icon("cam_adaptive2d")
def _():
    # a pocket cleared by curling passes that keep the same bite
    cx, cy = 24, 25
    return (
        _cam_plate()
        + path("M%d %d m-9 1 q4 -7 9 -4 q6 3 0 6 q-5 2 -3 -2 q2 -3 5 -1" % (cx, cy), BLUE[2], 1.8)
        + _cam_tool(34, 5, 24, 3.2)
    )


@icon("cam_pocket2d")
def _():
    # a pocket cleared by passes that follow its outline inwards
    return (
        _cam_plate()
        + _on_top([(4, 4), (20, 4), (20, 20), (4, 20), (4, 4)])
        + _on_top([(8, 8), (16, 8), (16, 16), (8, 16), (8, 8)])
        + _on_top([(11.5, 11.5), (12.5, 12.5)], w=2.4)
    )


@icon("cam_contour2d")
def _():
    # the tool following the outside of the part
    ox, oy = 24, 33
    return (
        block(3, 3, 0, 18, 18, 6, GREY, ox, oy)
        + _on_top([(0, 24), (24, 24), (24, 0)], w=2.0, h=0)
        + _on_top([(0, 24), (0, 0), (24, 0)], w=2.0, h=6)
        + _cam_tool(39, 8, 30, 3.0)
    )


@icon("cam_slot")
def _():
    # one straight pass down the middle of a slot
    return (
        _cam_plate()
        + _on_top([(5, 12), (19, 12)], GREY[2], 6.0)
        + _on_top([(5, 12), (19, 12)], BLUE[2], 1.8)
        + _cam_tool(34, 6, 25, 3.0)
    )


@icon("cam_trace")
def _():
    # the tool's centre following a curve
    return (
        _cam_plate()
        + path("M9 26 q6 -9 12 -2 q5 6 11 -2", BLUE[2], 2.0)
        + _cam_tool(34, 4, 21.5, 2.6, "ball")
    )


@icon("cam_engrave")
def _():
    # a V cutter writing on the top
    return (
        _cam_plate()
        + _on_top([(5, 6), (5, 18)], w=1.6)
        + _on_top([(5, 6), (12, 6)], w=1.6)
        + _on_top([(5, 12), (10, 12)], w=1.6)
        + _cam_tool(33, 5, 24, 3.6, "chamfer")
    )


@icon("cam_chamfer2d")
def _():
    # a chamfer mill breaking the top edge
    ox, oy = 24, 33
    return (
        _cam_plate()
        + poly([iso(24, 0, 6, ox, oy), iso(24, 24, 6, ox, oy), iso(24, 24, 3.5, ox, oy), iso(24, 0, 3.5, ox, oy)], BLUE[2])
        + _cam_tool(40, 6, 27, 4.0, "chamfer")
    )


@icon("cam_bore")
def _():
    # a helix going down a hole
    cx, cy = 22, 22
    return (
        _cam_plate()
        + ellipse(cx, cy, 8, 4, DARK)
        + path("M%d %d a7 3.3 0 1 0 14 0 a7 3.3 0 1 0 -14 2 a7 3.3 0 1 0 14 2" % (cx - 7, cy - 1), BLUE[2], 1.5)
        + _cam_tool(cx, 2, 20, 2.6)
    )


@icon("cam_circular")
def _():
    # rings widening a round pocket
    cx, cy = 23, 22
    return (
        _cam_plate()
        + ellipse(cx, cy, 10, 5, GREY[2], DARK, 0.6)
        + ellipse(cx, cy, 7.5, 3.7, "none", BLUE[2], 1.5)
        + ellipse(cx, cy, 4, 2, "none", BLUE[2], 1.5)
    )


@icon("cam_thread")
def _():
    # a hole with thread turns
    cx, cy = 23, 22
    return (
        _cam_plate()
        + ellipse(cx, cy, 8, 4, DARK)
        + line(cx - 7, cy - 2, cx + 7, cy + 1, BLUE[2], 1.3)
        + line(cx - 7, cy + 1, cx + 7, cy + 4, BLUE[2], 1.3)
        + _cam_tool(cx, 2, 19, 2.4)
    )


@icon("cam_drill")
def _():
    # a drill over a hole
    cx, cy = 23, 24
    return (
        _cam_plate()
        + ellipse(cx, cy, 5, 2.5, DARK)
        + _cam_tool(cx, 2, 19.5, 3.4, "drill")
        + arrow(34, 8, 34, 20, BLUE[2], 2.0, 4.5)
    )


def _cam_dome(ox=24, oy=33):
    """A plate with a rounded hump: a 3D part."""
    return (
        _cam_plate(4, ox, oy)
        + path("M10 25 Q24 4 38 25 Q24 33 10 25 Z", DARK, 0.7, GREY[0])
    )


@icon("cam_adaptive3d")
def _():
    # roughing around a 3D shape in level steps
    return (
        _cam_dome()
        + path("M12 24 q12 7 24 0", BLUE[2], 1.6)
        + path("M15 19 q9 5 18 0", BLUE[2], 1.6)
        + path("M19 14 q5 3 10 0", BLUE[2], 1.6)
    )


@icon("cam_pocket3d")
def _():
    # a 3D pocket cleared in offset passes
    return (
        _cam_plate(8)
        + ellipse(24, 21, 12, 6, GREY[2], DARK, 0.6)
        + ellipse(24, 21.5, 8, 4, "none", BLUE[2], 1.5)
        + ellipse(24, 22, 4, 2, "none", BLUE[2], 1.5)
    )


@icon("cam_parallel")
def _():
    # parallel passes riding over a 3D shape
    return (
        _cam_dome()
        + path("M12 23 Q19 8 24 8", BLUE[2], 1.5)
        + path("M16 26 Q22 11 28 10", BLUE[2], 1.5)
        + path("M21 28 Q27 14 32 14", BLUE[2], 1.5)
        + path("M27 28 Q32 19 35 19", BLUE[2], 1.5)
        + _cam_tool(35, 2, 14, 2.6, "ball")
    )


@icon("cam_contour3d")
def _():
    # level lines around the steep walls of a 3D shape
    return (
        _cam_dome()
        + path("M12.5 22 q11.5 6 23 0", BLUE[2], 1.6)
        + path("M14.5 18 q9.5 5 19 0", BLUE[2], 1.6)
        + path("M17.5 14 q6.5 3.5 13 0", BLUE[2], 1.6)
        + path("M21 10.5 q3 1.5 6 0", BLUE[2], 1.6)
    )


@icon("cam_generate")
def _():
    # make the toolpath again: a path and a turning arrow
    return (
        _on_top([(2, 6), (20, 6), (20, 14), (2, 14)], w=2.0, h=0, oy=22)
        + path("M33 30 a8 8 0 1 1 -3 -6.2", GREEN, 2.4)
        + poly([(27, 20), (34, 22), (29.5, 27.5)], GREEN)
    )


@icon("cam_simulate")
def _():
    # play: the stock being cut away
    return (
        _cam_plate(8)
        + poly([iso(6, 0, 8, 24, 33), iso(18, 0, 8, 24, 33), iso(18, 24, 8, 24, 33), iso(6, 24, 8, 24, 33)], GREY[2])
        + circle(36, 36, 9, GREEN)
        + poly([(33, 31), (41, 36), (33, 41)], WHITE)
    )


@icon("cam_post")
def _():
    # a program sheet with G-code lines and the arrow to the machine
    return (
        rect(8, 5, 24, 34, GREY[0], 2.5, 'stroke="%s" stroke-width="0.7"' % DARK)
        + line(12, 12, 22, 12, BLUE[2], 2.0)
        + line(12, 18, 27, 18, GREY[2], 2.0)
        + line(12, 24, 25, 24, GREY[2], 2.0)
        + line(12, 30, 20, 30, GREY[2], 2.0)
        + arrow(27, 36, 43, 36, GREEN, 3.0, 6.5)
    )


@icon("cam_sheet")
def _():
    # the setup sheet: a page with a picture of the part and a table
    return (
        rect(8, 4, 30, 38, GREY[0], 2.5, 'stroke="%s" stroke-width="0.7"' % DARK)
        + block(0, 0, 0, 10, 10, 4, GREY, 23, 14, 0.9)
        + line(12, 26, 34, 26, DARK, 1.2)
        + line(12, 31, 34, 31, GREY[2], 1.6)
        + line(12, 36, 34, 36, GREY[2], 1.6)
        + line(20, 26, 20, 38, DARK, 0.8)
    )


@icon("cam_tools")
def _():
    # the tool library: three different cutters side by side
    return (
        _cam_tool(11, 6, 36, 3.6, "flat")
        + _cam_tool(24, 6, 36, 3.6, "ball")
        + _cam_tool(37, 6, 34, 3.6, "drill")
        + line(5, 6, 43, 6, DARK, 2.4)
    )


@icon("cam_tool_flat")
def _():
    return _cam_tool(24, 5, 40, 6.0, "flat")


@icon("cam_tool_ball")
def _():
    return _cam_tool(24, 5, 41, 6.0, "ball")


@icon("cam_tool_bull")
def _():
    r = 6.0
    return (
        rect(24 - r, 5, 2 * r, 30, GOLD[1], 0.6, 'stroke="%s" stroke-width="0.6"' % DARK)
        + path("M%.1f 35 q0 5 4 5 h4 q4 0 4 -5 Z" % (24 - r), DARK, 0.6, GOLD[2])
    )


@icon("cam_tool_face")
def _():
    return (
        rect(20, 5, 8, 18, GOLD[2], 0.6, 'stroke="%s" stroke-width="0.6"' % DARK)
        + rect(8, 23, 32, 11, GOLD[1], 1.5, 'stroke="%s" stroke-width="0.6"' % DARK)
        + rect(9, 33, 5, 4, BLUE[2], 0.5)
        + rect(21.5, 33, 5, 4, BLUE[2], 0.5)
        + rect(34, 33, 5, 4, BLUE[2], 0.5)
    )


@icon("cam_tool_chamfer")
def _():
    return _cam_tool(24, 5, 40, 9.0, "chamfer")


@icon("cam_tool_drill")
def _():
    return _cam_tool(24, 4, 36, 5.5, "drill")


@icon("cam_tool_spot")
def _():
    return (
        rect(18.5, 5, 11, 22, GOLD[1], 0.6, 'stroke="%s" stroke-width="0.6"' % DARK)
        + poly([(18.5, 27), (29.5, 27), (24, 32.5)], GOLD[2], 'stroke="%s" stroke-width="0.6"' % DARK)
        + ellipse(24, 40, 9, 2.5, GREY[2])
        + poly([(20, 39.5), (28, 39.5), (24, 43)], DARK)
    )
