# SPDX-License-Identifier: LGPL-2.1-or-later
# Neon Lights hand-made icons for the ANIMATION area (icons_animation.py): the workspace, the
# film-strip commands and the timeline's transport buttons (drawn solid in the normal set, they
# turned into heavy outlines in the automatic neon copy). Helpers: icons_neon_kit.py.
# Original line art in an industrial sci-fi style.
# flake8: noqa


def nb_film(x, y, w, h, c=NB_P):
    """A strip of film: a cut-corner frame with sprocket dashes along its top and bottom."""
    out = nb_poly(nb_cut(x, y, w, h, 4), c, 1.5, 0.10)
    n = max(2, int(w // 7))
    for i in range(n):
        hx = x + 4 + i * (w - 10.0) / max(1, n - 1)
        out += rect(hx, y + 2.2, 2.4, 1.6, c, 0) + rect(hx, y + h - 3.8, 2.4, 1.6, c, 0)
    return out


def nb_play(cx, cy, r, c=NB_S, fo=0.22):
    return nb_poly([(cx - r * 0.6, cy - r), (cx + r, cy), (cx - r * 0.6, cy + r)], c, 1.7, fo)


@neon_icon("workspace_animation")
def _():
    # two parts lifting apart inside a film frame, a guide line between them
    return (
        nb_film(4, 4, 40, 40)
        + nb_box(0, 0, 0, 10, 10, 4, NB_P, 19, 29)
        + nb_line(19, 25, 19, 19.5, NB_S, 1.0, glow=False, extra='stroke-dasharray="1.6 1.4"')
        + nb_box(0, 0, 10, 10, 10, 4, NB_S, 19, 29)
        + nb_arrow(36, 33, 36, 13, NB_S, 1.6, 4.4)
    )


@neon_icon("anim_storyboard")
def _():
    return nb_film(4, 10, 34, 24) + nb_play(20, 22, 5.0, NB_T, 0.15) + nb_plus_badge(37, 37, 7.5)


@neon_icon("anim_publish")
def _():
    return nb_film(4, 12, 28, 22) + nb_play(17, 23, 4.6, NB_T, 0.15) + nb_arrow(29, 23, 45, 23, NB_S, 1.8, 5)


@neon_icon("anim_play")
def _():
    return nb_play(24, 24, 12, NB_S, 0.25)


@neon_icon("anim_pause")
def _():
    return nb_poly(nb_cut(13, 12, 8, 24, 2.5), NB_T, 1.6, 0.2) + nb_poly(nb_cut(27, 12, 8, 24, 2.5), NB_T, 1.6, 0.2)


@neon_icon("anim_to_start")
def _():
    return nb_line(11, 12, 11, 36, NB_T, 2.4) + nb_poly([(38, 12), (38, 36), (17, 24)], NB_T, 1.6, 0.2)


@neon_icon("anim_to_end")
def _():
    return nb_line(37, 12, 37, 36, NB_T, 2.4) + nb_poly([(10, 12), (10, 36), (31, 24)], NB_T, 1.6, 0.2)


@neon_icon("anim_previous")
def _():
    return nb_poly([(24, 13), (24, 35), (8, 24)], NB_T, 1.6, 0.2) + nb_poly([(40, 13), (40, 35), (24, 24)], NB_T, 1.6, 0.2)


@neon_icon("anim_next")
def _():
    return nb_poly([(8, 13), (8, 35), (24, 24)], NB_T, 1.6, 0.2) + nb_poly([(24, 13), (24, 35), (40, 24)], NB_T, 1.6, 0.2)


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
        + nb_path("M24 6 L31 9 L34 16 L31 23 V30 H24 Z", NB_A, 1.5, NB_A, 0.30, glow=False)
        + nb_line(18, 34, 30, 34, NB_P, 1.6)
        + nb_line(20, 38, 28, 38, NB_P, 1.6)
        + nb_line(37, 9, 41, 6, NB_A, 1.5)
        + nb_line(38, 17, 43, 17, NB_A, 1.5)
    )


def nb_camera(dot):
    return (
        nb_poly(nb_cut(6, 17, 25, 17, 3.5), NB_P, 1.5, 0.12)
        + nb_poly([(31, 22), (42, 16), (42, 35), (31, 29)], NB_P, 1.5, 0.08)
        + nb_circle(13, 12, 4.2, NB_P, 1.4)
        + nb_circle(24, 11, 5.2, NB_P, 1.4)
        + nb_circle(37, 39, 4.3, dot, 1.4, 0.45)
    )


@neon_icon("anim_view")
def _():
    return nb_camera(NB_A)


@neon_icon("anim_view_off")
def _():
    return nb_camera(NB_T)


@neon_icon("anim_scratch")
def _():
    return (
        nb_page(8, 8, 26, 32, NB_P, 5, 3, NB_P)
        + nb_poly([(40, 14), (44, 18), (30, 34), (25, 36), (26, 30)], NB_S, 1.4, 0.2)
    )
