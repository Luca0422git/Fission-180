# SPDX-License-Identifier: LGPL-2.1-or-later
# Neon Lights hand-made icons for icons_simresults.py: the report pages (solid sheets of paper
# in the automatic copy) and Finish Results. Helpers: icons_neon__kit.py. Original line art.
# flake8: noqa


def nb_result_strip(x0, x1, y, h=5.0):
    """A thin beam in result bands: cool at the free end, hot at the root."""
    n = 5
    w = (x1 - x0) / n
    out = ""
    for i in range(n):
        c = NB_A if i < 2 else NB_S
        out += rect(x0 + i * w, y, w - 0.8, h, c, 0, 'fill-opacity="%.2f"' % (0.85 - 0.12 * i))
    return out


@neon_icon("simr_report")
def _():
    # a report page: a result bar of four cells (hot on the left) and two lines of text
    out = npage(8, 4, 32, 40, NP, 7, 0)
    for k, (c, fo) in enumerate(((NA, 0.75), (NS, 0.7), (NS, 0.45), (NS, 0.25))):
        x = 13 + k * 6
        out += nf("M%d 15 H%d V21 H%d Z" % (x, x + 4.4, x), c, fo)
    return out + nl("M13 29 H35 M13 36 H28", NT, NI, glow=0.14, cap="butt")


@neon_icon("simr_solver_data")
def _():
    # the solver's numbers: a page with a two-column table
    return npage(8, 4, 32, 40, NP, 7, 0) + nl(
        "M13 17 H35 M13 25 H35 M13 33 H35 M21 13 V39", NT, NI, glow=0.14, cap="butt"
    )


@neon_icon("simr_details")
def _():
    return (
        nb_page(6, 6, 30, 36, NB_P, 6, 0)
        + nb_result_strip(10, 30, 11)
        + nb_line(10, 23, 29, 23, NB_T, 1.4, glow=False)
        + nb_line(10, 28, 25, 28, NB_T, 1.4, glow=False)
        + nb_octagon(36, 36, 8.5, NB_S, 1.4, 0.25)
        + line(36, 34.5, 36, 40.5, NB_S, 2.0)
        + nb_dot(36, 31.5, NB_S, 1.2)
    )


@neon_icon("simr_finish")
def _():
    return nb_octagon(24, 24, 16, NB_S, 1.6, 0.16) + nb_check(24, 24, 16, NB_S, 2.6)


@neon_icon("simr_convergence")
def _():
    # a chart: the value settling onto its target (dashed) step by step
    return (
        nl("M6 4 V42 H44", NT, NW, cap="butt")
        + nseg(6, 14, 44, 14, NP, NI, dash="3 2.4", cap="butt", glow=0.14)
        + nl("M10 38 L17 24 L25 18 L33 15.5 L41 14.5", NS, NW, cap="butt", glow=0.3)
        + ndot(17, 24, NS, 1.9)
        + ndot(25, 18, NS, 1.9)
        + ndot(33, 15.5, NS, 1.9)
    )
