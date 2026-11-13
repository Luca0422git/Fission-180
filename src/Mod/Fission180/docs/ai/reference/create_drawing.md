# `create_drawing`: Create drawing

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: File > New Drawing > From Design / From Animation. Category: Drawings. Changes the design (one undo step). Its undo step is named like "AI: New drawing". Needs a solid body.

## What it does

Make a 2D drawing of the design, kept in the design and updated with it. What it shows: bodies (step ids; default every visible body), contents full_assembly (every body, also ones made later), flat_pattern (a sheet metal body or its flat pattern: drawn from the top, for bend_table / bend_note) or storyboard (From Animation: the views show that storyboard's end, exploded). standard ISO | ASME, sheet (A4..A0 ISO, A..E ASME), units mm | in, title_block. automatic true: base Front, Top, Right and an isometric laid out at the largest standard scale that fits. Else a base view (base_view orientation, at [x, y] sheet mm, scale, style) and projected views (Top, Right, FrontTopRight...). Answers the ids and the scale. Slow on big designs: TechDraw works out each view's hidden lines, about 15 s a view of a 1,000-face assembly (draw only the bodies needed).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `bodies` | array of strings |  |  | at least 1 item(s) | the bodies to draw (default: every visible body) |
| `contents` | `full_assembly` \| `visible_only` |  |  |  | full_assembly: every body, and ones made later come in (instead of bodies) |
| `flat_pattern` | string |  |  |  | a sheet metal body (or its flat pattern) to draw flat |
| `storyboard` | string |  |  |  | an animation storyboard: every view shows its end, exploded |
| `standard` | `ISO` \| `ASME` |  | `"ISO"` |  |  |
| `sheet` | string |  |  |  | A4, A3, A2, A1, A0 (ISO) or A, B, C, D, E (ASME) |
| `units` | `mm` \| `in` |  | `"mm"` |  |  |
| `title_block` | boolean |  | `true` |  |  |
| `label` | string |  |  |  | the drawing's name |
| `automatic` | boolean |  |  |  | base, two projected and an isometric view, laid out to fit |
| `base_view` | `Front` \| `Back` \| `Top` \| `Bottom` \| `Left` \| `Right` \| `Home` |  | `"Front"` |  | the base view's orientation |
| `at` | array of 2 numbers | mm |  |  | [x, y] on the sheet (mm from its bottom left corner) of the base view |
| `scale` | number |  |  | > 0 | view scale, 0.5 for 1:2 (default: fits the sheet) |
| `style` | `Visible Edges` \| `Visible and Hidden Edges` \| `Shaded` \| `Shaded with Hidden Edges` |  | `"Visible and Hidden Edges"` |  |  |
| `projected` | array of strings |  |  |  | projected views to add |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without a solid body: `The design has no solid body yet: make one first (create_sketch + extrude, or primitive).`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: three views and an isometric

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 60, 40], "name": "base"}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 10}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 10, "geometry": [{"circle": [30, 20, 4]}]}},
  {"tool": "hole", "args": {"sketch": "Sketch2", "diameter": 8, "through_all": true}}
]
```

The call:

```json
{"tool": "create_drawing", "args": {"base_view": "Front", "projected": ["Top", "Right", "FrontTopRight"]}}
```

The answer:

```text
Done: drawing 'Example Drawing' (id 'Drawing') on a ISO A3 sheet, scale 2:1; views BaseView (Base View), ProjectedView (Top View), ProjectedView001 (Right View), ProjectedView002 (Isometric (top right) View).
```

## More argument examples

- the classic three views plus an isometric:
  `{"base_view": "Front", "projected": ["Top", "Right", "FrontTopRight"]}`
- Fusion's automatic views on an A3 sheet:
  `{"automatic": true, "sheet": "A3"}`

## See also

- Recipe: [an assembly drawing with an exploded view, balloons and a parts list](fission180://docs/recipes/assembly-drawing.md)
- Recipe: [a fully dimensioned part drawing](fission180://docs/recipes/part-drawing.md)
- Recipe: [a sheet metal drawing with the flat pattern, a bend table and bend notes](fission180://docs/recipes/sheet-metal-drawing.md)
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
