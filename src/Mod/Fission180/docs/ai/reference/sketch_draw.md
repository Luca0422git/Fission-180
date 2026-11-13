# `sketch_draw`: Sketch tools

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: SKETCH > CREATE (Midpoint Line, 3-Point Rectangle, 2-Point / 3-Point / 2-Tangent / 3-Tangent Circle, 3-Point / Tangent Arc, Edge Polygon, Slots, Ellipse, Conic Curve, Control / Fit Point Spline). Category: Sketch. Changes the design (one undo step). Its undo step is named like "AI: Conic Curve". Needs an open design.

## What it does

The SKETCH tab's drawing tools beyond add_to_sketch's plain shapes, with the tools' own code and constraints (a slot stays a slot). points: the clicks in order, [x, y] in the sketch: midpoint_line [middle, end]; rectangle_3point [corner, corner, far side]; circle_2point [a, b]; circle_3point 3 points; circle_2tangent / circle_3tangent: lines (indexes) + [a point near it]; arc_3point [start, on it, end]; tangent_arc: from {curve, point} + [end]; edge_polygon [p1, p2, side] + sides; slot_* [first, second] + width; arc_slot [end, on the centre arc, end] / arc_slot_center_point [centre, start, end direction] + width; conic [start, end, apex] + rho (0..1; 0.5 a parabola); ellipse [centre, major end, minor end]; control_point_spline / fit_point_spline: the points. length, angle (degrees), width, diameter, radius become dimensions, as typed in the tool. Answers the new curve indexes.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `sketch` (required) | string |  |  |  | the sketch to draw in |
| `kind` (required) | `midpoint_line` \| `rectangle_3point` \| `circle_2point` \| `circle_3point` \| `circle_2tangent` \| `circle_3tangent` \| `arc_3point` \| `tangent_arc` \| `edge_polygon` \| `slot_center_to_center` \| `slot_overall` \| `slot_center_point` \| `arc_slot` \| `arc_slot_center_point` \| `conic` \| `ellipse` \| `control_point_spline` \| `fit_point_spline` |  |  |  |  |
| `points` (required) | array of arrays |  |  | at least 1 item(s) | the clicks, in order |
| `lines` | array of integers |  |  | at least 2 item(s), at most 3 item(s) | tangent circles: line indexes (-1 / -2: axes) |
| `from` | object |  |  |  | tangent_arc: the end it starts from |
| `from.curve` (required) | integer |  |  | >= 0 | the line or arc it leaves |
| `from.point` (required) | `start` \| `end` |  |  |  |  |
| `sides` | integer | count |  | >= 3, <= 64 | edge_polygon: sides |
| `length` | number | mm |  | > 0 | the line's / first side's / slot's length: a dimension (mm) |
| `angle` | number | deg |  |  | its angle to the sketch x axis: a dimension (degrees) |
| `width` | number | mm |  | > 0 | rectangle / slot width (mm) |
| `diameter` | number | mm |  | > 0 | circle_2point: a diameter dimension (mm) |
| `radius` | number | mm |  | > 0 | tangent circle / arc: a radius dimension (mm) |
| `rho` | number |  |  | >= 0.01, <= 0.99 | conic: 0.01 .. 0.99 (0.5 a parabola) |
| `construction` | boolean |  | `false` |  | construction geometry (dashed) |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: sketch is missing; kind is missing; points is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: a conic curve from (0, 0) to (40, 0) pulled towards (20, 30)

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 60, 40], "name": "base"}]}}
]
```

The call:

```json
{"tool": "sketch_draw", "args": {"sketch": "Sketch1", "kind": "conic", "points": [[0, 0], [40, 0], [20, 30]], "rho": 0.4}}
```

The answer:

```text
Done: AI: Conic Curve. New curves 4 to 11 in Sketch1 (0 constraints from the values given). No solid body yet.
```

## More argument examples

- a conic curve from (0, 0) to (40, 0) pulled towards (20, 30):
  `{"sketch": "Sketch1", "kind": "conic", "points": [[0, 0], [40, 0], [20, 30]], "rho": 0.4}`
- an 8 mm wide slot with its end centres 30 mm apart:
  `{"sketch": "Sketch1", "kind": "slot_center_to_center", "points": [[0, 0], [30, 0]], "width": 8}`

## See also

- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
