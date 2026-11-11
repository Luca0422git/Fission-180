# SPDX-License-Identifier: LGPL-2.1-or-later
"""No dialog is ever wider or taller than the window, or partly off the screen.

The book parity report met a dialog whose OK and Cancel were at x = 2319 on a 1920 screen
(a command dialog grown by a long button text: taskui's width guard keeps those narrow).
This is the guard for the dialogs that are windows of their own (Fission 180's and FreeCAD's):
when one gets the keyboard for the first time since it was shown, it is made to fit the
main window's screen (never larger than it) and moved back inside it.
"""

import FreeCADGui as Gui

from . import log, warn
from .compat import QtCore, QtGui, QtWidgets

_state = {"on": False, "seen": {}}


def fitted(geometry, limit):
    """(x, y, width, height) of a window made to fit `limit` (x, y, width, height): no
    larger than it, and moved the least so that it lies inside. Pure numbers (unit tests)."""
    x, y, w, h = geometry
    lx, ly, lw, lh = limit
    w, h = min(w, lw), min(h, lh)
    x = min(max(x, lx), lx + lw - w)
    y = min(max(y, ly), ly + lh - h)
    return x, y, w, h


def _limit(widget):
    """The screen the dialog is on (what a person can reach), without the task bar."""
    try:
        screen = widget.screen() or Gui.getMainWindow().screen()
        area = screen.availableGeometry()
        return area.x(), area.y(), area.width(), area.height()
    except Exception:
        return None


def fit(widget):
    """Make one dialog fit. True when it was changed."""
    limit = _limit(widget)
    if limit is None:
        return False
    frame, inner = widget.frameGeometry(), widget.geometry()
    # the frame's own edges (title bar, borders) count: the buttons are at the bottom
    extra_w = max(0, frame.width() - inner.width())
    extra_h = max(0, frame.height() - inner.height())
    x, y, w, h = fitted((frame.x(), frame.y(), frame.width(), frame.height()), limit)
    if (x, y, w, h) == (frame.x(), frame.y(), frame.width(), frame.height()):
        return False
    if w != frame.width() or h != frame.height():
        widget.resize(max(1, w - extra_w), max(1, h - extra_h))
    widget.move(x, y)
    log("a dialog was brought back onto the screen: %s" % (widget.windowTitle() or "untitled"))
    return True


def _check():
    try:
        seen = _state["seen"]
        alive = {}
        for widget in QtWidgets.QApplication.topLevelWidgets():
            if not isinstance(widget, QtWidgets.QDialog) or not widget.isVisible():
                continue
            key = id(widget)
            alive[key] = True
            if key in seen:
                continue  # looked at when it came up: where a person drags it then is theirs
            fit(widget)
        _state["seen"] = alive
    except Exception as exc:
        warn("dialog fit: %s" % exc)


def _focus_changed(_window=None):
    if _state["on"]:
        QtCore.QTimer.singleShot(0, _check)


def enable():
    if _state["on"]:
        return
    try:
        QtGui.QGuiApplication.instance().focusWindowChanged.connect(_focus_changed)
        _state["on"] = True
    except Exception as exc:
        warn("dialog fit: %s" % exc)


def disable():
    if not _state["on"]:
        return
    _state["on"] = False
    try:
        QtGui.QGuiApplication.instance().focusWindowChanged.disconnect(_focus_changed)
    except Exception:
        pass
