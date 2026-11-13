# SPDX-License-Identifier: LGPL-2.1-or-later
"""An AI makes a plastic enclosure with bosses, a lip and a snap fit, then sends it to the 3D
printer's slicer, ONLY through MCP (wave 8, builder ai-workspaces; the recipe
docs/ai/recipes/plastic-enclosure.md): the real MCP server passes every call to Fission 180's AI
bridge on the window's thread.

Path 1, the rule and the two halves: ABS 2 mm; a 60 x 40 x 20 box open at the top and a
  60 x 40 x 10 lid open at the bottom, both shelled to the rule's 2 mm wall.
Path 2, the lip and groove on the box's inner rim (the golden model plastic2_lip_and_groove:
  the box 11900 mm3, the lid 7644.036 mm3), two bosses joining box and lid, a snap fit on the
  lid's wall: each changes the volumes it must.
Path 3, Design Advice: the walls without draft for the mould's pull, as numbers.
Path 4, UTILITIES > MAKE: print_part to a slicer found on this computer (a stand-in program
  that records the file it was given), print_part to a file, export_everything with a picture
  of the view; the design unchanged by them; each change one Undo step named AI: ...
"""

import os
import tempfile

import FreeCAD as App
from Fission180Tests.gui import ai_workspace_steps as ai
from Fission180Tests.gui import harness as h

S = {}
RIM = {
    "any_of": [
        {
            "type": "line",
            "parallel": [1, 0, 0],
            "at": [{"axis": "z", "value": 20}, {"axis": "y", "value": 2}],
            "count": 1,
        },
        {
            "type": "line",
            "parallel": [1, 0, 0],
            "at": [{"axis": "z", "value": 20}, {"axis": "y", "value": 38}],
            "count": 1,
        },
        {
            "type": "line",
            "parallel": [0, 1, 0],
            "at": [{"axis": "z", "value": 20}, {"axis": "x", "value": 2}],
            "count": 1,
        },
        {
            "type": "line",
            "parallel": [0, 1, 0],
            "at": [{"axis": "z", "value": 20}, {"axis": "x", "value": 58}],
            "count": 1,
        },
    ],
    "count": 4,
}


def _volumes():
    from fission180 import bodies

    return {b.Label: b.Shape.Volume for b in bodies.solid_bodies(App.ActiveDocument)}


# -- Path 1 -------------------------------------------------------------------------------------
def halves():
    ai.ok("new_design", {"name": "AiEnclosure"})
    rule = ai.ok("plastic_rule", {"rule": "ABS 2 mm"}, ["Plastic rule ABS 2 mm"])
    h.check("the ABS 2 mm rule: 2 mm walls", '"thickness"' in rule["text"], rule["text"][:300])
    ai.ok(
        "create_sketch",
        {"plane": "XY", "geometry": [{"rect": [0, 0, 60, 40]}], "name": "Box sketch"},
    )
    ai.ok("extrude", {"profile": "Sketch1", "distance": 20})
    ai.ok("rename", {"target": "Body", "name": "Box"})  # (the body new_design made)
    ai.ok("shell", {"faces": {"normal": [0, 0, 1], "count": 1}, "thickness": 2})
    ai.ok(
        "create_sketch",
        {"plane": "XY", "offset": 20, "geometry": [{"rect": [0, 0, 60, 40]}], "name": "Lid sketch"},
    )
    ai.ok("extrude", {"profile": "Sketch2", "distance": 10, "operation": "new_body", "name": "Lid"})
    ai.ok("shell", {"faces": {"normal": [0, 0, -1], "count": 1}, "thickness": 2})
    vols = _volumes()
    h.check(
        "the open box and lid with 2 mm walls",
        ai.near(vols.get("Box"), 60 * 40 * 20 - 56 * 36 * 18, 1e-6)
        and ai.near(vols.get("Lid"), 60 * 40 * 10 - 56 * 36 * 8, 1e-6),
        vols,
    )


# -- Path 2 -------------------------------------------------------------------------------------
def lip_bosses_snap():
    ai.ok(
        "lip",
        {
            "edges": RIM,
            "of": "Shell1",
            "lip_width": 1,
            "lip_height": 1,
            "clearance": 0.1,
            "clearance_height": 0.1,
            "inner_draft": 0,
            "outer_draft": 0,
        },
    )
    vols = _volumes()
    h.check(
        "the lip on the box's rim, the groove in the lid (golden plastic2_lip_and_groove)",
        ai.near(vols["Box"], 11900.0, 1e-5) and ai.near(vols["Lid"], 7644.036, 1e-5),
        vols,
    )
    S["after_lip"] = vols
    ai.ok(
        "boss",
        {
            "points": [[10, 10], [50, 30]],
            "plane": "XY",
            "offset": 20,
            "side1": {"draft": 0, "step_draft": 0, "root_radius": 0},
            "side2": {"draft": 0, "step_draft": 0, "root_radius": 0},
            "name": "Corner bosses",
        },
    )
    vols = _volumes()
    # (golden plastic_boss_enclosure: the bosses add 1485.936 mm3 to the box, 609.881 to the lid)
    h.check(
        "two bosses join box and lid",
        ai.near(vols["Box"] - S["after_lip"]["Box"], 13197.936411 - 11712.0, 1e-4)
        and ai.near(vols["Lid"] - S["after_lip"]["Lid"], 8481.881309 - 7872.0, 1e-4),
        vols,
    )
    S["after_boss"] = vols
    ai.ok(
        "snap_fit",
        {
            "points": [[58, 20]],
            "plane": "XY",
            "offset": 20,
            "fillet": 0,
            "draft": 0,
            "thickness": 2,
            "tip_thickness": 2,
            "clearance": 0.1,
            "loop_thickness": 2,
            "length": 12,
            "width": 6,
            "catch_depth": 1,
            "catch_length": 3,
            "name": "Side snap",
        },
    )
    vols = _volumes()
    h.check(
        "a snap fit: the hook hangs from the lid, the catch is cut in the box's wall",
        vols["Lid"] > S["after_boss"]["Lid"] + 50 and vols["Box"] < S["after_boss"]["Box"],
        (vols, S["after_boss"]),
    )
    check = ai.ok("check_design", {})["data"]
    h.check("check_design: both halves are sound solids", check.get("ok") is True, check)


# -- Path 3 -------------------------------------------------------------------------------------
def advice():
    before = _volumes()
    found = ai.ok("design_advice", {"checks": ["draft"], "pull": [0, 0, 1]})["data"]
    labels = sorted(b["label"] for b in found["bodies"])
    h.check(
        "Design Advice: both halves checked against ABS 2 mm, the straight walls found without "
        "draft for the pull",
        labels == ["Box", "Lid"]
        and all(b["rule"] == "ABS 2 mm" for b in found["bodies"])
        and found["counts"].get("draft", 0) > 0,
        str(found)[:600],
    )
    h.check("... and changed nothing", _volumes() == before)


# -- Path 4 -------------------------------------------------------------------------------------
def make():
    from fission180 import export_ui
    from Fission180Tests.gui import insert_steps as ins

    folder = tempfile.mkdtemp(prefix="fission180-slicer-")
    log = os.path.join(folder, "slicer.log")
    program = os.path.join(folder, "prusa-slicer")
    with open(program, "w") as handle:
        handle.write('#!/bin/sh\necho "$@" >> "%s"\n' % log)
    os.chmod(program, 0o755)
    export_ui.SLICER_ENV = {"PATH": folder, "HOME": folder}
    ins.real_program_start()
    del ins.started_programs[:]
    before = _volumes()
    try:
        sent = ai.ok("print_part", {"send_to": "prusaslicer"}, ["Sent to PrusaSlicer"])["data"]
        h.wait_for(
            lambda: os.path.isfile(log) and bool(open(log).read().strip()),
            "the stand-in slicer to write the file it was given",
        )
        given = open(log).read().strip()
        h.check(
            "the slicer got the 3MF of both halves, in mm, watertight",
            given.endswith(".3mf")
            and given == sent["file"]
            and sent["unit"] == "Millimeter"
            and sorted(sent["watertight"]) == ["Box", "Lid"]
            and all(sent["watertight"].values()),
            (given, sent),
        )
        out = os.path.join(h.OUT_DIR, "ai-plastic")
        os.makedirs(out, exist_ok=True)
        for name in os.listdir(out):
            os.remove(os.path.join(out, name)) if os.path.isfile(os.path.join(out, name)) else None
        saved = ai.ok(
            "print_part",
            {"path": os.path.join(out, "lid.stl"), "bodies": ["Lid"], "format": "STL (Binary)"},
            ["Saved"],
        )["data"]
        h.check(
            "the lid alone saved as an STL",
            os.path.isfile(saved["file"]) and saved["bodies"] == ["Lid"],
            saved,
        )
        every = ai.ok(
            "export_everything", {"folder": os.path.join(out, "handover")}, ["Exported 6 files"]
        )["data"]
        h.check(
            "Export Everything: STEP, STL, 3MF, OBJ, a picture of the view and a README",
            sorted(every["files"]) == ["3mf", "obj", "png", "readme", "step", "stl"],
            sorted(every["files"]),
        )
    finally:
        export_ui.SLICER_ENV = None
        export_ui.START_PROGRAM = None
    h.check("UTILITIES > MAKE changed nothing in the design", _volumes() == before)
    names = ai.undo_names()
    h.check(
        "each change one Undo step named AI: ...",
        names and all(n.startswith("AI:") for n in names) and names[0] == "AI: Snap fit (parallel)",
        names[:5],
    )


h.run(
    "ai_workspace_plastic",
    [ai.start, halves, lip_bosses_snap, advice, make, ai.stop],
    paced_by="state",
)
