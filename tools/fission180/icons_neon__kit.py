# SPDX-License-Identifier: LGPL-2.1-or-later
# Neon Lights (neon-lights-design.md 6.5): the ONE drawing kit of every hand-made neon icon
# (icons_neon_core.py and the icons_neon_<area>.py files). Named with a double underscore so it
# runs before them (make_icons.py execs the icons_*.py files in sorted order into its own
# namespace, so line, path, poly, circle, iso, P, _grow, _path_bounds and neon_icon_style are at
# hand; a name used as a default argument must be defined in a file that sorts earlier).
#
# The language (one standard for the whole set, the converter included):
# - thin angular lines in colour tokens: primary = the object, secondary = what the tool
#   changes or creates (and gold/orange accents), alert ONLY for warnings, deleting, failures
#   and the hot end of a result scale, text = neutral marks (glows in primary);
# - outlines LINE (2.1, about 1 px at 18 px), inner detail DETAIL (1.4), each line over a
#   wider, fainter copy (the glow: neon_icon_style.glow_width, opacity GLOW; Qt draws SVG
#   Tiny, no blur);
# - faces as a faint fill, never solid blocks; at most a few open shapes per icon so nothing
#   fills into a blob at 18 px;
# - corners cut at 45 degrees, top-left and bottom-right (ncut, nb_cut, the converter);
#   corner brackets instead of round frames; octagons instead of circles for badges;
# - points are small solid squares (ndot); arrow heads are small solid triangles (nhead);
# - transport buttons (timeline, animation) all come from ntransport().
# Original line art in an industrial sci-fi HUD style; nothing traced.
# flake8: noqa

NP, NS, NA, NT, NG = "#n30001", "#n30002", "#n30003", "#n30004", "#n30006"
NW, NI = neon_icon_style.LINE, neon_icon_style.DETAIL  # outline and inner-detail widths
GLOW = neon_icon_style.GLOW_OPACITY


def _d(points, close=False):
    """A path through points (absolute moves and lines)."""
    out = "M%.2f %.2f" % points[0]
    for x, y in points[1:]:
        out += " L%.2f %.2f" % (x, y)
    return out + (" Z" if close else "")


def nl(d, c=NP, w=NW, fill="none", fo=0.0, glow=GLOW, dash=None, join="miter", cap="square"):
    """One neon line (a path): its glow, then the line. `fill` + `fo` give a faint face."""
    _path_bounds(d, w / 2)
    extra = ' stroke-dasharray="%s"' % dash if dash else ""
    glow_colour = NP if c == NT else c
    out = ""
    if glow:
        out += (
            '<path d="%s" fill="none" stroke="%s" stroke-width="%.2f" stroke-opacity="%.2f" '
            'stroke-linejoin="%s" stroke-linecap="%s"/>'
            % (d, glow_colour, neon_icon_style.glow_width(w), glow, join, cap)
        )
    face = ' fill="%s" fill-opacity="%.2f"' % (fill, fo) if fill != "none" else ' fill="none"'
    out += (
        '<path d="%s"%s stroke="%s" stroke-width="%.2f" '
        'stroke-linejoin="%s" stroke-linecap="%s"%s/>'
        % (d, face, c, w, join, cap, extra)
    )
    return out


def nf(d, c=NP, fo=0.16):
    """A faint face with no line (under lines drawn separately)."""
    _path_bounds(d, 0)
    return '<path d="%s" fill="%s" fill-opacity="%.2f" stroke="none"/>' % (d, c, fo)


def npoly(points, c=NP, w=NW, fo=0.0, close=True, **kw):
    return nl(_d(points, close), c, w, c if fo else "none", fo, **kw)


def nseg(x1, y1, x2, y2, c=NP, w=NW, **kw):
    return nl(_d([(x1, y1), (x2, y2)]), c, w, **kw)


def ndot(x, y, c=NS, r=2.0):
    """A small solid square node (a sketch point, a light)."""
    _grow(x, y, r)
    return '<rect x="%.2f" y="%.2f" width="%.2f" height="%.2f" fill="%s"/>' % (
        x - r,
        y - r,
        2 * r,
        2 * r,
        c,
    )


def ncut(x, y, w, h, c=NP, cut=None, lw=NW, fo=0.0, corners="tl br", **kw):
    """A rectangle with cut corners (the HUD frame): top-left and bottom-right, the set's one
    convention (the converter and nb_cut cut the same two)."""
    k = cut if cut is not None else min(w, h) * 0.25
    tl = "tl" in corners and k
    tr = "tr" in corners and k
    br = "br" in corners and k
    bl = "bl" in corners and k
    pts = [(x + (tl or 0), y), (x + w - (tr or 0), y)]
    if tr:
        pts.append((x + w, y + tr))
    pts.append((x + w, y + h - (br or 0)))
    if br:
        pts.append((x + w - br, y + h))
    pts.append((x + (bl or 0), y + h))
    if bl:
        pts.append((x, y + h - bl))
    pts.append((x, y + (tl or 0)))
    return npoly(pts, c, lw, fo, **kw)


def nbrackets(x, y, w, h, c=NP, k=5.0, lw=NW, **kw):
    """Four corner brackets around a box (a HUD target frame)."""
    out = ""
    for cx, cy, sx, sy in (
        (x, y, 1, 1),
        (x + w, y, -1, 1),
        (x + w, y + h, -1, -1),
        (x, y + h, 1, -1),
    ):
        out += npoly([(cx, cy + sy * k), (cx, cy), (cx + sx * k, cy)], c, lw, close=False, **kw)
    return out


def nhead(x, y, ang, c=NS, w=NW, head=5.0):
    """A solid arrow head with its tip at (x, y), pointing along ang (radians): the set's one
    arrow head (the converter keeps the normal icons' solid heads solid too). Not glowed: a
    glow would blur it at 18 px."""
    h1 = (x - head * math.cos(ang - 0.5), y - head * math.sin(ang - 0.5))
    h2 = (x - head * math.cos(ang + 0.5), y - head * math.sin(ang + 0.5))
    for px, py in ((x, y), h1, h2):
        _grow(px, py, 0.5)
    return '<polygon points="%s" fill="%s" stroke="%s" stroke-width="0.8" stroke-linejoin="miter"/>' % (
        P([(x, y), h1, h2]),
        c,
        c,
    )


def narrow(x1, y1, x2, y2, c=NS, w=NW, head=5.0, **kw):
    """A line ending in a solid head at (x2, y2)."""
    a = math.atan2(y2 - y1, x2 - x1)
    bx, by = x2 - head * 0.7 * math.cos(a), y2 - head * 0.7 * math.sin(a)
    return nl(_d([(x1, y1), (bx, by)]), c, w, cap="butt", **kw) + nhead(x2, y2, a, c, w, head)


def nbox(x, y, z, dx, dy, dz, c=NP, ox=24, oy=30, s=1.0, top=None, w=NW, fo=0.14, inner=True):
    """An isometric block as a glowing wireframe: faint faces, the silhouette at full weight,
    the three inner edges thinner. `top` colours the top face (the face a tool acts on)."""
    q = lambda a, b, h: iso(a, b, h, ox, oy, s)  # noqa: E731
    T = [q(x, y, z + dz), q(x + dx, y, z + dz), q(x + dx, y + dy, z + dz), q(x, y + dy, z + dz)]
    B = [q(x, y, z), q(x + dx, y, z), q(x + dx, y + dy, z), q(x, y + dy, z)]
    out = nf(_d([T[3], T[2], B[2], B[3]], True), c, fo * 0.7)  # left face
    out += nf(_d([T[1], T[2], B[2], B[1]], True), c, fo * 0.35)  # right face
    out += nf(_d(T, True), top or c, fo * (1.9 if top else 1.4))
    out += nl(_d([T[0], T[1], B[1], B[2], B[3], T[3]], True), c, w)
    if inner:
        out += nl(_d([T[3], T[2], T[1]]) + " " + _d([T[2], B[2]]), c, w * 0.66, glow=0.16)
    if top:
        out += nl(_d(T, True), top, w * 0.9)
    return out


def nplus(cx, cy, c=NS, r=6.5):
    """ "Create": a cut-corner badge over a ground-coloured patch with a plus."""
    k = r * 0.45
    pts = [
        (cx - r + k, cy - r),
        (cx + r, cy - r),
        (cx + r, cy + r - k),
        (cx + r - k, cy + r),
        (cx - r, cy + r),
        (cx - r, cy - r + k),
    ]
    patch = '<polygon points="%s" fill="%s"/>' % (P(pts), NG)
    _grow(cx, cy, r + 1)
    return (
        patch
        + npoly(pts, c, 1.6)
        + nl(
            "M%.2f %.2f H%.2f M%.2f %.2f V%.2f"
            % (cx - r * 0.5, cy, cx + r * 0.5, cx, cy - r * 0.5, cy + r * 0.5),
            c,
            1.8,
            cap="butt",
        )
    )


def nmesh(cx, cy, r, c=NP, hi=None, w=NW):
    """A triangulated hexagon (a mesh): outline, spokes; `hi` fills chosen triangles."""
    pts = [
        (cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
        for a in (-90, -30, 30, 90, 150, 210)
    ]
    out = ""
    for k, col in (hi or {}).items():
        out += nf(_d([(cx, cy), pts[k], pts[(k + 1) % 6]], True), col, 0.45)
    out += nl(_d(pts, True), c, w)
    # three long diagonals only (six big triangles): with the old inner triangle too, every
    # mesh icon filled into a blob at 18 px
    spokes = " ".join(_d([pts[k], pts[k + 3]]) for k in range(3))
    return out + nl(spokes, c, NI, glow=0.14, cap="butt")


def nsheet(x0, y0, x1, y1, lift, c=NS, fo=0.18, w=NW):
    """A curved surface: a thin band between two parallel curves (top edge bowed up)."""
    d = "M%.2f %.2f Q%.2f %.2f %.2f %.2f L%.2f %.2f Q%.2f %.2f %.2f %.2f Z" % (
        x0,
        y0,
        (x0 + x1) / 2,
        y0 - lift,
        x1,
        y1,
        x1 + 6,
        y1 + 6,
        (x0 + x1) / 2 + 6,
        y0 - lift + 6,
        x0 + 6,
        y0 + 6,
    )
    return nl(d, c, w, c, fo)


def ncog(cx, cy, r, teeth=8, c=NT, w=NW, hub=None):
    """An angular cog: flat-topped teeth, a hexagonal hub."""
    pts = []
    for i in range(teeth):
        a0 = 2 * math.pi * i / teeth
        for da, rr in ((-0.20, r * 0.74), (-0.13, r), (0.13, r), (0.20, r * 0.74)):
            pts.append((cx + rr * math.cos(a0 + da), cy + rr * math.sin(a0 + da)))
    out = npoly(pts, c, w, fo=0.0)
    hub_r = r * 0.34
    hexagon = [
        (
            cx + hub_r * math.cos(math.radians(30 + 60 * i)),
            cy + hub_r * math.sin(math.radians(30 + 60 * i)),
        )
        for i in range(6)
    ]
    return out + npoly(hexagon, hub or NS, NI + 0.2)


def ncircle(cx, cy, r, c=NP, w=NW, fo=0.0, **kw):
    """A circle as a path (so it glows and frames like every other line)."""
    d = "M%.2f %.2f A%.2f %.2f 0 1 0 %.2f %.2f A%.2f %.2f 0 1 0 %.2f %.2f Z" % (
        cx - r, cy, r, r, cx + r, cy, r, r, cx - r, cy)
    _grow(cx, cy, r + w / 2)
    return nl(d, c, w, c if fo else "none", fo, **kw)


def noct(cx, cy, r, c=NS, w=NW, fo=0.0, **kw):
    """An octagon (the set's badge / round frame)."""
    pts = [(cx + r * math.cos(math.radians(22.5 + 45 * i)), cy + r * math.sin(math.radians(22.5 + 45 * i)))
           for i in range(8)]
    return npoly(pts, c, w, fo, **kw)


def npage(x, y, w, h, c=NP, k=6.0, lines=3, lc=NT, fo=0.08):
    """A sheet of paper: an outline with a folded top-right corner and a few text lines, kept
    apart enough (6.5 units) that they never merge at 18 px."""
    out = nl(_d([(x, y), (x + w - k, y), (x + w, y + k), (x + w, y + h), (x, y + h)], True), c, NW, c, fo)
    out += nl(_d([(x + w - k, y), (x + w - k, y + k), (x + w, y + k)]), c, NI, glow=0)
    for i in range(lines):
        ly = y + k + 5 + i * 6.5
        if ly > y + h - 4:
            break
        end = x + w - 5 if i < lines - 1 else x + w * 0.6
        out += nseg(x + 5, ly, end, ly, lc, NI + 0.3, cap="butt", glow=0.14)
    return out


def nbar(x, y, w, h, c=NT, fill=NP, fo=0.22):
    """A transport bar (a stop / pause / skip bar): a thin outlined block, the triangles' style."""
    return npoly([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], c, NW, 0) + nf(
        _d([(x, y), (x + w, y), (x + w, y + h), (x, y + h)], True), fill, fo)


def ntri(x, cy, h, flip=False, c=NT, fill=NP, fo=0.22):
    """A transport triangle of height h, its flat side at x (pointing right, or left if flip)."""
    tip = x - h * 0.85 if flip else x + h * 0.85
    pts = [(x, cy - h / 2), (tip, cy), (x, cy + h / 2)]
    return npoly(pts, c, NW, 0) + nf(_d(pts, True), fill, fo)


def ntransport(kind):
    """One style for every play-back button (timeline tl_* and animation anim_*): text-white
    outlines over a faint primary fill, bars as thin outlined blocks."""
    if kind == "play":
        return ntri(15, 24, 24)
    if kind == "pause":
        return nbar(13, 12, 7, 24) + nbar(28, 12, 7, 24)
    if kind == "back":  # one step back: a triangle pointing left
        return ntri(33, 24, 24, True)
    if kind == "step":  # one step forward: a triangle and one bar
        return ntri(10, 24, 24) + nbar(34, 12, 5, 24)
    if kind == "start":  # to the start: two bars, then a triangle pointing left
        return nbar(6, 12, 4, 24) + nbar(13, 12, 4, 24) + ntri(41, 24, 24, True)
    if kind == "end":
        return ntri(7, 24, 24) + nbar(31, 12, 4, 24) + nbar(38, 12, 4, 24)
    if kind == "rewind":  # two triangles pointing left
        return ntri(25, 24, 20, True) + ntri(42, 24, 20, True)
    if kind == "forward":
        return ntri(6, 24, 20) + ntri(23, 24, 20)
    raise ValueError(kind)


# ---- the nb_ names (icons_neon_<area>.py recipes): the same kit under the names those recipes
# use. Their widths were drawn on a 1.6 scale; _nbw maps them onto the set's standard (1.6 -> LINE).
NB_P, NB_S, NB_A, NB_T, NB_G = NP, NS, NA, NT, NG


def _nbw(w):
    return w * NW / 1.6


def _nbdash(extra):
    import re as _re

    m = _re.search(r'stroke-dasharray="([^"]*)"', extra or "")
    return m.group(1) if m else None


def nb_line(x1, y1, x2, y2, c=NB_P, w=1.6, glow=True, extra=""):
    return nseg(x1, y1, x2, y2, c, _nbw(w), glow=GLOW if glow else 0, dash=_nbdash(extra), cap="butt")


def nb_path(d, c=NB_P, w=1.6, fill="none", fo=0.16, glow=True, extra=""):
    return nl(d, c, _nbw(w), fill, fo if fill != "none" else 0.0, glow=GLOW if glow else 0,
              dash=_nbdash(extra), cap="butt")


def nb_poly(points, c=NB_P, w=1.5, fo=0.14, fill=None, glow=True):
    """A closed outline over a faint fill of the same colour (or `fill`)."""
    return nl(_d(points, True), c, _nbw(w), (fill or c) if fo else "none", fo, glow=GLOW if glow else 0)


def nb_solid(points, c=NB_S):
    """A small solid mark (an arrow head): no glow, it would blur it."""
    for x, y in points:
        _grow(x, y, 0.5)
    return '<polygon points="%s" fill="%s" stroke="%s" stroke-width="0.8" stroke-linejoin="miter"/>' % (
        P(points), c, c)


def nb_circle(cx, cy, r, c=NB_P, w=1.6, fo=0.0, glow=True):
    return ncircle(cx, cy, r, c, _nbw(w), fo, glow=GLOW if glow else 0)


def nb_dot(x, y, c=NB_S, r=2.2):
    """A point: the set's small solid square."""
    return ndot(x, y, c, r * 0.8)


def nb_cut(x, y, w, h, k=4.0, k2=None):
    """Points of a rectangle with its top-left and bottom-right corners cut (k, k2)."""
    k2 = k if k2 is None else k2
    return [(x + k, y), (x + w, y), (x + w, y + h - k2), (x + w - k2, y + h), (x, y + h), (x, y + k)]


def nb_brackets(x, y, w, h, n=4.0, c=NB_P, w_=1.4):
    return nbrackets(x, y, w, h, c, n, _nbw(w_))


def nb_arrow(x1, y1, x2, y2, c=NB_S, w=1.6, head=4.6):
    return narrow(x1, y1, x2, y2, c, _nbw(w), head)


def nb_box(x, y, z, dx, dy, dz, c=NB_P, ox=24, oy=30, s=1.0, w=1.4, glow=True):
    return nbox(x, y, z, dx, dy, dz, c, ox, oy, s, w=_nbw(w) if w >= 1.4 else NI)


def nb_page(x, y, w, h, c=NB_P, k=5.0, lines=3, lc=NB_T):
    return npage(x, y, w, h, c, max(k, 5.0), lines, lc)


def nb_check(cx, cy, s, c=NB_S, w=2.0):
    return nb_path("M%.2f %.2f L%.2f %.2f L%.2f %.2f" % (
        cx - s * 0.5, cy, cx - s * 0.12, cy + s * 0.38, cx + s * 0.55, cy - s * 0.4), c, w)


def nb_xmark(cx, cy, s, c=NB_A, w=2.0):
    h = s * 0.42
    return nb_path("M%.2f %.2f L%.2f %.2f M%.2f %.2f L%.2f %.2f" % (
        cx - h, cy - h, cx + h, cy + h, cx - h, cy + h, cx + h, cy - h), c, w)


def nb_octagon(cx, cy, r, c=NB_S, w=1.6, fo=0.12):
    return noct(cx, cy, r, c, _nbw(w), fo)


def nb_ok_badge(cx=36, cy=36, r=8.5):
    return nb_octagon(cx, cy, r, NB_S, 1.4, 0.22) + nb_check(cx, cy, r * 1.05, NB_S, 1.8)


def nb_bad_badge(cx=36, cy=36, r=8.5):
    return nb_octagon(cx, cy, r, NB_A, 1.4, 0.22) + nb_xmark(cx, cy, r * 1.0, NB_A, 1.8)


def nb_plus_badge(cx=37, cy=37, r=8.0, c=NB_S):
    return nplus(cx, cy, c, r * 0.85)


def nb_warn_badge(cx=36, cy=36, s=11.0):
    h = s * 0.87
    tri = [(cx, cy - h * 0.62), (cx + s * 0.58, cy + h * 0.38), (cx - s * 0.58, cy + h * 0.38)]
    return (nb_poly(tri, NB_A, 1.4, 0.22) + nseg(cx, cy - h * 0.22, cx, cy + h * 0.06, NB_A, NW, cap="butt")
            + ndot(cx, cy + h * 0.22, NB_A, 1.1))


def nb_hatch(x, y, w, c=NB_T, n=5.0):
    """A fixed ground: a line with short diagonal ticks under it."""
    d = ""
    k = x + 2
    while k < x + w - 1:
        d += "M%.2f %.2f L%.2f %.2f " % (k, y + 4.5, k + 3.5, y + 1)
        k += n
    return nseg(x, y, x + w, y, c, NW, cap="butt") + nl(d, c, NI, glow=0.14, cap="butt")


def nb_segments(x, y, w, h, n, colours):
    """A segmented bar (stress scale, progress): n cells with gaps."""
    gap = 1.6
    cw = (w - gap * (n - 1)) / n
    out = ""
    for i in range(n):
        c = colours[i % len(colours)]
        out += rect(x + i * (cw + gap), y, cw, h, c, 0, 'fill-opacity="%.2f"' % (0.35 + 0.55 * i / max(1, n - 1)))
    return out


def nb_sheet(d, c=NB_P, w=4.6):
    """A sheet seen edge-on: its two faces as a hollow double line over a tight glow."""
    _path_bounds(d, w / 2 + 1.3)
    return (
        path(d, c, neon_icon_style.glow_width(w), "none", 'stroke-opacity="0.22"')
        + path(d, c, w)
        + path(d, NB_G, w - 2.4)
        + path(d, c, w - 2.4, "none", 'stroke-opacity="0.22"')
    )
