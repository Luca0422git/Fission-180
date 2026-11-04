# SPDX-License-Identifier: LGPL-2.1-or-later
"""The pointer of Fission 180's own sketch tools: the crosshair with the tool's picture
beside it (Luca, 2026-11-04: "the sketch tools should show a little icon next to the
cursor. they just dont. the cut tool doesnt have one").

Fusion shows the tool's picture next to the pointer while a sketch tool runs (Trim: the
scissors). FreeCAD's own sketch tools do the same with their pointer pictures
(Gui/ToolHandler.cpp, setCrosshairCursor: a 32 x 32 picture, the crosshair's centre at
8, 8, the symbol bottom right). Fission 180's own tools (sketch_draw.DrawTool: Trim, Extend,
Break, Fillet, Chamfer, Offset, the circles, slots, conic, constraints that pick two
curves...) only had Qt's bare cross. Now they draw the same layout with their own ribbon
picture (Fission 180's artwork, light or dark with the look), the crosshair in FreeCAD's
colour (Preferences > Display > Cursor crosshair colour).

Each cursor made here is remembered (its picture's cache key), so a tool can tell its
own pointer from a FreeCAD tool's picture pointer (is_own): a FreeCAD tool started while
a Fission 180 tool ran takes the view over (sketch_draw.DrawTool._taken_over)."""

from . import ui_icon_path, warn
from .compat import QtCore, QtGui, QtWidgets

SIZE = 32  # the pointer in screen points, as FreeCAD's
HOT = 8  # the crosshair's centre (FreeCAD: "hot spot of all SVG icons should be 8,8")
CANVAS = 64.0  # drawn on a 64 x 64 grid, as FreeCAD's pointer pictures are
ICON_BOX = (27.0, 27.0, 36.0, 36.0)  # the picture: bottom right (x, y, w, h on the grid)

_cache = {}  # (icon file, ratio, colour) -> QCursor
_keys = set()  # cache keys of the pictures of the cursors made here
_icons = {}  # command -> ribbon icon name


def icon_for(command):
    """The ribbon picture's name of a Fission 180 command (ribbon_config), or ""."""
    if not command:
        return ""
    if not _icons:
        try:
            from . import ribbon_config

            def walk(items):
                for entry in items:
                    if not isinstance(entry, dict):
                        continue
                    if "submenu" in entry:
                        walk(entry["submenu"])
                        continue
                    names = entry.get("command")
                    names = names if isinstance(names, (tuple, list)) else (names,)
                    for name in names:
                        if name and entry.get("icon"):
                            _icons.setdefault(name, entry["icon"])

            for value in vars(ribbon_config).values():
                if isinstance(value, dict) and isinstance(value.get("items"), list):
                    walk(value["items"])
        except Exception as exc:
            warn("sketch cursor: %s" % exc)
    return _icons.get(command, "")


def crosshair_colour():
    """FreeCAD's crosshair colour (View/CursorCrosshairColor, RGBA; white by default)."""
    try:
        import FreeCAD as App

        value = App.ParamGet("User parameter:BaseApp/Preferences/View").GetUnsigned(
            "CursorCrosshairColor", 0xFFFFFFFF
        )
        return QtGui.QColor((value >> 24) & 0xFF, (value >> 16) & 0xFF, (value >> 8) & 0xFF)
    except Exception:
        return QtGui.QColor(255, 255, 255)


def _render_icon(path, size_px):
    """The SVG at `path` as a size_px square image (None when it cannot be read)."""
    try:
        from PySide import QtSvg
    except Exception:
        try:
            from PySide6 import QtSvg
        except Exception:
            QtSvg = None
    image = QtGui.QImage(size_px, size_px, QtGui.QImage.Format_ARGB32_Premultiplied)
    image.fill(QtCore.Qt.transparent)
    if QtSvg is not None:
        renderer = QtSvg.QSvgRenderer(path)
        if not renderer.isValid():
            return None
        painter = QtGui.QPainter(image)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        renderer.render(painter, QtCore.QRectF(0, 0, size_px, size_px))
        painter.end()
        return image
    icon = QtGui.QIcon(path)
    if icon.isNull():
        return None
    painter = QtGui.QPainter(image)
    icon.paint(painter, QtCore.QRect(0, 0, size_px, size_px))
    painter.end()
    return image


def _shadow(image):
    """A dark copy of the picture's shape (it keeps a light picture readable on a light
    face of the part, and a dark one on the dark background)."""
    shade = QtGui.QImage(image.size(), QtGui.QImage.Format_ARGB32_Premultiplied)
    shade.fill(QtCore.Qt.transparent)
    painter = QtGui.QPainter(shade)
    painter.drawImage(0, 0, image)
    painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceIn)
    painter.fillRect(shade.rect(), QtGui.QColor(0, 0, 0, 170))
    painter.end()
    return shade


def picture(icon_path, ratio, colour):
    """The pointer's picture (a QPixmap of SIZE points at `ratio` device pixels each)."""
    px = max(1, int(round(SIZE * ratio)))
    scale = px / CANVAS
    pixmap = QtGui.QPixmap(px, px)
    pixmap.fill(QtCore.Qt.transparent)
    painter = QtGui.QPainter(pixmap)
    painter.setRenderHint(QtGui.QPainter.Antialiasing)
    # FreeCAD's crosshair (its pointer pictures: "m16,3v9m0,8v9m-13-13h9m8,0h9", 2.5 wide)
    pen = QtGui.QPen(colour, 2.5 * scale)
    pen.setCapStyle(QtCore.Qt.RoundCap)
    painter.setPen(pen)
    for x1, y1, x2, y2 in ((16, 3, 16, 12), (16, 20, 16, 29), (3, 16, 12, 16), (20, 16, 29, 16)):
        painter.drawLine(QtCore.QPointF(x1 * scale, y1 * scale), QtCore.QPointF(x2 * scale, y2 * scale))
    if icon_path:
        x, y, w, h = (v * scale for v in ICON_BOX)
        image = _render_icon(icon_path, max(1, int(round(w))))
        if image is not None:
            offset = max(1.0, scale)
            painter.drawImage(QtCore.QPointF(x + offset, y + offset), _shadow(image))
            painter.drawImage(QtCore.QPointF(x, y), image)
    painter.end()
    pixmap.setDevicePixelRatio(ratio)
    return pixmap


def cursor_for(command, widget=None):
    """The pointer for the tool of `command` on `widget` (its screen's pixel ratio); a
    plain crosshair picture when the command has no ribbon picture."""
    try:
        ratio = float(widget.devicePixelRatioF()) if widget is not None else 1.0
    except Exception:
        ratio = 1.0
    name = icon_for(command)
    path = ui_icon_path(name) if name else ""
    colour = crosshair_colour()
    key = (path, ratio, colour.rgb())
    cursor = _cache.get(key)
    if cursor is None:
        pixmap = picture(path, ratio, colour)
        hot = HOT
        try:
            app = QtWidgets.QApplication.instance()
            if app is not None and app.platformName() == "xcb":
                hot = int(round(HOT * ratio))  # as FreeCAD does on Linux (X11)
        except Exception:
            pass
        cursor = QtGui.QCursor(pixmap, hot, hot)
        _cache[key] = cursor
        _keys.add(pixmap.cacheKey())
        try:
            _keys.add(cursor.pixmap().cacheKey())
        except Exception:
            pass
    return cursor


def is_own(cursor):
    """The pointer is one of Fission 180's tools' (or Qt's cross they used before)."""
    try:
        shape = cursor.shape()
        if shape == QtCore.Qt.CrossCursor:
            return True
        if shape != QtCore.Qt.BitmapCursor:
            return False
        return cursor.pixmap().cacheKey() in _keys
    except Exception:
        return False


def forget():
    """The look or the crosshair colour changed: the pointers are drawn again."""
    _cache.clear()
