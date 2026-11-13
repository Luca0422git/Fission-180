# `edit_drawing_view`: Edit drawing view

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: DRAWING > MODIFY > Edit View (or double-click a view). Category: Drawings. Changes the design (one undo step). Its undo step is named like "AI: Edit BaseView". Needs a drawing.

## What it does

Change a view as its dialog does: orientation (a base view; its projected views turn with it), style, tangent_edges, scale (its projected views follow; the title block's Scale follows the first base view), label (its text) and show_label, center_marks {holes, extrudes, cuts: true | false} (automated centre marks and lines that follow the design), storyboard (a base view's Representation: a storyboard's name, or Model for the design as it is), a section's depth_mode Full | Slice | Distance with depth and hatch, a broken view's gap, a breakout's depth / through_all or remove_breakout. To move or turn a view: modify_drawing. One undo step.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `view` (required) | string |  |  |  | the view |
| `orientation` | `Front` \| `Back` \| `Top` \| `Bottom` \| `Left` \| `Right` \| `Home` |  |  |  |  |
| `style` | `Visible Edges` \| `Visible and Hidden Edges` \| `Shaded` \| `Shaded with Hidden Edges` |  |  |  |  |
| `tangent_edges` | `Full Length` \| `Off` |  |  |  |  |
| `scale` | number |  |  | > 0 | 0.5 for 1:2 |
| `label` | string |  |  |  | the view label's text |
| `show_label` | boolean |  |  |  | show the view label under the view |
| `center_marks` | object |  |  |  | automated centre marks and centre lines on these rounds |
| `center_marks.holes` | boolean |  |  |  |  |
| `center_marks.extrudes` | boolean |  |  |  | round extrudes |
| `center_marks.cuts` | boolean |  |  |  | round cuts |
| `storyboard` | string |  |  |  | a storyboard's name, or "Model" |
| `depth_mode` | `Full` \| `Slice` \| `Distance` |  |  |  | a section's depth |
| `depth` | number | mm |  | > 0 | section Distance / breakout depth (mm) |
| `through_all` | boolean |  |  |  | a breakout through everything |
| `hatch` | boolean |  |  |  | a section's hatching |
| `gap` | number | mm |  | > 0 | a broken view's gap (mm on the sheet) |
| `remove_breakout` | boolean |  |  |  | take the breakout away |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without a drawing: `The design has no drawing yet: call create_drawing first.`
- Called without arguments, the arguments are refused before anything runs: `Not done: view is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: the base view at 1:1 without hidden edges (its projected views follow)

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
{"tool": "edit_drawing_view", "args": {"view": "BaseView", "scale": 1, "style": "Visible Edges"}}
```

The answer:

```text
Done: BaseView 'Base View' (id 'BaseView') at [265, 216.5], 60 x 10 mm on the sheet, scale 1:1.
```

## More argument examples

- 1:2 with a centre mark on every hole:
  `{"view": "BaseView", "scale": 0.5, "center_marks": {"holes": true}}`

## See also

- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
