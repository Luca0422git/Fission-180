# SPDX-License-Identifier: LGPL-2.1-or-later
"""Fusion's Simulate (MANUFACTURE > ACTIONS > Simulate): the tool follows the toolpaths of a
setup (or of the picked operations) and cuts the stock away.

The player: Play / Pause, Next Move, To End, Restart, a speed slider and a position slider
(drag it to any moment; back in time too). Beside it the statistics: the machining time and
how much of it has played, the cutting and rapid distances, the volume of stock removed, and
every rapid move that went into material (a crash on a real machine), listed with its
operation and the line of its toolpath. The stock is Fission 180's own height-field model
(manufacture_sim.py); the holder is not checked. Toolpaths that are missing or out of date
are generated first. Closing the player puts the setup's see-through stock back.
"""

import time

import FreeCADGui as Gui

from . import commands, log, warn
from . import manufacture_core as core
from .compat import QtCore, QtWidgets
from .simulation_dialogs import FocusBack

OPEN = {"player": None}
PLAY_SECONDS = 20.0  # at speed 1 the whole program plays in about this long
TICK_MS = 60


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


class Player(FocusBack, QtWidgets.QDialog):
    def __init__(self, doc, setup, playback, labels):
        super().__init__(Gui.getMainWindow())
        self.setObjectName("Fission180CamSimulate")
        self.setWindowTitle("Simulate: %s" % setup.Label)
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.Tool)
        self.doc = doc
        self.setup = setup
        self.playback = playback
        self.frame = _cam().frame(setup)
        self.playing = False
        self.last_tick = None
        self.dragging = False
        layout = QtWidgets.QVBoxLayout(self)
        what = QtWidgets.QLabel("Operations: " + ", ".join(labels))
        what.setWordWrap(True)
        layout.addWidget(what)
        row = QtWidgets.QHBoxLayout()
        layout.addLayout(row)
        self.buttons = {}
        for key, text, tip, slot in (
            ("restart", "Restart", "Back to the start: the whole stock again", self.restart),
            ("play", "Play", "Play or pause", self.toggle),
            ("step", "Next Move", "Play one move of the tool", self.step),
            ("end", "To End", "Cut everything at once", self.to_end),
            ("close", "Close", "Close the player: the see-through stock is back", self.reject),
        ):
            button = QtWidgets.QPushButton(text)
            button.setObjectName("Fission180CamSim_" + key)
            button.setToolTip(tip)
            button.clicked.connect(slot)
            row.addWidget(button)
            self.buttons[key] = button
        form = QtWidgets.QFormLayout()
        layout.addLayout(form)
        self.position = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.position.setObjectName("Fission180CamSim_position")
        self.position.setRange(0, 1000)
        self.position.sliderPressed.connect(self._drag_start)
        self.position.sliderReleased.connect(self._drag_end)
        self.position.valueChanged.connect(self._moved)
        form.addRow("Position", self.position)
        self.speed = QtWidgets.QSlider(QtCore.Qt.Horizontal)
        self.speed.setObjectName("Fission180CamSim_speed")
        self.speed.setRange(1, 100)
        self.speed.setValue(10)
        self.speed.setToolTip("Left: slow; right: fast")
        form.addRow("Speed", self.speed)
        self.stats = QtWidgets.QLabel("")
        self.stats.setObjectName("Fission180CamSim_stats")
        self.stats.setWordWrap(True)
        layout.addWidget(self.stats)
        self.collisions = QtWidgets.QLabel("")
        self.collisions.setObjectName("Fission180CamSim_collisions")
        self.collisions.setWordWrap(True)
        layout.addWidget(self.collisions)
        note = QtWidgets.QLabel(core.SAFETY_NOTE)
        note.setWordWrap(True)
        note.setStyleSheet("color: #b8c4d0;")
        layout.addWidget(note)
        self.timer = QtCore.QTimer(self)
        self.timer.setInterval(TICK_MS)
        self.timer.timeout.connect(self._tick)
        self.setMinimumWidth(430)
        self.show_now()

    # -- playing ---------------------------------------------------------------------------
    def toggle(self):
        if not self.playing and self.playback.done():
            self.playback.reset()  # (Play at the end starts over)
        self.playing = not self.playing
        self.buttons["play"].setText("Pause" if self.playing else "Play")
        self.last_tick = time.time()
        if self.playing:
            self.timer.start()
        else:
            self.timer.stop()

    def pause(self):
        if self.playing:
            self.toggle()

    def restart(self):
        self.pause()
        self.playback.reset()
        self.show_now()

    def step(self):
        self.pause()
        self.playback.step_moves(1)
        self.show_now()

    def to_end(self):
        self.pause()
        self.playback.finish()
        self.show_now()

    def seek(self, fraction):
        """Jump to a moment of the program (0 = the start, 1 = the end)."""
        self.pause()
        self.playback.seek(max(0.0, min(1.0, float(fraction))) * self.playback.total)
        self.show_now()

    def _rate(self):
        """Machining seconds played per real second."""
        factor = 10.0 ** ((self.speed.value() - 10) / 30.0)  # 1 at the default position
        return max(self.playback.total / PLAY_SECONDS, 1e-6) * factor

    def _tick(self):
        try:
            now = time.time()
            passed = min(now - (self.last_tick or now), 0.5)
            self.last_tick = now
            self.playback.advance(passed * self._rate())
            self.show_now()
            if self.playback.done():
                self.pause()
        except Exception as exc:
            self.timer.stop()
            warn("simulate: %s" % exc)

    def _drag_start(self):
        self.dragging = True
        self.pause()

    def _drag_end(self):
        self.dragging = False
        self.seek(self.position.value() / 1000.0)

    def _moved(self, value):
        if self.dragging:
            self.playback.seek(value / 1000.0 * self.playback.total)
            self.show_now(slider=False)

    # -- showing ---------------------------------------------------------------------------
    def show_now(self, slider=True):
        from . import manufacture_view

        play = self.playback
        try:
            manufacture_view.drop("setup")
            manufacture_view.drop("paths")
            manufacture_view.show_simulation(
                self.doc, self.frame, play.stock, play.tool(), play.position
            )
        except Exception as exc:
            warn("simulate: %s" % exc)
        if slider and not self.dragging:
            self.position.blockSignals(True)
            self.position.setValue(int(round(1000 * play.progress())))
            self.position.blockSignals(False)
        s = play.statistics()
        op = play.operations[min(play.operation, len(play.operations) - 1)]
        self.stats.setText(
            "Machining time %s (played %s); now: %s\n"
            "Cutting distance %s mm, rapid distance %s mm\n"
            "Stock removed %s cm3 of %s cm3"
            % (
                core.time_text(s["time_s"]),
                core.time_text(s["played_s"]),
                op.get("label", ""),
                core.fmt(s["cut_length"], 0),
                core.fmt(s["rapid_length"], 0),
                core.fmt(s["removed"] / 1000.0, 2),
                core.fmt(s["start_volume"] / 1000.0, 2),
            )
        )
        if play.collisions:
            first = play.collisions[0]
            self.collisions.setStyleSheet("color: #ff8a80;")
            self.collisions.setText(
                "%d rapid move%s went into the stock (a crash on a machine). First: %s, toolpath line %s, "
                "%s mm deep at (%s)."
                % (
                    len(play.collisions),
                    "" if len(play.collisions) == 1 else "s",
                    first["label"],
                    first["line"],
                    core.fmt(first["depth"], 2),
                    ", ".join(core.fmt(c, 1) for c in first["point"]),
                )
            )
        else:
            self.collisions.setStyleSheet("color: #7bd88f;")
            self.collisions.setText(
                "No rapid move into the stock so far."
                if not play.done()
                else "No rapid move went into the stock."
            )

    def closeEvent(self, event):
        self._put_back()
        super().closeEvent(event)

    def reject(self):
        self._put_back()
        super().reject()

    def _put_back(self):
        try:
            self.timer.stop()
            from . import manufacture_view

            manufacture_view.drop("simulation")
            if OPEN["player"] is self:
                OPEN["player"] = None
            _ui().refresh_view(True)
        except Exception as exc:
            warn("simulate: %s" % exc)


def open_simulate(doc, setup=None, ops=None):
    """Simulate `setup` (default: the active one) or `ops` of it."""
    if not commands.finish_open_dialog():
        return None
    cam = _cam()
    ui = _ui()
    setup = setup or ui.active_setup(doc)
    if setup is None:
        commands.tell("There is nothing to simulate yet: make a setup and an operation first.")
        return None
    if ops is None:  # the rows picked in the browser, else the whole setup
        try:
            from . import manufacture_browser

            picked = manufacture_browser.picked_ops(doc) or []
            ops = [o for o in picked if cam.setup_of(o) is setup] or None
        except Exception:
            ops = None
    chosen = cam.postable(setup, ops)
    if not chosen:
        commands.tell(
            "%s has no operation to simulate: add one (2D, 3D or DRILLING), or unsuppress them."
            % setup.Label
        )
        return None
    todo = [o for o in chosen if cam.state(o, setup) != "valid"]
    if todo:
        ui.generate(todo)
        if not ui.wait_generated():
            commands.tell("The toolpaths are still being generated: try again in a moment.")
            return None
        failed = [o for o in todo if cam.state(o, setup) != "valid"]
        if failed:
            commands.tell(
                "%s has no toolpath (%s): fix it first, or suppress it."
                % (
                    failed[0].Label,
                    cam.result(failed[0]).get("error") or "it could not be generated",
                )
            )
            return None
    close()
    try:
        playback = cam.playback(setup, chosen)
    except core.CamError as exc:
        commands.tell(str(exc))
        return None
    if playback.total <= 0:
        commands.tell("These toolpaths have no moves to play.")
        return None
    player = Player(doc, setup, playback, [o.Label for o in chosen])
    OPEN["player"] = player
    player.show()
    try:  # at the bottom left of the 3D view, off the part
        main = Gui.getMainWindow()
        corner = main.mapToGlobal(QtCore.QPoint(340, main.height() - player.height() - 70))
        player.move(corner)
    except Exception:
        pass
    log(
        "simulate %s: %d operation(s), %s"
        % (setup.Label, len(chosen), core.time_text(playback.total))
    )
    return player


def player():
    found = OPEN["player"]
    return found if found is not None and _alive(found) and found.isVisible() else None


def close():
    found = OPEN["player"]
    OPEN["player"] = None
    if found is not None and _alive(found):
        try:
            found.reject()
        except Exception:
            pass


COMMANDS = {}
