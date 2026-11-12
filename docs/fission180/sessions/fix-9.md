# Wave 7, builder fix-9: a hidden body, a sketch and an Extrude (Luca's very first steps)

Luca installed the release candidate and the first thing he did broke. Branch `sf/fix-9`,
from develop 81f756ec. Real FreeCAD 1.1.4, every scenario run alone, real input only.

His steps (Windows, a fresh design, default settings, mm): a 2-point rectangle on XY,
Finish Sketch; Extrude (a cube, Body1); Body1's eye (hidden); a larger square on XY around
the cube's footprint, Finish Sketch. **Bug A:** Sketch 2 did not show, its eye open. Body1
shown and hidden again: Sketch 2 then showed. Extrude of Sketch 2. **Bug B:** Operation
Cut, Body1 ticked under Bodies to Cut, the hidden Body1 drawn being cut (red), its eye open
in the browser during the preview; OK cut it. Fusion leaves a hidden body alone.

Both reproduced first, by the new scenario `fix9_hidden_body_sketch_extrude` (Luca's steps
with a person's defaults): "4 Sketch 2 is not in the hidden Body1: Sketch001 in Body1 (on
False)", "Sketch 2's area shows on the screen: no", "Extrude proposes New Body, not Cut:
Cut", "no Bodies to Cut row: Bodies to Cut, 1 body, Body1", "Body1 is unchanged: 500000"
(the 100 x 100 x 100 cube cut to half by the 50 mm slab), no Body2.

## When they came in (bisect, a probe of steps 1-6 in a separate worktree)

The orchestrator relayed that both bugs were new in wave 7 (3.3.10 fine). The probe says
otherwise; the same steps give the same result at the 3.3.10 tag and at develop:

| Commit | Sketch 2 (step 4) | Extrude (step 6) | Result |
|---|---|---|---|
| 3.3.7 (34389861) | in the hidden Body, not drawn (A) | New Body, no row | Body untouched, Body2 the slab |
| 94928b56 (patch 3.3.8, "Sketches show in hidden bodies") | A | **Cut, row "Body"** (B) | Body cut away (volume 0) |
| 3.3.10 (7813ef69, tag) | A | Cut, row "Body" (B) | Body cut away |
| develop 81f756ec | A | Cut, row "Body1" (B) | Body1 cut away |

(Home > New Design, then real clicks and keys; probe kept out of the branch.) None of the
wave 7 merges changed either result.

## Root causes and fixes

| Bug | Root cause | Fix (functions) |
|---|---|---|
| B | 94928b56 made a hidden body whose sketch shows stay ON with its solid (Tip) off, so the sketch is drawn. Only the browser learned that state (`body_visibility.body_shown`); `bodies.is_shown` still read the body's own eye. After Luca's show-and-hide of Body1 (step 5), Body1 was in that state: Extrude's `extrude_bodies.candidate_bodies` took it for a shown body, so `start_state` (automatic Cut), `in_the_way` (Bodies to Cut) and the preview (built in Body1, the new Tip shown: the eye opened, red) all used it | `bodies.is_shown`: a body counts by its solid (`body_shown`), the reader every tool shares; new `bodies.solid_hidden` (a body's solid not seen: its eye or its component's). `candidate_bodies` leaves those out. Extrude (`_src_hidden`): a hidden profile body is no reason for Join (`_base_joinable`), is not named in the row, and a Cut through nothing builds no preview inside it (`_bodies_for_build` returns [], the reason "Hidden bodies are not cut (Body1 is hidden)" shows). What 94928b56 was for (a sketch shows in a hidden body) is kept |
| A | Older than wave 7 and than 3.3.8: Create Sketch puts a sketch on an origin plane into the active body, also a hidden one, and FreeCAD draws a body's sketches through the body. Finish Sketch set the sketch's own eye only | Where Sketch 2 lives: `sketch_ui._for_a_sketch_body` / `_sketch_body` (`create_sketch`): on an origin plane, with the work body's solid hidden, the sketch goes into an empty body of the same component (`components.body_beside`: a body nothing was put in first, else a new one, standing where the hidden body stands, made active), inside the Create Sketch undo step. Why: Fusion keeps a sketch in the component, never in a body, so hiding or deleting Body1 never touches it and its Extrude starts as New Body; the empty body is the kind Create Sketch already makes for a new design's first sketch (no browser row until a solid is made in it), and the Extrude's New Body fills it (Body2), with no reference across bodies. The precedent: a used-up (hidden) body never stays the work body (`bodies.leave_used_up`). And whatever body a sketch is in: `sketch_mode._show_finished` -> `_drawn_in_hidden_body`: a finished sketch that is on is drawn (`body_visibility.show_sketch` turns a hidden body on with its solid off), and stays drawn when the body is hidden again (3.3.8). `extrude.hide_sketches` hides the extrude's sketch through `body_visibility.show_sketch`, so a body kept on only for it goes back to plainly hidden |

## The same mistake in sibling code (fixed)

- Revolve, Sweep, Loft (`bodies_row_ui.hidden_source`, their `_auto_operation`): a hidden
  profile body no longer turns the operation into Join / Cut; their Objects To Cut row
  does not name it and a Cut through nothing builds nothing in it (`BodiesRow.for_build`).
  Their bodies in the way come from `candidate_bodies` (fixed above).
- Box, Cylinder, Sphere, Torus, Coil, Gear (`primitives_ui._base_shape`) and Pipe
  (`pipe_ui._base_shape`): the automatic operation does not count a hidden work body (a
  Box through the hidden active body proposed Join and joined it, invisible).
- Hole, Press Pull, Emboss, Fillet, Plastic Lip / Snap / Rest: they act on a face, edge or
  sketch area the person clicks, which a hidden body cannot offer. Plastic Boss finds its
  bodies with `bodies.is_shown` (`plastic_boss.candidate_bodies`): fixed with it. The
  Extrude's profile picker's occluder (`profile_pick.shown_part`) also asked `is_shown`: a
  body kept on for its sketch hid the profiles behind it.
- Combine: its bodies are picked by the person; a body hidden after it was picked stays in
  (Fusion), unchanged.

## Other visibility breakage found and fixed (scenario `fix9_hidden_body_tools`)

- Editing a sketch of a hidden body (its sketch shown on its own) showed the body's solid
  for as long as the sketch was open: FreeCAD's edit shows what the sketch projects from
  ("Show links": Auto project had put the face's edges in). `sketch_ui.open_sketch` notes
  the body was hidden before FreeCAD's edit starts (`_HIDDEN_AT_OPEN`), `show_design_at`
  hides its solid again in the same TempoVis (Finish Sketch puts it back).
- CONSTRUCT on the origin (Offset Plane from XY) with the active body hidden: the plane went
  into that body and never showed. `construct._off_hidden_body` (`make`): into an empty body
  beside it, on its own origin, as Create Sketch.
- Isolate of a body hidden while its sketch shows: Isolate only turned on what was off, the
  body stayed invisible (`components_ui.show_isolated`, also for several rows).

Checked and fine: undo / redo of the extrude with Body1 hidden (Body1 stays hidden, Sketch 2
shows again after the undo); an eye click is no undo step (as in Fusion: Undo undoes the
last modelling step); save, close and reopen with hidden bodies and a sketch shown in a
hidden body; Show All Bodies / the browser's eyes already went through `body_visibility`.

Known limit, left as it is: a Rib / Web needs its sketch inside the part's body
(`rib.build`); a sketch drawn on an origin plane while that part was hidden is now in a
body of its own, so after showing the part, Rib says "make the part first". Drawing the
sketch with the part shown (or on its face) works as before.

## Runs (one scenario per fresh profile, all PASS)

New: `fix9_hidden_body_sketch_extrude` 73, `fix9_hidden_body_tools` 75; both at GitHub's
770-pixel view too (throwaway copies, window one pixel taller, gui-tests.md): 74 and 70.
Regression: `book_extrude_operation` 74, `book_extrude_across` 43, `book_extrude2_across` 37,
`book_extrude_picking` 49, `book_components_active` 95, `book_components2_cross` 238,
`browser_ghost` 33, `browser_empty_body` 213, `browser_sketch_in_hidden_body` 27,
`browser_multi_select` 86, `extrude_hidden_sketch` 9, `bodies_combine` 93, `bodies_qa` 317,
`bodies_qa_2` 240, `bodies_timeline` 65, `book_extrude_primitives` 48, `components_basic`
252, `extrude_multibody_edit` 138 (more in the final report); unit suite 3754 tests OK
(10 skipped).

## Shared files touched

`fission180/bodies.py` (`is_shown`, `solid_hidden`), `components.py` (`body_beside`),
`components_ui.py`, `browser_ui.py` (Isolate), `construct.py`, `sketch_ui.py`,
`sketch_mode.py`, `extrude.py`, `extrude_bodies.py`, `extrude_ui.py`, `bodies_row_ui.py`,
`revolve_ui.py`, `sweep_ui.py`, `loft_ui.py`, `primitives_ui.py`, `pipe_ui.py`; tests
`Fission180Tests/gui/fix9_steps.py` and two scenarios. No FreeCAD file, no MEMORY /
CHANGELOG / VERSION edit.

## Changelog lines

- A sketch drawn after hiding a body now shows as soon as you finish it (it went into the
  hidden body and stayed invisible, its eye open). It no longer belongs to the hidden body:
  hiding or deleting that body leaves the sketch alone, as in Fusion.
- Extrude (and Revolve, Sweep, Loft, Box and the other shapes, Pipe) leaves hidden bodies
  alone: it no longer proposes Cut or Join because of a hidden body, lists it under Bodies
  to Cut, draws it being cut or changes it. Choosing Cut by hand with only hidden bodies in
  the way says that hidden bodies are not cut.
- Editing a sketch of a hidden body keeps the body hidden; an Offset Plane made from the
  origin while the body was hidden now shows; Isolate shows a body that was hidden while
  one of its sketches stayed on.
