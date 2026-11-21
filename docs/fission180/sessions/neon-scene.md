# Neon Lights builder B7 `scene`: the rest of the 3D view (2026-11-20)

Branch `sf/neon-scene` (from `sf/neon-lights` a419cafa). Spec: neon-lights-design.md 3 and 6.6;
plan task B7.

## What was built

**In plain words (for Luca):** in Neon Lights the 3D view's background is now a faint dark
gradient tinted by the preset; the grid, the X/Y/Z axes, sketch lines, the selection and
hover colours, the arrows, discs and balls of the commands, the cut and profile previews,
Measure's line and dots, the orbit dot and the origin squares all take neon colours from the
preset. Switching back to Dark puts every one of them back exactly as before, and the preview
picture saved inside a design is still the normal one.

- **`neon_scene_core.py`** (new, pure Python, unit tested):
  - `roles3d(p)`: every 3D colour role from a neon palette (the palette's keys plus scene roles:
    `rim`, `disc`, `disc_hot`, `disc_rim`, `dot`, `arc`, `ring`, `hot`, `pick`, `pick_fill`,
    `pick_glow`, `pick_edge`, `hover`, `cut_glow`, `cut_edge`, `rail`, `ghost`, `ghost_glow`,
    `preview`, `measure`, `snap`, `marker`, `marker_rim`, `bright`, `sketch_free`, `grid_text`,
    `hidden_edge`, `axis_x/y/z`).
  - `background(p)`: the gradient (top: the view colour lifted 8% toward primary and 3% toward
    secondary; bottom: 35% toward black).
  - `sketch_hex(p)` / `sketch(p)` / `SKETCH_PARAMS`: the neon sketch table (under-constrained =
    primary, fully constrained = near white, construction = alert, projected = primary/secondary
    mix, fixed = neon green, selection = `select`, hover = `preselect`, sketch grid =
    `grid_minor/major`, profile shade = secondary, alpha 0x60).
  - **`Live(rgb, role)`**: the mechanism for "every constant keeps its exact Dark value". A
    `tuple` subclass whose stored items, `==`, `hash` and `repr` are the Dark tuple, always;
    reading it (unpacking `*c`, `c[0]`, iterating, `tuple(c)`: what every Coin call and colour
    arithmetic does) gives the Dark value unless Neon Lights is on, then the neon colour of its
    role. While `theme.normal_look(True)` (a save drawing the preview) it reads Dark. So each 3D
    file changed only its constant definitions: `BLUE = Live((0.16, 0.50, 0.93), "arrow")`.
    `normal()` returns the plain Dark tuple (for values saved in a design).
- **`neon_scene.py`** (the part): `enable` sets `Gradient`, `RadialGradient`,
  `BackgroundColor2/3` through `theme.keep_and_set` under its own backup
  (`Mod/Fission180/NeonViewerBackup`), so `disable` gives back exactly the values Fission 180 had
  (the theme's own `ViewerBackup` keys are untouched). Registers `neon_view.add_save_hook`:
  before a save the views get the normal flat background and the sketch its Dark colours; after
  it (one 0 ms timer, because neon_view turns `normal_look` off right after the hooks) they are
  neon again. `theme_changed()` (added to `theme.LISTENERS`) redraws the grid and the views once
  right after leaving Neon Lights (the parts are switched off *before* the look changes, so a
  redraw during `disable` still read neon). `leftover()` cleans up the backup if a session ended
  in Neon Lights and the next one starts in Dark/Light (called from `display_ui.enable`).
- **`display_ui.py`**: `apply_background(viewer)` / `apply_backgrounds()` split out of
  `apply_view`. The "Theme" environment asks `neon_scene.gradient()` (None outside neon) and
  `neon_scene.flat_background()`; any other Environment (Photo Booth, Dark Sky...) is the
  person's choice and wins in every look. Every neon background change ends with
  `apply_backgrounds()`, so FreeCAD's own parameter observer and display_ui never fight.
- **`sketch_mode.py`**: `neon_table()`, `look(colour)` (a module colour such as `BLUE`,
  `GREEN`, `SELECT` in the look in use), `_COLOUR_NAMES`; `_all_params()` takes the neon table
  in Neon Lights; `theme_changed()` also sets the neon names. `PARAMS` and `LIGHT` are unchanged
  (the fingerprint passes). The fixed-geometry painter uses `look(GREEN/SELECT/HOVER)`;
  `sketch_draw.py` and `sketch_infer.py` use `sketch_mode.look(...)` for the curve being drawn.
- **`grid_ui.py`**: constants are `Live`; A7's `NEON_X/NEON_Y if neon` branch removed (it drew
  neon axes into the saved preview, since it ignored `normal_look`); the unused `theme` import
  removed.
- **`live_shapes.py`**: `cut_look` colours are `Live` (imported as `LiveColour`: the file has its
  own `class Live`); `colors()` gives a part's live picture the neon `outline` colour.
- **Constant sweep (Live)**: `handle_look_core` (arrow, hot, rim, disc, dot, arc, axis triad),
  `handles3d`, `cut_preview`, `profile_pick`, `protractor`, `origin_look.AXIS_RGB`, `orbit`
  (+ `orbit_ui.RIM`), `measure_ui` (LINE, DOT, SNAP only), `construct_ui`, `curve_pick`,
  `display_ui` (hidden edges), `extrude_to_face`, `hole_ui`, `hover_ghost`, `joints_ui`,
  `joints_limit_drag`, `move_ui`, `pattern_light`, `pattern_ui`, `pipe_ui`, `plastic_lip_ui`,
  `primitives_ui`, `revolve_ui`, `sketch_areas`, `sketch_axes`, `surface_iso_ui`,
  `surface_pick`, `surface_ui`, `text_ui`, `timeline_hover`, `rebuild_ui` (ghost only),
  `interference_ui` (RED), `animation_view` (TRAIL).
- **Tests**: `T/unit/test_neon_scene_core.py` (Live is exact outside neon, neon inside, Dark
  under normal_look; every role for every preset; gradient dark and two-tone; sketch table
  covers LIGHT's names and keeps free/done/selected/hovered apart for all 17 presets). Scenario
  `neon_scene` (24 checks): V background top and bottom equal the gradient, grid line colours,
  Extrude arrow colour (on its nodes), sketch parameters, `sketch_mode.look`, FreeCAD's gradient
  settings, a selected face's hue; Johnny changes them all; the preview saved in neon equals the
  one saved in Dark; Extrude and sketch-edit screenshots; back in Dark: parameters, background,
  arrow, grid and constants exactly as before.

## Results of the guards (final run)

- `run_tests.sh --only unit` (with FreeCAD: includes `test_theme_identity`'s FreeCAD part):
  4067 tests OK.
- `look_unchanged` PASS, `neon_switch` PASS, `neon_scene` PASS.
- `neon_outlines`: FAIL on one check, "the design is not marked modified", **identical on the
  untouched `sf/neon-lights`** (I ran it there with my changes stashed). The A7 commit message
  already names it as open for B6. All its other checks pass with my changes.

## Not done / decisions, and why

- **Legend colours kept**: simulation results, plastic advice, analysis maps, manufacture
  toolpaths, rebuild's red/green (missing/extra material), interference's contact orange,
  animation pins, joints' construction orange. Their colours carry meaning and match legends in
  the panels; changing them would hurt reading (anti-goal "too busy to model in").
- **Kept on purpose**: `drawing_ui.SHADED_FACE` (drawings stay normal), `appearance.OLD_GREY`
  (compared with what FreeCAD drew), `section_ui.HATCH`, `thread_ui.COLOR`, `sketch3d.BLUE`
  (it is written into the view-provider's `LineColor`, i.e. saved: must never be neon).
  `text_ui._style` writes `FILL.normal()` into the saved appearance for the same reason.
- **Inline literal colours** (a `setValue(0.3, 0.6, 0.9)` in a function body rather than a
  constant) in the ~50 3D files were not swept, only the constants (as the plan asks). They stay
  in their Dark colours in Neon Lights; a later sweep can turn them into `Live` constants.
- **Live re-colouring of shapes already on screen**: handles and previews built before a preset
  change keep the old preset until they are rebuilt (the next drag/hover/command). Persistent
  ones (grid, background, sketch, selection) follow at once.
- Arrow and picked profile have the same colour (`secondary`), as in Dark (both blue); so the
  scenario checks the arrow's colour on its Coin nodes rather than on screen.
- Measure's dot size issue from MEMORY.md's known issues: not touched (colours only).

## Facts found (FreeCAD / Coin / Python)

- `View3DSettings::OnChange`: **any** of `BackgroundColor`, `BackgroundColor2/3/4` pushes the
  background *and* the gradient colours from the parameters to every open viewer; `Gradient` /
  `RadialGradient` push the gradient mode. So `theme._view_background()` on a look switch resets
  a viewer's gradient colours to FreeCAD's parameters, overwriting display_ui's Environment until
  display_ui paints again (true in Dark before this work too, for non-Theme environments).
- `View3DInventorViewer::savePicture` (the thumbnail) draws the gradient node when the viewer has
  one, else the flat background colour: the save hook must switch the viewers to `NONE` itself.
- A `tuple` subclass with `__iter__`/`__getitem__` overridden: CPython's `f(*t)`, `a, b, c = t`
  and `tuple(t)` go through `__iter__` for a subclass (fast paths are for exact tuples only),
  while `==`, `hash`, `repr` read the stored items. pivy's `setValue(*c)` therefore sees the neon
  value. Verified in FreeCAD 1.1.4 (Python 3.11).
- neon parts are disabled before `theme._use()` changes the look, so a part redrawing in its
  `disable()` still sees `is_neon()` True; use a `theme.LISTENERS` entry for "after the switch".
- Editing a sketch (setEdit/resetEdit) after a save changes how the grid shows through the
  sketch's profile shade in the next saved preview (lines hidden under it), in neon at least;
  not a colour leak (the previews compared are Dark-coloured), not investigated further. The
  scenario compares the previews before it edits the sketch.

## Shared files touched

- `theme.py`: one line, `"neon_scene"` appended to `LISTENERS`.
- Other builders' files: `measure_ui.py` (B3 owns its boxes; I changed only its three 3D colour
  constants LINE/DOT/SNAP, per the plan's "Measure's dots and line").
- `neon_view.py` (B6): not touched; note for B6/orchestrator: `neon_view.disable()` calls
  `_grid()` while `is_neon()` is still True (harmless now, neon_scene's listener redraws after).

## Screenshots (docs/fission180/images/neon/)

- `scene-v-background-outlines.png`: V, gradient background, outlines, neon sketch profile.
- `scene-v-extrude-arrows.png`: V, Extrude open: neon grid and axes, arrow, angle disc.
- `scene-v-sketch.png`: V, sketch editing: neon curves, points, constraint glyphs, sketch grid.
- `scene-johnny.png`: Johnny, same design: everything follows the preset.

## Files

New: `fission180/neon_scene_core.py`, `Fission180Tests/unit/test_neon_scene_core.py`,
`Fission180Tests/gui/scenarios/neon_scene.py`, the four screenshots, this report.
Changed: `neon_scene.py`, `display_ui.py`, `sketch_mode.py`, `sketch_draw.py`,
`sketch_infer.py`, `grid_ui.py`, `live_shapes.py`, `orbit_ui.py`, `theme.py` (one line), and the
constants of the 33 files listed in the sweep above.
