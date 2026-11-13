# SPDX-License-Identifier: LGPL-2.1-or-later
"""The SKETCH tab's tools for an AI, through the real MCP server and Fission 180's AI bridge
(wave 8, builder ai-design; Fission180Tests/gui/ai_design_steps.py).

Path 1, AI control on, the MCP server's tool list has the new SKETCH tools.
Path 2, every drawing tool with its own code and constraints (Midpoint Line with a 30 mm
  length dimension, 3-Point Rectangle, 2-Point Circle 12 mm across, 3-Point Circle through
  three points, 2-Tangent Circle on the axes, the triangle's 3-Tangent incircle, 3-Point and
  Tangent Arc, Edge Polygon, the three linear slots and the arc slot, Conic Curve, Ellipse,
  control and fit point splines), Sketch Scale, Fillet, Chamfer, Break, Extend, Toggle
  Construction, Offset, Mirror, Rectangular / Circular Pattern, Move/Copy, Curvature,
  Fix / Unfix, Project, Include 3D Geometry, Project to Surface, Intersect, Isoparametric
  Curve: every check of the headless run (design_tools.SKETCH), each sketch still solving.
Path 3, a slot drawn by the AI is a profile: extruded 5 mm it is a solid of (30 x 8 + 16 pi) x 5
  mm3; Undo takes the slot's extrude and the slot back, Redo brings them again.
Path 4, AI control off again.
"""

import math

import FreeCAD as App
from Fission180Tests.gui import ai_design_steps as ai
from Fission180Tests.gui import harness as h


def start():
    ai.start()
    ai.offers("sketch_draw", "sketch_modify", "sketch_pattern", "sketch_project")


def sketch_tools():
    from Fission180Tests.headless import design_tools

    ai.run_calls(design_tools.SKETCH, "sketch")
    ai.ai_steps_only("sketch")


sketch_tools.timeout_s = 300  # (some 55 calls through the bridge)


def slot_extruded():
    run = ai.run_calls(
        [
            {
                "tool": "create_curve_sketch",
                "save": "k8",
                "args": {"plane": "XY", "offset": 300, "curves": [{"point": [0, 0]}]},
            },
            {
                "tool": "sketch_draw",
                "args": {
                    "sketch": "$k8",
                    "kind": "slot_center_to_center",
                    "points": [[0, 0], [30, 0]],
                    "width": 8,
                },
                "contains": ["Center to Center Slot"],
            },
            {
                "tool": "extrude",
                "save": "slot",
                "args": {"profile": "$k8", "distance": 5, "operation": "new_body"},
            },
        ],
        "slot",
    )
    want = (30 * 8 + math.pi * 16) * 5
    got = run.body_volume("slot")
    h.check(
        "the slot extruded 5 mm is (30 x 8 + 16 pi) x 5 mm3",
        got is not None and abs(got - want) < 1e-3,
        got,
    )
    ai.show_all("sketch")
    h.shot("ai-design-sketch")
    names = ai.undo_names()
    h.check("the slot is one Undo step", "AI: Center to Center Slot" in names[:3], names[:3])
    ai.call("undo", {})
    ai.call("undo", {})
    h.check("Undo took the extrude and the slot back", run.obj("slot") is None)
    ai.call("redo", {})
    ai.call("redo", {})
    got = run.body_volume("slot")
    h.check("Redo brought them again", got is not None and abs(got - want) < 1e-3, got)
    doc = App.ActiveDocument
    h.check("the design has no broken step", not [o for o in doc.Objects if "Invalid" in o.State])


def stop():
    ai.stop()


h.run("ai_design_sketch", [start, sketch_tools, slot_extruded, stop], paced_by="state")
