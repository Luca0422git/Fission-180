# SPDX-License-Identifier: LGPL-2.1-or-later
"""The SKETCH > MODIFY > Move/Copy command (M in a sketch): Fusion's sketch Move/Copy with its
MOVE/COPY panel and manipulator (sketch_move_tool.py). Registered by commands.py like every
*_ui.py module.

It starts every time it is clicked in a sketch: whatever tool runs ends first (Fission 180's
or FreeCAD's), the curves selected then are its Objects. Clicked again while it runs, it
keeps running (nothing is lost)."""

import FreeCAD as App

from . import commands, sketch_mode, ui_icon_path, warn


class SketchMoveCommand:
    title = "Move/Copy"
    tip = (
        "Move or copy sketch curves: pick them (click, or drag a box), then drag the arrows "
        "or the turn handle, or type X / Y Distance and Angle; OK (M)"
    )
    icon = "sk_move"

    def GetResources(self):
        return {"MenuText": self.title, "ToolTip": self.tip, "Pixmap": ui_icon_path(self.icon)}

    def IsActive(self):
        return App.ActiveDocument is not None

    def tool_class(self):
        from . import sketch_move_tool

        return sketch_move_tool.SketchMove

    def Activated(self):
        try:
            from . import sketch_draw

            sketch = sketch_mode.editing_sketch()
            if sketch is None:
                commands.tell(
                    "%s works inside a sketch: click Create Sketch (or edit a sketch) first."
                    % self.title
                )
                return
            cls = self.tool_class()
            running = sketch_draw.current_tool()
            if isinstance(running, cls):
                running.say("%s is running: %s" % (self.title, running.prompt()))
                return
            sketch_draw.run(cls)
        except Exception as exc:
            warn("%s failed: %s" % (self.title, exc))


COMMANDS = {"Fission180_SketchMove": SketchMoveCommand}
