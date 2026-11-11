# `cam_post`: Post process

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: MANUFACTURE > MILLING > ACTIONS > Post Process. Category: Manufacture. Writes files. Needs a solid body.
It builds the design step(s) `cam_post` (the golden models' step language).

## What it does

Write a setup's toolpaths as a G-code program for a controller (Fusion's Post Process) and check it. post: grbl (default) | linuxcnc | mach3_mach4 | fanuc | marlin | centroid | smoothie | rrf | refactored_masso_g3; units mm | in; path: the file to write (a full path; a folder: the program's name with the post's extension is added); program / comment: over the setup's own; operations: only these. Toolpaths that are missing or out of date are generated first. Answers the file's path, the operations in it, and the checker's result: problems (sentences: no units, spindle not started before cutting, a sideways rapid below the safe height, a move below the lowest cut or outside the toolpaths' box, no spindle stop), notes, units, lowest and highest Z, the X / Y box, the tools and the number of lines. An empty problems list does not make a program safe for a particular machine. A program must be checked before it runs on a machine: simulate it, read the G-code, make the first run above the part. A file that exists is not replaced unless the person agrees. setup: the setup's id or name (cam_setup answers it; default: the newest setup).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `setup` | string |  |  |  | the setup's id or name (default: the newest setup) |
| `path` (required) | string |  |  |  | the G-code file to write, or the folder for it (a full path) |
| `post` | `grbl` \| `linuxcnc` \| `mach3_mach4` \| `fanuc` \| `marlin` \| `centroid` \| `smoothie` \| `rrf` \| `refactored_masso_g3` |  | `"grbl"` |  | the controller's dialect |
| `units` | `mm` \| `in` |  | `"mm"` |  | the program's units |
| `program` | string |  |  |  | the program's name or number (default: the setup's) |
| `comment` | string |  |  |  | the program's comment (default: the setup's) |
| `operations` | array of strings |  |  | at least 1 item(s) | only these operations (ids or names) |

## Answer

A plain sentence, then JSON with: `file`, `post`, `units`, `program`, `operations`, `check`. The example below shows a real one.

## Errors

- Without a solid body: `The design has no solid body yet: make one first (create_sketch + extrude, or primitive).`
- Called without arguments, the arguments are refused before anything runs: `Not done: path is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: the program for a Grbl router, checked

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
{"tool": "cam_post", "args": {"path": "/home/me/fission180/plate.nc"}}
```

The answer:

```text
Posted Setup1 to /home/me/fission180/plate.nc (Grbl, 103 lines, 2 operations): the checker found no problem. Check a program before it runs on a machine: simulate it, read it, make the first run above the part.
{
 "file": "/home/me/fission180/plate.nc",
 "post": "Grbl",
 "units": "mm",
 "program": "1001",
 "operations": ["Face1", "2D Contour1"],
 "check": {
  "problems": [],
  "notes": [],
  "units": "mm",
  "min_z": -11.0,
  "max_z": 15.0,
  "bounds_xy": [-1.0, -1.0, 105.0, 65.0],
  "tools": [],
  "lines": 103
 }
}
```

## More argument examples

- the newest setup as Grbl G-code:
  `{"path": "~/cnc/plate.nc"}`
- Setup1 for LinuxCNC in inches, named after its program number:
  `{"setup": "Setup1", "path": "~/cnc", "post": "linuxcnc", "units": "in"}`

## See also

- Golden models built with its steps (read one with docs_read golden/<id>): `cam_plate_face_contour_drill`
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
