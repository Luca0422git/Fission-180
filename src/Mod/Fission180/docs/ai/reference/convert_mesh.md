# `convert_mesh`: Convert mesh

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: MESH > CONVERT > Convert Mesh. Category: Mesh. Changes the design (one undo step). Its undo step is named like "AI: Convert Mesh". Needs an open design.

## What it does

Make a solid body from a closed mesh body (MESH > Convert Mesh). A new body whose first step builds the solid, so fillet, chamfer, hole, press_pull, combine work on it. method prismatic (default): triangles in one plane become one flat face, round or free-form areas stay many small flat faces (Fission 180 fits no cylinders: use the rebuild route for true round holes); faceted: one face per triangle. operation parametric (default: follows later MESH steps of the mesh) or base_feature (made once). The mesh body is hidden. Refused for a mesh that is not closed (mesh_prepare kind repair first) and when it would take more than a minute (about 0.25 s per 1,000 triangles: mesh_modify kind reduce first, or allow_slow). Answers faces, volume against the mesh's and seconds. No timeline of features: that is start_rebuild.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `body` | string |  |  |  | the mesh body: its id (import_file answers it; any step of its history works) or name; default: the only mesh body of the design |
| `method` | `prismatic` \| `faceted` |  | `"prismatic"` |  | how the faces are made |
| `operation` | `parametric` \| `base_feature` |  | `"parametric"` |  | parametric follows the mesh; base_feature is made once |
| `allow_slow` | boolean |  | `false` |  | convert even when it is estimated to take more than a minute |
| `name` | string |  |  |  | the new solid body's name (default '<mesh> (solid)') |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: a solid body from the mesh, flat faces merged

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
{"tool": "convert_mesh", "args": {"name": "Plate solid"}}
```

The answer:

```text
Done: AI: Convert Mesh. The solid body 'Plate solid' (id 'Body001'): 54 faces from 208 triangles (flat faces merged; 6 big flat faces, the rest are the small flat facets of round or free-form areas), 23498.8 mm3 against the mesh's 23498.8 mm3 (0 % apart). The mesh body plate is hidden and kept (parametric: an edit of the mesh's steps updates the solid). Next: the solid takes fillet, chamfer, hole, press_pull, shell and combine like any body; for a timeline of real features instead (editable sizes), start_rebuild. Bodies now: Plate solid: 23498.8 mm3, 60 x 40 x 10 mm.
Took under a second.
```

## More argument examples

- the only mesh body as a solid, flat faces merged:
  `{}`
- one face per triangle, named:
  `{"body": "MeshBody", "method": "faceted", "name": "Scan solid"}`

## See also

- Recipe: [a mesh (STL, OBJ, 3MF, a scan) into a solid](fission180://docs/recipes/mesh-to-solid.md)
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
