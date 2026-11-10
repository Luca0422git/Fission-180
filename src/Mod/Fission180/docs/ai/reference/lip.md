# `lip`: Lip

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: PLASTIC > CREATE > Lip. Category: Plastic. Changes the design (one undo step). Its undo step is named like "AI: Lip (lip)". Needs a solid body.
It builds the design step(s) `sf_lip` (the golden models' step language).

## What it does

Fusion's Lip (Lip, Groove or Lip And Groove): a lip on the rim of one half of a plastic part and the matching groove in the other half, so the two locate and seal. edges: the rim's edges (a closed or open chain of edges round the flat parting face, on the body of of: a step id, default the active body); type lip_and_groove (default: the lip here, the groove in the touching body, mate: a step of that body, default found) | lip | groove; swap (the groove here, the lip on the mate); guide pull (the rim face's normal, default) | face. lip_width, lip_height, groove_width, groove_depth, clearance, clearance_height, inner_draft / outer_draft (degrees), tip_radius, root_radius (mm). Sizes left out follow the plastic rule assigned to the design (plastic_rule; Default (mm): 2 mm walls, 1 degree draft, 0.1 mm clearance) and keep following it when it changes.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `edges` (required) | object |  |  |  | the rim's edges (an edge selector: filters type, parallel, radius, on_faces, not_on_faces, at, all, count, any_of; see get_help topic selectors). Give count. |
| `of` | string |  |  |  | the body the edges are on (a step in it) |
| `mate` | string |  |  |  | lip_and_groove: the touching body (a step in it) |
| `type` | `lip_and_groove` \| `lip` \| `groove` |  | `"lip_and_groove"` |  |  |
| `guide` | `pull` \| `face` |  | `"pull"` |  |  |
| `swap` | boolean |  | `false` |  |  |
| `lip_width` | number | mm |  | > 0 | mm |
| `lip_height` | number | mm |  | > 0 | mm |
| `clearance` | number | mm |  | >= 0 | mm |
| `clearance_height` | number | mm |  | >= 0 | mm |
| `groove_width` | number | mm |  | > 0 | mm |
| `groove_depth` | number | mm |  | > 0 | mm |
| `inner_draft` | number | deg |  | >= 0 | (degrees) |
| `outer_draft` | number | deg |  | >= 0 | (degrees) |
| `tip_radius` | number | mm |  | >= 0 | mm |
| `root_radius` | number | mm |  | >= 0 | mm |

## Answer

On success: `Done: <undo title>. Its id is '<id>'. Bodies now: <each solid body's volume in mm3 and size in mm>.` (some steps report no id); then `These steps now fail: ...` when the change broke later steps, and `Warning: no solid changed ...` when it changed no solid at all. On failure nothing changes and the answer is `Not done (<undo title>): <the reason>`.

## Errors

- Without a solid body: `The design has no solid body yet: make one first (create_sketch + extrude, or primitive).`
- Called without arguments, the arguments are refused before anything runs: `Not done: edges is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When Fission 180 cannot build the step (a selector that picks another number of elements than `count`, a size that does not fit, an id that does not exist), the answer is `Not done (<undo title>): <reason>` and nothing changes; [troubleshooting](fission180://docs/troubleshooting.md) lists the usual causes.

## Example 1: a 1 x 1 mm lip on the cylinder's top rim

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "primitive", "args": {"kind": "cylinder", "plane": "XY", "diameter": 16, "height": 10}}
]
```

The call:

```json
{"tool": "lip", "args": {"edges": {"type": "circle", "at": {"axis": "z", "value": "max"}, "count": 1}, "type": "lip", "lip_width": 1, "lip_height": 1}}
```

The answer:

```text
Done: AI: Lip (lip). Its id is 'Lip1'. Bodies now: Body1: 2056.92 mm3, 16 x 16 x 11 mm.
```

## More argument examples

- a 1 x 1 mm lip on the round top rim of a cylinder:
  `{"edges": {"type": "circle", "at": {"axis": "z", "value": "max"}, "count": 1}, "type": "lip", "lip_width": 1, "lip_height": 1}`

## See also

- Golden models built with its steps (read one with docs_read golden/<id>): `plastic2_groove_only`, `plastic2_lip_and_groove`, `plastic2_lip_drafted`, `plastic2_lip_face_guide`, `plastic2_lip_open_chain`, `plastic2_lip_root_radius`, `plastic2_lip_round_rim`, `plastic2_lip_suppress`, `plastic2_lip_swap`, `plastic2_lip_tip_radius`, `plastic2_split_enclosure`
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
