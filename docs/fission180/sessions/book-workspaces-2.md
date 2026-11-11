# Wave 7, builder workspaces-2: the follow-up on MANUFACTURE and ANIMATION (branch `sf/book-workspaces-2`, 2026-11-11)

Builders cam and animation built the two workspaces; this session took both over: AI tools,
the fields the engine ignored, the workspace switching bug, and the gaps the book's projects
use. Parity docs: `docs/fission180/parity/manufacture.md`, `parity/animation.md`.

## 1. AI tools for both workspaces

Eighteen tools, each an action on the workspaces' own Qt-free modules (the three that make
or change setups and operations run the same design steps as the golden models; the
animation tools call `animation.py` with the call's title as the undo step's name):

| Tool | What it does |
|---|---|
| `cam_setup` | New Setup: bodies, stock (relative / fixed / from solid / from preceding setup), work coordinate system, program; answers the stock and model boxes |
| `cam_operation` | one of the 15 operations with picks by selector, a tool of a library or described by its sizes, the dialog's options; generates and answers the toolpath's numbers |
| `cam_edit` | change a setup or an operation (options, tool, picks, suppress, order, name) and regenerate |
| `cam_delete` | delete an operation, or a setup with its operations |
| `cam_generate` | make the toolpaths that are missing or out of date |
| `cam_simulate` | machining time, cutting and rapid distances, stock volume, volume removed (per operation too), every rapid move into the stock |
| `cam_post` | write the G-code (nine controllers, mm / in); answers the file and the checker's result |
| `cam_setups` | the browser as data: setups, operations, states, numbers; `details` adds every option |
| `cam_tools` | the Tool Library: libraries, and a library's tools with their cutting data |
| `anim_storyboard` | new / duplicate / reverse / rename / delete / activate |
| `anim_transform` | move and turn components by numbers, recorded at a time |
| `anim_explode` | Auto Explode: One Level / All Levels, scale, sequential, trails |
| `anim_manual_explode` | components along their axes by a distance |
| `anim_show_hide` | show or hide from a moment on |
| `anim_restore_home` | components back to where the design has them |
| `anim_callout` | a text pinned to a point, optionally following a component |
| `anim_storyboards` | storyboards, a storyboard's actions, the components' places at a time |
| `anim_publish_video` | AVI / MP4 / PNG from the 3D view (needs the window) |

`catalog.AI_TOOLS_TO_COME` is `()` again and `test_no_op_waits_for_its_tool` asserts it.
New categories "manufacture" and "animation" in `catalog/registry.py`.

Decisions: a call that adds an operation whose geometry or tool is wrong is refused before
anything is added (`manufacture.plan` runs inside the undo step); an engine failure after
that leaves the operation with its error and answers an error naming `cam_edit` /
`cam_delete`. `at` is required for every recording tool (0 is the scratch zone, and the
answer says that nothing was recorded there). Publishing answers no file size (it differs
between runs; the docs examples are compared).

## 2. Manufacture: fields the engine ignored

Reproduced by reading the generated G-code: with Lead-In Feedrate 150 and Ramp Feedrate 77
typed, every lead and ramp was cut at 600 or 200; a Tolerance of 0.5 gave the same path as
0.01. Root cause: `engine_plan` never passed them on. See the parity doc ("Tolerance",
"Lead-In Feedrate", "Ramp Feedrate") for what each maps to. Fusion (Autodesk's help, search
excerpts): the tolerance is "the maximum chord distance" when curves are linearized;
Lead-in / Ramp feedrate are the feeds "used when leading in to a cutting move" / "doing
helical ramps into stock".

FreeCAD facts: `Path.Area.setDefaultParams(Accuracy=, Deflection=)` is what FreeCAD's CAM
preferences set once at start; it changes what Profile / Pocket / MillFace make. The path is
up to 2.35 x the accuracy from the true offset curve (measured, proportional at 0.01 and
0.5), so a third of the Tolerance is passed. The ramp dress-up has `RampFeedRate = "Custom"`
with `CustomFeedRate`. The lead-in dress-up has no feed property. Adaptive's helix is made at
`vertFeed` (the plunge feed).

## 3. Workspace switching

Reproduced with real input (scenario `book_workspaces_switch` on the unfixed code, 22
failures): in Manufacture, S (command search) > "New Simulation Study" > Enter entered
Simulation without leaving Manufacture. The design's keys came back on in Simulation, and
after the workspace menu's Design the design timeline stayed hidden for the rest of the
session (every later visit to Design too). The same after Simulation > Animation,
Animation > Manufacture and so on by a command.

Root cause: each workspace remembered for itself whether it had hidden the timeline
(`STATE["timeline"]`) and the keys (`STATE["held"]`), and watched for the others on a timer.
The second one found nothing left to hide; the first, noticing it, let go without showing
the timeline (another workspace was on) and switched the keys back on.

Fix: `workspace_switch.py`. Whoever enters calls `leave_others` first (one workspace at a
time, always left by its own code); the timeline is held by name through `timeline_ui.hold`
(what Home and drawings already used) and the keys through `hold_design_keys`, so both come
back when the last holder lets go, in any order. `ribbon_ui.py` is unchanged: its five mode
setters passed every route (the `elif` chains were not the cause).

Also seen: the command search runs a command whose `IsActive` is false without a word
(S > "Study Materials" from Manufacture does nothing). `search_ui.py` is the shell
builder's: reported, not changed.

## 4. Manufacture: what the book's two CAM projects use

The book itself is not in the repository; the report lists the chapter's steps (Setup, 2D
Adaptive, 2D Contour, Tool Library, Simulate, Post Process), and Autodesk's help was used
for what a longboard and a guitar body need on top: a board as stock, tabs that hold the
part, and a second setup for the other side. Followed by real input in
`book_cam_book_projects` (a board 200 x 120 x 30 with a pocket on top, a cavity in its
back and two holes). What could not be followed before, and was built:

- **Tabs at clicked points** ("Tab Positioning: At points", the Tab Positions box).
- **Stock From preceding setup** for the second setup (greyed before).
- An inch tool was there already (the inch sample library); Fixed size box, Simulate and
  Post Process worked as the first scenarios left them.

Not built (the book's text could not be read to confirm whether it uses them): NC Program
objects (Post Process posts the active setup or the picked operations), machining
boundaries for the 3D operations, a Lead-Out Feedrate field.

FreeCAD facts: the tab dress-up places tabs at `Positions` (points that must lie within
0.1 mm of the toolpath's bottom wire, `pathData.bottomEdges`), and disables tabs that
overlap (`Disabled`); a straight edge's `discretize(Deflection=...)` gives its two ends
only (use `distToShape`).

## 5. Animation: what the book's animation project uses

Followed by real input in `book_animation_book_project` (explode, a part moved, a callout,
duplicate and reverse, publish). Built on the way:

- **Space** plays and pauses whenever the workspace is in front and nobody is typing (an
  application event filter; before, only the timeline took it, and in the 3D view FreeCAD's
  own Space, Toggle Visibility, hid what was selected).
- **A part inside a subassembly** by a second click (Fusion's rule for Transform Components
  was not found written; see the parity doc).
- **Hidden in the design**: the row's tip was there for the component itself; it now also
  covers a part inside a hidden subassembly, and Show/Hide says which component hides it.

View actions (the camera) are covered by `book_animation_publish`; the drawing's Exploded
View is the drawings builder's (merged: it reads `animation.placements_at`, `trail_lines`,
`hidden_at`, whose signatures are unchanged).

## 6. MP4

The AppImage: no ffmpeg program, no Qt Multimedia; VTK's `vtkIOFFMPEG` is there (its writer
makes AVI only). The Windows build comes from the same conda recipe, and conda-forge builds
`vtk-io-ffmpeg` only for Linux and macOS, so nothing there can encode either (read from the
recipe; no Windows machine here to look at). AVI and PNG stay; the greyed MP4 entry's tip,
the refusal and the AI tool now tell where to get ffmpeg for each system, and ffmpeg is also
looked for where `winget` and `C:\Program Files` put it. Nothing is bundled.

## Tests

| Scenario (real input, paced by state) | Checks |
|---|---|
| book_workspaces_switch (every route between the workspaces) | 229 |
| book_cam_feeds (tolerance, lead-in and ramp feedrates read in the G-code) | 77 |
| book_cam_book_projects (the book's two CAM projects) | 69 |
| book_animation_book_project (the book's animation project) | 51 |
| book_workspaces_ai_tools (the AI tools with the window) | 47 |

Headless: `Fission180Tests/headless/workspace_tools.py`, 90 calls (every tool, its numbers
against the golden models', its refusals). Unit: `test_ai_workspace_tools.py`,
`test_workspace_switch.py`, new cases in `test_manufacture_core.py` and
`test_animation_core.py`.

The final round, after merging `develop` with all thirteen areas in it (d248501c): unit 3664
tests OK; golden `cam_*` and `anim_*` 4 of 4; `--only headless`: the runner 555 calls on 172
tools, none missing (one check of this session's own first call assumed no design was open
yet, corrected and the runner run again: 0 failed), documentation examples 197 items / 1343
calls 0 failed, the AI agent end to end 81 checks 0 failed, Auto Timeline 153 + 15 checks
and 71 recognised parts 0 failed. Scenarios, each alone: the five above, and the older ones
of the files changed: book_cam_setup 58, book_cam_operations 79, book_cam_program 87,
book_cam_refusals 50, book_cam_orientation 35, book_animation_workspace 75,
book_animation_switching 76, book_animation_explode 79, book_animation_playback 37,
book_animation_publish 67, book_animation_transform 99, book_animation_storyboards 124,
sim_setup_workspace 70, simres_workspace 71, home_tab_panels 14, ai_docs_gui 19: all PASS.

The run was cut off once (usage credits, a machine restart) between items 3 and 4; the
worktree survived and nothing had to be redone but the scenario that was running.

## Shared files touched

- `ai/catalog/__init__.py` (two imports, `AI_TOOLS_TO_COME = ()`, the module's docstring),
  `ai/catalog/registry.py` (categories "manufacture" and "animation"),
  `ai/actions/__init__.py` (two imports).
- `Fission180Tests/unit/test_ai_sheetmetal_plastic_tools.py` (the assertion put back),
  `Fission180Tests/headless/runner.py` (runs the new session),
  `Fission180Tests/docs/tool_examples.py` and `tool_results.json` (the new tools' examples),
  `Fission180Tests/gui/scenarios/book_animation_publish.py` (the MP4 tip's new words).
- `simulation_ui.py`: `_timeline` and `_hold_design_keys` use `workspace_switch`, and
  `enter_workspace` calls `workspace_switch.leave_others("simulation")`.
- `ribbon_ui.py`, `browser_ui.py`: not touched.

## Changelog lines

- The AI assistant can now work in the MANUFACTURE workspace: make a setup, add and change
  milling and drilling operations with tools from the Tool Library, generate, simulate (with
  the machining time, the volume removed and any rapid move into the stock) and post process
  (with the file and what the checker found).
- The AI assistant can now work in the ANIMATION workspace: storyboards, moving and
  exploding components, show / hide, callouts, reading a storyboard, publishing a video.
- Manufacture: Tolerance, Lead-In Feedrate and Ramp Feedrate now reach the toolpath (they
  were shown but ignored); where an operation has no use for one, the field is greyed and
  its tip says why.
- Manufacture: holding tabs can be put where you click (Tab Positioning: At points).
- Manufacture: a second setup can take its stock From preceding setup, for the other side
  of a part.
- Fixed: after going from Manufacture to Simulation (or between any two workspaces) through
  a command of the other workspace, Design came back without its timeline, and the design's
  keys worked inside the other workspace.
- Animation: Space plays and pauses wherever the pointer is (no need to click the timeline
  first); it no longer hides the selected component.
- Animation: a part inside a subassembly can be picked in the 3D view: click it a second
  time (the first click takes the subassembly, and the dialog says so).
- Animation: a component hidden in Design says so in its browser row's tip, also when it is
  hidden because the subassembly it is in is hidden.
- Publish Video: the greyed MP4 entry now tells where to get ffmpeg.

## Known issues

- Stock From preceding setup is the whole block of the setup before: what that setup's
  operations cut away is not taken off. The tool then treats those places as material (safe,
  a little slower); Simulate starts from the full block.
- A lead-out is cut at the cutting feed (Fusion has a Lead-Out Feedrate of its own).
- A toolpath made before this version shows "needs regenerating" once (the engine changed).
- Tabs At points: the points are kept where they were clicked; after the design changes,
  a point that is no longer on the contour is refused with how far off it is. Click the
  positions again.
- The command search (S) runs a command that is greyed in the ribbon without saying
  anything (in Manufacture, S > "Study Materials" does nothing). Use the workspace menu, or
  "New Simulation Study".
- MP4 still needs the ffmpeg program installed; AVI and PNG need nothing.
- The AI assistant cannot yet change or delete one action of a storyboard, or record camera
  moves; undo, or the timeline, does that.
