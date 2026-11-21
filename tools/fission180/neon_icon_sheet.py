#!/usr/bin/env python3
# SPDX-License-Identifier: LGPL-2.1-or-later
"""Contact sheet of the Neon Lights icons in a preset (for reviewing them by eye):

    <freecad python> tools/fission180/neon_icon_sheet.py OUT.png [preset] [size] [names...]

Draws every icon of fission180/icons/neon/ (or the named ones, normal beside neon) on the
preset's ground with QtSvg, without a window."""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
MODULE = os.path.normpath(os.path.join(HERE, "..", "..", "src", "Mod", "Fission180"))
sys.path.insert(0, MODULE)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def main(argv):
    from PySide6 import QtCore, QtGui, QtSvg, QtWidgets

    from fission180 import neon_icons, neon_palette

    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication([])  # noqa: F841
    out = argv[0]
    preset = argv[1] if len(argv) > 1 else "v"
    size = int(argv[2]) if len(argv) > 2 else 36
    names = argv[3:]
    p = neon_palette.derive(neon_palette.roles(preset))
    pairs = bool(names)
    if not names:
        names = sorted(n[:-4] for n in os.listdir(neon_icons.NEON) if n.endswith(".svg"))
    cell = size + 10
    columns = 8 if pairs else 24
    per = 2 if pairs else 1
    rows = (len(names) + columns - 1) // columns
    image = QtGui.QImage(columns * cell * per, rows * cell, QtGui.QImage.Format_ARGB32)
    image.fill(QtGui.QColor(p["chrome"]))
    painter = QtGui.QPainter(image)
    for index, name in enumerate(names):
        x0 = (index % columns) * cell * per
        y0 = (index // columns) * cell
        sources = []
        if pairs:
            with open(os.path.join(neon_icons.UI, name + ".svg"), encoding="utf-8") as handle:
                sources.append(handle.read())
        with open(os.path.join(neon_icons.NEON, name + ".svg"), encoding="utf-8") as handle:
            sources.append(neon_icons.recolour(handle.read(), p))
        for k, text in enumerate(sources):
            renderer = QtSvg.QSvgRenderer(QtCore.QByteArray(text.encode("utf-8")))
            renderer.render(painter, QtCore.QRectF(x0 + k * cell + 5, y0 + 5, size, size))
    painter.end()
    image.save(out)
    print("[Fission 180] %d icons -> %s" % (len(names), out))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
