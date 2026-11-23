# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fission 180's own title bar (Luca, 2026-11-23: "on my laptop screen where there is less real
estate, That top bar that says Fission 180 with the minimize and close button is kinda
annoying. Is there a way to integrate the top bar into the program? for both windows and
linux"). Like Fusion's window: the system draws no title bar; Fission 180's top row (the
quick-access buttons and the document tabs) is the title bar:

* minimize, maximize / restore and close at its right end, after the profile button;
* a press on an empty part of it moves the window, by the system's own move
  (QWindow.startSystemMove: snapping to the screen's edges on Windows and Linux, a maximized
  window comes back to its size when dragged); a double-click maximizes and restores;
* without the system's frame the window has no resize border: thin grips line its edges
  and corners (titlebar_core.grips) and start the system's own resize; not while maximized.

Preferences > General > Appearance > Title bar: Fission 180's (the default) or the system's.
Switching Fission 180's interface off gives the system's title bar back. The window keeps its
title (the taskbar shows it). Never lets an exception out of an event filter.
"""

import FreeCAD as App

from . import log, warn
from . import titlebar_core as core
from .compat import QtCore, QtGui, QtWidgets

PARAMS = "User parameter:BaseApp/Preferences/Mod/Fission180/Preferences"  # prefs_core.PREFS
KEY = "TitleBar"
BUTTON = 30  # px: the window buttons' width (the row's height decides theirs)

_state = {
    "on": False,
    "controls": None,
    "grips": [],
    "watcher": None,
    "drag": None,
    "closing": False,  # the window is closing: its frame is left alone
    "quit_hook": False,
}


def mode():
    try:
        return core.mode_of(App.ParamGet(PARAMS).GetString(KEY, core.DEFAULT_MODE))
    except Exception:
        return core.DEFAULT_MODE


def wanted():
    return _state["on"] and mode() == core.OWN


def _main():
    try:
        import FreeCADGui as Gui

        return Gui.getMainWindow()
    except Exception:
        return None


def _row():
    """Fission 180's top row (the ribbon's application bar), or None."""
    mw = _main()
    profile = mw.findChild(QtWidgets.QToolButton, "Fission180Profile") if mw is not None else None
    return profile.parentWidget() if profile is not None else None


# -- what the buttons and grips do (tests replace these) -----------------------------------
def _system_move(window):
    handle = window.windowHandle()
    return bool(handle is not None and handle.startSystemMove())


def _system_resize(window, edges):
    handle = window.windowHandle()
    return bool(handle is not None and handle.startSystemResize(edges))


def _minimize(window):
    window.showMinimized()


def _close(window):
    window.close()  # (FreeCAD asks about unsaved designs, as with the system's close)


def _toggle_maximize(window):
    if window.windowState() & QtCore.Qt.WindowMaximized:
        window.showNormal()
    else:
        window.showMaximized()


# -- the buttons ---------------------------------------------------------------------------
def _glyph(kind, colour, size=16, ratio=2.0):
    """The button's picture, drawn (no file): a line, a square, two squares or a cross."""
    px = QtGui.QPixmap(int(size * ratio), int(size * ratio))
    px.setDevicePixelRatio(ratio)
    px.fill(QtCore.Qt.transparent)
    p = QtGui.QPainter(px)
    p.setRenderHint(QtGui.QPainter.Antialiasing, True)
    pen = QtGui.QPen(colour)
    pen.setWidthF(1.2)
    p.setPen(pen)
    a, b = 4.0, size - 4.0
    if kind == "minimize":
        p.drawLine(QtCore.QPointF(a, size / 2.0 + 0.5), QtCore.QPointF(b, size / 2.0 + 0.5))
    elif kind == "maximize":
        p.drawRect(QtCore.QRectF(a + 0.5, a + 0.5, b - a - 1, b - a - 1))
    elif kind == "restore":
        p.drawRect(QtCore.QRectF(a + 0.5, a + 2.5, b - a - 3, b - a - 3))
        p.drawPolyline(
            [QtCore.QPointF(a + 2.5, a + 2.5), QtCore.QPointF(a + 2.5, a + 0.5),
             QtCore.QPointF(b - 0.5, a + 0.5), QtCore.QPointF(b - 0.5, b - 2.5),
             QtCore.QPointF(b - 2.5, b - 2.5)]
        )  # fmt: skip
    else:  # close
        p.drawLine(QtCore.QPointF(a, a), QtCore.QPointF(b, b))
        p.drawLine(QtCore.QPointF(a, b), QtCore.QPointF(b, a))
    p.end()
    return QtGui.QIcon(px)


CLOSE_RED = (232, 17, 35)  # Windows' red behind close while the mouse is on it


class _CloseButton(QtWidgets.QToolButton):
    """Close: red with a white cross while the mouse is on it (painted here, not by a style
    sheet: Dark and Light stay exactly as they were, theme_identity)."""

    def paintEvent(self, event):
        try:
            if self.isEnabled() and self.underMouse():
                p = QtGui.QPainter(self)
                p.fillRect(self.rect(), QtGui.QColor(*CLOSE_RED))
                size = self.iconSize()
                x = (self.width() - size.width()) // 2
                y = (self.height() - size.height()) // 2
                _glyph("close", QtGui.QColor(255, 255, 255)).paint(p, x, y, size.width(), size.height())
                p.end()
                return
        except Exception as exc:
            warn("title bar: %s" % exc)
        super().paintEvent(event)


class WindowButtons(QtWidgets.QWidget):
    """Minimize, maximize / restore and close, for the end of the top row."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Fission180WindowButtons")
        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(6, 0, 0, 0)
        row.setSpacing(0)
        self.buttons = {}
        for name, tip, act in (
            ("Minimize", "Minimize", lambda: _minimize(_main())),
            ("Maximize", "Maximize", lambda: _toggle_maximize(_main())),
            ("Close", "Close", lambda: _close(_main())),
        ):
            b = (_CloseButton if name == "Close" else QtWidgets.QToolButton)(self)
            b.setObjectName("Fission180Window" + name)
            b.setAutoRaise(True)
            b.setToolTip(tip)
            b.setFixedWidth(BUTTON)
            b.setIconSize(QtCore.QSize(16, 16))
            b.setFocusPolicy(QtCore.Qt.NoFocus)
            b.clicked.connect(lambda _=False, f=act: self._run(f))
            row.addWidget(b)
            self.buttons[name] = b
        self.refresh()

    def fit(self, reference):
        """As tall as the row's other buttons (`reference`: the profile button), so the row
        keeps its height and nothing below it moves."""
        try:
            height = reference.sizeHint().height()
            for b in self.buttons.values():
                b.setFixedHeight(height)
            self.setFixedHeight(height)
        except Exception as exc:
            warn("title bar: %s" % exc)

    @staticmethod
    def _run(fn):
        try:
            fn()
        except Exception as exc:
            warn("title bar: %s" % exc)

    def refresh(self):
        """The pictures in the look's text colour; maximize or restore as the window is."""
        if _state["closing"]:
            return
        try:
            colour = self.palette().color(QtGui.QPalette.ButtonText)
            mw = _main()
            big = mw is not None and bool(mw.windowState() & QtCore.Qt.WindowMaximized)
            self.buttons["Minimize"].setIcon(_glyph("minimize", colour))
            self.buttons["Maximize"].setIcon(_glyph("restore" if big else "maximize", colour))
            self.buttons["Maximize"].setToolTip("Restore Down" if big else "Maximize")
            self.buttons["Close"].setIcon(_glyph("close", colour))
        except Exception as exc:
            warn("title bar: %s" % exc)

    def changeEvent(self, event):
        try:
            # (not while the window closes: FreeCAD's teardown changes palettes of widgets
            # whose main window is already gone, and asking it for its state crashed FreeCAD)
            if not _state["closing"] and event.type() in (
                QtCore.QEvent.PaletteChange,
                QtCore.QEvent.StyleChange,
            ):
                self.refresh()
        except Exception as exc:
            warn("title bar: %s" % exc)
        super().changeEvent(event)


# -- the grips -------------------------------------------------------------------------------
CURSORS = {
    "top": QtCore.Qt.SizeVerCursor,
    "bottom": QtCore.Qt.SizeVerCursor,
    "left": QtCore.Qt.SizeHorCursor,
    "right": QtCore.Qt.SizeHorCursor,
    "top_left": QtCore.Qt.SizeFDiagCursor,
    "bottom_right": QtCore.Qt.SizeFDiagCursor,
    "top_right": QtCore.Qt.SizeBDiagCursor,
    "bottom_left": QtCore.Qt.SizeBDiagCursor,
}
QT_EDGES = {
    "top": QtCore.Qt.TopEdge,
    "bottom": QtCore.Qt.BottomEdge,
    "left": QtCore.Qt.LeftEdge,
    "right": QtCore.Qt.RightEdge,
}


class Grip(QtWidgets.QWidget):
    """An invisible band at an edge (or a corner) of the window that resizes it."""

    def __init__(self, name, parent):
        super().__init__(parent)
        self.name = name
        self.setObjectName("Fission180ResizeGrip")
        self.setProperty("fission180Edge", name)
        self.setCursor(CURSORS[name])
        edges = QtCore.Qt.Edges()
        for edge in core.EDGES[name]:
            edges |= QT_EDGES[edge]
        self.edges = edges

    def mousePressEvent(self, event):
        try:
            if event.button() == QtCore.Qt.LeftButton:
                _system_resize(self.window(), self.edges)
                event.accept()
                return
        except Exception as exc:
            warn("title bar: resize: %s" % exc)
        super().mousePressEvent(event)


def _place_grips():
    mw = _main()
    grips = _state["grips"]
    if mw is None or not grips:
        return
    full = bool(mw.windowState() & (QtCore.Qt.WindowMaximized | QtCore.Qt.WindowFullScreen))
    show = wanted() and not full
    rects = core.grips(mw.width(), mw.height())
    for grip in grips:
        try:
            if show:
                grip.setGeometry(*rects[grip.name])
                grip.raise_()
            grip.setVisible(show)
        except RuntimeError:
            pass


# -- the top row: move and maximize ---------------------------------------------------------
class _Watcher(QtCore.QObject):
    """On the main window: its size and state (the grips, the maximize button). On the top
    row: a press on an empty part moves the window, a double-click maximizes / restores."""

    def eventFilter(self, obj, event):
        try:
            kind = event.type()
            mw = _main()
            if obj is mw:
                if kind == QtCore.QEvent.Close:
                    # (shell's close guard switches Fission 180 off next: the frame is not
                    # given back to a window that is going away; enable() clears this when
                    # the close was cancelled)
                    _state["closing"] = True
                if kind in (QtCore.QEvent.Resize, QtCore.QEvent.WindowStateChange, QtCore.QEvent.Show):
                    _place_grips()
                    controls = _state["controls"]
                    if controls is not None and kind == QtCore.QEvent.WindowStateChange:
                        controls.refresh()
                return False
            if not wanted() or obj is not _row():
                return False
            if kind == QtCore.QEvent.MouseButtonDblClick and event.button() == QtCore.Qt.LeftButton:
                _state["drag"] = None
                _toggle_maximize(mw)
                return True
            if kind == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.LeftButton:
                if _system_move(mw):
                    _state["drag"] = None
                else:  # (no system move here: the window follows the mouse itself)
                    _state["drag"] = event.globalPosition().toPoint() - mw.frameGeometry().topLeft()
                return True
            if kind == QtCore.QEvent.MouseMove and _state["drag"] is not None:
                if event.buttons() & QtCore.Qt.LeftButton:
                    mw.move(event.globalPosition().toPoint() - _state["drag"])
                    return True
                _state["drag"] = None
            if kind == QtCore.QEvent.MouseButtonRelease:
                _state["drag"] = None
        except Exception as exc:
            warn("title bar: %s" % exc)
        return False


# -- turning it on and off --------------------------------------------------------------------
def _alive(widget):
    try:
        import shiboken6

        return shiboken6.isValid(widget)
    except Exception:
        return False



def _frameless(mw, on):
    """The system's title bar off (on) or back (not on); the window keeps its place, its size
    and whether it is maximized (changing the flag makes Qt hide it: shown again at once)."""
    has = bool(mw.windowFlags() & QtCore.Qt.FramelessWindowHint)
    if has == on:
        return False
    state = mw.windowState()
    geometry = mw.geometry()
    visible = mw.isVisible()
    mw.setWindowFlag(QtCore.Qt.FramelessWindowHint, on)
    if visible:
        if state & (QtCore.Qt.WindowMaximized | QtCore.Qt.WindowFullScreen):
            mw.setWindowState(state)
        else:
            mw.setGeometry(geometry)
        mw.show()
    # (a new window flag polishes the window again, and Qt gives the ribbon's tool bar its
    # style margin back: everything sat 4 px lower and further right, as after a look switch)
    _no_bar_margins()
    QtCore.QTimer.singleShot(0, _no_bar_margins)
    log("title bar: %s" % ("Fission 180's" if on else "the system's"))
    return True


def _no_bar_margins():
    try:
        from . import shell

        shell._ribbon_bar_margins()
    except Exception as exc:
        warn("title bar: %s" % exc)


def apply():
    """The title bar as the preference and Fission 180's interface want it."""
    mw = _main()
    if mw is None:
        return
    want = wanted()
    try:
        if want and _state["watcher"] is None:
            _state["watcher"] = _Watcher()
            mw.installEventFilter(_state["watcher"])
        row = _row()
        controls = _state["controls"]
        if controls is not None and (not _alive(controls) or controls.parentWidget() is not row):
            controls = _state["controls"] = None  # (the ribbon was made again: a new row)
        if want and controls is None and row is not None and row.layout() is not None:
            _state["controls"] = WindowButtons(row)
            _state["controls"].fit(row.findChild(QtWidgets.QToolButton, "Fission180Profile"))
            row.layout().addWidget(_state["controls"])
        if row is not None and _state["watcher"] is not None:
            row.removeEventFilter(_state["watcher"])
            if want:
                row.installEventFilter(_state["watcher"])
        if _state["controls"] is not None:
            _state["controls"].setVisible(want)
        if row is not None and row.layout() is not None:
            # (close flush with the window's right edge, as on a system title bar)
            m = row.layout().contentsMargins()
            row.layout().setContentsMargins(m.left(), m.top(), 0 if want else m.left(), m.bottom())
        if want and not _state["grips"]:
            _state["grips"] = [Grip(name, mw) for name in core.EDGES]
        if want or not _state["closing"]:
            _frameless(mw, want)
        _place_grips()
        if _state["controls"] is not None:
            _state["controls"].refresh()
    except Exception as exc:
        warn("title bar: %s" % exc)


def _quitting():
    """Qt's aboutToQuit: the watcher off the window before FreeCAD destroys it (a Python event
    filter called while the window was being destroyed crashed FreeCAD at every exit)."""
    try:
        _state["closing"] = True
        watcher = _state["watcher"]
        if watcher is None:
            return
        mw = _main()
        row = _row()
        for widget in (mw, row):
            if widget is not None and _alive(widget):
                widget.removeEventFilter(watcher)
        _state["watcher"] = None
    except Exception as exc:
        warn("title bar: %s" % exc)


def enable():
    """Fission 180's interface on: its own title bar, unless Preferences say the system's."""
    _state["on"] = True
    _state["closing"] = False
    if not _state["quit_hook"]:
        try:
            QtWidgets.QApplication.instance().aboutToQuit.connect(_quitting)
            _state["quit_hook"] = True
        except Exception as exc:
            warn("title bar: %s" % exc)
    apply()


def disable():
    """Fission 180's interface off: the system's title bar."""
    _state["on"] = False
    apply()
