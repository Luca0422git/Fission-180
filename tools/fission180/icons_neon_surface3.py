# SPDX-License-Identifier: LGPL-2.1-or-later
# Neon Lights hand-made icon for icons_surface3.py: the environment map (a grey ball with soft
# light strips, which turned into a muddy disc). Here a wire globe catching three light bands.
# Helpers: icons_neon__kit.py. Original line art.
# flake8: noqa


@neon_icon("environment_map")
def _():
    return (
        nb_circle(24, 24, 15, NB_P, 1.6, 0.10)
        + ellipse(24, 15, 10.5, 2.6, "none", NB_T, 1.4)
        + ellipse(24, 24, 14, 2.6, "none", NB_S, 1.6)
        + ellipse(24, 32.5, 10.5, 2.2, "none", NB_S, 1.2)
        + nb_dot(18, 18.5, NB_T, 1.8)
    )
