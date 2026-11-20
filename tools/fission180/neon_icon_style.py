# SPDX-License-Identifier: LGPL-2.1-or-later
"""Draws Fission 180's icon recipes in the Neon Lights language (docs/fission180/
neon-lights-design.md 6.5), used by make_icons.py for fission180/icons/neon/.

The same drawing, re-inked: solid faces become outlines over a faint fill (an isometric block
turns into a glowing wireframe), every line gets a wider, fainter copy under it (the glow; Qt
draws SVG Tiny, which has no blur), and every colour becomes one of the look's roles, written
as a token that fission180/neon_icons.py replaces with the preset's colour at run time:

    #n30001 primary   #n30002 secondary   #n30003 alert   #n30004 text   #n30006 ground

Small solid marks (points, arrow heads, the bars of a plus) stay solid. Pure text processing.
"""

import colorsys
import math
import re

PRIMARY, SECONDARY, ALERT, TEXT, GROUND = "#n30001", "#n30002", "#n30003", "#n30004", "#n30006"
TOKENS = (PRIMARY, SECONDARY, ALERT, TEXT, GROUND)

# ---- the one stroke standard of the whole neon set (hand-made kits and this converter) ----
# Chosen on contact sheets at 36 and 18 px: an icon is framed to about a 38-unit square, so
# LINE (2.1 units) is about 1 px at 18 px; DETAIL is the weight of inner lines. Every line has
# a wider, fainter copy under it (the glow): 2 x width + 0.9, but never more than width + 2.6,
# so a thick stroke gets a tight halo instead of a fat tube.
LINE, DETAIL = 2.1, 1.4
GLOW_SCALE, GLOW_ADD, GLOW_CAP, GLOW_OPACITY = 2.0, 0.9, 2.6, 0.24
# the converter's outlines of a normal icon's solid shapes: a block's silhouette (EDGE) and a
# flat face (FACE). The normal icons' blocks are smaller than the hand-made ones (often three
# to an icon), so they sit between DETAIL and LINE: at LINE, small blocks filled in at 18 px.
EDGE, FACE = 1.75, 1.5


def glow_width(width):
    """Width of the glow copy under a line of `width`."""
    return min(width * GLOW_SCALE + GLOW_ADD, width + GLOW_CAP)


# make_icons.py's palette -> role. Gold, orange and yellow are accents (secondary), never
# warnings: in a preset whose alert is red they read as errors. Red is alert only in icons whose
# red means warn / delete / fail or the hot end of a result scale (ALERT_MEANING below).
KNOWN = {
    "#ececec": PRIMARY,
    "#d2d4d7": PRIMARY,
    "#aeb2b8": PRIMARY,  # GREY: the neutral solid
    "#bfe5ff": SECONDARY,
    "#8fd0ff": SECONDARY,
    "#5aaee8": SECONDARY,  # BLUE: what changes
    "#7cc4f5": SECONDARY,
    "#4da3e0": SECONDARY,
    "#2f7fbf": SECONDARY,  # DBLUE
    "#e2d4ff": SECONDARY,
    "#c4aef5": SECONDARY,
    "#9f86dd": SECONDARY,  # PURPLE
    "#4fb0f5": SECONDARY,  # POINT
    "#3cc46a": SECONDARY,  # GREEN (create)
    "#f2a66a": SECONDARY,  # ORANGE (an accent: an axis, a path, a load)
    "#f6dc8c": SECONDARY,
    "#e8c460": SECONDARY,
    "#c9a23e": SECONDARY,  # GOLD (a tool, a mesh: see GOLD_OBJECT)
    "#ffcc33": ALERT,  # WARN: always a warning
    "#dfe3e8": TEXT,
    "#f5f5f5": TEXT,
    "#ffffff": TEXT,  # STROKE, WHITE
    "#2b313b": GROUND,  # DARK
}
REDS = ("#ef6f6c", "#e5534b", "#e5584b", "#ef8b88", "#f7b3b1")
GOLDS = ("#f6dc8c", "#e8c460", "#c9a23e")
# icons whose red means a warning, deleting, a failure, or the hot end of a result/analysis
# scale; in every other icon red is an accent (a sketch constraint, a load, a normal)
ALERT_MEANING = {
    "delete",
    "cancel",
    "remove",
    "surfmod_delete",
    "mesh_delete_faces",
    "interference",
    "sim_precheck_error",
    "sim_stage_failed",
    "sim_results",
    "sim_static_stress",
    "sim_study",
    "curvature_map",
    "draft_analysis",
    "accessibility",
    "min_radius",
    "pl_design_advice",
}
ALERT_PREFIXES = ("simr_",)
GOLD_OBJECT = ("mesh_",)  # gold is the mesh itself there: the object, so primary like the
# hand-made mesh icons beside them on the MESH tab


def alert_meaning(name):
    return bool(name) and (name in ALERT_MEANING or name.startswith(ALERT_PREFIXES))


_TAG = re.compile(r"<(polygon|polyline|line|path|circle|rect|ellipse)\b([^>]*?)/?>")
_ATTR = re.compile(r'([a-zA-Z][\w:-]*)="([^"]*)"')
SMALL_AREA = 34.0  # below this (in the 48 px canvas) a solid shape stays solid


def role(colour, name=None):
    """The role token for a colour of a recipe (`name`: the icon, for the colours whose role
    depends on what they mean there)."""
    if not colour or colour == "none" or colour.startswith("url("):
        return colour
    c = colour.strip().lower()
    if c in REDS:
        return ALERT if alert_meaning(name) else SECONDARY
    if c in GOLDS and name and name.startswith(GOLD_OBJECT):
        return PRIMARY
    if c in KNOWN:
        return KNOWN[c]
    if not re.match(r"^#[0-9a-f]{6}$", c):
        return colour
    r, g, b = (int(c[i : i + 2], 16) / 255.0 for i in (1, 3, 5))
    hue, light, sat = colorsys.rgb_to_hls(r, g, b)
    if sat < 0.2:
        if light < 0.3:
            return GROUND
        return TEXT if light > 0.85 else PRIMARY
    hue *= 360.0
    if hue < 20 or hue >= 330:  # red
        return ALERT if alert_meaning(name) else SECONDARY
    return SECONDARY


def _shade(colour):
    """How strongly a solid face is filled (lighter faces of a block a little more)."""
    c = (colour or "").strip().lower()
    if not re.match(r"^#[0-9a-f]{6}$", c):
        return 0.14
    r, g, b = (int(c[i : i + 2], 16) / 255.0 for i in (1, 3, 5))
    light = colorsys.rgb_to_hls(r, g, b)[1]
    return max(0.06, min(0.26, 0.06 + (light - 0.45) * 0.45))


def _area(points):
    nums = [float(v) for v in re.findall(r"-?\d*\.?\d+", points)]
    pts = list(zip(nums[0::2], nums[1::2]))
    if len(pts) < 3:
        return 0.0
    total = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        total += x1 * y2 - x2 * y1
    return abs(total) / 2.0


def _tag(kind, attrs):
    return "<%s %s/>" % (kind, " ".join('%s="%s"' % kv for kv in attrs.items()))


def _glow(kind, attrs, width, opacity=GLOW_OPACITY):
    """The wider, fainter copy under a line. A white (text) line glows in the primary colour:
    a white-hot core in a coloured halo, the look of a real neon tube."""
    copy = dict(attrs)
    copy["fill"] = "none"
    if copy.get("stroke") == TEXT:
        copy["stroke"] = PRIMARY
    copy["stroke-width"] = "%.2f" % glow_width(width)
    copy["stroke-opacity"] = "%.2f" % opacity
    copy.pop("stroke-dasharray", None)
    copy.pop("opacity", None)
    copy.pop("fill-opacity", None)
    return _tag(kind, copy)


def _cut_rect(attrs):
    """A large square-cornered rect as a polygon with two opposite corners cut off (the HUD
    look); a rounded rect (a screen, a page) keeps its shape."""
    try:
        x, y = float(attrs.get("x", 0)), float(attrs.get("y", 0))
        w, h = float(attrs["width"]), float(attrs["height"])
        rx = float(attrs.get("rx", 0) or 0)
    except (KeyError, ValueError):
        return "rect", attrs
    if rx > 1.2 or min(w, h) < 7 or "transform" in attrs:
        return "rect", attrs
    c = min(w, h) * 0.24
    pts = [(x + c, y), (x + w, y), (x + w, y + h - c), (x + w - c, y + h), (x, y + h), (x, y + c)]
    out = {k: v for k, v in attrs.items() if k not in ("x", "y", "width", "height", "rx", "ry")}
    out["points"] = " ".join("%.2f,%.2f" % p for p in pts)
    return "polygon", out


def _node(attrs):
    """A small solid dot (a point, a node) as a small square: the set's one point mark."""
    try:
        cx, cy, r = float(attrs.get("cx", 0)), float(attrs.get("cy", 0)), float(attrs["r"])
    except (KeyError, ValueError):
        return "circle", attrs
    half = r * 0.85
    out = {k: v for k, v in attrs.items() if k not in ("cx", "cy", "r")}
    out.update(
        {"x": "%.2f" % (cx - half), "y": "%.2f" % (cy - half), "width": "%.2f" % (2 * half)}
    )
    out["height"] = out["width"]
    return "rect", out


def _outline(kind, attrs, colour, name=None):
    """A solid face as a glowing outline over a faint fill."""
    token = role(colour, name)
    face = dict(attrs)
    face["fill"] = token
    face["fill-opacity"] = "%.2f" % _shade(colour)
    face["stroke"] = token if token.startswith("#n3") else SECONDARY  # (a gradient fill)
    face["stroke-width"] = "%.2f" % FACE
    face["stroke-linejoin"] = "miter"
    if kind == "rect":
        kind, face = _cut_rect(face)
    return _glow(kind, face, FACE, 0.18) + _tag(kind, face)


# make_icons.py's three-face palettes (top, left, right face): GREY, BLUE, DBLUE, PURPLE, GOLD
BLOCK_COLOURS = (
    ("#ececec", "#d2d4d7", "#aeb2b8"),
    ("#bfe5ff", "#8fd0ff", "#5aaee8"),
    ("#7cc4f5", "#4da3e0", "#2f7fbf"),
    ("#e2d4ff", "#c4aef5", "#9f86dd"),
    ("#f6dc8c", "#e8c460", "#c9a23e"),
)
_POLY = r'<polygon points="([^"]*)" fill="(#[0-9a-fA-F]{6})"\s*/>\s*'
_BLOCK = re.compile(_POLY * 3)
TUBE = 4.0  # a stroke at least this wide is drawn as a hollow tube, not a glowing bar


def _points(text):
    nums = [float(v) for v in re.findall(r"-?\d*\.?\d+", text)]
    return list(zip(nums[0::2], nums[1::2]))


def _near(a, b):
    return abs(a[0] - b[0]) < 0.05 and abs(a[1] - b[1]) < 0.05


def _block(match, name=None):
    """make_icons.block()'s three faces as one glowing wireframe: faint faces, the silhouette
    at full weight, the three inner edges thin (three separate outlines doubled every shared
    edge and buzzed at 18 px). None when the polygons are not such a block."""
    g = match.groups()
    colours = (g[1].lower(), g[3].lower(), g[5].lower())
    if colours not in BLOCK_COLOURS:
        return None
    top, left, right = _points(g[0]), _points(g[2]), _points(g[4])
    if len(top) != 4 or len(left) != 4 or len(right) != 4:
        return None
    if not (
        _near(left[2], top[2])
        and _near(right[2], top[2])
        and _near(left[3], top[3])
        and _near(right[3], top[1])
        and _near(left[1], right[1])
    ):
        return None
    t0, t1, t2, t3 = top
    b1, b2, b3 = right[0], right[1], left[0]
    token = role(colours[0], name)

    def poly(pts, **attrs):
        attrs = dict(attrs)
        attrs["points"] = " ".join("%.2f,%.2f" % p for p in pts)
        return attrs

    out = ""
    for pts, opacity in ((top, 0.22), (left, 0.12), (right, 0.06)):
        out += _tag("polygon", poly(pts, fill=token, **{"fill-opacity": "%.2f" % opacity}))
    edge = {"fill": "none", "stroke": token, "stroke-width": "%.2f" % EDGE, "stroke-linejoin": "miter"}
    hexagon = poly([t0, t1, b1, b2, b3, t3], **edge)
    out += _glow("polygon", hexagon, EDGE, 0.2) + _tag("polygon", hexagon)
    inner = dict(edge)
    inner["stroke-width"] = "%.2f" % (DETAIL * 0.8)
    inner["d"] = "M%.2f %.2f L%.2f %.2f L%.2f %.2f M%.2f %.2f L%.2f %.2f" % (t3 + t2 + t1 + t2 + b2)
    del inner["stroke-linejoin"]
    return out + _tag("path", inner)


def _tube(kind, attrs, width):
    """A very wide stroke (a pipe, a spring) as a hollow glowing tube."""
    glow = dict(attrs)
    glow.update({"fill": "none", "stroke-width": "%.2f" % glow_width(width), "stroke-opacity": "0.2"})
    if glow.get("stroke") == TEXT:
        glow["stroke"] = PRIMARY
    glow.pop("stroke-dasharray", None)
    hollow = dict(attrs)
    hollow.update({"stroke": GROUND, "stroke-width": "%.2f" % (width - 2.6)})
    inside = dict(hollow)
    inside.update({"stroke": attrs.get("stroke", PRIMARY), "stroke-opacity": "0.2"})
    return _tag(kind, glow) + _tag(kind, attrs) + _tag(kind, hollow) + _tag(kind, inside)


def neonize(body, name=None):
    """A recipe's SVG body in the neon language (`name`: the icon's, see role())."""
    out = []
    last = 0
    for match in _BLOCK.finditer(body):
        block = _block(match, name)
        if block is None:
            continue
        out.append(_convert(body[last : match.start()], name))
        out.append(block)
        last = match.end()
    out.append(_convert(body[last:], name))
    # gradients and any other colour attribute left: their role too
    return re.sub(
        r'((?:stop-color|color|fill|stroke)=")(#[0-9a-fA-F]{6})(")',
        lambda m: m.group(1) + role(m.group(2), name) + m.group(3),
        "".join(out),
    )


def _convert(body, name=None):
    """Every shape of a piece of SVG body, one at a time."""
    out = []
    last = 0
    for match in _TAG.finditer(body):
        out.append(body[last : match.start()])
        last = match.end()
        kind = match.group(1)
        attrs = dict(_ATTR.findall(match.group(2)))
        fill = attrs.get("fill", "none" if kind in ("line", "polyline", "path") else "#000000")
        stroke = attrs.get("stroke")
        width = float(attrs.get("stroke-width", "1.5") or 1.5)
        if kind in ("line", "polyline") or (kind == "path" and fill == "none"):
            if stroke:
                attrs["stroke"] = role(stroke, name)
            if width >= TUBE and stroke:
                out.append(_tube(kind, attrs, width))
                continue
            out.append(_glow(kind, attrs, width) + _tag(kind, attrs))
            continue
        if kind == "path":  # a filled path
            attrs["fill"] = role(fill, name)
            attrs["fill-opacity"] = "0.30"
            attrs["stroke"] = role(stroke, name) if stroke else role(fill, name)
            attrs.setdefault("stroke-width", "1.30")
            out.append(_glow(kind, attrs, float(attrs["stroke-width"])) + _tag(kind, attrs))
            continue
        if kind == "polygon":
            small = _area(attrs.get("points", "")) < SMALL_AREA
        elif kind == "rect":
            small = float(attrs.get("width", 0)) * float(attrs.get("height", 0)) < SMALL_AREA
        elif kind == "circle":
            small = math.pi * float(attrs.get("r", 0)) ** 2 < SMALL_AREA
        else:  # ellipse
            small = math.pi * float(attrs.get("rx", 0)) * float(attrs.get("ry", 0)) < SMALL_AREA
        if fill in ("none", "") and stroke:  # an outline already
            attrs["stroke"] = role(stroke, name)
            out.append(_glow(kind, attrs, width) + _tag(kind, attrs))
        elif small:
            attrs["fill"] = role(fill, name)
            if stroke:
                attrs["stroke"] = role(stroke, name)
            if kind == "circle":
                kind, attrs = _node(attrs)
            out.append(_tag(kind, attrs))
        else:
            if stroke:
                attrs.pop("stroke-width", None)
            out.append(_outline(kind, attrs, fill, name))
    out.append(body[last:])
    return "".join(out)
