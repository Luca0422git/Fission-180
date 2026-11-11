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

## Item 2: one direction rule for the Front plane

Reproduced without a window, with the code the dialogs call (that path is still there, for
older objects, and `front_plane_check.py` keeps checking it): on the Front plane a Box of height 10 lay at y -10..0, a Cylinder and a Coil likewise, an Offset
Plane of 10 at y = -10, while a new sketch extruded 10 lay at y 0..10. Hole already drilled
into the part on every plane.

Fusion (sources in `parity/extrude-presspull.md`, "One rule on the Front plane for every
command"): the Front plane's normal is +Y (sketch x = X, sketch y = -Z: Forum and a
third-party Fusion scripting reference; "Positive offset goes in the plane's normal
direction. For XY: +Z. For XZ: +Y"). No page states the sign of a Box or Cylinder height on
the Front plane: Guess, the plane's normal like every other command. A Box is one "Box
Primitive" step in Fusion's timeline (Forum), not a sketch and an extrude.

Root cause: FreeCAD's XZ plane looks to -Y. The first builder turned Extrude round with a
mark on the sketch; the primitives build in the plane's attachment frame and the Offset
Plane writes its distance on the attachment offset, both FreeCAD's way.

Built:
- `extrude.is_front_plane(plane)`: the origin's XZ plane, or a datum plane made from it and
  parallel to it (`on_front_plane(sketch)` now uses it).
- `primitives.front_turned` / `FRONT_TURN`, `frame(ref, options)`,
  `global_frame(ref, options)`, `attachment_offset(..., options)`: a step whose options
  hold `"front": true` is built in Fusion's frame of the Front plane (x = X, y = -Z,
  z = +Y), so every arrow, value box, snap and preview that asks for the frame agrees.
  `PlacedPanel.COUNTS_FRONT` turns the note on for new Box, Cylinder, Sphere, Torus and Coil
  steps; Gear derives from the same dialog base and is modify's, so it is off there.
- `construct.offset_side`, `FRONT` on the datum (and on its hidden helper), `read` /
  `update` / `_c_OffsetPlane`, the dialog's arrow and its To Object distance.
- The AI tools keep "XZ (normal -Y)": `Builder._along_plane_normal` turns the extrude step's
  options round on a sketch marked Fusion's way; the tools' help says so.

FreeCAD facts and traps:
- A frame turned half a turn about its own x axis is Fusion's Front frame; a proper turn
  keeps a coil's hand. Turning only z would be a mirror.
- `PlacedPanel` is also Gear's base class: a new option set there reaches Gear's dialog but
  not `gear.py`, so it must be asked for per dialog class.
- Extrude takes the newest unused sketch's single area by itself: a scenario that makes two
  sketches and then presses E gets the second one picked, and a click on the first ADDS it.

## Item 3: the automatic Cut across components

Reproduced (`book_extrude_across` as merged, 43 checks): with Axle active, a circle on the
Nozzle's face pushed 4 into the Nozzle came up as New Body; Cut had to be picked by hand.

Fusion: a Cut by itself, with the other component's body under Objects To Cut. Sources:
Autodesk's J. Strater confirmed a user's reading on the forum ("Tool behaviour -
unexpected"): mostly inside another VISIBLE body: Cut; mostly outside but touching or
overlapping: Join; touching nothing: New Body. Forum, "Stop automatically changing the
operation from New Body to Cut": the automatic Cut happens "even when the cut goes through
all components in the assembly". Forum, "extrude-cut through all problem": Objects To Cut
offers the bodies of both components and both are selected; people asked for an "Active
Component" choice, which Fusion does not have. The report's own claim ("Fusion starts a new
component's first extrude as New Body", bug 10) is true for its case and for the reason
above, not because other components are ignored: the Strandbeest link only overlaps the
other component's pin a little (6 % of the link), so it is not a Cut, a Join has nothing to
join in the active component, and New Body is left.

Root cause: `extrude_bodies.auto_scope` (the first builder's and the components builder's
fix for bug 10) let only bodies of the active component decide.

Built: `extrude_bodies_core.mostly_inside` and `auto_operation(..., inside_others)`,
`extrude_bodies.inside_others` (one boolean for each body of another component the
extrusion passes through, only when the preview is rebuilt, never during a drag), the rule
in `ExtrudePanel._auto_operation`; the check box list (`_show_body_checks`,
`_body_check_toggled`); `bodies.clear_name` / `named` / `list_names`.

Found on the way, not mine: with a component active, the timeline shows that component's
steps only, and a cut made there in ANOTHER component's body (the step lives in the body it
cuts) is not among them: `['Pin', 'Sketch 2']` after the cut, `Extrude 2` shows once the
top row is active. Fusion lists a step with the component that was active when it was made
(Guess from Fusion's per-component timeline). `timeline_ops.py` / `timeline_ui.py` are
modify's.

## Item 6: body names

Reproduced: the design's first body and a component's first body are both "Body1"; the
Extrude dialog's Bodies to Cut row, Combine's Target box and the pick boxes of Move, Split
and the other body commands showed the plain "Body1" for either; the AI tools answered
"Several things are called 'Body1': use the id get_design lists" and did not take
"Body1 (Bracket)"; the step language (`Builder.learn`) gave the first object of that label.

Fusion numbers bodies per component and shows them under their component in the browser
(Autodesk: bodies live in a component's Bodies folder); a list outside the browser needs
the component's name next to the body's to say which one it is (the materials list of the
looks builder already writes "Body1 (Bracket)").

Built: `bodies.clear_name` ("Body1 (Bracket)"; plain at the top level), `bodies.shown_name`
(the plain label while it is the only one in the design, else with the component, and with
the object name where two components have the same name), `bodies.named(doc, text)` (finds
a body from the full name, the object name or a label only one body has; says what to write
when several share it). Used by the Extrude list and row, the shared bodies row of Revolve /
Sweep / Loft (`bodies_row_ui`), every body pick box (`bodies_gui.body_text`), Combine's
Target (`combine_ui`, one line), the AI tools (`ai/executor.resolve`) and the step language
(`Builder.learn`). A design without components shows what it always showed.

Not changed: the browser (a body is under its component there), the timeline, the looks
builder's `material.body_name` (always with the component), scripts that call
`doc.getObjectsByLabel` themselves (FreeCAD's own call: it returns every match).

## Item 7: `live_shapes` speed checks

The four checks that failed on GitHub ("no exact rebuild between the moves") compared move
numbers: any exact rebuild before the last moves of a drag was a failure. The dialog rebuilds
once the handle has rested for its own rest time (`taskui.Panel._rest_needed`, 0.2 s, or a
multiple of the last rebuild's cost while the button is held); on a machine so slow that two
moves of the scripted drag come further apart than that, the rebuild in between is right.

The check now counts by what the dialog decides with: at each exact rebuild during a drag it
records how long the dialog had seen no change and no mouse move (`last_moved`) and the rest
time it needed then; a rebuild that came after less than 0.9 of that rest time is a fault and
is counted on every machine (a plain check, also under `--stress`); a rebuild between moves
that were further apart than the rest time is printed, not counted. Run here with eight
other builders on the machine: PASS, 120 checks, and no rebuild between moves at all, so the
see-through profile pick and `SaysWhy` add none.

`draft_live` and `fillet_live` (modify's) have the same wall-clock check and were left as
they are: named in the report.

## Items 4 and 5: not built (room ran out), with what was checked

Item 4 (one rule for the automatic operation in Sweep, Loft, Revolve, Pipe, Coil and the
primitives). Checked by reading the code, nothing changed:
- A hand-picked operation never changes by itself in any of them: each has
  `user_picked_operation`, set from the list's `activated` signal (picking the value that
  already shows counts), and `_auto_operation` returns at once when it is set (Revolve,
  Sweep, Loft, Pipe, Box / Cylinder / Sphere / Torus / Coil through `PlacedPanel`). An edit
  from the timeline starts with it set.
- Rib, Web and Emboss have no Operation list (Fusion's Rib always adds; Emboss / Deboss is
  a choice of its own).
- The rule they use (`revolve.auto_operation`, `sweep.auto_operation`,
  `loft.auto_operation`, `primitives.auto_operation` / `primitives_core.operation_for`):
  more of the new solid inside the part than outside: Cut; touching or overlapping: Join;
  away from it or the first solid: New Body. That is the reading Autodesk's J. Strater
  confirmed on the forum ("mostly inside another visible body"), so it is Fusion's rule,
  not an old one. What is not Fusion's: they compare against the profile's OWN body only,
  where Fusion looks at every visible body for the Cut and at the bodies of the active
  component for the Join.
- The way to close it (for whoever takes it): `extrude_bodies.candidate_bodies(doc, lead)`
  gives every shown body as it was before the step; decide Cut against all of them
  (`extrude_bodies_core.mostly_inside`) and Join against the active component's
  (`auto_scope`), in Revolve, Sweep and Loft, whose build already acts on several bodies
  (`participants_of`, the shared bodies row). The primitives, Coil and Pipe build into the
  plane's own body only (`primitives.build_step`), so a Cut of another body needs that
  first.

Item 5 (the carabiner's 27 regions, the Hot End's false "cut does not go through any body",
the Drone with a circular pattern of spokes): not rebuilt. The first builder's proof stands
as it was: `book_extrude_areas` (slivers on a made-up crack, a 30-area parametric plate),
the headless `sketch_area_id_check.py` (37 areas, the pitch changed, undo), to which item 1
added save / reopen / change for Extrude, Revolve, Sweep and Loft.

## Proof

| Scenario (`paced_by="state"`) | Checks | Covers |
|---|---|---|
| `book_extrude2_planes` | 114 | Item 2: Box, Hole, Offset Plane, Extrude on the plane and on the offset plane, Cylinder, undo / redo, on Top, Front and Right; an older box keeps its side |
| `book_extrude2_across` | 37 | Items 3 and 6: Cut by itself across components, the check box list, "Body1 (Block)", mostly outside is a New Body, the top row active, the edit reads back |
| `book_extrude_across` (updated) | 43 | Item 3: the first builder's cross-component paths with the new rule |
| `book_extrude_operation` (R9 updated) | 74 | Item 3: wholly inside another component's block: Cut; two fifths inside: New Body (bug 10); own body: Cut |
| `surface2_loft`, `surface3_untrim_revolve`, `extrude_presspull_qa4` | 107, 77, 73 | Item 1 |
| `live_shapes` | 120 | Item 7 |

Older scenarios of the files changed, run one batch at a time, all PASS: `primitives_qa`
(109), `primitives_qa_keys` (52), `book_extrude_primitives` (48), `inspect_construct` (69),
`inspect_construct_planes` (86), `book_extrude_direction` (41), `components_extrude` (171),
`extrude_multibody` (127), `extrude_multibody_edit` (138), `extrude_objects` (44),
`gaps_join_new_body` (241), `bodies_combine` (93), `components_basic` (252),
`modeling2_bodies` (57).

Without a window (each with a unit test that runs it in real FreeCAD):
`front_plane_check.py` (98 checks), `body_names_check.py` (21), `sketch_area_id_check.py`
(64 + 27 for save / reopen). Unit: `test_extrude_bodies_core.py` (2 new tests).

## Shared files touched

- `construct.py`, `construct_ui.py` (components'): the Offset Plane's side on the Front
  plane (item 2; the brief allows it). About 60 lines in `construct.py` (a block of its own
  before `_c_OffsetPlane`, and the three places the distance is written, computed and
  read), 6 in `construct_ui.py`.
- `ai/ops/core.py`, `ai/catalog/kit.py`, `ai/executor.py` (nobody's by the table): the
  extrude step on a marked sketch, the help text, body names.
- `combine_ui.py` (modify's): one line, the Target box's text.
- `bodies_gui.py`, `bodies_row_ui.py` (body naming: mine by the brief): the names shown.
- Scenarios of other areas: `surface2_loft`, `surface3_untrim_revolve` (surface; the body
  lookup after reopening), `live_shapes` (the rebuild check).

## Changelog lines

- A Box, Cylinder or Coil placed on the Front plane now grows away from the front for a positive height, the same way Extrude goes, like Fusion.
- An Offset Plane made from the Front plane now moves away from the front for a positive distance, like Fusion; planes you made before stay where they are.
- Extrude now switches to Cut by itself when you push a profile into a part of another component, and lists that part under Bodies to Cut.
- The Bodies to Cut list of Extrude now has a check box for each body: untick one to leave it out.
- When two bodies have the same name (each component's first body is Body1), dialogs now show which one: "Body1 (Bracket)". The AI tools take that name too.
- If every body is left out of a Cut, the dialog says that the list is empty and how to take a body back.

## Known issues

- A Gear placed on the Front plane still counts its thickness towards the front.
- Revolve, Sweep, Loft, Pipe, Coil and the primitives choose Cut or Join by looking at the body their profile or plane belongs to; pushed into a different body they stay New Body or Join until you pick Cut.
- With a component active, a cut you make in another component's body is not shown in the timeline until the design's top row is active again.
- The AI tools count along FreeCAD's own direction on the Front (XZ) plane (towards -Y), as their help says; a number you typed in a dialog for the same plane has the other sign.
