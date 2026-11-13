# `add_drawing_symbol`: Add drawing symbol

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: DRAWING > SYMBOLS > Surface Texture, Feature Control Frame, Datum Identifier. Category: Drawings. Changes the design (one undo step). Its undo step is named like "AI: Drawing datum identifier". Needs a drawing.

## What it does

A symbol on a view's edge (pick: {kind, near} in the view's own mm), placed at [x, y] on the sheet (on the edge, or away with a leader; default 12 mm out from the edge): surface_texture (texture basic | removal | no_removal, value "Ra 3.2", lay, all_around), feature_control_frame (GD&T: characteristic position, flatness, perpendicularity..., tolerance mm, diameter_zone, material M | L, datums ["A", "B"], second_row for a composite frame; without view and pick it stands alone) or datum_identifier (letter, default the next free one). One undo step each.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `kind` (required) | `surface_texture` \| `feature_control_frame` \| `datum_identifier` |  |  |  |  |
| `drawing` | string |  |  |  | a frame alone: the drawing or sheet (default: the newest) |
| `view` | string |  |  |  | the view |
| `pick` | object |  |  |  | the edge it stands on |
| `pick.kind` | `line` \| `circle` \| `arc` \| `vertex` |  |  |  |  |
| `pick.near` | array of 2 numbers | mm |  |  | [x, y] in the view's own mm: model size (not scaled) from the view's centre, x right, y up, as get_drawing with edges true lists its elements |
| `pick.radius` | number | mm |  | > 0 | circles / arcs: the radius (model mm) |
| `at` | array of 2 numbers | mm |  |  | [x, y] on the sheet (mm from its bottom left corner) (default: 12 mm out from the edge) |
| `texture` | `basic` \| `removal` \| `no_removal` |  | `"removal"` |  | the symbol |
| `value` | string |  |  |  | roughness, e.g. "Ra 3.2" |
| `lay` | `` \| `=` \| `⊥` \| `X` \| `M` \| `C` \| `R` \| `P` |  |  |  | lay direction symbol |
| `all_around` | boolean |  |  |  |  |
| `characteristic` | `position` \| `concentricity` \| `symmetry` \| `parallelism` \| `perpendicularity` \| `angularity` \| `cylindricity` \| `flatness` \| `circularity` \| `straightness` \| `profile_surface` \| `profile_line` \| `circular_runout` \| `total_runout` |  | `"position"` |  |  |
| `tolerance` | number | mm | `0.1` | > 0 | the zone (mm) |
| `diameter_zone` | boolean |  |  |  | a round zone (⌀) |
| `material` | `` \| `M` \| `L` |  |  |  | M maximum / L least material condition |
| `datums` | array of strings |  |  | at least 0 item(s), at most 3 item(s) | datum letters, e.g. ["A", "B"] |
| `second_row` | object |  |  |  | a composite frame's second row |
| `second_row.tolerance` (required) | number | mm |  | > 0 | the row's tolerance (mm) |
| `second_row.diameter_zone` | boolean |  |  |  | a round zone (⌀) |
| `second_row.material` | `` \| `M` \| `L` |  |  |  | M maximum / L least material condition |
| `second_row.datums` | array of strings |  |  | at least 0 item(s), at most 3 item(s) | datum letters, e.g. ["A", "B"] |
| `letter` | string |  |  |  | the datum's letter |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without a drawing: `The design has no drawing yet: call create_drawing first.`
- Called without arguments, the arguments are refused before anything runs: `Not done: kind is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: datum A on the plate's bottom edge

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 60, 40], "name": "base"}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 10}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 10, "geometry": [{"circle": [30, 20, 4]}]}},
  {"tool": "hole", "args": {"sketch": "Sketch2", "diameter": 8, "through_all": true}},
  {"tool": "create_drawing", "args": {"base_view": "Front", "projected": ["Top", "Right"]}}
]
```

The call:

```json
{"tool": "add_drawing_symbol", "args": {"kind": "datum_identifier", "view": "BaseView", "pick": {"kind": "line", "near": [0, -5]}}}
```

The answer:

```text
Done: datum identifier 'Annotation' on Base View (line (-30, -5)-(30, -5)): A.
```

## More argument examples

- datum A on the bottom edge:
  `{"kind": "datum_identifier", "view": "BaseView", "pick": {"kind": "line", "near": [0, -5]}, "at": [120, 120]}`
- a flatness frame on its own:
  `{"kind": "feature_control_frame", "characteristic": "flatness", "tolerance": 0.05, "at": [80, 60]}`

## See also

- Recipe: [a fully dimensioned part drawing](fission180://docs/recipes/part-drawing.md)
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
