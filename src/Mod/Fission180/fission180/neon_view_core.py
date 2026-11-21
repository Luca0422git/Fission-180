# SPDX-License-Identifier: LGPL-2.1-or-later
"""The pure part of neon_view (no FreeCAD, no Coin): names of the scene nodes Neon Lights adds,
and the colours and sizes of the body outlines, their glow and Hologram bodies
(docs/fission180/neon-lights-design.md 6.6; plan task B6)."""

from . import neon_palette

PREFIX = "Fission180Neon"
EDGE_NODE = PREFIX + "Edge"  # the outline colour, first in each body's "Edge" group
EDGE_BIND = PREFIX + "EdgeBind"
GLOW_NODE = PREFIX + "Glow"  # the glow pass, a separator before the outline in "Edge"
HOLO_NODE = PREFIX + "Hologram"  # the glass material, first in each body's "FlatRoot"
HOLO_BIND = PREFIX + "HologramBind"
RIM_NODE = PREFIX + "Rim"  # the rim-light shader (neon_shader.NODE), after the glass
EDGE_NAMES = (GLOW_NODE, EDGE_NODE, EDGE_BIND)
FLAT_NAMES = (HOLO_NODE, HOLO_BIND, RIM_NODE)

GLOW_WIDTH = 5.0  # the glow line is this many times the body's own line width
GLOW_MIN_WIDTH = 8.0
HOLOGRAM_TRANSPARENCY = 0.72


def is_neon(name):
    """Whether a scene node's name is one of Neon Lights' (every one is removed in Dark)."""
    return bool(name) and name.startswith(PREFIX)


def glow_style(line_width, strength):
    """(line width, transparency) of the glow pass under a body's edges of `line_width`
    pixels, at Glow strength `strength` (0..100): wider than the edge, translucent; stronger
    means less see-through, never fully opaque (the edge itself stays the brightest line)."""
    try:
        width = float(line_width)
    except (TypeError, ValueError):
        width = 2.0
    width = max(1.0, width)
    strength = min(100, max(0, int(strength)))
    transparency = 1.0 - 0.6 * strength / 100.0
    return max(GLOW_MIN_WIDTH, width * GLOW_WIDTH), round(transparency, 3)


def colours(palette, hologram=False):
    """{"edge", "glow", "glass", "glass_glow", "rim"}: "#rrggbb" colours for the body outline,
    its glow, Hologram's glass (diffuse), the glass's faint self-light (emissive) and the rim
    light, from a Neon Lights palette (theme.palette())."""
    outline = palette.get("outline") or palette["primary"]
    background = palette.get("background") or "#000000"
    edge = neon_palette.mix(outline, "#ffffff", 0.25) if hologram else outline
    return {
        "edge": edge,
        "glow": outline,
        "glass": neon_palette.mix(outline, background, 0.82),
        "glass_glow": neon_palette.mix(background, outline, 0.12),
        "rim": outline,
    }


def glow_wanted(effects, glow, hologram):
    """The glow pass is drawn while the Glow effect is on (and the effects' master switch),
    and always on Hologram bodies (their edges glow by design)."""
    return bool(hologram) or (bool(effects) and bool(glow))


def rim_wanted(setting, hologram, self_test_ok):
    """The rim-light shader is used on Hologram bodies when the RimLight setting allows it:
    "off" never, "on" or "auto" only once the self-test passed (a shader that failed it is
    never used: the flat glass is the fallback)."""
    if not hologram or not self_test_ok:
        return False
    return str(setting).lower() in ("auto", "on")
