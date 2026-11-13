You are building one area of Fission 180, a FreeCAD 1.1.4 fork that must behave like Autodesk
Fusion. Read `CLAUDE.md`, `docs/fission180/dev/briefs/common.md` and the sections "Machine,
tests, time" and "Your final message" of `docs/fission180/dev/briefs/ai-common.md` (they apply
to you; the rest of that file is about AI tools and does not). Then this file.

## Your area: the Move tool must move live and smoothly, even on complex parts (builder move-speed, branch `sf/move-speed`)

Luca (2026-11-13): "the move tool. its too slow. especially for complex parts. it needs to be
optimized CONSIDERABLY. That relic file that i gave you is a great example of it. while i was
working on it, i could pretty much say goodbye to live movement. only basic shapes move
quickly, and even those are a bit choppy."

His design "Relic" (not in the repository and never to be added: it is his) holds five
PartDesign bodies; the main one has 611 faces and about 30 features (27 pockets, 2 grooves,
4 pads, sketches), plus two hidden mesh bodies of 8,486 triangles. A copy for your own
measurements only is at
`/tmp/claude-0/-home-user-Fission-180/c863d717-16ff-5ab9-bc20-80e6eeec0d09/scratchpad/relic_in/Relic.FCStd`
(read it, never copy it into the worktree; tests build their own big parts).

Fusion's behaviour (copy the behaviour, never its code): while the manipulator is dragged the
body follows the mouse at the screen's frame rate whatever its size (only the drawn picture
moves); the real result is computed when the mouse is released (or the value typed). The
timeline step, the dialog values and Undo behave exactly as before.

### What to do
1. **Measure first** (before changing anything): the time per mouse-move frame while dragging
   Move/Copy's arrows and rotation handles with real mouse moves under Xvfb (`gui-tests.md`),
   on: a basic box; a PartDesign body like Relic's (a plate with ~30 pockets / holes / grooves
   in its history, ~600 faces); a solid of ~3,000 faces; a mesh body of ~8,500 triangles; two
   or three bodies at once; Create Copy on; Point to Point; a component (`component_move*`,
   if the same tool path moves components). Also on Relic itself (your scratchpad copy).
   Profile (cProfile around the drag handler, and the time Qt spends drawing) and write down
   where the time goes: per-frame `recompute()` of the Move step and of everything after it in
   the timeline, a shape copy / transform per frame, the view provider re-tessellating a new
   shape, selection / highlight / preselection updates, the browser or timeline refreshing,
   handles redrawn, `drag_guard`, Qt timers firing more often than frames.
2. **Make dragging live**: during a drag, move only what is drawn (a transform on the view
   providers' scene nodes or a placement change that does not re-tessellate), never recompute
   the document or rebuild shapes per frame; compute the real result once, on release (and on a
   typed value). Coalesce mouse events to one update per frame. Targets: a box at the screen's
   frame rate (no choppiness: steady, under 16 ms a frame); Relic-like parts and the 3,000-face
   solid under 33 ms a frame; the 8,500-triangle mesh under 33 ms; the release's recompute as
   fast as before or faster. Keep everything else exactly as it is: snapping and increments
   (`increments.py`), the typed fields updating while dragging, Point to Point, Rotate about a
   picked axis, Create Copy's preview, OK / Cancel / Esc, one "Move" undo step, editing the Move
   from the timeline, bodies picked before M, multi-body moves, joints / components
   (`drag_guard`), the move of faces (`move_face.py`) if it shares the drag path.
3. If the same slowness is in other live drags that share code (Press Pull's arrow, sketch
   Move, component Move, joints drag), measure them too and fix what shares the cause; list the
   rest with numbers for later.

### Files
`fission180/move.py`, `move_ui.py`, `move_face.py`, `handles3d.py`, `drag_guard.py`,
`component_move.py` / `component_move_ui.py`, `increments.py`, and whatever the profile shows.
Two builders are still working: ai-speed (`fission180/ai/bridge.py`, `executor.py`,
`progress.py`, `fission180_mcp.py`) and ai-mesh (`fission180/mesh.py`, `insert.py`,
`mesh_cut_ui.py`, `fission180/ai/catalog/mesh_tools.py`): do not touch their files. A FreeCAD core
change only if the profile proves Python cannot do it, with a `FISSION180:` comment and an entry
in `docs/fission180/core-patches.md` (and say so loudly in your report: core changes need a full
4-hour build, Luca's releases are patches).

### Proof
- A GUI scenario `move_speed.py` with real mouse drags that measures frame times on the big
  parts and fails when they exceed the targets (with headroom for CI's slower machine: say
  what you chose and why), and checks the result after release (placement, volume, one undo
  step, the timeline). Before / after numbers in your session log
  `docs/fission180/sessions/move-speed.md`, Relic's included.
- Every existing Move scenario still passes, one at a time: `bodies_move`,
  `book_components_move`, `components2_move`, `components_move`, `extrude_multibody_move`,
  `fixdecal_body_move`, `modify2_move_face`, `regress_revolve_move`, `surface4_move_faces`,
  `surface4_move_mirror`, and any other that uses the files you changed; the 770 px check for
  scenarios that click in the 3D view; unit (`--only unit`); golden (`--only golden`) if you
  touch geometry code.
- Plain-language "what changed for Luca" in your report.
