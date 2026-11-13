# `cam_operation`: New operation

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: MANUFACTURE > MILLING > 2D / 3D / DRILLING. Category: Manufacture. Changes the design (one undo step). Its undo step is named like "AI: New operation (drill)". Needs a solid body.
It builds the design step(s) `cam_operation` (the golden models' step language).

## What it does

Add a milling or drilling operation to a setup and make its toolpath. kind: face (the stock's top down to the model's top; no pick needed), adaptive2d / pocket2d (clear a pocket: pick its floor face), contour2d (cut along an outline: pick a face, its outer edge is followed outside the material, or edges with chain), slot, trace (the tool's centre along picked edges), engrave, chamfer2d (chamfer mill along edges), bore / circular (helix a round hole: pick its wall), drill (pick hole walls; options.geometry.same_diameter takes every hole of that size), adaptive3d / pocket3d (3D roughing), parallel / contour3d (3D finishing; they need OpenCAMLib, the answer says when FreeCAD has none). faces / edges: selectors on the body `of` (default: the active body); chain: each picked edge stands for the closed loop it is in. tool: either a tool of a library, {"library": "sample:mm" | "sample:in" | "local:<name>" | "document", "id": its id (cam_tools lists them)}, or one described here, {"type": flat | ball | bull | face | chamfer | drill | spot, "diameter": mm} with anything else to set (number, flutes, corner_radius, flute_length, cutting {spindle_speed rpm, cutting_feed, leadin_feed, plunge_feed, ramp_feed mm/min, stepdown, stepover mm}); sizes left out follow from the diameter, speeds and feeds from the tool's size. options: the dialog's tabs as nested objects, only what differs from the defaults: feeds {spindle_speed, cutting_feed, leadin_feed, plunge_feed, ramp_feed} over the tool's own; geometry {flip_side, same_diameter (drill: every hole of the picked diameter), tabs {on, shape rectangular | triangular, width, height, positioning distance | count | points, distance, count, points [[x, y, z], ...]}}; heights {clearance | retract | feed | top | bottom: {"from": model_top | model_bottom | stock_top | stock_bottom | selection | origin | (a higher one of) retract | feed | top | bottom, "offset": mm}}; passes {tolerance, direction climb | conventional, compensation computer | off, stepover, optimal_load, multiple_depths, stepdown, finishing_passes, finishing_stepover, stock_to_leave, radial_stock, axial_stock, pass_angle, pass_extension, both_ways, chamfer_width, chamfer_tip_offset, cycle drilling | counterboring | chip_breaking | deep_drilling, peck_depth, dwell, tip_through, break_through, pitch}; linking {lead_in, lead_out, lead_radius, ramp plunge | helix | profile | zigzag, ramp_angle, helix_diameter, keep_down}. generate false: add it without a toolpath (cam_generate makes it later). Answers the operation's id, its state and the toolpath's numbers: cutting and rapid lengths (mm), machining time, lowest cut Z and the box of every move, in the setup's coordinates. setup: the setup's id or name (cam_setup answers it; default: the newest setup).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `setup` | string |  |  |  | the setup's id or name (default: the newest setup) |
| `kind` (required) | `face` \| `adaptive2d` \| `pocket2d` \| `contour2d` \| `slot` \| `trace` \| `engrave` \| `chamfer2d` \| `bore` \| `circular` \| `drill` \| `adaptive3d` \| `pocket3d` \| `parallel` \| `contour3d` |  |  |  | the strategy |
| `faces` | object |  |  |  | the faces picked for it (a face selector: filters type, normal, along, radius, at, all, count, any_of; see get_help topic selectors). Give count. |
| `edges` | object |  |  |  | the edges picked for it (an edge selector: filters type, parallel, radius, on_faces, not_on_faces, at, all, count, any_of; see get_help topic selectors). Give count. |
| `of` | string |  |  |  | the body the picks are on (default: the active body) |
| `chain` | boolean |  |  |  | edges: the whole closed loop of each picked edge |
| `tool` | object |  |  |  | the tool (see the description) |
| `options` | object |  |  |  | the dialog's tabs (see the description) |
| `generate` | boolean |  | `true` |  | make the toolpath now |
| `label` | string |  |  |  | its name (default: the strategy's, numbered) |

## Answer

A plain sentence, then JSON with: `id`, `name`, `kind`, `title`, `tool`, `state`, `toolpath`. The example below shows a real one.

## Errors

- Without a solid body: `The design has no solid body yet: make one first (create_sketch + extrude, or primitive).`
- Called without arguments, the arguments are refused before anything runs: `Not done: kind is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: drill the plate's two 6 mm holes

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "primitive", "args": {"kind": "box", "plane": "XY", "length": 100, "width": 60, "height": 10}},
  {"tool": "primitive", "args": {"kind": "cylinder", "plane": "XY", "x": 20, "y": 30, "diameter": 6, "height": 10, "operation": "cut"}},
  {"tool": "primitive", "args": {"kind": "cylinder", "plane": "XY", "x": 80, "y": 30, "diameter": 6, "height": 10, "operation": "cut"}},
  {"tool": "cam_setup", "args": {"stock": {"mode": "relative", "offset_mode": "sides_top_bottom", "side": 2, "top": 1}, "wcs": {"origin": "stock_point", "box_point": [-1, -1, 1]}, "post": {"program": "1001", "comment": "plate"}}}
]
```

The call:

```json
{"tool": "cam_operation", "args": {"kind": "drill", "faces": {"type": "cylinder", "radius": 3, "count": 2}, "tool": {"type": "drill", "diameter": 6, "number": 3}}}
```

The answer:

```text
Done: Drill 'Drill1' (id 'CamOp') added to Setup1. Toolpath: 30 mm of cutting, 102 mm of rapid moves, 0:06, lowest cut at Z -11.
{
 "id": "CamOp",
 "name": "Drill1",
 "kind": "drill",
 "title": "Drill",
 "tool": "#3 - 6 mm drill",
 "state": "valid",
 "toolpath": {
  "cut_length": 30.0,
  "rapid_length": 102.0,
  "time_s": 5.96,
  "min_cut_z": -11.0,
  "bounds": [22.0, 32.0, -11.0, 82.0, 32.0, 15.0]
 }
}
```

## More argument examples

- face the stock down to the top of the part:
  `{"kind": "face", "tool": {"type": "flat", "diameter": 10}}`
- cut the part out along its bottom outline in 3 mm steps, held by four tabs:
  `{"kind": "contour2d", "faces": {"normal": [0, 0, -1], "count": 1}, "tool": {"library": "sample:mm", "id": "sample-mm-flat-6"}, "options": {"passes": {"multiple_depths": true, "stepdown": 3}, "geometry": {"tabs": {"on": true, "positioning": "count", "count": 4}}}}`
- drill two 6 mm holes with pecks:
  `{"kind": "drill", "faces": {"type": "cylinder", "radius": 3, "count": 2}, "tool": {"type": "drill", "diameter": 6}, "options": {"passes": {"cycle": "chip_breaking", "peck_depth": 2}}}`

## See also

- Recipe: [mill a pocketed plate on a CNC router (MANUFACTURE)](fission180://docs/recipes/mill-pocketed-plate.md)
- Golden models built with its steps (read one with docs_read golden/<id>): `cam_block_contour3d`, `cam_block_side_setup`, `cam_plate_face_contour_drill`
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
