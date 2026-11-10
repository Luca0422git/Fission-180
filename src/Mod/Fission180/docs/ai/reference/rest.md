# `rest`: Rest

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: PLASTIC > CREATE > Rest. Category: Plastic. Changes the design (one undo step). Its undo step is named like "AI: Rest". Needs a solid body.
It builds the design step(s) `sf_rest` (the golden models' step language).

## What it does

Fusion's Rest: a flat landing on a curved or sloping plastic wall (for a label, a switch, a PCB standoff). rect: [x0, y0, x1, y1] the landing's rectangle in a sketch on plane (XY | XZ | YZ) moved offset mm along its normal: the plane cuts the active body's wall where the landing goes. Inside the rectangle the body is cut back to the plane where it bulges past it, and a pedestal thickness mm thick (drafted by draft degrees) fills where it lies below; flip turns which side is inside. Sizes left out follow the plastic rule assigned to the design (plastic_rule; Default (mm): 2 mm walls, 1 degree draft, 0.1 mm clearance) and keep following it when it changes.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `rect` (required) | array of 4 numbers | mm |  |  | [x0, y0, x1, y1] in the sketch (mm) |
| `plane` | `XY` \| `XZ` \| `YZ` |  | `"XY"` |  | the sketch plane (an origin plane) |
| `offset` | number | mm | `0` |  | the plane moved along its normal (mm) |
| `thickness` | number | mm |  | > 0 | the wall under the landing (mm) |
| `draft` | number | deg |  | >= 0 | the pedestal walls' draft (degrees) |
| `flip` | boolean |  | `false` |  |  |
| `name` | string |  |  |  | a descriptive name for what this makes: its sketch of the rest's rectangle becomes "<name> sketch", e.g. "Base plate" (required in effect: unnamed bodies and sketches must be renamed before the next change) |

## Answer

On success: `Done: <undo title>. Its id is '<id>'. Bodies now: <each solid body's volume in mm3 and size in mm>.` (some steps report no id); then `These steps now fail: ...` when the change broke later steps, and `Warning: no solid changed ...` when it changed no solid at all. On failure nothing changes and the answer is `Not done (<undo title>): <the reason>`.

## Errors

- Without a solid body: `The design has no solid body yet: make one first (create_sketch + extrude, or primitive).`
- Called without arguments, the arguments are refused before anything runs: `Not done: rect is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When Fission 180 cannot build the step (a selector that picks another number of elements than `count`, a size that does not fit, an id that does not exist), the answer is `Not done (<undo title>): <reason>` and nothing changes; [troubleshooting](fission180://docs/troubleshooting.md) lists the usual causes.

## Example 1: a pad 3 mm below the floor of a hollow box

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 60, 40]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 20}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 2, "geometry": [{"rect": [2, 2, 58, 38]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch2", "distance": 16, "operation": "cut"}}
]
```

The call:

```json
{"tool": "rest", "args": {"rect": [20, 10, 40, 30], "plane": "XY", "offset": -3, "thickness": 2, "draft": 0}}
```

The answer:

```text
Done: AI: Rest. Its id is 'Rest1'. Bodies now: Body1: 16176 mm3, 60 x 40 x 23 mm.
```

## More argument examples

- a pad 3 mm below the floor of a hollow box:
  `{"rect": [20, 10, 40, 30], "plane": "XY", "offset": -3, "thickness": 2, "draft": 0}`

## See also

- Golden models built with its steps (read one with docs_read golden/<id>): `plastic_rest_closed_box`, `plastic_rest_cut`, `plastic_rest_cylinder`
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
