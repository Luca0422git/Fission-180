You are building one area of Fission 180, a FreeCAD 1.1.4 fork that must behave like Autodesk
Fusion. Read `docs/fission180/dev/briefs/ai-common.md` first (and everything it lists).

## Your area: SIMULATION, MANUFACTURE, ANIMATION, SHEET METAL, PLASTIC and UTILITIES for the AI (builder ai-workspaces, branch `sf/ai-workspaces`)

Luca: "I want it to be able to simulate, manufacture, animate and draw" (drawings are ai-drawing's).
The AI has tools in each of these (simulate 10, manufacture 9, animation 9, sheet metal 15,
plastic 7). The 2026-11-13 audit by name (check each; a `kind` may cover a command) found without
a tool:

- SIMULATION setup: Manage Physical Materials, Toggle Gravity, Automatic Contacts, Contact
  Manager, DOF View, Show Mesh, Load Case Attributes, Generate Mesh, Job Status.
- SIMULATION results: Animate, Convergence Plot, Legend Min / Max, Report, deformation scale
  (Undeformed / Actual / Adjusted x0.5 / x1 / x2 / x5), Show Mesh, Undeformed Model, Loads and
  Constraints display, Surface Probes, Point Probes, Show Min / Max, Slice Plane, Iso-surface,
  Solver Data. For an AI the numbers matter most: probes at a point or on a face (stress,
  displacement, safety factor), min / max with where, the report as a file.
- MANUFACTURE: check `cam_operation` kinds against every 2D / 3D / Drilling command; Setup Sheet;
  the tool library, the post processors, stock and WCS options of `cam_setup`; simulate with
  collision / gouge results as numbers.
- ANIMATION: Auto Explode: All Levels; check every TRANSFORM / ANNOTATION / VIEW / PUBLISH command.
- SHEET METAL and PLASTIC: check every command of their tabs (including the flat pattern
  workspace's commands and PLASTIC INSPECT) against the existing tools.
- UTILITIES > MAKE: 3D Print (send to a slicer / save a print file), Export Everything.

### What to build
Every command above that changes or measures something reachable by a tool or a `kind`, through
the code of the workspace's own files, with the rules of ai-common.md. Long computations (solve,
cam_generate, cam_simulate, publish video) answer with how long they took and say in their
description how long they can take; check with ai-speed's builder (its branch `sf/ai-speed`)
how a long call reports progress, and use it. Recipes for an AI: "check a bracket under load and
make it strong enough" (study -> results numbers -> change the design -> solve again), "mill a
pocketed plate" (setup, operations, simulate, post), "an exploded-view video", "a sheet metal
bracket and its flat pattern for a laser cutter", "a plastic enclosure with bosses, lip and snap
fits".

### Proof
Headless runner cases for every tool and kind; GUI scenarios through the real MCP server and
bridge (`ai_workspace_*.py`), one per workspace, doing the recipe end to end and checking the
numbers on the model / study / toolpath / storyboard.
