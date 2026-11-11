# Wave 7, the book replay, part C (chapters 2 and 3): session log

Builder "replay-c", branch `sf/replay-c` (from develop 39fd9e9b). The brief:
`docs/fission180/dev/briefs/book-replay.md`. Projects: 6 Play Brick, 7 Geocache Hide,
8 Metric Bolt, 9 Prototype Drone (report lines 1210-1636).

Each project is one scenario, `Fission180Tests/gui/scenarios/replay_<nn>_<project>.py`, with a
person's defaults (`replay_c_steps.user_defaults`: Snap on the grid, Scale entire sketch at
first dimension, the layout grid, the first component grounded, an undo step left open is a
failure). Helpers: `Fission180Tests/gui/replay_c_steps.py`.

## Project 6, Play Brick: `replay_06_play_brick` (199 checks, PASS)

Replayed, in one design: Box typed on the canvas (31.8 Tab 15.8 Enter 9.6 Enter), the stud's
sketch on the top face (circle 4.8, 3.9 / 3.9 from the origin with D), E 1.8, Draft 1 degree
(first an OK with no face: refused, the pull direction stays), Rectangular Pattern of the
Extrude and the Draft with the directions clicked on two edges (Spacing, 4 x 8, 2 x 8), Shell
1.2 from the bottom face, a sketch on a stud with the text PLAY (two clicks, bold, italic,
centre, middle, height 1) and Tangent between each frame line and the stud's projected rim, E
of the letters 0.1, the pattern of that extrude, M with Y Angle 180, a sketch on the inner
face (three pairs of circles drawn freehand, concentric by inference, Ctrl+click three + Equal
twice, D 6.51 and 4.8, the centres placed with D and Horizontal/Vertical), E of the three rings
8.4, Draft of six tube walls, Appearance search "red plastic" and a drop, M back, four Ctrl+Z
and four Ctrl+Y, Ctrl+S, the tab closed, the design opened again from Home.

Hitches found and fixed:

| Report line | What happened | Fusion (source) | Root cause | Fix |
|---|---|---|---|---|
| 1224 ("OK" in the report) | The stud's second "3.9 from the origin", put to the left of the two points at half height, became the slanted distance: the circle ended at (3.9, 0) | Straight left or right of two points is the vertical distance, straight above or below the horizontal one; the aligned zone of a nearly upright line is small (Autodesk forum "Dimension diagonal line"; the exact zones: Guess) | `sketch_dimension_core.linear_kind` gave the aligned length everywhere between the two perpendiculars through the points, also outside their box | `linear_kind`: outside the points' box on one side only is VERTICAL / HORIZONTAL; aligned inside the box and in the corners square to the line. Unit tests `test_sketch_dimension_core` |
| 1231-1236 | The first edge clicked became Direction 1, the second edge was not taken: the dialog had gone back to Objects, Direction 2 stayed the one worked out | Fusion's Rectangular Pattern has one Axes box that takes two picks (Autodesk help "Rectangular Pattern": "Axes: select up to two") | `pattern_ui.PatternPanel._reference_picked` always went back to the Objects box | After the first direction the second direction's box is the active one (once; not when editing). `patterns_rect` updated: it checked "Objects box active again" |

Not hitches, but facts a replay has to know:

- A click that places a dimension on another curve is a second pick (Fusion too): the replay
  places dimensions in empty space.
- Circles drawn freehand with Snap land on the grid; drawn so large that they touch, they get
  a Tangent by inference (Fusion infers it too). The replay zooms in first, as a person does.
- A cone's half angle is negative for a drafted hole: the tube bores lean -1 degree.
- Shell 1.2 hollows the studs too (Fusion's Shell does the same; a real brick has them).
- Closing the last design shows Home; the design is opened again from its Recent row.
- The Save dialog's default folder is the person's Documents/Fission 180 Designs: the replays
  set `ProjectFolder` to a temporary folder first.

Skipped (the report skipped them too, and gives no positions): the twelve 0.2 x 0.6 rectangles
with their mirrors and the ribs between the tubes.

## Project 7, Geocache Hide: `replay_07_geocache` (190 checks, PASS)

Replayed, in one design: Cylinder 33 x 16 typed on the canvas (OK before the centre is
refused with the reason), Body1 renamed "Bottom Screw" by a double-click in the browser,
Chamfer 3 on the top edge, Thread on the side (M33x3.5 offered, Modeled), Thread 1 dragged in
front of Chamfer 1 (the thread then runs into the chamfer), Offset Face -0.25 on the thread
(one click takes the whole thread), the knob (Cylinder 40, Height -8 typed: grows away from
the screw, Join), Coil (0.1 rev, -10, Triangular (Internal), Inside, 1, Cut), Mirror of Coil 1
about XZ from the browser, Circular Pattern of Coil 1 + Mirror 1 about Z, 25 (light preview,
built once on OK outside the window's process: 20-50 s on this machine, with a progress
window), the Top Cap (a sketch on Front, six lines drawn freehand and dimensioned, Revolve
about Z from the browser: New Body), the screw hidden with its eye, Thread on the cap's inner
wall (Modeled remembered, Full Length off, 18), Offset Plane -30 from XZ, a sketch on it with
the words (Height 7.5, centred), Emboss 0.75 onto the cap, a second sketch with Insert SVG
(0.3, both flips, -15 / 2), Create Group of the whole timeline, Section Analysis on XZ,
Ctrl+Z / Ctrl+Y, save, close, open again from Home.

| Report line | What happened | Fusion (source) | Root cause | Fix |
|---|---|---|---|---|
| 1306-1307 | Cylinder Height -8 for the knob (the centre on the screw's plane): the -8 went into the Diameter (the knob came out 8 across, 50 high) | Right after placing, the number typed is the height (Book; Fusion's on-canvas flow) | The Height arrow's box was off the screen (the first preview is 50 high); `PlacedPanel.typing_field` then gave the last size typed (Diameter) | `primitives_ui.PlacedPanel.typing_field` / `typing_box` / new `_just_placed`: right after placing, the READY_KEY (Height) field takes the number when its box is not shown |
| 1315-1319 | The knurl: only the mirror's 25 copies were cut, the coil's copies cut nothing (half the knurl) | The pattern repeats both features (Book) | FreeCAD keeps a feature's tool solid (AddSubShape) in the feature's own coordinates; a feature takes the Placement of the step before it, here the knob primitive's (z -8); `pattern.feature_tools` took it as it was: 8 mm too high | `pattern.add_sub_shape` (new), used by `feature_tools`, `objects_center`, `feature_of_face`. Same mistake fixed in `extrude_bodies.lead_tool` (`_placed_tool`, new). Golden `pattern_circ_after_primitive_off_origin`, headless `replay_c_check` |
| 1346-1347 | Emboss: the offset plane in front of the cap took the click meant for the cap's face | Fusion's Faces box takes faces only: the click reaches the face (Guess, from how selection filters work) | `emboss_ui.EmbossPanel._take` ignored a plane | `_take`: a plane clicked while the Faces box is active looks behind it (`_face_behind`, new, `view.getObjectsInfo`) |
| 1355-1356 ("OK") | After Create Group of the whole timeline, the next recompute (Section Analysis's) rebuilt every step, the knurl too: 35 s, no progress note | A group is a timeline folder; nothing is rebuilt (Autodesk help "Timeline groups") | `timeline_ops._set_group` adding the group properties touched the steps (their Output flag notwithstanding) | `timeline_ops._untouched` (new) around `_set_group` and `rename_group`: a step not touched before stays untouched. Section now 1.2 s |

Where the report was wrong about Fusion, or the stand-in differs:

- The cap's internal thread on a 33 bore is offered M33x3.5 (the nearest nominal, Autodesk
  tech tip; thread_tables.closest), not the report's M36x3: it fits the screw, as the book wants.
  The threaded hole then goes to the minor diameter (Autodesk forum "BUG thread changes the
  hole diameter": as designed), so the cap gains material.
- Thread remembers Modeled from the last thread (Fusion does): the replay leaves it ticked.
- A click on a wall with another wall in front picks the front one, in Fusion too: the replay
  hides the screw (its eye) and clicks the far inner wall through the open end.
- The words are on two lines: the stand-in cap (39 across) is smaller than the book's.
- The cap profile is dimensioned inner wall before outer wall: with the outer wall set first
  (after Scale at first dimension had grown the sketch 1.5 times) its top came below the inner
  top and the profile crossed itself; the solver moves only what a dimension pulls (Fusion too).
- The knurl's groove pair is a V (the coil and its mirror meet at the top), so the replay
  counts the grooves at mid height: 50, 7.2 degrees apart. (`book_modifyc_knurl` checks the
  removed volume against a pair measured with 3 copies; it would also pass with half the
  grooves. Not changed: its stand-in is built by script, where the coil has no offset.)

## Project 8, Metric Bolt: `replay_08_metric_bolt` (117 checks, PASS)

Replayed, in one design: MODIFY > Change Parameters, "+" nine times (Head_Diam 8.5,
Head_Length 5, Shank_Length 45, Bolt_Diam 5, Wrench_Width 4, Wrench_Depth 3, Thread_Length =
Shank_Length / 2, Chamfer_Size 1, Quantity 6 with No Units), the half profile on Front drawn
with L, its bottom line made a Centerline with the palette, D to the centerline giving the
diameters, the bare names typed in the value boxes (Head_Diam, Bolt_Diam, Head_Length,
Shank_Length), S "rev" Enter, Revolve (the centerline the axis by itself), the hex socket
(Circumscribed Polygon on the head's end, its circle "Wrench_Width", E "-Wrench_Depth": Cut by
itself), Chamfer with two sets (the shank's end "Chamfer_Size"; "+", both head ends 0.5),
Thread on the shank (Modeled, Full Length off, "Thread_Length": M5x0.8, 22.5), Thread 1
dragged in front of Chamfer 1, Change Parameters Shank_Length 25 (the bolt 30 long, the
thread 12.5), Circular Pattern of the bolt body about Z with Quantity "Quantity" (6 bolts),
Change Parameters Quantity 8 (8 bolts), Ctrl+Z / Ctrl+Y, save, close, open again.

| Report line | What happened | Fusion (source) | Root cause | Fix |
|---|---|---|---|---|
| 1410-1411 (skipped there) | Thread 1 dragged in front of Chamfer 1: refused, "Chamfer 1 would fail there: Set 1: Distance 1 mm is too big here" | The thread then runs into the chamfer (Book; the report's own Geocache line) | `fillet_robust.thread_twin` takes the grooves as the blank minus the threaded part; for this bolt (revolved on the Front plane, its Revolution placed by the sketch) that boolean gave the whole blank back, and the chamfer cut by it left nothing | `thread.groove_tools` (new): the thread's own cutting tools; `fillet_robust._grooves_plausible` (new) in `thread_twin`: grooves that do not hold what the thread took away are replaced by those tools |
| (not in the report) | After that drag the view drew the Thread step (no chamfer at the shank's end) and the browser's eye said Body1 was hidden, also after save and reopen | The body shows its last step (FreeCAD's Tip; Fusion shows the result) | the recompute in `timeline_ops.move` showed the moved step again after `_set_tips` had shown the Tip | `timeline_ops.move`: after the recompute, `_show_only_tip` for each body. Checked in both replays (`tip_shown`) |

What the report said that is no longer so (fixed by the wave's builders, replayed here with
the book's input): "+" in Change Parameters works; the Centerline linetype exists and D to it
gives a diameter; bare parameter names work in the sketch's value boxes; a body pattern
follows its Quantity parameter.

Skipped as the report did: the 40 straight knurls on the head (no sizes in the report;
`book_modifyc_knurl` builds them).

## Project 9, Prototype Drone: `replay_09_drone` (155 checks, PASS)

The report never rebuilt the drone with its own sketch; it is rebuilt here from its text, in
its plainest form: a hub (20 across), a middle ring (drawn freehand, no size) and a rim whose
diameter is "Limits_Arm_Length * 2", cut by twelve spokes made with one line and a sketch
Circular Pattern: 36 areas (the report's "36 selected"). Replayed, in one design: ASSEMBLE >
New Component "Drone Frame" (active, grounded: the first component), a sketch on its Top
plane, MODIFY > Change Parameters from inside the sketch ("+" Arm_Length 53 and
Limits_Arm_Length = min(100; max(45; Arm_Length)): 53 mm, the bare numbers taken as mm), the
circles (20 typed; a click; the rim's formula typed in the circle's box), the spoke from the
origin to the rim, the spoke selected, Circular Pattern about the origin, 12, Finish Sketch
(the sketch stays shown), E with the 24 inner areas clicked, Distance "Thickness = -2.5 mm"
(a parameter made in the box, negative), the sketch's eye, E with eight outer areas,
"Thickness", New Body (four bodies), MODIFY > Combine (target the plate, the four the tools,
Join: one body), Ctrl+Z / Ctrl+Y of the Combine, Change Parameters Arm_Length 50, 40, 110, 53,
60 (the rim 50, 45, 100, 53, 60; every time the same 32 areas, the windows stay: the report's
"Extrude 1 would break: Sub shape not found: Sketch.InternalFace56" does not happen), Fillet
2.5 on the two inside corners of a window, a window drag over the plate in Chamfer, 0.25
(23 edges, 1.4 s; the report: "too big here, also at 0.1"), the sketch opened from the
timeline, the middle ring dragged and Ctrl+Z (0.4 s; the report: "One drag + undo froze the
app for about 80 s"), Finish Sketch, three Ctrl+Z and three Ctrl+Y, save, close, open again,
Arm_Length 70 after reopening.

No hitch of Fission 180's was found in the drone: the wave's builders had fixed the report's
items (parameters dialog, negative and `Name = value` parameters, min/max with bare numbers,
the sketch's MODIFY menu, tied pattern copies, area references that survive a parameter
change, Combine's undo). The replay's own mistakes on the way (all in the scenario):
"-Thickness" for a second extrude when Thickness is already negative put the pieces above
the plate (then Combine rightly kept five solids); edge clicks in a view where the short
upright corner edge was not the nearest edge picked the wall's top edge (a person turns the
part until the edge lights up: the replay looks at each corner from inside the window).

Out of the replay (the report's own stand-ins; other builders' scenarios cover the tools):
the STEP motors, board and battery from CADclass.org (Data Panel Upload, Insert into Current
Design, Move with parameters), Copy / Paste of a component, Rigid Group, Physical Material
and Properties, the appearance.

## Changelog lines

- A dimension between two points that you place straight to the left or right of them is the vertical distance, and straight above or below them the horizontal one, however near you place it.
- In Rectangular Pattern, after you click the first direction the next click sets the second direction, so you can click two edges one after the other as in Fusion.
- A number typed right after placing a Box, Cylinder or other shape goes into its Height, also when the Height arrow is outside the view.
- A pattern of features made after a Box or Cylinder that is not at the origin repeats the features in the right place (the Geocache knurl had only half its grooves).
- Emboss takes the face behind a construction plane when you click through the plane.
- Grouping steps in the timeline no longer makes the design rebuild every step afterwards (a Section Analysis after Create Group waited half a minute).
- Dragging a modeled Thread in front of the Chamfer of its end now works on the Metric Bolt too: the thread runs into the chamfer.
- After a step is dragged in the timeline the part shows its finished shape, and the browser's eye no longer says the body is hidden.

## Known issues

- A knurl of 25 crossing grooves takes 20 to 50 s to build once you press OK (a progress
  window says so and can cancel); Fusion takes seconds.
- A body used up by Combine (Join) stays in the browser, hidden; Fusion takes it away.
- The first body's eye in the browser and what the view draws now follow the body's last
  step after a timeline drag; a design saved before this fix with the wrong step shown keeps
  it until the next change (click the body's eye twice).
- A dimension placed beside a slanted pair of points, inside the box they span, is the
  aligned length; to get the horizontal or vertical one place it straight above / below or
  beside the box (or right-click: Horizontal / Vertical).
- The Rectangular Pattern's second direction takes the click after the first only once per
  dialog; to change Direction 1 again later, click its box first.
- Not replayed: the Drone's motors, board and battery (CADclass.org STEP files), Copy and
  Paste of a component, Rigid Group, Properties; the Geocache's STL export; the Play Brick's
  twelve small rectangles and the ribs; the Metric Bolt's 40 knurls.
