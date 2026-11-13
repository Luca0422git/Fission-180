# SPDX-License-Identifier: LGPL-2.1-or-later
"""An AI mills a pocketed plate, ONLY through MCP (wave 8, builder ai-workspaces; the recipe
docs/ai/recipes/mill-pocketed-plate.md): the real MCP server passes every call to Fission 180's
AI bridge on the window's thread.

Path 1, the part: a 100 x 60 x 10 plate with a 40 x 20 x 4 pocket and four 5 mm holes; its
  setup (stock 2 mm around and 1 mm on top, the origin at the stock's top corner).
Path 2, the Tool Library: the sample 6 mm end mill copied into the person's Local library and
  its feed changed there (cam_tool_library), then used by the pocket.
Path 3, the operations: facing, a 2D pocket on the pocket's floor, a 2D contour cut out with
  four tabs in 4 mm steps, drilling the four holes; every toolpath valid.
Path 4, Simulate as numbers: no rapid into the stock, no gouge, the stock left on the part is
  the pocket's corners the 6 mm tool cannot reach (at most the pocket's 4 mm depth); a facing
  1 mm too deep is found as a gouge of the part's whole top, named by its operation.
Path 5, the program and the sheet: Grbl G-code checked (no problem, millimetres, the lowest Z
  the stock's bottom), the setup sheet with every operation; the design never changed.
"""

import os

import FreeCAD as App
from Fission180Tests.gui import ai_workspace_steps as ai
from Fission180Tests.gui import harness as h

S = {}
POCKET_FLOOR = {"normal": [0, 0, 1], "at": {"axis": "z", "value": 6}, "count": 1}
VOLUME = 100 * 60 * 10 - 40 * 20 * 4 - 4 * 3.141592653589793 * 2.5**2 * 10


def _volume():
    from fission180 import bodies

    found = bodies.solid_bodies(App.ActiveDocument)
    return found[0].Shape.Volume if len(found) == 1 else None


# -- Path 1 -------------------------------------------------------------------------------------
def part_and_setup():
    ai.ok("new_design", {"name": "AiPocketPlate"})
    ai.ok("primitive", {"kind": "box", "plane": "XY", "length": 100, "width": 60, "height": 10})
    ai.ok(
        "create_sketch",
        {"plane": "XY", "offset": 10, "geometry": [{"center_rect": [50, 30, 40, 20]}]},
    )
    ai.ok("extrude", {"profile": "Sketch1", "distance": 4, "operation": "cut", "flip": True})
    ai.ok(
        "create_sketch",
        {
            "plane": "XY",
            "offset": 10,
            "geometry": [{"circle": [x, y, 2.5]} for x in (10, 90) for y in (10, 50)],
        },
    )
    ai.ok("hole", {"sketch": "Sketch2", "diameter": 5, "through_all": True})
    h.check("the plate with its pocket and holes", ai.near(_volume(), VOLUME, 1e-6), _volume())
    setup = ai.ok(
        "cam_setup",
        {
            "stock": {"mode": "relative", "offset_mode": "sides_top_bottom", "side": 2, "top": 1},
            "wcs": {"origin": "stock_point", "box_point": [-1, -1, 1]},
            "post": {"program": "2001", "comment": "pocket plate"},
        },
        ["Setup1", "104 x 64 x 11"],
    )["data"]
    h.check(
        "cam_setup: the origin at the stock's top corner, the part 1 mm below it",
        setup["stock_box"] == [0, 0, -11, 104, 64, 0] and setup["model_box"][5] == -1,
        setup,
    )


# -- Path 2 -------------------------------------------------------------------------------------
def tool_library():
    copied = ai.ok(
        "cam_tool_library",
        {"action": "copy", "from_library": "sample:mm", "id": "sample-mm-flat-6"},
        ["copied into local:Local"],
    )["data"]["tool"]
    S["tool_id"] = copied["id"]
    edited = ai.ok(
        "cam_tool_library",
        {"action": "edit", "id": copied["id"], "tool": {"cutting": {"cutting_feed": 700}}},
        ["changed in local:Local"],
    )["data"]["tool"]
    h.check(
        "the copy's feed is 700 mm/min in the person's library",
        edited["cutting"]["cutting_feed"] == 700.0 and edited["diameter"] == 6.0,
        edited,
    )
    listed = ai.ok("cam_tools", {"library": "local:Local", "diameter": 6})["data"]["tools"]
    h.check(
        "cam_tools lists it in local:Local", [t["id"] for t in listed] == [copied["id"]], listed
    )
    ai.refused(
        "cam_tool_library",
        {"action": "edit", "library": "sample:mm", "id": "sample-mm-flat-6", "tool": {"flutes": 3}},
        ["cannot be changed"],
    )


# -- Path 3 -------------------------------------------------------------------------------------
def operations():
    ai.ok("cam_operation", {"kind": "face", "tool": {"type": "flat", "diameter": 10, "number": 1}})
    pocket = ai.ok(
        "cam_operation",
        {
            "kind": "pocket2d",
            "faces": POCKET_FLOOR,
            "tool": {"library": "local:Local", "id": S["tool_id"]},
        },
    )["data"]
    h.check(
        "the pocket's toolpath goes down to the pocket floor (Z -5 in the setup)",
        pocket["state"] == "valid" and ai.near(pocket["toolpath"]["min_cut_z"], -5.0, 0.001, 0.01),
        pocket,
    )
    ai.ok(
        "cam_operation",
        {
            "kind": "contour2d",
            "faces": {"normal": [0, 0, -1], "count": 1},
            "tool": {"library": "sample:mm", "id": "sample-mm-flat-6"},
            "options": {
                "passes": {"multiple_depths": True, "stepdown": 4},
                "geometry": {"tabs": {"on": True, "positioning": "count", "count": 4}},
            },
        },
    )
    ai.ok(
        "cam_operation",
        {
            "kind": "drill",
            "faces": {"type": "cylinder", "radius": 2.5, "count": 4},
            "tool": {"type": "drill", "diameter": 5, "number": 4},
        },
    )
    rows = ai.ok("cam_setups", {})["data"]["setups"][0]["operations"]
    h.check(
        "four operations, every toolpath valid",
        [r["state"] for r in rows] == ["valid"] * 4,
        [(r["name"], r["state"], r.get("error")) for r in rows],
    )
    ai.ok("cam_generate", {}, ["Nothing to generate"])


operations.timeout_s = 600


# -- Path 4 -------------------------------------------------------------------------------------
def simulate():
    sim = ai.ok("cam_simulate", {}, ["no rapid move into the stock", "No gouge"])["data"]
    h.check("Simulate: no collision", sim["collisions"] == [], sim["collisions"])
    h.check("... no gouge", sim["gouges"]["cells"] == 0, sim["gouges"])
    left = sim["stock_left_on_model"]
    h.check(
        "... the stock left is the pocket's corners (at most its 4 mm depth)",
        3.0 < left["max_mm"] <= 4.05
        and abs(abs(left["at"][0] - 52.0) - 20.0) < 3.5
        and abs(abs(left["at"][1] - 32.0) - 10.0) < 3.5,
        left,
    )
    h.check("... and how long it took", sim["seconds"] >= 0 and sim["time_s"] > 0, sim["time_s"])
    ai.ok(
        "cam_operation",
        {
            "kind": "face",
            "tool": {"type": "flat", "diameter": 10, "number": 1},
            "options": {"heights": {"bottom": {"from": "model_top", "offset": -1}}},
            "label": "Too deep",
        },
    )
    bad = ai.ok("cam_simulate", {}, ["GOUGES"])["data"]
    named = [r["name"] for r in bad["operations"] if r.get("deepest_gouge_mm")]
    h.check(
        "a facing 1 mm into the part is a gouge, 1 mm deep, put on that operation",
        ai.near(bad["gouges"]["deepest_mm"], 1.0, 0.02) and named == ["Too deep"],
        (bad["gouges"], named),
    )
    ai.ok("cam_delete", {"target": "Too deep"})


simulate.timeout_s = 600


# -- Path 5 -------------------------------------------------------------------------------------
def program_and_sheet():
    folder = os.path.join(h.OUT_DIR, "ai-cam")
    os.makedirs(folder, exist_ok=True)
    for name in ("2001.nc", "Setup1 setup sheet.html"):
        if os.path.exists(os.path.join(folder, name)):
            os.remove(os.path.join(folder, name))
    posted = ai.ok("cam_post", {"path": folder}, ["the checker found no problem"])["data"]
    check = posted["check"]
    h.check(
        "Grbl G-code in millimetres, four operations, no problem",
        posted["file"].endswith("2001.nc")
        and check["units"] == "mm"
        and not check["problems"]
        and len(posted["operations"]) == 4,
        posted,
    )
    h.check("... its lowest Z the stock's bottom", -13.0 < check["min_z"] <= -11.0 + 1e-3, check)
    sheet = ai.ok("cam_setup_sheet", {"path": folder}, ["4 operations"])["data"]
    text = open(sheet["file"], encoding="utf-8").read() if os.path.isfile(sheet["file"]) else ""
    h.check(
        "the setup sheet names the program, each operation and tool",
        "2001" in text and "2D Pocket" in text and "Drill" in text and "6 mm" in text,
        sheet["file"],
    )
    h.check(
        "nothing in MANUFACTURE changed the design", ai.near(_volume(), VOLUME, 1e-6), _volume()
    )
    names = ai.undo_names()
    h.check(
        "each change one Undo step named AI: ...",
        names and all(n.startswith("AI:") for n in names),
        names[:5],
    )


h.run(
    "ai_workspace_manufacture",
    [ai.start, part_and_setup, tool_library, operations, simulate, program_and_sheet, ai.stop],
    paced_by="state",
)
