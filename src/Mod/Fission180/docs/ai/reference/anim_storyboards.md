# `anim_storyboards`: Storyboards and actions

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: ANIMATION > ANIMATION TIMELINE. Category: Animation. Read-only. Needs an open design.

## What it does

Read the animations. Without storyboard: every storyboard (name, length in seconds, how many actions of each kind, the components it moves) and the active one, and the components an animation can move. With storyboard: its actions in time order (id, kind transform | visibility | view | callout, the component, start and end in seconds, and its values: move, axis, angle, pivot / show / text, point), how it starts (components placed or hidden in the scratch zone) and its trail lines. at (seconds; with storyboard): also where every moved component is at that time (its position and its turn as axis and angle, design coordinates) and which are hidden. Changes nothing.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `storyboard` | string |  |  |  | read this storyboard's actions (default: list them all) |
| `at` | number | mm |  | >= 0 | with storyboard: the components' places at this time (s) |

## Answer

A plain sentence, then JSON with: `storyboard`, `length_s`, `actions`, `starts_with`, `trails`, `at`, `components_at`, `hidden_at`. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: the storyboard's actions, and where the wheel is half way

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
{"tool": "anim_storyboards", "args": {"storyboard": "Explode", "at": 1.5}}
```

The answer:

```text
Storyboard 'Explode': 3 s, 1 action.
{
 "storyboard": "Explode",
 "length_s": 3.0,
 "actions": [
  {
   "id": 1,
   "kind": "transform",
   "what": "Move",
   "component": "Wheel",
   "component_id": "Component001",
   "start": 0.0,
   "end": 3.0,
   "move": [0.0, 0.0, 15.0],
   "frame": "the component's parent"
  }
 ],
 "starts_with": {"moved": [], "visibility": {}, "camera": false},
 "trails": [],
 "at": 1.5,
 "components_at": [
  {
   "component": "Wheel",
   "id": "Component001",
   "position": [0.0, 0.0, 7.5],
   "moved_by": [0.0, 0.0, 7.5],
   "axis": [0.0, 0.0, 1.0],
   "angle": 0.0
  }
 ],
 "hidden_at": []
}
```

## More argument examples

- the storyboards:
  `{}`
- its actions, and the places at 3 s:
  `{"storyboard": "Explode", "at": 3}`

## See also

- Recipe: [an exploded-view video of an assembly (ANIMATION)](fission180://docs/recipes/exploded-view-video.md)
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
