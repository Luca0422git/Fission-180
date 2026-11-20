# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights' frame pieces (docs/fission180/neon-lights-design.md 6.3): small SVG pictures
of cut-corner frames with bracket marks, tick marks and a glow, drawn in a palette's colours
and used by the style sheet as nine-slice `border-image`s (buttons, fields, menus, panels...),
plus a few tiles (hazard stripes, check boxes, rails).

The look language (industrial HUD, original shapes; nothing traced from any picture):
- corners cut at 45 degrees on two opposite corners (top-left, bottom-right), never rounded;
- small L-shaped bracket marks on the other two corners, a little brighter than the line;
- thin glowing lines (Qt draws SVG Tiny: no filters, so the glow is wider, fainter copies of
  each line under it);
- ruler ticks along the long edges of big frames (menus, group boxes), which repeat ("round")
  instead of stretching, so they keep their spacing whatever the frame's width;
- hazard stripes for warnings, a red double rule for errors, segmented bars.

Pieces are drawn at twice the size they are shown (slice in image pixels -> border in screen
pixels) so they stay sharp on high-resolution screens. Pure logic apart from write().
"""

import os

from .neon_palette import contrast, mix

# A change of any shape: a new number, so the pictures already written for a palette (in the
# user folder, once per palette) are made again.
VERSION = 5

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
    "menu_item": (48, 16, 8, 4),
    "tooltip": (48, 32, 10, 5),
    "header": (64, 32, 8, 4),
    "tab_active": (32, 16, 6, 3),
    "check": (26, 26, 0, 0),
    "check_on": (26, 26, 0, 0),
    "radio": (26, 26, 0, 0),
    "radio_on": (26, 26, 0, 0),
    "progress": (48, 24, 6, 3),
    "scroll_handle": (12, 48, 6, 3),
    "scroll_handle_h": (48, 12, 6, 3),
    "rail_v": (10, 10, 0, 0),
    "rail_h": (10, 10, 0, 0),
    "slider_handle": (16, 32, 0, 0),
    "stripes": (96, 24, 0, 0),
    "warning_header": (96, 24, 0, 0),
    "message": (96, 48, 12, 6),
    "message_warning": (96, 48, 12, 6),
    "message_error": (96, 48, 12, 6),
    "arrow_down": (20, 20, 0, 0),
    "icon_info": (64, 64, 0, 0),
    "icon_question": (64, 64, 0, 0),
    "icon_warning": (64, 64, 0, 0),
    "icon_error": (64, 64, 0, 0),
}
PIECES = tuple(SIZES)
SLICE = {name: size[2] for name, size in SIZES.items()}
BORDER = {name: size[3] for name, size in SIZES.items()}
# Pieces whose slices differ per side: (top, right, bottom, left) in image px and screen px.
SIDES = {
    "menu_item": ((0, 0, 0, 8), (0, 0, 0, 4)),
    # only a bottom edge, 2 px like Dark's underline: a tab is exactly as tall in both looks
    # (a taller open tab made FreeCAD's 3D window 4 px shorter, and it did not always grow
    # back after a switch to Dark)
    "tab_active": ((0, 0, 4, 0), (0, 0, 2, 0)),
    "message": ((28, 12, 12, 12), (14, 6, 6, 6)),
    "message_warning": ((28, 12, 12, 12), (14, 6, 6, 6)),
    "message_error": ((28, 12, 12, 12), (14, 6, 6, 6)),
}
# How the edges between the corners fill a longer side: "stretch", or "round" (repeated a
# whole number of times: the ticks and stripes keep their spacing). (horizontal, vertical)
REPEAT = {
    "panel": ("round", "stretch"),
    "menu": ("round", "stretch"),
    "message": ("round", "stretch"),
    "message_warning": ("round", "stretch"),
    "message_error": ("round", "stretch"),
}


def slices(piece):
    """(top, right, bottom, left) slice in image px and border in screen px of `piece`."""
    if piece in SIDES:
        return SIDES[piece]
    s, b = SLICE[piece], BORDER[piece]
    return (s, s, s, s), (b, b, b, b)


def on_colour(p, ground):
    """The palette's text or its background, whichever reads better on `ground`."""
    return p["text"] if contrast(p["text"], ground) >= contrast(p["background"], ground) else p["background"]


def error_colour(p):
    """Errors are red: the palette's reddest role (alert, primary or secondary) when it is
    red enough, else a neon red."""
    import colorsys

    from .neon_palette import rgb01

    best, distance = None, 99.0
    for role in ("alert", "primary", "secondary"):
        hue, light, saturation = colorsys.rgb_to_hls(*rgb01(p[role]))
        away = min(hue, 1.0 - hue) * 360.0
        if saturation > 0.6 and 0.3 < light < 0.8 and away < distance:
            best, distance = p[role], away
    return best if best is not None and distance <= 20.0 else "#ff2e4a"


def default_fill(p):
    """The fill of the default (OK) button: the primary colour, a little deeper."""
    return mix(p["primary"], p["background"], 0.18)


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
        'stroke-opacity="%g" stroke-linecap="butt" />' % (x1, y1, x2, y2, colour, width, opacity)
    )


def _rect(x, y, w, h, colour, opacity=1.0):
    return '<rect x="%g" y="%g" width="%g" height="%g" fill="%s" fill-opacity="%g" />' % (
        x, y, w, h, colour, opacity
    )


def _svg(w, h, body, defs=""):
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="%d" height="%d" viewBox="0 0 %d %d">%s%s</svg>'
        % (w, h, w, h, ("<defs>%s</defs>" % defs) if defs else "", "".join(body))
    )


def _glow(points, colour, strength=1.0):
    """Two wide, faint copies of an outline: the glow under it."""
    return [
        _poly(points, stroke=colour, width=5.0, opacity=0.14 * strength),
        _poly(points, stroke=colour, width=3.2, opacity=0.30 * strength),
    ]


def _brackets(x, y, w, h, k, colour, width=2.4, corners=("tr", "bl")):
    """L-shaped marks with arms `k` long in the given corners of the box (x, y, w, h)."""
    out = []
    if "tr" in corners:
        out += [_line(x + w - k, y, x + w, y, colour, width), _line(x + w, y, x + w, y + k, colour, width)]
    if "bl" in corners:
        out += [_line(x, y + h - k, x, y + h, colour, width), _line(x, y + h, x + k, y + h, colour, width)]
    if "tl" in corners:
        out += [_line(x, y + k, x, y, colour, width), _line(x, y, x + k, y, colour, width)]
    if "br" in corners:
        out += [_line(x + w, y + h - k, x + w, y + h, colour, width), _line(x + w - k, y + h, x + w, y + h, colour, width)]
    return out


def _ticks(w, s, y0, y1, colour, opacity):
    """One ruler tick in the middle of the repeated part of a horizontal edge."""
    mid = s + (w - 2 * s) / 2.0
    return [_line(mid, y0, mid, y1, colour, 1.6, opacity)]


def _frame(w, h, s, fill, fill_opacity, stroke, glow, brackets=None, corners=("tl", "br"),
           ticks=None, inner=None, cut=None, bottom_ticks=True):
    """A cut-corner frame: glow, fill, line, bracket marks, ruler ticks and an inner rule."""
    g = 3.0  # room for the glow; a 2 px line centred here covers screen pixel 1 exactly
    c = cut if cut is not None else max(3.0, s - 3.0)
    pts = _chamfer(g, g, w - 2 * g, h - 2 * g, c, corners)
    body = []
    if glow:
        body += _glow(pts, glow)
    body.append(_poly(pts, fill=fill, fill_opacity=fill_opacity, stroke=stroke, width=2.0))
    if inner:
        # a faint second rule inside the frame along the top and bottom: "glass" depth
        body.append(_line(s, g + 8, w - s, g + 8, inner, 1.2, 0.3))
        body.append(_line(s, h - g - 8, w - s, h - g - 8, inner, 1.2, 0.3))
    if ticks:
        # pointing in from the top edge (and from the bottom edge where `bottom_ticks`); the
        # lower 3 px of a menu stay its plain ground
        if bottom_ticks:
            body += _ticks(w, s, h - g - 1, h - g - 6, ticks, 0.75)
        body += _ticks(w, s, g + 1, g + 6, ticks, 0.6)
    if brackets:
        k = s - 3.0
        body += _brackets(g - 1, g - 1, w - 2 * g + 2, h - 2 * g + 2, k, brackets)
    return _svg(w, h, body)


def _clip(points, xmin, xmax):
    """A convex polygon cut to xmin <= x <= xmax (Sutherland-Hodgman, two edges)."""
    for edge, keep in ((xmin, lambda x: x >= xmin), (xmax, lambda x: x <= xmax)):
        out = []
        for i, (x1, y1) in enumerate(points):
            x0, y0 = points[i - 1]
            if keep(x1):
                if not keep(x0):
                    out.append((edge, y0 + (y1 - y0) * (edge - x0) / (x1 - x0)))
                out.append((x1, y1))
            elif keep(x0):
                out.append((edge, y0 + (y1 - y0) * (edge - x0) / (x1 - x0)))
        points = out
        if not points:
            break
    return points


def _stripes(w, h, colour, ground, opacity, y=0.0, band=None, xmin=None, xmax=None):
    """Hazard stripes leaning right, 12 px apart (a whole number of them in 24 px), inside
    xmin..xmax (the whole width when not given)."""
    band = h if band is None else band
    xmin = 0.0 if xmin is None else xmin
    xmax = float(w) if xmax is None else xmax
    body = []
    if ground:
        body.append(_rect(xmin, y, xmax - xmin, band, ground))
    step = 12
    for x in range(-int(band) - step, w + int(band) + step, step):
        shape = _clip([(x, y + band), (x + 6, y + band), (x + 6 + band, y), (x + band, y)], xmin, xmax)
        if len(shape) >= 3:
            body.append(_poly(" ".join("%g,%g" % pt for pt in shape), fill=colour, fill_opacity=opacity))
    return body


def _message(p, piece):
    """A message box's frame: a header band 14 px tall (hazard stripes in a warning, a red
    band in an error, the primary colour otherwise) above a cut-corner frame."""
    w, h, _s, _b = SIZES[piece]
    top = SIDES[piece][0][0]
    g = 3.0
    colour = {"message_warning": p["alert"], "message_error": error_colour(p)}.get(piece, p["primary"])
    pts = _chamfer(g, g, w - 2 * g, h - 2 * g, 8, ("tl", "br"))
    body = _glow(pts, colour, 0.8 if piece == "message" else 1.2)
    body.append(_poly(pts, fill=p["chrome"], stroke=colour, width=2.0))
    band_y, band_h = g + 3, top - g - 7
    if piece == "message_warning":
        # inside the band; the corner cut at the top-left stays clear
        body += _stripes(w, h, p["alert"], mix(p["chrome"], p["alert"], 0.18), 0.85,
                         y=band_y, band=band_h, xmin=10, xmax=w - 2)
        defs = ""
    else:
        tint = 0.30 if piece == "message_error" else 0.16
        body.append(_rect(10, band_y, w - 12, band_h, mix(p["chrome"], colour, tint)))
        body.append(_line(10, band_y + band_h - 3, w - 2, band_y + band_h - 3, colour, 1.2, 0.6))
        defs = ""
    body.append(_line(g, top - 2, w - g, top - 2, colour, 2.0))
    if piece == "message_error":
        body.append(_line(g, top + 1.5, w - g, top + 1.5, colour, 1.0, 0.55))
    body += _brackets(g - 1, g - 1, w - 2 * g + 2, h - 2 * g + 2, 9.0, mix(colour, "#ffffff", 0.35))
    return _svg(w, h, body, defs)


def _message_icon(p, piece):
    """A message box's sign as line art: a hexagon (information, question), a hazard
    triangle (warning) or a cut-corner square with a cross (error)."""
    w = h = 64
    kind = piece[5:]
    colour = {"warning": p["alert"], "error": error_colour(p)}.get(kind, p["primary"])
    hot = mix(colour, "#ffffff", 0.35)
    if kind == "warning":
        shape = "32,6 60,56 4,56"
    elif kind == "error":
        shape = _chamfer(6, 6, 52, 52, 12, ("tl", "tr", "br", "bl"))
    else:
        shape = "32,4 56,18 56,46 32,60 8,46 8,18"
    body = _glow(shape, colour, 1.4) + [_poly(shape, fill=colour, fill_opacity=0.14, stroke=colour, width=3.0)]
    if kind == "warning":
        body += [_line(32, 24, 32, 41, hot, 5.0), _rect(29.5, 45, 5, 5, hot)]
    elif kind == "error":
        body += [_line(22, 22, 42, 42, hot, 5.0), _line(42, 22, 22, 42, hot, 5.0)]
    elif kind == "question":
        body.append('<polyline points="24,24 24,18 40,18 40,30 32,34 32,40" fill="none" stroke="%s" '
                    'stroke-width="5" stroke-linecap="butt" stroke-linejoin="miter" />' % hot)
        body.append(_rect(29.5, 44, 5, 5, hot))
    else:
        body += [_rect(29.5, 16, 5, 5, hot), _line(32, 26, 32, 48, hot, 5.0)]
    return _svg(w, h, body)


def svg(piece, p):
    """The SVG text of one piece in palette `p` (theme / neon_palette.derive keys)."""
    w, h, s, _border = SIZES[piece]
    primary, secondary = p["primary"], p["secondary"]
    hot, dim = p["primary_hot"], p["primary_dim"]
    if piece == "panel":
        return _frame(w, h, s, p["chrome"], 0.55, mix(p["line"], primary, 0.25), None, brackets=primary,
                      ticks=dim, cut=8)
    if piece == "button":
        body = [_poly(_chamfer(3, 3, w - 6, h - 6, 5), fill=p["button"], stroke=dim, width=2.0),
                _line(w - 9, h - 3.5, w - 3.5, h - 9, primary, 2.0)]
        return _svg(w, h, body)
    if piece == "button_hover":
        pts = _chamfer(3, 3, w - 6, h - 6, 5)
        body = _glow(pts, primary) + [_poly(pts, fill=p["hover"], stroke=primary, width=2.0),
                                      _line(w - 9, h - 3.5, w - 3.5, h - 9, hot, 2.4)]
        return _svg(w, h, body)
    if piece == "button_pressed":
        pts = _chamfer(3, 3, w - 6, h - 6, 5)
        return _svg(w, h, _glow(pts, primary, 1.4) + [_poly(pts, fill=p["active"], stroke=hot, width=2.4)])
    if piece == "button_default":
        pts = _chamfer(3, 3, w - 6, h - 6, 5)
        body = _glow(pts, primary) + [_poly(pts, fill=default_fill(p), stroke=hot, width=2.0)]
        body += _brackets(1, 1, w - 2, h - 2, 5.0, hot, 2.0)
        return _svg(w, h, body)
    if piece in ("field", "field_focus"):
        focus = piece == "field_focus"
        pts = _chamfer(1, 1, w - 2, h - 2, 4, ("br",))
        body = _glow(pts, primary, 0.8) if focus else []
        body.append(_poly(pts, fill=mix(p["field"], primary, 0.05) if focus else p["field"],
                          stroke=primary if focus else mix(p["line"], p["field"], 0.35), width=1.6))
        body.append(_line(2, h - 2, w - 6, h - 2, hot if focus else dim, 2.6 if focus else 2.0))
        body.append(_line(2, 3, 2, 9, hot if focus else dim, 2.0))  # the slot's start mark
        return _svg(w, h, body)
    if piece == "menu":
        return _frame(w, h, s, p["menu"], 0.88, primary, primary, brackets=hot, ticks=dim, inner=primary,
                      cut=9, bottom_ticks=False)
    if piece == "menu_item":
        defs = (
            '<linearGradient id="fade" x1="0" y1="0" x2="1" y2="0">'
            '<stop offset="0" stop-color="%s" stop-opacity="0.38" />'
            '<stop offset="1" stop-color="%s" stop-opacity="0.06" /></linearGradient>' % (primary, primary)
        )
        body = ['<rect x="0" y="0" width="%d" height="%d" fill="url(#fade)" />' % (w, h),
                _rect(0, 0, 6, h, hot), _rect(6, 0, 2, h, primary, 0.45)]
        return _svg(w, h, body, defs)
    if piece == "tooltip":
        return _frame(w, h, s, p["menu"], 0.94, secondary, secondary, brackets=p["secondary_hot"],
                      corners=("tl",), cut=8)
    if piece == "header":
        body = [
            _poly(_chamfer(1, 1, w - 2, h - 2, 6, ("tl",)), fill=p["header"], stroke=p["line"], width=1.5),
            _line(2, h - 1.5, w - 2, h - 1.5, primary, 2.0),
        ]
        return _svg(w, h, body)
    if piece == "tab_active":
        # a faint tint above a bright underline (the lower 4 image px: the 2 screen px edge)
        body = [
            _rect(0, 0, w, h - 4, primary, 0.10),
            _rect(0, h - 8, w, 4, primary, 0.18),
            _rect(0, h - 4, w, 4, hot),
        ]
        return _svg(w, h, body)
    if piece in ("check", "check_on"):
        on = piece == "check_on"
        pts = _chamfer(3, 3, w - 6, h - 6, 5, ("tl", "br"))
        body = _glow(pts, primary, 0.7) if on else []
        body.append(_poly(pts, fill=primary if on else p["field"], fill_opacity=0.95 if on else 1.0,
                          stroke=hot if on else p["check_line"], width=2.0))
        if on:
            body.append(
                '<polyline points="7.5,13 11.5,17 18.5,9" fill="none" stroke="%s" stroke-width="3" '
                'stroke-linecap="square" stroke-linejoin="miter" />' % on_colour(p, primary)
            )
        else:
            body.append(_line(w - 9, h - 4.5, w - 4.5, h - 9, p["check_line"], 1.6))
        return _svg(w, h, body)
    if piece in ("radio", "radio_on"):
        on = piece == "radio_on"
        mid = w / 2.0
        diamond = "%g,%g %g,%g %g,%g %g,%g" % (mid, 3, w - 3, mid, mid, h - 3, 3, mid)
        body = _glow(diamond, primary, 0.7) if on else []
        body.append(_poly(diamond, fill=p["field"], stroke=hot if on else p["check_line"], width=2.0))
        if on:
            inner = "%g,%g %g,%g %g,%g %g,%g" % (mid, 8, w - 8, mid, mid, h - 8, 8, mid)
            body.append(_poly(inner, fill=primary))
        return _svg(w, h, body)
    if piece == "progress":
        pts = _chamfer(1, 1, w - 2, h - 2, 4, ("tl", "br"))
        return _svg(w, h, [_poly(pts, fill=p["field"], stroke=p["line"], width=1.6),
                           _line(2, 4, 2, h - 4, dim, 2.0)])
    if piece in ("scroll_handle", "scroll_handle_h"):
        pts = _chamfer(2, 2, w - 4, h - 4, 3, ("tl", "tr", "br", "bl"))
        return _svg(w, h, [_poly(pts, fill=dim, stroke=primary, width=1.2, opacity=0.8)])
    if piece == "rail_v":
        return _svg(w, h, [_line(w / 2.0, 0, w / 2.0, h, p["line"], 1.4, 0.7)])
    if piece == "rail_h":
        return _svg(w, h, [_line(0, h / 2.0, w, h / 2.0, p["line"], 1.4, 0.7)])
    if piece == "slider_handle":
        pts = _chamfer(3, 2, w - 6, h - 4, 4, ("tl", "br"))
        body = _glow(pts, primary) + [_poly(pts, fill=hot, stroke=primary, width=1.6),
                                      _line(w / 2.0, 9, w / 2.0, h - 9, p["background"], 2.0, 0.7)]
        return _svg(w, h, body)
    if piece == "stripes":
        return _svg(w, h, _stripes(w, h, primary, None, 0.22))
    if piece == "warning_header":
        return _svg(w, h, _stripes(w, h, p["alert"], mix(p["background"], p["alert"], 0.12), 0.55))
    if piece in ("message", "message_warning", "message_error"):
        return _message(p, piece)
    if piece.startswith("icon_"):
        return _message_icon(p, piece)
    if piece == "arrow_down":
        body = [
            '<polyline points="4,7 10,13 16,7" fill="none" stroke="%s" stroke-width="2.6" '
            'stroke-linecap="square" stroke-linejoin="miter" />' % primary,
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
