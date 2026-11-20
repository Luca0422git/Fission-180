# SPDX-License-Identifier: LGPL-2.1-or-later
# Neon Lights hand-made icon for icons_beta3.py: the SIMULATION workspace (seen in the workspace
# menu and on the ribbon). Helpers: icons_neon__kit.py (the set's one kit). Original line art.
# flake8: noqa


@neon_icon("workspace_simulation")
def _():
    # a bracket fixed to a wall, glowing strongest at its root, its bent shape dashed under it,
    # and the load pressing on its tip
    return (
        nseg(8, 5, 8, 43, NP, NW, cap="butt")
        + nl("M8 9 L3 14 M8 18 L3 23 M8 27 L3 32 M8 36 L3 41", NP, NI, glow=0.14, cap="butt")
        + nf("M8 16 H20 V25 H8 Z", NS, 0.45)
        + nf("M20 16 H30 V25 H20 Z", NS, 0.22)
        + npoly([(8, 16), (41, 16), (41, 25), (8, 25)], NP, NW, close=False)
        + nl("M8 31 Q28 32 41 39", NS, NI, dash="3.2 2.4", cap="butt", glow=0.2)
        + narrow(41, 2, 41, 14, NS, NW, 5)
    )


