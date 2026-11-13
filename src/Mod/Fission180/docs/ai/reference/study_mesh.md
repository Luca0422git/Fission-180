# `study_mesh`: Generate mesh

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: SIMULATION > SETUP > SOLVE > Generate Mesh (and DISPLAY > Show Mesh). Category: Simulation. Changes the design (one undo step). Its undo step is named like "AI: Generate mesh". Needs an open design.

## What it does

Make a study's mesh now, without solving (Fusion's Generate Mesh): its nodes, elements, smallest and largest element edge (mm), worst aspect ratio and how long it took; no constraint or load needed. Use it before a long solve to see how big it will be (a solve takes about 1 s per 10,000 nodes) and after study_settings / local_mesh_control to check the mesh got finer where it matters. show true: the mesh is drawn on the model in the window (Show Mesh). Seconds; tens of seconds for thousands of faces. Not an undo step. study: the study's id or name (create_study answers it; default the newest study).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `study` | string |  |  |  | the study's id or name (default: the newest study) |
| `show` | boolean |  | `false` |  | draw the mesh on the model (the window) |
| `timeout` | number |  | `600` | > 0, <= 7200 | give up after this many seconds |

## Answer

A plain sentence, then JSON with: `study`, `id`, `mesh`, `seconds`, `shown`. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: the mesh, without solving

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 60, 40], "name": "base"}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 10}},
  {"tool": "create_study", "args": {}}
]
```

The call:

```json
{"tool": "study_mesh", "args": {}}
```

The answer:

```text
Done: Study 1 - Static Stress meshed (took 0.2 s): 1137 nodes, 528 elements, element edges 4.297 to 13.17 mm.
{
 "study": "Study 1 - Static Stress",
 "id": "SimStudy",
 "mesh": {
  "elements": 528,
  "largest": 13.17,
  "mesher": "gmsh",
  "nodes": 1137,
  "order": "parabolic",
  "over_limit": 0,
  "sampled": false,
  "size": 7.28,
  "smallest": 4.297,
  "worst_aspect": 5.296
 },
 "seconds": 0.2,
 "shown": false
}
```

## More argument examples

- mesh the newest study:
  `{}`
- and show it:
  `{"show": true}`

## See also

- Recipe: [is this bracket strong enough? (Static Stress)](fission180://docs/recipes/static-stress.md)
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
