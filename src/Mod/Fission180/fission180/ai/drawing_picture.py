# SPDX-License-Identifier: LGPL-2.1-or-later
"""A picture of a drawing sheet for the AI (get_drawing picture true; wave 8, ai-drawing).

The sheet is drawn from the DXF Fission 180 writes for it (drawing.export_dxf: the frame and
title block, every view's visible, hidden and centre lines, hatching, dimensions, text,
balloons, symbols and tables), so the picture shows exactly what the drawing's export holds,
with or without the Fission 180 window: lines and arcs on their layers (hidden edges dashed,
centre lines dash-dot, dimensions in blue), filled arrow heads, and the text in a plain stroke
font of Fission 180's own (capital letters, digits and the drawing symbols; other characters
as a small box). Drawn at twice the size and averaged (anti-aliased), written as a PNG here.

Pure Python plus numpy (FreeCAD ships numpy). No FreeCAD, no Qt.
"""

import math
import struct
import zlib

SUPERSAMPLE = 2
WHITE = (255, 255, 255)
# layer -> (colour, line width on the paper in mm, dash pattern in mm or None)
LAYERS = {
    "SHEET": ((40, 40, 40), 0.35, None),
    "VISIBLE": ((0, 0, 0), 0.5, None),
    "HIDDEN": ((110, 110, 110), 0.3, (3.0, 1.5)),
    "CENTER": ((60, 90, 140), 0.18, (12.0, 3.0, 2.0, 3.0)),
    "HATCH": ((150, 150, 150), 0.18, None),
    "DIMENSIONS": ((20, 70, 170), 0.25, None),
    "TEXT": ((0, 0, 0), 0.25, None),
    "TABLE": ((0, 0, 0), 0.25, None),
    "SYMBOLS": ((0, 100, 60), 0.25, None),
}
DEFAULT_LAYER = ((0, 0, 0), 0.25, None)

# -- the stroke font: each glyph is polylines on a grid 4 wide, 6 high (the capital height),
# the base line at 0. An original, deliberately plain design.
_O = [(1, 0), (3, 0), (4, 1.2), (4, 4.8), (3, 6), (1, 6), (0, 4.8), (0, 1.2), (1, 0)]
_P = [(0, 0), (0, 6), (3, 6), (4, 5), (4, 4), (3, 3), (0, 3)]
_DOT = [(1.7, 0), (2.3, 0), (2.3, 0.6), (1.7, 0.6), (1.7, 0)]
GLYPHS = {
    "0": [_O, [(0.6, 1), (3.4, 5)]],
    "1": [[(1, 5), (2, 6), (2, 0)], [(1, 0), (3, 0)]],
    "2": [[(0, 5), (1, 6), (3, 6), (4, 5), (4, 4), (0, 0), (4, 0)]],
    "3": [
        [(0, 5), (1, 6), (3, 6), (4, 5), (4, 4), (3, 3), (4, 2), (4, 1), (3, 0), (1, 0), (0, 1)],
        [(1.5, 3), (3, 3)],
    ],
    "4": [[(3, 0), (3, 6), (0, 2), (4, 2)]],
    "5": [[(4, 6), (0, 6), (0, 3.4), (3, 3.4), (4, 2.4), (4, 1), (3, 0), (1, 0), (0, 1)]],
    "6": [[(4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0), (3, 0), (4, 1), (4, 2), (3, 3), (0, 3)]],
    "7": [[(0, 6), (4, 6), (1.2, 0)]],
    "8": [
        [(1, 3), (0, 4), (0, 5), (1, 6), (3, 6), (4, 5), (4, 4), (3, 3), (1, 3)],
        [(1, 3), (0, 2), (0, 1), (1, 0), (3, 0), (4, 1), (4, 2), (3, 3)],
    ],
    "9": [[(0, 1), (1, 0), (3, 0), (4, 1), (4, 5), (3, 6), (1, 6), (0, 5), (0, 4), (1, 3), (4, 3)]],
    "A": [[(0, 0), (2, 6), (4, 0)], [(0.7, 2), (3.3, 2)]],
    "B": [
        [(0, 0), (0, 6), (3, 6), (4, 5), (4, 4), (3, 3), (0, 3)],
        [(3, 3), (4, 2), (4, 1), (3, 0), (0, 0)],
    ],
    "C": [[(4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0), (3, 0), (4, 1)]],
    "D": [[(0, 0), (0, 6), (2.5, 6), (4, 4.5), (4, 1.5), (2.5, 0), (0, 0)]],
    "E": [[(4, 6), (0, 6), (0, 0), (4, 0)], [(0, 3), (3, 3)]],
    "F": [[(4, 6), (0, 6), (0, 0)], [(0, 3), (3, 3)]],
    "G": [[(4, 5), (3, 6), (1, 6), (0, 5), (0, 1), (1, 0), (3, 0), (4, 1), (4, 3), (2, 3)]],
    "H": [[(0, 0), (0, 6)], [(4, 0), (4, 6)], [(0, 3), (4, 3)]],
    "I": [[(1, 6), (3, 6)], [(2, 6), (2, 0)], [(1, 0), (3, 0)]],
    "J": [[(4, 6), (4, 1), (3, 0), (1, 0), (0, 1)]],
    "K": [[(0, 0), (0, 6)], [(4, 6), (0, 2)], [(1.3, 3.3), (4, 0)]],
    "L": [[(0, 6), (0, 0), (4, 0)]],
    "M": [[(0, 0), (0, 6), (2, 3), (4, 6), (4, 0)]],
    "N": [[(0, 0), (0, 6), (4, 0), (4, 6)]],
    "O": [_O],
    "P": [_P],
    "Q": [_O, [(2.5, 1.5), (4, 0)]],
    "R": [_P, [(2, 3), (4, 0)]],
    "S": [
        [(4, 5), (3, 6), (1, 6), (0, 5), (0, 4), (1, 3), (3, 3), (4, 2), (4, 1), (3, 0), (1, 0)]
        + [(0, 1)]
    ],
    "T": [[(0, 6), (4, 6)], [(2, 6), (2, 0)]],
    "U": [[(0, 6), (0, 1), (1, 0), (3, 0), (4, 1), (4, 6)]],
    "V": [[(0, 6), (2, 0), (4, 6)]],
    "W": [[(0, 6), (1, 0), (2, 4), (3, 0), (4, 6)]],
    "X": [[(0, 0), (4, 6)], [(0, 6), (4, 0)]],
    "Y": [[(0, 6), (2, 3), (4, 6)], [(2, 3), (2, 0)]],
    "Z": [[(0, 6), (4, 6), (0, 0), (4, 0)]],
    ".": [_DOT],
    ",": [[(2.3, 0.6), (2, 0), (1.4, -1)]],
    ":": [_DOT, [(1.7, 3.5), (2.3, 3.5), (2.3, 4.1), (1.7, 4.1), (1.7, 3.5)]],
    ";": [[(2.3, 0.6), (2, 0), (1.4, -1)], [(1.7, 3.5), (2.3, 3.5), (2.3, 4.1), (1.7, 4.1)]],
    "-": [[(0.6, 3), (3.4, 3)]],
    "_": [[(0, -0.6), (4, -0.6)]],
    "+": [[(0.5, 3), (3.5, 3)], [(2, 1.5), (2, 4.5)]],
    "=": [[(0.5, 2), (3.5, 2)], [(0.5, 4), (3.5, 4)]],
    "/": [[(0, 0), (4, 6)]],
    "\\": [[(0, 6), (4, 0)]],
    "(": [[(3, 6.5), (2, 5.5), (1.5, 3), (2, 0.5), (3, -0.5)]],
    ")": [[(1, 6.5), (2, 5.5), (2.5, 3), (2, 0.5), (1, -0.5)]],
    "[": [[(3, 6.5), (1.5, 6.5), (1.5, -0.5), (3, -0.5)]],
    "]": [[(1, 6.5), (2.5, 6.5), (2.5, -0.5), (1, -0.5)]],
    "<": [[(4, 5), (0, 3), (4, 1)]],
    ">": [[(0, 5), (4, 3), (0, 1)]],
    "*": [[(2, 1.5), (2, 4.5)], [(0.7, 2.2), (3.3, 3.8)], [(0.7, 3.8), (3.3, 2.2)]],
    "!": [[(2, 6), (2, 1.8)], _DOT],
    "?": [[(0, 5), (1, 6), (3, 6), (4, 5), (4, 4), (2, 2.6), (2, 1.6)], _DOT],
    "'": [[(2, 6), (2, 4.5)]],
    '"': [[(1.3, 6), (1.3, 4.5)], [(2.7, 6), (2.7, 4.5)]],
    "|": [[(2, -1), (2, 7)]],
    "#": [[(1.3, 0), (1.3, 6)], [(2.7, 0), (2.7, 6)], [(0, 2), (4, 2)], [(0, 4), (4, 4)]],
    "%": [
        [(0, 0), (4, 6)],
        [(0, 5), (1, 5), (1, 6), (0, 6), (0, 5)],
        [(3, 0), (4, 0), (4, 1), (3, 1), (3, 0)],
    ],
    "&": [[(4, 0), (1, 4), (1, 5.4), (2, 6), (3, 5.4), (3, 4.6), (0, 2), (0, 1), (1, 0), (4, 3)]],
    "@": [_O, [(2.8, 2), (2.8, 4), (1.4, 4), (1.4, 2), (2.8, 2)]],
    "°": [[(1.4, 4.6), (2.6, 4.6), (2.6, 5.8), (1.4, 5.8), (1.4, 4.6)]],
    "⌀": [  # the diameter sign
        [(2, 0.6), (3.2, 1.1), (3.6, 3), (3.2, 4.9), (2, 5.4), (0.8, 4.9), (0.4, 3), (0.8, 1.1)]
        + [(2, 0.6)],
        [(0, 0), (4, 6)],
    ],
    "±": [[(0.5, 3.6), (3.5, 3.6)], [(2, 2.1), (2, 5.1)], [(0.5, 0.6), (3.5, 0.6)]],
    "×": [[(0.6, 1.4), (3.4, 4.6)], [(0.6, 4.6), (3.4, 1.4)]],
}
GLYPHS["Ø"] = GLYPHS["⌀"]  # (Ø)
GLYPHS["∅"] = GLYPHS["⌀"]  # (∅)
_BOX = [[(0.5, 0), (3.5, 0), (3.5, 5), (0.5, 5), (0.5, 0)]]
GLYPH_WIDTH = 0.85  # the grid's x scaled: a glyph is 3.4 units wide
ADVANCE = 4.6  # units from one character to the next (a capital's height is 6)


def glyph(char):
    """The strokes of a character (lower case drawn as capitals; a space has none)."""
    if char == " ":
        return []
    found = GLYPHS.get(char)
    if found is None:
        found = GLYPHS.get(char.upper())
    return found if found is not None else _BOX


def text_width(text, height):
    """Width (mm) of a text line drawn `height` mm high."""
    return max(0, len(text)) * ADVANCE * height / 6.0


def text_strokes(text, x, y, height, align="left", rotation=0.0):
    """Polylines (page mm) of a text line: (x, y) its base line's start, middle (align
    center) or end (right); rotation in degrees counter-clockwise."""
    unit = height / 6.0
    width = text_width(text, height)
    start = {"center": -width / 2.0, "middle": -width / 2.0, "right": -width}.get(align, 0.0)
    c, s = math.cos(math.radians(rotation)), math.sin(math.radians(rotation))
    out = []
    for i, char in enumerate(text):
        ox = start + i * ADVANCE * unit
        for line in glyph(char):
            pts = []
            for gx, gy in line:
                u = ox + gx * GLYPH_WIDTH * unit
                v = gy * unit
                pts.append((x + u * c - v * s, y + u * s + v * c))
            out.append(pts)
    return out


# -- DXF entities --------------------------------------------------------------------------------
def _num(codes, code, default=0.0, index=0):
    try:
        return float(codes[code][index])
    except (KeyError, IndexError, ValueError):
        return default


def _arc_points(cx, cy, r, a0, a1, mm_per_px):
    if a1 <= a0:
        a1 += 360.0
    span = math.radians(a1 - a0)
    n = max(8, int(abs(span) * r / max(mm_per_px * 2.0, 1e-6)) + 1)
    n = min(n, 720)
    return [
        (
            cx + r * math.cos(math.radians(a0) + span * i / n),
            cy + r * math.sin(math.radians(a0) + span * i / n),
        )
        for i in range(n + 1)
    ]


def shapes(entities, mm_per_px=0.25):
    """{layer: {"lines": [polyline], "fills": [polygon]}} in page mm from DXF entities
    (drawing_core.read_dxf_entities)."""
    out = {}
    for kind, codes in entities:
        layer = (codes.get(8) or ["0"])[0]
        bucket = out.setdefault(layer, {"lines": [], "fills": []})
        if kind == "LINE":
            bucket["lines"].append(
                [(_num(codes, 10), _num(codes, 20)), (_num(codes, 11), _num(codes, 21))]
            )
        elif kind == "CIRCLE":
            bucket["lines"].append(
                _arc_points(
                    _num(codes, 10), _num(codes, 20), _num(codes, 40), 0.0, 360.0, mm_per_px
                )
            )
        elif kind == "ARC":
            bucket["lines"].append(
                _arc_points(
                    _num(codes, 10),
                    _num(codes, 20),
                    _num(codes, 40),
                    _num(codes, 50),
                    _num(codes, 51),
                    mm_per_px,
                )
            )
        elif kind == "SOLID":
            pts = [(_num(codes, 10 + i), _num(codes, 20 + i)) for i in range(4)]
            if pts[3] == pts[2]:
                pts = pts[:3]
            else:  # (DXF's SOLID corner order: 1 2 4 3; Fission 180 writes triangles)
                pts = [pts[0], pts[1], pts[3], pts[2]]
            bucket["fills"].append(pts)
        elif kind == "TEXT":
            text = (codes.get(1) or [""])[0]
            height = _num(codes, 40, 2.5)
            align = {"1": "center", "2": "right", "4": "center"}.get((codes.get(72) or ["0"])[0])
            if align and 11 in codes:
                x, y = _num(codes, 11), _num(codes, 21)
            else:
                x, y = _num(codes, 10), _num(codes, 20)
            bucket["lines"] += text_strokes(
                text, x, y, height, align or "left", _num(codes, 50, 0.0)
            )
    return out


# -- drawing --------------------------------------------------------------------------------------
def _np():
    import numpy

    return numpy


def _stamp(np, image, xs, ys, color, radius):
    h, w = image.shape[:2]
    r = max(0, int(round(radius)))
    for dy in range(-r, r + 1):
        for dx in range(-r, r + 1):
            if dx * dx + dy * dy > r * r + r:
                continue
            x = xs + dx
            y = ys + dy
            keep = (x >= 0) & (x < w) & (y >= 0) & (y < h)
            image[y[keep], x[keep]] = color


def _polylines(np, image, lines, to_px, k, color, width_mm, dash):
    xs_all, ys_all = [], []
    for line in lines:
        for a, b in zip(line, line[1:]):
            ax, ay = to_px(a)
            bx, by = to_px(b)
            length = math.hypot(bx - ax, by - ay)
            n = max(2, int(length) + 2)
            t = np.linspace(0.0, 1.0, n)
            if dash:
                period = sum(dash)
                along = t * length / k  # mm along the segment
                phase = np.mod(along, period)
                on = np.zeros(n, dtype=bool)
                start = 0.0
                for i, part in enumerate(dash):
                    if i % 2 == 0:
                        on |= (phase >= start) & (phase < start + part)
                    start += part
                t = t[on]
            xs_all.append(np.rint(ax + (bx - ax) * t).astype(np.int64))
            ys_all.append(np.rint(ay + (by - ay) * t).astype(np.int64))
    if not xs_all:
        return
    xs = np.concatenate(xs_all)
    ys = np.concatenate(ys_all)
    _stamp(np, image, xs, ys, color, max(width_mm * k / 2.0, 0.5))


def _fill(np, image, polygon, to_px, color):
    pts = [to_px(p) for p in polygon]
    x0 = max(int(math.floor(min(p[0] for p in pts))), 0)
    x1 = min(int(math.ceil(max(p[0] for p in pts))), image.shape[1] - 1)
    y0 = max(int(math.floor(min(p[1] for p in pts))), 0)
    y1 = min(int(math.ceil(max(p[1] for p in pts))), image.shape[0] - 1)
    if x1 < x0 or y1 < y0:
        return
    gx, gy = np.meshgrid(np.arange(x0, x1 + 1) + 0.5, np.arange(y0, y1 + 1) + 0.5)
    inside = np.zeros(gx.shape, dtype=bool)
    n = len(pts)
    for i in range(n):
        (xa, ya), (xb, yb) = pts[i], pts[(i + 1) % n]
        crosses = ((ya > gy) != (yb > gy)) & (
            gx < (xb - xa) * (gy - ya) / ((yb - ya) if abs(yb - ya) > 1e-12 else 1e-12) + xa
        )
        inside ^= crosses
    region = image[y0 : y1 + 1, x0 : x1 + 1]
    region[inside] = color


def render(entities, sheet_size, width=1200):
    """A PNG (bytes) of a sheet `sheet_size` (w, h) mm whose DXF entities are given,
    `width` pixels wide."""
    np = _np()
    sheet_w, sheet_h = float(sheet_size[0]), float(sheet_size[1])
    if sheet_w <= 0 or sheet_h <= 0:
        raise ValueError("the sheet has no size")
    width = int(max(64, min(width, 6000)))
    height = max(1, int(round(width * sheet_h / sheet_w)))
    big_w, big_h = width * SUPERSAMPLE, height * SUPERSAMPLE
    k = big_w / sheet_w  # pixels per mm

    def to_px(p):
        return p[0] * k, (sheet_h - p[1]) * k

    image = np.empty((big_h, big_w, 3), dtype=np.uint8)
    image[:] = WHITE
    layers = shapes(entities, 1.0 / k)
    order = ["HATCH", "CENTER", "HIDDEN", "SHEET", "TABLE", "VISIBLE"]
    order += sorted(name for name in layers if name not in order)
    for name in order:
        bucket = layers.get(name)
        if not bucket:
            continue
        color, width_mm, dash = LAYERS.get(name, DEFAULT_LAYER)
        _polylines(np, image, bucket["lines"], to_px, k, color, width_mm, dash)
        for polygon in bucket["fills"]:
            _fill(np, image, polygon, to_px, color)
    small = image.reshape(height, SUPERSAMPLE, width, SUPERSAMPLE, 3).mean(axis=(1, 3))
    return png_bytes(np.clip(np.rint(small), 0, 255).astype(np.uint8))


def png_bytes(rgb):
    """A PNG file of an (h, w, 3) uint8 array."""
    h, w = rgb.shape[:2]
    raw = b"".join(b"\x00" + rgb[y].tobytes() for y in range(h))

    def chunk(tag, data):
        body = tag + data
        return (
            struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)
        )

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw, 6))
        + chunk(b"IEND", b"")
    )


def ink(png_rgb, box=None):
    """How many pixels of an (h, w, 3) array are not white (tests)."""
    np = _np()
    area = png_rgb if box is None else png_rgb[box[1] : box[3], box[0] : box[2]]
    return int(np.count_nonzero(np.any(area < 250, axis=2)))
