# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fission 180's own title bar on Windows, the way Windows programs with their own title bar do
it: the window keeps its whole Windows frame, and Fission 180 answers two of Windows'
questions about it (a native event filter).

Why not Qt's FramelessWindowHint, as on Linux (titlebar_ui)? Luca, 2026-11-26, Windows: "If i
even look at the top bar wrong, the window glitches out ... I cant resize the window, nor move
it around ... when fission is in full screen, i cant access my hidden taskbar. and pressing the
windows key causes the window to move randomly". On GitHub's Windows runner
(tools/fission180/windows_window_check.py): switched to Fission 180's title bar while
maximized (FreeCAD starts maximized), the window's style lost Windows' "maximized" bit (Qt's
applyWindowFlags keeps only "visible" and "disabled" of a shown window's style), so the window
sat 8 px off every edge of the screen, neither maximized nor with a size to come back to; and a
frameless window filling the screen is taken for a full screen program, which keeps a hidden
taskbar away.

The answers:

* WM_NCCALCSIZE, how much of the window is the program's: what Windows says, except the
  caption: the window's inside starts at its top edge (maximized: at the screen's top, the
  frame's border Windows puts above the screen taken off, as at the sides). The left, right and
  bottom borders stay Windows' own (invisible, they resize the window), which is the one frame
  change Qt 6.8 follows by itself (QWindowsWindow::calculateFullFrameMargins, QTBUG-113736).
* WM_NCHITTEST, what is under the mouse: Windows' answer for its borders; in the window, a
  thin band along the top edge resizes, the empty parts of Fission 180's top row are the
  caption (Windows then moves the window, snaps it to the screen's edges, maximizes it on a
  double-click and opens the window menu on a right-click), the rest is the program's
  (titlebar_core.hit_test).
* Maximized on a monitor whose taskbar hides itself, the window's inside stops 2 px short of
  that edge (in WM_NCCALCSIZE; titlebar_core.autohide_gaps), so the mouse there still brings the
  taskbar out: a window whose inside covers the whole screen is taken for a full screen program
  and the taskbar stays away. (On GitHub's runner Windows ignored a smaller maximized size asked
  for in WM_GETMINMAXINFO, and put back a maximized rectangle trimmed in WM_WINDOWPOSCHANGING.)

Maximize, restore, minimize, Windows+arrows, the Windows key, snap and the taskbar are then
Windows' own. Nothing here lets an exception out of the filter.
"""

import sys

from . import titlebar_core as core
from . import warn
from .compat import QtCore

WM_NCCALCSIZE = 0x0083
WM_NCHITTEST = 0x0084
HTCLIENT = 1
HITS = {core.CAPTION: 2, core.TOP: 12, core.TOP_LEFT: 13, core.TOP_RIGHT: 14}

_state = {"filter": None, "installed": False}


def available():
    return sys.platform == "win32"


_api = {}


def _win():
    """user32 / shell32 and the structures, loaded on first use (Windows only)."""
    if _api:
        return _api
    import ctypes
    from ctypes import wintypes as W

    class MSG(ctypes.Structure):
        _fields_ = [
            ("hwnd", W.HWND),
            ("message", W.UINT),
            ("wParam", W.WPARAM),
            ("lParam", W.LPARAM),
            ("time", W.DWORD),
            ("pt", W.POINT),
            ("lPrivate", W.DWORD),
        ]

    class NCCALCSIZE_PARAMS(ctypes.Structure):
        _fields_ = [("rgrc", W.RECT * 3), ("lppos", ctypes.c_void_p)]

    class MONITORINFO(ctypes.Structure):
        _fields_ = [("cbSize", W.DWORD), ("rcMonitor", W.RECT), ("rcWork", W.RECT), ("dwFlags", W.DWORD)]

    class APPBARDATA(ctypes.Structure):
        _fields_ = [
            ("cbSize", W.DWORD),
            ("hWnd", W.HWND),
            ("uCallbackMessage", W.UINT),
            ("uEdge", W.UINT),
            ("rc", W.RECT),
            ("lParam", W.LPARAM),
        ]

    user32 = ctypes.WinDLL("user32")
    shell32 = ctypes.WinDLL("shell32")
    user32.DefWindowProcW.restype = ctypes.c_ssize_t
    user32.DefWindowProcW.argtypes = [W.HWND, W.UINT, W.WPARAM, W.LPARAM]
    user32.IsZoomed.argtypes = [W.HWND]
    user32.GetWindowRect.argtypes = [W.HWND, ctypes.POINTER(W.RECT)]
    user32.ClientToScreen.argtypes = [W.HWND, ctypes.POINTER(W.POINT)]
    user32.SetWindowPos.argtypes = [W.HWND, W.HWND, ctypes.c_int, ctypes.c_int, ctypes.c_int, ctypes.c_int, W.UINT]
    user32.MonitorFromWindow.restype = W.HMONITOR
    user32.MonitorFromWindow.argtypes = [W.HWND, W.DWORD]
    user32.GetMonitorInfoW.argtypes = [W.HMONITOR, ctypes.POINTER(MONITORINFO)]
    shell32.SHAppBarMessage.restype = ctypes.c_size_t
    shell32.SHAppBarMessage.argtypes = [W.DWORD, ctypes.POINTER(APPBARDATA)]
    _api.update(
        ctypes=ctypes,
        W=W,
        user32=user32,
        shell32=shell32,
        MSG=MSG,
        NCCALCSIZE_PARAMS=NCCALCSIZE_PARAMS,
        MONITORINFO=MONITORINFO,
        APPBARDATA=APPBARDATA,
    )
    return _api


def _signed16(value):
    value &= 0xFFFF
    return value - 0x10000 if value & 0x8000 else value


EDGE_NAMES = {0: "left", 1: "top", 2: "right", 3: "bottom"}


def _hidden_edges(monitor_rect):
    """The edges of this monitor where a taskbar hides itself: ABM_GETAUTOHIDEBAREX for each
    edge; else Windows' own taskbar (ABM_GETSTATE says it hides itself, ABM_GETTASKBARPOS says on
    which edge) when it is on this monitor."""
    api = _win()
    ctypes, shell32 = api["ctypes"], api["shell32"]
    edges = []
    for code, name in EDGE_NAMES.items():
        abd = api["APPBARDATA"]()
        abd.cbSize = ctypes.sizeof(abd)
        abd.uEdge = code
        abd.rc.left, abd.rc.top, abd.rc.right, abd.rc.bottom = monitor_rect
        if shell32.SHAppBarMessage(0x0000000B, ctypes.byref(abd)):
            edges.append(name)
    if not edges:
        abd = api["APPBARDATA"]()
        abd.cbSize = ctypes.sizeof(abd)
        if shell32.SHAppBarMessage(0x00000004, ctypes.byref(abd)) & 0x1:  # ABM_GETSTATE: ABS_AUTOHIDE
            pos = api["APPBARDATA"]()
            pos.cbSize = ctypes.sizeof(pos)
            if shell32.SHAppBarMessage(0x00000005, ctypes.byref(pos)):  # ABM_GETTASKBARPOS
                left, top, right, bottom = monitor_rect
                cx, cy = (pos.rc.left + pos.rc.right) // 2, (pos.rc.top + pos.rc.bottom) // 2
                near = left - 64 <= cx <= right + 64 and top - 64 <= cy <= bottom + 64
                if near and pos.uEdge in EDGE_NAMES:
                    edges.append(EDGE_NAMES[pos.uEdge])
    return edges


class _Filter(QtCore.QAbstractNativeEventFilter):
    """Answers WM_NCCALCSIZE and WM_NCHITTEST for the main window while
    `on`; everything else, and every other window, goes on to Qt untouched."""

    def __init__(self):
        super().__init__()
        self.hwnd = 0
        self.on = False
        self.closing = False
        self.window = None  # the main window (a Qt widget)
        self.empty_at = None  # (window, x, y) -> True on an empty part of the top row

    def nativeEventFilter(self, event_type, message):
        if not self.on:
            return False, 0
        try:
            api = _win()
            msg = api["MSG"].from_address(int(message))
            if (msg.hwnd or 0) != self.hwnd:
                return False, 0
            kind = msg.message
            if kind == WM_NCCALCSIZE:
                return self._calc_size(api, msg)
            if kind == WM_NCHITTEST:
                return self._hit_test(api, msg)

        except Exception as exc:  # (never out of a native filter)
            _warn_once("title bar (Windows): %s" % exc)
        return False, 0

    def _calc_size(self, api, msg):
        if not msg.wParam:
            return False, 0
        params = api["NCCALCSIZE_PARAMS"].from_address(msg.lParam)
        top, left = params.rgrc[0].top, params.rgrc[0].left
        result = api["user32"].DefWindowProcW(msg.hwnd, msg.message, msg.wParam, msg.lParam)
        r = params.rgrc[0]
        if api["user32"].IsZoomed(msg.hwnd):
            # (maximized, Windows puts the frame's border outside the screen: as much at the top
            # as it put at the left)
            r.top = top + (r.left - left)
            sides, above = self._autohide_inset(api, msg.hwnd)
            # (Qt follows a frame whose left, right and bottom borders are equal: a gap at any of
            # those three edges goes on all three; one at the top on its own)
            r.left += sides
            r.right -= sides
            r.bottom -= sides
            r.top += above
        else:
            r.top = top
        return True, result

    def _autohide_inset(self, api, hwnd):
        """(sides, top): how much less of a maximized window is the program's where a taskbar
        hides itself on this monitor (titlebar_core.autohide_gaps), so the mouse at that edge
        still brings it out: a window whose inside covers the whole screen is taken for a full
        screen program and the taskbar stays away (Luca, 2026-11-26)."""
        user32, ctypes = api["user32"], api["ctypes"]
        info = api["MONITORINFO"]()
        info.cbSize = ctypes.sizeof(info)
        if not user32.GetMonitorInfoW(user32.MonitorFromWindow(hwnd, 2), ctypes.byref(info)):
            return 0, 0
        mon = (info.rcMonitor.left, info.rcMonitor.top, info.rcMonitor.right, info.rcMonitor.bottom)
        work = (info.rcWork.left, info.rcWork.top, info.rcWork.right, info.rcWork.bottom)
        edges = _hidden_edges(mon)
        rect = core.autohide_gaps(mon, work, edges)
        _state["last_max"] = {"monitor": mon, "work": work, "edges": edges, "rect": rect}
        if rect is None:
            return 0, 0
        sides = max(rect[0] - work[0], work[2] - rect[2], work[3] - rect[3])
        return sides, rect[1] - work[1]

    def _hit_test(self, api, msg):
        user32 = api["user32"]
        answer = user32.DefWindowProcW(msg.hwnd, msg.message, msg.wParam, msg.lParam)
        if answer != HTCLIENT or self.closing or self.window is None:
            return True, answer
        x, y = _signed16(msg.lParam), _signed16(msg.lParam >> 16)
        origin = api["W"].POINT(0, 0)
        user32.ClientToScreen(msg.hwnd, api["ctypes"].byref(origin))
        window = self.window
        ratio = window.devicePixelRatioF() or 1.0
        lx, ly = (x - origin.x) / ratio, (y - origin.y) / ratio
        empty = bool(self.empty_at is not None and self.empty_at(window, lx, ly))
        what = core.hit_test(lx, ly, window.width(), bool(user32.IsZoomed(msg.hwnd)), empty)
        return True, HITS.get(what, HTCLIENT)


_warned = set()


def _warn_once(text):
    if text not in _warned:
        _warned.add(text)
        warn(text)


def _frame_changed(hwnd):
    """Windows asks WM_NCCALCSIZE again (the caption goes or comes back). The inside moves and
    changes size, so Windows sends WM_MOVE and WM_SIZE: Qt takes the new frame from the first
    and the window's new geometry from the second."""
    api = _win()
    flags = 0x0020 | 0x0002 | 0x0001 | 0x0004 | 0x0010 | 0x0200  # FRAMECHANGED|NOMOVE|NOSIZE|NOZORDER|NOACTIVATE|NOOWNERZORDER
    api["user32"].SetWindowPos(hwnd, None, 0, 0, 0, 0, flags)


def set_on(window, on, empty_at=None):
    """Fission 180's title bar on `window` (the main window) or Windows' own back."""
    if not available() or window is None:
        return
    try:
        flt = _state["filter"]
        if flt is None:
            flt = _state["filter"] = _Filter()
        app = QtCore.QCoreApplication.instance()
        if on and not _state["installed"]:
            app.installNativeEventFilter(flt)
            _state["installed"] = True
        flt.window = window
        flt.empty_at = empty_at
        flt.closing = False
        hwnd = int(window.winId())
        changed = flt.on != bool(on) or flt.hwnd != hwnd
        flt.hwnd = hwnd
        flt.on = bool(on)
        if changed:
            _frame_changed(hwnd)
    except Exception as exc:
        warn("title bar (Windows): %s" % exc)


def closing():
    """The window is going away: no more questions to Qt's widgets (the frame stays as it is)."""
    flt = _state["filter"]
    if flt is not None:
        flt.closing = True


def remove():
    """Qt's aboutToQuit: the filter off the application before its windows are destroyed."""
    try:
        flt = _state["filter"]
        if flt is not None:
            flt.on = False
            flt.window = None
            flt.empty_at = None
            if _state["installed"]:
                QtCore.QCoreApplication.instance().removeNativeEventFilter(flt)
                _state["installed"] = False
    except Exception as exc:
        warn("title bar (Windows): %s" % exc)
