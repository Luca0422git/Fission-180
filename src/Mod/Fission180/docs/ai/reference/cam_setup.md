# `cam_setup`: New setup

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: MANUFACTURE > MILLING > SETUP > New Setup. Category: Manufacture. Changes the design (one undo step). Its undo step is named like "AI: New Setup". Needs a solid body.
It builds the design step(s) `cam_setup` (the golden models' step language).

## What it does

Make a manufacturing setup (Fusion's New Setup): how the part sits on the milling machine and what stock it is cut from. Every operation belongs to a setup; a part machined from two sides has two. bodies: the bodies to machine (default: every solid body). stock: {"mode": "relative" (the model's box plus offsets; offset_mode none | sides_top_bottom with side / top / bottom (mm) | all_sides with all {xn, xp, yn, yp, zn, zp}; round_up) | "fixed" (width, depth, height along X, Y, Z of the setup; x_position / y_position / z_position min | center | max with x_offset / y_offset / z_offset) | "solid" (stock_body: the id of the body that is the stock) | "preceding" (what the setup before this one leaves: its stock, for the second side of a part)}. wcs (the work coordinate system): {"orientation": "model" (the design's Z is up, default) | "z_x" | "z_y" | "x_y" with picks z / x ({"face": selector} whose normal, or {"edge": selector} whose direction is the axis; "of": the body), flip_z, flip_x; "origin": "stock_point" (default) | "model_point" with box_point [x, y, z] each -1 | 0 | 1 (the box's low side, middle, high side: [-1, -1, 1] is the top corner at low X and Y, [0, 0, 1] the top centre) | "model_origin" | "selected" with point {"vertex": [x, y, z]}}. post: {program: its name or number, comment, wcs_offset: 1 = G54 ... 6 = G59}. Defaults: a relative stock 1 mm larger on the sides and the top, the origin at the stock's top centre, Z up as in the design. Answers the setup's id, and its stock and model boxes in the setup's own coordinates (origin and axes of the work coordinate system: toolpath numbers are in these). The design's bodies are never changed by anything in MANUFACTURE.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `bodies` | array of strings |  |  | at least 1 item(s) | the bodies to machine, or components (all their bodies); default: every solid body |
| `stock` | object |  |  |  | the stock (see the description) |
| `wcs` | object |  |  |  | the work coordinate system (see the description) |
| `post` | object |  |  |  | program name / number, comment, wcs_offset |
| `label` | string |  |  |  | its name (default "Setup1", "Setup2"...) |

## Answer

A plain sentence, then JSON with: `id`, `name`, `stock_box`, `model_box`, `origin_in_design`, `z_axis_in_design`, `bodies`, `operations`. The example below shows a real one.

## Errors

- Without a solid body: `The design has no solid body yet: make one first (create_sketch + extrude, or primitive).`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: a plate in stock 2 mm larger around and 1 mm on top, the origin on the stock's top at low X and Y

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "primitive", "args": {"kind": "box", "plane": "XY", "length": 100, "width": 60, "height": 10}},
  {"tool": "primitive", "args": {"kind": "cylinder", "plane": "XY", "x": 20, "y": 30, "diameter": 6, "height": 10, "operation": "cut"}},
  {"tool": "primitive", "args": {"kind": "cylinder", "plane": "XY", "x": 80, "y": 30, "diameter": 6, "height": 10, "operation": "cut"}}
]
```

The call:

```json
{"tool": "cam_setup", "args": {"stock": {"mode": "relative", "offset_mode": "sides_top_bottom", "side": 2, "top": 1}, "wcs": {"origin": "stock_point", "box_point": [-1, -1, 1]}, "post": {"program": "1001", "comment": "plate"}}}
```

The answer:

```text
Done: new setup 'Setup1' (id 'CamSetup'): stock 104 x 64 x 11 mm around a model of 100 x 60 x 10 mm; the origin is at [-2.0, -2.0, 11.0] in the design. Next: cam_operation (cam_tools lists the tool libraries).
{
 "id": "CamSetup",
 "name": "Setup1",
 "stock_box": [0.0, 0.0, -11.0, 104.0, 64.0, 0.0],
 "model_box": [2.0, 2.0, -11.0, 102.0, 62.0, -1.0],
 "origin_in_design": [-2.0, -2.0, 11.0],
 "z_axis_in_design": [0.0, 0.0, 1.0],
 "bodies": ["Body"],
 "operations": []
}
```

## More argument examples

- a setup of every body with the default stock:
  `{}`
- 2 mm of stock around, 1 mm on top; the origin on the stock's top, low X and Y:
  `{"stock": {"mode": "relative", "side": 2, "top": 1, "bottom": 0}, "wcs": {"origin": "stock_point", "box_point": [-1, -1, 1]}, "post": {"program": "1001", "comment": "plate"}}`
- the second side: the part turned over, cut from what the first setup left:
  `{"stock": {"mode": "preceding"}, "wcs": {"orientation": "model", "flip_z": true}}`

## See also

- Golden models built with its steps (read one with docs_read golden/<id>): `cam_block_side_setup`, `cam_plate_face_contour_drill`
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
