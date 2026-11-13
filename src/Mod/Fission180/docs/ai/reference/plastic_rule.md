# `plastic_rule`: Assign plastic rule

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: PLASTIC > SETUP > Assign Plastic Rule / Manage Plastic Rules. Category: Plastic. Changes the design (one undo step). Its undo step is named like "AI: Plastic rule PC 2 mm". Needs an open design.
It builds the design step(s) `sf_plastic_rule` (the golden models' step language).

## What it does

Assign a plastic rule to the design (Fusion's Assign Plastic Rule): the wall thickness, draft, radii, clearance and limits that Boss, Snap Fit, Lip, Rest and Design Advice start from, and the material the bodies get. rule: a library rule (Default (mm), Default (in), ABS 2 mm, ABS 1.5 mm, PC 2 mm, PC/ABS 2 mm, PP 1.5 mm, PA66 1.5 mm, POM 1.5 mm, HIPS 2 mm, HDPE 2 mm, PBT 1.8 mm, PMMA 2.5 mm, TPE 1.5 mm, FDM PLA 2 mm, FDM PETG 2 mm) or one of the design's (a library rule is copied into the design). set: change the design's copy (Manage Plastic Rules > Edit): material, thickness, draft_angle, nominal_radius, reveal_height, clearance, minimum_thickness, maximum_thickness, thickness_variation (%), minimum_draft_angle, knife_edge_threshold; lengths in mm or text in Thickness ("Thickness / 2"). Bosses, snap fits, lips and rests whose sizes follow the rule update. Answers the rule's values.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `rule` (required) | string |  |  |  | the rule's name |
| `set` | object |  |  |  | the design's copy of the rule: fields to change |
| `set.material` | string |  |  |  | the material's name |
| `set.thickness` | number or string |  |  |  | a number (mm or degrees, a percentage for thickness_variation), or an expression in Thickness for a length |
| `set.draft_angle` | number or string |  |  |  | a number (mm or degrees, a percentage for thickness_variation), or an expression in Thickness for a length |
| `set.nominal_radius` | number or string |  |  |  | a number (mm or degrees, a percentage for thickness_variation), or an expression in Thickness for a length |
| `set.reveal_height` | number or string |  |  |  | a number (mm or degrees, a percentage for thickness_variation), or an expression in Thickness for a length |
| `set.clearance` | number or string |  |  |  | a number (mm or degrees, a percentage for thickness_variation), or an expression in Thickness for a length |
| `set.minimum_thickness` | number or string |  |  |  | a number (mm or degrees, a percentage for thickness_variation), or an expression in Thickness for a length |
| `set.maximum_thickness` | number or string |  |  |  | a number (mm or degrees, a percentage for thickness_variation), or an expression in Thickness for a length |
| `set.thickness_variation` | number or string |  |  |  | a number (mm or degrees, a percentage for thickness_variation), or an expression in Thickness for a length |
| `set.minimum_draft_angle` | number or string |  |  |  | a number (mm or degrees, a percentage for thickness_variation), or an expression in Thickness for a length |
| `set.knife_edge_threshold` | number or string |  |  |  | a number (mm or degrees, a percentage for thickness_variation), or an expression in Thickness for a length |

## Answer

A plain sentence, then JSON with: `rule`, `assigned_to`, `design_rules`. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: rule is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: polycarbonate, 2 mm walls

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}}
]
```

The call:

```json
{"tool": "plastic_rule", "args": {"rule": "PC 2 mm"}}
```

The answer:

```text
Done: AI: Plastic rule PC 2 mm. No solid body yet.
{
 "rule": {
  "name": "PC 2 mm",
  "units": "mm",
  "material": "Polycarbonate",
  "thickness": "2.0",
  "draft_angle": "1.0",
  "nominal_radius": "Thickness / 2",
  "reveal_height": "Thickness / 2",
  "clearance": "0.1",
  "minimum_thickness": "1.0",
  "maximum_thickness": "3.8",
  "thickness_variation": "25",
  "minimum_draft_angle": "0.5",
  "knife_edge_threshold": "Thickness / 4",
  "values": {
   "thickness": 2.0,
   "nominal_radius": 1.0,
   "reveal_height": 1.0,
   "clearance": 0.1,
   "minimum_thickness": 1.0,
   "maximum_thickness": 3.8,
   "knife_edge_threshold": 0.5,
   "draft_angle": 1.0,
   "thickness_variation": 25.0,
   "minimum_draft_angle": 0.5
  }
 },
 "assigned_to": "the design (its root component)",
 "design_rules": ["PC 2 mm"]
}
```

## More argument examples

- polycarbonate, 2 mm walls:
  `{"rule": "PC 2 mm"}`
- ABS with 2.5 mm walls and 0.15 mm clearance:
  `{"rule": "ABS 2 mm", "set": {"thickness": 2.5, "clearance": 0.15}}`

## See also

- Recipe: [a plastic enclosure with bosses, a lip and a snap fit (PLASTIC)](fission180://docs/recipes/plastic-enclosure.md)
- Golden models built with its steps (read one with docs_read golden/<id>): `plastic_rule_boss_wall`, `plastic_rule_edit_moves_boss`
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
