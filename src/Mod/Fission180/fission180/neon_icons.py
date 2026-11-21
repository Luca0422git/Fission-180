# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights icons (docs/fission180/neon-lights-design.md 6.5): fission180/icons/neon/ holds
every ribbon / menu / browser icon drawn in the neon language (tools/fission180/make_icons.py)
with colour tokens; path() writes a copy in the preset's colours to Fission 180's user folder
(once per palette) and returns it. An icon without a neon drawing falls back to its normal
picture re-inked the same way, never to a blank."""

import os
import re

from . import ROOT, warn

NEON = os.path.join(ROOT, "icons", "neon")
UI = os.path.join(ROOT, "icons", "ui")
# token -> palette key (tools/fission180/neon_icon_style.py writes the tokens)
TOKENS = {
    "#n30001": "primary",
    "#n30002": "secondary",
    "#n30003": "alert",
    "#n30004": "text",
    "#n30006": "background",
}
_TOKEN = re.compile(r"#n3000[0-9]")


def recolour(svg_text, p):
    """An icon's SVG with its tokens replaced by palette `p`'s colours."""
    return _TOKEN.sub(lambda m: p.get(TOKENS.get(m.group(0), "primary"), p["primary"]), svg_text)


def _palette():
    from . import theme

    return theme.palette()


def _folder(p):
    from . import neon_style

    return os.path.join(neon_style.folder(p), "icons")


def _fallback(name):
    """A normal icon re-inked in the neon language (no neon drawing of it exists)."""
    import sys

    path = os.path.join(UI, name + ".svg")
    with open(path, "r", encoding="utf-8") as handle:
        text = handle.read()
    tools = os.path.normpath(os.path.join(ROOT, "..", "..", "..", "..", "tools", "fission180"))
    try:
        if tools not in sys.path:
            sys.path.insert(0, tools)
        import neon_icon_style

        head, _, rest = text.partition(">")
        body, _, tail = rest.rpartition("</svg>")
        return head + ">" + neon_icon_style.neonize(body) + "</svg>" + tail
    except Exception:
        return text  # an installed Fission 180 has no tools folder: the normal picture


def path(name):
    """The icon file for `name` in the preset's colours."""
    normal = os.path.join(UI, name + ".svg")
    try:
        p = _palette()
        source = os.path.join(NEON, name + ".svg")
        target = os.path.join(_folder(p), name + ".svg")
        fresh = os.path.isfile(target) and os.path.getmtime(target) >= os.path.getmtime(
            source if os.path.isfile(source) else normal
        )
        if not fresh:
            if os.path.isfile(source):
                with open(source, "r", encoding="utf-8") as handle:
                    text = handle.read()
            elif os.path.isfile(normal):
                text = _fallback(name)
            else:
                return normal
            os.makedirs(os.path.dirname(target), exist_ok=True)
            with open(target, "w", encoding="utf-8") as handle:
                handle.write(recolour(text, p))
        return target
    except Exception as exc:
        warn("Neon Lights: icon %s: %s" % (name, exc))
        return normal


def enable():
    pass


def disable():
    pass


def refresh():
    pass
