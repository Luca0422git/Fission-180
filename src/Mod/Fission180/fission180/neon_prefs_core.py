# SPDX-License-Identifier: LGPL-2.1-or-later
"""The Neon Lights page of Preferences as data (docs/fission180/neon-lights-design.md 6.10, plan
task B10): its colour rows, its effect rows, what a preset is called once a person changed a
colour, and the checks on a typed colour. No FreeCAD, no Qt: unit tested
(Fission180Tests/unit/test_neon_prefs_core.py). neon_prefs_ui.py is the page."""

from . import neon_palette

# (role, label, what it colours) in the order of the page; Alert is under "More".
COLOUR_ROWS = (
    ("primary", "Primary", "The main glow: frames, the active tab, the focused field, selected rows."),
    ("secondary", "Secondary", "The second accent: hover, icon accents, timeline markers, progress."),
    ("outline", "Outline", "The edges of bodies in the 3D view (the same as Primary until you set it)."),
    ("background", "Background", "The near-black ground of the panels and the 3D view."),
    ("text", "Text", "The words. Kept readable on the background whatever you pick."),
)
MORE_ROWS = (
    ("alert", "Alert", "Warnings and errors: hazard stripes, error boxes."),
)

# (switch, strength, label, what it does) of the four screen effects (neon_settings keys).
EFFECTS = (
    ("Glow", "GlowStrength", "Glow", "A soft halo around frames, lines and the active controls."),
    ("ScanLines", "ScanLinesStrength", "Scan lines", "Fine horizontal lines, like an old monitor."),
    ("CRT", "CRTStrength", "CRT", "A faint curved-screen shade at the window's edges."),
    ("Glitch", "GlitchStrength", "Glitch", "Now and then a short flicker; never while you drag, pick or type."),
)

# The Neon Lights part that follows each setting (neon.PARTS); Hologram goes through neon_view.
PART_OF = {
    "Effects": "neon_effects",
    "Glow": "neon_effects",
    "GlowStrength": "neon_effects",
    "ScanLines": "neon_effects",
    "ScanLinesStrength": "neon_effects",
    "ScanBand": "neon_effects",
    "CRT": "neon_effects",
    "CRTStrength": "neon_effects",
    "Glitch": "neon_effects",
    "GlitchStrength": "neon_effects",
    "ViewStrength": "neon_effects",
    "Hologram": "neon_view",
    "Boot": "neon_boot",
    "Sounds": "neon_sound",
    "Volume": "neon_sound",
    "HomeAnimation": "neon_home",
}

EXAMPLE = "#ff003c"


def preset_name(preset):
    return (neon_palette.PRESETS.get(preset) or neon_palette.PRESETS[neon_palette.DEFAULT])["name"]


def preset_title(preset, custom):
    """What the page calls the colours in use: "V", or "Custom (based on V)" once a person
    changed a colour."""
    name = preset_name(preset)
    return "Custom (based on %s)" % name if custom else name


def parse_hex(text):
    """(colour, "") for a colour typed as #rrggbb (the # may be left out; any case), else
    (None, why it was refused)."""
    raw = (text or "").strip()
    if not raw:
        return None, "Type a colour like %s." % EXAMPLE
    colour = raw if raw.startswith("#") else "#" + raw
    if neon_palette.valid_hex(colour):
        return colour.lower(), ""
    return None, "%s is not a colour: type # and six of 0-9 / a-f, like %s." % (raw, EXAMPLE)


def matching_set(sets, preset, custom):
    """The name of the saved set that holds exactly the colours in use, or None."""
    custom = {k: v.lower() for k, v in (custom or {}).items()}
    for s in sets or ():
        theirs = {k: (v or "").lower() for k, v in (s.get("custom") or {}).items() if v}
        if (s.get("preset") or neon_palette.DEFAULT) == preset and theirs == custom:
            return s.get("name")
    return None


def renamed(sets, old, new):
    """`sets` with the set `old` called `new`. ValueError (with a sentence for the page) when
    there is no `old`, `new` is empty, or another set has that name."""
    new = (new or "").strip()
    if not new:
        raise ValueError("Type the new name first.")
    names = [s.get("name") for s in sets]
    if old not in names:
        raise ValueError("Choose the colour set to rename.")
    if new != old and new in names:
        raise ValueError("A colour set called %s exists already." % new)
    return [dict(s, name=new) if s.get("name") == old else s for s in sets]


def lifted(roles):
    """True when the chosen Text colour is too faint on the panels made from the chosen
    Background, so the look shows it lifted (neon_palette.derive keeps text readable).

    The typed colour itself is measured against the panel colours: derive() also nudges every
    colour by a hair to keep them unique (#ffffff comes back #fbfafa), which is no lifting."""
    p = neon_palette.derive(roles)
    text = roles["text"].lower()
    return any(neon_palette.contrast(text, p[g]) < READABLE for g in GROUNDS)


READABLE = 4.5  # the WCAG ratio the page's words keep on its panels
GROUNDS = ("chrome", "menu", "field", "view")  # the panels text is drawn on

# The page's own coloured words: (key of inks(), palette colour, the ground it is drawn on).
INKS = (
    ("primary_ink", "primary", "chrome"),  # section titles
    ("primary_hot_ink", "primary_hot", "chrome"),  # the banner's title
    ("primary_list_ink", "primary_hot", "active"),  # the chosen colour set
    ("secondary_ink", "secondary", "chrome"),  # "In use", notes, strength values, More
    ("secondary_hover_ink", "secondary_hot", "hover"),  # a button under the mouse
    ("alert_ink", "alert", "chrome"),  # refusal messages
    ("alert_field_ink", "alert", "field"),  # a refused colour in its field
    ("text_dim_ink", "text_dim", "chrome"),  # captions, the banner's small print
)


def inks(p):
    """The page's coloured words for palette `p`, each kept readable on what it is drawn on
    (Review Focus: an Alert of #1a0a10 or a Secondary of #000000 must not make words vanish)."""
    return {key: neon_palette.readable(p[colour], p[ground], READABLE) for key, colour, ground in INKS}
