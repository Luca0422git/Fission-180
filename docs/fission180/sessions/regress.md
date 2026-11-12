# Wave 7, builder regress: a beginner's first half hour, 0.1.0-beta.3.3.10 against the release candidate

Luca installed the release candidate and met a regression within two minutes (a sketch made
while Body1 was hidden did not show; Extrude then proposed Cut on the hidden body: fix-9's,
merged as 8a3ce9e5). About 25 builders had changed the code since 3.3.10, each testing its own
feature. This session compared everyday use of the two versions, step by step, with the same
real input.

Branch `sf/regress`, from develop ccfdcbd7, develop 8a3ce9e5 (fix-9) merged before the last
round. The released code ran from a second worktree (`git worktree add ../regress-3310
7813ef69`), both with the same FreeCAD 1.1.4 (`.fission180-cache/freecad`) and each through its
own `tools/fission180/run_tests.sh`.

## The scenarios

Twelve `Fission180Tests/gui/scenarios/regress_*.py`, sharing `Fission180Tests/gui/regress_steps.py`
(only harness calls and helper modules that exist in 3.3.10 too, so they run on both). Each
starts like a person: Home > New design, with a new user's settings (below). Every sketch is
drawn with the tools' keys and clicks (R, C, D and typed sizes), every command from the ribbon,
a key or a menu; the model is checked (volumes, bodies, which body, Visibility) and the screen
too: what FreeCAD's 3D view picks at known points (`getObjectInfo`, which never picks a hidden
object; `regress_steps.drawn_here` checks the pick lands ON the point, not on what lies behind),
the colours there (a screen grab), and screenshots, which were compared side by side.

| Scenario | What a beginner does | Checks |
|---|---|---|
| regress_first_part | sketch on XY, rectangle 40 x 30 (sizes typed), Finish, E 10; a circle on the top face, E 5 (Join proposed); a circle, E -4 (Cut proposed) | 47 |
| regress_hide_show | the body's eye off / on, the sketch's eye on / off, right-click Hide / Show, a second block (New Body), its eye | 57 |
| regress_offset_plane | Offset Plane 15 above the top, a sketch on the plane, a disc (New Body), a post down onto the block (Join), a small circle on the plane | 51 |
| regress_fillet_chamfer | F on an edge 3, Chamfer 2, double-click the fillet in the timeline 4, Ctrl+Z / Ctrl+Y | 35 |
| regress_hole | H on the top (6 x 5, flat), a face clicked then H (All), Ctrl+Z / Ctrl+Y | 30 |
| regress_undo_redo | block, fillet, boss; Ctrl+Z back to nothing, Ctrl+Y back to all, the view checked each time | 83 |
| regress_bodies_combine | a second overlapping block as New Body, F2 rename Lid, Combine, Ctrl+Z / Ctrl+Y | 47 |
| regress_pattern_mirror | a disc, a boss, Circular Pattern x 4 round Z, Ctrl+Z / Ctrl+Y, Mirror of a second boss | 62 |
| regress_presspull_shell | Q on the top +5, Q on the front -2, Shell 2 open at the top, Ctrl+Z / Ctrl+Y | 28 |
| regress_save_reopen | Ctrl+S (Save dialog), the tab's x, Data Panel, double-click the design, edit the extrude 15, Ctrl+S again | 37 |
| regress_look_measure_tabs | A: red plastic on the block, Ctrl+Z / Ctrl+Y; I: area, two faces; the Home tab and back; wheel out, F6 | 29 |
| regress_revolve_move | sketch on XZ, Revolve round Z, M 30 along X, Delete the Move in the timeline, Ctrl+Z / Ctrl+Y | 28 |

## A new user's settings: what the suite never ran

`harness.run` switches three of wave 7's new defaults OFF for every scenario (full grid snap,
"scale the sketch at the first dimension", the layout grid), because the older scenarios click
free points at exact coordinates and read the empty view's colours. A person has all three on.
So nothing but their own three scenarios ever drew with them: the regress scenarios put the
defaults back (`regress_steps.user_defaults`), and `FISSION180_USER_DEFAULTS=1` now does the same
for any scenario run (harness), for sweeps like the one below.

## Differences found

| Scenario | 3.3.10 | Now | Verdict |
|---|---|---|---|
| all | first body "Body" | "Body1" | on purpose (CHANGELOG, Fusion) |
| all | new bodies light grey | Steel satin | on purpose (default look) |
| all (Home > New design) | no layout grid | grid, red X / green Y line, origin dot | on purpose |
| first_part, combine | Extrude preview of a New Body opaque | profile seen through the preview (faint blue) | on purpose ("a profile behind a face is clicked through") |
| first_part (Cut) | Bodies to Cut: "Body" | "Body1" written above a check box "Body1": the name twice | cosmetic, from book-extrude-2 (a5033375); not changed (below) |
| first_part, undo | a circle clicked at (30, 15) on the top face: centre (30, 14.92) | (30, 14): on a grid crossing | on purpose (full grid snap) |
| offset_plane | a 5 mm circle on a sketch on an offset plane: drawn | **nothing drawn, nothing said** | **regression** (book-sketch-c ee6562f3): fixed |
| offset_plane | a circle in a second sketch on the same plane: nothing drawn | drawn | improvement (an old bug gone) |
| undo_redo | Ctrl+Z through a finished sketch: 9 steps for the rectangle, 5 for the circle | 6 and 4 | improvement (fewer undo steps; extrude and fillet one each in both) |
| look | the block's top before a look: brightness 165 | 140 | on purpose (Steel satin) |
| save_reopen | Data Panel: Upload, New Folder | also New Project | on purpose |
| look (Home) | tabs: Home, design | also "+" | on purpose |
| hole | browser lists "Hole 1 Sketch" | not listed | on purpose |
| all | browser header: three small buttons | the close button only, drawn readable | on purpose (book-shell e35d1ef2) |
| pattern_mirror | Mirror: a click on the Pattern Type drop-down (QTest) does not open its list | the same | no difference (noted below) |
| hide_show, fillet, hole, combine, presspull, revolve | | identical model, view and screenshots | |

The hidden-body case (fix-9's) was left to fix-9; with its merge, regress_hide_show passes on
both versions (it hides and shows without sketching on a hidden body).

## The regression: a circle drawn on a sketch on an offset plane made nothing

regress_offset_plane, step c: C, a click at (20, 15), a click 5 mm to the right: no circle,
no message, then "Extrude took a profile" failed. With the harness's settings (full snap off)
the circle was drawn, and on 3.3.10 too.

Probe (a copy of the scenario logging `sketch_infer.Inference._forward`): the sketch opened on
the plane at 0.135 mm per pixel, so FreeCAD's adaptive grid (steps 2, 10, 50 mm with the five
subdivisions of Grid Settings, the next step when the lines would be closer than 15 px) was at
its 10 mm step, 74 px between crossings. Full grid snap sends every free point to its nearest
crossing: the centre (20, 15) went to (20, 10), and the rim (25, 15), equally far from four
crossings, to (20, 10) too: the centre. FreeCAD makes no circle of radius 0 and says nothing.
The same goes for a line's end on its start and a rectangle's corner on (or level with) its
first corner. Introduced with full grid snap (book-sketch-c, ee6562f3, `GridSnapFull`, on by
default); the suite never saw it because the harness switches full snap off.

Fix (sketch_infer.py, `_apart_from_start`; the maths in sketch_infer_core.py, `flat_with`,
`crossing_apart`, unit tested): a free point the grid would put on the shape's first point (for
a rectangle also level with it) goes to the nearest grid crossing that gives the shape a size.
A snap, a guide, a point on a curve and the pointer right on that point are left alone. Fusion's
snap is kept: the point still lands on a crossing.

The sweep below showed that this first version had a side effect, fixed in the next commit:
the press and the release of a click were worked out separately, and at the release the press
had become the shape's first point, so the release of a circle's centre click went to another
crossing than its press. Now a click's release goes where its press went
(`_release_of_click`): one click is one point, whatever changed between press and release.

Guard: regress_offset_plane step g ("two clicks 5 mm apart made a circle"); it fails without
the fix (checked by switching `_apart_from_start` off: "a circle is drawn []").

## Not changed

- **Bodies to Cut shows each name twice** (a line of names, then the same names as check
  boxes): book-extrude-2 added Fusion's check list under the names line it already had. Fusion
  shows the list only. Six scenarios read the names line's text (book_extrude2_across,
  extrude_multibody, extrude_multibody_edit, gaps_join_new_body, fix9_hidden_body_*,
  replay_03_surfboard), so hiding it is a change of its own: left as a known cosmetic issue.
- **Mirror's Pattern Type drop-down** did not open for a `QTest` click right after Mirror was
  started from the ribbon (focus stayed on the 3D view), in both versions alike; choosing the
  feature in the timeline switches the type by itself, which the scenario does now. Not a
  regression; worth a look on a real screen.
- **Full grid snap at the coarse step**: right at the 15 px threshold the snap points are 74 px
  apart (2 mm and 10 mm are a factor 5 apart), so a click meant for a 5 mm circle gets 10 mm.
  That is the snap working as designed (Fusion's grid also snaps to its lines); the first
  dimension typed then scales the sketch. With a new user's settings these scenarios fail for
  that reason only (exact free clicks): fixsketch_join, sketch_draw, sketch_end_line,
  sketch_face, sketch_tools_draw.

## The sweep with a new user's settings

`FISSION180_USER_DEFAULTS=1` over sixteen everyday scenarios on the merged code: extrude_feel,
fillet, hole, luca_session, patterns_circ, replay_00_basics, replay_01_donut, revolve_basic,
shell_draft, sketch_polygon, sketch_qa pass; fixsketch_join, sketch_draw, sketch_end_line,
sketch_face and sketch_tools_draw fail on free clicks that now land on grid crossings (the
checks expect the clicked coordinates), every failure read: none was anything else.

## Runs

- Every regress_* scenario on 3.3.10 (copies, thrown away with the worktree) and on the
  merged code: the results and the screenshots compared (`r-old` / `r-new`, side by side).
- Unit suite: 3,762 tests OK (10 skipped).

## Changelog lines

- Sketch: with Snap on, a circle's rim, a line's end or a rectangle's corner clicked near the
  first point no longer lands on it: it goes to the nearest grid crossing that gives the shape
  a size. A 5 mm circle drawn on a coarse grid (for example in a sketch on an offset plane)
  made nothing at all, without a word.
