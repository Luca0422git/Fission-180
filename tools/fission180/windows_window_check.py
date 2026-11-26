# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fission 180's own title bar on a real Windows desktop (GitHub's Windows runner), driven like
a person would: real mouse presses, drags and key presses (SendInput), and Windows' own view of
the window (its rectangle, its style, whether Windows thinks it is maximized, the monitor's work
area, the taskbar).

Luca (2026-11-26, Windows): "If i even look at the top bar wrong, the window glitches out ... I
cant resize the window, nor move it around. if i click the top bar, it randomly moves it to the
side without me interacting with it ... when fission is in full screen, i cant access my
hidden taskbar. and pressing the windows key causes the window to move randomly". None of it
can happen under Linux's virtual screen (no window manager), so it is checked here.

    python tools/fission180/windows_window_check.py --freecad DIR --out DIR

DIR holds an unpacked FreeCAD for Windows (bin/freecad.exe); Fission 180 goes in as an add-on
(a throw-away profile). FreeCAD runs tools/fission180/windows_window_helper.py, which reports
what Qt thinks (state.json) and does what is asked (command.json). Exit code 1 if a check
failed. Windows only.
"""

import argparse
import ctypes
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import traceback
from ctypes import wintypes as W

REPO = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
HELPER = os.path.join(REPO, "tools", "fission180", "windows_window_helper.py")
TOL = 4  # px: Windows and Qt round, the checks allow this much

# -- Windows -----------------------------------------------------------------------------------
user32 = ctypes.WinDLL("user32", use_last_error=True)
shell32 = ctypes.WinDLL("shell32")
dwmapi = ctypes.WinDLL("dwmapi")
try:  # the screen's own pixels everywhere (the runner is at 100 % anyway)
    user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
except Exception:
    pass

ULONG_PTR = ctypes.c_size_t


class MONITORINFO(ctypes.Structure):
    _fields_ = [("cbSize", W.DWORD), ("rcMonitor", W.RECT), ("rcWork", W.RECT), ("dwFlags", W.DWORD)]


class WINDOWPLACEMENT(ctypes.Structure):
    _fields_ = [
        ("length", W.UINT),
        ("flags", W.UINT),
        ("showCmd", W.UINT),
        ("ptMinPosition", W.POINT),
        ("ptMaxPosition", W.POINT),
        ("rcNormalPosition", W.RECT),
    ]


class APPBARDATA(ctypes.Structure):
    _fields_ = [
        ("cbSize", W.DWORD),
        ("hWnd", W.HWND),
        ("uCallbackMessage", W.UINT),
        ("uEdge", W.UINT),
        ("rc", W.RECT),
        ("lParam", W.LPARAM),
    ]


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [
        ("dx", W.LONG),
        ("dy", W.LONG),
        ("mouseData", W.DWORD),
        ("dwFlags", W.DWORD),
        ("time", W.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class KEYBDINPUT(ctypes.Structure):
    _fields_ = [
        ("wVk", W.WORD),
        ("wScan", W.WORD),
        ("dwFlags", W.DWORD),
        ("time", W.DWORD),
        ("dwExtraInfo", ULONG_PTR),
    ]


class HARDWAREINPUT(ctypes.Structure):
    _fields_ = [("uMsg", W.DWORD), ("wParamL", W.WORD), ("wParamH", W.WORD)]


class _INPUTUNION(ctypes.Union):
    _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]


class INPUT(ctypes.Structure):
    _fields_ = [("type", W.DWORD), ("u", _INPUTUNION)]


user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
user32.GetWindowLongPtrW.argtypes = [W.HWND, ctypes.c_int]
user32.GetWindowRect.argtypes = [W.HWND, ctypes.POINTER(W.RECT)]
user32.IsZoomed.argtypes = [W.HWND]
user32.IsIconic.argtypes = [W.HWND]
user32.IsWindow.argtypes = [W.HWND]
user32.MonitorFromWindow.restype = W.HMONITOR
user32.MonitorFromWindow.argtypes = [W.HWND, W.DWORD]
user32.GetMonitorInfoW.argtypes = [W.HMONITOR, ctypes.POINTER(MONITORINFO)]
user32.GetForegroundWindow.restype = W.HWND
user32.FindWindowW.restype = W.HWND
user32.FindWindowW.argtypes = [W.LPCWSTR, W.LPCWSTR]
user32.GetWindowPlacement.argtypes = [W.HWND, ctypes.POINTER(WINDOWPLACEMENT)]
user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
user32.GetCursorPos.argtypes = [ctypes.POINTER(W.POINT)]
user32.SendInput.argtypes = [W.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
user32.GetSystemMetrics.argtypes = [ctypes.c_int]
user32.SetForegroundWindow.argtypes = [W.HWND]
user32.WindowFromPoint.restype = W.HWND
user32.WindowFromPoint.argtypes = [W.POINT]
user32.GetAncestor.restype = W.HWND
user32.GetAncestor.argtypes = [W.HWND, W.UINT]
user32.GetClassNameW.argtypes = [W.HWND, W.LPWSTR, ctypes.c_int]
user32.GetWindowTextW.argtypes = [W.HWND, W.LPWSTR, ctypes.c_int]
user32.IsWindowEnabled.argtypes = [W.HWND]
user32.GetWindowThreadProcessId.argtypes = [W.HWND, ctypes.POINTER(W.DWORD)]
user32.GetClientRect.argtypes = [W.HWND, ctypes.POINTER(W.RECT)]
user32.ClientToScreen.argtypes = [W.HWND, ctypes.POINTER(W.POINT)]
dwmapi.DwmGetWindowAttribute.argtypes = [W.HWND, W.DWORD, ctypes.c_void_p, W.DWORD]
shell32.SHAppBarMessage.restype = ULONG_PTR
shell32.SHAppBarMessage.argtypes = [W.DWORD, ctypes.POINTER(APPBARDATA)]

STYLES = {
    "WS_POPUP": 0x80000000,
    "WS_MINIMIZE": 0x20000000,
    "WS_VISIBLE": 0x10000000,
    "WS_MAXIMIZE": 0x01000000,
    "WS_CAPTION": 0x00C00000,
    "WS_SYSMENU": 0x00080000,
    "WS_THICKFRAME": 0x00040000,
    "WS_MINIMIZEBOX": 0x00020000,
    "WS_MAXIMIZEBOX": 0x00010000,
}
INPUT_MOUSE, INPUT_KEYBOARD = 0, 1
MOUSEEVENTF_MOVE, MOUSEEVENTF_LEFTDOWN, MOUSEEVENTF_LEFTUP = 0x0001, 0x0002, 0x0004
MOUSEEVENTF_VIRTUALDESK, MOUSEEVENTF_ABSOLUTE = 0x4000, 0x8000
KEYEVENTF_KEYUP, KEYEVENTF_EXTENDEDKEY = 0x0002, 0x0001
VK_LWIN, VK_UP, VK_DOWN, VK_ESCAPE = 0x5B, 0x26, 0x28, 0x1B
ABM_GETSTATE, ABM_SETSTATE, ABS_AUTOHIDE, ABS_ALWAYSONTOP = 4, 10, 1, 2


def _rect(r):
    return [r.left, r.top, r.right, r.bottom]


def window_rect(hwnd):
    r = W.RECT()
    user32.GetWindowRect(hwnd, ctypes.byref(r))
    return _rect(r)


def visible_rect(hwnd):
    """The window as one sees it (without Windows' invisible resize borders)."""
    r = W.RECT()
    if dwmapi.DwmGetWindowAttribute(hwnd, 9, ctypes.byref(r), ctypes.sizeof(r)) == 0:
        return _rect(r)
    return window_rect(hwnd)


def inside(hwnd):
    """The window's inside (the program's part) on the screen: [x, y, width, height]."""
    r = W.RECT()
    user32.GetClientRect(hwnd, ctypes.byref(r))
    p = W.POINT(0, 0)
    user32.ClientToScreen(hwnd, ctypes.byref(p))
    return [p.x, p.y, r.right - r.left, r.bottom - r.top]


def monitor(hwnd):
    info = MONITORINFO()
    info.cbSize = ctypes.sizeof(info)
    user32.GetMonitorInfoW(user32.MonitorFromWindow(hwnd, 2), ctypes.byref(info))
    return _rect(info.rcMonitor), _rect(info.rcWork)


def styles(hwnd):
    value = user32.GetWindowLongPtrW(hwnd, -16) & 0xFFFFFFFF
    return [name for name, bit in STYLES.items() if value & bit]


def placement(hwnd):
    p = WINDOWPLACEMENT()
    p.length = ctypes.sizeof(p)
    user32.GetWindowPlacement(hwnd, ctypes.byref(p))
    return {"showCmd": p.showCmd, "normal": _rect(p.rcNormalPosition)}


def describe(hwnd):
    if not hwnd:
        return None
    cls = ctypes.create_unicode_buffer(128)
    user32.GetClassNameW(hwnd, cls, 128)
    title = ctypes.create_unicode_buffer(128)
    user32.GetWindowTextW(hwnd, title, 128)
    pid = W.DWORD()
    user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    return {"hwnd": int(hwnd), "class": cls.value, "title": title.value, "pid": pid.value}


def under(x, y):
    """The window under a screen point and its top-level window (what a click there hits)."""
    hwnd = user32.WindowFromPoint(W.POINT(x, y))
    root = user32.GetAncestor(hwnd, 2) if hwnd else None
    return {"at": describe(hwnd), "root": describe(root)}


def cursor():
    p = W.POINT()
    user32.GetCursorPos(ctypes.byref(p))
    return [p.x, p.y]


def tray():
    return user32.FindWindowW("Shell_TrayWnd", None)


def autohide():
    abd = APPBARDATA()
    abd.cbSize = ctypes.sizeof(abd)
    abd.hWnd = tray()
    return bool(shell32.SHAppBarMessage(ABM_GETSTATE, ctypes.byref(abd)) & ABS_AUTOHIDE)


def set_autohide(on):
    abd = APPBARDATA()
    abd.cbSize = ctypes.sizeof(abd)
    abd.hWnd = tray()
    abd.lParam = ABS_AUTOHIDE if on else ABS_ALWAYSONTOP
    shell32.SHAppBarMessage(ABM_SETSTATE, ctypes.byref(abd))


def _send(*inputs):
    arr = (INPUT * len(inputs))(*inputs)
    sent = user32.SendInput(len(inputs), arr, ctypes.sizeof(INPUT))
    if sent != len(inputs):
        print("[Fission 180] SendInput sent %d of %d (error %d)" % (sent, len(inputs), ctypes.get_last_error()))


def _mouse(flags, x=0, y=0):
    i = INPUT()
    i.type = INPUT_MOUSE
    i.u.mi = MOUSEINPUT(x, y, 0, flags, 0, 0)
    return i


def move(x, y):
    vx, vy = user32.GetSystemMetrics(76), user32.GetSystemMetrics(77)
    vw, vh = user32.GetSystemMetrics(78), user32.GetSystemMetrics(79)
    nx = int(round((x - vx) * 65535.0 / max(1, vw - 1)))
    ny = int(round((y - vy) * 65535.0 / max(1, vh - 1)))
    _send(_mouse(MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE | MOUSEEVENTF_VIRTUALDESK, nx, ny))
    if cursor() != [x, y]:  # (rounding: put it exactly there)
        user32.SetCursorPos(x, y)


def down():
    _send(_mouse(MOUSEEVENTF_LEFTDOWN))


def up():
    _send(_mouse(MOUSEEVENTF_LEFTUP))


def key(vk, release=False):
    i = INPUT()
    i.type = INPUT_KEYBOARD
    flags = KEYEVENTF_KEYUP if release else 0
    if vk in (VK_LWIN, VK_UP, VK_DOWN):
        flags |= KEYEVENTF_EXTENDEDKEY
    i.u.ki = KEYBDINPUT(vk, 0, flags, 0, 0)
    _send(i)


def press(*vks):
    for vk in vks:
        key(vk)
        time.sleep(0.05)
    for vk in reversed(vks):
        key(vk, release=True)
        time.sleep(0.05)


def click(x, y):
    print("[Fission 180] click at %s,%s on %s" % (x, y, (under(x, y)["root"] or {}).get("title")))
    move(x, y)
    time.sleep(0.15)
    down()
    time.sleep(0.06)
    up()
    time.sleep(0.6)


def double_click(x, y):
    print("[Fission 180] double-click at %s,%s on %s" % (x, y, (under(x, y)["root"] or {}).get("title")))
    move(x, y)
    time.sleep(0.15)
    for _ in range(2):
        down()
        time.sleep(0.04)
        up()
        time.sleep(0.06)
    time.sleep(0.8)


def drag(x0, y0, dx, dy, steps=15):
    print("[Fission 180] drag from %s,%s by %s,%s on %s" % (x0, y0, dx, dy, (under(x0, y0)["root"] or {}).get("title")))
    move(x0, y0)
    time.sleep(0.2)
    down()
    time.sleep(0.2)
    for i in range(1, steps + 1):
        move(int(round(x0 + dx * i / float(steps))), int(round(y0 + dy * i / float(steps))))
        time.sleep(0.03)
    time.sleep(0.25)
    up()
    time.sleep(0.8)


# -- FreeCAD and the helper --------------------------------------------------------------------
class App:
    def __init__(self, exe, out):
        self.out = out
        self.cid = 0
        self.profile = tempfile.mkdtemp(prefix="fission180-window-")
        os.makedirs(os.path.join(self.profile, "Mod"))
        shutil.copytree(os.path.join(REPO, "src", "Mod", "Fission180"), os.path.join(self.profile, "Mod", "Fission180"))
        env = dict(os.environ)
        env.update(
            FREECAD_USER_HOME=self.profile,
            FISSION180_WINDOW_OUT=out,
            FISSION180_NO_INTERNET="1",
        )
        self.proc = subprocess.Popen([exe, HELPER], env=env)
        self.started = time.time()

    def state(self):
        for _ in range(20):
            try:
                with open(os.path.join(self.out, "state.json"), encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                time.sleep(0.05)
        return {}

    def wait(self, cond, timeout=20.0):
        end = time.time() + timeout
        while time.time() < end:
            s = self.state()
            if s and cond(s):
                return s
            if self.proc.poll() is not None:
                raise RuntimeError("FreeCAD exited (code %s)" % self.proc.returncode)
            time.sleep(0.1)
        return None

    def command(self, do, arg=None, settle=1.0):
        self.cid += 1
        tmp = os.path.join(self.out, "command.json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump({"id": self.cid, "do": do, "arg": arg}, f)
        for attempt in range(50):  # (Windows: FreeCAD may have the file open just then)
            try:
                os.replace(tmp, os.path.join(self.out, "command.json"))
                break
            except PermissionError:
                time.sleep(0.05)
        else:
            raise RuntimeError("cannot hand the helper %s" % do)
        cid = self.cid
        if self.wait(lambda s: s.get("ack") == cid, 20) is None:
            raise RuntimeError("the helper did not do %s" % do)
        time.sleep(settle)
        return self.state()


# -- the checks --------------------------------------------------------------------------------
RESULTS = []


def check(name, ok, detail=""):
    RESULTS.append({"name": name, "passed": bool(ok), "detail": detail})
    print("[Fission 180] %s: %s%s" % ("PASS" if ok else "FAIL", name, (" (%s)" % detail) if detail else ""))
    sys.stdout.flush()


def facts(app, label):
    s = app.state()
    hwnd = s.get("hwnd")
    f = {"label": label, "qt": {k: s.get(k) for k in ("t", "qt_maximized", "qt_fullscreen", "qt_geometry", "qt_frame", "frameless", "mode", "active", "maximize_tip", "events", "last_event", "modal", "popup", "active_window", "other_windows", "enabled")}}
    if hwnd:
        mon, work = monitor(hwnd)
        f["win"] = {
            "rect": window_rect(hwnd),
            "visible": visible_rect(hwnd),
            "zoomed": bool(user32.IsZoomed(hwnd)),
            "iconic": bool(user32.IsIconic(hwnd)),
            "styles": styles(hwnd),
            "enabled": bool(user32.IsWindowEnabled(hwnd)),
            "placement": placement(hwnd),
            "foreground": user32.GetForegroundWindow() == hwnd,
            "monitor": mon,
            "work": work,
            "cursor": cursor(),
            "taskbar": window_rect(tray()) if tray() else None,
            "autohide": autohide(),
        }
    q, w = f["qt"], f.get("win") or {}
    short = {"MAXIMIZE": "MAX", "CAPTION": "CAP", "THICKFRAME": "THICK", "POPUP": "POPUP"}
    style = "+".join(short[s[3:]] for s in w.get("styles", []) if s[3:] in short)
    print(
        "[Fission 180] facts %s | qt max=%s geom=%s press=%s modal=%s | win rect=%s zoomed=%s %s enabled=%s fg=%s work=%s cursor=%s"
        % (label, q.get("qt_maximized"), q.get("qt_geometry"), (q.get("events") or {}).get("press", 0),
           (q.get("modal") or [None, None, None])[2], w.get("rect"), w.get("zoomed"), style,
           w.get("enabled"), w.get("foreground"), w.get("work"), w.get("cursor"))
    )
    with open(os.path.join(app.out, "facts.jsonl"), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(f) + "\n")
    sys.stdout.flush()
    shot(app, label)
    return s, f


def shot(app, label):
    try:
        from PIL import ImageGrab

        name = "".join(c if c.isalnum() else "_" for c in label)[:60]
        ImageGrab.grab(all_screens=True).save(os.path.join(app.out, "%02d_%s.png" % (len(RESULTS), name)))
    except Exception:
        pass


def near(a, b, tol=TOL):
    return all(abs(x - y) <= tol for x, y in zip(a, b))


def size(r):
    return [r[2] - r[0], r[3] - r[1]]


def on_screen(r, mon):
    return r[0] >= mon[0] - TOL and r[1] >= mon[1] - TOL and r[2] <= mon[2] + TOL and r[3] <= mon[3] + TOL


def point(app, name):
    s = app.state()
    p = (s.get("points") or {}).get(name)
    if not p:
        raise RuntimeError("no %s on the screen (points: %s)" % (name, sorted((s.get("points") or {}))))
    return p


def fills_work(f):
    return near(f["win"]["visible"], f["win"]["work"])


def agree(app, label):
    """Qt draws the window where Windows has its inside (the runner is at 100 %: Qt's pixels
    are the screen's)."""
    s = app.state()
    hwnd = s.get("hwnd")
    if not hwnd:
        return
    win = inside(hwnd)
    check("%s: Qt and Windows agree where the window's inside is" % label, near(s.get("qt_geometry") or [], win, 2), "Qt %s, Windows %s" % (s.get("qt_geometry"), win))


def step(name, fn):
    try:
        fn()
    except Exception:
        check(name + " (ran to the end)", False, traceback.format_exc().strip().splitlines()[-1])
        traceback.print_exc()


def run(app):
    hwnd = app.state()["hwnd"]
    app.command("activate")
    user32.SetForegroundWindow(hwnd)
    facts(app, "start")
    memo = {}

    def a0_start_drag():
        s, f = facts(app, "start, before a drag")
        before = f["win"]["rect"]
        x, y = point(app, "row_empty")
        drag(x, y, 60, 40)
        s, f = facts(app, "start, after a drag")
        after = f["win"]["rect"]
        moved = [after[0] - before[0], after[1] - before[1]]
        ev = s.get("events") or {}
        check("As FreeCAD starts: the press arrives (Qt's or Windows' caption)", ev.get("press", 0) + ev.get("nc_press", 0) > 0, str(ev))
        check("As FreeCAD starts: dragging the top row moves the window", near(moved, [60, 40]), "moved %s" % moved)

    def a_system_normal():
        app.command("titlebar", "system")
        app.command("normal")
        app.command("geometry", [120, 90, 760, 540], settle=1.5)
        s, f = facts(app, "system title bar, normal")
        memo["client"] = s["qt_geometry"][2:]
        memo["visible"] = size(f["win"]["visible"])
        agree(app, "System title bar")
        check("With the system's title bar the window is where it was put", not s["qt_maximized"] and on_screen(f["win"]["visible"], f["win"]["monitor"]), str(f["win"]["visible"]))

    def b_switch_while_maximized():
        app.command("maximize", settle=1.5)
        s, f = facts(app, "system title bar, maximized")
        check("The system's maximize fills the work area", fills_work(f), "%s vs work %s" % (f["win"]["visible"], f["win"]["work"]))
        app.command("titlebar", "own", settle=2.0)
        s, f = facts(app, "own title bar switched on while maximized")
        check("Switched on while maximized: still maximized (restore button)", s["qt_maximized"] and s.get("maximize_tip") == "Restore Down", s.get("maximize_tip"))
        check("Switched on while maximized: fills the work area, no more", fills_work(f), "%s vs work %s" % (f["win"]["visible"], f["win"]["work"]))
        check("Switched on while maximized: Windows still has it maximized", f["win"]["zoomed"] and "WS_MAXIMIZE" in f["win"]["styles"], f["win"]["styles"])
        agree(app, "Own title bar, maximized")

    def c_restore():
        click(*point(app, "maximize"))
        s, f = facts(app, "restore button")
        check("Restore Down: no longer maximized", not s["qt_maximized"], s.get("maximize_tip"))
        check("Restore Down: the window's earlier size", near(size(f["win"]["visible"]), memo["visible"], 12), "%s vs %s" % (size(f["win"]["visible"]), memo["visible"]))
        check("Restore Down: on the screen", on_screen(f["win"]["visible"], f["win"]["monitor"]), str(f["win"]["visible"]))
        agree(app, "Own title bar, restored")

    def d_drag():
        place()
        s, f = facts(app, "before drag")
        before = f["win"]["rect"]
        x, y = point(app, "row_empty")
        drag(x, y, 120, 60)
        s, f = facts(app, "after drag")
        after = f["win"]["rect"]
        moved = [after[0] - before[0], after[1] - before[1]]
        check("Dragging the top row moves the window with the mouse", near(moved, [120, 60]), "moved %s" % moved)
        check("Dragging the top row keeps the size", near(size(after), size(before)), "%s -> %s" % (size(before), size(after)))
        move(x + 120 + 150, y + 60 + 100)
        time.sleep(1.0)
        s, f2 = facts(app, "mouse moved after the drag")
        check("After the drag, moving the mouse alone moves nothing", near(f2["win"]["rect"], after, 1), "%s -> %s" % (after, f2["win"]["rect"]))

    def e_click():
        place()
        s, f = facts(app, "before click")
        before = f["win"]["rect"]
        x, y = point(app, "row_empty")
        click(x, y)
        move(x + 150, y + 80)
        time.sleep(1.0)
        s, f = facts(app, "mouse moved after a click on the top row")
        check("A click on the top row, then moving the mouse, moves nothing", near(f["win"]["rect"], before, 1), "%s -> %s" % (before, f["win"]["rect"]))

    def place():
        """A known, whole-on-screen place to start from (a drag before may have left the
        window half off the screen, and a corner of the screen is the taskbar's Show desktop)."""
        app.command("activate", settle=0.3)
        app.command("normal", settle=0.8)
        app.command("geometry", [150, 110, 640, 420], settle=1.2)
        user32.SetForegroundWindow(hwnd)

    def f_resize():
        place()
        s, f = facts(app, "before resize")
        before = f["win"]["rect"]
        v = f["win"]["visible"]
        # (Windows' own invisible border just outside the visible window, as a person grabs it)
        drag(v[2] + 3, (v[1] + v[3]) // 2, 100, 0)
        s, f = facts(app, "after right edge")
        after = f["win"]["rect"]
        check("Dragging the right edge makes the window wider", near(size(after), [size(before)[0] + 100, size(before)[1]]), "%s -> %s" % (size(before), size(after)))
        v = f["win"]["visible"]
        drag(v[2] + 3, v[3] + 3, -80, 50)
        s, f = facts(app, "after bottom-right corner")
        after2 = f["win"]["rect"]
        check("Dragging the bottom-right corner resizes both ways", near(size(after2), [size(after)[0] - 80, size(after)[1] + 50]), "%s -> %s" % (size(after), size(after2)))
        v = f["win"]["visible"]
        drag((v[0] + v[2]) // 2, v[1] + 2, 0, -40)
        s, f = facts(app, "after top edge")
        after3 = f["win"]["rect"]
        check("Dragging the top edge makes the window taller", near(size(after3), [size(after2)[0], size(after2)[1] + 40]) and near([after3[1]], [after2[1] - 40]), "%s -> %s" % (after2, after3))
        agree(app, "Own title bar, resized")
        memo["normal"] = size(after3)
        memo["normal_client"] = s["qt_geometry"][2:]

    def g_double_click():
        place()
        memo["normal_client"] = app.state()["qt_geometry"][2:]  # (the size it comes back to)
        x, y = point(app, "row_empty")
        double_click(x, y)
        s, f = facts(app, "double-click on the top row")
        check("Double-click on the top row maximizes", s["qt_maximized"] and fills_work(f), "%s vs work %s" % (f["win"]["visible"], f["win"]["work"]))
        agree(app, "Own title bar, maximized by a double-click")
        x, y = point(app, "row_empty")
        double_click(x, y)
        s, f = facts(app, "double-click again")
        check("Double-click again restores the size", not s["qt_maximized"] and near(s["qt_geometry"][2:], memo["normal_client"], 12), "%s vs %s" % (s["qt_geometry"][2:], memo["normal_client"]))

    def h_drag_maximized():
        place()
        memo["normal_client"] = app.state()["qt_geometry"][2:]
        click(*point(app, "maximize"))
        s, f = facts(app, "maximize button")
        check("The maximize button fills the work area", s["qt_maximized"] and fills_work(f), "%s vs work %s" % (f["win"]["visible"], f["win"]["work"]))
        x, y = point(app, "row_empty")
        drag(x, y, 40, 160)
        s, f = facts(app, "dragged down while maximized")
        c = cursor()
        r = f["win"]["rect"]
        check("Dragging a maximized window restores it", not s["qt_maximized"] and near(s["qt_geometry"][2:], memo["normal_client"], 12), "%s vs %s" % (s["qt_geometry"][2:], memo["normal_client"]))
        check("... and the mouse still holds its top row", r[0] <= c[0] <= r[2] and r[1] <= c[1] <= r[1] + 60, "cursor %s, window %s" % (c, r))

    def i_windows_key():
        place()
        click(*point(app, "maximize"))
        s, f = facts(app, "maximized again")
        before = f["win"]["visible"]
        press(VK_LWIN)
        time.sleep(1.5)
        facts(app, "Start menu open")
        press(VK_ESCAPE)
        time.sleep(1.0)
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.5)
        s, f = facts(app, "Start menu closed")
        check("The Windows key leaves the window where it is", near(f["win"]["visible"], before) and s["qt_maximized"], "%s -> %s" % (before, f["win"]["visible"]))

    def j_snap_keys():
        user32.SetForegroundWindow(hwnd)
        time.sleep(0.3)
        press(VK_LWIN, VK_DOWN)
        time.sleep(1.2)
        s, f = facts(app, "Windows+Down")
        check("Windows+Down restores the maximized window", not s["qt_maximized"] and not f["win"]["iconic"] and on_screen(f["win"]["visible"], f["win"]["monitor"]), "%s %s" % (s.get("qt_geometry"), f["win"]["visible"]))
        press(VK_LWIN, VK_UP)
        time.sleep(1.2)
        s, f = facts(app, "Windows+Up")
        check("Windows+Up maximizes it again", s["qt_maximized"] and fills_work(f), "%s vs work %s" % (f["win"]["visible"], f["win"]["work"]))

    def k_autohide():
        was = autohide()
        try:
            set_autohide(True)
            time.sleep(2.0)
            app.command("normal", settle=1.0)
            click(*point(app, "maximize"))
            time.sleep(1.0)
            s, f = facts(app, "maximized, taskbar hides itself")
            print("[Fission 180] native: %s" % json.dumps(s.get("native")))
            mon, vis = f["win"]["monitor"], f["win"]["visible"]
            check("With a hiding taskbar the maximized window leaves the screen's edge free", vis[3] < mon[3] or vis[1] > mon[1] or vis[0] > mon[0] or vis[2] < mon[2], "%s vs monitor %s" % (vis, mon))
            move((mon[0] + mon[2]) // 2, mon[3] - 1)
            time.sleep(2.0)
            s, f = facts(app, "mouse at the bottom edge")
            bar = f["win"]["taskbar"] or [0, 0, 0, 0]
            check("The hidden taskbar slides in at the screen's edge", bar[1] < mon[3] - 10, "taskbar %s" % bar)
        finally:
            set_autohide(was)
            time.sleep(1.5)

    for name, fn in (
        ("start: drag", a0_start_drag),
        ("system title bar, normal", a_system_normal),
        ("own title bar while maximized", b_switch_while_maximized),
        ("restore", c_restore),
        ("drag", d_drag),
        ("click", e_click),
        ("resize", f_resize),
        ("double-click", g_double_click),
        ("drag maximized", h_drag_maximized),
        ("Windows key", i_windows_key),
        ("Windows+arrows", j_snap_keys),
        ("auto-hide taskbar", k_autohide),
    ):
        print("[Fission 180] -- %s" % name)
        step(name, fn)


def find_exe(folder):
    names = ("fission180.exe", "freecad.exe")
    found = []
    for path in glob.glob(os.path.join(folder, "**", "*.exe"), recursive=True):
        if os.path.basename(path).lower() in names and os.sep + "bin" + os.sep in path:
            found.append(path)
    found.sort(key=lambda p: names.index(os.path.basename(p).lower()))
    return found[0] if found else None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--freecad", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args()
    out = os.path.abspath(args.out)
    os.makedirs(out, exist_ok=True)
    exe = find_exe(args.freecad)
    if not exe:
        print("[Fission 180] no bin/freecad.exe in %s" % args.freecad)
        return 1
    print("[Fission 180] FreeCAD: %s; screen %dx%d" % (exe, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)))
    app = App(exe, out)
    try:
        if app.wait(lambda s: s.get("ready") and not s.get("modal"), 180) is None:
            print("[Fission 180] Fission 180 did not come on")
            return 1
        run(app)
        quit_started = time.time()
        try:
            app.command("quit", settle=0)
        except Exception:
            pass
        try:
            app.proc.wait(30)
            check("FreeCAD quits at once (no design open)", time.time() - quit_started < 8, "%.1f s" % (time.time() - quit_started))
        except subprocess.TimeoutExpired:
            check("FreeCAD quits at once (no design open)", False, "still running after 30 s")
    finally:
        if app.proc.poll() is None:
            app.proc.kill()
        for name in ("helper.log",):
            path = os.path.join(out, name)
            if os.path.exists(path):
                print(open(path, encoding="utf-8", errors="replace").read())
    failed = [r for r in RESULTS if not r["passed"]]
    with open(os.path.join(out, "window-report.json"), "w", encoding="utf-8") as f:
        json.dump(RESULTS, f, indent=1)
    lines = ["## Fission 180's title bar on Windows", "", "%d checks, %d failed" % (len(RESULTS), len(failed)), ""]
    lines += ["- %s %s%s" % ("✅" if r["passed"] else "❌", r["name"], (" (%s)" % r["detail"]) if r["detail"] else "") for r in RESULTS]
    with open(os.path.join(out, "window-report.md"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")
    print("[Fission 180] -- all checks")
    for r in RESULTS:
        print("[Fission 180]   %s %s (%s)" % ("PASS" if r["passed"] else "FAIL", r["name"], r["detail"][:160]))
    print("[Fission 180] window summary: %d checks, %d failed" % (len(RESULTS), len(failed)))
    return 1 if failed or not RESULTS else 0


if __name__ == "__main__":
    sys.exit(main())
