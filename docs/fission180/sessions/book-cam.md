# Wave 7, builder cam: the MANUFACTURE workspace (branch `sf/book-cam`, 2026-11-11)

Brief: `docs/fission180/dev/briefs/book-cam.md`. Report lines 185-222 (Workspaces table) and
2550-2560 (Projects 25 + 26, Wooden Longboard and Electric Guitar: "There is no Manufacture
(CAM) workspace in Fission's switcher ... none of the book's steps can be followed as
written"). Spec and mapping: `docs/fission180/parity/manufacture.md`.

## What the report says, and what I found

- **Reproduced**: on `develop` (3.3.10) the workspace menu offers Design / Simulation /
  Drawing only; FreeCAD's CAM is reachable through UTILITIES > FREECAD > Switch to FreeCAD's
  interface, with FreeCAD's own names. The report's diagnosis is right; there was nothing to
  fix, a workspace to build.
- **Fusion's behaviour**: Autodesk's help pages for the Setup, the Stock tab, the heights, 2D
  Contour and its tabs, 2D Pocket, 2D Adaptive and the drilling cycles confirm the dialog
  structure (Setup / Stock / Post Process; Tool / Geometry / Heights / Passes / Linking), the
  orientation and origin modes, the stock modes, the height references and the drilling
  cycles. WebFetch cannot reach hosts from the sandbox; search excerpts could. Defaults the
  excerpts did not give (stock offsets, the exact default heights) are marked G in the
  parity doc.

## What I built

- `manufacture_core.py` (no FreeCAD, no Qt; 51 unit tests): Setup options, stock boxes,
  work coordinate system axes, heights, tools with FreeCAD's tool-bit format and the sample
  libraries (43 metric, 26 inch tools, cutting data from formulas), the operations and their
  options, `engine_plan` (the Fusion -> FreeCAD mapping), G-code reading into moves with
  exact arc lengths and drilling cycles, path statistics, the G-code checker, the setup sheet,
  the browser tree.
- `manufacture.py`: setups and operations as objects of the design, the setup's `Frame` (the
  model turned into the setup's coordinates), picked geometry resolved (chain selection, the
  side of a contour, holes), fingerprints ("needs regenerating"), `Run` (generate / post in
  FreeCAD's engine), `playback` (Simulate), `setup_sheet`, `summary`.
- `manufacture_engine.py`: FreeCAD's CAM driven from a job folder; runs in `freecadcmd` when
  the window is open, directly without one.
- `manufacture_sim.py`: stock removal as a height field (numpy), rapid-into-stock detection.
- `manufacture_tools.py`: Document / Local / sample libraries; Local as FreeCAD `.fctb` and
  `.fctl` files in `<user data>/Fission180/ToolLibrary`.
- `manufacture_ui.py` (workspace, background generate, 21 commands), `manufacture_browser.py`,
  `manufacture_view.py` (Coin: stock, triad, toolpaths, height planes, simulated stock and
  tool), `manufacture_panels.py` (dialog base with several selection boxes),
  `manufacture_setup_ui.py`, `manufacture_op_ui.py`, `manufacture_tools_ui.py`,
  `manufacture_simulate_ui.py`, `manufacture_post_ui.py`.
- `tools/fission180/icons_manufacture.py` (29 icons), `ai/ops/manufacture_ops.py` (design steps
  `cam_setup`, `cam_operation`, `cam_edit`, `cam_generate`, `cam_post`),
  `golden/manufacture_schema.py`, `golden/manufacture_checks.py` (`cam_expect`), two golden
  models with hand-derived contour and drilling lengths.

## Shared files touched (smallest possible, each in a block of its own)

- `ribbon_ui.py`: `MANUFACTURE_TABS`, the Manufacture entry of `_workspace_menu`,
  `set_manufacture_mode`, one `elif` in each of `set_drawing_mode`, `set_flat_pattern_mode`,
  `set_simulation_mode` so the MILLING tab stays hidden there.
- `ribbon_config.py`: the `CAM_*` groups, `TABS.append(...)` and the workspace's marking menu,
  appended after `TABS`.
- `browser_ui.py`: the manufacture rows' kinds start with `sim_cam_`, so they take the
  SIMULATION hooks; `_simulation_tree` and `_simulation_call` hand them to
  `manufacture_browser` while the design is in Manufacture; three kinds added to
  `SIM_RENAMABLE`.
- `marking_menu.py`: the workspace's own ring (5 lines before Simulation's).
- `ai/ops/core.py`, `golden/schema.py`, `golden/checks.py`: one import line each.
- `ai/catalog/__init__.py`: `AI_TOOLS_TO_COME` lists the five `cam_*` steps;
  `test_ai_sheetmetal_plastic_tools.py`: its "nothing waits" check now allows them.

- `tools/fission180/data/fusion-menus.txt`: "Manufacture" is no longer marked out of scope in
  the workspace list; Fusion's MILLING tab is listed (Scallop, Pencil, Spiral, Radial marked
  out: FreeCAD's engine has no such strategy).

## FreeCAD facts and traps

See the last section of the parity doc. The ones that cost time:

- FreeCAD's CAM cannot run inside the window: `Job.Create`, the stock and `findToolController`
  use `FreeCAD.ActiveDocument`, and the Adaptive operation runs Qt's events while it computes.
  The engine runs in `freecadcmd` (start 0.5 s).
- `Path.Dressup.Utils.baseOp` finds the operation under a dress-up by the word "Dressup" in
  object names. A dress-up named "Tabs" made every later dress-up fail with "no attribute
  ToolController".
- Tabs and lead-ins cannot be combined (see the parity doc's gaps).
- A new Drilling operation fills its Base with every hole it finds; with `Locations` given too
  each hole was drilled twice.
- Seven of FreeCAD's sixteen post processors do not give a usable program (parity doc).
- `App::PropertyLinkListHidden` gives no `InList`: `setup_of(op)` searches the setups.
- A body's shape is often a compound without `CenterOfMass`: the first fingerprint silently
  never changed (it now can never read "unchanged" by mistake).
- A modal Fission 180 window that closes must give the main window the keyboard back
  (`simulation_dialogs.FocusBack`): under xvfb Esc did nothing after the Tool Library closed.
- FreeCAD's own `make_icons.py` output for `split_body.svg` differs from the committed file on
  `develop` (not mine; I left the committed one).

## Tests

- Unit: `test_manufacture_core.py`, 51 tests.
- Golden: `cam_plate_face_contour_drill`, `cam_block_side_setup`.
- Scenarios (real input, paced by state), 309 checks: `book_cam_setup` (58),
  `book_cam_operations` (79), `book_cam_program` (87), `book_cam_refusals` (50),
  `book_cam_orientation` (35).
- Older scenarios of the shared files: `sim_setup_browser` (67), `drawing_new` (63),
  `sim_setup_documents` (71), all passing.
- `ribbon_sweep` with `SWEEP_TABS=cam_milling` found the 3D dialogs' start-up error (fixed);
  it still reports the Tool Library as a pop-up, which it is by design (Fusion's is a window
  too). The default sweep (solid, sketch) is not affected.

## Changelog lines

- New MANUFACTURE workspace (workspace menu > Manufacture): turn a design into a CNC milling
  program the way Fusion does, without leaving Fission 180's interface.
- New Setup: say how the part sits on the machine (the origin, the directions) and what
  stock it is cut from; the stock and the axes are drawn on the part.
- Milling operations with Fusion's names and five-tab dialogs: Face, 2D Adaptive Clearing, 2D
  Pocket, 2D Contour (with holding tabs), Slot, Trace, Engrave, 2D Chamfer, Bore, Circular,
  Drill, and the 3D Adaptive Clearing, Pocket Clearing, Parallel and Contour.
- Tool Library with a sample library of common end mills, ball mills, drills, chamfer mills
  and face mills in metric and inch, and your own tools.
- Simulate: watch the tool cut the stock, with the machining time and a warning for any
  rapid move into material.
- Post Process: write the G-code for Grbl, LinuxCNC, Mach3 / Mach4, Fanuc, Marlin and four
  more controllers; the program is checked before you see it. Setup Sheet: a page with the
  tools, operations and times.
- Toolpaths are kept in the design; when the design changes they show "needs regenerating".

## Known issues

- A program must be checked before it runs on a machine: simulate it, read the G-code, make
  the first run above the part. Fission 180 cannot know your machine, clamps or tool lengths.
- With holding tabs on, 2D Contour has no lead-in or lead-out (FreeCAD's engine cannot make
  both). Do instead: nothing, or cut the tabs' contour as a second operation without tabs.
- Compensation "In control" / "Wear" (G41 / G42) is not available: the toolpath is always
  compensated in the computer.
- Engrave follows the picked edges with the tool's centre (no V-carving of closed letters).
- Thread milling, tabs at clicked points, rest machining, machine definitions, templates, NC
  Program objects, turning, multi-axis and additive are not built.
- Simulate does not check the holder or the tool's shaft, only rapid moves of the cutter into
  material.
- The AI assistant has no Manufacture tools yet (the design steps exist for scripts and
  tests).
- Heidenhain, Dynapath, Snapmaker, ShopBot, UCCNC and Estlcam posts of FreeCAD are not offered:
  in FreeCAD 1.1.4 they fail or write programs without units.
- 3D Adaptive Clearing uses a FreeCAD feature FreeCAD itself calls experimental: simulate it.
