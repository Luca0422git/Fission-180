# `lofted_flange`: Lofted flange

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: SHEET METAL > CREATE > Lofted Flange. Category: Sheet metal. Changes the design (one undo step). Its undo step is named like "AI: Lofted flange". Needs an open design.
It builds the design step(s) `sf_sm_lofted_flange` (the golden models' step language).

## What it does

Fusion's lofted flange: a sheet of the rule's thickness lofted between two profiles on separate planes (both open or both closed, lines and arcs only), like a square-to-round transition. profile1 / profile2: the sketches. forming brake (press-brake facets, default) | die (one smooth surface: it cannot be laid flat); control chord_tolerance (default, value 0.1 mm) | facet_angle (degrees) | facet_distance (mm) | facet_number, value; orientation side1 | side2 | center (which side of the profiles the thickness goes); operation new_body (default) | join (into the active sheet metal body); rule (a new body's rule). Fission 180's library rules: Steel (mm), Stainless Steel (mm), Aluminum (mm), Copper (mm), Steel (in), Stainless Steel (in), Aluminum (in), Copper (in) (Steel (mm): 1 mm thick, Aluminum (mm): 1.5 mm; bend radius = Thickness, K factor 0.44), plus the design's own (sheet_metal_rule makes them).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `profile1` (required) | string |  |  |  | the first profile's sketch |
| `profile2` (required) | string |  |  |  | the second profile's sketch |
| `rule` | string |  |  |  | new body: its sheet metal rule |
| `operation` | `new_body` \| `join` |  | `"new_body"` |  |  |
| `forming` | `brake` \| `die` |  | `"brake"` |  |  |
| `control` | `chord_tolerance` \| `facet_angle` \| `facet_distance` \| `facet_number` |  | `"chord_tolerance"` |  |  |
| `value` | number | mm or deg |  | > 0 | the facet control's value (mm, degrees or a number of facets) |
| `orientation` | `side1` \| `side2` \| `center` |  | `"side1"` |  |  |
| `name` | string |  |  |  | a descriptive name for the new body (several: numbered), e.g. "Base plate" (required in effect: unnamed bodies and sketches must be renamed before the next change) |

## Answer

On success: `Done: <undo title>. Its id is '<id>'. Bodies now: <each solid body's volume in mm3 and size in mm>.` (some steps report no id); then `These steps now fail: ...` when the change broke later steps, and `Warning: no solid changed ...` when it changed no solid at all. On failure nothing changes and the answer is `Not done (<undo title>): <the reason>`.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: profile1 is missing; profile2 is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When Fission 180 cannot build the step (a selector that picks another number of elements than `count`, a size that does not fit, an id that does not exist), the answer is `Not done (<undo title>): <reason>` and nothing changes; [troubleshooting](fission180://docs/troubleshooting.md) lists the usual causes.

## Example 1: a square-to-round transition, its facets within 0.5 mm of the circle

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [-20, -20, 20, 20]}]}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 30, "geometry": [{"circle": [0, 0, 15]}]}}
]
```

The call:

```json
{"tool": "lofted_flange", "args": {"profile1": "Sketch1", "profile2": "Sketch2", "value": 0.5}}
```

The answer:

```text
Done: AI: Lofted flange. Its id is 'LoftedFlange1'. Bodies now: Body2: 3867.85 mm3, 41.81 x 41.86 x 30 mm.
```

## More argument examples

- a square-to-round hopper, facets within 0.5 mm:
  `{"profile1": "Sketch1", "profile2": "Sketch2", "value": 0.5}`

## See also

- Golden models built with its steps (read one with docs_read golden/<id>): `sheetmetal_smm_lofted_brake`, `sheetmetal_smm_lofted_die`, `sheetmetal_smm_lofted_join`, `sheetmetal_smm_lofted_lines`
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
