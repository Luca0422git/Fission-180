# `anim_storyboard`: Storyboard

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: ANIMATION > STORYBOARD > New Storyboard (and a storyboard tab's right-click menu). Category: Animation. Changes the design (one undo step). Its undo step is named like "AI: New storyboard". Needs an open design.
It builds the design step(s) `anim_storyboard`, `anim_reverse` (the golden models' step language).

## What it does

Make or manage a storyboard, one animation of the design (Fusion's storyboard tabs under the ANIMATION TIMELINE). action: new (default; name: its name, default Storyboard1, Storyboard2...; clean true: components where the design has them, false: Start from end of previous, they start as the active storyboard ends) | duplicate | reverse (it plays backwards from now on: an explode becomes an assemble) | rename (name: the new name) | delete | activate (the storyboard later calls use by default). storyboard: which one (default: the active one). Answers the storyboards and the active one. An animation moves a display copy of the design's components: the design itself never changes (a design of plain bodies has nothing to animate: components_from_bodies first).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `action` | `new` \| `duplicate` \| `reverse` \| `rename` \| `delete` \| `activate` |  | `"new"` |  | what to do |
| `storyboard` | string |  |  |  | the storyboard's name (default: the active one) |
| `name` | string |  |  |  | new: its name; rename: the new name |
| `clean` | boolean |  |  |  | new: start as the design is (true) or as the previous ends |

## Answer

A plain sentence, then JSON with: `storyboards`, `active`. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: a new storyboard

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
{"tool": "anim_storyboard", "args": {"name": "Explode"}}
```

The answer:

```text
Done: new storyboard 'Explode' (clean); it is the active one.
{
 "storyboards": [{"name": "Explode", "length_s": 0.0, "actions": {}, "components": []}],
 "active": "Explode"
}
```

## More argument examples

- a new, clean storyboard:
  `{"name": "Explode"}`
- a copy of it:
  `{"action": "duplicate", "storyboard": "Explode"}`
- the copy plays backwards:
  `{"action": "reverse", "storyboard": "Explode (copy)"}`

## See also

- Recipe: [an assembly drawing with an exploded view, balloons and a parts list](fission180://docs/recipes/assembly-drawing.md)
- Golden models built with its steps (read one with docs_read golden/<id>): `anim_auto_explode_one_level`, `anim_sequential_transform_reverse`
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
