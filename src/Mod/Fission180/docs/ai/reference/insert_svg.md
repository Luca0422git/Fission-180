# `insert_svg`: Insert SVG / DXF

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: INSERT > Insert SVG (and Insert DXF with its placement). Category: Import and export. Changes the design (one undo step). Its undo step is named like "AI: Insert logo.svg". Needs an open design.

## What it does

Bring the curves of an SVG (or DXF) file into a sketch (Fusion's Insert SVG / Insert DXF), ready to extrude, emboss or cut: logos, outlines from a drawing program. plane (XY | XZ | YZ | {"face": sel} | {"construct": id}: a new sketch there) or sketch (an existing one); an SVG is centred on the sketch origin, a DXF keeps its own origin; dx / dy (mm), angle (degrees), scale, flip_h / flip_v; unit (DXF: the file's unit). The curves are fixed. Answers the sketch, the curve count, its size and its closed areas.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `path` (required) | string |  |  |  | full path of the .svg or .dxf file |
| `plane` | string or object |  |  |  | where it goes: "XY" \| "XZ" \| "YZ" (an origin plane), {"face": selector} (a flat face of the active body; "of": a step id for another body) or {"construct": id} (a construction plane) |
| `sketch` | string |  |  |  | an existing sketch to add the curves to |
| `dx` | number | mm | `0` |  | (mm) |
| `dy` | number | mm | `0` |  | (mm) |
| `angle` | number | deg | `0` |  | (degrees) |
| `scale` | number |  | `1` | > 0 | size factor |
| `flip_h` | boolean |  | `false` |  |  |
| `flip_v` | boolean |  | `false` |  |  |
| `unit` | `mm` \| `cm` \| `m` \| `in` \| `ft` |  |  |  | DXF: the file's unit |
| `name` | string |  |  |  | the new sketch's name |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: path is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: an SVG's rectangle and circle in a new sketch on XY

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}}
]
```

The call:

```json
{"tool": "insert_svg", "args": {"path": "/home/me/fission180/logo.svg", "plane": "XY", "name": "Logo"}}
```

The answer:

```text
Done: 5 curves of logo.svg in the sketch 'Logo' (id 'Sketch'), fixed in place, 30 x 20 mm (sketch x -15 .. 15, y -10 .. 10); 2 closed areas. Next: extrude with profile Sketch (or emboss). No solid body yet.
```

## More argument examples

- a logo's outline on the top face:
  `{"path": "/home/me/logo.svg", "plane": {"face": {"normal": [0, 0, 1], "count": 1}}}`

## See also

- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
