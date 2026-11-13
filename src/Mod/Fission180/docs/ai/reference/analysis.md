# `analysis`: Surface analysis

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: INSPECT > Draft / Minimum Radius / Curvature Map / Accessibility / Zebra / Environmental Map / Curvature Comb / Isocurve Analysis. Category: Inspect and measure. Read-only. Needs an open design.

## What it does

INSPECT's analyses as numbers (nothing is left in the design). draft: each face's draft angle against direction (pull, default Z), the faces under draft_min (degrees, default 1) with refs; minimum_radius: the tightest inner round and where, faces under min_radius (mm); curvature_map: the tightest bends (under min_radius flagged); accessibility: the share of area a tool along direction reaches, blocked faces; zebra / environment_map: edges where faces meet with a crease or a curvature jump (what stripes show); curvature_comb (edges): curvature along them; isocurve (faces): along U / V. bodies (default every visible one), faces. picture: true adds a render with the faces found in orange. On a 1,500-face part about 2 s; accessibility 14 s; a picture 25 s.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `kind` (required) | `draft` \| `minimum_radius` \| `curvature_map` \| `accessibility` \| `zebra` \| `environment_map` \| `curvature_comb` \| `isocurve` |  |  |  |  |
| `bodies` | array of strings |  |  | at least 1 item(s) | the bodies (default: every visible solid) |
| `faces` | object |  |  |  | only these faces (isocurve: the faces) (a face selector: filters type, normal, along, radius, at, all, count, any_of; see get_help topic selectors). Give count. |
| `edges` | object |  |  |  | curvature_comb: the edges (an edge selector: filters type, parallel, radius, on_faces, not_on_faces, at, all, count, any_of; see get_help topic selectors). Give count. |
| `direction` | string or array or object |  |  |  | draft / accessibility: the pull or tool direction: X, Y, Z, [x, y, z], an origin plane (its normal) or {"face": sel} / {"edge": sel} |
| `flip` | boolean |  | `false` |  | the direction the other way |
| `draft_min` | number | deg | `1` | >= 0 | below this draft a face is flagged (degrees) |
| `draft_ok` | number | deg | `3` | >= 0 | from this draft on a face is fine (degrees) |
| `min_radius` | number | mm | `1` | > 0 | minimum_radius: rounds tighter are flagged (mm) |
| `tool_radius` | number | mm | `5` | > 0 | minimum_radius: a cutter of this radius fits (mm) |
| `include_sharp` | boolean |  | `false` |  | minimum_radius: sharp inner edges count |
| `access` | `direction` \| `opposite` \| `both` |  | `"direction"` |  |  |
| `iso_count` | integer |  | `5` | >= 1, <= 50 | isocurve: lines per direction |
| `picture` | boolean |  | `false` |  | add a picture with the flagged faces in orange |
| `limit` | integer |  | `20` | >= 1, <= 200 | most rows per list |

## Answer

A plain sentence, then JSON with: `pull`, `draft_min_deg`, `draft_ok_deg`, `classes`, `bodies`, `kind`, `seconds`. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: kind is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: the faces without draft for a mould opening along Z

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 60, 40], "name": "base"}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 10}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 10, "geometry": [{"circle": [30, 20, 4]}]}},
  {"tool": "hole", "args": {"sketch": "Sketch2", "diameter": 8, "through_all": true}}
]
```

The call:

```json
{"tool": "analysis", "args": {"kind": "draft", "direction": "Z", "draft_min": 1}}
```

The answer:

```text
Draft along [0, 0, 1]: 5 faces under 1 degree(s) (no draft), 0 between 1 and 3 degrees. Next: draft with those faces (refs) and the pull direction.
{
 "pull": [0.0, 0.0, 1.0],
 "draft_min_deg": 1.0,
 "draft_ok_deg": 3.0,
 "classes": {
  "along": "draft >= draft_ok along the pull (green)",
  "against": "draft >= draft_ok against the pull: the other mould half (blue)",
  "under_min": "|draft| < draft_min: no draft, will not release (red)",
  "between": "draft_min <= |draft| < draft_ok (yellow)"
 },
 "bodies": [
  {
   "body": "Body",
   "label": "Body1",
   "faces_by_worst_class": {"along": 1, "against": 1, "under_min": 5, "between": 0},
   "area_mm2_by_class": {"along": 2349.735, "against": 2349.735, "under_min": 2251.327, "between": 0.0},
   "flagged_faces": [
    {
     "face": "Face1",
     "type": "plane",
     "area_mm2": 600.0,
     "draft_deg": [0.0, 0.0],
     "flag": "under_min",
     "share_under_min": 1.0,
     "ref": {"type": "plane", "normal": [0.0, -1.0, 0.0], "count": 1, "body": "Body"}
    },
    {
     "face": "Face6",
     "type": "plane",
     "area_mm2": 600.0,
     "draft_deg": [0.0, 0.0],
     "flag": "under_min",
     "share_under_min": 1.0,
     "ref": {"type": "plane", "normal": [0.0, 1.0, 0.0], "count": 1, "body": "Body"}
    },
    {
     "face": "Face2",
     "type": "plane",
     "area_mm2": 400.0,
     "draft_deg": [0.0, 0.0],
     "flag": "under_min",
     "share_under_min": 1.0,
     "ref": {"type": "plane", "normal": [-1.0, 0.0, 0.0], "count": 1, "body": "Body"}
    },
    {
     "face": "Face3",
     "type": "plane",
     "area_mm2": 400.0,
     "draft_deg": [0.0, 0.0],
     "flag": "under_min",
     "share_under_min": 1.0,
     "ref": {"type": "plane", "normal": [1.0, 0.0, 0.0], "count": 1, "body": "Body"}
    },
    {
     "face": "Face7",
     "type": "cylinder",
     "area_mm2": 251.327,
     "draft_deg": [0.0, 0.0],
     "flag": "under_min",
     "share_under_min": 1.0,
     "ref": {"type": "cylinder", "radius": 4.0, "count": 1, "body": "Body"}
    }
   ],
   "more": 0
  }
 ],
 "kind": "draft",
 "seconds": 0.015
}
```

## More argument examples

- which faces lack 1 degree of draft for a mould opening along Z:
  `{"kind": "draft", "direction": "Z", "draft_min": 1}`
- inner rounds a 3 mm cutter cannot cut:
  `{"kind": "minimum_radius", "min_radius": 3}`

## See also

- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
