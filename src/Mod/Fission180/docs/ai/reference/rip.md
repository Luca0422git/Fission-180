# `rip`: Rip

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: SHEET METAL > MODIFY > Rip. Category: Sheet metal. Changes the design (one undo step). Its undo step is named like "AI: Rip (face)". Needs a solid body.
It builds the design step(s) `sf_rip` (the golden models' step language).

## What it does

Fusion's Rip: open a closed or overlapping sheet (a tube, a box) of the active sheet metal body so it can be laid flat. type face: face (one face: a bend's round face or a corner face) is cut away through the thickness; edge (default): a gap gap mm wide along edge (a sharp edge where two walls meet); points: a straight slot gap mm wide between two points on one face, each offset1 / offset2 mm along an edge (point1 / point2) from its start. gap: mm (default 1).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `type` | `face` \| `edge` \| `points` |  | `"edge"` |  |  |
| `face` | object |  |  |  | type face: the face to cut away (one) (a face selector: filters type, normal, along, radius, at, all, count, any_of; see get_help topic selectors). Give count. |
| `edge` | object |  |  |  | type edge: the edge to rip along (one) (an edge selector: filters type, parallel, radius, on_faces, not_on_faces, at, all, count, any_of; see get_help topic selectors). Give count. |
| `point1` | object |  |  |  | type points: the edge the first point is on (one) (an edge selector: filters type, parallel, radius, on_faces, not_on_faces, at, all, count, any_of; see get_help topic selectors). Give count. |
| `point2` | object |  |  |  | type points: the edge the second point is on (one) (an edge selector: filters type, parallel, radius, on_faces, not_on_faces, at, all, count, any_of; see get_help topic selectors). Give count. |
| `offset1` | number | mm | `0` | >= 0 | mm along point1's edge from its start |
| `offset2` | number | mm | `0` | >= 0 | mm along point2's edge from its start |
| `gap` | number | mm | `1` | > 0 | the rip's width (mm) |

## Answer

On success: `Done: <undo title>. Its id is '<id>'. Bodies now: <each solid body's volume in mm3 and size in mm>.` (some steps report no id); then `These steps now fail: ...` when the change broke later steps, and `Warning: no solid changed ...` when it changed no solid at all. On failure nothing changes and the answer is `Not done (<undo title>): <the reason>`.

## Errors

- Without a solid body: `The design has no solid body yet: make one first (create_sketch + extrude, or primitive).`
- Called without arguments, the arguments are refused before anything runs: `Not done: type edge needs edge.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When Fission 180 cannot build the step (a selector that picks another number of elements than `count`, a size that does not fit, an id that does not exist), the answer is `Not done (<undo title>): <reason>` and nothing changes; [troubleshooting](fission180://docs/troubleshooting.md) lists the usual causes.

## Example 1: cut one round corner out of a closed tube so it can be laid flat

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 40, 30]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 20}},
  {"tool": "fillet", "args": {"edges": {"type": "line", "parallel": [0, 0, 1], "count": 4}, "radius": 2}},
  {"tool": "shell", "args": {"faces": {"any_of": [{"type": "plane", "normal": [0, 0, 1], "count": 1}, {"type": "plane", "normal": [0, 0, -1], "count": 1}]}, "thickness": 1}},
  {"tool": "convert_to_sheet_metal", "args": {"face": {"type": "plane", "normal": [0, -1, 0], "at": {"axis": "y", "value": "min"}, "count": 1}}}
]
```

The call:

```json
{"tool": "rip", "args": {"type": "face", "face": {"type": "cylinder", "radius": 2, "at": [{"axis": "x", "value": "max"}, {"axis": "y", "value": "max"}], "count": 1}}}
```

The answer:

```text
Done: AI: Rip (face). Its id is 'Rip1'. Bodies now: Body1: 2621.37 mm3, 40 x 30 x 20 mm.
```

## More argument examples

- cut one round corner out of a converted tube:
  `{"type": "face", "face": {"type": "cylinder", "radius": 2, "at": [{"axis": "x", "value": "max"}, {"axis": "y", "value": "max"}], "count": 1}}`

## See also

- Golden models built with its steps (read one with docs_read golden/<id>): `sm_flat_rip_points`, `sm_flat_rip_tube`
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
