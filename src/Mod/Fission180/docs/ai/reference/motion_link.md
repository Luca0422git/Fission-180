# `motion_link`: Motion link

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: ASSEMBLE > Motion Link. Category: Assemble. Changes the design (one undo step). Its undo step is named like "AI: Motion link". Needs an open design.

## What it does

Tie two joints' motions (Fusion's Motion Link): when the first moves values[0], the second moves values[1] (degrees for turning joints, mm for sliding ones): a gear pair [360, -720], a rack and pinion [360, 62.83]. The same joint twice ties its turn to its slide (a screw: [360, 1.5] for a 1.5 mm pitch, on a cylindrical or pin-slot joint). motions: which motion of each joint (angle | slide; default its own: a slider's slide, else its angle); reverse flips the second. Check it with drive_joint on the first.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `joints` (required) | array of 2 strings |  |  |  | the two joints (the same id twice: Link with Same Joint) |
| `values` (required) | array of 2 numbers | mm or deg |  |  | [first, second] (degrees or mm) |
| `reverse` | boolean |  | `false` |  | the second moves the other way |
| `motions` | array of 2 strings |  |  |  | [first, second] |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: joints is missing; values is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: a turn of the arm slides the block 36 mm

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
  {"tool": "as_built_joint", "args": {"type": "revolute", "components": ["Arm", "Base"], "position": {"component": "Arm", "edge": {"type": "circle", "radius": 3, "at": {"axis": "z", "value": "max"}, "count": 1}, "snap": "circle"}}},
  {"tool": "new_component", "args": {"label": "Slide"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 10, "geometry": [{"rect": [60, -30, 70, -20]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch4", "distance": 10}},
  {"tool": "as_built_joint", "args": {"type": "slider", "components": ["Slide", "Base"], "position": {"component": "Slide", "edge": {"type": "line", "parallel": [1, 0, 0], "at": [{"axis": "y", "value": "min"}, {"axis": "z", "value": "max"}], "count": 1}, "snap": "midpoint"}}}
]
```

The call:

```json
{"tool": "motion_link", "args": {"joints": ["Joint", "Joint001"], "values": [360, 36]}}
```

The answer:

```text
Done: motion link 'Motion Link 1' (id 'MotionLink'): when Revolute 1 moves 1 degree (angle), Slider 1 moves 0.1 mm (slide). Next: drive_joint Joint and check that Joint001 follows. Bodies now: Body001: 111749 mm3, 140 x 80 x 10 mm; Body002: 2608.63 mm3, 55 x 10 x 5 mm; Body003: 500 mm3, 10 x 10 x 5 mm; Body004: 1000 mm3, 10 x 10 x 10 mm.
```

## More argument examples

- the second gear turns twice as fast, the other way:
  `{"joints": ["Joint1", "Joint2"], "values": [360, -720]}`

## See also

- Recipe: [an assembly that moves (hinge, linked slider, stop)](fission180://docs/recipes/hinged-assembly.md)
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
