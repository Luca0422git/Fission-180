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
    return (
        nb_page(10, 5, 29, 38, NB_P, 7, 0)
        + nb_result_strip(14, 34, 15)
        + nb_line(14, 29, 34, 29, NB_T, 1.4, glow=False)
        + nb_line(14, 34, 34, 34, NB_T, 1.4, glow=False)
        + nb_line(14, 39, 27, 39, NB_T, 1.4, glow=False)
    )


@neon_icon("simr_solver_data")
def _():
    out = nb_page(10, 5, 29, 38, NB_P, 7, 0)
    for k in range(5):
        out += line(14, 17 + k * 5, 35, 17 + k * 5, NB_T, 1.2)
    return out + line(22, 15, 22, 39, NB_T, 1.0)


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
