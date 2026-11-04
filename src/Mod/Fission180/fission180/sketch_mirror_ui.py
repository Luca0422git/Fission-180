# SPDX-License-Identifier: LGPL-2.1-or-later
"""The SKETCH > CREATE > Mirror command: Fusion's sketch Mirror with its MIRROR panel
(sketch_mirror_tool.py). Registered by commands.py like every *_ui.py module.

Mirror again while it runs ends it without making anything, like another sketch tool."""

import FreeCAD as App

from . import commands, sketch_mode, ui_icon_path, warn


class SketchMirrorCommand:
    title = "Mirror"
    tip = (
        "Mirror curves about a line: pick the Objects, then Mirror Line's Select and the "
        "line; OK. The copies stay symmetric to the originals"
    )
    icon = "sk_mirror"

    def GetResources(self):
        return {"MenuText": self.title, "ToolTip": self.tip, "Pixmap": ui_icon_path(self.icon)}

    def IsActive(self):
        return App.ActiveDocument is not None

    def Activated(self):
        try:
            from . import sketch_draw, sketch_mirror_tool

            tool = sketch_draw.current_tool()
            if isinstance(tool, sketch_mirror_tool.SketchMirror):
                tool.stop()  # Mirror again: it ends, nothing is made
                return
            sketch = sketch_mode.editing_sketch()
            if sketch is None:
                commands.tell("Mirror works inside a sketch: click Create Sketch (or edit a sketch) first.")
                return
            if not sketch.Geometry:
                commands.tell("Mirror: draw some curves first.")
                return
            sketch_draw.run(sketch_mirror_tool.SketchMirror)
        except Exception as exc:
            warn("Mirror failed: %s" % exc)


COMMANDS = {"Fission180_SketchMirror": SketchMirrorCommand}
