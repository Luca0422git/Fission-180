# `mesh_modify`: Modify mesh

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: MESH > MODIFY > Remesh, Reduce, Plane Cut, Shell, Smooth, Combine, Separate, Reverse Normal, Direct Edit, Erase and Fill, Delete Faces. Category: Mesh. Changes the design (one undo step). Its undo step is named like "AI: Plane Cut". Needs an open design.

## What it does

Change a mesh body as a MODIFY dialog does (one undo and timeline step; the body keeps its name). kind remesh (density 0..1); reduce (target tolerance mm | proportion % kept | face_count: before a slow convert); plane_cut (plane XY | XZ | YZ or a construction plane, moved distance mm, tilted angle_x / angle_y; trim removes the side its normal points to, XY +Z, XZ -Y, YZ +X, flip the other; split_body; split_faces; fill uniform can be slow on a cut through many holes: minimal is quick); shell (thickness mm); smooth (scans: it rounds a CAD part's edges); combine (tools; join | cut | intersect | merge; bodies sharing a flat face: exact up to 5,000 faces, else refused); separate; reverse_normal; erase_and_fill / delete_faces (faces); direct_edit (edits: delete, erase_fill, group, reverse, move, smooth). groups / faces limit smooth, reverse_normal, separate. Answers triangles, closed or not, time.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `kind` (required) | `remesh` \| `reduce` \| `plane_cut` \| `shell` \| `smooth` \| `combine` \| `separate` \| `reverse_normal` \| `erase_and_fill` \| `delete_faces` \| `direct_edit` |  |  |  |  |
| `body` | string |  |  |  | the mesh body: its id (import_file answers it; any step of its history works) or name; default: the only mesh body of the design |
| `remesh_type` | `adaptive` \| `uniform` |  | `"adaptive"` |  | remesh |
| `density` | number |  |  | >= 0, <= 1 | remesh / erase_and_fill: 0 coarse .. 1 fine |
| `shape_preservation` | number | 0..1 |  | >= 0, <= 1 | remesh adaptive: 0..1 |
| `preserve_sharp_edges` | boolean |  | `false` |  | remesh |
| `preserve_boundaries` | boolean |  | `false` |  | remesh: keep open edges |
| `target` | `tolerance` \| `proportion` \| `face_count` |  | `"tolerance"` |  | reduce |
| `tolerance` | number | mm |  | > 0 | reduce tolerance: largest deviation (mm) |
| `proportion` | number |  |  | > 0, <= 100 | reduce proportion: percent of the faces kept |
| `face_count` | integer |  |  | >= 4 | reduce face_count: faces kept |
| `reduce_type` | `adaptive` \| `uniform` |  | `"adaptive"` |  | reduce |
| `plane` | string |  |  |  | plane_cut: XY, XZ, YZ or the id of a construction plane |
| `distance` | number | mm |  |  | plane_cut: move the plane along its normal (mm) |
| `angle_x` | number | deg |  |  | plane_cut: tilt about the plane's x axis (degrees) |
| `angle_y` | number | deg |  |  | plane_cut: tilt about the plane's y axis (degrees) |
| `cut_type` | `trim` \| `split_body` \| `split_faces` |  | `"trim"` |  | plane_cut |
| `fill` | `uniform` \| `minimal` \| `no_fill` |  |  |  | plane_cut: how the cut is closed; erase_and_fill: uniform \| minimal |
| `flip` | boolean |  | `false` |  | plane_cut: remove the other side |
| `thickness` | number | mm |  | > 0 | shell: wall thickness (mm) |
| `smoothness` | number | 0..1 |  | >= 0, <= 1 | smooth: 0..1 |
| `tools` | array of strings |  |  | at least 1 item(s) | combine: the other mesh bodies' ids |
| `operation` | `join` \| `cut` \| `intersect` \| `merge` |  | `"join"` |  | combine |
| `keep_tools` | boolean |  | `false` |  | combine: keep the tool bodies |
| `separate_type` | `mesh_shells` \| `all_face_groups` \| `select_face_groups` |  | `"mesh_shells"` |  | separate |
| `keep_body` | boolean |  | `false` |  | separate: keep the original body too |
| `groups` | array of integers |  |  | at least 1 item(s) | smooth / reverse_normal / separate: face groups |
| `faces` | object |  |  |  | the faces (erase_and_fill, delete_faces; or the groups they are in). Faces of a mesh are its triangles, named by where they are, never by number: {"groups": [n, ...]} (face groups; inspect_mesh detail groups lists them), {"points": [[x, y, z], ...]} (the face at each point of the surface), {"ray": {"from": [x, y, z], "direction": [x, y, z]}} (the first face along it, like a click), {"box": [x0, y0, z0, x1, y1, z1]} (every face whose centre is inside) or {"all": true}; add "facing": {"normal": [x, y, z], "within": degrees} to keep only faces facing that way. |
| `edits` | array of objects |  |  | at least 1 item(s) | direct_edit: the edits, in order |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: kind is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: everything above 5 mm cut away, the cut closed

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 60, 40], "name": "base"}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 10}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 10, "geometry": [{"circle": [30, 20, 4]}]}},
  {"tool": "hole", "args": {"sketch": "Sketch2", "diameter": 8, "through_all": true}},
  {"tool": "export", "args": {"format": "stl", "path": "/home/me/fission180/plate.stl"}},
  {"tool": "new_design", "args": {"name": "Mesh"}},
  {"tool": "import_file", "args": {"path": "/home/me/fission180/plate.stl"}}
]
```

The call:

```json
{"tool": "mesh_modify", "args": {"kind": "plane_cut", "plane": "XY", "distance": 5, "fill": "minimal"}}
```

The answer:

```text
Done: AI: Plane Cut (208 -> 312 triangles). The body now: plate001 (id 'PlaneCut'): 312 triangles, 60 x 40 x 5 mm, closed (watertight), 11749.4 mm3. Cut at the XY plane (normal [0, 0, 1]). plate001 is closed and clean: convert_mesh (method prismatic) gives a solid in under a second. No solid body yet.
Took under a second.
```

## More argument examples

- fewer faces before a slow conversion:
  `{"kind": "reduce", "target": "face_count", "face_count": 5000}`
- trim away everything above z = 2.5, the cut closed:
  `{"kind": "plane_cut", "plane": "XY", "distance": 2.5}`
- hollow it with 1.5 mm walls:
  `{"kind": "shell", "thickness": 1.5}`
- remove the face at a point and fill the gap:
  `{"kind": "erase_and_fill", "faces": {"points": [[40, 30, 5]]}}`
- Direct Edit: the top faces moved up 1 mm:
  `{"kind": "direct_edit", "edits": [{"op": "move", "faces": {"box": [0, 0, 4.9, 80, 60, 5.1]}, "direction": "z", "distance": 1}]}`

## See also

- Recipe: [a mesh (STL, OBJ, 3MF, a scan) into a solid](fission180://docs/recipes/mesh-to-solid.md)
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
