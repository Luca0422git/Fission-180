# `inspect_mesh`: Inspect mesh

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: MESH > PREPARE > Repair (its analysis), Properties of a mesh body. Category: Mesh. Read-only. Needs an open design.

## What it does

Read a mesh body before changing it (an STL / OBJ / 3MF from import_file, a tessellated body or a MESH step). It answers triangles, size, closed or what is wrong (holes, flipped faces, edges with more than two faces, separate shells), volume, face groups, the shapes it is made of (overview: its big flat faces, and its small round or free-form details grouped, with a grid or ring of equal ones found: what to rebuild as features) and advice: the next call and how long it takes. Call it first on any mesh, then ask the person what they want (a solid to cut and print now, or an editable timeline). detail groups also lists every face group. Changes nothing; under a second for 10,000 triangles.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `body` | string |  |  |  | the mesh body: its id (import_file answers it; any step of its history works) or name; default: the only mesh body of the design |
| `detail` | `summary` \| `groups` |  | `"summary"` |  | summary: numbers, overview, advice; groups: also each face group |
| `self_intersections` | boolean |  | `false` |  | also count where the mesh crosses itself (slow on big meshes) |

## Answer

A plain sentence, then JSON with: `body`, `label`, `triangles`, `points`, `size`, `box`, `area`, `closed`, `volume`, `problems`, `holes`, `open_edges`, `non_manifold`, `flipped`, `shells`, `duplicated`, `degenerate`, `inside_out`, `face_groups`, `overview`, `estimates`, `advice`. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: the plate's mesh: closed, its shapes, and what to do next

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
{"tool": "inspect_mesh", "args": {}}
```

The answer:

```text
plate (id 'MeshBody'): 208 triangles, 60 x 40 x 10 mm, closed (watertight), 23498.8 mm3. A part 60 x 40 x 10 mm: 96 % of its area is 6 big flat faces (most facing along z), and 1 small detail (round or free-form: facets of curved surfaces): 1 round through hole about 8 x 8 mm, through the 10 mm, on its -z face. plate is closed and clean: convert_mesh (method prismatic) gives a solid in under a second.
{
 "body": "MeshBody",
 "label": "plate",
 "triangles": 208,
 "points": 104,
 "size": [60.0, 40.0, 10.0],
 "box": [0.0, 0.0, 0.0, 60.0, 40.0, 10.0],
 "area": 6950.909668,
 "closed": true,
 "volume": 23498.779427,
 "problems": [],
 "holes": 0,
 "open_edges": 0,
 "non_manifold": 0,
 "flipped": 0,
 "shells": 1,
 "duplicated": 0,
 "degenerate": 0,
 "inside_out": false,
 "face_groups": 1,
 "overview": {
  "triangles": 208,
  "size": [60.0, 40.0, 10.0],
  "flat_faces": 6,
  "flat_share": 0.9639,
  "axis": "z",
  "details": 1,
  "detail_groups": [
   {
    "count": 1,
    "kind": "round through hole",
    "face": "-z",
    "footprint": [8.0, 8.0],
    "height": 10.0,
    "triangles": 96,
    "centres": [[30.0, 20.0, 5.0]]
   }
  ],
  "words": "A part 60 x 40 x 10 mm: 96 % of its area is 6 big flat faces (most facing along z), and 1 small detail (round or free-form: facets of curved surfaces): 1 round through hole about 8 x 8 mm, through the 10 mm, on its -z face."
 },
 "estimates": {"convert_prismatic_s": 0.2, "convert_faceted_s": 0.2},
 "advice": "plate is closed and clean: convert_mesh (method prismatic) gives a solid in under a second."
}
```

## More argument examples

- the only mesh body: closed?, size, shapes, what to do next:
  `{}`
- with every face group:
  `{"body": "MeshBody", "detail": "groups"}`

## See also

- Recipe: [a mesh (STL, OBJ, 3MF, a scan) into a solid](fission180://docs/recipes/mesh-to-solid.md)
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
