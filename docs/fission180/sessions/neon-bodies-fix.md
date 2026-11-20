# Neon Lights fix round `bodies-fix`: 3D bodies (2026-11-20)

Branch `sf/neon-bodies-fix` (from `sf/neon-integration` aad96d3b). Plan task B6; design 6.6 and
6.13. Fixes the six problems the independent review found in `bodies` (see
`sessions/neon-bodies.md`).

## In plain words (for Luca)

- **A save that fails no longer leaves Neon half off.** Before, if saving failed (for example
  the file was read-only), the 3D view stayed in the plain look: no glowing outlines, no
  Hologram, Dark colours in the scene, even after switching looks. Now Fission 180 notices the
  save did not finish and puts the neon look back at once. Switching looks also clears any such
  leftover.
- **Hover and selection look the same width as in Dark.** With Glow on, a hovered edge (or
  every edge of a selected body) used to become a thick 10-pixel band. Now it is the normal thin
  highlight with the soft glow underneath.
- **Sketches inside a body keep their own colours.** They were getting the body outline colour
  and glow.
- **The Hologram "rim light" test is safer.** It only runs the first time you turn Hologram on
  (not at every start). If a graphics driver ever crashed FreeCAD during that test, Fission 180
  remembers it and uses the plain glass from then on instead of crashing at every start. The
  test also checks more strictly that the shader draws the right colours.
- **Speed:** the glow costs nothing measurable (see below), so it stays as it is.

## What changed

| # | Problem | Fix | Proved by |
|---|---|---|---|
| 1 | Failed save left `saving`, `theme._neon["normal"]`, the background and the scene part stuck | `slotStartSaveDocument` queues `QTimer.singleShot(0, ...)` (`_after_failed_save`): if the design is still in `saving` when it runs (FreeCAD sends "finished" within the same call, so only after a failure), `_to_neon` runs, including every part's after-save hook. `enable()`/`disable()` call `_reset_pictures()` (clears `saving`, `normal`, `neon_background`, `theme.normal_look(False)`). `normal_look()`'s depth never goes below 0. | `neon_bodies` `failed_save`/`failed_save_recovered` (saveAs to a chmod-444 file with Hologram on: error raised, not saving, neon colours live, BackgroundColor setting unchanged, glass/glow/outline back, view corner = neon gradient top, i.e. the scene part's after-save ran); `stuck_save`/`stuck_cleared`/`neon_after_stuck` (a stuck state is cleared by Dark and by Neon); `save_hologram` checks the next good save keeps the background setting |
| 2 | Glow pass reused the body's `SoBrepEdgeSet`, drawing its highlight at glow width | The glow draws a plain `SoIndexedLineSet` named `Fission180NeonGlowLines`, `coordIndex.connectFrom(body edge set)`, no selection logic; the glow separator has render and bounding-box caching OFF (like `ViewProviderPartExt::attach`) | `neon_bodies` `hover_edge`/`select_body` measured in Dark and in Neon with Glow on: pixels changed across the hovered edge 2 (Dark) vs 2 (Neon); selection reaching into the background below the edge 0 vs 0. On the old code: 2 vs 7 and 0 vs 3 (both fail). Also checks the node type and caching. |
| 3 | `_groups` from a Body walked its children's scenes (sketches got the overrides) | Matches whose path passes through a node of type `SoFCSelectionRoot` (every view provider's `RootNode`, and a group's children holder) are skipped | `neon_bodies` `sketch_own_colours`: a visible sketch in the body ("Loose", beside the pad) has no `Fission180Neon*` node, the body's groups leave out the sketch's, no glow beside its curve, its curve is not in the outline colour. On the old code: 6 neon nodes in the sketch, curve drawn (255, 0, 60) = outline. |
| 4 | Rim-light self-test at every start, memory-only, could pass wrongly | Not called in `enable()`; runs from `_style()` only when a Hologram body needs it. Before drawing it stores `RimLightTest = "testing"` in `neon_settings.PARAMS` and writes the settings to disk (`App.saveParameter()`; FreeCAD otherwise saves them only at exit); clears it after. A leftover `testing` at the next start becomes `crashed`: fails at once, never drawn again (`neon_shader.reset(forget_crash=True)` allows a retry). New `judge()`: the centre pixel must stay within 15 of the plain render (the plain test picture is now unlit `BASE_COLOR`, i.e. the face colour itself). | unit `ShaderJudge` (4) and `ShaderSelfTest` (4) in `test_neon_view_core.py`; `neon_bodies`: self-test not run with Hologram off, flag cleared after it ran |
| 5 | Speed of the see-through glow | Measured (below): within budget, so no change to an opaque glow | new scenario `neon_glow_speed` (a speed check, budget +10%) |
| 6 | Loose tests | Capture checks the corner against the neon gradient's top (from `p["view"]`, what the view uses) without the `or > 6` escape; checks Hologram's glass is in the capture and the normal face in "Normal look" (captured at the view's size, sampled at the face); checks the real `BackgroundColor` setting instead of `_state`. `_apply_glow` no longer compares pivy nodes with `is not` nor replaces a child on every apply (it only rebuilds when the structure is wrong or the connected edge set changed; colours/width are written only when they change) | `neon_bodies` `capture` |

## Speed (task 5)

`neon_glow_speed`: a `Part::Feature` of 500 boxes (3,000 faces, 6,000 edges), Neon Lights, 60
frames of a slow orbit per round, each frame drawn at once (`QWidget.grab()`), CPU time per
frame with `time.thread_time()`; 3 rounds each, the lowest middle value compared.

| | CPU per frame (middle, ms) |
|---|---|
| Neon, Glow on | 7.20 / 10.64 / 7.95 |
| Neon, Glow off | 8.64 / 10.88 / 7.84 |
| **on / off** | **0.92** (budget 1.10) |
| Dark (same part) | 3.47 |

The glow's cost is lost in the noise, so it stays see-through. Note for the orchestrator: Neon
with Glow **off** still costs about 2x Dark's CPU per frame on this part (7.8 vs 3.5 ms). That is
not the glow; I did not look for which part costs it (the effects overlay of B8 or the
outline's override material are candidates). Software OpenGL in the sandbox (llvmpipe draws in
its own threads, so thread time is mostly Coin's own traversal).

## Facts found (FreeCAD / Coin / pivy)

- pivy node wrappers compare correctly with `==` (same C++ node), never with `is`.
- `App.Document.saveAs()` to a file with no owner-write permission bit fails even as root:
  `FileInfo::isWritable()` reads the permission bits. It raises after `signalStartSave`, so
  "save finished" never comes (`Document::saveToFile`).
- `saveAs` renames the design (Label) before it saves, even when the save then fails.
- Preselection on a body's feature reports the sub-element through the path:
  `SubElementNames` like `"Pad.Edge1"`, not `"Edge1"`.
- `QWidget.grab()` on the 3D view's `QOpenGLWidget` draws a frame synchronously (PySide sees it
  as a plain `QWidget`, so `grabFramebuffer` is not available); `repaint()` drew nothing.
- Under Coin, the sandbox's plain (fixed-function) test sphere comes out darker than its
  diffuse colour (10 vs 26 at the centre), while the rim shader's centre is the diffuse colour:
  a fair "colour reaches the shader" comparison needs the plain picture unlit (`BASE_COLOR`).
- FreeCAD settings live in memory until FreeCAD closes: `App.saveParameter()` writes them now.

## Files touched

- `F/neon_view.py`, `F/neon_shader.py`
- `T/gui/scenarios/neon_bodies.py` (now 68 checks), new `T/gui/scenarios/neon_glow_speed.py`
- `T/unit/test_neon_view_core.py` (17 tests)
- No shared or other builder's file. The self-test flag is written with
  `App.ParamGet(neon_settings.PARAMS)` directly, not as a `neon_settings.DEFAULTS` key, so
  `neon_prefs_ui`'s settings snapshot (every DEFAULTS key) does not pick it up.
- `capture_ui.py` / `export_ui.py` needed no change.

## Tests (last run)

`run_tests.sh --only unit`: 4126 tests OK (incl. `test_theme_identity.py`). Scenarios
`look_unchanged` 13, `neon_switch` 27, `neon_outlines` 14, `neon_bodies` 68, `neon_views` 10,
`neon_glow_speed` 5: all PASS. The new `neon_bodies` checks were also run against the old
`neon_view.py`: they fail there (highlight widths, sketch nodes and colour, the failed save).

## Screenshots (`docs/fission180/images/neon/`)

- `bodies-fix-hover-edge.png`: a hovered edge with Glow on: a thin highlight, as in Dark.
- `bodies-fix-selected-body.png`: the whole body selected with Glow on (thin edges; the sketch
  beside it keeps its own colour).
- `bodies-fix-after-failed-save.png`: Hologram right after a save to a read-only file failed:
  the neon look is back.

## Not done / open

- `--stress` was not run for the new steps (they wait for state, not for time).
- The rim-light "crashed" mark is permanent until `neon_shader.reset(forget_crash=True)`; a
  "try the rim light again" button (B10's Preferences or B8's self-check) could call it.
