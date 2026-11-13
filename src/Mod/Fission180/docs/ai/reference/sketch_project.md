# `sketch_project`: Project / Include

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: SKETCH > CREATE > Project / Include (Project, Intersect, Include 3D Geometry, Project to Surface, Isoparametric Curve). Category: Sketch. Changes the design (one undo step). Its undo step is named like "AI: Project". Needs an open design.

## What it does

Bring model geometry into a sketch; it follows the model. project: edges / faces (their outline) / body (every edge) of body of (default: the sketch's body; another body or component works too) flattened onto the sketch (purple, they make profiles); include_3d: the same as reference curves (no profiles); intersect: where the sketch plane cuts faces / edges / body; project_to_surface: the sketch's curves (indexes) landed on faces as 3D curves (along closest | normal); isoparametric: U or V curves of one face (direction, fraction 0..1 or count spread evenly). Answers what came in.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `sketch` (required) | string |  |  |  | the sketch |
| `kind` (required) | `project` \| `include_3d` \| `intersect` \| `project_to_surface` \| `isoparametric` |  |  |  |  |
| `of` | string |  |  |  | the body the selectors look at (default: the sketch's body) |
| `edges` | object |  |  |  | model edges (an edge selector: filters type, parallel, radius, on_faces, not_on_faces, at, all, count, any_of; see get_help topic selectors). Give count. |
| `faces` | object |  |  |  | model faces (a face selector: filters type, normal, along, radius, at, all, count, any_of; see get_help topic selectors). Give count. |
| `body` | boolean |  | `false` |  | every edge of the body |
| `curves` | array of integers |  |  | at least 1 item(s) | project_to_surface: sketch curve indexes |
| `along` | `closest` \| `normal` |  | `"closest"` |  | project_to_surface |
| `direction` | `U` \| `V` |  | `"U"` |  | isoparametric |
| `fraction` | number | 0..1 |  | >= 0, <= 1 | isoparametric: 0..1 across the face |
| `count` | integer | count |  | >= 1, <= 50 | isoparametric: curves spread evenly |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: sketch is missing; kind is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: the plate's top outline into the sketch above it

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 60, 40], "name": "base"}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 10}},
  {"tool": "create_curve_sketch", "args": {"plane": "XY", "offset": 20, "curves": [{"point": [0, 0]}]}}
]
```

The call:

```json
{"tool": "sketch_project", "args": {"sketch": "Sketch2", "kind": "project", "faces": {"normal": [0, 0, 1], "at": {"axis": "z", "value": "max"}, "count": 1}}}
```

The answer:

```text
Done: AI: Project: 4 curves into Sketch2. Bodies now: Body1: 24000 mm3, 60 x 40 x 10 mm.
```

## More argument examples

- the top face's outline into Sketch2, to extrude from it:
  `{"sketch": "Sketch2", "kind": "project", "faces": {"normal": [0, 0, 1], "at": {"axis": "z", "value": "max"}, "count": 1}}`

## See also

- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
