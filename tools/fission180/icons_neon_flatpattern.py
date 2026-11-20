# SPDX-License-Identifier: LGPL-2.1-or-later
# Neon Lights hand-made icons for icons_flatpattern.py: Rip (a thick square tube that glowed
# into a block) and Finish Flat Pattern (a solid disc). Helpers: icons_neon__kit.py.
# Original line art.
# flake8: noqa


@neon_icon("sm_rip")
def _():
    # a square tube seen from its end, opened by a cut at one corner
    return (
        nb_sheet("M15 8 H40 V40 H8 V15", NB_P, 4.6)
        + nb_line(5, 5, 14, 14, NB_A, 1.8)
        + nb_line(8, 3.5, 3.5, 8, NB_A, 1.0, glow=False)
    )


@neon_icon("fp_finish")
def _():
    return nb_octagon(24, 24, 16, NB_S, 1.6, 0.16) + nb_check(24, 24, 16, NB_S, 2.6)
