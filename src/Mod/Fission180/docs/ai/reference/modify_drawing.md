# `modify_drawing`: Move, rotate or delete on a drawing

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: DRAWING > MODIFY > Move / Rotate / Delete (and Delete of a drawing in the browser). Category: Drawings. Changes the design (one undo step), destructive. Its undo step is named like "AI: Drawing move". Needs a drawing.

## What it does

kind move: items (views, the parts list or bend table, text notes, balloons, symbols and dimensions' text) by [dx, dy] mm on the sheet, or one item to [x, y]; a view takes its dimensions, marks and balloons along, a projected view slides along its line from its parent. kind rotate: views by angle degrees, counter-clockwise about their middle. kind delete: the items (a view takes its dimensions, balloons, sections, details and projected views with it; a broken view brings back the view it stood in for; a drawing's id deletes the whole drawing, every sheet). Ids from get_drawing. One undo step.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `kind` (required) | `move` \| `rotate` \| `delete` |  |  |  |  |
| `items` (required) | array of strings |  |  | at least 1 item(s) | ids of what to change (get_drawing lists them) |
| `by` | array of 2 numbers | mm |  |  | move: [dx, dy] mm on the sheet |
| `to` | array of 2 numbers | mm |  |  | move: [x, y] on the sheet (mm from its bottom left corner) (one item) |
| `angle` | number | deg |  |  | rotate: degrees, counter-clockwise |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without a drawing: `The design has no drawing yet: call create_drawing first.`
- Called without arguments, the arguments are refused before anything runs: `Not done: kind is missing; items is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: the base view 10 mm left and 5 mm up; its projected views stay lined up

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
{"tool": "modify_drawing", "args": {"kind": "move", "items": ["BaseView"], "by": [-10, 5]}}
```

The answer:

```text
Done: BaseView at [255, 221.5], turned 0°.
```

## More argument examples

- a view 20 mm left:
  `{"kind": "move", "items": ["BaseView"], "by": [-20, 0]}`
- a view turned:
  `{"kind": "rotate", "items": ["ProjectedView"], "angle": 90}`

## See also

- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
