# Neon Lights wave (2026-11-20): rules for every builder

Luca (the owner, a beginner at software engineering, who tests and does not code) wants a
third look for Fission 180 called **Neon Lights**: a full cyberpunk overhaul of every part of the
window, so that people walking past his screen ask "what program is he using? that looks
sick!". He loves the current look: **Dark and Light must not change at all.** In his words: "I
like the current look of Fission. Dont change any of that. Only make changes to the NEW themes".
He wants it **all in one update**, not in pieces.

Read first, in this order:
1. `CLAUDE.md` (every rule applies, **except** the branch rule below).
2. `docs/fission180/neon-lights-design.md`: the approved design. Sections 3 (goals, non-goals,
   anti-goals) and 6 are your spec.
3. `docs/fission180/plan-neon-lights.md`: Global Constraints, Review Focus, the Phase A
   interfaces (A1-A7, already built), and **your task** (B1-B10).
4. `docs/fission180/dev/gui-tests.md` (how GUI scenarios wait for state, never for time).
5. `MEMORY.md` is 8,900 lines: do not read it whole; `grep` it for your files.

## Branches (overrides CLAUDE.md for this wave)

- Start from `sf/neon-lights`. Work and push **only** on your own branch `sf/neon-<id>`
  (`git push -u origin HEAD:sf/neon-<id>`). **Never push to `develop`, `Release` or
  `sf/neon-lights`**, never open a pull request. The orchestrator merges your branch.
- Do not edit `MEMORY.md`, `CHANGELOG.md` or `VERSION`: write your report to
  `docs/fission180/sessions/neon-<id>.md` instead (what you built, what you could not and why,
  facts you found about FreeCAD/Qt/Coin, every file outside your list you touched and why,
  screenshot file names). The orchestrator folds it into MEMORY.md.

## Builders and their ids

| Task | id | Owns (see the plan for the full list) |
|---|---|---|
| B1 | `chrome` | `neon_qss_chrome.py`, `neon_frames.py`, `neon_popups.py`, `neon_style.py`, `tips_ui.py`, `parameters_complete.py` |
| B2 | `shell` | `neon_qss_shell.py`, `ribbon_ui.py`, `browser_ui.py`, `timeline_ui.py`, `navbar_ui.py`, `doc_tabs.py`, `viewcube_ui.py` |
| B3 | `panels` | `neon_qss_panels.py`, `home*_ui.py`, `data_panel_ui.py`, `taskui.py`, `sketch_palette.py`, `measure_ui.py` (boxes), `marking_menu.py`, `sketch_marking.py`, `ai_panel_ui.py`, `animation_timeline_ui.py`, `search_ui.py`, `simulation_results_view.py` (its `is_light` uses) |
| B4 | `icons-a` | `tools/fission180/make_icons.py`, `tools/fission180/neon_icon_style.py`, new `tools/fission180/icons_neon_core.py` |
| B5 | `icons-b` | new `tools/fission180/icons_neon_<area>.py` files for the 18 area icon files |
| B6 | `bodies` | `neon_view.py`, `capture_ui.py`, new `neon_shader.py` |
| B7 | `scene` | `neon_scene.py` (new part, already in `neon.PARTS`), `grid_ui.py`, `sketch_mode.py`, `handle_look*.py`, `handles3d.py`, `cut_preview.py`, `origin_look.py`, `profile_pick.py`, `protractor.py`, `draft_live.py`, `live_shapes.py` (`cut_look`), `orbit_ui.py`, `display_ui.py` (background), the colour constants of the other 3D files |
| B8 | `effects` | `neon_effects.py`, new `neon_glitch_core.py`, new `neon_selfcheck.py`, `diagnostics.py` |
| B9 | `extras` | `neon_boot.py`, `neon_sound.py`, `neon_home.py`, new `tools/fission180/make_sounds.py`, `fission180/sounds/` |
| B10 | `settings` | new `neon_prefs_ui.py`, `preferences_ui.py`, `prefs_core.py` |

Files of the orchestrator (`theme.py`, `neon.py`, `neon_palette.py`, `neon_settings.py`,
`fission180/__init__.py`, `M/CMakeLists.txt`): change them only when your task truly needs it,
with the smallest additive change (a new palette key, a new install rule), and list it in your
report under "Shared files touched". Another builder's file: only a one-line hook your task
names; list it too. Generated `fission180/icons/neon/*.svg`: conflicts there are resolved at the
merge by running `tools/fission180/make_icons.py` again, so commit them freely.

## What Phase A built (use it, do not rebuild it)

- `theme.is_neon()`, `theme.name()`, `theme.palette()` (DARK's keys plus neon keys:
  `primary, secondary, alert, outline, background, primary_dim, primary_hot, secondary_dim,
  secondary_hot, glow, panel, grid_minor, grid_major, select, preselect, arrow, arrow_hot, cut`).
- **`theme.neon(role, literal)`** and **`theme.neon3d(rgb, role)`**: return the literal unchanged
  unless Neon Lights is on. This is how painted code (QPainter, Coin colours) gets neon colours
  while Dark and Light keep their exact values. Never branch on `is_neon()` in a way that could
  change a Dark/Light value.
- `theme.translate()` already maps the dark, light and `_EXTRA` colours of every panel's own
  style sheet to the neon palette and back exactly (`theme.NEON_SWAP` turns white boxes with
  near-black text into neon fields). Colours not in those tables stay as they are in Neon
  Lights: find them in your files and route them through `theme.neon()`.
- `theme.refresh_neon()` re-applies everything after a preset/colour change;
  `theme.LISTENERS` lists modules whose `theme_changed()` runs on every switch (append yours
  in `theme.py` with a one-line change if you need it). `theme.normal_look(True)` makes
  `neon()`/`neon3d()` return the normal colours (used while a save draws the preview picture).
- `neon.py` switches the parts in `neon.PARTS` together (`enable/disable/refresh`); a part that
  raises is switched off and listed in `neon.failed()`.
- `neon_settings.get/put` (keys in `DEFAULTS`), `neon_settings.current_roles()`.
- `neon_style.qss(p)` joins `neon_qss_chrome/shell/panels.qss(p, frames, fonts, translucent)`;
  `neon_frames` draws the nine-slice pieces; `neon_popups.compositing()` decides see-through
  pop-ups (`FISSION180_NEON_OPAQUE=1` forces solid; xvfb has no compositor, so tests see solid
  pop-ups).
- `neon_icons.path(name)` (used by `ui_icon_path` in neon); `tools/fission180/make_icons.py`
  writes `icons/ui/` and `icons/neon/`; `tools/fission180/neon_icon_sheet.py` renders contact
  sheets (`<freecad>/usr/bin/python tools/fission180/neon_icon_sheet.py out.png v 36 [names]`).
- `neon_view`: body outline override nodes (`EDGE_NODE`), `add_save_hook(before, after)`,
  `hologram()`, `set_hologram(on)`.

## Facts found in Phase A (they will save you time)

- **Dark/Light guard:** `tools/fission180/theme_identity.py` (+ unit test
  `test_theme_identity.py`) fingerprints Dark/Light, and scenario `look_unchanged` compares
  screenshots of Dark and Light with `Fission180Tests/fixtures/look_baseline/`. **Run both
  before every commit. Never re-record or edit the fixtures to pass.** `neon_switch` must stay
  green too.
- `make_icons.py` regenerates `icons/ui/split_body.svg` differently from the committed file (an
  old hand edit): after running it, `git checkout -- src/Mod/Fission180/fission180/icons/ui/split_body.svg`.
- In a style-sheet template, never give a frame rule the same `format` name as a palette key
  (`field`, `button`, `panel`, `header`...): a border-image landed in a `background:` and Qt
  silently dropped **every rule after it** (the window turned white). `test_neon_style.py`
  checks colour properties now. To find a rule Qt rejects, apply the rules one by one in an
  offscreen `QApplication` and look for "Could not parse".
- A widget's own style sheet beats the app style for the same property, but properties it does
  not set (a `border-image`) still come from the app style.
- FreeCAD's overlay task panel grabs see-through on its own: sample colours from
  `Gui.getMainWindow().grab()` at the panel's mapped position. `Gui.Control.activeDialog()`
  returns True/False, not a dialog. A design's tab is shown again by clicking it in
  `h.document_tabs()`.
- `Fission180Tests/gui/look_compare.py` has `set_look(name)`, `setup()` (a box design),
  `make_round(look, prefix)`, `group_label(id)`, `compare(name, image)`.
- Qt's SVG renderer is SVG Tiny: no filters/blur. Glow = a wider, fainter copy under a line.
- `make_ai_docs.py` must be re-run when a `docs/fission180/*.md` file changes
  (`test_ai_docs_contract`).

## How to work

- Set up: `tools/fission180/get_freecad.sh`, then `tools/fission180/run_tests.sh --only unit`
  and your scenarios with `--scenario a,b` (each twice; `--stress` for timing-sensitive ones).
- Test first where it is pure logic (`T/unit/test_*.py`, stdlib unittest); a GUI scenario for
  every surface you change, checking colours on screen in Neon Lights (V and one other preset)
  and that Dark is unchanged after a round trip.
- Take screenshots of your surfaces in V and Johnny with `h.shot()` and copy the best 2-4 into
  `docs/fission180/images/neon/<id>-*.png` (they go to Luca).
- Make it look genuinely cyberpunk (Luca's references: neon HUD frames with cut corners and
  bracket marks, hazard stripes, glowing thin lines, segmented bars, dark translucent glass,
  uppercase letter-spaced labels), never like a recoloured Dark, and never at the cost of
  readability or speed (Global Constraints).
- Commit small and often on your branch; push at least every hour and at the end.
- When done: final run of `--only unit`, `look_unchanged`, `neon_switch` and your scenarios,
  write the report, push, and end with a short summary (what works, what does not, files).
