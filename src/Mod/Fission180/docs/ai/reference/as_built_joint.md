# `as_built_joint`: As-built joint

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: ASSEMBLE > As-built Joint. Category: Assemble. Changes the design (one undo step). Its undo step is named like "AI: As-built joint (revolute)". Needs an open design.

## What it does

Join two components WHERE THEY STAND NOW (nothing moves), Fusion's As-built Joint: for parts already modelled in place. For parts that must be brought together, use joint. type rigid | revolute | slider | cylindrical | pinslot | planar | ball; components: the two (a body or step in each works); position (every type but rigid): {component, face | edge | vertex, snap, point} on one of the two, the joint's origin and axis (a revolute turns about the axis of the round face or circle picked). Answers the joint's id and whether it holds; drive_joint moves it.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `type` | `rigid` \| `revolute` \| `slider` \| `cylindrical` \| `pinslot` \| `planar` \| `ball` |  | `"rigid"` |  |  |
| `components` (required) | array of 2 strings |  |  |  | the two components, as they stand |
| `position` | object |  |  |  | one side of a joint: a component and an element of it with a snap point |
| `position.component` (required) | string |  |  |  | the component or body this side is on (a step in it works) |
| `position.face` | object |  |  |  | the face clicked (on that component) (a face selector: filters type, normal, along, radius, at, all, count, any_of; see get_help topic selectors). Give count. |
| `position.edge` | object |  |  |  | the edge clicked (an edge selector: filters type, parallel, radius, on_faces, not_on_faces, at, all, count, any_of; see get_help topic selectors). Give count. |
| `position.vertex` | array of 3 numbers |  |  |  | the corner clicked |
| `position.snap` | `centre` \| `vertex` \| `midpoint` \| `circle` \| `point` \| `origin` |  |  |  | which snap point of the element (default: the nearest to point, else its centre) |
| `position.point` | array of 3 numbers | mm |  |  | where on the element (design coordinates) |
| `position.joint_origin` | string |  |  |  | a joint origin (joint_origin) instead of an element |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: components is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: the arm turns on the base about its round hole, where it stands

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "new_component", "args": {"label": "Base"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [-40, -40, 100, 40]}, {"circle": [80, 30, 2]}, {"circle": [80, -30, 2]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 10}},
  {"tool": "ground", "args": {"component": "Base"}},
  {"tool": "new_component", "args": {"label": "Arm"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 10, "geometry": [{"rect": [-5, -5, 50, 5]}, {"circle": [0, 0, 3]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch2", "distance": 5}},
  {"tool": "new_component", "args": {"label": "Stop"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 10, "geometry": [{"rect": [20, -20, 30, -10]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch3", "distance": 5}}
]
```

The call:

```json
{"tool": "as_built_joint", "args": {"type": "revolute", "components": ["Arm", "Base"], "position": {"component": "Arm", "edge": {"type": "circle", "radius": 3, "at": {"axis": "z", "value": "max"}, "count": 1}, "snap": "circle"}}}
```

The answer:

```text
Done: as-built revolute joint between Arm and Base, where they stand. Its id is 'Joint'. Its origin is at [0, 0, 15]. It holds. Next: drive_joint Joint to move it. Bodies now: Body001: 111749 mm3, 140 x 80 x 10 mm; Body002: 2608.63 mm3, 55 x 10 x 5 mm; Body003: 500 mm3, 10 x 10 x 5 mm.
```

## More argument examples

- the lid hinges on the box's round hinge pin, where it is:
  `{"type": "revolute", "components": ["Lid", "Box"], "position": {"component": "Box", "edge": {"type": "circle", "count": 1}, "snap": "circle"}}`
- lock the bracket to the base as it is:
  `{"components": ["Bracket", "Base"]}`

## See also

- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
