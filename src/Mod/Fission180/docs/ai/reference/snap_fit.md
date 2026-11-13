# `snap_fit`: Snap fit

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: PLASTIC > CREATE > Snap Fit. Category: Plastic. Changes the design (one undo step). Its undo step is named like "AI: Snap fit (parallel)". Needs a solid body.
It builds the design step(s) `sf_snap_fit` (the golden models' step language).

## What it does

Fusion's Snap Fit: a cantilever hook at each point between two bodies (a lid and its box) and the part it catches on the other body. points: [[x, y], ...] in a sketch on plane (XY | XZ | YZ) moved offset mm along its normal: the parting plane, each point the middle of the beam's catch-side face at its root. type parallel (Hook and Groove: the catch goes into a groove cut in a wall along the beam, default) | perpendicular (the beam passes a slot and hooks under the wall) | loop (Hook and Loop: a frame on the other body). The beam: length, width, thickness, tip_thickness, draft (degrees), fillet (base fillet); the catch: catch_depth, catch_length, insertion_angle, retention_angle; clearance, loop_thickness; extent to_next (base block to the body, default) | distance (extent_distance); rotation uniform (angle) | independent (angles, one per point) | aligned (align_point [x, y, z], align_inward); flip; hook / groove (make each, default true). hook_body / groove_body: a step of the body that gets the hooks / the grooves (default: found as the dialog finds them). All mm and degrees. Sizes left out follow the plastic rule assigned to the design (plastic_rule; Default (mm): 2 mm walls, 1 degree draft, 0.1 mm clearance) and keep following it when it changes.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `points` (required) | array of arrays |  |  | at least 1 item(s) | the hooks' points |
| `plane` | `XY` \| `XZ` \| `YZ` |  | `"XY"` |  | the sketch plane (an origin plane) |
| `offset` | number | mm | `0` |  | the plane moved along its normal (mm) |
| `type` | `parallel` \| `perpendicular` \| `loop` |  | `"parallel"` |  |  |
| `rotation` | `uniform` \| `independent` \| `aligned` |  | `"uniform"` |  |  |
| `angle` | number | deg |  |  | rotation uniform: the catch direction from the sketch's x axis (degrees) |
| `angles` | array of numbers | deg |  |  | rotation independent: one angle per point (degrees) |
| `align_point` | array of 3 numbers |  |  |  | rotation aligned: the catches face this point |
| `align_inward` | boolean |  |  |  | rotation aligned: toward the point (else away) |
| `flip` | boolean |  | `false` |  |  |
| `hook` | boolean |  | `true` |  | make the hooks |
| `groove` | boolean |  | `true` |  | make the grooves / loops |
| `extent` | `to_next` \| `distance` |  | `"to_next"` |  |  |
| `extent_distance` | number | mm |  | > 0 | extent distance: the base block's depth (mm) |
| `length` | number | mm |  | > 0 | the beam's length (mm) |
| `width` | number | mm |  | > 0 | the beam's width (mm) |
| `thickness` | number | mm |  | > 0 | the beam's thickness at its root (mm) |
| `tip_thickness` | number | mm |  | > 0 | the beam's thickness at its tip (mm) |
| `catch_depth` | number | mm |  | > 0 | mm |
| `catch_length` | number | mm |  | > 0 | mm |
| `insertion_angle` | number | deg |  |  | (degrees) |
| `retention_angle` | number | deg |  |  | (degrees) |
| `draft` | number | deg |  | >= 0 | (degrees) |
| `fillet` | number | mm |  | >= 0 | the base fillet's radius (mm) |
| `clearance` | number | mm |  | >= 0 | mm |
| `loop_thickness` | number | mm |  | > 0 | type loop (mm) |
| `hook_body` | string |  |  |  | the body that gets the hooks (a step in it) |
| `groove_body` | string |  |  |  | the body that gets the grooves (a step in it) |
| `name` | string |  |  |  | a descriptive name for what this makes: its sketch of the hook points becomes "<name> sketch", e.g. "Base plate" (required in effect: unnamed bodies and sketches must be renamed before the next change) |

## Answer

On success: `Done: <undo title>. Its id is '<id>'. Bodies now: <each solid body's volume in mm3 and size in mm>.` (some steps report no id); then `These steps now fail: ...` when the change broke later steps, and `Warning: no solid changed ...` when it changed no solid at all. On failure nothing changes and the answer is `Not done (<undo title>): <the reason>`.

## Errors

- Without a solid body: `The design has no solid body yet: make one first (create_sketch + extrude, or primitive).`
- Called without arguments, the arguments are refused before anything runs: `Not done: points is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When Fission 180 cannot build the step (a selector that picks another number of elements than `count`, a size that does not fit, an id that does not exist), the answer is `Not done (<undo title>): <reason>` and nothing changes; [troubleshooting](fission180://docs/troubleshooting.md) lists the usual causes.

## Example 1: a hook under the lid catching in the box's right-hand wall

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 60, 40]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 20}},
  {"tool": "shell", "args": {"faces": {"normal": [0, 0, 1], "count": 1}, "thickness": 2}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 20, "geometry": [{"rect": [0, 0, 60, 40]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch2", "distance": 2, "operation": "new_body"}}
]
```

The call:

```json
{"tool": "snap_fit", "args": {"points": [[58, 20]], "plane": "XY", "offset": 20, "length": 12, "width": 6}}
```

The answer:

```text
Done: AI: Snap fit (parallel). Its id is 'SnapFit1'. Bodies now: Body1: 11690.2 mm3, 60 x 40 x 20 mm; Body2: 4954.65 mm3, 60 x 40 x 14 mm.
```

## More argument examples

- a hook under a lid at z = 20, catching in the box's right-hand wall:
  `{"points": [[58, 20]], "plane": "XY", "offset": 20, "length": 12, "width": 6}`

## See also

- Recipe: [a plastic enclosure with bosses, a lip and a snap fit (PLASTIC)](fission180://docs/recipes/plastic-enclosure.md)
- Golden models built with its steps (read one with docs_read golden/<id>): `plastic2_snap_distance`, `plastic2_snap_edit_taper`, `plastic2_snap_loop`, `plastic2_snap_parallel`, `plastic2_snap_perpendicular`, `plastic2_snap_rolled_back`, `plastic2_snap_skip_point`, `plastic2_snap_two_points`, `plastic2_split_enclosure`
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
