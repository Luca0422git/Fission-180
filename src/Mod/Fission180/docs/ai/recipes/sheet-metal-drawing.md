# Recipe: a sheet metal drawing with the flat pattern, a bend table and bend notes

Tags: drawing, sheet metal, flat pattern, bend table, bend note, bends, k-factor, csv, dxf

A tray bent from 1 mm sheet (a 50 x 30 base, four 10 mm walls) and the drawing a workshop cuts
and bends it from: the flat pattern seen from the top with its overall size, a bend table
(each bend's identifier, direction, angle, radius and K-factor), a note along every bend
line, the folded tray beside it, the bend table as CSV and the sheet as DXF. Every call was
run by Fission 180's tests; `expect` is what the answer must contain.

## 1. The tray and its flat pattern

The walls are edge flanges on the base's four top edges (SHEET METAL tools); the flat pattern
is unfolded from the base's bottom face. A drawing of the flat pattern needs it: before, the
drawing is refused and says which tool makes it.

```json fission180-calls
[
  {"tool": "new_design", "args": {"name": "Sheet tray"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 50, 30]}]}},
  {"tool": "flange", "args": {"kind": "base", "profile": "Sketch1"},
   "expect": {"contains": ["50 x 30 x 1 mm"]}},
  {"tool": "flange", "args": {"kind": "edge", "edges": {"type": "line",
    "at": {"axis": "z", "value": "max"}, "count": 4}, "height": 10},
   "expect": {"contains": ["50 x 30 x 11 mm"]}},
  {"tool": "create_drawing", "args": {"flat_pattern": "Flange1"},
   "expect": {"error": true, "contains": ["has no flat pattern"]}},
  {"tool": "flat_pattern", "args": {"face": {"normal": [0, 0, -1], "count": 1}},
   "expect": {"contains": ["flat 68.5239 x 48.5239 mm, 4 bends"]}},
  {"tool": "check_design", "args": {}, "expect": {"json": {"ok": true}}}
]
```

## 2. The flat pattern drawing

`create_drawing` with `flat_pattern` (the sheet metal body, or its flat pattern's id) draws the
flat pattern from the top; at 2:1 it leaves room for the bend table and the folded part (the
scale it picks by itself, 4:1, fills the A3 sheet). Its overall size goes on it: the flat runs from x = -34.26 to
34.26 and y = -24.26 to 24.26 in the view's own mm (`get_drawing` with `edges` lists them),
so the two outermost side edges give its length.

```json fission180-calls
[
  {"tool": "create_drawing", "args": {"flat_pattern": "Flange1", "scale": 2},
   "expect": {"contains": ["(id 'Drawing')", "scale 2:1", "views BaseView"]}},
  {"tool": "get_drawing", "args": {},
   "expect": {"json": {"drawings.0.views.0.orientation": "Top"},
     "contains": ["\"flat_pattern\": \"FlatPattern"]}},
  {"tool": "add_drawing_dimension", "args": {"view": "BaseView", "picks": [
    {"kind": "line", "near": [-34.26, 0]}, {"kind": "line", "near": [34.26, 0]}]},
   "expect": {"contains": ["DistanceX 'Dimension': 68.52"]}}
]
```

## 3. The bend table and the bend notes

The bend table numbers the bends B1, B2... (left to right) with an identifier on each bend
line; a bend note writes a bend's direction, angle and inside radius along its line (`bends`
1-based, as the table numbers them; none: every bend without a note).

```json fission180-calls
[
  {"tool": "add_drawing_annotation", "args": {"kind": "bend_table", "view": "BaseView"},
   "expect": {"contains": ["with 4 bends", "B1 DOWN 90° R1.00"]}},
  {"tool": "add_drawing_annotation", "args": {"kind": "bend_note", "view": "BaseView"},
   "expect": {"contains": ["4 bend notes", "B4 DOWN 90° R 1.00"]}},
  {"tool": "add_drawing_annotation", "args": {"kind": "bend_note", "view": "BaseView",
    "bends": [7]},
   "expect": {"error": true, "contains": ["bends 1 to 4"]}}
]
```

## 4. The folded part beside it

A base view of the sheet metal body (`bodies`) shows the tray folded. At 1:1 it fits the free
paper right of the flat pattern: give it that place with `at`.

```json fission180-calls
[
  {"tool": "add_drawing_view", "args": {"kind": "base", "bodies": ["Flange1"],
    "orientation": "Home", "scale": 1, "at": [345, 225]},
   "expect": {"contains": ["BaseView001"], "not_contains": ["overlaps"]}}
]
```

## 5. The files, the check

```json fission180-calls
[
  {"tool": "export_drawing", "args": {"format": "csv", "path": "{tmp}/bends.csv"},
   "expect": {"contains": ["Exported Bend Table", "4 rows"]}},
  {"tool": "export_drawing", "args": {"format": "dxf", "path": "{tmp}/tray.dxf"},
   "expect": {"contains": ["Exported Sheet tray Drawing"]}},
  {"tool": "get_drawing", "args": {"picture": true, "width": 840}, "expect": {"image": [840, 594]}},
  {"tool": "check_design", "args": {}, "expect": {"json": {"ok": true}}}
]
```

## Variations

- The flat pattern as a DXF for a laser or a punch (the outline and the bend lines, no
  sheet): `export_flat_pattern`, not a drawing.
- Another K-factor: change the sheet metal rule (`sheet_metal_rule`); the bend table and the
  flat's size follow.
- The bend table somewhere else: `modify_drawing` kind move with its id (get_drawing lists it).
