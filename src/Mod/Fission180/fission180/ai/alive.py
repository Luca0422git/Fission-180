# SPDX-License-Identifier: LGPL-2.1-or-later
"""The window stays alive during a long AI call (wave 8, builder ai-speed; parity:
docs/fission180/parity/ai.md, "Wave 8: the AI works fast, and the window stays alive").

An AI call runs on the window's thread (bridge.py), so FreeCAD can be touched; meanwhile the
window does not answer, and Windows marks a window that has not looked at its messages for
5 s "Not responding". A long call's tool code calls progress.step() at safe points; there,
at most every progress.PUMP_EVERY seconds, pump() lets the window live for a moment:

  * it shows the working line over the 3D view, "AI: working on compare_to_reference (12 s):
    comparing faces 1,200 of 3,209", with a Stop button (and the same line on the AI panel's
    Activity tab, with its own Stop), after the call has run progress.SHOW_AFTER seconds;
  * it lets Qt handle what is waiting (QApplication.processEvents): the window repaints,
    moves, resizes, and Windows sees it answer;
  * while it does, an event filter on the application decides what may happen:
      - input (mouse, keys, wheel, touch, drag and drop, context menus) reaches only the Stop
        buttons (and a question box the call itself opened); anywhere else it is dropped,
        and the line says why ("busy with the AI's call: wait, or press Stop");
      - timers wait: a timer event for anything but a widget or a window (QTimer and
        single-shot timers, FreeCAD's AutoSaver, Fission 180's recovery copies, the bridge's
        own pump, the chat panel's, the browser's and timeline's polls, Coin's sensors) is
        dropped, and Qt sends it again at its next interval: postponed, never lost. Widget
        and window timers (a blinking cursor, Qt's own repaint requests) run;
      - a zero-delay QTimer.singleShot(0, fn) started from Python during a call becomes a
        1 ms timer (_defer_zero), so Fission 180's deferred follow-ups also wait for the end of
        the call instead of running in the middle of it;
      - closing the main window is refused while the call runs.
  * Stop asks the call to stop at its next safe point (progress.request_stop): the
    executor takes back its half-made change and answers in words.

What it cannot do: one long OpenCASCADE call (a boolean, isValid() of 3,000 faces) is not
Python and cannot be split: the window waits for it (Windows may show "Not responding" if it
takes over 5 s). Re-entrancy checked (docs/fission180/sessions/ai-speed.md lists each one):
a pump never runs inside a pump, nor inside a recompute (progress.set_guard), nor while a
modal question of the call is open (its own loop; no step() is called meanwhile); the
bridge's pump and the chat's are timers (postponed) and refuse a second call anyway.
"""

import time

import FreeCAD as App
import FreeCADGui as Gui

from .. import log, warn
from ..compat import QtCore, QtGui, QtWidgets
from . import progress

BAR_NAME = "Fission180AIWorking"
STOP_NAME = "Fission180AIWorkingStop"
PANEL_STOP_NAME = "Fission180AIActivityStop"
PUMP_MS = 50  # at most this long in one look at the window
REFUSED_SHOW_S = 2.5  # how long the line says a click was refused
TEST_TICK = None  # tests: function(call) run at every pump, while input is filtered

_state = {
    "installed": False,
    "filter": None,
    "bar": None,
    "pumping": False,
    "call": None,
    "cursor": False,  # the busy cursor is ours to take back
    "refused_at": 0.0,  # when a click outside Stop was last dropped
    "stats": None,  # per call: paints, timers held, inputs dropped, pumps (tests read it)
}

_INPUT = None  # the event types that are a person's input (made on first use)
_PRESSES = None


def _input_types():
    global _INPUT, _PRESSES
    if _INPUT is None:
        E = QtCore.QEvent
        names = (
            "MouseButtonPress",
            "MouseButtonRelease",
            "MouseButtonDblClick",
            "MouseMove",
            "Wheel",
            "KeyPress",
            "KeyRelease",
            "ShortcutOverride",
            "Shortcut",
            "ContextMenu",
            "TabletPress",
            "TabletMove",
            "TabletRelease",
            "TouchBegin",
            "TouchUpdate",
            "TouchEnd",
            "DragEnter",
            "DragMove",
            "Drop",
            "NativeGesture",
            "Gesture",
        )
        _INPUT = frozenset(getattr(E, n) for n in names if hasattr(E, n))
        _PRESSES = frozenset(
            getattr(E, n)
            for n in ("MouseButtonPress", "MouseButtonDblClick", "KeyPress", "Wheel", "ContextMenu")
            if hasattr(E, n)
        )
    return _INPUT


def _new_stats():
    return {"paints": 0, "timers_held": 0, "inputs_dropped": 0, "presses_dropped": 0,
            "closes_refused": 0, "pumps": 0, "shown": False, "lines": []}  # fmt: skip


def stats():
    """What the last (or current) call's pumps did: {paints, timers_held, inputs_dropped,
    presses_dropped, closes_refused, pumps, shown, lines} (tests)."""
    return dict(_state["stats"] or _new_stats())


# -- the filter ----------------------------------------------------------------------------------
class _Filter(QtCore.QObject):
    """On the application while a call runs. It acts while a pump lets the window live, and
    whenever else Qt handles events in the middle of the call (FreeCAD's own recompute lets
    the window handle what is waiting every 0.1 s between steps: Base::SequencerBar), except
    while a question box is open (its own loop: the person answers it, the tests' timers click
    it)."""

    def eventFilter(self, obj, event):
        if not _state["pumping"]:
            if _state["call"] is None:
                return False
            try:
                if QtWidgets.QApplication.activeModalWidget() is not None:
                    return False
            except Exception:
                return False
        try:
            return _decide(obj, event)
        except Exception:
            return False  # (never let a filter error drop or break an event)


def _allowed_widgets():
    found = []
    bar = _state["bar"]
    if bar is not None:
        found.append(bar)
    try:
        from .. import ai_ui

        page = ai_ui.panel()
        button = getattr(page, "stop_button", None) if page is not None else None
        if button is not None:
            found.append(button)
    except Exception:
        pass
    modal = QtWidgets.QApplication.activeModalWidget()
    if modal is not None:
        found.append(modal)  # (a question the call itself opened must be answerable)
    return found


def _inside(obj, widgets):
    for widget in widgets:
        try:
            if obj is widget or (isinstance(obj, QtWidgets.QWidget) and widget.isAncestorOf(obj)):
                return True
        except RuntimeError:
            continue
    return False


def _at_point(event, widgets):
    """A window-level mouse event (Qt hands it to the window first) over an allowed widget."""
    try:
        point = event.globalPosition().toPoint()
    except Exception:
        return False
    for widget in widgets:
        try:
            if widget.isVisible() and widget.rect().contains(widget.mapFromGlobal(point)):
                return True
            if isinstance(widget, QtWidgets.QAbstractButton) and widget.isDown():
                return True  # (its release, wherever the pointer went)
        except RuntimeError:
            continue
    return False


def _decide(obj, event):
    """True: the event is dropped (filtered). The rules are in the module's docstring."""
    kind = event.type()
    stats = _state["stats"]
    E = QtCore.QEvent
    if kind == E.Timer:
        if isinstance(obj, (QtWidgets.QWidget, QtGui.QWindow)):
            return False
        stats["timers_held"] += 1
        return True
    if kind == E.Paint:
        stats["paints"] += 1
        return False
    if kind in _input_types():
        widgets = _allowed_widgets()
        if _inside(obj, widgets):
            return False
        if isinstance(obj, QtGui.QWindow):  # (Qt hands input to the window first)
            modal = QtWidgets.QApplication.activeModalWidget()
            if modal is not None and _same(obj, modal.windowHandle()):
                return False
            if _mouse(kind) and _at_point(event, widgets):
                return False
        stats["inputs_dropped"] += 1
        if kind in _PRESSES:
            stats["presses_dropped"] += 1
            _state["refused_at"] = time.monotonic()
        return True
    if kind == E.Close:
        main = Gui.getMainWindow()
        if _same(obj, main) or _same(obj, main.windowHandle()):
            event.ignore()
            stats["closes_refused"] += 1
            _state["refused_at"] = time.monotonic()
            return True
    return False


def _same(a, b):
    """The same Qt object (Python wrappers of one C++ object compared by its address)."""
    if a is None or b is None:
        return False
    if a is b:
        return True
    try:
        import shiboken6

        return shiboken6.getCppPointer(a)[0] == shiboken6.getCppPointer(b)[0]
    except Exception:
        return False


def _mouse(kind):
    E = QtCore.QEvent
    return kind in (
        E.MouseButtonPress,
        E.MouseButtonRelease,
        E.MouseButtonDblClick,
        E.MouseMove,
        E.Wheel,
    )


# -- zero-delay timers wait for the end of the call ------------------------------------------------
def _defer_zero():
    """QTimer.singleShot(0, fn) posts fn as an event Qt runs in the very next look at the
    window, so a follow-up a tool's change posted would run in the middle of the call; while
    a call runs it is started as a 1 ms timer instead, which the filter holds until the call
    is over. Installed once; a wrapper (the GUI tests' harness has one) is kept inside."""
    current = QtCore.QTimer.singleShot
    if getattr(current, "_fission180_defers", False):
        return

    def single_shot(*args, **kwargs):
        if args and type(args[0]) is int and args[0] <= 0 and progress.working():
            args = (1,) + tuple(args[1:])
        return current(*args, **kwargs)

    single_shot._fission180_defers = True
    QtCore.QTimer.singleShot = staticmethod(single_shot)


# -- the working line ------------------------------------------------------------------------------
class WorkingBar(QtWidgets.QFrame):
    """The working line over the 3D view, with Stop."""

    def __init__(self, parent):
        super().__init__(parent)
        self.setObjectName(BAR_NAME)
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        row = QtWidgets.QHBoxLayout(self)
        row.setContentsMargins(12, 6, 6, 6)
        row.setSpacing(10)
        self.label = QtWidgets.QLabel("")
        self.label.setObjectName("Fission180AIWorkingText")
        row.addWidget(self.label, 1)
        self.stop_button = QtWidgets.QPushButton("Stop")
        self.stop_button.setObjectName(STOP_NAME)
        self.stop_button.setToolTip(
            "Stop the AI's call at its next safe point; what it did is taken back"
        )
        self.stop_button.setCursor(QtCore.Qt.PointingHandCursor)
        self.stop_button.clicked.connect(lambda *_: press_stop())
        row.addWidget(self.stop_button)
        self._style()

    def _style(self):
        try:
            from .. import theme

            self.setStyleSheet(
                "#%s { background: %s; border: 1px solid %s; border-radius: 6px; }"
                "#Fission180AIWorkingText { color: %s; }"
                "#%s { padding: 3px 14px; }"
                % (BAR_NAME, theme.CHROME, theme.ACCENT, theme.TEXT, STOP_NAME)
            )
        except Exception:
            pass

    def place(self):
        """Top middle of the 3D view."""
        main = self.parentWidget()
        area = main.findChild(QtWidgets.QMdiArea) if main is not None else None
        self.adjustSize()
        width = max(self.sizeHint().width(), 360)
        if area is not None and area.isVisible():
            top_left = area.mapTo(main, QtCore.QPoint(0, 0))
            width = min(width, max(200, area.width() - 40))
            x = top_left.x() + (area.width() - width) // 2
            y = top_left.y() + 14
        else:
            x, y = max(0, (main.width() - width) // 2), 60
        self.setGeometry(x, y, width, self.sizeHint().height())


def _bar():
    bar = _state["bar"]
    try:
        if bar is not None:
            bar.isVisible()
            return bar
    except RuntimeError:
        pass
    main = Gui.getMainWindow()
    bar = _state["bar"] = WorkingBar(main)
    bar.hide()
    return bar


def press_stop():
    """The Stop buttons: the call stops at its next safe point."""
    try:
        if progress.request_stop("stopped by the person in Fission 180"):
            log("AI: Stop pressed")
            _show_line(progress.current())
    except Exception as exc:
        warn("AI Stop: %s" % exc)


def _line_text(status):
    text = progress.line(status)
    if time.monotonic() - _state["refused_at"] < REFUSED_SHOW_S:
        text += "  (busy with the AI's call: wait, or press Stop)"
    return text


def _show_line(status):
    if status is None:
        return
    text = _line_text(status)
    stats = _state["stats"]
    try:
        bar = _bar()
        bar.label.setText(text)
        bar.stop_button.setEnabled(not status.get("stopping"))
        bar.place()
        if not bar.isVisible():
            bar.show()
            if stats is not None:
                stats["shown"] = True
            if not _state["cursor"]:
                QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.BusyCursor)
                _state["cursor"] = True
        bar.raise_()
        if stats is not None and (not stats["lines"] or stats["lines"][-1] != text):
            stats["lines"].append(text)
            del stats["lines"][:-50]
    except RuntimeError:
        pass
    try:
        from .. import ai_ui

        page = ai_ui.panel()
        if page is not None:
            page.show_working(text, not status.get("stopping"))
    except Exception:
        pass


def _hide_line():
    try:
        bar = _state["bar"]
        if bar is not None:
            bar.hide()
    except RuntimeError:
        pass
    if _state["cursor"]:
        try:
            QtWidgets.QApplication.restoreOverrideCursor()
        except Exception:
            pass
        _state["cursor"] = False
    try:
        from .. import ai_ui

        page = ai_ui.panel()
        if page is not None:
            page.show_working("", False)
    except Exception:
        pass


# -- the call's life -------------------------------------------------------------------------------
def pump(call):
    """progress's pump: show the line, let the window live for a moment (see the module)."""
    if _state["pumping"] or not App.GuiUp:
        return
    status = progress.current()
    if status is None:
        return
    if status["seconds"] >= progress.SHOW_AFTER or status.get("stopping"):
        _show_line(status)
    _state["pumping"] = True
    try:
        stats = _state["stats"]
        if stats is not None:
            stats["pumps"] += 1
        flags = QtCore.QEventLoop.AllEvents | QtCore.QEventLoop.ExcludeSocketNotifiers
        QtWidgets.QApplication.processEvents(flags, PUMP_MS)
        if TEST_TICK is not None:
            try:
                TEST_TICK(call)
            except progress.Stopped:
                raise
            except Exception as exc:
                warn("AI alive test hook: %s" % exc)
    finally:
        _state["pumping"] = False


def _event(kind, call):
    if kind == "begin":
        _state["call"] = call
        _state["stats"] = _new_stats()
        _state["refused_at"] = 0.0
        if _state["filter"] is None:
            _state["filter"] = _Filter()
        QtWidgets.QApplication.instance().installEventFilter(_state["filter"])
    elif kind == "end":
        try:
            QtWidgets.QApplication.instance().removeEventFilter(_state["filter"])
        except Exception:
            pass
        _hide_line()
        _state["call"] = None
        stats = _state["stats"]
        if stats is not None and (stats["presses_dropped"] or stats["closes_refused"]):
            log(
                "AI: %s: %d click(s) / key(s) refused during the call (Fission 180 was busy)"
                % (call.get("tool"), stats["presses_dropped"] + stats["closes_refused"])
            )


def install():
    """Fission 180's window is up: long AI calls keep it alive (ai_ui.enable)."""
    if _state["installed"]:
        return
    try:
        _defer_zero()
        progress.set_pump(pump)
        progress.add_listener(_event)
        _state["installed"] = True
    except Exception as exc:
        warn("AI: the working line could not be set up: %s" % exc)


def uninstall():
    progress.set_pump(None)
    progress.remove_listener(_event)
    _state["installed"] = False
