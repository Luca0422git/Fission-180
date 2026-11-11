# SPDX-License-Identifier: LGPL-2.1-or-later
"""The patterns of textured looks (wood grain, leather, brushed metal, carbon weave, mesh...),
made here by plain arithmetic: no picture file, nothing downloaded or copied. Pure Python (no
FreeCAD, no Qt, no numpy), unit tested (test_appearance_textures.py).

A pattern is a function of (u, v) in 0..1, the same at 0 and at 1 on both sides (it repeats
without a seam), giving a number -1..1: below 0 the look's colour is darkened by that much
there, above 0 lightened. pixels() draws one as an RGBA picture the 3D view lays over the
look's colour (black or white with the strength as its alpha), so one pattern serves a look
of any colour and an edited colour keeps its grain.

TILE: how many millimetres one repeat covers at Scale 100 %.
"""

import math
import random

TWO_PI = 2.0 * math.pi


class Lattice:
    """Smooth noise that repeats: random values on an nx x ny grid, blended in between."""

    def __init__(self, nx, ny, seed):
        rnd = random.Random(seed)
        self.nx, self.ny = nx, ny
        self.values = [[rnd.random() for _ in range(nx)] for _ in range(ny)]

    def at(self, u, v):
        x, y = u * self.nx, v * self.ny
        ix, iy = int(math.floor(x)), int(math.floor(y))
        fx, fy = x - ix, y - iy
        fx = fx * fx * (3.0 - 2.0 * fx)
        fy = fy * fy * (3.0 - 2.0 * fy)
        ix %= self.nx
        iy %= self.ny
        jx, jy = (ix + 1) % self.nx, (iy + 1) % self.ny
        rows = self.values
        a, b, c, d = rows[iy][ix], rows[iy][jx], rows[jy][ix], rows[jy][jx]
        return a + (b - a) * fx + (c - a) * fy + (a - b - c + d) * fx * fy


class Cells:
    """Scattered points on an n x n grid (one in each square, repeating): near() gives the
    distances to the nearest and the second nearest, in squares."""

    def __init__(self, n, seed):
        rnd = random.Random(seed)
        self.n = n
        self.points = [[(rnd.random(), rnd.random()) for _ in range(n)] for _ in range(n)]

    def near(self, u, v):
        n = self.n
        x, y = u * n, v * n
        ix, iy = int(math.floor(x)), int(math.floor(y))
        first = second = 9.0
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                cx, cy = ix + dx, iy + dy
                px, py = self.points[cy % n][cx % n]
                dist = math.hypot(cx + px - x, cy + py - y)
                if dist < first:
                    first, second = dist, first
                elif dist < second:
                    second = dist
        return first, second


def _fract(value):
    return value - math.floor(value)


def _step(lo, hi, value):
    if value <= lo:
        return 0.0
    if value >= hi:
        return 1.0
    t = (value - lo) / (hi - lo)
    return t * t * (3.0 - 2.0 * t)


# -- the patterns (each maker returns the function) ----------------------------------------------
def _brushed(streaks, long_streaks, seed):
    fine = Lattice(streaks[0], streaks[1], seed)
    wide = Lattice(long_streaks[0], long_streaks[1], seed + 1)

    def at(u, v):
        return (fine.at(u, v) - 0.5) * 0.55 + (wide.at(u, v) - 0.5) * 0.3

    return at


def _stone(seed):
    layers = [Lattice(n, n, seed + i) for i, n in enumerate((4, 8, 16, 32))]

    def at(u, v):
        total = 0.0
        weight = 0.5
        for layer in layers:
            total += (layer.at(u, v) - 0.5) * weight
            weight *= 0.55
        return total * 0.95

    return at


def _speckle(seed):
    dots = Lattice(72, 72, seed)
    cloud = Lattice(6, 6, seed + 1)

    def at(u, v):
        value = dots.at(u, v)
        return (value - 0.5) * 0.5 + (cloud.at(u, v) - 0.5) * 0.12

    return at


def _mesh(cells):
    wire = 0.24

    def at(u, v):
        fu, fv = _fract(u * cells), _fract(v * cells)
        if fu < wire or fv < wire:  # a wire: rounded by a highlight along its middle
            across = fu / wire if fu < wire else fv / wire
            return 0.22 * (1.0 - abs(2.0 * across - 1.0)) - 0.05
        return -0.82  # the hole (drawn dark: the view cannot cut it out)

    return at


def _knurl(lines):
    def at(u, v):
        a, b = _fract((u + v) * lines), _fract((u - v) * lines)
        if a < 0.16 or b < 0.16:
            return -0.45
        peak = 1.0 - 2.0 * max(abs(a - 0.58), abs(b - 0.58))
        return 0.22 * max(0.0, peak)

    return at


def _cells(count, edge, depth, seed, bumps=0.0):
    cells = Cells(count, seed)
    grain = Lattice(48, 48, seed + 7)

    def at(u, v):
        first, second = cells.near(u, v)
        border = 1.0 - _step(0.0, edge, second - first)
        value = -depth * border + 0.10 * (1.0 - _step(0.0, 0.6, first))
        if bumps:
            value += (grain.at(u, v) - 0.5) * bumps
        return value

    return at


def _cloth(threads):
    def at(u, v):
        iu, iv = int(math.floor(u * threads)), int(math.floor(v * threads))
        fu, fv = _fract(u * threads), _fract(v * threads)
        if (iu + iv) % 2 == 0:  # the thread running along u lies on top here
            return 0.24 * (1.0 - abs(2.0 * fv - 1.0)) - 0.14
        return 0.24 * (1.0 - abs(2.0 * fu - 1.0)) - 0.2

    return at


def _carbon(tows, twill):
    def at(u, v):
        iu, iv = int(math.floor(u * tows)), int(math.floor(v * tows))
        fu, fv = _fract(u * tows), _fract(v * tows)
        if fu < 0.06 or fv < 0.06:
            return -0.5  # the gap between two tows
        over = ((iu - iv) % 4) < 2 if twill else (iu + iv) % 2 == 0
        if over:
            return 0.08 + 0.26 * (1.0 - abs(2.0 * fu - 1.0)) + 0.05 * math.sin(fv * TWO_PI * 6)
        return -0.32 - 0.14 * abs(2.0 * fv - 1.0) + 0.04 * math.sin(fu * TWO_PI * 6)

    return at


def _wood(rings, wave, sharp, depth, pores, seed, fine=(6, 12, 0.6), early=False):
    """Grain running along u: `rings` dark lines across v, bent by `wave`."""
    bend = Lattice(2, 3, seed)
    ripple = Lattice(fine[0], fine[1], seed + 1)
    tone = Lattice(2, 2, seed + 2)
    pore = Lattice(28, 200, seed + 3)

    def at(u, v):
        t = v * rings + wave * (bend.at(u, v) - 0.5) + fine[2] * (ripple.at(u, v) - 0.5)
        band = _fract(t)
        if early:  # softwood: a narrow dark line where each year ends
            value = -depth * band**sharp
        else:
            value = -depth * (abs(band - 0.5) * 2.0) ** sharp
        value += 0.14 * (tone.at(u, v) - 0.5)
        if pores and pore.at(u, v) > 0.8:
            value -= pores
        return value

    return at


def _flake(seed):
    sparks = Lattice(110, 110, seed)
    cloud = Lattice(24, 24, seed + 1)

    def at(u, v):
        spark = sparks.at(u, v)
        if spark > 0.82:
            return 0.6 * (spark - 0.82) / 0.18
        return (cloud.at(u, v) - 0.5) * 0.14

    return at


MAKERS = {
    "brushed": lambda: _brushed((3, 180), (2, 40), 11),
    "brushed_long": lambda: _brushed((1, 150), (1, 36), 21),
    "stone": lambda: _stone(31),
    "speckle": lambda: _speckle(41),
    "mesh": lambda: _mesh(5),
    "mesh_small": lambda: _mesh(12),
    "knurl": lambda: _knurl(10),
    "foam": lambda: _cells(9, 0.16, 0.34, 51),
    "leather": lambda: _cells(16, 0.2, 0.42, 61, bumps=0.16),
    "leather_coarse": lambda: _cells(9, 0.18, 0.5, 71, bumps=0.14),
    "cloth": lambda: _cloth(28),
    "carbon": lambda: _carbon(8, True),
    "carbon_plain": lambda: _carbon(8, False),
    "wood_oak": lambda: _wood(12, 2.2, 3, 0.42, 0.18, 81),
    "wood_fine": lambda: _wood(26, 1.2, 2, 0.22, 0.14, 91, fine=(8, 20, 0.4)),
    "wood_pine": lambda: _wood(7, 1.8, 4, 0.4, 0.0, 101, early=True),
    "wood_wavy": lambda: _wood(10, 3.6, 2, 0.36, 0.12, 111, fine=(5, 7, 1.2)),
    "flake": lambda: _flake(121),
}

# Millimetres one repeat of the pattern covers at Scale 100 %.
TILE = {
    "brushed": 40.0,
    "brushed_long": 80.0,
    "stone": 80.0,
    "speckle": 20.0,
    "mesh": 30.0,
    "mesh_small": 30.0,
    "knurl": 20.0,
    "foam": 30.0,
    "leather": 32.0,
    "leather_coarse": 30.0,
    "cloth": 20.0,
    "carbon": 16.0,
    "carbon_plain": 16.0,
    "wood_oak": 90.0,
    "wood_fine": 90.0,
    "wood_pine": 90.0,
    "wood_wavy": 90.0,
    "flake": 24.0,
}

# What the patterns are called in the look editor's Pattern list.
LABELS = {
    "brushed": "Brushed, short",
    "brushed_long": "Brushed, long",
    "stone": "Mottled",
    "speckle": "Speckled",
    "mesh": "Mesh, large squares",
    "mesh_small": "Mesh, small squares",
    "knurl": "Knurled",
    "foam": "Foam beads",
    "leather": "Leather, fine",
    "leather_coarse": "Leather, pebbled",
    "cloth": "Woven cloth",
    "carbon": "Carbon weave, twill",
    "carbon_plain": "Carbon weave, plain",
    "wood_oak": "Wood grain, open",
    "wood_fine": "Wood grain, fine",
    "wood_pine": "Wood grain, softwood",
    "wood_wavy": "Wood grain, wavy",
    "flake": "Metallic flake",
}

SIZE = 128  # pixels on a side of the picture the 3D view uses
_PIXELS = {}


def names():
    return sorted(MAKERS)


def exists(name):
    return name in MAKERS


def tile_mm(name):
    return TILE.get(name, 40.0)


def label(name):
    return LABELS.get(name, name)


def function(name):
    """The pattern's function of (u, v), or None for an unknown name."""
    maker = MAKERS.get(name)
    return maker() if maker is not None else None


def pixels(name, size=SIZE):
    """The pattern as RGBA bytes, size x size, rows from v = 0: black (darken) or white
    (lighten) with the strength as alpha. None for an unknown name. Cached."""
    key = (name, int(size))
    if key in _PIXELS:
        return _PIXELS[key]
    at = function(name)
    if at is None:
        return None
    size = int(size)
    data = bytearray(size * size * 4)
    step = 1.0 / size
    index = 0
    for row in range(size):
        v = (row + 0.5) * step
        for column in range(size):
            value = at((column + 0.5) * step, v)
            if value > 0.0:  # lighten: white (darken stays black)
                data[index] = data[index + 1] = data[index + 2] = 255
            data[index + 3] = int(min(1.0, abs(value)) * 255.0 + 0.5)
            index += 4
    _PIXELS[key] = bytes(data)
    return _PIXELS[key]


def shade(name, color, u, v):
    """The look's colour (r, g, b 0..1) with the pattern laid on it at (u, v): what the 3D
    view shows there before the light (swatches, tests)."""
    at = function(name)
    if at is None:
        return tuple(color)
    return blend(color, at(u, v))


def blend(color, value):
    """`color` darkened (value < 0) or lightened (value > 0) by a pattern's value."""
    if value < 0.0:
        keep = 1.0 - min(1.0, -value)
        return tuple(c * keep for c in color)
    mix = min(1.0, value)
    return tuple(c + (1.0 - c) * mix for c in color)
