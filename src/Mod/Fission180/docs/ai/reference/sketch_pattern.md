# `sketch_pattern`: Sketch mirror / pattern / move

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: SKETCH > CREATE > Mirror / Circular Pattern / Rectangular Pattern, MODIFY > Move/Copy. Category: Sketch. Changes the design (one undo step). Its undo step is named like "AI: Sketch Circular Pattern". Needs an open design.

## What it does

Repeat sketch curves with the SKETCH tab's own code; the copies stay tied to the originals (change one, they follow). curves: the indexes to repeat. mirror: line (index; -1 x axis, -2 y axis). rectangular: quantity, distance (mm) along direction (a line index, default -1), quantity2, distance2 along direction2 (default -2), distribution extent (distance is the whole span) | spacing (between copies). circular: center {curve, point}, quantity, angle (degrees, default 360), circular_type full | angle | symmetric. move_copy: dx, dy (mm), rotate (degrees about about [x, y]), copy (keep the originals). Answers the new curve indexes.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `sketch` (required) | string |  |  |  | the sketch |
| `kind` (required) | `mirror` \| `rectangular` \| `circular` \| `move_copy` |  |  |  |  |
| `curves` (required) | array of integers |  |  | at least 1 item(s) | the curves |
| `line` | integer |  |  | >= -2 | mirror: the mirror line |
| `quantity` | integer | count |  | >= 1, <= 500 | how many in all (with the originals) |
| `distance` | number | mm |  |  | mm |
| `direction` | integer |  |  | >= -2 | rectangular: a line index (-1 x axis) |
| `quantity2` | integer | count | `1` | >= 1, <= 500 | rectangular: across |
| `distance2` | number | mm | `20` |  | mm |
| `direction2` | integer |  |  | >= -2 | a line index (-2 y axis) |
| `distribution` | `extent` \| `spacing` |  | `"extent"` |  |  |
| `center` | object |  |  |  | a point of the sketch |
| `center.curve` (required) | integer |  |  | >= -2 | its curve (index; -1 with point start: the origin) |
| `center.point` (required) | `start` \| `end` \| `center` |  |  |  |  |
| `angle` | number | deg | `360` |  | circular: degrees |
| `circular_type` | `full` \| `angle` \| `symmetric` |  | `"full"` |  |  |
| `dx` | number | mm | `0` |  | move_copy: mm |
| `dy` | number | mm | `0` |  | move_copy: mm |
| `rotate` | number | deg | `0` |  | move_copy: degrees |
| `about` | array of 2 numbers |  |  |  | move_copy: the point it turns about |
| `copy` | boolean |  | `false` |  | move_copy: keep the originals |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: sketch is missing; kind is missing; curves is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: six circles round the origin

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_curve_sketch", "args": {"plane": "XY", "curves": [{"circle": [10, 0, 2]}]}}
]
```

The call:

```json
{"tool": "sketch_pattern", "args": {"sketch": "Sketch1", "kind": "circular", "curves": [0], "center": {"curve": -1, "point": "start"}, "quantity": 6}}
```

The answer:

```text
Done: AI: Sketch Circular Pattern. New curves 1 to 11 in Sketch1. No solid body yet.
```

## More argument examples

- mirror curves 0 and 1 about the sketch's y axis:
  `{"sketch": "Sketch1", "kind": "mirror", "curves": [0, 1], "line": -2}`
- six of circle 4 round the origin:
  `{"sketch": "Sketch1", "kind": "circular", "curves": [4], "center": {"curve": -1, "point": "start"}, "quantity": 6}`

## See also

- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
