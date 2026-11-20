# SPDX-License-Identifier: LGPL-2.1-or-later
"""The small navigation bar floating at the bottom centre of the 3D view: Orbit, Look At,
Pan, Zoom, Fit, Display Settings, Grid and Snaps, Viewports (ribbon_config.NAV_BAR; the
commands in orbit_ui, navigate_ui, display_ui, grid_ui, viewports_ui)."""

import FreeCADGui as Gui

from . import neon_shell_paint as neon_paint, registry, ribbon_config as cfg, ui_icon, warn
from .compat import QtCore, QtGui, QtWidgets
from .ribbon_ui import build_menu, resolve, run

_bar = None
HOLOGRAM = "Fission180Hologram"


class NavBar(QtWidgets.QWidget):
    def __init__(self, area):
        super().__init__(area)
        self.setObjectName("Fission180NavBar")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        available = registry.available_commands()
        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(4, 2, 4, 2)
        row.setSpacing(2)
        for entry in cfg.NAV_BAR:
            button = QtWidgets.QToolButton()
            button.setIcon(ui_icon(entry.get("icon")))
            button.setProperty("fission180Icon", entry.get("icon") or "")  # (theme.py redraws it)
            button.setIconSize(QtCore.QSize(20, 20))
            button.setAutoRaise(True)
            if "submenu" in entry:
                tip = entry["label"]
                if entry.get("note"):
                    tip += "\n" + entry["note"]
                button.setToolTip(tip)
                button.setPopupMode(QtWidgets.QToolButton.InstantPopup)
                button.setMenu(build_menu(button, entry["submenu"], available))
            else:
                resolved = resolve(entry["command"], available)
                tip = entry["label"] + ("  (%s)" % entry["key"] if entry.get("key") else "")
                if entry.get("note"):
                    tip += "\n" + entry["note"]
                button.setToolTip(tip)
                if resolved:
                    button.clicked.connect(lambda _=False, r=resolved, e=entry: run(r, e["label"]))
                elif not entry.get("note"):
                    button.setEnabled(False)
            row.addWidget(button)
        # Neon Lights only (design 8): a quick Hologram switch for the bodies (neon_view)
        self.hologram = QtWidgets.QToolButton()
        self.hologram.setObjectName(HOLOGRAM)
        self.hologram.setCheckable(True)
        self.hologram.setIconSize(QtCore.QSize(20, 20))
        self.hologram.setAutoRaise(True)
        self.hologram.setToolTip("Hologram\nShow the bodies as see-through holograms (Neon Lights)")
        self.hologram.clicked.connect(self._hologram_clicked)
        self.hologram.setVisible(False)
        row.addWidget(self.hologram)
        self._area = area
        area.installEventFilter(self)
        self.adjustSize()
        self.place()

    # -- Neon Lights ------------------------------------------------------------------------
    def neon_sync(self):
        """The Hologram button shows only in Neon Lights, ticked as neon_view says."""
        try:
            lit = neon_paint.on()
            if lit:
                from . import neon_view

                self.hologram.setChecked(bool(neon_view.hologram()))
                self.hologram.setIcon(_hologram_icon())
            if self.hologram.isVisibleTo(self) != lit:
                self.hologram.setVisible(lit)
                self.place()
            self.update()
        except Exception as exc:
            warn("navigation bar: Hologram button: %s" % exc)

    def _hologram_clicked(self, checked=False):
        try:
            from . import neon_view

            neon_view.set_hologram(bool(checked))
            self.hologram.setChecked(bool(neon_view.hologram()))
        except Exception as exc:
            warn("navigation bar: Hologram: %s" % exc)

    def paintEvent(self, event):
        super().paintEvent(event)
        if not neon_paint.on():
            return
        try:
            # a HUD frame: cut corners, a glowing line and bracket marks
            painter = QtGui.QPainter(self)
            try:
                painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
                rect = QtCore.QRectF(self.rect()).adjusted(1.5, 1.5, -1.5, -1.5)
                neon_paint.glow_path(
                    painter, neon_paint.chamfer_path(rect, 6), neon_paint.colour("primary_dim"), 1.0, 0.6
                )
                neon_paint.glow_path(
                    painter,
                    neon_paint.bracket_path(rect.adjusted(-0.5, -0.5, 0.5, 0.5), 7, ("tr", "bl")),
                    neon_paint.colour("primary"),
                    1.8,
                )
            finally:
                painter.end()
        except Exception as exc:
            warn("navigation bar: %s" % exc)

    def place(self):
        area = self._area
        self.adjustSize()
        x = (area.width() - self.width()) // 2
        y = area.height() - self.height() - 12
        self.move(max(0, x), max(0, y))
        self.raise_()

    def eventFilter(self, obj, event):
        if obj is self._area and event.type() in (QtCore.QEvent.Resize, QtCore.QEvent.Show):
            QtCore.QTimer.singleShot(0, self.place)
        return False


def _hologram_icon():
    """The Hologram button's picture, drawn in the palette's colours: a wireframe cube with
    scan lines (off: primary; on: secondary)."""
    icon = QtGui.QIcon()
    for state, role in ((QtGui.QIcon.Off, "primary"), (QtGui.QIcon.On, "secondary")):
        pixmap = QtGui.QPixmap(40, 40)
        pixmap.fill(QtCore.Qt.transparent)
        painter = QtGui.QPainter(pixmap)
        try:
            painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
            c = neon_paint.colour(role)
            front = QtCore.QRectF(7, 13, 20, 20)
            path = QtGui.QPainterPath()
            path.addRect(front)
            for a, b in (((7, 13), (15, 5)), ((27, 13), (35, 5)), ((27, 33), (35, 25))):
                path.moveTo(*a)
                path.lineTo(*b)
            path.moveTo(15, 5)
            path.lineTo(35, 5)
            path.lineTo(35, 25)
            neon_paint.glow_path(painter, path, c, 2.2)
            fill = QtGui.QColor(c)
            fill.setAlphaF(0.22)
            for y in range(16, 32, 4):  # scan lines across the front face
                painter.fillRect(QtCore.QRectF(9, y, 16, 1.6), fill)
        finally:
            painter.end()
        icon.addPixmap(pixmap, QtGui.QIcon.Normal, state)
    return icon


def theme_changed():
    """neon_shell_paint.theme_changed: the Hologram button and the frame follow the look."""
    if _bar is not None:
        try:
            _bar.neon_sync()
        except RuntimeError:
            pass


def bar():
    """The navigation bar widget (None before Fission 180's interface was first shown)."""
    return _bar


def show():
    global _bar
    try:
        if _bar is None:
            area = Gui.getMainWindow().findChild(QtWidgets.QMdiArea)
            if area is None:
                warn("navigation bar: no 3D view area found")
                return
            _bar = NavBar(area)
        _bar.neon_sync()
        _bar.show()
        _bar.place()
    except Exception as exc:
        warn("navigation bar: %s" % exc)
    # what the bar's menus set: display settings, the layout grid (remembered choices)
    for name in ("display_ui", "grid_ui"):
        try:
            __import__("fission180." + name, fromlist=["enable"]).enable()
        except Exception as exc:
            warn("navigation bar: %s" % exc)


def hide():
    if _bar is not None:
        _bar.hide()
    for name in ("navigate_ui", "viewports_ui", "display_ui", "grid_ui"):
        try:
            module = __import__("fission180." + name, fromlist=["disable"])
            if name == "navigate_ui":
                module.stop()
            elif name == "viewports_ui":
                module.set_layout("Single View", quiet=True)
            else:
                module.disable()
        except Exception as exc:
            warn("navigation bar: %s" % exc)
