# `join_by_bend`: Join by bend

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: SHEET METAL > CREATE > Join by Bend. Category: Sheet metal. Changes the design (one undo step). Its undo step is named like "AI: Join by bend". Needs a solid body.
It builds the design step(s) `sf_sm_join_bend` (the golden models' step language).

## What it does

Fusion's Join by Bend: one bend joins two sheet metal bodies of the same thickness into one (the active body keeps the step; the other is used up). first: a sheet edge of the active body; other: the other body (any step in it); second: a sheet edge of the other body. Both plates are extended or trimmed so a bend of the rule's radius (or bend_radius) meets each; the bend runs where the two edges overlap. Refused with the reason for different thicknesses, parallel sheets or edges that do not overlap.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `first` (required) | object or array |  |  |  | the active body's sheet edge: an edge selector that picks exactly one edge, or a point [x, y, z] on it (mm, design coordinates) |
| `other` (required) | string |  |  |  | the other sheet metal body (a step in it) |
| `second` (required) | object or array |  |  |  | the other body's sheet edge: an edge selector that picks exactly one edge, or a point [x, y, z] on it (mm, design coordinates) |
| `bend_radius` | number | mm |  | >= 0 | instead of the rule's: the inside radius (mm) |

## Answer

On success: `Done: <undo title>. Its id is '<id>'. Bodies now: <each solid body's volume in mm3 and size in mm>.` (some steps report no id); then `These steps now fail: ...` when the change broke later steps, and `Warning: no solid changed ...` when it changed no solid at all. On failure nothing changes and the answer is `Not done (<undo title>): <the reason>`.

## Errors

- Without a solid body: `The design has no solid body yet: make one first (create_sketch + extrude, or primitive).`
- Called without arguments, the arguments are refused before anything runs: `Not done: first is missing; other is missing; second is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When Fission 180 cannot build the step (a selector that picks another number of elements than `count`, a size that does not fit, an id that does not exist), the answer is `Not done (<undo title>): <reason>` and nothing changes; [troubleshooting](fission180://docs/troubleshooting.md) lists the usual causes.

## Example 1: join a standing plate to a flat one with one bend

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 50, 40]}]}},
  {"tool": "flange", "args": {"kind": "base", "profile": "Sketch1"}},
  {"tool": "create_sketch", "args": {"plane": "YZ", "offset": 60, "geometry": [{"rect": [20, 5, 60, 45]}]}},
  {"tool": "flange", "args": {"kind": "base", "profile": "Sketch2"}}
]
```

The call:

```json
{"tool": "join_by_bend", "args": {"first": [60, 40, 5], "other": "Flange1", "second": [50, 20, 1]}}
```

The answer:

```text
Done: AI: Join by bend. Its id is 'JoinByBend1'. Bodies now: Body1: 2000 mm3, 50 x 40 x 1 mm; Body2: 3887.12 mm3, 61 x 60 x 45 mm.
```

## More argument examples

- join a standing plate at x = 60 to the flat plate Flange1 with one bend:
  `{"first": [60, 40, 5], "other": "Flange1", "second": [50, 20, 1]}`

## See also

- Golden models built with its steps (read one with docs_read golden/<id>): `sheetmetal_smm_join_bend`, `sheetmetal_smm_join_bend_below`, `sheetmetal_smm_join_bend_overlap`
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
