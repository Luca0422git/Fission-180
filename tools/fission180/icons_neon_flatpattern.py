# SPDX-License-Identifier: LGPL-2.1-or-later
# Neon Lights hand-made icons for icons_flatpattern.py: Rip (a thick square tube that glowed
# into a block), Finish Flat Pattern (a solid disc), and the FLAT PATTERN / unfold buttons. Helpers: icons_neon__kit.py.
# Original line art.
# flake8: noqa


@neon_icon("sm_rip")
def _():
    # a square tube seen from its end, opened by a cut at one corner
    return (
        nb_sheet("M15 8 H40 V40 H8 V15", NB_P, 4.6)
        + nb_line(4, 4, 14, 14, NB_S, 1.8)
    )


@neon_icon("fp_finish")
def _():
    return nb_octagon(24, 24, 16, NB_S, 1.6, 0.16) + nb_check(24, 24, 16, NB_S, 2.6)


@neon_icon("sm_flat_pattern")
def _():
    # a part unfolded into its flat net: the outline, the bend lines dashed
    net = [(15, 5), (33, 5), (33, 15), (43, 15), (43, 33), (33, 33), (33, 43), (15, 43),
           (15, 33), (5, 33), (5, 15), (15, 15)]
    return npoly(net, NP, NW, fo=0.1) + nl(
        "M15 15 H33 V33 H15 Z", NS, NI + 0.2, dash="3 2.2", cap="butt", glow=0.2
    )


@neon_icon("sm_unfold")
def _():
    # the flap standing up, its flat place dashed, the turn that lays it down
    return (
        nb_sheet("M4 40 H22 V12", NP)
        + nseg(27, 40, 45, 40, NS, NI + 0.2, dash="3 2.4", cap="butt", glow=0.2)
        + nl("M28 10 Q42 12 43 29", NS, NW, cap="butt")
        + nhead(43, 34, math.pi / 2, NS, NW, 5)
    )


@neon_icon("sm_refold")
def _():
    # the flap lying flat, its bent place dashed, the turn that stands it up again
    return (
        nb_sheet("M4 40 H44", NP)
        + nseg(22, 35, 22, 8, NS, NI + 0.2, dash="3 2.4", cap="butt", glow=0.2)
        + nl("M42 33 Q42 13 31 10", NS, NW, cap="butt")
        + nhead(26, 9.4, math.pi, NS, NW, 5)
    )
