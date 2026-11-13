# `anim_view`: View action

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: ANIMATION > VIEW > View. Category: Animation. Changes the design (one undo step). Its undo step is named like "AI: View". Needs an open design.

## What it does

Record a camera move on a storyboard (what Fusion's View records while a person orbits and zooms): the camera ends at `at` looking from view (iso, Fusion's Home: from the front, right and top; front, back, top, bottom, left, right) or from direction [x, y, z], with up the screen's up, and turns, pans and zooms smoothly from where it was. It fits the components shown at that time (of: fit these instead); zoom 2 is twice as close; perspective true for a perspective camera (orthographic by default). at 0: the storyboard just starts with this view. A storyboard without a view yet starts from the window's (iso without the window). Publish Video follows these views. Answers the action and the camera. storyboard: its name (default: the active storyboard; a design without one gets "Storyboard1"). An animation moves a display copy of the design's components: the design itself never changes (a design of plain bodies has nothing to animate: components_from_bodies first).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `storyboard` | string |  |  |  | the storyboard's name (default: the active one) |
| `at` (required) | number | mm |  | >= 0 | where the playhead stands (seconds; 0 = the scratch zone) |
| `view` | `iso` \| `front` \| `back` \| `top` \| `bottom` \| `left` \| `right` |  | `"iso"` |  | a standard view |
| `direction` | array of 3 numbers |  |  |  | [x, y, z] where the camera looks from (instead of view) |
| `up` | array of 3 numbers |  |  |  | [x, y, z] the screen's up (default: the view's own, Z up) |
| `of` | array of strings |  |  | at least 1 item(s) | fit these components (default: all that are shown) |
| `zoom` | number |  | `1.0` | > 0 | how close: 1 fits them, 2 twice as close |
| `perspective` | boolean |  | `false` |  | a perspective camera |

## Answer

A plain sentence, then JSON with: `storyboard`, `at`, `looks_from`, `up`, `looks_at`, `fits_box`, `camera`, `action`. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: at is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: turn to the front view, a little closer, by 5 seconds

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
{"tool": "anim_view", "args": {"at": 5, "view": "front", "zoom": 1.5}}
```

The answer:

```text
Done: a View action on 'Explode' from 0 to 5 s (action id 2); the storyboard is 5 s long.
{
 "storyboard": "Explode",
 "at": 5.0,
 "looks_from": [0.0, -1.0, 0.0],
 "up": [0.0, 0.0, 1.0],
 "looks_at": [0.0, 0.0, 20.0],
 "fits_box": [-30.0, -30.0, 0.0, 30.0, 30.0, 40.0],
 "camera": {
  "type": "Orthographic",
  "position": [0.0, -187.61663, 20.0],
  "orientation": [0.707106781187, 0.0, 0.0, 0.707106781187],
  "focal": 187.61663,
  "height": 68.7927645,
  "angle": 0.7853981633974483
 },
 "action": {"id": 2, "kind": "view", "what": "View", "start": 0.0, "end": 5.0}
}
```

## More argument examples

- the storyboard starts from the Home view:
  `{"at": 0, "view": "iso"}`
- turn to the front view by 3 s:
  `{"at": 3, "view": "front", "zoom": 1.5}`
- close in on the wheel by 6 s:
  `{"at": 6, "of": ["Wheel"], "zoom": 2}`

## See also

- Recipe: [an exploded-view video of an assembly (ANIMATION)](fission180://docs/recipes/exploded-view-video.md)
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
