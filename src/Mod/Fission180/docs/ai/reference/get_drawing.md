# `get_drawing`: Get drawing

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: BROWSER > Drawings (and what the sheets show). Category: Drawings. Read-only. Needs a drawing.

## What it does

Describe drawings so you can check your work without a picture: each drawing's sheets (size, standard, units, title block) and on each: views (id, kind, orientation, scale, place and size on the sheet, label, style, what they show: bodies, flat pattern, storyboard; section line and depth, break, breakout, rotation), dimensions (type, value, the text written, what they measure), annotations (leaders, symbols, ordinates: kind and text), balloons (number, component), tables (rows), centre marks, centre lines. edges true: each view's lines, circles and points (view's own mm) for picks; with view, that view's only (a big assembly's edges run to 500 kB). picture true: a PNG of one sheet (frame, title block, views, dimensions, text) drawn from its DXF (about 15 s for an A2 sheet of a 1,000-face assembly).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `drawing` | string |  |  |  | one drawing or sheet (default: all) |
| `edges` | boolean |  | `false` |  | list each view's lines and circles |
| `view` | string |  |  |  | edges: only this view's (and its drawing) |
| `picture` | boolean |  |  |  | a PNG of the sheet (the drawing's first, or the given sheet) |
| `width` | integer |  | `1200` | >= 200, <= 4000 | picture width in pixels |

## Answer

A plain sentence, then JSON with: `drawings`. The example below shows a real one.

## Errors

- Without a drawing: `The design has no drawing yet: call create_drawing first.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: the sheet and its views

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
{"tool": "get_drawing", "args": {}}
```

The answer:

```text
{
 "drawings": [
  {
   "id": "Drawing",
   "label": "Example Drawing",
   "sheet_name": "Sheet 1",
   "standard": "ISO",
   "sheet": "A3",
   "units": "mm",
   "sheet_size_mm": [420.0, 297.0],
   "title_block": {
    "ApprovedBy": "",
    "CheckedBy": "",
    "Date": "2026-11-13",
    "Description": "",
    "DrawnBy": "root",
    "Material": "Steel",
    "PartNumber": "Example",
    "Revision": "",
    "Scale": "2:1",
    "Sheet": "1 / 1",
    "Size": "A3",
    "Title": "Example",
    "Units": "mm"
   },
   "views": [
    {
     "id": "BaseView",
     "label": "Base View",
     "kind": "BaseView",
     "orientation": "Front",
     "scale": 2.0,
     "scale_text": "2:1",
     "at": [265.0, 216.5],
     "half_size_mm": [60.0, 10.0],
     "style": "Visible and Hidden Edges",
     "shows": ["Body"]
    },
    {
     "id": "ProjectedView",
     "label": "Top View",
     "kind": "ProjectedView",
     "orientation": "Front",
     "scale": 2.0,
     "scale_text": "2:1",
     "at": [265.0, 146.5],
     "half_size_mm": [60.0, 40.0],
     "style": "Visible and Hidden Edges",
     "parent": "BaseView",
     "direction": "Top",
     "shows": ["Body"]
    },
    {
     "id": "ProjectedView001",
     "label": "Right View",
     "kind": "ProjectedView",
     "orientation": "Front",
     "scale": 2.0,
     "scale_text": "2:1",
     "at": [145.0, 216.5],
     "half_size_mm": [40.0, 10.0],
     "style": "Visible and Hidden Edges",
     "parent": "BaseView",
     "direction": "Right",
     "shows": ["Body"]
    }
   ],
   "annotations": [],
   "sheets": [{"id": "Drawing", "name": "Sheet 1"}]
  }
... (2 more lines)
```

## More argument examples

- views and their lines and circles:
  `{"edges": true}`
- a picture of the sheet:
  `{"picture": true, "width": 800}`

## See also

- Recipe: [an assembly drawing with an exploded view, balloons and a parts list](fission180://docs/recipes/assembly-drawing.md)
- Recipe: [a fully dimensioned part drawing](fission180://docs/recipes/part-drawing.md)
- Recipe: [a sheet metal drawing with the flat pattern, a bend table and bend notes](fission180://docs/recipes/sheet-metal-drawing.md)
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
