# `study_report`: Results report

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: SIMULATION > RESULTS > RESULT TOOLS > Report. Category: Simulation. Writes files. Needs an open design.

## What it does

Write a solved study's report as one HTML file (Fusion's Report): the design, the study's materials, constraints, loads, contacts and mesh, every result's minimum and maximum with where, per body, the reaction forces and the verdict against the safety factor target (target, default 3; upper, default 6: above it the part is stronger than needed). path: a full path (.html added; a folder: named after the design and the study). title, author and the cover's summary / project / approver / revision; more_studies: more solved studies in the same report. pictures true (needs the window): the results are shown in the SIMULATION workspace and pictured, as a person's Report does. A file that exists is not replaced unless the person agrees. study: the study's id or name (create_study answers it; default the newest study).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `study` | string |  |  |  | the study's id or name (default: the newest study) |
| `path` (required) | string |  |  |  | the HTML file to write, or its folder (a full path) |
| `title` | string |  |  |  | the report's title (default: the study's name) |
| `author` | string |  |  |  | who made it |
| `summary` | string |  |  |  | a paragraph for the cover |
| `project` | string |  |  |  | the project |
| `approver` | string |  |  |  | who approves it |
| `revision` | string |  |  |  | its revision |
| `target` | number |  | `3.0` | > 0 | the safety factor the part should reach |
| `upper` | number |  | `6.0` | > 0 | above this the part is stronger than needed |
| `more_studies` | array of strings |  |  | at least 1 item(s) | more solved studies in the same report |
| `pictures` | boolean |  | `false` |  | pictures of the results (needs the window) |

## Answer

A plain sentence. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: path is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: the study's report, judged against a safety factor of 2

Starting from this design (made by these calls):

```json
[
  {"tool": "new_design", "args": {"name": "Example"}},
  {"tool": "create_sketch", "args": {"plane": "XY", "geometry": [{"rect": [0, 0, 60, 40], "name": "base"}]}},
  {"tool": "extrude", "args": {"profile": "Sketch1", "distance": 10}},
  {"tool": "create_study", "args": {}},
  {"tool": "add_constraint", "args": {"kind": "fixed", "on": [{"face": {"normal": [-1, 0, 0], "count": 1}}]}},
  {"tool": "add_load", "args": {"kind": "force", "on": [{"face": {"normal": [1, 0, 0], "count": 1}}], "magnitude": 2000, "direction": "vector", "vector": [0, 0, -1]}},
  {"tool": "solve_study", "args": {}}
]
```

The call:

```json
{"tool": "study_report", "args": {"path": "/home/me/fission180/plate report.html", "title": "Plate under 2 kN", "target": 2}}
```

The answer:

```text
Written /home/me/fission180/plate report.html (5 kB): the report of Study 1 - Static Stress: setup (materials, constraints, loads, mesh), every result's minimum and maximum with where, per body, reaction forces, and the verdict against a safety factor target of 2 to 6.
```

## More argument examples

- the newest study's report:
  `{"path": "~/reports/bracket.html", "target": 2}`

## See also

- Recipe: [is this bracket strong enough? (Static Stress)](fission180://docs/recipes/static-stress.md)
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
