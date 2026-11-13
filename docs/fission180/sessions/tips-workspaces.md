# Wave 8, builder tips-workspaces: Fusion-style tooltips for the workspace tabs

Luca (2026-11-13): "Fusion has this feature that when you hover over a tool, it displays a
tooltip on how it works, what it does, and how to execute it, along with a picture. EVERY
tool needs this." Brief: `docs/fission180/dev/briefs/tips.md`. This builder wrote the
tooltips, and made the pictures, of the MESH tab (19 commands), SHEET METAL (14) and its FLAT
PATTERN tab (2), PLASTIC (8), the SIMULATION workspace's SETUP (16) and RESULTS (23) tabs,
MANUFACTURE's MILLING tab (21) and ANIMATION (10): **113 commands**. The tooltip widget, its
timing and the Preferences option are builder tips-ui's (`fission180/tips_ui.py`,
`tips/__init__.py`, `docs/fission180/parity/tooltips.md`).

## What was built

| File | What |
|---|---|
| `fission180/tips/mesh.py` | 19 entries (MESH; Insert Mesh is on SOLID's INSERT too, so it is in `tips/solid.py`) |
| `fission180/tips/sheet_metal.py` | 16 entries (SHEET METAL's own commands, FLAT PATTERN's Export DXF and Finish Flat Pattern; the SOLID commands the tab repeats are in `tips/solid.py`) |
| `fission180/tips/plastic.py` | 8 entries |
| `fission180/tips/simulation.py` | 39 entries (SETUP 16, RESULTS 23; Manage Physical Materials and Measure are SOLID's) |
| `fission180/tips/manufacture.py` | 21 entries (the greyed Thread / Scallop / Pencil / Spiral / Radial have no command and keep their "Not in Fission 180" note) |
| `fission180/tips/animation.py` | 10 entries |
| `fission180/icons/tips/{mesh,sm,fp,pl,sim,simr,cam,anim}_*.png` | the 113 pictures, 320 x 200, 6 to 45 KB |
| `tools/fission180/tip_pictures_{mesh,sheet_metal,plastic,simulation,manufacture,animation}.py` | the scripts that make them (`make_tip_pictures.sh <module>`) |
| `tools/fission180/tip_pictures_workspaces.py` | what those scripts share: the design-step builder on the demo design, a camera with Z up (`look`), a task panel grab without its empty bottom (`trim_panel`) |
| `Fission180Tests/gui/scenarios/tipsws_hover.py` | the GUI check: real pointer on five of these commands, their own expanded tooltips |
| `docs/fission180/dev/tips-workspaces-sheet.png` | the contact sheet of the 113 pictures (for the merger) |

Each entry: `summary` (<= 110 characters, one sentence), `what` (<= 400, 1 to 3 sentences),
`steps` (2 to 6, each <= 120), `tips` (0 to 3) and `picture`. The texts were written from each
command's own dialog code (the labels, the order of the boxes, what is refused and why), so
a step names the field the person sees ("Click Create Study", "Geometry tab: click the
pocket's floor face"). Everything a step claims was looked up: field labels
(`self.combo("Repair Type", ...)`), button texts (`+ New Set`, `Save Rule`, `Remove Slice`),
defaults (Stitch and Remove, Prismatic, Automatic), what happens with nothing picked (Restore
Home refuses, a CAM operation makes a setup, Simulate plays the active setup) and what runs
by itself (Post Process and Simulate generate out-of-date toolpaths first).

## How the pictures are made

Every picture is made by a script in the real Fission 180 under Xvfb, with tips-ui's helpers
(`tools/fission180/tip_pictures.py`; `docs/fission180/dev/tip-pictures.md`):

- **Demo parts by Fission 180's own code.** Sheet metal, plastic, manufacture and animation
  demos are built with the design-step language of the golden models and the AI tools
  (`fission180/ai/ops`: the code the dialogs run), most step lists copied from the golden
  models of the same tool (`sheetmetal_smm_*`, `sm_flat_*`, `plastic_*`, `plastic2_*`,
  `cam_plate_face_contour_drill`, `anim_*`). MESH pictures make real MESH steps
  (`mesh.new_step`, computed as the dialogs make them) on a mesh body as Insert Mesh makes it;
  SIMULATION builds the study with `fission180/simulation.py` and solves it through the Solve
  dialog's job (`simulation_solve_dialog.start`, CalculiX, about a second).
- **Before / after** for tools that change the part, what the tool made in the selection
  blue (new faces, or the faces it lifted, or the edges that outline a thin new face);
  **the workspace as it shows it** for CAM (stock, axes, picks in blue, the toolpath) and
  RESULTS (the coloured result with the legend grabbed beside it, tags as the view draws
  them); **the dialog**, alone or beside the model, for settings, export and inspection tools
  and where the result is not visible (Convert to Sheet Metal changes no geometry; 3D Contour
  on a small demo).
- Run time (this sandbox, 4 CPUs shared by ten builders): mesh 1 min 24 s, sheet metal
  1 min 27 s, plastic 8 pictures of 2 to 5 s each, animation 43 s, manufacture 2 min 21 s,
  simulation 3 min 13 s (each with about 10 s to start Fission 180).

## Proofs

- `Fission180Tests.unit.test_tips.Coverage.test_module_{mesh,sheet_metal,plastic,simulation,
  manufacture,animation}`: OK (every command of the tabs has a complete entry and a right-sized
  picture). In this branch alone the coverage tests of solid, surface, sketch, drawing and
  utilities fail ("tips/<module>.py is not written yet": the other builders' modules); a cross
  check of all eleven modules from their branches: 377 entries, no command id or picture name
  twice.
- `tipsws_hover` (real pointer moves): MESH > Remesh, SHEET METAL > Flange, PLASTIC > Boss, the
  Smooth entry of MESH > MODIFY's drop-down and, in the MANUFACTURE workspace, MILLING >
  2D Pocket: each shows its small tooltip, then the expanded one with its own picture drawn on
  the screen, its words and numbered steps. PASS, 58 checks.
- Unit tests (`run_tests.sh --only unit`): 3813 tests, only the five other modules' coverage
  tests fail (above). Headless runner (`--only headless`): all passed (555 tool calls, 197
  documentation items, the MCP agent's 81 checks, rebuild 153 + 15, recognition 71 parts).
  tips-ui's `tips_hover` with these modules loaded: PASS, 44 checks. No golden model run: no
  geometry code was changed. The scenarios hover the ribbon and move into the 3D view without
  clicking there, so the one-pixel-taller window check of gui-tests.md does not apply.

## FreeCAD and Fission 180 traps found on the way

- **A Coin search in a picture script crashed FreeCAD now and then** (SIGSEGV in about 4 of 10
  runs, the backtrace a jump to a heap address): `coin.SoSearchAction` over the CAM view's
  nodes, then changing the `SoDrawStyle` nodes its paths led to. The CAM pictures now make
  the lines wide when the workspace draws them (`manufacture_view._lines` wrapped while the
  pictures are made): 20 renders in a row, no crash. FreeCAD's own crash handler runs before
  Python's faulthandler, and the GUI's stdout is buffered: write markers to a file to find
  where a GUI script dies.
- **FreeCAD's CAM Adaptive, run inside the window, fails** ("'NoneType' object has no attribute
  'getSceneGraph'": it looks for a 3D view of its own). The app generates in a program of its
  own (`manufacture_ui.generate`, `wait_generated`); the AI / golden step `cam_operation` with
  `generate: true` runs the engine in-process, which works headless only. The picture script
  generates as the app does.
- **MESH > Combine (Join) of two bodies with coplanar faces crashes Fission 180** (SIGSEGV in
  FreeCAD's `MeshCore::SetOperations` / `Delaunay2`, 3 of 3 headless): a box mesh and a
  cylinder mesh standing on the same floor. Reported as a suggested task; the picture keeps
  the knob off the floor plane.
- **MANUFACTURE > 3D > Contour makes no toolpath on a plain box** ("no toolpath came out for
  this selection"), flat or ball tool; it works on a round boss, and Parallel works on the box.
  Reported as a suggested task; the picture shows the dialog beside a round part.
- A Separate step makes its pieces in the dialog (`sync_pieces`: `mesh.set_piece_count`), not
  when it computes; a Point Probes table fills on its panel's `refresh()`; Convert to Sheet
  Metal on an XZ-sketch extrusion: the part runs along -Y (pick the face at y < 0).
- The sandbox's scratchpad is shared by every builder of the wave: a file named
  `check_tips.py` was written over by another builder; keep scratch files in a folder of
  one's own.
- Fusion's tooltips (for the record; the widget is tips-ui's): forum excerpts (2026-11-13
  WebSearch) say a small balloon shows at once and the expanded one with text and images
  follows while the pointer stays, it goes when the pointer leaves, Preferences has "show
  tool tips". Sources: Autodesk Community threads "Display of Feature/Tool Detailed
  Description Disappears too fast to read" (5934856, 6581314), "Disappearing tool tips"
  (8195293), "Tooltips erratic, showing too soon" (12707332).

## Gaps (honest pictures over pretty ones)

- Tags over the RESULTS view (min / max, probes) are small at 320 x 200: the picture is the
  view as the window draws it, cut around the part, so their words are only just readable.
- The 3D Contour picture is its dialog (the toolpath passes on a small demo were not
  readable, and on a box there were none: above).
- The callout's words are FreeCAD's small view font.

## Changelog lines

- Every command of the MESH, SHEET METAL, PLASTIC, SIMULATION, MANUFACTURE and ANIMATION tabs
  now has a tooltip: hover it to see what it does, and keep the mouse still to see a picture
  of it at work, the steps to use it and a hint or two.

## Known issues

- MESH > Combine (Join, Cut, Intersect) of mesh bodies with faces in one plane can crash
  Fission 180 (FreeCAD's mesh booleans); move one body slightly first (suggested task).
- MANUFACTURE > 3D > Contour finds no toolpath on straight-walled parts like a plain box; use
  2D Contour for straight walls (suggested task).
