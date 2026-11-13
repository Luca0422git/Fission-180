# `base_feature`: Base feature

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: SOLID > CREATE > Create Base Feature / Finish Base Feature. Category: Timeline (history). Changes the design (one undo step). Its undo step is named like "AI: Create base feature". Needs an open design.

## What it does

Fusion's base feature: start: the bodies made next (new_body first, or a tool with operation new_body) are NOT recorded step by step; finish: each becomes one base feature in the timeline (no parameters to edit later). For a quick direct-modelling stretch in a parametric design. For the whole design without history use capture_design_history.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `action` (required) | `start` \| `finish` |  |  |  |  |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: action is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: direct edits from here on

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
{"tool": "base_feature", "args": {"action": "start"}}
```

The answer:

```text
Done: a base feature is open. What the next tools make goes into one base feature per body, not step by step; base_feature finish ends it.
```

## More argument examples

- direct edits from here, one step per body:
  `{"action": "start"}`

## See also

- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
