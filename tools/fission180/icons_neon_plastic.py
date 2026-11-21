# SPDX-License-Identifier: LGPL-2.1-or-later
# Neon Lights hand-made icons for icons_plastic.py: the PLASTIC tab's visible buttons (assign,
# rules, boss, rest, manage).
# Kit and stroke standard: icons_neon__kit.py. Original line art in an industrial sci-fi style.
# flake8: noqa


def nb_card(x, y, w, h, c=NB_S, rows=2):
    """A rules card: a small cut-corner panel with a few short lines."""
    out = ncut(x, y, w, h, c, 3, fo=0.12)
    for i in range(rows):
        ly = y + 5 + i * 5.5
        out += nseg(x + 3.5, ly, x + w - 3.5, ly, c, NI, cap="butt", glow=0.14)
    return out


@neon_icon("pl_assign")
def _():
    # a rules card handed to a part
    return (
        nbox(0, 0, 0, 16, 16, 13, NP, 18, 30, fo=0.14)
        + nb_card(28, 4, 16, 14)
        + narrow(32, 21, 25, 28, NS, NW, 4.6)
    )


@neon_icon("pl_rule_fillet")
def _():
    # the fillet rule: a rounded inside corner and its card
    return (
        nl("M6 8 V40 H34", NP, NW, cap="butt")
        + nl("M6 26 Q6 40 20 40", NS, NW + 0.4, cap="butt", glow=0.34)
        + ndot(6, 26, NS, 1.8)
        + ndot(20, 40, NS, 1.8)
        + nb_card(22, 5, 20, 17)
    )


@neon_icon("pl_boss")
def _():
    # a plate with a hollow round boss standing on it
    top = "M17 15 A7 3.6 0 1 0 31 15 A7 3.6 0 1 0 17 15 Z"
    hole = "M21.5 15 A2.5 1.3 0 1 0 26.5 15 A2.5 1.3 0 1 0 21.5 15 Z"
    return (
        nbox(0, 0, 0, 22, 22, 4, NP, 24, 20, inner=False, fo=0.1)
        + nl("M17 15 V29 A7 3.6 0 0 0 31 29 V15", NS, NW, NG, 0.9, cap="butt")
        + nl(top, NS, NW, NS, 0.2, cap="butt")
        + nl(hole, NS, NI, NG, 1.0, glow=0)
    )


@neon_icon("pl_rest")
def _():
    # a wall with a small ledge, and the part resting on it (dashed)
    return (
        npoly([(6, 6), (14, 6), (14, 42), (6, 42)], NP, NW, fo=0.12)
        + npoly([(14, 26), (26, 26), (26, 30), (14, 37)], NS, NW, fo=0.25, glow=0.3)
        + nl("M18 21 H43 V12 H18 Z", NP, NI + 0.2, dash="3 2.2", cap="butt", glow=0.14)
    )


@neon_icon("pl_manage")
def _():
    # two rules cards and a pencil
    return (
        ncut(4, 4, 24, 28, NP, 4, fo=0.06)
        + nb_card(11, 12, 24, 30, NP, 3)
        + npoly([(40, 14), (45, 19), (31, 33), (25, 35), (27, 29)], NS, NW, fo=0.2, glow=0.3)
    )
