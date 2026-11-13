# `edit_title_block`: Edit title block

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: DRAWING > MODIFY > Title Block (or double-click the title block). Category: Drawings. Changes the design (one undo step). Its undo step is named like "AI: Title block". Needs a drawing.

## What it does

Type into the title block: values {field: text} with the fields Title, PartNumber, Description, Material, DrawnBy, Date, CheckedBy, ApprovedBy, Scale, Size, Sheet, Units, Revision. Fission 180 fills Title, PartNumber, Material, Scale, Size, Sheet and Units from the design until a field is typed: a typed field keeps its text on every sheet of the drawing. A sheet made with title_block false has none (refused).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `drawing` | string |  |  |  | the drawing or one of its sheets (default: the newest) |
| `values` (required) | object |  |  |  | {field: text}, e.g. {"Description": "Bracket"} |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without a drawing: `The design has no drawing yet: call create_drawing first.`
- Called without arguments, the arguments are refused before anything runs: `Not done: values is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: a description and a revision in the title block

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
{"tool": "edit_title_block", "args": {"values": {"Description": "Plate with a hole", "Revision": "A"}}}
```

The answer:

```text
Done: title block of Example Drawing: Description 'Plate with a hole', Revision 'A'.
```

## More argument examples

- describe the part and its revision:
  `{"values": {"Description": "Mounting bracket", "Revision": "B", "CheckedBy": "LS"}}`

## See also

- Recipe: [a fully dimensioned part drawing](fission180://docs/recipes/part-drawing.md)
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
