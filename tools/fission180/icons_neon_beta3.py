# SPDX-License-Identifier: LGPL-2.1-or-later
# Neon Lights hand-made icon for icons_beta3.py: the SIMULATION workspace (seen in the workspace
# menu and on the ribbon). Helpers: icons_neon__kit.py. Original line art.
# flake8: noqa


@neon_icon("workspace_simulation")
def _():
    # a bracket fixed at its foot, its arm glowing from cool (free end) to hot (foot), a load
    # arrow pressing on the arm's tip
    return (
        nb_hatch(6, 40, 16, NB_T)
        + nb_poly([(8, 39), (19, 39), (19, 21), (8, 25)], NB_A, 1.5, 0.30)
        + nb_poly([(19, 21), (31, 17), (31, 24), (19, 28)], NB_P, 1.5, 0.22)
        + nb_poly([(31, 17), (42, 13), (42, 20), (31, 24)], NB_S, 1.5, 0.22)
        + nb_arrow(38, 3, 38, 13, NB_T, 1.6, 4.2)
    )
