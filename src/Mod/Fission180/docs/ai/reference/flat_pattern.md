# `flat_pattern`: Create flat pattern

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: SHEET METAL > CREATE > Create Flat Pattern. Category: Sheet metal. Changes the design (one undo step). Its undo step is named like "AI: Create flat pattern". Needs a solid body.
It builds the design step(s) `sf_flat_pattern` (the golden models' step language).

## What it does

Fusion's Create Flat Pattern: lay a sheet metal body (body; default the active one) flat from a stationary face, every bend developed with the rule's K factor; the flat pattern follows later changes of the folded part (one per component). face: a top or bottom face of a wall (it lies on XY facing up, the sheet below z = 0). Answers the flat size (mm), thickness, K factor and every bend (angle, inside radius, up / down, allowance, its centre line in the flat's XY). export_flat_pattern writes it as DXF.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `face` (required) | object |  |  |  | the stationary face (one) (a face selector: filters type, normal, along, radius, at, all, count, any_of; see get_help topic selectors). Give count. |
| `body` | string |  |  |  | the sheet metal body (default: the active one) |

## Answer

A plain sentence, then JSON with: `id`, `label`, `body`, `stationary_face`, `flat_size_mm`, `bbox_mm`, `thickness_mm`, `k_factor`, `volume_mm3`, `bends`. The example below shows a real one.

## Errors

- Without a solid body: `The design has no solid body yet: make one first (create_sketch + extrude, or primitive).`
- Called without arguments, the arguments are refused before anything runs: `Not done: face is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: the tray laid flat from its floor

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 50, 30]}]}},
  {"tool": "flange", "args": {"kind": "base", "profile": "Sketch1"}},
  {"tool": "flange", "args": {"kind": "edge", "edges": {"type": "line", "at": {"axis": "z", "value": "max"}, "count": 4}, "height": 15}}
]
```

The call:

```json
{"tool": "flat_pattern", "args": {"face": {"type": "plane", "normal": [0, 0, 1], "at": {"axis": "z", "value": "min"}, "count": 1}}}
```

The answer:

```text
Done: AI: Create flat pattern. Its id is 'FlatPattern1': flat 78.5239 x 58.5239 mm, 4 bends. Bodies now: Body1: 3645.43 mm3, 50 x 30 x 16 mm.
{
 "id": "FlatPattern1",
 "label": "Flat Pattern",
 "body": "Body",
 "stationary_face": "Face5",
 "flat_size_mm": [78.5239, 58.5239],
 "bbox_mm": [0.0, 0.0, -1.0, 78.5239, 58.5239, 0.0],
 "thickness_mm": 1.0,
 "k_factor": 0.44,
 "volume_mm3": 3553.4913,
 "bends": [
  {
   "angle_deg": 90.0,
   "inside_radius_mm": 1.0,
   "direction": "up",
   "allowance_mm": 2.261947,
   "centre_line_mm": [[15.969053492, 43.392920066], [62.554839929, 43.392920066]]
  },
  {
   "angle_deg": 90.0,
   "inside_radius_mm": 1.0,
   "direction": "up",
   "allowance_mm": 2.261947,
   "centre_line_mm": [[63.392920066, 42.554839929], [63.392920066, 15.969053492]]
  },
  {
   "angle_deg": 90.0,
   "inside_radius_mm": 1.0,
   "direction": "up",
   "allowance_mm": 2.261947,
   "centre_line_mm": [[62.554839929, 15.130973355], [15.969053492, 15.130973355]]
  },
  {
   "angle_deg": 90.0,
   "inside_radius_mm": 1.0,
   "direction": "up",
   "allowance_mm": 2.261947,
   "centre_line_mm": [[15.130973355, 15.969053492], [15.130973355, 42.554839929]]
  }
 ]
}
```

## More argument examples

- the folded tray laid flat from its floor:
  `{"face": {"type": "plane", "normal": [0, 0, 1], "at": {"axis": "z", "value": "min"}, "count": 1}}`

## See also

- Golden models built with its steps (read one with docs_read golden/<id>): `sm_flat_bend_box`, `sm_flat_bend_roundtrip`, `sm_flat_contour_flange`, `sm_flat_corner_closure`, `sm_flat_corner_closure_tangent`, `sm_flat_edge_flange`, `sm_flat_hem_flat`, `sm_flat_hem_open`, `sm_flat_k_factor`, `sm_flat_l_bracket`, `sm_flat_moved_body`, `sm_flat_partial_relief` and 7 more
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
