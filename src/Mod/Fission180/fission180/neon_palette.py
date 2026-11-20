# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights colours (docs/fission180/neon-lights-design.md, 6.2). Pure logic: no FreeCAD,
no Qt.

A look is six roles (primary, secondary, alert, background, text, outline); every other colour
of the look (panels, lines, hover, grid, arrows...) is derived from them here, so a preset is a
handful of values and a person's own colours work everywhere. The preset names are references
only: no logos, artwork, fonts or quotes from the works they are named after.
"""

import hashlib
import json
import re

ROLES = ("primary", "secondary", "alert", "background", "text", "outline")

_P = lambda name, after, primary, secondary, alert, background, text: {  # noqa: E731
    "name": name,
    "after": after,
    "primary": primary,
    "secondary": secondary,
    "alert": alert,
    "background": background,
    "text": text,
}

PRESETS = {
    "johnny": _P("Johnny", "yellow and electric blue, after Johnny of Cyberpunk 2077",
                 "#fcee0a", "#00c2ff", "#ff3b3b", "#0b0d14", "#f3f1d8"),
    "v": _P("V", "neon red and cyan-blue, after V of Cyberpunk 2077",
            "#ff003c", "#00e5ff", "#ffb000", "#0a0b12", "#f2f4ff"),
    "night_city": _P("Night City", "hot pink and cyan, the classic cyberpunk pair",
                     "#ff2a6d", "#05d9e8", "#ffd319", "#0b0a1f", "#d1f7ff"),
    "judy": _P("Judy", "magenta and teal, after Judy of Cyberpunk 2077",
               "#ff4fd8", "#2df5c8", "#ffb000", "#0d0a16", "#f6eefc"),
    "arasaka": _P("Arasaka", "blood red and steel, after Cyberpunk 2077's corporation",
                  "#ff1e1e", "#e6e8eb", "#ffb000", "#0a0a0a", "#ececec"),
    "the_grid": _P("The Grid", "cyan and orange, after Tron: Legacy",
                   "#6ff3ff", "#ff9a1f", "#ff3b3b", "#050a10", "#e6fbff"),
    "replicant": _P("Replicant", "orange haze and teal, after Blade Runner 2049",
                    "#ff7a18", "#19c3b3", "#ff3b3b", "#0d0906", "#fbe9d9"),
    "red_pill": _P("Red Pill", "falling-code green, after The Matrix",
                   "#00ff41", "#00b32c", "#ffcc00", "#000000", "#d6ffe0"),
    "kaneda": _P("Kaneda", "red and sky blue, after Akira",
                 "#ff2340", "#42c8ff", "#ffc400", "#0b0a10", "#fff2e6"),
    "section_9": _P("Section 9", "aqua and violet, after Ghost in the Shell",
                    "#00ffc8", "#9b5cff", "#ff4d6d", "#050b0d", "#e0fff8"),
    "outrun": _P("Outrun", "magenta and sunset orange, synthwave",
                 "#ff2bd6", "#ffb000", "#ff3b3b", "#120326", "#fbe6ff"),
    "vaporwave": _P("Vaporwave", "pink and cyan, vaporwave",
                    "#ff71ce", "#01cdfe", "#fffb96", "#1a1033", "#f5e9ff"),
    "miami": _P("Miami", "pink and aqua, after Hotline Miami",
                "#ff3ea5", "#00f6ff", "#ffd23f", "#0e0614", "#ffeaf6"),
    "pip_boy": _P("Pip-Boy", "phosphor green, after Fallout",
                  "#18ff6d", "#a8ffc8", "#ffcc33", "#000000", "#c9ffdb"),
    "mainframe": _P("Mainframe", "amber, after old amber terminals",
                    "#ffb000", "#ffe0a0", "#ff5a36", "#0a0700", "#ffe9bf"),
    "augmented": _P("Augmented", "gold and orange, after Deus Ex",
                    "#f7b500", "#ff7a00", "#ff3b30", "#0a0805", "#fff3d6"),
    "upside_down": _P("Upside Down", "red and blue, after Stranger Things",
                      "#ff1e1e", "#3d6bff", "#ffcc00", "#07070d", "#f0eef5"),
}
ORDER = (
    "johnny", "v", "night_city", "judy", "arasaka", "the_grid", "replicant", "red_pill",
    "kaneda", "section_9", "outrun", "vaporwave", "miami", "pip_boy", "mainframe",
    "augmented", "upside_down",
)
DEFAULT = "v"

# Keys of theme.DARK (the panels' colours), in the order they are made unique.
THEME_KEYS = (
    "chrome", "menu", "view", "text", "text_dim", "disabled", "hover", "active", "line",
    "accent", "field", "button", "header", "alternate", "tree_hover", "handle", "check",
    "check_line", "marker", "bright",
)
# Neon's own keys (frames, icons, the 3D view).
NEON_KEYS = (
    "primary", "secondary", "alert", "outline", "background", "primary_dim", "primary_hot",
    "secondary_dim", "secondary_hot", "glow", "panel", "grid_minor", "grid_major", "select",
    "preselect", "arrow", "arrow_hot", "cut",
)
# Colours of the dark and light looks: a neon panel colour never equals one of them, so
# theme.translate() can always tell which look a style sheet was written in. White and black
# are never swapped by the theme, so they may be shared.
_TAKEN = {
    # theme.DARK and theme.LIGHT
    "#3b4453", "#454f61", "#2a2a2a", "#f5f5f5", "#c3cad4", "#7d8593", "#56647a", "#354a63",
    "#56606f", "#3fa9f5", "#2f3540", "#4a5568", "#2f3643", "#303030", "#3a4252", "#5d6778",
    "#2b313b", "#8a94a3", "#e8e8e8", "#f0f2f5", "#f7f8fa", "#1f2329", "#5b6573", "#9aa3ae",
    "#dde5ef", "#cde2f7", "#c9ced6", "#e6eaf0", "#e3e7ec", "#f4f6f8", "#e8eef5", "#b8bfc9",
    # theme._EXTRA (both sides)
    "#343a46", "#e3e8ef", "#3b4250", "#d5dae1", "#b8c7d9", "#4a5a70", "#8cc4ff", "#1f6fbf",
    "#9aa4b1", "#9aa4b2", "#9aa4b5", "#5f6977", "#8a94a6", "#9fb3c8", "#4f6378", "#b8c4d0",
    "#4f5b68", "#b9bec6", "#9fb4cc", "#3d5f85", "#ff8a80", "#c62828", "#ef6f6c", "#ff6b6b",
    "#ff5c5c", "#ffb74d", "#a35f00", "#ffcc66", "#8a6100", "#9fe0a0", "#9fe0a8", "#7fd18b",
    "#2e7d32", "#63b3ff", "#4da3ff", "#5aa0e6", "#1f78c8", "#5a4a2a", "#fff1d6", "#dfe3e8",
}

_HEX = re.compile(r"^#[0-9a-fA-F]{6}$")


def valid_hex(text):
    return isinstance(text, str) and bool(_HEX.match(text.strip()))


def _rgb(colour):
    colour = colour.strip().lstrip("#")
    return tuple(int(colour[i : i + 2], 16) for i in (0, 2, 4))


def _hex(rgb):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(round(c)))) for c in rgb)


def mix(a, b, t):
    """`a` moved by `t` (0..1) toward `b`."""
    ra, rb = _rgb(a), _rgb(b)
    return _hex([ra[i] + (rb[i] - ra[i]) * t for i in range(3)])


def rgba(colour, alpha):
    r, g, b = _rgb(colour)
    return "rgba(%d, %d, %d, %s)" % (r, g, b, ("%.3f" % alpha).rstrip("0").rstrip("."))


def rgb01(colour):
    return tuple(c / 255.0 for c in _rgb(colour))


def _luminance(colour):
    def channel(c):
        c = c / 255.0
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = (channel(c) for c in _rgb(colour))
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    """WCAG 2 contrast ratio of two colours (1 to 21)."""
    la, lb = _luminance(a), _luminance(b)
    hi, lo = max(la, lb), min(la, lb)
    return (hi + 0.05) / (lo + 0.05)


def readable(fg, bg, minimum=4.5):
    """`fg`, moved toward white (on a dark ground) or black (on a light one) just enough to
    reach `minimum` contrast with `bg`."""
    if contrast(fg, bg) >= minimum:
        return fg.lower()
    target = "#ffffff" if _luminance(bg) < 0.18 else "#000000"
    for step in range(1, 21):
        moved = mix(fg, target, step / 20.0)
        if contrast(moved, bg) >= minimum:
            return moved
    return target


def roles(preset, custom=None):
    """The six roles of a preset, with a person's own colours on top (invalid ones ignored)."""
    base = PRESETS.get(preset) or PRESETS[DEFAULT]
    out = {role: base[role] for role in ROLES if role != "outline"}
    out["outline"] = base["primary"]
    for role, value in (custom or {}).items():
        if role in ROLES and valid_hex(value or ""):
            out[role] = value.strip().lower()
    if not (custom or {}).get("outline") or not valid_hex(custom.get("outline") or ""):
        out["outline"] = out["primary"]
    return out


def digest(r):
    """8 hex characters naming a palette (its icon and frame folders)."""
    text = json.dumps({k: r.get(k) for k in ROLES}, sort_keys=True)
    return hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]


def _free(colour, used):
    """`colour`, nudged one step at a time until it is neither a dark/light colour nor one
    already used by this palette."""
    r, g, b = _rgb(colour)
    step = 0
    candidate = colour
    while candidate in _TAKEN or candidate in used:
        step += 1
        delta = (step + 1) // 2 * (1 if step % 2 else -1)
        candidate = _hex((r, g, max(0, min(255, b + delta))))
        if step > 600:
            candidate = _hex((r, max(0, min(255, g + step % 7)), b))
    return candidate


def derive(r):
    """Every colour of the look from its roles: the keys of theme.DARK plus NEON_KEYS."""
    primary, secondary, alert = r["primary"], r["secondary"], r["alert"]
    bg = r["background"]
    dark_ground = _luminance(bg) < 0.18
    away = "#ffffff" if dark_ground else "#000000"
    view = bg
    chrome = mix(mix(bg, primary, 0.07), away, 0.03)
    menu = mix(mix(bg, primary, 0.10), away, 0.04)
    field = mix(bg, primary, 0.03)
    text = r["text"]
    for ground in (chrome, menu, field, view):
        text = readable(text, ground, 4.6)
    p = {
        "chrome": chrome,
        "menu": menu,
        "view": view,
        "text": text,
        "text_dim": readable(mix(text, chrome, 0.35), chrome, 3.2),
        "disabled": mix(text, chrome, 0.6),
        "hover": mix(chrome, primary, 0.22),
        "active": mix(chrome, primary, 0.32),
        "line": mix(chrome, primary, 0.45),
        "accent": primary,
        "field": field,
        "button": mix(chrome, primary, 0.12),
        "header": mix(chrome, primary, 0.16),
        "alternate": mix(view, primary, 0.04),
        "tree_hover": mix(view, primary, 0.14),
        "handle": mix(chrome, primary, 0.5),
        "check": mix(field, away, 0.02),
        "check_line": mix(primary, chrome, 0.3),
        "marker": secondary,
        "bright": mix(text, away, 0.5),
    }
    used = set()
    for key in THEME_KEYS:
        value = p[key].lower()
        if value in ("#ffffff", "#000000"):
            # white and black are never swapped by the theme: keep a near one instead
            value = mix(value, chrome, 0.02)
        value = _free(value, used)
        used.add(value)
        p[key] = value
    p.update(
        {
            "primary": primary,
            "secondary": secondary,
            "alert": alert,
            "outline": r["outline"],
            "background": bg,
            "primary_dim": mix(primary, bg, 0.45),
            "primary_hot": mix(primary, "#ffffff", 0.35),
            "secondary_dim": mix(secondary, bg, 0.45),
            "secondary_hot": mix(secondary, "#ffffff", 0.35),
            "glow": mix(primary, "#ffffff", 0.15),
            "panel": p["chrome"],
            "grid_minor": mix(view, primary, 0.16),
            "grid_major": mix(view, primary, 0.36),
            "select": secondary,
            "preselect": mix(secondary, "#ffffff", 0.35),
            "arrow": secondary,
            "arrow_hot": mix(secondary, "#ffffff", 0.35),
            "cut": alert,
        }
    )
    return p
