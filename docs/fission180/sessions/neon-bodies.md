# Neon Lights builder B6 `bodies`: 3D bodies (2026-11-20)

Branch `sf/neon-bodies` (from `sf/neon-lights` a419cafa). Plan task B6; design 6.6 and 6.13.

## In plain words (for Luca)

- In Neon Lights, every body's edges get a soft **glow**: a wider, see-through copy of the
  edge drawn underneath it. It only appears while the Glow effect is on, and you can't click
  it by mistake (clicks find exactly what they found without it).
- **Hologram bodies** (`neon_view.set_hologram(True)`; the switch in Preferences and the
  navigation-bar toggle belong to B10/B2) turn faces into dark, tinted, see-through glass with
  bright glowing edges. A **rim light** makes faces seen edge-on glow brighter in the outline
  colour. It is a small graphics-card program that runs only after a self-test at start
  passes; otherwise the glass is plain and the log says why. Hover and selection colours still
  show on glass faces.
- None of it touches your design: nothing is saved, the design is never marked modified, no
  undo step appears. The preview picture saved in the file is always the normal look.
- **Capture Image** gets a "Normal look" box (only in Neon Lights; Dark's dialog is unchanged).
  Unticked, the picture shows the neon screen with Hologram; ticked, it shows the normal look.
- Split viewports, a design opened later and bodies made later all get the effects. Switching
  to Dark removes every last piece.

## The Phase A open item: "the design is not marked modified"

It was **not** the look switch. FreeCAD's app-level `App.ActiveDocument.saveAs()` (what the
scenario used) does not clear the window's "modified" flag; only the GUI save does. So the
design was already "modified" before the switch, left over from the recompute. A diagnostic run
watched every property change and both flags: Dark->Light, Light->Dark and Dark->Neon change
neither the modified flag nor the undo count, and no view-provider or document property changes.
Fix (test only): `neon_outlines` clears the flag after its save and now also checks that no undo
step is added. `neon_bodies` and `neon_views` check the same around the glow, Hologram, a preset
change, saves and captures.

## What was built

| File | What |
|---|---|
| `F/neon_view.py` | Outline + glow + Hologram overrides per body, `normal_look()` context manager, `neon_nodes()`/`_strip()` (find/remove every `Fission180Neon*` node), `rim_light()`, GUI observer for new view providers, `slotFinishRestoreDocument` for opened designs |
| `F/neon_view_core.py` (new, pure) | Node names, `glow_style(width, strength)`, `colours(palette, hologram)`, `glow_wanted`, `rim_wanted` |
| `F/neon_shader.py` (new) | Rim-light GLSL (`program`, `set_colour`), `self_test() -> (ok, reason)` (cached per session; `FISSION180_NEON_NO_SHADER=1` forces the flat fallback) |
| `F/capture_ui.py` | "Normal look" check box (Neon Lights only), `save(..., normal=)` |
| `T/unit/test_neon_view_core.py` | 9 tests |
| `T/gui/scenarios/neon_bodies.py` | 38 checks (see its docstring) |
| `T/gui/scenarios/neon_views.py` | 10 checks: 4 split panes, a design opened later, a body made later, Dark leaves no node in any view |
| `T/gui/scenarios/neon_outlines.py` | the fix above (Phase A's file) |

### How it works (scene graph)

- **Glow**: a `SoSeparator` `Fission180NeonGlow` placed **first** in each body's `Edge` group:
  `SoPickStyle UNPICKABLE`, `SoLightModel BASE_COLOR`, override `OVERALL` binding, override
  material (outline colour, transparency `1 - 0.6 * GlowStrength/100`), override `SoDrawStyle`
  (line width = 5 x the body's `LineStyle` width, at least 8 px), then the body's own
  `SoBrepEdgeSet` (the same node, shared). It must come before the outline's override material:
  in Coin a material override cannot be overridden again further down. Drawn while
  `Effects` and `Glow` are on, and always on Hologram bodies.
- **Hologram**: `Fission180NeonHologram` (override material: diffuse/ambient = outline mixed 82%
  into the background, emissive = background with 12% outline, transparency 0.72) and an
  override `OVERALL` binding first in each `FlatRoot`, then the shared rim program
  `Fission180NeonRim`. Hologram edges are the outline colour mixed 25% toward white.
- **Removal** takes the named nodes out of `Edge`/`FlatRoot`, then walks the view provider's
  `RootNode` and removes any node whose name starts with `Fission180Neon` (whoever put it there).
- **Pictures**: the save hooks and `normal_look(doc)` share `_to_normal`/`_to_neon` (nodes off,
  `theme.normal_look(True)`, the Dark view background, the grid, the other parts' save hooks).
  While inside, recomputes do not put the nodes back.

## Facts found (FreeCAD / Coin / GL)

- `App.Document.saveAs()` from Python leaves `Gui.Document.Modified` as it was (the GUI save
  clears it). Tests that save through the App must clear it before checking "not modified".
- Coin's own `SoOffscreenRenderer` cannot get a context under xvfb ("glxglue_context_create_software():
  Couldn't create GLX context"). Drawing through a Qt `QOffscreenSurface` + `QOpenGLContext` +
  `QOpenGLFramebufferObject` and `SoGLRenderAction.apply` works (that's how FreeCAD's `saveImage`
  does it). The self-test does this, and restores the previously current context afterwards.
- Under a GLSL program on a `SoBrepFaceSet`, **the face colour and FreeCAD's hover/selection
  colours all arrive in `gl_Color`**. They never reach `gl_FrontMaterial.diffuse` or `.emission`
  (measured by drawing each one alone). A shader that ignores `gl_Color` loses highlighting.
- FreeCAD's default camera is orthographic: a rim shader must use (0,0,1) as the view direction
  there (`gl_ProjectionMatrix[3][3] == 1`); `-eye.xyz` gives a false gradient across flat faces.
- Split viewports are separate `View3DInventor`s sharing the view providers' scene, so overrides
  in the view providers reach every pane; a design opened from a file is named after the file,
  not after the name it was created with.
- The neon nodes survive recomputes, display-mode changes and preset changes (A7's finding holds
  for `FlatRoot` too).

## Decisions (please check)

- `RimLight` "auto" (the default in `neon_settings`) means **use the shader when the self-test
  passes**, as the plan says. The design says the shader should be on by default only once your
  two machines pass. If you want it off until then, change the default to `"off"` in
  `neon_settings.DEFAULTS` (orchestrator's file; I did not change it). It passes in the sandbox's
  software OpenGL (rim red 136 vs 24 without it).
- The fallback message ("rim light shader not used, Hologram is flat: ...") is a log line, not a
  warning: a machine without the shader is expected, not an error.
- "Export everything"'s screenshot (`export_ui.py`) is taken in the **normal look**, because the
  design says exports are untouched by the look. The other image callers follow Capture with the
  box unticked (the screen as it is), with no change needed:
  `animation_video.py:249` (video frames), `simulation_results_panels.py:1976` (animation frames),
  `:2781`, `:2840`, `:2873` (result images).

## Not done / for others

- No Preferences switch or navigation-bar toggle for Hologram (B10 / B2 call
  `neon_view.set_hologram(on)`; `neon_view.rim_light()` gives (used, why) for B8's self-check).
- Speed: the glow draws each body's edges twice. It can't be judged in software GL; B8's
  self-check should orbit with Glow on/off. If it costs too much, raise `GLOW_MIN_WIDTH` less or
  draw the glow only for the active body.
- Wide GL lines have square ends, so the glow pokes out slightly past corners (visible only
  zoomed in).

## Files outside my list touched

- `F/export_ui.py`: the "Export everything" screenshot in `neon_view.normal_look(doc)` (3 lines).
- `T/gui/scenarios/neon_outlines.py` (Phase A): the modified-flag fix asked for in the task.
- No shared/orchestrator file was changed.

## Tests (last run)

`run_tests.sh --only unit`: all passed. Scenarios `look_unchanged` 13, `neon_switch` 27,
`neon_outlines` 14, `neon_bodies` 38, `neon_views` 10: all PASS; `neon_bodies,neon_views` also
PASS under `--stress`; `check_waits` 0/0. The flat fallback (`FISSION180_NEON_NO_SHADER=1`) was
checked by hand: hover and selection pass. The only failures there are the two rim-light checks,
which expect the shader.

## Screenshots (`docs/fission180/images/neon/`)

- `bodies-hologram-v.png`: Hologram, preset V (rim light on).
- `bodies-hologram-johnny.png`: Hologram after a live switch to Johnny.
- `bodies-outline-glow-v.png`: outlines with the glow, V.
- `bodies-split-views.png`: Multiple Views, every pane with Hologram.
