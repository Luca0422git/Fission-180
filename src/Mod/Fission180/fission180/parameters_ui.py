# SPDX-License-Identifier: LGPL-2.1-or-later
"""Change Parameters dialog (Fusion: Modify > Change Parameters).

Top: Favorites (the starred parameters of both kinds), then the user parameters (Name, Unit,
Expression, Value, Comment) with "+ User Parameter" and Delete, then the model parameters:
every size in the design, grouped by step, in the design's units, editable in place.
Expressions are written Fusion's way: parameter names bare (`width / 2 + wall`), a number
without a unit in the design's units (`Arm_Length + 5`), `;` between a function's arguments.
A name is renamed by typing over it (every formula follows); the star in front of a row
makes it a favourite.
Everything is one undo step; Cancel puts the design back as it was.
A value that would break a step (a feature that fails, a sketch whose constraints conflict, a
sketch length of 0 or less) is tried and put back, and the message names the step and the
dimension (parameters.change_checked). What cannot be done is said in red in the dialog,
never only in the log.
"""

import FreeCAD as App
import FreeCADGui as Gui

from . import log, parameters, parameters_complete, parameters_core as core
from . import ui_icon, ui_icon_path, warn
from .compat import QtCore, QtGui, QtWidgets

USER_COLUMNS = ["Name", "Unit", "Expression", "Value", "Comment"]
MODEL_COLUMNS = ["Parameter", "Name", "Expression", "Value"]
FAVORITE_COLUMNS = ["Name", "Unit", "Expression", "Value", "Of"]
UNIT_CHOICES = [
    ("mm", "mm"),
    ("cm", "cm"),
    ("m", "m"),
    ("in", "in"),
    ("ft", "ft"),
    ("deg", "deg"),
    ("rad", "rad"),
    ("", "No Units"),
]
STAR_WIDTH = 20
STAR_ON = "#f5b301"
STAR_OFF = "#8a94a6"
ERROR_STYLE = "color: #ff8a80;"


def _fmt(value, unit):
    if isinstance(value, float):
        text = ("%.4f" % value).rstrip("0").rstrip(".")
    else:
        text = str(value)
    return text + (" " + unit if unit else "")


def _is_on(state):
    """True for a checked check state, whether Qt hands it over as a number or an enum."""
    return getattr(state, "value", state) == 2


def unit_label(unit):
    return dict(UNIT_CHOICES).get(unit, unit)


class RowDelegate(QtWidgets.QStyledItemDelegate):
    """The cells of the three lists: a star in front of a row that can be a favourite (a
    click on it toggles it), a drop-down for a user parameter's unit, and an expression
    editor that offers the parameter names while typing."""

    def __init__(self, view, unit_column=None, formula_column=2):
        super().__init__(view)
        self.unit_column = unit_column
        self.formula_column = formula_column

    # -- the star ---------------------------------------------------------------------------
    def _starred(self, index):
        return index.data(QtCore.Qt.CheckStateRole)

    def star_rect(self, option):
        rect = QtCore.QRect(option.rect)
        rect.setWidth(STAR_WIDTH)
        return rect

    def paint(self, painter, option, index):
        state = self._starred(index)
        if state is None:
            super().paint(painter, option, index)
            return
        opt = QtWidgets.QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        opt.features &= ~QtWidgets.QStyleOptionViewItem.HasCheckIndicator
        style = opt.widget.style() if opt.widget is not None else QtWidgets.QApplication.style()
        style.drawControl(QtWidgets.QStyle.CE_ItemViewItem, opt, painter, opt.widget)
        on = _is_on(state)
        painter.save()
        painter.setPen(QtGui.QColor(STAR_ON if on else STAR_OFF))
        font = QtGui.QFont(opt.font)
        font.setPointSizeF(max(8.0, font.pointSizeF() * 1.15))
        painter.setFont(font)
        painter.drawText(self.star_rect(option), QtCore.Qt.AlignCenter, "★" if on else "☆")
        painter.restore()

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        if self._starred(index) is not None:
            option.features &= ~QtWidgets.QStyleOptionViewItem.HasCheckIndicator
            option.text = "     " + (option.text or "")  # room for the star

    def editorEvent(self, event, model, option, index):
        if self._starred(index) is None:
            return super().editorEvent(event, model, option, index)
        kind = event.type()
        mouse = (QtCore.QEvent.MouseButtonRelease, QtCore.QEvent.MouseButtonDblClick)
        if kind in mouse and self.star_rect(option).contains(event.pos()):
            # (a second click soon after the first reaches the view as a double-click, and
            # the view then sends no release for it: each of the two is one click here)
            # (plain numbers: a PySide enum stored in the model reads back as "unchecked")
            model.setData(index, 0 if _is_on(self._starred(index)) else 2, QtCore.Qt.CheckStateRole)
            return True
        if kind == QtCore.QEvent.MouseButtonPress and self.star_rect(option).contains(event.pos()):
            return True
        return False

    def updateEditorGeometry(self, editor, option, index):
        rect = QtCore.QRect(option.rect)
        if self._starred(index) is not None:
            rect.setLeft(rect.left() + STAR_WIDTH)
        editor.setGeometry(rect)

    # -- editors ------------------------------------------------------------------------------
    def createEditor(self, parent, option, index):
        if self.unit_column is not None and index.column() == self.unit_column:
            combo = QtWidgets.QComboBox(parent)
            for unit, label in UNIT_CHOICES:
                combo.addItem(label, unit)
            combo.activated.connect(lambda *_: self._commit_combo(combo))
            return combo
        editor = super().createEditor(parent, option, index)
        if index.column() == self.formula_column and isinstance(editor, QtWidgets.QLineEdit):
            parameters_complete.mark(editor)
        return editor

    def _commit_combo(self, combo):
        self.commitData.emit(combo)
        self.closeEditor.emit(combo, QtWidgets.QAbstractItemDelegate.NoHint)

    def setEditorData(self, editor, index):
        if isinstance(editor, QtWidgets.QComboBox):
            unit = index.data(QtCore.Qt.UserRole)
            at = editor.findData(unit if unit is not None else "mm")
            editor.setCurrentIndex(max(0, at))
            return
        super().setEditorData(editor, index)
        if isinstance(editor, QtWidgets.QLineEdit):
            editor.setText((editor.text() or "").strip())

    def setModelData(self, editor, model, index):
        if isinstance(editor, QtWidgets.QComboBox):
            model.setData(index, editor.currentData(), QtCore.Qt.UserRole)
            model.setData(index, unit_label(editor.currentData()), QtCore.Qt.EditRole)
            return
        super().setModelData(editor, model, index)


class AddParameterDialog(QtWidgets.QDialog):
    """Fusion's Add User Parameter: Name, Unit, Expression, Value (worked out while typing),
    Comment. OK is refused, with the reason in red, until the name and the expression are
    good."""

    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.doc = owner.doc
        self.setWindowTitle("Add User Parameter")
        self.setObjectName("Fission180AddParameter")
        form = QtWidgets.QFormLayout(self)
        self.name = QtWidgets.QLineEdit()
        self.name.setObjectName("Fission180ParameterName")
        self.unit = QtWidgets.QComboBox()
        self.unit.setObjectName("Fission180ParameterUnit")
        for unit, label in UNIT_CHOICES:
            self.unit.addItem(label, unit)
        design = parameters.design_unit(self.doc)
        self.unit.setCurrentIndex(max(0, self.unit.findData(design)))
        self.expression = parameters_complete.mark(QtWidgets.QLineEdit())
        self.expression.setObjectName("Fission180ParameterExpression")
        self.value = QtWidgets.QLabel("")
        self.value.setObjectName("Fission180ParameterValue")
        self.comment = QtWidgets.QLineEdit()
        self.comment.setObjectName("Fission180ParameterComment")
        form.addRow("Name", self.name)
        form.addRow("Unit", self.unit)
        form.addRow("Expression", self.expression)
        form.addRow("Value", self.value)
        form.addRow("Comment", self.comment)
        self.message = QtWidgets.QLabel("")
        self.message.setWordWrap(True)
        self.message.setStyleSheet(ERROR_STYLE)
        form.addRow(self.message)
        self.buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)
        form.addRow(self.buttons)
        self.expression.textChanged.connect(self._preview)
        self.unit.currentIndexChanged.connect(self._preview)
        self.name.textChanged.connect(self._preview)
        self.resize(360, self.sizeHint().height())
        self.name.setFocus()

    def chosen_unit(self):
        return self.unit.currentData() or ""

    def problem(self):
        """Why the parameter cannot be made as typed ("" when it can)."""
        name = self.name.text().strip()
        text = self.expression.text().strip()
        if not name:
            return "Give the parameter a name."
        try:
            core.check_name(name, existing=set(parameters.user_names(self.doc)))
        except core.ParameterError as exc:
            return str(exc)
        if not text:
            return "Type a value or a formula."
        try:
            unit = self.chosen_unit()
            parameters.read(self.doc, text, core.PARAMETER_UNITS[unit], unit=unit or None)
        except core.ParameterError as exc:
            return str(exc)
        return ""

    def _preview(self, *_):
        text = self.expression.text().strip()
        unit = self.chosen_unit()
        shown = ""
        if text:
            try:
                got = parameters.read(self.doc, text, core.PARAMETER_UNITS[unit], unit=unit or None)
                shown = parameters.value_text(got.value, unit)
            except Exception:
                shown = ""
        self.value.setText(shown)
        if self.message.text():
            self.message.setText(self.problem())

    def accept(self):
        try:
            problem = self.problem()
            if problem:
                self.message.setText(problem)
                return
            refused = self.owner.add_parameter(
                self.name.text().strip(),
                self.chosen_unit(),
                self.expression.text().strip(),
                self.comment.text().strip(),
            )
            if refused:
                self.message.setText(refused)
                return
        except Exception as exc:
            self.message.setText(str(exc))
            return
        super().accept()


class ParametersDialog(QtWidgets.QDialog):
    last = None

    def __init__(self, doc, parent=None):
        super().__init__(parent or Gui.getMainWindow())
        ParametersDialog.last = self
        self.doc = doc
        self.adder = None
        self.setWindowTitle("Parameters")
        self.setWindowIcon(ui_icon("parameters"))
        self.resize(820, 640)
        # Like Fusion's, the dialog keeps the rest of the window still while it is open (it
        # holds one undo step: another command started under it would close that step).
        self.setModal(True)
        self._open_step()
        self._loading = False

        layout = QtWidgets.QVBoxLayout(self)
        head = QtWidgets.QHBoxLayout()
        self.filter = QtWidgets.QLineEdit()
        self.filter.setObjectName("Fission180ParameterFilter")
        self.filter.setPlaceholderText("Filter parameters")
        self.filter.setClearButtonEnabled(True)
        self.filter.textChanged.connect(self._filter)
        head.addWidget(self.filter, 1)
        # (push buttons: the theme styles them; a bare QToolButton was drawn as a blank
        # white square with its "+" in the theme's light text colour)
        self.add_button = QtWidgets.QPushButton("+ User Parameter")
        self.add_button.setObjectName("Fission180AddParameterButton")
        self.add_button.setToolTip("Add a user parameter")
        self.add_button.setAutoDefault(False)
        # (clicked passes Qt's `checked`: never straight into a method with arguments)
        self.add_button.clicked.connect(lambda *_: self.ask_parameter())
        self.remove_button = QtWidgets.QPushButton("Delete")
        self.remove_button.setObjectName("Fission180DeleteParameterButton")
        self.remove_button.setToolTip("Delete the selected user parameter")
        self.remove_button.setAutoDefault(False)
        self.remove_button.clicked.connect(lambda *_: self.remove_parameter())
        head.addWidget(self.add_button)
        head.addWidget(self.remove_button)
        layout.addLayout(head)

        self.favorites_label = QtWidgets.QLabel("<b>Favorites</b>")
        layout.addWidget(self.favorites_label)
        self.favorites = QtWidgets.QTableWidget(0, len(FAVORITE_COLUMNS))
        self.favorites.setObjectName("Fission180FavoriteParameters")
        self.favorites.setHorizontalHeaderLabels(FAVORITE_COLUMNS)
        self.favorites.horizontalHeader().setStretchLastSection(True)
        self.favorites.verticalHeader().setVisible(False)
        self.favorites.setItemDelegate(RowDelegate(self.favorites))
        self.favorites.itemChanged.connect(self._favorite_changed)
        layout.addWidget(self.favorites, 1)

        layout.addWidget(QtWidgets.QLabel("<b>User Parameters</b>"))
        self.user = QtWidgets.QTableWidget(0, len(USER_COLUMNS))
        self.user.setObjectName("Fission180UserParameters")
        self.user.setHorizontalHeaderLabels(USER_COLUMNS)
        self.user.horizontalHeader().setStretchLastSection(True)
        self.user.verticalHeader().setVisible(False)
        self.user.setItemDelegate(RowDelegate(self.user, unit_column=1))
        self.user.itemChanged.connect(self._user_changed)
        layout.addWidget(self.user, 2)

        layout.addWidget(QtWidgets.QLabel("<b>Model Parameters</b>"))
        self.model = QtWidgets.QTreeWidget()
        self.model.setObjectName("Fission180ModelParameters")
        self.model.setColumnCount(len(MODEL_COLUMNS))
        self.model.setHeaderLabels(MODEL_COLUMNS)
        self.model.setItemDelegate(RowDelegate(self.model))
        self.model.itemChanged.connect(self._model_changed)
        layout.addWidget(self.model, 3)

        self.message = QtWidgets.QLabel("")
        self.message.setObjectName("Fission180ParameterMessage")
        self.message.setWordWrap(True)
        self.message.setStyleSheet(ERROR_STYLE)
        layout.addWidget(self.message)
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        for button in buttons.buttons():
            button.setAutoDefault(False)  # Enter in a cell ends the cell, not the dialog
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.reload()

    # -- filling -------------------------------------------------------------------------------
    def reload(self):
        self._loading = True
        try:
            self._fill_user()
            model_rows = self._fill_model()
            self._fill_favorites(model_rows)
            self._filter()
        except Exception as exc:
            warn("parameters: the lists could not be filled: %s" % exc)
        finally:
            self._loading = False

    def _fill_user(self):
        rows = parameters.user_parameters(self.doc)
        derived = parameters.derived_parameters(self.doc)
        self.user.setRowCount(len(rows) + len(derived))
        grey = QtGui.QBrush(QtGui.QColor("#8a94a6"))
        for r, row in enumerate(rows + derived):
            own = r < len(rows)
            cells = [
                row["name"],
                unit_label(row["unit"]),
                row["shown"],
                row["display"],
                row["comment"],
            ]
            for c, text in enumerate(cells):
                item = QtWidgets.QTableWidgetItem(text)
                if c == 3 or not own:
                    item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
                if not own:  # derived (Derive): greyed, changed in its source
                    item.setForeground(grey)
                if c == 0:
                    item.setData(QtCore.Qt.UserRole, row["name"])
                    if own:
                        star = QtCore.Qt.Checked if row["favorite"] else QtCore.Qt.Unchecked
                        item.setCheckState(star)
                if c == 1:
                    item.setData(QtCore.Qt.UserRole, row["unit"])
                self.user.setItem(r, c, item)
        self.user.resizeColumnsToContents()

    def _fill_model(self):
        expanded = {
            self.model.topLevelItem(i).text(0)
            for i in range(self.model.topLevelItemCount())
            if self.model.topLevelItem(i).isExpanded()
        }
        seen = self.model.topLevelItemCount() > 0
        self.model.clear()
        groups = {}
        rows = parameters.model_parameters(self.doc)
        for row in rows:
            group = groups.get(row["owner"])
            if group is None:
                group = QtWidgets.QTreeWidgetItem(self.model, [row["owner"]])
                group.setFlags(group.flags() & ~QtCore.Qt.ItemIsEditable)
                group.setExpanded(not seen or row["owner"] in expanded)
                groups[row["owner"]] = group
            item = QtWidgets.QTreeWidgetItem(
                group, ["", row["label"], row["shown"], row["display"]]
            )
            item.setData(0, QtCore.Qt.UserRole, row)
            item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
            item.setCheckState(0, QtCore.Qt.Checked if row["favorite"] else QtCore.Qt.Unchecked)
        for c in range(len(MODEL_COLUMNS)):
            self.model.resizeColumnToContents(c)
        return rows

    def _fill_favorites(self, model_rows):
        entries = []
        for row in parameters.user_parameters(self.doc):
            if row["favorite"]:
                cells = [row["name"], unit_label(row["unit"]), row["shown"], row["display"]]
                entries.append((("user", row["name"]), cells + ["User Parameters"]))
        for row in model_rows:
            if row["favorite"]:
                cells = [row["label"], row["display_unit"], row["shown"], row["display"]]
                entries.append((("model", row), cells + [row["owner"]]))
        self.favorites.setRowCount(len(entries))
        for r, (key, cells) in enumerate(entries):
            for c, text in enumerate(cells):
                item = QtWidgets.QTableWidgetItem(text)
                if c != 2:
                    item.setFlags(item.flags() & ~QtCore.Qt.ItemIsEditable)
                if c == 0:
                    item.setData(QtCore.Qt.UserRole, key)
                    item.setCheckState(QtCore.Qt.Checked)
                self.favorites.setItem(r, c, item)
        self.favorites.resizeColumnsToContents()
        self.favorites.setVisible(bool(entries))
        self.favorites_label.setVisible(bool(entries))

    def _filter(self, *_):
        """Show only the rows whose name, expression, comment or step holds the typed text."""
        needle = self.filter.text().strip().lower()
        for table in (self.user, self.favorites):
            for r in range(table.rowCount()):
                texts = [
                    table.item(r, c).text() for c in range(table.columnCount()) if table.item(r, c)
                ]
                table.setRowHidden(r, bool(needle) and not any(needle in t.lower() for t in texts))
        for i in range(self.model.topLevelItemCount()):
            group = self.model.topLevelItem(i)
            in_group = needle in group.text(0).lower()
            any_shown = False
            for j in range(group.childCount()):
                child = group.child(j)
                texts = [child.text(c) for c in range(1, len(MODEL_COLUMNS))]
                show = not needle or in_group or any(needle in t.lower() for t in texts)
                child.setHidden(not show)
                any_shown = any_shown or show
            group.setHidden(not any_shown)

    # -- editing -------------------------------------------------------------------------------
    def say(self, text):
        """Show why something was not done (red, in the dialog), or clear the message."""
        self.message.setText(("⚠ " + text) if text else "")

    def _apply(self, fn, checked=None):
        """Run a change. `checked`: (object, property path, "name = value") of a value change,
        tried first: when it would break a step it is put back and the message says which
        step and which dimension (parameters.change_checked). Returns the message ("" when
        the change stands)."""
        refused = ""
        try:
            if checked is not None:
                obj, path, what = checked
                refused = parameters.change_checked(self.doc, obj, path, fn, what)
            else:
                fn()
                self.doc.recompute()
            self.say(refused)
        except Exception as exc:
            refused = str(exc) or exc.__class__.__name__
            self.say(refused)
            log("parameters: not changed: %s" % refused)
        QtCore.QTimer.singleShot(0, self.reload)
        return refused

    def _set_user(self, name, text):
        prop = core.prop_name(name)
        return self._apply(
            lambda: parameters.set_user(self.doc, name, text),
            (parameters.container(self.doc), prop, "%s = %s" % (name, text.strip())),
        )

    def _set_model(self, row, text):
        return self._apply(
            # (a number typed here is in the design's units, like in every value box)
            lambda: parameters.set_model(
                self.doc, row, text, unit=parameters.design_unit(self.doc)
            ),
            (
                self.doc.getObject(row["object"]),
                row["path"],
                "%s = %s" % (row["label"], text.strip()),
            ),
        )

    def _user_changed(self, item):
        if self._loading:
            return
        column = item.column()
        name = self.user.item(item.row(), 0).data(QtCore.Qt.UserRole)
        if name is None:
            return
        if column == 0:
            new = item.text().strip()
            starred = item.checkState() == QtCore.Qt.Checked
            if new != name:
                self._apply(lambda: parameters.rename_user(self.doc, name, new))
            elif starred != (name in parameters.favorites(self.doc)):
                self._apply(lambda: parameters.set_favorite(self.doc, name, starred))
        elif column == 1:
            unit = item.data(QtCore.Qt.UserRole)
            if unit != parameters.unit_of_parameter(self.doc, name):
                self._apply(lambda: parameters.set_unit(self.doc, name, unit))
        elif column == 2:
            self._set_user(name, item.text())
        elif column == 4:
            obj = parameters.container(self.doc)
            text = item.text()
            self._apply(lambda: obj.setDocumentationOfProperty(core.prop_name(name), text))

    def _model_changed(self, item, column):
        if self._loading:
            return
        row = item.data(0, QtCore.Qt.UserRole)
        if row is None:
            return
        if column == 0:
            starred = item.checkState(0) == QtCore.Qt.Checked
            key = parameters.model_key(row)
            if starred != (key in parameters.favorites(self.doc)):
                self._apply(lambda: parameters.set_favorite(self.doc, key, starred))
        elif column == 2:
            self._set_model(row, item.text(2))

    def _favorite_changed(self, item):
        if self._loading:
            return
        first = self.favorites.item(item.row(), 0)
        key = first.data(QtCore.Qt.UserRole) if first is not None else None
        if key is None:
            return
        kind, what = key
        if item.column() == 0:
            if item.checkState() != QtCore.Qt.Checked:
                star = what if kind == "user" else parameters.model_key(what)
                self._apply(lambda: parameters.set_favorite(self.doc, star, False))
        elif item.column() == 2:
            if kind == "user":
                self._set_user(what, item.text())
            else:
                self._set_model(what, item.text())

    def ask_parameter(self):
        """+ User Parameter: Fusion's Add User Parameter box."""
        try:
            self.say("")
            self.adder = AddParameterDialog(self)
            self.adder.open()
        except Exception as exc:
            self.say("The parameter could not be added: %s" % exc)

    def add_parameter(self, name, unit="mm", text="10", comment=""):
        """Add the user parameter `name`. Returns "" or why it was not added (also shown)."""
        return self._apply(
            lambda: parameters.add_user(self.doc, str(name).strip(), unit, text, comment)
        )

    def selected_user(self):
        """The name of the selected user parameter, or None."""
        row = self.user.currentRow()
        if row < 0 or self.user.item(row, 0) is None:
            return None
        return self.user.item(row, 0).data(QtCore.Qt.UserRole)

    def remove_parameter(self):
        name = self.selected_user()
        if name is None:
            self.say("Click the user parameter to delete first.")
            return
        self._apply(lambda: parameters.remove_user(self.doc, name))

    def _open_step(self):
        """One undo step for everything done in the dialog. It has to outlive the command
        that opens the dialog: FreeCAD closes a step opened inside a command when the
        command returns (App::AutoTransaction), and the dialog's changes were then made
        outside any undo step: Ctrl+Z did not take them back and Cancel put nothing back
        (found by scenario book_params_dialog). `persist` keeps the step open."""
        try:
            App.setActiveTransaction("Change Parameters", True)
        except Exception:
            self.doc.openTransaction("Change Parameters")

    def _close_step(self, abort):
        try:
            if abort:
                self.doc.abortTransaction()
            else:
                self.doc.commitTransaction()
        finally:
            try:
                App.closeActiveTransaction(abort)  # the step's name, when nothing changed
            except Exception:
                pass

    def accept(self):
        try:
            self.doc.recompute()
            self._close_step(False)
            log("parameters changed")
        except Exception as exc:
            warn("Change Parameters: %s" % exc)
        super().accept()
        self._back_to_the_design()

    def reject(self):
        try:
            self._close_step(True)
            self.doc.recompute()
        except Exception as exc:
            warn("Change Parameters: %s" % exc)
        super().reject()
        self._back_to_the_design()

    def _back_to_the_design(self):
        """The keyboard goes back to the main window (Ctrl+Z right after OK is the window's
        shortcut: without a window manager handing the focus back it did nothing)."""
        try:
            window = Gui.getMainWindow()
            window.activateWindow()
            view = Gui.ActiveDocument.ActiveView if Gui.ActiveDocument is not None else None
            if view is not None and hasattr(view, "setFocus"):
                view.setFocus()
        except Exception:
            pass


class ChangeParametersCommand:
    def GetResources(self):
        return {
            "MenuText": "Change Parameters",
            "ToolTip": "Named user parameters and every dimension of the design in one table",
            "Pixmap": ui_icon_path("parameters"),
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        try:
            if not _finish_open_command():
                return
            dialog = ParametersDialog(App.ActiveDocument)
            dialog.show()
        except Exception as exc:
            warn("Change Parameters failed to open: %s" % exc)


def _finish_open_command():
    """Fusion: starting a command ends the one in progress. A Fission 180 command dialog
    that is open (Extrude, Fillet...) is finished first: Change Parameters holds an undo step
    of its own, and opened over another command's it would close that one half-way. An open
    sketch stays open (Fusion's sketch has Change Parameters in its MODIFY menu)."""
    from . import commands, taskui

    panel = taskui.current()
    if panel is None:
        return True
    try:
        panel.finish()
    except Exception as exc:
        warn("could not finish the open command: %s" % exc)
    if taskui.current() is not None:
        commands.tell("Finish the open command first (OK or Cancel in its panel).")
        return False
    return True


try:  # the list of parameter names under every value box (parameters_complete.py)
    parameters_complete.install()
except Exception as exc:
    warn("parameter names while typing are off: %s" % exc)
try:  # every design keeps its units (design_units.py: bug 2 of the book parity report)
    from . import design_units

    design_units.install()
except Exception as exc:
    warn("units: designs are not held to their units: %s" % exc)
