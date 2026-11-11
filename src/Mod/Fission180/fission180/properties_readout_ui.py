# SPDX-License-Identifier: LGPL-2.1-or-later
"""The selection read-out at the bottom right of the 3D view, as in Fusion: select a face and
it says its area (and the length of its outline), an edge its length (and radius), a corner
its position, a body its volume and area, two things the distance between them and, where
they are not parallel, the angle (book parity report: "Clicking the flat underside shows no
area in the bottom right (Fusion shows 'Area 812.278 mm^2' for a selected face)").

A small label over the corner of the 3D view, never in the way of a click (the mouse goes
through it), in the design's units. It shows while something is selected and no command
dialog is open (a dialog takes the clicks as its picks). Nothing in the design changes. The
texts are properties_core.readout(); this module installs itself when it is loaded.
"""

import FreeCAD as App
import FreeCADGui as Gui

from . import warn
from . import properties_core as core
from .compat import QtCore, QtWidgets

NAME = "Fission180SelectionReadout"
MANY = 200  # more things than this selected: only counted
_STATE = {"label": None, "observer": None, "timer": None, "rows": [], "filter": None}


def rows():
    """[(name, text)] the read-out shows now ([] when it is hidden): tests."""
    label = _STATE.get("label")
    try:
        if label is None or not label.isVisible():
            return []
    except RuntimeError:
        return []
    return list(_STATE["rows"])


def text():
    return "   ".join("%s %s" % row for row in rows())


def _unit(doc):
    try:
        from . import browser_core

        return browser_core.doc_length_unit(doc)
    except Exception:
        return "mm"


def _direction(shape):
    """The direction a flat face looks along or a straight edge runs along, or None."""
    try:
        kind = shape.ShapeType
        if kind == "Face" and shape.Surface.TypeId == "Part::GeomPlane":
            axis = shape.Surface.Axis
            return (axis.x, axis.y, axis.z), "face"
        if kind == "Edge" and shape.Curve.TypeId == "Part::GeomLine":
            d = shape.Curve.Direction
            return (d.x, d.y, d.z), "edge"
    except Exception:
        pass
    return None, None


def _item(obj, short):
    """(item for properties_core.readout, the shape in design coordinates) of one selected
    thing, or (None, None)."""
    from . import bodies, hole_common

    if not short:
        body = bodies.body_of(obj)
        target = body if body is not None else obj
        try:
            shape = bodies.global_shape(target, copy=False)
            if shape.isNull() or not shape.Solids:
                return None, None
            return {"kind": "body", "volume": shape.Volume, "area": shape.Area}, shape
        except Exception:
            return None, None
    shape = hole_common.global_shape(obj, short)
    if shape is None:
        return None, None
    try:
        if short.startswith("Face"):
            loop = shape.OuterWire.Length if shape.Wires else 0.0
            return {"kind": "face", "area": shape.Area, "loop": loop}, shape
        if short.startswith("Edge"):
            item = {"kind": "edge", "length": shape.Length}
            if shape.Curve.TypeId == "Part::GeomCircle":
                item["radius"] = float(shape.Curve.Radius)
            return item, shape
        if short.startswith("Vertex"):
            p = shape.Point
            return {"kind": "vertex", "point": (p.x, p.y, p.z)}, shape
    except Exception:
        return None, None
    return None, None


def measure(picks, doc):
    """[(name, text)] for a selection [(object, short element name), ...]."""
    if len(picks) > MANY:
        return [("Selected", "%d" % len(picks))]
    items, shapes = [], []
    for obj, short in picks:
        item, shape = _item(obj, short)
        if item is None:
            continue
        items.append(item)
        shapes.append(shape)
    distance = angle = None
    if len(items) == 2:
        try:
            distance = shapes[0].distToShape(shapes[1])[0]
        except Exception:
            distance = None
        (a, kind_a), (b, kind_b) = _direction(shapes[0]), _direction(shapes[1])
        if a is not None and b is not None:
            found = core.angle_between(a, b)
            if found is not None:
                if kind_a != kind_b:  # a face's direction is across it: an edge in it is at 0
                    found = abs(90.0 - found)
                elif found > 90.0:
                    found = 180.0 - found
                if found > 1e-6:
                    angle = found
    return core.readout(items, _unit(doc), distance, angle)


def _picks():
    """[(object, short name)] of the selection in the active design."""
    from . import hole_common

    doc = App.ActiveDocument
    if doc is None:
        return None, []
    found = []
    for sel in Gui.Selection.getSelectionEx(doc.Name):
        obj = sel.Object
        names = list(sel.SubElementNames)
        if not names:
            found.append((obj, ""))
            continue
        for name in names:
            found.append(hole_common.resolve(obj, name))
    return doc, found


def _dialog_open():
    try:
        from . import taskui

        # (a dialog that is being built counts: it registers itself before it is on screen,
        # and this is asked from a timer that can fire during its first preview)
        panel = taskui._OPEN.get("dialog")
        if panel is not None and not getattr(panel, "_closed", False):
            return True
        return bool(Gui.Control.activeDialog())
    except Exception:
        return False


def _label():
    label = _STATE.get("label")
    try:
        if label is not None:
            label.objectName()
            return label
    except RuntimeError:
        label = None
    window = Gui.getMainWindow()
    label = QtWidgets.QLabel(window)
    label.setObjectName(NAME)
    label.setAttribute(QtCore.Qt.WA_TransparentForMouseEvents, True)
    label.setStyleSheet(
        "QLabel#%s { background: rgba(30, 36, 44, 215); color: #e8edf3; border: 1px solid "
        "#55657a; border-radius: 3px; padding: 4px 8px; }" % NAME
    )
    label.hide()
    _STATE["label"] = label
    return label


def _place(label):
    """At the bottom right of the 3D view area, left of the axis cross in its corner."""
    try:
        window = label.parentWidget()
        area = window.centralWidget()
        if area is not None:
            corner = area.mapTo(window, QtCore.QPoint(area.width(), area.height()))
        else:
            corner = QtCore.QPoint(window.width(), window.height())
        label.adjustSize()
        label.move(max(0, corner.x() - label.width() - 84), max(0, corner.y() - label.height() - 8))
    except Exception:
        pass


def update():
    """Show what is selected now (or hide)."""
    try:
        label = _label()
        found = []
        if not _dialog_open():
            doc, picks = _picks()
            if doc is not None and picks:
                found = measure(picks, doc)
        _STATE["rows"] = found
        if not found:
            label.hide()
            return
        label.setText(
            "&nbsp;&nbsp;&nbsp;".join("<b>%s</b>&nbsp;%s" % (n, core.pretty(t)) for n, t in found)
        )
        _place(label)
        label.show()
        label.raise_()
    except Exception as exc:
        warn("selection read-out: %s" % exc)


class _Observer:
    """Every slot only schedules the look (nothing is measured inside FreeCAD's callbacks)."""

    def _later(self):
        timer = _STATE.get("timer")
        if timer is not None:
            timer.start()

    def addSelection(self, *args):
        self._later()

    def removeSelection(self, *args):
        self._later()

    def setSelection(self, *args):
        self._later()

    def clearSelection(self, *args):
        self._later()


class _Resized(QtCore.QObject):
    def eventFilter(self, obj, event):
        try:
            if event.type() == QtCore.QEvent.Resize:
                label = _STATE.get("label")
                if label is not None and label.isVisible():
                    _place(label)
        except Exception:
            pass
        return False


def install():
    if _STATE["observer"] is not None or not App.GuiUp:
        return
    timer = QtCore.QTimer(Gui.getMainWindow())
    timer.setSingleShot(True)
    timer.setInterval(60)
    timer.timeout.connect(update)
    _STATE["timer"] = timer
    _STATE["observer"] = _Observer()
    Gui.Selection.addObserver(_STATE["observer"])
    _STATE["filter"] = _Resized()
    Gui.getMainWindow().installEventFilter(_STATE["filter"])


try:
    install()
except Exception as _exc:  # pragma: no cover - only without a GUI
    warn("selection read-out not installed: %s" % _exc)
