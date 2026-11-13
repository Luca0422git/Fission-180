# `edit_study_item`: Edit constraint or load

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: SIMULATION > browser > constraint / load / mesh control > Edit / Suppress / Delete. Category: Simulation. Changes the design (one undo step). Its undo step is named like "AI: Edit Force 1". Needs an open design.

## What it does

Change a constraint, load or local mesh control of a study (what its browser row's Edit, Suppress and Delete do), one undo step. item: its id or label (study_setup lists them). on: picks again (they replace the old ones); magnitude, direction, vector, point, flip, per_entity (loads), x / y / z, radial / axial / tangential (constraints), size (mesh controls): only what changes, with add_constraint's and add_load's meanings and units; suppressed true leaves it out of the solve (false brings it back); label; delete true removes it. A study solved before shows out of date: solve it again. on: where it acts, a list of picks: {"face": selector}, {"edge": selector} or {"vertex": {"at": ...}} on a body, with "of": the body (or a step in it; default the active body). Every face / edge / corner a selector picks is used (give count).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `study` | string |  |  |  | the study the item is in (default: any) |
| `item` (required) | string |  |  |  | the constraint's, load's or mesh control's id or label |
| `on` | array of objects |  |  | at least 1 item(s) | where it acts now |
| `magnitude` | number | mm |  |  | a load's size: N, MPa or N mm |
| `direction` | `normal` \| `vector` |  |  |  | a force / moment's direction |
| `vector` | array of 3 numbers |  |  |  | a load's direction [x, y, z] |
| `point` | array of 3 numbers | mm |  |  | a remote force's point (mm) |
| `flip` | boolean |  |  |  | reverse a load |
| `per_entity` | boolean |  |  |  | each pick gets the whole force / moment |
| `x` | boolean or number or null |  |  |  | fixed: held; displacement: mm |
| `y` | boolean or number or null |  |  |  | fixed: held; displacement: mm |
| `z` | boolean or number or null |  |  |  | fixed: held; displacement: mm |
| `radial` | boolean |  |  |  | pin: keeps the hole's size and place |
| `axial` | boolean |  |  |  | pin: no sliding along it |
| `tangential` | boolean |  |  |  | pin: no turning about it |
| `size` | number | mm |  | > 0 | a local mesh control's element size (mm) |
| `suppressed` | boolean |  |  |  | leave it out of the solve (true) or bring it back |
| `label` | string |  |  |  | its new name |
| `delete` | boolean |  | `false` |  | delete it |

## Answer

A plain sentence, then JSON with: `id`, `label`, `category`, `kind`, `what`, `on`, `options`, `suppressed`. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: item is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: half the force

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 60, 40], "name": "base"}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 10}},
  {"tool": "create_study", "args": {}},
  {"tool": "add_constraint", "args": {"kind": "fixed", "on": [{"face": {"normal": [-1, 0, 0], "count": 1}}]}},
  {"tool": "add_load", "args": {"kind": "force", "on": [{"face": {"normal": [1, 0, 0], "count": 1}}], "magnitude": 2000, "direction": "vector", "vector": [0, 0, -1]}}
]
```

The call:

```json
{"tool": "edit_study_item", "args": {"item": "Force 1", "magnitude": 1000}}
```

The answer:

```text
Done: Force 1 is now Force 1000 N.
{
 "id": "SimItem001",
 "label": "Force 1",
 "category": "load",
 "kind": "force",
 "what": "Force 1000 N",
 "on": "Body1: 1 face",
 "options": {
  "direction": "vector",
  "flip": false,
  "magnitude": 1000.0,
  "per_entity": false,
  "vector": [0.0, 0.0, -1.0]
 },
 "suppressed": false
}
```

## More argument examples

- the force halved to 500 N:
  `{"item": "Force 1", "magnitude": 500}`
- solve without that constraint:
  `{"item": "Fixed 1", "suppressed": true}`
- delete the pressure:
  `{"item": "Pressure 1", "delete": true}`

## See also

- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
