# Wave 7 follow-up, builder "extrude-2" (branch `sf/book-extrude-2`, 2026-11-11)

Brief: `docs/fission180/dev/briefs/book-extrude-2.md` (seven items, in order). Everything was
reproduced in real FreeCAD 1.1.4 before it was changed.

## Item 1: the full suite on GitHub after the merge (run of 049c500b)

| Scenario | Failing check | Reproduced? | Cause | Decision |
|---|---|---|---|---|
| `surface3_untrim_revolve` | `[reopened] Revolve 1 (942.48)` got 0.0 | Yes, twice | The check, not the app. After reopening it found its bodies by label. Revolve 1 goes into a new component, whose first body is "Body1"; since the extrude merge the design's first (empty) body is "Body1" too, and `getObjectsByLabel("Body1")[0]` is that empty body (area 0). In the saved file: `Body` = "Body1", `Body001` = "Body2", `Body002` (in Component) = "Body1", `Body003` = "Body3". The revolve itself is saved and read back whole | The scenario finds its bodies by object name (`by_name`). Fusion numbers bodies per component, so two "Body1" are right |
| `surface2_loft` | `[l4_reopened] both lofts are surface bodies`, `loft 1 the same` 0.0, `[l4_done] still smooth with the wall`: list index out of range | Yes (the same three) | The same: Loft 1 is made with Operation New Component | The same change |
| `extrude_presspull_qa4` | `[p19_done] the unfinished extrude was cancelled (OK not possible)`, `nothing added` | Yes, twice | Not `extrude_finish.SaysWhy`: the timeline. Since the modify builder's fix for the report's bug 20 ("Edit Feature on a Gear step opened nothing and the step vanished") a double-click on the timeline icon of the step the open dialog is still making no longer ends that dialog: `timeline_ui.edit` says "Extrude is still open for this step: finish it with OK (or Cancel) in its dialog first." and leaves it alone | Fusion shows no timeline icon before OK, so it has no such case (Guess: nothing to copy); keeping the person's unfinished work and saying why is the better of the two. The check follows the app: the dialog stays open with its To Object extent, the message is said, the step is still there; Esc then cancels it and nothing is added (73 checks) |

A surface or solid Loft / Revolve / Sweep / Extrude is not empty after save and reopen (checked
without a window, see "Proof"), and the three old designs of `Fission180Tests/fixtures/`
(`before_rename_box`, `before_rename_lip_and_groove`, `pattern_bodies_v1`) open, rebuild with
every step touched, and keep every volume.

