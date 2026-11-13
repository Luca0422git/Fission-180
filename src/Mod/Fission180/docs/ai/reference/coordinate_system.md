# `coordinate_system`: User coordinate system

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: SOLID > CONSTRUCT > User Coordinate System. Category: Construct. Changes the design (one undo step). Its undo step is named like "AI: User coordinate system". Needs an open design.

## What it does

A user coordinate system (origin point and X / Y / Z axes) in the active body: a frame to sketch on (its XY plane), to measure from, or to attach things to. origin [x, y, z] (mm), z_axis and x_axis directions (default the design's); on: a pick it follows when the part changes ({"face": selector}: on that flat face, {"plane": "XY"}, {"vertex": [x, y, z]}, {"construct": id}); origin and axes are then measured in that frame. Answers its id and its frame in design coordinates.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `origin` | array of 3 numbers | mm |  |  | its origin (mm) |
| `z_axis` | array of 3 numbers |  |  |  | its Z direction |
| `x_axis` | array of 3 numbers |  |  |  | its X direction (made square to Z) |
| `on` | object |  |  |  | what it follows. (rules: [picks](fission180://docs/tools.md#help-picks)) |
| `name` | string |  |  |  | its name |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: a frame on the plate's end whose Z points along X

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
{"tool": "coordinate_system", "args": {"origin": [60, 0, 0], "z_axis": [1, 0, 0], "name": "End frame"}}
```

The answer:

```text
Done: user coordinate system 'End frame' (id 'CoordinateSystem') in Body1: origin [60, 0, 0], X [0, 1, 0], Y [0, 0, 1], Z [1, 0, 0]. Bodies now: Body1: 24000 mm3, 60 x 40 x 10 mm.
```

## More argument examples

- a frame at (50, 0, 20) whose Z points along X:
  `{"origin": [50, 0, 20], "z_axis": [1, 0, 0]}`

## See also

- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
