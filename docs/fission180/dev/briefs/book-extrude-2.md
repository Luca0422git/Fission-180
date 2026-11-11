# Wave 7 follow-up: builder "extrude-2"

Builder "extrude" finished and is merged into `develop` (049c500b) with every other first-round
area. You take over its area. Read `book-common.md` first (rules, tests, report format), then
`book-extrude.md`, then `docs/fission180/sessions/book-extrude.md` (all of it: the Operation
rule, the Front-plane mark, `sketch_area_id`, `extrude_finish`, known issues), the extrude parts
of `sessions/book-components.md` and `sessions/book-params.md`, and
`docs/fission180/parity/extrude-presspull.md`.

**Your files:** `extrude*.py`, `revolve*.py`, `sweep*.py`, `loft*.py`, `profile_pick.py`,
`sketch_area*.py`, `primitives*.py`, `coil*.py`, `rib*.py`, the surface create tools where they
share that code, body naming. Shared files: smallest change, listed in your report.

## Items, in this order

1. **The full suite on GitHub after the merge** (run of 049c500b; 20 scenarios failed, most are
   with other builders). Yours:
   - `surface2_loft`: `[l4_reopened] both lofts are surface bodies` empty; `loft 1 the same`
     0.0; `[l4_done] still smooth with the wall`: list index out of range.
   - `surface3_untrim_revolve`: `[reopened] Revolve 1 (942.48)` got 0.0.
     Both are new since the extrude merge: a surface loft / revolve is empty after save and
     reopen. Suspects: the sketch-area re-link after a restore (`sketch_area_id`), the
     Front-plane mark, `extrude_finish`. Find the cause; check solid Loft / Revolve / Sweep /
     Extrude after reopen too (areas picked, several profiles, a parameter changed after
     reopen), and an old design (`Fission180Tests/fixtures/`) opened in the new code.
   - `extrude_presspull_qa4`: `[p19_done] the unfinished extrude was cancelled (OK not
     possible)` and `nothing added` come back empty (the refused-OK behaviour of
     `extrude_finish.SaysWhy`). Decide by Fusion's behaviour, fix the app or the check.
   - `export_report` is shell's ("Body comes back as Body1"): not yours, but grep the scenario
     folder for other label lookups of `"Body"` that only pass by luck.
   Then find what GitHub cannot show: grep the scenarios for expected `"Join"` after an extrude
   from an offset plane or from a sketch above a part, and for signed distances or Y bounding
   boxes after a sketch on the XZ / Front plane, in tools that call `auto_operation` /
   `ensure_body` (Press Pull, Emboss, Hole, Rib, Web, Sweep, Sheet Metal Flange, Plastic
   tools), and probe the suspicious ones.
2. **One direction rule for the Front plane everywhere.** A new Front-plane sketch extrudes to
   +Y for a positive distance (Fusion), but Box / Cylinder / Torus / Coil placed on the Front
   plane, Offset Plane from the Front plane (`construct*.py` is components': a small commented
   change is allowed), Revolve / Sweep / Loft directions, Hole depth on a Front-plane sketch,
   Emboss, Rib / Web, the Move triad's signs and the AI's extrude tool (its docs say "XZ
   (normal -Y)") still count FreeCAD's way. Confirm Fusion's convention with sources for each,
   then make every command that takes a signed distance from an origin plane agree, for NEW
   objects only (old designs keep their geometry: the first builder's mark). The AI tools must
   build the same geometry as before for old calls unless the op is versioned: choose the
   cleanest route, update the AI docs, say what you chose. Scenario `book_extrude2_planes`: the
   same positive number on Top, Front and Right for Extrude, Box, Cylinder, Offset Plane, Hole.
3. **Automatic Cut across components.** With component A active and a profile pushed into a
   body of component B: does Fusion propose Cut and list B's body under Objects To Cut, or New
   Body? (Autodesk Extrude reference "Objects To Cut"; the support article "How to extrude from
   one component to cut another component"; forum.) Do what Fusion does, with the Objects To
   Cut list and its checkboxes. Join stays limited to the active component (checked
   2026-11-11 against Autodesk forum answers).
4. **Sweep, Loft, Revolve, Rib, Web, Emboss, Pipe, Coil, Thicken** decide their automatic
   operation the old way ("mostly inside" their own body). One rule for all (the five rows of
   `auto_operation`, where it makes sense; confirm Fusion's default per feature), and a
   hand-picked operation never changes by itself in any of them.
5. **The book's own cases never rebuilt:** the carabiner's 27 regions (report: grep -n -i
   "carabiner\|sliver\|region") to the chapter's steps, slivers filtered, every region
   pickable; the Hot End's false "cut does not go through any body" (grep -n -i "does not go
   through"); the Drone with the report's own sketch (a circular pattern of spokes, 36 areas,
   Arm_Length changed several times, undo, redo, save / reopen: `book_params_drone` is the
   start, sketch-b now ties pattern copies).
6. **Body names:** the root's first body and a component's first body are both "Body1" (Fusion
   numbers per component too). Every place that finds or shows a body by label (dialog lists,
   the AI tools' `body` argument, Combine's target list, scripts) must show or accept "Body1
   (Component)" unambiguously, as the materials list now does.
7. `live_shapes` failed 4 speed checks ("no exact rebuild between the moves") under load: make
   those checks count rebuilds, not wall-clock, and check that the see-through profile pick
   and `SaysWhy` added no exact rebuild between mouse moves.

Scenarios `book_extrude2_*`, session log `docs/fission180/sessions/book-extrude-2.md` (ending
with "## Changelog lines" and "## Known issues"). Commit after every finished item. If you run
short of room, finish and report rather than start the next item.
