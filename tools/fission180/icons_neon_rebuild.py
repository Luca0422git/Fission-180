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


@neon_icon("rebuild_ai")
def _():
    # the part still to be built (dashed wireframe) and the assistant's spark
    q = lambda a, b, h: iso(a, b, h, 21, 30, 1.0)  # noqa: E731
    sil = [q(0, 0, 14), q(16, 0, 14), q(16, 0, 0), q(16, 16, 0), q(0, 16, 0), q(0, 16, 14)]
    near = q(16, 16, 14)
    spark = "M38 4 L40 11 L46 13 L40 15 L38 22 L36 15 L30 13 L36 11 Z"
    return (
        nl(_d(sil, True), NP, NW, NP, 0.08, dash="4.5 2.5", cap="butt")
        + nl(_d([sil[0], near, sil[2]]) + " " + _d([near, sil[4]]), NP, NI, dash="4 2.5", glow=0.12, cap="butt")
        + nl(spark, NS, NI, NS, 0.55, glow=0.34)
    )


@neon_icon("rebuild_compare")
def _():
    # the rebuilt part over the original (dashed): the difference shows
    q = lambda a, b, h: iso(a, b, h, 28, 26, 1.0)  # noqa: E731
    sil = [q(0, 0, 14), q(16, 0, 14), q(16, 0, 0), q(16, 16, 0), q(0, 16, 0), q(0, 16, 14)]
    return (
        nl(_d(sil, True), NS, NW, dash="3.2 2.2", cap="butt", glow=0.2)
        + nbox(0, 0, 0, 16, 16, 14, NP, 20, 32, fo=0.14)
    )
