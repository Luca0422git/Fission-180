#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fingerprint of Fission 180's Dark and Light looks, so the Neon Lights work (and anything
after it) can prove it changed neither (docs/fission180/neon-lights-design.md, section 3:
"Dark or Light change in any visible way" is a failure).

    python3 tools/fission180/theme_identity.py            # compare with the fixture, exit 1 on a change
    python3 tools/fission180/theme_identity.py --write    # write the fixture (only on develop's look!)

The parts that need FreeCAD (sketch_mode's colour table) are fingerprinted when FreeCAD can be
imported: run the same commands with FreeCAD's own Python, e.g.
    <freecad>/AppRun freecadcmd -c "import sys; sys.argv=['x', '--write']; exec(open('tools/fission180/theme_identity.py').read())"
The fixture keeps both sets; each run compares (or writes) only the keys it can compute.
"""

import ast
import glob
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.path.join(
    os.getcwd(), "tools", "fission180"
)
ROOT = os.path.normpath(os.path.join(HERE, "..", ".."))
MODULE = os.path.join(ROOT, "src", "Mod", "Fission180")
FIXTURE = os.path.join(MODULE, "Fission180Tests", "fixtures", "theme_identity.json")
_HEX = re.compile(r"#[0-9a-fA-F]{6}\b")


def _sha(text):
    if not isinstance(text, (str, bytes)):
        text = json.dumps(text, sort_keys=True, default=repr)
    if isinstance(text, str):
        text = text.encode("utf-8")
    return hashlib.sha256(text).hexdigest()


def _style_literals():
    """Every string literal of the module's code that carries a #rrggbb colour (the style
    sheets the setStyleSheet hook translates), sorted and unique."""
    found = set()
    for path in sorted(glob.glob(os.path.join(MODULE, "fission180", "**", "*.py"), recursive=True)):
        if os.path.basename(path).startswith("neon"):
            continue  # the new look's own files
        try:
            with open(path, "r", encoding="utf-8") as handle:
                tree = ast.parse(handle.read())
        except (OSError, SyntaxError):
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                if _HEX.search(node.value) and ("{" in node.value or ":" in node.value):
                    found.add(node.value)
    return sorted(found)


def pure_fingerprint():
    """Keys that need no FreeCAD."""
    if MODULE not in sys.path:
        sys.path.insert(0, MODULE)
    import fission180
    from fission180 import theme

    out = {
        "qss_template": _sha(theme._QSS),
        "qss_dark": _sha(theme._QSS.format(**theme.DARK)),
        "qss_light": _sha(theme._QSS.format(**theme.LIGHT)),
        "dark": _sha(theme.DARK),
        "light": _sha(theme.LIGHT),
        "extra": _sha(theme._EXTRA),
        "to_light": _sha(theme.TO_LIGHT),
        "to_dark": _sha(theme.TO_DARK),
        "light_ink": _sha(fission180._LIGHT_INK),
        "keep_white": _sha(sorted(fission180._KEEP_WHITE)),
        "viewer_settings_dark": _sha(
            [(g, k, n, v) for g, k, n, v in theme.VIEWER_SETTINGS if n != "BackgroundColor"]
        ),
    }
    literals = _style_literals()
    out["style_literals"] = _sha(literals)
    out["translate_to_light"] = _sha([theme.translate(t, light=True) for t in literals])
    out["translate_to_dark"] = _sha([theme.translate(t, light=False) for t in literals])
    for path in sorted(glob.glob(os.path.join(MODULE, "fission180", "icons", "ui", "*.svg"))):
        with open(path, "rb") as handle:
            out["icon:" + os.path.basename(path)] = _sha(handle.read())
    return out


def freecad_fingerprint():
    """Keys that need FreeCAD (empty when it cannot be imported)."""
    try:
        import FreeCAD  # noqa: F401
    except ImportError:
        return {}
    if MODULE not in sys.path:
        sys.path.insert(0, MODULE)
    from fission180 import sketch_mode

    return {
        "fc:sketch_params": _sha(sketch_mode.PARAMS),
        "fc:sketch_light": _sha(sketch_mode.LIGHT),
    }


def fingerprint():
    out = pure_fingerprint()
    out.update(freecad_fingerprint())
    return out


def compare(now, saved):
    """Names whose fingerprint differs (or appeared / vanished) among the keys `now` holds,
    plus saved icon keys that vanished."""
    changed = sorted(k for k in now if saved.get(k) != now[k])
    if not any(k.startswith("icon:") for k in now):
        return changed  # a FreeCAD-only run holds no icon keys
    gone = sorted(k for k in saved if k.startswith("icon:") and k not in now)
    return changed + gone


def main(argv):
    now = fingerprint()
    saved = {}
    if os.path.isfile(FIXTURE):
        with open(FIXTURE, "r", encoding="utf-8") as handle:
            saved = json.load(handle)
    if "--write" in argv:
        saved.update(now)
        os.makedirs(os.path.dirname(FIXTURE), exist_ok=True)
        with open(FIXTURE, "w", encoding="utf-8") as handle:
            json.dump(saved, handle, indent=1, sort_keys=True)
            handle.write("\n")
        print("[Fission 180] theme identity: wrote %d keys to %s" % (len(now), FIXTURE))
        return 0
    changed = compare(now, saved)
    if changed:
        print("[Fission 180] theme identity CHANGED: " + ", ".join(changed))
        return 1
    print("[Fission 180] theme identity unchanged (%d keys)" % len(now))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
