# SPDX-License-Identifier: LGPL-2.1-or-later
"""The SKETCH > MODIFY > Offset command (key O): Fusion's sketch Offset with its OFFSET
panel (sketch_offset_tool.py). Registered by commands.py like every *_ui.py module.

O (or the menu entry) while Offset already runs ends it, without making anything, like
another sketch tool does."""

import FreeCAD as App

from . import commands, sketch_mode, ui_icon_path, warn


class SketchOffsetCommand:
    title = "Offset"
    tip = (
        "Offset curves: click them (Chain Selection takes the curves joined to the one "
        "clicked), then drag or type the distance; One Side or Symmetric, Flip, OK (O)"
    )
    icon = "sk_offset"

    def GetResources(self):
        return {"MenuText": self.title, "ToolTip": self.tip, "Pixmap": ui_icon_path(self.icon)}

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        try:
            from . import sketch_draw, sketch_offset_tool

            tool = sketch_draw.current_tool()
            if isinstance(tool, sketch_offset_tool.SketchOffset):
                tool.stop()  # O again: Offset ends, nothing is made
                return
            sketch = sketch_mode.editing_sketch()
            if sketch is not None and not sketch.Geometry and len(sketch.ExternalGeo) <= 2:
                commands.tell("Offset: draw some curves first.")
                return
            sketch_draw.run(sketch_offset_tool.SketchOffset)
        except Exception as exc:
            warn("Offset failed: %s" % exc)


COMMANDS = {"Fission180_SketchOffset": SketchOffsetCommand}
