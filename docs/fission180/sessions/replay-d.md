# Session log: replay-d (wave 7, the acceptance test: chapter 4 of the book)

Builder "replay-d", branch `sf/replay-d` (from develop 39fd9e9b). Brief:
`docs/fission180/dev/briefs/book-replay.md`. Part of the book: Chapter 4, Project 10 "Fire
Piston" and Project 11 "3D Printer Hot End" (report lines 1637-1949). The run was cut off once
(credits, then a machine restart); it resumed from the branch as committed.

## What was built

- `scenarios/replay_10_fire_piston.py` (steps: `gui/replay_10_steps.py`): the Fire Piston from
  Change Active Units to the Section Analysis in ONE inch design, by real input, with a
  user's defaults (first component grounded, full grid snap, scale at first dimension,
  layout grid on) and an open undo step a failure. 15 stages: units, the Piston Body's
  sketch, its revolve and modeled 3/8-16 thread, the chamfer sets, the offset plane and the
  knurl (Coil, Mirror, Circular Pattern x6), the anodized-blue look and the group, the End
  Cap (polyline, R0.04 sketch fillet, revolve, chamfers, cosmetic thread, Brass, group, drag
  + Ctrl+Z), its O-ring from INSERT > Hardware (AS568-012, Move Y 90 / X -2, Joint with
  Offset Z -0.465), the End Cap joined to the body, Isolate / Exit Isolate, Piston End and
  Piston (new components, first-dimension scaling with typed sums), the countersunk tip hole
  dragged to the centre, the 5/16-18 UNC tapped hole, the tip chamfer, the piston's O-ring
  (AS568-009, Offset Z -5/32), As-built Rigid, As-built Slider (OK without a position is
  refused), limits with Flip / Rest / Preview Motion, drags (spring back to rest, no push
  into the body), Opacity Control 60 %, Section Analysis.
- `scenarios/replay_11_hot_end.py` (steps: `gui/replay_11_steps.py`): part of the Hot End in
  one millimetre design: the Nozzle (circumscribed polygon, 5.95 across flats, Horizontal,
  E taking the only profile, the bore revolved as a Cut with the body hidden as the book
  says, then shown), the Heater Block (Offset Plane picked in the browser with the Nozzle
  hidden, 20 x 12 x 10), the flat cut To Object on the underside (the report's "cut does
  not go through any body"), the PTFE Tube sketched on the Nozzle's face with PTFE Tube
  active.
- `scenarios/replay_d_section_root.py`: Section Analysis with the design's row active and
  every body in a component (the section vanished at OK).
- `gui/replay_d_steps.py`: shared helpers (user defaults, real polyline / dimension input, a
  face spot the view really shows, ViewCube orbit, rim clicks that tell nearby edges apart,
  checkpoints). Development aid in `replay_d_steps.stages`: `REPLAY_D_SAVE=<folder>` saves
  the design after each stage, `REPLAY_D_FROM=<stage>` starts from the copy saved before a
  stage. The test runner never sets them; a full run is always from the first step.
- The book's figures are not in the repository: every part is a stand-in drawn to the
  numbers the report quotes (the report's line is named at each step).

## Hitches found and fixed

| Report line | What happened in the replay | Fusion (source) | Root cause | Fix (function) |
|---|---|---|---|---|
| 1675 chamfer sets after the modeled thread | set 2 (outer rim + the left end FACE, whose inner rim is the threaded hole's mouth): after each pick 8 - 25 s busy; 0.02 typed right after the click took 9 s to arrive | the picks and the typed size are taken at once (Guess) | `value_limits.Background` ran a trial build between every two keys; `fillet_robust._clean`'s verdict lived in the per-part table, pushed out by part-way solids, so OpenCASCADE's `check` (2 - 5 s on a modeled thread) ran at every second trial | `value_limits.Background._watch_input / _unwatch_input / _typing / _waits` (no build for 0.4 s after a key, a press or a drag move); `fillet_robust._clean` (own cache `_STATE["clean"]`) |
| 1716 Joint on an O-ring | the lit snap on the O-ring was the centre of the ring's cross-section (inside the rubber, 5.5 mm off the axis) | the ring's centre (Guess from the book's step) | `joints._face_keypoints` / `_edge_keypoints` offered the seam circle's centre; `_face_frame` asked for "Part::GeomTorus" (FreeCAD: "Part::GeomToroid") | `joints._face_keypoints`, `_edge_keypoints`, new `_ring_of`, `_off_axis`, `RING`, `_face_frame` |
| 1671 / 1693 dimensions typed as sums | "0.70/2" as a sketch's FIRST dimension did not scale the sketch (only a plain number did); the next dimensions flipped the profile | Fusion scales at the first dimension whatever is typed (Autodesk API isSketchScaledWithFirstDimension; Guess for formulas) | `sketch_mode.DimensionEditor.apply`: the formula branch never called `_scale_at_first` | `sketch_mode.DimensionEditor.apply` |
| 1747 Section Analysis (skipped in the report) | with the design's row active (all bodies in components) the section was gone after OK | the section stays (Autodesk) | `section_ui.start` asks `ensure_body` for a body (origin squares); its open "Add a Body" step swallowed the dialog's; at OK the close saw no new step and undid it as a cancelled command | new `commands.drop_unused_made_body`, called in `section_ui.SectionPanel.accept` |
| 1808 Offset Plane, new component active | FreeCAD's modal "Bad base feature: A body cannot be based on a Part Design feature" | no such box (Fusion has no bodies-in-bodies) | `commands.ensure_body` runs `PartDesign_Body`, which takes a selected PartDesign feature as base | `commands.ensure_body` + `_hold_selection`, `_give_back_selection` |
| 1774 Revolve (Cut) with the body hidden | "The revolve does not go through any body" though the bore is drawn in it | Fusion leaves hidden bodies out of the bodies to cut (Autodesk Extrude reference: "Auto-Select re-computes the bodies to cut based on the current visibility state"): the report's claim that it should work is not Fusion's behaviour | the refusal did not say a hidden body was the reason | `extrude_bodies.nothing_touched` (+ `hidden_solids`); callers in `extrude.build`, `extrude_ui.ExtrudePanel`, `revolve.build`, `bodies_row_ui.BodiesRow.for_build` pass the design |

## Report items checked and found working (the replay does them the book's way)

Units held in inches through 15 stages, every Ctrl+Z / Ctrl+Y, chamfer OKs and drags (1648);
the grid steps in inches (1655); New Component grounds the first component and leaves the next
free (1689); From Bodies not ticked by steps selected in the timeline (1725); Thread starts
ANSI in an inch design and offers 3/8-16 UNC for d25/64 (1673); the sketch Fillet takes its
typed 0.04 (1692); Coil switches to Cut by itself (1678); the knurl's preview answers in
under a second (1682; OK builds it in 200 - 260 s on this loaded machine, outside the
window's process, with a progress note); "Anodized" search (1684); Create Group (1687); the
O-rings from Hardware by dash number (1702); drag + Ctrl+Z of the End Cap 1 - 2 s (1701,
was 80 s); the hole's blue dot snaps to the centre (1731); the dialog remembers the last
hole (1733); As-built Slider with no position is refused with a message (1735); limits with
Flip, Preview Motion and Rest that springs back (1739-1742); the blue look survives joints,
hide/show, Isolate and Opacity (1744); E takes the only profile (1765); a sketch on another
component's face keeps the active component (1919).

The Hot End's "cut does not go through any body" (1884-1898): with the whole centre
rectangle picked (E takes both halves the block's edge cuts it into), To Object on the
underside chooses Cut by itself and cuts the flat. With only the outer half picked, the
extrusion lies beside the block: Join is right, and Cut is refused with that message, which
is then true. The report's tester most likely had only that half picked (the profile
question, not the message).

## Results

- `replay_10_fire_piston`: PASS, 527 checks, from the first step (19 min on the shared,
  loaded machine; the knurl's OK alone 260 s).
- `replay_11_hot_end`: PASS, 98 checks (run_tests.sh).
- `replay_d_section_root`: PASS, 10 checks.
- Older scenarios of the files changed, one batch at a time: book_joints_snap (41),
  book_sketch_c_scale (26), book_components2_cancel (29), book_modifyc_section (28),
  book_extrude_operation (74), book_modify_thread_chamfer (52), book_modify_fillet_limit_note
  (18), book_modifyb_draft (31), inspect_construct (69), book_extrude_across (43): PASS.
  book_components_active FAILS at H ("still New Body, not Cut"): its check predates the
  extrude-2 merge (a5033375), which made a push into another component's body a Cut on
  purpose (Fusion, forum "Tool behaviour - unexpected"); not caused by this branch, the check
  needs the components owner's update.
- Unit tests: all pass but the known `test_vex_qa_freecad` (another builder's).
  New: `test_value_limits` (typing pause), `test_fillet_robust` (clean verdict kept),
  `test_ring_snap_freecad` (13 checks in real FreeCAD).
- Golden models: 649 pass, 2 xfail (as before).

## Hitches found and NOT fixed

- **A construction plane is drawn as large as its whole part.** The Offset Plane inside the
  Piston Body is 38 mm square (FreeCAD's automatic size: the body's box); Fusion's is the
  size of its face. From the home view it lies in front of the End Cap's shank and J takes
  the plane: the replay hides the Construction folder first, as the report's tester hid parts
  (1720). Would take: size the plane to its face in `construct.update` (ResizeMode Manual)
  and re-run the 32 scenarios that use offset planes.
- **A coil's section shows again after the design is saved and opened.** The helper triangle
  a Coil sweeps (`CoilSection`, Part2DObjectPython) is hidden in the session and saved hidden
  (GuiDocument.xml Visibility false), but is visible right after `App.openDocument`, set by
  FreeCAD's C++ restore (no Python on the stack). Gear and pipe helpers are likely the same.
  Would take: hide `primitives.is_helper` objects once a document has finished opening (a
  Gui-side hook after the view providers are restored).
- **Showing a hidden body while Revolve / Extrude is open does not re-check the bodies to
  cut**: the dialog keeps "does not go through any body" until an input changes. The message
  now says "show it, then start again".
- **Section Analysis's undo step is named "Add a Body"** when it made the empty body (the
  two steps merged); Ctrl+Z works (the section goes, no body is left).
- **Typing a chamfer size right after a pick on a threaded part can still wait** behind
  one trial build of the size search (2 - 5 s each on this machine; 26 s in the full run
  under load, when the hand's way from the view to the box let builds start). Would take:
  the search in a worker process, as the knurl's build is.
- A slider dragged by hand stops a hair short of the pointer (0.997 in for 1 in): the
  Minimum box shows 1.00 in (two decimals) when ticked.

## Not replayed (out of time)

Project 11: the Nozzle's chamfer sets, Brass material, M6 thread and engraved "0.4" text;
the Heater Block's bolt-hole chamfers, the right-face cuts (Extrude -4 / -5 / All + Flip),
the M3 threads, the thread dragged before the chamfer; the Thermistor / Heater element STEP
inserts and their joints; the Heat Break (Project from the Nozzle: covered by
book_components_project); the Heat Sink's snake fins (sketch pattern), 3-point arc, threads
and side holes; the Bowden connector STEP, the PTFE Tube's tangent arc and sweep, the
material colour, the McMaster set screws and pan heads (INSERT > Hardware: covered by
book_hardware_inch / book_hardware_countersunk). Out of scope: McMaster-Carr's catalogue,
CADclass STEP downloads (stand-ins), the Render workspace.

## Things learned (FreeCAD / harness facts)

- `Shape.BoundBox` of a part with a modeled thread is larger than the part (it counts the
  swept faces' hidden ends): `optimalBoundingBox(False, False)` in checks.
- A click on a dialog's floating value box is taken by the box (as in Fusion): click the rim
  clear of it (`replay_d_steps.click_rim`, `click_circle`).
- A line's middle on an axis: a click there takes the axis (`Sketch Dimension: click the
  point or line to measure from the axis`); click a quarter along.
- `doc.openTransaction(name)` while FreeCAD's Body command has its step open joins that
  step (`App.getActiveTransaction()` stays "Add a Body"); a dialog then sees no new undo
  step at OK.
- Under load the dimension box can show before it has the keyboard: wait for its focus
  before typing (`replay_d_steps.dimension`).

## Changelog lines

- Typing a size right after clicking an edge or face in Fillet or Chamfer no longer waits
  behind the search for the largest size that fits.
- A chamfer or fillet on a part with a modeled thread previews faster: the part is checked
  once, not at every try.
- A Joint clicked on an O-ring takes the centre of the ring, on its axis; it could take a
  point inside the rubber and put the ring off-centre.
- A sketch's first dimension scales the whole sketch also when its value is typed as a sum
  or a parameter (0.70/2).
- Section Analysis keeps its section when the design's top row is active and every part is
  in a component (it disappeared at OK).
- Starting Offset Plane (and other commands that need a body) with a part step selected no
  longer stops at FreeCAD's "Bad base feature" box.
- A cut that only reaches a hidden body now says that hidden bodies are not cut and names
  them.

## Known issues

- A construction plane is drawn as large as its whole part, not as its face: hide it (the
  eye of the Construction folder) when it lies in front of something you want to click.
- After opening a saved design, a coil's small section triangle can show at the coil's
  start: right-click it in the browser > Hide.
- Showing a hidden body while a Cut dialog is open does not make the cut reach it: Cancel
  and start the command again.
- A fillet or chamfer on the end face of a threaded hole still takes a second or two per
  preview; the knurl pattern takes several minutes to build at OK on a busy computer.
