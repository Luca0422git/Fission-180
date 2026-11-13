# `cam_setup_sheet`: Setup sheet

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: MANUFACTURE > MILLING > ACTIONS > Setup Sheet. Category: Manufacture. Writes files. Needs a solid body.

## What it does

Write a setup's Setup Sheet (Fusion's): one HTML page for the person at the machine with the program, the work coordinate system and its origin, the stock and model sizes, every tool (number, type, diameter, flute length, flutes) and every operation in machining order (strategy, tool, spindle speed, feeds, stepdown, stepover, lowest Z, cutting length and time). path: a full path (.html added; a folder: "<setup> setup sheet.html" in it). Operations without an up-to-date toolpath have no numbers (the answer names them: cam_generate first). A file that exists is not replaced unless the person agrees. setup: the setup's id or name (cam_setup answers it; default: the newest setup).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `setup` | string |  |  |  | the setup's id or name (default: the newest setup) |
| `path` (required) | string |  |  |  | the HTML file to write, or its folder (a full path) |

## Answer

A plain sentence, then JSON with: `file`, `operations`, `tools`. The example below shows a real one.

## Errors

- Without a solid body: `The design has no solid body yet: make one first (create_sketch + extrude, or primitive).`
- Called without arguments, the arguments are refused before anything runs: `Not done: path is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: the setup sheet of the facing and the contour

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
{"tool": "cam_setup_sheet", "args": {"path": "/home/me/fission180"}}
```

The answer:

```text
Written /home/me/fission180/Setup1 setup sheet.html: the setup sheet of Setup1, 2 operations, 2 tools, 1:51 of machining.
{
 "file": "/home/me/fission180/Setup1 setup sheet.html",
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
 ],
 "tools": ["#1 - 10 mm flat end mill", "#6 - 6 mm flat end mill"]
}
```

## More argument examples

- the newest setup's sheet in ~/cnc:
  `{"path": "~/cnc"}`

## See also

- Recipe: [mill a pocketed plate on a CNC router (MANUFACTURE)](fission180://docs/recipes/mill-pocketed-plate.md)
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
