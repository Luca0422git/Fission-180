# `sheet_metal_chamfer`: Sheet metal chamfer

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: SHEET METAL > MODIFY > Chamfer. Category: Sheet metal. Changes the design (one undo step). Its undo step is named like "AI: Sheet metal chamfer 3 mm". Needs a solid body.
It builds the design step(s) `sf_sm_chamfer` (the golden models' step language).

## What it does

Fusion's sheet metal chamfer: chamfer the corners of the active sheet metal body's plates, i.e. only edges that run straight through the sheet's thickness (the part can still be laid flat; any other edge is refused with the reason). edges and distance (mm), or sets: [{edges, distance}, ...] with a size each. The corner edges of a 1 mm plate on XY are its 4 edges parallel to Z: {"type": "line", "parallel": [0, 0, 1], "count": 4}.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `edges` | object or array |  |  |  | the corner edges: an edge selector (get_help topic selectors; give count) or a list of points [x, y, z] (mm, design coordinates), one on each edge (query_geometry's center_mm of a straight edge lies on it) |
| `distance` | number | mm |  | > 0 | mm |
| `sets` | array of objects |  |  | at least 1 item(s) | several sets, each with its own distance |

## Answer

On success: `Done: <undo title>. Its id is '<id>'. Bodies now: <each solid body's volume in mm3 and size in mm>.` (some steps report no id); then `These steps now fail: ...` when the change broke later steps, and `Warning: no solid changed ...` when it changed no solid at all. On failure nothing changes and the answer is `Not done (<undo title>): <the reason>`.

## Errors

- Without a solid body: `The design has no solid body yet: make one first (create_sketch + extrude, or primitive).`
- Called without arguments, the arguments are refused before anything runs: `Not done: give edges and distance, or sets (one or the other).`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When Fission 180 cannot build the step (a selector that picks another number of elements than `count`, a size that does not fit, an id that does not exist), the answer is `Not done (<undo title>): <reason>` and nothing changes; [troubleshooting](fission180://docs/troubleshooting.md) lists the usual causes.

## Example 1: chamfer the plate's four corners

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 50, 30]}]}},
  {"tool": "flange", "args": {"kind": "base", "profile": "Sketch1"}}
]
```

The call:

```json
{"tool": "sheet_metal_chamfer", "args": {"edges": {"type": "line", "parallel": [0, 0, 1], "count": 4}, "distance": 3}}
```

The answer:

```text
Done: AI: Sheet metal chamfer 3 mm. Its id is 'SheetMetalChamfer1'. Bodies now: Body1: 1482 mm3, 50 x 30 x 1 mm.
```

## More argument examples

- chamfer the four corners of a plate:
  `{"edges": {"type": "line", "parallel": [0, 0, 1], "count": 4}, "distance": 3}`

## See also

- Golden models built with its steps (read one with docs_read golden/<id>): `sheetmetal_smm_fillet_chamfer`
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
