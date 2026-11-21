# SPDX-License-Identifier: LGPL-2.1-or-later
# Neon Lights hand-made icons for icons_sheetmetal2.py: the hem and joint-bend icons draw the
# sheet as a thick stroke, which glowed into a fat tube in the automatic copy. Here a sheet is a
# hollow double line (its two faces: nb_sheet), the industrial way. Helpers: icons_neon__kit.py.
# Original line art.
# flake8: noqa


@neon_icon("sm_hem")
def _():
    return (
        nb_sheet("M6 30 H30", NB_P)
        + nb_sheet("M30 30 A6 6 0 0 0 30 18 H14", NB_S)
        + nb_line(14, 38, 30, 38, NB_T, 1.2, glow=False)
        + line(14, 36, 14, 40, NB_T, 1.2) + line(30, 36, 30, 40, NB_T, 1.2)
    )


@neon_icon("sm_join_bend")
def _():
    return (
        nb_sheet("M6 36 H22", NB_P)
        + nb_sheet("M34 26 V8", NB_P)
        + nb_sheet("M22 36 H26 A8 8 0 0 0 34 28 V26", NB_S)
        + nb_dot(22, 36, NB_T, 2.0)
        + nb_dot(34, 26, NB_T, 2.0)
    )


@neon_icon("sm_fillet")
def _():
    plate = [iso(-14, -14, 0), iso(14, -14, 0), iso(14, 6, 0), iso(6, 14, 0), iso(-14, 14, 0)]
    d = "M%.2f %.2f Q%.2f %.2f %.2f %.2f" % (*iso(14, 2, 0), *iso(14, 14, 0), *iso(2, 14, 0))
    return nb_poly(plate, NB_P, 1.4, 0.14) + nb_path(d, NB_S, 2.2)


@neon_icon("sm_chamfer")
def _():
    plate = [iso(-14, -14, 0), iso(14, -14, 0), iso(14, 4, 0), iso(4, 14, 0), iso(-14, 14, 0)]
    return nb_poly(plate, NB_P, 1.4, 0.14) + nb_line(*iso(14, 4, 0), *iso(4, 14, 0), c=NB_S, w=2.2)


@neon_icon("sm_bend")
def _():
    # the flat part, the flap bent up about the bend, the flap's flat place dashed, the turn
    return (
        nb_sheet("M4 38 H22", NP)
        + nb_sheet("M22 38 Q28 38 30 32 L36 14", NS)
        + nseg(31, 38, 45, 38, NS, NI, dash="3 2.4", cap="butt", glow=0.14)
        + nl("M45 32 Q46 23 42 18", NS, NW, cap="butt")
        + nhead(41, 16, math.radians(-125), NS, NW, 5)
    )
