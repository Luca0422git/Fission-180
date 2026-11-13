# `show_study_results`: Show results

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: SIMULATION > RESULTS (DEFORMATION, DISPLAY, Legend Min/Max, Slice Plane, Iso-surface, Animate, Compare, Finish Results). Category: Simulation. Read-only. Needs an open design, the Fission 180 window.

## What it does

Show a solved study's results in the window as the RESULTS tab does, so the person (and render / screenshot) sees them; the part is fitted when this opens them. result: the legend's result; deformation (adjusted: Fusion's default, the largest movement drawn at 5 % of the model); mesh, undeformed_model (a ghost), loads, min_max: true / false; legend_range [min, max] or null (not for safety); slice {axis | normal, offset | point, flip, style clip | slice} or null; iso_surface: a value, true (half way) or null; animate true / false; compare: studies side by side on one scale; view: a standard view, fitted; finish true: Finish Results. Needs the window and refuses while the person has a dialog open; study_probe has the numbers without it. study: the study's id or name (create_study answers it; default the newest study).

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `study` | string |  |  |  | the study's id or name (default: the newest study) |
| `result` | `safety` \| `von_mises` \| `principal_1` \| `principal_3` \| `sxx` \| `syy` \| `szz` \| `sxy` \| `syz` \| `szx` \| `displacement` \| `dx` \| `dy` \| `dz` \| `strain` \| `strain_1` \| `strain_3` \| `exx` \| `eyy` \| `ezz` |  |  |  | the result the legend shows |
| `deformation` | `undeformed` \| `actual` \| `adjusted_half` \| `adjusted` \| `adjusted_2` \| `adjusted_5` |  |  |  | how much the bend is drawn |
| `mesh` | boolean |  |  |  | the element edges drawn |
| `undeformed_model` | boolean |  |  |  | the unloaded part drawn as a ghost |
| `loads` | boolean |  |  |  | the loads and constraints drawn |
| `min_max` | boolean |  |  |  | the min / max tags |
| `legend_range` | array or null |  |  |  | [min, max] of the colours in the result's unit, null: its own |
| `slice` | object or null |  |  |  | the slice plane (see the description), null: none |
| `iso_surface` | number or boolean or null |  |  |  | the iso-surface's value (true: half way, null / false: none) |
| `animate` | boolean |  |  |  | play the bending |
| `compare` | array of strings |  |  | at least 1 item(s) | other studies to show side by side |
| `view` | `iso` \| `front` \| `back` \| `top` \| `bottom` \| `left` \| `right` |  |  |  | look from this standard view, the part fitted |
| `finish` | boolean |  | `false` |  | Finish Results: back to SETUP |

## Answer

A plain sentence, then JSON with: `study`, `result`, `unit`, `legend`, `deformation`, `drawn_times_true_size`, `mesh`, `undeformed_model`, `loads`, `min_max`, `slice`, `iso_surface`, `animate`. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Without the Fission 180 window: `This needs the Fission 180 window, and Fission 180 is running without one (headless / command line).`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: the stress in the window, the bend drawn twice as big

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
{"tool": "show_study_results", "args": {"result": "von_mises", "deformation": "adjusted_2", "min_max": true}}
```

The answer:

```text
Done: Study 1 - Static Stress shows Stress: Von Mises (MPa) in the window, Adjusted x 2. render or screenshot shows it; study_probe reads the numbers.
{
 "study": "Study 1 - Static Stress",
 "result": "von_mises",
 "unit": "MPa",
 "legend": [0.87046, 163.21],
 "deformation": "adjusted_2",
 "drawn_times_true_size": 34.338,
 "mesh": false,
 "undeformed_model": false,
 "loads": false,
 "min_max": true,
 "slice": null,
 "iso_surface": null,
 "animate": false
}
```

## More argument examples

- the stress, the bend drawn twice as big, with min / max tags:
  `{"result": "von_mises", "deformation": "adjusted_2", "min_max": true}`
- cut through the middle across Y:
  `{"slice": {"axis": "y"}}`
- back to the SETUP tab:
  `{"finish": true}`

## See also

- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
