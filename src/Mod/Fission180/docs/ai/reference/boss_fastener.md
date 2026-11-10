# `boss_fastener`: Boss fastener

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: PLASTIC > CREATE > Boss > Fastener: Create Component. Category: Plastic. Changes the design (one undo step). Its undo step is named like "AI: Boss fastener". Needs a solid body.
It builds the design step(s) `sf_boss_fastener` (the golden models' step language).

## What it does

Add the screws to an existing boss (the Boss dialog's Fastener > Create Component): a simple screw at every boss point in a component of its own, following the boss when it changes. boss: the boss step; head pan | round | flat | hex | hex_washer; length (mm, 0 = to the pilot hole's bottom).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `boss` (required) | string |  |  |  | the boss step (either side) |
| `head` | `pan` \| `round` \| `flat` \| `hex` \| `hex_washer` |  | `"pan"` |  |  |
| `length` | number | mm | `0` | >= 0 | the screw's length (mm), 0 = auto |
| `name` | string |  |  |  | a descriptive name for the screws' new body, e.g. "Base plate" (required in effect: unnamed bodies and sketches must be renamed before the next change) |

## Answer

On success: `Done: <undo title>. Its id is '<id>'. Bodies now: <each solid body's volume in mm3 and size in mm>.` (some steps report no id); then `These steps now fail: ...` when the change broke later steps, and `Warning: no solid changed ...` when it changed no solid at all. On failure nothing changes and the answer is `Not done (<undo title>): <the reason>`.

## Errors

- Without a solid body: `The design has no solid body yet: make one first (create_sketch + extrude, or primitive).`
- Called without arguments, the arguments are refused before anything runs: `Not done: boss is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When Fission 180 cannot build the step (a selector that picks another number of elements than `count`, a size that does not fit, an id that does not exist), the answer is `Not done (<undo title>): <reason>` and nothing changes; [troubleshooting](fission180://docs/troubleshooting.md) lists the usual causes.

## Example 1: pan head screws in the bosses

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 60, 40]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 20}},
  {"tool": "shell", "args": {"faces": {"normal": [0, 0, 1], "count": 1}, "thickness": 2}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 20, "geometry": [{"rect": [0, 0, 60, 40]}]}},
  {"tool": "extrude", "args": {"profile": "Sketch2", "distance": 10, "operation": "new_body"}},
  {"tool": "shell", "args": {"faces": {"normal": [0, 0, -1], "count": 1}, "thickness": 2}},
  {"tool": "boss", "args": {"points": [[10, 10], [50, 30]], "plane": "XY", "offset": 20}}
]
```

The call:

```json
{"tool": "boss_fastener", "args": {"boss": "Boss", "head": "pan"}}
```

The answer:

```text
Done: AI: Boss fastener. Its id is 'Fastener' (shown as 'Fastener001'). Bodies now: Body1: 13345.6 mm3, 60 x 40 x 20.85 mm; Body2: 8531.15 mm3, 60 x 40 x 10 mm; Screw: 392.306 mm3, 46 x 26 x 22.35 mm.
```

## More argument examples

- pan head screws in Boss1's holes:
  `{"boss": "Boss1", "head": "pan"}`

## See also

- Golden models built with its steps (read one with docs_read golden/<id>): `plastic_boss_fastener`
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
