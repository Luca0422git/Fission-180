# Wave 7, builder fix-10: the two scenarios GitHub failed on the release candidate

GitHub's full run on develop 589890c5 failed `replay_11_hot_end` and `regress_hide_show`.
Branch `sf/fix-10`, from 589890c5. Real FreeCAD 1.1.4, every scenario in a fresh profile,
real input only; both reproduced first with GitHub's own message, here (1538 x 769) and at
GitHub's 1538 x 770 view (throwaway copies, window one pixel taller: gui-tests.md).

## 1. replay_11_hot_end [bore_hidden_said]: "There is no solid to cut yet"

The book revolves the Nozzle's bore as a Cut with the Nozzle's body hidden. Fusion leaves a
hidden body out of a cut (replay-d), so the dialog must say that hidden bodies are not cut and
name Body1. It said "There is no solid to cut yet: this revolve makes the first one. Use New
Body." at both view sizes (not a pixel matter).

Cause: since fix-9, a sketch drawn on an origin plane while the work body is hidden goes into
an empty body beside it. Revolve's Objects To Cut row found no shown body in the way, wrote the
hidden-body reason, and then (the profile's body not being the hidden one) let the revolve be
built as a Groove in the EMPTY body: FreeCAD's Groove there shows the revolved solid, and
Revolve's own check ("no solid to cut yet") is read before the row's reason. Extrude in the
same place (Luca's own steps, Cut picked by hand) built a Pocket in the empty body. And the
one-body tools (Box, Cylinder, Sphere, Torus, Coil, Gear, Pipe) with a Cut or Join picked by
hand still cut or joined a hidden work body, unseen (fix-9 only changed their automatic
operation).

Fix: one rule and one sentence for every tool fix-9 changed.

- `extrude_bodies_core.hidden_note(labels, operation)`: "Hidden bodies are not cut (Body1 is
  hidden): show it, then start again." (joined / intersected; "them" for several), unit
  tested. `extrude_bodies.nothing_touched(..., hidden=)` uses it, and with hidden bodies in
  the way says "The revolve goes through no shown body, so it cuts nothing." instead of
  "does not go through any body ... change the profile".
- `extrude_bodies.hidden_reached(doc, tool_fn, lead)`: the hidden bodies a step really passes
  through or touches (`candidate_bodies(..., hidden=True)`: the ones left out only because
  hidden), so the sentence names those, not every hidden body of the design.
- Revolve, Sweep, Loft (`bodies_row_ui.BodiesRow.for_build`) and Extrude
  (`extrude_ui._bodies_for_build`, `_hidden_reached`): a new Cut / Intersect that reaches only
  hidden bodies is refused before anything is built (no Groove in the empty body, no preview
  in a hidden one), the reason in the dialog; a Join that touches only hidden bodies makes a
  new body (as before) and its row says "Touches no shown body: a new body is made." with the
  sentence. An edit keeps its own bodies (unchanged).
- Box, Cylinder, Sphere, Torus, Coil, Gear (`primitives_ui.PlacedPanel._build_beside_hidden`)
  and Pipe (`pipe_ui.PipePanel._build_beside_hidden`), through
  `bodies_row_ui.hidden_work_body`: a new step's Cut / Intersect on a hidden work body is
  refused with the sentence; a Join makes a new body, the sentence in the dialog's blue note.

New checks: Luca's Extrude with Cut picked by hand (`fix9_hidden_body_sketch_extrude`: refused,
"Hidden bodies are not cut (Body1 is hidden)", Body1 untouched, New Body again); the Box with
Cut and Join picked by hand through the hidden bodies (`fix9_hidden_body_tools` D).

## 2. regress_hide_show [c_sketch_shown]: GitHub only

"sketch shown with its eye: Sketch is drawn  picked ('Extrude', 'Face2')". Reproduced at 770
(passes at 769). The app is right: at that step the body is shown (its eye was opened in
step b), and the sketch IS drawn at 770. Its bottom line is the block's own bottom front edge,
on the block's outline; in the screenshot the edge pixel is the sketch's blue (68, 104, 128),
the body's black edge colour (25, 25, 25) only once the sketch is hidden. The probe asked what
FreeCAD picks FIRST at the line's projected pixel: on a 770 view that pixel's centre falls just
inside the front face (Face2 first), on a 769 one just outside it (the sketch first). Not from
fix-9 (the scenario came with the regress merge, after fix-9; nothing in fix-9 draws a shown
body's sketch differently).

Fix (the probe, by state): `regress_steps._sketch_at` lists everything picked at the pixel
(FreeCAD's `getObjectsInfo`, which never picks a hidden object): drawn = the sketch is picked
there at all and the first thing picked lies on the point (nothing in front of the line);
not drawn = the sketch is not picked there. The reason is at the function; gui-tests.md has
the rule.

## Runs (see the final report for the numbers)

Every scenario run alone at the sandbox view; the two failing ones and
`fix9_hidden_body_sketch_extrude` also at 770 (throwaway copies, not committed). Unit suite and
golden models (extrude_bodies is shared with scripts).

## Shared files touched

`fission180/extrude_bodies.py` (`nothing_touched`, `hidden_note`, `hidden_reached`,
`candidate_bodies(hidden=)`), `extrude_bodies_core.py` (`hidden_note`), `bodies_row_ui.py`,
`extrude_ui.py`, `primitives_ui.py`, `pipe_ui.py`; tests `regress_steps.py`,
`fix9_hidden_body_sketch_extrude.py`, `fix9_hidden_body_tools.py`,
`unit/test_extrude_bodies_core.py`; `docs/fission180/dev/gui-tests.md`. No FreeCAD file, no
MEMORY / CHANGELOG / VERSION edit.

## Changelog lines

- A Cut (Revolve, Extrude, Sweep, Loft) that reaches only a hidden body now says so and names
  it ("Hidden bodies are not cut (Body1 is hidden): show it, then start again."); Revolve said
  "There is no solid to cut yet" when the sketch was drawn while the body was hidden.
- Box, Cylinder, Sphere, Torus, Coil, Gear and Pipe leave a hidden body alone also when Cut or
  Join is picked by hand: a Cut is refused with that reason, a Join makes a new body and says
  why (they cut or joined the hidden body, unseen).
