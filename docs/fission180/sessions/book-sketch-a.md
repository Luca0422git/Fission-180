# Wave 7, sketch-a: drawing, snapping, selecting, display and undo in a sketch (branch `sf/book-sketch-a`, 2026-11-11)

The book parity report (`docs/fission180/dev/research/book-parity-report.txt`) is the backbone;
its statements were treated as leads, not facts. Every item was first reproduced in FreeCAD
1.1.4 with input through the X server (below), then checked against what Fusion's own
sources say, then fixed at the cause. Behaviour spec with sources:
`docs/fission180/parity/sketch.md`, section "Wave 7".

## Real input: `Fission180Tests/gui/x_input.py`

The report said three things only happened "with real X-server input". QtTest hands an event
to one widget with the modifiers written into it; a mouse goes X server -> Qt -> the
application, which works out the double-click and the keys held by itself. `x_input` sends
pointer moves, button and key presses with the XTEST extension (libXtst through ctypes, no
new dependency: Xvfb has it). `x_input.click(pos, held=("ctrl",))`, `double_click`,
`press_drag_release`. It refuses a pixel outside the widget or under a floating panel (a
real pointer clicks whatever is there: an early version opened the MODIFY menu). All nine
`book_sketch_a_*` scenarios use it. It found two things QtTest never showed: the Ctrl+click
bug and the press-and-drag inside the double-click time.

## What was reproduced, and what was not

| Report | Reproduced? | Cause |
|---|---|---|
| Ctrl+click does not add | Yes | While a button is down FreeCAD's view shows a pointing hand (and keeps it while Ctrl stays held). Fission 180 took "cursor is not an arrow" for "a tool runs": the release went through the inference's Ctrl path, which shrinks the pick radius, so FreeCAD found nothing to select |
| A plain click adds | Yes | FreeCAD's sketch toggles on every click (ViewProviderSketch: `preselectToSelection(..., toggle)`) |
| Double-click "selects and deselects" | Only inside Circular Pattern | Outside a tool the chain was selected. In a tool's Objects selection the second click of the double-click toggled the curve off |
| Snap far too strong | Yes | Two causes: Grid Settings' major spacing was handed to FreeCAD as the line spacing (50 mm lines for 50 / 5), and FreeCAD snaps within a fifth of the spacing, a model distance (10 mm = 55 px) |
| 45 degree driving angle | Yes | Our own: the 45 degree snap added an Angle constraint after the click |
| Press and drag draws no arc | Yes, when the press comes within the double-click time of the click | Qt reports that press as a double-click, which ended the chain |
| The chain ends at the origin | No: a chain through the bare origin goes on | In the report the origin was also the polygon's centre: existing geometry, where Fusion ends the chain too |
| One Ctrl+Z too many leaves the sketch | Yes | It undoes "Create Sketch", which deletes the sketch |
| Redo does not reopen it | Yes, and worse: Ctrl+Y with nothing to redo finished the sketch | `commands.make_way_for` finished the sketch to "make way" for a command that could not start |
| Ctrl+Z removes only the constraints | Yes | FreeCAD's line is three steps here: the line, "Add Auto-Constraints", our "Inferred Constraints" |
| The sketch hidden after Finish Sketch | Yes, after an Undo and Redo of its making | FreeCAD hides a sketch while it is open; the redo brings it back hidden and TempoVis "restores" hidden |
| Undo reverted an X toggle | Not reproduced | Most likely two steps in one press (the glued steps); the Coincident tool itself added one PointOnObject here, no Symmetric |
| The SKETCH tab vanished after undoing a pattern | Not reproduced (the tab stayed through every undo tried) | Probably the same as "one too many": with the sketch's making undone and redone, FreeCAD's sketch came back without Fission 180's session |
| Polygon / spline / ellipse helpers shown | Yes | FreeCAD draws every helper curve and constraint |
| "Solver failed to converge" on a fresh spline | Not reproduced | In the report all six points had been snapped onto the axis (a spline of collinear points); with the snap fixed it does not happen |
| "Redundant constraints (17)" on a polygon | Not reproduced with the polygon alone | The polygon's own constraints are consistent (solve 0, nothing redundant, also with Horizontal on an edge). The report's polygon sat on the axis, where the edge is level already: the Horizontal was the redundant one; refusing it with the reason is `sketch_explain`'s (sketch-b) |
| Deleted Auto-projected edges come back | Yes (by reading `follow`), and Del on four of them raised three errors | `follow()` re-projected when it found none of its curves; FreeCAD removes a face's reference with the first edge |
| Fit zooms out to 24 m | Yes (the cause: the Layout Grid node, four view heights wide, in the scene's bounding box) | Each Fit framed the grid, which then grew |
| A dimension placed on an axis becomes an angle | Yes | FreeCAD's Dimension tool takes any click on something for one more pick |
| No Centerline | Yes | Not built before |
| Inch grid metric | Yes (by reading the code) | The adaptive grid always started from 10 mm |
| 80 s freeze after a drag + undo (Fire Piston) | Not reproduced, not profiled | A component drag in an assembly (joints' and modify's files: `undo_*.py`); nothing of the sketch code runs there |

## Where the report (or the brief) was wrong about Fusion

- **"Fusion would place them where clicked"** (snap). The sources say the opposite: with Snap on
  the pointer snaps to grid intersections, for every point that no inference takes (Lynda
  course, Autodesk community manager). What was wrong in Fission 180 was the 50 mm lines and a
  pull that grew with the grid. Fission 180 now snaps by nearness on the screen; a full snap
  like Fusion's is a decision for Luca (FreeCAD's grid is much coarser on the screen).
- **"Fusion keeps the chain going"** over existing geometry. An Autodesk answer on the forum:
  the sequence ends when you click an existing line, curve or point, on purpose.
- **A centerline "like construction geometry"** (the brief). Autodesk's help: centerline
  geometry still contributes to the profile. Here it is a normal line, so the half profile of
  a turned part closes on it and Revolve finds both the profile and its axis.
- **Auto project "off by default"**: no source found states either default. Luca's wish
  (2026-10-16) keeps the face's edges on.
- **Undo "keeps you in the sketch"**: no source found either way. Built as the report says,
  marked Guess.

## What was built

- `sketch_select.py`, `sketch_select_core.py`: Fusion's click rule, from FreeCAD's selection
  messages; `SketchSession.drawing_cursor` (the pointing hand says nothing).
- `sketch_draw.py`: `DrawTool.chain_double_click` (a tool's Objects selection); hidden helper
  curves are no snap targets.
- `sketch_grid.py` (new) + four lines in `grid_ui.apply_to_sketch`; `sketch_infer_core.grid_snap`
  with a reach, `grid_capped`, `Result.grid`; `Inference._grid_only` / `_grid_plan`.
- `sketch_infer.py`: `DiagonalConstraint` (off); the chain's point follows a tangent arc's end.
- `sketch_mode.py`: the press-and-drag inside the double-click time; `_count_undo` /
  `_back_into_sketch`; every tool's "Add Auto-Constraints" glued; `_show_finished`;
  `_tidy_new` (spline, ellipse, centerline mode); `ControlFrames`; `_delete_projected`;
  `toggle_centerline`; `_diameter_dimension`; `_placing_dimension`.
- `sketch_draw_helpers.py` (new): virtual space and visual layers for helpers.
- `sketch_centerline.py` (new): the line type, the diameter, Revolve's axis.
- `sketch_line.py`: the chain's end says so. `sketch_polygon.py`: tidy at creation.
- `sketch_auto_project.py`: `auto_curves_left`. `sketch_palette.py`: the Centerline button.
- `sketch_ui.py`: `used_by_feature`, `shown_before_edit`.

## FreeCAD 1.1.4 facts and traps

- `Gui.Selection.getPreselection()` can still name a curve after the pointer left it;
  FreeCAD's sketch uses its own preselection for the click. Read what a click did from the
  selection observer's add / remove / clear, not from the preselection.
- A sketch element is kept in the selection under the object the sketch is edited through
  (`Body`, "Sketch.Edge1"): `removeSelection(doc, "Sketch", "Edge1")` removes nothing. Clear
  and add again.
- `View3DInventorViewer::setCursorRepresentation`: the navigation's SELECTION mode (any left
  press) sets a pointing hand; with the Revit style, Ctrl held alone changes no mode, so the
  hand stays after the release until Ctrl goes up.
- FreeCAD's grid snap (`SnapManager::snapToGrid`): each coordinate on its own, within
  `GridSize / 5`. `GridSize` is the distance between two lines; every
  `GridNumberSubdivision`-th line is drawn stronger.
- `doc.UndoNames` lists the OPEN transaction first. A dimension that "is there" with its step
  in the list may not be placed yet (FreeCAD's Dimension tool keeps its transaction open
  while the dimension follows the pointer).
- `sketch.setVirtualSpace(i, True)`: the constraint works and is not drawn; saved with the
  file. Visual layers: every sketch has three (0 normal, 1 dashed "discontinuous", 2 hidden);
  a curve's layer is the `VisualLayerId` of its `SketcherGui.ViewProviderSketchGeometryExtension`
  (GUI only), set through `sketch.GeometryFacadeList`. A hidden-layer curve is not drawn and
  not clickable, and its points are hidden too.
- An ellipse's focus points can be deleted (`delGeometries`); its axes stay aligned.
- FreeCAD's spline tool keeps each clicked point loose until the spline is made. A point
  moved after its click (the grid-reach move) left the finished spline with constraints on
  the wrong curves ("Sketcher constraint number 15 is malformed", `sketch_spline_luca` A).
  A spline's points keep FreeCAD's own grid rule.
- FreeCAD's delete of a projected curve removes the reference it came from; a face's
  reference carries all its edges (`delExternal` of the next index then fails).
- FreeCAD's Dimension tool: a click with something lit under the pointer is a pick, with
  nothing lit it places. A pick radius of 0.01 for one move and click makes it place.
- `run_tests.sh` links the module into the test profile (no copy): a file edited while a
  scenario batch runs is what the later scenarios of the batch run with.
- The scratch folder of a session is shared by every builder of the wave: keep helper scripts
  in a folder of your own.

## Tests

Scenarios (real input through the X server, paced by state): `book_sketch_a_select` (26),
`book_sketch_a_line` (36), `book_sketch_a_undo` (52), `book_sketch_a_shapes` (48),
`book_sketch_a_project` (17), `book_sketch_a_fit` (16), `book_sketch_a_centerline` (40),
`book_sketch_a_dimension` (12). Unit: `test_book_sketch_a.py` (29). Older scenarios changed
for the new behaviour, each with the reason at the changed line: `sketch_glyphs` (no Angle
after a 45 degree snap), `sketch_infer` (one Ctrl+Z takes the line too), `sketch_end_line`
(the release of its double-click).

## Gaps

See "Not built, or still different (wave 7)" in `parity/sketch.md`: Fusion's full grid snap,
Scale entire sketch at first dimension, Auto project edges on reference, world axis colours,
a narrower midpoint snap, the 80 s freeze (not reproduced), a dimension that sometimes gets no
value box (not reproduced; one cause found and fixed: the placement click taken for a pick).

## Changelog lines

- In a sketch a click now selects only what you click; hold Ctrl to add or remove, Shift to add.
- Ctrl+click in a sketch selected nothing; it now adds to the selection, as the book says.
- A double-click on a line inside Circular Pattern, Rectangular Pattern, Mirror, Move/Copy or
  Scale takes the whole connected shape.
- Points no longer jump onto the axis or a grid line from far away: the grid only pulls within
  a few pixels. Grid Settings' "Fixed, 50 mm, 5 subdivisions" now gives a line every 10 mm.
- In an inch design the sketch grid is in inches.
- A line drawn near 45 degrees still snaps to 45, but no angle dimension is added by itself.
- In the Line tool, press on the end of the line and drag to draw a tangent arc, also right
  after the click.
- When a line ends on something already drawn the chain ends, and a note says so.
- Ctrl+Z never throws you out of the sketch any more, and one Ctrl+Z takes back one drawn line.
  Ctrl+Y with nothing to redo no longer closes the sketch.
- A finished sketch stays visible until you use it.
- Polygons, splines and ellipses are shown without FreeCAD's helper circles, points and "="
  labels. An ellipse drawn level stays level.
- Deleting the automatically projected edges of a face now sticks.
- New line type Centerline (Sketch Palette > Linetype): a dimension to a centerline is a
  diameter, and Revolve takes the centerline as its axis by itself.
- The click that places a dimension places it, also on top of an axis or another line.
- Fit no longer zooms out further every time when the Layout Grid is on.

## Known issues

- With Snap on, Fusion puts every point on a grid crossing; Fission 180 only pulls a point that
  is close to a grid line. Turn Snap off in the Sketch Palette for no pull at all.
- "Scale entire sketch at first dimension" does not exist yet: dimension every size.
- A centerline dimension shows the diameter as a plain number (no diameter sign).
- Deleting one of the automatically projected edges of a face removes all of them; project the
  ones you want again with P.
- A control point spline's dashed frame catches up when you let go of a dragged point.
- Sketch axes are drawn grey; they do not show the world axis colours.
