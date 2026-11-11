# Wave 7, builder animation: the ANIMATION workspace (branch `sf/book-animation`, 2026-11-11)

Brief: `docs/fission180/dev/briefs/book-animation.md`. Report lines 185-222 (Workspaces table:
"Animation workspace (storyboards, Transform Components, Auto Explode, Publish Video): none"),
2524-2531 (Japanese Pull Saw, Machinist Hammer: "Animation workspace ... does not exist";
"Drawing > CREATE > Exploded View is in the menu but does nothing") and 2577-2578 (the Hilt's
exploded animation and diagram). Spec with sources, how it is built and the contract for the
Drawing workspace: `docs/fission180/parity/animation.md`.

## What the report says, and what I found

- **Reproduced**: on `develop` (3.3.10 + the Manufacture merge) the workspace menu offers
  Design / Simulation / Manufacture / Drawing; there is no animation code at all. The
  report is right: nothing to fix, a workspace to build.
- **Fusion's behaviour** (WebSearch excerpts of Autodesk's Fusion-Animate help, Autodesk's
  blog and support articles, the Community forum, tutorials; WebFetch cannot reach
  help.autodesk.com from the sandbox): the toolbar groups, New Storyboard's two types, the
  scratch zone ("actions are not being recorded, but the transforms performed are honored"),
  an action ending at the playhead, the Auto Explode toolbar (Explosion Scale, One-Step /
  Sequential, trail lines), Manual Explode (component, then axis), Show/Hide with Edit
  Action > Instant / Duration, View's red / yellow dot, Publish Video's Video Scope and Video
  Resolution, Reverse on the storyboard's tab, and a drawing's exploded view showing the
  storyboard "as it appears at the end". **Not found written down** (marked Guess): where
  an action starts (taken: where the component's previous one ended), and how Auto Explode
  chooses directions and distances (ours: see the parity doc).
- The report's claim "FreeCAD's own interface has no animation workbench either" is right
  for 1.1.4; nothing of FreeCAD's is used but its view providers and its off-screen
  renderer.

## What I built

- `animation_core.py` (no FreeCAD, no Qt; 60 unit tests with the AVI writer's): the
  storyboard data and its clean-up on load, quaternions, slerp, poses, a transform action's
  pose at a fraction, the state at a time (offsets, opacity, camera, callouts), recording
  (transform, home, visibility, view, callout) with the scratch-zone rule, timeline edits,
  end state, Reverse, the explode maths, sequence spans, the slider's scale, frame times.
- `animation.py`: the hidden `Animation` object, `change()` (one undo step per change),
  the contract (`storyboards`, `duration`, `placements_at`, `global_placements_at`,
  `hidden_at`, `trail_lines`), boxes of components, `explode_groups` / `explode_plan` /
  `auto_explode`, `manual_explode`, `transform`, `restore_home`, `show_hide`, `add_callout`,
  storyboard new / rename / delete / duplicate / reverse / move.
- `animation_view.py`: a moment drawn on the components' views only, and everything put back.
- `animation_ui.py`: the workspace (enter, leave, other designs, Home, drawings, other
  workspaces), the playhead, playback and loop, the view watcher, 12 commands.
- `animation_timeline_ui.py`: the ANIMATION TIMELINE (hand-painted canvas: ruler, scratch
  zone, rows, bars, playhead; transport buttons; storyboard tabs).
- `animation_panels.py`: New Storyboard, Transform Components, Auto Explode, Manual Explode,
  Create Callout, Edit Start/End (Edit Action), Publish Video.
- `animation_video.py`, `animation_video_core.py`: frames from the view, the AVI (Motion
  JPEG) writer and reader, ffmpeg for MP4 when found, PNG sequence.
- `animation_browser.py`: Storyboards and Components (with eyes) in the browser.
- `ai/ops/animation_ops.py` (7 design steps), `golden/animation_schema.py`,
  `golden/animation_checks.py` (`anim_expect`), 2 golden models.
- 24 icons (`tools/fission180/icons_animation.py`).

## Tests

| Scenario (real input) | Checks | Result |
|---|---|---|
| book_animation_workspace | 75 | PASS |
| book_animation_transform | 99 | PASS (also under `--stress`) |
| book_animation_storyboards | 124 | PASS |
| book_animation_explode | 79 | PASS |
| book_animation_publish | 67 | PASS (also under `--stress`) |
| book_animation_playback | 37 | PASS (also under `--stress`) |
| book_animation_switching | 76 | PASS |

Older scenarios of the shared files, run after my changes: `book_cam_setup` (58),
`sim_setup_canvas` (29), `drawing_new` (63), `components_basic` (252), `ribbon_sweep` with
`SWEEP_TABS=anim_animation` (29): all PASS. Golden: `anim_auto_explode_one_level`,
`anim_sequential_transform_reverse` PASS. Unit: see the final report.

## Bugs my own tests found on the way

- **A camera was never "near" itself** unless it looked straight along an axis:
  `camera_near` compared the dot product of two single-precision quaternions with 1 - 1e-8,
  and the product of one with itself is 0.99999994. The first view change (the ViewCube's
  top: quaternion 0, 0, 0, 1) was recorded, every later one never. Normalised first now
  (unit test with the real numbers).
- **Auto Explode's first rule threw parts out of the view** (distance from the middle + half
  the assembly: 90 mm for a pin on a 100 mm tool) and moved the base plate because a pin on
  one side shifted the middle. Now the biggest part stays and the gap is a quarter of the
  assembly's size.
- **A click on a part of a subassembly took the part's own component** in a dialog but the
  top-level one before the command (FreeCAD's observer names the clicked leaf, the
  selection's own list the top object). One rule now: `animation.clicked_component`.
- **The design's keys came back on in Manufacture** when it was entered from Animation
  (Animation had switched them off, Manufacture found nothing left to switch off, Animation
  then switched them on as it left). The held keys are handed over now; the same for the
  design timeline (which Manufacture would not have brought back).
- **New Storyboard on a design without one** made "Storyboard1", which looked like nothing
  had happened (the empty first tab is called that). It now keeps the first and adds
  "Storyboard2".
- **Undo walked on into the design's steps** once the storyboard's were used up (a design
  step undone from a workspace that must not change the design). The workspace now knows
  the undo steps it made by name; an Undo that took back another one is redone at once
  with a message (`animation_ui._Watch.slotUndoDocument`).

## FreeCAD facts and traps

- `ViewObject.setTransformation(matrix)` moves what the view draws and nothing else: the
  object's `Placement`, the document's "changed" mark and the undo stack stay as they are;
  picking follows the drawn place; a recompute does not put it back (a change of the
  object's Placement does). Nested `App::Part`s nest in the scene too, so a subassembly's
  transform carries its parts.
- `ViewObject.SwitchNode.whichChild = -1` hides a view without `Visibility` changing (and
  without marking the document). A material node of our own with `setOverride(True)` and
  only `transparency` not ignored, inserted at the front of `ViewObject.RootNode`, fades
  everything under it (the trick `component_look.py` uses).
- `Gui.getDocument(name).Modified` can be read and set from Python; `doc.saveAs()` by script
  does not clear it (the Save command does).
- `ViewObject.Transparency` and `Visibility` do mark the document as changed: not used.
- `view.saveImage(path, w, h, "Current")` renders off screen at any size (0.3 s for 640 x
  360 under software GL), with the scene's annotation nodes (callouts, trails) in it.
- Qt writes JPEG (`libqjpeg`) in both builds; there is no Qt Multimedia and no ffmpeg
  program in the AppImage (only `libavcodec` inside VTK's `vtkIOFFMPEG`, not used: the
  Windows build's VTK may differ).
- FreeCAD's selection observer names the clicked leaf object ("Box001"), while
  `Gui.Selection.getSelectionEx(doc, 0)` gives the top-level object with a path.
- A camera's orientation comes as single-precision floats: normalise before comparing.
- `QTabBar.setMovable(True)` emits `tabMoved(from, to)` during the drag; the tab then at
  `to` is the one that moved.
- The harness cannot see a repeating timer: a step that starts a playback or a Publish
  Video names its `done` (`a.played`, `a.published`); steps that act while one runs say
  `while_busy = True`.
- A golden model's body made after a `components_from_bodies` step lands in the component
  that is active by then: make the bodies first, then the components.
- The scratchpad folder is shared between builders: another builder's `patch7.py` replaced
  mine minutes after I ran it. Name scratch files after your area.

## Shared files touched

- `ribbon_ui.py`: `ANIMATION_TABS` (+ `CONTEXTUAL`), `self._anim_mode` and the tab hidden at
  start, the "Animation" entry in `_workspace_menu` (a block of its own, put before
  Simulation as in Fusion; Design / Simulation / Manufacture leave Animation),
  `set_animation_mode`, `_keep_animation_tabs`, and one line at the end of
  `set_drawing_mode`, `set_flat_pattern_mode`, `set_simulation_mode`,
  `set_manufacture_mode` (`self._keep_animation_tabs()`).
- `ribbon_config.py`: the `ANIM_*` groups, the `anim_animation` tab appended to `TABS`,
  `ANIM_MARKING_MENU` / `ANIM_MARKING_LIST`, after cam's block.
- `browser_ui.py`: `_animation_browser`, two lines in `_simulation_tree` /
  `_simulation_call`, `SIM_RENAMABLE +=`, and the eye of a `sim_anim_` row in `toggle_eye`.
- `marking_menu.py`: 7 lines (the workspace's ring).
- `ai/ops/core.py`, `golden/schema.py`, `golden/checks.py`: one import line each.
- `ai/catalog/__init__.py`: `AI_TOOLS_TO_COME += (the seven anim_ ops)`.
- `Fission180Tests/unit/test_ai_sheetmetal_plastic_tools.py`: the "no op waits for its tool"
  test lets `anim_` ops wait, as it lets `cam_` ops.
- `tools/fission180/data/fusion-menus.txt`: Animation is a workspace; Fusion's ANIMATION tab.
- `manufacture_ui.STATE` / `simulation_ui.STATE` are written to (not their files): when one
  of them takes over from Animation it is handed the design timeline to bring back and the
  held keys.

## Gaps (what Fusion has that this does not)

See "Differences" and "Gaps" in the parity doc. The ones a person may notice: no AI tools
yet (the steps wait in `AI_TOOLS_TO_COME`); a click in the view takes the top-level
component (a part inside a subassembly: its browser row); a component hidden in the design
cannot be shown by a storyboard; MP4 only with ffmpeg installed; Space plays only when the timeline has the keyboard; trails per
component, not per action.

## Changelog lines

- New ANIMATION workspace (workspace menu > Animation): make exploded views and assembly
  animations of a design's components without changing the design.
- Storyboards: several per design as tabs under the timeline; New Storyboard (clean, or
  starting where the previous one ends), rename, duplicate, reverse (explode becomes
  assemble), delete, reorder by dragging.
- The ANIMATION TIMELINE: drag the playhead, record at the playhead, drag a bar or its ends,
  double-click a bar to type its times, Del to delete, play / pause / loop.
- Transform Components: move and turn components with the manipulator or typed values, Set
  Pivot, Trail Line Visibility.
- Auto Explode: One Level and All Levels with the Explosion Scale slider, One-Step or
  Sequential; Manual Explode: pick a component, its axis and a distance.
- Show/Hide at the playhead (instant or a fade), from the ribbon or a component's eye in
  the browser; Restore Home.
- Create Callout: a text pinned to a point of a component, shown from the playhead on.
- View: orbiting, panning and zooming past the scratch zone is recorded as camera moves
  (switch it off to look around freely).
- Publish Video: the current storyboard or all of them as an AVI video (works everywhere),
  an MP4 when ffmpeg is installed, or a folder of PNG pictures, at the size and frame rate
  you choose.
- Drawings can ask a storyboard for its exploded positions (`animation.placements_at`).

## Known issues

- An animation moves components only. A design of plain bodies has nothing to animate: in
  Design, right-click the bodies > Create Components from Bodies first (the workspace says
  so).
- A click in the 3D view picks the top-level component. To move a part inside a subassembly,
  click its row in the browser.
- A component hidden in Design stays hidden in every storyboard: show it in Design first.
- Undo in the Animation workspace stops at the design's own steps (it says so): go to
  Design to undo those. After closing and reopening the program there is no undo history,
  as everywhere.
- MP4 needs the ffmpeg program installed on the computer; without it choose AVI (Motion
  JPEG), which VLC and Windows' players open.
- Space plays and pauses only after a click on the timeline.
- No AI tools for the Animation workspace yet.
