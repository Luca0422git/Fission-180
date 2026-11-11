# `anim_callout`: Create callout

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: ANIMATION > ANNOTATION > Create Callout. Category: Animation. Changes the design (one undo step). Its undo step is named like "AI: Create Callout". Needs an open design.

## What it does

Pin a text to a point of the animation (Fusion's Create Callout): shown from `at` seconds on. point: [x, y, z] in design coordinates (mm), as the components stand at that time; of: the component it is on (the callout then moves with it). storyboard: its name (default: the active storyboard; a design without one gets "Storyboard1"). An animation moves a display copy of the design's components: the design itself never changes (a design of plain bodies has nothing to animate: components_from_bodies first).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `storyboard` | string |  |  |  | the storyboard's name (default: the active one) |
| `at` (required) | number | mm |  | >= 0 | where the playhead stands (seconds; 0 = the scratch zone) |
| `text` (required) | string |  |  |  | the callout's text |
| `point` (required) | array of 3 numbers | mm |  |  | [x, y, z] where it points (design coordinates, mm) |
| `of` | string |  |  |  | the component it follows (default: it stays in place) |

## Answer

A plain sentence, then JSON with: `storyboard`, `action`. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: at is missing; text is missing; point is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: a note on the lifted wheel

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
{"tool": "anim_callout", "args": {"at": 3, "text": "Wheel", "point": [0, 0, 40], "of": "Wheel"}}
```

The answer:

```text
Done: callout 'Wheel' on 'Explode' from 3 s on, following Wheel (action id 2).
{
 "storyboard": "Explode",
 "action": {
  "id": 2,
  "kind": "callout",
  "what": "Callout",
  "component": "Wheel",
  "component_id": "Component001",
  "start": 3.0,
  "end": null,
  "text": "Wheel",
  "point_on_component": [0.0, 0.0, 25.0]
 }
}
```

## More argument examples

- a note on the wheel from 2 s on:
  `{"at": 2, "text": "M4 x 12 screw", "point": [0, 0, 55], "of": "Wheel"}`

## See also

- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
