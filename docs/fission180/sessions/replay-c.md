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

## Changelog lines

- A dimension between two points that you place straight to the left or right of them is the vertical distance, and straight above or below them the horizontal one, however near you place it.
- In Rectangular Pattern, after you click the first direction the next click sets the second direction, so you can click two edges one after the other as in Fusion.

## Known issues

- (filled in at the end)
