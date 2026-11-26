# SPDX-License-Identifier: LGPL-2.1-or-later
"""Runs inside FreeCAD's window for tools/fission180/windows_window_check.py (the check of
Fission 180's own title bar on a real Windows desktop, Luca 2026-11-26: "If i even look at
the top bar wrong, the window glitches out ... I cant resize the window, nor move it around
... when fission is in full screen, i cant access my hidden taskbar. and pressing the windows
key causes the window to move randomly").

FreeCAD runs normally; this script switches Fission 180 on and then, every 100 ms, writes what
Qt thinks of the main window into state.json (its state, its geometry, where on the screen the
top row's empty part, the window buttons and the resize grips are, in the screen's own
pixels). The checker clicks, drags and presses keys like a person and asks this script for a
few things through command.json ({"id": n, "do": ..., "arg": ...}): switch the title bar,
maximize, restore, put the window somewhere, quit. Everything it does is logged to
helper.log (FreeCAD's own output has no console on Windows).
"""

import json
import os
import time
import traceback

import FreeCAD as App
import FreeCADGui as Gui
from PySide import QtCore, QtWidgets

OUT = os.environ.get("FISSION180_WINDOW_OUT") or App.getUserAppDataDir()
STATE = os.path.join(OUT, "state.json")
COMMAND = os.path.join(OUT, "command.json")
LOG = os.path.join(OUT, "helper.log")
PARAMS = "User parameter:BaseApp/Preferences/Mod/Fission180/Preferences"

_S = {"ready": False, "done": set(), "ack": 0, "started": time.time(), "timer": None, "notes": [], "events": {}, "last": None}


class _Input(QtCore.QObject):
    """Counts the mouse and key presses Qt delivers (does the checker's input arrive?)."""

    KINDS = {
        QtCore.QEvent.MouseButtonPress: "press",
        QtCore.QEvent.MouseButtonRelease: "release",
        QtCore.QEvent.MouseButtonDblClick: "double",
        QtCore.QEvent.KeyPress: "key",
        QtCore.QEvent.NonClientAreaMouseButtonPress: "nc_press",
    }

    def eventFilter(self, obj, event):
        try:
            kind = self.KINDS.get(event.type())
            if kind and isinstance(obj, QtWidgets.QWidget):
                _S["events"][kind] = _S["events"].get(kind, 0) + 1
                pos = event.globalPosition().toPoint() if hasattr(event, "globalPosition") else None
                _S["last"] = [kind, type(obj).__name__, obj.objectName(), [pos.x(), pos.y()] if pos else None]
        except Exception:
            pass
        return False


_INPUT = _Input()


def log(text):
    line = "[Fission 180] window helper %.1fs: %s" % (time.time() - _S["started"], text)
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(line + "\n")
    except Exception:
        pass
    App.Console.PrintMessage(line + "\n")


def _main():
    return Gui.getMainWindow()


def _native(widget, point):
    """A point of `widget` in the screen's own pixels (what Windows' mouse and window rects
    use): Qt's global position scaled by the screen's device pixel ratio."""
    g = widget.mapToGlobal(point)
    screen = widget.screen()
    dpr = screen.devicePixelRatio()
    sg = screen.geometry()
    return [int(round(sg.x() + (g.x() - sg.x()) * dpr)), int(round(sg.y() + (g.y() - sg.y()) * dpr))]


def _centre(widget):
    return _native(widget, widget.rect().center())


def _row():
    from fission180 import titlebar_ui

    return titlebar_ui._row()


def _row_empty(row):
    """The middle of the longest run of the top row where a press reaches the row itself (no
    button, tab or field under it), at half its height."""
    y = row.height() // 2
    best, start = (0, -1, -1), None
    for x in range(0, row.width() + 1):
        child = row.childAt(x, y) if x < row.width() else QtWidgets.QPushButton()
        empty = child is None or type(child) in (QtWidgets.QWidget, QtWidgets.QFrame, QtWidgets.QLabel)
        if empty and start is None:
            start = x
        elif not empty and start is not None:
            if x - start > best[0]:
                best = (x - start, start, x)
            start = None
    if best[0] <= 0:
        return None
    return _native(row, QtCore.QPoint((best[1] + best[2]) // 2, y)) + [best[0]]


def _state():
    from fission180 import titlebar_ui

    mw = _main()
    out = {
        "t": round(time.time() - _S["started"], 2),
        "ready": _S["ready"],
        "ack": _S["ack"],
        "notes": _S["notes"][-20:],
    }
    if mw is None:
        return out
    g, f = mw.geometry(), mw.frameGeometry()
    state = mw.windowState()
    out.update(
        hwnd=int(mw.winId()),
        qt_state=int(state.value if hasattr(state, "value") else state),
        qt_maximized=bool(state & QtCore.Qt.WindowMaximized),
        qt_fullscreen=bool(state & QtCore.Qt.WindowFullScreen),
        qt_minimized=bool(state & QtCore.Qt.WindowMinimized),
        qt_geometry=[g.x(), g.y(), g.width(), g.height()],
        qt_frame=[f.x(), f.y(), f.width(), f.height()],
        frameless=bool(mw.windowFlags() & QtCore.Qt.FramelessWindowHint),
        dpr=mw.screen().devicePixelRatio(),
        mode=titlebar_ui.mode(),
        wanted=titlebar_ui.wanted(),
        active=QtWidgets.QApplication.activeWindow() is mw,
    )
    points = {}
    row = _row()
    if row is not None and row.isVisible():
        empty = _row_empty(row)
        if empty:
            points["row_empty"] = empty[:2]
            out["row_empty_width"] = empty[2]
        out["row_rect"] = _native(row, QtCore.QPoint(0, 0)) + _native(row, QtCore.QPoint(row.width(), row.height()))
    controls = titlebar_ui._state.get("controls")
    if controls is not None and controls.isVisible():
        for name, button in controls.buttons.items():
            points[name.lower()] = _centre(button)
        out["maximize_tip"] = controls.buttons["Maximize"].toolTip()
    for grip in titlebar_ui._state.get("grips") or []:
        try:
            if grip.isVisible():
                points["grip_" + grip.name] = _centre(grip)
        except RuntimeError:
            pass
    out["points"] = points
    out["events"] = dict(_S["events"])
    out["last_event"] = _S["last"]
    app = QtWidgets.QApplication.instance()
    modal, popup = app.activeModalWidget(), app.activePopupWidget()
    out["modal"] = [type(modal).__name__, modal.objectName(), modal.windowTitle()] if modal is not None else None
    out["popup"] = [type(popup).__name__, popup.objectName()] if popup is not None else None
    out["active_window"] = type(app.activeWindow()).__name__ if app.activeWindow() is not None else None
    tops = []
    for w in app.topLevelWidgets():
        try:
            if w.isVisible() and w is not mw:
                g = w.geometry()
                tops.append([type(w).__name__, w.objectName(), w.windowTitle()[:40], [g.x(), g.y(), g.width(), g.height()], bool(w.isModal())])
        except RuntimeError:
            pass
    out["other_windows"] = tops[:12]
    out["enabled"] = mw.isEnabled()
    try:
        from fission180 import titlebar_win

        flt = titlebar_win._state.get("filter")
        out["native"] = {
            "on": bool(flt is not None and flt.on),
            "installed": titlebar_win._state.get("installed"),
            "last_max": titlebar_win._state.get("last_max"),
        }
    except Exception as exc:
        out["native"] = str(exc)
    return out


def _write():
    try:
        data = _state()
        tmp = STATE + ".tmp"
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f)
        os.replace(tmp, STATE)
    except Exception:
        log("state: %s" % traceback.format_exc())


def _command():
    try:
        if not os.path.exists(COMMAND):
            return
        with open(COMMAND, encoding="utf-8") as f:
            cmd = json.load(f)
    except Exception:
        return  # (half written: the next tick reads it)
    cid = cmd.get("id")
    if cid in _S["done"]:
        return
    _S["done"].add(cid)
    do, arg = cmd.get("do"), cmd.get("arg")
    log("command %s: %s %s" % (cid, do, arg))
    mw = _main()
    try:
        if do == "titlebar":
            from fission180 import titlebar_ui

            App.ParamGet(PARAMS).SetString(titlebar_ui.KEY, arg)
            titlebar_ui.apply()
        elif do == "maximize":
            mw.showMaximized()
        elif do == "normal":
            mw.showNormal()
        elif do == "geometry":
            mw.setGeometry(*[int(v) for v in arg])
        elif do == "activate":
            mw.raise_()
            mw.activateWindow()
        elif do == "quit":
            for name in list(App.listDocuments()):
                App.closeDocument(name)
            QtCore.QTimer.singleShot(200, mw.close)
        else:
            log("unknown command %r" % do)
    except Exception:
        log("command %s failed: %s" % (cid, traceback.format_exc()))
        _S["notes"].append("command %s failed" % cid)
    _S["ack"] = cid
    _write()


def _tick():
    _command()
    _write()


def _wait_ready(tries=[0]):
    try:
        from fission180 import titlebar_ui

        tries[0] += 1
        # (GitHub's Windows runner has no real graphics card: FreeCAD greets it with its
        # "Invalid OpenGL Version" box, a modal dialog that disables the main window and so
        # every click the checker makes. Closed here, as a person would.)
        modal = QtWidgets.QApplication.instance().activeModalWidget()
        if isinstance(modal, QtWidgets.QDialog):
            log("closing a dialog in the way: %s %r" % (modal.objectName(), modal.windowTitle()))
            modal.accept()
            QtCore.QTimer.singleShot(300, _wait_ready)
            return
        on = titlebar_ui._state.get("on") and titlebar_ui._state.get("controls") is not None
        if on:
            _S["ready"] = True
            log("ready: Fission 180 is on, title bar %s" % titlebar_ui.mode())
            return
        if tries[0] > 600:
            log("Fission 180 did not come on in 60 s")
            _S["notes"].append("not ready")
            return
    except Exception:
        log("wait: %s" % traceback.format_exc())
    QtCore.QTimer.singleShot(100, _wait_ready)


def _start():
    try:
        log("activating Fission 180")
        Gui.activateWorkbench("Fission180Workbench")
    except Exception:
        log("activate: %s" % traceback.format_exc())
    QtWidgets.QApplication.instance().installEventFilter(_INPUT)
    timer = QtCore.QTimer()
    timer.setInterval(100)
    timer.timeout.connect(_tick)
    timer.start()
    _S["timer"] = timer
    _wait_ready()


log("started (FreeCAD %s)" % ".".join(App.Version()[:3]))
QtCore.QTimer.singleShot(1000, _start)
