# `study_probe`: Probe results

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: SIMULATION > RESULTS > INSPECT > Surface Probes / Point Probes / Slice Plane. Category: Simulation. Read-only. Needs an open design.

## What it does

Read a solved study's results where you choose, as numbers (what Surface and Point Probes and a Slice Plane show a person): points [[x, y, z], ...] mm on or inside the part (each point's values, interpolated in its element, and how far it moves); on: picks (faces, edges, corners, whole bodies, like add_constraint's) with each one's minimum, maximum (with where) and mean; section: a plane through the part with the minimum and maximum on the cut. results: which (default safety, von_mises, displacement; also principal_1 / 3, the stress components, dx / dy / dz, strain and its components). Use it to check a spot the extremes of study_results do not name (the stress away from a fixed hole's edge, the deflection at a tip). Under 1 s on a mesh of 100,000 nodes. Changes nothing. study: the study's id or name (create_study answers it; default the newest study).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `study` | string |  |  |  | the study's id or name (default: the newest study) |
| `points` | array of arrays |  |  | at least 1 item(s), at most 50 item(s) | points on or in the part (mm) |
| `on` | array of objects |  |  | at least 1 item(s) | faces, edges, corners or bodies to read the results over |
| `section` | object |  |  |  | a plane: {"axis": "x" \| "y" \| "z"} or {"normal": [x, y, z]}, with "offset" (mm along it from the origin) or "point" [x, y, z]; neither: through the middle |
| `results` | array of strings |  |  | at least 1 item(s) | the results to read |

## Answer

A plain sentence, then JSON with: `study`, `id`, `out_of_date`, `units`, `points`, `on`. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Called without arguments, the arguments are refused before anything runs: `Not done: give points, on (picks) or section: where to read the results.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: the free end and the middle of the top, and the whole top face

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
{"tool": "study_probe", "args": {"points": [[60, 20, 10], [30, 20, 10]], "on": [{"face": {"normal": [0, 0, 1], "count": 1}}], "results": ["displacement", "von_mises"]}}
```

The answer:

```text
Probes of Study 1 - Static Stress: 2 of 2 points on the part, 1 pick; units displacement mm, von_mises MPa.
{
 "study": "Study 1 - Static Stress",
 "id": "SimStudy",
 "out_of_date": false,
 "units": {"displacement": "mm", "von_mises": "MPa"},
 "points": [
  {
   "at": [60.0, 20.0, 10.0],
   "inside": true,
   "values": {"displacement": 0.212, "von_mises": 13.553},
   "moved_mm": [0.026119, 6.7126e-07, -0.21039]
  },
  {
   "at": [30.0, 20.0, 10.0],
   "inside": true,
   "values": {"displacement": 0.069486, "von_mises": 87.301},
   "moved_mm": [0.019185, -2.6795e-06, -0.066776]
  }
 ],
 "on": [
  {
   "pick": "Body1.Face6",
   "nodes": 307,
   "values": {
    "displacement": {
     "min": 0.0,
     "min_at": [0.0, 0.0, 10.0],
     "max": 0.212,
     "max_at": [60.0, 20.0, 10.0],
     "mean": 0.083696
    },
    "von_mises": {
     "min": 4.865,
     "min_at": [60.0, 0.0, 10.0],
     "max": 163.21,
     "max_at": [6.121, 26.131, 10.0],
     "mean": 84.876
    }
   }
  }
 ]
}
```

## More argument examples

- the deflection at the free end's top and the stress half way along:
  `{"points": [[100, 10, 10], [50, 10, 5]], "results": ["displacement", "von_mises"]}`
- safety factor, stress and displacement over the top face:
  `{"on": [{"face": {"normal": [0, 0, 1], "count": 1}}]}`
- the numbers on a cut at x = 25 mm:
  `{"section": {"axis": "x", "offset": 25}}`

## See also

- Recipe: [is this bracket strong enough? (Static Stress)](fission180://docs/recipes/static-stress.md)
- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
