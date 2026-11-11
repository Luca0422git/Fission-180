# SPDX-License-Identifier: LGPL-2.1-or-later
"""The headless calls of the MANUFACTURE and ANIMATION AI tools (runner.py runs SESSION after
its own, so every tool of the catalogue is called). The numbers are the golden models' (the
same design steps): a 100 x 60 x 10 plate with two 6 mm holes, faced, cut out and drilled
(golden/models/cam_plate_face_contour_drill.json), and two components exploded and put back.

    freecadcmd -c "from Fission180Tests.headless import workspace_tools; workspace_tools.main()"

runs these calls alone (the report goes to FISSION180_HEADLESS_OUT like the runner's)."""

import json
import math
import os


def _json(answer):
    text = answer["text"]
    start = text.find("{")
    return json.loads(text[start:]) if start >= 0 else None


def _near(got, expected, tol=1e-3):
    return got is not None and abs(got - expected) <= tol


def _box_near(got, expected, tol=1e-3):
    return got is not None and all(_near(a, b, tol) for a, b in zip(got, expected))


def setup_boxes(stock, model, origin):
    def check(answer, run):
        data = _json(answer)
        for key, want in (("stock_box", stock), ("model_box", model), ("origin_in_design", origin)):
            if not _box_near(data.get(key), want):
                return "%s is %s, expected %s" % (key, data.get(key), want)
        return None

    return check


def toolpath(cut_length=None, bounds=None, min_z=None, state="valid", tol=0.01):
    def check(answer, run):
        data = _json(answer)
        if data.get("state") != state:
            return "state %r, expected %r" % (data.get("state"), state)
        path = data.get("toolpath") or {}
        if cut_length is not None and not _near(path.get("cut_length"), cut_length, tol):
            return "cut length %s, expected %s" % (path.get("cut_length"), cut_length)
        if bounds is not None and not _box_near(path.get("bounds"), bounds, tol):
            return "bounds %s, expected %s" % (path.get("bounds"), bounds)
        if min_z is not None and not _near(path.get("min_cut_z"), min_z, tol):
            return "lowest cut %s, expected %s" % (path.get("min_cut_z"), min_z)
        return None

    return check


def states(expected):
    """{operation name: state} of a cam_setups / cam_generate answer."""

    def check(answer, run):
        data = _json(answer)
        rows = data["operations"] if "operations" in data else data["setups"][-1]["operations"]
        got = {r["name"]: r["state"] for r in rows}
        return None if got == expected else "states %s, expected %s" % (got, expected)

    return check


def _body_unchanged(answer, run):
    """Nothing in MANUFACTURE changes the design: the plate less its two holes."""
    import FreeCAD as App

    from fission180 import bodies

    found = bodies.solid_bodies(App.ActiveDocument)
    want = 100 * 60 * 10 - 2 * math.pi * 9 * 10
    if len(found) != 1 or abs(found[0].Shape.Volume - want) > 0.01:
        return "the design changed: %s" % [round(b.Shape.Volume, 3) for b in found]
    return None


def _simulated(answer, run):
    data = _json(answer)
    # the stock is 104 x 64 x 11: facing takes the millimetre on top (104 x 64 x 1 = 6656),
    # the contour a 6 mm slot around the part 10 mm deep (about 7200) and the drill the two
    # holes through the stock (2 x pi x 9 x 11 = 622; the grid of 0.33 mm columns finds less)
    if data["collisions"]:
        return "collisions: %s" % data["collisions"]
    if not _near(data["stock_volume_mm3"], 104 * 64 * 11, 104 * 64 * 11 * 0.01):
        return "stock volume %s" % data["stock_volume_mm3"]
    if not 11000 < data["removed_mm3"] < 16000:
        return "removed %s mm3, expected the top millimetre and the slot (about 13000)" % (
            data["removed_mm3"]
        )
    if [o["name"] for o in data["operations"]] != ["Face1", "2D Contour1", "Drill1"]:
        return "operations %s" % data["operations"]
    # facing 1472, the contour three times around (3 x 338.85, Z -4, -8, -11) with its 16 mm
    # of plunging, the two holes 2 x 15
    if not _near(data["cut_length_mm"], 1472.0 + 3 * 338.85 + 16.0 + 30.0, 1.0):
        return "cut length %s" % data["cut_length_mm"]
    if data["time_s"] <= 0:
        return "no machining time"
    return None


def _posted(answer, run):
    data = _json(answer)
    path = data["file"]
    if not os.path.isfile(path):
        return "no file %s" % path
    with open(path, encoding="utf-8") as handle:
        text = handle.read()
    check = data["check"]
    if check["problems"]:
        return "the checker's problems: %s" % check["problems"]
    if "G21" not in text or check["units"] != "mm":
        return "the program does not say millimetres"
    if not _near(check["min_z"], -11.0):
        return "lowest Z %s, expected -11" % check["min_z"]
    if data["operations"] != ["Face1", "2D Contour1", "Drill1"]:
        return "operations %s" % data["operations"]
    if "(Program 1001)" not in text:
        return "no program comment in %s" % text[:120]
    return None


def _posted_inches(answer, run):
    data = _json(answer)
    with open(data["file"], encoding="utf-8") as handle:
        text = handle.read()
    if "G20" not in text or data["check"]["units"] != "in":
        return "the program is not in inches"
    if not data["file"].endswith("77.ngc"):
        return "the file is %s, expected the program's name with LinuxCNC's extension" % (
            data["file"]
        )
    if data["operations"] != ["Drill1"]:
        return "operations %s" % data["operations"]
    if not _near(data["check"]["min_z"], -11.0 / 25.4, 1e-3):
        return "lowest Z %s in, expected %s" % (data["check"]["min_z"], -11 / 25.4)
    return None


def _library(answer, run):
    data = _json(answer)
    rows = data["tools"]
    if len(rows) != 1 or rows[0]["id"] != "sample-mm-flat-6" or rows[0]["diameter"] != 6.0:
        return "tools %s" % rows
    if rows[0]["cutting"]["spindle_speed"] <= 0 or rows[0]["cutting"]["cutting_feed"] <= 0:
        return "no cutting data: %s" % rows[0]
    return None


def libraries(*expected):
    def check(answer, run):
        rows = {row["library"]: row["tools"] for row in _json(answer)["libraries"]}
        if tuple(rows) != expected:
            return "libraries %s, expected %s" % (list(rows), list(expected))
        if rows["sample:mm"] != 43 or rows["sample:in"] != 26:
            return "the sample libraries have %s tools" % rows
        if "document" in rows and rows["document"] != 3:
            return "the design uses %s tools, expected 3" % rows["document"]
        return None

    return check


def _details(answer, run):
    setup = _json(answer)["setups"][0]
    if setup["options"]["stock"]["side"] != 2.0:
        return "the setup's options: %s" % setup["options"]["stock"]
    contour = [o for o in setup["operations"] if o["name"] == "2D Contour1"][0]
    if contour["options"]["passes"]["stepdown"] != 4 or not contour["picks"]:
        return "the contour's options: %s, picks %s" % (
            contour["options"]["passes"],
            contour.get("picks"),
        )
    if not _near(contour["heights_mm"]["bottom"], -11.0):
        return "the contour's heights: %s" % contour["heights_mm"]
    if contour["options"]["tool"]["id"] != "sample-mm-flat-6":
        return "the contour's tool: %s" % contour["options"]["tool"]
    return None


def _two_tabs(answer, run):
    """The contour's toolpath lifts over a tab at each of the two points given, and nowhere
    else (setup coordinates: origin at the stock's low X, low Y corner, 2 mm outside the
    plate; the 6 mm tool runs 3 mm outside the plate)."""
    import FreeCAD as App

    from fission180 import manufacture as cam
    from fission180 import manufacture_core as core

    doc = App.ActiveDocument
    op = [o for s in cam.setups(doc) for o in cam.operations(s) if o.Label == "2D Contour1"][0]
    segs = core.moves(core.parse_gcode(cam.toolpath(op)), feed_scale=60.0)
    bottom = min(p[2] for seg in segs for p in seg["points"])
    lifts = [
        seg["points"][0]
        for seg in segs
        if seg["kind"] != "rapid"
        and abs(seg["points"][0][2] - bottom) < 1e-3
        and seg["points"][-1][2] > bottom + 1.0
        and math.hypot(
            seg["points"][-1][0] - seg["points"][0][0], seg["points"][-1][1] - seg["points"][0][1]
        )
        < 1e-6
    ]
    if len(lifts) != 2:
        return "%d lifts over tabs, expected 2: %s" % (len(lifts), lifts)
    for want in ((52.0, -1.0), (105.0, 32.0)):
        near = min(math.hypot(p[0] - want[0], p[1] - want[1]) for p in lifts)
        if near > 7.0:
            return "no tab near %s: the lifts are at %s" % (want, lifts)
    return None


def _undo_names(expected_first):
    def check(answer, run):
        import FreeCAD as App

        names = list(App.ActiveDocument.UndoNames)
        if not names or names[0] != expected_first:
            return "the undo list starts with %s, expected %r" % (names[:2], expected_first)
        return None

    return check


TOOL_6 = {"library": "sample:mm", "id": "sample-mm-flat-6"}
CAM = [
    # (without a design there is no Document library)
    {"tool": "cam_tools", "args": {}, "check": libraries("local:Local", "sample:mm", "sample:in")},
    {"tool": "new_design", "args": {"name": "CamPlate"}},
    {"tool": "cam_setups", "args": {}, "contains": ["no setup yet"]},
    {
        "tool": "cam_setup",
        "args": {},
        "expect": "error",
        "contains": ["no solid body"],
    },
    {
        "tool": "primitive",
        "args": {"kind": "box", "plane": "XY", "length": 100, "width": 60, "height": 10},
    },
    {
        "tool": "primitive",
        "args": {
            "kind": "cylinder",
            "plane": "XY",
            "x": 20,
            "y": 30,
            "diameter": 6,
            "height": 10,
            "operation": "cut",
        },
    },
    {
        "tool": "primitive",
        "args": {
            "kind": "cylinder",
            "plane": "XY",
            "x": 80,
            "y": 30,
            "diameter": 6,
            "height": 10,
            "operation": "cut",
        },
    },
    {
        "tool": "cam_operation",
        "args": {"kind": "face", "tool": {"type": "flat", "diameter": 10}},
        "expect": "error",
        "contains": ["no setup yet", "cam_setup"],
    },
    {
        "tool": "cam_setup",
        "args": {
            "stock": {"mode": "relative", "offset_mode": "sides_top_bottom", "side": 2, "top": 1},
            "wcs": {"origin": "stock_point", "box_point": [-1, -1, 1]},
            "post": {"program": "1001", "comment": "golden plate"},
        },
        "save": "cam_setup",
        "contains": ["'Setup1'", "104 x 64 x 11"],
        "check": setup_boxes([0, 0, -11, 104, 64, 0], [2, 2, -11, 102, 62, -1], [-2, -2, 11]),
    },
    {
        "tool": "cam_setup",
        "args": {"stock": {"mode": "solid"}},
        "expect": "error",
        "contains": ["stock_body"],
    },
    {
        "tool": "cam_tools",
        "args": {"library": "sample:mm", "type": "flat", "diameter": 6},
        "check": _library,
    },
    {
        "tool": "cam_tools",
        "args": {"library": "nowhere"},
        "expect": "error",
        "contains": ["no tool library 'nowhere'", "sample:mm"],
    },
    {
        "tool": "cam_operation",
        "args": {"kind": "face", "tool": {"type": "flat", "diameter": 10, "number": 1}},
        "save": "cam_face",
        "contains": ["'Face1'"],
        "check": toolpath(bounds=[5, 5, -1, 99, 59, 15], min_z=-1),
    },
    {
        "tool": "cam_operation",
        "args": {
            "kind": "contour2d",
            "faces": {"normal": [0, 0, -1], "count": 1},
            "tool": TOOL_6,
            "options": {"linking": {"lead_in": False, "lead_out": False}},
        },
        "save": "cam_contour",
        # around the plate 3 mm out with rounded corners: 2 x (100 + 60) + 2 pi x 3 = 338.85
        # at Z -11, plus the 16 mm plunge from the feed height
        "check": toolpath(cut_length=354.85, bounds=[-1, -1, -11, 105, 65, 15], min_z=-11),
    },
    {
        "tool": "cam_operation",
        "args": {
            "kind": "drill",
            "faces": {"type": "cylinder", "radius": 3, "count": 2},
            "tool": {"type": "drill", "diameter": 6, "number": 3},
        },
        "save": "cam_drill",
        "check": toolpath(cut_length=30, bounds=[22, 32, -11, 82, 32, 15], min_z=-11),
    },
    {"tool": "cam_setups", "args": {}, "check": _body_unchanged},
    {
        "tool": "cam_tools",
        "args": {},
        "check": libraries("document", "local:Local", "sample:mm", "sample:in"),
    },
    {"tool": "cam_tools", "args": {"library": "document"}, "contains": ["3 tools in document"]},
    # refusals an AI can act on: nothing added, nothing left in the undo list
    {
        "tool": "cam_operation",
        "args": {"kind": "pocket2d", "tool": TOOL_6},
        "expect": "error",
        "contains": ["Nothing is selected"],
        "check": None,
    },
    {
        "tool": "cam_operation",
        "args": {
            "kind": "drill",
            "faces": {"type": "cylinder", "radius": 3, "count": 2},
            "tool": TOOL_6,
        },
        "expect": "error",
        "contains": ["Drill cannot cut with a flat end mill"],
    },
    {
        "tool": "cam_operation",
        "args": {"kind": "face", "tool": {"library": "sample:mm", "id": "no-such-tool"}},
        "expect": "error",
        "contains": ["no tool with id 'no-such-tool'", "cam_tools"],
    },
    {
        "tool": "cam_operation",
        "args": {"kind": "face", "setup": "Setup9", "tool": TOOL_6},
        "expect": "error",
        "contains": ["no setup 'Setup9'", "Setup1"],
    },
    {
        "tool": "cam_setups",
        "args": {},
        "contains": ["1 setup, 3 operations."],
        "check": states({"Face1": "valid", "2D Contour1": "valid", "Drill1": "valid"}),
    },
    {
        "tool": "cam_edit",
        "args": {
            "target": "2D Contour1",
            "options": {"passes": {"multiple_depths": True, "stepdown": 4}},
        },
        # three depths (Z -4, -8, -11): three times around, three plunges
        "check": toolpath(min_z=-11),
        "contains": ["2D Contour1 changed"],
    },
    {
        "tool": "cam_edit",
        "args": {"target": "2D Contour1", "stock": {"top": 2}},
        "expect": "error",
        "contains": ["an operation", "stock"],
    },
    {
        "tool": "cam_edit",
        "args": {"target": "Drill1", "move": "down"},
        "expect": "error",
        "contains": ["last operation"],
    },
    {
        "tool": "cam_edit",
        "args": {"target": "Drill1", "suppressed": True},
        "contains": ["suppressed"],
    },
    {
        "tool": "cam_edit",
        "args": {"target": "Drill1", "suppressed": False},
        "check": _undo_names("AI: Edit Drill1"),
    },
    {
        "tool": "cam_setups",
        "args": {"setup": "Setup1", "details": True},
        "check": _details,
    },
    {"tool": "cam_simulate", "args": {}, "check": _simulated},
    {
        "tool": "cam_post",
        "args": {"path": "{tmp}"},
        "contains": ["1001.nc", "no problem", "Grbl"],
        "check": _posted,
    },
    {
        "tool": "cam_post",
        "args": {"path": "{tmp}/1001.nc"},
        "expect": "error",
        "contains": ["1001.nc"],
    },
    {
        "tool": "cam_post",
        "args": {
            "path": "{tmp}",
            "post": "linuxcnc",
            "units": "in",
            "program": "77",
            "operations": ["Drill1"],
        },
        "check": _posted_inches,
    },
    {
        "tool": "cam_post",
        "args": {"path": "{tmp}/no/such/folder/a.nc"},
        "expect": "error",
        "contains": ["does not exist"],
    },
    # the design changes: every toolpath is out of date, simulate refuses, generate rebuilds
    {"tool": "cam_edit", "args": {"target": "Setup1", "stock": {"top": 2}}, "contains": ["need"]},
    {
        "tool": "cam_setups",
        "args": {},
        "check": states({"Face1": "stale", "2D Contour1": "stale", "Drill1": "stale"}),
    },
    {
        "tool": "cam_simulate",
        "args": {},
        "expect": "error",
        "contains": ["no up-to-date toolpath", "generate"],
    },
    {
        "tool": "cam_generate",
        "args": {"operations": ["Face1"]},
        "contains": ["1 toolpath"],
        "check": states({"Face1": "valid", "2D Contour1": "stale", "Drill1": "stale"}),
    },
    {
        "tool": "cam_generate",
        "args": {},
        "contains": ["2 toolpaths"],
        "check": states({"Face1": "valid", "2D Contour1": "valid", "Drill1": "valid"}),
    },
    {"tool": "cam_generate", "args": {}, "contains": ["Nothing to generate"]},
    {"tool": "cam_delete", "args": {"target": "Face1"}, "contains": ["Face1 deleted"]},
    {"tool": "undo", "args": {}, "contains": ["AI: Delete Face1"]},
    {
        "tool": "cam_setups",
        "args": {},
        "contains": ["1 setup, 3 operations"],
        "check": _body_unchanged,
    },
    # the other side: the stock From preceding setup is Setup1's block, turned over (the top
    # is 2 mm above the plate by now: 104 x 64 x 12, the plate's underside flush with it)
    {
        "tool": "cam_setup",
        "args": {"stock": {"mode": "preceding"}, "wcs": {"flip_z": True}},
        "contains": ["'Setup2'", "104 x 64 x 12"],
        "check": setup_boxes([-52, -32, -12, 52, 32, 0], [-50, -30, -10, 50, 30, 0], [50, 30, 0]),
    },
    {"tool": "cam_delete", "args": {"target": "Setup2"}, "contains": ["Setup2 deleted"]},
    # tabs at points: on the plate's outline (y = 0 and x = 100), and one that is not
    {
        "tool": "cam_edit",
        "args": {
            "target": "2D Contour1",
            "options": {
                "passes": {"multiple_depths": False},
                "geometry": {
                    "tabs": {
                        "on": True,
                        "positioning": "points",
                        "points": [[50, 0, 0], [100, 30, 5]],
                    }
                },
            },
        },
        "check": _two_tabs,
    },
    {
        "tool": "cam_edit",
        "args": {
            "target": "2D Contour1",
            "options": {"geometry": {"tabs": {"points": [[50, 30, 0]]}}},
        },
        "expect": "error",
        "contains": ["Tab position 1 is not on the picked contour", "30 mm away"],
    },
    {
        "tool": "cam_setups",
        "args": {},
        "check": states({"Face1": "valid", "2D Contour1": "valid", "Drill1": "valid"}),
    },
    {"tool": "cam_delete", "args": {"target": "Setup1"}, "contains": ["3 operations"]},
    {"tool": "cam_setups", "args": {}, "contains": ["no setup yet"]},
    {"tool": "cam_delete", "args": {"target": "Setup1"}, "expect": "error"},
]


# -- ANIMATION ----------------------------------------------------------------------------------
def places(expected, hidden=()):
    """{component label: position} of an answer's components_at (the ones moved)."""

    def check(answer, run):
        data = _json(answer)
        got = {row["component"]: row["position"] for row in data.get("components_at", [])}
        if set(got) != set(expected):
            return "moved: %s, expected %s" % (sorted(got), sorted(expected))
        for name, want in expected.items():
            if not _box_near(got[name], want):
                return "%s is at %s, expected %s" % (name, got[name], want)
        if sorted(data.get("hidden_at", [])) != sorted(hidden):
            return "hidden: %s, expected %s" % (data.get("hidden_at"), list(hidden))
        return None

    return check


def _design_untouched(answer, run):
    """An animation never moves the design's components."""
    import FreeCAD as App

    from fission180 import components

    for comp in components.list_components(App.ActiveDocument):
        if comp.Placement.Base.Length > 1e-9 or abs(comp.Placement.Rotation.Angle) > 1e-9:
            return "%s was moved in the design: %s" % (comp.Label, comp.Placement)
    return None


def boards(names, active):
    def check(answer, run):
        data = _json(answer)
        got = [row["name"] for row in data["storyboards"]]
        if got != names or data["active"] != active:
            return "storyboards %s (active %r), expected %s (active %r)" % (
                got,
                data["active"],
                names,
                active,
            )
        return None

    return check


def _reversed(answer, run):
    """The copy plays backwards: where "Explode" is 4 s in (7 s long), the copy is at 3 s."""
    import FreeCAD as App

    from fission180 import animation

    doc = App.ActiveDocument
    wheel = [c for c in animation.movables(doc) if c.Label == "Wheel"][0]
    there = animation.placements_at(doc, "Explode", 4.0)[wheel.Name].Base
    here = animation.placements_at(doc, "Explode (copy)", 3.0)[wheel.Name].Base
    if (there - here).Length > 1e-6 or abs(here.x - 20.0) > 1e-6 or abs(here.z - 15.0) > 1e-6:
        return "the reversed copy is at %s at 3 s; Explode is at %s at 4 s" % (here, there)
    if abs(animation.duration(doc, "Explode (copy)") - 7.0) > 1e-9:
        return "the copy is %s s long" % animation.duration(doc, "Explode (copy)")
    return None


def _actions(answer, run):
    data = _json(answer)
    kinds = [a["kind"] for a in data["actions"]]
    if sorted(kinds) != ["callout", "transform", "transform", "transform", "visibility"]:
        return "actions: %s" % kinds
    spans = [(a["start"], a["end"]) for a in data["actions"] if a["kind"] == "transform"]
    if spans != [(0.0, 3.0), (3.0, 5.0), (5.0, 7.0)]:
        return "the transform actions' times: %s" % spans
    if data["length_s"] != 7.0:
        return "length %s" % data["length_s"]
    return None


ANIM = [
    {"tool": "new_design", "args": {"name": "AnimParts"}},
    {
        "tool": "primitive",
        "args": {"kind": "box", "plane": "XY", "length": 20, "width": 20, "height": 10},
    },
    {
        "tool": "anim_storyboard",
        "args": {"name": "Explode"},
        "expect": "error",
        "contains": ["has no components", "components_from_bodies"],
    },
    {"tool": "new_design", "args": {"name": "AnimWheel"}},
    {"tool": "new_component", "args": {"label": "Base"}},
    {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [-30, -30, 30, 30]}]}},
    {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 10}},
    {"tool": "new_component", "args": {"label": "Wheel"}},
    {
        "tool": "create_sketch",
        "args": {"plane": "XY", "offset": 20, "geometry": [{"circle": [0, 0, 15]}]},
    },
    {"tool": "extrude", "args": {"profile": "Sketch2", "distance": 5}},
    {"tool": "anim_storyboards", "args": {}, "contains": ["no storyboard yet"]},
    {
        "tool": "anim_storyboard",
        "args": {"name": "Explode"},
        "check": boards(["Explode"], "Explode"),
    },
    {
        "tool": "anim_storyboard",
        "args": {"name": "Explode"},
        "expect": "error",
        "contains": ["Explode"],
    },
    # the scratch zone: the storyboard starts that way, nothing is recorded
    {
        "tool": "anim_transform",
        "args": {"at": 0, "of": ["Wheel"], "move": [0, 0, 5]},
        "contains": ["scratch zone", "no action"],
        "check": places({"Wheel": [0, 0, 5]}),
    },
    {
        "tool": "anim_transform",
        "args": {"at": 0, "of": ["Wheel"], "move": [0, 0, -5]},
        "check": places({}),
    },
    {
        "tool": "anim_transform",
        "args": {"at": 2, "of": ["Wheel"]},
        "expect": "error",
        "contains": ["nothing would move"],
    },
    {
        "tool": "anim_transform",
        "args": {"at": 2, "of": ["Nut"], "move": [0, 0, 5]},
        "expect": "error",
        "contains": ["Nut"],
    },
    # Auto Explode: the larger Base stays, the Wheel moves away from it along Z by a quarter
    # of the assembly's size (60 x 60 x 25: 15 mm)
    {
        "tool": "anim_explode",
        "args": {"at": 3},
        "contains": ["1 component exploded", "ending at 3 s"],
        "check": places({"Wheel": [0, 0, 15]}),
    },
    {
        "tool": "anim_manual_explode",
        "args": {"at": 5, "picks": [{"of": "Wheel", "axis": "X+"}], "distance": 20, "scale": 2},
        "check": places({"Wheel": [40, 0, 15]}),
    },
    {
        "tool": "anim_show_hide",
        "args": {"at": 5, "of": ["Wheel"], "show": False},
        "contains": ["Wheel hidden"],
        "check": places({"Wheel": [40, 0, 15]}, hidden=["Wheel"]),
    },
    {
        "tool": "anim_show_hide",
        "args": {"at": 5, "of": ["Wheel"], "show": False},
        "expect": "error",
        "contains": ["hidden", "already"],
    },
    {
        "tool": "anim_restore_home",
        "args": {"at": 7, "of": ["Wheel"]},
        "contains": ["Wheel sent home"],
        "check": places({}, hidden=["Wheel"]),
    },
    {
        "tool": "anim_restore_home",
        "args": {"at": 7, "of": ["Base"]},
        "expect": "error",
        "contains": ["Already home"],
    },
    {
        "tool": "anim_callout",
        "args": {"at": 2, "text": "The wheel", "point": [0, 0, 35], "of": "Wheel"},
        "contains": ["'The wheel'", "following Wheel"],
    },
    {
        "tool": "anim_callout",
        "args": {"at": 2, "text": "  ", "point": [0, 0, 0]},
        "expect": "error",
        "contains": ["text"],
    },
    {
        "tool": "anim_storyboards",
        "args": {"storyboard": "Explode", "at": 4},
        # 4 s is half way through the manual explode (3 s to 5 s): 15 up, 20 of the 40 out
        "check": places({"Wheel": [20, 0, 15]}),
    },
    {"tool": "anim_storyboards", "args": {"storyboard": "Explode"}, "check": _actions},
    {
        "tool": "anim_storyboard",
        "args": {"action": "duplicate", "storyboard": "Explode"},
        "check": boards(["Explode", "Explode (copy)"], "Explode (copy)"),
    },
    {"tool": "anim_storyboard", "args": {"action": "reverse"}, "check": _reversed},
    {
        "tool": "anim_storyboard",
        "args": {"action": "rename", "name": "Assemble"},
        "check": boards(["Explode", "Assemble"], "Assemble"),
    },
    {
        "tool": "anim_storyboard",
        "args": {"action": "rename", "storyboard": "Assemble", "name": "Explode"},
        "expect": "error",
        "contains": ["Explode"],
    },
    {
        "tool": "anim_storyboard",
        "args": {"action": "activate", "storyboard": "Explode"},
        "check": boards(["Explode", "Assemble"], "Explode"),
    },
    {
        "tool": "anim_storyboard",
        "args": {"clean": False},
        # "Start from end of previous": Explode ends with the wheel home and hidden
        "check": boards(["Explode", "Assemble", "Storyboard3"], "Storyboard3"),
    },
    {
        "tool": "anim_storyboards",
        "args": {"storyboard": "Storyboard3", "at": 0},
        "check": places({}, hidden=["Wheel"]),
    },
    {
        "tool": "anim_storyboard",
        "args": {"action": "delete", "storyboard": "Storyboard3"},
        "check": boards(["Explode", "Assemble"], "Assemble"),
    },
    {"tool": "undo", "args": {}, "contains": ["AI: Delete storyboard"]},
    {
        "tool": "anim_storyboards",
        "args": {},
        "contains": ["3 storyboards"],
        "check": _design_untouched,
    },
    {
        "tool": "anim_storyboard",
        "args": {"action": "delete", "storyboard": "Nowhere"},
        "expect": "error",
        "contains": ["no storyboard 'Nowhere'", "'Explode'"],
    },
    {
        "tool": "anim_publish_video",
        "args": {"path": "{tmp}/explode.avi"},
        "expect": "error",
        "contains": ["needs the Fission 180 window"],
    },
]

SESSION = CAM + ANIM


def main():
    """These calls alone, with the runner's report."""
    import tempfile

    import FreeCAD as App

    from Fission180Tests.headless import runner

    out_dir = os.environ.get("FISSION180_HEADLESS_OUT") or App.getUserAppDataDir()
    os.makedirs(out_dir, exist_ok=True)
    run = runner.Run(tempfile.mkdtemp(prefix="fission180-headless-"))
    runner.run_session(run, SESSION, os.environ.get("FISSION180_HEADLESS_FILTER", ""))
    failed = [r for r in run.results if r["status"] != "pass"]
    for r in run.results:
        App.Console.PrintMessage(
            "[Fission 180] workspace tools %s %s %s\n"
            % (r["status"].upper(), r["label"], "; ".join(r["problems"])[:900])
        )
    with open(os.path.join(out_dir, "workspace-tools-report.json"), "w", encoding="utf-8") as h:
        json.dump({"passed": not failed, "results": run.results}, h, indent=2)
    App.Console.PrintMessage(
        "[Fission 180] workspace tools summary: %d calls, %d failed\n"
        % (len(run.results), len(failed))
    )
    return not failed
