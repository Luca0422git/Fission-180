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
