# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion-style tooltips on the ribbon (wave 8, tips-ui; docs/fission180/parity/tooltips.md).

Fusion: the pointer on a ribbon command shows a small tooltip at once (its name, one line of
what it does, its shortcut); kept still on it a moment longer, the tooltip grows into the
expanded one: a picture, what the command does and when to use it, the steps, a few hints.
Moving away closes it; so do a click and Escape. The same in the ribbon's drop-down menus.
Preferences > General > Tooltips: "Show expanded tooltips" (on) and its delay.

The texts and pictures are fission180/tips (one entry per command id); a command without an
entry gets the small tooltip with its name, its key and its note (or "Not available in Fission
180 yet" for a greyed one), as before. Qt's own tooltip text stays on every button and menu
entry (setToolTip in ribbon_ui): what the card shows instead, and what shows if this module
is ever off.

How it stays cheap and out of the way: one card (a frameless Qt tool-tip window that never
takes focus or input), its pictures loaded on first show and kept, and one repeating 40 ms
poll that runs only while the pointer is on a command (it times the small and the expanded
tooltip and closes the card once the pointer is off its command, also when Qt missed a
Leave). Every handler catches its own errors.
"""

import time
import weakref

from . import tips, warn
from .compat import QtCore, QtGui, QtWidgets

SMALL_MS = 120  # the small tooltip: at once, but not for a pointer only passing over a command
POLL_MS = 40
STILL_PX = 4  # a pointer that moves less than this is still (the expanded one's wait goes on)
DEFAULT_DELAY_MS = 1000
WIDTH = tips.PICTURE_SIZE[0]  # the expanded tooltip's text is as wide as its picture
SMALL_WIDTH = 300


# -- preferences -------------------------------------------------------------------------------
def _param():
    import FreeCAD as App

    from . import prefs_core

    return App.ParamGet(prefs_core.TOOLTIPS)


def expanded_on():
    """Preferences > General > Show expanded tooltips (on by default)."""
    try:
        return bool(_param().GetBool("Expanded", True))
    except Exception:
        return True


def delay_ms():
    """Preferences > General > Expanded tooltip delay, in milliseconds (200 to 5000)."""
    try:
        value = int(_param().GetInt("DelayMs", DEFAULT_DELAY_MS))
    except Exception:
        value = DEFAULT_DELAY_MS
    return max(200, min(5000, value))


# -- the card ----------------------------------------------------------------------------------
class Card(QtWidgets.QFrame):
    """The tooltip window: small (name, key, one line, note) or expanded (+ picture, what it
    does, the steps, hints). Never takes focus, never takes a click."""

    def __init__(self):
        flags = (
            QtCore.Qt.ToolTip
            | QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.WindowDoesNotAcceptFocus
            | QtCore.Qt.WindowTransparentForInput
        )
        super().__init__(None, flags)
        self.setObjectName("Fission180Tip")
        self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating, True)
        self.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        self.setFocusPolicy(QtCore.Qt.NoFocus)
        self.mode = ""  # "" (hidden), "small", "expanded"
        self.info = None
        self._pictures = {}  # path -> QPixmap (loaded on first show, kept)
        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 9)
        layout.setSpacing(5)
        head = QtWidgets.QHBoxLayout()
        head.setSpacing(12)
        self.title = self._label("Fission180TipTitle")
        self.key = self._label("Fission180TipKey")
        self.key.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)
        head.addWidget(self.title, 1)
        head.addWidget(self.key, 0)
        layout.addLayout(head)
        self.picture = self._label("Fission180TipPicture")
        self.picture.setFixedSize(*tips.PICTURE_SIZE)
        self.picture.setAlignment(QtCore.Qt.AlignCenter)
        layout.addWidget(self.picture)
        self.summary = self._label("Fission180TipSummary", wrap=True)
        self.what = self._label("Fission180TipWhat", wrap=True)
        self.steps_title = self._label("Fission180TipStepsTitle")
        self.steps = self._label("Fission180TipSteps", wrap=True)
        self.hints = self._label("Fission180TipHints", wrap=True)
        self.note = self._label("Fission180TipNote", wrap=True)
        for widget in (
            self.summary,
            self.what,
            self.steps_title,
            self.steps,
            self.hints,
            self.note,
        ):
            layout.addWidget(widget)

    def _label(self, name, wrap=False):
        label = QtWidgets.QLabel(self)
        label.setObjectName(name)
        label.setTextFormat(QtCore.Qt.PlainText)
        label.setWordWrap(wrap)
        label.setFocusPolicy(QtCore.Qt.NoFocus)
        label.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
        return label

    def _look(self):
        from . import theme

        back = theme.MENU or "#454f61"
        text = theme.TEXT or "#f5f5f5"
        dim = theme.TEXT_DIM or "#c3cad4"
        line = theme.LINE or "#56606f"
        self.setStyleSheet(
            "QFrame#Fission180Tip { background: %s; border: 1px solid %s; }"
            "QFrame#Fission180Tip QLabel { color: %s; background: transparent; border: none; }"
            "QLabel#Fission180TipTitle { font-weight: bold; }"
            "QLabel#Fission180TipKey, QLabel#Fission180TipNote { color: %s; }"
            "QLabel#Fission180TipStepsTitle { font-weight: bold; }"
            "QLabel#Fission180TipHints { color: %s; }" % (back, line, text, dim, dim)
        )

    def picture_of(self, path):
        if not path:
            return None
        pixmap = self._pictures.get(path)
        if pixmap is None:
            pixmap = QtGui.QPixmap(path)
            if pixmap.isNull():
                return None
            self._pictures[path] = pixmap
        return pixmap

    def fill(self, info, expanded):
        """Write `info` (label, key, summary, note, tip) into the card, small or expanded."""
        self._look()
        tip = info.get("tip") if expanded else None
        self.info = info
        self.title.setText(info["label"])
        self.key.setText(info.get("key") or "")
        self.key.setVisible(bool(info.get("key")))
        summary = info.get("summary") or ""
        note = info.get("note") or ""
        pixmap = self.picture_of(tip.get("picture_path")) if tip else None
        self.picture.setVisible(pixmap is not None)
        if pixmap is not None:
            self.picture.setPixmap(pixmap)
        self.summary.setText(summary)
        self.summary.setVisible(bool(summary) and not (tip and tip.get("what")))
        what = (tip or {}).get("what") or ""
        steps = tips.numbered((tip or {}).get("steps"))
        hints = tips.bulleted((tip or {}).get("tips"))
        self.what.setText(what)
        self.what.setVisible(bool(what))
        self.steps_title.setText("How to use it")
        self.steps_title.setVisible(bool(steps))
        self.steps.setText(steps)
        self.steps.setVisible(bool(steps))
        self.hints.setText(hints)
        self.hints.setVisible(bool(hints))
        self.note.setText(note)
        self.note.setVisible(bool(note))
        width = WIDTH + 20 if tip else None
        for label in (self.summary, self.what, self.steps, self.hints, self.note):
            label.setFixedWidth(WIDTH if tip else SMALL_WIDTH)
        if not tip:
            # a small one is as narrow as its words (up to SMALL_WIDTH)
            metrics = QtGui.QFontMetrics(self.summary.font())
            longest = max([metrics.horizontalAdvance(t) for t in (summary, note) if t] + [0])
            head = QtGui.QFontMetrics(self.title.font()).horizontalAdvance(info["label"])
            head += self.key.sizeHint().width() + 16 if info.get("key") else 0
            inner = min(SMALL_WIDTH, max(head, longest) + 4)
            for label in (self.summary, self.note):
                label.setFixedWidth(inner)
            width = inner + 20
        self.mode = "expanded" if tip else "small"
        self.layout().activate()
        self.setFixedWidth(width)
        self.adjustSize()

    def show_at(self, anchor, beside):
        """Show beside `anchor` (a QRect in screen pixels), inside the screen."""
        screen = (
            QtGui.QGuiApplication.screenAt(anchor.center()) or QtGui.QGuiApplication.primaryScreen()
        )
        area = screen.availableGeometry()
        x, y = tips.place(
            (anchor.x(), anchor.y(), anchor.width(), anchor.height()),
            (self.width(), self.height()),
            (area.x(), area.y(), area.width(), area.height()),
            beside=beside,
        )
        self.move(x, y)
        if not self.isVisible():
            self.show()
        self.raise_()

    def close_card(self):
        self.mode = ""
        self.info = None
        self.hide()


# -- what is hovered ---------------------------------------------------------------------------
def info_for(entry):
    """What a card shows for a ribbon item: its label, key, summary, note and tip entry."""
    from . import ribbon_ui

    tip = tips.for_entry(entry)  # (a greyed command shows its tooltip too, as in Fusion)
    note = entry.get("note") or ""
    if not ribbon_ui.resolve(entry.get("command"), _available()):
        note = note or "Not available in Fission 180 yet"
    return {
        "label": entry.get("label", ""),
        "key": ribbon_ui.shown_key(entry),
        "summary": (tip or {}).get("summary", ""),
        "note": note,
        "tip": tip,
        "command": tips.command_id(entry),
    }


_AVAILABLE = {"names": None, "at": 0.0}


def _available():
    """FreeCAD's command names (read at most every 5 s: a hover must stay cheap)."""
    now = time.monotonic()
    if _AVAILABLE["names"] is None or now - _AVAILABLE["at"] > 5.0:
        try:
            import FreeCADGui as Gui

            _AVAILABLE["names"] = set(Gui.listCommands())
        except Exception:
            _AVAILABLE["names"] = set()
        _AVAILABLE["at"] = now
    return _AVAILABLE["names"]


class Hover(QtCore.QObject):
    """Watches the ribbon's buttons and drop-down menus and shows the card for the command
    under the pointer."""

    def __init__(self):
        super().__init__()
        self.card = None
        self.target = None  # weakref of the button or menu
        self.action = None  # the menu's QAction under the pointer
        self.entry = None
        self.beside = False
        self.rest_pos = None
        self.rest_at = 0.0
        self.suppressed = None  # (widget id, action id): clicked, until the pointer leaves it
        self.keys = _Keys(self)
        self.keys_watched = False
        self.began_at = 0.0
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(POLL_MS)
        self.timer.timeout.connect(self._tick)

    # watching
    def watch_button(self, button, entry):
        button._sf_tip_entry = entry
        button.installEventFilter(self)

    def watch_menu(self, menu):
        if not getattr(menu, "_sf_tips_watched", False):
            menu._sf_tips_watched = True
            menu._sf_tip_entries = {}
            menu.installEventFilter(self)
            menu.aboutToHide.connect(lambda: _safely(self.end))

    def watch_action(self, menu, action, entry):
        self.watch_menu(menu)
        menu._sf_tip_entries[id(action)] = (action, entry)

    # events
    def eventFilter(self, obj, event):
        try:
            if isinstance(obj, QtWidgets.QMenu):
                return self._menu_event(obj, event)
            if isinstance(obj, QtWidgets.QAbstractButton):
                return self._button_event(obj, event)
        except Exception as exc:
            warn("tooltip: %s" % exc)
        return False

    def _button_event(self, button, event):
        kind = event.type()
        entry = getattr(button, "_sf_tip_entry", None)
        if entry is None:
            return False
        if kind == QtCore.QEvent.Enter:
            self.begin(button, None, entry)
        elif kind == QtCore.QEvent.Leave:
            if self._is_target(button):
                self.end()
            self._unsuppress(button, None)
        elif kind in (QtCore.QEvent.MouseButtonPress, QtCore.QEvent.MouseButtonDblClick):
            if self._is_target(button):
                self.end(suppress=True)
        elif kind == QtCore.QEvent.Hide:
            if self._is_target(button):
                self.end()
        elif kind == QtCore.QEvent.ToolTip:
            # Qt's own tooltip never shows over the card (its text stays on the button)
            if not self._is_target(button) and not self._is_suppressed(button, None):
                self.begin(button, None, entry, show_now=True)
            return True
        return False

    def _menu_event(self, menu, event):
        kind = event.type()
        if kind == QtCore.QEvent.MouseMove:
            pos = event.position().toPoint() if hasattr(event, "position") else event.pos()
            self._menu_hover(menu, menu.actionAt(pos))
        elif kind == QtCore.QEvent.Leave:
            if self._is_target(menu):
                self.end()
            self.suppressed = None
        elif kind in (
            QtCore.QEvent.MouseButtonPress,
            QtCore.QEvent.MouseButtonRelease,
            QtCore.QEvent.ContextMenu,
        ):
            if self._is_target(menu):
                self.end(suppress=True)
        elif kind == QtCore.QEvent.Hide:
            if self._is_target(menu):
                self.end()
        elif kind == QtCore.QEvent.ToolTip:
            pos = event.pos()
            action = menu.actionAt(pos)
            if action is not None and id(action) in getattr(menu, "_sf_tip_entries", {}):
                return True  # the card shows it (or nothing has to be said)
        return False

    def _menu_hover(self, menu, action):
        found = getattr(menu, "_sf_tip_entries", {}).get(id(action)) if action else None
        if found is None:
            if self._is_target(menu):
                self.end()
            return
        if self._is_target(menu) and self.action is action:
            return
        if self._is_suppressed(menu, action):
            return
        self.end()
        self.begin(menu, action, found[1])

    # state
    def _is_target(self, widget):
        target = self.target() if self.target is not None else None
        return target is not None and target is widget

    def _is_suppressed(self, widget, action):
        return self.suppressed == (id(widget), id(action) if action is not None else None)

    def _unsuppress(self, widget, action):
        if self._is_suppressed(widget, action):
            self.suppressed = None

    def begin(self, widget, action, entry, show_now=False):
        if self._is_suppressed(widget, action):
            return
        if QtWidgets.QApplication.mouseButtons() != QtCore.Qt.NoButton:
            return  # (a drag goes on)
        self.target = weakref.ref(widget)
        self.action = action
        self.entry = entry
        self.beside = isinstance(widget, QtWidgets.QMenu)
        self.rest_pos = QtGui.QCursor.pos()
        self.rest_at = time.monotonic() - (SMALL_MS / 1000.0 if show_now else 0.0)
        self.began_at = self.rest_at
        if self.card is not None and self.card.mode:
            self.card.close_card()
        if not self.timer.isActive():
            self.timer.start()
        if show_now:
            self._tick()

    def end(self, suppress=False):
        target = self.target() if self.target is not None else None
        if suppress and target is not None:
            self.suppressed = (id(target), id(self.action) if self.action is not None else None)
        self.target = None
        self.action = None
        self.entry = None
        if self.timer.isActive():
            self.timer.stop()
        if self.card is not None and self.card.mode:
            self.card.close_card()
        self._watch_keys(False)

    def _watch_keys(self, on):
        app = QtWidgets.QApplication.instance()
        if app is None or on == self.keys_watched:
            return
        if on:
            app.installEventFilter(self.keys)
        else:
            app.removeEventFilter(self.keys)
        self.keys_watched = on

    def _anchor(self, widget):
        """The screen rectangle the card goes beside, or None when the pointer is off it."""
        if self.action is None:
            top_left = widget.mapToGlobal(QtCore.QPoint(0, 0))
            rect = QtCore.QRect(top_left, widget.size())
            return rect if widget.isVisible() and rect.contains(QtGui.QCursor.pos()) else None
        row = widget.actionGeometry(self.action)
        if not widget.isVisible() or row.isNull():
            return None
        row_global = QtCore.QRect(widget.mapToGlobal(row.topLeft()), row.size())
        if not row_global.contains(QtGui.QCursor.pos()):
            return None
        menu_rect = QtCore.QRect(widget.mapToGlobal(QtCore.QPoint(0, 0)), widget.size())
        return QtCore.QRect(menu_rect.x(), row_global.y(), menu_rect.width(), row_global.height())

    def _tick(self):
        try:
            widget = self.target() if self.target is not None else None
            if widget is None:
                self.end()
                return
            try:
                anchor = self._anchor(widget)
            except RuntimeError:  # (the button was deleted: the ribbon was rebuilt)
                anchor = None
            if anchor is None or QtWidgets.QApplication.mouseButtons() != QtCore.Qt.NoButton:
                self.end()
                return
            now = time.monotonic()
            pos = QtGui.QCursor.pos()
            if (pos - self.rest_pos).manhattanLength() > STILL_PX:
                self.rest_pos, self.rest_at = pos, now
                if self.card is None or not self.card.mode:
                    self.began_at = now
            mode = self.card.mode if self.card is not None else ""
            if not mode and (now - self.began_at) * 1000.0 >= SMALL_MS:
                self._show(anchor, expanded=False)
            elif mode == "small" and expanded_on() and (now - self.rest_at) * 1000.0 >= delay_ms():
                info = info_for(self.entry)
                if info["tip"]:
                    self._show(anchor, expanded=True, info=info)
        except Exception as exc:
            warn("tooltip: %s" % exc)
            self.end()

    def _show(self, anchor, expanded, info=None):
        info = info or info_for(self.entry)
        if not expanded and self.action is not None and not (info["summary"] or info["note"]):
            # a menu row already says its name and key: nothing to add
            return
        if self.card is None:
            self.card = Card()
        self.card.fill(info, expanded)
        self.card.show_at(anchor, self.beside)
        self._watch_keys(True)


class _Keys(QtCore.QObject):
    """Escape closes a tooltip that shows (the key goes on to what it was for: a menu closes,
    a command is cancelled, as without the tooltip). Watches the app only while one shows."""

    def __init__(self, owner):
        super().__init__()
        self.owner = owner

    def eventFilter(self, obj, event):
        try:
            if event.type() == QtCore.QEvent.KeyPress and event.key() == QtCore.Qt.Key_Escape:
                card = self.owner.card
                if card is not None and card.mode:
                    self.owner.end(suppress=True)
        except Exception as exc:
            warn("tooltip: %s" % exc)
        return False


_HOVER = []


def hover():
    if not _HOVER:
        _HOVER.append(Hover())
    return _HOVER[0]


def _safely(function, *args):
    try:
        function(*args)
    except Exception as exc:
        warn("tooltip: %s" % exc)


# -- what ribbon_ui calls ----------------------------------------------------------------------
def watch_button(button, entry):
    """A ribbon button (a group's big icon or a pinned one) gets Fusion's tooltips."""
    _safely(hover().watch_button, button, entry)


def watch_action(menu, action, entry):
    """A drop-down menu's entry gets Fusion's tooltips."""
    _safely(hover().watch_action, menu, action, entry)


def card():
    """The tooltip card (None before the first one showed): for the GUI tests."""
    return hover().card


def state():
    """What shows now: {"mode": "" | "small" | "expanded", "label": ..., "command": ...}."""
    found = hover().card
    if found is None or not found.mode or not found.isVisible():
        return {"mode": "", "label": "", "command": None}
    info = found.info or {}
    return {"mode": found.mode, "label": info.get("label", ""), "command": info.get("command")}


def close():
    """Close any tooltip (a command started, the ribbon changed)."""
    _safely(hover().end)
