# `motion_study`: Motion study

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: ASSEMBLE > Motion Study. Category: Assemble. Changes the design (one undo step). Its undo step is named like "AI: Motion study". Needs an open design.

## What it does

Fusion's Motion Study: joints driven together over steps 0..100 by key values, kept in the design to play back (browser). joints: the joints; keys: [{joint, step, value}] (degrees or mm; between keys the value goes straight from one to the next; a joint without a key at 0 starts where it is); mode once | loop | pingpong, speed. report: the steps whose component positions the answer gives (default [0, 50, 100]); after it the assembly is put back as it was. Checks a mechanism's travel without moving it.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `joints` (required) | array of strings |  |  | at least 1 item(s) | the joints it drives |
| `keys` (required) | array of objects |  |  | at least 1 item(s) | the key values |
| `mode` | `once` \| `loop` \| `pingpong` |  | `"once"` |  |  |
| `speed` | number |  | `1` | > 0 | playback speed (1: 4 s for 100 steps) |
| `report` | array of numbers | 0..1 |  | at least 1 item(s), at most 11 item(s) | steps to report (0..100) |

## Answer

A plain sentence, then JSON with: `study`, `label`, `mode`, `note`, `at_steps`. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: joints is missing; keys is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: the arm swung from 0 to 90 degrees, where things stand half way

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
  {"tool": "as_built_joint", "args": {"type": "revolute", "components": ["Arm", "Base"], "position": {"component": "Arm", "edge": {"type": "circle", "radius": 3, "at": {"axis": "z", "value": "max"}, "count": 1}, "snap": "circle"}}}
]
```

The call:

```json
{"tool": "motion_study", "args": {"joints": ["Joint"], "keys": [{"joint": "Joint", "step": 0, "value": 0}, {"joint": "Joint", "step": 100, "value": 90}], "report": [0, 50, 100]}}
```

The answer:

```text
Done: motion study 'Motion Study 1' (id 'MotionStudy') with 1 joint; the assembly is back as it was.
{
 "study": "MotionStudy",
 "label": "Motion Study 1",
 "mode": "once",
 "note": "joints: [angle (degrees), slide (mm)] at each step; components: where each one's origin stands (mm)",
 "at_steps": [
  {
   "step": 0.0,
   "joints": {"Joint": [0.0, 0.0]},
   "components": {"Base": [0.0, 0.0, 0.0], "Arm": [0.0, 0.0, 0.0], "Stop": [0.0, 0.0, 0.0]},
   "solved": true
  },
  {
   "step": 50.0,
   "joints": {"Joint": [45.0, 0.0]},
   "components": {"Base": [0.0, 0.0, 0.0], "Arm": [0.0, 0.0, 0.0], "Stop": [0.0, 0.0, 0.0]},
   "solved": true
  },
  {
   "step": 100.0,
   "joints": {"Joint": [90.0, 0.0]},
   "components": {"Base": [0.0, 0.0, 0.0], "Arm": [0.0, 0.0, 0.0], "Stop": [0.0, 0.0, 0.0]},
   "solved": true
  }
 ]
}
```

## More argument examples

- turn Joint1 from 0 to 90 degrees:
  `{"joints": ["Joint1"], "keys": [{"joint": "Joint1", "step": 0, "value": 0}, {"joint": "Joint1", "step": 100, "value": 90}]}`

## See also

- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
