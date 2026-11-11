# SPDX-License-Identifier: LGPL-2.1-or-later
"""Physical Material (Modify > Physical Material) with a Fusion-like dialog:

  In This Design  the materials the bodies are made of now
  Library         steels, aluminium, copper, titanium, plastics (ABS, PLA, PETG, nylon,
                  polycarbonate, acetal, acrylic...), wood, glass, with their density

Pick a material, then click bodies in the 3D view (or the browser): each click makes that
body of the material, and gives it the material's look unless it has an Appearance of its
own. Or drag a material from the list onto a body, as in Fusion. Bodies selected before the
command get the first material picked. The bodies' mass is
shown, each body with its component's name. A search box narrows the library. Library
materials cannot be changed (as in Fusion); double-click one (or right-click > Edit a Copy)
to make a material of your own from it with another density: it is listed under My
Materials from then on. OK keeps it (one undo step), Cancel / Esc puts the old materials
back. The material
is FreeCAD's own (the body's ShapeMaterial, saved in the file); Inspect and Measure read the
mass through bodies.mass(). The document side is material.py.
"""

import FreeCAD as App

from . import bodies, bodies_gui, material, ui_icon_path, warn
from .bodies_panel import BodyPanel, start as _start
from .compat import QtCore, QtWidgets

MIME = "application/x-fission180-material"


def key_of(mime):
    """The material key carried by a drag (a row of the dialog's library), or None."""
    try:
        if mime is None or not mime.hasFormat(MIME):
            return None
        return bytes(mime.data(MIME)).decode("utf-8") or None
    except Exception:
        return None


class _MaterialList(QtWidgets.QListWidget):
    """The library; dragging a row carries its material (drop it on a body)."""

    def mimeTypes(self):
        return [MIME]

    def mimeData(self, items):
        mime = QtCore.QMimeData()
        key = items[0].data(QtCore.Qt.UserRole) if items else None
        if key:
            mime.setData(MIME, QtCore.QByteArray(str(key).encode("utf-8")))
        return mime


class _DropTaker(QtCore.QObject):
    """Event filter on the 3D view: takes a material dragged from the dialog."""

    def __init__(self, panel):
        super().__init__()
        self.panel = panel

    def eventFilter(self, obj, event):
        try:
            kind = event.type()
            if kind not in (QtCore.QEvent.DragEnter, QtCore.QEvent.DragMove, QtCore.QEvent.Drop):
                return False
            panel = self.panel
            if panel is None or panel._closed:
                return False
            key = key_of(event.mimeData())
            if key is None:
                return False
            if kind == QtCore.QEvent.Drop:
                position = event.position().toPoint()
                QtCore.QTimer.singleShot(
                    0, lambda: panel._guarded(lambda: panel.dropped(key, position))
                )
            event.setDropAction(QtCore.Qt.CopyAction)
            event.accept()
            return True
        except Exception as exc:
            warn("material drop: %s" % exc)
            return False


class _EnterStays(QtCore.QObject):
    """Event filter: Enter / Return in a field goes no further (the task panel would take it
    as OK and close the dialog)."""

    def eventFilter(self, obj, event):
        try:
            if event.type() == QtCore.QEvent.KeyPress and event.key() in (
                QtCore.Qt.Key_Return,
                QtCore.Qt.Key_Enter,
            ):
                return True
        except Exception:
            pass
        return False


class MaterialPanel(BodyPanel):
    title = "Physical Material"
    icon = "material"
    needs_pick = ()

    def picks_bodies(self):
        """Every click takes a whole body: it lights up whole under the pointer (body_hover)."""
        return True

    def __init__(self, doc):
        self.key = None
        self.pending = []
        self.touched = []
        super().__init__(doc, "Physical Material")
        self.pending = []
        for obj, _s, _p in bodies_gui.selection_entries():
            body = bodies.body_of(obj)
            if obj.Document is doc and body is not None and body not in self.pending:
                self.pending.append(body)
        bodies_gui.clear_selection()
        self._fill_design()
        self._drop_widget = None
        self._install_drop()
        self.info.setText(
            "Pick a material, then click bodies to make them of it (or drag it onto them)."
            if not self.pending
            else "Pick a material for the selected bodies."
        )

    def build_form(self):
        self.layout.addRow(QtWidgets.QLabel("<b>In This Design</b>"))
        self.design = QtWidgets.QListWidget()
        self.design.setFixedHeight(90)
        self.design.itemClicked.connect(lambda item: self._guarded(lambda: self._clicked(item)))
        self.layout.addRow(self.design)
        self.layout.addRow(QtWidgets.QLabel("<b>Library</b>"))
        self.search = QtWidgets.QLineEdit()
        self.search.setObjectName("Fission180MaterialPanelSearch")
        self.search.setPlaceholderText("Search")
        self.search.setClearButtonEnabled(True)
        self.search.textChanged.connect(lambda *_: self._guarded(self._fill_library))
        # Enter in the search box must not reach the task panel (it would press OK).
        self._search_enter = _EnterStays()
        self.search.installEventFilter(self._search_enter)
        self.layout.addRow(self.search)
        self.library = _MaterialList()
        self.library.setObjectName("Fission180MaterialPanelLibrary")
        self.library.setMinimumHeight(240)
        self.library.setDragEnabled(True)  # Fusion: drag a material onto a body
        self.library.setDragDropMode(QtWidgets.QAbstractItemView.DragOnly)
        self.library.itemClicked.connect(lambda item: self._guarded(lambda: self._clicked(item)))
        self.library.itemDoubleClicked.connect(
            lambda item: self._guarded(lambda: self.edit_copy(item.data(QtCore.Qt.UserRole)))
        )
        self.library.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.library.customContextMenuRequested.connect(
            lambda pos: self._guarded(lambda: self._library_menu(pos))
        )
        self.layout.addRow(self.library)
        self.found = QtWidgets.QLabel("")
        self.found.setStyleSheet("color: #b8c7d9;")
        self.layout.addRow(self.found)
        self._fill_library()
        # Edit a Copy: library materials are read-only (Fusion), a copy gets its own density.
        self.copy_box = QtWidgets.QGroupBox("Edit a Copy")
        self.copy_box.setObjectName("Fission180MaterialCopyBox")
        form = QtWidgets.QFormLayout(self.copy_box)
        self.copy_of = QtWidgets.QLabel("")
        form.addRow("Copy of", self.copy_of)
        self.copy_name = QtWidgets.QLineEdit()
        self.copy_name.setObjectName("Fission180MaterialCopyName")
        form.addRow("Name", self.copy_name)
        self.copy_density = QtWidgets.QLineEdit()
        self.copy_density.setObjectName("Fission180MaterialCopyDensity")
        form.addRow("Density (g/cm³)", self.copy_density)
        self._copy_enter = _EnterStays()
        self.copy_name.installEventFilter(self._copy_enter)
        self.copy_density.installEventFilter(self._copy_enter)
        row = QtWidgets.QHBoxLayout()
        self.copy_create = QtWidgets.QPushButton("Create")
        self.copy_create.setObjectName("Fission180MaterialCopyCreate")
        self.copy_create.clicked.connect(lambda *_: self._guarded(self.create_copy))
        self.copy_cancel = QtWidgets.QPushButton("Close")
        self.copy_cancel.clicked.connect(lambda *_: self.copy_box.setVisible(False))
        row.addWidget(self.copy_create)
        row.addWidget(self.copy_cancel)
        form.addRow(row)
        self.copy_box.setVisible(False)
        self.copy_base = None
        self.layout.addRow(self.copy_box)
        self.chosen = QtWidgets.QLabel("")
        self.chosen.setStyleSheet("color: #b8c7d9;")
        self.layout.addRow("Material", self.chosen)
        self.masses = QtWidgets.QLabel("")
        self.masses.setWordWrap(True)
        self.masses.setStyleSheet("color: #b8c7d9;")
        self.layout.addRow("Mass", self.masses)

    def _fill_library(self):
        """The library list: every material, or the ones the search box asks for."""
        text = self.search.text().strip() if hasattr(self, "search") else ""
        rows = material.search(text)
        self.library.clear()
        for row in rows:
            rho = material.density_of(row["key"])
            label = row["label"]
            if rho is not None:
                label += "   %.3g g/cm³" % (rho * 1e6)
            item = QtWidgets.QListWidgetItem(label)
            item.setData(QtCore.Qt.UserRole, row["key"])
            item.setToolTip(
                "%s (%s). Double-click to make a copy of your own with another density."
                % (row["label"], row["group"])
            )
            self.library.addItem(item)
        if text and not rows:
            self.found.setText('No material called "%s". Try fewer letters.' % text)
        else:
            self.found.setText("%d materials" % len(rows) if text else "")

    def _fill_design(self):
        self.design.clear()
        used = {}
        for body in _material_bodies(self.doc):
            label, _rho = material.effective(body)
            used.setdefault((material.key_of(body), label), []).append(body)
        for (key, label), found in sorted(used.items(), key=lambda kv: kv[0][1]):
            names = ", ".join(material.body_name(b) for b in found[:4])
            if len(found) > 4:
                names += " and %d more" % (len(found) - 4)
            item = QtWidgets.QListWidgetItem("%s  (%s)" % (label, names))
            item.setData(QtCore.Qt.UserRole, key or material.DEFAULT_KEY)
            self.design.addItem(item)
        self._show_masses()

    def _show_masses(self):
        rows = []
        for body in bodies.solid_bodies(self.doc, visible_only=True):
            kg = material.mass(body)
            label, _rho = material.effective(body)
            if kg is not None:
                rows.append("%s: %s (%s)" % (material.body_name(body), _mass_text(kg), label))
        self.masses.setText("\n".join(rows))

    def item_for(self, label):
        """The library row of the material called `label`, among the ones listed now."""
        for i in range(self.library.count()):
            item = self.library.item(i)
            if material.entry(item.data(QtCore.Qt.UserRole))["label"] == label:
                return item
        return None

    # -- a copy of a library material with its own density ------------------------------------
    def _library_menu(self, pos):
        item = self.library.itemAt(pos)
        if item is None:
            return
        key = item.data(QtCore.Qt.UserRole)
        menu = QtWidgets.QMenu(self.library)
        menu.setObjectName("Fission180MaterialMenu")
        menu.addAction("Edit a Copy", lambda: self._guarded(lambda: self.edit_copy(key)))
        menu.exec(self.library.viewport().mapToGlobal(pos))

    def edit_copy(self, key):
        row = material.entry(key)
        if row is None:
            return
        self.copy_base = key
        self.copy_of.setText(row["label"])
        taken = material.taken_names()
        name, number = "%s (1)" % row["label"], 1
        while name.lower() in taken:
            number += 1
            name = "%s (%d)" % (row["label"], number)
        self.copy_name.setText(name)
        rho = material.density_of(key)
        self.copy_density.setText("%.4g" % (rho * 1e6) if rho is not None else "")
        self.copy_box.setVisible(True)
        self.message.setText("")
        self.info.setText(
            "Library materials cannot be changed. Give the copy a name and a density, then "
            "Create."
        )
        self.copy_density.setFocus()
        self.copy_density.selectAll()

    def create_copy(self):
        base = self.copy_base
        row = material.entry(base) if base else None
        if row is None:
            return
        if row.get("uuid"):  # a copy of one of the user's own: built on what that was built on
            base = row.get("base") or material.DEFAULT_KEY
        try:
            key = material.create_user_material(
                self.copy_name.text(), base, self.copy_density.text().replace(",", ".")
            )
        except material.MaterialError as exc:
            self.message.setText("⚠ %s" % exc)
            return
        self.message.setText("")
        self.copy_box.setVisible(False)
        self.search.clear()
        self._fill_library()
        made = material.entry(key)
        item = self.item_for(made["label"])
        if item is not None:
            self.library.setCurrentItem(item)
            self.library.scrollToItem(item)
            self._clicked(item)
        self.note.setText("%s made: it is under My Materials" % made["label"])

    def _clicked(self, item):
        key = item.data(QtCore.Qt.UserRole)
        row = material.entry(key)
        if row is None:
            return
        self.key = key
        self.chosen.setText(row["label"])
        self.info.setText("Click bodies to make them of %s." % row["label"])
        if self.pending:
            pending, self.pending = self.pending, []
            for body in pending:
                self._give(body)

    def picked(self, obj, short, point):
        body = bodies.body_of(obj)
        if body is None:
            return
        if self.key is None:
            if body not in self.pending:
                self.pending.append(body)
            self.message.setText("Pick a material first, then click.")
            return
        self.message.setText("")
        self._give(body)

    def _give(self, body):
        try:
            material.assign(body, self.key)
        except material.MaterialError as exc:
            self.message.setText("⚠ %s" % exc)
            return
        if body not in self.touched:
            self.touched.append(body)
        try:
            from . import appearance

            appearance.apply(body, force=True)
        except Exception as exc:
            warn("appearance: %s" % exc)
        self._fill_design()
        text = "%s: %s" % (material.body_name(body), material.entry(self.key)["label"])
        try:
            from . import appearance

            if appearance.get(body).get("body"):
                text += " (it keeps its Appearance, %s)" % appearance.get(body)["body"]["label"]
        except Exception:
            pass
        self.note.setText(text)

    # -- drag and drop -------------------------------------------------------------------------
    def _install_drop(self):
        try:
            from .appearance_ui import _gl_widget

            widget = _gl_widget()
            if widget is None:
                return
            self._drop_widget = widget
            self._drop_filter = _DropTaker(self)
            self._drop_accepted = widget.acceptDrops()
            widget.setAcceptDrops(True)
            widget.installEventFilter(self._drop_filter)
        except Exception as exc:
            warn("material drag and drop unavailable: %s" % exc)

    def remove_handles(self):
        widget = getattr(self, "_drop_widget", None)
        if widget is not None:
            try:
                widget.removeEventFilter(self._drop_filter)
                widget.setAcceptDrops(self._drop_accepted)
            except Exception:
                pass
            self._drop_widget = None

    def dropped(self, key, position):
        """A material dropped at widget pixel `position`: the body there is made of it."""
        widget = self._drop_widget
        row = material.entry(key)
        if widget is None or row is None:
            return False
        ratio = widget.devicePixelRatioF()
        info = self.view.getObjectInfo(
            (position.x() * ratio, (widget.height() - position.y()) * ratio)
        )
        obj = self.doc.getObject(info["Object"]) if info and info.get("Object") else None
        body = bodies.body_of(obj)
        if body is None:
            self.message.setText("Drop the material on a body.")
            return False
        self.key = key
        self.chosen.setText(row["label"])
        self.message.setText("")
        self._give(body)
        return True


def _mass_text(kg):
    if kg >= 1.0:
        return "%.3f kg" % kg
    return "%.2f g" % (kg * 1000.0)


class MaterialCommand:
    def GetResources(self):
        return {
            "MenuText": "Physical Material",
            "ToolTip": "Say what bodies are made of (steel, aluminium, plastics...): their "
            "mass and look follow",
            "Pixmap": ui_icon_path("material"),
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        try:
            _start(MaterialPanel)
        except Exception as exc:
            warn("Physical Material could not start: %s" % exc)


COMMANDS = {"Fission180_PhysicalMaterial": MaterialCommand}


def _material_bodies(doc):
    """The bodies whose materials the dialog lists: solids and surface bodies (a surface
    body has a material and a look too, only no mass; surface-4)."""
    found = list(bodies.solid_bodies(doc))
    try:
        from . import surface

        found += [b for b in surface.surface_bodies(doc) if b not in found]
    except Exception:
        pass
    return found
