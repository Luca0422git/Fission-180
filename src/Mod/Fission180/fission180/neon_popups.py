# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights' pop-ups (design 6.3; plan task B1 owns this file).

- Menus, drop-down lists and tooltips are see-through dark glass when the screen can show it
  (compositing()), else solid, so no corner ever shows black.
- They open with a short animation: they fade in and unfold from 85 % to their full height in
  OPEN_MS, while a bright scan line runs once from top to bottom (SCAN_MS).
- Message boxes get their kind (property fission180Kind: info, warning, error), which the style
  sheet turns into a hazard-stripe header (warning) or a red frame (error), and a neon sign in
  place of the system's icon; an error box plays a short glitch when it appears (GLITCH_MS; off
  with the Glitch effect).

One event filter on the application, installed only while Neon Lights is on; disable() takes
everything back (no animation, overlay, property or icon is left)."""

import os
import random
import sys

from . import warn

OPEN_MS = 120
SCAN_MS = 200
GLITCH_MS = 120
START_HEIGHT = 0.85
_state = {"filter": None, "animations": {}, "translucent": [], "solid": [], "boxes": []}
_POPUP_NAMES = ("Fission180Tip", "Fission180ParameterNames")


def compositing():
    """Whether see-through windows can be shown: always on Windows and macOS; on Linux with a
    Wayland session or a desktop that composites (KDE, GNOME and the like). A plain X server
    without a compositor (a test's virtual screen, some remote desktops, X forwarded over ssh)
    shows see-through parts black, so pop-ups stay solid there. FISSION180_NEON_OPAQUE=1
    forces solid pop-ups anywhere."""
    if os.environ.get("FISSION180_NEON_OPAQUE") == "1":
        return False
    if sys.platform.startswith("win"):
        return True
    if sys.platform == "darwin":
        return True
    if os.environ.get("QT_QPA_PLATFORM", "").startswith(("offscreen", "minimal", "vnc")):
        return False
    if os.environ.get("XRDP_SESSION") or os.environ.get("VNCDESKTOP"):
        return False
    display = os.environ.get("DISPLAY", "")
    if display and not display.startswith(":") and not os.environ.get("WAYLAND_DISPLAY"):
        return False  # X forwarded from another machine (localhost:10.0 and the like)
    if os.environ.get("WAYLAND_DISPLAY") or os.environ.get("XDG_SESSION_TYPE") == "wayland":
        return True
    desktop = (os.environ.get("XDG_CURRENT_DESKTOP") or "").upper()
    return any(name in desktop for name in ("KDE", "GNOME", "CINNAMON", "BUDGIE", "PANTHEON", "DEEPIN"))


def _alive(widget):
    try:
        import shiboken6

        return shiboken6.isValid(widget)
    except ImportError:
        try:
            widget.objectName()
            return True
        except RuntimeError:
            return False


def _is_popup(widget):
    """A menu, a drop-down list, Qt's tooltip, or one of Fission 180's own pop-ups (the
    tooltip card, the parameter names list)."""
    from .compat import QtCore, QtWidgets

    if isinstance(widget, QtWidgets.QMenu):
        return True
    if not widget.isWindow():
        return False
    name = widget.metaObject().className()
    if name in ("QComboBoxPrivateContainer", "QTipLabel"):
        return True
    kind = widget.windowFlags() & QtCore.Qt.WindowType_Mask
    return kind == QtCore.Qt.ToolTip and widget.objectName() in _POPUP_NAMES


SOLID = "fission180Solid"


def see_through(widget):
    """Make a pop-up see-through if the screen can show it; whether it is.

    Qt gives a window an alpha channel only if WA_TranslucentBackground is set before its
    native window is made: set later (a menu opened in Dark, then Neon Lights switched on) the
    window has no alpha and a see-through ground shows black. Such a pop-up is marked solid
    instead (property fission180Solid, which the style sheets turn into a solid ground); it
    gets its glass at the next start."""
    from .compat import QtCore

    if not compositing():
        return False
    if widget.testAttribute(QtCore.Qt.WA_TranslucentBackground):
        return True
    if not widget.testAttribute(QtCore.Qt.WA_WState_Created):
        widget.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
        _state["translucent"].append(widget)
        return True
    if widget.property(SOLID) is not True:
        widget.setProperty(SOLID, True)
        _state["solid"].append(widget)
        style = widget.style()
        style.unpolish(widget)
        style.polish(widget)
    return False


def _make_see_through(widget):
    see_through(widget)


# -- the open animation and the scan line ---------------------------------------------------
def _ease(t):
    """OutCubic."""
    t = max(0.0, min(1.0, t)) - 1.0
    return t * t * t + 1.0


def _make_scan(popup):
    """A child widget over the pop-up that paints the scan line (never takes a click)."""
    from .compat import QtCore, QtGui, QtWidgets

    class Scan(QtWidgets.QWidget):
        def __init__(self, parent):
            super().__init__(parent)
            self.setObjectName("Fission180NeonScan")
            self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
            self.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
            self.setFocusPolicy(QtCore.Qt.NoFocus)
            self.at = 0.0
            from . import theme

            p = theme.palette()
            self.colour = QtGui.QColor(p.get("primary_hot") or p.get("primary") or "#ffffff")
            self.setGeometry(parent.rect())

        def paintEvent(self, event):
            try:
                painter = QtGui.QPainter(self)
                try:
                    y = int(self.at * (self.height() - 1))
                    for spread, alpha in ((5, 26), (3, 60), (1, 150)):
                        colour = QtGui.QColor(self.colour)
                        colour.setAlpha(alpha)
                        painter.fillRect(2, y - spread, self.width() - 4, spread * 2 + 1, colour)
                    painter.fillRect(2, y, self.width() - 4, 1, QtGui.QColor(255, 255, 255, 200))
                finally:
                    painter.end()
            except Exception as exc:
                warn("Neon Lights: scan line: %s" % exc)

    scan = Scan(popup)
    scan.show()
    scan.raise_()
    return scan


class _Opening:
    """One pop-up's opening: fade, unfold, scan line; finish() leaves it fully shown."""

    def __init__(self, popup):
        from .compat import QtCore

        self.popup = popup
        self.scan = _make_scan(popup)
        self.animation = QtCore.QVariantAnimation()
        self.animation.setDuration(SCAN_MS)
        self.animation.setStartValue(0.0)
        self.animation.setEndValue(1.0)
        self.animation.valueChanged.connect(self.step)
        self.animation.finished.connect(self.finish)
        popup.setWindowOpacity(0.0)
        self.step(0.0)
        self.animation.start()

    def step(self, value):
        from .compat import QtGui

        try:
            if not _alive(self.popup):
                self.finish()
                return
            elapsed = float(value) * SCAN_MS
            opened = _ease(elapsed / OPEN_MS)
            self.popup.setWindowOpacity(opened)
            if opened < 1.0:
                height = max(1, int(self.popup.height() * (START_HEIGHT + (1.0 - START_HEIGHT) * opened)))
                self.popup.setMask(QtGui.QRegion(0, 0, self.popup.width(), height))
            elif not self.popup.mask().isEmpty():
                self.popup.clearMask()
            if self.scan is not None and _alive(self.scan):
                self.scan.at = float(value)
                self.scan.setGeometry(self.popup.rect())
                self.scan.update()
        except Exception as exc:
            warn("Neon Lights: pop-up animation: %s" % exc)
            self.finish()

    def finish(self):
        """Fully shown: opacity 1, no mask, no scan line (also when stopped early)."""
        try:
            self.animation.stop()
        except RuntimeError:
            pass
        if _alive(self.popup):
            try:
                self.popup.setWindowOpacity(1.0)
                self.popup.clearMask()
            except RuntimeError:
                pass
        if self.scan is not None and _alive(self.scan):
            self.scan.hide()
            self.scan.deleteLater()
        self.scan = None
        _state["animations"].pop(id(self.popup), None)


def _animate(popup):
    old = _state["animations"].pop(id(popup), None)
    if old is not None:
        old.finish()
    _state["animations"][id(popup)] = _Opening(popup)


def animating():
    """How many pop-ups are opening right now (tests wait for 0)."""
    return len(_state["animations"])


# -- message boxes ----------------------------------------------------------------------------
_ICONS = ("info", "warning", "error", "question")


def _kind(box):
    """info, warning, error or question: by its icon, or the one it had before it got its
    neon sign (setIconPixmap leaves no icon)."""
    from .compat import QtWidgets

    before = box.property("fission180Sign")
    if before in _ICONS:
        return before
    icon = box.icon()
    if icon == QtWidgets.QMessageBox.Warning:
        return "warning"
    if icon == QtWidgets.QMessageBox.Critical:
        return "error"
    if icon == QtWidgets.QMessageBox.Question:
        return "question"
    if icon == QtWidgets.QMessageBox.Information:
        return "info"
    return None


def _sign(kind):
    """The neon sign picture for a message box of `kind`, or None."""
    from .compat import QtGui

    from . import neon_style

    path = neon_style.frame_paths().get("icon_" + kind)
    if not path:
        return None
    icon = QtGui.QIcon(path)
    return icon.pixmap(32, 32) if not icon.isNull() else None


def _style_box(box):
    """Name a message box's kind for the style sheet and give it the neon sign; its kind."""
    kind = _kind(box)
    style = {"question": "info", None: "info"}.get(kind, kind)
    if box.property("fission180Kind") != style:
        box.setProperty("fission180Kind", style)
        _repolish(box)
    if kind is not None:
        sign = _sign(kind)
        if sign is not None and not sign.isNull():
            box.setProperty("fission180Sign", kind)
            box.setIconPixmap(sign)
    if not any(box is other for other in _state["boxes"]):
        _state["boxes"].append(box)
    return kind


def _unstyle_box(box):
    """The box as it was: the system's icon, no kind."""
    from .compat import QtWidgets

    if not _alive(box):
        return
    kind = box.property("fission180Sign")
    if kind in _ICONS:
        box.setProperty("fission180Sign", None)
        box.setIcon(
            {
                "info": QtWidgets.QMessageBox.Information,
                "warning": QtWidgets.QMessageBox.Warning,
                "error": QtWidgets.QMessageBox.Critical,
                "question": QtWidgets.QMessageBox.Question,
            }[kind]
        )
    if box.property("fission180Kind") is not None:
        box.setProperty("fission180Kind", None)
        _repolish(box)


def _repolish(box):
    """The box and its children styled again: rules such as
    QMessageBox[fission180Kind="error"] QLabel name the box's kind, and Qt does not polish a
    child again when only its parent's property changed."""
    from .compat import QtWidgets

    style = box.style()
    style.unpolish(box)
    style.polish(box)
    for child in box.findChildren(QtWidgets.QWidget):
        child.style().unpolish(child)
        child.style().polish(child)
        child.update()


def _forget_box(box):
    """A message box that closed: its system icon back and no longer kept (if it is shown
    again, Show names it again)."""
    if any(box is other for other in _state["boxes"]):
        _unstyle_box(box)
    _state["boxes"] = [other for other in _state["boxes"] if other is not box and _alive(other)]


def boxes():
    """How many message boxes are kept for a palette change (tests)."""
    return len(_state["boxes"])


def _glitch_on():
    try:
        from . import neon_settings

        return bool(neon_settings.get("Effects")) and bool(neon_settings.get("Glitch"))
    except Exception:
        return True


def _glitch_strength():
    try:
        from . import neon_settings

        return max(0, min(100, int(neon_settings.get("GlitchStrength")))) / 100.0
    except Exception:
        return 0.5


class _Glitch:
    """A short burst over an error box: displaced bands of the error colour and a split of
    cyan/red lines, re-drawn a few times, then gone."""

    def __init__(self, box):
        from .compat import QtCore, QtGui, QtWidgets

        from . import neon_frames, theme

        p = theme.palette()
        self.box = box
        self.colours = (
            QtGui.QColor(neon_frames.error_colour(p)),
            QtGui.QColor(p.get("secondary") or "#00e5ff"),
            QtGui.QColor(p.get("primary_hot") or "#ffffff"),
        )
        self.strength = 0.4 + 0.6 * _glitch_strength()
        owner = self

        class Overlay(QtWidgets.QWidget):
            def paintEvent(self, event):
                owner.paint(self)

        self.overlay = Overlay(box)
        self.overlay.setObjectName("Fission180NeonGlitch")
        self.overlay.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.overlay.setAttribute(QtCore.Qt.WA_NoSystemBackground, True)
        self.overlay.setGeometry(box.rect())
        self.overlay.show()
        self.overlay.raise_()
        self.frame = -1
        self.animation = QtCore.QVariantAnimation()
        self.animation.setDuration(GLITCH_MS)
        self.animation.setStartValue(0)
        self.animation.setEndValue(4)
        self.animation.valueChanged.connect(self.step)
        self.animation.finished.connect(self.finish)
        self.animation.start()

    def step(self, value):
        try:
            frame = int(value)
            if frame != self.frame and self.overlay is not None and _alive(self.overlay):
                self.frame = frame
                self.overlay.setGeometry(self.box.rect())
                self.overlay.update()
        except Exception as exc:
            warn("Neon Lights: glitch: %s" % exc)
            self.finish()

    def paint(self, widget):
        from .compat import QtGui

        try:
            if self.frame >= 4:
                return
            rnd = random.Random(self.frame * 7919 + 17)
            painter = QtGui.QPainter(widget)
            try:
                w, h = widget.width(), widget.height()
                for _ in range(3 + rnd.randint(0, 3)):
                    colour = QtGui.QColor(rnd.choice(self.colours))
                    colour.setAlpha(int(rnd.randint(40, 110) * self.strength))
                    y = rnd.randint(0, max(0, h - 4))
                    band = rnd.randint(2, max(3, h // 10))
                    shift = rnd.randint(-w // 8, w // 8)
                    painter.fillRect(max(0, shift), y, w - abs(shift), band, colour)
                for _ in range(2):
                    colour = QtGui.QColor(rnd.choice(self.colours[:2]))
                    colour.setAlpha(int(170 * self.strength))
                    painter.fillRect(0, rnd.randint(0, max(0, h - 1)), w, 1, colour)
            finally:
                painter.end()
        except Exception as exc:
            warn("Neon Lights: glitch: %s" % exc)

    def finish(self):
        try:
            self.animation.stop()
        except RuntimeError:
            pass
        if self.overlay is not None and _alive(self.overlay):
            self.overlay.hide()
            self.overlay.deleteLater()
        self.overlay = None
        _state["animations"].pop(("glitch", id(self.box)), None)


def _glitch(box):
    old = _state["animations"].pop(("glitch", id(box)), None)
    if old is not None:
        old.finish()
    _state["animations"][("glitch", id(box))] = _Glitch(box)


# -- the filter -------------------------------------------------------------------------------
def _make_filter():
    from .compat import QtCore, QtWidgets

    class PopupFilter(QtCore.QObject):
        def eventFilter(self, obj, event):
            try:
                kind = event.type()
                if kind == QtCore.QEvent.Hide and isinstance(obj, QtWidgets.QMessageBox):
                    if not event.spontaneous():
                        _forget_box(obj)
                    return False
                if kind not in (QtCore.QEvent.Polish, QtCore.QEvent.Show) or not obj.isWidgetType():
                    return False
                if _is_popup(obj):
                    _make_see_through(obj)
                    if kind == QtCore.QEvent.Show:
                        _animate(obj)
                elif kind == QtCore.QEvent.Show and isinstance(obj, QtWidgets.QMessageBox):
                    if _style_box(obj) == "error" and _glitch_on():
                        _glitch(obj)
            except Exception as exc:  # never break a menu
                warn("Neon Lights: pop-up: %s" % exc)
            return False

    return PopupFilter()


def enable():
    from .compat import QtWidgets

    if _state["filter"] is None:
        _state["filter"] = _make_filter()
        QtWidgets.QApplication.instance().installEventFilter(_state["filter"])
    # pop-ups made before Neon Lights was switched on: see-through if their window does not
    # exist yet, else marked solid (see_through())
    for widget in QtWidgets.QApplication.allWidgets():
        try:
            if _is_popup(widget):
                see_through(widget)
        except Exception as exc:
            warn("Neon Lights: pop-up: %s" % exc)


def disable():
    from .compat import QtWidgets

    if _state["filter"] is not None:
        QtWidgets.QApplication.instance().removeEventFilter(_state["filter"])
        _state["filter"] = None
    for job in list(_state["animations"].values()):
        try:
            job.finish()
        except RuntimeError:
            pass
    _state["animations"].clear()
    for box in _state["boxes"]:
        try:
            _unstyle_box(box)
        except RuntimeError:
            pass
    _state["boxes"] = []
    for widget in _state["solid"]:
        try:
            if _alive(widget):
                widget.setProperty(SOLID, None)
        except RuntimeError:
            pass
    _state["solid"] = []
    # Pop-ups made see-through stay so (Qt takes the attribute only before a window is
    # made); Dark and Light paint their whole ground, so it shows nothing there.
    _state["translucent"] = []


def refresh():
    """New colours: open message boxes get their sign in them."""
    for box in list(_state["boxes"]):
        try:
            if _alive(box) and box.isVisible():
                _style_box(box)
        except Exception as exc:
            warn("Neon Lights: message box: %s" % exc)
    _state["boxes"] = [box for box in _state["boxes"] if _alive(box)]
