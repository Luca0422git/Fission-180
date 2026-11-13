# `study_setup`: Study setup

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: SIMULATION > SETUP > Load Case Attributes / Contact Manager / Automatic Contacts / DOF View. Category: Simulation. Read-only. Needs an open design.

## What it does

Read a study's whole setup (Fusion's Load Case Attributes, Contact Manager and DOF View): every constraint, load and mesh control (id, kind, values, what it is on, status ok / suppressed / lost its faces), each body's study material, gravity, the bonded contacts (bodies closer than the contact tolerance are glued), bodies that overlap or touch only along an edge or at a corner, how each piece could still move (free_motions: empty when everything is held), and the last mesh. contact_tolerance (mm): the contacts as Automatic Contacts' Generate would find them with that tolerance, with their gaps (study_settings contact_tolerance keeps it). Changes nothing. study: the study's id or name (create_study answers it; default the newest study).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `study` | string |  |  |  | the study's id or name (default: the newest study) |
| `contact_tolerance` | number | mm |  | >= 0, <= 10 | try another contact tolerance (mm) |

## Answer

A plain sentence, then JSON with: `study`, `id`, `solved`, `out_of_date`, `bodies`, `materials`, `items`, `gravity`, `contact_tolerance_mm`, `contacts`, `overlapping`, `touching_only_at_edge_or_corner`, `free_motions`, `mesh`. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: everything the study holds

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
{"tool": "study_setup", "args": {}}
```

The answer:

```text
Study 1 - Static Stress: 2 constraints and loads, 0 bonded contacts, every body is held.
{
 "study": "Study 1 - Static Stress",
 "id": "SimStudy",
 "solved": false,
 "out_of_date": false,
 "bodies": ["Body1"],
 "materials": [
  {
   "material": "Steel-Generic",
   "from": "the body",
   "youngs_mpa": 200000.0,
   "poisson": 0.30000001192092896,
   "density": 7900.0,
   "yield_mpa": 207.0,
   "ultimate_mpa": 345.0,
   "filled_in": ["yield_mpa", "ultimate_mpa"],
   "body": "Body1",
   "id": "Body"
  }
 ],
 "items": [
  {
   "id": "SimItem",
   "label": "Fixed 1",
   "category": "constraint",
   "kind": "fixed",
   "what": "Fixed",
   "on": "Body1: 1 face",
   "options": {"x": true, "y": true, "z": true},
   "suppressed": false,
   "status": "ok"
  },
  {
   "id": "SimItem001",
   "label": "Force 1",
   "category": "load",
   "kind": "force",
   "what": "Force 2000 N",
   "on": "Body1: 1 face",
   "options": {
    "direction": "vector",
    "flip": false,
    "magnitude": 2000.0,
    "per_entity": false,
    "vector": [0.0, 0.0, -1.0]
   },
   "suppressed": false,
   "status": "ok"
  }
 ],
 "gravity": {"on": false, "direction": [0.0, 0.0, -1.0]},
 "contact_tolerance_mm": 0.1,
 "contacts": [],
 "overlapping": [],
 "touching_only_at_edge_or_corner": [],
 "free_motions": [],
 "mesh": {}
}
```

## More argument examples

- everything the newest study is set up with:
  `{}`
- which bodies a 0.5 mm tolerance would glue:
  `{"contact_tolerance": 0.5}`

## See also

- Recipe: [is this bracket strong enough? (Static Stress)](fission180://docs/recipes/static-stress.md)
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
