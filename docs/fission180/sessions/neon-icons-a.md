# Neon Lights B4: core neon icons (builder `icons-a`), 2026-11-20

Branch `sf/neon-icons-a` (from `sf/neon-lights` at `a419cafa`).

## What I built

**1. The automatic converter, tuned** (`tools/fission180/neon_icon_style.py`). It still draws
every icon that has no hand-made neon recipe (173 of the 242 core icons, and all 183 area icons).
Changes, each judged on contact sheets at 36 px and 18 px in V and Johnny:

- **Thinner glow:** the glow copy is now `2.0 x width + 0.9` at opacity 0.24 (was `2.4 x + 0.8`
  at 0.28). At 18 px the old glow merged close lines (pattern squares, gear teeth) into blobs.
- **White lines glow in the primary colour:** a white (text-role) line keeps its white core but
  its glow is the preset's primary colour, which is how a real neon tube looks (white-hot core,
  coloured halo). Gears, eyes, hands, arrows now look lit instead of grey and fuzzy.
- **Isometric blocks as one wireframe:** `make_icons.block()` writes three faces; the converter
  now recognises the three polygons (by the GREY/BLUE/DBLUE/PURPLE/GOLD face triples and by
  checking the shared corners) and draws one glowing silhouette, three thin inner edges and
  faint faces (top brightest). Before, each face was outlined separately, so every shared edge
  was drawn twice with two glows and blocks buzzed at 18 px. 83 icons use this.
- **Wide strokes become hollow tubes:** a stroke 4 px or wider (pipes, springs, bent tubes) is
  drawn as an outline tube (coloured edges, dark inside, faint fill) instead of a wide glowing bar.
- **Cut corners:** a large square-cornered flat panel (a solid `rect`, at least 7 x 7, not
  rounded) becomes a polygon with two opposite corners cut off (top-left and bottom-right), the
  HUD frame shape. Rounded rects (screens, pages) keep their shape.
- Face outlines use mitred (sharp) corners and a slightly lighter weight (1.25).

**2. 69 hand-made neon recipes** in the new `tools/fission180/icons_neon_core.py` (picked up by
`make_icons.py`'s existing `icons_*.py` loop, no change to `make_icons.py` was needed). Original
line art, nothing traced: angular shapes, cut-corner frames, HUD corner brackets, open chevron
arrow heads, square nodes, two-tone (primary = the object, secondary = what the tool does,
alert only for delete/trim-away/ground). The file has a small drawing kit (`nl`, `nbox`,
`ncut`, `nbrackets`, `narrow`, `nmesh`, `nplus`, `ncog`, ...) that `icons-b` may reuse in their
`icons_neon_<area>.py` files: every `icons_*.py` file is run in the same namespace and the
recipes are only called later (in `write_neon`), so the helpers are found from any file's recipe
whatever the file order (only top-level code in a file run before `icons_neon_core.py`, i.e.
`icons_neon_animation`, `..._beta3`, `..._components`, could not use them).

Icons drawn by hand:

- SOLID visible row: sketch_create, extrude, revolve, hole, pattern_rect, mirror, press_pull,
  fillet, chamfer, shell, combine, split_body, scale, move, new_component, offset_plane,
  measure, section, insert_component, canvas, insert_mesh, select.
- SURFACE: surface_extrude, surface_loft, patch, thicken, trim, surface_extend, stitch.
- MESH: mesh_tessellate, mesh_face_groups, mesh_repair, mesh_remesh, mesh_reduce,
  mesh_plane_cut, convert_mesh.
- PLASTIC (core ones): draft (plus extrude, fillet, shell, combine, press_pull above).
- UTILITIES: print_3d, export, parameters, ai_panel, freecad_tools, tl_settings.
- Navigation bar: nav_orbit, nav_lookat, nav_pan, nav_zoom, nav_zoom_window, nav_fit,
  nav_display, nav_grid.
- Browser: eye, eye_off, folder, document, units, box (a body), surface_body, sk_rectangle
  (a sketch), point, axis, offset_plane, ground, delete, panel_close.
- Timeline: tl_start, tl_prev, tl_play, tl_next, tl_end (the steps use the feature icons above).

How I found the visible rows: each ribbon tab's groups in `ribbon_config.TABS`, their `big`
labels resolved like `ribbon_ui.RibbonGroup.refresh` does (a submenu's first entry).

## What I did not do, and why

- **SHEET METAL and PLASTIC tools' own icons** (`sm_flange`, `sm_bend`, `sm_hem`,
  `sm_flat_pattern`, `sm_unfold`, `sm_refold`, `sm_rip`, `sm_rules`, `pl_assign`, `pl_boss`,
  `pl_snap_fit`, `pl_lip`, `pl_rest`) are drawn in area files (`icons_sheetmetal*.py`,
  `icons_plastic*.py`), which belong to `icons-b` (B5). I left them to B5 so the two builders
  never register the same `@neon_icon` (the later file would silently win). Those tabs' other
  visible icons (sketch_create, press_pull, extrude, fillet, shell, draft, combine,
  new_component, offset_plane, measure, section, insert_*, canvas, select) are hand-made here.
  **Orchestrator: please check B5 covered those 13.**
- Browser icons not in `make_icons.py` (`component`, `origin`, `saved_view`,
  `sheet_metal_body`, `mesh_body`) come from area files or other names; same reason.
- No GUI scenario: icons are files; the tests that guard them are unit tests.

## Tests

- `test_theme_identity` (both tests, sketch colours with `FISSION180_FC_CMD` set to the
  FreeCAD AppImage) and `test_neon_icons`: pass before each commit.
- `icons/ui/` byte-identical (after `make_icons.py`, `git checkout -- .../icons/ui/split_body.svg`
  as the brief says; `git status` shows no change in `icons/ui/`).
- `ruff` (E, F) clean on my two files; formatted with `black -l 100`.

## Contact sheets (for Luca)

In `docs/fission180/images/neon/`, each icon shown as normal | neon:

- `icons-core-hand-v-36.png`, `icons-core-hand-johnny-36.png`: the 69 hand-made icons at 36 px.
- `icons-core-hand-v-18.png`, `icons-core-hand-johnny-18.png`: the same at 18 px (picture
  enlarged 2x, pixel for pixel, so the small size can be judged on a big screen).
- `icons-core-all-v-36.png`, `icons-core-all-johnny-36.png`, `icons-core-all-v-18.png`,
  `icons-core-all-johnny-18.png`: all 242 core icons (18 px ones enlarged 2x).

## Facts found

- Qt's SVG renderer handles `stroke-opacity`, `fill-opacity` and `stroke-dasharray` fine at
  18 px; dashes shorter than about 2.2 canvas units vanish at 18 px.
- A stroke of 2.1 canvas units is about 1 px at 18 px (icons are framed to roughly a 35-unit
  viewBox); inner detail below 1.2 units disappears at 18 px.
- `make_icons.svg()` frames each neon icon to its drawing's bounds (`pad=2.5`), so a hand
  recipe must record its bounds (`_grow`/`_path_bounds`), as the helpers in
  `icons_neon_core.py` do; the glow reaches about 1.5 units past the line, which the padding
  covers.
- My converter changes also changed the generated neon files of the area icons (B5's area). That
  is expected: the merge regenerates them with `make_icons.py`.

## Files touched

- `tools/fission180/neon_icon_style.py` (mine), new `tools/fission180/icons_neon_core.py`
  (mine), generated `src/Mod/Fission180/fission180/icons/neon/*.svg`, new
  `docs/fission180/images/neon/icons-core-*.png`, this report.
- `tools/fission180/make_icons.py`: not changed (not needed). No shared or other builders'
  files touched.
