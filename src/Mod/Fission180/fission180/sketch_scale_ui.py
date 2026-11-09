# SPDX-License-Identifier: LGPL-2.1-or-later
"""The SKETCH > MODIFY > Sketch Scale command: Fusion's Sketch Scale with its SKETCH SCALE
panel and drag arrow (sketch_scale_tool.py). Registered by commands.py like every *_ui.py
module. It starts every time it is clicked in a sketch (see sketch_move_ui)."""

from . import sketch_move_ui


class SketchScaleCommand(sketch_move_ui.SketchMoveCommand):
    title = "Sketch Scale"
    tip = (
        "Scale sketch curves about a point: pick them (click, or drag a box), the base point, "
        "then drag the arrow or type the Scale Factor (2, 0.5 or 50%); OK"
    )
    icon = "sk_scale"

    def tool_class(self):
        from . import sketch_scale_tool

        return sketch_scale_tool.SketchScale


COMMANDS = {"Fission180_SketchScale": SketchScaleCommand}
