# Session log: wave 7, replay-a (`sf/replay-a`, 2026-11-11)

The acceptance test of wave 7 for the book's chapter 1, first half: Project 0 "The Basics",
Project 1 "Classic Donut", Project 2 "Saturn V Rocket" (book parity report lines 655-973),
replayed step by step with real input and a user's defaults (brief
`docs/fission180/dev/briefs/book-replay.md`). Every hitch found on the way is fixed here.
The run was cut off once (credits, then a machine restart); it was resumed from the branch.

Scenarios: `replay_00_basics`, `replay_01_donut`, `replay_02_saturn_v`; helpers
`Fission180Tests/gui/replay_a_steps.py`; unit `Fission180Tests/unit/test_replay_a.py` (14).

## Status

| Project | Scenario | Checks | Result |
|---|---|---|---|
| 0 The Basics | `replay_00_basics` | 102 | PASS |
| 1 Classic Donut | `replay_01_donut` | 197 | PASS (failed once on a palette read before the palette's own timer: the check now waits for it by state) |
| 2 Saturn V Rocket | `replay_02_saturn_v` | 260 | PASS |

Each replay starts with the four defaults the harness switches off for older scenarios
switched on again (first component grounded, Fusion's grid snap, scale entire sketch at
first dimension, the layout grid) and `STRICT["undo"]` on; the harness's Report-view and
dialog checks stay on. No step took more than 6 s.

## Hitches (all fixed)

| # | Report line | What happened in the replay | Fusion (source) | Root cause | Fix (functions) |
|---|---|---|---|---|---|
| 1 | Basics 697 ("Fit frames the origin planes off-centre") | Origin eye on, F6: the view zoomed to 49 mm with the origin 254 px off the middle | Fit frames the design; the origin's planes are no part of it (Guess, the shell builder's rule) | `view_fit.content_box` asked the empty first body for a box; a body without a shape answers with its Origin planes' box | `view_fit.object_box`: a `PartDesign::Body` without a shape has no box |
| 2 | Donut 748 (green upright axis on the Front plane) | Still green (#33cc33); two builders had left it "not built" | A sketch shows the origin's own axes, red X, green Y, blue Z (Book) | FreeCAD's two sketch axis colours are C++ constants, rewritten at every recolouring | `sketch_axes.py` (new: `axis_of`, `colours`, `shown`, `directions`, `AxisColours`): the two lines drawn again just before FreeCAD's own, in the axes' colours, FreeCAD's highlight kept; hooked in `sketch_mode.SketchSession.__init__` / `_refreshed` / `close` and the two mouse-event pokes |
| 3 | Saturn 924 (the handles sit on the other profile), met in the Donut's bite | The second of the bite's five areas could not be picked: the taper disc lay on it | Fusion's handles do not hide what can still be picked (Guess) | `ExtrudePanel._make_taper_handle` put the disc on the profile's right edge whatever was there; extrude's earlier fix moved only the value boxes | `extrude_ui.ExtrudePanel._taper_pivot`, `_unpicked_faces`, `_covers_free_area` (new): the other edge when an unpicked area lies under the disc |
| 4 | Saturn 889-891 (Plane 1's square takes the click meant for the face) | Split Face said "Click faces of a body" | A selection box that takes faces only does not take a plane (Guess, Fusion's selection filters; Extrude does the same since wave 7) | `SplitFacePanel._pick_face` refused anything but a face | `split_face_ui.SplitFacePanel._behind_glyph` (new), `_pick_face`, `picked` (passes the point): the face behind the glyph is taken |
| 5 | Saturn 903 (the split band merged by the next extrude) | Still lost after stage 3, although `book_modify_split_pattern` passed | Fusion keeps split faces (Book) | `split_face.keep_splits` marks a step it switched to no Refine and then leaves marked steps alone; the Extrude dialog writes its step anew at every change of the preview (`extrude._apply`: Refine = True), so a step switched between two changes stayed merged | `split_face.keep_splits` (a marked step with Refine on is looked at again), `split_face.kept_unrefined` (new), `extrude._refine` (new, used by `extrude._apply`) |
| 6 | Saturn 921-924 (the thruster's two halves) | Extrude took both halves by itself; the book's "click both halves" dropped the first, and the second click landed on the arrow that then stood on it: one half extruded | Fusion takes no profile by itself when a sketch has several; its users click each (Book, the report) | `extrude.taken_by_itself` takes the pieces of a shape drawn over a projected edge (Fission 180's own rule), and a click toggles | `extrude_pick_core.toggled` (new, unit-tested), `extrude_ui.ExtrudePanel._toggle`, `_start` (`_auto_pieces`): a click on one of the pieces the dialog took starts the person's own choice; one area taken by itself still toggles off (Fusion) |
| 7 | Saturn 950 (the fin), new | The fin's outline did not close: the last line ended 0.06 mm beside the first corner, unjoined; no profile, Extrude refused | Clicking the first point closes the shape (Autodesk sketch basics) | Three, in `sketch_infer.Inference`: the line's end click counted as a new line's first click when FreeCAD's preview could not be read, so the first point was never made exact (0.09 mm off its grid crossing); a grid or guide point exactly on an existing point was not that point; and the closing Coincident was the constraint dropped when an older point-to-point guide made it redundant | `Inference._step`, `Inference._landed_on_snap` (new, used by `_plan`), `_guide_now_the_line` (new, used by `_apply_shape`) |
| 8 | Saturn 969-971 (USDZ), new | USDZ written, but the white / black / steel rocket came out all grey | Export keeps the looks (Autodesk blog, USDZ) | `export.body_looks` read the body's own view; Fission 180's looks are written to the steps' views | `export.body_looks`: the end step's colours first |

## Where the report was wrong about Fusion (the replay does what Fusion does)

- Donut 772-776, "Fusion would place them where clicked": with Snap ticked (Fusion's
  default) a free point goes to the nearest grid crossing (sketch-c's sources). The replay
  clicks 8 mm above the axis and checks the point on (30, 10).
- Donut 860, the icing: the book drags the plain look of In This Design onto the top half
  and edits its colour; the replay does exactly that (no custom colour needed).
- Saturn 945: typing -52 is Fusion's own way too; the replay types it.

## What simply worked (each is a step of the replays)

Basics: new design view and grid, the Data Panel (icon, New Project and New Folder typed in
place, the folder's menu, Delete, the empty space's menu, X, Ctrl+Alt+P), the Units row's
button and double-click, the Origin eye, workspaces and ribbon order, Grid Settings, the
mouse, the ViewCube, the profile button and Preferences, a sketch edited from the timeline.

Donut: everything of the report's list, from the Front plane sketch to Save into
"1 - Fundamentals"; Revolve gives 315,827.3 mm3 exactly; the bite is checked against an
OpenCASCADE cut of both halves.

Saturn V: the tube (exact volume), Appearance search and Favorites, Project on the face
(nothing twice, no complaint), the two-profile frustum with Taper -16 as one cone, black
oxide on one face, the face extrude, Offset Plane -13 at z 450, the seven tapered stages
to 600 mm (each picked from the fitted view, 12-44 px faces), the looks on the band, the
long cone and the mesh (Rotation 45), the thruster (Coincident to the rim, H/V, D 25,
-52 / -11 / Join, one cone with a 2.39 mm top, Fillet 2.9), the fin (Coincident line and
origin, the four dimensions, Symmetric / Whole Length 2.4, Join), its Split Face with XZ
picked in the browser, a look dropped on an edge (the face next to it, nothing else
changed), the Circular Pattern of four features including the Split Face (all eight fin
tip halves split), Save, USDZ with the colours.

## FreeCAD facts and traps

- Under xvfb there is no window manager: after a modal box, a dialog window or a real drag
  ends, no window is active and a shortcut goes nowhere (`replay_a_steps.keys_to_window`).
- A wheel event goes to `Gui::View3DInventorViewer`, with its position in that widget's
  coordinates (`gl.mapTo(viewer, pos)`; `viewer.mapFrom(gl, ...)` prints "parent must be in
  parent hierarchy").
- The sketch's axis lines: `RootCrossMaterials` / `RootCrossCoordinate` /
  `RootCrossLineSet` in one `SoGroup`. A second line set drawn after FreeCAD's at the same
  depth does not show (also with its own `SoDepthBuffer` LEQUAL); drawn before, it does. A
  node found by a search action is not kept alive by Python: removing it from its parent
  after FreeCAD deleted the edit nodes is a segfault.
- A real drag and drop works under xvfb through XTEST when the moves and the release come
  from a timer (Qt runs the drag in a loop of its own): `replay_a_steps.drag_look`.
- `BoundBox` of a torus is a little off (119.9 for 120): `optimalBoundingBox(False, False)`.
- After a cut a body's `Shape` can be a compound (no `CenterOfMass`): go through `Solids`.
- The Sketch Palette's "left to define" follows the solver on a timer of its own: wait for
  it by state.

## Steps skipped as out of scope

- Basics: the Render and Generative Design workspaces; A360 / cloud projects (a project is
  a folder on this computer).
- Donut and Saturn V: rendering (the oak, the brushed steel and the mesh are drawn
  patterns; the mesh look has no see-through holes).
- Saturn V: the fin's exact outline in the book's figure (not at hand): the report's four
  numbers 28 / 30 / 12.5 / 30.5 laid out as a fin standing on the thruster.

## Changelog lines

- Fit (F6) in an empty design keeps the origin in the middle also while the origin's planes
  are shown.
- In a sketch the two axis lines have the colours of the design's axes: on the Front plane
  the upright line is blue (Z), as in Fusion; it used to be green.
- In Extrude, the small round taper handle no longer sits on an area you still want to
  click.
- Split Face: a click on a construction plane drawn over the part picks the face behind it.
- A split face stays split while you change the next Extrude in its dialog (the Saturn V's
  black band no longer disappears).
- Extrude: when it picked the halves of a circle by itself, clicking the halves one after
  the other (as the book says) picks exactly those halves.
- Sketch Line: clicking near the first corner of an outline closes it, also when the grid
  or a guide put the click on that corner.
- USDZ, 3MF and OBJ exports carry the colours you gave the bodies and faces.

## Known issues

- Round faces show FreeCAD's seam lines (the white tube of the Saturn V has one).
- A cone extruded from two touching profiles (the thruster) keeps a line where its two
  halves meet; a click on it while sketching projects it (Auto project edges on reference).
  Click a little beside it.
- A circle drawn with its centre within a few pixels of a projected rim snaps onto the rim;
  the book's Coincident then says "already makes it so" (zoom in to draw it beside the rim).
- Extrude still picks by itself the pieces of a shape drawn over a projected edge (Fusion
  picks nothing when a sketch has several areas); a click on one of them starts your own
  choice.
- The oak at 100 % shows the pattern stretched over the ring in places; at the book's 44 %
  it reads as wood.
- The active body's row carries a dot ("Body1 ●"); Fusion shows none.
