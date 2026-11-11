# Wave 7 fix-1: the fillet / chamfer scenarios that failed on the merged develop (2026-11-11)

Branch `sf/fix-1`, from develop at 9547b0e7. GitHub's full run of 9547b0e7 failed six fillet /
chamfer scenarios that each builder had passed on their own branch: `fillet`, `fillet_qa`,
`fillet2_full_round`, `limits_presspull`, `undo_fast`, `book_modifyb_tensegrity`. This is
what each was, which merge broke it and what was changed.

(The session was cut off once, by the usage limit and a machine restart; nothing had been
committed then.)

## How the merge was found

A second worktree at a merge commit, the scenario run there (`git log --first-parent
--oneline 3dbde183..HEAD` for the merges in order).

| Scenario | Here at 9547b0e7 | At ee6562f3 (sketch-c, before modify-b) | At 43d1db44 (modify-b merged) | Merge |
|---|---|---|---|---|
| fillet | FAIL (8 checks, as on GitHub) | PASS 67 | FAIL | modify-b; one check modify-c |
| fillet_qa | FAIL (9) | (GitHub green at 049c500b) | - | modify-b (same cause as fillet) |
| fillet2_full_round | FAIL (1) | PASS 28 | FAIL | modify-b |
| limits_presspull | FAIL (7) | PASS 35 | FAIL | modify-b |
| undo_fast | FAIL (5) | PASS 113 | FAIL | modify-b |
| book_modifyb_tensegrity | PASS | - | - | none: GitHub's renderer (see 6) |

## Root causes

### 1. A plain fillet held at its limit became Fission 180's own step for good (fillet, fillet_qa)

`fillet`: 50 typed on the front top edge of the 40 x 30 x 10 box is held at the largest
radius that fits; then 2 is typed and OK. The timeline then held Fission 180's own fillet step
(`FilletSets`), not FreeCAD's `PartDesign::Fillet`: "one Fillet feature" found none, and
everything after it (Ctrl+Y, the edit, the second fillet) counted wrong.

Two builders' changes meet here:
- builder **modify** (first pass, 52ad540d) made the dialog turn FreeCAD's fillet into its own
  step when only another route than the kernel's one run builds it (`fillet_robust.used()`),
  and remembered that in `BlendPanel._robust`, set once and never cleared. It was made for a
  chamfer after a modeled thread, where every size needs the other route, so "never cleared"
  did no harm.
- builder **modify-b** (43d1db44) added routes that build exactly the size at the limit
  (`fillet_section`: the 10 mm round that uses up the 10 mm front face; two rounds that use up
  a face between them). The search for the largest radius that fits now ends on a size only
  that route builds, so the dialog switched to its own step at 10.00 mm, and the sticky flag
  kept it there when 2 mm (which the kernel builds in one run) was typed afterwards.

Fix (`fillet_ui.py`): the flag is decided again for every size (`_trial`), and an own step
the dialog made only for such a size (`_for_route`) becomes FreeCAD's step again once the
kernel builds the size (`_swap_back`, the same `fillet_sets.replace` the other way). An own
step opened for editing, or needed for its rows / types, stays one (`_route_only`). The search
for the largest size asks what the step it will be builds (`_limit_works`).

### 2. Press Pull held a fillet at a size its FreeCAD step cannot build (limits_presspull)

Press Pull on an edge makes a FreeCAD Fillet and holds a radius past what fits at the largest
that fits. Its search asks `blend.check_build`, which since modify-b also answers "works" for
a size only Fission 180's own step builds (10.00 mm here). Press Pull cannot turn its step
into that one, so FreeCAD's fillet failed at 10.00 ("BRep_API: command not done"), the note
was not shown, OK was refused and the next steps waited on a dialog still searching.

Fix: `blend.check_plain` (check_build, refused when only another route builds it), used by
Press Pull's `limit_works`: 50 is held at 9.99 mm, which its FreeCAD step builds, and said.

### 3. The full round's radius in the design's units (fillet2_full_round)

modify-b (092b5080, builder params' hand-over) writes the dialog's lengths in the design's
units: "Half the width between the side faces: 2 mm" (trailing zeros dropped, as the value
boxes write lengths). The check looked for "2.00 mm". On purpose, so the check now reads the
exact new text (reason at the line).

### 4. undo_fast path E: the held radius is now Fission 180's own step

Edit Fillet 1 (four upright corners of the 40 x 30 block), 50 typed: the largest radius that
fits is now 15 mm, where two rounds use up the 30 mm side exactly; only Fission 180's own step
builds it, so OK keeps that step (modify-b's session log: "the dialog switches to Fission
180's step"). The check read `Fillet 1`'s FreeCAD `Radius` and found no step: the swap also
copied the label "f1" onto the new step, and "f1" was the default label only of the old object
(its Name), so the timeline called the new step "f1" instead of "Fillet 1".

Fixes: `_swap` / `_swap_back` carry a label only when the person gave it (the rule
`fillet_sets.rescue` already had); the scenario reads the radius of either step
(`fillet_radius`), and since the AI's `edit_step` changes FreeCAD's Fillet only (an own
step's sizes go through `set_model_parameter`, by design), path F starts from Fillet 1 before
E: one more Ctrl+Z after E's Ctrl+Y, itself checked to rebuild nothing.

### 5. Ctrl+Y after Ctrl+Z inside the dialog (fillet, one check; builder modify-c)

modify-c (fa410604, report bug 18): Ctrl+Z inside an open dialog is its Cancel and the
unfinished step never reaches the Redo list, so Ctrl+Y brings no half-made step back
(`book_modifyc_undo_in_dialog` checks that for Fillet). `fillet`'s last check still wanted
Ctrl+Y to bring the cancelled fillet back as "Fillet 3". Updated to modify-c's rule, reason at
the line.

### 6. The Tensegrity's corner: the wrong edge clicked on GitHub (book_modifyb_tensegrity)

Passes here, before and after. On GitHub the click meant for the inner corner under the arm
(3.4, 0, 6) selected `e2.Edge97`, the arm's front leaning edge: the 20 mm chamfer was held at
6 mm (the arm's thickness) and removed 1407.6 mm3 (6 x 6 / 2 x the 78.2 mm edge) instead of
adding the 1058.8 mm3 gusset, and every later step met another part.

Measured with a probe scenario (not committed): Edge97 starts at the corner's front end and
runs within 0-4 px of the corner on the screen (1.4 px at the middle the scenario aimed at).
FreeCAD's `getObjectInfo`, which `h.click_edge` uses to move onto the nearest edge pixel,
never reports this inside (concave) corner, only the leaning edge, so the aim moved onto
Edge97's pixel (780, 521), here and on GitHub alike; a real click there selected the corner
here and the leaning edge on GitHub (the renderer decides). A click one pixel off the
corner's line selects a face. Not an app fault: the app chamfered what it was given.

Fix (scenario only): `click_lit` hovers over the pixels around a point 1.5 mm behind the
middle (4 px from the leaning edge, 6.7 px from the back one) until FreeCAD lights up the edge
through it (its preselection), as a person does, and clicks there; with the aim shifted by up
to 2 px either way (25 shifts) it selected the corner every time. `type_20` and `type_50` now
check that the one pick is the edge through the aimed point (they only counted picks).
Whether it ever passed on GitHub before the merge is not known (modify-b ran it locally; no
merge to blame).

## Tests

The six, after the fixes (each alone): fillet 67 PASS, fillet_qa 114 PASS, fillet2_full_round
28 PASS, limits_presspull 35 PASS, undo_fast 116 PASS, book_modifyb_tensegrity 25 PASS.

Every scenario named fillet*, fillet2*, limits_*, chamfer*, book_modify_*, book_modifyb_*,
shell_draft*, undo_* (51), one at a time on the finished branch: 50 PASS. `fillet_live`
FAILED (twice) on its speed check "no exact rebuild between the moves" (`h.speed_check`, real
time) with the machine at load 10-18 (about nine builders on 4 CPUs). The same scenario on
9547b0e7 without these changes, run alternately with this branch: FAIL then FLAKY on both
(base: FLAKY, FLAKY; this branch: FAILED, FLAKY). It passed on GitHub's run of 9547b0e7. So
not this branch: the check needs an idle machine.

Unit (`run_tests.sh --only unit`): 3681 tests OK (10 skipped), with the new
`test_fillet_robust.CheckPlainTests`. Golden models not run (no geometry code changed: the
dialog's choice of step, a refusal for Press Pull's search, a label).

Probes (not committed): the Tensegrity's corner from the scenario's view (what
`getObjectInfo` reports around it, what a real click selects at each pixel, `click_lit` with
its aim shifted by up to 2 px).

## Changelog lines

- A fillet that was held at the largest size that fits and then made smaller is an ordinary fillet step again (it stayed a special one, which the AI's edit and other tools treat differently).
- Press Pull on an edge holds a too-big radius at the largest one its fillet can really build, and says so (it could stop at a size the fillet then failed at, with "command not done").
- A fillet step that turns into Fission 180's own kind keeps its "Fillet 1" name in the timeline.

## Known issues

- The AI's design steps `blend_insert` / `blend_edit` (`ai/ops/blend_ops.py`) check a size with `blend.trial` and then make FreeCAD's step: a size only Fission 180's own step builds passes the check and then fails as "these steps broke". `ai/ops/core.py` uses `blend.make_best`, which does it right.
- A fillet held at the exact largest size (two rounds that meet) is Fission 180's own step: the AI's `edit_step` asks for `set_model_parameter` there (by design since modify-b).
- A fillet that became Fission 180's own step at its largest size and was then closed with OK stays that kind of step when it is edited to a smaller size later (only the step the open dialog made itself goes back to FreeCAD's): its sizes are changed in the dialog or with Change Parameters as usual.
- `fillet_live`'s speed check (no exact rebuild between the moves of a drag) fails on a heavily loaded machine, on develop as on this branch; it passes on GitHub.
