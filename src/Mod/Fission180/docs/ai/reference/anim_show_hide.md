# `anim_show_hide`: Show / hide

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: ANIMATION > TRANSFORM > Show/Hide. Category: Animation. Changes the design (one undo step). Its undo step is named like "AI: Hide components". Needs an open design.
It builds the design step(s) `anim_show_hide` (the golden models' step language).

## What it does

Show or hide components from a moment of a storyboard on (Fusion's Show/Hide: the light-bulb action on the timeline). show true | false (left out: each is toggled). at: the moment (seconds; 0: the storyboard starts that way). A component hidden in the design itself cannot be shown by a storyboard (the answer says so: show it in Design, show_hide). of: the components (ids or names; a body or step inside one stands for it). storyboard: its name (default: the active storyboard; a design without one gets "Storyboard1"). An animation moves a display copy of the design's components: the design itself never changes (a design of plain bodies has nothing to animate: components_from_bodies first).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `storyboard` | string |  |  |  | the storyboard's name (default: the active one) |
| `at` (required) | number | mm |  | >= 0 | where the playhead stands (seconds; 0 = the scratch zone) |
| `of` (required) | array of strings |  |  | at least 1 item(s) | the components to show or hide |
| `show` | boolean |  |  |  | show (true) or hide (false); left out: toggle |

## Answer

A plain sentence, then JSON with: `storyboard`, `at`, `actions`, `components_at`, `hidden_at`. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: at is missing; of is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: the wheel disappears at 2 seconds

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
{"tool": "anim_show_hide", "args": {"at": 2, "of": ["Wheel"], "show": false}}
```

The answer:

```text
Done: Wheel hidden on 'Storyboard1', 1 action ending at 2 s. The storyboard is 2 s long.
{
 "storyboard": "Storyboard1",
 "at": 2.0,
 "actions": [
  {
   "id": 1,
   "kind": "visibility",
   "what": "Hide",
   "component": "Wheel",
   "component_id": "Component001",
   "start": 2.0,
   "end": 2.0,
   "show": false
  }
 ],
 "components_at": [],
 "hidden_at": ["Wheel"]
}
```

## More argument examples

- the wheel disappears at 2 s:
  `{"at": 2, "of": ["Wheel"], "show": false}`

## See also

- Golden models built with its steps (read one with docs_read golden/<id>): `anim_sequential_transform_reverse`
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
