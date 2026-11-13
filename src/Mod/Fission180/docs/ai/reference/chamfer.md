# `chamfer`: Chamfer

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: SOLID > MODIFY > Chamfer. Category: Modify. Changes the design (one undo step). Its undo step is named like "AI: Chamfer 1 mm". Needs a solid body.
It builds the design step(s) `blend_chamfer`, `blend_insert` (the golden models' step language).

## What it does

Bevel edges of the current body (Fission 180's Chamfer). distance alone: equal distances; distance and distance2: two distances (flip swaps the sides); distance and angle: a distance and an angle in degrees. Pick edges as for fillet. All lengths are in millimetres (mm) and all angles in degrees.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `edges` | object |  |  |  | The edges to bevel. A selector picks faces or edges by their geometry, never by names like "Edge7": type, normal [x, y, z], parallel [x, y, z], along [x, y, z], radius, on_faces / not_on_faces (a face selector), at {"axis": "x"\|"y"\|"z", "value": "max"\|"min"\|mm} (or a list), all, any_of [selectors], count (always give it: the tool refuses a different number). Example: the 4 top edges of a box {"type": "line", "at": {"axis": "z", "value": "max"}, "count": 4}. The full rules: the server's instructions (Selectors) or get_help topic selectors. |
| `faces` | object |  |  |  | Bevel every sharp edge around these faces. A selector picks faces or edges by their geometry, never by names like "Edge7": type, normal [x, y, z], parallel [x, y, z], along [x, y, z], radius, on_faces / not_on_faces (a face selector), at {"axis": "x"\|"y"\|"z", "value": "max"\|"min"\|mm} (or a list), all, any_of [selectors], count (always give it: the tool refuses a different number). Example: the 4 top edges of a box {"type": "line", "at": {"axis": "z", "value": "max"}, "count": 4}. The full rules: the server's instructions (Selectors) or get_help topic selectors. |
| `features` | array of strings |  |  | at least 1 item(s) | ids of earlier steps (from get_design's timeline) |
| `distance` (required) | number | mm |  | > 0 |  |
| `distance2` | number | mm |  | > 0 |  |
| `angle` | number | deg |  | > 0, <= 89 |  |
| `flip` | boolean |  | `false` |  |  |

## Answer

On success: `Done: <undo title>. Its id is '<id>'. Bodies now: <each solid body's volume in mm3 and size in mm>.` (some steps report no id); then `These steps now fail: ...` when the change broke later steps, and `Warning: no solid changed ...` when it changed no solid at all. On failure nothing changes and the answer is `Not done (<undo title>): <the reason>`.

## Errors

- Without a solid body: `The design has no solid body yet: make one first (create_sketch + extrude, or primitive).`
- Called without arguments, the arguments are refused before anything runs: `Not done: distance is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When Fission 180 cannot build the step (a selector that picks another number of elements than `count`, a size that does not fit, an id that does not exist), the answer is `Not done (<undo title>): <reason>` and nothing changes; [troubleshooting](fission180://docs/troubleshooting.md) lists the usual causes.
- A size that does not fit (`distance`, `distance2`) is refused, never built smaller in its place: the reason ends with the largest value that fits, found by trying smaller ones (`Largest radius that fits here: 19.99 mm (30 mm does not; ... give radius 19.99 or less).`; `Furthest ... that fits here` for a value below 0). A value given as a formula is not searched. See [troubleshooting](fission180://docs/troubleshooting.md#a-size-that-does-not-fit).

## Example 1: a 1 mm chamfer on the four top edges

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 60, 40], "name": "base"}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 10}}
]
```

The call:

```json
{"tool": "chamfer", "args": {"edges": {"type": "line", "at": {"axis": "z", "value": "max"}, "count": 4}, "distance": 1}}
```

The answer:

```text
Done: AI: Chamfer 1 mm. Its id is 'Chamfer1'. Bodies now: Body1: 23901.3 mm3, 60 x 40 x 10 mm.
```

## More argument examples

- 1 mm at 30 degrees:
  `{"edges": {"type": "line", "at": {"axis": "z", "value": "max"}, "count": 4}, "distance": 1, "angle": 30}`

## See also

- Recipe: [L bracket with mounting holes](fission180://docs/recipes/bracket.md)
- Recipe: [flange with a bolt circle](fission180://docs/recipes/flange-bolt-pattern.md)
- Recipe: [stepped shaft with a keyway](fission180://docs/recipes/shaft-with-keyway.md)
- Recipe: [threaded fastener (hex bolt M8 x 30)](fission180://docs/recipes/threaded-fastener.md)
- Golden models built with its steps (read one with docs_read golden/<id>): `blend_chamfer_angle`, `blend_chamfer_top_face`, `blend_chamfer_two_flip`, `blend_edit_keeps_later_chamfer`, `book_carabiner_full_round_4`, `book_chamfer_after_modeled_thread`, `book_tensegrity_corner_chamfer_20`, `book_thread_dragged_before_chamfer`, `book_thread_quarter_inch_before_chamfer`, `book_thread_stops_at_chamfer`, `book_thread_survives_deleted_chamfer`, `live_blend_chamfer_angle` and 5 more
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
