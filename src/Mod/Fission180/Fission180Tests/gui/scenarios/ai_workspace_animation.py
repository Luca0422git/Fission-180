# SPDX-License-Identifier: LGPL-2.1-or-later
"""An AI makes an exploded-view video, ONLY through MCP (wave 8, builder ai-workspaces; the
recipe docs/ai/recipes/exploded-view-video.md): the real MCP server passes every call to
Fission 180's AI bridge on the window's thread.

Path 1, the assembly: a Base and a Rotor subassembly (a Shaft and a Wheel in it).
Path 2, the storyboard: it starts from the Home (iso) view (anim_view at 0), Auto Explode: All
  Levels one component after another with trail lines (the Rotor leaves the Base, the Shaft
  and the Wheel come apart inside it), the camera turns to the front and closes in (a View
  action), a callout on the Wheel.
Path 3, the timeline edited (anim_action): the View action moved 1 s later, the storyboard
  1 s longer; a refusal for an action that does not exist.
Path 4, Publish Video: an AVI of every frame (the answer's frames, the file's size); the
  design's own components never moved; each change one Undo step named AI: ...
"""

import os

import FreeCAD as App
from Fission180Tests.gui import ai_workspace_steps as ai
from Fission180Tests.gui import harness as h

S = {}


def _placements():
    from fission180 import animation

    return {c.Label: tuple(c.Placement.Base) for c in animation.movables(App.ActiveDocument)}


# -- Path 1 -------------------------------------------------------------------------------------
def assembly():
    ai.ok("new_design", {"name": "AiExplode"})
    ai.ok("new_component", {"label": "Base"})
    ai.ok("create_sketch", {"plane": "XY", "geometry": [{"rect": [-40, -40, 40, 40]}]})
    ai.ok("extrude", {"profile": "Sketch1", "distance": 10})
    ai.ok("new_component", {"label": "Rotor"})
    ai.ok("new_component", {"label": "Shaft", "parent": "Rotor"})
    ai.ok("create_sketch", {"plane": "XY", "offset": 10, "geometry": [{"circle": [0, 0, 5]}]})
    ai.ok("extrude", {"profile": "Sketch2", "distance": 40})
    ai.ok("new_component", {"label": "Wheel", "parent": "Rotor"})
    ai.ok("create_sketch", {"plane": "XY", "offset": 30, "geometry": [{"circle": [0, 0, 20]}]})
    ai.ok("extrude", {"profile": "Sketch3", "distance": 8})
    listed = ai.ok("anim_storyboards", {}, ["no storyboard yet"])["data"]
    names = sorted(c["name"] for c in listed["components"])
    h.check(
        "four components an animation can move", names == ["Base", "Rotor", "Shaft", "Wheel"], names
    )
    S["home"] = _placements()


# -- Path 2 -------------------------------------------------------------------------------------
def storyboard():
    ai.ok("anim_storyboard", {"name": "Explode"}, ["new storyboard 'Explode'"])
    start = ai.ok("anim_view", {"at": 0, "view": "iso"}, ["starts with this view"])["data"]
    h.check(
        "the storyboard starts from the Home view (from the front, right and top)",
        start["looks_from"][0] > 0.5
        and start["looks_from"][1] < -0.5
        and start["looks_from"][2] > 0.5,
        start["looks_from"],
    )
    boom = ai.ok(
        "anim_explode",
        {"at": 3, "levels": "all", "sequential": True, "trails": True},
        ["Explode"],
    )["data"]
    moved = sorted(r["component"] for r in boom["components_at"])
    h.check(
        "Auto Explode: All Levels moves the Rotor and, inside it, the Shaft or the Wheel",
        "Rotor" in moved and ({"Shaft", "Wheel"} & set(moved)) and "Base" not in moved,
        boom["components_at"],
    )
    h.check(
        "... one after another (sequential): several actions ending by 3 s",
        len(boom["actions"]) >= 2 and max(a["end"] for a in boom["actions"]) <= 3.0 + 1e-9,
        boom["actions"],
    )
    view = ai.ok("anim_view", {"at": 5, "view": "front", "zoom": 1.5}, ["a View action"])["data"]
    S["view_id"] = view["action"]["id"]
    h.check(
        "a View action ending at 5 s, looking from the front",
        view["action"]["end"] == 5.0 and abs(view["looks_from"][1] + 1.0) < 1e-6,
        view,
    )
    ai.ok("anim_callout", {"at": 4, "text": "Wheel, 40 mm", "point": [0, 0, 38], "of": "Wheel"})


# -- Path 3 -------------------------------------------------------------------------------------
def timeline():
    moved = ai.ok("anim_action", {"actions": [S["view_id"]], "shift": 1}, ["6 s long now"])["data"]
    h.check(
        "the View action moved 1 s later, its length kept",
        moved["actions"][0]["end"] == 6.0,
        moved["actions"],
    )
    ai.refused("anim_action", {"actions": [99], "delete": True}, ["no action 99"])
    board = ai.ok("anim_storyboards", {"storyboard": "Explode", "at": 6})["data"]
    kinds = sorted({a["kind"] for a in board["actions"]})
    h.check(
        "the storyboard: transforms, a view and a callout, 6 s long",
        kinds == ["callout", "transform", "view"] and board["length_s"] == 6.0,
        (kinds, board["length_s"]),
    )
    h.check(
        "... with trail lines for the components that moved",
        len(board["trails"]) >= 2,
        board["trails"],
    )


# -- Path 4 -------------------------------------------------------------------------------------
def video():
    folder = os.path.join(h.OUT_DIR, "ai-anim")
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, "explode.avi")
    if os.path.exists(path):
        os.remove(path)
    made = ai.ok(
        "anim_publish_video",
        {"path": path, "width": 320, "height": 240, "fps": 8},
        ["Published"],
        timeout=900,
    )["data"]
    size = os.path.getsize(path) if os.path.isfile(path) else 0
    h.check(
        "Publish Video: an AVI of 6 s at 8 frames a second",
        made["frames"] >= 48
        and made["width"] == 320
        and abs(made["length_s"] - made["frames"] / 8.0) < 1e-6,
        made,
    )
    h.check("... a file of every frame", size > made["frames"] * 500, size)
    h.check("the design's own components never moved", _placements() == S["home"], _placements())
    names = ai.undo_names()
    h.check(
        "each change one Undo step named AI: ...",
        names
        and all(n.startswith("AI:") for n in names)
        and names[0] == "AI: Edit animation action",
        names[:5],
    )


video.timeout_s = 900


h.run(
    "ai_workspace_animation",
    [ai.start, assembly, storyboard, timeline, video, ai.stop],
    paced_by="state",
)
