# SPDX-License-Identifier: LGPL-2.1-or-later
"""Hand-made Neon Lights icons for the most-seen core icons (plan task B4): the visible rows of
the SOLID, SURFACE, MESH, SHEET METAL, PLASTIC and UTILITIES ribbons (the icons drawn in
make_icons.py; the sheet metal and plastic tools' own icons live in their area files), the
navigation bar, the browser and the timeline.

Run by make_icons.py in its own namespace (like every tools/fission180/icons_*.py file), so the
helpers there (iso, _grow, _path_bounds, neon_icon, math) are at hand. Each @neon_icon recipe
returns the SVG body in the neon language directly (no automatic conversion): original line art
on the 48 x 48 canvas, angular (cut corners, brackets, straight segments), two-tone (primary for
the object, secondary for what the tool does, alert only for warnings and deleting), every line
with a wider faint copy under it (the glow; Qt draws SVG Tiny, which has no blur). Colours are
the role tokens that fission180/neon_icons.py replaces with the preset's colours at run time.

Line weights were chosen on contact sheets at 36 px and 18 px (tools/fission180/
neon_icon_sheet.py): 2.1 for outlines (about 1 px at 18 px), 1.4 for inner detail, glow 2x + 0.9
at 0.24 opacity so neighbouring lines never merge into one blob.
"""

NP, NS, NA, NT, NG = "#n30001", "#n30002", "#n30003", "#n30004", "#n30006"
NW, NI = 2.1, 1.4  # outline and inner-detail widths


def _d(points, close=False):
    """A path through points (absolute moves and lines)."""
    out = "M%.2f %.2f" % points[0]
    for x, y in points[1:]:
        out += " L%.2f %.2f" % (x, y)
    return out + (" Z" if close else "")


def nl(d, c=NP, w=NW, fill="none", fo=0.0, glow=0.24, dash=None, join="miter", cap="square"):
    """One neon line (a path): its glow, then the line. `fill` + `fo` give a faint face."""
    _path_bounds(d, w / 2)
    extra = ' stroke-dasharray="%s"' % dash if dash else ""
    glow_colour = NP if c == NT else c
    out = ""
    if glow:
        out += (
            '<path d="%s" fill="none" stroke="%s" stroke-width="%.2f" stroke-opacity="%.2f" '
            'stroke-linejoin="%s" stroke-linecap="%s"/>'
            % (d, glow_colour, w * 2.0 + 0.9, glow, join, cap)
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


def ndiamond(x, y, c=NS, r=2.4):
    _grow(x, y, r)
    return '<polygon points="%s" fill="%s"/>' % (
        P([(x, y - r), (x + r, y), (x, y + r), (x - r, y)]),
        c,
    )


def ncut(x, y, w, h, c=NP, cut=None, lw=NW, fo=0.0, corners="tr bl", **kw):
    """A rectangle with cut corners (the HUD frame)."""
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


def narrow(x1, y1, x2, y2, c=NS, w=NW, head=5.0, **kw):
    """A line with an open chevron head (line art, not a solid triangle)."""
    a = math.atan2(y2 - y1, x2 - x1)
    h1 = (x2 - head * math.cos(a - 0.6), y2 - head * math.sin(a - 0.6))
    h2 = (x2 - head * math.cos(a + 0.6), y2 - head * math.sin(a + 0.6))
    return nl(_d([(x1, y1), (x2, y2)]) + " " + _d([h1, (x2, y2), h2]), c, w, **kw)


def nhead(x, y, ang, c=NS, w=NW, head=5.0):
    """Only a chevron head at (x, y) pointing along ang (radians)."""
    h1 = (x - head * math.cos(ang - 0.6), y - head * math.sin(ang - 0.6))
    h2 = (x - head * math.cos(ang + 0.6), y - head * math.sin(ang + 0.6))
    return nl(_d([h1, (x, y), h2]), c, w)


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
    spokes = " ".join(_d([(cx, cy), p]) for p in pts)
    mids = _d([pts[0], pts[2], pts[4]], True)
    return out + nl(spokes + " " + mids, c, NI * 0.85, glow=0.14)


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


# ---- SOLID > CREATE -----------------------------------------------------------------------
@neon_icon("sketch_create")
def _():
    return (
        nbrackets(6, 8, 30, 30, NP, 6)
        + nl("M12 32 L20 18 Q26 10 31 16", NT, NW, join="round", cap="round")
        + ndot(12, 32)
        + ndot(20, 18)
        + ndot(31, 16)
        + nplus(36, 36)
    )


@neon_icon("extrude")
def _():
    return nbox(0, 0, 0, 16, 16, 12, NP, 22, 38, top=NS) + narrow(22, 21, 22, 6, NS, head=5)


@neon_icon("revolve")
def _():
    return (
        nseg(18, 4, 18, 44, NP, NI, dash="3 2.5", cap="butt")
        + npoly([(22, 9), (32, 9), (37, 14), (37, 32), (22, 32)], NP, NW, fo=0.18)
        + nl("M32 39 Q32 45 18 45 Q4 45 4 39 Q4 35 11 34", NS, NW, cap="butt", join="round")
        + nhead(12, 33.8, -0.1, NS, NW, 4.4)
    )


@neon_icon("hole")
def _():
    return (
        nbox(0, 0, 0, 20, 20, 12, NP, 24, 38, inner=False)
        + nl("M18 24 L24 21 L30 24 L24 27 Z", NS, NW, NS, 0.35)
        + nseg(24, 27, 24, 40, NS, NI, dash="2.5 2", cap="butt")
        + nseg(18, 24, 18, 34, NS, NI, dash="2.5 2", cap="butt")
        + nseg(30, 24, 30, 34, NS, NI, dash="2.5 2", cap="butt")
    )


@neon_icon("pattern_rect")
def _():
    return (
        ncut(7, 7, 14, 14, NP, 4, fo=0.2)
        + ncut(27, 7, 14, 14, NS, 4)
        + ncut(7, 27, 14, 14, NS, 4)
        + ncut(27, 27, 14, 14, NS, 4)
        + ndot(24, 24, NS, 1.4)
    )


@neon_icon("mirror")
def _():
    return (
        nseg(24, 5, 24, 43, NS, NI, dash="3.5 2.5", cap="butt")
        + npoly([(20, 10), (20, 38), (6, 38)], NP, NW, fo=0.2)
        + npoly([(28, 10), (28, 38), (42, 38)], NS, NW, glow=0.3)
        + ndiamond(24, 24, NS, 2.2)
    )


# ---- SOLID > MODIFY -----------------------------------------------------------------------
@neon_icon("press_pull")
def _():
    return (
        nbox(0, 0, 0, 18, 18, 10, NP, 20, 42, top=NS)
        + narrow(36, 25, 36, 6, NS, head=4.5)
        + nhead(36, 26, math.pi / 2, NS, NW, 4.5)
    )


@neon_icon("fillet")
def _():
    return (
        nl("M8 40 L8 22 Q8 8 22 8 L40 8", NP, NW, NP, 0.0, join="round")
        + nl("M8 40 L40 40 L40 8", NP, NI, glow=0.14, dash="3 2.5", cap="butt")
        + nl("M8 24 Q8 8 24 8", NS, NW + 0.6, cap="butt", glow=0.34)
        + ndot(8, 24, NS, 1.8)
        + ndot(24, 8, NS, 1.8)
        + nseg(15, 15, 22, 22, NT, NI, cap="butt")
    )


@neon_icon("chamfer")
def _():
    return (
        npoly([(8, 40), (8, 22), (22, 8), (40, 8)], NP, NW, close=False)
        + nl("M8 40 L40 40 L40 8", NP, NI, glow=0.14, dash="3 2.5", cap="butt")
        + nseg(8, 22, 22, 8, NS, NW + 0.6, cap="butt", glow=0.34)
        + ndot(8, 22, NS, 1.8)
        + ndot(22, 8, NS, 1.8)
    )


@neon_icon("shell")
def _():
    q = lambda a, b, h: iso(a, b, h, 24, 38, 1.0)  # noqa: E731
    rim = [q(3, 3, 16), q(17, 3, 16), q(17, 17, 16), q(3, 17, 16)]
    floor = [q(3, 3, 5), q(17, 3, 5), q(17, 17, 5), q(3, 17, 5)]
    return (
        nbox(0, 0, 0, 20, 20, 16, NP, 24, 38, inner=True)
        + nl(_d(rim, True), NS, NI + 0.3, NG, 0.8)
        + nl(_d([rim[0], floor[0], floor[1]]) + " " + _d([floor[0], floor[3]]), NS, NI, glow=0.18)
    )


@neon_icon("combine")
def _():
    return nbox(0, 0, 0, 13, 13, 13, NP, 18, 40) + nbox(0, 0, 0, 13, 13, 13, NS, 30, 30, fo=0.1)


@neon_icon("split_body")
def _():
    return nbox(0, 0, 0, 18, 18, 14, NP, 24, 40) + npoly(
        [(13, 8), (37, 20), (37, 44), (13, 32)], NS, NW, fo=0.18, glow=0.3
    )


@neon_icon("scale")
def _():
    return (
        nbrackets(6, 6, 36, 36, NP, 7)
        + ncut(8, 26, 14, 14, NS, 3.5, fo=0.2)
        + narrow(24, 24, 38, 10, NS, head=5)
    )


@neon_icon("move")
def _():
    out = ncut(19, 19, 10, 10, NP, 3, fo=0.25)
    for x1, y1, x2, y2 in ((24, 17, 24, 5), (24, 31, 24, 43), (17, 24, 5, 24), (31, 24, 43, 24)):
        out += narrow(x1, y1, x2, y2, NS, NW, head=4.5)
    return out


@neon_icon("draft")
def _():
    return (
        npoly([(14, 8), (34, 8), (40, 40), (8, 40)], NP, NW, fo=0.14)
        + nseg(34, 8, 34, 40, NS, NI, dash="3 2.2", cap="butt")
        + nl("M34 30 Q37 30 38.4 32.6", NS, NI + 0.3, cap="butt")
        + nseg(34, 8, 40, 40, NS, NW + 0.4, glow=0.34)
    )


# ---- ASSEMBLE / CONSTRUCT / INSPECT / INSERT / SELECT ------------------------------------
@neon_icon("new_component")
def _():
    return (
        nbox(0, 0, 0, 10, 10, 9, NP, 16, 42, fo=0.1)
        + nbox(0, 0, 0, 10, 10, 9, NP, 32, 42, fo=0.1)
        + nbox(0, 0, 0, 10, 10, 9, NP, 24, 28, fo=0.1)
        + nplus(38, 12, NS, 6)
    )


@neon_icon("offset_plane")
def _():
    return (
        npoly([(6, 32), (24, 23), (42, 32), (24, 41)], NP, NW, fo=0.16)
        + npoly([(6, 17), (24, 8), (42, 17), (24, 26)], NS, NW, fo=0.12, glow=0.3)
        + narrow(24, 32, 24, 19, NS, NI + 0.3, head=3.6)
    )


@neon_icon("measure")
def _():
    out = ncut(5, 26, 38, 12, NP, 3.5, fo=0.14)
    for i, x in enumerate(range(10, 41, 5)):
        out += nseg(x, 26, x, 30 if i % 2 else 32, NP, NI, cap="butt", glow=0)
    return (
        out
        + nseg(5, 9, 5, 20, NS, NI, cap="butt")
        + nseg(43, 9, 43, 20, NS, NI, cap="butt")
        + narrow(22, 14.5, 7, 14.5, NS, NI + 0.4, head=3.6)
        + narrow(26, 14.5, 41, 14.5, NS, NI + 0.4, head=3.6)
    )


@neon_icon("section")
def _():
    q = lambda a, b, h: iso(a, b, h, 24, 40, 1.0)  # noqa: E731
    cut = [q(10, 0, 0), q(10, 0, 16), q(10, 20, 16), q(10, 20, 0)]
    hatch = ""
    for t in (0.2, 0.45, 0.7, 0.95):
        a = (cut[0][0] + (cut[3][0] - cut[0][0]) * t, cut[0][1] + (cut[3][1] - cut[0][1]) * t)
        hatch += _d([a, (a[0] + 4.5, a[1] - 9.5)]) + " "
    return (
        nbox(0, 0, 0, 10, 20, 16, NP, 24, 40)
        + nl(_d(cut, True), NS, NW, NS, 0.22, glow=0.32)
        + nl(hatch, NS, 1.0, glow=0, cap="butt")
    )


@neon_icon("insert_component")
def _():
    return (
        nbox(0, 0, 0, 15, 15, 13, NP, 30, 32)
        + nl("M5 40 L5 30 L13 22 L20 22", NS, NW, cap="butt")
        + nhead(21, 22, 0.0, NS, NW, 4.6)
    )


@neon_icon("canvas")
def _():
    return (
        ncut(6, 9, 36, 30, NP, 5, fo=0.1)
        + npoly([(9, 35), (18, 23), (25, 30), (31, 24), (39, 33)], NS, NW, close=False)
        + ndiamond(31, 16, NA, 3)
    )


@neon_icon("insert_mesh")
def _():
    return (
        nmesh(21, 27, 14, NP, {0: NS, 3: NS})
        + nl("M34 6 L42 6 L42 14", NS, NW, cap="butt")
        + nseg(42, 6, 33, 15, NS, NW)
    )


@neon_icon("select")
def _():
    arrow_pts = [(16, 9), (16, 37), (22, 31), (26, 40), (30, 38), (26, 29), (34, 29)]
    return (
        nbrackets(6, 5, 36, 38, NS, 6, NI + 0.2)
        + npoly(arrow_pts, NT, NW, fo=0.0)
        + nf(_d(arrow_pts, True), NP, 0.3)
    )


# ---- SURFACE ------------------------------------------------------------------------------
@neon_icon("surface_extrude")
def _():
    base = "M6 38 Q16 30 24 36 Q32 42 42 34"
    top = "M6 22 Q16 14 24 20 Q32 26 42 18"
    return (
        nf(base + " L42 18 Q32 26 24 20 Q16 14 6 22 Z", NS, 0.14)
        + nl(base, NP, NW, cap="butt", join="round")
        + nl(top, NS, NW, cap="butt", join="round")
        + nseg(6, 38, 6, 22, NS, NI, cap="butt")
        + nseg(42, 34, 42, 18, NS, NI, cap="butt")
        + narrow(24, 18, 24, 5, NS, NI + 0.4, head=4)
    )


@neon_icon("surface_loft")
def _():
    lower = "M6 38 Q24 30 42 38"
    upper = "M12 12 Q24 18 36 12"
    return (
        nf("M6 38 Q24 30 42 38 L36 12 Q24 18 12 12 Z", NS, 0.14)
        + nl(lower, NP, NW, cap="butt")
        + nl(upper, NP, NW, cap="butt")
        + nl("M6 38 L12 12 M42 38 L36 12 M24 34 L24 15", NS, NI, cap="butt")
    )


@neon_icon("patch")
def _():
    loop = "M8 24 L14 10 L32 7 L42 20 L36 38 L16 41 Z"
    return (
        nl(loop, NP, NW, NS, 0.16)
        + nl("M14 10 L16 41 M32 7 L36 38 M8 24 L42 20", NS, 1.0, glow=0.12, cap="butt")
        + ndot(14, 10, NP, 1.8)
        + ndot(42, 20, NP, 1.8)
        + ndot(16, 41, NP, 1.8)
    )


@neon_icon("thicken")
def _():
    top, low = "M6 20 Q24 6 42 20", "M6 32 Q24 18 42 32"
    return (
        nf(top + " L42 32 Q24 18 6 32 Z", NS, 0.2)
        + nl(top, NP, NW, cap="butt")
        + nl(low + " M6 20 L6 32 M42 20 L42 32", NS, NW, cap="butt")
        + narrow(24, 15, 24, 23.5, NS, NI + 0.2, head=3)
    )


@neon_icon("trim")
def _():
    return (
        nl("M18 24 Q26 15 42 13", NP, NW, cap="butt")
        + nl("M10 6 L26 40", NS, NW, cap="butt")
        + nl("M18 24 Q12 30 5 34", NA, NW, cap="butt", dash="2.6 2.2", glow=0.3)
    )


@neon_icon("surface_extend")
def _():
    return (
        nl("M6 32 L18 16 L30 16 L30 40 L6 40 Z", NP, NW, NP, 0.14)
        + nl("M30 16 L40 16 L40 40 L30 40", NS, NW, dash="3 2.2", cap="butt")
        + narrow(32, 28, 44, 28, NS, NW, head=4.5)
    )


@neon_icon("stitch")
def _():
    return (
        npoly([(5, 12), (22, 12), (22, 38), (5, 38)], NP, NW, fo=0.14)
        + npoly([(26, 12), (43, 12), (43, 38), (26, 38)], NP, NW, fo=0.14)
        + nl("M20 15 L28 19 L20 23 L28 27 L20 31 L28 35", NS, NI + 0.4, cap="butt", glow=0.32)
    )


# ---- MESH ---------------------------------------------------------------------------------
@neon_icon("mesh_tessellate")
def _():
    return (
        nbox(0, 0, 0, 13, 13, 12, NP, 13, 34, fo=0.1)
        + narrow(21, 22, 28, 22, NS, NI + 0.4, head=3.4)
        + nmesh(36, 22, 9, NS)
    )


@neon_icon("mesh_face_groups")
def _():
    return nmesh(24, 24, 18, NP, {0: NS, 1: NS, 3: NA, 4: NA})


@neon_icon("mesh_repair")
def _():
    return nmesh(20, 26, 15, NP, {1: NS}) + nl(
        "M31 12 L37 18 L44 7", NS, NW + 0.3, cap="square", glow=0.32
    )


@neon_icon("mesh_remesh")
def _():
    return (
        nmesh(20, 26, 14, NP)
        + nl("M30 10 Q42 8 42 22", NS, NW, cap="butt")
        + nhead(42, 22, math.pi / 2, NS, NW, 4)
        + nl("M42 34 Q40 43 30 42", NS, NW, cap="butt", dash="3 2")
    )


@neon_icon("mesh_reduce")
def _():
    return (
        nmesh(20, 24, 15, NP)
        + nseg(36, 28, 44, 28, NS, NW + 0.3, cap="butt")
        + narrow(40, 8, 40, 22, NS, NW, head=4)
    )


@neon_icon("mesh_plane_cut")
def _():
    return nmesh(22, 26, 16, NP) + npoly(
        [(4, 22), (36, 10), (44, 18), (12, 30)], NS, NW, fo=0.2, glow=0.3
    )


@neon_icon("convert_mesh")
def _():
    return (
        nmesh(12, 24, 9, NP)
        + narrow(22, 24, 28, 24, NS, NI + 0.4, head=3.4)
        + nbox(0, 0, 0, 11, 11, 10, NS, 37, 30, fo=0.16)
    )


# ---- UTILITIES ----------------------------------------------------------------------------
@neon_icon("print_3d")
def _():
    return (
        ncut(5, 5, 38, 38, NP, 6, fo=0.06)
        + nseg(5, 13, 43, 13, NP, NI, glow=0.12, cap="butt")
        + npoly([(19, 13), (29, 13), (29, 18), (24, 23), (19, 18)], NT, NI + 0.3)
        + nl("M14 36 H34 M15 32 H33 M17 28 H31", NS, NI + 0.2, cap="butt", glow=0.3)
    )


@neon_icon("export")
def _():
    return (
        nl("M24 12 L8 12 L8 40 L36 40 L36 30", NP, NW, NP, 0.0, cap="butt")
        + nbox(0, 0, 0, 9, 9, 8, NP, 17, 33, fo=0.1, w=NI + 0.3)
        + narrow(25, 23, 42, 6, NS, NW, head=5)
    )


@neon_icon("parameters")
def _():
    return (
        ncut(5, 8, 38, 32, NP, 6, fo=0.08)
        + nl("M22 14 Q17 13 17 19 L16 34 Q15 38 11 37 M12 22 H21", NT, NW, cap="butt", join="round")
        + nl("M25 22 L35 34 M35 22 L25 34", NS, NW, cap="butt")
    )


@neon_icon("ai_panel")
def _():
    spark = "M35 11 L37 18 L43 20 L37 22 L35 29 L33 22 L27 20 L33 18 Z"
    return (
        ncut(5, 7, 38, 34, NP, 6)
        + nseg(25, 7, 25, 41, NP, NI, glow=0.12, cap="butt")
        + nl("M10 16 H20 M10 23 H18 M10 30 H20", NT, NI + 0.3, cap="butt", glow=0.2)
        + nl(spark, NS, NI, NS, 0.55, glow=0.34)
    )


@neon_icon("freecad_tools")
def _():
    return ncog(20, 26, 15, 8, NP) + nl(
        "M27 21 L41 7 M37 5 L43 11", NS, NW + 0.4, cap="butt", glow=0.32
    )


@neon_icon("tl_settings")
def _():
    return ncog(24, 24, 18, 8, NT, NW, NS)


# ---- NAVIGATION BAR -----------------------------------------------------------------------
@neon_icon("nav_orbit")
def _():
    return (
        nl("M10 30 Q4 22 16 17 Q24 14 34 16", NT, NW, cap="butt", join="round")
        + nhead(35, 16.2, 0.1, NT, NW, 4.6)
        + nl("M38 20 Q44 27 32 31 Q22 34 13 33", NT, NW, cap="butt", dash="3 2.4")
        + nseg(24, 6, 24, 42, NP, NI, dash="2.5 2.5", cap="butt", glow=0.14)
        + ndiamond(24, 24, NS, 3)
    )


@neon_icon("nav_lookat")
def _():
    return (
        npoly([(18, 8), (40, 14), (40, 40), (18, 34)], NP, NW, fo=0.14)
        + narrow(4, 24, 25, 24, NS, NW, head=5)
        + ndot(29, 24, NS, 1.8)
    )


@neon_icon("nav_pan")
def _():
    hand = [
        (14, 42),
        (9, 28),
        (12, 26),
        (16, 31),
        (16, 10),
        (20, 10),
        (20, 24),
        (20, 6),
        (24, 6),
        (24, 24),
        (24, 8),
        (28, 8),
        (28, 25),
        (28, 12),
        (32, 12),
        (32, 34),
        (28, 42),
    ]
    return npoly(hand, NT, NW, fo=0.0, close=True) + nf(_d(hand, True), NP, 0.14)


@neon_icon("nav_zoom")
def _():
    lens = [
        (
            20 + 12 * math.cos(math.radians(22.5 + 45 * i)),
            20 + 12 * math.sin(math.radians(22.5 + 45 * i)),
        )
        for i in range(8)
    ]
    return (
        npoly(lens, NT, NW, fo=0.0)
        + nf(_d(lens, True), NP, 0.12)
        + nseg(29, 29, 41, 41, NT, NW + 1.2)
        + nl("M15 20 H25 M20 15 V25", NS, NW, cap="butt")
    )


@neon_icon("nav_zoom_window")
def _():
    lens = [
        (
            31 + 7 * math.cos(math.radians(22.5 + 45 * i)),
            31 + 7 * math.sin(math.radians(22.5 + 45 * i)),
        )
        for i in range(8)
    ]
    return (
        npoly(
            [(5, 26), (5, 5), (32, 5), (32, 18)],
            NS,
            NI + 0.3,
            close=False,
            dash="3 2.2",
            cap="butt",
        )
        + nseg(5, 26, 18, 26, NS, NI + 0.3, dash="3 2.2", cap="butt")
        + npoly(lens, NT, NW, fo=0.0)
        + nf(_d(lens, True), NP, 0.12)
        + nseg(36.5, 36.5, 43, 43, NT, NW + 0.8)
    )


@neon_icon("nav_fit")
def _():
    return nbrackets(5, 5, 38, 38, NT, 8) + nbox(
        0, 0, 0, 12, 12, 10, NS, 24, 30, fo=0.14, w=NI + 0.4
    )


@neon_icon("nav_display")
def _():
    return (
        ncut(5, 7, 38, 26, NT, 5)
        + nl("M17 41 H31 M24 33 V41", NT, NW, cap="butt")
        + nbox(0, 0, 0, 9, 9, 7, NS, 24, 25, fo=0.18, w=NI + 0.3)
    )


@neon_icon("nav_grid")
def _():
    return npoly([(4, 26), (24, 14), (44, 26), (24, 38)], NT, NW, fo=0.0) + nl(
        "M9 23 L29 35 M14 20 L34 32 M19 17 L39 29 M9 29 L29 17 M14 32 L34 20 M19 35 L39 23",
        NP,
        1.25,
        glow=0.12,
        cap="butt",
    )


# ---- BROWSER ------------------------------------------------------------------------------
def _eye(c_line, c_iris):
    lid = "M4 24 L14 15 L34 15 L44 24 L34 33 L14 33 Z"
    return nl(lid, c_line, NW, NP, 0.08) + ndiamond(24, 24, c_iris, 6) + ndot(24, 24, NG, 1.6)


@neon_icon("eye")
def _():
    return _eye(NT, NS)


@neon_icon("eye_off")
def _():
    return nl(
        "M4 24 L14 15 L34 15 L44 24 L34 33 L14 33 Z",
        NP,
        NI + 0.2,
        dash="3 2.4",
        cap="butt",
        glow=0.1,
    ) + nseg(8, 40, 40, 8, NP, NW)


@neon_icon("folder")
def _():
    return nl("M5 12 L17 12 L21 16 L43 16 L43 38 L39 42 L5 42 Z", NP, NW, NP, 0.14) + nseg(
        5, 21, 43, 21, NP, NI, glow=0.12, cap="butt"
    )


@neon_icon("document")
def _():
    return (
        nl("M10 5 L30 5 L39 14 L39 43 L10 43 Z", NT, NW, NP, 0.08)
        + nl("M30 5 L30 14 L39 14", NT, NI, cap="butt")
        + nl("M16 21 H33 M16 28 H33 M16 35 H27", NS, NI + 0.2, cap="butt", glow=0.24)
    )


@neon_icon("units")
def _():
    out = ncut(5, 17, 38, 14, NT, 4, fo=0.0)
    for i, x in enumerate(range(10, 40, 4)):
        out += nseg(x, 17, x, 22 if i % 2 else 25, NS, NI, cap="butt", glow=0.14)
    return out


@neon_icon("box")
def _():
    return nbox(0, 0, 0, 18, 18, 16, NP, 24, 38, top=None, fo=0.18)


@neon_icon("surface_body")
def _():
    return nsheet(5, 26, 33, 20, 18, NS, 0.2)


@neon_icon("sk_rectangle")
def _():
    return (
        npoly([(9, 12), (39, 12), (39, 36), (9, 36)], NT, NW)
        + ndot(9, 12)
        + ndot(39, 12)
        + ndot(39, 36)
        + ndot(9, 36)
    )


@neon_icon("point")
def _():
    return nl("M24 6 V17 M24 31 V42 M6 24 H17 M31 24 H42", NP, NI + 0.3, cap="butt") + ndiamond(
        24, 24, NS, 4.2
    )


@neon_icon("axis")
def _():
    return (
        nseg(10, 38, 16, 32, NP, NI, cap="butt", dash="3 2")
        + narrow(18, 30, 40, 8, NS, NW, head=5)
        + ndot(18, 30, NP, 2.2)
    )


@neon_icon("ground")
def _():
    hatch = " ".join("M%.1f 44 L%.1f 40" % (x, x + 4) for x in range(8, 40, 6))
    return (
        nbox(0, 0, 0, 16, 16, 12, NP, 24, 34)
        + nseg(6, 40, 42, 40, NA, NW, cap="butt")
        + nl(hatch, NA, 1.2, cap="butt", glow=0.16)
    )


@neon_icon("delete")
def _():
    return nl("M10 10 L38 38 M38 10 L10 38", NA, NW + 1.2, cap="square", glow=0.3)


@neon_icon("panel_close")
def _():
    return nl("M14 14 L34 34 M34 14 L14 34", NT, NW + 0.5, cap="square")


# ---- TIMELINE -----------------------------------------------------------------------------
def _play(x, flip=False, w=NW):
    pts = [(x, 12), (x + 18, 24), (x, 36)]
    if flip:
        pts = [(2 * x + 18 - px, py) for px, py in pts]
    return npoly(pts, NT, w, fo=0.0) + nf(_d(pts, True), NP, 0.2)


@neon_icon("tl_play")
def _():
    return _play(16)


@neon_icon("tl_prev")
def _():
    return _play(14, True)


@neon_icon("tl_next")
def _():
    return _play(10) + nseg(35, 12, 35, 36, NS, NW + 0.6, cap="butt")


@neon_icon("tl_end")
def _():
    return (
        _play(8)
        + nseg(30, 12, 30, 36, NS, NW, cap="butt")
        + nseg(37, 12, 37, 36, NS, NW, cap="butt")
    )


@neon_icon("tl_start")
def _():
    return (
        _play(22, True)
        + nseg(18, 12, 18, 36, NS, NW, cap="butt")
        + nseg(11, 12, 11, 36, NS, NW, cap="butt")
    )
