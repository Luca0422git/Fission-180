# SPDX-License-Identifier: LGPL-2.1-or-later
"""An AI makes a sheet metal bracket and its flat pattern for a laser cutter, ONLY through MCP
(wave 8, builder ai-workspaces; the recipe docs/ai/recipes/sheet-metal-bracket.md): the real
MCP server passes every call to Fission 180's AI bridge on the window's thread.

Path 1, the rule: a 1.5 mm steel rule of the design's own, made the active one.
Path 2, the bracket: an 80 x 40 base flange, a 30 mm flange standing on its back edge, two
  5 mm holes in the base; it is sheet metal following the rule.
Path 3, the flat pattern: 80 mm wide, one 90 degree bend, the flat holding the folded part's
  material; the DXF for the laser cutter (outline, the holes, the bend's centre line on its own
  layer).
Path 4, the rule swapped on the body (sheet_metal_rule bodies) to 1 mm Steel (mm): the bracket
  and its flat pattern follow; the 1.5 mm rule, used by nothing any more, deleted; the active
  rule refused; each change one Undo step named AI: ...
"""

import os

import FreeCAD as App
from Fission180Tests.gui import ai_workspace_steps as ai
from Fission180Tests.gui import harness as h

S = {}
BASE_TOP = {"type": "plane", "normal": [0, 0, 1], "at": {"axis": "z", "value": "min"}, "count": 1}
BACK_EDGE = {
    "type": "line",
    "parallel": [1, 0, 0],
    "at": [{"axis": "z", "value": "max"}, {"axis": "y", "value": "max"}],
    "count": 1,
}


def _body():
    from fission180 import sheetmetal

    found = sheetmetal.sheet_metal_bodies(App.ActiveDocument)
    return found[0] if len(found) == 1 else None


# -- Path 1 -------------------------------------------------------------------------------------
def rule():
    ai.ok("new_design", {"name": "AiLaserBracket"})
    made = ai.ok(
        "sheet_metal_rule",
        {"rule": "Steel 1.5", "from": "Steel (mm)", "set": {"thickness": 1.5}, "active": True},
    )["data"]
    h.check(
        "a 1.5 mm steel rule, the active one",
        made["active_rule"] == "Steel 1.5" and made["rule"]["in_mm"]["thickness"] == 1.5,
        made,
    )


# -- Path 2 -------------------------------------------------------------------------------------
def bracket():
    ai.ok("create_sketch", {"plane": "XY", "geometry": [{"rect": [0, 0, 80, 40]}]})
    ai.ok("flange", {"kind": "base", "profile": "Sketch1"})
    ai.ok("flange", {"kind": "edge", "edges": BACK_EDGE, "height": 30})
    ai.ok(
        "create_sketch",
        {
            "plane": "XY",
            "offset": 5,
            "geometry": [{"circle": [20, 20, 2.5]}, {"circle": [60, 20, 2.5]}],
        },
    )
    ai.ok("hole", {"sketch": "Sketch2", "diameter": 5, "through_all": True})
    body = _body()
    h.check("one sheet metal body", body is not None)
    from fission180 import sheetmetal

    h.check("... following the 1.5 mm rule", sheetmetal.body_rule_name(body) == "Steel 1.5")
    box = body.Shape.BoundBox
    h.check(
        "... an L bracket: 80 wide, 40 deep, its flange standing 30 (+ the sheet)",
        abs(box.XLength - 80) < 1e-6 and abs(box.YLength - 40) < 1e-6 and 30 <= box.ZLength <= 31.6,
        box,
    )
    S["folded"] = body.Shape.Volume


# -- Path 3 -------------------------------------------------------------------------------------
def flat():
    data = ai.ok("flat_pattern", {"face": BASE_TOP}, ["1 bends"])["data"]
    S["flat"] = data
    bend = data["bends"][0]
    h.check(
        "the flat: 80 wide, one 90 degree bend of the 1.5 mm sheet, K 0.44",
        abs(data["flat_size_mm"][0] - 80) < 1e-3
        and abs(bend["angle_deg"] - 90) < 1e-6
        and data["thickness_mm"] == 1.5,
        data,
    )
    h.check(
        "... 40 + 30 less the bend's corner plus its allowance long",
        62.0 < data["flat_size_mm"][1] < 70.0,
        data["flat_size_mm"],
    )
    h.check(
        "... holding the folded part's material (within 3 %)",
        0.97 * S["folded"] < data["volume_mm3"] < 1.03 * S["folded"],
        (data["volume_mm3"], S["folded"]),
    )
    folder = os.path.join(h.OUT_DIR, "ai-sm")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "bracket-flat.dxf")
    if os.path.exists(path):
        os.remove(path)
    ai.ok("export_flat_pattern", {"path": path}, ["Exported", "1 bends"])
    text = open(path, encoding="ascii", errors="replace").read() if os.path.isfile(path) else ""
    h.check(
        "the DXF for the laser cutter: the outline, the two holes, the bend line on its layer",
        "BEND_CENTER_LINES" in text and text.count("\nCIRCLE\n") >= 2 and "LINE" in text,
        (len(text), text.count("\nCIRCLE\n")),
    )


# -- Path 4 -------------------------------------------------------------------------------------
def swap_rule():
    swapped = ai.ok("sheet_metal_rule", {"rule": "Steel (mm)", "bodies": [_body().Name]})["data"]
    h.check(
        "the bracket follows Steel (mm) now",
        swapped["sheet_metal_bodies"][0]["rule"] == "Steel (mm)",
        swapped["sheet_metal_bodies"],
    )
    body = _body()
    h.check(
        "... 1 mm sheet: about two thirds of the material",
        0.6 * S["folded"] < body.Shape.Volume < 0.72 * S["folded"],
        (body.Shape.Volume, S["folded"]),
    )
    now = ai.ok(
        "export_flat_pattern", {"path": os.path.join(h.OUT_DIR, "ai-sm", "bracket-1mm.dxf")}
    )
    h.check("... and its flat pattern follows (1 mm)", "1 bends" in now["text"], now["text"])
    ai.refused("sheet_metal_rule", {"rule": "Steel 1.5", "delete": True}, ["active rule"])
    ai.ok("sheet_metal_rule", {"rule": "Steel (mm)", "active": True})
    gone = ai.ok("sheet_metal_rule", {"rule": "Steel 1.5", "delete": True})["data"]
    h.check(
        "the 1.5 mm rule, used by nothing, deleted", "Steel 1.5" not in gone["design_rules"], gone
    )
    names = ai.undo_names()
    h.check(
        "each change one Undo step named AI: ...",
        names
        and all(n.startswith("AI:") for n in names)
        and names[0] == "AI: Sheet metal rule Steel 1.5",
        names[:5],
    )


h.run(
    "ai_workspace_sheetmetal",
    [ai.start, rule, bracket, flat, swap_rule, ai.stop],
    paced_by="state",
)
