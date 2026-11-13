# `tessellate`: Tessellate

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: MESH > CREATE > Tessellate. Category: Mesh. Changes the design (one undo step). Its undo step is named like "AI: Tessellate Body". Needs an open design.

## What it does

Make a mesh body from a solid body (MESH > Tessellate). One undo step; each face of the solid becomes a face group. refinement low | medium (default) | high | custom (surface_deviation mm, normal_deviation degrees); max_edge_length (mm) splits longer edges. The solid body is used up (hidden: the mesh body takes its place, as in Fusion; undo brings it back). Use it to reach the MESH tools from a design (shell, remesh for printing); to export an STL, export does it without changing the design.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `body` (required) | string |  |  |  | the solid body (or a step in it) |
| `refinement` | `low` \| `medium` \| `high` \| `custom` |  | `"medium"` |  |  |
| `surface_deviation` | number | mm |  | > 0 | custom: largest gap to the surface (mm) |
| `normal_deviation` | number | deg |  | >= 0.5, <= 90 | custom: largest angle between faces (degrees) |
| `max_edge_length` | number | mm |  | >= 0 | split edges longer than this (mm); 0: no limit |
| `name` | string |  |  |  | the new mesh body's name (default: the solid's) |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: body is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: the plate as a mesh body, one face group per face

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 60, 40], "name": "base"}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 10}}
]
```

The call:

```json
{"tool": "tessellate", "args": {"body": "Body", "name": "Plate mesh"}}
```

The answer:

```text
Done: AI: Tessellate Body. The mesh body Plate mesh (id 'Tessellate'): 12 triangles, 60 x 40 x 10 mm, closed (watertight), 24000 mm3; 6 face groups (one per face of Body1). Body1 is used up by it (hidden; undo brings it back). Plate mesh is closed and clean: convert_mesh (method prismatic) gives a solid in under a second. Bodies now: Body1: 24000 mm3, 60 x 40 x 10 mm.
Took under a second.
```

## More argument examples

- the body as a mesh body, medium refinement:
  `{"body": "Body"}`
- a finer mesh, named:
  `{"body": "Body", "refinement": "high", "name": "Print mesh"}`

## See also

- Recipe: [a mesh (STL, OBJ, 3MF, a scan) into a solid](fission180://docs/recipes/mesh-to-solid.md)
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
