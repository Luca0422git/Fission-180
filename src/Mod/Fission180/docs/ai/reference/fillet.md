# `fillet`: Fillet

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: SOLID > MODIFY > Fillet. Category: Modify. Changes the design (one undo step). Its undo step is named like "AI: Fillet 5 mm". Needs a solid body.
It builds the design step(s) `blend_fillet`, `blend_insert` (the golden models' step language).

## What it does

Round edges of the current body with a radius (Fission 180's Fillet). Pick them with edges (an edge selector), faces (every sharp edge around the faces a face selector picks) and/or features (the edges earlier steps made, by step id). Errors such as 'the radius is too big for this edge' come back as sentences. For several radii, chord length, variable radius or tangent chain off use fillet_sets; Rule Fillet and Full Round Fillet are their own tools. With the timeline marker rolled back the fillet goes in at the marker and later fillets keep their edges. All lengths are in millimetres (mm) and all angles in degrees.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `edges` | object |  |  |  | The edges to round. A selector picks faces or edges by their geometry, never by names like "Edge7": type, normal [x, y, z], parallel [x, y, z], along [x, y, z], radius, on_faces / not_on_faces (a face selector), at {"axis": "x"\|"y"\|"z", "value": "max"\|"min"\|mm} (or a list), all, any_of [selectors], count (always give it: the tool refuses a different number). Example: the 4 top edges of a box {"type": "line", "at": {"axis": "z", "value": "max"}, "count": 4}. The full rules: the server's instructions (Selectors) or get_help topic selectors. |
| `faces` | object |  |  |  | Round every sharp edge around these faces. A selector picks faces or edges by their geometry, never by names like "Edge7": type, normal [x, y, z], parallel [x, y, z], along [x, y, z], radius, on_faces / not_on_faces (a face selector), at {"axis": "x"\|"y"\|"z", "value": "max"\|"min"\|mm} (or a list), all, any_of [selectors], count (always give it: the tool refuses a different number). Example: the 4 top edges of a box {"type": "line", "at": {"axis": "z", "value": "max"}, "count": 4}. The full rules: the server's instructions (Selectors) or get_help topic selectors. |
| `features` | array of strings |  |  | at least 1 item(s) | ids of earlier steps (from get_design's timeline) |
| `radius` (required) | number | mm |  | > 0 |  |

## Answer

On success: `Done: <undo title>. Its id is '<id>'. Bodies now: <each solid body's volume in mm3 and size in mm>.` (some steps report no id); then `These steps now fail: ...` when the change broke later steps, and `Warning: no solid changed ...` when it changed no solid at all. On failure nothing changes and the answer is `Not done (<undo title>): <the reason>`.

## Errors

- Without a solid body: `The design has no solid body yet: make one first (create_sketch + extrude, or primitive).`
- Called without arguments, the arguments are refused before anything runs: `Not done: radius is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When Fission 180 cannot build the step (a selector that picks another number of elements than `count`, a size that does not fit, an id that does not exist), the answer is `Not done (<undo title>): <reason>` and nothing changes; [troubleshooting](fission180://docs/troubleshooting.md) lists the usual causes.
- A size that does not fit (`radius`) is refused, never built smaller in its place: the reason ends with the largest value that fits, found by trying smaller ones (`Largest radius that fits here: 19.99 mm (30 mm does not; ... give radius 19.99 or less).`; `Furthest ... that fits here` for a value below 0). A value given as a formula is not searched. See [troubleshooting](fission180://docs/troubleshooting.md#a-size-that-does-not-fit).

## Example 1: round the four vertical corners

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
{"tool": "fillet", "args": {"edges": {"type": "line", "parallel": [0, 0, 1], "count": 4}, "radius": 5}}
```

The answer:

```text
Done: AI: Fillet 5 mm. Its id is 'Fillet1'. Bodies now: Body1: 23785.4 mm3, 60 x 40 x 10 mm.
```

## More argument examples

- round the 4 top edges of a box, 3 mm:
  `{"edges": {"type": "line", "at": {"axis": "z", "value": "max"}, "count": 4}, "radius": 3}`

## See also

- Recipe: [L bracket with mounting holes](fission180://docs/recipes/bracket.md)
- Recipe: [check a part before it is made (draft, inner rounds, reach, smoothness)](fission180://docs/recipes/check-before-making.md)
- Recipe: [enclosure with a lid](fission180://docs/recipes/enclosure-with-lid.md)
- Recipe: [flange with a bolt circle](fission180://docs/recipes/flange-bolt-pattern.md)
- Recipe: [a fully dimensioned part drawing](fission180://docs/recipes/part-drawing.md)
- Recipe: [rebuild a part that has no timeline (reverse engineering)](fission180://docs/recipes/reverse-engineer.md)
- Recipe: [revolved knob with grip grooves](fission180://docs/recipes/revolved-knob.md)
- Recipe: [stepped shaft with a keyway](fission180://docs/recipes/shaft-with-keyway.md)
- Recipe: [cantilever snap-fit hook](fission180://docs/recipes/snap-fit.md)
- Golden models built with its steps (read one with docs_read golden/<id>): `blend_edit_keeps_later_chamfer`, `blend_fillet_boss_feature`, `blend_fillet_edit_radius`, `blend_fillet_presspull_radius`, `blend_fillet_slot_chain`, `blend_fillet_top_face`, `blend_insert_chamfer_before_fillet`, `book_carabiner_full_round_4`, `export_report_design`, `live_blend_fillet_boss_feature`, `live_blend_fillet_slot_chain`, `live_spline_top_fillet` and 3 more
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
