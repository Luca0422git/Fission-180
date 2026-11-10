# `hem`: Hem

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: SHEET METAL > CREATE > Hem. Category: Sheet metal. Changes the design (one undo step). Its undo step is named like "AI: Hem (open)". Needs a solid body.
It builds the design step(s) `sf_sm_hem` (the golden models' step language).

## What it does

Fusion's Hem: fold sheet edges of the active sheet metal body back on themselves (safe edges, stiffening). edges: the sheet edges (a flange's top edge, say). type flat | open (default) | rolled | teardrop | rope | double, and the values each type uses: flat: length; open: length, gap; rolled: radius, angle (degrees); teardrop: radius, length, gap; rope: length, gap, radius; double: gap, length, setback (mm; defaults from the thickness T: length 4 T, gap T / 2, radius 2 T, angle 270). position inside | outside | adjacent | tangent, flip (curl to the other side), miter (default true: two hems meeting at a corner are mitred), bend_radius (overrides the rule's). A sheet edge is a straight edge where the sheet's top or bottom face meets a side face as thick as the sheet (on a 1 mm plate on XY, the top face's four edges at z = 1).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `edges` (required) | object or array |  |  |  | the sheet edges: an edge selector (get_help topic selectors; give count) or a list of points [x, y, z] (mm, design coordinates), one on each edge (query_geometry's center_mm of a straight edge lies on it) |
| `type` | `flat` \| `open` \| `rolled` \| `teardrop` \| `rope` \| `double` |  | `"open"` |  |  |
| `length` | number | mm |  | > 0 | mm |
| `gap` | number | mm |  | > 0 | mm |
| `radius` | number | mm |  | > 0 | the hem's radius (mm) |
| `angle` | number | deg |  |  | rolled: how far it rolls (degrees) |
| `setback` | number | mm |  | >= 0 | double: mm |
| `position` | `inside` \| `outside` \| `adjacent` \| `tangent` |  | `"inside"` |  |  |
| `flip` | boolean |  | `false` |  |  |
| `miter` | boolean |  | `true` |  |  |
| `bend_radius` | number | mm |  | >= 0 | override: the bend's inside radius (mm) |

## Answer

On success: `Done: <undo title>. Its id is '<id>'. Bodies now: <each solid body's volume in mm3 and size in mm>.` (some steps report no id); then `These steps now fail: ...` when the change broke later steps, and `Warning: no solid changed ...` when it changed no solid at all. On failure nothing changes and the answer is `Not done (<undo title>): <the reason>`.

## Errors

- Without a solid body: `The design has no solid body yet: make one first (create_sketch + extrude, or primitive).`
- Called without arguments, the arguments are refused before anything runs: `Not done: edges is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When Fission 180 cannot build the step (a selector that picks another number of elements than `count`, a size that does not fit, an id that does not exist), the answer is `Not done (<undo title>): <reason>` and nothing changes; [troubleshooting](fission180://docs/troubleshooting.md) lists the usual causes.

## Example 1: an open hem on the top edge of a 20 mm wall

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 50, 30]}]}},
  {"tool": "flange", "args": {"kind": "base", "profile": "Sketch1"}},
  {"tool": "flange", "args": {"kind": "edge", "edges": [[50, 15, 1]], "height": 20}}
]
```

The call:

```json
{"tool": "hem", "args": {"edges": [[50, 15, 21]], "type": "open"}}
```

The answer:

```text
Done: AI: Hem (open). Its id is 'Hem1'. Bodies now: Body1: 2196.37 mm3, 51.5 x 30 x 21 mm.
```

## More argument examples

- an open hem on the top edge of a 20 mm flange standing at x = 50:
  `{"edges": [[50, 15, 21]], "type": "open"}`

## See also

- Golden models built with its steps (read one with docs_read golden/<id>): `sheetmetal_smm_hem_after_bend`, `sheetmetal_smm_hem_beside_flange`, `sheetmetal_smm_hem_double`, `sheetmetal_smm_hem_edit_type`, `sheetmetal_smm_hem_flat`, `sheetmetal_smm_hem_miter_two_edges`, `sheetmetal_smm_hem_on_flange`, `sheetmetal_smm_hem_open`, `sheetmetal_smm_hem_rolled`, `sheetmetal_smm_hem_rope`, `sheetmetal_smm_hem_teardrop`, `sheetmetal_smm_reopen_all` and 2 more
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
