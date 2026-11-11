# Wave 7 fix-6: seven scenarios that failed on the merged develop (2026-11-11)

Branch `sf/fix-6`, from develop at 45563499. GitHub's full run of 45563499 failed 14
scenarios; fix-5 took the sketch dimension ones, these are the other seven. Each was an
integration clash or a check a deliberate change made stale. All seven fail the same way on
GitHub's run of dfa89fd2 (before fix-3, replay-c and fix-4). `replay_manufacture` came with
replay-g and never had a finished GitHub run before it failed.

| Scenario | Here before | Cause | Fix |
|---|---|---|---|
| `selection_dialogs` | FAIL (as on GitHub) | Select Through is on by default since replay-b (Fusion's default). B: the window round the top face inside Extrude also took the side faces hidden behind it; the dialog took the first face it was given (Face1, hidden) as the profile and the top face as where the extrusion ends (13500). D: the crossing box inside the top face also took the hidden bottom face; Press Pull moved both (16800) | App: `selection_ui._shown_faces_first` (a box inside a command with Select Through on hands the faces the view shows first); `ExtrudePanel._picked` / `_window_off_plane` (from a window only faces in the profiles' plane are profiles, a window never sets the end). Check D: with Select Through on Press Pull moves both faces (Fusion's Offset Face takes every face given; Autodesk's Select Through: a box takes hidden objects): 16800, reason at the line; D2 the same box with it off: 14400 |
| `selection_sketch` | FAIL | D: the window round the box with Select Through on takes all 6 faces and 12 edges (replay-b's deliberate change, Fusion's default) | Check: 6 and 12, reason and source at the line; then the Select-Through-off variant (3 faces), as replay-b did in `selection_box` |
| `sweep_loft_qa_loft` | FAIL | The click order was kept; replay-b made Loft's list name sketches as the browser does ("Sketch 2", `loft_ui.shown_label`); the check looked for FreeCAD's label "Sketch001" | Check: compares the shown names (`timeline_ops.shown_label`), and P1 also the profiles' own order |
| `replay_13_tesla_turbine` | PASS (fonts) | GitHub's names button shortened before the "&" ("Housing… + 1 more"); the app is right | Check, as fix-2 did in `book_shell_dialogs`: no lone "&" on the button, a roomy button draws "Housing && Inlet Tube", a shortened one has the names as its tool tip |
| `book_modifyc_knurl_piston` | FAIL | The window's process and the worker were not apart: both build 67.893 mm3 (GUI 67.8931; headless: window 67.89273, worker's code 67.89325, by hand 67.89536). The expected 37.086 was measured while the Coil's tool solid was taken in its own coordinates (the Coil follows the handle's sketch on YZ): its five copies were turned off the handle and only the Mirror's cut; replay-c's `pattern.add_sub_shape` placed it | Check: 67.893, reason at the line. New `headless/knurl_check.py` (unit `test_knurl_freecad`): the Coil's tool lies where it cut; the pattern built in the window, through `pattern_worker.run` with the files `build_outside` writes, and by hand is one solid |
| `book_params_units` | FAIL | Both chamfer sets listed, under "Chamfer001": fix-1's `_carry_label` skipped every default label, so the Chamfer that "+" turned into Fission 180's own step lost "Chamfer" (Change Parameters groups by label; formulas reach a step by it) | App: `fillet_ui._carry_label` also carries a default label of the new step's kind ("Chamfer" onto Chamfer001; the timeline still says Chamfer 1); "f1" onto a Fillet still does not go (`undo_fast` E) |
| `replay_manufacture` | PASS (screen) | A sketch point on the board's face is as near the eye as the face: the picks' depths differ only by the far camera's float rounding (12.0 / 12.0078). On GitHub's screen (one pixel taller) the face came first at the point's own pixel, here one pixel below it (probe). Different view providers, so FreeCAD's point-before-face preference does not apply; Hole From Sketch refuses faces and the click selected nothing; `_fall_through` only handled a refused corner or edge of the same object | App: `selection_ui._fall_through` / `_sketch_on`: a refused face, edge or corner gives the click to a sketch point (else curve) the command takes at the same depth, never through to something behind. The replay clicks its second point a pixel below it (`h.click(..., nudge=)`): with the fall-through off it picked nothing here too, with it both points |

## Tests

Each scenario above after its fix: PASS (selection_dialogs 37, selection_sketch 19,
sweep_loft_qa_loft 255, replay_13_tesla_turbine 253, book_modifyc_knurl_piston 24,
book_params_units 157, replay_manufacture 97).

Neighbours, all PASS: selection_box, selection_filters, selection_other (after both
selection changes), extrude_presspull_objects, extrude_presspull_regions,
extrude_presspull_qa; fillet, fillet_qa, fillet_chamfer, fillet2_chamfer, fillet2_component,
fillet2_edit_later, fillet2_full_round, fillet2_sets, undo_fast, book_params_dialog,
book_params_fields; book_modifyc_hole_drag, book_modifyc_hole_sketch, fixsketch_hole, hole,
hole_edges, hole_qa, hole_qa_part, hole_sketch; sweep_loft_sweep, sweep_loft_qa_sweep.

Unit: 3747 run, all OK once the AI docs were written again (`make_ai_docs.py`: the parity
page changed); the new `test_knurl_freecad` passes (about 35 s for 3 around, 3 minutes for
the scenario's 6 with FISSION180_KNURL_QUANTITY=6).

Probe (not committed): getObjectsInfo round the two hole points (5 x 5 pixels) and clicks one
pixel beside them, with and without the fall-through.

## Changelog lines

- With Select Through on, a selection window drawn inside Extrude gives it the face you see
  as the profile (it could take a face hidden behind it and end the extrusion at the one you
  meant).
- Hole From Sketch: a click on a sketch point that lies on a face picks the point (it could
  pick nothing, depending on the screen).
- Fillet / Chamfer: a chamfer given a second set keeps its name in Change Parameters (it was
  listed as Chamfer001).
