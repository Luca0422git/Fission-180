# `add_drawing_geometry`: Add drawing geometry

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: DRAWING > GEOMETRY > Center Mark, Centerline, Center Mark Pattern, Edge Extension. Category: Drawings. Changes the design (one undo step). Its undo step is named like "AI: Drawing center mark". Needs a drawing.

## What it does

Construction lines on a view, as GEOMETRY's commands make them: center_mark (picks: circles / arcs; none: every circle without a mark), centerline (two parallel straight edges: a dash-dot line midway), center_mark_pattern (2+ holes of one pattern: a mark on each and the line or bolt circle through their centres) or edge_extension (two straight edges: thin lines to where they would meet, a point there that takes dimensions: a rounded corner's sharp corner). A pick is {kind: line | circle | arc, near: [x, y] in the view's own mm (get_drawing edges), radius}. They follow the design.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `kind` (required) | `center_mark` \| `centerline` \| `center_mark_pattern` \| `edge_extension` |  |  |  |  |
| `view` (required) | string |  |  |  | the view |
| `picks` | array of objects |  |  | at least 1 item(s), at most 60 item(s) | the edges or circles |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without a drawing: `The design has no drawing yet: call create_drawing first.`
- Called without arguments, the arguments are refused before anything runs: `Not done: kind is missing; view is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: a centre mark on the hole, seen from above

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
{"tool": "add_drawing_geometry", "args": {"kind": "center_mark", "view": "ProjectedView", "picks": [{"kind": "circle", "radius": 4}]}}
```

The answer:

```text
Done: 1 centre marks on Top View: circle R4 at (0, 0).
```

## More argument examples

- a centre line between the two sides:
  `{"kind": "centerline", "view": "BaseView", "picks": [{"kind": "line", "near": [-30, 0]}, {"kind": "line", "near": [30, 0]}]}`

## See also

- Recipe: [a fully dimensioned part drawing](fission180://docs/recipes/part-drawing.md)
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
