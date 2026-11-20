# SPDX-License-Identifier: LGPL-2.1-or-later
"""Neon Lights' pop-ups (design 6.3): menus, drop-down lists and tooltips are see-through dark
glass (when the screen can show that) and open with a short animation. One event filter on
the application, installed only while Neon Lights is on (plan task B1 owns this file)."""

import os
import sys

from . import warn

DURATION_MS = 120
_state = {"filter": None, "animations": {}}


def compositing():
    """Whether see-through windows can be shown: always on Windows; on Linux with a Wayland
    session or a desktop that composites (KDE, GNOME and the like). A plain X server without a
    compositor (a test's virtual screen, some remote desktops) shows see-through parts black,
    so pop-ups stay solid there."""
    if os.environ.get("FISSION180_NEON_OPAQUE") == "1":
        return False
    if sys.platform.startswith("win"):
        return True
    if sys.platform == "darwin":
        return True
    if os.environ.get("WAYLAND_DISPLAY") or os.environ.get("XDG_SESSION_TYPE") == "wayland":
        return True
    desktop = (os.environ.get("XDG_CURRENT_DESKTOP") or "").upper()
    return any(name in desktop for name in ("KDE", "GNOME", "CINNAMON", "BUDGIE", "PANTHEON", "DEEPIN"))


def _is_popup(widget):
    from .compat import QtCore, QtWidgets

    if isinstance(widget, QtWidgets.QMenu):
        return True
    if not widget.isWindow():
        return False
    kind = widget.windowFlags() & QtCore.Qt.WindowType_Mask
    if kind == QtCore.Qt.ToolTip:
        return True
    return widget.metaObject().className() == "QComboBoxPrivateContainer"


def _animate(widget):
    from .compat import QtCore

    old = _state["animations"].pop(id(widget), None)
    if old is not None:
        try:
            old.stop()
        except RuntimeError:
            pass
    fade = QtCore.QPropertyAnimation(widget, b"windowOpacity", widget)
    fade.setDuration(DURATION_MS)
    fade.setStartValue(0.0)
    fade.setEndValue(1.0)
    fade.setEasingCurve(QtCore.QEasingCurve.OutCubic)
    _state["animations"][id(widget)] = fade
    fade.finished.connect(lambda key=id(widget): _state["animations"].pop(key, None))
    widget.setWindowOpacity(0.0)
    fade.start()


def _make_filter():
    from .compat import QtCore

    class PopupFilter(QtCore.QObject):
        def eventFilter(self, obj, event):
            try:
                kind = event.type()
                if kind == QtCore.QEvent.Polish and obj.isWidgetType() and _is_popup(obj):
                    if compositing():
                        obj.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
                elif kind == QtCore.QEvent.Show and obj.isWidgetType() and _is_popup(obj):
                    if compositing() and not obj.testAttribute(QtCore.Qt.WA_TranslucentBackground):
                        obj.setAttribute(QtCore.Qt.WA_TranslucentBackground, True)
                    _animate(obj)
            except Exception as exc:  # never break a menu
                warn("Neon Lights: pop-up: %s" % exc)
            return False

    return PopupFilter()


def enable():
    from .compat import QtWidgets

    if _state["filter"] is None:
        _state["filter"] = _make_filter()
        QtWidgets.QApplication.instance().installEventFilter(_state["filter"])


def disable():
    from .compat import QtWidgets

    if _state["filter"] is not None:
        QtWidgets.QApplication.instance().removeEventFilter(_state["filter"])
        _state["filter"] = None
    for fade in list(_state["animations"].values()):
        try:
            fade.stop()
            fade.targetObject().setWindowOpacity(1.0)
        except RuntimeError:
            pass
    _state["animations"].clear()


def refresh():
    pass
