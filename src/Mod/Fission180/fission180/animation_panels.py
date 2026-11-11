# SPDX-License-Identifier: LGPL-2.1-or-later
"""The dialogs of the ANIMATION workspace (docs/fission180/parity/animation.md): New Storyboard,
Transform Components, Auto Explode (One Level / All Levels), Manual Explode, Create Callout,
Edit Start/End of an action and Publish Video.

Each is a Fission 180 task dialog (taskui.Panel): one undo step, OK / Enter keeps it, Cancel /
Esc puts everything back. While one is open the 3D view shows its preview: the storyboard at
the playhead with the dialog's change in it (drawn on the components' views only, the design
is never touched). A dialog that picks components takes them like a Fusion command: a click
on a component in the view (or on its browser row) adds it, a click on a picked one drops
it; what was selected before the command started is taken at once.
"""

import copy
import os

import FreeCAD as App
import FreeCADGui as Gui

from . import animation, animation_ui as ui, animation_view, commands, log, taskui, warn
from . import animation_core as core
from .compat import QtCore, QtWidgets

V = App.Vector
PREFIX = "Fission180Anim_"
HINT_STYLE = "color: #b8c4d0;"
SEQUENCES = [("One-Step Explosion", False), ("Sequential Explosion", True)]
AXIS_COLOURS = {"X": (0.94, 0.33, 0.31), "Y": (0.30, 0.78, 0.36), "Z": (0.30, 0.62, 0.95)}


class _Observer:
    """FreeCAD's selection, handed to the dialog a moment later (never work inside it)."""

    def __init__(self, panel):
        self.panel = panel

    def addSelection(self, doc, obj, sub, pnt):
        self.panel._selection_event(("add", doc, obj, sub, tuple(pnt)))

    def removeSelection(self, doc, obj, sub):
        self.panel._selection_event(("remove", doc, obj, sub, None))

    def setSelection(self, doc):
        self.panel._selection_event(("set", doc, None, None, None))

    def clearSelection(self, doc):
        self.panel._selection_event(("clear", doc, None, None, None))


class AnimPanel(taskui.Panel):
    """What the workspace's dialogs share: the storyboard and playhead they work on, the
    preview, the keys, picking components."""

    animation_dialog = True
    animation_preview = True
    picks_components = False
    last = None

    def __init__(self, doc, transaction):
        super().__init__(doc, transaction)
        type(self).last = self
        self.name = ui.current(doc)
        self.at = ui.playhead(doc)
        self.picks = []  # the components picked, in order
        self.observer = None
        self._events = []
        self._syncing = False
        self._soon = QtCore.QTimer()
        self._soon.setSingleShot(True)
        self._soon.setInterval(0)
        self._soon.timeout.connect(self._preview_now)
        self._guards = []
        self.escape = None
        try:
            from . import preview

            self.escape = preview.EscapeCancels(self)
            self._guards = [self.escape, preview.UndoCancels(self), preview.EnterFinishes(self)]
        except Exception as exc:
            warn("%s: keys unavailable: %s" % (self.title, exc))

    # -- widgets ------------------------------------------------------------------------------
    def hint(self, text):
        label = QtWidgets.QLabel(text)
        label.setWordWrap(True)
        label.setStyleSheet(HINT_STYLE)
        self.layout.addRow(label)
        return label

    def where_text(self):
        if core.in_scratch(self.at):
            return (
                "The playhead is in the scratch zone: this sets how %s starts, nothing is "
                "recorded as an action." % self.name
            )
        return "Recorded on %s as an action that ends at the playhead (%s)." % (
            self.name,
            core.time_text(self.at),
        )

    def named(self, widget, key):
        widget.setObjectName(PREFIX + key)
        return widget

    def slider(self, key, value):
        box = QtWidgets.QWidget()
        row = QtWidgets.QHBoxLayout(box)
        row.setContentsMargins(0, 0, 0, 0)
        slider = self.named(QtWidgets.QSlider(QtCore.Qt.Horizontal), key)
        slider.setRange(0, 100)
        slider.setPageStep(10)
        slider.setValue(int(value))
        shown = self.named(QtWidgets.QLabel(""), key + "_value")
        shown.setMinimumWidth(44)
        row.addWidget(slider, 1)
        row.addWidget(shown)
        return box, slider, shown

    # -- the storyboard and the preview -------------------------------------------------------
    def board(self):
        return ui.board(self.doc)

    def changed(self):
        """Something of the dialog changed: draw the preview shortly."""
        if not self._closed:
            self._soon.start()

    def _preview_now(self):
        try:
            if not self._closed:
                self.preview()
        except Exception as exc:
            warn("%s preview: %s" % (self.title, exc))

    def preview_board(self):
        """The storyboard with the dialog's change in it (override), or None for as it is."""
        return None

    def preview(self):
        temp = None
        try:
            temp = self.preview_board()
            self.message.setText("")
        except core.AnimationError as exc:
            self.message.setText(str(exc))
        animation_view.show(self.doc, temp or self.board(), self.at)

    # -- picking components -------------------------------------------------------------------
    def start_picking(self):
        """Take what is selected now, then follow the clicks."""
        self.picks = list(ui.selected_components(self.doc))
        self.observer = _Observer(self)
        Gui.Selection.addObserver(self.observer)
        self._show_picks()
        self.picks_changed()

    def _selection_event(self, event):
        if self._syncing or self._closed:
            return
        self._events.append(event)
        QtCore.QTimer.singleShot(30, self._process_selection)

    def handles_busy(self):
        """True while a handle of the dialog is in use: that click is not a pick."""
        from . import handles3d

        return handles3d.dragging() or handles3d.just_used()

    def _process_selection(self):
        if self._closed:
            return
        events, self._events = self._events, []
        if not events:
            return
        try:
            busy = self.handles_busy()
            for kind, doc_name, obj_name, sub, point in events:
                if kind != "add" or doc_name != self.doc.Name or busy:
                    continue
                obj = self.doc.getObject(obj_name)
                comp = animation.component_for(obj)
                where = V(*point) if point is not None else None
                if sub and where is not None and self.point_clicked(comp, where):
                    continue
                if comp is None:
                    self.message.setText(
                        "%s is not in a component: an animation moves components (in Design: "
                        "right-click the body > Create Components from Bodies)."
                        % (obj.Label if obj is not None else "That")
                    )
                    continue
                self.component_clicked(comp)
            self._show_picks()
        except Exception as exc:
            warn("%s: %s" % (self.title, exc))

    def point_clicked(self, comp, point):
        """A click on the model at `point` (design coordinates) on `comp` (None: on something
        that is not in a component). True when the dialog used it itself (Set Pivot, a
        callout's place)."""
        return False

    def component_clicked(self, comp):
        if comp in self.picks:
            self.picks.remove(comp)
        else:
            self.picks.append(comp)
        self.message.setText("")
        self.picks_changed()

    def picks_changed(self):
        self.changed()

    def _show_picks(self):
        """FreeCAD's selection shows the picked components (whole, highlighted)."""
        self._syncing = True
        try:
            Gui.Selection.clearSelection()
            for comp in self.picks:
                Gui.Selection.addSelection(self.doc.Name, comp.Name)
        except Exception as exc:
            warn("%s: %s" % (self.title, exc))
        finally:
            QtCore.QTimer.singleShot(0, self._synced)

    def _synced(self):
        self._syncing = False

    def picks_text(self):
        if not self.picks:
            return "Select components"
        if len(self.picks) == 1:
            return self.picks[0].Label
        return "%d components" % len(self.picks)

    # -- OK / Cancel --------------------------------------------------------------------------
    def commit(self):
        """Write the dialog's change to the storyboard (override). AnimationError refuses."""

    def accept(self):
        try:
            self.commit()
        except core.AnimationError as exc:
            self.message.setText("⚠ %s" % exc)
            return False
        except Exception as exc:
            self.message.setText("⚠ %s" % exc)
            warn("%s: %s" % (self.title, exc))
            return False
        done = super().accept()
        ui.STATE["current"][self.doc.Name] = self.name
        ui.refresh()
        return done

    def reject(self):
        done = super().reject()
        ui.refresh()
        return done

    def cleanup(self):
        self._closed = True
        try:
            self._soon.stop()
        except Exception:
            pass
        for guard in self._guards:
            try:
                guard.remove()
            except Exception:
                pass
        self._guards = []
        if self.observer is not None:
            try:
                Gui.Selection.removeObserver(self.observer)
            except Exception:
                pass
            self.observer = None
        super().cleanup()


def _open(panel_class, doc, *args, **kwargs):
    """Open a dialog the way every Fission 180 command does: the open one is finished first."""
    from . import bodies_panel

    if not commands.finish_open_dialog():
        return None
    ui.pause()
    try:
        return bodies_panel._open(panel_class, doc, *args, **kwargs)
    except core.AnimationError as exc:
        commands.tell(str(exc))
    except Exception as exc:
        warn("%s could not open: %s" % (getattr(panel_class, "title", "dialog"), exc))
    ui.refresh_view()
    return None


def current_panel(kind=None):
    """The workspace's dialog open now (of a class, when given), or None (tests)."""
    panel = taskui.current()
    if panel is None or getattr(panel, "_closed", True):
        return None
    if not getattr(panel, "animation_dialog", False):
        return None
    return panel if kind is None or isinstance(panel, kind) else None


# -- New Storyboard ------------------------------------------------------------------------------
class NewStoryboardPanel(AnimPanel):
    title = "New Storyboard"
    icon = "anim_storyboard"
    animation_preview = False

    def __init__(self, doc):
        super().__init__(doc, "New Storyboard")
        names = animation.storyboards(doc)
        self.field = self.named(QtWidgets.QLineEdit(core.unique_name(names or [])), "name")
        if not names:
            self.field.setText(animation.FIRST)
        self.layout.addRow("Name", self.field)
        self.kind = self.named(QtWidgets.QComboBox(), "type")
        self.kind.addItem("Clean", True)
        self.kind.addItem("Start from end of previous", False)
        self.kind.setToolTip(
            "Clean: the components where the design has them. Start from end of previous: "
            "where the storyboard shown now leaves them."
        )
        self.layout.addRow("Storyboard Type", self.kind)
        if not names:
            self.kind.model().item(1).setEnabled(False)
        self.hint(
            "A storyboard is one animation. A design can have several: each has its own tab "
            "under the timeline."
        )
        self.finish_layout()

    def commit(self):
        clean = bool(self.kind.currentData())
        name = self.field.text().strip()
        if not name:
            raise core.AnimationError("A storyboard needs a name.")
        doc = self.doc
        previous = self.name

        def run(data):
            title = core.check_name(data, name)
            start = None
            if not clean:
                before = core.find(data, previous) or (
                    data["storyboards"][-1] if data["storyboards"] else None
                )
                start = core.end_state(before) if before is not None else None
            data["storyboards"].append(core.new_storyboard(title, start))
            data["active"] = title
            return title

        self.name = animation.change(doc, None, run)
        ui.STATE["playheads"][(doc.Name, self.name)] = 0.0
        ui.note("%s made." % self.name)


def open_new_storyboard(doc):
    return _open(NewStoryboardPanel, doc)


# -- Transform Components ------------------------------------------------------------------------
class TransformPanel(AnimPanel):
    title = "Transform Components"
    icon = "anim_transform"
    picks_components = True

    def __init__(self, doc):
        super().__init__(doc, "Transform Components")
        self.view = animation_view.view_of(doc)
        self.triad = None
        self.pivot = None  # design coordinates; None: the middle of the picked components
        self.setting_pivot = False
        self._drag_start = None
        self._box_handle = None
        self.value_boxes = taskui.ValueBoxes(self, default="move2")
        self.pick_label = self.named(QtWidgets.QLabel("Select components"), "components")
        self.layout.addRow("Components", self.pick_label)
        self.pivot_button = self.named(QtWidgets.QPushButton("Set Pivot"), "set_pivot")
        self.pivot_button.setCheckable(True)
        self.pivot_button.setToolTip(
            "Then click a point on the model: the manipulator moves there and turns go " "about it"
        )
        self.pivot_button.toggled.connect(self._pivot_toggled)
        self.layout.addRow("Pivot", self.pivot_button)
        self.distance_fields = []
        for index, label in enumerate(("X Distance", "Y Distance", "Z Distance")):
            field = taskui.DistanceField(0.0, on_change=lambda _v: self.values_changed())
            self.named(field.widget, "d" + "xyz"[index])
            self.layout.addRow(label, field.widget)
            self.distance_fields.append(field)
        self.angle_fields = []
        for index, label in enumerate(("X Angle", "Y Angle", "Z Angle")):
            field = taskui.DistanceField(
                0.0, unit="deg", on_change=lambda _v: self.values_changed()
            )
            self.named(field.widget, "r" + "xyz"[index])
            self.layout.addRow(label, field.widget)
            self.angle_fields.append(field)
        self.trails = self.named(QtWidgets.QCheckBox(), "trails")
        self.trails.setToolTip("Draw the path of the components as a line")
        self.trails.toggled.connect(lambda *_a: self.changed())
        self.layout.addRow("Trail Line Visibility", self.trails)
        self.hint(self.where_text())
        self.finish_layout()
        self.start_picking()
        board = self.board()
        self._trails_before = bool(self.picks) and all(
            c.Name in board.get("trails", []) for c in self.picks
        )
        self.trails.setChecked(self._trails_before)

    def typing_field(self):
        return self.distance_fields[2]

    # -- values -------------------------------------------------------------------------------
    def move_vector(self):
        return V(*[f.value() for f in self.distance_fields])

    def rotation(self):
        """The turn the three angles give: about X, then Y, then Z (design axes)."""
        rx, ry, rz = [f.value() for f in self.angle_fields]
        turn = App.Rotation(V(1, 0, 0), rx)
        turn = App.Rotation(V(0, 1, 0), ry).multiply(turn)
        return App.Rotation(V(0, 0, 1), rz).multiply(turn)

    def moved(self):
        return self.move_vector().Length > 1e-9 or abs(self.rotation().Angle) > 1e-9

    def centre(self):
        """Where the manipulator stands before any move: the pivot, else the middle of the
        picked components as the storyboard has them at the playhead."""
        if self.pivot is not None:
            return V(self.pivot)
        board = self.board()
        local = animation.placements_of(self.doc, board, self.at)
        points = [animation.global_centre(self.doc, c, local) for c in self.picks]
        points = [p for p in points if p is not None]
        if not points:
            return V()
        return sum(points, V()) * (1.0 / len(points))

    def apply_to(self, board):
        """Record the dialog's transform on a storyboard (the preview's copy, or the real
        one). Returns the actions made."""
        made = []
        if not self.picks:
            return made
        turn = self.rotation()
        axis, angle = V(turn.Axis), turn.Angle * 180.0 / 3.141592653589793
        move = self.move_vector()
        pivot = self.centre()
        world = animation.global_of(self.doc, animation.placements_of(self.doc, board, self.at))
        for comp in self.picks:
            m = animation.to_parent_frame(comp, move, world=world)
            a = animation.to_parent_frame(comp, axis, world=world)
            p = animation.to_parent_frame(comp, pivot, point=True, world=world)
            act = core.record_transform(
                board, comp.Name, tuple(m), tuple(a), angle, tuple(p), self.at
            )
            if act is not None:
                made.append(act)
        names = [c.Name for c in self.picks]
        kept = [n for n in board.get("trails", []) if n not in names]
        board["trails"] = kept + (names if self.trails.isChecked() else [])
        return made

    def preview_board(self):
        temp = copy.deepcopy(self.board())
        self.apply_to(temp)
        return temp

    def values_changed(self):
        if self._closed:
            return
        self._place_triad()
        self.changed()

    # -- picks and the manipulator ------------------------------------------------------------
    def picks_changed(self):
        self.pick_label.setText(self.picks_text())
        self._make_triad()
        self.changed()

    def handles_busy(self):
        if self.triad is not None and self.triad.busy():
            return True
        return super().handles_busy()

    def point_clicked(self, comp, point):
        if not self.setting_pivot:
            return False
        self.pivot = V(point)
        self.pivot_button.setChecked(False)
        self._make_triad()
        self.changed()
        return True

    def _pivot_toggled(self, on):
        self.setting_pivot = bool(on)
        self.message.setText(
            "Click the point on the model the manipulator should stand on." if on else ""
        )

    def _triad_centre(self):
        return self.centre() + self.move_vector()

    def _make_triad(self):
        self._drop_triad()
        if self._closed or not self.picks or self.view is None:
            return
        try:
            from .move_ui import Triad

            self.triad = Triad(
                self.view,
                self._triad_centre(),
                10.0,
                turns=True,
                on_drag=self._dragged,
                on_release=self._released,
                on_handle=self._triad_handle,
            )
            if self._box_handle:
                self.triad.use(self._box_handle)
        except Exception as exc:
            warn("Transform Components: no manipulator: %s" % exc)

    def _drop_triad(self):
        if self.triad is not None:
            try:
                self.triad.remove()
            except Exception as exc:
                warn("Transform Components: %s" % exc)
            self.triad = None

    def _place_triad(self):
        if self.triad is not None and not self.triad.dragging():
            self.triad.set_center(self._triad_centre())

    def _field_of(self, handle):
        kind, index = handle
        return (self.distance_fields if kind == "move" else self.angle_fields)[index]

    def _triad_handle(self, handle):
        if self._closed or self.triad is None:
            return
        self._box_handle = handle
        field = self._field_of(handle)
        self.value_boxes.attach(
            self.triad,
            "%s%d" % handle,
            lambda: field.widget.text(),
            lambda text: self._box_typed(field, text),
        )

    def _box_typed(self, field, text):
        if self._closed:
            return
        try:
            value = field.parse(text.strip().lstrip("="))
        except ValueError as exc:
            self.message.setText("⚠ %s" % exc)
            return
        self.message.setText("")
        field.take(value)

    def _dragged(self, kind, index, value):
        if self._closed:
            return
        fields = self.distance_fields if kind == "move" else self.angle_fields
        if self._drag_start is None:
            self._drag_start = [f.value() for f in fields]
        fields[index].set_value(self._drag_start[index] + value)
        if kind == "move" and self.triad is not None:
            self.triad.set_center(self._triad_centre())
        self.changed()

    def _released(self):
        self._drag_start = None
        self.changed()

    # -- OK -----------------------------------------------------------------------------------
    def commit(self):
        if not self.picks:
            raise core.AnimationError(
                "Pick the components to transform first: click them in the view or in the "
                "browser."
            )
        if not self.moved() and self.trails.isChecked() == self._trails_before:
            raise core.AnimationError(
                "Nothing moved yet: drag an arrow or a turn handle, or type a distance or an "
                "angle."
            )
        made = {}

        def run(data):
            board = animation._board(data, self.name)
            made["actions"] = self.apply_to(board)
            board["playhead"] = self.at
            data["active"] = board["name"]

        animation.change(self.doc, None, run)
        count = len(made.get("actions") or [])
        if core.in_scratch(self.at):
            ui.note("In the scratch zone: %s starts with that." % self.name)
        else:
            ui.note(
                "%d action%s recorded, ending at %s."
                % (count, "" if count == 1 else "s", core.time_text(self.at))
            )

    def cleanup(self):
        self._drop_triad()
        try:
            self.value_boxes.discard()
        except Exception:
            pass
        super().cleanup()


def open_transform(doc):
    return _open(TransformPanel, doc)


# -- Auto Explode --------------------------------------------------------------------------------
class ExplodePanel(AnimPanel):
    title = "Auto Explode"
    icon = "anim_explode_one"

    def __init__(self, doc, levels):
        self.levels = levels
        self.title = "Auto Explode: %s" % ("All Levels" if levels == "all" else "One Level")
        super().__init__(doc, self.title)
        self.roots = list(ui.selected_components(doc))
        what = ", ".join(c.Label for c in self.roots) if self.roots else "The whole design"
        self.layout.addRow("Explode", self.named(QtWidgets.QLabel(what), "what"))
        box, self.scale, self.scale_text = self.slider("scale", core.slider_from_scale(1.0))
        self.scale.setToolTip("Left: closer together. Right: further apart.")
        self.scale.valueChanged.connect(lambda *_a: self._scale_changed())
        self.layout.addRow("Explosion Scale", box)
        self.sequence = self.named(QtWidgets.QComboBox(), "sequence")
        for text, value in SEQUENCES:
            self.sequence.addItem(text, value)
        self.sequence.setToolTip(
            "One-Step: every component moves at the same time. Sequential: one after "
            "another, the outermost first."
        )
        self.sequence.currentIndexChanged.connect(lambda *_a: self.changed())
        self.layout.addRow("Sequence", self.sequence)
        self.trails = self.named(QtWidgets.QCheckBox(), "trails")
        self.trails.setToolTip("Draw the path of each component as a line")
        self.trails.toggled.connect(lambda *_a: self.changed())
        self.layout.addRow("Trail Line Visibility", self.trails)
        self.count = self.named(QtWidgets.QLabel(""), "count")
        self.count.setStyleSheet(HINT_STYLE)
        self.layout.addRow(self.count)
        self.hint(self.where_text())
        self.finish_layout()
        self._scale_changed()
        Gui.Selection.clearSelection()

    def scale_value(self):
        return core.scale_from_slider(self.scale.value())

    def _scale_changed(self):
        self.scale_text.setText("%.2f" % self.scale_value())
        self.changed()

    def plan(self, board):
        return animation.explode_plan(
            self.doc, board, self.at, self.roots, self.levels, self.scale_value()
        )

    def preview_board(self):
        temp = copy.deepcopy(self.board())
        plan = self.plan(temp)
        self.count.setText(
            "%d component%s move." % (len(plan), "" if len(plan) == 1 else "s")
            if plan
            else "Nothing moves at this scale."
        )
        animation.apply_moves(
            temp, plan, self.at, bool(self.sequence.currentData()), self.trails.isChecked()
        )
        return temp

    def commit(self):
        plan = animation.auto_explode(
            self.doc,
            self.name,
            self.at,
            self.roots,
            self.levels,
            self.scale_value(),
            bool(self.sequence.currentData()),
            self.trails.isChecked(),
            step=None,
        )
        if core.in_scratch(self.at):
            ui.note("In the scratch zone: %s starts exploded." % self.name)
        else:
            ui.note(
                "%d move action%s recorded, ending at %s."
                % (len(plan), "" if len(plan) == 1 else "s", core.time_text(self.at))
            )


def open_explode(doc, levels):
    board = ui.board(doc)
    picked = ui.selected_components(doc)
    try:
        plan = animation.explode_plan(doc, board, ui.playhead(doc), picked, levels, 1.0)
    except core.AnimationError as exc:
        commands.tell(str(exc))
        return None
    if not plan:
        commands.tell(
            "Nothing to explode here: there is only one component, or they sit on the same "
            "spot. Pick an assembly with several parts, or use Manual Explode."
        )
        return None
    return _open(ExplodePanel, doc, levels)


# -- Manual Explode ------------------------------------------------------------------------------
class ManualExplodePanel(AnimPanel):
    title = "Manual Explode"
    icon = "anim_explode_manual"
    picks_components = True

    def __init__(self, doc):
        super().__init__(doc, "Manual Explode")
        self.view = animation_view.view_of(doc)
        self.axes = {}  # component name -> "X+" ... "Z-"
        self.current = None  # the component whose axis is being picked
        self.arrows = None
        self.lines = None
        self.list = self.named(QtWidgets.QListWidget(), "list")
        self.list.setMaximumHeight(96)
        self.list.currentRowChanged.connect(self._row_changed)
        self.layout.addRow("Components", self.list)
        self.axis = self.named(QtWidgets.QComboBox(), "axis")
        self.axis.addItem("Pick an axis", "")
        for key in ("X+", "X-", "Y+", "Y-", "Z+", "Z-"):
            self.axis.addItem(key[1] + key[0], key)
        self.axis.setToolTip(
            "The direction the component picked in the list goes (or click one of the six "
            "arrows on it in the view)"
        )
        self.axis.currentIndexChanged.connect(lambda *_a: self._axis_chosen())
        self.layout.addRow("Axis", self.axis)
        self.distance = taskui.DistanceField(self._default_distance(), on_change=self._typed)
        self.named(self.distance.widget, "distance")
        self.layout.addRow("Distance", self.distance.widget)
        box, self.scale, self.scale_text = self.slider("scale", core.slider_from_scale(1.0))
        self.scale.valueChanged.connect(lambda *_a: self._scale_changed())
        self.layout.addRow("Explosion Scale", box)
        self.sequence = self.named(QtWidgets.QComboBox(), "sequence")
        for text, value in SEQUENCES:
            self.sequence.addItem(text, value)
        self.sequence.currentIndexChanged.connect(lambda *_a: self.changed())
        self.layout.addRow("Sequence", self.sequence)
        self.trails = self.named(QtWidgets.QCheckBox(), "trails")
        self.trails.toggled.connect(lambda *_a: self.changed())
        self.layout.addRow("Trail Line Visibility", self.trails)
        self.hint(
            "Click a component, then the axis it goes along (an arrow on it, or the Axis "
            "list). Repeat for each component."
        )
        self.hint(self.where_text())
        self.finish_layout()
        self.scale_text.setText("%.2f" % self.scale_value())
        self.start_picking()

    def typing_field(self):
        return self.distance

    def _default_distance(self):
        """Half the size of the design's components, rounded: a visible move to start from."""
        boxes = animation.sibling_boxes(
            self.doc, None, {c.Name: c.Placement for c in animation.movables(self.doc)}
        )
        size = max(core.box_size(core.box_union(boxes.values()))) if boxes else 20.0
        return float(max(1.0, round(size / 2.0)))

    def scale_value(self):
        return core.scale_from_slider(self.scale.value())

    def _scale_changed(self):
        self.scale_text.setText("%.2f" % self.scale_value())
        self.changed()

    def _typed(self, _value):
        self.changed()

    # -- picks --------------------------------------------------------------------------------
    def component_clicked(self, comp):
        if self.arrows is not None and self.arrows.clicked_recently():
            return  # (the click was on an axis arrow)
        if comp in self.picks:
            if self.current is comp:
                self.picks.remove(comp)
                self.axes.pop(comp.Name, None)
                self.current = self.picks[-1] if self.picks else None
            else:
                self.current = comp
        else:
            self.picks.append(comp)
            self.current = comp
        self.message.setText("")
        self.picks_changed()

    def picks_changed(self):
        if self.current not in self.picks:
            self.current = self.picks[-1] if self.picks else None
        self._fill()
        self._make_arrows()
        self.changed()

    def _fill(self):
        self.list.blockSignals(True)
        self.axis.blockSignals(True)
        try:
            self.list.clear()
            for comp in self.picks:
                axis = self.axes.get(comp.Name)
                self.list.addItem(
                    "%s: %s" % (comp.Label, (axis[1] + axis[0]) if axis else "pick its axis")
                )
            if self.current in self.picks:
                self.list.setCurrentRow(self.picks.index(self.current))
            wanted = self.axes.get(self.current.Name, "") if self.current is not None else ""
            for i in range(self.axis.count()):
                if self.axis.itemData(i) == wanted:
                    self.axis.setCurrentIndex(i)
            self.axis.setEnabled(self.current is not None)
        finally:
            self.list.blockSignals(False)
            self.axis.blockSignals(False)

    def _row_changed(self, row):
        if 0 <= row < len(self.picks):
            self.current = self.picks[row]
            self._fill()
            self._make_arrows()

    def _axis_chosen(self):
        key = self.axis.currentData()
        if self.current is None or not key:
            return
        self.set_axis(key)

    def set_axis(self, key):
        if self.current is None or key not in core.AXES:
            return
        self.axes[self.current.Name] = key
        self.message.setText("")
        self._fill()
        self._make_arrows()
        self.changed()

    # -- the six arrows on the current component ----------------------------------------------
    def arrow_points(self):
        """({axis key: tip point}, centre) in design coordinates of the arrows drawn on the
        current component, as the preview shows it; None when there is none."""
        if self.current is None or self.view is None:
            return None
        board = self.preview_board_quiet()
        local = animation.placements_of(self.doc, board, self.at)
        centre = animation.global_centre(self.doc, self.current, local)
        if centre is None:
            return None
        length = taskui.mm_per_pixel(self.view, centre) * 70.0
        return {key: centre + V(*vec) * length for key, vec in core.AXES.items()}, centre

    def _make_arrows(self):
        self._drop_arrows()
        if self._closed or self.current is None or self.view is None:
            return
        try:
            from . import handles3d

            found = self.arrow_points()
            if not found:
                return
            points, centre = found
            chosen = self.axes.get(self.current.Name)
            self.lines = handles3d.Overlay(self.view)
            dots = []
            for key, tip in points.items():
                colour = AXIS_COLOURS[key[0]]
                self.lines.line(centre, tip, colour, 3.0 if key == chosen else 1.5)
                dots.append((key, tip, colour))
            size = taskui.mm_per_pixel(self.view, centre) * 28.0
            self.arrows = handles3d.PointDots(self.view, dots, self._arrow_clicked, size)
        except Exception as exc:
            warn("Manual Explode: no arrows: %s" % exc)

    def _drop_arrows(self):
        for name in ("arrows", "lines"):
            thing = getattr(self, name)
            if thing is not None:
                try:
                    thing.remove()
                except Exception as exc:
                    warn("Manual Explode: %s" % exc)
            setattr(self, name, None)

    def _arrow_clicked(self, key):
        if self._closed:
            return
        from . import handles3d

        handles3d.touch()  # (the click is the arrow's, not a pick of what lies behind it)
        self.set_axis(key)

    def handles_busy(self):
        if self.arrows is not None and self.arrows.clicked_recently():
            return True
        return super().handles_busy()

    # -- preview and OK -----------------------------------------------------------------------
    def chosen(self):
        return [(c, self.axes[c.Name]) for c in self.picks if self.axes.get(c.Name)]

    def plan(self, board):
        world = animation.global_of(self.doc, animation.placements_of(self.doc, board, self.at))
        return animation.manual_plan(
            self.doc, self.chosen(), self.distance.value(), self.scale_value(), world=world
        )

    def preview_board_quiet(self):
        temp = copy.deepcopy(self.board())
        plan = [p for p in self.plan(temp) if core.v_len(p[1]) > 1e-9]
        animation.apply_moves(
            temp, plan, self.at, bool(self.sequence.currentData()), self.trails.isChecked()
        )
        return temp

    def preview_board(self):
        return self.preview_board_quiet()

    def commit(self):
        if not self.picks:
            raise core.AnimationError(
                "Pick a component first: click it in the view or in the browser."
            )
        missing = [c.Label for c in self.picks if not self.axes.get(c.Name)]
        if missing:
            raise core.AnimationError(
                "Pick the axis %s explodes along: click one of its arrows, or choose it in "
                "the Axis list." % missing[0]
            )
        if abs(self.distance.value() * self.scale_value()) < 1e-9:
            raise core.AnimationError("The distance is 0: type a distance, or move the scale.")
        sequential = bool(self.sequence.currentData())
        trails = self.trails.isChecked()
        made = {}

        def run(data):
            board = animation._board(data, self.name)
            plan = self.plan(board)
            made["plan"] = plan
            animation.apply_moves(board, plan, self.at, sequential, trails)
            board["playhead"] = self.at
            data["active"] = board["name"]

        animation.change(self.doc, None, run)
        count = len(made.get("plan") or [])
        ui.note(
            "%d component%s exploded%s."
            % (
                count,
                "" if count == 1 else "s",
                (
                    " (scratch zone: the storyboard starts that way)"
                    if core.in_scratch(self.at)
                    else ", ending at %s" % core.time_text(self.at)
                ),
            )
        )

    def cleanup(self):
        self._drop_arrows()
        super().cleanup()


def open_manual_explode(doc):
    return _open(ManualExplodePanel, doc)


# -- Create Callout ------------------------------------------------------------------------------
class CalloutPanel(AnimPanel):
    title = "Create Callout"
    icon = "anim_callout"
    picks_components = True

    def __init__(self, doc):
        super().__init__(doc, "Create Callout")
        self.point = None  # design coordinates
        self.comp = None
        self.where = self.named(QtWidgets.QLabel("Click a point on the model"), "where")
        self.layout.addRow("Point", self.where)
        self.text = self.named(QtWidgets.QLineEdit(), "text")
        self.text.setPlaceholderText("What the callout says")
        self.text.textChanged.connect(lambda *_a: self.changed())
        self.layout.addRow("Text", self.text)
        self.hint(
            "Click where the callout points to, then type its text. On a component the pin "
            "is green and follows it; elsewhere it is red and stays in space. It shows from "
            "the playhead (%s) on; drag its bar in the timeline to change that."
            % ("the start" if core.in_scratch(self.at) else core.time_text(self.at))
        )
        self.finish_layout()
        self.observer = _Observer(self)
        Gui.Selection.addObserver(self.observer)
        Gui.Selection.clearSelection()

    def point_clicked(self, comp, point):
        self.point, self.comp = V(point), comp
        self.where.setText(
            "On %s" % comp.Label if comp is not None else "In space (not on a component)"
        )
        self.message.setText("")
        self.changed()
        QtCore.QTimer.singleShot(0, self._focus_text)
        return True

    def _focus_text(self):
        try:
            if not self._closed:
                self.text.setFocus()
        except RuntimeError:
            pass

    def component_clicked(self, comp):
        pass  # (a row of the browser: a callout needs a point on the model)

    def _show_picks(self):
        self._syncing = True
        try:
            Gui.Selection.clearSelection()
        finally:
            QtCore.QTimer.singleShot(0, self._synced)

    def _record(self, board, text):
        where = V(self.point)
        target = ""
        if self.comp is not None:
            local = animation.placements_of(self.doc, board, self.at)
            where = animation.global_of(self.doc, local)[self.comp.Name].inverse().multVec(where)
            target = self.comp.Name
        return core.record_callout(board, target, tuple(where), text, self.at)

    def preview_board(self):
        if self.point is None:
            return None
        temp = copy.deepcopy(self.board())
        self._record(temp, self.text.text().strip() or "...")
        return temp

    def commit(self):
        if self.point is None:
            raise core.AnimationError("Click the point on the model the callout points to.")
        text = self.text.text().strip()
        if not text:
            raise core.AnimationError("Type the callout's text first.")

        def run(data):
            board = animation._board(data, self.name)
            self._record(board, text)
            board["playhead"] = self.at
            data["active"] = board["name"]

        animation.change(self.doc, None, run)
        ui.note('Callout "%s" added.' % text)


def open_callout(doc):
    return _open(CalloutPanel, doc)


# -- Edit Start/End (and a visibility action's transition, a callout's text) -----------------------
class EditActionPanel(AnimPanel):
    title = "Edit Start/End"
    icon = "anim_storyboard"

    def __init__(self, doc, action_id):
        act = core.action(ui.board(doc), action_id)
        if act is None:
            raise core.AnimationError("That action is gone.")
        self.action_id = action_id
        self.kind = act["kind"]
        self.title = "Edit Action" if self.kind == "visibility" else "Edit Start/End"
        super().__init__(doc, self.title)
        what = core.title(act)
        if self.kind in ("transform", "visibility"):
            what += " of %s" % animation.label(doc, act["target"])
        self.layout.addRow("Action", self.named(QtWidgets.QLabel(what), "what"))
        self.transition = None
        self.text = None
        if self.kind == "callout":
            self.text = self.named(QtWidgets.QLineEdit(act.get("text", "")), "text")
            self.text.textChanged.connect(lambda *_a: self.changed())
            self.layout.addRow("Text", self.text)
        self.start = self._time("start", float(act["start"]))
        self.layout.addRow("Start", self.start)
        end = act.get("end")
        instant = end is not None and float(end) - float(act["start"]) < 1e-9
        if self.kind == "visibility":
            self.transition = self.named(QtWidgets.QComboBox(), "transition")
            self.transition.addItem("Instant", "instant")
            self.transition.addItem("Duration", "duration")
            self.transition.setCurrentIndex(0 if instant else 1)
            self.transition.setToolTip(
                "Instant: shown or hidden at once. Duration: it fades between Start and End."
            )
            self.transition.currentIndexChanged.connect(lambda *_a: self._transition_changed())
            self.layout.addRow("Transition", self.transition)
        self.to_end = None
        if self.kind == "callout":
            self.to_end = self.named(QtWidgets.QCheckBox(), "to_end")
            self.to_end.setChecked(end is None)
            self.to_end.setToolTip("Shown until the storyboard ends")
            self.to_end.toggled.connect(lambda *_a: self._transition_changed())
            self.layout.addRow("To the end", self.to_end)
        shown_end = float(act["start"]) + 1.0 if end is None else float(end)
        self.end = self._time("end", shown_end)
        self.layout.addRow("End", self.end)
        self.length = self.named(QtWidgets.QLabel(""), "length")
        self.length.setStyleSheet(HINT_STYLE)
        self.layout.addRow(self.length)
        self.finish_layout()
        self._transition_changed()

    def _time(self, key, value):
        box = self.named(QtWidgets.QDoubleSpinBox(), key)
        box.setRange(0.0, 36000.0)
        box.setDecimals(2)
        box.setSingleStep(0.1)
        box.setSuffix(" s")
        box.setValue(value)
        box.setKeyboardTracking(False)
        box.valueChanged.connect(lambda *_a: self.changed())
        return box

    def _transition_changed(self):
        fixed = (self.transition is not None and self.transition.currentData() == "instant") or (
            self.to_end is not None and self.to_end.isChecked()
        )
        self.end.setEnabled(not fixed)
        if self.transition is not None and not fixed and self.end.value() <= self.start.value():
            self.end.setValue(self.start.value() + 1.0)
        self.changed()

    def span(self):
        start = float(self.start.value())
        if self.transition is not None and self.transition.currentData() == "instant":
            return start, start
        if self.to_end is not None and self.to_end.isChecked():
            return start, None
        return start, float(self.end.value())

    def apply_to(self, board):
        start, end = self.span()
        act = core.set_span(board, self.action_id, start, end)
        if self.text is not None:
            text = self.text.text().strip()
            if not text:
                raise core.AnimationError("Type the callout's text first.")
            act["text"] = text
        return act

    def preview_board(self):
        temp = copy.deepcopy(self.board())
        start, end = self.span()
        self.length.setText(
            "Shown from %s on." % core.time_text(start)
            if end is None
            else "Length: %s." % core.time_text(end - start)
        )
        self.apply_to(temp)
        return temp

    def commit(self):
        animation.change(
            self.doc, None, lambda data: self.apply_to(animation._board(data, self.name))
        )
        start, end = self.span()
        ui.note(
            "Action: %s to %s."
            % (core.time_text(start), "the end" if end is None else core.time_text(end))
        )


def open_edit_action(doc, action_id):
    if doc is None:
        return None
    return _open(EditActionPanel, doc, action_id)


# -- Publish Video -------------------------------------------------------------------------------
SIZES = [
    ("Current Document Window Size", None),
    ("1280 x 720 (HD)", (1280, 720)),
    ("1920 x 1080 (Full HD)", (1920, 1080)),
    ("3840 x 2160 (4K)", (3840, 2160)),
    ("640 x 360", (640, 360)),
    ("Custom", "custom"),
]
# A stand-in for the system's save dialog (the scenarios set it): fn(suggested path) -> path
SAVE_PICKER = [None]


class PublishPanel(AnimPanel):
    title = "Publish Video"
    icon = "anim_publish"
    animation_preview = False

    def __init__(self, doc):
        from . import animation_video

        super().__init__(doc, "Publish Video")
        self.video = animation_video
        self.job = None
        self.scope = self.named(QtWidgets.QComboBox(), "scope")
        self.scope.addItem("Current Storyboard", "current")
        self.scope.addItem("All Storyboards", "all")
        self.scope.currentIndexChanged.connect(lambda *_a: self._changed())
        self.layout.addRow("Video Scope", self.scope)
        self.size = self.named(QtWidgets.QComboBox(), "size")
        for text, value in SIZES:
            self.size.addItem(text, value)
        self.size.currentIndexChanged.connect(lambda *_a: self._size_changed())
        self.layout.addRow("Video Resolution", self.size)
        w, h = animation_video.window_size(doc)
        self._ratio = w / float(max(h, 1))
        self.width = self._pixels("width", w)
        self.height = self._pixels("height", h)
        self.layout.addRow("Width", self.width)
        self.layout.addRow("Height", self.height)
        self.lock = self.named(QtWidgets.QCheckBox(), "lock")
        self.lock.setChecked(True)
        self.layout.addRow("Lock Aspect Ratio", self.lock)
        self.width.valueChanged.connect(lambda *_a: self._side_changed("width"))
        self.height.valueChanged.connect(lambda *_a: self._side_changed("height"))
        self.fps = self.named(QtWidgets.QComboBox(), "fps")
        for value in animation_video.FRAME_RATES:
            self.fps.addItem("%d frames a second" % value, value)
        self.fps.setCurrentIndex(animation_video.FRAME_RATES.index(24))
        self.fps.currentIndexChanged.connect(lambda *_a: self._changed())
        self.layout.addRow("Frame Rate", self.fps)
        self.format = self.named(QtWidgets.QComboBox(), "format")
        for key, text, enabled, tip in animation_video.formats():
            self.format.addItem(text, key)
            item = self.format.model().item(self.format.count() - 1)
            item.setEnabled(enabled)
            item.setToolTip(tip)
        self.format.currentIndexChanged.connect(lambda *_a: self._format_changed())
        self.layout.addRow("File Type", self.format)
        self.path = self.named(QtWidgets.QLineEdit(self._default_path("avi")), "path")
        browse = self.named(QtWidgets.QPushButton("Browse..."), "browse")
        browse.clicked.connect(lambda *_a: self._browse())
        row = QtWidgets.QWidget()
        box = QtWidgets.QHBoxLayout(row)
        box.setContentsMargins(0, 0, 0, 0)
        box.addWidget(self.path, 1)
        box.addWidget(browse)
        self.layout.addRow("Save As", row)
        self.info = self.named(QtWidgets.QLabel(""), "info")
        self.info.setWordWrap(True)
        self.info.setStyleSheet(HINT_STYLE)
        self.layout.addRow(self.info)
        self.progress = self.named(QtWidgets.QProgressBar(), "progress")
        self.progress.setVisible(False)
        self.layout.addRow(self.progress)
        self.finish_layout()
        self._size_changed()
        self._changed()

    def _pixels(self, key, value):
        box = self.named(QtWidgets.QSpinBox(), key)
        box.setRange(16, 8192)
        box.setSingleStep(2)
        box.setValue(int(value))
        box.setKeyboardTracking(False)
        return box

    def _default_path(self, extension):
        from . import animation_video

        return animation_video.default_path(self.doc, self.name, extension)

    def _size_changed(self):
        value = self.size.currentData()
        custom = value == "custom"
        for box in (self.width, self.height):
            box.setEnabled(custom)
        self.lock.setEnabled(custom)
        if value is None:
            value = self.video.window_size(self.doc)
        if not custom:
            for box, number in zip((self.width, self.height), value):
                box.blockSignals(True)
                box.setValue(int(number))
                box.blockSignals(False)
        self._ratio = self.width.value() / float(max(self.height.value(), 1))
        self._changed()

    def _side_changed(self, which):
        if self.lock.isChecked() and self.size.currentData() == "custom":
            other = self.height if which == "width" else self.width
            value = (
                self.width.value() / self._ratio
                if which == "width"
                else self.height.value() * self._ratio
            )
            other.blockSignals(True)
            other.setValue(max(16, int(round(value))))
            other.blockSignals(False)
        else:
            self._ratio = self.width.value() / float(max(self.height.value(), 1))
        self._changed()

    def _format_changed(self):
        key = self.format.currentData()
        extension = self.video.EXTENSIONS.get(key, "avi")
        path = self.path.text().strip()
        if path:
            self.path.setText(os.path.splitext(path)[0] + "." + extension)
        self._changed()

    def _browse(self):
        key = self.format.currentData()
        extension = self.video.EXTENSIONS.get(key, "avi")
        start = self.path.text().strip() or self._default_path(extension)
        picker = SAVE_PICKER[0]
        if picker is not None:
            chosen = picker(start)
        else:
            chosen, _filter = QtWidgets.QFileDialog.getSaveFileName(
                Gui.getMainWindow(),
                "Publish Video",
                start,
                "%s (*.%s)" % (self.format.currentText(), extension),
            )
        if chosen:
            if not os.path.splitext(chosen)[1]:
                chosen += "." + extension
            self.path.setText(chosen)

    def names(self):
        if self.scope.currentData() == "all":
            return [
                n for n in animation.storyboards(self.doc) if animation.duration(self.doc, n) > 0
            ]
        return [self.name]

    def settings(self):
        return {
            "names": self.names(),
            "width": int(self.width.value()),
            "height": int(self.height.value()),
            "fps": int(self.fps.currentData()),
            "format": self.format.currentData(),
            "path": self.path.text().strip(),
        }

    def _changed(self):
        try:
            s = self.settings()
            total = 0.0
            for name in s["names"]:
                if name in animation.storyboards(self.doc):
                    total += animation.duration(self.doc, name)
            frames = sum(
                len(core.frame_times(animation.duration(self.doc, n), s["fps"]))
                for n in s["names"]
                if n in animation.storyboards(self.doc)
            )
            self.info.setText(
                "%s, %d frames, %d x %d. %s"
                % (
                    core.time_text(total),
                    frames,
                    s["width"],
                    s["height"],
                    self.video.encoder_note(),
                )
            )
        except Exception as exc:
            self.info.setText(str(exc))

    def getStandardButtons(self):
        buttons = QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel
        return getattr(buttons, "value", buttons)

    def accept(self):
        """OK starts the rendering; the dialog closes when the file is written."""
        if self.job is not None:
            return False
        try:
            self.job = self.video.start(self.doc, self.settings(), self._progress, self._finished)
        except core.AnimationError as exc:
            self.message.setText("⚠ %s" % exc)
            self.job = None
            return False
        self.progress.setVisible(True)
        self.message.setText("Rendering... (Cancel stops it)")
        for widget in (
            self.scope,
            self.size,
            self.width,
            self.height,
            self.fps,
            self.format,
            self.path,
        ):
            widget.setEnabled(False)
        return False

    def _progress(self, done, total):
        try:
            if not self._closed:
                self.progress.setRange(0, max(1, total))
                self.progress.setValue(done)
        except RuntimeError:
            pass

    def _finished(self, path, error):
        self.job = None
        if self._closed:
            return
        if error:
            self.message.setText("⚠ %s" % error)
            self.progress.setVisible(False)
            for widget in (self.scope, self.size, self.fps, self.format, self.path):
                widget.setEnabled(True)
            self._size_changed()
            return
        AnimPanel.reject(self)  # (nothing of the design changed: the undo step is dropped)
        ui.note("Video saved: %s" % path)
        commands.tell("Video saved: %s" % path)
        log("video published: %s" % path)

    def reject(self):
        if self.job is not None:
            self.video.cancel()
            self.job = None
        return super().reject()

    def finish(self):
        self.reject()


def open_publish(doc):
    names = [n for n in animation.storyboards(doc) if animation.duration(doc, n) > 0]
    if not names:
        commands.tell(
            "There is nothing to publish yet: no storyboard has an action. Move the playhead "
            "past 0 and transform or explode a component first."
        )
        return None
    return _open(PublishPanel, doc)
