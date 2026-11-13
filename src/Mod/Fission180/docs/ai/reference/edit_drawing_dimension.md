# `edit_drawing_dimension`: Edit drawing dimension

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: DRAWING > DIMENSIONS > Edit Dimension (or double-click a dimension). Category: Drawings. Changes the design (one undo step). Its undo step is named like "AI: Edit dimension". Needs a drawing.

## What it does

Change dimensions' text as the Dimension dialog does: override (text instead of the value; "" gives the value back), prefix / suffix ("4x ", " THRU"), precision, tolerance none | symmetric | deviation | limits | fit with upper / lower (mm) or fit (ISO 286 "H7/g6", or one class "H7"), fit_member hole | shaft, fit_display class | class_and_tolerances | limits | fit, tol_precision, basic (boxed), reference (in parentheses); at moves one dimension's text to [x, y] on the sheet. dimensions: ids (get_drawing). A wrong entry (upper under lower, an unknown class, a fit over 500 mm) is refused with the reason. Answers the text each now shows.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `dimensions` (required) | array of strings |  |  | at least 1 item(s) | the dimensions |
| `override` | string |  |  |  | text shown instead of the value |
| `prefix` | string |  |  |  | text before the value |
| `suffix` | string |  |  |  | text after the value |
| `precision` | `Default` \| `0` \| `0.1` \| `0.12` \| `0.123` \| `0.1234` |  |  |  |  |
| `tolerance` | `none` \| `symmetric` \| `deviation` \| `limits` \| `fit` |  |  |  |  |
| `upper` | number | mm or deg |  |  | upper tolerance (mm, or degrees on an angle) |
| `lower` | number |  |  |  | lower tolerance |
| `fit` | string |  |  |  | an ISO 286 fit "H7/g6" or one class "H7" / "g6" |
| `fit_member` | `hole` \| `shaft` |  |  |  | this dimension is the hole or the shaft |
| `fit_display` | `class` \| `class_and_tolerances` \| `limits` \| `fit` |  |  |  |  |
| `tol_precision` | `Default` \| `0` \| `0.1` \| `0.12` \| `0.123` \| `0.1234` |  |  |  | the tolerance's decimals |
| `basic` | boolean |  |  |  | a basic (theoretically exact) dimension: boxed |
| `reference` | boolean |  |  |  | a reference dimension: in parentheses |
| `at` | array of 2 numbers | mm |  |  | the text's place [x, y] on the sheet (mm from its bottom left corner) |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without a drawing: `The design has no drawing yet: call create_drawing first.`
- Called without arguments, the arguments are refused before anything runs: `Not done: dimensions is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: the hole's diameter with its ISO fit class

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 60, 40], "name": "base"}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 10}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 10, "geometry": [{"circle": [30, 20, 4]}]}},
  {"tool": "hole", "args": {"sketch": "Sketch2", "diameter": 8, "through_all": true}},
  {"tool": "create_drawing", "args": {"base_view": "Front", "projected": ["Top", "Right"]}},
  {"tool": "add_drawing_dimension", "args": {"view": "ProjectedView", "picks": [{"kind": "circle", "radius": 4}]}}
]
```

The call:

```json
{"tool": "edit_drawing_dimension", "args": {"dimensions": ["Dimension"], "tolerance": "fit", "fit": "H7"}}
```

The answer:

```text
Done: Diameter 'Dimension': 8 (written '⌀8 H7').
```

## More argument examples

- a fit on the hole's diameter:
  `{"dimensions": ["Dimension"], "tolerance": "fit", "fit": "H7/g6"}`
- ± 0.1:
  `{"dimensions": ["Dimension001"], "tolerance": "symmetric", "upper": 0.1}`

## See also

- Recipe: [a fully dimensioned part drawing](fission180://docs/recipes/part-drawing.md)
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
