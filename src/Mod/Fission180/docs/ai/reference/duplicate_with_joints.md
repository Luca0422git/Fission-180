# `duplicate_with_joints`: Duplicate with joints

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: ASSEMBLE > Duplicate With Joints. Category: Assemble. Changes the design (one undo step). Its undo step is named like "AI: Duplicate with joints". Needs an open design.

## What it does

Copy jointed components to new places, joined there (Fusion's Duplicate With Joints): a screw (and its nut) into more holes. components: the jointed ones to copy (linked copies); joint: the open joint (from them to something outside; default: the only one); at: one place per copy, {component, face | edge | vertex, snap, point} as joint's second side (the hole's circular edge, snap circle). Joints and rigid groups between the copied components are copied too. Answers the copies' ids and where they went.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `components` (required) | array of strings |  |  | at least 1 item(s) | the jointed components to copy |
| `joint` | string |  |  |  | the open joint the copies are joined with |
| `at` (required) | array of objects |  |  | at least 1 item(s) | one new place per copy |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: components is missing; at is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: a second pin in the other hole, joined like the first

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "new_component", "args": {"label": "Base"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [-40, -40, 100, 40]}, {"circle": [80, 30, 2]}, {"circle": [80, -30, 2]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 10}},
  {"tool": "ground", "args": {"component": "Base"}},
  {"tool": "new_component", "args": {"label": "Arm"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 10, "geometry": [{"rect": [-5, -5, 50, 5]}, {"circle": [0, 0, 3]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch2", "distance": 5}},
  {"tool": "new_component", "args": {"label": "Stop"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 10, "geometry": [{"rect": [20, -20, 30, -10]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch3", "distance": 5}},
  {"tool": "new_component", "args": {"label": "Pin"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 10, "geometry": [{"circle": [80, 30, 2]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch4", "distance": 8}},
  {"tool": "joint", "args": {"type": "rigid", "first": {"component": "Pin", "face": {"normal": [0, 0, -1], "count": 1}, "snap": "centre"}, "second": {"component": "Base", "edge": {"type": "circle", "at": [{"axis": "x", "value": 80}, {"axis": "y", "value": 30}, {"axis": "z", "value": "max"}], "count": 1}, "snap": "circle"}}}
]
```

The call:

```json
{"tool": "duplicate_with_joints", "args": {"components": ["Pin"], "at": [{"component": "Base", "edge": {"type": "circle", "at": [{"axis": "x", "value": 80}, {"axis": "y", "value": -30}, {"axis": "z", "value": "max"}], "count": 1}, "snap": "circle"}]}}
```

The answer:

```text
Done: 1 duplicate of Pin joined like Rigid 1: Pin:2 (id Component004) at [0, -60, 0]. Bodies now: Body001: 111749 mm3, 140 x 80 x 10 mm; Body002: 2608.63 mm3, 55 x 10 x 5 mm; Body003: 500 mm3, 10 x 10 x 5 mm; Body004: 100.531 mm3, 4 x 4 x 8 mm; Body005: 100.531 mm3, 4 x 4 x 8 mm.
```

## More argument examples

- a second screw in the hole at x = 30:
  `{"components": ["Screw"], "at": [{"component": "Plate", "edge": {"type": "circle", "at": {"axis": "x", "value": 30}, "count": 1}, "snap": "circle"}]}`

## See also

- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
