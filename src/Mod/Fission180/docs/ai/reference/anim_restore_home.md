# `anim_restore_home`: Restore home

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: ANIMATION > TRANSFORM > Restore Home. Category: Animation. Changes the design (one undo step). Its undo step is named like "AI: Restore Home". Needs an open design.
It builds the design step(s) `anim_restore_home` (the golden models' step language).

## What it does

Send components back to where the design has them (Fusion's Restore Home): an action that undoes what the storyboard did to them up to the playhead. of: the components (ids or names; a body or step inside one stands for it). at: where the playhead stands, in seconds on the storyboard's timeline. The action is recorded so that it ENDS there and starts where the component's previous action ended (1 s before, when that leaves no room). at 0 is the scratch zone: nothing is recorded, the storyboard just starts that way. storyboard: its name (default: the active storyboard; a design without one gets "Storyboard1"). Refused with the reason when they are home already. An animation moves a display copy of the design's components: the design itself never changes (a design of plain bodies has nothing to animate: components_from_bodies first).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `storyboard` | string |  |  |  | the storyboard's name (default: the active one) |
| `at` (required) | number | mm |  | >= 0 | where the playhead stands (seconds; 0 = the scratch zone) |
| `of` (required) | array of strings |  |  | at least 1 item(s) | the components to send home |

## Answer

A plain sentence, then JSON with: `storyboard`, `at`, `actions`, `components_at`. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: at is missing; of is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: the wheel back in place by 5 seconds

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "new_component", "args": {"label": "Base"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [-30, -30, 30, 30]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 10}},
  {"tool": "new_component", "args": {"label": "Wheel"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 20, "geometry": [{"circle": [0, 0, 15]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch2", "distance": 5}},
  {"tool": "anim_storyboard", "args": {"name": "Explode"}},
  {"tool": "anim_explode", "args": {"at": 3}}
]
```

The call:

```json
{"tool": "anim_restore_home", "args": {"at": 5, "of": ["Wheel"]}}
```

The answer:

```text
Done: Wheel sent home on 'Explode', 1 action ending at 5 s. The storyboard is 5 s long.
{
 "storyboard": "Explode",
 "at": 5.0,
 "actions": [
  {
   "id": 2,
   "kind": "transform",
   "what": "Move",
   "component": "Wheel",
   "component_id": "Component001",
   "start": 3.0,
   "end": 5.0,
   "move": [0.0, 0.0, -15.0],
   "frame": "the component's parent"
  }
 ],
 "components_at": []
}
```

## More argument examples

- the wheel back in place by 5 s:
  `{"at": 5, "of": ["Wheel"]}`

## See also

- Golden models built with its steps (read one with docs_read golden/<id>): `anim_sequential_transform_reverse`
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
