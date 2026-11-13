# `decal`: Decal

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: INSERT > Decal. Category: Import and export. Changes the design (one undo step). Its undo step is named like "AI: Decal label.png". Needs an open design.

## What it does

Stick a picture on a face (Fusion's Decal): a label, a logo. It follows the face when the part changes and wraps onto tangent faces (chain_faces). Only the look changes: no geometry, no volume (use emboss or sketch_text + extrude for raised letters). image: a full path; face: a selector of one face of body (default the active body); point: where on the face its middle goes ([x, y, z], default the face's centre); width (mm, height follows) or scale / scale_x / scale_y; dx / dy (mm), angle (degrees), opacity (0..100), flip_h / flip_v. Answers its id, size and the face it is on.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `image` (required) | string |  |  |  | full path of a PNG, JPEG, BMP, GIF or TIFF image |
| `face` (required) | object |  |  |  | the face it goes on (a face selector: filters type, normal, along, radius, at, all, count, any_of; see get_help topic selectors). Give count. |
| `body` | string |  |  |  | the body (default: the active body) |
| `point` | array of 3 numbers | mm |  |  | where on the face its middle goes |
| `width` | number | mm |  | > 0 | its width (mm); the height keeps the picture's proportions |
| `scale` | number |  |  | > 0 | both directions |
| `scale_x` | number |  |  | > 0 | width factor |
| `scale_y` | number |  |  | > 0 | height factor |
| `dx` | number | mm | `0` |  | moved along the face (mm) |
| `dy` | number | mm | `0` |  | moved across the face (mm) |
| `angle` | number | deg | `0` |  | turned on the face (degrees) |
| `opacity` | integer |  | `100` | >= 0, <= 100 | 0 (clear) .. 100 (solid) |
| `chain_faces` | boolean |  | `true` |  | wraps onto tangent faces |
| `flip_h` | boolean |  | `false` |  |  |
| `flip_v` | boolean |  | `false` |  |  |
| `name` | string |  |  |  | its name in the browser |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: image is missing; face is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: an 80 x 40 pixel label, 30 mm wide, on the plate's top

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
{"tool": "decal", "args": {"image": "/home/me/fission180/label.png", "face": {"normal": [0, 0, 1], "at": {"axis": "z", "value": "max"}, "count": 1}, "width": 30}}
```

The answer:

```text
Done: decal 'label' (id 'Decal'), 80 x 40 pixels, 30 x 15 mm on the flat face Face6 of Body1, its middle at [30, 20, 10]; it covers 450 mm2. Only the look changed (no geometry). Bodies now: Body1: 24000 mm3, 60 x 40 x 10 mm.
```

## More argument examples

- a 30 mm wide logo on the top face:
  `{"image": "/home/me/logo.png", "face": {"normal": [0, 0, 1], "count": 1}, "width": 30}`

## See also

- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
