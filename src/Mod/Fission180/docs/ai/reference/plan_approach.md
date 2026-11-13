# `plan_approach`: Plan the approach

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: (Fission 180's advice for AI models: the route, the questions, the cost). Category: Help. Read-only. Needs nothing.

## What it does

Plan a job before you build: give the person's request in their own words (and the body, mesh, component or drawing it is about). Reads the open design (meshes and their triangles, solids and their faces, timeline or not, sheet metal, components, studies, CAM setups, drawings, units) and answers the route (workspaces and tools in order, the cheapest that does the job, with argument hints), the questions to ask the person first (only those that change the result, at most five, each with a default), the slow steps with the seconds they take here, and what to avoid. Call it for any job bigger than one step (a mesh to a solid, make it editable, will it break, mill it, laser cut it, print it, draw it, animate it, a new part); not for one change you already know (call that tool). Read-only, well under a second.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `request` (required) | string |  |  |  | what the person asked for, in their words |
| `target` | string |  |  |  | the id or name of the body, mesh, component, drawing, study or setup it is about (default: what the person selected, else the design) |

## Answer

A plain sentence, then JSON with: `request`, `goals`, `workspaces`, `route`, `ask_first`, `cost`, `avoid`, `notes`, `about`, `next`, `design`. The example below shows a real one.

## Errors

- Called without arguments, the arguments are refused before anything runs: `Not done: request is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: the route, the questions and the cost for a mesh

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 60, 40], "name": "base"}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 10}},
  {"tool": "create_sketch", "args": {"plane": "XY", "offset": 10, "geometry": [{"circle": [30, 20, 4]}]}},
  {"tool": "hole", "args": {"sketch": "Sketch2", "diameter": 8, "through_all": true}},
  {"tool": "export", "args": {"format": "stl", "path": "/home/me/fission180/plate.stl"}},
  {"tool": "new_design", "args": {"name": "Relic"}},
  {"tool": "import_file", "args": {"path": "/home/me/fission180/plate.stl"}}
]
```

The call:

```json
{"tool": "plan_approach", "args": {"request": "make this mesh a solid", "target": "MeshBody"}}
```

The answer:

```text
Plan: turn the mesh into a solid (mesh 'plate': 208 triangles).
Route: check_design; under a second in all.
Ask the person first, in one message (2 questions, with the defaults): (1) Do you need an editable timeline (steps you can change later, many calls and much slower), or is a solid you can cut, fillet, measure and print enough? (2) Keep the original (hidden in the design) or replace it?
Next: check_design.
{
 "request": "make this mesh a solid",
 "goals": [{"id": "mesh_to_solid", "goal": "turn the mesh into a solid"}],
 "workspaces": [{"workspace": "design", "title": "DESIGN", "tab": "mesh"}],
 "route": [
  {
   "step": 1,
   "tool": "check_design",
   "why": "one valid, closed solid",
   "where": "INSPECT > Interference + the timeline's warnings",
   "seconds": 0.2,
   "for": "mesh_to_solid"
  }
 ],
 "ask_first": [
  {
   "id": "editable",
   "question": "Do you need an editable timeline (steps you can change later, many calls and much slower), or is a solid you can cut, fillet, measure and print enough?",
   "default": "a solid now; a timeline can still be made from it later"
  },
  {
   "id": "keep_original",
   "question": "Keep the original (hidden in the design) or replace it?",
   "default": "keep it, hidden"
  }
 ],
 "cost": {"seconds": 0.2, "about": "under a second", "slow_steps": []},
 "avoid": [
  "Never copy a mesh facet by facet (or triangle by triangle) into sketches and features: thousands of calls for a worse result. convert_mesh makes the solid in one call."
 ],
 "notes": [
  "Not in this Fission 180's tools (left out of the route): inspect_mesh, mesh_prepare, convert_mesh. The person can use the ribbon command instead; tell them which."
 ],
 "about": {"id": "MeshBody", "label": "plate", "kind": "mesh", "triangles": 208, "closed": true},
 "next": {"tool": "check_design", "args": {}},
 "design": {
  "open": true,
  "name": "Relic",
  "units": "mm",
  "workspace": null,
  "meshes": [{"id": "MeshBody", "label": "plate", "triangles": 208, "closed": true}],
  "solids": []
 }
}
```

## Example 2: a Static Stress study, planned

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
{"tool": "plan_approach", "args": {"request": "will this plate break if I stand on it?"}}
```

The answer:

```text
Plan: find out whether it is strong enough (Static Stress).
Route: create_study -> set_study_material -> add_constraint -> add_load -> precheck_study -> solve_study -> study_results -> study_probe (if needed); about 9 s in all.
Ask the person first, in one message (4 questions, with the defaults): (1) Which material? (2) Where is it held or bolted down (which faces or holes do not move)? (3) What load must it carry: how much (N, or a mass in kg), where and in which direction? (4) What safety factor is enough?
Next: create_study.
{
 "request": "will this plate break if I stand on it?",
 "goals": [{"id": "strength", "goal": "find out whether it is strong enough (Static Stress)"}],
 "workspaces": [{"workspace": "simulation", "title": "SIMULATION", "tab": null}],
 "route": [
  {
   "step": 1,
   "tool": "create_study",
   "why": "a Static Stress study of the design",
   "where": "SIMULATION > SETUP > STUDY > New Simulation Study (Static Stress)",
   "seconds": 0.3,
   "for": "strength"
  },
  {
   "step": 2,
   "tool": "set_study_material",
   "why": "the material the part is made of (its stiffness and yield strength set the safety factor)",
   "where": "SIMULATION > SETUP > MATERIALS > Study Materials",
   "seconds": 0.3,
   "for": "strength"
  },
  {
   "step": 3,
   "tool": "add_constraint",
   "why": "fixed where it is held or bolted",
   "args": {"kind": "fixed"},
   "where": "SIMULATION > SETUP > CONSTRAINTS > Structural Constraints",
   "seconds": 0.3,
   "for": "strength"
  },
  {
   "step": 4,
   "tool": "add_load",
   "why": "the force or pressure, where and in which direction",
   "where": "SIMULATION > SETUP > LOADS > Structural Loads",
   "seconds": 0.3,
   "for": "strength"
  },
  {
   "step": 5,
   "tool": "precheck_study",
   "why": "everything the solve needs, before the long part",
   "where": "SIMULATION > SETUP > SOLVE > Pre-check",
   "seconds": 0.3,
   "for": "strength"
  },
  {
   "step": 6,
   "tool": "solve_study",
   "why": "mesh and solve (CalculiX); the window waits meanwhile",
   "where": "SIMULATION > SETUP > SOLVE > Solve",
   "seconds": 6.8,
   "for": "strength"
  },
  {
   "step": 7,
   "tool": "study_results",
   "why": "safety factor, stress and displacement with where they are",
   "where": "SIMULATION > RESULTS (legend, Show Min / Max, Reaction Force, Results Details)",
   "seconds": 0.3,
   "for": "strength"
  },
  {
   "step": 8,
   "tool": "study_probe",
   "why": "the numbers at the places that matter (a hole's edge, a face)",
... (50 more lines)
```

## More argument examples

- Relic is a mesh:
  `{"request": "make this mesh a solid", "target": "Relic"}`
- a study:
  `{"request": "will this bracket break if I hang 20 kg on it?"}`

## See also

- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
