# `export_flat_pattern`: Export flat pattern DXF

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: FLAT PATTERN > EXPORT > Export DXF. Category: Sheet metal. Writes files. Needs a solid body.

## What it does

Write a flat pattern as DXF for a laser or water-jet cutter (Fusion's Export DXF on the FLAT PATTERN tab): the outline and holes on their layers, the bend centre lines (up / down) and extent lines on theirs, with notes. path: a full path (.dxf added); flat_pattern: its id (default: the active body's, or the design's only one); center_lines / extent_lines (default true); splines_to_polylines with tolerance (mm, default 0.1). A file that exists is not replaced unless the person agrees.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `path` (required) | string |  |  |  | the DXF file to write (a full path) |
| `flat_pattern` | string |  |  |  | the flat pattern (or its body) |
| `center_lines` | boolean |  | `true` |  |  |
| `extent_lines` | boolean |  | `true` |  |  |
| `splines_to_polylines` | boolean |  | `false` |  |  |
| `tolerance` | number | mm | `0.1` | > 0 | splines_to_polylines: mm |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without a solid body: `The design has no solid body yet: make one first (create_sketch + extrude, or primitive).`
- Called without arguments, the arguments are refused before anything runs: `Not done: path is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: the tray's flat pattern as DXF for a laser cutter

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 50, 30]}]}},
  {"tool": "flange", "args": {"kind": "base", "profile": "Sketch1"}},
  {"tool": "flange", "args": {"kind": "edge", "edges": {"type": "line", "at": {"axis": "z", "value": "max"}, "count": 4}, "height": 15}},
  {"tool": "flat_pattern", "args": {"face": {"type": "plane", "normal": [0, 0, 1], "at": {"axis": "z", "value": "min"}, "count": 1}}}
]
```

The call:

```json
{"tool": "export_flat_pattern", "args": {"path": "/home/me/fission180/tray-flat.dxf"}}
```

The answer:

```text
Exported /home/me/fission180/tray-flat.dxf: the flat pattern of Body1, 78.5239 x 58.5239 mm, 4 bends (outline and holes, bend lines on their own layers).
```

## More argument examples

- the tray's flat pattern for the laser cutter:
  `{"path": "~/parts/tray-flat.dxf"}`

## See also

- Recipe: [a laser-cut sheet metal bracket and its flat pattern (SHEET METAL)](fission180://docs/recipes/laser-cut-bracket.md)
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
