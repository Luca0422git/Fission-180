# SPDX-License-Identifier: LGPL-2.1-or-later
# Neon Lights hand-made icons for icons_shell.py: the "+" beside the design tabs, the profile
# button and the Data Panel's project folder (seen all the time in the application bar; their
# thick strokes glowed into fat halos in the automatic copy). Helpers: icons_neon__kit.py.
# Original line art.
# flake8: noqa


@neon_icon("qa_plus")
def _():
    return nb_line(24, 11, 24, 37, NB_T, 2.2) + nb_line(11, 24, 37, 24, NB_T, 2.2)


@neon_icon("qa_profile")
def _():
    # a head and shoulders inside an octagon
    return (
        nb_octagon(24, 24, 18, NB_T, 1.6, 0.0)
        + nb_poly([(21, 12), (27, 12), (29, 14.5), (29, 20), (26.5, 22.5), (21.5, 22.5), (19, 20), (19, 14.5)], NB_T, 1.6, 0.0)
        + nb_path("M12 36 L16 28 H32 L36 36", NB_T, 1.6)
    )


@neon_icon("project")
def _():
    return (
        nb_path("M6 14 H18 L22 18 H42 V35 L39 38 H6 Z", NB_T, 1.7, NB_T, 0.08)
        + nb_line(17, 28, 31, 28, NB_S, 1.8)
        + nb_line(24, 23, 24, 33, NB_S, 1.8)
    )
