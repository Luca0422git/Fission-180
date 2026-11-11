# SPDX-License-Identifier: LGPL-2.1-or-later
"""The ANIMATION TIMELINE along the bottom of the ANIMATION workspace (it takes the place of the
design timeline there): transport buttons, a ruler in seconds with the scratch zone left of 0,
the playhead, one row per component with its actions as bars (plus a View row and a Callouts
row), and the storyboards as tabs. Spec: docs/fission180/parity/animation.md.

    click or drag on the ruler / an empty row   move the playhead (0 and the scratch zone:
                                                nothing is recorded there)
    drag a bar                                  move the action in time
    drag a bar's end                            make it longer or shorter
    double-click a bar / right-click > Edit Start/End   type its times
    click a bar, Del                            delete it (Ctrl+click picks several)
    Space                                       play / pause
    a tab                                       show that storyboard; right-click: Rename,
                                                Duplicate, Reverse, Delete; drag to reorder
    +                                           New Storyboard

Times snap to tenths of a second. Every change is one undo step (animation_ui.edit).
"""

import FreeCAD as App
import FreeCADGui as Gui

from . import animation, animation_ui as ui, animation_view, commands, log, ui_icon, warn
from . import animation_core as core
from .compat import QtCore, QtGui, QtWidgets

LABEL_W = 170
SCRATCH_W = 46
RIGHT_PAD = 14
RULER_H = 22
ROW_H = 22
BAR_PAD = 4
EDGE = 6  # pixels at a bar's end that take a resize
DRAG_START = 3  # pixels a press must move to be a drag
MIN_ROWS = 3
COLOURS = {
    "transform": "#3fa9f5",
    "visibility": "#f2c440",
    "view": "#b58af5",
    "callout": "#3cc46a",
}

_dock = None


def _doc():
    return App.ActiveDocument


def _palette():
    from . import theme

    return theme.LIGHT if theme.is_light() else theme.DARK


def _later(fn, *args):
    def run():
        try:
            fn(*args)
        except core.AnimationError as exc:
            commands.tell(str(exc))
        except Exception as exc:
            warn("animation timeline: %s" % exc)

    QtCore.QTimer.singleShot(0, run)


class Canvas(QtWidgets.QWidget):
    """The ruler, the rows and the bars, drawn by hand."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Fission180AnimationCanvas")
        self.setMouseTracking(True)
        self.setFocusPolicy(QtCore.Qt.ClickFocus)
        self.board = core.new_storyboard(animation.FIRST)
        self.rows = []
        self.labels = {}
        self.playhead = 0.0
        self.span = core.DEFAULT_SPAN
        self.selected = set()
        self._drag = None  # {"id", "part", "x", "start", "end", "moved", "now": (start, end)}
        self._scrub = False
        self.setMinimumHeight(RULER_H + MIN_ROWS * ROW_H + 2)

    # -- what it shows ----------------------------------------------------------------------
    def set_board(self, board, labels, playhead):
        self.board = board
        self.rows = core.rows(board)
        self.labels = labels
        self.playhead = float(playhead)
        if self._drag is None:
            self.span = core.ruler_span(dict(board, playhead=playhead))
        ids = {a["id"] for a in board["actions"]}
        self.selected &= ids
        self.setMinimumHeight(RULER_H + max(MIN_ROWS, len(self.rows)) * ROW_H + 2)
        self.update()

    # -- geometry (also for the tests) ------------------------------------------------------
    def zero_x(self):
        return LABEL_W + SCRATCH_W

    def pixels_per_second(self):
        return max(1.0, (self.width() - self.zero_x() - RIGHT_PAD) / float(self.span))

    def time_x(self, t):
        """The x of a time on the ruler (widget pixels)."""
        return self.zero_x() + float(t) * self.pixels_per_second()

    def time_at(self, x):
        """The time under an x, snapped to the ruler's small marks (the scratch zone: 0)."""
        if x <= self.zero_x():
            return 0.0
        return core.snap((x - self.zero_x()) / self.pixels_per_second())

    def playhead_x(self):
        """Where the playhead is drawn: in the middle of the scratch zone at time 0."""
        if core.in_scratch(self.playhead):
            return LABEL_W + SCRATCH_W / 2.0
        return self.time_x(self.playhead)

    def row_y(self, row):
        """The top of a row (widget pixels), or None."""
        if row not in self.rows:
            return None
        return RULER_H + self.rows.index(row) * ROW_H

    def _span_of(self, act):
        if self._drag is not None and self._drag["id"] == act["id"] and self._drag.get("now"):
            return self._drag["now"]
        end = act.get("end")
        if end is None:  # a callout shown to the end: its bar runs to the end of the ruler
            end = max(self.span, float(act["start"]))
        return float(act["start"]), float(end)

    def bar_rect(self, action_id):
        """The rectangle of an action's bar (an instant one is a marker 10 px wide)."""
        act = core.action(self.board, action_id)
        if act is None:
            return None
        y = self.row_y(core.row_of(act))
        if y is None:
            return None
        start, end = self._span_of(act)
        x0, x1 = self.time_x(start), self.time_x(end)
        if x1 - x0 < 10:
            mid = (x0 + x1) / 2.0
            x0, x1 = mid - 5, mid + 5
        return QtCore.QRect(int(x0), int(y + BAR_PAD), int(x1 - x0), ROW_H - 2 * BAR_PAD)

    def _hit(self, pos):
        """(action id, "start" / "end" / "body") under a point, or None. The bar drawn last
        (on top) wins."""
        for act in reversed(core.ordered(self.board)):
            rect = self.bar_rect(act["id"])
            if rect is None or not rect.adjusted(-2, -2, 2, 2).contains(pos):
                continue
            instant = act.get("end") is not None and float(act["end"]) - float(act["start"]) < 1e-9
            if instant or rect.width() < 3 * EDGE:
                part = "body"
                if not instant and rect.width() >= 2 * EDGE:
                    part = "start" if pos.x() < rect.center().x() else "end"
                if act.get("end") is None and part == "end":
                    part = "body"
                return act["id"], part
            if pos.x() <= rect.left() + EDGE:
                return act["id"], "start"
            if pos.x() >= rect.right() - EDGE and act.get("end") is not None:
                return act["id"], "end"
            return act["id"], "body"
        return None

    # -- painting ---------------------------------------------------------------------------
    def paintEvent(self, event):
        try:
            self._paint()
        except Exception as exc:
            warn("animation timeline: %s" % exc)

    def _paint(self):
        colours = _palette()
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing, False)
        w, h = self.width(), self.height()
        painter.fillRect(0, 0, w, h, QtGui.QColor(colours["chrome"]))
        text = QtGui.QColor(colours["text"])
        dim = QtGui.QColor(colours["text_dim"])
        line = QtGui.QColor(colours["line"])
        zero = self.zero_x()
        # the scratch zone
        painter.fillRect(LABEL_W, 0, SCRATCH_W, h, QtGui.QColor(colours["header"]))
        hatch = QtGui.QBrush(line, QtCore.Qt.BDiagPattern)
        painter.fillRect(LABEL_W, RULER_H, SCRATCH_W, h - RULER_H, hatch)
        icon = ui_icon("anim_scratch")
        if icon is not None and not icon.isNull():
            icon.paint(painter, QtCore.QRect(LABEL_W + (SCRATCH_W - 16) // 2, 3, 16, 16))
        # rows
        for index, row in enumerate(self.rows):
            y = RULER_H + index * ROW_H
            if index % 2:
                painter.fillRect(0, y, w, ROW_H, QtGui.QColor(colours["alternate"]))
            painter.setPen(text)
            painter.drawText(
                QtCore.QRect(8, y, LABEL_W - 12, ROW_H),
                int(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft),
                painter.fontMetrics().elidedText(
                    self.labels.get(row, row), QtCore.Qt.ElideRight, LABEL_W - 14
                ),
            )
        if not self.rows:
            painter.setPen(dim)
            painter.drawText(
                QtCore.QRect(zero + 10, RULER_H, w - zero - 20, ROW_H * 2),
                int(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft),
                "Drag the playhead past 0, then transform or explode components: each change "
                "becomes a bar here.",
            )
        # the ruler
        painter.setPen(line)
        painter.drawLine(0, RULER_H, w, RULER_H)
        painter.drawLine(LABEL_W, 0, LABEL_W, h)
        painter.drawLine(zero, 0, zero, h)
        pps = self.pixels_per_second()
        step = 1
        for step in (1, 2, 5, 10, 20, 30, 60, 120, 300, 600):
            if step * pps >= 34:
                break
        second = 0
        while second <= self.span + 1e-9:
            x = int(self.time_x(second))
            painter.setPen(line)
            painter.drawLine(x, RULER_H - 7, x, RULER_H)
            if second % step == 0:
                painter.setPen(dim)
                painter.drawText(x + 3, RULER_H - 8, "%d" % second)
                painter.setPen(QtGui.QColor(colours["header"]))
                painter.drawLine(x, RULER_H + 1, x, h)
            second += 1
        if pps >= 40:
            painter.setPen(line)
            tenth = 1
            while tenth < self.span * 10:
                if tenth % 10:
                    x = int(self.time_x(tenth / 10.0))
                    painter.drawLine(x, RULER_H - (5 if tenth % 5 == 0 else 3), x, RULER_H)
                tenth += 1
        # bars
        painter.setRenderHint(QtGui.QPainter.Antialiasing, True)
        for act in core.ordered(self.board):
            rect = self.bar_rect(act["id"])
            if rect is None:
                continue
            colour = QtGui.QColor(COLOURS[act["kind"]])
            picked = act["id"] in self.selected
            painter.setPen(
                QtGui.QPen(
                    QtGui.QColor(colours["bright"]) if picked else colour.darker(140),
                    2 if picked else 1,
                )
            )
            painter.setBrush(colour if picked else colour.darker(115))
            instant = act.get("end") is not None and float(act["end"]) - float(act["start"]) < 1e-9
            if instant:
                c = rect.center()
                r = rect.height() / 2.0
                painter.drawPolygon(
                    QtGui.QPolygonF(
                        [
                            QtCore.QPointF(c.x(), c.y() - r),
                            QtCore.QPointF(c.x() + r, c.y()),
                            QtCore.QPointF(c.x(), c.y() + r),
                            QtCore.QPointF(c.x() - r, c.y()),
                        ]
                    )
                )
            else:
                painter.drawRoundedRect(rect, 3, 3)
                if rect.width() > 46:
                    painter.setPen(QtGui.QColor("#10151c"))
                    painter.drawText(
                        rect.adjusted(5, 0, -3, 0),
                        int(QtCore.Qt.AlignVCenter | QtCore.Qt.AlignLeft),
                        painter.fontMetrics().elidedText(
                            self._bar_text(act), QtCore.Qt.ElideRight, rect.width() - 8
                        ),
                    )
        # the playhead
        x = int(self.playhead_x())
        accent = QtGui.QColor("#ff5c5c")
        painter.setPen(QtGui.QPen(accent, 2))
        painter.drawLine(x, 4, x, h)
        painter.setBrush(accent)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawPolygon(
            QtGui.QPolygonF(
                [
                    QtCore.QPointF(x - 6, 2),
                    QtCore.QPointF(x + 6, 2),
                    QtCore.QPointF(x + 6, 9),
                    QtCore.QPointF(x, 15),
                    QtCore.QPointF(x - 6, 9),
                ]
            )
        )
        painter.end()

    def _bar_text(self, act):
        if act["kind"] == "callout":
            return act.get("text", "")
        return core.title(act)

    # -- the mouse --------------------------------------------------------------------------
    def mousePressEvent(self, event):
        try:
            self._press(event)
        except Exception as exc:
            warn("animation timeline: %s" % exc)

    def _press(self, event):
        pos = event.pos()
        self.setFocus()
        if event.button() != QtCore.Qt.LeftButton:
            return
        ui.pause()
        hit = self._hit(pos) if pos.y() > RULER_H else None
        if hit is not None:
            action_id, part = hit
            act = core.action(self.board, action_id)
            if event.modifiers() & QtCore.Qt.ControlModifier:
                self.selected ^= {action_id}
            elif action_id not in self.selected:
                self.selected = {action_id}
            start, end = float(act["start"]), act.get("end")
            self._drag = {
                "id": action_id,
                "part": part,
                "x": pos.x(),
                "start": start,
                "end": None if end is None else float(end),
                "moved": False,
                "now": None,
            }
            self.update()
            return
        self.selected = set()
        if pos.x() >= LABEL_W:
            self._scrub = True
            ui.set_playhead(self.time_at(pos.x()))
        self.update()

    def mouseMoveEvent(self, event):
        try:
            self._move(event)
        except Exception as exc:
            warn("animation timeline: %s" % exc)

    def _move(self, event):
        pos = event.pos()
        if self._scrub:
            ui.set_playhead(self.time_at(pos.x()))
            return
        drag = self._drag
        if drag is None:
            hit = self._hit(pos) if pos.y() > RULER_H else None
            if hit is not None and hit[1] in ("start", "end"):
                self.setCursor(QtCore.Qt.SizeHorCursor)
            elif hit is not None:
                self.setCursor(QtCore.Qt.OpenHandCursor)
            else:
                self.unsetCursor()
            self._tip(hit)
            return
        if not drag["moved"] and abs(pos.x() - drag["x"]) < DRAG_START:
            return
        drag["moved"] = True
        drag["now"] = self._dragged_span(drag, pos.x())
        self._preview_drag()
        self.update()

    def _dragged_span(self, drag, x):
        """The (start, end) a drag gives its action with the mouse at x."""
        shift = (x - drag["x"]) / self.pixels_per_second()
        act = core.action(self.board, drag["id"])
        least = core.min_length(act)
        start, end = drag["start"], drag["end"]
        if drag["part"] == "body":
            new = core.snap(max(0.0, start + shift))
            return new, (None if end is None else new + (end - start))
        if drag["part"] == "start":
            limit = start if end is None else end - least
            new = core.snap(max(0.0, start + shift))
            return (min(new, limit) if end is not None else new), end
        new = core.snap(max(start + least, end + shift))
        return start, max(new, start + least)

    def _preview_drag(self):
        """The 3D view follows the bar being dragged."""
        drag = self._drag
        doc = _doc()
        if drag is None or drag["now"] is None or doc is None:
            return
        import copy

        temp = copy.deepcopy(self.board)
        act = core.action(temp, drag["id"])
        act["start"], act["end"] = drag["now"]
        animation_view.show(doc, temp, self.playhead)

    def mouseReleaseEvent(self, event):
        try:
            self._release(event)
        except Exception as exc:
            warn("animation timeline: %s" % exc)

    def _release(self, event):
        if event.button() != QtCore.Qt.LeftButton:
            return
        self._scrub = False
        drag, self._drag = self._drag, None
        if drag is None:
            return
        if not drag["moved"] or drag["now"] is None:
            self.update()
            return
        start, end = drag["now"]
        if abs(start - drag["start"]) < 1e-9 and end == drag["end"]:
            ui.refresh_view()
            self.update()
            return
        action_id = drag["id"]
        name = "Move Action" if drag["part"] == "body" else "Change Action Length"

        def change(board):
            act = core.action(board, action_id)
            if act is None:
                raise core.AnimationError("That action is gone.")
            act["start"], act["end"] = start, end
            return act

        _later(self._commit, name, change, start, end)

    def _commit(self, name, change, start, end):
        if ui.edit(name, change) is not None:
            ui.note(
                "%s: %s to %s."
                % (
                    name,
                    core.time_text(start),
                    "the end" if end is None else core.time_text(end),
                )
            )

    def mouseDoubleClickEvent(self, event):
        try:
            hit = self._hit(event.pos()) if event.pos().y() > RULER_H else None
            if hit is not None and event.button() == QtCore.Qt.LeftButton:
                self._drag = None
                _later(self._edit, hit[0])
        except Exception as exc:
            warn("animation timeline: %s" % exc)

    def _edit(self, action_id):
        from . import animation_panels

        animation_panels.open_edit_action(_doc(), action_id)

    def _tip(self, hit):
        if hit is None:
            self.setToolTip("")
            return
        act = core.action(self.board, hit[0])
        if act is None:
            return
        end = act.get("end")
        where = self.labels.get(core.row_of(act), "")
        self.setToolTip(
            "%s%s: %s to %s. Drag to move, drag an end to change its length, double-click to "
            "type the times."
            % (
                core.title(act),
                (" of " + where) if act["kind"] in ("transform", "visibility") else "",
                core.time_text(act["start"]),
                "the end" if end is None else core.time_text(end),
            )
        )

    def contextMenuEvent(self, event):
        try:
            self._menu(event)
        except Exception as exc:
            warn("animation timeline: %s" % exc)

    def _menu(self, event):
        pos = event.pos()
        hit = self._hit(pos) if pos.y() > RULER_H else None
        menu = QtWidgets.QMenu(self)
        menu.setObjectName("Fission180AnimationMenu")
        handlers = {}
        if hit is not None:
            if hit[0] not in self.selected:
                self.selected = {hit[0]}
                self.update()
            act = core.action(self.board, hit[0])
            edit = "Edit Action" if act["kind"] == "visibility" else "Edit Start/End"
            handlers[menu.addAction(edit)] = lambda: self._edit(hit[0])
            menu.addSeparator()
            many = len(self.selected) > 1
            handlers[menu.addAction(ui_icon("delete"), "Delete Actions" if many else "Delete")] = (
                self.delete_selected
            )
        elif pos.x() < LABEL_W and pos.y() > RULER_H:
            index = (pos.y() - RULER_H) // ROW_H
            row = self.rows[index] if 0 <= index < len(self.rows) else None
            if row is None:
                return
            if not row.startswith("__"):
                trail = menu.addAction("Trail Line Visibility")
                trail.setCheckable(True)
                trail.setChecked(row in self.board.get("trails", []))
                handlers[trail] = lambda: self._toggle_trail(row)
            handlers[menu.addAction(ui_icon("delete"), "Delete Actions of This Row")] = (
                lambda: self._delete_row(row)
            )
        else:
            return
        chosen = menu.exec_(event.globalPos())
        if chosen in handlers:
            _later(handlers[chosen])

    def _toggle_trail(self, row):
        def change(board):
            trails = board.setdefault("trails", [])
            if row in trails:
                trails.remove(row)
            else:
                trails.append(row)
            return trails

        ui.edit("Trail Line Visibility", change)

    def _delete_row(self, row):
        ids = [a["id"] for a in self.board["actions"] if core.row_of(a) == row]
        self._delete(ids)

    def delete_selected(self):
        self._delete(sorted(self.selected))

    def _delete(self, ids):
        if not ids:
            commands.tell("Click an action's bar first, then press Del.")
            return
        if not commands.finish_open_dialog():
            return
        count = ui.edit(
            "Delete Action" if len(ids) == 1 else "Delete Actions",
            lambda board: core.delete_actions(board, ids),
        )
        if count:
            self.selected = set()
            ui.note("%d action%s deleted." % (count, "" if count == 1 else "s"))

    def keyPressEvent(self, event):
        try:
            if event.key() in (QtCore.Qt.Key_Delete, QtCore.Qt.Key_Backspace):
                if self.selected:
                    _later(self.delete_selected)
                else:
                    commands.tell("Click an action's bar first, then press Del.")
                event.accept()
                return
            if event.key() == QtCore.Qt.Key_Space:
                _later(ui.toggle_play)
                event.accept()
                return
            if event.key() == QtCore.Qt.Key_Home:
                _later(ui.to_start)
                event.accept()
                return
            if event.key() == QtCore.Qt.Key_End:
                _later(ui.to_end)
                event.accept()
                return
        except Exception as exc:
            warn("animation timeline: %s" % exc)
        super().keyPressEvent(event)


class TimelinePanel(QtWidgets.QWidget):
    """Transport buttons, the canvas and the storyboards' tabs."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("Fission180AnimationTimeline")
        self.setAttribute(QtCore.Qt.WA_StyledBackground, True)
        self._filling = False
        self._editor = None
        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(6, 3, 6, 3)
        outer.setSpacing(2)

        top = QtWidgets.QHBoxLayout()
        top.setSpacing(2)
        self.buttons = {}
        for key, icon, tip, fn in (
            ("start", "anim_to_start", "Go to the start of the storyboard", ui.to_start),
            ("previous", "anim_previous", "Previous action", lambda: ui.step(False)),
            ("play", "anim_play", "Play / pause (Space)", ui.toggle_play),
            ("next", "anim_next", "Next action", lambda: ui.step(True)),
            ("end", "anim_to_end", "Go to the end of the storyboard", ui.to_end),
        ):
            button = self._tool(icon, tip, fn)
            button.setObjectName("Fission180Animation_" + key)
            self.buttons[key] = button
            top.addWidget(button)
        self.loop = self._tool("anim_loop", "Loop: play again from the start at the end", None)
        self.loop.setObjectName("Fission180Animation_loop")
        self.loop.setCheckable(True)
        self.loop.toggled.connect(lambda on: ui.set_loop(on))
        top.addWidget(self.loop)
        top.addSpacing(10)
        self.time = QtWidgets.QLabel("0.0 s")
        self.time.setObjectName("Fission180Animation_time")
        self.time.setMinimumWidth(150)
        top.addWidget(self.time)
        self.view_state = QtWidgets.QLabel("")
        self.view_state.setObjectName("Fission180Animation_view")
        top.addWidget(self.view_state)
        top.addSpacing(10)
        self.note = QtWidgets.QLabel("")
        self.note.setObjectName("Fission180Animation_note")
        self.note.setStyleSheet("color: #c3cad4;")
        self.note.setTextInteractionFlags(QtCore.Qt.NoTextInteraction)
        top.addWidget(self.note, 1)
        title = QtWidgets.QLabel("ANIMATION TIMELINE")
        title.setStyleSheet("color: #9aa4b1; font-weight: bold;")
        top.addWidget(title)
        outer.addLayout(top)

        self.canvas = Canvas()
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QtWidgets.QFrame.NoFrame)
        self.scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.scroll.setWidget(self.canvas)
        self.scroll.setFixedHeight(RULER_H + 5 * ROW_H + 4)
        outer.addWidget(self.scroll)

        bottom = QtWidgets.QHBoxLayout()
        bottom.setSpacing(4)
        self.tabs = QtWidgets.QTabBar()
        self.tabs.setObjectName("Fission180AnimationStoryboards")
        self.tabs.setExpanding(False)
        self.tabs.setMovable(True)
        self.tabs.setDrawBase(False)
        self.tabs.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tabs.customContextMenuRequested.connect(self._tab_menu)
        self.tabs.currentChanged.connect(self._tab_changed)
        self.tabs.tabMoved.connect(self._tab_moved)
        self.tabs.tabBarDoubleClicked.connect(self._rename_tab)
        bottom.addWidget(self.tabs)
        self.add = self._tool("anim_storyboard", "New Storyboard", ui.new_storyboard_command)
        self.add.setObjectName("Fission180Animation_new")
        bottom.addWidget(self.add)
        bottom.addStretch(1)
        outer.addLayout(bottom)

    def _tool(self, icon, tip, fn):
        button = QtWidgets.QToolButton()
        button.setIcon(ui_icon(icon))
        button.setIconSize(QtCore.QSize(18, 18))
        button.setToolTip(tip)
        button.setAutoRaise(True)
        button.setFocusPolicy(QtCore.Qt.NoFocus)
        if fn is not None:
            button.clicked.connect(lambda _checked=False, fn=fn: _later(fn))
        return button

    # -- following the workspace ------------------------------------------------------------
    def refresh(self):
        doc = _doc()
        if doc is None or not ui.in_workspace(doc):
            return
        board = ui.board(doc)
        labels = {core.VIEW_ROW: "View", core.CALLOUT_ROW: "Callouts"}
        for name in core.rows(board):
            if not name.startswith("__"):
                labels[name] = animation.label(doc, name)
        at = ui.playhead(doc)
        self.canvas.set_board(board, labels, at)
        length = core.duration(board)
        where = "scratch zone" if core.in_scratch(at) else core.time_text(at)
        self.time.setText("%s  /  %s" % (where, core.time_text(length)))
        self.view_state.setText("View: recording" if ui.recording() else "View: off")
        self.view_state.setStyleSheet("color: #ef6f6c;" if ui.recording() else "color: #e8c460;")
        self.note.setText(ui.note())
        self.buttons["play"].setIcon(ui_icon("anim_pause" if ui.playing() else "anim_play"))
        if self.loop.isChecked() != bool(ui.STATE["loop"]):
            self.loop.blockSignals(True)
            self.loop.setChecked(bool(ui.STATE["loop"]))
            self.loop.blockSignals(False)
        self._fill_tabs(doc)

    def _fill_tabs(self, doc):
        names = ui.storyboard_names(doc)
        current = ui.current(doc)
        have = [self.tabs.tabText(i) for i in range(self.tabs.count())]
        self._filling = True
        try:
            if have != names:
                while self.tabs.count():
                    self.tabs.removeTab(0)
                for name in names:
                    self.tabs.addTab(name)
            if current in names and self.tabs.currentIndex() != names.index(current):
                self.tabs.setCurrentIndex(names.index(current))
        finally:
            self._filling = False

    def tab_names(self):
        return [self.tabs.tabText(i) for i in range(self.tabs.count())]

    def _tab_changed(self, index):
        if self._filling or index < 0:
            return
        name = self.tabs.tabText(index)
        _later(ui.set_current, name)

    def _tab_moved(self, source, target):
        if self._filling:
            return
        name = self.tabs.tabText(target)
        doc = _doc()
        if doc is None:
            return
        if name not in animation.storyboards(doc):
            return

        def move():
            ui.call(animation.move_storyboard, doc, name, target)

        _later(move)

    def _exists(self, doc, name):
        if name in animation.storyboards(doc):
            return True
        commands.tell(
            "%s is still empty: record something on it first (it is made in the design "
            "with its first action)." % name
        )
        return False

    def _tab_menu(self, pos):
        try:
            index = self.tabs.tabAt(pos)
            doc = _doc()
            if doc is None:
                return
            menu = QtWidgets.QMenu(self)
            menu.setObjectName("Fission180AnimationTabMenu")
            handlers = {}
            if index >= 0:
                name = self.tabs.tabText(index)
                handlers[menu.addAction("Rename")] = lambda: self._rename_tab(index)
                handlers[menu.addAction("Duplicate")] = lambda: self._duplicate(name)
                handlers[menu.addAction("Reverse")] = lambda: self._reverse(name)
                menu.addSeparator()
                handlers[menu.addAction(ui_icon("delete"), "Delete")] = lambda: self._delete(name)
                menu.addSeparator()
            handlers[menu.addAction("New Storyboard")] = ui.new_storyboard_command
            chosen = menu.exec_(self.tabs.mapToGlobal(pos))
            if chosen in handlers:
                _later(handlers[chosen])
        except Exception as exc:
            warn("animation timeline: %s" % exc)

    def _duplicate(self, name):
        doc = _doc()
        if not self._exists(doc, name) or not commands.finish_open_dialog():
            return
        made = ui.call(animation.duplicate_storyboard, doc, name)
        if made:
            ui.set_current(made)
            ui.note("%s is a copy of %s." % (made, name))

    def _reverse(self, name):
        doc = _doc()
        if not self._exists(doc, name) or not commands.finish_open_dialog():
            return
        if animation.duration(doc, name) <= 0:
            commands.tell("%s has no actions to reverse yet." % name)
            return
        if ui.call(animation.reverse_storyboard, doc, name):
            ui.set_playhead(0.0)
            ui.note("%s now plays backwards." % name)

    def _delete(self, name):
        doc = _doc()
        if not self._exists(doc, name) or not commands.finish_open_dialog():
            return
        ui.pause()
        ui.call(animation.delete_storyboard, doc, name)
        ui.STATE["current"].pop(doc.Name, None)
        ui.refresh()
        ui.note("%s deleted (Ctrl+Z brings it back)." % name)

    def _rename_tab(self, index):
        try:
            if index < 0 or (self._editor is not None and self._editor.is_open()):
                return
            from . import inline_edit

            name = self.tabs.tabText(index)
            rect = self.tabs.tabRect(index)
            self._editor = inline_edit.InlineEditor(
                self.tabs,
                rect,
                name,
                lambda text, old=name: _later(self._renamed, old, text),
                name="Fission180AnimationRename",
            )
        except Exception as exc:
            warn("animation timeline: %s" % exc)

    def _renamed(self, old, text):
        doc = _doc()
        text = (text or "").strip()
        if doc is None or not text or text == old:
            return
        if not commands.finish_open_dialog():
            return
        at = ui.playhead(doc)

        def rename():
            if old not in animation.storyboards(doc):
                # an empty first storyboard: made in the design under its new name
                return animation.new_storyboard(doc, text, step="Rename Storyboard")
            return animation.rename_storyboard(doc, old, text)

        made = ui.call(rename)
        if made:
            ui.STATE["current"][doc.Name] = made
            ui.STATE["playheads"][(doc.Name, made)] = at
            ui.refresh()
            log("storyboard %s renamed %s" % (old, made))

    def delete_current(self):
        doc = _doc()
        if doc is not None:
            self._delete(ui.current(doc))


# -- the dock ------------------------------------------------------------------------------------
def _ensure_dock():
    global _dock
    if _dock is None:
        main = Gui.getMainWindow()
        _dock = QtWidgets.QDockWidget("Animation Timeline", main)
        _dock.setObjectName("Fission180AnimationDock")
        _dock.setTitleBarWidget(QtWidgets.QWidget())  # no title bar, like the design timeline
        _dock.setFeatures(QtWidgets.QDockWidget.NoDockWidgetFeatures)
        _dock.setWidget(TimelinePanel())
        main.addDockWidget(QtCore.Qt.BottomDockWidgetArea, _dock)
        _dock.hide()
    return _dock


def widget():
    return _dock.widget() if _dock is not None else None


def canvas():
    panel = widget()
    return panel.canvas if panel is not None else None


def show():
    dock = _ensure_dock()
    dock.show()
    refresh()


def hide():
    if _dock is not None:
        _dock.hide()


def visible():
    return _dock is not None and _dock.isVisible()


def refresh():
    try:
        panel = widget()
        if panel is not None and _dock.isVisible():
            panel.refresh()
    except RuntimeError:
        pass  # (the window is closing)
    except Exception as exc:
        warn("animation timeline: %s" % exc)
