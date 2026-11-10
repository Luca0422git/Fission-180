# `bend`: Bend

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: SHEET METAL > CREATE > Bend. Category: Sheet metal. Changes the design (one undo step). Its undo step is named like "AI: Bend 90 deg". Needs a solid body.
It builds the design step(s) `sf_sm_bend` (the golden models' step language).

## What it does

Fusion's Bend: bend the active flat sheet metal body along sketch lines that lie across its top or bottom face (draw them in a sketch on that face, or on its plane). lines: the sketch (every line in it; at: [[x, y], ...] sketch points to use only the lines through them); stationary: a point [x, y, z] (mm) on that top or bottom face, on the side of the lines that stays where it is. angle (degrees, default 90), position start | center | end (where the bend zone lies against the line, default center), flip (bend the other way), bend_relief / corner_relief (default true), bend_radius (overrides the rule's). Several lines are bent farthest from the stationary side first; holes in a bend zone come through bent.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `lines` (required) | string |  |  |  | the sketch with the bend lines |
| `at` | array of arrays |  |  | at least 1 item(s) | sketch points: only the lines through them |
| `stationary` (required) | array of 3 numbers |  |  |  | a point on the face's side that stays |
| `angle` | number | deg | `90` |  | the bend angle (degrees) |
| `position` | `start` \| `center` \| `end` |  | `"center"` |  |  |
| `flip` | boolean |  | `false` |  |  |
| `bend_relief` | boolean |  | `true` |  |  |
| `corner_relief` | boolean |  | `true` |  |  |
| `bend_radius` | number | mm |  | >= 0 | override: the inside radius (mm) |

## Answer

On success: `Done: <undo title>. Its id is '<id>'. Bodies now: <each solid body's volume in mm3 and size in mm>.` (some steps report no id); then `These steps now fail: ...` when the change broke later steps, and `Warning: no solid changed ...` when it changed no solid at all. On failure nothing changes and the answer is `Not done (<undo title>): <the reason>`.

## Errors

- Without a solid body: `The design has no solid body yet: make one first (create_sketch + extrude, or primitive).`
- Called without arguments, the arguments are refused before anything runs: `Not done: lines is missing; stationary is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When Fission 180 cannot build the step (a selector that picks another number of elements than `count`, a size that does not fit, an id that does not exist), the answer is `Not done (<undo title>): <reason>` and nothing changes; [troubleshooting](fission180://docs/troubleshooting.md) lists the usual causes.

## Example 1: fold the right half of a plate up along the line x = 50

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 100, 40]}]}},
  {"tool": "flange", "args": {"kind": "base", "profile": "Sketch1"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 1, "geometry": [{"line": [50, -5, 50, 45]}]}}
]
```

The call:

```json
{"tool": "bend", "args": {"lines": "Sketch2", "stationary": [10, 20, 1], "angle": 90}}
```

The answer:

```text
Done: AI: Bend 90 deg. Its id is 'Bend1'. Bodies now: Body1: 4003.77 mm3, 50.87 x 40 x 50.87 mm.
```

## More argument examples

- fold a 1 mm plate up 90 degrees along Sketch2's line, the left part staying:
  `{"lines": "Sketch2", "stationary": [10, 20, 1], "angle": 90}`

## See also

- Golden models built with its steps (read one with docs_read golden/<id>): `sheetmetal_smm_bend_after_flange`, `sheetmetal_smm_bend_box`, `sheetmetal_smm_bend_center`, `sheetmetal_smm_bend_diagonal`, `sheetmetal_smm_bend_flip_start_45`, `sheetmetal_smm_bend_hole_in_zone`, `sheetmetal_smm_bend_slanted_end`, `sheetmetal_smm_bend_tab`, `sheetmetal_smm_bend_tab_end`, `sheetmetal_smm_bend_two_lines`, `sheetmetal_smm_hem_after_bend`, `sheetmetal_smm_reopen_all` and 2 more
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
