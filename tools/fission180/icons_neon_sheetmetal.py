# SPDX-License-Identifier: LGPL-2.1-or-later
# Neon Lights hand-made icons for icons_sheetmetal.py: the SHEET METAL tab's visible buttons
# (flange, rules) and the browser's sheet metal body. A sheet seen edge-on is a hollow double
# line (nb_sheet), as in the other sheet metal icons.
# Kit and stroke standard: icons_neon__kit.py. Original line art in an industrial sci-fi style.
# flake8: noqa


@neon_icon("sheet_metal_body")
def _():
    # a U-channel: its front edge as a sheet, its depth as three thin receding edges
    return (
        nl("M17 8 V27 H41 V8", NP, NI, glow=0.14, cap="butt")
        + nl("M9 14 L17 8 M33 14 L41 8 M33 33 L41 27", NP, NI, glow=0.14, cap="butt")
        + nb_sheet("M9 14 V33 H33 V14", NP, 4.4)
    )


@neon_icon("sm_flange")
def _():
    # a flat plate and the flange standing up along its back edge
    q = lambda a, b, h: iso(a, b, h, 20, 24, 1.0)  # noqa: E731
    plate = [q(0, 0, 0), q(22, 0, 0), q(22, 16, 0), q(0, 16, 0)]
    flange = [q(0, 0, 0), q(22, 0, 0), q(22, 0, 15), q(0, 0, 15)]
    return (
        npoly(plate, NP, NW, fo=0.14)
        + npoly(flange, NS, NW, fo=0.2, glow=0.3)
        + narrow(9, 30, 9, 13, NS, NI + 0.4, 4.5)
    )


@neon_icon("sm_rules")
def _():
    # the sheet's rules: a bent sheet and its thickness "T"
    return (
        nb_sheet("M6 40 H20 Q28 40 28 32 V8", NP, 4.4)
        + nl("M33 12 H45 M39 12 V30", NS, NW + 0.2, cap="butt", glow=0.32)
    )
