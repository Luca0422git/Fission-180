# SPDX-License-Identifier: LGPL-2.1-or-later
# Neon Lights hand-made icons for the MANUFACTURE area (icons_manufacture.py): the workspace and
# the panels whose pages and plates turned into filled blocks in the automatic copy.
# Helpers: icons_neon__kit.py. Original line art in an industrial sci-fi style.
# flake8: noqa


def nb_mill(cx, top, tip, r=3.4, c=NB_S):
    """An end mill standing upright: an outline with one flute line (secondary: the tool is
    what acts, never a warning)."""
    return npoly([(cx - r, top), (cx + r, top), (cx + r, tip - 2), (cx, tip), (cx - r, tip - 2)], c, NW, 0.18) + nseg(
        cx - r, tip - 10, cx + r, tip - 5, c, NI, glow=0, cap="butt"
    )


@neon_icon("workspace_manufacture")
def _():
    # a plate with the path the tool has cut on its top, and the tool above it
    q = lambda a, b, h: iso(a, b, h, 22, 22, 1.0)  # noqa: E731
    cut = [q(5, 4, 6), q(5, 20, 6), q(12, 20, 6), q(12, 8, 6)]
    return (
        nbox(0, 0, 0, 24, 24, 6, NP, 22, 22, inner=False, fo=0.12)
        + nl(_d(cut), NS, NW, cap="butt", glow=0.3)
        + nb_mill(36, 3, 24, 3.6)
    )


@neon_icon("cam_post")
def _():
    # the program as a page, sent out
    return npage(5, 4, 26, 34, NP, 7, 3, NT) + narrow(22, 42, 45, 42, NS, NW, 5.5)


@neon_icon("cam_sheet")
def _():
    # a setup sheet: a page with the part on it and a short table
    return (
        npage(7, 3, 32, 42, NP, 7, 0)
        + nbox(0, 0, 0, 10, 10, 5, NS, 22, 13, fo=0.2, inner=False)
        + nl("M12 31 H34 M12 38 H34 M22 27 V42", NT, NI, glow=0.14, cap="butt")
    )
