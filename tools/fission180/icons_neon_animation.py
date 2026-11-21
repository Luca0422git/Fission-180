# SPDX-License-Identifier: LGPL-2.1-or-later
# Neon Lights hand-made icons for the ANIMATION area (icons_animation.py): the workspace, the
# film-strip commands and the timeline's transport buttons (drawn solid in the normal set, they
# turned into heavy outlines in the automatic neon copy). Helpers: icons_neon_kit.py.
# Original line art in an industrial sci-fi style.
# flake8: noqa


def nb_film(x, y, w, h, c=NB_P):
    """A strip of film: a cut-corner frame with a row of sprocket squares along its top and
    bottom, spaced so they stay apart at 18 px."""
    out = ncut(x, y, w, h, c, 4, fo=0.06)
    n = max(2, int(w // 11))
    for i in range(n):
        hx = x + 7 + i * (w - 14.0) / max(1, n - 1)
        out += ndot(hx, y + 3.6, c, 1.1) + ndot(hx, y + h - 3.6, c, 1.1)
    return out


def nb_play(cx, cy, r, c=NB_S, fo=0.22):
    return npoly([(cx - r * 0.6, cy - r), (cx + r, cy), (cx - r * 0.6, cy + r)], c, NW, fo)


@neon_icon("workspace_animation")
def _():
    # a film frame; inside it a part moving out along its path (its start position dashed)
    return (
        nb_film(3, 6, 42, 36)
        + nl("M11 22 H19 V30 H11 Z", NP, NI, dash="2.6 2", cap="butt", glow=0.12)
        + nseg(19, 26, 26, 23, NS, NI, cap="butt", glow=0.2)
        + nbox(0, 0, 0, 8, 8, 7, NS, 33, 23, fo=0.2)
    )


@neon_icon("anim_storyboard")
def _():
    return nb_film(4, 10, 34, 24) + nb_play(20, 22, 5.0, NB_T, 0.15) + nb_plus_badge(37, 37, 7.5)


@neon_icon("anim_publish")
def _():
    return nb_film(4, 12, 28, 22) + nb_play(17, 23, 4.6, NB_T, 0.15) + nb_arrow(29, 23, 45, 23, NB_S, 1.8, 5)


@neon_icon("anim_play")
def _():
    return ntransport("play")


@neon_icon("anim_pause")
def _():
    return ntransport("pause")


@neon_icon("anim_to_start")
def _():
    return ntransport("start")


@neon_icon("anim_to_end")
def _():
    return ntransport("end")


@neon_icon("anim_previous")
def _():
    return ntransport("rewind")


@neon_icon("anim_next")
def _():
    return ntransport("forward")


@neon_icon("anim_loop")
def _():
    # two angular half loops chasing each other
    return (
        nb_path("M10 26 V18 L14 14 H34", NB_T, 2.0)
        + nb_solid([(33, 9.5), (40, 14), (33, 18.5)], NB_T)
        + nb_path("M38 22 V30 L34 34 H14", NB_T, 2.0)
        + nb_solid([(15, 29.5), (8, 34), (15, 38.5)], NB_T)
    )


@neon_icon("anim_showhide")
def _():
    # a bulb: its left half dark glass, its right half lit
    return (
        nb_path("M24 6 L31 9 L34 16 L31 23 V30 H17 V23 L14 16 L17 9 Z", NB_P, 1.5, NB_P, 0.10)
        + nf("M24 6 L31 9 L34 16 L31 23 V30 H24 Z", NS, 0.4)
        + nb_line(18, 35, 30, 35, NB_P, 1.6)
        + nb_line(20, 40, 28, 40, NB_P, 1.6)
        + nb_line(37, 9, 41, 5, NB_S, 1.5)
        + nb_line(38, 17, 44, 17, NB_S, 1.5)
    )


def nb_camera(lamp):
    """A film camera: a cut-corner body, a lens hood, two reels, and its lamp (lit or not)."""
    return (
        ncut(5, 19, 26, 17, NB_P, 3.5, fo=0.1)
        + npoly([(31, 24), (43, 18), (43, 37), (31, 31)], NB_P, NW, 0.06)
        + ncircle(12, 12, 5, NB_P, NW)
        + ncircle(25, 12, 5, NB_P, NW)
        + lamp
    )


@neon_icon("anim_view")
def _():
    return nb_camera(ndot(37, 42, NB_S, 2.4))


@neon_icon("anim_view_off")
def _():
    return nb_camera(nseg(4, 44, 44, 6, NB_T, NW))


@neon_icon("anim_scratch")
def _():
    return (
        nb_page(8, 8, 26, 32, NB_P, 5, 3, NB_P)
        + nb_poly([(40, 14), (44, 18), (30, 34), (25, 36), (26, 30)], NB_S, 1.4, 0.2)
    )
