# SPDX-License-Identifier: LGPL-2.1-or-later
# ANIMATION workspace icons (wave 7, animation): the workspace, New Storyboard, Transform
# Components, Restore Home, Auto Explode (one level / all levels), Manual Explode, Show/Hide,
# Create Callout, View, Publish Video, and the timeline's transport buttons. Run inside
# make_icons.py's namespace (block, poly, iso, ... are its helpers). Original artwork in the
# style of the existing icons.
# flake8: noqa


def _anim_frame(x, y, w, h, color=None):
    """A strip of film: a frame with sprocket holes above and below."""
    c = color or DARK
    out = rect(x, y, w, h, c, 1.5)
    n = max(2, int(w // 7))
    for i in range(n):
        hx = x + 2.5 + i * (w - 5.0 - 3.0) / max(1, n - 1)
        out += rect(hx, y + 1.5, 3, 2.2, WHITE, 0.5) + rect(hx, y + h - 3.7, 3, 2.2, WHITE, 0.5)
    return out


def _anim_play(cx, cy, r, color=None):
    return poly([(cx - r * 0.6, cy - r), (cx - r * 0.6, cy + r), (cx + r, cy)], color or GREEN)


@icon("workspace_animation")
def _():
    # two parts coming apart, on a strip of film
    return (
        _anim_frame(4, 6, 40, 36)
        + block(0, 0, 0, 9, 9, 5, GREY, 17, 33)
        + block(0, 0, 9, 9, 9, 5, BLUE, 17, 33)
        + arrow(34, 30, 34, 15, WHITE, 2.0, 4.5)
    )


@icon("anim_storyboard")
def _():
    # a strip of film with a plus: a new storyboard
    return _anim_frame(4, 10, 36, 24) + _anim_play(21, 22, 5.5, WHITE) + plus_badge()


@icon("anim_transform")
def _():
    # a part with the move / turn manipulator on it
    o = (22, 30)
    return (
        block(0, 0, 0, 12, 12, 7, GREY, 22, 36)
        + line(o[0], o[1], o[0], o[1] - 20, BLUE[2], 2.2)
        + poly([(o[0] - 3.2, o[1] - 19), (o[0] + 3.2, o[1] - 19), (o[0], o[1] - 25)], BLUE[2])
        + line(o[0], o[1], o[0] + 16, o[1] + 9, RED, 2.2)
        + poly([(o[0] + 14.2, o[1] + 11.6), (o[0] + 17.2, o[1] + 6.2), (o[0] + 20.6, o[1] + 11.8)], RED)
        + line(o[0], o[1], o[0] - 16, o[1] + 9, GREEN, 2.2)
        + poly([(o[0] - 14.2, o[1] + 11.6), (o[0] - 17.2, o[1] + 6.2), (o[0] - 20.6, o[1] + 11.8)], GREEN)
        + path("M33 12 A13 13 0 0 1 41 24", GOLD[1], 2.2)
        + circle(o[0], o[1], 2.2, WHITE, DARK, 0.6)
    )


@icon("anim_home")
def _():
    # a part going back to its place: a house and an arrow into it
    return (
        poly([(8, 24), (24, 9), (40, 24)], GREY[2], 'stroke="%s" stroke-width="0.6"' % DARK)
        + rect(12, 24, 24, 16, GREY[0], 1, 'stroke="%s" stroke-width="0.6"' % DARK)
        + rect(20.5, 29, 7, 11, BLUE[2], 0.8)
        + arrow(43, 8, 31, 19, GOLD[1], 2.4, 5.0)
    )


def _anim_stack(gap):
    return (
        block(0, 0, 0, 13, 13, 4, GREY, 24, 40)
        + block(0, 0, 4 + gap, 13, 13, 4, BLUE, 24, 40)
        + block(0, 0, 8 + 2 * gap, 13, 13, 4, GREY, 24, 40)
    )


@icon("anim_explode_one")
def _():
    # a stack of three parts pulled apart, one arrow
    return _anim_stack(5) + arrow(41, 30, 41, 12, GOLD[1], 2.2, 4.5)


@icon("anim_explode_all")
def _():
    # the same stack with arrows both ways and a small part off to the side: every level
    return (
        _anim_stack(5)
        + arrow(42, 24, 42, 9, GOLD[1], 2.2, 4.5)
        + arrow(42, 28, 42, 42, GOLD[1], 2.2, 4.5)
        + arrow(8, 26, 3, 23, GOLD[1], 2.0, 4.0)
    )


@icon("anim_explode_manual")
def _():
    # one part lifted off the other along an axis, with a hand-set arrow
    return (
        block(0, 0, 0, 13, 13, 5, GREY, 22, 40)
        + line(22, 32, 22, 6, BLUE[2], 1.4, 'stroke-dasharray="2.5 2"')
        + block(0, 0, 14, 13, 13, 5, BLUE, 22, 40)
        + arrow(40, 34, 40, 14, RED, 2.4, 5.0)
        + circle(40, 36, 2.4, WHITE, DARK, 0.6)
    )


@icon("anim_showhide")
def _():
    # a light bulb, half lit: show / hide
    return (
        path("M24 6 A11 11 0 0 0 17 26 V31 H31 V26 A11 11 0 0 0 24 6 Z", DARK, 0.8, GOLD[0])
        + path("M24 6 A11 11 0 0 0 17 26 V31 H24 Z", DARK, 0.8, GREY[2])
        + rect(18, 32, 12, 3, GREY[1], 1)
        + rect(19.5, 36, 9, 3, GREY[2], 1)
        + line(36, 8, 40, 5, GOLD[1], 1.8)
        + line(38, 17, 43, 17, GOLD[1], 1.8)
    )


@icon("anim_callout")
def _():
    # a pin on a part with a text bubble
    return (
        block(0, 0, 0, 12, 12, 6, GREY, 15, 38)
        + line(17, 27, 27, 15, DARK, 1.4)
        + circle(17, 27, 2.6, GREEN, DARK, 0.6)
        + rect(24, 5, 20, 13, WHITE, 2.5, 'stroke="%s" stroke-width="0.7"' % DARK)
        + line(27.5, 9.5, 40.5, 9.5, DARK, 1.2)
        + line(27.5, 13.5, 37, 13.5, DARK, 1.2)
    )


def _anim_camera(dot):
    return (
        rect(6, 16, 26, 18, GREY[1], 2.5, 'stroke="%s" stroke-width="0.7"' % DARK)
        + poly([(32, 22), (42, 16), (42, 34), (32, 28)], GREY[2], 'stroke="%s" stroke-width="0.7"' % DARK)
        + circle(13, 12, 4.5, GREY[2], DARK, 0.7)
        + circle(24, 11, 5.5, GREY[2], DARK, 0.7)
        + circle(36, 38, 5.0, dot, DARK, 0.7)
    )


@icon("anim_view")
def _():
    # a film camera with a red dot: view changes are recorded
    return _anim_camera(RED)


@icon("anim_view_off")
def _():
    # the same camera with a yellow dot: view changes are not recorded
    return _anim_camera(GOLD[0])


@icon("anim_publish")
def _():
    # a strip of film going out: publish the video
    return (
        _anim_frame(4, 12, 30, 22)
        + _anim_play(18, 23, 5.0, WHITE)
        + arrow(30, 23, 45, 23, GREEN, 2.6, 5.5)
    )


@icon("anim_play")
def _():
    return _anim_play(24, 24, 12, GREEN)


@icon("anim_pause")
def _():
    return rect(13, 12, 8, 24, WHITE, 1.5) + rect(27, 12, 8, 24, WHITE, 1.5)


@icon("anim_to_start")
def _():
    return rect(9, 12, 4, 24, WHITE, 1) + poly([(38, 12), (38, 36), (15, 24)], WHITE)


@icon("anim_to_end")
def _():
    return rect(35, 12, 4, 24, WHITE, 1) + poly([(10, 12), (10, 36), (33, 24)], WHITE)


@icon("anim_previous")
def _():
    return poly([(24, 12), (24, 36), (7, 24)], WHITE) + poly([(41, 12), (41, 36), (24, 24)], WHITE)


@icon("anim_next")
def _():
    return poly([(7, 12), (7, 36), (24, 24)], WHITE) + poly([(24, 12), (24, 36), (41, 24)], WHITE)


@icon("anim_loop")
def _():
    return (
        path("M12 20 A13 11 0 0 1 37 18", WHITE, 2.6)
        + poly([(33, 12), (41, 19), (32, 23)], WHITE)
        + path("M36 28 A13 11 0 0 1 11 30", WHITE, 2.6)
        + poly([(15, 36), (7, 29), (16, 25)], WHITE)
    )


@icon("anim_scratch")
def _():
    # the scratch zone: a board with a pencil (set the scene up, nothing is recorded)
    return (
        rect(8, 8, 26, 32, GREY[0], 2, 'stroke="%s" stroke-width="0.7"' % DARK)
        + line(13, 16, 28, 16, GREY[2], 1.4)
        + line(13, 22, 28, 22, GREY[2], 1.4)
        + line(13, 28, 22, 28, GREY[2], 1.4)
        + poly([(40, 14), (44, 18), (30, 34), (25, 36), (26, 30)], GOLD[1], 'stroke="%s" stroke-width="0.6"' % DARK)
    )
