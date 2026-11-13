# Recipe: a fully dimensioned part drawing

Tags: drawing, dimensions, ordinate, baseline, tolerance, fit, centre marks, section, detail, title block, gd&t, datum, dxf, picture

A drawing of a plate 80 x 40 x 10 with two 10 mm holes 40 apart and its two right-hand corners
rounded R6: three views, every size a machinist needs (overall size, hole size and places,
corner radius), a fit on the holes, a datum and a position tolerance, centre marks, a section
and a detail, the title block filled in, checked with `get_drawing` and exported. Every call
was run by Fission 180's tests; `expect` is what the answer must contain.

How to work on a drawing without seeing it: everything on a view is picked by where it is in
**the view's own mm** (model size, not scaled, from the view's centre, x right, y up), the
numbers `get_drawing` with `edges: true` lists; places on the sheet are **[x, y] mm from the
sheet's bottom left corner**. Leave out `at` and Fission 180 puts the thing where a person
would (a dimension's text just outside the view, a view on free paper) and says when
something overlaps. Check every step with the numbers the answers give, then once with
`get_drawing` (and its `picture`).

## 1. The part

The sketch on XY makes the plate with its holes at (20, 20) and (60, 20); the fillet rounds
the two vertical edges at x = 80.

```json fission180-calls
[
  {"tool": "new_design", "args": {"name": "Drawn plate"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [
    {"rect": [0, 0, 80, 40]}, {"circle": [20, 20, 5]}, {"circle": [60, 20, 5]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 10},
   "expect": {"contains": ["80 x 40 x 10 mm"]}},
  {"tool": "fillet", "args": {"edges": {"type": "line", "parallel": [0, 0, 1],
    "at": {"axis": "x", "value": "max"}, "count": 2}, "radius": 6},
   "expect": {"contains": ["Fillet1"]}},
  {"tool": "check_design", "args": {}, "expect": {"json": {"ok": true}}}
]
```

## 2. The drawing and its views

[create_drawing](fission180://docs/reference/create_drawing.md) makes the drawing (ISO, A3,
first angle projection: the view from below goes above the top view, the right view to its
left) and lays the views out side by side at the largest standard scale that fits: 2:1 here.
The top view is the one that shows the holes and the rounded corners, so it is the base view.
`get_drawing` with `edges` lists each view's elements; in the base view the plate runs from
(-40, -20) to (40, 20), the holes are circles R5 at (-20, 0) and (20, 0), the rounded
corners arcs R6 at (34, ±14). Hidden edges are listed too, marked `"hidden": true`.

```json fission180-calls
[
  {"tool": "create_drawing", "args": {"base_view": "Top", "projected": ["Bottom", "Right"]},
   "expect": {"contains": ["(id 'Drawing')", "scale 2:1", "BaseView (Base View)"]}},
  {"tool": "get_drawing", "args": {"edges": true},
   "expect": {"json": {"drawings.0.views.0.id": "BaseView",
     "drawings.0.views.0.orientation": "Top", "drawings.0.views.0.half_size_mm": [80.0, 40.0],
     "drawings.0.views.#": 3}}}
]
```

## 3. The sizes

Dimension what a machinist needs, each once: the overall length between the two side edges
(two parallel lines: their distance), the height between the long edges, the hole diameter,
the corner radius. [add_drawing_dimension](fission180://docs/reference/add_drawing_dimension.md)
works out the kind from what is picked, like Fusion's Dimension command; `type` forces one.
Every answer gives the measured value: check it against the model.

```json fission180-calls
[
  {"tool": "add_drawing_dimension", "args": {"view": "BaseView", "picks": [
    {"kind": "line", "near": [-40, 0]}, {"kind": "line", "near": [40, 0]}]},
   "expect": {"contains": ["DistanceX 'Dimension': 80"]}},
  {"tool": "add_drawing_dimension", "args": {"view": "BaseView", "picks": [
    {"kind": "line", "near": [0, -20]}, {"kind": "line", "near": [0, 20]}]},
   "expect": {"contains": ["DistanceY 'Dimension001': 40"]}},
  {"tool": "add_drawing_dimension", "args": {"view": "BaseView",
    "picks": [{"kind": "circle", "near": [-20, 0]}]},
   "expect": {"contains": ["Diameter 'Dimension002': 10"]}},
  {"tool": "add_drawing_dimension", "args": {"view": "BaseView",
    "picks": [{"kind": "arc", "near": [40, 20]}]},
   "expect": {"contains": ["Radius 'Dimension003': 6"]}},
  {"tool": "add_drawing_dimension", "args": {"view": "ProjectedView001",
    "picks": [{"kind": "line", "near": [-5, 0]}, {"kind": "line", "near": [5, 0]}]},
   "expect": {"contains": ["Dimension004': 10"]}}
]
```

The last one is the thickness, on the right view (the plate seen from its side: 10 wide, 40
high there).

## 4. Where the holes are

The holes' places from one corner: an **ordinate** set (the corner is 0, each hole gets its
x and y), or **baseline** dimensions (each from the same end of a first dimension, stacked 8 mm
apart). One of the two is enough on a real drawing; both are shown here. `axis` picks the
values; `at` would put the values' lines through a point of the sheet.

```json fission180-calls
[
  {"tool": "add_drawing_dimension", "args": {"view": "BaseView", "type": "ordinate",
    "origin": {"kind": "vertex", "near": [-40, -20]},
    "picks": [{"kind": "circle", "near": [-20, 0]}, {"kind": "circle", "near": [20, 0]}],
    "axis": "x"},
   "expect": {"contains": ["3 ordinate values", "= 20", "= 60"]}},
  {"tool": "add_drawing_dimension", "args": {"view": "BaseView", "type": "linear", "picks": [
    {"kind": "vertex", "near": [-40, -20]}, {"kind": "circle", "near": [-20, 0]}]},
   "expect": {"contains": ["DistanceX 'Dimension005': 20"]}},
  {"tool": "add_drawing_dimension", "args": {"type": "baseline", "from": "Dimension005",
    "picks": [{"kind": "circle", "near": [20, 0]}]},
   "expect": {"contains": ["1 baseline dimensions", "DistanceX 'Dimension006': 60"]}}
]
```

## 5. Tolerances, centre marks, GD&T

[edit_drawing_dimension](fission180://docs/reference/edit_drawing_dimension.md) is Fusion's
Edit Dimension: the holes take an H7 fit and "2x" (two of them), the length ±0.1. A wrong
entry (an upper tolerance under the lower, a class Fission 180 does not know) is refused with
the reason. Centre marks and a centre line come from
[add_drawing_geometry](fission180://docs/reference/add_drawing_geometry.md) (no picks: every
circle without one); datums and frames from
[add_drawing_symbol](fission180://docs/reference/add_drawing_symbol.md): datum A on the bottom
edge, a position tolerance of 0.05 on the holes measured from A.

```json fission180-calls
[
  {"tool": "edit_drawing_dimension", "args": {"dimensions": ["Dimension002"],
    "tolerance": "fit", "fit": "H7", "prefix": "2x "},
   "expect": {"contains": ["2x ⌀10 H7"]}},
  {"tool": "edit_drawing_dimension", "args": {"dimensions": ["Dimension"],
    "tolerance": "symmetric", "upper": 0.1},
   "expect": {"contains": ["80 ±0.1"]}},
  {"tool": "edit_drawing_dimension", "args": {"dimensions": ["Dimension001"],
    "tolerance": "deviation", "upper": -0.1, "lower": 0.1},
   "expect": {"error": true, "contains": ["upper tolerance must be above the lower"]}},
  {"tool": "add_drawing_geometry", "args": {"kind": "center_mark", "view": "BaseView"},
   "expect": {"contains": ["2 centre marks"]}},
  {"tool": "add_drawing_geometry", "args": {"kind": "centerline", "view": "BaseView", "picks": [
    {"kind": "line", "near": [0, -20]}, {"kind": "line", "near": [0, 20]}]},
   "expect": {"contains": ["centre line on Base View"]}},
  {"tool": "add_drawing_symbol", "args": {"kind": "datum_identifier", "view": "BaseView",
    "pick": {"kind": "line", "near": [0, -20]}},
   "expect": {"contains": [": A."]}},
  {"tool": "add_drawing_symbol", "args": {"kind": "feature_control_frame", "view": "BaseView",
    "pick": {"kind": "circle", "near": [20, 0]}, "tolerance": 0.05, "datums": ["A"]},
   "expect": {"contains": ["Position|⌀0.05|A"]}}
]
```

## 6. A section and a detail

A section through the holes shows they go through: the cut line is in the base view's own
mm, across it at y = 0. Fission 180 puts the section beside the view along the cut line's
normal, past the views in the way. A detail at twice the base view's scale (4:1) shows the
rounded corner.

```json fission180-calls
[
  {"tool": "add_drawing_view", "args": {"kind": "section", "parent": "BaseView",
    "line": [[-50, 0], [50, 0]]},
   "expect": {"contains": ["SECTION A-A"], "not_contains": ["overlaps"]}},
  {"tool": "add_drawing_view", "args": {"kind": "detail", "parent": "BaseView",
    "center": [40, 20], "radius": 8},
   "expect": {"contains": ["DETAIL B (4:1)"]}}
]
```

## 7. Title block, the check, the files

[edit_title_block](fission180://docs/reference/edit_title_block.md) types into the title block
(the title, part number, material, scale, size and sheet follow the design by themselves).
`get_drawing` then says everything the drawing holds: read the dimensions' `value` and `text`,
and `picture` returns a PNG of the sheet drawn from its DXF. Export DXF here; PDF needs the
Fission 180 window (`export_drawing` format `pdf` there).

```json fission180-calls
[
  {"tool": "edit_title_block", "args": {"values": {"Description": "Mounting plate",
    "Revision": "A", "CheckedBy": "LS"}},
   "expect": {"contains": ["Description 'Mounting plate'"]}},
  {"tool": "get_drawing", "args": {},
   "expect": {"contains": ["\"text\": \"2x ⌀10 H7\"", "\"kind\": \"datum\"",
     "\"Description\": \"Mounting plate\"", "\"Scale\": \"2:1\""]}},
  {"tool": "get_drawing", "args": {"picture": true, "width": 840}, "expect": {"image": [840, 594]}},
  {"tool": "export_drawing", "args": {"format": "dxf", "path": "{tmp}/plate.dxf"},
   "expect": {"contains": ["Exported Drawn plate Drawing", "Not kept in this file:"]}},
  {"tool": "check_design", "args": {}, "expect": {"json": {"ok": true}}}
]
```

## Variations

- An ASME drawing in inches: `create_drawing` with `standard` ASME, `units` in, `sheet` B
  (third angle projection: the top view goes above the front).
- Fusion's automatic layout: `create_drawing` with `automatic` true (front, top, right and
  an isometric view, laid out to fit).
- Too big for the sheet: the answers say "overlaps" or "reaches off the sheet"; give a
  smaller `scale` (`edit_drawing_view`), `modify_drawing` kind move, or a bigger `sheet`.
- More sheets: `drawing_sheet` action add, then give the new sheet's id as `drawing`.
- A long part: `add_drawing_view` kind break leaves out the middle; a hidden pocket: kind
  breakout opens the view down to a depth.
