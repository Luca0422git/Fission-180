# SPDX-License-Identifier: LGPL-2.1-or-later
# Neon Lights hand-made icons for icons_plastic2.py: the lip and the snap fit, cut through.
# Kit and stroke standard: icons_neon__kit.py. Original line art in an industrial sci-fi style.
# flake8: noqa


@neon_icon("pl_lip")
def _():
    # two walls cut through: the lower one's lip sits in the upper one's groove
    return (
        npoly([(9, 44), (9, 30), (20, 30), (20, 22), (27, 22), (27, 30), (39, 30), (39, 44)],
              NP, NW, fo=0.14, close=False)
        + npoly([(9, 4), (9, 26), (16, 26), (16, 17), (31, 17), (31, 26), (39, 26), (39, 4)],
                NS, NW, fo=0.14, close=False, glow=0.3)
    )


@neon_icon("pl_snap_fit")
def _():
    # a flexing hook (cut through) caught under the other part's edge
    return (
        npoly([(4, 44), (26, 44), (26, 37), (4, 37)], NP, NW, fo=0.14)
        + npoly([(9, 37), (9, 6), (14, 6), (21, 14), (21, 18), (14, 18), (14, 37)], NS, NW, fo=0.2, glow=0.3)
        + nl("M44 20 H17 V28 H44", NP, NW, NP, 0.1, cap="butt")
    )
