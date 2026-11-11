# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's Post Process and Setup Sheet (MANUFACTURE > ACTIONS).

Post Process: the post (FreeCAD's post processors under the names of their machine
dialects: Grbl, LinuxCNC, Mach3 / Mach4, Fanuc, Marlin...), the output folder, the program's
name or number and comment, the units (millimeters or inches) and "Open NC file in editor".
Post writes the G-code file, after generating the toolpaths that are missing or out of date,
and reads it back with Fission 180's own checker (units stated, spindle on before cutting,
no sideways rapid below the top of the stock, nothing below the lowest height, inside the
toolpaths' box): what it finds is shown in the dialog, in red when something is wrong. The
safety note is always there: a program must be checked before it runs on a machine.

Setup Sheet: an HTML page with the tools, the operations, their times and the stock, written
into the output folder and opened.
"""

import os

import FreeCAD as App
import FreeCADGui as Gui

from . import commands, log, warn
from . import manufacture_core as core
from .compat import QtCore, QtGui, QtWidgets
from .simulation_dialogs import FocusBack

OPEN = {"dialog": None}
LAST = {"posted": None, "sheet": None, "opened": []}  # what was written last (tests read it)
OPEN_FILES = True  # False: "open after" only records the file (tests)
PREFS = "User parameter:BaseApp/Preferences/Mod/Fission180/Manufacture"


def _cam():
    from . import manufacture

    return manufacture


def _ui():
    from . import manufacture_ui

    return manufacture_ui


def _alive(widget):
    try:
        widget.objectName()
        return True
    except Exception:
        return False


def _open_file(path):
    LAST["opened"].append(path)
    if not OPEN_FILES or os.environ.get("FISSION180_NO_INTERNET"):
        return
    try:
        QtGui.QDesktopServices.openUrl(QtCore.QUrl.fromLocalFile(path))
    except Exception as exc:
        warn("could not open %s: %s" % (path, exc))


class PostDialog(FocusBack, QtWidgets.QDialog):
    def __init__(self, doc, setup, ops=None, sheet=False):
        super().__init__(Gui.getMainWindow())
        self.setObjectName("Fission180CamPost")
        self.setWindowTitle("Setup Sheet" if sheet else "Post Process")
        self.setWindowModality(QtCore.Qt.ApplicationModal)
        self.doc = doc
        self.setup = setup
        self.ops = ops
        self.sheet = sheet
        cam = _cam()
        prefs = App.ParamGet(PREFS)
        opts = cam.setup_options(setup)["post"]
        layout = QtWidgets.QVBoxLayout(self)
        chosen = cam.postable(setup, ops)
        what = QtWidgets.QLabel(
            "%s: %s" % (setup.Label, ", ".join(o.Label for o in chosen) or "no operations")
        )
        what.setObjectName("Fission180CamPost_what")
        what.setWordWrap(True)
        layout.addWidget(what)
        form = QtWidgets.QFormLayout()
        layout.addLayout(form)
        self.post = QtWidgets.QComboBox()
        self.post.setObjectName("Fission180CamPost_post")
        for key, (title, _ext, text) in core.POSTS.items():
            self.post.addItem(title, key)
            self.post.setItemData(self.post.count() - 1, text, QtCore.Qt.ToolTipRole)
        index = self.post.findData(prefs.GetString("Post", core.DEFAULT_POST))
        self.post.setCurrentIndex(index if index >= 0 else 0)
        self.post.currentIndexChanged.connect(self._name_shown)
        self.folder = QtWidgets.QLineEdit(
            prefs.GetString("Folder", "") or _ui().default_folder(doc)
        )
        self.folder.setObjectName("Fission180CamPost_folder")
        browse = QtWidgets.QPushButton("...")
        browse.setObjectName("Fission180CamPost_browse")
        browse.setToolTip("Choose the folder")
        browse.setFixedWidth(34)
        browse.clicked.connect(self._browse)
        line = QtWidgets.QWidget()
        row = QtWidgets.QHBoxLayout(line)
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(self.folder, 1)
        row.addWidget(browse)
        self.program = QtWidgets.QLineEdit(opts["program"])
        self.program.setObjectName("Fission180CamPost_program")
        self.program.textChanged.connect(self._name_shown)
        self.comment = QtWidgets.QLineEdit(opts["comment"])
        self.comment.setObjectName("Fission180CamPost_comment")
        self.units = QtWidgets.QComboBox()
        self.units.setObjectName("Fission180CamPost_units")
        for key, title in core.POST_UNITS:
            self.units.addItem(title, key)
        index = self.units.findData(prefs.GetString("Units", "mm"))
        self.units.setCurrentIndex(index if index >= 0 else 0)
        self.open_after = QtWidgets.QCheckBox(
            "Open the file when done" if sheet else "Open NC file in editor"
        )
        self.open_after.setObjectName("Fission180CamPost_open")
        self.open_after.setChecked(prefs.GetBool("OpenAfter", True))
        if not sheet:
            form.addRow("Post", self.post)
        form.addRow("Output Folder", line)
        if not sheet:
            form.addRow("Program Name/Number", self.program)
            form.addRow("Program Comment", self.comment)
            form.addRow("Unit", self.units)
        self.file_label = QtWidgets.QLabel("")
        self.file_label.setObjectName("Fission180CamPost_file")
        form.addRow("File", self.file_label)
        form.addRow(self.open_after)
        self.result = QtWidgets.QLabel("")
        self.result.setObjectName("Fission180CamPost_result")
        self.result.setWordWrap(True)
        self.result.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse)
        layout.addWidget(self.result)
        note = QtWidgets.QLabel(core.SAFETY_NOTE)
        note.setObjectName("Fission180CamPost_safety")
        note.setWordWrap(True)
        note.setStyleSheet("color: #f2c440;")
        layout.addWidget(note)
        buttons = QtWidgets.QHBoxLayout()
        layout.addLayout(buttons)
        buttons.addStretch(1)
        self.go = QtWidgets.QPushButton("Create" if sheet else "Post")
        self.go.setObjectName("Fission180CamPost_go")
        self.go.setDefault(True)
        self.go.clicked.connect(self.run)
        buttons.addWidget(self.go)
        close = QtWidgets.QPushButton("Close")
        close.setObjectName("Fission180CamPost_close")
        close.clicked.connect(self.reject)
        buttons.addWidget(close)
        self.setMinimumWidth(520)
        self._name_shown()

    def _browse(self):
        folder = QtWidgets.QFileDialog.getExistingDirectory(
            self, "Output Folder", self.folder.text()
        )
        if folder:
            self.folder.setText(folder)

    def file_name(self):
        if self.sheet:
            safe = "".join(
                c if c.isalnum() or c in " _-." else "_" for c in self.setup.Label
            ).strip()
            return "%s setup sheet.html" % (safe or "Setup")
        return core.post_file_name(self.program.text(), self.post.currentData())

    def _name_shown(self, *_a):
        self.file_label.setText(self.file_name())

    def _say(self, text, error=False):
        self.result.setStyleSheet("color: #ff8a80;" if error else "color: #7bd88f;")
        self.result.setText(text)

    def run(self):
        """Post (or make the sheet); the dialog stays open and says what happened."""
        cam = _cam()
        folder = self.folder.text().strip()
        if not folder or not os.path.isdir(folder):
            self._say(
                "The output folder does not exist: choose one with the ... button.", error=True
            )
            return None
        path = os.path.join(folder, self.file_name())
        prefs = App.ParamGet(PREFS)
        prefs.SetString("Folder", folder)
        prefs.SetBool("OpenAfter", self.open_after.isChecked())
        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)
        try:
            ui = _ui()
            todo = [
                o for o in cam.postable(self.setup, self.ops) if cam.state(o, self.setup) != "valid"
            ]
            if todo:
                self._say(
                    "Generating %d toolpath%s first..." % (len(todo), "" if len(todo) == 1 else "s")
                )
                ui.generate(todo)
                if not ui.wait_generated():
                    self._say(
                        "The toolpaths are still being generated: try again in a moment.",
                        error=True,
                    )
                    return None
            if self.sheet:
                cam.setup_sheet(self.setup, path)
                LAST["sheet"] = path
                self._say("Wrote %s." % path)
                if self.open_after.isChecked():
                    _open_file(path)
                return path
            prefs.SetString("Post", self.post.currentData())
            prefs.SetString("Units", self.units.currentData())
            self._keep_program()
            posted = cam.post_process(
                self.setup,
                self.post.currentData(),
                self.units.currentData(),
                ops=self.ops,
                program=self.program.text().strip() or None,
                comment=self.comment.text(),
                path=path,
                background=True,
            )
        except core.CamError as exc:
            self._say(str(exc), error=True)
            return None
        except Exception as exc:
            warn("post process: %s" % exc)
            self._say("It could not be written: %s" % exc, error=True)
            return None
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
        LAST["posted"] = posted
        check = posted["check"]
        text = "Wrote %s (%d lines, %s)." % (
            posted["file"],
            check["lines"],
            core.post_title(posted["post"]),
        )
        if check["problems"]:
            self._say(text + " Checked: " + " ".join(check["problems"]), error=True)
        else:
            notes = (" " + " ".join(check["notes"])) if check["notes"] else ""
            self._say(text + " Checked: nothing found." + notes)
        if self.open_after.isChecked():
            _open_file(posted["file"])
        return posted

    def _keep_program(self):
        """The program's name and comment typed here are the setup's from now on."""
        cam = _cam()
        opts = cam.setup_options(self.setup)["post"]
        new = dict(
            opts,
            program=self.program.text().strip() or opts["program"],
            comment=self.comment.text(),
        )
        if new == opts:
            return
        doc = self.doc
        doc.openTransaction("Program %s" % new["program"])
        try:
            cam.update_setup(self.setup, {"post": new})
        finally:
            doc.commitTransaction()


def open_post(doc, setup=None, ops=None, sheet=False):
    if not commands.finish_open_dialog():
        return None
    cam = _cam()
    setup = setup or _ui().active_setup(doc)
    if setup is None:
        commands.tell("There is no setup yet: SETUP > New Setup, then add operations.")
        return None
    if not cam.postable(setup, ops):
        commands.tell(
            "%s has no operation to %s: add one from 2D, 3D or DRILLING first (or unsuppress them)."
            % (setup.Label, "list" if sheet else "post")
        )
        return None
    close()
    dialog = PostDialog(doc, setup, ops, sheet)
    OPEN["dialog"] = dialog
    dialog.show()
    log("%s: %s" % ("setup sheet" if sheet else "post process", setup.Label))
    return dialog


def setup_sheet(doc, setup=None):
    cam = _cam()
    if setup is not None and cam.is_op(setup):
        setup = cam.setup_of(setup)
    return open_post(doc, setup, None, sheet=True)


def dialog():
    found = OPEN["dialog"]
    return found if found is not None and _alive(found) and found.isVisible() else None


def close():
    found = OPEN["dialog"]
    OPEN["dialog"] = None
    if found is not None and _alive(found) and found.isVisible():
        try:
            found.reject()
        except Exception:
            pass


COMMANDS = {}
