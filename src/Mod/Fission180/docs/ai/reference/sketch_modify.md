# `sketch_modify`: Sketch modify

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: SKETCH > MODIFY (Fillet, Chamfer, Offset, Extend, Break) and FINISH SKETCH > Toggle Construction (X). Category: Sketch. Changes the design (one undo step). Its undo step is named like "AI: Sketch Fillet". Needs an open design.

## What it does

The SKETCH tab's MODIFY tools by their own code: fillet / chamfer: points at corners (where two curves meet), radius (fillet) or distance (chamfer; distance2 or angle (degrees) for unequal sides), each a dimension; extend: points on curves near the end to grow until it meets another curve; break: points on the pieces to split at their nearest crossings (trim removes a piece: sketch_trim); offset: curves (a chain of indexes), distance (mm; + on the side the chain turns to, - the other side), both_sides; toggle_construction: curves become construction (or back). Indexes after the change can move: get_sketch again.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `sketch` (required) | string |  |  |  | the sketch |
| `kind` (required) | `fillet` \| `chamfer` \| `extend` \| `break` \| `offset` \| `toggle_construction` |  |  |  |  |
| `points` | array of arrays |  |  | at least 1 item(s) | fillet / chamfer: corners; extend / break: on curves |
| `curves` | array of integers |  |  | at least 1 item(s) | offset / toggle_construction: curve indexes |
| `radius` | number | mm |  | > 0 | fillet (mm) |
| `distance` | number | mm |  |  | chamfer setback (mm, above 0); offset (mm, signed) |
| `distance2` | number | mm |  | > 0 | chamfer: the second setback (mm) |
| `angle` | number | deg |  | > 0, <= 179 | chamfer: the angle from the first line (degrees) |
| `both_sides` | boolean |  | `false` |  | offset: on both sides |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: sketch is missing; kind is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: a 5 mm round at the rectangle's corner

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 60, 40], "name": "base"}]}}
]
```

The call:

```json
{"tool": "sketch_modify", "args": {"sketch": "Sketch1", "kind": "fillet", "points": [[0, 0]], "radius": 5}}
```

The answer:

```text
Done: AI: Sketch Fillet: fillet arcs [4], radius 5 mm. New curves 4 to 5 in Sketch1. No solid body yet.
```

## More argument examples

- round the corner at the origin with 3 mm:
  `{"sketch": "Sketch1", "kind": "fillet", "points": [[0, 0]], "radius": 3}`
- split the curve through (10, 0) where it crosses the others:
  `{"sketch": "Sketch1", "kind": "break", "points": [[10, 0]]}`

## See also

- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
