# Wave 7 acceptance replay, part b (builder "replay-b", branch `sf/replay-b`)

Chapter 1, second half of *Mastering Autodesk Fusion, 2nd ed.*: Project 3 "Finger
Surfboard", Project 4 "Tensegrity Tower", Project 5 "Carabiner" (book parity report lines
974-1209). Brief: `docs/fission180/dev/briefs/book-replay.md`. Each project is replayed as
one scenario, from its first step to its last, in one design, with a person's defaults
(`replay_b_steps.user_defaults`: full grid snap, scale at the first dimension, the layout
grid, first component grounded; an undo step left open fails the run) and real input only.

## Status

| Project | Scenario | State |
|---|---|---|
| 3 Finger Surfboard | `replay_03_surfboard` | steps 1-8 replay clean (121 checks); fin extrude, tail hole, fillet, export being written |
| 4 Tensegrity Tower | `replay_04_tensegrity` | not started |
| 5 Carabiner | `replay_05_carabiner` | not started |

## Project 3, Finger Surfboard: hitches

| Report line | What happened in the replay | Fusion (source) | Root cause | Fix (function) |
|---|---|---|---|---|
| 1001-1006 | Loft: the click on the ORIGIN (as the book says) took the offset plane's square drawn over it: "Plane1 is no profile" | Loft to a point, the origin among them (Autodesk blog "Get Smart ... Loft"; forum "Loft the base to a point (Origin)") | In a new design the Origin folder is hidden, so the origin point itself cannot be clicked; the layout grid's dot shows there, and the square in front took the click | `loft_ui.LoftPanel._origin_dot`, `_pressed`, `_origin_clicked` (a press on the origin's dot picks the origin point); `profile_pick.origin_dot_point` |
| (new) | Loft's Profiles list said "Sketch003 (area)" for the browser's "Sketch 4" | Dialogs name things as the browser does (Guess) | FreeCAD's Label shown | `loft_ui.shown_label` -> `timeline_ops.shown_label` |
| 1017-1019 | Intersect: in the front view the four offset planes cross the board as yellow lines; a click there gave a traceback "Not able to add external shape element Plane" and nothing in the sketch | Intersect brings the curves where the sketch plane cuts what is clicked (Autodesk help, Project / Include > Intersect) | FreeCAD's Sketcher_Intersection takes a datum plane and calls `addExternal(plane, defining=True)`, which fails for planes | `sketch_tools_ui._PlaneClicks` (a click on a plane while Intersect runs: the line where the planes cut, or a refusal with the reason); `SketchIntersect.run` |
| 1023 | Fin extrude: Join shown, but "Touches no body: a new body is made" and a second body made | Join joins the fin to the board (Book) | The fin touches the board only along the Intersect curve (its top edge, in the profile plane); no shared volume, no shared face: not "touching" | `extrude_bodies._curve_contact` (points of the profile's and the solid's edges classified, no boolean) in `in_the_way` and `bodies_in_way` |
| 1023 | Once joined, the board's deck was no longer drawn and the tail edge could not be clicked | One body (Book) | OpenCASCADE's fuse of the board and a fin that touches it only along a curve returns the fin alone (4 faces) | `extrude_bodies.beside`, `join_shape`, `joins_beside`; `extrude._structure` (such a Join is Fission 180's own extrude feature), `ExtrudeFeature.execute` (the two solids side by side in one body) |
| 1034-1041 | D from the hole's centre to the board's tail EDGE: the edge was not reached (the click fell on Plane 4, at x = 140, seen edge-on over the tail edge) | The edge is projected on the fly (Fusion's "auto project edges on reference": sketch-b's fix) | `sketch_project_across.element_at` took only the first thing under the pointer | `sketch_project_across.element_at` looks through origin / construction planes and axes (`_is_glyph_info`, `_element_of`) |
| 1042-1043 | Tail hole: Extent All, Flip: Join stayed (the book: red Cut by itself) and OK added a stub of cylinder | Cut (Book; Autodesk: an extrusion that "intersects a solid" is a Cut) | The share a body takes of the extrusion ("reaches into it by 1 %") was counted against the whole All prism, which runs four times the design's size past everything: the 4 mm board was 0.9 % of it | `extrude_bodies._within_reach` (the share is counted against the prism inside the bodies' box) in `in_the_way` |
| 1044 | F: a click on the fin's edge took Plane 3, drawn over it: nothing picked | A command picks only what it takes (Fusion's selection inside a command) | FreeCAD's click selects the first thing under the pointer | `fillet_ui.BlendPanel._behind_glyph`, `_released`, `_GlyphRelease` (Fillet and Chamfer pick the edge or face behind a plane or axis) |
| 1044 | F 1 mm on the fin's two edges and the hole: "1 mm does not fit: limited to 0.49 mm" | 1 mm (Book; the report's 3.3.9 run said OK, maybe capped silently then) | The fin is a solid of its own beside the board (it touches it along a curve only), so the rounds of its outline run into its own top edges at its ends (0.71 fits); the hole's rims are 1 mm from the board's tail (0.49 fits) | NOT FIXED (see Known issues) |
| (speed) | Each change in the fin's Extrude dialog took about 2 minutes under the test machine's load | - | `extrude_bodies._same_surface` took any two faces that meet along a curve for "one surface" (their distance is 0) and then made a boolean of them (10 s each, 8 per preview) | `extrude_bodies._same_surface` / `_lies_on`: points inside one face must lie on the other's surface (about half the time now; the two booleans of `start_state`'s 0.01 mm slices remain) |
| (test env) | E after the look editor (a window of its own) did nothing | - | The test screen has no window manager: the main window stays inactive after the editor closes; not a product bug | `replay_b_steps.key` activates the main window first, as a desktop does |

Book steps that are not what the report did, with the reason:

- The ellipses' centres are put BELOW the origin. The book's later tail hole is sketched on
  the Top plane and needs Flip to go into the board (report line 1042), which only happens
  with the board under that plane.
- The book's canvas picture is a download of its publisher: a stand-in PNG (`canvas.png`).

## Facts found on the way

- `addExternal(datum_plane, "", True, True)` fails ("Not able to add external shape element
  Plane"); `defining=False` works and gives the line where the planes cut.
- Under the load of seven builders (load average 20 on 4 CPUs) a boolean between the lofted
  board and the fin takes 14-23 s; Extrude's `extrude_bodies.start_state` took 170 s.
  Point classification (`isInside`) takes milliseconds: tests that run with every preview
  must use points, not booleans.

## Changelog lines

- Loft: clicking the origin (its dot) as the last section works also when the Origin folder
  is hidden or a construction plane is drawn over it.
- Loft lists its sections by the names the browser shows ("Sketch 4", "Origin").
- Sketch Intersect: clicking a construction plane brings in the line where it cuts the sketch
  (it showed an error in the Report view and did nothing).
- Extrude Join: a part that only touches the body along a curve (the surfboard's fin) is
  joined to it, and the body stays whole on the screen (it made a second body, or lost the
  board's surface).

## Known issues

- Surfboard: the fin joined to the board stays a solid of its own inside the body (it
  touches the board along a curve only; OpenCASCADE's union of the two lost the board). A
  1 mm round on the fin's outline is then held at 0.71 mm (the dialog says so); a fin that
  goes 0.1 mm into the board (draw its top edge a hair above the outline) fuses normally.
- Surfboard: the tail hole's 1 mm rim round is held at 0.49 mm: the hole is 1 mm from the
  tail. Put the hole 2.5 mm from the tail for a full 1 mm round.
- (more to be filled at the end)
