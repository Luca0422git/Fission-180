# Wave 7, builder fix-2: twelve scenarios that failed on the merged develop (9547b0e7)

About twenty builders' branches were merged into `develop` one after another; GitHub's full
run on the merged code failed 18 scenarios. Builder fix-1 took the six fillet / chamfer ones;
these are the other twelve, plus the harness's three "undo step left open" notes. Branch
`sf/fix-2`, from 9547b0e7. Every scenario was run alone, real FreeCAD 1.1.4, one at a time.

## What each failure was

| Scenario | Reproduced here? | Root cause | Fix |
|---|---|---|---|
| `fixdecal_components` | Yes (K2 on: the component not picked) | Since components-2 the first component of each level is grounded (Fusion's "First component Ground to Parent") and Move refuses a grounded component; the harness no longer turns that off. "Body001" was right: the first browser step was the knock-on | Scenario: right-click Box > Unground From Parent before Move (`component_steps.unground`), 134 checks PASS |
| `book_looks_kept` | (same cause) | Same: C moves the Bracket, the first component | Scenario: Unground From Parent first, 93 PASS |
| `browser_empty_body` | Yes | components-2's `commands.drop_made_body` takes away the body Create Sketch made for itself when it is cancelled (with FreeCAD's open "Add a Body" step); A still expected that body to stay. The app's rule is right: only the body made for that very command goes (`_MADE_BODY`, `is_unused`) | A now checks that the cancelled command left no body, no open step, nothing to undo. New part H proves the other side: an empty body that was there before (a sketch made and undone) survives a cancelled Create Sketch, the undo list is untouched, the next sketch goes into it. 213 PASS |
| `book_components2_cross` | (expectation) | extrude-2 built Fusion's rule (Autodesk's J. Strater, forum "Tool behaviour - unexpected": mostly inside a shown body, of any component, is a Cut by itself) | Both sides tested, as `book_extrude_operation` R9: 25 down (two fifths inside B's block): New Body, B untouched; 5 down (wholly inside): Cut by itself, B's block under Bodies to Cut. 238 PASS |
| `book_components_active` | (expectation) | Same; bug 10 as the book met it (a small overlap) stays New Body | H: 25 down: New Body, the Nozzle untouched; 4 down: Cut by itself, the Nozzle listed; New Body chosen by hand for the Axle's own body. 95 PASS |
| `hardware_insert` | No (passes here) | The rim of the magnet's pocket (6.2) and the magnet's own edge (6.0) are 0.1 mm apart, a pixel or two; GitHub's software OpenGL draws the magnet's edge on top, the click went to the magnet, which the dialog never takes (`HardwarePanel.allow`): M3 left, no target | Scenario: zoom in about the pocket until a millimetre is 30 px, and aim until the edge the dialog lets light up is under the pointer (`harness.click_edge(..., accept=)`, new optional argument). 84 PASS |
| `primitives_qa_paths` | Yes, by probe (a size box was under the pointer) | **App bug.** While a Box is placed, its Width size box on the canvas came to rest under the pointer: the pointer's moves went to the box, the outline kept the size from before (GitHub: 12 for 15) and a person's click there would land in the box | `primitives_ui.PlacingBox` passes a move with no button down on to the 3D view; the boxes keep clear of a square around the pointer (`_pointer_rect`). New P1 steps: the pointer brought straight onto the Width box still sizes the outline (fails with the forwarding taken out: 12 for 15.2) and no box is under the pointer at the click. 85 PASS, 3 of 3 |
| `book_shell_dialogs` | No (passes here) | The names button shortens to its room, which depends on the fonts: GitHub cut the first name before its "&" | Check: every "&" the button shows is doubled for Qt, and a names button with its full room (NAMES_WIDTH) draws "Housing && Inlet Tube". 106 PASS |
| `flatpattern_l_bracket` | (expectation) | shell made the Flat Pattern row's text the design's units, each size with its unit ("Flat 98.26 mm x 20 mm, 1 bend(s)"); right (an inch design reads inches) | Check updated, reason at the line. 47 PASS |
| `sketch_sweep` | (expectation) | Change Parameters is in the sketch's MODIFY menu now (shell, as Fusion), its dialog modal on purpose (params) | `INTENDED = {"Change Parameters": "Parameters"}` as `ribbon_sweep`, plus a check that it opens. 521 PASS |
| `book_params_units` | Yes | modify-b gave the chamfer's hidden document the design's units, so nothing is carried over there any more. Making such a document on purpose (hidden, mm, property writes) showed a **guard bug**: the statement `scratch.UnitSystem = mm` made FreeCAD carry mm into the active inch design while it ran, and `design_units._asked_for` took any running `UnitSystem` store for the design's own choice: the design stayed in mm | `design_units_core.store_target(frame)` reads which document the running statement sets (a name or an attribute chain; Python 3.11 and 3.13); `_asked_for(frame, doc)` keeps a change only for that document. C makes the hidden mm document on purpose and checks the put-back. 157 PASS; unit `StoreTarget` |
| `sketch_qa_keys` | No as such; reproduced by emulating GitHub's state | With a typed length FreeCAD makes the line from its on-screen **angle field as it stands, read off the pointer's pixel**: exactly 90 degrees on the local screen (view 1538 x 769: FreeCAD's own Vertical), 89.856 on GitHub's (1538 x 770: an Angle, no Vertical: x 20.0302). Fission 180's upright could not step in: the typed end is off the pointer, so `_apply_shape` found no vertex for the pointer's point, and any pointer event after the typed value dropped `Inference.last` | `Inference.last_move` keeps the last move's inference for the commit; the record marks the point a typed value finished; `_typed_direction` decides from the line itself (`core.typed_axis`, within HVDegrees) and replaces an Angle that is only the pointer's pixel off the axis (`core.pointer_angle`; a typed angle is kept). Emulation (FreeCAD's Vertical swapped for Angle 89.8558 before Fission 180 applies): x 20.0302 before, PASS after. R2 now moves the hand a little before Enter. 122 PASS; unit `TypedLength` |
| `mesh_separate_combine` (FLAKY) | Not in 5 runs; reproduced in freecadcmd | **FreeCAD's mesh booleans depend on the facets' order**: the scenario's cube and bar with shuffled facets gave Intersect 120 (open) 2 times in 300, Cut 880 6 times, Join wrong twice; the order changes from run to run | `mesh._boolean`: a result that is not closed is computed again with the facets in other deterministic orders (Join / Intersect also swapped); still open: said in the dialog. `mesh_boolean_check` / `test_mesh_boolean_freecad`: 300 orders right and closed (one try only: reports the open ones) |
| `sheetmetal_qa` NOTE | Yes | Sheet Metal Rules opened its step before a change; the change was refused; Close used `commitTransaction`, which only closes a step with changes | `_commit` uses `transactions.close`. No NOTE, 170 PASS |
| `overlay_outline` NOTE | Yes | The scenario closed Extrude with `Gui.Control.closeDialog()`, skipping its Cancel | Scenario presses Cancel. No NOTE, 11 PASS |
| `sketch_areas_face` NOTE | Yes | The scenario removed an empty sketch with a bare `removeObject`: FreeCAD files that under a "Delete" step it leaves open (checked in freecadcmd) | Scenario does it inside a step of its own, closed. No NOTE, 44 PASS |

## Other scenarios run (one at a time, all PASS)

`primitives_qa_keys` 52, `book_extrude_primitives` 48, `primitives_qa` 109,
`value_box_units` 8, `book_params_dialog` 88, `sketch_infer_tools` 162,
`book_sketch_c_merge` 47, `sheetmetal_rules` 60, `meshinspect2_groups` 74, `sketch_infer`
224, `sketch_draw` 134, `mesh_separate_combine` 4 of 4 before the fix and once after.
Unit suite (`--only unit`): 3688 tests OK (10 skipped).

A size box on the canvas now moves out of the pointer's way while a shape is placed, so it
cannot be clicked into with the mouse at that moment (typing goes into the first box by
itself and Tab moves between them, as before). Fusion places the point with a click there
too (Guess: no source found on clicking into those boxes while rubber-banding).

## FreeCAD facts found

- `doc.removeObject()` outside any undo step opens a "Delete" step and leaves it pending.
- FreeCAD's window code writes a document's units into the active design while a statement
  that sets that document's `UnitSystem` is running (the frame shows that statement).
- With a typed length, FreeCAD's Line takes its angle field as it stands: 90 degrees gives
  its own Vertical, anything else an Angle constraint (`ConstraintLineByAngle`); the angle
  is read off the pointer's pixel, so the result depends on the screen's size.
- Mesh `unite` / `difference` / `intersect` give different (open, wrong) results for the
  same two boxes with their facets in another order.

## Shared files touched

`fission180/primitives_ui.py` (extrude's), `fission180/design_units.py` and
`design_units_core.py` (params'), `fission180/sketch_infer.py` and `sketch_infer_core.py`
(sketch-a's), `fission180/mesh.py`, `fission180/sheetmetal_rules_ui.py`,
`Fission180Tests/gui/harness.py` (`click_edge` takes `accept`).

## Changelog lines

- Moving the mouse onto one of the size boxes while placing a box or cylinder no longer
  freezes the shape: it keeps following the mouse, and the box moves out of the way of your
  click.
- A line drawn along the vertical or horizontal guide with a typed length is now always
  exactly vertical or horizontal, also when the mouse moved after you typed.
- An inch design no longer switches to millimetres when a hidden helper document in
  millimetres is changed while the design is open.
- Combine on mesh bodies no longer gives, now and then, a wrong body with holes for
  Intersect, Cut or Join; when it cannot make a closed body it says so.
- Closing Sheet Metal Rules after a change it refused no longer leaves the next change
  joined to it in the undo list.

## Known issues

- FreeCAD's mesh booleans can still fail on some shapes for every facet order: Combine then
  says so and makes nothing; Repair both bodies first, or use Merge.
- A typed angle that is within a pixel's worth of vertical or horizontal (about 0.1 degree
  at the usual zoom) while the pointer is on that guide becomes a Vertical / Horizontal
  constraint, not an angle dimension.
- The Hardware dialog does not take a click on another hardware part's edge (a magnet's rim
  inside its pocket): nothing lights up there; zoom in and click the pocket's rim.
