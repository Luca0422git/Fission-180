# SPDX-License-Identifier: LGPL-2.1-or-later
"""An AI app turns a Relic-like mesh into a solid through MCP (wave 8, builder ai-mesh): the
real MCP server (fission180_mcp.py) is started as an AI app starts it and passes every call to
Fission 180's AI bridge, as in ai_agent_e2e. Luca's Relic (an STL of 8,486 triangles, a plate
with a field of small round dots) stays his: the test writes stand-ins
(Fission180Tests/headless/mesh_tools.py): a plate 80 x 60 x 5 with a 10 x 8 grid of 3 mm holes
2 mm deep (about 9,000 triangles) and the same plate with a 10 x 8 grid of 3 mm domes.

Path 1, the AI app starts, AI control on; the stand-ins are written.
Path 2, import_file the holes plate: one mesh body in the window; inspect_mesh says closed,
  the triangles, the volume, and what it is made of (80 equal round recesses in a 10 x 8 grid).
Path 3, convert_mesh prismatic: a solid body of the mesh's volume, its flat faces merged (one
  top face with 80 holes, one bottom, 80 hole floors), in seconds; the mesh hidden, the solid
  shown; one undo step "AI: Convert Mesh".
Path 4, a fillet on the solid's four corners: the volume drops by exactly the corners' share,
  the solid stays valid: a usable solid.
Path 5, undo back to the mesh; start_rebuild on it says what it is made of and the quick route;
  describe_reference reads a plan (holes and a pattern).
Path 6, the dome plate: describe_reference reads no plan and says so plainly, with the two
  honest routes (convert_mesh, or the main shapes by hand with a 10 x 8 rectangular pattern) in
  a short answer; route (1) taken: undo, convert_mesh.
Path 7, AI control off again.
"""

import math
import os
import re
import tempfile

import FreeCAD as App
from Fission180Tests.gui import ai_workspace_steps as ai
from Fission180Tests.gui import harness as h

S = {}
HOLES_VOLUME = 80 * 60 * 5 - 80 * math.pi * 1.5**2 * 2  # 22869.03 (round holes)
CORNERS = {
    "any_of": [
        {
            "type": "line",
            "parallel": [0, 0, 1],
            "at": [{"axis": "x", "value": x}, {"axis": "y", "value": y}],
            "count": 1,
        }
        for x in (0, 80)
        for y in (0, 60)
    ],
    "count": 4,
}


def _took(answer):
    """The seconds an answer says it took ("Took about 3 s.", "Took under a second.")."""
    if "Took under a second" in answer["text"]:
        return 0.5
    found = re.search(r"Took about (\d+) (s|minutes)", answer["text"])
    if not found:
        return None
    return float(found.group(1)) * (60 if found.group(2) == "minutes" else 1)


def _solids():
    from fission180 import bodies

    return bodies.solid_bodies(App.ActiveDocument)


def _shown(obj):
    try:
        return bool(obj.ViewObject.Visibility)
    except Exception:
        return False


# -- Path 1 -------------------------------------------------------------------------------------
def write_stand_ins():
    from Fission180Tests.headless import mesh_tools

    folder = tempfile.mkdtemp(prefix="fission180-relic-")
    S["holes"] = os.path.join(folder, "relic-holes.stl")
    S["domes"] = os.path.join(folder, "relic-domes.stl")
    S["holes_n"] = mesh_tools.write_stl(S["holes"], "holes")
    S["domes_n"] = mesh_tools.write_stl(S["domes"], "domes")
    h.check(
        "the stand-ins are about Relic's size (8,486 triangles)",
        6000 < S["holes_n"] < 12000 and 6000 < S["domes_n"] < 10000,
        (S["holes_n"], S["domes_n"]),
    )


write_stand_ins.timeout_s = 120  # (two solids with 80 holes / domes, meshed)


# -- Path 2 -------------------------------------------------------------------------------------
def insert_and_inspect():
    from fission180 import mesh

    ai.ok("new_design", {"name": "Relic stand-in"})
    ai.ok("import_file", {"path": S["holes"], "label": "Relic"}, ["as a mesh body"])
    found = mesh.mesh_bodies(App.ActiveDocument)
    h.check("one mesh body in the window, shown", len(found) == 1 and _shown(found[0]), found)
    S["mesh"] = found[0] if found else None
    undo_before = ai.undo_names()
    answer = ai.ok(
        "inspect_mesh",
        {},
        ["closed (watertight)", "80 equal round recesses", "in a 10 x 8 grid", "convert_mesh"],
    )
    data = answer["data"] or {}
    h.check("inspect_mesh counts the triangles", data.get("triangles") == S["holes_n"], data)
    volume = S["mesh"].Mesh.Volume if S["mesh"] is not None else 0
    h.check("... and gives the mesh's volume", ai.near(data.get("volume"), volume, 1e-4), data)
    h.check(
        "... and its shapes: 6 big flat faces, 80 details",
        (data.get("overview") or {}).get("flat_faces") == 6
        and (data.get("overview") or {}).get("details") == 80,
        data.get("overview"),
    )
    h.check("inspect_mesh changed nothing", ai.undo_names() == undo_before, ai.undo_names())


# -- Path 3 -------------------------------------------------------------------------------------
def convert():
    answer = ai.ok("convert_mesh", {"method": "prismatic"}, ["flat faces merged", "is hidden"])
    solids = _solids()
    h.check("a solid body now", len(solids) == 1, solids)
    if not solids:
        return
    shape = solids[0].Shape
    mesh_volume = S["mesh"].Mesh.Volume
    h.check(
        "its volume is the mesh's",
        ai.near(shape.Volume, mesh_volume, 1e-4),
        (shape.Volume, mesh_volume),
    )
    h.check(
        "... within 0.1 % of the true part's (round holes)",
        ai.near(shape.Volume, HOLES_VOLUME, 1e-3),
        (shape.Volume, HOLES_VOLUME),
    )
    flat = {}
    for face in shape.Faces:
        if face.Surface.TypeId == "Part::GeomPlane" and abs(face.normalAt(0, 0).z) > 0.9999:
            z = round(face.CenterOfMass.z, 3)
            flat[z] = flat.get(z, 0) + 1
    h.check(
        "flat faces merged: one top (with its 80 holes), one bottom, 80 hole floors",
        flat == {5.0: 1, 0.0: 1, 3.0: 80},
        flat,
    )
    h.check(
        "fewer faces than triangles",
        len(shape.Faces) < S["holes_n"] / 3,
        (len(shape.Faces), S["holes_n"]),
    )
    took = _took(answer)
    h.check("it took seconds, not minutes", took is not None and took < 30 * h.SLOWDOWN, took)
    h.check("the mesh is hidden, the solid shown", not _shown(S["mesh"]) and _shown(solids[0]))
    h.check("one undo step: AI: Convert Mesh", ai.undo_names()[:1] == ["AI: Convert Mesh"])
    S["solid_volume"] = shape.Volume


convert.timeout_s = 120


# -- Path 4 -------------------------------------------------------------------------------------
def fillet_the_solid():
    ai.ok("fillet", {"edges": CORNERS, "radius": 3})
    solids = _solids()
    shape = solids[0].Shape if solids else None
    corners = 4 * (9 - 9 * math.pi / 4) * 5
    h.check(
        "the fillet took the four corners off the converted solid",
        shape is not None and ai.near(S["solid_volume"] - shape.Volume, corners, 1e-3),
        (S.get("solid_volume"), shape.Volume if shape else None, corners),
    )
    h.check("the filleted solid is valid", shape is not None and shape.isValid())


fillet_the_solid.timeout_s = 120


# -- Path 5 -------------------------------------------------------------------------------------
def rebuild_reads_a_plan():
    ai.ok("undo")
    ai.ok("undo")
    h.check("back to the mesh alone", not _solids(), _solids())
    ai.ok(
        "start_rebuild",
        {"body": "Relic"},
        ["is the reference now", "What the mesh is made of", "10 x 8 grid", "convert_mesh"],
    )
    answer = ai.ok("describe_reference", {}, ['"plan"'])
    plan = (answer["data"] or {}).get("plan") or []
    tools = [step.get("tool") for step in plan]
    h.check(
        "describe_reference's plan: the plate, the hole, the pattern",
        "extrude" in tools and "hole" in tools and "rectangular_pattern" in tools,
        tools,
    )
    h.check("the plan is short", len(plan) <= 8, len(plan))
    ai.ok("undo")


rebuild_reads_a_plan.timeout_s = 120


# -- Path 6 -------------------------------------------------------------------------------------
def domes_honest_routes():
    ai.ok("new_design", {"name": "Dome plate"})
    ai.ok("import_file", {"path": S["domes"], "label": "Domes"})
    ai.ok("start_rebuild", {"body": "Domes"}, ["80 equal round bumps", "convert_mesh"])
    answer = ai.ok(
        "describe_reference",
        {},
        [
            "No plan could be read from this mesh",
            "Two honest routes",
            "convert_mesh",
            "rectangular_pattern of 10 x 8, 8 x 7.5 mm apart",
            "Never one feature per facet",
        ],
    )
    h.check(
        "the answer is short (no list of every facet)",
        len(answer["text"]) < 20000,
        len(answer["text"]),
    )
    h.check(
        "it says it read no base",
        ((answer["data"] or {}).get("base") or {}).get("kind") == "none",
        (answer["data"] or {}).get("base"),
    )
    # route (1), what most people want: a solid now
    ai.ok("undo")
    answer = ai.ok("convert_mesh", {}, ["flat faces merged"])
    solids = _solids()
    from fission180 import mesh

    domes = mesh.mesh_bodies(App.ActiveDocument)
    h.check(
        "the dome plate is a solid of the mesh's volume",
        solids and domes and ai.near(solids[0].Shape.Volume, domes[0].Mesh.Volume, 1e-4),
        (solids, domes),
    )
    took = _took(answer)
    h.check("in seconds", took is not None and took < 30 * h.SLOWDOWN, took)


domes_honest_routes.timeout_s = 180


h.run(
    "ai_mesh_relic",
    [
        ai.start,
        write_stand_ins,
        insert_and_inspect,
        convert,
        fillet_the_solid,
        rebuild_reads_a_plan,
        domes_honest_routes,
        ai.stop,
    ],
    paced_by="state",
)
