# `anim_manual_explode`: Manual explode

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: ANIMATION > TRANSFORM > Manual Explode. Category: Animation. Changes the design (one undo step). Its undo step is named like "AI: Manual Explode". Needs an open design.
It builds the design step(s) `anim_manual_explode` (the golden models' step language).

## What it does

Fusion's Manual Explode: each picked component moves `distance` mm (times scale) along its axis. picks: [{"of": a component, "axis": "X+" | "X-" | "Y+" | "Y-" | "Z+" | "Z-"}] (design directions). sequential true: one after another, in the order picked. trails: trail lines on or off. at: where the playhead stands, in seconds on the storyboard's timeline. The action is recorded so that it ENDS there and starts where the component's previous action ended (1 s before, when that leaves no room). at 0 is the scratch zone: nothing is recorded, the storyboard just starts that way. storyboard: its name (default: the active storyboard; a design without one gets "Storyboard1"). Answers each component's move. An animation moves a display copy of the design's components: the design itself never changes (a design of plain bodies has nothing to animate: components_from_bodies first).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `storyboard` | string |  |  |  | the storyboard's name (default: the active one) |
| `at` (required) | number | mm |  | >= 0 | where the playhead stands (seconds; 0 = the scratch zone) |
| `picks` (required) | array of objects |  |  | at least 1 item(s) | the components and their directions |
| `distance` (required) | number | mm |  | > 0 | how far each moves (mm) |
| `scale` | number |  | `1.0` | > 0 | the Explosion Scale: multiplies the distance |
| `sequential` | boolean |  | `false` |  | one after another instead of all at once |
| `trails` | boolean |  |  |  | trail lines on (true) or off (false) for the moved components |

## Answer

A plain sentence, then JSON with: `storyboard`, `at`, `actions`, `moves`, `components_at`. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: at is missing; picks is missing; distance is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: the wheel 40 mm up

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
{"tool": "anim_manual_explode", "args": {"at": 2, "picks": [{"of": "Wheel", "axis": "Z+"}], "distance": 40}}
```

The answer:

```text
Done: 1 component exploded on 'Storyboard1', 1 action ending at 2 s. The storyboard is 2 s long.
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
   "move": [0.0, 0.0, 40.0],
   "frame": "the component's parent"
  }
 ],
 "moves": [{"component": "Wheel", "id": "Component001", "move_in_parent": [0.0, 0.0, 40.0]}],
 "components_at": [
  {
   "component": "Wheel",
   "id": "Component001",
   "position": [0.0, 0.0, 40.0],
   "moved_by": [0.0, 0.0, 40.0],
   "axis": [0.0, 0.0, 1.0],
   "angle": 0.0
  }
 ]
}
```

## More argument examples

- the wheel 40 mm up:
  `{"at": 2, "picks": [{"of": "Wheel", "axis": "Z+"}], "distance": 40}`

## See also

- Golden models built with its steps (read one with docs_read golden/<id>): `anim_sequential_transform_reverse`
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
