# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's Tool Library (MANUFACTURE > MANAGE > Tool Library, and Select on an operation's
Tool tab) and its tool editor.

The window: the libraries on the left (the open design's own tools, the person's libraries
on this computer, Fission 180's metric and inch samples), their tools in a table (number,
name, type, diameter, flute length, flutes, spindle speed, feedrate) with a type filter and a
search box, and New Tool, Edit, Copy To Local, Delete, New Library. Opened from an operation
it also has Select (a double-click selects), showing the tools that operation can cut with.

The editor (Fusion's tabs): General (name, vendor, product id, comment, unit), Cutter (type,
diameter, flute / shoulder / body / overall length, shaft diameter, flutes, material, corner
radius / taper angle / tip angle), Holder, Cutting Data (spindle speed, feedrates, stepdown,
stepover, coolant, and Suggest: starting values from the usual formulas), Post Processor
(the tool number). Tools are kept as FreeCAD tool-bit files (manufacture_tools.py).
"""

import FreeCAD as App
import FreeCADGui as Gui

from . import commands, log, ui_icon, warn
from . import manufacture_core as core
from .compat import QtCore, QtWidgets

OPEN = {"library": None, "editor": None}
COLUMNS = (
    "#",
    "Name",
    "Type",
    "Diameter",
    "Flute Length",
    "Flutes",
    "Spindle (rpm)",
    "Feed (mm/min)",
)
FILTERS = (
    ("all", "All types"),
    ("milling", "Milling"),
    ("hole", "Hole making"),
)


def _lib():
    from . import manufacture_tools

    return manufacture_tools


def _alive(widget):
    try:
        widget.objectName()
        return True
    except Exception:
        return False


class ToolEditor(QtWidgets.QDialog):
    """Fusion's tool editor for one tool. `on_save(tool)` gets the edited tool on OK."""

    LENGTHS = (
        ("diameter", "Diameter"),
        ("shaft_diameter", "Shaft Diameter"),
        ("overall_length", "Overall Length"),
        ("body_length", "Length Below Holder"),
        ("shoulder_length", "Shoulder Length"),
        ("flute_length", "Flute Length"),
        ("corner_radius", "Corner Radius"),
        ("tip_diameter", "Tip Diameter"),
    )
    CUTTING = (
        ("spindle_speed", "Spindle Speed", " rpm", False),
        ("cutting_feed", "Cutting Feedrate", " /min", True),
        ("leadin_feed", "Lead-In Feedrate", " /min", True),
        ("ramp_feed", "Ramp Feedrate", " /min", True),
        ("plunge_feed", "Plunge Feedrate", " /min", True),
        ("stepdown", "Stepdown", "", True),
        ("stepover", "Stepover", "", True),
    )

    def __init__(self, parent, tool, on_save, title="Edit Tool"):
        super().__init__(parent)
        self.setObjectName("Fission180CamToolEditor")
        self.setWindowTitle(title)
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.on_save = on_save
        self.tool = core.tool(tool)
        self.fields = {}
        layout = QtWidgets.QVBoxLayout(self)
        self.setMinimumWidth(620)  # (all five tabs show: none hides behind a scroll arrow)
        self.tabs = QtWidgets.QTabWidget()
        self.tabs.setObjectName("Fission180CamToolTabs")
        self.tabs.setUsesScrollButtons(False)
        layout.addWidget(self.tabs)
        self._general()
        self._cutter()
        self._holder()
        self._cutting()
        self._post()
        self.message = QtWidgets.QLabel("")
        self.message.setObjectName("Fission180CamToolMessage")
        self.message.setWordWrap(True)
        self.message.setStyleSheet("color: #ff8a80;")
        layout.addWidget(self.message)
        box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        )
        box.setObjectName("Fission180CamToolButtons")
        box.accepted.connect(self._ok)
        box.rejected.connect(self.reject)
        layout.addWidget(box)
        self._show_rows()

    def _page(self, title):
        page = QtWidgets.QWidget()
        form = QtWidgets.QFormLayout(page)
        self.tabs.addTab(page, title)
        return form

    def _scale(self):
        return core.MM_PER_IN if self.tool["unit"] == "in" else 1.0

    def _text(self, form, key, label, value):
        box = QtWidgets.QLineEdit(str(value or ""))
        box.setObjectName("Fission180CamTool_" + key)
        form.addRow(label, box)
        self.fields[key] = box

    def _spin(self, form, key, label, value, low=0.0, high=100000.0, decimals=4, suffix=""):
        box = QtWidgets.QDoubleSpinBox()
        box.setObjectName("Fission180CamTool_" + key)
        box.setRange(low, high)
        box.setDecimals(decimals)
        if suffix:
            box.setSuffix(suffix)
        box.setValue(float(value))
        box.setKeyboardTracking(False)
        text = QtWidgets.QLabel(label)
        form.addRow(text, box)
        self.fields[key] = box
        return text, box

    def _combo(self, form, key, label, rows, current):
        box = QtWidgets.QComboBox()
        box.setObjectName("Fission180CamTool_" + key)
        for value, text in rows:
            box.addItem(text, value)
        index = box.findData(current)
        box.setCurrentIndex(index if index >= 0 else 0)
        form.addRow(label, box)
        self.fields[key] = box
        return box

    def _general(self):
        form = self._page("General")
        tool = self.tool
        self._text(form, "name", "Description", tool["name"])
        self._text(form, "vendor", "Vendor", tool["vendor"])
        self._text(form, "product_id", "Product ID", tool["product_id"])
        self._text(form, "comment", "Comment", tool["comment"])
        unit = self._combo(
            form, "unit", "Unit", (("mm", "Millimeters"), ("in", "Inches")), tool["unit"]
        )
        unit.currentIndexChanged.connect(self._unit_changed)

    def _cutter(self):
        form = self._page("Cutter")
        tool = self.tool
        kind = self._combo(
            form, "type", "Type", [(k, v[0]) for k, v in core.TOOL_TYPES.items()], tool["type"]
        )
        kind.currentIndexChanged.connect(self._show_rows)
        scale = self._scale()
        self.length_rows = {}
        for key, label in self.LENGTHS:
            self.length_rows[key] = self._spin(form, key, label, tool[key] / scale)
        self._spin(form, "flutes", "Number of Flutes", tool["flutes"], 1, 20, 0)
        self._combo(
            form, "material", "Material", [(m, m) for m in core.TOOL_MATERIALS], tool["material"]
        )
        self.angle_rows = {
            "taper_angle": self._spin(
                form, "taper_angle", "Taper Angle", tool["taper_angle"], 1, 89, 2, " deg"
            ),
            "tip_angle": self._spin(
                form, "tip_angle", "Tip Angle", tool["tip_angle"], 30, 180, 2, " deg"
            ),
        }

    def _holder(self):
        form = self._page("Holder")
        holder = self.tool["holder"]
        scale = self._scale()
        self._text(form, "holder_name", "Holder", holder.get("name", ""))
        self._spin(
            form, "holder_diameter", "Holder Diameter", float(holder.get("diameter") or 0.0) / scale
        )
        self._spin(
            form, "holder_length", "Holder Length", float(holder.get("length") or 0.0) / scale
        )
        note = QtWidgets.QLabel("The holder is kept with the tool; Simulate does not check it yet.")
        note.setWordWrap(True)
        form.addRow(note)

    def _cutting(self):
        form = self._page("Cutting Data")
        cutting = self.tool["cutting"]
        scale = self._scale()
        for key, label, suffix, length in self.CUTTING:
            value = cutting[key] / scale if length else cutting[key]
            self._spin(form, "cut_" + key, label, value, 0.0, 1000000.0, 4 if length else 0, suffix)
        self._combo(
            form, "cut_coolant", "Coolant", core.COOLANTS, cutting.get("coolant", "disabled")
        )
        suggest = QtWidgets.QPushButton("Suggest")
        suggest.setObjectName("Fission180CamToolSuggest")
        suggest.setToolTip(
            "Starting values for aluminium and hard woods from the tool's size (the usual "
            "formulas; check your tool maker's table)"
        )
        suggest.clicked.connect(self._suggest)
        form.addRow(suggest)

    def _post(self):
        form = self._page("Post Processor")
        self._spin(form, "number", "Number", self.tool["number"], 0, 9999, 0)
        note = QtWidgets.QLabel("The tool number the program calls (T1, T2...).")
        note.setWordWrap(True)
        form.addRow(note)

    def _show_rows(self, *_a):
        kind = self.fields["type"].currentData()
        show = {
            "corner_radius": kind == "bull",
            "tip_diameter": kind == "chamfer",
            "shoulder_length": kind in core.MILLS,
        }
        for key, (label, box) in self.length_rows.items():
            on = show.get(key, True)
            label.setVisible(on)
            box.setVisible(on)
        for key, (label, box) in self.angle_rows.items():
            on = (key == "taper_angle" and kind == "chamfer") or (
                key == "tip_angle" and kind in ("drill", "spot")
            )
            label.setVisible(on)
            box.setVisible(on)

    def _unit_changed(self, *_a):
        """The sizes shown are converted so the tool stays the same size."""
        try:
            new = self.fields["unit"].currentData()
            old = self.tool["unit"]
            if new == old:
                return
            factor = (core.MM_PER_IN if old == "in" else 1.0) / (
                core.MM_PER_IN if new == "in" else 1.0
            )
            keys = [k for k, _l in self.LENGTHS] + ["holder_diameter", "holder_length"]
            keys += ["cut_" + k for k, _l, _s, length in self.CUTTING if length]
            for key in keys:
                self.fields[key].setValue(self.fields[key].value() * factor)
            self.tool["unit"] = new
        except Exception as exc:
            warn("tool editor: %s" % exc)

    def read(self):
        tool = core.merge(self.tool, None)
        scale = core.MM_PER_IN if self.fields["unit"].currentData() == "in" else 1.0
        for key in ("name", "vendor", "product_id", "comment"):
            tool[key] = self.fields[key].text().strip()
        tool["unit"] = self.fields["unit"].currentData()
        tool["type"] = self.fields["type"].currentData()
        tool["material"] = self.fields["material"].currentData()
        for key, _label in self.LENGTHS:
            tool[key] = self.fields[key].value() * scale
        tool["flutes"] = int(self.fields["flutes"].value())
        tool["taper_angle"] = self.fields["taper_angle"].value()
        tool["tip_angle"] = self.fields["tip_angle"].value()
        tool["number"] = int(self.fields["number"].value())
        tool["holder"] = {
            "name": self.fields["holder_name"].text().strip(),
            "diameter": self.fields["holder_diameter"].value() * scale,
            "length": self.fields["holder_length"].value() * scale,
        }
        for key, _label, _suffix, length in self.CUTTING:
            value = self.fields["cut_" + key].value()
            tool["cutting"][key] = value * scale if length else value
        tool["cutting"]["coolant"] = self.fields["cut_coolant"].currentData()
        if tool["type"] == "ball":
            tool["corner_radius"] = tool["diameter"] / 2.0
        if not tool["name"]:
            tool["name"] = core.tool_size_name(tool)
        return core.tool(tool)

    def _suggest(self):
        try:
            tool = self.read()
            data = core.cutting_data(
                tool["type"], tool["diameter"], tool["flutes"], tool["material"]
            )
            scale = core.MM_PER_IN if tool["unit"] == "in" else 1.0
            for key, _label, _suffix, length in self.CUTTING:
                self.fields["cut_" + key].setValue(data[key] / scale if length else data[key])
        except Exception as exc:
            warn("tool editor: %s" % exc)

    def _ok(self):
        try:
            tool = self.read()
            problems = core.tool_problems(tool)
            if problems:
                self.message.setText(" ".join(problems))
                return
            self.on_save(tool)
        except core.CamError as exc:
            self.message.setText(str(exc))
            return
        except Exception as exc:
            warn("tool editor: %s" % exc)
            self.message.setText("The tool could not be kept: %s" % exc)
            return
        self.accept()


class LibraryDialog(QtWidgets.QDialog):
    def __init__(self, doc, on_select=None, kinds=None):
        super().__init__(Gui.getMainWindow())
        self.setObjectName("Fission180CamToolLibrary")
        self.setWindowTitle("Tool Library" if on_select is None else "Select Tool")
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.doc = doc
        self.on_select = on_select
        self.kinds = tuple(kinds) if kinds else None
        self.shown = []
        outer = QtWidgets.QVBoxLayout(self)
        split = QtWidgets.QHBoxLayout()
        outer.addLayout(split, 1)
        self.libraries = QtWidgets.QListWidget()
        self.libraries.setObjectName("Fission180CamLibraries")
        self.libraries.setFixedWidth(240)
        self.libraries.currentRowChanged.connect(lambda *_a: self.fill())
        split.addWidget(self.libraries)
        right = QtWidgets.QVBoxLayout()
        split.addLayout(right, 1)
        top = QtWidgets.QHBoxLayout()
        right.addLayout(top)
        self.search = QtWidgets.QLineEdit()
        self.search.setObjectName("Fission180CamToolSearch")
        self.search.setPlaceholderText("Search (name, diameter...)")
        self.search.textChanged.connect(lambda *_a: self.fill())
        top.addWidget(self.search, 1)
        self.filter = QtWidgets.QComboBox()
        self.filter.setObjectName("Fission180CamToolFilter")
        if self.kinds:
            self.filter.addItem("Fits this operation", "fits")
        for key, title in FILTERS:
            self.filter.addItem(title, key)
        for key, (title, _shape, _type) in core.TOOL_TYPES.items():
            self.filter.addItem(title, key)
        self.filter.currentIndexChanged.connect(lambda *_a: self.fill())
        top.addWidget(self.filter)
        self.table = QtWidgets.QTableWidget(0, len(COLUMNS))
        self.table.setObjectName("Fission180CamTools")
        self.table.setHorizontalHeaderLabels(COLUMNS)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(1, 230)
        self.table.setMinimumSize(760, 380)
        self.table.itemDoubleClicked.connect(lambda *_a: self._double_clicked())
        self.table.itemSelectionChanged.connect(self._buttons)
        right.addWidget(self.table, 1)
        self.message = QtWidgets.QLabel("")
        self.message.setObjectName("Fission180CamLibraryMessage")
        self.message.setWordWrap(True)
        outer.addWidget(self.message)
        row = QtWidgets.QHBoxLayout()
        outer.addLayout(row)
        self.new_type = QtWidgets.QComboBox()
        self.new_type.setObjectName("Fission180CamNewToolType")
        for key, (title, _shape, _type) in core.TOOL_TYPES.items():
            self.new_type.addItem(title, key)
        row.addWidget(self.new_type)
        self.buttons = {}
        for key, text, tip, slot in (
            (
                "new",
                "New Tool",
                "A new tool of the type on the left, in your own library",
                self.new_tool,
            ),
            ("edit", "Edit", "Change the selected tool", self.edit_tool),
            (
                "copy",
                "Copy To Local",
                "Copy the selected tool into your own library",
                self.copy_tool,
            ),
            ("delete", "Delete", "Delete the selected tool from your library", self.delete_tool),
            ("new_library", "New Library", "A new library of your own", self.new_library),
        ):
            button = QtWidgets.QPushButton(text)
            button.setObjectName("Fission180CamLibrary_" + key)
            button.setToolTip(tip)
            button.clicked.connect(slot)
            row.addWidget(button)
            self.buttons[key] = button
        row.addStretch(1)
        if on_select is not None:
            select = QtWidgets.QPushButton("Select")
            select.setObjectName("Fission180CamLibrary_select")
            select.setDefault(True)
            select.clicked.connect(self.select_tool)
            row.addWidget(select)
            self.buttons["select"] = select
        close = QtWidgets.QPushButton("Close" if on_select is None else "Cancel")
        close.setObjectName("Fission180CamLibrary_close")
        close.clicked.connect(self.reject)
        row.addWidget(close)
        self.fill_libraries()

    # -- lists -----------------------------------------------------------------------------
    def fill_libraries(self, keep=None):
        keep = keep or self.library_key()
        self.libraries.blockSignals(True)
        self.libraries.clear()
        rows = _lib().libraries(self.doc)
        for row in rows:
            item = QtWidgets.QListWidgetItem(
                "%s: %s" % (row["group"], row["title"]) if row["group"] == "Local" else row["title"]
            )
            item.setData(QtCore.Qt.UserRole, row["key"])
            item.setToolTip(
                "Read only: copy a tool into a library of your own to change it"
                if row["readonly"]
                else ""
            )
            self.libraries.addItem(item)
        keys = [r["key"] for r in rows]
        if keep not in keys:
            # a design with tools opens on them, else Fission 180's metric samples
            keep = "sample:mm"
            try:
                if self.doc is not None and _lib().tools("document", self.doc):
                    keep = "document"
            except Exception:
                pass
        self.libraries.setCurrentRow(keys.index(keep) if keep in keys else 0)
        self.libraries.blockSignals(False)
        self.fill()

    def library_key(self):
        item = self.libraries.currentItem()
        return item.data(QtCore.Qt.UserRole) if item is not None else None

    def local_key(self):
        """The library New Tool and Copy go to: the selected one when it is the person's
        own, else Local."""
        key = self.library_key()
        return key if key and key.startswith("local:") else "local:" + _lib().DEFAULT_LOCAL

    def _fits(self, tool):
        chosen = self.filter.currentData()
        if chosen == "fits":
            return tool["type"] in (self.kinds or ())
        if chosen == "milling":
            return tool["type"] in core.MILLS + ("chamfer",)
        if chosen == "hole":
            return tool["type"] in ("drill", "spot")
        if chosen in core.TOOL_TYPES:
            return tool["type"] == chosen
        return True

    def fill(self, select_id=None):
        try:
            key = self.library_key()
            tools = _lib().tools(key, self.doc) if key else []
        except core.CamError as exc:
            tools = []
            self.message.setText(str(exc))
        words = self.search.text().strip().lower().split()
        self.shown = []
        for tool in tools:
            if not self._fits(tool):
                continue
            hay = (
                "%s %s %s"
                % (tool["name"], core.TOOL_TYPES[tool["type"]][0], core.fmt(tool["diameter"]))
            ).lower()
            if all(w in hay for w in words):
                self.shown.append(tool)
        self.table.setRowCount(len(self.shown))
        for r, tool in enumerate(self.shown):
            unit = tool.get("unit", "mm")
            cells = (
                str(tool["number"]),
                tool["name"],
                core.TOOL_TYPES[tool["type"]][0],
                core.length_text(tool["diameter"], unit),
                core.length_text(tool["flute_length"], unit),
                str(tool["flutes"]),
                core.fmt(tool["cutting"]["spindle_speed"], 0),
                core.fmt(tool["cutting"]["cutting_feed"], 0),
            )
            for c, text in enumerate(cells):
                item = QtWidgets.QTableWidgetItem(text)
                if c == 1:
                    item.setIcon(ui_icon("cam_tool_" + tool["type"]))
                self.table.setItem(r, c, item)
            if select_id and tool.get("id") == select_id:
                self.table.selectRow(r)
        if key == "document" and not tools:
            self.message.setText(
                "This design uses no tools yet: a tool comes here when an operation uses it."
            )
        elif not self.shown and tools:
            self.message.setText(
                "No tool here fits the filter: choose All types, or another library."
            )
        else:
            self.message.setText("")
        self._buttons()

    def current_tool(self):
        row = self.table.currentRow()
        selected = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        if selected:
            row = selected[0].row()
        return self.shown[row] if 0 <= row < len(self.shown) and selected else None

    def _buttons(self):
        key = self.library_key() or ""
        tool = self.current_tool()
        own = key.startswith("local:")
        self.buttons["edit"].setEnabled(tool is not None and (own or key == "document"))
        self.buttons["delete"].setEnabled(tool is not None and own)
        self.buttons["copy"].setEnabled(tool is not None)
        if "select" in self.buttons:
            self.buttons["select"].setEnabled(tool is not None)

    def tool_names(self):
        return [t["name"] for t in self.shown]

    def select_row(self, name):
        """Select the tool named `name` in the table (tests; a click does the same)."""
        for r, tool in enumerate(self.shown):
            if tool["name"] == name:
                self.table.selectRow(r)
                return True
        return False

    # -- actions ---------------------------------------------------------------------------
    def _say(self, text):
        self.message.setText(text)

    def _edit(self, tool, key, title):
        def save(edited):
            kept = _lib().save_tool(key, edited, self.doc)
            log("tool %s saved" % core.tool_title(kept))
            self.fill_libraries(keep=key)
            self.fill(select_id=kept.get("id"))
            if key == "document":
                from . import manufacture_ui

                manufacture_ui.refresh()

        editor = ToolEditor(self, tool, save, title)
        OPEN["editor"] = editor
        editor.show()
        return editor

    def new_tool(self):
        try:
            key = self.local_key()
            kind = self.new_type.currentData()
            size = {"face": 50.0, "drill": 5.0, "spot": 6.0, "chamfer": 10.0}.get(kind, 6.0)
            tool = core.make_tool(kind, size, number=_lib().next_number(key, self.doc))
            tool["name"] = ""
            return self._edit(tool, key, "New Tool")
        except core.CamError as exc:
            self._say(str(exc))
        except Exception as exc:
            warn("tool library: %s" % exc)

    def edit_tool(self):
        tool = self.current_tool()
        key = self.library_key() or ""
        if tool is None:
            self._say("Select a tool first.")
            return None
        if not (key.startswith("local:") or key == "document"):
            self._say(
                "The sample library cannot be changed: Copy To Local first, then edit the copy."
            )
            return None
        return self._edit(tool, key, "Edit Tool")

    def copy_tool(self):
        tool = self.current_tool()
        if tool is None:
            self._say("Select a tool first.")
            return
        try:
            target = self.local_key()
            if target == self.library_key():
                target = "local:" + _lib().DEFAULT_LOCAL
            kept = _lib().copy_tool(tool, target, self.doc)
            self.fill_libraries(keep=target)
            self.fill(select_id=kept.get("id"))
            self._say("Copied %s to %s." % (core.tool_title(kept), target[6:]))
        except core.CamError as exc:
            self._say(str(exc))

    def delete_tool(self):
        tool = self.current_tool()
        key = self.library_key() or ""
        if tool is None:
            self._say("Select a tool first.")
            return
        try:
            _lib().delete_tool(key, tool["id"], self.doc)
            self.fill()
            self._say("Deleted %s." % core.tool_title(tool))
        except core.CamError as exc:
            self._say(str(exc))

    def new_library(self):
        name, ok = QtWidgets.QInputDialog.getText(self, "New Library", "Name of the library")
        if not ok:
            return
        try:
            key = _lib().new_library(name)
            self.fill_libraries(keep=key)
        except core.CamError as exc:
            self._say(str(exc))

    def _double_clicked(self):
        if self.on_select is not None:
            self.select_tool()
        else:
            self.edit_tool()

    def select_tool(self):
        tool = self.current_tool()
        if tool is None:
            self._say("Select a tool first.")
            return
        if self.kinds and tool["type"] not in self.kinds:
            names = ", ".join(core.TOOL_TYPES[k][0].lower() for k in self.kinds)
            self._say(
                "This operation cannot cut with a %s: pick a %s."
                % (core.TOOL_TYPES[tool["type"]][0].lower(), names)
            )
            return
        callback = self.on_select
        self.accept()
        try:
            callback(core.tool(tool))
        except Exception as exc:
            warn("tool library: %s" % exc)


def open_library(doc=None, on_select=None, kinds=None):
    """The Tool Library window (with Select when an operation asks for a tool)."""
    doc = doc or App.ActiveDocument
    if on_select is None and not commands.finish_open_dialog():
        return None
    close()
    dialog = LibraryDialog(doc, on_select, kinds)
    OPEN["library"] = dialog
    dialog.show()
    return dialog


def library_dialog():
    dialog = OPEN["library"]
    return dialog if dialog is not None and _alive(dialog) and dialog.isVisible() else None


def editor_dialog():
    dialog = OPEN["editor"]
    return dialog if dialog is not None and _alive(dialog) and dialog.isVisible() else None


def close():
    for key in ("editor", "library"):
        dialog = OPEN[key]
        OPEN[key] = None
        if dialog is not None and _alive(dialog) and dialog.isVisible():
            try:
                dialog.reject()
            except Exception:
                pass


COMMANDS = {}
