# SPDX-License-Identifier: LGPL-2.1-or-later
"""MODIFY > Move and Rotate, GEOMETRY > Center Mark Pattern, TABLES > Renumber and Align
Balloons of the DRAWING workspace: the dialogs and the clicks on the sheet (the work is in
drawing_tools.py). Each is one undo step; Esc or Cancel leaves the sheet as it was."""

import FreeCADGui as Gui

from . import drawing, drawing_tools, drawing_ui, taskui
from .compat import QtCore, QtWidgets

DrawingPanel = drawing_ui.DrawingPanel


def _spin(lo, hi, value=0.0, step=1.0, suffix="", decimals=2):
    box = QtWidgets.QDoubleSpinBox()
    box.setRange(lo, hi)
    box.setDecimals(decimals)
    box.setSingleStep(step)
    box.setValue(value)
    if suffix:
        box.setSuffix(suffix)
    box.setKeyboardTracking(False)
    return box


def _preselected(page, accept):
    """What is selected on the sheet when a command starts (Fusion commands take it)."""
    found = []
    try:
        for sel in Gui.Selection.getSelectionEx("", 0):
            obj = sel.Object
            if (
                obj is not None
                and drawing.same(drawing.page_of(obj), page)
                and accept(obj)
                and obj.Name not in [f.Name for f in found]
            ):
                found.append(obj)
    except Exception:
        pass
    return found


class _PickPanel(DrawingPanel):
    """A dialog whose first step is clicking things on the sheet: a click picks, a second
    click on the same thing lets it go; what is picked is framed."""

    def _toggle(self, obj):
        names = [o.Name for o in self.picked]
        if obj.Name in names:
            self.picked = [o for o in self.picked if o.Name != obj.Name]
        else:
            self.picked.append(obj)
        self._frame()

    def _frame(self):
        self.clear_overlay()
        for obj in self.picked:
            if drawing.alive(obj):
                self.overlay_rect(*drawing_tools.rect_of(obj))


# ------------------------------------------------------------------ Move
class MovePanel(_PickPanel):
    """Fusion's Move on a sheet: pick views, tables, text or balloons, then click the point
    to move from and the point to move to (or type the distances)."""

    title = "Move"
    icon = "move"

    def __init__(self, page):
        super().__init__(page, "Move")
        self.picked = _preselected(page, self._movable)
        self.phase = "pick"
        self.base = None
        self.start = None
        self.dx = drawing_ui.LengthBox(page, -5000.0, 5000.0, 0.0)
        self.dx.setKeyboardTracking(False)
        self.dx.setObjectName("Fission180DrawingMoveX")
        self.dy = drawing_ui.LengthBox(page, -5000.0, 5000.0, 0.0)
        self.dy.setKeyboardTracking(False)
        self.dy.setObjectName("Fission180DrawingMoveY")
        self.layout.addRow("X Distance", self.dx)
        self.layout.addRow("Y Distance", self.dy)
        self.dx.valueChanged.connect(self._typed)
        self.dy.valueChanged.connect(self._typed)
        self.finish_layout()
        self._frame()
        self._say_pick()

    @staticmethod
    def _movable(obj):
        return (
            drawing.is_view(obj)
            or obj.TypeId in (drawing.BALLOON, drawing.ANNOTATION)
            or drawing_tools._is_table(obj)
        )

    def _say_pick(self):
        if self.picked:
            self.say(
                "%d picked. Click more, or press Enter and click the point to move from "
                "(or type the distances)." % len(self.picked)
            )
        else:
            self.say("Click what to move: views, the parts list, text or balloons.")

    def _begin(self):
        if self.start is None:
            self.start = drawing_tools.places_of(self.picked)

    def on_press(self, point, event):
        if self._closed:
            return True
        if self.phase == "pick":
            obj = drawing_tools.object_at(self.page, point)
            if obj is None:
                self.message.setText("Click a view, a table, a text note or a balloon.")
                return True
            self.message.setText("")
            self._toggle(obj)
            self._say_pick()
            return True
        if self.phase == "from":
            self.base = point
            self._begin()
            self.phase = "to"
            self.say("Click where that point goes.")
            return True
        if self.phase == "to":
            self._apply(point[0] - self.base[0], point[1] - self.base[1], show=True)
            self.phase = "done"
            self.clear_overlay()
            self.say("Moved. OK keeps it; type other distances to change it.")
        return True

    def on_move(self, point, event):
        if self._closed or self.phase != "to":
            return
        self._apply(point[0] - self.base[0], point[1] - self.base[1], show=True)

    def _apply(self, dx, dy, show=False):
        drawing_tools.move_to(self.doc, self.start, dx, dy)
        if show:
            for box, value in ((self.dx, dx), (self.dy, dy)):
                box.blockSignals(True)
                box.set_mm(value)
                box.blockSignals(False)
        self.clear_overlay()
        self.schedule()

    def _typed(self, *_args):
        if self._closed:
            return
        if not self.picked:
            self.message.setText("Click what to move first.")
            return
        self.message.setText("")
        self._begin()
        self.phase = "done"
        self._apply(self.dx.mm(), self.dy.mm())

    def on_key(self, key, event):
        if key in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter) and self.phase == "pick":
            if not self.picked:
                self.message.setText("Click what to move first.")
                return True
            self.phase = "from"
            self.say("Click the point to move from.")
            return True
        return super().on_key(key, event)

    def accept(self):
        if not self.picked:
            self.message.setText("Click what to move first.")
            return False
        if self.start is None:
            self.message.setText(
                "Nothing was moved yet: press Enter and click two points, or type the " "distances."
            )
            return False
        return super().accept()


# ------------------------------------------------------------------ Rotate
class RotatePanel(_PickPanel):
    """Fusion's Rotate on a sheet: pick views, give the angle (counter-clockwise)."""

    title = "Rotate"
    icon = "move"

    def __init__(self, page):
        super().__init__(page, "Rotate")
        self.picked = _preselected(page, drawing_tools.can_rotate)
        self.start = {}
        self.angle = _spin(-360.0, 360.0, 0.0, 15.0, "°")
        self.angle.setObjectName("Fission180DrawingRotateAngle")
        self.layout.addRow("Angle", self.angle)
        self.angle.valueChanged.connect(self._typed)
        self.finish_layout()
        self._frame()
        self.say("Click the views to turn, then type the angle (counter-clockwise).")

    def on_press(self, point, event):
        if self._closed:
            return True
        obj = drawing_tools.object_at(self.page, point)
        if obj is None or not drawing_tools.can_rotate(obj):
            self.message.setText("Rotate turns views: click a view.")
            return True
        self.message.setText("")
        if obj.Name in self.start:  # (let go: back to where it was)
            drawing_tools.rotate_to(self.doc, {obj.Name: self.start.pop(obj.Name)}, 0.0)
        self._toggle(obj)
        self._typed()
        return True

    def _typed(self, *_args):
        if self._closed:
            return
        for view in self.picked:
            if view.Name not in self.start:
                self.start.update(drawing_tools.rotations_of([view]))
        live = {v.Name: self.start[v.Name] for v in self.picked if v.Name in self.start}
        drawing_tools.rotate_to(self.doc, live, self.angle.value())
        self.schedule()

    def accept(self):
        if not self.picked:
            self.message.setText("Click a view to turn first.")
            return False
        self.clear_overlay()
        return super().accept()


# ------------------------------------------------------------------ Center Mark Pattern
class CenterMarkPatternPanel(DrawingPanel):
    """Fusion's Center Mark Pattern: click the holes of a pattern in one view, Enter: a
    centre mark on each and the line or circle through their centres."""

    title = "Center Mark Pattern"
    icon = "dw_center_mark"

    def __init__(self, page):
        super().__init__(page, "Center Mark Pattern")
        self.view = None
        self.names = []
        self.finish_layout()
        self.say("Click the holes of one pattern (round edges), then Enter.")

    def on_press(self, point, event):
        if self._closed:
            return True
        view, name, _local = drawing_ui.pick_at(
            self.page, point, self.tolerance(), want_vertex=False, curve="circle"
        )
        info = drawing.edge_info(view, name) if view is not None and name else None
        if info is None or info["kind"] not in ("circle", "arc"):
            self.message.setText("Click on a round edge (a hole).")
            return True
        if self.view is not None and not drawing.same(view, self.view):
            self.message.setText("A pattern is in one view: click holes of the same view.")
            return True
        self.message.setText("")
        self.view = view
        if name in self.names:
            self.names.remove(name)
        else:
            self.names.append(name)
        self._show()
        self.say("%d picked. Click more holes, then Enter." % len(self.names))
        return True

    def _show(self):
        self.clear_overlay()
        s = drawing.scale_of(self.view) or 1.0
        for name in self.names:
            info = drawing.edge_info(self.view, name)
            if info is not None:
                centre = drawing.local_to_page(self.view, info["center"])
                self.overlay_circle(centre, info["radius"] * s + 1.0)

    def accept(self):
        if self.view is None or len(self.names) < 2:
            self.message.setText("Click at least two holes of the pattern first.")
            return False
        try:
            drawing_tools.add_mark_pattern(self.view, self.names)
        except drawing.DrawingError as exc:
            self.message.setText(str(exc))
            return False
        self.names = []
        self.clear_overlay()
        self.doc.recompute()
        return super().accept()


# ------------------------------------------------------------------ Renumber
class RenumberPanel(DrawingPanel):
    """Fusion's Renumber: type the number, click the balloon that gets it (the next click
    gets the next number); the parts list sorts to the new numbers."""

    title = "Renumber"
    icon = "dw_balloon"

    def __init__(self, page):
        super().__init__(page, "Renumber")
        if drawing.parts_list_of(page) is None:
            raise drawing.DrawingError(
                "Renumber changes the parts list's item numbers: make the parts list first "
                "(TABLES > Parts List)."
            )
        self.number = QtWidgets.QSpinBox()
        self.number.setRange(1, 9999)
        self.number.setValue(1)
        self.number.setObjectName("Fission180DrawingRenumberNumber")
        self.layout.addRow("Number", self.number)
        self.done = 0
        self.finish_layout()
        self._say()

    def _say(self):
        self.say(
            "Click the balloon that gets number %d; Enter or Esc when done." % self.number.value()
        )

    def on_press(self, point, event):
        if self._closed:
            return True
        balloon = drawing_tools.balloon_at(self.page, point)
        if balloon is None:
            self.message.setText("Click on a balloon.")
            return True
        try:
            old, new = drawing_tools.renumber(self.page, balloon, self.number.value())
        except drawing.DrawingError as exc:
            self.message.setText(str(exc))
            return True
        self.message.setText("")
        self.done += 1
        self.number.setValue(new + 1)
        self.say(
            "Balloon %d is %d now. Click the balloon that gets number %d; Enter or Esc "
            "when done." % (old, new, self.number.value())
        )
        self.schedule()
        return True

    def escape(self):
        taskui.press_dialog_button("accept")  # (Esc ends and keeps what was renumbered)


# ------------------------------------------------------------------ Align Balloons
class AlignBalloonsPanel(_PickPanel):
    """Fusion's Align Balloons: click the balloons, Enter, then click where their line
    goes: they stand on one level or one upright line."""

    title = "Align Balloons"
    icon = "dw_balloon"

    def __init__(self, page):
        super().__init__(page, "Align Balloons")
        if not drawing_tools.balloons_of(page):
            raise drawing.DrawingError(
                "There are no balloons on this sheet yet (TABLES > Parts List adds them)."
            )
        self.picked = _preselected(page, lambda o: o.TypeId == drawing.BALLOON)
        self.phase = "pick"
        self.aligned = False
        self.finish_layout()
        self._frame()
        self.say("Click the balloons to line up, then press Enter.")

    def on_press(self, point, event):
        if self._closed:
            return True
        if self.phase == "pick":
            balloon = drawing_tools.balloon_at(self.page, point)
            if balloon is None:
                self.message.setText("Click on a balloon.")
                return True
            self.message.setText("")
            self._toggle(balloon)
            self.say("%d picked. Click more, then press Enter." % len(self.picked))
            return True
        way = drawing_tools.align_balloons(self.picked, point)
        self.aligned = True
        self.phase = "done"
        self.clear_overlay()
        self.say("Lined up (%s). OK keeps it." % way)
        self.schedule()
        return True

    def on_move(self, point, event):
        if self._closed or self.phase != "place":
            return
        drawing_tools.align_balloons(self.picked, point)
        self.aligned = True
        self.schedule()

    def on_key(self, key, event):
        if key in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter) and self.phase == "pick":
            if len(self.picked) < 2:
                self.message.setText("Click at least two balloons first.")
                return True
            self.message.setText("")
            self.phase = "place"
            self.clear_overlay()
            self.say("Move to where their line goes and click.")
            return True
        return super().on_key(key, event)

    def accept(self):
        if not self.aligned:
            self.message.setText(
                "Nothing is lined up yet: click two or more balloons, press Enter, then "
                "click where their line goes."
            )
            return False
        return super().accept()


# ------------------------------------------------------------------ commands
class MoveCommand(drawing_ui._Base):
    title = "Move"
    tip = "Move views, the parts list, text or balloons by two clicks or typed distances"
    icon = "move"

    def run(self):
        drawing_ui._start(MovePanel)


class RotateCommand(drawing_ui._Base):
    title = "Rotate"
    tip = "Turn views on the sheet by an angle"
    icon = "move"

    def run(self):
        drawing_ui._start(RotatePanel)


class CenterMarkPatternCommand(drawing_ui._Base):
    title = "Center Mark Pattern"
    tip = "Centre marks on the holes of a pattern and the line or circle through them"
    icon = "dw_center_mark"

    def run(self):
        drawing_ui._start(CenterMarkPatternPanel)


class RenumberCommand(drawing_ui._Base):
    title = "Renumber"
    tip = "Give balloons other item numbers; the parts list sorts to them"
    icon = "dw_balloon"

    def run(self):
        drawing_ui._start(RenumberPanel)


class AlignBalloonsCommand(drawing_ui._Base):
    title = "Align Balloons"
    tip = "Line balloons up on one level or upright line"
    icon = "dw_balloon"

    def run(self):
        drawing_ui._start(AlignBalloonsPanel)


COMMANDS = {
    "Fission180_DrawingMove": MoveCommand,
    "Fission180_DrawingRotate": RotateCommand,
    "Fission180_DrawingCenterMarkPattern": CenterMarkPatternCommand,
    "Fission180_DrawingRenumber": RenumberCommand,
    "Fission180_DrawingAlignBalloons": AlignBalloonsCommand,
}
