# SPDX-License-Identifier: LGPL-2.1-or-later
"""Properties (Fusion: right-click a component or a body > Properties): what the selected
components and bodies weigh and measure.

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
        self.copy.setObjectName("Fission180PropertiesCopy")
        self.copy.clicked.connect(lambda *_: self._guarded(self.copy_text))
        row.addWidget(self.copy)
        row.addStretch(1)
        close = QtWidgets.QPushButton("Close")
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
        count = len(counted)
        self.name = title
        self.title.setText(
            "<b>%s</b> &nbsp; %d bod%s" % (title, count, "y" if count == 1 else "ies")
        )
        self.values = {}
        self.tree.clear()
        for section, entries in self.sections:
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

    def value(self, section, name):
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
