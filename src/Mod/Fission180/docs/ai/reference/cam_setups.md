# `cam_setups`: Setups and operations

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: MANUFACTURE > browser > Setups. Category: Manufacture. Read-only. Needs an open design.

## What it does

Read the MANUFACTURE browser: every setup (id, name, stock and model boxes in its own coordinates, where its origin is in the design, warnings) with its operations in machining order: id, name, kind, tool, state (valid | stale: needs regenerating | empty: no toolpath yet | error | suppressed), the reason of an error, and the toolpath's numbers (cut_length, rapid_length mm, time_s, min_cut_z, bounds). details true adds every option of each setup and operation as cam_edit takes them, and the heights in mm. setup: only this one. Changes nothing.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `setup` | string |  |  |  | only this setup (id or name; default: all) |
| `details` | boolean |  | `false` |  | add every option and the heights |

## Answer

A plain sentence, then JSON with: `setups`. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: the setup and its two operations

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "primitive", "args": {"kind": "box", "plane": "XY", "length": 100, "width": 60, "height": 10}},
  {"tool": "primitive", "args": {"kind": "cylinder", "plane": "XY", "x": 20, "y": 30, "diameter": 6, "height": 10, "operation": "cut"}},
  {"tool": "primitive", "args": {"kind": "cylinder", "plane": "XY", "x": 80, "y": 30, "diameter": 6, "height": 10, "operation": "cut"}},
  {"tool": "cam_setup", "args": {"stock": {"mode": "relative", "offset_mode": "sides_top_bottom", "side": 2, "top": 1}, "wcs": {"origin": "stock_point", "box_point": [-1, -1, 1]}, "post": {"program": "1001", "comment": "plate"}}},
  {"tool": "cam_operation", "args": {"kind": "face", "tool": {"type": "flat", "diameter": 10, "number": 1}}},
  {"tool": "cam_operation", "args": {"kind": "contour2d", "faces": {"normal": [0, 0, -1], "count": 1}, "tool": {"library": "sample:mm", "id": "sample-mm-flat-6"}, "options": {"linking": {"lead_in": false, "lead_out": false}}}}
]
```

The call:

```json
{"tool": "cam_setups", "args": {}}
```

The answer:

```text
1 setup, 2 operations.
{
 "setups": [
  {
   "id": "CamSetup",
   "name": "Setup1",
   "stock_box": [0.0, 0.0, -11.0, 104.0, 64.0, 0.0],
   "model_box": [2.0, 2.0, -11.0, 102.0, 62.0, -1.0],
   "origin_in_design": [-2.0, -2.0, 11.0],
   "z_axis_in_design": [0.0, 0.0, 1.0],
   "bodies": ["Body"],
   "operations": [
    {
     "id": "CamOp",
     "name": "Face1",
     "kind": "face",
     "title": "Face",
     "tool": "#1 - 10 mm flat end mill",
     "state": "valid",
     "toolpath": {
      "cut_length": 1472.0,
      "rapid_length": 16.0,
      "time_s": 87.49,
      "min_cut_z": -1.0,
      "bounds": [5.0, 5.0, -1.0, 99.0, 59.0, 15.0]
     }
    },
    {
     "id": "CamOp001",
     "name": "2D Contour1",
     "kind": "contour2d",
     "title": "2D Contour",
     "tool": "#6 - 6 mm flat end mill",
     "state": "valid",
     "toolpath": {
      "cut_length": 354.85,
      "rapid_length": 26.0,
      "time_s": 23.07,
      "min_cut_z": -11.0,
      "bounds": [-1.0, -1.0, -11.0, 105.0, 65.0, 15.0]
     }
    }
   ]
  }
 ]
}
```

## More argument examples

- every setup and operation with its state:
  `{}`
- Setup1 with every option:
  `{"setup": "Setup1", "details": true}`

## See also

- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
