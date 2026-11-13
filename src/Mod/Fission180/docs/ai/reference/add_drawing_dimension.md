# `add_drawing_dimension`: Add drawing dimension

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: DRAWING > DIMENSIONS > Dimension, Linear, Aligned, Angular, Radius, Diameter, Arc Length, Ordinate, Baseline, Chain. Category: Drawings. Changes the design (one undo step). Its undo step is named like "AI: Drawing dimension". Needs a drawing.

## What it does

Dimension a drawing view. Without type, as Fusion's Dimension command infers it from picks: one line (its length), one circle (diameter) or arc (radius), two lines / points (distance or angle). type forces linear, aligned, radius, diameter, angular, or: arc_length (picks: one arc); ordinate (origin: the 0 point, picks: the points, axis x | y | both, at: [x, y] sheet mm the values' lines go through); baseline / chain (from: a horizontal or vertical dimension's id, picks: more points; baseline measures each from that dimension's start, stacked 8 mm apart, chain each from the one before). A pick is {kind: line | circle | arc | vertex, near: [x, y] in the view's own mm (get_drawing edges), radius}; a circle given as a point is its centre. at: the text on the sheet. Isometric views cannot be dimensioned. Answers each value.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `view` | string |  |  |  | the view |
| `picks` (required) | array of objects |  |  | at least 1 item(s), at most 40 item(s) | the elements (one or two; more for ordinate, baseline, chain) |
| `type` | `linear` \| `aligned` \| `radius` \| `diameter` \| `angular` \| `arc_length` \| `ordinate` \| `baseline` \| `chain` |  |  |  |  |
| `origin` | object |  |  |  | ordinate: the point the values count from |
| `origin.kind` | `line` \| `circle` \| `arc` \| `vertex` |  |  |  |  |
| `origin.near` | array of 2 numbers | mm |  |  | [x, y] in the view's own mm: model size (not scaled) from the view's centre, x right, y up, as get_drawing with edges true lists its elements |
| `origin.radius` | number | mm |  | > 0 | circles / arcs: the radius (model mm) |
| `axis` | `x` \| `y` \| `both` |  | `"both"` |  | ordinate: which values |
| `from` | string |  |  |  | baseline / chain: the dimension to go on from |
| `at` | array of 2 numbers | mm |  |  | text position (ordinate: the values' lines) [x, y] on the sheet (mm from its bottom left corner) |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without a drawing: `The design has no drawing yet: call create_drawing first.`
- Called without arguments, the arguments are refused before anything runs: `Not done: picks is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: the length of the line nearest to (0, 5) in the base view

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
{"tool": "add_drawing_dimension", "args": {"view": "BaseView", "picks": [{"kind": "line", "near": [0, 5]}]}}
```

The answer:

```text
Done: dimension on Base View: DistanceX 'Dimension': 60 (written '60'); it measures line (-30, 5)-(30, 5).
```

## More argument examples

- the diameter of the 6 mm hole:
  `{"view": "BaseView", "picks": [{"kind": "circle", "radius": 3}]}`
- the hole's x from the bottom left corner:
  `{"view": "BaseView", "type": "ordinate", "origin": {"kind": "vertex", "near": [-30, -20]}, "picks": [{"kind": "circle", "near": [0, 0]}], "axis": "x"}`

## See also

- Recipe: [a fully dimensioned part drawing](fission180://docs/recipes/part-drawing.md)
- Recipe: [a sheet metal drawing with the flat pattern, a bend table and bend notes](fission180://docs/recipes/sheet-metal-drawing.md)
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
