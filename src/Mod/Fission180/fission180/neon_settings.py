# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights' stored choices (docs/fission180/neon-lights-design.md, 6.2 and 6.10), in
FreeCAD's preferences under Mod/Fission180/Neon: the preset, a person's own colours, saved
colour sets, the effects, Hologram, boot-up, sounds and the animated Home."""

import json
import os
import re
import shutil

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


def has_set(name):
    name = (name or "").strip()
    return any(s["name"] == name for s in saved_sets())


def save_set(name):
    """The colours in use saved as `name` (replacing a set of that name: the page asks first,
    has_set())."""
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


def rename_set(old, new):
    """The saved set `old` called `new` (ValueError with a sentence for the page otherwise)."""
    from . import neon_prefs_core

    _write_sets(neon_prefs_core.renamed(saved_sets(), old, (new or "").strip()))


# -- the pictures made for each palette --------------------------------------------------------
_DIGEST = re.compile(r"^[0-9a-f]{8}$")


def neon_folder():
    """<UserAppData>/Fission180/neon: one folder per palette tried (neon_style.folder)."""
    from . import neon_style

    return os.path.dirname(neon_style.folder(neon_palette.derive(neon_palette.roles(neon_palette.DEFAULT))))


def prune_folders(keep, base=None):
    """Delete the picture folders of palettes no longer in use (every colour tried in the live
    preview wrote one). `keep`: folder names (neon_palette.digest) to leave. Only folders named
    like a digest directly in `base` (default neon_folder()) go; links, files and anything else
    stay. Returns the names deleted."""
    base = base or neon_folder()
    parts = os.path.normpath(base).split(os.sep)
    if parts[-2:] != ["Fission180", "neon"] or not os.path.isdir(base):
        return []  # never outside Fission180/neon
    gone = []
    for name in sorted(os.listdir(base)):
        path = os.path.join(base, name)
        if name in keep or not _DIGEST.match(name) or os.path.islink(path) or not os.path.isdir(path):
            continue
        try:
            shutil.rmtree(path)
            gone.append(name)
        except OSError:
            pass
    return gone


def prune_unused():
    """prune_folders() keeping only the palette in use (the stored one when the look is not
    Neon Lights). Never raises."""
    try:
        from . import neon_style, theme

        p = theme.palette() if theme.is_neon() else neon_palette.derive(current_roles())
        keep = {os.path.basename(neon_style.folder(p))}
        return prune_folders(keep)
    except Exception as exc:
        try:
            from . import warn

            warn("Neon Lights: tidying the colour pictures: %s" % exc)
        except Exception:
            pass
        return []
