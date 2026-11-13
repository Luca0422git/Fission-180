# `appearance`: Appearance

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: SOLID > MODIFY > Appearance (A) / Texture Map Controls. Category: Modify. Changes the design (one undo step). Its undo step is named like "AI: Appearance". Needs an open design.

## What it does

Fusion's Appearance: colour a body, or some faces of it, without changing its material. body: a step of it (default: the current body); faces: a selector (only these faces); look: a library key (list_materials) or color [r, g, b] (0..1) with shininess (0..1) and transparency (0..1). When the body has faces with looks of their own, keep_face_looks must be given: true keeps them over the new look, false gives the whole body the new look (Fusion asks Keep / Remove). texture_map (Texture Map Controls, alone or with a look): how a textured look's pattern lies on the body: projection automatic | box | planar | cylindrical | spherical, axis x | y | z, offset_u / offset_v (mm), rotation (degrees), scale (%); reset: true puts it back.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `body` | string |  |  |  | a step of the body |
| `faces` | object |  |  |  | only these faces (a face selector: filters type, normal, along, radius, at, all, count, any_of; see get_help topic selectors). Give count. |
| `look` | string |  |  |  | an appearance key, e.g. plastic_red |
| `color` | array of 3 numbers | 0..1 |  |  | [r, g, b] 0..1 |
| `shininess` | number |  | `0.5` | >= 0, <= 1 |  |
| `transparency` | number |  | `0` | >= 0, <= 1 |  |
| `keep_face_looks` | boolean |  |  |  | faces that have looks of their own keep them (true) or take the new look too (false); needed when the body has such faces |
| `texture_map` | object |  |  |  | Texture Map Controls for the body's textured look |
| `texture_map.projection` | `automatic` \| `box` \| `planar` \| `cylindrical` \| `spherical` |  |  |  |  |
| `texture_map.axis` | `x` \| `y` \| `z` |  |  |  |  |
| `texture_map.offset_u` | number | mm |  |  | mm |
| `texture_map.offset_v` | number | mm |  |  | mm |
| `texture_map.rotation` | number | deg |  |  | degrees |
| `texture_map.scale` | number |  |  | > 0 | per cent of the look's own size |
| `texture_map.reset` | boolean |  |  |  | back to the look's own mapping |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: give look (a library key) or color ([r, g, b] 0..1), or texture_map alone.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: red plastic

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 60, 40], "name": "base"}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 10}}
]
```

The call:

```json
{"tool": "appearance", "args": {"body": "Extrude1", "look": "plastic_red"}}
```

The answer:

```text
Done: Body1 in Glossy plastic, red.
```

## More argument examples

- the current body in glossy red:
  `{"look": "plastic_red"}`
- just the top face blue:
  `{"faces": {"normal": [0, 0, 1], "count": 1}, "color": [0.1, 0.3, 0.8]}`

## See also

- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
