# SPDX-License-Identifier: LGPL-2.1-or-later
# Neon Lights hand-made icon for the VIEW workspace (icons_view.py): a wireframe part floating in
# front of a pair of XR glasses. Helpers: icons_neon__kit.py. Original line art.
# flake8: noqa


@neon_icon("workspace_view")
def _():
    lens = "M%(x)s 30 H%(x2)s Q%(x3)s 30 %(x3)s 34 Q%(x3)s 40 %(x2)s 40 H%(x)s Q%(x0)s 40 %(x0)s 34 Q%(x0)s 30 %(x)s 30 Z"
    left = lens % {"x0": 5, "x": 9, "x2": 18, "x3": 22}
    right = lens % {"x0": 26, "x": 30, "x2": 39, "x3": 43}
    return (
        nb_box(0, 0, 0, 10, 10, 9, NB_S, 24, 21)
        + nb_path(left, NB_P, fo=0.10)
        + nb_path(right, NB_P, fo=0.10)
        + nb_path("M22 33 Q24 30.5 26 33", NB_P, fo=0.0)
        + nb_line(5, 32, 2.5, 29.5, NB_P)
        + nb_line(43, 32, 45.5, 29.5, NB_P)
    )
