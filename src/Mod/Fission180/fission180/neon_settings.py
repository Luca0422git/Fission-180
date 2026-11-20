# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights' stored choices (docs/fission180/neon-lights-design.md, 6.2 and 6.10), in
FreeCAD's preferences under Mod/Fission180/Neon: the preset, a person's own colours, saved
colour sets, the effects, Hologram, boot-up, sounds and the animated Home."""

import json

from . import neon_palette

PARAMS = "User parameter:BaseApp/Preferences/Mod/Fission180/Neon"

DEFAULTS = {
    "Preset": "v",
    "Effects": True,
    "Glow": True,
    "GlowStrength": 70,
    "ScanLines": True,
    "ScanLinesStrength": 35,
    "ScanBand": False,
    "CRT": True,
    "CRTStrength": 50,
    "Glitch": True,
    "GlitchStrength": 50,
    "ViewStrength": 40,
    "Hologram": False,
    "RimLight": "auto",
    "Boot": True,
    "Sounds": False,
    "Volume": 60,
    "HomeAnimation": True,
}
_CUSTOM = "Custom_"
_SETS = "SavedSets"


def _params():
    import FreeCAD as App

    return App.ParamGet(PARAMS)


def _kind(name):
    value = DEFAULTS[name]
    if isinstance(value, bool):
        return "Bool"
    if isinstance(value, int):
        return "Int"
    return "String"


def get(name):
    """A stored choice, or its default."""
    kind = _kind(name)
    return getattr(_params(), "Get" + kind)(name, DEFAULTS[name])


def put(name, value):
    kind = _kind(name)
    if kind == "Bool":
        value = bool(value)
    elif kind == "Int":
        value = int(value)
    else:
        value = str(value)
    getattr(_params(), "Set" + kind)(name, value)


def custom():
    """A person's own colours: {role: "#rrggbb"} for the roles they changed."""
    group = _params()
    out = {}
    for role in neon_palette.ROLES:
        value = group.GetString(_CUSTOM + role, "")
        if value:
            out[role] = value
    return out


def set_custom(role, colour):
    """Set one role's colour ("" puts the preset's back). ValueError on a bad role or colour."""
    if role not in neon_palette.ROLES:
        raise ValueError("Unknown colour %r" % role)
    colour = (colour or "").strip()
    if colour and not neon_palette.valid_hex(colour):
        raise ValueError("%r is not a colour like #ff003c" % colour)
    if colour:
        _params().SetString(_CUSTOM + role, colour.lower())
    else:
        _params().RemString(_CUSTOM + role)


def clear_custom():
    for role in neon_palette.ROLES:
        _params().RemString(_CUSTOM + role)


def current_roles():
    return neon_palette.roles(get("Preset"), custom())


def saved_sets():
    """[{"name", "preset", "custom"}] a person saved under their own names."""
    try:
        sets = json.loads(_params().GetString(_SETS, "[]") or "[]")
    except ValueError:
        return []
    return [s for s in sets if isinstance(s, dict) and s.get("name")]


def _write_sets(sets):
    _params().SetString(_SETS, json.dumps(sets))


def save_set(name):
    """The colours in use saved as `name` (replacing a set of that name)."""
    name = (name or "").strip()
    if not name:
        raise ValueError("A colour set needs a name")
    sets = [s for s in saved_sets() if s["name"] != name]
    sets.append({"name": name, "preset": get("Preset"), "custom": custom()})
    _write_sets(sets)


def load_set(name):
    for s in saved_sets():
        if s["name"] == name:
            put("Preset", s.get("preset") or neon_palette.DEFAULT)
            clear_custom()
            for role, colour in (s.get("custom") or {}).items():
                try:
                    set_custom(role, colour)
                except ValueError:
                    pass
            return True
    return False


def delete_set(name):
    _write_sets([s for s in saved_sets() if s["name"] != name])
