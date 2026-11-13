# Recipe: check a part before it is made (draft, inner rounds, reach, smoothness)

Tags: inspect, analysis, draft analysis, minimum radius, accessibility, zebra, moulding, milling

Fission 180's INSPECT analyses colour the model for a person; for an AI the
[analysis](fission180://docs/reference/analysis.md) tool answers the same analyses as
numbers, with a ref for every face it flags, and leaves nothing in the design. Every call
below was run by Fission 180's tests; the `expect` part of each call is what the answer must
contain, not a tool argument.

## Ask first: how will it be made?

| Made by | Ask | Analysis | Fix with |
|---|---|---|---|
| Moulding, casting | Which way does the mould open? How much draft (1 to 3 degrees is usual)? | draft (direction: the opening direction) | draft |
| Milling | The smallest cutter's radius? From which sides can it reach? | minimum_radius (tool_radius), accessibility (direction) | fillet the inner corners, change the setup |
| A visible, smooth shape | Must the surfaces flow without a visible line? | zebra (or environment_map) | fillet_sets with radius_type, loft / surface with curvature continuity |

Run the analysis, read its numbers, fix, and run it again: the numbers say when it is done.
A picture helps a person (picture: true marks the faces found in orange); trust the numbers.

## 1. A box for a mould: which faces lack draft?

A 40 x 40 x 20 box opening along Z: the top comes out along the pull, the bottom is the other
mould half, and the four sides have no draft at all.

```json fission180-calls
[
  {"tool": "new_design", "args": {"name": "Moulded"}},
  {"tool": "primitive", "args": {"kind": "box", "length": 40, "width": 40, "height": 20},
   "expect": {"contains": ["32000 mm3"]}},
  {"tool": "analysis", "args": {"kind": "draft", "direction": "Z", "draft_min": 1, "draft_ok": 3},
   "expect": {"contains": ["4 faces under 1 degree(s)", "\"under_min\": 4"]}}
]
```

The four flagged faces come with refs: give them (or a selector for them) to draft, its
neutral plane square to the pull, then analyse again.

```json fission180-calls
[
  {"tool": "draft", "args": {"plane": "XY",
    "faces": {"along": [0, 0, 1], "type": "plane", "count": 4}, "angle": 5},
   "expect": {"contains": ["Done"]}},
  {"tool": "analysis", "args": {"kind": "draft", "direction": "Z", "draft_min": 1, "draft_ok": 3},
   "expect": {"contains": ["0 faces under 1 degree(s)"]}}
]
```

## 2. A plate for milling: tight inner rounds and what a cutter reaches

A plate with an 8 mm hole: a 5 mm cutter cannot mill a 4 mm radius (minimum_radius flags the
hole), and a cutter coming down Z reaches the top and nothing else.

```json fission180-calls
[
  {"tool": "new_design", "args": {"name": "Milled"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [
    {"rect": [0, 0, 40, 40]}, {"circle": [20, 20, 4]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 10}},
  {"tool": "analysis", "args": {"kind": "minimum_radius", "min_radius": 5, "tool_radius": 6},
   "expect": {"contains": ["The tightest inner round is 4 mm", "1 face tighter than 5 mm"]}},
  {"tool": "analysis", "args": {"kind": "accessibility", "direction": "Z"},
   "expect": {"contains": ["A tool along [0, 0, 1] (direction) reaches"]}}
]
```

## 3. Rounded edges: do the surfaces flow?

A fillet meets a flat face tangentially but its curvature jumps from 0 to 1 / r there: zebra
stripes kink (G1). The analysis lists those edges; a curvature-continuous blend removes them.

```json fission180-calls
[
  {"tool": "new_design", "args": {"name": "Smooth"}},
  {"tool": "primitive", "args": {"kind": "box", "length": 40, "width": 40, "height": 20}},
  {"tool": "fillet", "args": {"edges": {"type": "line", "at": {"axis": "z", "value": "max"},
    "count": 4}, "radius": 3}},
  {"tool": "analysis", "args": {"kind": "zebra"},
   "expect": {"contains": ["8 tangent edges with a curvature jump"]}},
  {"tool": "check_design", "args": {}, "expect": {"json": {"ok": true}}}
]
```

Curvature along chosen edges (curvature_comb) and along a face's U / V lines (isocurve) give
the tightest bend and the inflections of a free-form shape.
