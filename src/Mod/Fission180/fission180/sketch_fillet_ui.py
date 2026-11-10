# SPDX-License-Identifier: LGPL-2.1-or-later
"""The SKETCH > MODIFY > Fillet command: Fusion's sketch fillet between lines, arcs and
circles, with its FILLET panel and radius arrow (sketch_fillet_tool.py). Registered by
commands.py like every *_ui.py module.

It starts every time it is clicked in a sketch: whatever tool runs ends first (Fission 180's
or FreeCAD's), corners selected then are taken. Clicked again while it runs, it keeps running
(the corners picked are not lost), as Move/Copy."""

from . import sketch_move_ui


class SketchFilletCommand(sketch_move_ui.SketchMoveCommand):
    title = "Fillet"
    tip = (
        "Round corners with arcs: click the corners (or two curves; again to drop one), then "
        "drag the arrow or type the Radius; OK"
    )
    icon = "sk_fillet"

    def tool_class(self):
        from . import sketch_fillet_tool

        return sketch_fillet_tool.SketchFillet


COMMANDS = {"Fission180_SketchFillet": SketchFilletCommand}
