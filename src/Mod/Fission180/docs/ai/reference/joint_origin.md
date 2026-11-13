# `joint_origin`: Joint origin

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: SOLID > CREATE > Joint Origin (and ASSEMBLE > Joint Origin). Category: Assemble. Changes the design (one undo step). Its undo step is named like "AI: Joint origin". Needs an open design.

## What it does

Put a joint origin on a component (Fusion's Joint Origin): a saved snap point with axes that moves with its geometry, for a joint where no edge or face gives the right point. at: {component, face | edge | vertex, snap, point} as in joint; offset [x, y, z] (mm) and angle (degrees about its Z) move it from the snap; flip turns its Z over. Answers its id and where it is (design coordinates).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `at` (required) | object |  |  |  | one side of a joint: a component and an element of it with a snap point |
| `at.component` (required) | string |  |  |  | the component or body this side is on (a step in it works) |
| `at.face` | object |  |  |  | the face clicked (on that component) (a face selector: filters type, normal, along, radius, at, all, count, any_of; see get_help topic selectors). Give count. |
| `at.edge` | object |  |  |  | the edge clicked (an edge selector: filters type, parallel, radius, on_faces, not_on_faces, at, all, count, any_of; see get_help topic selectors). Give count. |
| `at.vertex` | array of 3 numbers |  |  |  | the corner clicked |
| `at.snap` | `centre` \| `vertex` \| `midpoint` \| `circle` \| `point` \| `origin` |  |  |  | which snap point of the element (default: the nearest to point, else its centre) |
| `at.point` | array of 3 numbers | mm |  |  | where on the element (design coordinates) |
| `at.joint_origin` | string |  |  |  | a joint origin (joint_origin) instead of an element |
| `offset` | array of 3 numbers | mm |  |  | [x, y, z] moved from the snap point (mm) |
| `angle` | number | deg | `0` |  | turned about its Z (degrees) |
| `flip` | boolean |  | `false` |  | its Z the other way |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: at is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: a joint origin 5 mm above the middle of the stop's top face

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
{"tool": "joint_origin", "args": {"at": {"component": "Stop", "face": {"normal": [0, 0, 1], "at": {"axis": "z", "value": "max"}, "count": 1}}, "offset": [0, 0, 5]}}
```

The answer:

```text
Done: joint origin 'Joint Origin 1' on Stop at [25, -15, 20], its Z along [0, 0, 1]. Its id is 'JointOrigin'; use it in joint or as_built_joint as {"component": "Component002", "joint_origin": "JointOrigin"}. Bodies now: Body001: 111749 mm3, 140 x 80 x 10 mm; Body002: 2608.63 mm3, 55 x 10 x 5 mm; Body003: 500 mm3, 10 x 10 x 5 mm.
```

## More argument examples

- a joint origin 5 mm above the centre of the base's top face:
  `{"at": {"component": "Base", "face": {"normal": [0, 0, 1], "count": 1}}, "offset": [0, 0, 5]}`

## See also

- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
