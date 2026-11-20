# SPDX-License-Identifier: LGPL-2.1-or-later
# Neon Lights hand-made icon for icons_rebuild.py: Finish Rebuild (its solid check disc).
# Helpers: icons_neon__kit.py. Original line art.
# flake8: noqa


@neon_icon("rebuild_finish")
def _():
    return (
        nb_box(0, 0, 0, 20, 14, 12, NB_S, 22, 27)
        + nb_poly(nb_cut(4, 39, 26, 6, 1.5), NB_P, 1.2, 0.10)
        + rect(7, 40.6, 5, 2.8, NB_S, 0) + rect(14, 40.6, 5, 2.8, NB_S, 0) + rect(21, 40.6, 5, 2.8, NB_S, 0)
        + nb_ok_badge(37, 36, 8.5)
    )
