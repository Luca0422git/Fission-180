# SPDX-License-Identifier: LGPL-2.1-or-later
# Neon Lights hand-made icons for the MANUFACTURE area (icons_manufacture.py): the workspace and
# the panels whose pages and plates turned into filled blocks in the automatic copy.
# Helpers: icons_neon__kit.py. Original line art in an industrial sci-fi style.
# flake8: noqa


def nb_mill(cx, top, tip, r=3.4, c=NB_A):
    """An end mill standing upright, drawn as an outline with two flute lines."""
    return (
        nb_poly([(cx - r, top), (cx + r, top), (cx + r, tip), (cx - r, tip)], c, 1.4, 0.18)
        + line(cx - r, tip - 7, cx + r, tip - 4, c, 1.0)
        + line(cx - r, tip - 11, cx + r, tip - 8, c, 1.0)
    )


@neon_icon("workspace_manufacture")
def _():
    # a plate with the zig-zag the tool has cut on its top, and the tool still cutting
    pts = [iso(x, y, 6, 24, 33) for x, y in [(4, 4), (20, 4), (20, 10), (4, 10), (4, 16), (20, 16)]]
    d = "M%.2f %.2f " % pts[0] + " ".join("L%.2f %.2f" % p for p in pts[1:])
    return (
        nb_box(0, 0, 0, 24, 24, 6, NB_P, 24, 33)
        + nb_path(d, NB_S, 1.6)
        + nb_mill(30, 3, 25, 3.4)
        + nb_dot(30, 27.5, NB_S, 1.5)
    )


@neon_icon("cam_post")
def _():
    # the program as a page, sent out
    return nb_page(7, 5, 24, 32, NB_P, 6, 4, NB_T) + nb_arrow(24, 40, 43, 40, NB_S, 1.8, 5)


@neon_icon("cam_sheet")
def _():
    # a setup sheet: a page with a small plate on it and a table
    return (
        nb_page(9, 4, 30, 40, NB_P, 6, 0)
        + nb_box(0, 0, 0, 9, 9, 3, NB_S, 24, 14, glow=False)
        + nb_line(13, 29, 35, 29, NB_T, 1.2, glow=False)
        + nb_line(13, 35, 35, 35, NB_T, 1.2, glow=False)
        + nb_line(24, 26, 24, 39, NB_T, 1.2, glow=False)
    )
