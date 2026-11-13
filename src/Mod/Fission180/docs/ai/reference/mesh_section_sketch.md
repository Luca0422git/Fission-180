# `mesh_section_sketch`: Mesh section sketch

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: MESH > CREATE > Create Mesh Section Sketch. Category: Mesh. Changes the design (one undo step). Its undo step is named like "AI: Mesh Section Sketch". Needs an open design.

## What it does

Make a sketch of where a plane cuts a mesh body (Create Mesh Section Sketch). Fixed lines in a new sketch of the active body (made if there is none), on plane XY | XZ | YZ (or a construction plane's id) moved distance mm along its normal. Use it to trace a mesh's outline for a rebuild by hand: then redraw the outline with add_to_sketch lines, arcs and circles (a few clean curves, never the section's hundreds of segments) and extrude that. Answers the section's loops and segments and their box.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `body` | string |  |  |  | the mesh body: its id (import_file answers it; any step of its history works) or name; default: the only mesh body of the design |
| `plane` | string |  | `"XY"` |  | XY, XZ, YZ or the id of a construction plane |
| `distance` | number | mm | `0` |  | move the plane along its normal (mm) |
| `name` | string |  |  |  | the sketch's name (default 'Mesh Section <body>') |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: a sketch of the plate's outline and hole at 5 mm

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
{"tool": "mesh_section_sketch", "args": {"plane": "XY", "distance": 5}}
```

The answer:

```text
Done: AI: Mesh Section Sketch. The sketch 'Mesh Section plate' (id 'Sketch') on the XY plane (normal [0, 0, 1]) moved 5 mm holds the section: 2 loops (2 closed), 53 fixed segments, 60 x 40 x 0 mm. These segments trace the mesh's facets: to rebuild, draw the outline again with a few lines, arcs and circles (add_to_sketch, or create_sketch) and extrude that, not these segments. No solid body yet.
```

## More argument examples

- the outline 2.5 mm up the only mesh body:
  `{"plane": "XY", "distance": 2.5}`
- a side section:
  `{"body": "MeshBody", "plane": "XZ", "name": "Side section"}`

## See also

- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
