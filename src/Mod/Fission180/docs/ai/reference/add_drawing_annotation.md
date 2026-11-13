# `add_drawing_annotation`: Add drawing annotation

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: DRAWING > TEXT (Text, Leader, Bend Note) and TABLES (Table / Parts List, Bend Table, Balloon), GEOMETRY > Center Mark on every circle. Category: Drawings. Changes the design (one undo step). Its undo step is named like "AI: Drawing text". Needs a drawing.

## What it does

Add to a drawing: kind text (text lines at [x, y], size mm), leader (view, pick: the edge its arrow goes on, at: where the text goes, text), bend_note (a flat pattern view: direction, angle and radius along bends, numbers 1.. as the bend table, default all), parts_list (a table of the view's components with balloons, at = its top-left corner; balloons false: none), bend_table (a flat pattern view: its bends, with identifiers on the view), balloon (view, component: a parts-list part number or body id; its arrow on an edge of that part, at: the balloon) or center_marks (a centre mark on every circle of a view that has none). Answers the ids.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `drawing` | string |  |  |  | the drawing or sheet (default: the view's, or the newest) |
| `kind` (required) | `text` \| `leader` \| `bend_note` \| `parts_list` \| `bend_table` \| `balloon` \| `center_marks` |  |  |  |  |
| `text` | string |  |  |  | text (new lines split it) |
| `size` | number | mm | `3.5` | > 0 | text height (mm) |
| `view` | string |  |  |  | the view it belongs to |
| `pick` | object |  |  |  | leader: the edge the arrow goes on |
| `pick.kind` | `line` \| `circle` \| `arc` \| `vertex` |  |  |  |  |
| `pick.near` | array of 2 numbers | mm |  |  | [x, y] in the view's own mm: model size (not scaled) from the view's centre, x right, y up, as get_drawing with edges true lists its elements |
| `pick.radius` | number | mm |  | > 0 | circles / arcs: the radius (model mm) |
| `component` | string |  |  |  | balloon: a parts-list part number (component name) or body id |
| `bends` | array of integers |  |  |  | bend_note: bend numbers (B1 = 1) |
| `at` | array of 2 numbers | mm |  |  | [x, y] on the sheet (mm from its bottom left corner) |
| `balloons` | boolean |  | `true` |  | parts list: balloons on the view |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without a drawing: `The design has no drawing yet: call create_drawing first.`
- Called without arguments, the arguments are refused before anything runs: `Not done: kind is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: a note on the sheet

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
{"tool": "add_drawing_annotation", "args": {"kind": "text", "text": "Break all sharp edges", "at": [20, 40]}}
```

The answer:

```text
Done: text 'Text' on Example Drawing at [20, 40].
```

## More argument examples

- a note on the sheet:
  `{"kind": "text", "text": "Break all sharp edges", "at": [20, 40]}`
- a leader note on an edge:
  `{"kind": "leader", "view": "BaseView", "pick": {"kind": "line", "near": [0, 5]}, "at": [60, 60], "text": "Polished"}`

## See also

- Recipe: [an assembly drawing with an exploded view, balloons and a parts list](fission180://docs/recipes/assembly-drawing.md)
- Recipe: [a sheet metal drawing with the flat pattern, a bend table and bend notes](fission180://docs/recipes/sheet-metal-drawing.md)
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
