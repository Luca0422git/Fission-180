# `surface_modify`: Surface modify

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: SURFACE > MODIFY (Fillet, Chamfer, Press Pull, Delete, Merge on surface bodies). Category: Surface. Changes the design (one undo step). Its undo step is named like "AI: Surface press pull". Needs an open design.
It builds the design step(s) `sf_surface_modify`, `use_body` (the golden models' step language).

## What it does

The SURFACE tab's Fillet, Chamfer, Press Pull, Delete and Merge on a surface body (open faces, no volume, made with the surface tool; for a solid use fillet, chamfer, press_pull and delete_face). body: the surface body (a step in it; default the active body: the last one made or activated). kind fillet: edges (each between two faces of the body), radius (mm, default 1), radius_type constant | chord (radius is the chord's length) | variable (radius at each edge's start, radius2 at its end), tangent_chain (default true). kind chamfer: edges, chamfer_type equal | two (distance2 on the edge's second face) | angle (angle degrees), distance (mm, default 1), flip, tangent_chain. kind press_pull: faces, distance (mm; + pulls the face out along its normal, - pushes it in; the faces around it follow). kind delete_face: faces taken away without healing the hole. kind merge: faces of the body that lie on one surface become one face. Surface bodies have no volume: inspect_design and diff_design give their area_mm2 and faces to check the result.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `kind` (required) | `chamfer` \| `delete_face` \| `fillet` \| `merge` \| `press_pull` |  |  |  |  |
| `body` | string |  |  |  | the surface body (default: the active body) |
| `edges` | object |  |  |  | fillet / chamfer: the edges (an edge selector: filters type, parallel, radius, on_faces, not_on_faces, at, all, count, any_of; see get_help topic selectors). Give count. |
| `faces` | object |  |  |  | press_pull / delete_face / merge: the faces (a face selector: filters type, normal, along, radius, at, all, count, any_of; see get_help topic selectors). Give count. |
| `radius` | number | mm | `1` | > 0 | fillet: mm |
| `radius_type` | `constant` \| `chord` \| `variable` |  | `"constant"` |  |  |
| `radius2` | number | mm |  | > 0 | fillet, variable: the end radius (mm) |
| `tangent_chain` | boolean |  | `true` |  | take the edges tangent to them too |
| `chamfer_type` | `equal` \| `two` \| `angle` |  | `"equal"` |  |  |
| `distance` | number | mm |  |  | chamfer: mm (above 0); press_pull: mm, + pulls, - pushes |
| `distance2` | number | mm |  | > 0 | chamfer two: the second distance (mm) |
| `angle` | number | deg |  | > 0, <= 89.999 | chamfer angle: degrees |
| `flip` | boolean |  | `false` |  | chamfer: swap the two faces' distances |

## Answer

On success: `Done: <undo title>. Its id is '<id>'. Bodies now: <each solid body's volume in mm3 and size in mm>.` (some steps report no id); then `These steps now fail: ...` when the change broke later steps, and `Warning: no solid changed ...` when it changed no solid at all. On failure nothing changes and the answer is `Not done (<undo title>): <the reason>`.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: kind is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When Fission 180 cannot build the step (a selector that picks another number of elements than `count`, a size that does not fit, an id that does not exist), the answer is `Not done (<undo title>): <reason>` and nothing changes; [troubleshooting](fission180://docs/troubleshooting.md) lists the usual causes.

## Example 1: push the floor of an open box of surfaces 5 mm down: the walls grow

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_curve_sketch", "args": {"plane": "XY", "curves": [{"polyline": [[0, 0], [30, 0], [30, 20], [0, 20], [0, 0]]}]}},
  {"tool": "surface", "args": {"kind": "extrude", "refs": [{"sketch": "Sketch1", "at": [15, 0]}], "options": {"distance": 10}}},
  {"tool": "surface", "args": {"kind": "patch", "refs": [{"sketch": "Sketch1", "at": [15, 0]}]}},
  {"tool": "surface", "args": {"kind": "stitch", "refs": [{"step": "Surface1"}, {"step": "Surface2"}]}}
]
```

The call:

```json
{"tool": "surface_modify", "args": {"kind": "press_pull", "faces": {"normal": [0, 0, 1], "count": 1}, "distance": -5}}
```

The answer:

```text
Done: AI: Surface press pull. Its id is 'SurfacePressPull'. No solid body yet.
```

## More argument examples

- round the four vertical corners of an open box of surfaces:
  `{"kind": "fillet", "edges": {"parallel": [0, 0, 1], "count": 4}, "radius": 3}`
- push the box's floor 5 mm down (the walls grow):
  `{"kind": "press_pull", "faces": {"normal": [0, 0, 1], "count": 1}, "distance": -5}`
- two faces in one plane become one face:
  `{"kind": "merge", "faces": {"parallel": [0, 1, 0], "count": 2}}`

## See also

- Golden models built with its steps (read one with docs_read golden/<id>): `surface4_chamfer_delete`, `surface4_fillet_box`, `surface4_fillet_chord`, `surface4_fillet_variable`, `surface4_merge`, `surface4_merge_smooth`, `surface4_press_pull`, `surface4_press_pull_cup`, `surface4_press_pull_shade`, `surface4_press_pull_tray`, `surface4_press_pull_two_walls`, `surface4_replace_face_two` and 27 more
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
