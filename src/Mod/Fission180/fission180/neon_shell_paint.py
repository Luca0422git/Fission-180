# SPDX-License-Identifier: LGPL-2.1-or-later
"""Small painting helpers for Neon Lights' look on Fission 180's own bars (plan task B2): the
ribbon's tab underline and group brackets, the navigation bar's HUD frame, the timeline's
marker beam, the browser's selection bar and the ViewCube.

Every helper is used only while Neon Lights is on (on()); Dark and Light never reach them, so
their painting stays exactly as it was. Qt has no blur on a QPainter line: a glow is wider,
fainter copies of the line drawn under it."""

from . import theme
from .compat import QtCore, QtGui

# (extra width in px, opacity) of the copies under a glowing line, widest first
GLOW = ((6.0, 0.10), (3.5, 0.22))


def on():
    """Neon Lights is on and painting its own colours (not while a save draws the normal
    preview picture: theme.normal_look)."""
    return theme.is_neon() and theme.neon("primary", None) is not None


def colour(role, literal="#000000", alpha=None):
    """QColor of a palette role in Neon Lights (the literal otherwise)."""
    c = QtGui.QColor(theme.neon(role, literal))
    if alpha is not None:
        c.setAlphaF(max(0.0, min(1.0, alpha)))
    return c


def glow_pen(c, width, alpha=1.0, cap=None):
    pen = QtGui.QPen(QtGui.QColor(c), width)
    col = QtGui.QColor(c)
    col.setAlphaF(alpha)
    pen.setColor(col)
    pen.setCapStyle(cap if cap is not None else QtCore.Qt.FlatCap)
    pen.setJoinStyle(QtCore.Qt.MiterJoin)
    return pen


def glow_path(painter, path, c, width=1.4, strength=1.0):
    """`path` stroked in `c` with a soft glow under it."""
    painter.save()
    try:
        painter.setBrush(QtCore.Qt.NoBrush)
        for extra, alpha in GLOW:
            painter.setPen(glow_pen(c, width + extra, alpha * strength))
            painter.drawPath(path)
        painter.setPen(glow_pen(c, width))
        painter.drawPath(path)
    finally:
        painter.restore()


def glow_line(painter, a, b, c, width=1.4, strength=1.0):
    path = QtGui.QPainterPath(QtCore.QPointF(*a))
    path.lineTo(QtCore.QPointF(*b))
    glow_path(painter, path, c, width, strength)


def bracket_path(rect, arm, corners=("tl", "tr", "bl", "br")):
    """Corner brackets of a rectangle (QRectF), each arm `arm` px long."""
    path = QtGui.QPainterPath()
    x0, y0, x1, y1 = rect.left(), rect.top(), rect.right(), rect.bottom()
    for corner in corners:
        x = x0 if corner[1] == "l" else x1
        y = y0 if corner[0] == "t" else y1
        dx = arm if corner[1] == "l" else -arm
        dy = arm if corner[0] == "t" else -arm
        path.moveTo(x + dx, y)
        path.lineTo(x, y)
        path.lineTo(x, y + dy)
    return path


def side_brackets(rect, arm):
    """Two square brackets, [ at the left end of `rect` and ] at its right end."""
    path = QtGui.QPainterPath()
    x0, y0, x1, y1 = rect.left(), rect.top(), rect.right(), rect.bottom()
    path.moveTo(x0 + arm, y0)
    path.lineTo(x0, y0)
    path.lineTo(x0, y1)
    path.lineTo(x0 + arm, y1)
    path.moveTo(x1 - arm, y0)
    path.lineTo(x1, y0)
    path.lineTo(x1, y1)
    path.lineTo(x1 - arm, y1)
    return path


def chamfer_path(rect, cut, corners=("tl", "br")):
    """A closed rectangle with the given corners cut by `cut` px."""
    x0, y0, x1, y1 = rect.left(), rect.top(), rect.right(), rect.bottom()
    pts = []
    pts += [(x0, y0 + cut), (x0 + cut, y0)] if "tl" in corners else [(x0, y0)]
    pts += [(x1 - cut, y0), (x1, y0 + cut)] if "tr" in corners else [(x1, y0)]
    pts += [(x1, y1 - cut), (x1 - cut, y1)] if "br" in corners else [(x1, y1)]
    pts += [(x0 + cut, y1), (x0, y1 - cut)] if "bl" in corners else [(x0, y1)]
    path = QtGui.QPainterPath(QtCore.QPointF(*pts[0]))
    for pt in pts[1:]:
        path.lineTo(QtCore.QPointF(*pt))
    path.closeSubpath()
    return path


def display_font(pixels, bold=True):
    """The display face (Orbitron) at `pixels`; the app's font if it is not loaded."""
    from .compat import QtWidgets

    font = QtGui.QFont(QtWidgets.QApplication.font())
    try:
        from . import neon_style

        family = neon_style.fonts()[1]
        if family:
            font.setFamily(family)
    except Exception:
        pass
    font.setBold(bold)
    font.setPixelSize(max(6, int(pixels)))
    return font


_seen = {"neon": False}


def _refit_views():
    """Every maximized design window filling its area again. Neon Lights' style changes the
    height of FreeCAD's (hidden) document tab bar and of the ribbon; Qt's MDI area then moves
    its maximized window by the difference only, and after Neon -> Dark the 3D view was left
    4 px short (the model drawn 2 px higher than before: neon_switch's pictures)."""
    try:
        import FreeCADGui as Gui

        from .compat import QtWidgets

        area = Gui.getMainWindow().findChild(QtWidgets.QMdiArea)
        if area is None:
            return
        # the bars' new sizes laid out first (they come as posted layout requests)
        QtWidgets.QApplication.sendPostedEvents(None, QtCore.QEvent.LayoutRequest)
        room = area.viewport().rect()

        for sub in area.subWindowList():
            if sub.isMaximized() and sub.geometry() != room:
                sub.setGeometry(room)
    except Exception as exc:
        from . import warn

        warn("Neon Lights: design window size: %s" % exc)


def theme_changed():
    """theme.LISTENERS: after a switch of look or of Neon Lights' colours, the bars this
    task paints by hand are painted again (their style sheets follow by themselves)."""
    lit = theme.is_neon()
    if lit or _seen["neon"]:  # a switch into, inside or out of Neon Lights
        _refit_views()
        QtCore.QTimer.singleShot(0, _refit_views)  # (once the bars' new sizes are laid out)
    _seen["neon"] = lit
    for name, step in (
        ("viewcube_ui", "theme_changed"),
        ("navbar_ui", "theme_changed"),
        ("timeline_ui", "theme_changed"),
        ("ribbon_ui", "theme_changed"),
        ("browser_ui", "theme_changed"),
    ):
        try:
            module = __import__("fission180." + name, fromlist=["x"])
            getattr(module, step, lambda: None)()
        except Exception as exc:
            from . import warn

            warn("Neon Lights: %s: %s" % (name, exc))
