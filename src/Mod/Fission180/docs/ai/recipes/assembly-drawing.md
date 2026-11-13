# Recipe: an assembly drawing with an exploded view, balloons and a parts list

Tags: drawing, assembly, components, exploded view, storyboard, animation, parts list, bill of materials, balloons, renumber, csv

An assembly of three components (a base 60 x 60 x 10, a wheel 30 mm across with a 6 mm bore,
a pin 6 mm across through it)
drawn the way Fusion's assembly drawings are: a front and a top view of the assembly, an
exploded isometric view of an animation storyboard's end, the parts list with a balloon on
each part, the balloons renumbered and lined up, the parts list as a CSV for a spreadsheet.
Every call was run by Fission 180's tests; `expect` is what the answer must contain.

Ask the person first: which parts go in the parts list (a drawing of the full assembly lists
every component; `bodies` draws only some), what the item order should be, and whether they
want an exploded view (it needs an animation storyboard: the ANIMATION tools make one).

## 1. The assembly

Each part is a component of its own (a parts list lists components, as in Fusion); the next
sketches go into the component made last. The wheel's sketch has its bore inside its outline:
the extrude makes a ring, and the pin goes through it without the two overlapping
(`check_design` says so when parts overlap).

```json fission180-calls
[
  {"tool": "new_design", "args": {"name": "Wheel assembly"}},
  {"tool": "new_component", "args": {"label": "Base"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [-30, -30, 30, 30]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 10}},
  {"tool": "new_component", "args": {"label": "Wheel"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 20,
    "geometry": [{"circle": [0, 0, 15]}, {"circle": [0, 0, 3]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch2", "distance": 5}},
  {"tool": "new_component", "args": {"label": "Pin"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 10,
    "geometry": [{"circle": [0, 0, 3]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch3", "distance": 25},
   "expect": {"contains": ["6 x 6 x 25 mm"]}},
  {"tool": "check_design", "args": {}, "expect": {"json": {"ok": true}}}
]
```

## 2. The storyboard an exploded view shows

An exploded view draws a storyboard of the ANIMATION workspace at its end. Auto Explode moves
the smaller components away from the biggest one.

```json fission180-calls
[
  {"tool": "anim_storyboard", "args": {"name": "Explode"}},
  {"tool": "anim_explode", "args": {"at": 3}, "expect": {"contains": ["2 components exploded"]}}
]
```

## 3. The drawing, the exploded view, the parts list

`contents` full_assembly: the drawing shows every component, also ones made later. The
exploded view is a base view of the storyboard (`add_drawing_view` kind exploded): Fission 180
puts it on free paper at the scale its parts fit. The parts list
(`add_drawing_annotation` kind parts_list) lists the components the view shows, numbered,
and puts a balloon on each, outside the view, nearest its part. `get_drawing` reads the rows.

```json fission180-calls
[
  {"tool": "create_drawing", "args": {"contents": "full_assembly", "base_view": "Front",
    "projected": ["Top"]},
   "expect": {"contains": ["(id 'Drawing')"]}},
  {"tool": "add_drawing_view", "args": {"kind": "exploded", "orientation": "Home"},
   "expect": {"contains": ["storyboard 'Explode' at its end"], "not_contains": ["overlaps"]}},
  {"tool": "add_drawing_annotation", "args": {"kind": "parts_list", "view": "BaseView001"},
   "expect": {"contains": ["3 rows (1 Base x1, 2 Wheel x1, 3 Pin x1) and 3 balloons"]}},
  {"tool": "get_drawing", "args": {},
   "expect": {"contains": ["\"storyboard\": \"Explode\"", "\"kind\": \"parts_list\"",
     "\"PartNumber\": \"Pin\""]}}
]
```

## 4. Item numbers and balloons

Renumber gives a balloon's row the number asked for (the row that had it takes the old one)
and the parts list sorts; Align Balloons lines balloons up through a point of the sheet (one
level line when they spread sideways, else one upright line). A balloon on another view names
its part by the parts list's part number (or a body id).

```json fission180-calls
[
  {"tool": "edit_balloons", "args": {"kind": "renumber", "balloon": "3", "to": 1},
   "expect": {"contains": ["item 3 is now 1", "1 Pin, 2 Wheel, 3 Base"]}},
  {"tool": "edit_balloons", "args": {"kind": "align", "balloons": ["1", "2", "3"],
    "at": [60, 250]},
   "expect": {"contains": ["3 balloons on one"]}},
  {"tool": "add_drawing_annotation", "args": {"kind": "balloon", "view": "BaseView",
    "component": "Pin"},
   "expect": {"contains": ["(1, Pin) on Base View"]}},
  {"tool": "add_drawing_annotation", "args": {"kind": "balloon", "view": "BaseView",
    "component": "Nut"},
   "expect": {"error": true, "contains": ["no row 'Nut'"]}}
]
```

## 5. The parts list as a file, the check

`export_drawing` format csv writes the parts list for a spreadsheet (UTF-8, the header first).
The picture shows the sheet: views, balloons, the table.

```json fission180-calls
[
  {"tool": "export_drawing", "args": {"format": "csv", "path": "{tmp}/parts.csv"},
   "expect": {"contains": ["Exported Parts List", "3 rows"]}},
  {"tool": "get_drawing", "args": {"picture": true, "width": 840}, "expect": {"image": [840, 594]}},
  {"tool": "check_design", "args": {}, "expect": {"json": {"ok": true}}}
]
```

## Variations

- A whole drawing of the storyboard (Fusion's New Drawing From Animation): `create_drawing`
  with `storyboard` "Explode" and `automatic` true: four views, every one exploded.
- Back to the assembled design in one view: `edit_drawing_view` with `storyboard` "Model".
- No storyboard yet: `add_drawing_view` kind exploded says so and names the ANIMATION tools.
- A balloon that should point elsewhere: `modify_drawing` kind move with the balloon's id moves
  its circle (its arrow stays on its part).
