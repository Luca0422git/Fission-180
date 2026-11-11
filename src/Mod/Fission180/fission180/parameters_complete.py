# SPDX-License-Identifier: LGPL-2.1-or-later
"""Parameter names offered while typing in a value box, like Fusion.

Fusion: type `S` in a dimension box and a list with Support_Width opens under the box; Enter
or Tab fills the name in, the arrows choose another one, Esc closes the list. Fission 180
had no such list (book parity report, Metric Bolt and Drone: "typing S shows no parameter
autocomplete list").

One watcher for the whole application (install(), on QApplication.focusChanged: it runs
when the keyboard focus moves, not on every event): a value box that gets the focus gets
the list. A value box is a line edit marked with the dynamic property `fission180_formula`
(taskui.DistanceField's box, the Parameters dialog's cells), the box of a sketch dimension
or of a drawing tool, the box next to a handle in the 3D view, or a pattern's Quantity.

suggestions() and fragment() are pure Python (unit tested).
"""

import re

MARK = "fission180_formula"
MAX_ROWS = 8
# line edits that are value boxes by their class or object name (other builders' widgets:
# nothing to change in their files)
VALUE_BOX_CLASSES = ("ArrowValueBox", "ValueBox")
VALUE_BOX_NAMES = ("Fission180DimensionValue",)
VALUE_BOX_PARENTS = ("CountBox",)

_FRAGMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*$")


def fragment(text, cursor):
    """(start, word): the name being typed just before the cursor, or (cursor, "") when
    the cursor is not at the end of a name (after a number, a unit, an operator, a dot)."""
    before = text[:cursor]
    match = _FRAGMENT.search(before)
    if not match:
        return cursor, ""
    start = match.start()
    if cursor < len(text) and (text[cursor].isalnum() or text[cursor] == "_"):
        return cursor, ""  # in the middle of a word
    lead = before[:start].rstrip()
    if start and before[start - 1] == ".":
        return cursor, ""  # another object's property
    if lead and (lead[-1].isdigit() or lead[-1] == ".") and lead == before[:start]:
        return cursor, ""  # "5m": a unit glued to its number
    return start, match.group(0)


def suggestions(word, names, limit=MAX_ROWS):
    """The parameter names to offer for the typed `word`: the ones that start with it
    first (in the design's order), then the ones that contain it. Case does not matter.
    Nothing when the word is already one of the names and no other name starts with it."""
    if not word:
        return []
    low = word.lower()
    starts = [n for n in names if n.lower().startswith(low)]
    inside = [n for n in names if low in n.lower() and n not in starts]
    found = starts + inside
    if found == [word]:
        return []
    return found[:limit]


def complete(text, cursor, name):
    """(new text, new cursor) with the name being typed replaced by `name`."""
    start, _word = fragment(text, cursor)
    return text[:start] + name + text[cursor:], start + len(name)


# -- the list under the box ------------------------------------------------------------------------
_state = {"installed": False, "popup": None, "edit": None, "keys": None, "filter": None}
_state["names"] = None  # a function that gives the names to offer (tests), else the design's


def install():
    """Watch the keyboard focus (once). Safe to call again."""
    if _state["installed"]:
        return
    try:
        from .compat import QtWidgets

        app = QtWidgets.QApplication.instance()
        if app is None:
            return
        app.focusChanged.connect(_focus_changed)
        _state["installed"] = True
    except Exception as exc:
        from . import warn

        warn("parameter names while typing are off: %s" % exc)


def edit_of(widget):
    """The line edit of the value box `widget`, or None when it is no value box. A spin box
    (FreeCAD's number field, a pattern's Quantity) takes the keyboard focus itself and
    hands the keys to the line edit inside it."""
    from .compat import QtWidgets

    try:
        if isinstance(widget, QtWidgets.QAbstractSpinBox):
            if widget.property(MARK) or type(widget).__name__ in VALUE_BOX_PARENTS:
                return widget.findChild(QtWidgets.QLineEdit)
            return None
        return widget if is_value_box(widget) else None
    except Exception:
        return None


def is_value_box(widget):
    """True for a line edit a value or formula is typed in (see the module's text)."""
    from .compat import QtWidgets

    try:
        if not isinstance(widget, QtWidgets.QLineEdit):
            return False
        if widget.property(MARK):
            return True
        if type(widget).__name__ in VALUE_BOX_CLASSES and type(widget).__module__.startswith(
            "fission180"
        ):
            return True
        if widget.objectName() in VALUE_BOX_NAMES:
            return True
        parent = widget.parent()
        if parent is not None and (
            parent.property(MARK) or type(parent).__name__ in VALUE_BOX_PARENTS
        ):
            return True
    except Exception:
        return False
    return False


def _names():
    """The parameter names of the active design (a formula can name these)."""
    custom = _state["names"]
    if custom is not None:
        return list(custom())
    try:
        import FreeCAD as App

        from . import parameters

        doc = App.ActiveDocument
        return list(parameters.user_names(doc)) if doc is not None else []
    except Exception:
        return []


def _focus_changed(_old, new):
    try:
        if new is not None and new in (_state["edit"], _state["keys"]):
            return
        _detach()
        edit = edit_of(new) if new is not None else None
        if edit is not None:
            _attach(edit, new)
    except Exception as exc:
        from . import warn

        warn("parameter names while typing: %s" % exc)


def _attach(edit, keys=None):
    """Offer names in `edit`; `keys` is the widget the keys arrive at (the edit itself, or
    the spin box around it)."""
    from .compat import QtCore

    class Keys(QtCore.QObject):
        def eventFilter(self, obj, event):
            try:
                return _key(obj, event)
            except Exception as exc:
                from . import warn

                warn("parameter names while typing: %s" % exc)
                return False

    keys = keys if keys is not None else edit
    _state["edit"] = edit
    _state["keys"] = keys
    _state["filter"] = Keys()
    keys.installEventFilter(_state["filter"])
    if keys is not edit:
        edit.installEventFilter(_state["filter"])
    edit.textEdited.connect(_typed)
    edit.destroyed.connect(_gone)


def _gone(*_):
    _state["edit"] = None
    _state["keys"] = None
    _state["filter"] = None
    hide()


def _detach():
    edit = _state["edit"]
    keys = _state["keys"]
    _state["edit"] = None
    _state["keys"] = None
    hide()
    if edit is None:
        return
    try:
        if keys is not None and keys is not edit:
            keys.removeEventFilter(_state["filter"])
        edit.removeEventFilter(_state["filter"])
        edit.textEdited.disconnect(_typed)
        edit.destroyed.disconnect(_gone)
    except Exception:
        pass  # the box went with its dialog
    _state["filter"] = None


def popup():
    """The list, when it is open (a QListWidget), else None."""
    p = _state["popup"]
    try:
        return p if p is not None and p.isVisible() else None
    except RuntimeError:
        _state["popup"] = None
        return None


def shown():
    """The names the open list offers ([] when it is closed)."""
    p = popup()
    return [p.item(i).text() for i in range(p.count())] if p is not None else []


def hide():
    p = _state["popup"]
    try:
        if p is not None:
            p.hide()
    except RuntimeError:
        _state["popup"] = None


def _typed(_text=None):
    edit = _state["edit"]
    if edit is None:
        return
    _start, word = fragment(edit.text(), edit.cursorPosition())
    found = suggestions(word, _names())
    if not found:
        hide()
        return
    _show(edit, found)


def _show(edit, names):
    from .compat import QtCore, QtWidgets

    p = _state["popup"]
    try:
        if p is not None:
            p.count()
    except RuntimeError:
        p = None
    if p is None:
        p = QtWidgets.QListWidget()
        p.setObjectName("Fission180ParameterNames")
        p.setWindowFlags(
            QtCore.Qt.ToolTip | QtCore.Qt.FramelessWindowHint | QtCore.Qt.WindowStaysOnTopHint
        )
        p.setAttribute(QtCore.Qt.WA_ShowWithoutActivating, True)
        p.setFocusPolicy(QtCore.Qt.NoFocus)
        p.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        p.setStyleSheet(
            "QListWidget { background: #ffffff; color: #111111; border: 1px solid #3fa9f5; }"
            " QListWidget::item { padding: 2px 8px; }"
            " QListWidget::item:selected { background: #3fa9f5; color: #ffffff; }"
        )
        p.itemClicked.connect(lambda item: accept(item.text()))
        _state["popup"] = p
    p.clear()
    p.addItems(names)
    p.setCurrentRow(0)
    row = max(18, p.sizeHintForRow(0))
    width = max(edit.width(), p.sizeHintForColumn(0) + 24)
    p.resize(width, row * len(names) + 4)
    p.move(edit.mapToGlobal(QtCore.QPoint(0, edit.height() + 1)))
    p.show()
    p.raise_()


def accept(name=None):
    """Fill the chosen name (the list's current row when None) into the box."""
    edit = _state["edit"]
    p = popup()
    if edit is None:
        return False
    if name is None:
        if p is None or p.currentItem() is None:
            return False
        name = p.currentItem().text()
    text, cursor = complete(edit.text(), edit.cursorPosition(), name)
    edit.setText(text)
    edit.setCursorPosition(cursor)
    try:
        edit.textEdited.emit(text)  # the box's owner hears it as typed
    except Exception:
        pass
    hide()
    return True


def _key(obj, event):
    """Keys of the box while the list is open: arrows choose, Enter / Tab fill, Esc closes
    the list (and nothing else: the next Esc is the box's own)."""
    from .compat import QtCore

    kind = event.type()
    if kind in (QtCore.QEvent.FocusOut, QtCore.QEvent.Hide):
        hide()
        return False
    p = popup()
    if p is None:
        return False
    if kind == QtCore.QEvent.ShortcutOverride:
        if event.key() in (
            QtCore.Qt.Key_Escape,
            QtCore.Qt.Key_Return,
            QtCore.Qt.Key_Enter,
            QtCore.Qt.Key_Tab,
        ):
            event.accept()  # the key is the list's: no shortcut (Esc cancels, Enter is OK)
            return True
        return False
    if kind != QtCore.QEvent.KeyPress:
        return False
    key = event.key()
    if key in (QtCore.Qt.Key_Down, QtCore.Qt.Key_Up):
        step = 1 if key == QtCore.Qt.Key_Down else -1
        p.setCurrentRow((p.currentRow() + step) % p.count())
        return True
    if key in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter, QtCore.Qt.Key_Tab):
        accept()
        return True
    if key == QtCore.Qt.Key_Escape:
        hide()
        return True
    return False


def mark(widget):
    """Mark a line edit (or the spin box that holds one) as a value box."""
    try:
        widget.setProperty(MARK, True)
    except Exception:
        pass
    return widget
