# Session log: wave 7, replay-a (`sf/replay-a`, 2026-11-11)

The acceptance test of wave 7 for the book's chapter 1, first half: Project 0 "The Basics",
Project 1 "Classic Donut", Project 2 "Saturn V Rocket" (book parity report lines 655-973),
replayed step by step with real input and a user's defaults (brief
`docs/fission180/dev/briefs/book-replay.md`). Every hitch found on the way is fixed here.

Scenarios: `replay_00_basics`, `replay_01_donut`, `replay_02_saturn_v`; helpers
`Fission180Tests/gui/replay_a_steps.py`; unit `Fission180Tests/unit/test_replay_a.py`.

## Status

| Project | Scenario | Checks | Result |
|---|---|---|---|
| 0 The Basics | `replay_00_basics` | 102 | PASS |
| 1 Classic Donut | `replay_01_donut` | 197 | PASS |
| 2 Saturn V Rocket | `replay_02_saturn_v` | - | not yet replayed |

## Hitches

| # | Project, report line | What happened | Fusion (source) | Root cause | Fix (function) |
|---|---|---|---|---|---|
| 1 | Basics, 697 ("Origin planes are small and the Fit (F6) frames them off-centre in an otherwise empty view") | Still there: eye of Origin on, F6: the view zoomed in to 49 mm and the origin stood 254 px left of the middle | Fit frames the design; the origin's planes are not part of it (Guess; the shell builder's rule "an empty design: the origin in the middle" is the same) | `view_fit.content_box` asked the empty first body for its box; a body without a shape answers with its view provider's box, which is the box of its Origin's planes once they show | `view_fit.object_box`: a `PartDesign::Body` without a shape has no box |
| 2 | Donut, 748 ("the vertical axis is drawn GREEN ... The book tells you a green vertical axis means your Z-up preference is wrong") | Still there (#33cc33 on the upright axis of a Front plane sketch); two builders had left it open ("Not built") | A sketch shows the origin's own axes: red X, green Y, blue Z (Book) | FreeCAD paints the sketch's level line red and its upright line green, constants in C++ that it writes again at every recolouring | `sketch_axes.py` (new: `axis_of`, `colours`, `shown`, `directions`, `AxisColours`): the two lines are drawn a second time right before FreeCAD's own, with its coordinates, in the origin axes' colours; a hovered or selected axis keeps FreeCAD's highlight. Hooked in `sketch_mode.SketchSession.__init__` / `_refreshed` / `close` and the two mouse-event pokes of `sketch_mode._MouseFilter` |
| 3 | Saturn V, 924 ("right after picking the first profile, the arrow and value boxes sit on top of the other profile and swallow the click meant for it"), met in the Donut's bite | The second of the bite's five areas could not be picked: the taper disc of the Extrude dialog sat exactly on it | Fusion's manipulators sit on the picked profile (Guess) | `ExtrudePanel._make_taper_handle` put the disc on the picked profile's right edge (as seen on the screen), which is the next circle's overlap; extrude's wave 7 fix only moved the value boxes | `extrude_ui.ExtrudePanel._taper_pivot`, `_unpicked_faces`, `_covers_free_area` (new), used by `_make_taper_handle`: the disc goes to the profile's other edge when an area that can still be clicked lies under it |

## Where the report was wrong about Fusion (the replay does what Fusion does)

- Line 772-776, "Fusion would place them where clicked": with Snap ticked (Fusion's default)
  a free point goes to the nearest crossing of the grid lines (sketch-c's sources: Lynda,
  Autodesk forum). The replay clicks 8 mm above the axis with the book's grid and checks
  the point on the crossing (30, 10): not on the axis, and not where clicked either.
- Line 860, the pink icing: the book drags the plain look of In This Design onto the top
  half and edits its colour; the replay does that (no custom colour needed).

## What was checked and simply worked (no hitch)

Basics: new design view and grid, Data Panel (icon, New Project, New Folder typed in place
with the keyboard's own focus, folder menu, Delete, empty-space menu, X, Ctrl+Alt+P), Units
row button and double-click, Origin eye, workspaces, ribbon order, Grid Settings, wheel /
middle drag / Shift + middle drag, ViewCube, profile button and Preferences, a sketch
edited from the timeline.

Donut: Front plane sketch (FRONT, SKETCH tab, palette rows), Snap to the grid crossing, F6
in the sketch, one Ctrl+Z too many (stays in the sketch), Horizontal/Vertical centre to
origin, D with Scale entire sketch at first dimension, the diameter, Fully constrained,
Revolve (profile taken by itself, sketch on show, Z axis, torus 120 x 120 x 40 of
315,827.3 mm3, Body1), the eye of Bodies, Appearance (default look listed, Wood, search,
Oak dragged with the real mouse, editor, Scale 44 %), Fit Point Spline (no control frame,
no labels, solves), Fix/Unfix on a spline, Split Body with Extend Splitting Tool (two
bodies, same volume), the nested row's eye, three circles, Ctrl + click adds, Fix/Unfix of
a selection, Extrude (five areas, Cut by itself, Symmetric keeps Cut, Measurement, 20 and
Enter: the bite out of both halves), the pink icing, Save with the dialog's folder tree.

## FreeCAD facts and traps

- Under xvfb there is no window manager: after a modal box, a dialog window (the look
  editor) or a real drag ends, no window is active and a shortcut (Ctrl+Alt+P, Ctrl+S) goes
  nowhere. `replay_a_steps.keys_to_window()` does what a desktop does. Not a hitch of the app.
- A mouse wheel event sent to the 3D view's OpenGL widget is ignored: it goes to the
  `Gui::View3DInventorViewer` above it.
- The sketch's axis lines: nodes `RootCrossMaterials` (2 colours, (0.8, 0.2, 0.2) and
  (0.2, 0.8, 0.2)), `RootCrossCoordinate`, `RootCrossLineSet` in one `SoGroup`. A second
  line set drawn AFTER FreeCAD's at the same depth does not show (also with an
  `SoDepthBuffer` LEQUAL of its own); drawn BEFORE it, it does. A node found with a search
  action is not kept alive by its Python proxy: `parent.removeChild` after FreeCAD deleted
  the edit nodes is a segfault. Do not keep such a parent.
- A real drag and drop works under xvfb through XTEST when the moves and the release are
  sent from a timer (Qt runs the drag in a loop of its own): `replay_a_steps.drag_look`.
- FreeCAD's `BoundBox` of a torus is a little off (119.9 for 120): use
  `optimalBoundingBox(False, False)`.
- After a cut a body's `Shape` can be a `Part.Compound` (no `CenterOfMass`): go through
  `Shape.Solids`.

## Steps skipped as out of scope

- Basics: the Render and Generative Design workspaces in the switcher; A360 / cloud projects
  (a project is a folder on this computer).
- Donut: a rendered wood (the oak is a drawn pattern; no reflections).

## Seen and not fixed (so far)

- The oak pattern on the donut at 100 % shows the pattern's own arches as "stars" and its
  pixels in places (a 128 pixel picture stretched over the ring); at the book's 44 % it reads
  as wood. Looks' own texture, not changed here.
- Round faces show FreeCAD's seam lines (the report's line 908): the donut has two black
  lines (round the tube, along the outer rim). Not addressed by any builder; see Known
  issues.
- The active body's row carries a dot ("Body1 ●"): Fission 180's own mark, Fusion has none.

## Changelog lines

- Fit (F6) in an empty design keeps the origin in the middle of the view also while the
  origin's planes are shown (it zoomed in on the little squares, off to one side).
- In a sketch the two axis lines have the colours of the design's axes they lie along: on the
  Front plane the upright line is blue (Z), as in Fusion; it used to be green.
- In Extrude, the small round taper handle no longer sits on a neighbouring area you still
  want to click (three overlapping circles: the second area could not be picked).

## Known issues

(filled at the end)
