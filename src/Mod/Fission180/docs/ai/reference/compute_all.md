# `compute_all`: Compute all

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: SOLID > MODIFY > Compute All (Ctrl+B). Category: Timeline (history). Changes the design (one undo step). Its undo step is named like "AI: Compute all". Needs an open design.

## What it does

Compute every parameter and step of the design again from the start (Fusion's Compute All): after a design was opened with stale steps, or to find the steps that fail. Answers how many steps, how long it took, and each step that failed or warns with the reason (fix them with get_step / edit_step). Takes about as long as opening the design (seconds; a minute for a big assembly).

## Arguments

No arguments.

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: everything computed again

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 60, 40], "name": "base"}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 10}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 10, "geometry": [{"circle": [30, 20, 4]}]}},
  {"tool": "hole", "args": {"sketch": "Sketch2", "diameter": 8, "through_all": true}}
]
```

The call:

```json
{"tool": "compute_all", "args": {}}
```

The answer:

```text
Compute All: 4 steps in 0.0 s, all computed. Bodies now: Body1: 23497.3 mm3, 60 x 40 x 10 mm.
```

## More argument examples

- recompute everything and list the failing steps:
  `{}`

## See also

- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
