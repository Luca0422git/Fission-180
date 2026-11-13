# `cam_simulate`: Simulate

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: MANUFACTURE > MILLING > ACTIONS > Simulate. Category: Manufacture. Read-only. Needs a solid body.

## What it does

Play a setup's toolpaths against its stock and answer the numbers (Fusion's Simulate, without the pictures): machining time (s), cutting and rapid distances (mm), the stock's volume before and the volume removed (mm3; the stock is a grid of columns, so volumes are within a few percent), collisions: every rapid move that went into material, with its operation, G-code line, place [x, y, z] in setup coordinates and depth (mm), and the stock compared with the model (Fusion's stock comparison): gouges (where the tool cut into the part: area, deepest, where, and which operation did it) and stock_left_on_model (the most and the mean left above the part: a finishing pass needed?). Empty collisions and no gouge is what a safe program has. operations: only these. Every operation simulated needs an up-to-date toolpath (cam_generate). Only the cutter is checked, not the holder or clamps. 1 to 10 s (a 3D finishing toolpath of 100,000 moves: a minute). Changes nothing. setup: the setup's id or name (cam_setup answers it; default: the newest setup).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `setup` | string |  |  |  | the setup's id or name (default: the newest setup) |
| `operations` | array of strings |  |  | at least 1 item(s) | only these operations (ids or names) |

## Answer

A plain sentence, then JSON with: `setup`, `time_s`, `time`, `cut_length_mm`, `rapid_length_mm`, `stock_volume_mm3`, `removed_mm3`, `left_mm3`, `grid_cell_mm`, `operations`, `collisions`, `gouges`, `stock_left_on_model`, `gouge_tolerance_mm`, `seconds`. The example below shows a real one.

## Errors

- Without a solid body: `The design has no solid body yet: make one first (create_sketch + extrude, or primitive).`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: play the facing and the contour against the stock

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
{"tool": "cam_simulate", "args": {}}
```

The answer:

```text
Simulated Setup1: no rapid move into the stock, 1:51, 13811.1 mm3 of 73715.1 mm3 removed. No gouge; up to 0 mm of stock is left on the part.
{
 "setup": "Setup1",
 "time_s": 110.55,
 "time": "1:51",
 "cut_length_mm": 1826.85,
 "rapid_length_mm": 42.0,
 "stock_volume_mm3": 73715.09,
 "removed_mm3": 13811.09,
 "left_mm3": 59904.0,
 "grid_cell_mm": 0.3331,
 "operations": [
  {"name": "Face1", "id": "CamOp", "removed_mm3": 6656.1},
  {"name": "2D Contour1", "id": "CamOp001", "removed_mm3": 7155.0}
 ],
 "collisions": [],
 "gouges": {"cells": 0, "area_mm2": 0.0, "deepest_mm": 0.0, "volume_mm3": 0.0},
 "stock_left_on_model": {"max_mm": 0.0, "mean_mm": 0.0, "volume_mm3": 0.0, "at": [0.16653, 0.16653, -Infinity]},
 "gouge_tolerance_mm": 0.083267,
 "seconds": 0.2
}
```

## More argument examples

- simulate the newest setup:
  `{}`

## See also

- Recipe: [mill a pocketed plate on a CNC router (MANUFACTURE)](fission180://docs/recipes/mill-pocketed-plate.md)
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
