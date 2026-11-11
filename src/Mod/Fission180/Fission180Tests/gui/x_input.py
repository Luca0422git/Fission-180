# SPDX-License-Identifier: LGPL-2.1-or-later
"""Input through the X server itself (the XTEST extension), for the places where a click
Qt's test library sends differs from the one a person's mouse makes: the keys held during
a click (Ctrl, Shift), a double-click, a press that turns into a drag.

QtTest hands an event to one widget with the modifiers written into it. A real mouse goes
X server -> Qt's xcb plugin -> QGuiApplication, which works out the double-click, the
buttons held and the keyboard's modifiers by itself (`QGuiApplication.keyboardModifiers()`
is then true as well, which code may ask instead of the event). The book parity report
(2026-11-10) found three behaviours that only showed with such input: Ctrl+click in a
sketch, the double-click chain, the Line tool's press-and-drag arc.

Linux / X11 only (the GUI tests run under Xvfb everywhere). `available()` says whether the
extension could be loaded; a scenario that needs it fails its first check when not."""

import ctypes
import ctypes.util
import time

from PySide import QtCore, QtGui, QtWidgets

from Fission180Tests.gui import harness as h

_x11 = None
_xtst = None
_display = None

KEYS = {
    "ctrl": 0xFFE3,  # XK_Control_L
    "shift": 0xFFE1,  # XK_Shift_L
    "alt": 0xFFE9,  # XK_Alt_L
    "escape": 0xFF1B,
    "enter": 0xFF0D,
    "tab": 0xFF09,
    "delete": 0xFFFF,
    "backspace": 0xFF08,
    "f6": 0xFFC3,
}


def _load():
    global _x11, _xtst, _display
    if _display is not None:
        return True
    try:
        _x11 = ctypes.CDLL(ctypes.util.find_library("X11") or "libX11.so.6")
        _xtst = ctypes.CDLL(ctypes.util.find_library("Xtst") or "libXtst.so.6")
        _x11.XOpenDisplay.restype = ctypes.c_void_p
        _x11.XOpenDisplay.argtypes = [ctypes.c_char_p]
        _x11.XFlush.argtypes = [ctypes.c_void_p]
        _x11.XSync.argtypes = [ctypes.c_void_p, ctypes.c_int]
        _x11.XKeysymToKeycode.argtypes = [ctypes.c_void_p, ctypes.c_ulong]
        _x11.XKeysymToKeycode.restype = ctypes.c_ubyte
        _x11.XStringToKeysym.argtypes = [ctypes.c_char_p]
        _x11.XStringToKeysym.restype = ctypes.c_ulong
        _xtst.XTestFakeMotionEvent.argtypes = [
            ctypes.c_void_p,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_int,
            ctypes.c_ulong,
        ]
        _xtst.XTestFakeButtonEvent.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.c_int,
            ctypes.c_ulong,
        ]
        _xtst.XTestFakeKeyEvent.argtypes = [
            ctypes.c_void_p,
            ctypes.c_uint,
            ctypes.c_int,
            ctypes.c_ulong,
        ]
        display = _x11.XOpenDisplay(None)
        if not display:
            return False
        _display = display
        return True
    except Exception as exc:
        print("[Fission 180] x_input: no XTEST here (%s)" % exc, flush=True)
        return False


def available():
    return _load()


def _need():
    if not _load():
        raise RuntimeError("no XTEST extension here: real X input is not possible")


def _pump(ms=0):
    """Let Qt read what the X server sent (the events arrive on Qt's own connection a
    moment after the fake ones were flushed on ours)."""
    _x11.XSync(_display, 0)
    end = time.monotonic() + ms / 1000.0
    while True:
        QtWidgets.QApplication.processEvents()
        if time.monotonic() >= end:
            break
        time.sleep(0.005)  # input pace: the X server's round trip


def _global(widget, pos):
    return widget.mapToGlobal(QtCore.QPoint(int(pos.x()), int(pos.y())))


def _reaches(widget, pos):
    """The click at widget pixel `pos` of the 3D view reaches the view: nothing that takes
    the mouse floats over it there (the Sketch Palette, a dialog). A real pointer clicks
    whatever is on top."""
    if widget is not h.gl_widget():
        return
    on_top = h.covered(QtCore.QPoint(int(pos.x()), int(pos.y())))
    if on_top is not None and on_top.testAttribute(QtCore.Qt.WA_TransparentForMouseEvents):
        on_top = None  # (a hint beside the pointer: clicks go through it)
    if on_top:
        raise RuntimeError(
            "x_input: pixel (%d, %d) of the 3D view is covered by %s"
            % (pos.x(), pos.y(), h.describe(on_top))
        )


def move_to(pos, widget=None):
    """The real pointer onto widget pixel `pos` (of the 3D view when no widget is given),
    waiting until Qt has seen it there."""
    _need()
    widget = widget or h.gl_widget()
    if not widget.rect().contains(QtCore.QPoint(int(pos.x()), int(pos.y()))):
        # a real pointer goes wherever it is sent: off the widget it would click
        # whatever is there (a ribbon button, a menu)
        raise RuntimeError(
            "x_input: pixel (%d, %d) is outside the %d x %d widget"
            % (pos.x(), pos.y(), widget.width(), widget.height())
        )
    at = _global(widget, pos)
    _xtst.XTestFakeMotionEvent(_display, -1, at.x(), at.y(), 0)
    _x11.XFlush(_display)
    end = time.monotonic() + 2.0
    while time.monotonic() < end:
        _pump(10)
        if QtGui.QCursor.pos() == at:
            break
    _pump(20)
    return at


def glide_to(pos, widget=None, steps=6):
    """Come to `pos` from where the pointer is in a few moves, as a hand does."""
    widget = widget or h.gl_widget()
    start = widget.mapFromGlobal(QtGui.QCursor.pos())
    for i in range(1, steps + 1):
        x = start.x() + (pos.x() - start.x()) * i / float(steps)
        y = start.y() + (pos.y() - start.y()) * i / float(steps)
        move_to(QtCore.QPoint(int(round(x)), int(round(y))), widget)


def button(down, number=1):
    _need()
    _xtst.XTestFakeButtonEvent(_display, number, 1 if down else 0, 0)
    _x11.XFlush(_display)
    _pump(30)


def key(name, down):
    """A key down or up. name: one of KEYS or a single character / X keysym name."""
    _need()
    sym = KEYS.get(name)
    if sym is None:
        sym = _x11.XStringToKeysym(name.encode("ascii"))
    code = _x11.XKeysymToKeycode(_display, sym)
    _xtst.XTestFakeKeyEvent(_display, code, 1 if down else 0, 0)
    _x11.XFlush(_display)
    _pump(30)


def tap(name, held=()):
    """Press and release a key, with the keys in `held` down around it ("ctrl",)."""
    for k in held:
        key(k, True)
    key(name, True)
    key(name, False)
    for k in reversed(held):
        key(k, False)
    _pump(30)


def click(pos, held=(), widget=None, hover=True):
    """A real click on widget pixel `pos` with the keys in `held` down ("ctrl", "shift"):
    the keys go down first, the pointer comes over the spot, rests until the view has
    drawn what is under it, press, release, keys up."""
    widget = widget or h.gl_widget()
    _reaches(widget, pos)
    h.press_pace()
    for k in held:
        key(k, True)
    if hover:
        glide_to(QtCore.QPoint(pos.x() + 9, pos.y() + 6), widget, steps=3)
    move_to(pos, widget)
    try:
        h.view_drawn()
    except Exception:
        pass
    button(True)
    button(False)
    for k in reversed(held):
        key(k, False)
    _pump(30)


def double_click(pos, widget=None):
    """A real double-click: two clicks well inside the system's double-click time."""
    widget = widget or h.gl_widget()
    _reaches(widget, pos)
    h.press_pace()
    glide_to(QtCore.QPoint(pos.x() + 9, pos.y() + 6), widget, steps=3)
    move_to(pos, widget)
    try:
        h.view_drawn()
    except Exception:
        pass
    button(True)
    button(False)
    _pump(60)  # input pace: the gap between the two clicks of a double-click
    button(True)
    button(False)
    _pump(30)


def press_drag_release(start, end, held=(), widget=None, steps=10, rest_ms=0):
    """Press at `start`, move to `end` with the button down, release there."""
    widget = widget or h.gl_widget()
    _reaches(widget, start)
    h.press_pace()
    for k in held:
        key(k, True)
    move_to(start, widget)
    try:
        h.view_drawn()
    except Exception:
        pass
    button(True)
    if rest_ms:
        _pump(rest_ms)
    for i in range(1, steps + 1):
        x = start.x() + (end.x() - start.x()) * i / float(steps)
        y = start.y() + (end.y() - start.y()) * i / float(steps)
        move_to(QtCore.QPoint(int(round(x)), int(round(y))), widget)
    button(False)
    for k in reversed(held):
        key(k, False)
    _pump(30)
