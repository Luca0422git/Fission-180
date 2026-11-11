# Wave 7, builder fix-7: the last three GitHub failures on the release candidate (421a9553)

GitHub's full run on develop 421a9553 (CI #78) failed three scenarios, twice each. Branch
`sf/fix-7`, from 421a9553. Real FreeCAD 1.1.4, every scenario run alone.

GitHub's 3D view is 1538 x 770, this sandbox's 1538 x 769. Two of the three failures showed
here only with the main window made one pixel taller in a throwaway copy of the scenario
(`docs/fission180/dev/gui-tests.md`, last fact); each then failed with GitHub's own message.

| Scenario | Reproduced here? | Root cause | Fix |
|---|---|---|---|
| `sketch_geometry_keep` [s_check] | Yes, as it is (both runs) | **App bug.** `scale.scale_sketch` gave each dimension its new value with `setDatum`, and FreeCAD solved the sketch after each one while the others still had their old value. On OK the Scale dialog puts its preview back (scale by 1/2) and scales again: the ellipse's major axis went 24 -> 12 while its minor axis was still 12, an ellipse with equal axes, and FreeCAD refused the next value ("Cannot set the datum because the sketch contains conflicting constraints"). The dialog stayed open with the sketch half scaled (the conflict, the areas, the dimensions in the report). It passed on GitHub in run #76 (develop 45563499); on 421a9553 it fails here too, both runs (FreeCAD's answer to such a mix is not fixed: the plain ellipse headless takes it) | `scale_sketch`: the dimensions are made inactive (an inactive constraint takes no part in a solve), the curves scaled, every value set, all made active again, one solve; reference dimensions are scaled too (one left at its old value pulled the free curves of a sketch not fully constrained half way back). Headless `sketch_scale_check` (25 checks: a triangle 10 / 6 / 6 doubled, which the old code refuses every time, and halved back; one side switched off; the ellipse both ways; the step made and edited again as OK does; 4 fail with the old code), unit `test_sketch_scale_freecad`. 162 PASS, 2 of 2 |
| `fix3_dimension_through_planes` [d_axis_first] | Yes, at 770 (the same message, the same pixel) | Scenario aim: FreeCAD's pick finds the XY plane seen edge-on from 1 pixel above the X axis to 1 below it on a 770 tall view, from 2 above here; the step searched only 2 pixels above the axis | `x_axis_pixel_under`: the rows within 2 pixels of the axis, farthest first, along 1.5 to 6 mm, the axis's own row last; none: the view moves a quarter pixel and the search runs again (4 times); still none: the click goes 3 mm out and the check says what is there. 770: 1 pixel off, 2 of 2; 769: 2 off, 2 of 2; the quarter-pixel path forced: PASS |
| `replay_07_geocache` [d_lines_done] | Yes, at 770 (the same message, the same list) | Scenario check. Nothing of the model was under the pointer at any of the seven clicks and nothing was projected (probe: `getObjectsInfo` empty, no external geometry, nothing selected): the "last click" in the message is an earlier step's `h.click` (the harness keeps the last one). At 770 the Line tool put the 4th line's far end on the Y axis instead of making the line Vertical; its near end is the end of the line before, which is on the axis: both ends on the axis, the line held upright, as in Fusion. The check counted only an end put on the axis itself | The check follows Coincident ties: an end tied to a point on an axis is on it. 770: 192 PASS (FAILED twice without the change) |

## Other runs (one at a time, all PASS)

`sketch_geometry_keep` 162 (2 of 2), `fix3_dimension_through_planes` 41 (2 of 2),
`replay_07_geocache` 192 (2 of 2), `book_sketch_c_reference` 37, `replay_14_strandbeest` 255,
`sketch_scale_dialog` 130, `selection_dialogs` 37, `replay_manufacture` 97, `modify2_scale` 58;
golden models 652 pass (2 known XFAIL); unit suite 3754 tests OK (10 skipped).

## Changelog lines

- Scaling a sketch with MODIFY > Scale no longer fails now and then with "conflicting
  constraints" (the dialog stayed open and the sketch was left half scaled), for example a
  sketch with an ellipse, or a triangle made twice as big.

## Shared files touched

`fission180/scale.py` (`scale_sketch`), `docs/fission180/dev/gui-tests.md` (a fact: emulating
GitHub's 770 tall view; its AI copy regenerated with `tools/fission180/make_ai_docs.py`).
