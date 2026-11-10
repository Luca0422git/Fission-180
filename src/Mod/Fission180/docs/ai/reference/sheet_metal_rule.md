# `sheet_metal_rule`: Sheet metal rule

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: SHEET METAL > MODIFY > Sheet Metal Rules. Category: Sheet metal. Changes the design (one undo step). Its undo step is named like "AI: Sheet metal rule Steel 0.5". Needs an open design.
It builds the design step(s) `sf_sheet_rule` (the golden models' step language).

## What it does

Add or change a sheet metal rule In This Design (Fusion's Sheet Metal Rules): the thickness, bend radius, K factor, miter / rip / seam gap and the reliefs that every flange, bend and flat pattern of a body following it uses. rule: its name. from: start it from another rule (a library rule or one of the design's); without from the design's rule of that name is changed (or a new one made with Steel (mm)'s values). set: {field: value}: thickness, bend_radius, k_factor (0..1), miter_gap, bend_relief_shape / width / depth / remnant, corner_relief_2bend_shape / placement / size, corner_relief_3bend_shape / radius, units (a new rule only); lengths are numbers in the rule's units or text in Thickness ("Thickness * 2"). active: true makes it the rule new flanges start with. Editing a rule that bodies follow rebuilds them. Fission 180's library rules: Steel (mm), Stainless Steel (mm), Aluminum (mm), Copper (mm), Steel (in), Stainless Steel (in), Aluminum (in), Copper (in) (Steel (mm): 1 mm thick, Aluminum (mm): 1.5 mm; bend radius = Thickness, K factor 0.44), plus the design's own (sheet_metal_rule makes them). Answers the rule's values and the design's rules.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `rule` (required) | string |  |  |  | the rule's name |
| `from` | string |  |  |  | start from this rule (library or design) |
| `set` | object |  |  |  | the rule's fields to set |
| `set.units` | `mm` \| `in` |  |  |  | only for a new rule |
| `set.thickness` | number or string |  |  |  | a number in the rule's units, or an expression in Thickness |
| `set.bend_radius` | number or string |  |  |  | a number in the rule's units, or an expression in Thickness |
| `set.k_factor` | number | 0..1 |  |  | 0..1: where the neutral fibre lies in the thickness |
| `set.miter_gap` | number or string |  |  |  | a number in the rule's units, or an expression in Thickness |
| `set.bend_relief_shape` | `straight` \| `tear` \| `round` |  |  |  |  |
| `set.bend_relief_width` | number or string |  |  |  | a number in the rule's units, or an expression in Thickness |
| `set.bend_relief_depth` | number or string |  |  |  | a number in the rule's units, or an expression in Thickness |
| `set.bend_relief_remnant` | number or string |  |  |  | a number in the rule's units, or an expression in Thickness |
| `set.corner_relief_2bend_shape` | `round` \| `square` \| `tear` \| `trim_to_bend` \| `linear_weld` \| `arc_weld` \| `laser_weld` |  |  |  |  |
| `set.corner_relief_2bend_placement` | `intersection` \| `tangent` |  |  |  |  |
| `set.corner_relief_2bend_size` | number or string |  |  |  | a number in the rule's units, or an expression in Thickness |
| `set.corner_relief_3bend_shape` | `no_replacement` \| `intersection` \| `full_round` \| `round_with_radius` |  |  |  |  |
| `set.corner_relief_3bend_radius` | number or string |  |  |  | a number in the rule's units, or an expression in Thickness |
| `active` | boolean |  | `false` |  | make it the active rule |

## Answer

A plain sentence, then JSON with: `rule`, `active_rule`, `design_rules`, `sheet_metal_bodies`. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: rule is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: a 0.5 mm steel rule, the one the next flanges start with

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}}
]
```

The call:

```json
{"tool": "sheet_metal_rule", "args": {"rule": "Steel 0.5", "from": "Steel (mm)", "set": {"thickness": 0.5}, "active": true}}
```

The answer:

```text
Done: AI: Sheet metal rule Steel 0.5. No solid body yet.
{
 "rule": {
  "name": "Steel 0.5",
  "units": "mm",
  "thickness": "0.5",
  "bend_radius": "Thickness",
  "k_factor": "0.44",
  "unfold_rule": "k_factor",
  "miter_gap": "Thickness",
  "bend_relief_shape": "round",
  "bend_relief_width": "Thickness",
  "bend_relief_depth": "Thickness / 2",
  "bend_relief_remnant": "Thickness * 2",
  "corner_relief_2bend_shape": "round",
  "corner_relief_2bend_placement": "intersection",
  "corner_relief_2bend_size": "Thickness * 4",
  "corner_relief_3bend_shape": "round_with_radius",
  "corner_relief_3bend_radius": "Thickness * 4",
  "in_mm": {
   "thickness": 0.5,
   "bend_radius": 0.5,
   "miter_gap": 0.5,
   "bend_relief_width": 0.5,
   "bend_relief_depth": 0.25,
   "bend_relief_remnant": 1.0,
   "corner_relief_2bend_size": 2.0,
   "corner_relief_3bend_radius": 2.0
  }
 },
 "active_rule": "Steel 0.5",
 "design_rules": ["Steel (mm)", "Steel 0.5"],
 "sheet_metal_bodies": []
}
```

## More argument examples

- a 0.5 mm steel rule, active for the next flanges:
  `{"rule": "Steel 0.5", "from": "Steel (mm)", "set": {"thickness": 0.5, "bend_radius": "Thickness"}, "active": true}`

## See also

- Golden models built with its steps (read one with docs_read golden/<id>): `sheetmetal_base_flange_side2_rule`, `sheetmetal_rule_edit_recomputes`, `sm_flat_k_factor`, `sm_flat_moved_body`, `sm_flat_thickness_change`, `sm_flat_thickness_follow`
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
