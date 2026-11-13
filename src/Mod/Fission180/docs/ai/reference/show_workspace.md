# `show_workspace`: Show workspace

<!-- Generated from the tool catalogue (src/Mod/Fission180/fission180/ai/catalog) by tools/fission180/make_ai_docs.py: do not edit by hand. The unit test test_ai_docs_contract.py fails when this file and the catalogue differ. -->

Fusion: WORKSPACE menu (DESIGN, SIMULATION, MANUFACTURE, ANIMATION, DRAWING) and the ribbon's tabs. Category: View. Read-only. Needs an open design, the Fission 180 window.

## What it does

Show a workspace in the Fission 180 window so the person sees what you do: design (tab solid, surface, mesh, sheet_metal, plastic or utilities), simulation (tab setup or results; a study must exist: create_study), manufacture, animation, drawing (the newest drawing, or drawing) or flat_pattern (the open sheet metal body's flat pattern: flat_pattern makes one). Only what the window shows changes: every tool works from any workspace, so never switch just to call a tool. Not an undo step. Needs the window; inspect_design and get_design say which workspace is shown.

## Arguments

| Argument | Type | Unit | Default | Limits | Description |
|---|---|---|---|---|---|
| `workspace` (required) | `design` \| `simulation` \| `manufacture` \| `animation` \| `drawing` \| `flat_pattern` |  |  |  | the workspace to show |
| `tab` | `solid` \| `surface` \| `mesh` \| `sheet_metal` \| `plastic` \| `utilities` \| `setup` \| `results` |  |  |  | the ribbon tab (design and simulation) |
| `drawing` | string |  |  |  | the drawing to show (workspace drawing; default the newest) |

## Answer

A plain sentence, then JSON with: `workspace`, `was`. The example below shows a real one.

## Errors

- Without an open design: `No design is open: call new_design or open_design first (or create_sketch, which starts a new design).`
- Without the Fission 180 window: `This needs the Fission 180 window, and Fission 180 is running without one (headless / command line).`
- Called without arguments, the arguments are refused before anything runs: `Not done: workspace is missing.`
- Arguments of the wrong type, out of their limits or not in the table are refused the same way, each problem in a sentence ("radius must be a number above 0").
- When it cannot be done the answer says why in a sentence (isError true) and nothing changes.

## Example 1: the MESH tab of the DESIGN workspace (needs the Fission 180 window)

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
{"tool": "show_workspace", "args": {"workspace": "design", "tab": "mesh"}}
```

The answer:

```text
The window shows DESIGN (MESH tab) now (it showed DESIGN (SOLID tab)). Every tool works from any workspace: this only changes what the person sees.
{
 "workspace": {"workspace": "design", "tab": "mesh"},
 "was": {"workspace": "design", "tab": "solid"}
}
```

## More argument examples

- show the study the AI builds:
  `{"workspace": "simulation"}`
- the MESH tab:
  `{"workspace": "design", "tab": "mesh"}`

## See also

- [All tools](fission180://docs/tools.md), [the handbook](fission180://docs/handbook.md)
