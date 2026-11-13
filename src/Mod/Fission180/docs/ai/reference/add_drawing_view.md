# `add_drawing_view`: Add drawing view

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: DRAWING > CREATE > Base / Projected / Section / Detail / Break / Breakout Section / Exploded View. Category: Drawings. Changes the design (one undo step). Its undo step is named like "AI: Projected view". Needs a drawing.

## What it does

Add a view. kind base (orientation, scale, style; bodies or flat_pattern, default what the drawing shows), projected (parent, direction Top, Right... FrontTopRight), section (parent, line: 2 points cut straight, more bend the cut (half, offset, aligned), side 1 | -1, depth_mode Full | Slice | Distance + depth), detail (parent, center, radius; scale default 2x the parent's), break (parent, start, end: the part between goes, across the longer way of the two points; gap mm), breakout (parent, boundary: 3+ points round what to open, depth mm from the front, default half way, or through_all) or exploded (a base view of a storyboard's end, default the front one). Points on a view are in its own mm (model size from its centre, y up: get_drawing edges). at: where on the sheet [x, y] mm (default: free paper, beside its parent). About 15 s a view of a 1,000-face assembly (an exploded one: 50 s).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `drawing` | string |  |  |  | the drawing or sheet (default: the newest drawing) |
| `kind` (required) | `base` \| `projected` \| `section` \| `detail` \| `break` \| `breakout` \| `exploded` |  |  |  |  |
| `parent` | string |  |  |  | the view it is made from |
| `orientation` | `Front` \| `Back` \| `Top` \| `Bottom` \| `Left` \| `Right` \| `Home` |  |  |  |  |
| `direction` | `Top` \| `Bottom` \| `Left` \| `Right` \| `FrontTopRight` \| `FrontTopLeft` \| `FrontBottomRight` \| `FrontBottomLeft` |  |  |  |  |
| `line` | array of arrays |  |  | at least 2 item(s), at most 12 item(s) | section line [[x1, y1], [x2, y2], ...] |
| `side` | integer |  |  |  | section: 1 looks from the left of the line's direction, -1 from the right (default: from where the view is placed) |
| `center` | array of 2 numbers | mm |  |  | detail centre [x, y] |
| `radius` | number | mm |  | > 0 | detail circle radius (mm) |
| `start` | array of 2 numbers |  |  |  | break: one end of the part left out [x, y] |
| `end` | array of 2 numbers |  |  |  | break: the other end [x, y] |
| `gap` | number | mm | `10` | > 0 | break: the gap between the two ends on the sheet (mm) |
| `boundary` | array of arrays |  |  | at least 3 item(s), at most 64 item(s) | breakout: the boundary's corners [[x, y], ...] |
| `depth` | number | mm |  | > 0 | breakout: how deep from the front (mm); section: Distance (mm) |
| `depth_mode` | `Full` \| `Slice` \| `Distance` |  | `"Full"` |  | section depth |
| `through_all` | boolean |  |  |  | breakout: cut through everything |
| `storyboard` | string |  |  |  | exploded: the storyboard (default: the front one) |
| `bodies` | array of strings |  |  | at least 1 item(s) | base: the bodies it shows (default: the drawing's) |
| `flat_pattern` | string |  |  |  | base: a sheet metal body or flat pattern drawn flat |
| `at` | array of 2 numbers | mm |  |  | [x, y] on the sheet (mm from its bottom left corner) |
| `scale` | number |  |  | > 0 | 0.5 for 1:2 |
| `style` | `Visible Edges` \| `Visible and Hidden Edges` \| `Shaded` \| `Shaded with Hidden Edges` |  |  |  |  |
| `label` | string |  |  |  | section / detail letter |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without a drawing: `The design has no drawing yet: call create_drawing first.`
- Called without arguments, the arguments are refused before anything runs: `Not done: kind is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: an isometric view projected from the base view

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
{"tool": "add_drawing_view", "args": {"kind": "projected", "parent": "BaseView", "direction": "FrontTopRight"}}
```

The answer:

```text
Done: projected view: ProjectedView 'Isometric (top right) View' (id 'ProjectedView002') at [114.29, 137.51], 141.4 x 98 mm on the sheet, scale 2:1 on Example Drawing.
```

## More argument examples

- a section through the middle of the base view:
  `{"kind": "section", "parent": "BaseView", "line": [[-50, 0], [50, 0]]}`
- leave out the middle 40 mm of a long part:
  `{"kind": "break", "parent": "BaseView", "start": [-20, 0], "end": [20, 0], "gap": 8}`
- open up a corner half way through:
  `{"kind": "breakout", "parent": "BaseView", "boundary": [[-5, -5], [5, -5], [5, 5]]}`

## See also

- Recipe: [an assembly drawing with an exploded view, balloons and a parts list](fission180://docs/recipes/assembly-drawing.md)
- Recipe: [a fully dimensioned part drawing](fission180://docs/recipes/part-drawing.md)
- Recipe: [a sheet metal drawing with the flat pattern, a bend table and bend notes](fission180://docs/recipes/sheet-metal-drawing.md)
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
