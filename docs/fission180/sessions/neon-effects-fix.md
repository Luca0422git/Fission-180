# Neon Lights fix round: effects (`effects-fix`)

Branch `sf/neon-effects-fix` (from `sf/neon-integration` 2145969c). Fixes the seven problems an
independent reviewer found in builder `effects`' work (plan task B8, design 6.7 and 6.13).

## In plain words (for Luca)

- **Turning the model no longer makes the screen effects redraw.** Before, every frame of the 3D
  view also repainted the see-through effects layer over it (+7% to +24% per frame in the
  builder's runs). Now the layer has a hole where each 3D view is, and the scan lines and shading
  over the model are drawn by the 3D view itself, on the graphics card. Measured here: every
  effect on adds **+0.9%** processor time per frame, and the layer repaints **0 times** in 120
  frames (budget: 10%).
- **The self-check tells the truth on real graphics cards.** It used to time frames on the clock,
  which a graphics card holds to the screen's refresh rate (60 a second), so it would have said OK
  whatever happened. It now measures the processor time of each frame, counts the layer's
  repaints, runs with Sounds on too, takes the runs in turns of 20 frames so the computer's own
  ups and downs do not decide, and ends with a **VERDICT** line in plain words.
- **Resizing the window no longer stutters.** The still picture took 46-69 ms and was made again
  on every step of a resize. It now takes about 4-10 ms and is made once, 0.2 s after the resize
  stops.
- **Nothing ticks while Fission 180 is minimised or in the background.** The glitch timer stops
  when another window is active and starts a fresh 40-120 s wait when you come back; a glitch held
  back because you are busy looks again once a second (not four times) and gives up after a
  minute.
- **One thing stays off by default, as before:** the *moving scan band* costs +13% while turning
  the view (it moves 25 times a second, and each move makes the window put its picture together
  again). It was already off unless you switch it on; the self-check reports it on its own line.
- On a computer **without a graphics-card driver** (OpenGL drawn by the processor, like this
  sandbox), the effects over the 3D view are skipped automatically, because there every pixel
  costs; the self-check says "skipped: ... (software)". Everything around the 3D view still shows.

## What changed, problem by problem

### 1. Speed budget (high)

- `neon_effects.Overlay.set_views()` gives the layer a **mask**: the window minus every 3D view's
  rectangle. Qt then never repaints the layer for a 3D frame. The mask follows the views: main
  window resize, `LayoutRequest`, the MDI area's `subWindowActivated` (a design opened, closed or
  brought to the front), and each 3D view widget's own Resize/Move/Show/Hide (an event filter).
- The part over the 3D views (`_ViewFx`): a Coin **superimposition** added to each view's
  `SoRenderManager` (`addSuperimposition`). It is drawn after the model by FreeCAD's own render
  (`View3DInventorViewer::renderScene` -> `inherited::actualRedraw` -> `SoRenderManager::render`),
  is not in saved pictures (`savePicture`/thumbnails use the offscreen renderer with the scene
  graph only) and is never picked. It holds:
  - the shade (glow and CRT corners/edges) as one texture at half the view's size (smooth
    content), drawn only in the 16-texel cells that have something in them (the empty middle of
    the view costs nothing);
  - the scan lines as thin quads on exactly the window rows the layer uses (`y % 3 == 2`);
  - ViewStrength as the materials' transparency (a strength change makes nothing again);
  - `SoTransparencyType BLEND` (no per-frame sorting of the see-through triangles: with Coin's
    sorted-triangle mode the quads cost +55% here) and no depth test.
- Software OpenGL (`llvmpipe`, `softpipe`, `swrast`, Windows' basic/GDI drivers, SwiftShader):
  the 3D-view part is off unless forced (`neon_effects.set_view_part(True)`, used by the tests and
  measured by the self-check as "3D-view part forced on"). Every pixel drawn costs processor time
  there.
- During a glitch the mask opens over the glitch strip for its 80-150 ms (a glitch never fires
  while the camera moves), so the strip still crosses the 3D view at ViewStrength%.

Measured in the sandbox (Mesa llvmpipe, 1800x1000 window, 3,000-face sample, self-check):

| run | processor ms/frame | against off | layer paints in 120 frames |
|---|---|---|---|
| effects off | 15.74 | | 0 |
| every effect on (band off) | 15.89 | **+0.9%** | 0 |
| + the moving scan band | 17.87 | +13.5% | 109 (= the band's 109 frames) |
| effects + Sounds on | 15.91 | +1.0% | 0 |
| effects + Hologram on | 16.47 | +4.6% | 0 |
| 3D-view part forced on (software GL) | 16.76 | +6.4% | 0 |

Scenario `neon_effects`: 30 frames of orbiting repaint the layer 0 times.

### 2. The self-check's false OK

`neon_selfcheck`:
- `_orbit` records per frame the main thread's processor time (`time.thread_time()`) and the
  clock time, and the layer's paints and painting ms (`neon_effects.stats()`), and the rolling
  band's frames (`neon_effects.band_steps()`), so band repaints are told apart.
- Runs: off, every effect on (band off), + the rolling band, + Sounds (the app-wide sound event
  filter on), + Hologram, and on software GL "3D-view part forced on". Each run's 120 frames are
  taken in 6 blocks of 20 in turn with the others (sandbox noise between whole runs was ±10%).
- Before the first run it waits for the window to be quiet (a design that just opened slides its
  timeline panel in for a moment: those repaints were counted as the orbit's before).
- The verdict uses processor time; a note says when the clock times sit at the screen's refresh
  rate. The report ends with "VERDICT: the effects fit / are OVER the speed budget on this
  computer ..." and a line on the band.

### 3. Resize stutter

- `build_still` is made in device pixels with whole-pixel strips (fractional strips at 150% cost
  tens of ms); the CRT edges fill only their 22-pixel strips; the corner shade is made once at
  96x96 and stretched/mirrored into the four corners; the glow halo is four gradient strips (Qt
  fills a tall 1-pixel strip row by row: 28 of them cost 15 ms).
- `tiles()` (pixel scanning in Python) is gone: the mask keeps the layer off the 3D views, and a
  paint copies only the rectangles Qt asks for.
- ViewStrength is no longer baked into the picture: the 3D views' part applies it as
  transparency.
- A resize restarts a 200 ms single-shot (`settle`); until it fires the old picture is stretched;
  then the picture and the views' textures are made once.

| | before (reviewer) | now |
|---|---|---|
| still picture 1920x1050 | 46 ms, on every resize event | 4-7 ms, once after the resize settles |
| still picture 2560x1400 at 150% | 69 ms, on every resize event | about 10 ms, once |
| 3D view texture | (none) | 1-2 ms picture + 2-6 ms texture, once |

Scenario: six resizes in a row make 0 pictures while resizing, then exactly one picture and one
texture.

### 4. Timers while minimised or inactive

- `neon_glitch_core.held_back(state, waited_s)` (pure, unit-tested) decides what a due glitch
  that may not fire does: `drop` (inactive, testing, effects or glitch off: no timer runs),
  `retry` (busy: look again in `POLL_S` = 1 s) or `restart` (busy for `GIVE_UP_S` = 60 s: a fresh
  40-120 s delay).
- `_pause_or_go` (on `ActivationChange` and `WindowStateChange`): not active or minimised -> the
  glitch timer and poll stop and a due glitch is dropped; active again -> a fresh 40-120 s delay.
- In the tests (`FISSION180_SCENARIO_FILE`) no glitch timer runs at all (`force_due` still works).

Scenario: with another window active no effects timer runs; back, a fresh delay of 40-120 s
starts (`schedules` +1); a held-back glitch's poll interval is 1000 ms.

### 5. Repaint storms

- `ChildAdded` raises only for widget children, and only through one 0 ms single-shot
  (`_raise_soon`) shared by everything that asks in the same moment, FreeCAD's overlay panels'
  `ZOrderChange` included; `_raise_now` skips the raise when the layer is already the top child.
- Scenario: 20 `QTimer`s and 5 `QAction`s added to the main window raise 0 times; 5 widgets added
  in one go raise once (`stats()["raises"]`).

### 6. Glitch grab hitch

- `_grab_outside_views` copies only the parts of the strip outside the 3D views (`mw.grab(r)`
  per rectangle of the strip minus the views); over the views the strip stays clear (the wash,
  tear lines and blocks still cross it).
- New blocker `camera_moving` (`neon_glitch_core.BLOCKERS`): the active view's camera (position,
  orientation, height/angle/focal distance) compared between two looks; it must have been still
  for 0.6 s. Costs nothing per 3D frame (it is read only when a glitch is due). The first look
  counts as moving, so a glitch due right as orbiting starts waits one poll.
- Measured: in this Qt (6.8.3) a `grab()` of the main window did **not** make the 3D view draw a
  frame (a Coin callback node counted 0 renders; `view.redraw()` counted 1), so the hitch the
  reviewer saw may depend on the Qt version; the copy now avoids the 3D view anyway. The
  outside-only copy of a full-width strip took 1.2-1.9 ms against 2.7-4.2 ms for the whole strip.
- Scenario: the glitch strip's copy is clear (alpha 0) over the 3D view and opaque beside it;
  a glitch made due while the camera keeps turning (a timer turning it every 40 ms, as a
  SpaceMouse would) waits with `camera_moving` and shows once it stops.

### 7. Tests that sample colours

- `neon_effects.hidden_for_sampling()` (and `set_hidden(on)`): the layer paints nothing and the
  3D views draw one frame without their part (waited for: a grab of a 3D view copies its last
  frame in Qt 6.8). No setting, timer or repaint of the window changes.
- `look_compare.no_effects()` / `look_compare.grab(widget, rect=None)` wrap it (nothing happens
  outside Neon Lights). Used by `look_compare.window_image()` and wherever a Neon scenario samples
  colours from the main window or the 3D view: `neon_panels.seen/picture`, `neon_switch`'s
  extrude dialog check, `neon_bodies.pixel`, `neon_outlines.near_outline_on_screen`,
  `neon_scene._corners/_hue_at/_near`. Grabs of child widgets (ribbon, browser, menus) do not
  include the layer and were left as they were. No check's meaning changed.
- Scenario: a picture taken inside `hidden_for_sampling()` equals the picture with the effects
  switched off.

## Facts found (Qt / Coin / FreeCAD)

- `SoRenderManager.addSuperimposition(node)` works from pivy, and FreeCAD's 3D view draws it
  after the model (before FreeCAD's delayed annotations). It is not in `savePicture`. Its
  AUTOREDRAW did not redraw the view here after a field change: call `view.redraw()`.
- In Qt 6.8.3, `QWidget.grab()` of a `QOpenGLWidget` (or of the main window over it) copies the
  last frame; it does not draw a new one. Wait for `frameSwapped` after changing the scene before
  grabbing.
- `view.graphicsView().viewport()` comes back as a plain `QWidget` wrapper (no `frameSwapped`,
  no `grabFramebuffer`): `shiboken6.wrapInstance(getCppPointer(w)[0], QOpenGLWidget)` gives one.
- Coin's default transparency for FreeCAD (sorted triangles) sorts every see-through triangle
  every frame: an overlay of hundreds of quads needs its own `SoTransparencyType BLEND`.
- `SoComplexity.textureQuality` 0.5 = smooth without mipmaps; `SoSFImage.setValue(SbVec2s(w, h),
  4, bytes)` works in pivy, but `getValue()` fails on binary data (UnicodeDecodeError).
- `QWidget.setMask(QRegion())` means "no mask": an empty area needs a 1-pixel mask instead.
- Qt raster: a fill of a 1-pixel-wide tall rectangle costs about 0.5 ms (row by row); a gradient
  strip 21 pixels wide 0.6 ms in all. Fractional rectangles at 150% are much slower than whole
  pixels.
- The sound part's app-wide event filter added about 0-1% per orbit frame here.

## Tests

- `Fission180Tests/unit/test_neon_glitch_core.py`: 10 tests (new: `camera_moving` blocks;
  `held_back` drops for inactive/testing/off, retries slowly while busy, restarts after
  `GIVE_UP_S`; stoppers are blockers).
- Scenario `neon_effects`: 47 checks (the new ones are listed under each problem above).
- Scenario `neon_effects_selfcheck`: the new report lines, 6 runs of 120 frames, layer repaints
  only for the band's own frames, Sounds/Hologram/effects put back.
- Run before the commit (`tools/fission180/run_tests.sh`): `--only unit` all passed (with
  `test_theme_identity.py`); scenarios `look_unchanged` PASS (13), `neon_switch` PASS (27),
  `neon_effects` PASS (46), `neon_effects_selfcheck` PASS, `neon_scene` PASS (24);
  `tools/fission180/check_waits.py`: 0 fixed waits.
- Scenarios whose colour sampling I changed, compared with the same run on `sf/neon-integration`
  without my changes:
  - `neon_bodies`: the same 5 checks fail with and without my changes ("the design is not marked
    modified", "no view property changed ['Sketch.ShapeAppearance', 'Sketch.Transparency']"):
    already broken, not about colours.
  - `neon_outlines`: "the design is not marked modified", already broken (builder `effects`
    reported it too).
  - `neon_panels`: without my changes it fails "[v] the Data Panel's Upload is filled with the
    primary colour ['#b20029', '#9e0025']": the effects' corner shade darkened the sampled
    button. With my changes that check passes, and `field_glows` fails instead: "... brighter
    than a field without the focus (56, 94)" (it wants a gap of 40, it is 38). The only
    difference is that the picture is now taken without the effects, so that check was passing
    because the shade darkened the unfocused field. I did not change the check (builder
    `panels`' file; the focus glow itself needs to be a little stronger or the check's margin
    reconsidered: for the orchestrator).

## Files

- Changed (mine): `src/Mod/Fission180/fission180/neon_effects.py`, `neon_glitch_core.py`,
  `neon_selfcheck.py`; `Fission180Tests/unit/test_neon_glitch_core.py`;
  `Fission180Tests/gui/scenarios/neon_effects.py`, `neon_effects_selfcheck.py`.
- `diagnostics.py`: unchanged (the button calls `neon_selfcheck.run()` as before).
- Outside my list, as the task asked (item 7), one-line grab changes only:
  `Fission180Tests/gui/look_compare.py` (`no_effects`, `grab`, `window_image`),
  `Fission180Tests/gui/scenarios/neon_panels.py`, `neon_switch.py`, `neon_bodies.py`,
  `neon_outlines.py`, `neon_scene.py`.
- No shared (orchestrator) file touched; no FreeCAD file touched.

## Left open

- The verdict on real graphics cards still comes from Luca's self-check (design 6.13). Expected:
  the 3D-view part costs next to nothing on a GPU (two small draw calls); the sandbox can only
  measure it in software ("forced on": +6.4%).
- The moving scan band stays over budget (+13.5% here) and stays off by default. Making it cheap
  would mean drawing it only outside the 3D views at a lower rate or as part of the 3D view's
  frame; not done.
- The band is not drawn over the 3D views any more (it would need the view to draw 25 frames a
  second).
- FreeCAD's overlay panels floating over the 3D view get no effects now (they are inside the
  view's hole and above the view's own drawing).
