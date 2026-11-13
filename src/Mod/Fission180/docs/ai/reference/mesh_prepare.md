# `mesh_prepare`: Prepare mesh

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: MESH > PREPARE > Repair, Generate Face Groups, Create Face Group, Combine Face Groups; MESH > MODIFY > Make Closed Mesh. Category: Mesh. Changes the design (one undo step). Its undo step is named like "AI: Generate Face Groups". Needs an open design.

## What it does

Get a mesh body ready, as the PREPARE dialogs do (one undo step, a step in the timeline). kind repair: close holes and fix flipped faces (repair_type close_holes | stitch_and_remove, the default: also joins cracks and drops loose bits | wrap: also inner shells and crossings | rebuild: a new closed surface from voxels, density 8..256). kind make_closed: Make Closed Mesh (repair rebuild, accurate): always closed, sharp details softened. kind generate_face_groups: faces split into groups by angle (method fast, angle degrees) or by fitted plane / cylinder / sphere (accurate). kind create_face_group: the faces given become one group; combine_face_groups: groups that touch become one. The answer says closed or what is left, with the next call. inspect_mesh first says which repair fits.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `kind` (required) | `repair` \| `make_closed` \| `generate_face_groups` \| `create_face_group` \| `combine_face_groups` |  |  |  |  |
| `body` | string |  |  |  | the mesh body: its id (import_file answers it; any step of its history works) or name; default: the only mesh body of the design |
| `repair_type` | `close_holes` \| `stitch_and_remove` \| `wrap` \| `rebuild` |  | `"stitch_and_remove"` |  | repair: how far it goes |
| `rebuild_type` | `fast` \| `preserve_sharp_edges` \| `accurate` \| `blocky` |  |  |  | repair rebuild / make_closed |
| `density` | integer |  |  | >= 8, <= 256 | rebuild: cells along the longest side |
| `offset` | number | mm |  |  | rebuild accurate: grow (+) or shrink (-) the surface (mm) |
| `method` | `fast` \| `accurate` |  | `"fast"` |  | generate_face_groups |
| `angle` | number | deg |  | > 0, <= 90 | generate_face_groups fast: degrees between groups |
| `min_size` | number | 0..1 |  | >= 0, <= 1 | generate_face_groups fast: smallest group as a share of the area (0..1) |
| `tolerance` | number | 0..1 |  | > 0, <= 1 | generate_face_groups accurate: as a share of the body's size (0..1) |
| `faces` | object |  |  |  | create / combine face groups: the faces. Faces of a mesh are its triangles, named by where they are, never by number: {"groups": [n, ...]} (face groups; inspect_mesh detail groups lists them), {"points": [[x, y, z], ...]} (the face at each point of the surface), {"ray": {"from": [x, y, z], "direction": [x, y, z]}} (the first face along it, like a click), {"box": [x0, y0, z0, x1, y1, z1]} (every face whose centre is inside) or {"all": true}; add "facing": {"normal": [x, y, z], "within": degrees} to keep only faces facing that way. |
| `groups` | array of integers |  |  | at least 1 item(s) | combine_face_groups: the groups joined |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: kind is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: the mesh's faces grouped by the way they face

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
{"tool": "mesh_prepare", "args": {"kind": "generate_face_groups"}}
```

The answer:

```text
Done: AI: Generate Face Groups (208 -> 208 triangles). The body now: plate001 (id 'FaceGroups'): 208 triangles, 60 x 40 x 10 mm, closed (watertight), 23498.8 mm3. plate001 has 7 face groups (inspect_mesh detail groups lists them). plate001 is closed and clean: convert_mesh (method prismatic) gives a solid in under a second. No solid body yet.
Took under a second.
```

## More argument examples

- close the holes of the only mesh body, flipped faces turned:
  `{"kind": "repair"}`
- a broken scan rebuilt closed:
  `{"kind": "repair", "body": "MeshBody", "repair_type": "rebuild", "density": 160}`
- face groups by angle:
  `{"kind": "generate_face_groups", "angle": 20}`
- the top faces become one face group:
  `{"kind": "create_face_group", "faces": {"box": [0, 0, 4.9, 80, 60, 5.1]}}`

## See also

- Recipe: [a mesh (STL, OBJ, 3MF, a scan) into a solid](fission180://docs/recipes/mesh-to-solid.md)
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
