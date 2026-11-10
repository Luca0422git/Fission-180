# `convert_to_sheet_metal`: Convert to sheet metal

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: SHEET METAL > MODIFY > Convert to Sheet Metal. Category: Sheet metal. Changes the design (one undo step). Its undo step is named like "AI: Convert to sheet metal". Needs a solid body.
It builds the design step(s) `sf_sm_convert` (the golden models' step language).

## What it does

Fusion's Convert to Sheet Metal: the active solid body, one sheet of even thickness (made with Shell, Extrude, or imported) with flat walls and round bends, becomes a sheet metal body (its walls the flanges, its round faces the bends) that unfold, rip and the flat pattern work on. face: one flat face of a wall, where the thickness is measured. rule: "template" (default: a new rule from the measured thickness and bend radius) or a rule's name (copied with the measured thickness). Sharp inside corners are refused: fillet them first (an inside radius r needs the outside r + thickness).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `face` (required) | object |  |  |  | one flat face of a wall (a face selector: filters type, normal, along, radius, at, all, count, any_of; see get_help topic selectors). Give count. |
| `rule` | string |  | `"template"` |  | "template" or a rule's name |

## Answer

On success: `Done: <undo title>. Its id is '<id>'. Bodies now: <each solid body's volume in mm3 and size in mm>.` (some steps report no id); then `These steps now fail: ...` when the change broke later steps, and `Warning: no solid changed ...` when it changed no solid at all. On failure nothing changes and the answer is `Not done (<undo title>): <the reason>`.

## Errors

- Without a solid body: `The design has no solid body yet: make one first (create_sketch + extrude, or primitive).`
- Called without arguments, the arguments are refused before anything runs: `Not done: face is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When Fission 180 cannot build the step (a selector that picks another number of elements than `count`, a size that does not fit, an id that does not exist), the answer is `Not done (<undo title>): <reason>` and nothing changes; [troubleshooting](fission180://docs/troubleshooting.md) lists the usual causes.

## Example 1: an even 1 mm U channel becomes sheet metal

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XZ", "geometry": [{"polyline": [[0, 30], [0, 0], [60, 0], [60, 30], [59, 30], [59, 1], [1, 1], [1, 30]]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 20}},
  {"tool": "fillet", "args": {"edges": {"type": "line", "parallel": [0, 1, 0], "at": {"axis": "z", "value": 0}, "count": 2}, "radius": 2}},
  {"tool": "fillet", "args": {"edges": {"type": "line", "parallel": [0, 1, 0], "at": {"axis": "z", "value": 1}, "count": 2}, "radius": 1}}
]
```

The call:

```json
{"tool": "convert_to_sheet_metal", "args": {"face": {"type": "plane", "normal": [0, 0, 1], "at": {"axis": "z", "value": "min"}, "count": 1}}}
```

The answer:

```text
Done: AI: Convert to sheet metal. Its id is 'ConvertToSheetMetal1'. Bodies now: Body1: 2334.25 mm3, 60 x 20 x 30 mm.
```

## More argument examples

- an even 1 mm U channel becomes sheet metal, measured at its floor:
  `{"face": {"type": "plane", "normal": [0, 0, 1], "at": {"axis": "z", "value": "min"}, "count": 1}}`

## See also

- Golden models built with its steps (read one with docs_read golden/<id>): `sm_flat_l_bracket`, `sm_flat_moved_body`, `sm_flat_rip_points`, `sm_flat_rip_tube`, `sm_flat_u_channel_hole`, `sm_flat_unfold_cut_refold`, `sm_flat_unfold_one_bend`
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
