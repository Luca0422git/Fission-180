# `flange`: Flange

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: SHEET METAL > CREATE > Flange. Category: Sheet metal. Changes the design (one undo step). Its undo step is named like "AI: Flange (edge)". Needs an open design.
It builds the design step(s) `sf_flange` (the golden models' step language).

## What it does

Fusion's Flange, the sheet metal body maker, in the active sheet metal rule's thickness. kind base: the closed areas of a sketch (profile; at: [[x, y], ...] a point in each area to use) become a flat plate; orientation side1 (up from the sketch, default) | side2 | centered. kind contour: an open chain of sketch lines and arcs (profile; at: a point on each curve to use, default all) becomes a bent strip, every sharp corner bent with the rule's radius; distance (mm, default 10), direction one_side | symmetric | two_sides (distance2), flip. Base and contour: operation new_body (default) | new_component (a Sheet Metal component) | join (into the active sheet metal body), rule (a new body's rule; default the active one). kind edge: a wall bent up from each sheet edge of the active sheet metal body (edges); height (mm, default 10), angle (degrees, default 90), flip (bend the other way), datum inner | outer | tangent (what height measures to), position inside | outside | adjacent | tangent (where the bend sits against the edge), width_type full | symmetric (width) | two_sides (distance1 before the edge's middle, width2 after it) | two_offsets (distance1 in from the edge's start, width2 from its end, or between offset_refs: two planes); extent to_object with target (a plane the wall runs up to) and target_offset. Edges that meet at a corner are mitred with the rule's gap. Rule overrides (the dialog's check boxes, ticked by giving a value): bend_radius, relief_shape straight | tear | round / relief_width / relief_depth / relief_remnant, corner_shape / corner_placement / corner_size, corner3_shape / corner3_radius. A sheet edge is a straight edge where the sheet's top or bottom face meets a side face as thick as the sheet (on a 1 mm plate on XY, the top face's four edges at z = 1). Fission 180's library rules: Steel (mm), Stainless Steel (mm), Aluminum (mm), Copper (mm), Steel (in), Stainless Steel (in), Aluminum (in), Copper (in) (Steel (mm): 1 mm thick, Aluminum (mm): 1.5 mm; bend radius = Thickness, K factor 0.44), plus the design's own (sheet_metal_rule makes them).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `kind` (required) | `base` \| `contour` \| `edge` |  |  |  |  |
| `profile` | string |  |  |  | base / contour: the sketch |
| `at` | array of arrays |  |  | at least 1 item(s) | base: a point in each area; contour: a point on each curve |
| `edges` | object or array |  |  |  | edge: the sheet edges: an edge selector (get_help topic selectors; give count) or a list of points [x, y, z] (mm, design coordinates), one on each edge (query_geometry's center_mm of a straight edge lies on it) |
| `rule` | string |  |  |  | base / contour, new body: its sheet metal rule |
| `operation` | `new_body` \| `new_component` \| `join` |  | `"new_body"` |  |  |
| `orientation` | `side1` \| `side2` \| `centered` |  | `"side1"` |  |  |
| `direction` | `one_side` \| `symmetric` \| `two_sides` |  | `"one_side"` |  |  |
| `distance` | number | mm | `10` | > 0 | contour: how far the strip runs (mm) |
| `distance2` | number | mm |  | > 0 | contour, two_sides: the other side (mm) |
| `flip` | boolean |  | `false` |  |  |
| `extent` | `distance` \| `to_object` |  | `"distance"` |  |  |
| `height` | number | mm | `10` | > 0 | edge: the wall's height (mm) |
| `datum` | `inner` \| `outer` \| `tangent` |  | `"inner"` |  |  |
| `position` | `inside` \| `outside` \| `adjacent` \| `tangent` |  | `"inside"` |  |  |
| `angle` | number | deg | `90` |  | edge: the bend angle (degrees) |
| `width_type` | `full` \| `symmetric` \| `two_sides` \| `two_offsets` |  | `"full"` |  |  |
| `width` | number | mm |  | > 0 | width_type symmetric: the wall's width (mm) |
| `distance1` | number | mm |  | >= 0 | two_sides / two_offsets: the first distance (mm) |
| `width2` | number | mm |  | >= 0 | two_sides / two_offsets: the second distance (mm) |
| `target` | object |  |  |  | an origin plane moved along its normal |
| `target.plane` (required) | `XY` \| `XZ` \| `YZ` |  |  |  |  |
| `target.offset` | number | mm | `0` |  | along its normal (mm) |
| `target_offset` | number | mm |  |  | extent to_object: the offset from target (mm) |
| `offset_refs` | array of 2 objects |  |  |  | two_offsets: the two reference planes |
| `bend_radius` | number | mm |  | >= 0 | override: the bend's inside radius (mm) |
| `relief_shape` | `straight` \| `tear` \| `round` |  |  |  |  |
| `relief_width` | number | mm |  | > 0 | override: bend relief width (mm) |
| `relief_depth` | number | mm |  | > 0 | override: bend relief depth (mm) |
| `relief_remnant` | number | mm |  | > 0 | override: bend relief remnant (mm) |
| `corner_shape` | `round` \| `square` \| `tear` \| `trim_to_bend` \| `linear_weld` \| `arc_weld` \| `laser_weld` |  |  |  |  |
| `corner_placement` | `intersection` \| `tangent` |  |  |  |  |
| `corner_size` | number | mm |  | > 0 | override: 2-bend corner relief size (mm) |
| `corner3_shape` | `no_replacement` \| `intersection` \| `full_round` \| `round_with_radius` |  |  |  |  |
| `corner3_radius` | number | mm |  | > 0 | override: 3-bend corner relief radius (mm) |
| `name` | string |  |  |  | a descriptive name for the new body (base / contour with operation new_body or new_component), e.g. "Base plate" (required in effect: unnamed bodies and sketches must be renamed before the next change) |

## Answer

On success: `Done: <undo title>. Its id is '<id>'. Bodies now: <each solid body's volume in mm3 and size in mm>.` (some steps report no id); then `These steps now fail: ...` when the change broke later steps, and `Warning: no solid changed ...` when it changed no solid at all. On failure nothing changes and the answer is `Not done (<undo title>): <the reason>`.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: kind is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When Fission 180 cannot build the step (a selector that picks another number of elements than `count`, a size that does not fit, an id that does not exist), the answer is `Not done (<undo title>): <reason>` and nothing changes; [troubleshooting](fission180://docs/troubleshooting.md) lists the usual causes.

## Example 1: 15 mm walls on the four top edges of a 1 mm plate: an open tray

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
{"tool": "flange", "args": {"kind": "edge", "edges": {"type": "line", "at": {"axis": "z", "value": "max"}, "count": 4}, "height": 15}}
```

The answer:

```text
Done: AI: Flange (edge). Its id is 'Flange2'. Bodies now: Body1: 3645.43 mm3, 50 x 30 x 16 mm.
```

## More argument examples

- a 1 mm plate from Sketch1's rectangle:
  `{"kind": "base", "profile": "Sketch1"}`
- 15 mm walls on the plate's four top edges: an open tray with mitred corners:
  `{"kind": "edge", "edges": {"type": "line", "at": {"axis": "z", "value": "max"}, "count": 4}, "height": 15}`
- an aluminium bracket bent along an L drawn in Sketch2, 30 mm wide:
  `{"kind": "contour", "profile": "Sketch2", "distance": 30, "rule": "Aluminum (mm)"}`

## See also

- Golden models built with its steps (read one with docs_read golden/<id>): `sheetmetal_base_flange_join`, `sheetmetal_base_flange_new_component`, `sheetmetal_base_flange_rect`, `sheetmetal_base_flange_side2_rule`, `sheetmetal_contour_flange_l`, `sheetmetal_contour_flange_on_edge`, `sheetmetal_contour_flange_two_sides`, `sheetmetal_edge_flange_adjacent_later`, `sheetmetal_edge_flange_angle_edit`, `sheetmetal_edge_flange_bend_positions`, `sheetmetal_edge_flange_inner_corner`, `sheetmetal_edge_flange_l_bracket` and 60 more
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
