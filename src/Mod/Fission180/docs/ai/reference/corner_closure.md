# `corner_closure`: Corner closure

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: SHEET METAL > MODIFY > Corner Closure. Category: Sheet metal. Changes the design (one undo step). Its undo step is named like "AI: Corner closure". Needs a solid body.
It builds the design step(s) `sf_sm_corner_closure` (the golden models' step language).

## What it does

Fusion's Corner Closure: close the open corner where two flanges of the active sheet metal body meet. dominant / submissive: an edge of each flange's end at the corner (the end faces that face each other). alignment symmetric (default: both stop gap / 2 from the corner's bisector) | overlap (the dominant runs over the other's end: overlap 0..1 of the thickness, flip_overlap swaps); gap (mm, default the rule's miter gap); extend_aligned (default true); relief trim_to_bend (default) | tear | round | square with relief_size (mm) and placement intersection | tangent | vertex.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `dominant` (required) | object or array |  |  |  | an edge of the first flange's end: an edge selector that picks exactly one edge, or a point [x, y, z] on it (mm, design coordinates) |
| `submissive` (required) | object or array |  |  |  | an edge of the second flange's end: an edge selector that picks exactly one edge, or a point [x, y, z] on it (mm, design coordinates) |
| `alignment` | `symmetric` \| `overlap` |  | `"symmetric"` |  |  |
| `gap` | number | mm |  | >= 0 | mm |
| `overlap` | number | 0..1 |  | >= 0, <= 1 | 0..1 of the thickness |
| `flip_overlap` | boolean |  | `false` |  |  |
| `extend_aligned` | boolean |  | `true` |  |  |
| `relief` | `round` \| `square` \| `tear` \| `trim_to_bend` |  | `"trim_to_bend"` |  |  |
| `relief_size` | number | mm |  | > 0 | mm |
| `placement` | `intersection` \| `tangent` \| `vertex` |  | `"intersection"` |  |  |

## Answer

On success: `Done: <undo title>. Its id is '<id>'. Bodies now: <each solid body's volume in mm3 and size in mm>.` (some steps report no id); then `These steps now fail: ...` when the change broke later steps, and `Warning: no solid changed ...` when it changed no solid at all. On failure nothing changes and the answer is `Not done (<undo title>): <the reason>`.

## Errors

- Without a solid body: `The design has no solid body yet: make one first (create_sketch + extrude, or primitive).`
- Called without arguments, the arguments are refused before anything runs: `Not done: dominant is missing; submissive is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When Fission 180 cannot build the step (a selector that picks another number of elements than `count`, a size that does not fit, an id that does not exist), the answer is `Not done (<undo title>): <reason>` and nothing changes; [troubleshooting](fission180://docs/troubleshooting.md) lists the usual causes.

## Example 1: close the corner between two flanges, 1 mm apart

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"polyline": [[0, 0], [100, 0], [100, 55], [95, 55], [95, 60], [0, 60]]}]}},
  {"tool": "flange", "args": {"kind": "base", "profile": "Sketch1"}},
  {"tool": "flange", "args": {"kind": "edge", "edges": [[100, 20, 1]], "height": 20}},
  {"tool": "flange", "args": {"kind": "edge", "edges": [[50, 60, 1]], "height": 20}}
]
```

The call:

```json
{"tool": "corner_closure", "args": {"dominant": [100, 55, 12], "submissive": [95, 60, 12], "gap": 1}}
```

The answer:

```text
Done: AI: Corner closure. Its id is 'CornerClosure1'. Bodies now: Body1: 9041.44 mm3, 100 x 60 x 21 mm.
```

## More argument examples

- close the corner between two 20 mm flanges with a 1 mm gap:
  `{"dominant": [100, 55, 12], "submissive": [95, 60, 12], "gap": 1}`

## See also

- Golden models built with its steps (read one with docs_read golden/<id>): `sheetmetal_smm_corner_closure`, `sheetmetal_smm_corner_closure_60`, `sheetmetal_smm_corner_closure_mitred`, `sheetmetal_smm_corner_closure_mitred_square`, `sheetmetal_smm_corner_closure_not_aligned`, `sheetmetal_smm_corner_closure_overlap`, `sheetmetal_smm_corner_closure_round`, `sheetmetal_smm_corner_closure_tangent`, `sheetmetal_smm_corner_closure_tear`, `sheetmetal_smm_corner_closure_vertex`, `sm_flat_corner_closure`, `sm_flat_corner_closure_tangent`
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
