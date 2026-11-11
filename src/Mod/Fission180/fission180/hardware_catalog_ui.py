# SPDX-License-Identifier: LGPL-2.1-or-later
"""INSERT > Insert Catalogue Part...: a part from a supplier's online catalogue (the stand-in
for Fusion's Insert McMaster-Carr Component; the rules are in hardware_catalog.py).

1. Supplier: pick one of the list (McMaster-Carr, MISUMI, TraceParts to start with; + adds
   your own name and address, - removes one), type the part number or what you look for,
   and "Open in my web browser" shows that page in your own browser. Fission 180 itself
   fetches nothing.
2. There you download the part's 3D model as STEP (or IGES).
3. "Downloaded file" lists the STEP / IGES files of your Downloads folder, the newest
   first (it looks again every two seconds while the dialog is open, so the file you just
   saved is picked by itself); Browse takes a file from anywhere.
4. OK (or "Insert the file I downloaded"): the file comes in as a component named after it,
   at the origin, and the Move dialog opens on it: the way Fusion's command ends, and the
   way the Data Panel's "Insert into Current Design" works.

Cancel or Esc changes nothing. A problem is said in the dialog, which then stays open.
"""

import os
import time

import FreeCAD as App
import FreeCADGui as Gui

from . import commands, log, preview, ui_icon_path, warn
from . import hardware_catalog as core
from .compat import QtCore, QtGui, QtWidgets
from .taskui import Panel

PREFS = "User parameter:BaseApp/Preferences/Mod/Fission180/Hardware"
OPENED = []  # every address handed to the web browser this session (the tests read it)
POLL_MS = 2000


def _prefs():
    return App.ParamGet(PREFS)


def suppliers():
    return core.load_suppliers(_prefs().GetString("Suppliers", ""))


def save_suppliers(rows):
    _prefs().SetString("Suppliers", core.dump_suppliers(rows))


def downloads_folder():
    standard = ""
    try:
        standard = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.DownloadLocation)
    except Exception:
        standard = ""
    return core.downloads_folder(saved=_prefs().GetString("Downloads", ""), standard=standard)


def open_address(address):
    """Show an address in the person's own web browser. With FISSION180_NO_INTERNET set (the
    tests) nothing is started; the address is only noted."""
    OPENED.append(address)
    log("catalogue: opening %s in the web browser" % address)
    if os.environ.get("FISSION180_NO_INTERNET"):
        return True
    return bool(QtGui.QDesktopServices.openUrl(QtCore.QUrl(address)))


def _safe(method):
    def wrapper(self, *args):
        try:
            return method(self, *args)
        except Exception as exc:
            warn("Insert Catalogue Part: %s" % exc)
            try:
                self.message.setText("⚠ %s" % exc)
            except Exception:
                pass
        return None

    wrapper.__name__ = method.__name__
    return wrapper


class CataloguePanel(Panel):
    title = "Insert Catalogue Part"
    icon = "catalogue_part"
    last = None

    def __init__(self, doc):
        super().__init__(doc, "Insert Catalogue Part")
        CataloguePanel.last = self
        self.escape = preview.EscapeCancels(self)
        self.rows = suppliers()
        self.files = []
        self.browsed = ""
        self._quiet = False
        self._build_form()
        self._show_suppliers(0)
        self._look_for_files()
        self.poll = QtCore.QTimer()
        self.poll.setInterval(POLL_MS)
        self.poll.timeout.connect(self._look_for_files)
        self.poll.start()

    def _build_form(self):
        form = self.layout
        info = QtWidgets.QLabel(core.INFO)
        info.setObjectName("Fission180Catalogue_info")
        info.setWordWrap(True)
        info.setStyleSheet("color: #9aa4b2;")
        form.addRow(info)
        self.supplier = QtWidgets.QComboBox()
        self.supplier.setObjectName("Fission180Catalogue_supplier")
        self.add_button = QtWidgets.QToolButton()
        self.add_button.setText("+")
        self.add_button.setObjectName("Fission180Catalogue_add")
        self.add_button.setToolTip("Add a supplier of your own: type its name and web address below")
        self.remove_button = QtWidgets.QToolButton()
        self.remove_button.setText("−")
        self.remove_button.setObjectName("Fission180Catalogue_remove")
        self.remove_button.setToolTip("Take this supplier off the list")
        line = QtWidgets.QHBoxLayout()
        line.setContentsMargins(0, 0, 0, 0)
        line.addWidget(self.supplier, 1)
        line.addWidget(self.add_button)
        line.addWidget(self.remove_button)
        holder = QtWidgets.QWidget()
        holder.setLayout(line)
        form.addRow("Supplier", holder)
        self.name = QtWidgets.QLineEdit()
        self.name.setObjectName("Fission180Catalogue_name")
        self.name.setPlaceholderText("The supplier's name")
        self.name_label = QtWidgets.QLabel("Name")
        form.addRow(self.name_label, self.name)
        self.address = QtWidgets.QLineEdit()
        self.address.setObjectName("Fission180Catalogue_address")
        self.address.setToolTip(
            "The supplier's web address. Put {} where a part number or search words go"
        )
        form.addRow("Address", self.address)
        self.words = QtWidgets.QLineEdit()
        self.words.setObjectName("Fission180Catalogue_words")
        self.words.setPlaceholderText("A part number or what you look for (optional)")
        form.addRow("Part", self.words)
        self.open_button = QtWidgets.QPushButton("Open in my web browser")
        self.open_button.setObjectName("Fission180Catalogue_open")
        form.addRow("", self.open_button)
        self.file = QtWidgets.QComboBox()
        self.file.setObjectName("Fission180Catalogue_file")
        self.browse_button = QtWidgets.QToolButton()
        self.browse_button.setText("Browse...")
        self.browse_button.setObjectName("Fission180Catalogue_browse")
        line = QtWidgets.QHBoxLayout()
        line.setContentsMargins(0, 0, 0, 0)
        line.addWidget(self.file, 1)
        line.addWidget(self.browse_button)
        holder = QtWidgets.QWidget()
        holder.setLayout(line)
        form.addRow("Downloaded file", holder)
        self.folder = QtWidgets.QLabel("")
        self.folder.setObjectName("Fission180Catalogue_folder")
        self.folder.setWordWrap(True)
        self.folder.setStyleSheet("color: #9aa4b2;")
        form.addRow("", self.folder)
        self.insert_button = QtWidgets.QPushButton("Insert the file I downloaded")
        self.insert_button.setObjectName("Fission180Catalogue_insert")
        form.addRow("", self.insert_button)
        self.finish_layout()
        self.name_label.setVisible(False)
        self.name.setVisible(False)
        self.supplier.currentIndexChanged.connect(self._supplier_changed)
        self.address.editingFinished.connect(self._address_edited)
        self.add_button.clicked.connect(self._add_clicked)
        self.remove_button.clicked.connect(self._remove_clicked)
        self.open_button.clicked.connect(self._open_clicked)
        self.browse_button.clicked.connect(self._browse_clicked)
        self.insert_button.clicked.connect(self._insert_clicked)

    # -- suppliers ------------------------------------------------------------------------------
    def _show_suppliers(self, index):
        self._quiet = True
        try:
            self.supplier.clear()
            for name, _address in self.rows:
                self.supplier.addItem(name)
            if self.rows:
                index = max(0, min(index, len(self.rows) - 1))
                self.supplier.setCurrentIndex(index)
                self.address.setText(self.rows[index][1])
        finally:
            self._quiet = False

    @_safe
    def _supplier_changed(self, index):
        if self._quiet or not 0 <= index < len(self.rows):
            return
        self.address.setText(self.rows[index][1])
        self.message.setText("")

    @_safe
    def _address_edited(self):
        """A changed address is kept for its supplier (unless a new one is being typed)."""
        if self.name.isVisible():
            return
        index = self.supplier.currentIndex()
        if not 0 <= index < len(self.rows):
            return
        try:
            address = core.clean_address(self.address.text())
        except core.CatalogueError as exc:
            self.message.setText("⚠ %s" % exc)
            return
        if address != self.rows[index][1]:
            self.rows[index] = (self.rows[index][0], address)
            save_suppliers(self.rows)

    @_safe
    def _add_clicked(self, *_):
        """First click: the Name box opens (type the name and the address). Second: kept."""
        if not self.name.isVisible():
            self.name_label.setVisible(True)
            self.name.setVisible(True)
            self.name.clear()
            self.address.clear()
            self.name.setFocus()
            self.message.setText("Type the new supplier's name and web address, then + again.")
            return
        name = self.name.text().strip()
        if not name:
            self.message.setText("⚠ Give the new supplier a name.")
            return
        if name.lower() in {n.lower() for n, _a in self.rows}:
            self.message.setText("⚠ There is already a supplier called %s." % name)
            return
        try:
            address = core.clean_address(self.address.text())
        except core.CatalogueError as exc:
            self.message.setText("⚠ %s" % exc)
            return
        self.rows.append((name, address))
        save_suppliers(self.rows)
        self.name_label.setVisible(False)
        self.name.setVisible(False)
        self._show_suppliers(len(self.rows) - 1)
        self.message.setText("")

    @_safe
    def _remove_clicked(self, *_):
        if self.name.isVisible():  # a new one being typed: given up
            self.name_label.setVisible(False)
            self.name.setVisible(False)
            self._show_suppliers(self.supplier.currentIndex())
            self.message.setText("")
            return
        index = self.supplier.currentIndex()
        if len(self.rows) <= 1:
            self.message.setText("⚠ The last supplier stays: change its address instead.")
            return
        if 0 <= index < len(self.rows):
            del self.rows[index]
            save_suppliers(self.rows)
            self._show_suppliers(index)

    def address_now(self):
        return core.address_for(self.address.text(), self.words.text())

    @_safe
    def _open_clicked(self, *_):
        try:
            address = self.address_now()
        except core.CatalogueError as exc:
            self.message.setText("⚠ %s" % exc)
            return
        if open_address(address):
            self.message.setText("")
            self.folder.setText(
                "Opened %s in your web browser. Download the part as STEP; it shows up here."
                % address
            )
        else:
            self.message.setText(
                "⚠ The web browser could not be started. Open %s yourself." % address
            )

    # -- the downloaded file --------------------------------------------------------------------
    def _look_for_files(self):
        """The STEP / IGES files of the Downloads folder, newest first (and the browsed one
        on top). A new newest file is picked by itself."""
        try:
            if self._closed:
                return
            folder = downloads_folder()
            found = core.downloaded_files(folder)
            paths = [p for p, _t in found]
            if self.browsed and self.browsed not in paths:
                try:
                    found.insert(0, (self.browsed, os.path.getmtime(self.browsed)))
                except OSError:
                    self.browsed = ""
            if found == self.files:
                return
            before = self.file.currentData()
            newest_before = self.files[0][0] if self.files else None
            self.files = found
            now = time.time()
            self._quiet = True
            try:
                self.file.clear()
                for path, changed in found:
                    self.file.addItem(core.file_label(path, changed, now), path)
                pick = 0
                paths = [p for p, _t in found]
                if before in paths and (not found or found[0][0] == newest_before):
                    pick = paths.index(before)  # nothing newer came: the choice stays
                if self.browsed in paths:
                    pick = paths.index(self.browsed)
                if found:
                    self.file.setCurrentIndex(pick)
            finally:
                self._quiet = False
            if not found:
                self.folder.setText("No STEP or IGES file in %s yet." % folder)
            elif not self.folder.text().startswith("Opened"):
                self.folder.setText("Looking in %s" % folder)
        except Exception as exc:
            warn("Insert Catalogue Part: %s" % exc)

    @_safe
    def _browse_clicked(self, *_):
        from . import insert_ui

        path = insert_ui.pick_file("step")
        if not path:
            return
        if not path.lower().endswith(core.EXTENSIONS):
            self.message.setText("⚠ Pick a STEP or IGES file (.step, .stp, .iges, .igs).")
            return
        self.browsed = path
        self.files = None  # (list again)
        self._look_for_files()
        self.message.setText("")

    def chosen(self):
        return self.file.currentData() or ""

    @_safe
    def _insert_clicked(self, *_):
        self.accept()

    # -- OK / Cancel ----------------------------------------------------------------------------
    def accept(self):
        if self._closed:
            return True
        path = self.chosen()
        if not path or not os.path.isfile(path):
            self.message.setText(
                "⚠ No downloaded file yet. In the supplier's page download the part's 3D "
                "model as STEP, then pick it here (or Browse)."
            )
            return False
        self.cleanup()
        preview.end_transaction(self.doc, abort=True)  # nothing was changed so far
        self._close()
        doc_name = self.doc.Name
        QtCore.QTimer.singleShot(0, lambda: insert_file(path, doc_name))
        return True

    def reject(self):
        if self._closed:
            return True
        self.cleanup()
        preview.end_transaction(self.doc, abort=True)
        self._close()
        return True

    def cleanup(self):
        try:
            self.poll.stop()
        except Exception:
            pass
        try:
            self.escape.remove()
        except Exception:
            pass
        super().cleanup()


def insert_file(path, doc_name=None):
    """Insert the downloaded STEP / IGES file as a component, then Move (insert_ui.py's
    Insert STEP: one undo step, the component named after the file)."""
    from . import insert, insert_ui

    try:
        if doc_name and doc_name in App.listDocuments():
            App.setActiveDocument(doc_name)
        made = insert_ui.insert_step_file(path)
        log("catalogue part %s inserted" % os.path.basename(path))
        return made
    except insert.InsertError as exc:
        commands.tell("%s could not be inserted: %s" % (os.path.basename(path), exc))
    except Exception as exc:
        warn("Insert Catalogue Part: %s" % exc)
        commands.tell("%s could not be inserted: %s" % (os.path.basename(path), exc))
    return None


class CatalogueCommand:
    def GetResources(self):
        return {
            "MenuText": "Insert Catalogue Part...",
            "ToolTip": "A part from a supplier's online catalogue (McMaster-Carr and "
            "others): open the supplier's website in your web browser, download the part "
            "as STEP, and insert the downloaded file as a component",
            "Pixmap": ui_icon_path("catalogue_part"),
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        try:
            if not commands.finish_open_dialog():
                return
            Gui.Control.showDialog(CataloguePanel(App.ActiveDocument))
            log("insert catalogue part started")
        except Exception as exc:
            warn("Insert Catalogue Part failed to start: %s" % exc)


COMMANDS = {"Fission180_InsertCataloguePart": CatalogueCommand}
