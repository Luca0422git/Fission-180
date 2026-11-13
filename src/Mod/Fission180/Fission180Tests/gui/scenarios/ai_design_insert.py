# SPDX-License-Identifier: LGPL-2.1-or-later
"""INSERT's commands for an AI (Decal, Canvas, Insert SVG, Insert Derive, another design as a
component), a user coordinate system, Compute All and a base feature, through the real MCP
server and Fission 180's AI bridge (wave 8, builder ai-design;
Fission180Tests/gui/ai_design_steps.py).

Path 1, AI control on, the MCP server's tool list has the INSERT tools.
Path 2, on a 140 x 80 x 10 plate: a 100 mm wide canvas behind XZ (40 % opaque), a 30 mm wide
  decal on the top face, an SVG's outline in a sketch (2 closed areas, 30 x 20 mm), a user
  coordinate system, Compute All; the canvas and the decal are drawn in the window (the
  decal's picture on its triangles, the canvas see-through as asked).
Path 3, a master design saved, then derived into a child design (Insert Derive: its body
  and parameter, linked), a base feature: every check of the headless run
  (design_tools.INSERT).
Path 4, the master inserted into a new, saved design as a linked component (INSERT > Insert
  Component: import_file of an .FCStd); Undo takes it out, Redo brings it back.
Path 5, AI control off again.
"""

import FreeCAD as App
from Fission180Tests.gui import ai_design_steps as ai
from Fission180Tests.gui import harness as h


def start():
    ai.start()
    ai.offers("decal", "canvas", "insert_svg", "derive", "coordinate_system", "base_feature")


def plate_with_pictures():
    from Fission180Tests.headless import design_tools

    calls = design_tools.ASSEMBLY[:5] + design_tools.INSERT[:9]  # (the plate "Base", INSERT)
    ai.run_calls(calls, "insert")
    from fission180 import decal, decal_ui, insert

    doc = App.ActiveDocument
    found = decal.decals(doc)
    view = found[-1].ViewObject.Proxy if found and found[-1].ViewObject is not None else None
    h.check("the decal is drawn in the window", isinstance(view, decal_ui.ViewProviderDecal), view)
    if isinstance(view, decal_ui.ViewProviderDecal):
        points, triangles, picture = view.drawn()
        h.check("... on its triangles, with its picture", points and triangles and picture)
    canvases = insert.canvases(doc)
    h.check(
        "the canvas is shown, 40 % opaque (60 % see-through)",
        canvases
        and canvases[-1].ViewObject.Visibility
        and canvases[-1].ViewObject.Transparency == 60,
        canvases and canvases[-1].ViewObject.Transparency,
    )
    ai.show_all("insert")
    h.shot("ai-design-insert")


plate_with_pictures.timeout_s = 180


def derived():
    from Fission180Tests.headless import design_tools

    ai.run_calls(design_tools.INSERT[9:], "derive")


derived.timeout_s = 180


def component_inserted():
    import os

    from fission180 import design_insert

    folder = ai.S["folder"]
    calls = [
        {"tool": "new_design", "args": {"name": "Holder"}},
        {"tool": "save_as", "args": {"path": "{tmp}/holder.FCStd"}},
        {
            "tool": "import_file",
            "args": {"path": "{tmp}/master.FCStd"},
            "contains": ["linked component"],
        },
    ]
    ai.run_calls(calls, "component")
    doc = App.ActiveDocument
    h.check("the master came in as a linked component", bool(design_insert.linked_components(doc)))
    h.check("... from its file", os.path.isfile(os.path.join(folder, "master.FCStd")))
    ai.call("undo", {})
    h.check("Undo took it out", not design_insert.linked_components(doc))
    ai.call("redo", {})
    h.check("Redo brought it back", bool(design_insert.linked_components(doc)))
    ai.ai_steps_only("component")


component_inserted.timeout_s = 120


def stop():
    ai.stop()


h.run(
    "ai_design_insert",
    [start, plate_with_pictures, derived, component_inserted, stop],
    paced_by="state",
)
