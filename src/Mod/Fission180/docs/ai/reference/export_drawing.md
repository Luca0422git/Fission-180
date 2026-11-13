# `export_drawing`: Export drawing

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: DRAWING > EXPORT > Export PDF / DXF / DWG / CSV. Category: Drawings. Writes files. Needs a drawing.

## What it does

Export a drawing: pdf (sheets all: every sheet in one PDF, or current: the given sheet; needs the Fission 180 window), dxf (the sheet: frame, views on their own layers, dimensions, text; sheets all: one file per sheet, "name - Sheet 2.dxf"), dwg (each sheet's DXF turned into DWG by a converter on this computer: LibreDWG, the ODA File Converter or QCAD; without one it is refused: export dxf) or csv (a table as a spreadsheet file: table its id, default the parts list, else the bend table). Replacing a file must be confirmed by the person. The answer lists what the file does not keep ("Not kept in this file:"), as the drawing's Export message does.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `drawing` | string |  |  |  | the drawing or sheet (default: the newest drawing) |
| `format` (required) | `pdf` \| `dxf` \| `dwg` \| `csv` |  |  |  |  |
| `path` (required) | string |  |  |  | full path |
| `sheets` | `all` \| `current` |  |  |  | pdf: all; dxf / dwg: current (the given sheet) |
| `table` | string |  |  |  | csv: the table (default: the parts list) |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without a drawing: `The design has no drawing yet: call create_drawing first.`
- Called without arguments, the arguments are refused before anything runs: `Not done: format is missing; path is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: the drawing as DXF (PDF needs the window)

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 60, 40], "name": "base"}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 10}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 10, "geometry": [{"circle": [30, 20, 4]}]}},
  {"tool": "hole", "args": {"sketch": "Sketch2", "diameter": 8, "through_all": true}},
  {"tool": "create_drawing", "args": {"base_view": "Front", "projected": ["Top", "Right"]}}
]
```

The call:

```json
{"tool": "export_drawing", "args": {"format": "dxf", "path": "/home/me/fission180/plate.dxf"}}
```

The answer:

```text
Exported Example Drawing to /home/me/fission180/plate.dxf.
Not kept in this file:
- the font of the text (the DXF names none: other programs use their own)
```

## More argument examples

- a PDF of the drawing:
  `{"format": "pdf", "path": "/home/me/bracket.pdf"}`
- the parts list for a spreadsheet:
  `{"format": "csv", "path": "/home/me/parts.csv"}`

## See also

- Recipe: [an assembly drawing with an exploded view, balloons and a parts list](fission180://docs/recipes/assembly-drawing.md)
- Recipe: [a fully dimensioned part drawing](fission180://docs/recipes/part-drawing.md)
- Recipe: [a sheet metal drawing with the flat pattern, a bend table and bend notes](fission180://docs/recipes/sheet-metal-drawing.md)
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
