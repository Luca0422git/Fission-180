# `boss`: Boss

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: PLASTIC > CREATE > Boss. Category: Plastic. Changes the design (one undo step). Its undo step is named like "AI: Boss". Needs a solid body.
It builds the design step(s) `sf_boss` (the golden models' step language).

## What it does

Fusion's Boss: screw bosses joining two halves of a plastic part (an enclosure and its lid). points: [[x, y], ...] the boss centres in a sketch on plane (XY | XZ | YZ) moved offset mm along its normal: put it on the parting plane between the halves. Side 1 (the head side, the screw head's counterbored hole, through) grows along the plane's normal, Side 2 (the thread side, a pilot hole) against it; flip swaps them; each side finds the body behind it. screw: the screw's size in mm (3 = M3, default) sizes both sides; position: moves the parting plane (mm). side1 / side2: any of the dialog's settings for that side. fastener: true adds a simple screw at every boss in a component of its own (head pan | round | flat | hex | hex_washer, length mm, 0 = to the pilot hole's bottom). Sizes left out follow the plastic rule assigned to the design (plastic_rule; Default (mm): 2 mm walls, 1 degree draft, 0.1 mm clearance) and keep following it when it changes.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `points` (required) | array of arrays |  |  | at least 1 item(s) | the boss centres |
| `plane` | `XY` \| `XZ` \| `YZ` |  | `"XY"` |  | the sketch plane (an origin plane) |
| `offset` | number | mm | `0` |  | the plane moved along its normal (mm) |
| `screw` | number | mm | `3` | > 0 | the screw's diameter (mm): 3 = M3 |
| `flip` | boolean |  | `false` |  |  |
| `position` | number | mm | `0` |  | moves the parting plane (mm) |
| `side1` | object |  |  |  | one side's settings (mm, degrees): shape blank \| constant_diameter \| constant_thickness, diameter, wall, draft; hole simple \| counterbore \| countersink, hole_diameter, hole_depth, hole_draft, extent through \| from_top \| from_bottom, major_diameter / major_depth / major_draft (counterbore), countersink_angle; step none \| in \| out (alignment step), step_diameter, step_depth, step_draft; clearance, root_radius, tip_radius; enabled; ribs (true / false), rib_count, rib_total_angle, rib_rotation, rib_thickness, rib_draft, rib_length, rib_extent length \| to_next, rib_offset, rib_profile none \| chamfer \| fillet, rib_cut, rib_chamfer_angle, rib_outer_draft |
| `side2` | object |  |  |  | one side's settings (mm, degrees): shape blank \| constant_diameter \| constant_thickness, diameter, wall, draft; hole simple \| counterbore \| countersink, hole_diameter, hole_depth, hole_draft, extent through \| from_top \| from_bottom, major_diameter / major_depth / major_draft (counterbore), countersink_angle; step none \| in \| out (alignment step), step_diameter, step_depth, step_draft; clearance, root_radius, tip_radius; enabled; ribs (true / false), rib_count, rib_total_angle, rib_rotation, rib_thickness, rib_draft, rib_length, rib_extent length \| to_next, rib_offset, rib_profile none \| chamfer \| fillet, rib_cut, rib_chamfer_angle, rib_outer_draft |
| `fastener` | boolean |  | `false` |  | add the screws (a component of their own) |
| `head` | `pan` \| `round` \| `flat` \| `hex` \| `hex_washer` |  | `"pan"` |  | fastener: the head |
| `length` | number | mm |  | >= 0 | fastener: the screw's length (mm), 0 = auto |
| `name` | string |  |  |  | a descriptive name for what this makes: its sketch of the boss points becomes "<name> sketch" (with fastener, the screws' body "<name>"), e.g. "Base plate" (required in effect: unnamed bodies and sketches must be renamed before the next change) |

## Answer

On success: `Done: <undo title>. Its id is '<id>'. Bodies now: <each solid body's volume in mm3 and size in mm>.` (some steps report no id); then `These steps now fail: ...` when the change broke later steps, and `Warning: no solid changed ...` when it changed no solid at all. On failure nothing changes and the answer is `Not done (<undo title>): <the reason>`.

## Errors

- Without a solid body: `The design has no solid body yet: make one first (create_sketch + extrude, or primitive).`
- Called without arguments, the arguments are refused before anything runs: `Not done: points is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When Fission 180 cannot build the step (a selector that picks another number of elements than `count`, a size that does not fit, an id that does not exist), the answer is `Not done (<undo title>): <reason>` and nothing changes; [troubleshooting](fission180://docs/troubleshooting.md) lists the usual causes.

## Example 1: M3 bosses at two corners where the lid sits on the box

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 60, 40]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 20}},
  {"tool": "shell", "args": {"faces": {"normal": [0, 0, 1], "count": 1}, "thickness": 2}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 20, "geometry": [{"rect": [0, 0, 60, 40]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch2", "distance": 10, "operation": "new_body"}},
  {"tool": "shell", "args": {"faces": {"normal": [0, 0, -1], "count": 1}, "thickness": 2}}
]
```

The call:

```json
{"tool": "boss", "args": {"points": [[10, 10], [50, 30]], "plane": "XY", "offset": 20, "screw": 3}}
```

The answer:

```text
Done: AI: Boss. Its id is 'Boss'. Bodies now: Body1: 13345.6 mm3, 60 x 40 x 20.85 mm; Body2: 8531.15 mm3, 60 x 40 x 10 mm.
```

## More argument examples

- M3 bosses at two corners where a lid sits on a box at z = 20:
  `{"points": [[10, 10], [50, 30]], "plane": "XY", "offset": 20, "screw": 3}`

## See also

- Golden models built with its steps (read one with docs_read golden/<id>): `plastic_boss_alignment_roots`, `plastic_boss_blends`, `plastic_boss_enclosure`, `plastic_boss_fastener`, `plastic_boss_hole_radii`, `plastic_boss_major_draft`, `plastic_boss_ribs_each`, `plastic_rule_boss_wall`, `plastic_rule_edit_moves_boss`
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
