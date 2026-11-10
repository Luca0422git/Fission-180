# `unfold`: Unfold

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: SHEET METAL > MODIFY > Unfold. Category: Sheet metal. Changes the design (one undo step). Its undo step is named like "AI: Unfold". Needs a solid body.
It builds the design step(s) `sf_unfold` (the golden models' step language).

## What it does

Fusion's Unfold: lay some or all bends of the active sheet metal body flat in the timeline (the stationary face stays put), to cut holes and slots across the bends while they are flat; refold folds them back carrying the cuts. face: the stationary face (a top or bottom face of a wall); bends: a face selector of the bends' round faces to lay flat, or all: true.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `face` (required) | object |  |  |  | the stationary face (one) (a face selector: filters type, normal, along, radius, at, all, count, any_of; see get_help topic selectors). Give count. |
| `bends` | object |  |  |  | the bends' round faces (a face selector: filters type, normal, along, radius, at, all, count, any_of; see get_help topic selectors). Give count. |
| `all` | boolean |  | `false` |  | every bend |

## Answer

On success: `Done: <undo title>. Its id is '<id>'. Bodies now: <each solid body's volume in mm3 and size in mm>.` (some steps report no id); then `These steps now fail: ...` when the change broke later steps, and `Warning: no solid changed ...` when it changed no solid at all. On failure nothing changes and the answer is `Not done (<undo title>): <the reason>`.

## Errors

- Without a solid body: `The design has no solid body yet: make one first (create_sketch + extrude, or primitive).`
- Called without arguments, the arguments are refused before anything runs: `Not done: face is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When Fission 180 cannot build the step (a selector that picks another number of elements than `count`, a size that does not fit, an id that does not exist), the answer is `Not done (<undo title>): <reason>` and nothing changes; [troubleshooting](fission180://docs/troubleshooting.md) lists the usual causes.

## Example 1: lay both bends of the channel flat, its floor staying where it is

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XZ", "geometry": [{"polyline": [[0, 30], [0, 0], [60, 0], [60, 30], [59, 30], [59, 1], [1, 1], [1, 30]]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 20}},
  {"tool": "fillet", "args": {"edges": {"type": "line", "parallel": [0, 1, 0], "at": {"axis": "z", "value": 0}, "count": 2}, "radius": 2}},
  {"tool": "fillet", "args": {"edges": {"type": "line", "parallel": [0, 1, 0], "at": {"axis": "z", "value": 1}, "count": 2}, "radius": 1}},
  {"tool": "convert_to_sheet_metal", "args": {"face": {"type": "plane", "normal": [0, 0, 1], "at": {"axis": "z", "value": "min"}, "count": 1}}}
]
```

The call:

```json
{"tool": "unfold", "args": {"face": {"type": "plane", "normal": [0, 0, 1], "at": {"axis": "z", "value": "min"}, "count": 1}, "all": true}}
```

The answer:

```text
Done: AI: Unfold. Its id is 'Unfold1'. Bodies now: Body1: 2330.48 mm3, 116.5 x 20 x 1 mm.
```

## More argument examples

- lay every bend flat, the floor staying where it is:
  `{"face": {"type": "plane", "normal": [0, 0, 1], "at": {"axis": "z", "value": "min"}, "count": 1}, "all": true}`

## See also

- Golden models built with its steps (read one with docs_read golden/<id>): `sm_flat_unfold_cut_refold`, `sm_flat_unfold_one_bend`
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
