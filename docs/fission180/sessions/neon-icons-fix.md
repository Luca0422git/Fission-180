# Neon Lights icon fix round (builder `icons-fix`), 2026-11-20

Branch `sf/neon-icons-fix` (from `sf/neon-integration` at `2145969c`, where icons-a and icons-b
were merged). Fixes the six problems of the independent icon review. In plain words: every neon
icon is now drawn with the same pen (the same line thickness and the same glow), warning red is
only used where something really is a warning, and the icons that turned into blobs at small
size are redrawn by hand.

## What I changed

**1. Warning colour (alert) only where it means a warning.** `neon_icon_style.role()`:

- gold, orange and yellow of the normal icons are now accents (`secondary`), never `alert`;
- red is `alert` only in icons whose red means warn / delete / fail or the hot end of a result
  scale (`ALERT_MEANING`: delete, cancel, remove, surfmod_delete, mesh_delete_faces (its
  deleted face only), interference, sim_precheck_error, sim_stage_failed, the stress / analysis
  maps and every `simr_*`); everywhere else red is an accent (all 13 `c_*` constraints, loads,
  normals, anim icons...); the warning yellow `#ffcc33` is always alert;
- on the MESH tab the gold mesh is the object, so it is `primary`, like icons-a's hand-made mesh
  icons beside it (`GOLD_OBJECT = ("mesh_",)`);
- `neonize(body, name)` now gets the icon's name from `make_icons.write_neon()` for this.
- Hand-made defaults: `nb_mill` (workspace_manufacture, cam) is secondary; sim_moment, the
  anim_showhide bulb, anim_view's lamp, sm_rip's cut, ground's hatch, mesh_face_groups' second
  group no longer use alert. Alert stays in hand-made icons only for delete, trim-away,
  failed / error badges and the hot cell of result scales.

**2. One stroke / glow standard for the whole set.** In `neon_icon_style.py`: `LINE = 2.1`
(about 1 px at 18 px), `DETAIL = 1.4`, `glow_width(w) = min(2w + 0.9, w + 2.6)` (icons-b's cap,
so thick strokes get a tight halo), opacity 0.24. The converter uses it (glow, tubes), and the
converter's outlines of solid shapes sit on it too (`EDGE = 1.75` for a block's silhouette,
`FACE = 1.5` for a flat face: at full `LINE` the small blocks of the normal icons filled in at
18 px). `make_icons.py` imports `neon_icon_style` before it runs the recipe files, so the kit
reads the same numbers: the hand-made and automatic icons can no longer drift apart.

**One kit.** `tools/fission180/icons_neon__kit.py` is now the single drawing kit: icons-a's
helpers (`nl`, `npoly`, `ncut`, `nbox`, `nmesh`, `ndot`, `nhead`, `narrow`...) moved there from
`icons_neon_core.py`, plus `ncircle`, `noct`, `npage`, `ntransport`; icons-b's `nb_*` helpers
are now thin wrappers on them that map their 1.6 scale onto `LINE` (1.6 -> 2.1). So every one of
icons-b's recipes is on the standard without rewriting each one.

**3. Blobs at 18 px, redrawn by hand:** workspace_animation, workspace_manufacture,
workspace_simulation, sim_study, cam_post, cam_sheet, simr_report, simr_solver_data, nav_grid
(one line each way instead of a dense grid), insert_mesh / mesh_remesh / mesh_reduce (now three
different open drawings: a coarse patch coming in, an even grid with a cycle arrow, a triangle
split in four with a minus), new_component, shell, nav_pan, eye_off (full-weight dashed outline).
Also anim_view / anim_view_off (camera redrawn), sim_pin, sim_results, sim_precheck*. Every
mesh icon is lighter: `nmesh` now draws the hexagon and three diagonals only (the extra inner
triangle filled it in). Page text lines are 6.5 units apart (they merged at 5.5).

**4. Automatic icons that read badly, now by hand:** material, emboss (a raised letter on a
plate), mesh_shell, sim_bolt, pl_rule_fillet, pl_manage, pl_lip, rebuild_ai, rebuild_compare,
sm_rules, sim_attributes, insert_dxf / insert_svg / insert_step (line-art pages with a picture of
what they hold: a 2D profile, a curve with handles, a part), simr_convergence. Found on the full
review and also drawn: sphere, view_single, view_two_h, view_two_v, nav_viewports (solid grey
tiles).

**5. Missing ribbon icons, drawn:** sm_flange, sm_bend, sm_flat_pattern, sm_unfold, sm_refold,
sm_rules, pl_assign, pl_boss, pl_snap_fit, pl_lip, pl_rest, and sheet_metal_body (browser).
New files `icons_neon_sheetmetal.py`, `icons_neon_plastic.py`, `icons_neon_plastic2.py`;
additions to `icons_neon_sheetmetal2.py`, `icons_neon_flatpattern.py`, `icons_neon_rebuild.py`,
`icons_neon_simulation.py`, `icons_neon_simresults.py`. 149 icons are hand-made now (was 119).

**6. Consistency (one convention each):**

- play-back buttons: `ntransport()` draws every tl_* and anim_* button (white outlines over a
  faint primary fill; bars are thin outlined blocks, pause included);
- points: small solid **squares** everywhere (`ndot`; `ndiamond` is gone; `nb_dot` is a square;
  the converter turns a normal icon's small solid dot into a square);
- arrow heads: small **solid** triangles everywhere (`nhead` / `narrow`, `nb_arrow`, and the
  converter already kept the normal icons' solid heads solid). Solid, because the 300 automatic
  icons have solid heads and they read better at 18 px than open chevrons;
- cut corners: **top-left and bottom-right** everywhere (`ncut`'s default changed from
  top-right/bottom-left; `nb_cut` and the converter already did this). A page's folded corner
  (top-right) is a page, not a HUD cut, and stays.

## Tests

- `test_neon_icons`, `test_theme_identity` (with `FISSION180_FC_CMD` set, both tests ran): pass
  before each commit. `python3 tools/fission180/theme_identity.py`: "unchanged (440 keys)".
- `icons/ui/` byte-identical (`split_body.svg` restored after every `make_icons.py` run).
- `run_tests.sh --only unit` (with FreeCAD): 4118 tests, OK (11 skipped), "all passed".
- ruff (E, F): clean on my changes (two long lines in `make_icons.py` 362 and 840 were already
  there).

## Contact sheets (for Luca)

`docs/fission180/images/neon/icons-final-{v,johnny,red_pill}-{36,18}.png`: all 426 neon icons
in each preset, made with `neon_icon_sheet.py` (the 18 px sheets enlarged 2x, pixel for pixel, so
the small size can be judged on a big screen).

## Facts found

- Qt's SVG renderer (SVG Tiny) draws elliptical arcs (`A`) in paths fine, so circles are drawn
  as paths and glow like every other line.
- `make_icons.py` can import `neon_icon_style` before it execs the recipe files; a name used in
  a recipe file at module level (a default argument, a constant) must come from a file that sorts
  earlier, which is why the kit is `icons_neon__kit.py`.
- At 18 px a gap under about 2 canvas units between two lines closes once both have their glow;
  detail lines need at least 6 units between them.

## Files touched

All mine for this round: `tools/fission180/neon_icon_style.py`, `make_icons.py` (imports the
style module early; passes the icon name to `neonize`), `icons_neon__kit.py`, `icons_neon_core.py`,
`icons_neon_animation.py`, `_beta3.py`, `_flatpattern.py`, `_manufacture.py`, `_rebuild.py`,
`_sheetmetal2.py`, `_simresults.py`, `_simulation.py`, new `_sheetmetal.py`, `_plastic.py`,
`_plastic2.py`; generated `src/Mod/Fission180/fission180/icons/neon/*.svg`; the six contact
sheets; this report. No shared or other builders' files, no MEMORY.md.
