# SPDX-License-Identifier: LGPL-2.1-or-later
"""Sketch commands that work on curves you pick first: Circular Pattern, Rectangular
Pattern. (Mirror has Fusion's MIRROR panel: sketch_mirror_tool.py; Sketch Scale and Move/Copy
have theirs: sketch_scale_tool.py, sketch_move_tool.py, commands in sketch_*_ui.py.
Circular and Rectangular Pattern are Fission 180 tools with a panel and drag handles like the
body patterns' since 2026-11-09: sketch_pattern_tool.py; their commands are here.)

FreeCAD's versions do nothing when nothing is selected, and its Rectangular Pattern
opens a pop-up asking for rows and columns. Fission 180's pattern tools start anyway and
take the curves in their own panel (click, or a box). The waiting below (_Waiter,
_PickCommand: click the curves, Enter, then a FreeCAD tool) has no command left using it;
stop_waiting / on_enter / settle_box / close_box stay for sketch_mode's calls.
"""

import FreeCAD as App
import FreeCADGui as Gui

from . import commands, log, sketch_mode, theme, ui_icon_path, warn
from .compat import QtCore, QtWidgets

_state = {"waiter": None, "box": None}


def selected_curves(sketch):
    from .sketch_tools_ui import selected_curves as picked

    return picked(sketch)


class _Waiter:
    """Waits for curves to be clicked; Enter (or the command again) continues."""

    def __init__(self, sketch, title, run):
        stop_waiting()
        _state["waiter"] = self
        self.sketch = sketch
        self.title = title
        self.run = run
        self._timer = QtCore.QTimer()
        self._timer.setInterval(250)
        self._timer.timeout.connect(self._check)
        self._timer.start()
        commands.tell("%s: click the curves, then press Enter." % title)
        log("%s: click the curves, then press Enter" % title)

    def _check(self):
        if sketch_mode.editing_sketch() is not self.sketch:
            self.stop()

    def confirm(self):
        ids = selected_curves(self.sketch)
        if not ids:
            commands.tell("%s: click at least one curve first." % self.title)
            return
        self.stop()
        self.run(self.sketch, ids)

    def stop(self):
        try:
            self._timer.stop()
        except Exception:
            pass
        if _state["waiter"] is self:
            _state["waiter"] = None


def stop_waiting():
    waiter = _state["waiter"]
    if waiter is not None:
        waiter.stop()


def on_enter():
    """Enter pressed on the 3D view while sketching: continue a waiting command."""
    waiter = _state["waiter"]
    if waiter is None:
        return False
    try:
        waiter.confirm()
    except Exception as exc:
        warn("%s failed: %s" % (waiter.title, exc))
    return True


class _PickCommand:
    title = ""
    tip = ""
    icon = ""
    freecad = ""  # FreeCAD's command that continues with the picked curves

    def GetResources(self):
        res = {"MenuText": self.title, "ToolTip": self.tip}
        if self.icon:
            res["Pixmap"] = ui_icon_path(self.icon)
        return res

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        try:
            session = sketch_mode.current()
            sketch = sketch_mode.editing_sketch()
            if sketch is None:
                if session is not None:
                    session.stop_tool()
                commands.tell(
                    "%s works inside a sketch: click Create Sketch (or edit a sketch) first."
                    % self.title
                )
                return
            waiter = _state["waiter"]
            if waiter is not None and waiter.title == self.title:
                waiter.confirm()  # the command clicked again: go on
                return
            if session is not None:
                session.give_way()  # the running tool ends, Fission 180's or FreeCAD's
            if not sketch.Geometry:
                commands.tell("%s: draw some curves first." % self.title)
                return
            ids = selected_curves(sketch)
            if ids:
                self.go(sketch, ids)
            else:
                _Waiter(sketch, self.title, self.go)
        except Exception as exc:
            warn("%s failed: %s" % (self.title, exc))

    def go(self, sketch, ids):
        _select(sketch, ids)
        Gui.runCommand(self.freecad)


def _select(sketch, ids):
    Gui.Selection.clearSelection()
    for index in ids:
        Gui.Selection.addSelection(sketch.Document.Name, sketch.Name, "Edge%d" % (index + 1))


class _SketchPatternCommand:
    """SKETCH > CREATE > Rectangular / Circular Pattern: Fission 180's pattern tool with its
    panel (sketch_pattern_tool.py). The command again while it runs ends it without making
    anything, like another sketch tool (as Mirror)."""

    title = ""
    tip = ""
    icon = ""
    tool = ""  # the tool's class in sketch_pattern_tool

    def GetResources(self):
        return {"MenuText": self.title, "ToolTip": self.tip, "Pixmap": ui_icon_path(self.icon)}

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        try:
            from . import sketch_draw, sketch_pattern_tool

            tool_class = getattr(sketch_pattern_tool, self.tool)
            running = sketch_draw.current_tool()
            if isinstance(running, tool_class):
                running.stop()  # the command again: it ends, nothing is made
                return
            sketch = sketch_mode.editing_sketch()
            if sketch is None:
                session = sketch_mode.current()
                if session is not None:
                    session.stop_tool()
                commands.tell(
                    "%s works inside a sketch: click Create Sketch (or edit a sketch) first."
                    % self.title
                )
                return
            if not sketch.Geometry:
                commands.tell("%s: draw some curves first." % self.title)
                return
            sketch_draw.run(tool_class)
        except Exception as exc:
            warn("%s failed: %s" % (self.title, exc))


class SketchCircularPattern(_SketchPatternCommand):
    title = "Circular Pattern"
    tip = (
        "Copy curves around a centre point: pick the Objects, Center Point's Select and the "
        "point; Full, Angle or Symmetric, Quantity, Total Angle; drag the disc to turn it"
    )
    icon = "sk_pattern_circ"
    tool = "SketchCircularPattern"


class SketchRectangularPattern(_SketchPatternCommand):
    title = "Rectangular Pattern"
    tip = (
        "Copy curves in rows and columns: pick the Objects; Directions (the sketch's X and Y, "
        "or lines), Quantity and Distance of each; drag the arrows to space them"
    )
    icon = "sk_pattern_rect"
    tool = "SketchRectangularPattern"


def settle_box():
    """The sketch closed (E, another command): nothing waits for curves any more. (The
    Rectangular Pattern box this kept is gone: the pattern tools are sketch_draw tools now,
    which the sketch ends itself.)"""
    _state["box"] = None
    stop_waiting()


def close_box(accept=False):
    """Esc (accept False) or Finish Sketch (accept True) in the sketch: kept for its callers
    in sketch_mode; the pattern tools end with the sketch's running tool (finish_tool makes
    a pattern that can be made, Esc makes nothing)."""
    _state["box"] = None


COMMANDS = {
    "Fission180_SketchCircularPattern": SketchCircularPattern,
    "Fission180_SketchRectangularPattern": SketchRectangularPattern,
}
# Sketch Scale and Move/Copy are Fission 180 tools with Fusion's panels since 2026-11-09
# (they waited here for curves, then handed them to FreeCAD's Scale / Translate):
# sketch_scale_ui.py / sketch_move_ui.py and their sketch_*_tool.py.
