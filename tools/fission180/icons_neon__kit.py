# SPDX-License-Identifier: LGPL-2.1-or-later
# Neon Lights (neon-lights-design.md 6.5, plan task B5): drawing helpers for the hand-made neon
# icons of the area files (icons_neon_<area>.py); named with a double underscore so it runs before them. Run inside make_icons.py's namespace like the
# other icons_*.py files, so line, path, poly, circle, iso and _BOUNDS are its own. Every helper
# is prefixed nb_ so it can never clash with the core neon recipes (icons_neon_core.py).
#
# The language: thin angular lines in colour tokens (neon_icon_style: primary = the object,
# secondary = what the tool changes or creates, alert = warnings and errors, text = neutral
# marks), each over a wider, fainter copy of itself (the glow: Qt draws SVG Tiny, no blur),
# faces as a faint fill, corners cut at 45 degrees, bracket marks instead of round frames.
# Original line art; nothing traced.
# flake8: noqa

NB_P, NB_S, NB_A, NB_T, NB_G = "#n30001", "#n30002", "#n30003", "#n30004", "#n30006"
NB_GLOW = 'stroke-opacity="0.26"'


def nb_gw(w):
    """Width of the glow under a line of width w."""
    return w * 2.2 + 0.9


def nb_line(x1, y1, x2, y2, c=NB_P, w=1.6, glow=True, extra=""):
    out = line(x1, y1, x2, y2, c, nb_gw(w), NB_GLOW) if glow else ""
    return out + line(x1, y1, x2, y2, c, w, extra)


def nb_path(d, c=NB_P, w=1.6, fill="none", fo=0.16, glow=True, extra=""):
    out = path(d, c, nb_gw(w), "none", NB_GLOW) if glow else ""
    if fill != "none":
        extra = ('fill-opacity="%.2f" ' % fo) + extra
    return out + path(d, c, w, fill, extra)


def nb_poly(points, c=NB_P, w=1.5, fo=0.14, fill=None, glow=True):
    """A closed outline over a faint fill of the same colour (or `fill`)."""
    stroke = 'stroke="%s" stroke-width="%.2f" stroke-linejoin="round"' % (c, w)
    out = ""
    if glow:
        out += poly(points, "none", 'stroke="%s" stroke-width="%.2f" stroke-linejoin="round" %s'
                    % (c, nb_gw(w), NB_GLOW))
    if fo:
        return out + poly(points, fill or c, 'fill-opacity="%.2f" %s' % (fo, stroke))
    return out + poly(points, "none", stroke)


def nb_solid(points, c=NB_S):
    """A small solid mark (an arrow head, a point): no glow, it would blur it."""
    return poly(points, c, 'stroke="%s" stroke-width="0.6" stroke-linejoin="round"' % c)


def nb_circle(cx, cy, r, c=NB_P, w=1.6, fo=0.0, glow=True):
    out = ""
    if glow:
        out += circle(cx, cy, r, "none", c, nb_gw(w)).replace("/>", " %s/>" % NB_GLOW)
    if fo:
        return out + circle(cx, cy, r, c, c, w).replace("/>", ' fill-opacity="%.2f"/>' % fo)
    return out + circle(cx, cy, r, "none", c, w)


def nb_dot(x, y, c=NB_S, r=2.2):
    """A point: a small diamond."""
    return nb_solid([(x, y - r), (x + r, y), (x, y + r), (x - r, y)], c)


def nb_cut(x, y, w, h, k=4.0, k2=None):
    """Points of a rectangle with its top-left and bottom-right corners cut (k, k2)."""
    k2 = k if k2 is None else k2
    return [(x + k, y), (x + w, y), (x + w, y + h - k2), (x + w - k2, y + h), (x, y + h), (x, y + k)]


def nb_brackets(x, y, w, h, n=4.0, c=NB_P, w_=1.4):
    """Four corner bracket marks round a box: the HUD frame."""
    d = (
        "M%.2f %.2f V%.2f H%.2f " % (x, y + n, y, x + n)
        + "M%.2f %.2f H%.2f V%.2f " % (x + w - n, y, x + w, y + n)
        + "M%.2f %.2f V%.2f H%.2f " % (x + w, y + h - n, y + h, x + w - n)
        + "M%.2f %.2f H%.2f V%.2f" % (x + n, y + h, x, y + h - n)
    )
    return nb_path(d, c, w_)


def nb_arrow(x1, y1, x2, y2, c=NB_S, w=1.6, head=4.6):
    """A line ending in a solid head (the head is not glowed)."""
    ang = math.atan2(y2 - y1, x2 - x1)
    hx1, hy1 = x2 - head * math.cos(ang - 0.5), y2 - head * math.sin(ang - 0.5)
    hx2, hy2 = x2 - head * math.cos(ang + 0.5), y2 - head * math.sin(ang + 0.5)
    bx, by = x2 - head * 0.75 * math.cos(ang), y2 - head * 0.75 * math.sin(ang)
    return nb_line(x1, y1, bx, by, c, w) + nb_solid([(x2, y2), (hx1, hy1), (hx2, hy2)], c)


def nb_box(x, y, z, dx, dy, dz, c=NB_P, ox=24, oy=30, s=1.0, w=1.4, glow=True):
    """An isometric block as a glowing wireframe: faint faces (lit top), one silhouette, the
    three edges of the near corner."""
    q = lambda a, b, h: iso(a, b, h, ox, oy, s)  # noqa: E731
    top = [q(x, y, z + dz), q(x + dx, y, z + dz), q(x + dx, y + dy, z + dz), q(x, y + dy, z + dz)]
    left = [q(x, y + dy, z), q(x + dx, y + dy, z), q(x + dx, y + dy, z + dz), q(x, y + dy, z + dz)]
    right = [q(x + dx, y, z), q(x + dx, y + dy, z), q(x + dx, y + dy, z + dz), q(x + dx, y, z + dz)]
    sil = [q(x, y, z + dz), q(x + dx, y, z + dz), q(x + dx, y, z), q(x + dx, y + dy, z),
           q(x, y + dy, z), q(x, y + dy, z + dz)]
    near = q(x + dx, y + dy, z + dz)
    out = poly(top, c, 'fill-opacity="0.24"') + poly(left, c, 'fill-opacity="0.12"')
    out += poly(right, c, 'fill-opacity="0.05"')
    out += nb_poly(sil, c, w, 0, glow=glow)
    for corner in (q(x + dx, y, z + dz), q(x, y + dy, z + dz), q(x + dx, y + dy, z)):
        out += line(near[0], near[1], corner[0], corner[1], c, w * 0.8)
    return out


def nb_page(x, y, w, h, c=NB_P, k=5.0, lines=3, lc=NB_T):
    """A sheet of paper with a cut corner and a few lines of text."""
    pts = [(x, y), (x + w - k, y), (x + w, y + k), (x + w, y + h), (x, y + h)]
    out = nb_poly(pts, c, 1.5, 0.12)
    for i in range(lines):
        ly = y + 7 + i * 4.5
        if ly > y + h - 3:
            break
        out += line(x + 4, ly, x + w - (4 if i < lines - 1 else w * 0.45), ly, lc, 1.3)
    return out


def nb_check(cx, cy, s, c=NB_S, w=2.0):
    return nb_path("M%.2f %.2f L%.2f %.2f L%.2f %.2f" % (
        cx - s * 0.5, cy, cx - s * 0.12, cy + s * 0.38, cx + s * 0.55, cy - s * 0.4), c, w)


def nb_xmark(cx, cy, s, c=NB_A, w=2.0):
    h = s * 0.42
    return nb_line(cx - h, cy - h, cx + h, cy + h, c, w) + nb_line(cx - h, cy + h, cx + h, cy - h, c, w)


def nb_octagon(cx, cy, r, c=NB_S, w=1.6, fo=0.12):
    """A badge frame: an octagon (the neon look's circle)."""
    pts = [(cx + r * math.cos(math.radians(22.5 + 45 * i)), cy + r * math.sin(math.radians(22.5 + 45 * i)))
           for i in range(8)]
    return nb_poly(pts, c, w, fo)


def nb_ok_badge(cx=36, cy=36, r=8.5):
    return nb_octagon(cx, cy, r, NB_S, 1.4, 0.22) + nb_check(cx, cy, r * 1.05, NB_S, 1.8)


def nb_bad_badge(cx=36, cy=36, r=8.5):
    return nb_octagon(cx, cy, r, NB_A, 1.4, 0.22) + nb_xmark(cx, cy, r * 1.0, NB_A, 1.8)


def nb_plus_badge(cx=37, cy=37, r=8.0, c=NB_S):
    return (nb_octagon(cx, cy, r, c, 1.4, 0.22)
            + line(cx - r * 0.5, cy, cx + r * 0.5, cy, c, 2.0)
            + line(cx, cy - r * 0.5, cx, cy + r * 0.5, c, 2.0))


def nb_warn_badge(cx=36, cy=36, s=11.0):
    h = s * 0.87
    tri = [(cx, cy - h * 0.62), (cx + s * 0.58, cy + h * 0.38), (cx - s * 0.58, cy + h * 0.38)]
    return (nb_poly(tri, NB_A, 1.4, 0.22) + line(cx, cy - h * 0.22, cx, cy + h * 0.08, NB_A, 1.6)
            + nb_dot(cx, cy + h * 0.24, NB_A, 0.9))


def nb_hatch(x, y, w, c=NB_T, n=4.0):
    """A fixed ground: a line with short diagonal ticks under it."""
    out = nb_line(x, y, x + w, y, c, 1.4)
    k = x + 2
    while k < x + w:
        out += line(k, y + 4, k + 3, y + 1, c, 1.0)
        k += n
    return out


def nb_segments(x, y, w, h, n, colours):
    """A segmented bar (stress scale, progress): n cells with gaps."""
    gap = 1.2
    cw = (w - gap * (n - 1)) / n
    out = ""
    for i in range(n):
        c = colours[i % len(colours)]
        out += rect(x + i * (cw + gap), y, cw, h, c, 0, 'fill-opacity="%.2f"' % (0.35 + 0.55 * i / max(1, n - 1)))
    return out


def nb_sheet(d, c=NB_P, w=4.6):
    """A sheet seen edge-on: its two faces as a hollow double line over a faint glow."""
    return (
        path(d, c, w + 2.6, "none", 'stroke-opacity="0.22"')
        + path(d, c, w)
        + path(d, NB_G, w - 2.4)
        + path(d, c, w - 2.4, "none", 'stroke-opacity="0.22"')
    )
