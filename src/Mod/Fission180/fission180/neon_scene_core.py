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
    # Not "SketchFaceColor": FreeCAD copies it into every sketch's ShapeAppearance (a saved
    # property, ViewProviderSketch's parameter map), so changing it marked designs modified
    # and saved the neon shade into them (found at the merge, 2026-11-20). The sketch areas
    # keep their Dark shade.
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


# Every Live made so far, in order (its index is its code): neon_scene's sweep repaints the
# shapes already on screen from this list.
LIVES = []
CODE_STEP = 2.0 ** -20  # about 1e-6: far under what a screen shows (1/255), far over float32 rounding


def coded(rgb, code):
    """`rgb` with `code` written into its red channel's last digits (invisible: at most about
    1e-4 for the 100-odd constants): every Live's neon value is its own, so a shape already
    drawn in a neon colour can be traced back to the constant it came from and given its exact
    Dark value again (neon_scene.sweep; two roles often share a neon colour)."""
    r, g, b = rgb
    step = (code + 1) * CODE_STEP
    return (r - step if r > 0.5 else r + step, g, b)


class Live(tuple):
    """A 3D colour constant: the tuple `rgb` itself, read as the neon colour of `role` while
    Neon Lights is on (see the module's doc).

    What reads which value (pinned by test_neon_scene_core.LiveOperations, FreeCAD's Python
    3.11 and 3.13 alike):
    - The colour of the look in use (neon in Neon Lights, else `rgb`): iterating, unpacking
      (`f(*c)`, `r, g, b = c`), `tuple(c)`, `list(c)`, indexing and slicing (`c[0]`, `c[:2]`),
      `min/max/sum`, comprehensions (`[x * 0.5 for x in c]`), `c + (1.0,)` and `(1.0,) + c`
      (overridden here), `json.dumps(c)`, `numpy.array(c)` and value(). In Neon Lights the
      red channel carries the constant's code (see coded()).
    - Always the stored Dark value: `==`/`!=`/`<`, `hash`, `repr`/`str`, `len`, `in`, `%`
      formatting (`"%s, %s, %s" % c`: CPython reads a tuple's items directly), `copy.copy`
      and `pickle` (both give a plain Dark tuple) and normal(). So tables keyed by colour
      keep working.
    Rules: to show a colour through `%` or `repr`, pass `tuple(c)` (or value()); whatever is
    saved (a property, a json file, a preference) takes normal(), never `c` itself, or a
    design saved in Neon Lights would keep a neon colour.
    """

    def __new__(cls, rgb, role):
        self = super().__new__(cls, rgb)
        self.role = role
        self.code = len(LIVES)
        LIVES.append(self)
        return self

    def normal(self):
        """The Dark value as a plain tuple."""
        return tuple(tuple.__iter__(self))

    def value_in(self, roles):
        """The colour in a look: `roles` is roles3d() of a neon palette, or None for Dark/Light
        (and for a save's preview picture)."""
        value = roles.get(self.role) if roles else None
        return self.normal() if value is None else coded(value, self.code)

    def value(self):
        """The colour of the look in use, as a plain tuple."""
        return tuple(self._now_or_normal())

    def _now(self):
        value = role_rgb(self.role)
        return value if value is None else coded(value, self.code)

    def __iter__(self):
        return iter(self._now_or_normal())

    def _now_or_normal(self):
        value = self._now()
        return value if value is not None else self.normal()

    def __getitem__(self, index):
        return self._now_or_normal()[index]

    def __add__(self, other):
        return tuple(self._now_or_normal()) + tuple(other)

    def __radd__(self, other):
        return tuple(other) + tuple(self._now_or_normal())

    def __reduce__(self):
        return (tuple, (self.normal(),))


def roles_now():
    """roles3d() of the palette in use while Neon Lights is on (and not drawing a saved preview
    picture), else None: what Live constants read now."""
    if not neon_live():
        return None
    try:
        role_rgb("primary")  # fills the cache
        return _cache["roles"] or None
    except Exception:
        return None


# How shapes are drawn from a constant (handle_look_core.shaded, hot_colour's lightening and the
# `[c * k for c in COLOUR]` glow of many files): a sweep follows these too.
SCALES = (0.35, 0.4, 0.45, 0.5, 0.6, 0.75)


def _derived(rgb):
    out = [tuple(rgb)]
    out += [tuple(c * k for c in rgb) for k in SCALES]
    lit = tuple(min(1.0, c + (1.0 - c) * 0.55) for c in rgb)  # hot_colour without its own hot
    out += [lit, tuple(c * 0.75 for c in lit), tuple(c * 0.40 for c in lit)]
    return out


def key(rgb):
    """A colour as Coin keeps it (float32), so a value read back from a node compares equal."""
    import struct

    return struct.unpack("3f", struct.pack("3f", *(float(c) for c in rgb[:3])))


def colour_map(old, new, lives=None):
    """{key(colour drawn in look `old`): colour in look `new`} for every Live constant and the
    ways shapes are drawn from one (_derived). `old`/`new` are roles3d() tables or None (the
    normal look). Neon values are coded, so going from neon to anything is exact; going from
    the normal look, two constants with the same Dark value and different roles give the
    colour of the one most constants share (a handle drawn before Neon Lights was switched on
    may take a neighbour role's neon colour until it is drawn again; never the other way)."""
    votes = {}
    for live in LIVES if lives is None else lives:
        before, after = live.value_in(old), live.value_in(new)
        if before == after:
            continue
        for a, b in zip(_derived(before), _derived(after)):
            k = key(a)
            if k == key(b):
                continue
            counts = votes.setdefault(k, {})
            counts[b] = counts.get(b, 0) + 1
    return {k: max(counts, key=lambda v: (counts[v], v)) for k, counts in votes.items()}
