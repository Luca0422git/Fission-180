# SPDX-License-Identifier: LGPL-2.1-or-later
"""Properties (Fusion: right-click a component or a body > Properties): what the selected
components and bodies weigh and measure.

  General         Part Number, Part Name, Description of the one component selected: typed
                  here, stored on the component (an occurrence: on its original), one undo
                  step each. The drawing's parts list shows the Part Number and the
                  Description (drawing._part_name, Label2).
  Physical        Area, Density, Mass, Volume, Physical Material, Appearance
  Bounding Box    Length (along X), Width (Y), Height (Z)
  Center of Mass  X, Y, Z in the design
  Moment of Inertia at Center of Mass / at Origin   Ixx, Ixy, Ixz, Iyy, Iyz, Izz

A component counts every body in it (and in the components inside it), each with its own
physical material; nothing selected means the whole design, as Properties of Fusion's top
component. Lengths are in the design's units. Copy to Clipboard copies the list as text.
The dialog floats (work goes on behind it) and follows the selection: click another body
or component while it is open. The numbers are properties_core.py.
"""

import FreeCAD as App
import FreeCADGui as Gui

from . import bodies, commands, components, log, ui_icon_path, warn
from . import properties_core as core
from .compat import QtCore, QtWidgets

_STATE = {"dialog": None}
NUMBER_PROP = "Fission180PartNumber"  # on a component: its Part Number ("" = its name)
FIELDS = (("number", "Part Number"), ("name", "Part Name"), ("description", "Description"))


def subject_of_selection(doc):
    """The one component Properties is about: the selected component (its original when an
    occurrence is selected), or None when nothing, a body or several things are selected."""
    try:
        selected = [sel.Object for sel in Gui.Selection.getSelectionEx(doc.Name)]
    except Exception:
        return None
    if len(selected) != 1 or not components.is_component(selected[0]):
        return None
    part = selected[0]
    try:
        from . import instances

        if instances.is_instance(part):
            part = instances.source_of(part) or part
    except Exception:
        pass
    return part


def part_number(part):
    """A component's Part Number: the one given in Properties, else its name (Fusion starts
    a component's part number as its name)."""
    return (getattr(part, NUMBER_PROP, "") or "").strip() or part.Label


def general_of(part):
    """{"number", "name", "description"} of a component."""
    return {
        "number": part_number(part),
        "name": part.Label,
        "description": getattr(part, "Label2", "") or "",
    }


def set_general(part, key, text):
    """Change a component's Part Number, Part Name or Description (one undo step). Returns
    what it is now. Raises ValueError with what to do when the text cannot be taken."""
    text = (text or "").strip()
    doc = part.Document
    now = general_of(part)
    if key not in now:
        raise ValueError("Unknown property %r." % (key,))
    if text == now[key]:
        return now[key]
    if key == "name":
        if not text:
            raise ValueError("A component needs a name: the old one is kept.")
        components.rename(doc, part, text)
        return general_of(part)[key]
    doc.openTransaction("Properties")
    try:
        if key == "number":
            if NUMBER_PROP not in part.PropertiesList:
                part.addProperty("App::PropertyString", NUMBER_PROP, "Fission180", "Part number", 4)
            # the name itself (or nothing) means "as the name": it follows a rename again
            setattr(part, NUMBER_PROP, "" if text in ("", part.Label) else text)
        else:
            part.Label2 = text
        doc.commitTransaction()
    except Exception:
        doc.abortTransaction()
        raise
    return general_of(part)[key]


def _unit(doc):
    try:
        from . import browser_core

        return browser_core.doc_length_unit(doc)
    except Exception:
        return "mm"


def targets_of_selection(doc):
    """(title, bodies) of what Properties is asked about: the selected components (with all
    their bodies) and bodies; the whole design when nothing of the kind is selected."""
    found, names = [], []
    try:
        selection = Gui.Selection.getSelectionEx(doc.Name) if doc is not None else []
    except Exception:
        selection = []
    for sel in selection:
        obj = sel.Object
        if components.is_component(obj):
            inside = components.bodies_in(doc, obj, recursive=True)
            names.append(obj.Label)
        else:
            body = bodies.body_of(obj)
            inside = [body] if body is not None else []
            if body is not None:
                from . import material

                names.append(material.body_name(body))
        for body in inside:
            if body not in found:
                found.append(body)
    if not names:
        return doc.Label, list(bodies.list_bodies(doc))
    title = names[0] if len(names) == 1 else "%s and %d more" % (names[0], len(names) - 1)
    return title, found


def measure(body):
    """[solid dict] (properties_core.combine) of a body's solids, in design coordinates."""
    from . import material

    try:
        if not bodies.has_solid(body):
            return []
        shape = bodies.global_shape(body, copy=False)
        kg = material.mass(body)
        total = sum(s.Volume for s in shape.Solids) or 0.0
    except Exception:
        return []
    out = []
    for solid in shape.Solids:
        try:
            volume = solid.Volume
            if volume <= 0:
                continue
            centre = solid.CenterOfMass
            matrix = solid.MatrixOfInertia
            box = solid.BoundBox
            out.append(
                {
                    "volume": volume,
                    "area": solid.Area,
                    "mass": (kg * volume / total) if kg is not None and total > 0 else None,
                    "center": (centre.x, centre.y, centre.z),
                    "inertia": [
                        [matrix.A11, matrix.A12, matrix.A13],
                        [matrix.A21, matrix.A22, matrix.A23],
                        [matrix.A31, matrix.A32, matrix.A33],
                    ],
                    "box": (box.XMin, box.YMin, box.ZMin, box.XMax, box.YMax, box.ZMax),
                }
            )
        except Exception:
            continue
    return out


def _one(values):
    values = [v for v in values if v]
    if not values:
        return ""
    return values[0] if len(set(values)) == 1 else "Various"


def gather(doc, found):
    """(result, material name, appearance name, bodies counted) for a list of bodies. Bodies
    a Combine used up, and bodies without a solid, do not count."""
    from . import appearance, material

    used = set()
    try:
        used = set(bodies.consumed(doc))
    except Exception:
        pass
    solids, materials, looks, counted = [], [], [], []
    for body in found:
        if body.Name in used:
            continue
        measured = measure(body)
        if not measured:
            continue
        counted.append(body)
        solids += measured
        try:
            materials.append(material.effective(body)[0])
        except Exception:
            pass
        try:
            looks.append(appearance.shown_look(body)["label"])
        except Exception:
            pass
    return core.combine(solids), _one(materials), _one(looks), counted


class PropertiesDialog(QtWidgets.QDialog):
    def __init__(self, doc):
        super().__init__(Gui.getMainWindow())
        self.setObjectName("Fission180Properties")
        self.setWindowTitle("Properties")
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Tool)
        self.doc = doc
        self.values = {}  # (section, name) -> the text shown (tests)
        self.counted = []
        self.result = None
        layout = QtWidgets.QVBoxLayout(self)
        self.title = QtWidgets.QLabel("")
        self.title.setObjectName("Fission180PropertiesTitle")
        layout.addWidget(self.title)
        self.subject = None  # the one component the General fields are about
        self.general = QtWidgets.QGroupBox("General")
        self.general.setObjectName("Fission180PropertiesGeneral")
        form = QtWidgets.QFormLayout(self.general)
        self.fields = {}
        for key, label in FIELDS:
            edit = QtWidgets.QLineEdit()
            edit.setObjectName("Fission180Properties_%s" % key)
            edit.editingFinished.connect(lambda k=key: self._guarded(lambda: self._field_edited(k)))
            form.addRow(label, edit)
            self.fields[key] = edit
        layout.addWidget(self.general)
        self.tree = QtWidgets.QTreeWidget()
        self.tree.setObjectName("Fission180PropertiesTree")
        self.tree.setColumnCount(2)
        self.tree.setHeaderHidden(True)
        self.tree.setRootIsDecorated(True)
        self.tree.setMinimumSize(420, 420)
        layout.addWidget(self.tree, 1)
        self.message = QtWidgets.QLabel("")
        self.message.setObjectName("Fission180PropertiesMessage")
        self.message.setWordWrap(True)
        self.message.setStyleSheet("color: #b8c7d9;")
        layout.addWidget(self.message)
        row = QtWidgets.QHBoxLayout()
        self.copy = QtWidgets.QPushButton("Copy to Clipboard")
        # (Enter in a General field commits that field: it must not press a button too)
        self.copy.setAutoDefault(False)
        self.copy.setObjectName("Fission180PropertiesCopy")
        self.copy.clicked.connect(lambda *_: self._guarded(self.copy_text))
        row.addWidget(self.copy)
        row.addStretch(1)
        close = QtWidgets.QPushButton("Close")
        close.setAutoDefault(False)
        close.setObjectName("Fission180PropertiesClose")
        close.clicked.connect(self.close)
        self.close_button = close
        row.addWidget(close)
        layout.addLayout(row)
        self.sections = []
        self._timer = QtCore.QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(120)
        self._timer.timeout.connect(lambda: self._guarded(self.fill))
        panel = self

        class Observer:
            def addSelection(self, *args):
                panel._timer.start()

            def removeSelection(self, *args):
                panel._timer.start()

            def setSelection(self, *args):
                panel._timer.start()

            def clearSelection(self, *args):
                panel._timer.start()

        self._observer = Observer()
        self._watching = False
        self.fill()

    def showEvent(self, event):
        # (the selection is followed only while the list is on screen: a dialog closed by
        # Esc or by another window's reject() is hidden, not destroyed)
        if not self._watching:
            Gui.Selection.addObserver(self._observer)
            self._watching = True
        super().showEvent(event)

    def hideEvent(self, event):
        self._unwatch()
        super().hideEvent(event)

    def _unwatch(self):
        if self._watching:
            self._watching = False
            try:
                Gui.Selection.removeObserver(self._observer)
            except Exception:
                pass
            self._timer.stop()

    def _guarded(self, fn):
        try:
            fn()
        except Exception as exc:
            warn("Properties: %s" % exc)

    def fill(self):
        doc = self.doc
        try:
            gone = doc is None or doc.Name not in App.listDocuments()
        except Exception:
            gone = True  # (the design was closed under the dialog)
        if gone:
            self.close()
            return
        title, found = targets_of_selection(doc)
        result, material_name, look_name, counted = gather(doc, found)
        self.result, self.counted = result, counted
        unit = _unit(doc)
        self.sections = core.rows(result, unit, material_name, look_name)
        self._fill_general(doc, title)
        count = len(counted)
        self.name = title
        self.title.setText(
            "<b>%s</b> &nbsp; %d bod%s" % (title, count, "y" if count == 1 else "ies")
        )
        self.values = {}
        self.tree.clear()
        for section, entries in self.sections:
            if section == "General":
                continue  # (shown in the fields above the list; part of the copied text)
            top = QtWidgets.QTreeWidgetItem(self.tree, [core.pretty(section), ""])
            font = top.font(0)
            font.setBold(True)
            top.setFont(0, font)
            for name, text in entries:
                QtWidgets.QTreeWidgetItem(top, [name, core.pretty(text)])
                self.values[(section.split(" (")[0], name)] = text
        self.tree.expandAll()
        self.tree.resizeColumnToContents(0)
        if not counted:
            self.message.setText(
                "Nothing here has a solid yet. Select a body or a component with a solid body "
                "(in the browser or the 3D view): the list follows the selection."
            )
        elif result["mass"] is None:
            self.message.setText("A body's material has no density: no mass can be given.")
        else:
            names = ", ".join(_name(b) for b in counted[:6])
            if len(counted) > 6:
                names += " and %d more" % (len(counted) - 6)
            self.message.setText("Counted: %s." % names)

    def _fill_general(self, doc, title):
        """The General fields: the one selected component's, to edit; else what is shown
        (the design's or the selection's name), greyed, with why."""
        part = self.subject = subject_of_selection(doc)
        if part is not None:
            shown = general_of(part)
            tip = "Type and press Enter: stored on the component %s" % part.Label
        else:
            shown = {"number": title, "name": title, "description": ""}
            tip = "Select one component (in the browser) to give it a part number or a description"
        self.general_values = dict(shown)
        for key, _label in FIELDS:
            edit = self.fields[key]
            edit.blockSignals(True)
            try:
                if not edit.hasFocus() or part is None:
                    edit.setText(shown[key])
                edit.setEnabled(part is not None)
                edit.setToolTip(tip)
            finally:
                edit.blockSignals(False)
        if part is not None:
            self.sections = [("General", [(label, shown[key]) for key, label in FIELDS])] + list(
                self.sections
            )

    def _field_edited(self, key):
        part = self.subject
        edit = self.fields[key]
        try:
            alive = part is not None and part.Document is not None
        except Exception:
            alive = False
        if not alive:
            return
        text = edit.text()
        if text.strip() == general_of(part)[key]:
            return
        label = dict(FIELDS)[key]
        try:
            now = set_general(part, key, text)
        except ValueError as exc:
            edit.setText(general_of(part)[key])
            self.message.setText("⚠ %s" % exc)
            return
        edit.setText(now)
        log("Properties: %s of %s is %s" % (label, part.Label, now or "(empty)"))
        self.fill()
        self.message.setText("%s: %s." % (label, now or "(empty)"))

    def value(self, section, name):
        if section == "General":
            key = {label: k for k, label in FIELDS}.get(name)
            return self.general_values.get(key) if key else None
        return self.values.get((section, name))

    def copy_text(self):
        text = core.as_text("Properties of %s" % self.name, self.sections)
        QtWidgets.QApplication.clipboard().setText(text)
        self.message.setText("Copied to the clipboard.")
        return text

    def closeEvent(self, event):
        self._unwatch()
        if _STATE.get("dialog") is self:
            _STATE["dialog"] = None
        try:
            from . import preferences_ui

            QtCore.QTimer.singleShot(0, preferences_ui.refocus_main)
        except Exception:
            pass
        super().closeEvent(event)

    def keyPressEvent(self, event):
        if event.key() == QtCore.Qt.Key_Escape:
            self.close()
            return
        super().keyPressEvent(event)


def _name(body):
    from . import material

    return material.body_name(body)


def dialog():
    """The open Properties dialog, or None (tests)."""
    found = _STATE.get("dialog")
    try:
        return found if found is not None and found.isVisible() else None
    except RuntimeError:
        return None


def show():
    doc = App.ActiveDocument
    if doc is None:
        commands.tell("Open or start a design first: Properties measures its bodies.")
        return None
    old = dialog()
    if old is not None:
        if old.doc is doc:
            old.fill()
            old.raise_()
            return old
        old.close()
    made = PropertiesDialog(doc)
    _STATE["dialog"] = made
    made.show()
    made.raise_()
    log("Properties of %s: %d bodies" % (made.name, len(made.counted)))
    return made


class PropertiesCommand:
    def GetResources(self):
        return {
            "MenuText": "Properties",
            "ToolTip": "Mass, volume, area, density, centre of mass and size of the selected "
            "bodies and components (the whole design when nothing is selected)",
            "Pixmap": ui_icon_path("material"),
        }

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        try:
            show()
        except Exception as exc:
            warn("Properties: %s" % exc)
            commands.tell("Properties could not open: %s" % exc)


COMMANDS = {"Fission180_Properties": PropertiesCommand}
