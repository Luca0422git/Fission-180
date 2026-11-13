# `anim_explode`: Auto explode

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: ANIMATION > TRANSFORM > Auto Explode: One Level / All Levels. Category: Animation. Changes the design (one undo step). Its undo step is named like "AI: Auto Explode (One Level)". Needs an open design.
It builds the design step(s) `anim_explode` (the golden models' step language).

## What it does

Fusion's Auto Explode: the components move apart, away from the largest one, which stays. levels one (default: the components directly under the top, or directly inside the ones in `of`) | all (every level, subassemblies come apart too). of: explode only inside these components (default: the whole design). scale: the Explosion Scale (1 = a gap of a quarter of the assembly's size; 0.1 to 4). sequential true: one after another (the time up to `at` is shared), false: all at once (One-Step). trails: show (true) or hide (false) their trail lines. at: where the playhead stands, in seconds on the storyboard's timeline. The action is recorded so that it ENDS there and starts where the component's previous action ended (1 s before, when that leaves no room). at 0 is the scratch zone: nothing is recorded, the storyboard just starts that way. storyboard: its name (default: the active storyboard; a design without one gets "Storyboard1"). Answers each component's move [x, y, z] mm. An animation moves a display copy of the design's components: the design itself never changes (a design of plain bodies has nothing to animate: components_from_bodies first).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `storyboard` | string |  |  |  | the storyboard's name (default: the active one) |
| `at` (required) | number | mm |  | >= 0 | where the playhead stands (seconds; 0 = the scratch zone) |
| `levels` | `one` \| `all` |  | `"one"` |  | how deep |
| `of` | array of strings |  |  | at least 1 item(s) | explode only inside these components |
| `scale` | number |  | `1.0` | > 0, <= 4 | the Explosion Scale |
| `sequential` | boolean |  | `false` |  | one after another instead of all at once |
| `trails` | boolean |  |  |  | trail lines on (true) or off (false) for the moved components |

## Answer

A plain sentence, then JSON with: `storyboard`, `at`, `actions`, `moves`, `components_at`. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: at is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: explode the top level in 3 seconds

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
{"tool": "anim_explode", "args": {"at": 3}}
```

The answer:

```text
Done: 1 component exploded on 'Storyboard1', 1 action ending at 3 s. The storyboard is 3 s long.
{
 "storyboard": "Storyboard1",
 "at": 3.0,
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
 "moves": [{"component": "Wheel", "id": "Component001", "move_in_parent": [0.0, 0.0, 15.0]}],
 "components_at": [
  {
   "component": "Wheel",
   "id": "Component001",
   "position": [0.0, 0.0, 15.0],
   "moved_by": [0.0, 0.0, 15.0],
   "axis": [0.0, 0.0, 1.0],
   "angle": 0.0
  }
 ]
}
```

## More argument examples

- explode the top level in 3 s, all at once:
  `{"at": 3}`
- every level, one component after another, wider, with trail lines:
  `{"at": 6, "levels": "all", "sequential": true, "scale": 1.5, "trails": true}`

## See also

- Recipe: [an assembly drawing with an exploded view, balloons and a parts list](fission180://docs/recipes/assembly-drawing.md)
- Recipe: [an exploded-view video of an assembly (ANIMATION)](fission180://docs/recipes/exploded-view-video.md)
- Golden models built with its steps (read one with docs_read golden/<id>): `anim_auto_explode_one_level`, `anim_sequential_transform_reverse`
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
