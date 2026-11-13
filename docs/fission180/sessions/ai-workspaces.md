# Session log: ai-workspaces (wave 8, 2026-11-13)

Brief: `docs/fission180/dev/briefs/ai-workspaces.md` (SIMULATION, MANUFACTURE, ANIMATION, SHEET
METAL, PLASTIC and UTILITIES > MAKE for an AI). Branch `sf/ai-workspaces`. Coverage tables,
Fusion's behaviour with sources and the measurements: `docs/fission180/parity/ai.md`, section
"Wave 8 coverage: workspaces".

## What I found

The 2026-11-13 audit by name was right for SIMULATION (most of SETUP's DISPLAY / CONTACTS /
SOLVE extras and every RESULTS command had no tool) and for UTILITIES > MAKE. MANUFACTURE's
`cam_operation` already had a kind for every 2D / 3D / drilling strategy the ribbon offers
(Thread, Scallop, Pencil, Spiral and Radial are greyed in the ribbon itself); stock, WCS and
the post processors were all in `cam_setup` / `cam_post`; missing were the Setup Sheet, changes
to the Tool Library and gouges. ANIMATION's "Auto Explode: All Levels" was already
`anim_explode levels all`; missing were VIEW and the timeline's own edits. SHEET METAL and
PLASTIC had a tool for every command of their own; the Sheet Metal Rules dialog's Delete and a
body's rule swap were missing. PLASTIC's Rule Fillet is SOLID's `rule_fillet` with the plastic
rule's nominal radius.

## What I built

Twelve tools and five extensions, each on the workspace's own code:

- SIMULATION: `study_probe` (Point / Surface Probes and a Slice Plane as numbers, with where),
  `study_report` (RESULTS > Report, pictures with the window), `study_mesh` (Generate Mesh,
  Show Mesh), `study_setup` (Load Case Attributes, Contact Manager / Automatic Contacts, DOF
  View), `edit_study_item` (a constraint's, load's or mesh control's Edit / Suppress / Delete),
  `show_study_results` (the whole RESULTS display, the part fitted when it opens); `create_study
  copy_of` (Clone Study), `study_results` with Solver Data and the Convergence Plot, `solve_study`
  says how long it took.
- MANUFACTURE: `cam_setup_sheet`, `cam_tool_library` (add, edit, delete, copy, new library,
  delete library: the person is asked first); `cam_simulate` compares the stock with the model
  (gouges with their area, depth, place and operation; the stock left on the part).
- ANIMATION: `anim_view` (a View action from a standard view or a direction, fitted),
  `anim_action` (Edit Start/End, a drag, Delete).
- SHEET METAL: `sheet_metal_rule` takes `bodies` (they follow the rule) and `delete`.
- UTILITIES > MAKE: `print_part` (3D Print: a print file, or a slicer found on this computer,
  the person asked first), `export_everything`.
- Long calls: solve_study, study_mesh, cam_simulate, cam_generate and anim_publish_video call
  ai-speed's `progress.step` safe points (`fission180/ai/workspaces_core.safe_point`) when its
  `progress.py` is there; a Stop cancels a solve's background job and removes a half-written
  video. Without it (this branch alone) the old path runs.
- The pure parts (`fission180/ai/workspaces_core.py`): a result's numbers with where, a slice
  plane from words, a storyboard camera from a standard view, the CAM stock compared with the
  model's height field (cells along the model's outline left out).
- Five recipes for an AI (static-stress.md extended; mill-pocketed-plate.md,
  exploded-view-video.md, laser-cut-bracket.md, plastic-enclosure.md), every call run by the
  documentation runner.

## Measurements

See the parity doc's table. The slow ones: `print_part` 11 s on a 1,400-face part (the 3D Print
dialog's own meshing and writing; my watertight check had added 7 s more and now reads the
shape's closed shells instead), `export_everything` 23 to 29 s, `solve_study` 9 s at 16,729
nodes; both MAKE tools say it in their descriptions. `study_probe` on 13 faces went from about
12 s (a distance to the face per node) to 2.1 s (the surface's projection and domain test, the
exact distance only for the outline's nodes).

Not mine, seen while measuring (for ai-speed / ai-design): `create_sketch` with 200 circles
took 29 s and with 400 circles 170 s; a 0.5 mm fillet of 200 hole rims 35 s; `get_design` on
that part 8 s; a 20 x 20 `rectangular_pattern` of one hole on a 210 x 210 plate ran the sandbox
out of memory (the kernel killed it). An AI making a hole grid should be told to pattern a few
holes, not to draw hundreds of circles.

## FreeCAD facts and traps

- `Face.isPartOfDomain(u, v)` is False for a point exactly on the face's outline (OCC's
  classifier says ON, not IN): mesh nodes on a hole's rim, where the stress peaks, were left
  out. Fall back to the exact distance for the on-surface nodes it refuses.
- `Surface.parameter(p)` of a periodic surface (a cylinder) can give u a period away from the
  face's own range: try u +- the period before refusing.
- A tool's name must be letters and underscores (`print_3d` failed test_ai_catalog): `print_part`.
- A storyboard's action ids are integers (`anim_action` takes them so); the View row's first
  action starts at 0 (its own row has no action before it), not where the explode ended.
- Auto Explode keeps the largest component of each level in place: inside a subassembly too.
- Timings and random tool ids in an answer cannot be compared by the documentation runner:
  `docs_runner.same_answer` now masks "took N s", "seconds", "solve_seconds" and UUIDs.
- The `name` argument of the first extrude in a new design does not name its body (new_design
  made that body, not the extrude): `rename` it.

## Gaps (what Fusion does that these tools do not)

- Job Status has no tool: an AI's solve and mesh wait for their job and answer it.
- `show_study_results` needs the window; its Compare is a display (study_results of each study
  has the numbers).
- `cam_simulate`'s gouges and stock left come from a height field (one height per column): an
  undercut cannot be seen, the holder and clamps are not checked (as before), and differences
  under max(0.05 mm, a quarter of a cell) are not gouges.
- `print_part` starts only a slicer Fission 180 found on this computer or the one the person
  picked in Preferences > 3D Print (never a program an AI names), and only with the window.
- `export_everything` has no picture without the window.
- The person's own library rules (sheet metal, plastic) and tool libraries other than local
  ones are not changed by an AI beyond copying into them.
- The safe points were written to ai-speed's committed API (`progress.step`, Stopped a
  BaseException) but not run together on this branch: run the ai_workspace_* scenarios after
  merging sf/ai-speed.

## Changelog lines

- An AI can now read a simulation's results anywhere: at points, over faces and on a cut
  through the part, with where the highest and lowest values are.
- An AI can write a simulation's report as an HTML file, with pictures when Fission 180's
  window is open.
- An AI can make a study's mesh without solving, read back everything a study is set up with
  (loads, constraints, contacts, how the part could still move), and change, switch off or
  delete a load or a constraint.
- An AI can show a study's results in the window the way the RESULTS tab does: the result, how
  much the bend is drawn, a slice, an iso-surface, the animation, two studies side by side.
- An AI can copy a study to try another load or material, and a solve now says how long it
  took.
- An AI's milling simulation now finds where a tool cuts into the part and how much stock is
  left on it, and names the operation that did it.
- An AI can write a milling setup's Setup Sheet, and add, change or copy tools in your own tool
  library (it asks you before deleting a library).
- An AI can record camera moves on an animation and move, shorten or delete actions on its
  timeline.
- An AI can make a 3D print file, or send the design to a slicer installed on your computer
  (it asks you first), and use Export Everything.
- An AI can give a sheet metal body another rule and delete a rule nothing uses.
- Five new step-by-step recipes help an AI simulate, mill, animate, make sheet metal for a
  laser cutter and design a plastic enclosure.

## Known issues

- A milling simulation cannot see gouges under an overhang (it looks straight down) and does
  not check the tool holder or clamps.
- Sending to a slicer needs Fission 180's window; without it the AI saves a file instead.
