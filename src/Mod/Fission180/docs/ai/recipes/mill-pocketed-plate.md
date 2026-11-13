# Recipe: mill a pocketed plate on a CNC router (MANUFACTURE)

Tags: manufacture, cam, cnc, milling, pocket, contour, tabs, drill, toolpath, simulate, gouge, g-code, setup sheet, tool library

A 100 x 60 x 10 mm plate with a 40 x 20 x 4 mm pocket and four 5 mm holes, milled from a block
on a 3-axis router: the setup (stock and origin), a tool of the person's own library, facing,
the pocket, the outline cut out with tabs, drilling; then Simulate as numbers (collisions,
gouges, the stock left), the G-code program checked and the setup sheet for the machine.
Every call below was run by Fission 180's tests; the `expect` part of each call is what the
answer must contain, not a tool argument.

This is Fusion's MANUFACTURE workspace on FreeCAD's CAM engine. Nothing in it changes the
design: setups and operations live beside it, toolpaths are made after each call. Ask the
person first what the machine is (its controller: Grbl, LinuxCNC...), the stock (its size and
material) and which tools they have; the defaults below are a hobby router's.

## 1. The part

```json fission180-calls
[
  {"tool": "new_design", "args": {"name": "PocketPlate"}},
  {"tool": "primitive", "args": {"kind": "box", "plane": "XY", "length": 100, "width": 60, "height": 10},
   "expect": {"contains": ["60000 mm3"]}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 10, "geometry": [{"center_rect": [50, 30, 40, 20]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 4, "operation": "cut", "flip": true},
   "expect": {"contains": ["56800 mm3"]}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 10, "geometry": [
    {"circle": [10, 10, 2.5]}, {"circle": [10, 50, 2.5]}, {"circle": [90, 10, 2.5]}, {"circle": [90, 50, 2.5]}]}},
  {"tool": "hole", "args": {"sketch": "Sketch2", "diameter": 5, "through_all": true}},
  {"tool": "check_design", "args": {}, "expect": {"json": {"ok": true}}}
]
```

## 2. The setup: stock and origin

[cam_setup](fission180://docs/reference/cam_setup.md): the stock is the part's box with 2 mm
around and 1 mm on top (relative), the origin (G54) at the stock's top corner at low X and Y,
Z up as in the design. The answer gives the stock's and the model's boxes in the setup's own
coordinates: every toolpath number is in these.

```json fission180-calls
[
  {"tool": "cam_setup", "args": {
    "stock": {"mode": "relative", "offset_mode": "sides_top_bottom", "side": 2, "top": 1},
    "wcs": {"origin": "stock_point", "box_point": [-1, -1, 1]},
    "post": {"program": "2001", "comment": "pocket plate"}},
   "expect": {"contains": ["Setup1", "104 x 64 x 11"],
     "json": {"stock_box": [0, 0, -11, 104, 64, 0], "model_box": [2, 2, -11, 102, 62, -1]}}}
]
```

## 3. A tool of the person's own library

[cam_tools](fission180://docs/reference/cam_tools.md) lists the libraries and their tools;
the sample libraries cannot change, so [cam_tool_library](fission180://docs/reference/cam_tool_library.md)
copies the 6 mm end mill into the person's Local library (it answers the copy's id, a new one
each time) and slows its feed for a softer router.

```json fission180-calls
[
  {"tool": "cam_tools", "args": {"library": "sample:mm", "type": "flat", "diameter": 6},
   "expect": {"json": {"tools.0.id": "sample-mm-flat-6"}}},
  {"tool": "cam_tool_library", "args": {"action": "copy", "from_library": "sample:mm", "id": "sample-mm-flat-6"},
   "expect": {"contains": ["copied into local:Local"], "json": {"tool.diameter": 6.0}}}
]
```

Use the copy in an operation with `{"library": "local:Local", "id": "<the id answered>"}`;
`cam_tool_library {"action": "edit", "id": ..., "tool": {"cutting": {"cutting_feed": 700}}}`
changes it. The calls below use the sample tool itself, whose id is always the same.

## 4. The operations

Facing takes the stock's top millimetre off; the 2D pocket clears the pocket from its floor
face; the 2D contour cuts the part out along its bottom outline in 4 mm steps, held by four
tabs; drilling picks the four hole walls. Each answer says the toolpath's state and numbers:
the pocket goes down to Z -5 (the pocket's floor, 6 mm above the part's bottom at -11).

```json fission180-calls
[
  {"tool": "cam_operation", "args": {"kind": "face", "tool": {"type": "flat", "diameter": 10, "number": 1}},
   "expect": {"json": {"state": "valid", "toolpath.min_cut_z": [-1, 0.001]}}},
  {"tool": "cam_operation", "args": {"kind": "pocket2d",
    "faces": {"normal": [0, 0, 1], "at": {"axis": "z", "value": 6}, "count": 1},
    "tool": {"library": "sample:mm", "id": "sample-mm-flat-6"}},
   "expect": {"json": {"state": "valid", "toolpath.min_cut_z": [-5, 0.01]}}},
  {"tool": "cam_operation", "args": {"kind": "contour2d", "faces": {"normal": [0, 0, -1], "count": 1},
    "tool": {"library": "sample:mm", "id": "sample-mm-flat-6"},
    "options": {"passes": {"multiple_depths": true, "stepdown": 4},
                "geometry": {"tabs": {"on": true, "positioning": "count", "count": 4}}}},
   "expect": {"json": {"state": "valid", "toolpath.min_cut_z": [-11, 0.01]}}},
  {"tool": "cam_operation", "args": {"kind": "drill", "faces": {"type": "cylinder", "radius": 2.5, "count": 4},
    "tool": {"type": "drill", "diameter": 5, "number": 4}},
   "expect": {"json": {"state": "valid"}}},
  {"tool": "cam_setups", "args": {}, "expect": {"contains": ["1 setup, 4 operations."]}}
]
```

## 5. Simulate as numbers

[cam_simulate](fission180://docs/reference/cam_simulate.md) plays the toolpaths against the
stock: no rapid move goes into material (collisions), no cut goes into the part (gouges), and
the stock left on the part is the pocket's four corners, which a 6 mm tool cannot reach (a
3 mm radius each): at most the pocket's 4 mm depth. To make them sharp, add a smaller tool's
pocket; to leave them round, give the pocket's corners a 3 mm or larger fillet in the design.

```json fission180-calls
[
  {"tool": "cam_simulate", "args": {},
   "expect": {"contains": ["no rapid move into the stock", "No gouge"],
     "json": {"collisions": [], "gouges.cells": 0, "stock_left_on_model.max_mm": [4, 0.05]}}}
]
```

A mistake shows as numbers too: a facing whose bottom is 1 mm into the part is a gouge 1 mm
deep over the part's top, put on that operation. Delete it again.

```json fission180-calls
[
  {"tool": "cam_operation", "args": {"kind": "face", "tool": {"type": "flat", "diameter": 10, "number": 1},
    "options": {"heights": {"bottom": {"from": "model_top", "offset": -1}}}, "label": "Too deep"}},
  {"tool": "cam_simulate", "args": {},
   "expect": {"contains": ["GOUGES"], "json": {"gouges.deepest_mm": [1, 0.02]}}},
  {"tool": "cam_delete", "args": {"target": "Too deep"}}
]
```

## 6. The program and the setup sheet

[cam_post](fission180://docs/reference/cam_post.md) writes the G-code for the controller and
checks it (units, spindle started before cutting, no rapid below the safe height, nothing
below the lowest cut); [cam_setup_sheet](fission180://docs/reference/cam_setup_sheet.md) writes
the page for the person at the machine. A program must still be checked on the machine: run it
above the part first.

```json fission180-calls
[
  {"tool": "cam_post", "args": {"path": "{tmp}", "post": "grbl"},
   "expect": {"contains": ["2001.nc", "the checker found no problem"],
     "json": {"units": "mm", "check.problems": [], "check.min_z": [-11, 0.001]}}},
  {"tool": "cam_setup_sheet", "args": {"path": "{tmp}"},
   "expect": {"contains": ["Setup1 setup sheet.html", "4 operations"]}},
  {"tool": "check_design", "args": {}, "expect": {"json": {"ok": true}}}
]
```

## Variations

- **The other side**: a second `cam_setup` with `stock {"mode": "preceding"}` and
  `wcs {"flip_z": true}` machines the part turned over.
- **Another controller**: `cam_post {"post": "linuxcnc", "units": "in"}`.
- **3D parts**: `adaptive3d` roughs, `parallel` / `contour3d` finish (they need OpenCAMLib; the
  answer says when FreeCAD has none); `stock_left_on_model` says whether a finishing pass is
  still needed.
