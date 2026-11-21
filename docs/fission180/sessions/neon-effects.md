# Neon Lights builder `effects` (plan task B8): screen effects and the self-check

Branch `sf/neon-effects` (from `sf/neon-lights` a419cafa). Commit "Neon B8: screen effects and the
self-check".

## What I built

**`fission180/neon_effects.py`**: one see-through layer (`Fission180NeonEffects`), a child of the
main window, over everything in it. It never takes a click or the keyboard
(`WA_TransparentForMouseEvents`, `NoFocus`). It paints:

| Effect | What you see |
|---|---|
| Glow | a soft halo of the primary colour along the window's edges, with a thin secondary line along the top. `neon_effects.glow()` returns how strong it should be (0 to 1, 0 when Glow is off), for the parts that draw their own halo (frames, icons, body edges). |
| Scan lines | a dark 1-pixel line every third row. The optional slow rolling band (ScanBand, off by default) is a bright band that crosses the window in 9 s at 25 frames a second. It runs only while the window is active. |
| CRT | dark corners (a shade round each corner) and a faint curved-glass shading along the edges, plus a faint highlight just inside the top edge. |
| Glitch | every 40 to 120 s, for 80 to 150 ms: a strip of the window is cut into slices that jump sideways, with red and cyan fringes, a primary-colour wash and thin tear lines (screenshot `effects-glitch.png`). |

- Every effect has its switch and strength in `neon_settings`, plus the master `Effects` switch.
  `refresh()` applies changes at once. With the master switch off, or with nothing left to draw,
  the layer is removed.
- Over each 3D view everything is drawn at `ViewStrength`% (40% by default).
- **Speed**: the still layers (glow and CRT) are drawn once into a picture. It is made again only
  when the window's size, the 3D views' places or a setting change. The picture is cut into
  runs of 64-pixel pieces and the empty ones are left out, so the empty middle of the window
  costs nothing. Scan lines are pre-cut rectangles (one `drawRects` call, picked by binary
  search). See "Facts" below for why.
- **Pauses**: when the window is not active or is minimised, the rolling band stops and no glitch
  fires.
- **Safety**: an exception in a paint, timer or event filter is logged (`[Fission 180]`), the
  effects are switched off, and the part is listed in `neon.failed()`. This path was exercised for
  real during development and the window carried on.
- Switching to Dark or Light removes the layer, its event filters and all four timers (checked
  by the scenario).

**`fission180/neon_glitch_core.py`** (pure, unit-tested):
- `next_delay(u)` = 40 + 80u s and `duration(u)` = 0.08 + 0.07u s (u clamped to 0..1).
- `may_fire(state)` is False while any of these is true: `mouse_down, dragging, text_focus,
  task_dialog, recomputing, testing, inactive, effects_off, glitch_off`.
- `why_not(state)` lists which of them.

`neon_effects.flags()` reads those blockers from the app:
- `QApplication.mouseButtons()`;
- `handles3d.dragging()`, or an open pop-up menu (counted as a pick);
- an editable line edit, text edit, spin box or editable combo with focus;
- `Gui.Control.activeDialog()`;
- `drag_guard.recomputing()`;
- `FISSION180_SCENARIO_FILE` set (a test), unless `force_due()` allows it;
- the window not active.

`neon_effects.busy()` is the "a person is busy" subset of those.

A due glitch that is held back looks again every 250 ms and fires once the person is done.

**`fission180/neon_selfcheck.py`** and the **Neon self-check** button in Fission 180 > Diagnostics:
1. Makes a temporary design (`Fission180NeonSelfCheck`) with a "circuit board" of 500 blocks, which
   is exactly 3,000 faces.
2. Orbits it 120 frames (after 10 warm-up frames) three times: effects off, every effect on, and
   effects with Hologram on (`neon_view.set_hologram`).
3. Reports the median, mean, 95th-percentile and worst time per frame, and how long the layer's
   own painting took.
4. Measures idle CPU for 5 s with the effects off and 5 s with them as set.
5. Reports the rim-light shader's self-test (`neon_shader.self_test`). Builder `bodies` had not
   made it on my branch, so the report says "not in this version". It accepts a bool, a tuple
   `(ok, why...)` or a dict `{"ok"/"passed", "why"/"reason"}`, and a test that raises is reported
   as FAILED with the exception.
6. Lists `neon.failed()`, plus the platform, window system, screen, and the graphics card and
   driver (from a small OpenGL context of its own).

Afterwards the sample design is closed without saving, the design that was active comes back, and
the Hologram and effect settings are put back. The text appears in the Diagnostics box, ready to
copy. Outside Neon Lights it measures only the "off" run and says so.

## Tests

- `Fission180Tests/unit/test_neon_glitch_core.py` (6 tests): delay and duration bounds, out-of-range
  and NaN input, every blocker blocks on its own, several at once.
- Scenario `neon_effects` (21 checks): one layer over the whole window, on top, transparent for
  the mouse, no focus. `QApplication.widgetAt` over the body is the 3D view and not the layer.
  The layer's pixels over the 3D view are about 40% of those over the ribbon.
  - **A click delivered to the main window's own `QWindow`** (so Qt itself finds the widget under
    the pointer, as with a person's click) selects the body.
  - A glitch made due while the mouse button is held does not fire; it fires after the release.
  - The same while a text field has focus.
  - A glitch frame screenshot.
  - Idle for 3 s with ScanBand off: 0 paints, 0 update requests, 0 rebuilds.
  - Effects off: the layer is gone. On again (Johnny preset): it is back.
  - Dark: no layer, no timer or filter left.
- Scenario `neon_effects_selfcheck` (19 checks): clicks the real Diagnostics button, checks every
  part of the report, that the sample design is closed, the old design is active again, and
  Hologram and the effects are back as set.
- Run before the commit: `--only unit` (all pass, including `test_theme_identity.py`),
  `look_unchanged` (pass), `neon_effects` and `neon_effects_selfcheck` (pass, run several times).
  `tools/fission180/check_waits.py`: 0 fixed waits. `check_install.sh`: all files installed
  (the new `.py` files are covered by the existing `fission180/*.py` glob).
- **Already broken before my work** (same result with my changes stashed, on `sf/neon-lights`
  a419cafa):
  - `neon_outlines` fails twice with "the design is not marked modified".
  - `neon_switch` is FLAKY: "dark-window looks as before 0.84% of pixels differ" and dark-extrude
    1.01%, then it passes in a fresh profile.

  Neither involves the effects layer (it is not in the Dark pictures). I did not touch them.

## Speed: what the sandbox says, and what Luca needs to check

The sandbox draws the 3D view in software (Mesa llvmpipe), on the same CPU as everything else, so
frame times swing from run to run. Over five runs, "effects add" came out at +7%, +8%, +14%, +23%
and +24% per frame. The steadier number is the layer's own painting: **about 1.0 ms a frame**
(4.6% of a 23 ms frame). The rest of the difference is Qt putting the window together and noise.

- Idle CPU added by the effects: **+0.1% of a core** (budget about 2%).
- How painting got to 1 ms: drawing the layer as one picture cost 0.6 ms in a micro-benchmark,
  but the first piece-by-piece version cost 6 ms in the app (300 small copies a frame). Merging
  pieces into runs and drawing scan lines as rectangles brought it to 1.0 ms (0.47 ms pieces,
  0.50 ms scan lines).
- **The verdict on the 10% budget has to come from Luca's machines** (design 6.13). A fast GPU
  draws a frame in a few milliseconds, and the layer is painted by the CPU.
- If the self-check says OVER BUDGET there, the cheap fixes are already in:
  - `ViewStrength` 0: nothing at all is painted over the 3D view, so orbiting costs nothing extra;
  - Scan lines off: that is half of the per-frame cost.

  The next step, if needed, is to draw the 3D-view part inside the Coin scene, on the GPU (a
  bigger change, not done).

Sandbox report, effects as delivered:

```
Graphics: Mesa | llvmpipe (LLVM 20.1.2, 256 bits) | OpenGL 4.5 (Compatibility Profile) Mesa 25.2.8 (compatibility)
Sample part: 3000 faces, 120 frames per run, 3 degrees a frame
  effects off                median  22.99 ms  mean  22.65 ms  95%  27.63 ms  worst  35.36 ms  (120 frames)
  every effect on            median  26.29 ms  mean  26.13 ms  95%  34.17 ms  worst  71.10 ms  (120 frames)
      of which layer painting    1.06 ms a frame (83 paints), 4.6% of a frame with effects off
  effects + Hologram on      median  27.72 ms  mean  26.40 ms  95%  33.65 ms  worst  43.52 ms  (120 frames)
  effects off          2.5%  /  effects as set  2.6%  ->  +0.1% of a core
```

## Facts found (Qt / FreeCAD)

- A child widget stacked over the 3D view's `QOpenGLWidget` is repainted on **every 3D frame**, for
  the whole view rectangle (Qt has to put the window back together). So the cost of whatever is
  painted over the view counts per frame, not once.
- In Qt's raster engine:
  - cosmetic `drawLines` (1.1 ms) and tiled brushes or `drawTiledPixmap` (1.2 ms) are much
    slower than solid `drawRects` (0.25 ms) for the same scan lines on 1800x1000;
  - hundreds of small `drawPixmap` calls from Python cost more than one big one.
- PySide6's `QRegion` has no `rects()`; iterate the region itself (`for r in region`).
- FreeCAD's overlay panels (`Gui::OverlayTabWidget`, e.g. `OverlayRight`) raise themselves above
  later siblings. The layer watches them for `ZOrderChange` and goes back on top.
  `QWidget.raise_()` sends `ZOrderChange` only to the raised widget, so there is no loop.
- `FreeCADGui` has no `activateDocument`; use `Gui.setActiveDocument(name)`.
- `QWidget.grab()` of the main window includes the effects layer. The layer paints nothing while
  it grabs its own glitch strip. **Note for other builders and the orchestrator:** scenario
  colour checks that sample `Gui.getMainWindow().grab()` in Neon Lights now see the scan lines
  (a darker row every third row, alpha up to about 52 at the default 35% strength) and corner
  shading. Sample a row where `y % 3 != 2`, or grab the widget itself (a child widget's own
  `grab()` does not include the layer).
- The harness counts "failed", "error" and "invalid" in the Report view as test errors. The
  self-check therefore logs only one line, and its report says "switched off", not "failed".
- QTest on the main window's `QWindow` (`QTest.mousePress(window().windowHandle(), ...)`) goes
  through Qt's own routing to the widget under the pointer: the right way to test click-through.
  `QTest` on a widget skips that routing.
- PySide6 `QOpenGLContext.functions().glGetString()` returns a `str`, and works on a context and
  offscreen surface of our own (shared with the global share context).

## Shared files touched

None. One read of another module's private state: `_fail` writes
`neon._state["failed"]["neon_effects"]` so a failing effect shows in `neon.failed()` without
waiting for the next `neon.enable()`. A public `neon.mark_failed(part, why)` in `neon.py` would be
cleaner; the orchestrator may want to add it.

## Files

- New: `src/Mod/Fission180/fission180/neon_glitch_core.py`, `src/Mod/Fission180/fission180/neon_selfcheck.py`,
  `src/Mod/Fission180/Fission180Tests/unit/test_neon_glitch_core.py`,
  `src/Mod/Fission180/Fission180Tests/gui/scenarios/neon_effects.py`,
  `src/Mod/Fission180/Fission180Tests/gui/scenarios/neon_effects_selfcheck.py`
- Changed: `src/Mod/Fission180/fission180/neon_effects.py` (was the scaffold),
  `src/Mod/Fission180/fission180/diagnostics.py` (the "Neon self-check" button; Copy now copies
  whatever the box shows)
- Screenshots in `docs/fission180/images/neon/`:
  - `effects-v.png`: V, with glow edge, scan lines over the box and dark corners;
  - `effects-glitch.png`: a glitch frame;
  - `effects-johnny.png`: Johnny.

## Not done or left open

- The rim-light shader self-test line can only say "not in this version" until builder `bodies`'
  `neon_shader.py` is merged. The handling of its result is written for the likely shapes and
  never raises.
- "A pick going on" is covered by: the mouse button held, `handles3d.dragging()`, an open pop-up
  menu, and command dialogs (`task_dialog`). There is no FreeCAD-wide "picking" flag to read
  beyond those.
- Whether the effects meet the 10% budget on real graphics cards: Luca's self-check decides
  (above).
