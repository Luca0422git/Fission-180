<!-- A copy of docs/fission180/parity/manufacture.md for AI models, made by tools/fission180/make_ai_docs.py: edit the original, then run the script. -->

# Parity spec: MANUFACTURE workspace, milling (wave 7, builder cam)

Fusion's Manufacture workspace for 3-axis milling, built on FreeCAD 1.1.4's CAM engine
(`Mod/CAM`: `Path.Main.Job`, `Path.Op.*`, `Path.Dressup.*`, `Path.Post.*`) the way Simulation
is built on FEM: the person sees Fusion's workspace, names and dialogs, never FreeCAD's CAM
workbench. In scope since 2026-11-11 (Luca; the book's chapter 11, Wooden Longboard and
Electric Guitar). Code: `fission180/manufacture*.py`; tests: `test_manufacture_core.py` (51),
golden `cam_*.json` (2), scenarios `book_cam_*.py` (4).

Source tags: **A** = Autodesk Fusion help (found by search, read through search excerpts:
WebFetch cannot reach hosts from the sandbox), **F** = Autodesk forum, **T** = tutorial,
**B** = the book as the parity report quotes it, **G** = guess (from memory of Fusion, or
Fission 180's choice where the sources are silent).

Sources:
- [A1] Setup tab (milling and cutting) reference, help.autodesk.com/cloudhelp/ENU/Fusion-CAM/files/MFG-REF-SETUP-MILL.htm
- [A2] Stock tab reference, .../MFG-REF-SETUP-STOCK.htm
- [A3] Create a setup, .../MFG-CREATE-SETUP.htm; Setups for manufacturing, .../GUID-AC4E6A7A-6A9A-45F3-9CEE-AC6BA29AB49A.htm
- [A4] Activity 1: Create the setup (tutorials), .../GUID0BDA384D-600F-4DDB-9578-03B72EB7423D.htm
- [A5] Setting Machining Heights reference, .../GUID3EB12C22-C06B-4601-ABFE-7F1ECBABB9CE.htm; Clearance height, .../MFG-REF-CLEARANCE-HEIGHT.htm; Feed height, .../MFG-REF-FEED-HEIGHT.htm
- [A6] 2D Contour reference, .../GUID75B6821B-DE26-4E3B-AF10-4A54131CD9E4.htm; Tabs reference, .../MFG-REF-2D-CONTOUR-TABS.htm
- [A7] 2D Pocket reference, .../GUID67DC60DE-EE42-4BC4-B50D-B28D938D146E.htm; 2D Adaptive Clearing reference, .../GUIDA73542E9-ED9C-4BD9-A87D-3A0ECA8BEB41.htm
- [A8] Drilling Cycles reference, .../MFG-REF-DRILLING-CYCLES.htm; Generate a Drill toolpath, .../LP-STEP-IRONSTRATEGY_DRILL.htm
- [A9] Workflow: Milling, .../MFG-OVERVIEW-MILLING-WORKFLOW.htm; Milling overview, .../MFG-MILLING-OVERVIEW.htm
- [F1] forums.autodesk.com: "Origin Model Box Point is at TopCenter instead of BottomLeft" (the default box point is the top centre)
- [F2] forums.autodesk.com: 2D Contour tab positioning threads (by distance works per segment; manual points fail on splines)
- [F3] forums.autodesk.com: "Z raises up, nobody asked it to" (Top, Retract and Clearance offsets stack)
- [T1] medium.com/@arstein "Creating setups", "Overview of cutting operations and common settings"

## Behaviour

### The workspace

| # | Fusion behaviour | Fission 180 | Src |
|---|---|---|---|
| W1 | Manufacture is a workspace of the workspace switcher; the MILLING tab has SETUP, 2D, 3D, DRILLING, MULTI-AXIS, MODIFY, ACTIONS, INSPECT, MANAGE, SELECT; other tabs TURNING, ADDITIVE, INSPECTION, FABRICATION | "Manufacture" in the workspace menu; MILLING tab with SETUP, 2D, 3D, DRILLING, ACTIONS, MANAGE, INSPECT, SELECT. MULTI-AXIS, MODIFY and the other tabs are left out (FreeCAD has no 4/5-axis, lathe or additive engine) | A9 |
| W2 | No design timeline in Manufacture; the browser shows Setups with their operations in order | Same (the timeline is hidden as in Simulation; the browser shows Document Settings, Named Views, Setups) | G |
| W3 | An operation shows its state: valid toolpath, out of date (needs regenerating), error, suppressed; Generate rebuilds | Same: yellow row "Needs regenerating", red row with the reason as its tool tip, struck through when suppressed, "(generating...)" while FreeCAD's engine works | G |
| W4 | Right-click: Edit, Generate, Suppress, Duplicate, Delete, Simulate, Post Process, Setup Sheet... | Setup: Edit, Generate, Simulate, Post Process, Setup Sheet, Suppress, Duplicate, Rename, Delete. Operation: Edit, Generate, Simulate, Post Process, Suppress, Duplicate, Move Up, Move Down, Rename, Delete. Setups folder: New Setup, Generate All. Double-click edits | G |
| W5 | Picking an operation draws its toolpath: blue cutting moves, yellow rapids, green lead-in / lead-out and ramps, red plunges | Same colours. FreeCAD's engine does not mark lead-ins: every cutting move that also changes height (ramp, helix, lead arc that goes down) is green, a straight plunge red | G |
| W6 | Switching workspace never changes the design | Same: setups and operations are objects of their own, not timeline steps; the modelling keys (E, Q, F, Delete...) are off in Manufacture; scenarios check the body's volume throughout | G |
| W7 | Toolpaths are generated in the background with progress | Same: FreeCAD's CAM runs in a command-line FreeCAD of its own (`manufacture.Run`); the window stays usable | G |

### Setup (SETUP > New Setup)

| # | Fusion behaviour | Fission 180 | Src |
|---|---|---|---|
| S1 | Tabs Setup, Stock, Post Process | Same | A1 A2 |
| S2 | Operation Type: Milling, Turning or mill/turn, Cutting, Additive | Milling; the others listed greyed with why | A1 |
| S3 | Model: the bodies to machine (default: the whole design) | Same (none picked = every solid body; click bodies to pick some) | A1 |
| S4 | WCS Orientation: Model orientation; Select Z axis/plane & X axis; Select Z axis/plane & Y axis; Select X & Y axes; Flip for each axis | Same four modes; a planar face gives its normal, a round face its axis, a straight edge its direction; Flip Z, Flip X. Any orientation works (the model is turned into the setup's coordinates before FreeCAD sees it) | A1 A4 T1 |
| S5 | WCS Origin: Model origin, Selected point, Stock box point, Model box point; the box points are white dots to click, the default is the stock's top centre | Same; the 27 dots are drawn on the box and clicked (or chosen in three drop-downs: Left / Middle / Right...) | A1 A4 F1 |
| S6 | The triad (X red, Y green, Z blue) and the see-through stock are shown on the model | Same, also while the dialog is open (they follow every change) | A4 |
| S7 | Stock modes: Fixed size box, Relative size box, Fixed / Relative size cylinder, Fixed size tube, From solid, From preceding setup | Relative size box, Fixed size box, From solid, From preceding setup (workspaces-2: the preceding setup's block as it lies now; what its operations cut away is not taken off). Cylinders greyed with why | A2 |
| S8 | Relative size box: No additional stock / Add stock to sides and top-bottom / Add stock to all sides; offsets may be negative; Round Up to Nearest | Same three modes (side, top, bottom; or six offsets); Round Up grows the sides evenly and the top. Defaults 1 mm side, 1 mm top, 0 bottom (G: Fusion's own defaults vary with its version). A stock that leaves the model outside warns where; offsets that leave no stock are refused | A2 |
| S9 | Fixed size box: width, depth, height and the model's position per axis (offset from a side, or centre) | Same | A2 G |
| S10 | Post Process tab: program name/number, comment, WCS offset | Same (WCS offset 1..6 = G54..G59 in the posted program) | A1 G |

### Operations

Every operation has Fusion's five tabs: Tool, Geometry, Heights, Passes, Linking. OK generates
the toolpath (in the background) and draws it.

| # | Fusion behaviour | Fission 180 | Src |
|---|---|---|---|
| O1 | Tool tab: Select opens the Tool Library; coolant; feed and speed (spindle speed, surface speed, cutting / lead-in / ramp / plunge feedrate, feed per tooth), filled from the tool | Same; surface speed and feed per tooth are shown, derived | A7 G |
| O2 | Geometry: pick contours / pocket faces / hole faces; a click on an edge takes the connected chain | Faces and edges of the setup's bodies; a click on an edge takes the whole closed loop at its height (the boundary of the flat face it bounds); a click on a picked element drops it | A6 G |
| O3 | 2D Contour picks its side by itself (outside an outer contour, inside a hole or pocket); the arrow flips it | The side is found by testing where the model has material next to the loop; "Machine the Other Side" flips it | A6 G |
| O4 | Tabs (2D Contour): rectangular or triangular, width, height, positioning by distance or by number, or at points | Shape, width, height, By distance / Number of tabs. Tabs at clicked points: not built | A6 F2 |
| O5 | Heights: Clearance, Retract, Feed, Top, Bottom, each From a reference (Retract height, Feed height, Top height, Model top, Stock top, Model bottom, Stock bottom, Selected contour(s), Origin (absolute)) plus an offset; drawn as coloured planes | Same references plus Hole top / Hole bottom for hole operations; five coloured planes over the stock and the Z of each beside its row. Defaults: Clearance = Retract + 10, Retract = Stock top + 5, Feed = Top + 5, Top = Stock top, Bottom = Selected contour(s) (Face: Model top; 3D: Model bottom; holes: Hole top / Hole bottom). Out of order (e.g. Retract below Feed) is refused with which and what to do. Dragging a plane in the canvas: not built | A5 F3 |
| O6 | Passes: tolerance, sideways compensation (left = climb / right = conventional), compensation type (in computer / in control / wear / off), stepover or optimal load, Multiple Depths with maximum roughing stepdown, finishing passes, Stock to Leave (radial, axial) | Same fields per strategy. In control / Wear are greyed (FreeCAD emits no G41 / G42). Tolerance is kept but FreeCAD's engine has its own fixed accuracy | A6 A7 |
| O7 | Linking: lead-in / lead-out with radius, ramp type (plunge, helix, profile, zig-zag...), ramping angle, helical ramp diameter, stay-down | Lead-In, Lead-Out, Lead Radius (2D Contour), Ramp Type (Plunge, Helix, Profile, Zig-zag), Ramping Angle, Helical Ramp Diameter, Keep Tool Down | A6 A7 G |
| O8 | Drill: cycle types (drilling - rapid out, counterboring - dwell and rapid out, chip breaking - partial retract, deep drilling - full retract, tapping, reaming, boring...), pecking depth, dwell, Drill Tip Through Bottom with Break-Through Depth, Select Same Diameter | The first four cycles (G81, G82, G73, G83); tapping / reaming / boring greyed with why. Select Same Diameter adds every hole of that size. Holes of different depths are drilled each to its own bottom | A8 |

### Tool Library, Simulate, Post Process, Setup Sheet

| # | Fusion behaviour | Fission 180 | Src |
|---|---|---|---|
| T1 | Tool Library: Documents, Local, Fusion Library (vendor tools), Cloud; a table of tools with filters; New Tool, Edit, Copy, Delete | Document (the tools the design's operations use), Local (the person's own, more can be made), Fission 180 Samples Metric / Inch (43 + 26 tools, read only). No Autodesk or vendor data: the samples are generated from standard sizes with formula cutting data | G |
| T2 | Tool editor tabs: General, Cutter, Shaft, Holder, Cutting Data, Post Processor | General, Cutter (with the shaft), Holder, Cutting Data (with Suggest), Post Processor (the number) | G |
| T3 | Simulate: play, step, speed, stock shown, tool shown, statistics (machining time, distance), collisions | Player with Play / Pause, Next Move, To End, Restart, a speed and a position slider; the stock is cut as a height field; machining time, cutting and rapid distance, volume removed; every rapid move into material is listed. The holder and shaft are not checked | G |
| T4 | Post Process: post, output folder, program name / number, comment, unit, Open NC file in editor | Same fields; nine posts (below). The written file is read back by a checker and the result shown | G |
| T5 | Setup Sheet: HTML with tools, operations, times, stock | Same | G |

## Mapping onto FreeCAD's CAM

How it is kept: a setup and each operation are `App::FeaturePython` objects of Fission 180's own
(JSON options, picks as links to the bodies' faces and edges). Nothing of FreeCAD's CAM is
stored in the design. **Generate** writes the model (turned and moved into the setup's
coordinates, as BREP) and a job description to a temporary folder; `manufacture_engine.py`
builds a FreeCAD Job there, makes FreeCAD's operations and dress-ups, and returns each
toolpath as G-code (FreeCAD's units: mm, mm/s), which is kept on the operation with a
fingerprint of the model, the setup and the options.

| Fusion operation | FreeCAD | Notes |
|---|---|---|
| Face | `Path.Op.MillFace` (BoundaryShape Stock, ZigZag or Line) on the model's top faces | The tool's edge reaches the stock's edge; Pass Extension = ExtraOffset |
| 2D Adaptive Clearing | `Path.Op.Adaptive` (Clearing, Inside) | Optimal Load = StepOver %; Keep Tool Down off = KeepToolDownRatio 0 (every link retracts) |
| 2D Pocket | `Path.Op.PocketShape` (Offset pattern) + RampEntry dress-up | |
| 2D Contour | `Path.Op.Profile` + `Dressup.Tags` (tabs) + RampEntry + LeadInOut | One Profile per loop, each with its side |
| Slot | `Path.Op.Slot` | |
| Trace, Engrave | `Path.Op.Engrave` | Fusion's Engrave is a V-carve of closed shapes; here the tool's centre follows the edges at the Bottom Height |
| 2D Chamfer | `Path.Op.Deburr` | Width and tip offset; FreeCAD works the depth out itself |
| Bore, Circular | `Path.Op.Helix` on a circular edge of each hole | Pitch = StepDown; a tool as wide as the hole is refused before FreeCAD is asked |
| Drill | `Path.Op.Drilling` with `Locations` (one FreeCAD operation per depth group) | G81 / G82 / G73 / G83 |
| 3D Adaptive Clearing | `Path.Op.Adaptive` with ModelAwareExperiment | FreeCAD marks it experimental |
| 3D Pocket Clearing | `Path.Op.Pocket` | |
| 3D Parallel | `Path.Op.Surface` (OpenCAMLib, in the AppImage as `opencamlib`) | |
| 3D Contour | `Path.Op.Waterline` (OCL Dropcutter, BoundBox Stock, LayerMode Multi-pass with Multiple Depths) | The engine scans 1.5 x the tool's diameter + 2 mm round the part where the stock is narrower (`waterline_margin`; for its computing only, the stock put back after); grid step = the tool's diameter / 24, 0.1 to 0.5 mm (`waterline_sample`): the passes stand at most that far outside the walls |
| Thread, Scallop, Pencil, Spiral, Radial | none | Listed greyed with the reason |

| Fusion option | FreeCAD property |
|---|---|
| Retract Height | ClearanceHeight (FreeCAD's travel height between cuts) |
| Feed Height | SafeHeight (where rapid turns into feed); Drill: RetractHeight (the R plane) |
| Clearance Height | no property: a rapid to it is added at the start and the end of the toolpath |
| Top / Bottom Height | StartDepth / FinalDepth (+ axial stock to leave) |
| Multiple Depths, Maximum Stepdown | StepDown (off: one step of the whole depth) |
| Stepover / Optimal Load | StepOver (% of the tool's diameter) |
| Sideways compensation | Profile: Direction CW (climb outside, conventional inside) / CCW; others: CutMode |
| Radial / Axial Stock to Leave | OffsetExtra, ExtraOffset, StockToLeave / FinalDepth raised |
| Tabs | Tags dress-up: Width, Height, Angle 90 (rectangular) or 45 (triangular), `generateTags(count)` |
| Lead-In / Lead-Out | LeadInOut dress-up (Arc, RadiusIn / RadiusOut) |
| Ramp Type | RampEntry dress-up: Helix, RampMethod1 (profile), RampMethod3 (zig-zag); Adaptive: HelixAngle, HelixDiameterLimit |
| Spindle speed, feedrates | a tool controller per operation: SpindleSpeed, HorizFeed, VertFeed |
| Tool | a FreeCAD tool bit made from the tool's `.fctb` content (endmill, ballend, bullnose, chamfer, drill shapes) |

Posts (FreeCAD's, by machine dialect): Grbl, LinuxCNC (EMC2), Mach3 / Mach4 Mill, Fanuc,
Marlin, Centroid, Smoothieware, RepRapFirmware (Duet), Masso G3. Each was run on a contour
and a drilling operation and read back by `manufacture_core.check_gcode` (2026-11-11).
Left out, with what happened: heidenhain (fails inside FreeCAD 1.1.4: it looks for
`Path.Op.ProfileEdges`, which is gone), dynapath and generic (write an empty program),
snapmaker (ends FreeCAD without a program), opensbp (refuses a second tool), uccnc and
estlcam (never state the units).

The G-code checker (Fission 180's own, `check_gcode`): the units are stated (G20 / G21) before
the first move and are the ones asked for; the spindle is on with a speed before the first
cutting move; a feedrate is set before cutting; no sideways rapid below the top of the stock
(with Keep Tool Down a note, not a problem); nothing below the lowest height of the
toolpaths; every move inside the toolpaths' box; the spindle is stopped at the end; a missing
M2 / M30 is a note. Moves in machine coordinates (G28, G53) and incremental moves (G91) are
not followed.

## What cannot be mapped, and known gaps

- **3D Contour's accuracy**: FreeCAD's Waterline finds the walls on a grid of drop-cutter
  points, so its passes stand up to one grid step (0.1 to 0.5 mm: the tool's diameter / 24)
  outside the walls, never inside; Fusion's stay within the Tolerance. A finer grid costs
  time (0.1 mm: 2.4 s on a 60 x 40 block, 7 s round a 40 mm boss). For exact straight walls,
  finish with 2D Contour. Before 0.1.0-beta.4.0.3 it found no wall at all when the stock
  stood less than about a tool's diameter + 1 mm off the part (FreeCAD scans only inside the
  stock's outline), left up to 1 mm, and cut the whole wall in one pass at the bottom
  (LayerMode was left at FreeCAD's Single-pass); such toolpaths in saved designs say they
  need regenerating (`manufacture.KIND_VERSIONS`). FreeCAD 1.1.4's other algorithm,
  Experimental, stops with a TypeError ("object of type 'Part.Compound' has no len()").

- **Lead-ins with tabs**: FreeCAD's tabs find no contour in a path that already has lead-ins,
  and lead-ins put on a path with tabs retract at every tab. With tabs on, the leads are left
  out and the operation says so (a warning in its tool tip).
- **Compensation In control / Wear** (G41 / G42): FreeCAD's Profile only compensates in the
  computer. Greyed.
- **Tolerance** (workspaces-2): reaches the engine where FreeCAD has an accuracy to set:
  Face, 2D Pocket, 2D Contour and Pocket Clearing through `Path.Area`'s default accuracy and
  deflection (a third of the Tolerance each: measured on a contour around an ellipse, the
  toolpath is up to 2.35 times the accuracy away from the true path) and the job's
  `GeometryTolerance`; the two Adaptive operations through their `Tolerance` property (their
  default is 0.1 mm, Fusion's roughing default (G) and FreeCAD's own); Parallel and Contour
  through `LinearDeflection`. Slot, Trace, Engrave, 2D Chamfer, Bore and Circular follow the
  picked edges and circles exactly: their Tolerance field is greyed with that reason. A
  value outside 0.001 to 1 mm is refused. **Smoothing** is not built.
- **Lead-In Feedrate** (workspaces-2): FreeCAD's lead-in dress-up has no feed of its own and
  cuts the lead at the cutting feed. The engine now returns the path as it was before the
  leads were added; `manufacture_core.with_feeds` finds the lead-in moves (the sideways
  cutting moves that start at a place the path without leads never visits) and writes the
  Lead-In Feedrate onto them. A lead-out keeps the cutting feed (Fusion has a Lead-Out
  Feedrate field of its own, which defaults to the cutting feed: A; not built). The field is
  greyed when the operation has no lead-in (not a 2D Contour, Lead-In off, or tabs on).
- **Ramp Feedrate** (workspaces-2): the ramp dress-up (2D Pocket, Pocket Clearing, 2D Contour
  with Ramp Type Helix / Profile / Zig-zag) takes it as its own "Custom" feed rate; FreeCAD's
  Adaptive goes down its helix at the plunge feed and has no property for it, so
  `with_feeds` writes the Ramp Feedrate onto every cutting move that goes down while it moves
  sideways. Greyed where there is no ramp (Ramp Type Plunge, or an operation without one).
  Sources (A, Autodesk's HSM / Fusion CAM help, search excerpts 2026-11-11): Lead-in feedrate
  "Feed used when leading in to a cutting move", Lead-out feedrate "Feed used when leading
  out from a cutting move", Ramp feedrate "Feed used when doing helical ramps into stock",
  Plunge feedrate "Feed used when plunging into stock"; Tolerance "the tolerance used when
  linearizing geometry such as splines and ellipses. The tolerance is taken as the maximum
  chord distance" (help.autodesk.com: Feedrate Reference, About 2D Contour, About 2D Adaptive
  Clearing). The default tolerances (0.01 mm, roughing 0.1 mm) were not found written: G.
- **Feed Height above Retract Height**: FreeCAD has one travel height.
- **Tabs at points** (workspaces-2): Tab Positioning "At points" with a Tab Positions box:
  each click on the model's side or edge is a tab (a click on a tab takes it away, the X
  takes all), a cross marks each while the dialog is open. The point is brought onto the
  toolpath's contour for FreeCAD's tab dress-up (`Positions`); a point more than 1 mm from
  the picked contour is refused with how far off it is, and tabs that overlap are refused.
- **Stock From preceding setup** (workspaces-2): the second setup takes the first one's
  block (box or solid) where it lies in the design, turned into its own coordinates. Fusion
  takes what the preceding setup left (A, Stock tab help); here the whole block stays
  (safe for the tool: it treats cut-away places as material; Simulate starts from the full
  block). A design change or a change of the first setup's stock makes the second setup's
  toolpaths "need regenerating".
- **Engrave** as Fusion's V-carve (variable depth in closed shapes),
  **Thread milling**, **rest machining** (rest material), **dragging
  the height planes**, **NC Programs** as browser objects (Post Process posts a setup or the
  picked operations), **machine definitions**, **templates**, **patterns of operations**,
  **stock contours / machining boundaries** for the 3D strategies (they machine the whole
  model inside the stock): not built.
- **Simulate**: Fission 180's own height-field model, not FreeCAD's simulator. FreeCAD 1.1.4 has
  two: `CAMSimulator` (OpenGL, needs a window of its own, gives no numbers) and the older
  `PathSimulator` (a voxel mesh, can be driven from Python, gives no volume and no collision
  report). The height field gives the removed volume and finds every rapid move into
  material; it cannot show undercuts (three-axis milling from above has none) and does not
  check the holder or shaft.
- **AI tools** (workspaces-2): `cam_setup`, `cam_operation` (all fifteen kinds, a tool of a
  library or described by its sizes), `cam_edit`, `cam_delete`, `cam_generate`,
  `cam_simulate` (time, distances, volume removed, every rapid move into the stock),
  `cam_post` (the file and the checker's result), `cam_setups` (the browser as data) and
  `cam_tools` (the Tool Library). They run the same design steps as the golden models and the
  same `manufacture.py` as the dialogs.
- **TURNING, ADDITIVE, INSPECTION, FABRICATION, MULTI-AXIS**: out. FreeCAD 1.1.4 has no lathe
  operations in the AppImage, no 4 / 5-axis strategies, and 3D printing goes through File >
  3D Print.

## FreeCAD facts (what the engine needs)

- `Path.Main.Job.Create`, the stock creators and `PathUtils.findToolController` all use
  `FreeCAD.ActiveDocument`, and FreeCAD's Adaptive runs Qt's events while it computes: inside
  the window the engine would switch the active document under the panels. So with the window
  open it runs in `freecadcmd` (0.5 s to start; the plate's three operations take 1.1 s).
- `findToolController` asks the person when a job has more than one tool controller (an
  unbound variable without a window): `PathUtils.UserInput` is replaced by an object that
  answers with the operation's own controller.
- A new Drilling operation fills its Base with every hole it finds: Base is always set.
- Dress-ups must have "Dressup" in their object names (`Path.Dressup.Utils.baseOp` walks by
  name).
- A property with a setup-sheet expression (StartDepth, StepDown, ClearanceHeight...) is only
  changed after `setExpression(prop, None)`.
- Toolpath feeds are mm/s inside FreeCAD; the posts multiply by 60.
- A body's shape is often a compound: it has no `CenterOfMass` of its own.
- Hidden link properties (`App::PropertyLinkListHidden`) give no `InList` back reference.
