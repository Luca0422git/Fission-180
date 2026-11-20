# SPDX-License-Identifier: LGPL-2.1-or-later
# Neon Lights hand-made icons for the SIMULATION area (icons_simulation.py): the study row of the
# browser, the stage and pre-check status marks (solid discs in the normal set, thick glowing
# rings in the automatic neon copy) and the result / solve / job panels. The workspace icon
# itself is in icons_neon_beta3.py. Helpers: icons_neon__kit.py.
# Original line art in an industrial sci-fi style.
# flake8: noqa


def nb_stress(x, y, w, h, n=5):
    """A result legend as a segmented bar: low (secondary, dim) at the bottom, high (alert) on top."""
    gap = 1.0
    ch = (h - gap * (n - 1)) / n
    out = nb_poly(nb_cut(x - 1.2, y - 1.2, w + 2.4, h + 2.4, 1.6), NB_P, 0.9, 0, glow=False)
    for i in range(n):
        c = NB_A if i >= n - 2 else NB_S
        cy = y + h - (i + 1) * ch - i * gap
        out += rect(x, cy, w, ch, c, 0, 'fill-opacity="%.2f"' % (0.35 + 0.6 * i / (n - 1)))
    return out


def nb_beam(c_root=NB_P, c_arm=NB_S):
    """The study's bracket: a fixed foot, a column and an arm reaching right."""
    return (
        nb_hatch(7, 38, 22, NB_T)
        + nb_poly([(11, 37), (25, 37), (25, 17), (11, 22)], c_root, 1.5, 0.14)
        + nb_poly([(25, 17), (40, 12), (40, 19), (25, 24)], c_arm, 1.5, 0.22)
    )


@neon_icon("sim_study")
def _():
    return nb_beam() + nb_stress(35, 24, 5, 14)


def nb_clip(c=NB_P):
    """A clipboard: cut-corner board with a clip at the top."""
    return (
        nb_poly(nb_cut(10, 7, 26, 35, 4), c, 1.5, 0.10)
        + nb_poly(nb_cut(17, 4, 12, 5, 1.5), c, 1.3, 0.3, glow=False)
    )


@neon_icon("sim_precheck")
def _():
    return (
        nb_clip()
        + nb_line(15, 17, 31, 17, NB_T, 1.4, glow=False)
        + nb_line(15, 24, 31, 24, NB_T, 1.4, glow=False)
        + nb_line(15, 31, 25, 31, NB_T, 1.4, glow=False)
    )


@neon_icon("sim_precheck_ok")
def _():
    return nb_clip() + nb_line(15, 17, 29, 17, NB_T, 1.4, glow=False) + nb_ok_badge(31, 33, 9.5)


@neon_icon("sim_precheck_warn")
def _():
    return nb_clip() + nb_line(15, 17, 29, 17, NB_T, 1.4, glow=False) + nb_warn_badge(31, 33, 17)


@neon_icon("sim_precheck_error")
def _():
    return nb_clip() + nb_line(15, 17, 29, 17, NB_T, 1.4, glow=False) + nb_bad_badge(31, 33, 9.5)


@neon_icon("sim_stage_done")
def _():
    return nb_octagon(24, 24, 15, NB_S, 1.6, 0.16) + nb_check(24, 24, 15, NB_S, 2.4)


@neon_icon("sim_stage_failed")
def _():
    return nb_octagon(24, 24, 15, NB_A, 1.6, 0.16) + nb_xmark(24, 24, 14, NB_A, 2.4)


@neon_icon("sim_stage_waiting")
def _():
    # a dim octagon with three dots: still in the queue
    return (nb_octagon(24, 24, 15, NB_P, 1.4, 0.06)
            + nb_dot(17, 24, NB_P, 1.6) + nb_dot(24, 24, NB_P, 1.6) + nb_dot(31, 24, NB_P, 1.6))


@neon_icon("sim_stage_running")
def _():
    # a ring of eight segments, three of them lit: a spinner
    out = ""
    for i in range(8):
        a0 = math.radians(-90 + i * 45 + 6)
        a1 = math.radians(-90 + i * 45 + 39)
        x0, y0 = 24 + 14 * math.cos(a0), 24 + 14 * math.sin(a0)
        x1, y1 = 24 + 14 * math.cos(a1), 24 + 14 * math.sin(a1)
        if i < 3:
            out += nb_line(x0, y0, x1, y1, NB_S, 3.0)
        else:
            out += line(x0, y0, x1, y1, NB_S, 2.2, 'stroke-opacity="0.35"')
    return out


@neon_icon("sim_solve")
def _():
    # a monitor with a play mark on its screen
    return (
        nb_poly(nb_cut(4, 8, 40, 26, 4), NB_P, 1.6, 0.10)
        + nb_poly([(19, 14), (19, 28), (31, 21)], NB_S, 1.6, 0.3)
        + nb_line(24, 34, 24, 38, NB_P, 1.6)
        + nb_line(14, 40, 34, 40, NB_P, 1.8)
    )


@neon_icon("sim_job_status")
def _():
    return (
        nb_poly(nb_cut(4, 7, 40, 34, 4), NB_P, 1.6, 0.08)
        + nb_line(10, 15, 26, 15, NB_T, 1.6, glow=False)
        + nb_line(10, 21, 22, 21, NB_T, 1.6, glow=False)
        + nb_segments(10, 29, 28, 5, 6, [NB_S, NB_S, NB_S, NB_S])
        + nb_check(35, 17, 7, NB_S, 1.8)
    )


@neon_icon("sim_results")
def _():
    # the bracket's arm in three result bands, and the legend
    return (
        nb_poly([(6, 38), (28, 38), (28, 14), (6, 22)], NB_P, 1.4, 0.06)
        + poly([(6, 22), (28, 14), (28, 22), (6, 30)], NB_S, 'fill-opacity="0.30"')
        + poly([(6, 30), (28, 22), (28, 30), (6, 38)], NB_A, 'fill-opacity="0.40"')
        + line(6, 30, 28, 22, NB_A, 1.0) + line(6, 22, 28, 14, NB_S, 1.0)
        + nb_stress(34, 10, 6, 28)
    )


@neon_icon("sim_settings")
def _():
    # a cog drawn as an outline (the automatic copy filled its middle into a blob)
    pts = []
    for i in range(24):
        r = 17 if i % 3 != 2 else 12.5
        a = math.radians(i * 15 + 7.5)
        pts.append((24 + r * math.cos(a), 24 + r * math.sin(a)))
    return nb_poly(pts, NB_P, 1.5, 0.10) + nb_circle(24, 24, 5.5, NB_S, 1.6)
