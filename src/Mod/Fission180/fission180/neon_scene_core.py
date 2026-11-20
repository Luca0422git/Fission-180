# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights' colours for the 3D view (docs/fission180/neon-lights-design.md 6.6; plan B7).

Pure Python (unit tested, test_neon_scene_core.py); FreeCAD is not imported here.

- roles3d(p): every 3D role of a neon palette p (theme.palette()) as (r, g, b) in 0..1: the
  palette's own keys plus the roles of the scene (arrow rims, angle discs, axis hues...).
- background(p): the faint vertical gradient of the 3D view, (top, bottom) as hex.
- sketch(p): FreeCAD's sketch colour parameters in Neon Lights (sketch_mode's NEON table).
- Live(rgb, role): a colour constant of a 3D file. It *is* the tuple `rgb` (equality, hash,
  repr, len: the exact Dark value, always), and reading its values (unpacking, indexing,
  iterating: what every Coin call does) gives `rgb` unless Neon Lights is on, then the neon
  colour of `role`. So `BLUE = Live((0.16, 0.50, 0.93), "arrow")` keeps Dark and Light exactly
  and turns neon with no change where it is used. While a save draws the preview picture kept
  in the file (theme.normal_look), it reads as `rgb` too.
"""

import sys

from . import neon_palette as _np

WHITE = "#ffffff"
BLACK = "#000000"
# The origin axes "in their usual X/Y/Z hues but neon" (6.6).
AXIS_X = (1.0, 0.18, 0.33)
AXIS_Y = (0.2, 1.0, 0.45)
AXIS_Z = (0.15, 0.55, 1.0)

# role -> how it is made from the palette (key, or (a, b, t): mix of two keys/hexes)
_RECIPES = {
    # the arrows, balls and discs of the commands (handle_look, handles3d...)
    "arrow": "arrow",
    "arrow_hot": "arrow_hot",
    "rim": ("secondary", WHITE, 0.72),  # the thin light outline round an arrow or a ball
    "disc": "primary_hot",  # the angle disc
    "disc_hot": ("primary", WHITE, 0.6),
    "disc_rim": "primary_dim",
    "dot": "background",  # the dot in the middle of a disc
    "arc": "glow",  # the thin light arc / line of an angle
    "ring": ("primary", WHITE, 0.55),  # the protractor's ring and free ticks
    "hot": ("secondary", WHITE, 0.5),  # a lit tick, an axis under the mouse
    # what is picked or will be made
    "pick": "secondary",  # picked profiles, faces, paths
    "pick_fill": ("secondary", WHITE, 0.25),  # a profile's shade
    "pick_glow": ("secondary", "background", 0.62),
    "pick_edge": ("secondary", WHITE, 0.15),
    "hover": "preselect",
    "cut": "cut",  # material taken away
    "cut_glow": ("cut", "background", 0.6),
    "cut_edge": ("cut", WHITE, 0.2),
    "rail": "primary",  # a second path / rail / reference picked over the part
    "ghost": ("text_dim", "primary", 0.25),  # a faint stand-in (hover ghost, rebuild original)
    "preview": ("primary", WHITE, 0.3),  # text or shapes being placed
    "measure": "primary_hot",  # Measure's line and dots
    "snap": ("secondary", "background", 0.35),  # a snap point that is not the nearest
    "marker": "primary",  # the orbit centre dot, the origin dot
    "marker_rim": ("primary", "background", 0.6),
    "ghost_glow": ("text_dim", "background", 0.75),
    "bright": ("text", WHITE, 0.3),  # fully constrained curves, white labels
    "sketch_free": "primary",  # sketch curves that can still move
    "grid_minor": "grid_minor",
    "grid_major": "grid_major",
    "grid_text": "text_dim",
    "hidden_edge": ("outline", "background", 0.45),
}
_FIXED = {"axis_x": AXIS_X, "axis_y": AXIS_Y, "axis_z": AXIS_Z}


def _hex_of(p, value):
    return p.get(value, value) if not value.startswith("#") else value


def roles3d(p):
    """{role: (r, g, b)} of palette `p` (every key of p too)."""
    out = {}
    for key, value in p.items():
        if isinstance(value, str) and _np.valid_hex(value):
            out[key] = _np.rgb01(value)
    for role, recipe in _RECIPES.items():
        if isinstance(recipe, str):
            out[role] = _np.rgb01(_hex_of(p, recipe))
        else:
            a, b, t = recipe
            out[role] = _np.rgb01(_np.mix(_hex_of(p, a), _hex_of(p, b), t))
    out.update(_FIXED)
    return out


def background(p):
    """(top, bottom) of the 3D view's faint vertical gradient: the preset's ground, a little
    lifted toward the primary at the top and sunk toward black at the bottom."""
    view = p["view"]
    top = _np.mix(_np.mix(view, p["primary"], 0.08), p["secondary"], 0.03)
    bottom = _np.mix(view, BLACK, 0.35)
    return top, bottom


def _packed(hex_colour, alpha=0xFF):
    return (int(hex_colour.lstrip("#"), 16) << 8) | alpha


def sketch_hex(p):
    """{sketch_mode colour name: hex} in Neon Lights. Under-constrained curves glow in the
    primary, fully constrained ones are near white, construction is the alert colour, the
    selection is the secondary (as on bodies)."""
    return {
        "BLUE": p["primary"],
        "WHITE": _np.mix(p["text"], WHITE, 0.3),
        "ORANGE": p["alert"],
        "PURPLE": _np.mix(p["secondary"], p["primary"], 0.5),
        "GREEN": _np.mix("#2bff88", p["secondary"], 0.15),
        "GLYPH": _np.mix(p["text"], p["secondary"], 0.45),
        "DRIVEN": p["text_dim"],
        "SELECT": p["select"],
        "HOVER": p["preselect"],
        "GRID": p["grid_minor"],
        "GRID_DIV": p["grid_major"],
        "FACE": _np.mix(p["secondary"], WHITE, 0.2),
    }


# FreeCAD's sketch parameter -> the sketch_hex name it takes in Neon Lights
SKETCH_PARAMS = {
    "GridLineColor": "GRID",
    "GridDivLineColor": "GRID_DIV",
    "EditedEdgeColor": "BLUE",
    "CreateLineColor": "BLUE",
    "FullyConstraintElementColor": "WHITE",
    "FullyConstrainedColor": "WHITE",
    "ConstructionColor": "ORANGE",
    "FullyConstraintConstructionElementColor": "ORANGE",
    "ExternalColor": "PURPLE",
    "ExternalDefiningColor": "PURPLE",
    "ConstrainedDimColor": "WHITE",
    "ConstrainedIcoColor": "GLYPH",
    "NonDrivingConstrDimColor": "DRIVEN",
    "CursorTextColor": "WHITE",
    "CursorCrosshairColor": "WHITE",
    "SelectionColor": "SELECT",
    "HighlightColor": "HOVER",
    "SketchFaceColor": "FACE",
}


def sketch(p):
    """{FreeCAD parameter name: packed colour} of the sketch colours in Neon Lights, for the
    names of sketch_mode.PARAMS (the profile shade keeps a see-through alpha)."""
    colours = sketch_hex(p)
    return {
        name: _packed(colours[key], 0x60 if name == "SketchFaceColor" else 0xFF)
        for name, key in SKETCH_PARAMS.items()
    }


# -- Live colour constants -------------------------------------------------------------------
_cache = {"palette": None, "roles": {}}


def _theme():
    return sys.modules.get("fission180.theme")


def neon_live():
    """Neon Lights is on and not drawing a saved preview picture."""
    theme = _theme()
    if theme is None:
        return False
    try:
        return theme.is_neon() and not theme._neon.get("normal")
    except Exception:
        return False


def role_rgb(role):
    """The neon (r, g, b) of `role` now (None outside Neon Lights or for an unknown role)."""
    if not neon_live():
        return None
    try:
        p = _theme().palette()
        if _cache["palette"] is not p:
            _cache["roles"] = roles3d(p)
            _cache["palette"] = p
        return _cache["roles"].get(role)
    except Exception:
        return None


def shade(rgb, role):
    """`rgb` unchanged unless Neon Lights is on, then the neon colour of `role`."""
    value = role_rgb(role)
    return tuple(rgb) if value is None else value


class Live(tuple):
    """A 3D colour constant: the tuple `rgb` itself, read as the neon colour of `role` while
    Neon Lights is on (see the module's doc)."""

    def __new__(cls, rgb, role):
        self = super().__new__(cls, rgb)
        self.role = role
        return self

    def normal(self):
        """The Dark value as a plain tuple."""
        return tuple(tuple.__iter__(self))

    def _now(self):
        value = role_rgb(self.role)
        return value if value is not None else self.normal()

    def __iter__(self):
        return iter(self._now())

    def __getitem__(self, index):
        return self._now()[index]

    def __reduce__(self):
        return (tuple, (self.normal(),))

