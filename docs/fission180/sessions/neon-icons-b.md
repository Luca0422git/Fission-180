# Neon Lights B5 "icons II" (builder `icons-b`), 2026-11-20

Branch `sf/neon-icons-b`. Plan task B5 (`docs/fission180/plan-neon-lights.md`), design 6.5.

## What I built

- Reviewed all **183 icons** of the 18 area files (`tools/fission180/icons_<area>.py`) on contact
  sheets, normal beside neon, at 56, 36 and 18 px in V and Johnny.
- Phase A's automatic converter reads well for most of them (isometric blocks become glowing
  wireframes, small marks stay solid; nothing lost at 18 px that the normal icon keeps). It reads
  badly for four kinds of drawing, which now have **50 hand-made `@neon_icon` recipes**:
  1. **Thick strokes** (a sheet drawn as a 4-5 px line, a 5 px ring): the glow made fat tubes
     and halos. Sheets are now a hollow double line (their two faces), rings two thin circles:
     `sm_hem`, `sm_join_bend`, `sm_rip`, `sim_pin`, `sim_bearing`, `sim_moment`,
     `sim_rigid_connector`, `sim_stage_running` (now an 8-segment spinner), `qa_plus`,
     `qa_profile`, `project`.
  2. **Solid discs and pages** (status discs, sheets of paper, clipboards): filled blobs. Status
     marks are now octagon badges with a thin check / cross / three dots; pages have a cut
     corner and thin text lines: `fp_finish`, `simr_finish`, `rebuild_finish`, `sim_stage_done`,
     `sim_stage_failed`, `sim_stage_waiting`, `sim_precheck(_ok/_warn/_error)`, `simr_report`,
     `simr_solver_data`, `simr_details`, `cam_post`, `cam_sheet`, `sim_job_status`, `sim_solve`,
     `sim_settings`, `sim_results`, `environment_map`.
  3. **Solid transport buttons** of the animation timeline (play, pause, to start/end,
     previous/next, loop) and the film-strip commands: thin outlines with a faint fill,
     angular loop arrows, cut-corner film frames with sprocket dashes.
  4. **The most-seen icons**: the three workspace icons `workspace_animation`,
     `workspace_simulation`, `workspace_manufacture`, the browser's `sim_study`, and the
     application bar (`qa_plus`, `qa_profile`, `project`).
- The other 133 area icons keep the automatic neon version (judged fine on the sheets).

## Files (all new, mine)

- `tools/fission180/icons_neon__kit.py`: the shared `nb_` helpers (glowing line / path /
  polygon / circle, cut-corner rectangle, HUD brackets, isometric wireframe box, page, octagon
  badges, check / cross / warn / plus badges, hatched ground, segmented bar, `nb_sheet`). The
  **double underscore** makes it sort (and so run) before the `icons_neon_<area>.py` files,
  because recipes use its constants as default arguments. Every name is prefixed `nb_` / `NB_`
  so it cannot clash with B4's `icons_neon_core.py`.
- `tools/fission180/icons_neon_animation.py`, `_beta3.py`, `_flatpattern.py`,
  `_manufacture.py`, `_rebuild.py`, `_sheetmetal2.py`, `_shell.py`, `_simresults.py`,
  `_simulation.py`, `_surface3.py` (recipes).
- Generated `src/Mod/Fission180/fission180/icons/neon/*.svg` (only my 50 changed).
- Contact sheets: `docs/fission180/images/neon/icons-areas-v-36.png`, `icons-areas-v-18.png`,
  `icons-areas-johnny-36.png`, `icons-areas-johnny-18.png` (all 183 area icons, normal | neon
  pairs) and `icons-areas-hand-v-56.png` (the 50 hand-made ones, larger).

No file outside my list touched. `make_icons.py` and `neon_icon_style.py` not edited.
`icons/ui/` is byte-identical (after each run `icons/ui/split_body.svg` was restored as the
brief says).

## Facts found

- `make_icons.py` execs the `icons_*.py` files in sorted order into one namespace: a helper used
  only *inside* a recipe can live in any file (it is looked up when the icon is drawn), but a
  name used at module level (a default argument, a constant) must come from a file that sorts
  earlier. `icons_neon__kit.py` sorts before `icons_neon_animation.py` (`_` < `a`).
- The plan says 183 icons; the 18 area files indeed register 183 (`grep -c '@icon('`).
- Hand recipes are not run through `neonize`, so they must write tokens only (`#n3000k`):
  `test_tokens_only` catches a stray `#rrggbb`.
- The ground token `#n30006` drawn over a coloured stroke makes a hollow line (used by
  `nb_sheet`); it follows the preset's background, so it stays correct in every preset.

## Suggestions for `icons-a` (not done, their files)

- `neon_icon_style.neonize` could cap the glow width for strokes wider than ~3 px (for example
  glow = w + 2.6 instead of 2.4 w + 0.8): every thick-stroke area icon I hand-drew was only
  needed because of that.
- `neon_icon_sheet.py` prints Fontconfig warnings with the AppImage python; harmless.

## Tests

- `test_neon_icons`, `test_theme_identity`: pass before each commit.
- `run_tests.sh --only unit` (with FreeCAD, so `test_theme_identity` ran in full): 4061 tests, OK (10 skipped), "all passed".
