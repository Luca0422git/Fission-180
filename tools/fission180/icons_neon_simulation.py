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
    # the study row: the bracket on its wall and a result scale (hot cell on top)
    return (
        nseg(8, 8, 8, 40, NP, NW, cap="butt")
        + nl("M8 12 L3 17 M8 22 L3 27 M8 32 L3 37", NP, NI, glow=0.14, cap="butt")
        + npoly([(8, 15), (30, 15), (30, 24), (8, 24)], NP, NW, fo=0.14, close=False)
        + nf("M8 15 H17 V24 H8 Z", NS, 0.4)
        + npoly([(35, 8), (43, 8), (43, 40), (35, 40)], NS, NW)
        + nf("M35 8 H43 V18 H35 Z", NA, 0.6)
        + nseg(35, 24, 43, 24, NS, NI, glow=0, cap="butt")
    )


def nb_clip(c=NB_P):
    """A clipboard: cut-corner board with a clip at the top."""
    return ncut(9, 7, 28, 36, c, 4, fo=0.08) + ncut(17, 3.5, 12, 6, c, 1.5, NI, fo=0.3)


@neon_icon("sim_precheck")
def _():
    return (
        nb_clip()
        + nl("M14 17 H32 M14 24 H32 M14 31 H25", NT, NI, glow=0.14, cap="butt")
        + ndot(29, 31, NS, 1.6)
    )


@neon_icon("sim_precheck_ok")
def _():
    return nb_clip() + nseg(14, 17, 27, 17, NT, NI, glow=0.14, cap="butt") + nb_ok_badge(31, 33, 9.5)


@neon_icon("sim_precheck_warn")
def _():
    return nb_clip() + nseg(14, 17, 27, 17, NT, NI, glow=0.14, cap="butt") + nb_warn_badge(31, 33, 17)


@neon_icon("sim_precheck_error")
def _():
    return nb_clip() + nseg(14, 17, 27, 17, NT, NI, glow=0.14, cap="butt") + nb_bad_badge(31, 33, 9.5)


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
    # the bracket in result bands (hot at the root) and the scale beside it
    return (
        npoly([(5, 38), (27, 38), (27, 14), (5, 22)], NP, NW, fo=0.0)
        + nf("M5 30 L27 22 L27 38 L5 38 Z", NA, 0.35)
        + nf("M5 22 L27 14 L27 22 L5 30 Z", NS, 0.25)
        + nseg(5, 30, 27, 22, NP, NI, glow=0, cap="butt")
        + npoly([(34, 8), (42, 8), (42, 40), (34, 40)], NS, NW)
        + nf("M34 8 H42 V18 H34 Z", NA, 0.6)
        + nseg(34, 24, 42, 24, NS, NI, glow=0, cap="butt")
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


def nb_ring(cx, cy, r, c=NB_P):
    """A thick ring (a pin's eye, a bearing) as two thin concentric lines."""
    return nb_circle(cx, cy, r + 2, c, 1.4, 0.12) + circle(cx, cy, r - 2, "none", c, 1.4)


@neon_icon("sim_pin")
def _():
    # a pin through an eye: the ring as two thin circles, the pin's axis across it
    return (
        ncircle(24, 24, 15, NP, NW, 0.08)
        + ncircle(24, 24, 7, NS, NW, 0.25)
        + nseg(24, 3, 24, 45, NS, NI, dash="4 2.5", cap="butt", glow=0.2)
    )


@neon_icon("sim_bearing")
def _():
    return nb_ring(24, 27, 14) + nb_arrow(24, 2, 24, 31, NB_S, 2.0, 6.5)


@neon_icon("sim_moment")
def _():
    # a turning load: an angular arc with its head, round the point it acts on (secondary, like
    # every other load: a load is not a warning)
    return (
        nl("M14 33 L9 24 L14 14 L24 9 L34 14 L39 24 L35 32", NS, NW + 0.2, cap="butt")
        + nhead(29, 37, math.radians(145), NS, NW, 6)
        + ndot(24, 24, NT, 2.6)
    )


@neon_icon("sim_rigid_connector")
def _():
    out = nb_circle(24, 24, 16, NB_P, 1.6)
    for i in range(6):
        a = math.radians(i * 60 + 15)
        x, y = 24 + 16 * math.cos(a), 24 + 16 * math.sin(a)
        out += line(24, 24, x, y, NB_S, 1.2) + nb_dot(x, y, NB_S, 2.4)
    return out + nb_octagon(24, 24, 4, NB_S, 1.2, 0.5)


@neon_icon("sim_bolt")
def _():
    # a bolt clamping two plates: hex head, shank, nut; the plates in the load's colour
    return (
        npoly([(13, 4), (35, 4), (35, 11), (13, 11)], NP, NW, fo=0.14)
        + nl("M20.5 4 V11 M27.5 4 V11", NP, NI, glow=0, cap="butt")
        + nl("M6 15 H42 V22 H6 Z M6 25 H42 V32 H6 Z", NS, NW, NS, 0.14, glow=0.3)
        + npoly([(20, 11), (28, 11), (28, 44), (20, 44)], NP, NW, close=False)
        + npoly([(14, 35), (34, 35), (34, 41), (14, 41)], NP, NW, fo=0.14)
    )


@neon_icon("sim_attributes")
def _():
    # a table of attributes: a header row and two rows
    return (
        ncut(4, 7, 40, 34, NP, 4, fo=0.06)
        + nf("M4 7 H44 V16 H4 Z", NP, 0.3)
        + nl("M4 16 H44 M4 28.5 H44 M18 7 V41", NP, NI, glow=0.14, cap="butt")
        + ndot(11, 22.3, NS, 1.8)
        + ndot(11, 34.8, NS, 1.8)
    )
