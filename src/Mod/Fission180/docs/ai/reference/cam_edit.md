# `cam_edit`: Edit setup or operation

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: MANUFACTURE > browser > right-click > Edit / Suppress. Category: Manufacture. Changes the design (one undo step). Its undo step is named like "AI: Edit 2D Contour1". Needs a solid body.
It builds the design step(s) `cam_edit` (the golden models' step language).

## What it does

Change a setup or an operation (what a double-click on its browser row opens). target: its id or name. An operation: options (laid over what it has: give only what changes), tool, faces / edges / of / chain (picked again: these replace the old picks), suppressed (true: left out of generate, simulate and post), move (up | down in the machining order), label; its toolpath is made again unless generate is false. A setup: stock / wcs / post (laid over what it has), bodies, suppressed, label; its operations then read "needs regenerating" (cam_generate). stock: {"mode": "relative" (the model's box plus offsets; offset_mode none | sides_top_bottom with side / top / bottom (mm) | all_sides with all {xn, xp, yn, yp, zn, zp}; round_up) | "fixed" (width, depth, height along X, Y, Z of the setup; x_position / y_position / z_position min | center | max with x_offset / y_offset / z_offset) | "solid" (stock_body: the id of the body that is the stock) | "preceding" (what the setup before this one leaves: its stock, for the second side of a part)}. wcs (the work coordinate system): {"orientation": "model" (the design's Z is up, default) | "z_x" | "z_y" | "x_y" with picks z / x ({"face": selector} whose normal, or {"edge": selector} whose direction is the axis; "of": the body), flip_z, flip_x; "origin": "stock_point" (default) | "model_point" with box_point [x, y, z] each -1 | 0 | 1 (the box's low side, middle, high side: [-1, -1, 1] is the top corner at low X and Y, [0, 0, 1] the top centre) | "model_origin" | "selected" with point {"vertex": [x, y, z]}}. tool: either a tool of a library, {"library": "sample:mm" | "sample:in" | "local:<name>" | "document", "id": its id (cam_tools lists them)}, or one described here, {"type": flat | ball | bull | face | chamfer | drill | spot, "diameter": mm} with anything else to set (number, flutes, corner_radius, flute_length, cutting {spindle_speed rpm, cutting_feed, leadin_feed, plunge_feed, ramp_feed mm/min, stepdown, stepover mm}); sizes left out follow from the diameter, speeds and feeds from the tool's size. options: the dialog's tabs as nested objects, only what differs from the defaults: feeds {spindle_speed, cutting_feed, leadin_feed, plunge_feed, ramp_feed} over the tool's own; geometry {flip_side, same_diameter (drill: every hole of the picked diameter), tabs {on, shape rectangular | triangular, width, height, positioning distance | count | points, distance, count, points [[x, y, z], ...]}}; heights {clearance | retract | feed | top | bottom: {"from": model_top | model_bottom | stock_top | stock_bottom | selection | origin | (a higher one of) retract | feed | top | bottom, "offset": mm}}; passes {tolerance, direction climb | conventional, compensation computer | off, stepover, optimal_load, multiple_depths, stepdown, finishing_passes, finishing_stepover, stock_to_leave, radial_stock, axial_stock, pass_angle, pass_extension, both_ways, chamfer_width, chamfer_tip_offset, cycle drilling | counterboring | chip_breaking | deep_drilling, peck_depth, dwell, tip_through, break_through, pitch}; linking {lead_in, lead_out, lead_radius, ramp plunge | helix | profile | zigzag, ramp_angle, helix_diameter, keep_down}.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `target` (required) | string |  |  |  | the setup's or the operation's id or name |
| `options` | object |  |  |  | an operation's options to change |
| `tool` | object |  |  |  | an operation's new tool |
| `faces` | object |  |  |  | an operation's faces, picked again (a face selector: filters type, normal, along, radius, at, all, count, any_of; see get_help topic selectors). Give count. |
| `edges` | object |  |  |  | an operation's edges, picked again (an edge selector: filters type, parallel, radius, on_faces, not_on_faces, at, all, count, any_of; see get_help topic selectors). Give count. |
| `of` | string |  |  |  | the body the new picks are on (default: the active body) |
| `chain` | boolean |  |  |  | edges: the whole closed loop of each picked edge |
| `stock` | object |  |  |  | a setup's stock values to change |
| `wcs` | object |  |  |  | a setup's work coordinate system values to change |
| `post` | object |  |  |  | a setup's program name / number, comment, wcs_offset |
| `bodies` | array of strings |  |  | at least 1 item(s) | a setup's bodies to machine |
| `suppressed` | boolean |  |  |  | leave it out (true) or bring it back (false) |
| `move` | `up` \| `down` |  |  |  | an operation one place up or down in its setup |
| `label` | string |  |  |  | its new name |
| `generate` | boolean |  | `true` |  | an operation: make its toolpath again |

## Answer

A plain sentence, then JSON with: `id`, `name`, `kind`, `title`, `tool`, `state`, `toolpath`. The example below shows a real one.

## Errors

- Without a solid body: `The design has no solid body yet: make one first (create_sketch + extrude, or primitive).`
- Called without arguments, the arguments are refused before anything runs: `Not done: target is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: cut the outline in steps of 4 mm; the toolpath is made again

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
{"tool": "cam_edit", "args": {"target": "2D Contour1", "options": {"passes": {"multiple_depths": true, "stepdown": 4}}}}
```

The answer:

```text
Done: 2D Contour1 changed. Toolpath: 1032.549 mm of cutting, 26 mm of rapid moves, 1:03, lowest cut at Z -11.
{
 "id": "CamOp001",
 "name": "2D Contour1",
 "kind": "contour2d",
 "title": "2D Contour",
 "tool": "#6 - 6 mm flat end mill",
 "state": "valid",
 "toolpath": {
  "cut_length": 1032.549,
  "rapid_length": 26.0,
  "time_s": 62.93,
  "min_cut_z": -11.0,
  "bounds": [-1.0, -1.0, -11.0, 105.0, 65.0, 15.0]
 }
}
```

## More argument examples

- a smaller step down; the toolpath is made again:
  `{"target": "2D Contour1", "options": {"passes": {"stepdown": 2}}}`
- 2 mm of stock on top:
  `{"target": "Setup1", "stock": {"top": 2}}`
- leave the drilling out:
  `{"target": "Drill1", "suppressed": true}`

## See also

- Golden models built with its steps (read one with docs_read golden/<id>): `cam_block_side_setup`
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
