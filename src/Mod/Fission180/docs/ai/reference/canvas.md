# `canvas`: Canvas

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: INSERT > Canvas. Category: Import and export. Changes the design (one undo step). Its undo step is named like "AI: Canvas photo.png". Needs an open design.

## What it does

Put a reference picture on a plane (Fusion's Canvas): a photo or drawing to sketch over. It is not part of the model (no geometry, not in the timeline). plane: XY | XZ | YZ, {"face": selector} or {"construct": id}; width: its width in mm (calibrate a photo: the real size of what it shows); dx / dy (mm) move it on the plane, angle (degrees); opacity (0..100, default 50), display_through (seen through bodies, default true), flip_h / flip_v. Answers its id and size; create_sketch on the same plane draws over it.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `image` (required) | string |  |  |  | full path of a PNG, JPEG, BMP, GIF or TIFF image |
| `plane` (required) | string or object |  |  |  | where it goes: "XY" \| "XZ" \| "YZ" (an origin plane), {"face": selector} (a flat face of the active body; "of": a step id for another body) or {"construct": id} (a construction plane) |
| `width` | number | mm |  | > 0 | its width (mm); the height keeps the picture's proportions |
| `dx` | number | mm | `0` |  | (mm) |
| `dy` | number | mm | `0` |  | (mm) |
| `angle` | number | deg | `0` |  | (degrees) |
| `opacity` | integer |  | `50` | >= 0, <= 100 | 0 (clear) .. 100 (solid) |
| `display_through` | boolean |  | `true` |  | seen through the bodies in front |
| `flip_h` | boolean |  | `false` |  |  |
| `flip_v` | boolean |  | `false` |  |  |
| `name` | string |  |  |  | its name in the browser |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: image is missing; plane is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: a reference picture 100 mm wide on the XZ plane

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 60, 40], "name": "base"}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 10}}
]
```

The call:

```json
{"tool": "canvas", "args": {"image": "/home/me/fission180/photo.png", "plane": "XZ", "width": 100, "opacity": 40}}
```

The answer:

```text
Done: canvas 'photo' (id 'Canvas'), 80 x 40 pixels shown 100 x 50 mm on XZ-plane, centred at [0, 0, 0], facing [0, -1, 0], 40 % opaque. It is not part of the model; sketch over it with create_sketch on the same plane.
```

## More argument examples

- a side photo, 180 mm wide, behind the XZ plane:
  `{"image": "/home/me/side_photo.jpg", "plane": "XZ", "width": 180, "opacity": 40}`

## See also

- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
