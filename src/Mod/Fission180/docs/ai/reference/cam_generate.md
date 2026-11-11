# `cam_generate`: Generate toolpaths

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: MANUFACTURE > MILLING > ACTIONS > Generate. Category: Manufacture. Changes the design (one undo step). Its undo step is named like "AI: Generate toolpaths". Needs a solid body.
It builds the design step(s) `cam_generate` (the golden models' step language).

## What it does

Make the toolpaths that are missing or out of date (Fusion's Generate): after the design, a setup or an operation changed, cam_setups shows them as "stale" (needs regenerating). operations: only these; all true: every operation of the setup, the valid ones too. Fission 180 waits until FreeCAD's CAM engine is done (seconds; an adaptive clearing can take a minute). Toolpaths are not undo steps. Answers each operation's state and numbers, and the reason for one that could not be made. setup: the setup's id or name (cam_setup answers it; default: the newest setup).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `setup` | string |  |  |  | the setup's id or name (default: the newest setup) |
| `operations` | array of strings |  |  | at least 1 item(s) | only these operations (ids or names) |
| `all` | boolean |  | `false` |  | the up-to-date ones too |

## Answer

A plain sentence, then JSON with: `setup`, `id`, `generated`, `operations`. The example below shows a real one.

## Errors

- Without a solid body: `The design has no solid body yet: make one first (create_sketch + extrude, or primitive).`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: the setup's stock changed: make its toolpaths again

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "primitive", "args": {"kind": "box", "plane": "XY", "length": 100, "width": 60, "height": 10}},
  {"tool": "primitive", "args": {"kind": "cylinder", "plane": "XY", "x": 20, "y": 30, "diameter": 6, "height": 10, "operation": "cut"}},
  {"tool": "primitive", "args": {"kind": "cylinder", "plane": "XY", "x": 80, "y": 30, "diameter": 6, "height": 10, "operation": "cut"}},
  {"tool": "cam_setup", "args": {"stock": {"mode": "relative", "offset_mode": "sides_top_bottom", "side": 2, "top": 1}, "wcs": {"origin": "stock_point", "box_point": [-1, -1, 1]}, "post": {"program": "1001", "comment": "plate"}}},
  {"tool": "cam_operation", "args": {"kind": "face", "tool": {"type": "flat", "diameter": 10, "number": 1}}},
  {"tool": "cam_operation", "args": {"kind": "contour2d", "faces": {"normal": [0, 0, -1], "count": 1}, "tool": {"library": "sample:mm", "id": "sample-mm-flat-6"}, "options": {"linking": {"lead_in": false, "lead_out": false}}}},
  {"tool": "cam_edit", "args": {"target": "Setup1", "stock": {"top": 2}}}
]
```

The call:

```json
{"tool": "cam_generate", "args": {}}
```

The answer:

```text
Done: 2 toolpaths of Setup1 generated (Face1, 2D Contour1).
{
 "setup": "Setup1",
 "id": "CamSetup",
 "generated": ["Face1", "2D Contour1"],
 "operations": [
  {
   "id": "CamOp",
   "name": "Face1",
   "kind": "face",
   "title": "Face",
   "tool": "#1 - 10 mm flat end mill",
   "state": "valid",
   "toolpath": {
    "cut_length": 1473.0,
    "rapid_length": 17.0,
    "time_s": 87.67,
    "min_cut_z": -2.0,
    "bounds": [5.0, 5.0, -2.0, 99.0, 59.0, 15.0]
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
    "cut_length": 355.85,
    "rapid_length": 27.0,
    "time_s": 23.26,
    "min_cut_z": -12.0,
    "bounds": [-1.0, -1.0, -12.0, 105.0, 65.0, 15.0]
   }
  }
 ]
}
```

## More argument examples

- every toolpath of the newest setup that needs it:
  `{}`
- all of Setup1's toolpaths again:
  `{"setup": "Setup1", "all": true}`

## See also

- Golden models built with its steps (read one with docs_read golden/<id>): `cam_block_side_setup`
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
