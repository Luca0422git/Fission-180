# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights' frame pieces (docs/fission180/neon-lights-design.md 6.3): small SVG pictures
of cut-corner frames with bracket marks and a glow, drawn in a palette's colours and used by
the style sheet as nine-slice `border-image`s (buttons, fields, menus, panels...), plus a few
tiles (hazard stripes, check boxes).

Original shapes in the style of industrial sci-fi interfaces; nothing traced from any picture.
Qt draws SVG Tiny: no filters, so the glow is a wider, fainter copy of each line under it.
Pieces are drawn at twice the size they are shown (SLICE image pixels -> BORDER screen pixels)
so they stay sharp on high-resolution screens. Pure logic apart from write().
"""

import os

from .neon_palette import mix

# piece -> (width, height, slice in image px, border in screen px)
SIZES = {
    "panel": (64, 48, 12, 6),
    "button": (48, 32, 8, 4),
    "button_hover": (48, 32, 8, 4),
    "button_pressed": (48, 32, 8, 4),
    "button_default": (48, 32, 8, 4),
    "field": (48, 32, 8, 4),
    "field_focus": (48, 32, 8, 4),
    "menu": (64, 48, 12, 6),
    "tooltip": (48, 32, 10, 5),
    "header": (64, 32, 8, 4),
    "tab_active": (32, 16, 6, 3),
    "check": (26, 26, 0, 0),
    "check_on": (26, 26, 0, 0),
    "radio": (26, 26, 0, 0),
    "radio_on": (26, 26, 0, 0),
    "stripes": (96, 24, 0, 0),
    "warning_header": (96, 24, 0, 0),
    "arrow_down": (20, 20, 0, 0),
}
PIECES = tuple(SIZES)
SLICE = {name: size[2] for name, size in SIZES.items()}
BORDER = {name: size[3] for name, size in SIZES.items()}


def _chamfer(x, y, w, h, c, corners=("tl", "br")):
    """Points of a rectangle with the given corners cut by `c`."""
    pts = []
    pts += [(x, y + c), (x + c, y)] if "tl" in corners else [(x, y)]
    pts += [(x + w - c, y), (x + w, y + c)] if "tr" in corners else [(x + w, y)]
    pts += [(x + w, y + h - c), (x + w - c, y + h)] if "br" in corners else [(x + w, y + h)]
    pts += [(x + c, y + h), (x, y + h - c)] if "bl" in corners else [(x, y + h)]
    return " ".join("%g,%g" % p for p in pts)


def _poly(points, fill="none", fill_opacity=1.0, stroke="none", width=0.0, opacity=1.0):
    return (
        '<polygon points="%s" fill="%s" fill-opacity="%g" stroke="%s" stroke-width="%g" '
        'stroke-opacity="%g" stroke-linejoin="miter" />' % (points, fill, fill_opacity, stroke, width, opacity)
    )


def _line(x1, y1, x2, y2, colour, width, opacity=1.0):
    return (
        '<line x1="%g" y1="%g" x2="%g" y2="%g" stroke="%s" stroke-width="%g" '
        'stroke-opacity="%g" stroke-linecap="square" />' % (x1, y1, x2, y2, colour, width, opacity)
    )


def _svg(w, h, body):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">%s</svg>'
        % (w, h, w, h, "".join(body))
    )


def _frame(w, h, s, fill, fill_opacity, stroke, glow, brackets=None, corners=("tl", "br")):
    """A cut-corner frame: glow, fill, line, and bracket marks in two corners."""
    g = 2.0  # room for the glow
    c = max(3.0, s - 3.0)
    pts = _chamfer(g, g, w - 2 * g, h - 2 * g, c, corners)
    body = []
    if glow:
        body.append(_poly(pts, stroke=glow, width=4.0, opacity=0.22))
        body.append(_poly(pts, stroke=glow, width=2.6, opacity=0.35))
    body.append(_poly(pts, fill=fill, fill_opacity=fill_opacity, stroke=stroke, width=2.0))
    if brackets:
        k = s - 1.0  # bracket arm length, inside the corner slice
        body.append(_line(g + 1, h - g - 1, g + 1, h - g - k, brackets, 2.4))
        body.append(_line(g + 1, h - g - 1, g + k, h - g - 1, brackets, 2.4))
        body.append(_line(w - g - 1, g + 1, w - g - k, g + 1, brackets, 2.4))
        body.append(_line(w - g - 1, g + 1, w - g - 1, g + k, brackets, 2.4))
    return _svg(w, h, body)


def _stripes(w, h, colour, ground, opacity):
    body = []
    if ground:
        body.append('<rect x="0" y="0" width="%d" height="%d" fill="%s" />' % (w, h, ground))
    step = 12
    for x in range(-h, w + h, step):
        body.append(
            _poly("%g,%g %g,%g %g,%g %g,%g" % (x, h, x + 6, h, x + 6 + h, 0, x + h, 0),
                  fill=colour, fill_opacity=opacity)
        )
    # fade toward the left: the stripes sit at the right end of a header
    return _svg(w, h, body)


def svg(piece, p):
    """The SVG text of one piece in palette `p` (theme / neon_palette.derive keys)."""
    w, h, s, _border = SIZES[piece]
    primary, secondary = p["primary"], p["secondary"]
    if piece == "panel":
        return _frame(w, h, s, p["chrome"], 0.92, p["line"], primary, brackets=primary)
    if piece == "button":
        return _frame(w, h, s, p["button"], 1.0, p["primary_dim"], None)
    if piece == "button_hover":
        return _frame(w, h, s, p["hover"], 1.0, primary, primary)
    if piece == "button_pressed":
        return _frame(w, h, s, p["active"], 1.0, p["primary_hot"], primary)
    if piece == "button_default":
        return _frame(w, h, s, mix(p["button"], primary, 0.25), 1.0, primary, primary, brackets=p["primary_hot"])
    if piece == "field":
        body = [
            _poly(_chamfer(1, 1, w - 2, h - 2, 4, ("br",)), fill=p["field"], stroke=p["line"], width=1.5),
            _line(2, h - 2, w - 6, h - 2, p["primary_dim"], 2.0),
        ]
        return _svg(w, h, body)
    if piece == "field_focus":
        body = [
            _poly(_chamfer(1, 1, w - 2, h - 2, 4, ("br",)), stroke=primary, width=4.0, opacity=0.25),
            _poly(_chamfer(1, 1, w - 2, h - 2, 4, ("br",)), fill=p["field"], stroke=primary, width=1.8),
            _line(2, h - 2, w - 6, h - 2, p["primary_hot"], 2.4),
        ]
        return _svg(w, h, body)
    if piece == "menu":
        return _frame(w, h, s, p["menu"], 0.88, primary, primary, brackets=p["primary_hot"],
                      corners=("tr", "bl"))
    if piece == "tooltip":
        return _frame(w, h, s, p["menu"], 0.94, secondary, secondary, brackets=p["secondary_hot"])
    if piece == "header":
        body = [
            _poly(_chamfer(1, 1, w - 2, h - 2, 6, ("tl",)), fill=p["header"], stroke=p["line"], width=1.5),
            _line(2, h - 1.5, w - 2, h - 1.5, primary, 2.0),
        ]
        return _svg(w, h, body)
    if piece == "tab_active":
        body = [
            _line(0, h - 3, w, h - 3, primary, 5.0, 0.3),
            _line(0, h - 2, w, h - 2, p["primary_hot"], 2.6),
        ]
        return _svg(w, h, body)
    if piece in ("check", "check_on"):
        on = piece == "check_on"
        body = [
            _poly(_chamfer(3, 3, w - 6, h - 6, 5, ("tl", "br")), fill=primary if on else p["field"],
                  fill_opacity=0.9 if on else 1.0, stroke=primary if on else p["check_line"], width=2.0),
        ]
        if on:
            body.append(
                '<polyline points="7,13 11.5,17.5 19,8.5" fill="none" stroke="%s" stroke-width="3" '
                'stroke-linecap="square" />' % p["background"]
            )
        return _svg(w, h, body)
    if piece in ("radio", "radio_on"):
        on = piece == "radio_on"
        mid = w / 2.0
        diamond = "%g,%g %g,%g %g,%g %g,%g" % (mid, 3, w - 3, mid, mid, h - 3, 3, mid)
        body = [_poly(diamond, fill=p["field"], stroke=primary if on else p["check_line"], width=2.0)]
        if on:
            inner = "%g,%g %g,%g %g,%g %g,%g" % (mid, 8, w - 8, mid, mid, h - 8, 8, mid)
            body.append(_poly(inner, fill=primary))
        return _svg(w, h, body)
    if piece == "stripes":
        return _stripes(w, h, primary, None, 0.22)
    if piece == "warning_header":
        return _stripes(w, h, p["alert"], mix(p["background"], p["alert"], 0.12), 0.55)
    if piece == "arrow_down":
        body = [
            '<polygon points="5,7 15,7 10,13" fill="%s" />' % primary,
        ]
        return _svg(w, h, body)
    raise KeyError(piece)


def write(p, folder):
    """Every piece of palette `p` as an SVG file in `folder` (made once): {piece: path}."""
    os.makedirs(folder, exist_ok=True)
    out = {}
    for piece in PIECES:
        path = os.path.join(folder, piece + ".svg")
        if not os.path.isfile(path):
            with open(path, "w", encoding="utf-8") as handle:
                handle.write(svg(piece, p))
        out[piece] = path.replace("\\", "/")
    return out
