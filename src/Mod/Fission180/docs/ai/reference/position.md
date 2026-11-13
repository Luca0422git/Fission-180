# `position`: Capture / revert position

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: ASSEMBLE > Capture Position / Revert Position. Category: Assemble. Changes the design (one undo step). Its undo step is named like "AI: Capture position". Needs an open design.

## What it does

After components were moved by drive_joint or move_copy: capture keeps them where they are now (a Position step in the timeline, Fusion's Capture Position); revert puts them back where the last capture (or the joints) left them. Answers where each component stands.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `action` (required) | `capture` \| `revert` |  |  |  |  |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: action is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: keep the arm turned 20 degrees as the assembly's position

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
  {"tool": "drive_joint", "args": {"joint": "Joint", "angle": 20}}
]
```

The call:

```json
{"tool": "position", "args": {"action": "capture"}}
```

The answer:

```text
Done: captured the positions as 'Position 1' (id 'Position') in the timeline. Components: Base at [0, 0, 0]; Arm at [0, 0, 0]; Stop at [0, 0, 0]. Bodies now: Body001: 111749 mm3, 140 x 80 x 10 mm; Body002: 2608.63 mm3, 55 x 10 x 5 mm; Body003: 500 mm3, 10 x 10 x 5 mm.
```

## More argument examples

- keep the assembly as it stands now:
  `{"action": "capture"}`

## See also

- Recipe: [an assembly that moves (hinge, linked slider, stop)](fission180://docs/recipes/hinged-assembly.md)
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
