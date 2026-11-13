# SPDX-License-Identifier: LGPL-2.1-or-later
"""An AI app repairs a broken mesh and works the MESH tab through MCP (wave 8, builder ai-mesh):
the real MCP server and the bridge, as in ai_agent_e2e; the window shows each step as the
MESH dialogs leave it.

Path 1, the AI app starts, AI control on; the test writes a 20 x 10 x 5 box mesh with one
  triangle missing (a hole) and one turned the wrong way.
Path 2, import_file it; inspect_mesh says it is not closed: 1 hole, a flipped face, and to run
  mesh_prepare kind repair; convert_mesh is refused in words.
Path 3, mesh_prepare kind repair: closed, 1000 mm3; the repaired body is shown, the broken one
  hidden (used up), both carry the body's name; inspect_mesh says closed; one undo step.
Path 4, convert_mesh: a six-face solid of 1000 mm3.
Path 5, the other MESH tools on the repaired mesh: face groups from a face pick, a plane cut
  (the body 4 mm high, the cut closed), Direct Edit moving the top faces up again, a section
  sketch in the window, Undo and Redo of an AI mesh step.
Path 6, tessellate the solid: a mesh body with six face groups (coloured), the solid used up.
Path 7, AI control off again.
"""

import os
import tempfile

import FreeCAD as App
from Fission180Tests.gui import ai_workspace_steps as ai
from Fission180Tests.gui import harness as h

S = {}
TOP4 = {"box": [-1, -1, 3.9, 21, 11, 4.1], "facing": {"normal": [0, 0, 1], "within": 5}}


def _shown(obj):
    try:
        return bool(obj.ViewObject.Visibility)
    except Exception:
        return False


def _meshes():
    from fission180 import mesh

    return mesh.mesh_bodies(App.ActiveDocument)


# -- Path 1 -------------------------------------------------------------------------------------
def write_broken_mesh():
    import Mesh

    x, y, z = 20.0, 10.0, 5.0
    pts = [
        (0, 0, 0), (x, 0, 0), (x, y, 0), (0, y, 0),
        (0, 0, z), (x, 0, z), (x, y, z), (0, y, z),
    ]  # fmt: skip
    quads = [(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (1, 2, 6, 5), (2, 3, 7, 6), (3, 0, 4, 7)]
    facets = []
    for a, b, c, d in quads:
        facets += [(a, b, c), (a, c, d)]
    facets.pop(2)  # the top's first triangle: a hole
    facets[-1] = tuple(reversed(facets[-1]))  # a triangle of the -X side the wrong way round
    mesh = Mesh.Mesh([[pts[i] for i in f] for f in facets])
    folder = tempfile.mkdtemp(prefix="fission180-broken-")
    S["path"] = os.path.join(folder, "broken-box.stl")
    mesh.write(S["path"])
    h.check("the broken box is written (11 triangles)", mesh.CountFacets == 11, mesh.CountFacets)


# -- Path 2 -------------------------------------------------------------------------------------
def inspect_says_broken():
    ai.ok("new_design", {"name": "Broken box"})
    ai.ok("import_file", {"path": S["path"], "label": "Scan"}, ["as a mesh body"])
    answer = ai.ok(
        "inspect_mesh",
        {},
        ["not closed (1 hole, ", "flipped face", "mesh_prepare kind repair"],
    )
    data = answer["data"] or {}
    h.check(
        "inspect_mesh counts the hole and the flipped face",
        data.get("holes") == 1 and data.get("flipped", 0) >= 1 and data.get("closed") is False,
        data,
    )
    ai.refused("convert_mesh", {}, ["is not closed", "mesh_prepare kind repair"])
    h.check("nothing changed", not ai.undo_names(), ai.undo_names())
    S["broken"] = _meshes()[0]


# -- Path 3 -------------------------------------------------------------------------------------
def repair():
    ai.ok("mesh_prepare", {"kind": "repair"}, ["closed (watertight)", "1000 mm3"])
    found = _meshes()
    h.check("still one mesh body", len(found) == 1, found)
    repaired = found[0] if found else None
    S["repaired"] = repaired
    h.check(
        "the repaired body is shown, the broken one hidden",
        repaired is not None and _shown(repaired) and not _shown(S["broken"]),
    )
    h.check(
        "both carry the body's name",
        repaired is not None and repaired.Label == "Scan" and S["broken"].Label == "Scan",
        (repaired.Label if repaired else None, S["broken"].Label),
    )
    h.check("closed in the model", repaired is not None and repaired.Mesh.isSolid())
    answer = ai.ok("inspect_mesh", {}, ["closed and clean"])
    h.check("inspect_mesh: 1000 mm3", ai.near((answer["data"] or {}).get("volume"), 1000, 1e-6))
    h.check("one undo step: AI: Repair", ai.undo_names() == ["AI: Repair"], ai.undo_names())


# -- Path 4 -------------------------------------------------------------------------------------
def convert():
    from fission180 import bodies

    ai.ok("convert_mesh", {"name": "Box solid"}, ["Box solid", "6 big flat faces"])
    solids = bodies.solid_bodies(App.ActiveDocument)
    h.check(
        "a six-face solid of 1000 mm3",
        len(solids) == 1
        and len(solids[0].Shape.Faces) == 6
        and ai.near(solids[0].Shape.Volume, 1000, 1e-9),
        [(s.Label, len(s.Shape.Faces), s.Shape.Volume) for s in solids],
    )
    ai.ok("undo")
    h.check("undone: no solid", not bodies.solid_bodies(App.ActiveDocument))
    h.check("... and the mesh body shown again", _shown(_meshes()[0]), _meshes())


# -- Path 5 -------------------------------------------------------------------------------------
def more_mesh_tools():
    ai.ok(
        "mesh_prepare",
        {"kind": "create_face_group", "faces": {"points": [[10, 5, 0]]}},
        ["face group"],
    )
    body = _meshes()[0]
    h.check(
        "the body has face groups, drawn in colour",
        len(set(body.FaceGroups)) == 2 and bool(body.ViewObject.Coloring),
        (list(body.FaceGroups), body.ViewObject.Coloring),
    )
    ai.ok(
        "mesh_modify",
        {"kind": "plane_cut", "plane": "XY", "distance": 4},
        ["20 x 10 x 4 mm", "closed (watertight)", "800 mm3"],
    )
    ai.ok(
        "mesh_modify",
        {
            "kind": "direct_edit",
            "edits": [{"op": "move", "faces": TOP4, "direction": "z", "distance": 1}],
        },
        ["20 x 10 x 5 mm", "1000 mm3"],
    )
    names = ai.undo_names()
    ai.ok("undo")
    h.check(
        "Undo takes the Direct Edit back (4 mm high again)",
        ai.near(_meshes()[0].Mesh.BoundBox.ZLength, 4, 1e-6),
        _meshes()[0].Mesh.BoundBox,
    )
    ai.ok("redo")
    h.check(
        "Redo brings it again",
        ai.near(_meshes()[0].Mesh.BoundBox.ZLength, 5, 1e-6) and ai.undo_names() == names,
        (ai.undo_names(), names),
    )
    ai.ok("mesh_section_sketch", {"plane": "XY", "distance": 2, "name": "Outline"}, ["1 loop"])
    sketches = [o for o in App.ActiveDocument.Objects if o.Label == "Outline"]
    h.check(
        "the section sketch is in the design: a 20 x 10 loop",
        len(sketches) == 1
        and ai.near(sketches[0].Shape.BoundBox.XLength, 20, 1e-6)
        and ai.near(sketches[0].Shape.BoundBox.YLength, 10, 1e-6),
        sketches,
    )
    h.check(
        "each change one undo step named AI: ...",
        all(n.startswith("AI:") for n in ai.undo_names()),
        ai.undo_names(),
    )


# -- Path 6 -------------------------------------------------------------------------------------
def tessellate():
    from fission180 import bodies

    ai.ok("new_design", {"name": "Tessellated"})
    ai.ok("primitive", {"kind": "box", "plane": "XY", "length": 30, "width": 20, "height": 10})
    solid = bodies.solid_bodies(App.ActiveDocument)[0]
    ai.ok("tessellate", {"body": solid.Name, "name": "Box mesh"}, ["6 face groups", "6000 mm3"])
    found = _meshes()
    h.check(
        "a mesh body with six face groups, in colour; the solid used up (hidden)",
        len(found) == 1
        and len(set(found[0].FaceGroups)) == 6
        and bool(found[0].ViewObject.Coloring)
        and not bodies.is_shown(solid),
        found,
    )


h.run(
    "ai_mesh_repair",
    [
        ai.start,
        write_broken_mesh,
        inspect_says_broken,
        repair,
        convert,
        more_mesh_tools,
        tessellate,
        ai.stop,
    ],
    paced_by="state",
)
