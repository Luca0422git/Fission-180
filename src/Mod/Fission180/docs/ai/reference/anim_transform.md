# `anim_transform`: Transform components

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: ANIMATION > TRANSFORM > Transform Components. Category: Animation. Changes the design (one undo step). Its undo step is named like "AI: Transform Components". Needs an open design.
It builds the design step(s) `anim_transform` (the golden models' step language).

## What it does

Move and / or turn components in a storyboard (Fusion's Transform Components, by numbers), in design coordinates: first the turn of angle degrees about axis through pivot (default: the middle of the components), then the move [x, y, z] mm. of: the components (ids or names; a body or step inside one stands for it). at: where the playhead stands, in seconds on the storyboard's timeline. The action is recorded so that it ENDS there and starts where the component's previous action ended (1 s before, when that leaves no room). at 0 is the scratch zone: nothing is recorded, the storyboard just starts that way. storyboard: its name (default: the active storyboard; a design without one gets "Storyboard1"). Answers the actions made (id, start, end) and where the components are at that time. An animation moves a display copy of the design's components: the design itself never changes (a design of plain bodies has nothing to animate: components_from_bodies first).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `storyboard` | string |  |  |  | the storyboard's name (default: the active one) |
| `at` (required) | number | mm |  | >= 0 | where the playhead stands (seconds; 0 = the scratch zone) |
| `of` (required) | array of strings |  |  | at least 1 item(s) | the components to transform |
| `move` | array of 3 numbers | mm |  |  | [x, y, z] the move in design coordinates (mm) |
| `axis` | array of 3 numbers |  |  |  | [x, y, z] the axis of the turn (default [0, 0, 1]) |
| `angle` | number | deg |  |  | the turn about the axis (degrees) |
| `pivot` | array of 3 numbers | mm |  |  | [x, y, z] a point the axis goes through (mm; default: the middle) |

## Answer

A plain sentence, then JSON with: `storyboard`, `at`, `actions`, `components_at`. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: at is missing; of is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: lift the wheel 30 mm in the first 2 seconds

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "new_component", "args": {"label": "Base"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [-30, -30, 30, 30]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 10}},
  {"tool": "new_component", "args": {"label": "Wheel"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 20, "geometry": [{"circle": [0, 0, 15]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch2", "distance": 5}}
]
```

The call:

```json
{"tool": "anim_transform", "args": {"at": 2, "of": ["Wheel"], "move": [0, 0, 30]}}
```

The answer:

```text
Done: Wheel transformed on 'Storyboard1', 1 action ending at 2 s. The storyboard is 2 s long.
{
 "storyboard": "Storyboard1",
 "at": 2.0,
 "actions": [
  {
   "id": 1,
   "kind": "transform",
   "what": "Move",
   "component": "Wheel",
   "component_id": "Component001",
   "start": 0.0,
   "end": 2.0,
   "move": [0.0, 0.0, 30.0],
   "frame": "the component's parent"
  }
 ],
 "components_at": [
  {
   "component": "Wheel",
   "id": "Component001",
   "position": [0.0, 0.0, 30.0],
   "moved_by": [0.0, 0.0, 30.0],
   "axis": [0.0, 0.0, 1.0],
   "angle": 0.0
  }
 ]
}
```

## More argument examples

- lift the wheel 30 mm in 2 s:
  `{"at": 2, "of": ["Wheel"], "move": [0, 0, 30]}`
- then turn it a quarter about Z through its middle:
  `{"at": 4, "of": ["Wheel"], "axis": [0, 0, 1], "angle": 90}`

## See also

- Golden models built with its steps (read one with docs_read golden/<id>): `anim_sequential_transform_reverse`
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
