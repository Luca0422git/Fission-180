# SPDX-License-Identifier: LGPL-2.1-or-later
"""Parameter names and formulas in the on-screen value boxes of FreeCAD's own drawing tools
(wave 7, sketch-c).

Fusion: while a line, rectangle or circle is drawn, a parameter's name (or a formula) typed
into the length box is taken, and the dimension the tool adds follows that parameter. The
boxes of FreeCAD's Line, Rectangle, Circle, Arc, Ellipse... are C++ number fields: a letter
typed there is dropped (params' wave 7 hand-over: "FreeCAD's own drawing tools take numbers
only: draw the shape, then double-click the dimension and type the parameter").

No C++ here. While one of those boxes has the keyboard, a letter that starts a parameter's
name (or "=") opens a small text box of Fission 180's own over it (NameBox, a marked value
box: the list of parameters_complete.py opens under it as in every other value box). Enter
or Tab there reads the text the one way every value box does (parameters.read_typed); the
number it works out is typed into FreeCAD's box, with its unit, and the same Enter or Tab
is handed on, so FreeCAD's tool goes on exactly as if the number had been typed. When the
tool has made its shape, the dimension it added for that box gets the formula
(parameters.bind_typed), in a step glued to the shape's own: one Ctrl+Z takes back the
shape with its dimension.

A letter no parameter starts with is still a tool's shortcut (L, C, R...), as before.
Never lets an exception out of an event handler (warn() and carry on).
"""

from . import log, warn
from .compat import QtCore, QtGui, QtWidgets

NAME = "Fission180FieldName"
ANGLE_UNITS = ("deg", "°", "rad")


class _Typed:
    """What parameters.bind_typed needs of a value box."""

    def __init__(self, formula, typed, kind):
        self.formula = formula
        self.typed = typed
        self.kind = kind


class NameBox(QtWidgets.QLineEdit):
    """The text box over one of FreeCAD's value boxes while a name or formula is typed."""

    def __init__(self, owner, field, first):
        super().__init__(field.parentWidget())
        self.owner = owner
        self.field = field
        self.setObjectName(NAME)
        from . import parameters_complete

        parameters_complete.mark(self)  # the list of parameter names opens under it
        self.setStyleSheet(
            "QLineEdit { background: #ffffff; color: #111111; border: 1px solid #3fa9f5;"
            " padding: 1px 3px; selection-background-color: #3fa9f5; }"
            ' QLineEdit[bad="true"] { border: 1px solid #b00020; }'
        )
        rect = field.geometry()
        self.setGeometry(rect.x(), rect.y(), max(rect.width(), 130), rect.height())
        self.setText(first)
        self.show()
        self.raise_()
        self.setFocus()
        self.setCursorPosition(len(first))
        try:
            self.textEdited.emit(first)  # (the list of names for the first letter)
        except Exception:
            pass

    def event(self, event):
        try:
            if event.type() == QtCore.QEvent.KeyPress:
                key = event.key()
                if key in (QtCore.Qt.Key_Tab, QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
                    self.owner.commit(self, key)
                    return True
                if key == QtCore.Qt.Key_Escape:
                    self.owner.cancel(self)
                    return True
            elif event.type() == QtCore.QEvent.ShortcutOverride:
                if event.key() in (
                    QtCore.Qt.Key_Tab,
                    QtCore.Qt.Key_Return,
                    QtCore.Qt.Key_Enter,
                    QtCore.Qt.Key_Escape,
                ):
                    event.accept()
                    return True
        except Exception as exc:
            warn("parameter name in a drawing box: %s" % exc)
        return super().event(event)

    def focusOutEvent(self, event):
        super().focusOutEvent(event)
        try:
            # a click in the view goes on drawing: the half-typed name is dropped
            if self.owner.box is self and not self.owner.feeding:
                QtCore.QTimer.singleShot(0, lambda: self.owner.dropped(self))
        except Exception:
            pass

    def set_bad(self, on):
        if bool(self.property("bad")) != on:
            self.setProperty("bad", on)
            self.style().unpolish(self)
            self.style().polish(self)


def field_kind(field):
    """ "angle" or "length": what FreeCAD's value box `field` holds (its unit)."""
    try:
        unit = str(field.property("unit") or "")
        text = field.text() if hasattr(field, "text") else ""
        if unit in ANGLE_UNITS or text.rstrip().endswith(("°", "deg")):
            return "angle"
    except Exception:
        pass
    return "length"


def number_text(value, kind):
    """The text typed into FreeCAD's box for `value` (mm, or degrees): with its unit, so
    that the design's units (inches) do not matter."""
    return "%.10g %s" % (value, "deg" if kind == "angle" else "mm")


class FieldNames:
    """Owned by sketch_mode.SketchSession."""

    def __init__(self, session):
        self.session = session
        self.box = None
        self.feeding = False  # our own keys are being typed into FreeCAD's box
        self.pending = []  # _Typed of the boxes that took a formula, for the next shape
        self.first = 0  # the sketch's constraint count before that shape's dimensions
        self.bound = 0  # how many dimensions the last shape's formulas were bound to (tests)

    # -- starting ---------------------------------------------------------------------------
    def wants(self, field, event):
        """A key typed into FreeCAD's value box `field` starts a name or a formula."""
        if self.feeding or self.box is not None:
            return False
        mods = event.modifiers() & ~(QtCore.Qt.ShiftModifier | QtCore.Qt.KeypadModifier)
        if mods != QtCore.Qt.NoModifier:
            return False
        text = event.text()[:1]
        typed = self.typed_so_far(field)
        if typed is not None:
            # a number is being typed: a letter after it is a unit ("12 mm"), unless it
            # follows an operator ("2 * W...": the formula goes on in the text box)
            if not typed.rstrip().endswith(("+", "-", "*", "/", "(")):
                return False
        elif text == "=":
            return True
        try:
            from . import parameters_complete

            return parameters_complete.starts_a_name(text)
        except Exception:
            return False

    def typed_so_far(self, field):
        """What the person typed into FreeCAD's box `field` so far, or None."""
        try:
            from . import sketch_mode

            if not sketch_mode._same(self.session._typed, field):
                return None
            edit = field.findChild(QtWidgets.QLineEdit)
            return edit.text() if edit is not None else None
        except Exception:
            return None

    def start(self, field, text):
        try:
            typed = self.typed_so_far(field)
            if typed is not None:
                text = typed + text
            self.box = NameBox(self, field, "" if text == "=" else text)
            log("drawing box: a parameter name or formula is being typed")
        except Exception as exc:
            self.box = None
            warn("parameter name in a drawing box: %s" % exc)

    # -- ending -----------------------------------------------------------------------------
    def _close(self, box):
        if self.box is box:
            self.box = None
        try:
            from . import parameters_complete

            parameters_complete.hide()
            box.hide()
            box.deleteLater()
        except Exception:
            pass

    def cancel(self, box):
        """Esc: the text box goes, FreeCAD's box has the keyboard again (the next Esc is
        the tool's)."""
        field = box.field
        self._close(box)
        try:
            field.setFocus()
        except Exception:
            pass

    def dropped(self, box):
        """The text box lost the keyboard (a click in the view)."""
        try:
            if self.box is box and not box.hasFocus():
                self._close(box)
        except RuntimeError:
            self.box = None

    def close(self):
        """The tool ended or the sketch closed."""
        if self.box is not None:
            self._close(self.box)
        self.pending = []

    def commit(self, box, key):
        """Enter or Tab in the text box."""
        text = box.text().strip()
        field = box.field
        if not text:
            self.cancel(box)
            return
        session = self.session
        kind = field_kind(field)
        try:
            from . import parameters

            got = parameters.read_typed(session.doc, text, kind)
            value = got.value
            if kind == "length" and value <= 1e-7:
                raise ValueError("The value must be more than 0.")
        except Exception as exc:
            box.set_bad(True)
            try:
                from . import commands

                commands.tell(str(exc))
            except Exception:
                pass
            return
        self._close(box)
        try:
            if not self.pending:
                self.first = len(session.sketch.Constraints)
            if not got.plain:
                import math

                typed = math.radians(value) if kind == "angle" else value
                self.pending.append(_Typed(got.freecad, typed, kind))
            self._feed(field, number_text(value, kind), key)
        except Exception as exc:
            warn("parameter name in a drawing box: %s" % exc)

    def _feed(self, field, text, key):
        """Type `text` into FreeCAD's box as a keyboard would (it replaces what the box
        shows), then hand on the Enter or Tab that ended the name."""
        send = QtWidgets.QApplication.sendEvent
        field.setFocus()
        self.feeding = True
        try:
            edit = field.findChild(QtWidgets.QLineEdit)
            if edit is not None:
                edit.selectAll()
            for ch in text:
                code = QtGui.QKeySequence(ch)[0].key() if ch.strip() else QtCore.Qt.Key_Space
                for kind in (QtCore.QEvent.KeyPress, QtCore.QEvent.KeyRelease):
                    send(field, QtGui.QKeyEvent(kind, code, QtCore.Qt.NoModifier, ch))
            self.session._typed = field
            self.session._typed_since_commit = True
        finally:
            self.feeding = False
        char = "\t" if key == QtCore.Qt.Key_Tab else "\r"
        for kind in (QtCore.QEvent.KeyPress, QtCore.QEvent.KeyRelease):
            send(field, QtGui.QKeyEvent(kind, key, QtCore.Qt.NoModifier, char))

    # -- after the shape ----------------------------------------------------------------------
    def settled(self, kind):
        """The sketch committed, aborted or undid a step (from FreeCAD's signal: only a
        timer here)."""
        if not self.pending:
            return
        if kind == "commit":
            QtCore.QTimer.singleShot(0, self.bind)
        elif kind in ("abort", "undo", "redo"):
            self.pending = []

    def bind(self):
        """The shape is made: its dimensions for the boxes that took a formula follow it."""
        session = self.session
        fields, self.pending = self.pending, []
        if session.closed or not fields:
            return
        sketch, doc = session.sketch, session.doc
        try:
            if len(sketch.Constraints) <= self.first:
                # (the shape's dimensions are not there yet: a click before the tool's last
                # one committed something else; keep the formulas for the shape)
                self.pending = fields
                return
            from . import parameters, sketch_mode

            infer = session.infer
            if infer is not None:
                infer._applying = True
            doc.openTransaction(sketch_mode.INFER_STEP)
            try:
                count = parameters.bind_typed(sketch, self.first, fields)
                if count:
                    sketch.recompute()
                    sketch.solve()
            except Exception:
                doc.abortTransaction()
                raise
            finally:
                if infer is not None:
                    infer._applying = False
            if count:
                doc.commitTransaction()
            else:
                from . import sketch_constrain_tools

                sketch_constrain_tools.end_step(doc, abort=True)
            self.bound = count
            if count:
                log("drawing box: %d dimension(s) follow the typed formula" % count)
            else:
                from . import commands

                commands.tell(
                    "The shape was drawn with the value typed, but it has no dimension to "
                    "hold the formula: add the dimension (D) and type the name there."
                )
        except Exception as exc:
            warn("parameter name in a drawing box: %s" % exc)
