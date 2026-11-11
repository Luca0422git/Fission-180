# Wave 7 builder: cam (the MANUFACTURE workspace), branch `sf/book-cam`

Read `book-common.md` first. Report lines: Workspaces table 185-222; CAM chapter 2550-2560.
Luca decided on 2026-11-11 that the Manufacture workspace is in scope (the outline's section
8 still says otherwise: the merger updates the outline).

The book's chapter 11 (Wooden Longboard, Electric Guitar) uses Fusion's MANUFACTURE
workspace: Setup, 2D Adaptive Clearing, 2D Contour, 2D Pocket, Face, Drill, 3D operations,
the Tool Library, Simulate, Post Process. Today a person must switch to FreeCAD's own
interface and use FreeCAD's CAM workbench with FreeCAD's names: "none of the book's steps can
be followed as written". Build Fusion's workspace **on FreeCAD's CAM engine** (`Mod/CAM`,
Python: `Path.Main.Job`, `Path.Op.*`, `Path.Tool.*`, `Path.Post.*`, the simulator), the way
Simulation was built on FreeCAD's FEM (read `simulation*.py` and
`docs/fission180/parity/simulation.md`, and
`docs/fission180/dev/research/integration-map.md`: how a workspace plugs in). The person
never sees FreeCAD's CAM workbench, its dialogs or its names.

1. **Research first** (WebSearch: Autodesk Fusion help for the Manufacture workspace: "New
   Setup" (Setup / Stock / Post Process tabs, WCS orientation and origin, stock modes: fixed
   size box, relative size box with offsets, from solid), the MILLING tab's 2D menu (2D
   Adaptive Clearing, 2D Pocket, Face, 2D Contour, Slot, Trace, Bore, Circular, Engrave,
   Chamfer), 3D menu (Adaptive Clearing, Pocket Clearing, Parallel, Contour, ...), DRILLING,
   the operation dialog's five tabs (Tool, Geometry, Heights, Passes, Linking) and their main
   options, the Tool Library, Simulate, Post Process, NC Programs, Setup Sheet). Also read
   what FreeCAD 1.1's CAM offers (run it headless: list `Path.Op` modules, the tool-bit
   library format, the bundled post-processors, whether OpenCamLib is in the AppImage for 3D
   surfacing, whether the simulator runs without its own window). Write
   `docs/fission180/parity/manufacture.md`: the behaviour spec with sources, and a mapping
   table Fusion operation -> FreeCAD operation and option -> property, with what cannot be
   mapped.
2. **The workspace**: "Manufacture" in the workspace switcher (your own block in
   `ribbon_ui._workspace_menu`), tabs MILLING (and what you can back with a real engine:
   TURNING and ADDITIVE are out; say so), groups SETUP, 2D, 3D, DRILLING, MULTI-AXIS left
   out, ACTIONS (Simulate, Post Process, Setup Sheet), MANAGE (Tool Library); the browser
   shows Setups with their operations in order, each with a state icon (valid toolpath,
   needs regenerating, error) and a right-click menu (Edit, Generate, Suppress, Duplicate,
   Delete, Simulate, Post Process); the design timeline is replaced as in Simulation.
3. **Setup** dialog with Fusion's tabs: model (body / component), WCS orientation (by Z axis
   / face / edges, flips) and origin (stock box point, model box point, selected point) with
   the triad shown on the stock, Stock (relative box with side / top / bottom offsets, fixed
   box, from solid), Post Process (program name / number, comment). Stock shown see-through.
4. **Operations**, each with Fusion's five-tab dialog and live toolpath preview after OK
   (blue cutting moves, yellow rapids, green lead-ins as far as the engine tells them apart):
   Face, 2D Adaptive Clearing, 2D Pocket, 2D Contour (with tabs / holding tabs: the longboard
   needs them), Slot, Drill (cycle types, from selected faces / all holes of a diameter),
   Bore / Circular (helix), Engrave / Trace, Chamfer (2D), 3D Adaptive and Parallel /
   Contour if the AppImage has the engine for them (else greyed with the reason). Geometry
   selection by clicking faces, edges / contours, pockets, with Fusion's chain selection;
   Heights (clearance, retract, feed, top, bottom: each "from" a reference + offset, shown
   as coloured planes); Passes (tolerance, stepover / optimal load, multiple depths, stock to
   leave, finishing passes, compensation side); Linking (leads, ramp type). Feeds and speeds
   from the tool.
5. **Tool Library**: Fusion-style dialog (libraries: Document, Local, a small original
   sample library of common end mills, ball mills, drills, chamfer mills, face mills in
   metric and inch with sensible cutting data from public sources), tool editor (cutter,
   shaft, holder basics, cutting data, post processor number), stored in FreeCAD's tool-bit
   files underneath. No Autodesk tool data copied.
6. **Simulate**: play / step / speed, stock removal shown, tool shown, collision or rapid
   into stock flagged if the engine can, statistics (machining time, distance); use
   FreeCAD's simulator if it can be embedded or driven; otherwise a toolpath playback with
   the tool moving along the path and, if feasible, a voxel or boolean stock removal of your
   own. Say honestly which.
7. **Post Process**: dialog (post, output folder, program name, units, open the file
   after), the bundled FreeCAD post-processors under Fusion-style names by machine dialect
   (grbl, LinuxCNC, Mach3 / 4, Fanuc, Marlin, ...), a G-code file a controller accepts
   (check with a small original G-code checker: units, spindle on before cutting, safe
   retracts, no moves below the bottom height). **Setup Sheet** (HTML: tools, operations,
   times, stock).
8. Stored in the design, survives save / reopen, the design changing afterwards marks the
   toolpaths "needs regenerating" (and Generate rebuilds them), undo / redo, Design <->
   Manufacture switching never changes the design's bodies.
9. Safety note in the workspace, as Simulation states its limits: generated G-code must be
   checked before it runs on a machine.

Qt-free core (`manufacture_core.py`: stock, heights, the Fusion -> FreeCAD mapping, G-code
checks) with unit tests; `manufacture.py` (document logic), `manufacture_*_ui.py`; icons in
`icons_manufacture.py`; AI ops and golden models for a setup + three operations with expected
path bounds and machining lengths.

Scenarios `book_cam_*.py` (at least: enter / leave; a Setup on a plate with pockets and
holes (stock offsets, WCS on the stock's top corner); Face; 2D Adaptive in a pocket; 2D
Contour around the outside with tabs; Drill all holes; tool picked from the library and a
new tool made; edit an operation and regenerate; simulate to the end (stock volume
decreases or the playhead reaches the end); post process to grbl and check the G-code (units,
depth, bounds); setup sheet; the design changed -> needs regenerating; save / reopen; undo /
redo; a refusal with a clear message (no tool, nothing selected)).
