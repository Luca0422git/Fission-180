# SPDX-License-Identifier: LGPL-2.1-or-later
"""The base of the MANUFACTURE workspace's dialogs that pick on the model (New Setup and the
operations): several of Fusion's blue selection boxes in one dialog, each with its own picks
(a click on the model goes to the box that is blue; a click on a picked element drops it),
whole bodies or their faces / edges / corners, number fields in the design's units, tick
boxes and drop-downs with names the tests can find ("Fission180Cam_<key>"), and the message
line. The design's bodies are never changed and never shown differently while it is open.
"""

import FreeCADGui as Gui

from . import bodies, hole_common, pickpanel, taskui, warn
from .compat import QtWidgets

ERROR_STYLE = "color: #ff8a80;"
HINT_STYLE = "color: #b8c4d0;"
PREFIX = "Fission180Cam_"


class _Gate:
    """FreeCAD names the top object and a path ("Body.Pad.Face6"): the panel is asked about
    the element itself."""

    def __init__(self, panel):
        self.panel = panel

    def allow(self, doc, obj, sub):
        try:
            panel = self.panel
            if panel is None or panel._closed or obj is None:
                return True
            from .construct_ui import _resolve_gate

            leaf, short = _resolve_gate(obj, sub)
            return bool(panel.allow(leaf, short))
        except Exception:
            return False


def element_kind(short):
    name = (short or "").split(".")[-1]
    for prefix, kind in (("Face", "faces"), ("Edge", "edges"), ("Vertex", "vertices")):
        if name.startswith(prefix):
            return kind
    return None


def body_pick(obj, short):
    """(body, element name on the body's own shape) for what was clicked."""
    from . import simulation_panels

    return simulation_panels.body_pick(obj, short)


class CamPanel(pickpanel.PickPanel):
    cam_view = True  # (manufacture_ui.refresh_view leaves this dialog's own drawing alone)
    cam_dialog = True

    def __init__(self, doc, transaction):
        super().__init__(doc, transaction)
        self.boxes = {}  # index -> hole_common.SelectionField
        self.box_picks = {}  # index -> [(body, element name or "" for the whole body)]
        self.box_rules = {}  # index -> {"single", "whole", "kinds"}
        self.active_box = None
        self.inputs = {}  # key -> the field / widget
        self.setup_bodies = None  # names of the bodies picks may be on (None: any solid body)

    # -- widgets ---------------------------------------------------------------------------
    def selection_box(self, index, key, empty, single=False, whole=False, kinds=("faces", "edges")):
        box = hole_common.SelectionField(self, index, empty)
        box.button.setObjectName(PREFIX + key)
        box.clear.setObjectName(PREFIX + key + "_clear")
        self.boxes[index] = box
        self.box_picks.setdefault(index, [])
        self.box_rules[index] = {"single": single, "whole": whole, "kinds": tuple(kinds)}
        return box

    def number(self, key, value, tip="", unit="mm"):
        field = taskui.DistanceField(float(value), unit, on_change=lambda *_a: self.changed(key))
        field.widget.setObjectName(PREFIX + key)
        if tip:
            field.widget.setToolTip(tip)
        self.inputs[key] = field
        return field

    def plain_number(self, key, value, low, high, decimals=0, step=1.0, suffix="", tip=""):
        box = QtWidgets.QDoubleSpinBox() if decimals else QtWidgets.QSpinBox()
        box.setObjectName(PREFIX + key)
        box.setRange(low, high)
        if decimals:
            box.setDecimals(decimals)
        box.setSingleStep(step)
        if suffix:
            box.setSuffix(suffix)
        box.setValue(value)
        box.setKeyboardTracking(False)
        if tip:
            box.setToolTip(tip)
        box.valueChanged.connect(lambda *_a: self.changed(key))
        self.inputs[key] = box
        return box

    def tick(self, key, text, on, tip=""):
        box = QtWidgets.QCheckBox(text)
        box.setObjectName(PREFIX + key)
        box.setChecked(bool(on))
        if tip:
            box.setToolTip(tip)
        box.toggled.connect(lambda *_a: self.changed(key))
        self.inputs[key] = box
        return box

    def choice(self, key, rows, current, tip=""):
        box = pickpanel.combo(rows, current)
        box.setObjectName(PREFIX + key)
        # (the dialog floats over the view: long entries must not make it wider than it)
        box.setSizeAdjustPolicy(QtWidgets.QComboBox.AdjustToMinimumContentsLengthWithIcon)
        box.setMinimumContentsLength(14)
        if tip:
            box.setToolTip(tip)
        box.currentIndexChanged.connect(lambda *_a: self.changed(key))
        self.inputs[key] = box
        return box

    def text(self, key, value, tip=""):
        box = QtWidgets.QLineEdit(str(value))
        box.setObjectName(PREFIX + key)
        if tip:
            box.setToolTip(tip)
        box.textEdited.connect(lambda *_a: self.changed(key))
        self.inputs[key] = box
        return box

    def value(self, key):
        """What a field holds now: a number, True / False, a drop-down's key or a text."""
        field = self.inputs[key]
        if isinstance(field, taskui.DistanceField):
            return field.value()
        if isinstance(field, QtWidgets.QCheckBox):
            return field.isChecked()
        if isinstance(field, QtWidgets.QComboBox):
            return field.currentData()
        if isinstance(field, QtWidgets.QLineEdit):
            return field.text()
        return field.value()

    def put(self, key, value):
        field = self.inputs[key]
        if isinstance(field, taskui.DistanceField):
            field.set_value(value)
            return
        field.blockSignals(True)
        try:
            if isinstance(field, QtWidgets.QCheckBox):
                field.setChecked(bool(value))
            elif isinstance(field, QtWidgets.QComboBox):
                hole_common.set_combo(field, value)
            elif isinstance(field, QtWidgets.QLineEdit):
                field.setText(str(value))
            else:
                field.setValue(value)
        finally:
            field.blockSignals(False)

    def changed(self, key):
        """A field changed (override to show / hide rows first)."""
        try:
            self.fields_changed(key)
            self.schedule()
        except Exception as exc:
            warn("%s: %s" % (self.title, exc))

    def fields_changed(self, key):
        pass

    def say(self, text, error=False):
        try:
            self.message.setStyleSheet(ERROR_STYLE if error else HINT_STYLE)
            self.message.setText(text or "")
        except RuntimeError:
            pass

    def feature(self):
        return None

    # -- picking ---------------------------------------------------------------------------
    def start_picking(self):
        super().start_picking()
        try:
            if self.gate is not None:
                hole_common.remove_gate(self.gate)
            self.gate = _Gate(self)
            Gui.Selection.addSelectionGate(self.gate)
        except Exception as exc:
            warn("%s: selection filter unavailable: %s" % (self.title, exc))

    def activate(self, index):
        """Make a selection box the one that takes the clicks (None: none does)."""
        self.active_box = index if index in self.boxes else None
        for i, box in self.boxes.items():
            box.set_active(i == self.active_box)
        self._sync()

    def clear_field(self, index):
        try:
            self.box_picks[index] = []
            self.picks_updated(index)
            self._sync()
            self.schedule()
        except Exception as exc:
            warn("%s: %s" % (self.title, exc))

    def pick_allowed(self, index, obj, short, body):
        """May this element go into box `index`? (override for more than the kinds)"""
        return True

    def allow(self, obj, short):
        index = self.active_box
        if index is None or obj is None or not short:
            return False
        body = bodies.body_of(obj)
        if body is None or not bodies.has_solid(body):
            return False
        rules = self.box_rules[index]
        if rules["whole"]:
            return self.pick_allowed(index, obj, short, body)
        if self.setup_bodies is not None and body.Name not in self.setup_bodies:
            return False
        if element_kind(short) not in rules["kinds"]:
            return False
        return self.pick_allowed(index, obj, short, body)

    def _pick_of(self, index, obj, short):
        if self.box_rules[index]["whole"]:
            body = bodies.body_of(obj)
            return (body, "") if body is not None else None
        return body_pick(obj, short)

    def expand_pick(self, index, pick):
        """The picks a click stands for (override: an edge's whole loop)."""
        return [pick]

    def picks_changed(self, added, dropped):
        index = self.active_box
        if index is None:
            return False
        rules = self.box_rules[index]
        picks = self.box_picks[index]
        changed = False
        for obj, short, _point in dropped:
            if rules["whole"] and short:
                continue
            found = self._pick_of(index, obj, short)
            if found is not None and found in picks:
                for one in self.expand_pick(index, found):
                    if one in picks:
                        picks.remove(one)
                changed = True
        for obj, short, _point in added:
            if not self.allow(obj, short):
                continue
            found = self._pick_of(index, obj, short)
            if found is None:
                continue
            group = self.expand_pick(index, found)
            if rules["single"]:
                picks[:] = [found]
            elif all(one in picks for one in group):
                for one in group:
                    picks.remove(one)
            else:
                for one in group:
                    if one not in picks:
                        picks.append(one)
            changed = True
        if changed:
            self.picks_updated(index)
        return changed

    def picks_updated(self, index):
        """The picks of a box changed: its text (override, call this)."""
        self.box_text(index)

    def box_text(self, index):
        picks = self.box_picks.get(index) or []
        box = self.boxes[index]
        if not picks:
            box.set_text(None)
            return
        counts = {}
        for _body, sub in picks:
            kind = element_kind(sub) or "bodies"
            counts[kind] = counts.get(kind, 0) + 1
        words = {"faces": "face", "edges": "edge", "vertices": "corner", "bodies": "body"}
        plural = {"faces": "faces", "edges": "edges", "vertices": "corners", "bodies": "bodies"}
        box.set_text(
            ", ".join("%d %s" % (n, words[k] if n == 1 else plural[k]) for k, n in counts.items())
        )

    def shown(self):
        index = self.active_box
        if index is None:
            return []
        grouped, order = {}, []
        for body, sub in self.box_picks.get(index) or []:
            if not bodies.alive(body):
                continue
            if not sub:
                grouped[body.Name] = (body, [])
                order.append(body.Name)
                continue
            target = getattr(body, "Tip", None) or body
            if target.Name not in grouped:
                grouped[target.Name] = (target, [])
                order.append(target.Name)
            grouped[target.Name][1].append(sub)
        return [grouped[n] for n in order]

    def flush_picks(self):
        """A click handled a moment later is taken now (OK right after a click keeps it)."""
        try:
            events = getattr(self, "_events", None)
            if events is not None and events.isActive():
                events.stop()
                self._process_selection()
        except Exception as exc:
            warn("%s: %s" % (self.title, exc))

    def cleanup(self):
        try:
            from . import manufacture_view

            manufacture_view.drop("heights")
            manufacture_view.drop("marks")
        except Exception:
            pass
        super().cleanup()


def open_panel(panel):
    Gui.Control.showDialog(panel)
    return panel
