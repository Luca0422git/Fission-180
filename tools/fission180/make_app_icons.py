#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Generates Fission 180's application identity images.

    python3 tools/fission180/make_app_icons.py            # writes the files listed below
    python3 tools/fission180/make_app_icons.py --out DIR  # writes everything into DIR instead

The mark is original artwork: a round nucleus split in two (fission), its halves drawn
apart with the amber spark of the split between them, in white and amber on a blue rounded
square. It is defined once, as geometry in a 64 x 64 design space, and drawn
from that geometry both as SVG (text) and as supersampled bitmaps (Pillow), so every
format shows the same picture. Nothing is traced from FreeCAD's or Autodesk's artwork.

Files written (all committed; re-run after editing the design):

  src/Gui/Icons/fission180app.svg                   window / taskbar icon (Qt resource)
  src/Gui/Icons/fission180-icon-{16..256}.png       Linux hicolor icons (installed by CMake)
  src/Gui/Icons/fission180splash.png, _2x.png        splash screen (568 x 368 and 2x)
  src/Gui/Icons/fission180about.png                  About dialog banner (552 x 189)
  src/Main/fission180.ico                            icon compiled into Fission180.exe
  src/Mod/Fission180/fission180/icons/fission180.svg     the workbench icon (same mark)
  package/WindowsInstaller/icons/Fission180.ico      installer / uninstaller icon
  package/WindowsInstaller/graphics/fission180-header.bmp   (150 x 57, 24-bit)
  package/WindowsInstaller/graphics/fission180-banner.bmp   (164 x 314, 24-bit)

The splash leaves room for what FreeCAD paints on it at start-up: the version number
right after the wordmark (SplashInfoPosition "190,189" in src/Main/MainGui.cpp puts it at
x = 190 + 235 = 425, y = 182, next to a baked "Version" caption) and the loading messages
at the bottom left.
"""

import argparse
import os
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:  # pragma: no cover
    sys.exit("[Fission 180] make_app_icons needs Pillow: python3 -m pip install pillow")

REPO = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

# ---- the mark, in a 64 x 64 design space ------------------------------------------------
BG_TOP = (74, 163, 245)  # blue gradient, top
BG_BOTTOM = (31, 99, 181)  # blue gradient, bottom
WHITE = (255, 255, 255)
AMBER = (255, 179, 71)  # the spark
AMBER_LIGHT = (255, 217, 122)
INSET, RADIUS = 2.0, 14.0  # rounded square
# The mark: a round nucleus split in two, the halves drawn apart along a slanted line, with
# the amber spark of the split between them and two particles flying off (the "fission").
import math  # noqa: E402

CENTER = (32.0, 33.0)
TILT = -32.0  # degrees: the split line leans like a forward slash


def _rotate(points, center=CENTER, degrees=TILT):
    a = math.radians(degrees)
    cx, cy = center
    out = []
    for x, y in points:
        dx, dy = x - cx, y - cy
        out.append((cx + dx * math.cos(a) - dy * math.sin(a), cy + dx * math.sin(a) + dy * math.cos(a)))
    return out


def half_disc(side, radius, gap, segments=48):
    """One half of the split nucleus (side -1: left, +1: right) as a polygon, its flat edge
    `gap` / 2 away from the centre line, before the tilt."""
    cx, cy = CENTER
    edge = cx + side * gap / 2.0
    points = []
    for i in range(segments + 1):
        angle = math.radians(-90 + i * 180.0 / segments)
        # (a right half runs from the top over the right side to the bottom; a left one mirrored)
        x = edge + side * radius * math.cos(angle)
        y = cy + radius * math.sin(angle)
        points.append((x, y))
    return _rotate(points)


HALF_RADIUS, HALF_GAP = 15.0, 9.0
HALVES = [half_disc(-1, HALF_RADIUS, HALF_GAP), half_disc(1, HALF_RADIUS, HALF_GAP)]
STAR_CENTER, STAR_OUTER, STAR_INNER = CENTER, 8.5, 2.6
DOTS = [((52.5, 11.5), 2.2), ((11.5, 54.5), 1.8)]
# At 24 px and below the gap and the dots blur away: bigger halves, a wider gap, one spark.
HALVES_SMALL = [half_disc(-1, 17.0, 11.0), half_disc(1, 17.0, 11.0)]
STAR_SMALL_CENTER, STAR_SMALL_OUTER, STAR_SMALL_INNER = CENTER, 10.0, 3.2
SMALL_ICON = 24

# ---- colours of the larger pictures (Fission 180's dark theme) -----------------------------
DARK = (22, 28, 38)
DARK_BAND = (29, 37, 51)
TEXT = (255, 255, 255)
TEXT_ACCENT = (143, 208, 255)  # "180" in the wordmark, also SplashTextColor
TEXT_SOFT = (207, 216, 227)
TEXT_DIM = (140, 151, 166)

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
FONT_BOLD = os.path.join(FONT_DIR, "DejaVuSans-Bold.ttf")
FONT_REGULAR = os.path.join(FONT_DIR, "DejaVuSans.ttf")

SUBTITLE = "Parametric CAD with the Fusion workflow"
BASED_ON = "Based on FreeCAD, free software under the LGPL-2.1-or-later"
REPO_URL = "github.com/Luca0422git/Fission-180"
# Where FreeCAD paints the version on the splash: SplashInfoPosition "x,y" in
# src/Main/MainGui.cpp is "SPLASH_TEXT_X,SPLASH_INFO_Y"; the number lands at (x + 235, y - 7).
SPLASH_TEXT_X, SPLASH_INFO_Y = 190, 189


def star_points(center, outer, inner, points=4):
    import math

    cx, cy = center
    result = []
    for i in range(points * 2):
        angle = math.radians(-90 + i * 180.0 / points)
        radius = outer if i % 2 == 0 else inner
        result.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))
    return result


def rgb(color):
    return "#%02x%02x%02x" % color


# ---- SVG ----------------------------------------------------------------------------------
def svg_text():
    def pts(points):
        return " ".join("%.2f,%.2f" % p for p in points)

    lines = [
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="64" height="64">',
        "  <!-- Fission 180 application icon: a nucleus splitting in two, with the spark of the",
        "       split. Original artwork, generated",
        "       by tools/fission180/make_app_icons.py (LGPL-2.1-or-later). -->",
        "  <defs>",
        '    <linearGradient id="bg" x1="0" y1="0" x2="0" y2="1">',
        '      <stop offset="0" stop-color="%s"/>' % rgb(BG_TOP),
        '      <stop offset="1" stop-color="%s"/>' % rgb(BG_BOTTOM),
        "    </linearGradient>",
        "  </defs>",
        '  <rect x="%g" y="%g" width="%g" height="%g" rx="%g" fill="url(#bg)"/>'
        % (INSET, INSET, 64 - 2 * INSET, 64 - 2 * INSET, RADIUS),
    ]
    for half in HALVES:
        lines.append('  <polygon points="%s" fill="%s"/>' % (pts(half), rgb(WHITE)))
    lines.append(
        '  <polygon points="%s" fill="%s"/>'
        % (pts(star_points(STAR_CENTER, STAR_OUTER, STAR_INNER)), rgb(AMBER))
    )
    for (cx, cy), r in DOTS:
        lines.append('  <circle cx="%g" cy="%g" r="%g" fill="%s"/>' % (cx, cy, r, rgb(AMBER_LIGHT)))
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


# ---- bitmaps ------------------------------------------------------------------------------
CANVAS = 1024  # the mark is drawn at this size and scaled down (antialiasing)


def _gradient(width, height, top, bottom):
    image = Image.new("RGBA", (width, height))
    draw = ImageDraw.Draw(image)
    for y in range(height):
        t = y / max(1, height - 1)
        color = tuple(int(round(top[i] + (bottom[i] - top[i]) * t)) for i in range(3))
        draw.line([(0, y), (width, y)], fill=color + (255,))
    return image


def render_mark(size, background=True):
    """The mark as an RGBA image of size x size pixels."""
    k = CANVAS / 64.0
    scale = lambda points: [(x * k, y * k) for x, y in points]  # noqa: E731
    if background:
        mask = Image.new("L", (CANVAS, CANVAS), 0)
        ImageDraw.Draw(mask).rounded_rectangle(
            [INSET * k, INSET * k, (64 - INSET) * k, (64 - INSET) * k],
            radius=RADIUS * k,
            fill=255,
        )
        image = Image.composite(
            _gradient(CANVAS, CANVAS, BG_TOP, BG_BOTTOM),
            Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0)),
            mask,
        )
    else:
        image = Image.new("RGBA", (CANVAS, CANVAS), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    if size <= SMALL_ICON:
        for half in HALVES_SMALL:
            draw.polygon(scale(half), fill=WHITE + (255,))
        star = star_points(STAR_SMALL_CENTER, STAR_SMALL_OUTER, STAR_SMALL_INNER)
        draw.polygon(scale(star), fill=AMBER + (255,))
    else:
        for half in HALVES:
            draw.polygon(scale(half), fill=WHITE + (255,))
        star = star_points(STAR_CENTER, STAR_OUTER, STAR_INNER)
        draw.polygon(scale(star), fill=AMBER + (255,))
        for (cx, cy), r in DOTS:
            draw.ellipse(
                [(cx - r) * k, (cy - r) * k, (cx + r) * k, (cy + r) * k],
                fill=AMBER_LIGHT + (255,),
            )
    if size == CANVAS:
        return image
    return image.resize((size, size), Image.LANCZOS)


def font(path, size):
    if not os.path.isfile(path):
        sys.exit("[Fission 180] font not found: %s (install fonts-dejavu-core)" % path)
    return ImageFont.truetype(path, size)


WORD, NUMBER = "Fission", " 180"


def wordmark_size(width, largest):
    """The largest font size up to `largest` whose wordmark fits in `width` pixels."""
    size = largest
    while size > 8 and font(FONT_BOLD, size).getlength(WORD + NUMBER) > width:
        size -= 1
    return size


def wordmark(draw, x, y, size):
    """'Fission' in white, '180' in light blue. Returns the x where the text ends."""
    f = font(FONT_BOLD, size)
    draw.text((x, y), WORD, font=f, fill=TEXT)
    x += f.getlength(WORD)
    draw.text((x, y), NUMBER, font=f, fill=TEXT_ACCENT)
    return x + f.getlength(NUMBER)


def render_splash(scale=1):
    """568 x 368 (times scale). Dark, the mark on the left, the wordmark on the right, a
    lighter band at the bottom for FreeCAD's loading messages. FreeCAD paints the version
    number at (SPLASH_TEXT_X + 235, SPLASH_INFO_Y - 7) = (425, 182): the "Version" caption
    is baked in just left of that spot, on the same baseline."""
    w, h = 568 * scale, 368 * scale
    image = Image.new("RGBA", (w, h), DARK + (255,))
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 318 * scale, w, h], fill=DARK_BAND + (255,))
    draw.rectangle([0, 318 * scale, w, 320 * scale], fill=BG_BOTTOM + (255,))
    image.alpha_composite(render_mark(130 * scale), (36 * scale, 95 * scale))
    x = SPLASH_TEXT_X * scale
    size = wordmark_size((568 - SPLASH_TEXT_X - 22) * scale, 60 * scale)
    wordmark(draw, x, (150 * scale) - size, size)
    caption = font(FONT_REGULAR, 12 * scale)
    draw.text(
        ((SPLASH_TEXT_X + 235 - 6) * scale, (SPLASH_INFO_Y - 7) * scale),
        "Version",
        font=caption,
        fill=TEXT_DIM,
        anchor="rs",
    )
    draw.text((x, 200 * scale), SUBTITLE, font=font(FONT_REGULAR, 16 * scale), fill=TEXT_SOFT)
    draw.text((x, 228 * scale), BASED_ON, font=font(FONT_REGULAR, 12 * scale), fill=TEXT_DIM)
    draw.text((x, 248 * scale), REPO_URL, font=font(FONT_REGULAR, 12 * scale), fill=TEXT_DIM)
    return image


def render_about():
    """552 x 189 banner at the top of Help > About."""
    w, h = 552, 189
    image = Image.new("RGBA", (w, h), DARK + (255,))
    draw = ImageDraw.Draw(image)
    image.alpha_composite(render_mark(120), (24, 34))
    size = wordmark_size(552 - 168 - 16, 48)
    wordmark(draw, 168, 96 - size, size)
    draw.text((171, 112), SUBTITLE, font=font(FONT_REGULAR, 16), fill=TEXT_SOFT)
    draw.text((171, 140), BASED_ON, font=font(FONT_REGULAR, 12), fill=TEXT_DIM)
    draw.text((171, 158), REPO_URL, font=font(FONT_REGULAR, 12), fill=TEXT_DIM)
    return image


def render_nsis_header():
    """150 x 57, shown at the top right of every installer page."""
    image = Image.new("RGBA", (150, 57), DARK + (255,))
    draw = ImageDraw.Draw(image)
    image.alpha_composite(render_mark(44), (6, 6))
    size = wordmark_size(150 - 54 - 4, 17)
    wordmark(draw, 54, 36 - size, size)
    return image


def render_nsis_banner():
    """164 x 314, the left side of the welcome and finish pages."""
    w, h = 164, 314
    image = _gradient(w, h, DARK_BAND, DARK)
    draw = ImageDraw.Draw(image)
    image.alpha_composite(render_mark(96), (34, 40))
    size = wordmark_size(w - 14, 26)
    width = font(FONT_BOLD, size).getlength(WORD + NUMBER)
    wordmark(draw, (w - width) / 2, 176 - size, size)
    f = font(FONT_REGULAR, 12)
    for i, line in enumerate(["Parametric CAD with", "the Fusion workflow"]):
        draw.text(((w - f.getlength(line)) / 2, 192 + 18 * i), line, font=f, fill=TEXT_SOFT)
    f = font(FONT_REGULAR, 11)
    line = "based on FreeCAD"
    draw.text(((w - f.getlength(line)) / 2, 284), line, font=f, fill=TEXT_DIM)
    return image


ICO_SIZES = [16, 24, 32, 48, 64, 128, 256]
PNG_SIZES = [16, 32, 48, 64, 128, 256]


def write_ico(path):
    # Pillow drops every size larger than the first image, so the biggest goes first.
    images = [render_mark(s) for s in reversed(ICO_SIZES)]
    images[0].save(path, format="ICO", sizes=[(s, s) for s in ICO_SIZES], append_images=images[1:])


def write_bmp(image, path):
    image.convert("RGB").save(path, format="BMP")  # 24-bit, what NSIS wants


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--out", help="write everything into this folder instead of the repo")
    args = parser.parse_args(argv)

    if args.out:
        out = os.path.abspath(args.out)
        gui_icons = main_dir = wb_icons = nsis_icons = nsis_graphics = out
    else:
        gui_icons = os.path.join(REPO, "src", "Gui", "Icons")
        main_dir = os.path.join(REPO, "src", "Main")
        wb_icons = os.path.join(REPO, "src", "Mod", "Fission180", "fission180", "icons")
        nsis_icons = os.path.join(REPO, "package", "WindowsInstaller", "icons")
        nsis_graphics = os.path.join(REPO, "package", "WindowsInstaller", "graphics")
    for folder in {gui_icons, main_dir, wb_icons, nsis_icons, nsis_graphics}:
        os.makedirs(folder, exist_ok=True)

    written = []

    def save(image, path):
        image.save(path)
        written.append(path)

    svg = svg_text()
    for path in (
        os.path.join(gui_icons, "fission180app.svg"),
        os.path.join(wb_icons, "fission180.svg"),
    ):
        with open(path, "w", encoding="utf-8") as handle:
            handle.write(svg)
        written.append(path)
    for size in PNG_SIZES:
        save(render_mark(size), os.path.join(gui_icons, "fission180-icon-%d.png" % size))
    save(render_splash(1), os.path.join(gui_icons, "fission180splash.png"))
    save(render_splash(2), os.path.join(gui_icons, "fission180splash_2x.png"))
    save(render_about(), os.path.join(gui_icons, "fission180about.png"))
    for path in (
        os.path.join(main_dir, "fission180.ico"),
        os.path.join(nsis_icons, "Fission180.ico"),
    ):
        write_ico(path)
        written.append(path)
    header = os.path.join(nsis_graphics, "fission180-header.bmp")
    banner = os.path.join(nsis_graphics, "fission180-banner.bmp")
    write_bmp(render_nsis_header(), header)
    write_bmp(render_nsis_banner(), banner)
    written += [header, banner]

    for path in written:
        print("[Fission 180] wrote %s" % os.path.relpath(path, REPO if not args.out else args.out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
