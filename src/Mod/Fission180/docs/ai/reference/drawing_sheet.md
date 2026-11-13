# `drawing_sheet`: Drawing sheet

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: DRAWING > the Sheet Bar (+, right-click a sheet: New Sheet, Rename, Delete, Move). Category: Drawings. Changes the design (one undo step). Its undo step is named like "AI: Add sheet". Needs a drawing.

## What it does

A drawing's sheets: action add (a new empty sheet with the same size, standard and title block: at the end, or at index; it numbers its title block 2 / 2...), rename (name), move (to index, 0 = first) or delete (the sheet and everything on it; the last sheet of a drawing stays: delete the drawing with modify_drawing). Each sheet has its own id: give it as drawing to add_drawing_view and the other tools to work on it. Answers the sheets in order.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `action` (required) | `add` \| `rename` \| `move` \| `delete` |  |  |  |  |
| `drawing` | string |  |  |  | the drawing (add) or the sheet (rename, move, delete) |
| `name` | string |  |  |  | rename: the sheet's new name |
| `index` | integer |  |  | >= 0 | add / move: its place, 0 = first |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without a drawing: `The design has no drawing yet: call create_drawing first.`
- Called without arguments, the arguments are refused before anything runs: `Not done: action is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: a second sheet

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
{"tool": "drawing_sheet", "args": {"action": "add"}}
```

The answer:

```text
Done: sheet 'Sheet 2' (id 'Drawing001') added. Sheets: 1. Sheet 1 (id 'Drawing'); 2. Sheet 2 (id 'Drawing001').
```

## More argument examples

- a second sheet for the details:
  `{"action": "add"}`

## See also

- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
