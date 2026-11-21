# SPDX-License-Identifier: LGPL-2.1-or-later
"""Hand-made Neon Lights icons for the most-seen core icons (plan task B4): the visible rows of
the SOLID, SURFACE, MESH, SHEET METAL, PLASTIC and UTILITIES ribbons (the icons drawn in
make_icons.py; the sheet metal and plastic tools' own icons live in their area files), the
navigation bar, the browser and the timeline.

Run by make_icons.py in its own namespace (like every tools/fission180/icons_*.py file), so the
helpers there (iso, _grow, _path_bounds, neon_icon, math) and the kit are at hand. Each @neon_icon recipe
returns the SVG body in the neon language directly (no automatic conversion): original line art
on the 48 x 48 canvas, angular (cut corners, brackets, straight segments), two-tone (primary for
the object, secondary for what the tool does, alert only for warnings and deleting), every line
with a wider faint copy under it (the glow; Qt draws SVG Tiny, which has no blur). Colours are
the role tokens that fission180/neon_icons.py replaces with the preset's colours at run time.

The drawing kit (nl, npoly, ncut, nbox, ndot, nhead, ntransport...) and the set's one stroke
and glow standard are in icons_neon__kit.py, shared with the area files' recipes.
"""

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
        + ndot(24, 24, NS, 2.0)
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
    # a hollowed block: the outer silhouette, the thin rim of the opening, its dark inside
    q = lambda a, b, h: iso(a, b, h, 24, 36, 1.0)  # noqa: E731
    rim = [q(4, 4, 16), q(18, 4, 16), q(18, 18, 16), q(4, 18, 16)]
    return (
        nbox(0, 0, 0, 22, 22, 16, NP, 24, 36, inner=False, fo=0.12)
        + nl(_d(rim, True), NS, NW, NG, 0.85, glow=0.3)
        + nseg(rim[0][0], rim[0][1], rim[0][0], rim[0][1] + 8, NS, NI, cap="butt", glow=0.14)
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
    # a part inside the HUD frame of a new component
    return (
        nbrackets(4, 8, 32, 34, NP, 6, NI + 0.3)
        + nbox(0, 0, 0, 13, 13, 11, NP, 20, 28, fo=0.16)
        + nplus(37, 11, NS, 6.5)
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
        + noct(31, 16, 3.2, NS, NI, 0.6)
    )


@neon_icon("insert_mesh")
def _():
    # a coarse mesh patch coming in from outside (the insert arrow of insert_component)
    return (
        nl("M6 40 L16 22 L30 26 L22 42 Z M16 22 L22 42 M30 26 L38 40 L22 42", NP, NW, NP, 0.1)
        + ndot(16, 22, NP, 1.8)
        + ndot(30, 26, NP, 1.8)
        + nl("M44 4 V14 M44 4 H34", NS, NW, cap="butt")
        + narrow(44, 4, 30, 18, NS, NW, 5)
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
    return nmesh(24, 24, 18, NP, {0: NS, 1: NS, 3: NT, 4: NT})


@neon_icon("mesh_repair")
def _():
    return nmesh(20, 26, 15, NP, {1: NS}) + nl(
        "M31 12 L37 18 L44 7", NS, NW + 0.3, cap="square", glow=0.32
    )


@neon_icon("mesh_remesh")
def _():
    # an even grid of triangles (a square split in four, each split once) and a cycle arrow
    return (
        npoly([(5, 17), (31, 17), (31, 43), (5, 43)], NP, NW, fo=0.1)
        + nl("M18 17 V43 M5 30 H31 M5 17 L31 43", NP, NI, glow=0.14, cap="butt")
        + nl("M24 5 H42 V22", NS, NW, cap="butt")
        + nhead(42, 27, math.pi / 2, NS, NW, 5)
        + nhead(19, 5, math.pi, NS, NW, 5)
    )


@neon_icon("mesh_reduce")
def _():
    # one big triangle split in four: fewer, larger faces; a minus and a down arrow
    return (
        npoly([(4, 42), (34, 42), (19, 12)], NP, NW, fo=0.1)
        + npoly([(11.5, 27), (26.5, 27), (19, 42)], NP, NI, glow=0.14)
        + nseg(32, 8, 44, 8, NS, NW + 0.3, cap="butt")
        + narrow(40, 15, 40, 32, NS, NW, 5)
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


# ---- automatic icons that read badly: drawn by hand ---------------------------------------
@neon_icon("material")
def _():
    # a material ball on a two-tone floor tile
    return (
        nf("M8 38 L24 30 L40 38 L24 46 Z", NP, 0.06)
        + nl("M8 38 L24 30 L40 38 L24 46 Z", NP, NI, glow=0.14)
        + nl("M16 34 L32 42", NP, NI, glow=0, cap="butt")
        + ncircle(24, 20, 13, NP, NW, 0.1)
        + nl("M13 16 Q24 25 35 16", NS, NI, glow=0.2, cap="butt")
        + nl("M15 11 Q18 7 23 6.5", NS, NW, cap="butt", glow=0.34)
    )


@neon_icon("emboss")
def _():
    # a raised letter on a plate
    return (
        nbox(0, 0, 0, 24, 24, 4, NP, 24, 22, inner=False, fo=0.1)
        + nl("M15 32 L24 8 L33 32 M18.5 23 H29.5", NS, NW + 0.2, cap="butt", glow=0.34)
    )


@neon_icon("mesh_shell")
def _():
    # a mesh hollowed to a wall: outer and inner hexagons, tied by three short struts
    outer = [(24 + 19 * math.cos(math.radians(a)), 24 + 19 * math.sin(math.radians(a)))
             for a in (-90, -30, 30, 90, 150, 210)]
    inner = [(24 + 10 * math.cos(math.radians(a)), 24 + 10 * math.sin(math.radians(a)))
             for a in (-90, -30, 30, 90, 150, 210)]
    struts = " ".join(_d([outer[k], inner[k]]) for k in range(6))
    return (
        npoly(outer, NP, NW, fo=0.14)
        + nl(_d(inner, True), NS, NW, NG, 0.9, glow=0.3)
        + nl(struts, NP, NI, glow=0.14, cap="butt")
    )


def _file(mark):
    """An inserted file: a page with a folded corner and a picture of what it holds."""
    return npage(6, 4, 30, 38, NP, 7, 0) + mark


@neon_icon("insert_dxf")
def _():
    # a 2D drawing: a profile with a hole and a dimension line
    return _file(
        nl("M11 34 V20 L19 14 H31 V34 Z", NS, NI + 0.3, glow=0.24)
        + ncircle(22, 25, 3.6, NS, NI)
        + nl("M11 39 H31", NT, NI, glow=0.14, cap="butt")
        + nl("M11 37 V41 M31 37 V41", NT, NI, glow=0, cap="butt")
    )


@neon_icon("insert_svg")
def _():
    # a vector curve with its two handles
    return _file(
        nl("M11 34 C13 16 27 32 31 14", NS, NW, cap="butt", glow=0.3)
        + nl("M11 34 L11 22 M31 14 L31 26", NT, NI, glow=0, cap="butt")
        + ndot(11, 21, NT, 1.9)
        + ndot(31, 27, NT, 1.9)
    )


@neon_icon("insert_step")
def _():
    # a 3D part in front of its file
    return (
        npage(4, 3, 26, 32, NP, 6, 2)
        + nbox(0, 0, 0, 14, 14, 11, NS, 32, 30, fo=0.18)
    )


@neon_icon("sphere")
def _():
    # a wire sphere: the outline, its equator, one meridian, a highlight
    return (
        ncircle(24, 24, 18, NS, NW, 0.1)
        + nl("M6 24 Q24 33 42 24", NS, NI, glow=0.16, cap="butt")
        + nl("M24 6 Q15 24 24 42", NS, NI, glow=0.16, cap="butt")
        + nl("M12 15 Q15 10 21 8.5", NT, NW, cap="butt", glow=0.3)
    )


def _views(frames):
    """Viewport layouts: each view an outlined frame with cut corners (they were solid grey
    tiles that merged at 18 px)."""
    return "".join(ncut(x, y, w, h, NT, 3, NW, fo=0.1) for x, y, w, h in frames)


@neon_icon("view_single")
def _():
    return _views([(5, 9, 38, 30)])


@neon_icon("view_two_h")
def _():
    return _views([(5, 9, 17, 30), (26, 9, 17, 30)])


@neon_icon("view_two_v")
def _():
    return _views([(5, 7, 38, 15), (5, 26, 38, 15)])


@neon_icon("nav_viewports")
def _():
    return "".join(
        ncut(x, y, 15, 15, NT, 3, NW, fo=0.06, glow=0.16) for x, y in ((5, 5), (28, 5), (5, 28), (28, 28))
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
        + ndot(24, 24, NS, 2.4)
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
    # an angular open hand: one outline, the fingers told apart by two short notches
    hand = [(15, 43), (8, 29), (12, 27), (16, 31), (16, 9), (21, 9), (21, 7), (27, 7),
            (27, 10), (33, 10), (33, 36), (29, 43)]
    return (
        npoly(hand, NT, NW, fo=0.0)
        + nf(_d(hand, True), NP, 0.12)
        + nl("M21 9 V22 M27 10 V22", NT, NI, glow=0.14, cap="butt")
    )


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
    # a floor grid in perspective: the outline and one line each way (three by three cells
    # filled into a solid diamond at 18 px)
    return npoly([(4, 26), (24, 14), (44, 26), (24, 38)], NT, NW, fo=0.0) + nl(
        "M14 20 L34 32 M14 32 L34 20", NP, NI, glow=0.18, cap="butt"
    )


# ---- BROWSER ------------------------------------------------------------------------------
def _eye(c_line, c_iris):
    lid = "M4 24 L14 15 L34 15 L44 24 L34 33 L14 33 Z"
    return nl(lid, c_line, NW, NP, 0.08) + noct(24, 24, 5.6, c_iris, NW, 0.35) + ndot(24, 24, c_iris, 1.6)


@neon_icon("eye")
def _():
    return _eye(NT, NS)


@neon_icon("eye_off")
def _():
    # the eye's outline dashed (hidden), struck through
    return nl(
        "M4 24 L14 15 L34 15 L44 24 L34 33 L14 33 Z",
        NT,
        NW,
        dash="4.5 2.6",
        cap="butt",
    ) + nseg(9, 41, 39, 7, NT, NW + 0.4)


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
    return nl("M24 6 V17 M24 31 V42 M6 24 H17 M31 24 H42", NP, NI + 0.3, cap="butt") + ndot(24, 24, NS, 3.4)


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
        + nseg(6, 40, 42, 40, NT, NW, cap="butt")
        + nl(hatch, NT, NI, cap="butt", glow=0.16)
    )


@neon_icon("delete")
def _():
    return nl("M10 10 L38 38 M38 10 L10 38", NA, NW + 1.2, cap="square", glow=0.3)


@neon_icon("panel_close")
def _():
    return nl("M14 14 L34 34 M34 14 L14 34", NT, NW + 0.5, cap="square")


# ---- TIMELINE (the same buttons as the animation timeline: ntransport) --------------------
@neon_icon("tl_play")
def _():
    return ntransport("play")


@neon_icon("tl_prev")
def _():
    return ntransport("back")


@neon_icon("tl_next")
def _():
    return ntransport("step")


@neon_icon("tl_end")
def _():
    return ntransport("end")


@neon_icon("tl_start")
def _():
    return ntransport("start")
