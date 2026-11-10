# SPDX-License-Identifier: LGPL-2.1-or-later
"""The SKETCH > MODIFY > Chamfer command: Fusion's sketch chamfer with its three types, its
CHAMFER panel and drag arrows (sketch_chamfer_tool.py). Registered by commands.py like every
*_ui.py module.

It starts every time it is clicked in a sketch: whatever tool runs ends first (Fission 180's
or FreeCAD's), a corner selected then is taken. Clicked again while it runs, it keeps running
(the corner picked is not lost), as Move/Copy and Fillet."""

from . import sketch_move_ui


class SketchChamferCommand(sketch_move_ui.SketchMoveCommand):
    title = "Chamfer"
    tip = (
        "Cut a corner off with a straight line: pick the Chamfer Type, click the corner (or its "
        "two lines), then drag the arrows or type the values; OK"
    )
    icon = "sk_chamfer"

    def tool_class(self):
        from . import sketch_chamfer_tool

        return sketch_chamfer_tool.SketchChamfer


COMMANDS = {"Fission180_SketchChamfer": SketchChamferCommand}
