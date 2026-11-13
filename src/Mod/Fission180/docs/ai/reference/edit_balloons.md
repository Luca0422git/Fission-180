# `edit_balloons`: Edit balloons

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: DRAWING > TABLES > Renumber, Align Balloons. Category: Drawings. Changes the design (one undo step). Its undo step is named like "AI: Renumber balloons". Needs a drawing.

## What it does

kind renumber: the balloon (its id or the number it shows) gets item number to; the row that had it takes the old one, the parts list sorts and every balloon of both rows shows its new number. kind align: balloons (ids or numbers) line up through at [x, y] on the sheet: on one level line when they spread more sideways than up, else on one upright line. One undo step.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `kind` (required) | `renumber` \| `align` |  |  |  |  |
| `drawing` | string |  |  |  | the drawing or sheet (default: the newest) |
| `balloon` | string |  |  |  | renumber: the balloon's id or number |
| `to` | integer |  |  | >= 1 | renumber: the new item number |
| `balloons` | array of strings |  |  |  | align: the balloons' ids or numbers |
| `at` | array of 2 numbers | mm |  |  | align: where their line goes [x, y] on the sheet (mm from its bottom left corner) |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without a drawing: `The design has no drawing yet: call create_drawing first.`
- Called without arguments, the arguments are refused before anything runs: `Not done: kind is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: the wheel becomes item 1 (the base takes 2)

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "new_component", "args": {"label": "Base"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [-30, -30, 30, 30]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 10}},
  {"tool": "new_component", "args": {"label": "Wheel"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 20, "geometry": [{"circle": [0, 0, 15]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch2", "distance": 5}},
  {"tool": "create_drawing", "args": {"base_view": "Front"}},
  {"tool": "add_drawing_annotation", "args": {"kind": "parts_list", "view": "BaseView"}}
]
```

The call:

```json
{"tool": "edit_balloons", "args": {"kind": "renumber", "balloon": "2", "to": 1}}
```

The answer:

```text
Done: item 2 is now 1. Parts list: 1 Wheel, 2 Base.
```

## More argument examples

- balloon 2 becomes item 1:
  `{"kind": "renumber", "balloon": "2", "to": 1}`
- the balloons on one line:
  `{"kind": "align", "balloons": ["1", "2", "3"], "at": [60, 250]}`

## See also

- Recipe: [an assembly drawing with an exploded view, balloons and a parts list](fission180://docs/recipes/assembly-drawing.md)
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
