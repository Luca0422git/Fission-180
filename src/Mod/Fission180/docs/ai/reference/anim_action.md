# `anim_action`: Edit animation actions

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: ANIMATION > ANIMATION TIMELINE > action > Edit Start/End, drag, Delete. Category: Animation. Changes the design (one undo step). Its undo step is named like "AI: Edit animation action". Needs an open design.

## What it does

Change actions already on a storyboard, as the ANIMATION TIMELINE does with its bars: start / end (seconds; Edit Start/End: one action), shift (seconds, a drag: every action named moves, its length kept, never before 0) or delete true. actions: the ids anim_storyboards lists (the recording tools answer them too). A transform or view needs at least 0.1 s; a callout's end may be null (shown to the end). Answers the actions' new times and the storyboard's length. storyboard: its name (default: the active storyboard; a design without one gets "Storyboard1"). An animation moves a display copy of the design's components: the design itself never changes (a design of plain bodies has nothing to animate: components_from_bodies first).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `storyboard` | string |  |  |  | the storyboard's name (default: the active one) |
| `actions` (required) | array of integers |  |  | at least 1 item(s) | the actions to change |
| `start` | number |  |  | >= 0 | Edit Start/End: when it starts (s) |
| `end` | number or null |  |  |  | when it ends (s; null: a callout to the end) |
| `shift` | number |  |  |  | move the actions this many seconds later (negative: earlier) |
| `delete` | boolean |  | `false` |  | delete the actions |

## Answer

A plain sentence, then JSON with: `storyboard`, `actions`. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: actions is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: the wheel's explosion from 1 s to 4 s

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
{"tool": "anim_action", "args": {"actions": [1], "start": 1, "end": 4}}
```

The answer:

```text
Done: 1 1.0 to 4.0 s on 'Explode'; it is 4 s long now.
{
 "storyboard": "Explode",
 "actions": [
  {
   "id": 1,
   "kind": "transform",
   "what": "Move",
   "component": "Wheel",
   "component_id": "Component001",
   "start": 1.0,
   "end": 4.0,
   "move": [0.0, 0.0, 15.0],
   "frame": "the component's parent"
  }
 ]
}
```

## More argument examples

- the action runs from 1 s to 4 s:
  `{"actions": [1], "start": 1, "end": 4}`
- two actions 2 s later:
  `{"actions": [2, 3], "shift": 2}`
- delete an action:
  `{"actions": [4], "delete": true}`

## See also

- Recipe: [an exploded-view video of an assembly (ANIMATION)](fission180://docs/recipes/exploded-view-video.md)
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
