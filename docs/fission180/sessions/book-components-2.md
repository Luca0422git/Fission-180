# Session log: book-components-2 (wave 7, 2026-11-11), branch `sf/book-components-2`

The follow-up of `sf/book-components` (merged): the older journeys its (correct) change
broke, the things it left open, and the scenarios run the way a person's install is set up
("First component Ground to Parent" on). Spec and sources: `docs/fission180/parity/components.md`,
"Part 4".

## Part 1: the plastic journeys, and every command aimed at another component

### The failing checks of `journey_plastic*` and what was decided

| Check (old) | What happened | Decision (Fusion) |
|---|---|---|
| "Lid: automatic operation Join (touches the Base), not Cut" got New Body | The Lid is active and has no body; the Base it touches is another component's | The check was the old behaviour. Fusion proposes New Body ("it has to be New Body, as there is nothing in the other Component to join to"). The check now expects New Body and the journey no longer picks it by hand |
| "boss_sketch / snap_sketch: the sketch is in the Base" got Lid | The journey clicked the Base's rim with the Lid active and relied on the click switching the active component | The journey now activates the Base first (the ring on its browser row, real input), as a Fusion user does; the checks stay |
| "Rest: a pad 3 mm out of the wall" got 0.0, "one flat 20 x 10 face at y -3" got [] | A real silent wrong result: `plastic_rest.body_under` took the body the profile's SKETCH was in whenever it had a solid. The sketch was in the Lid (new things go into the active component), so the rest was built on the Lid's snap hook, 46 mm behind the profile, and nothing was said | Fixed in the app: the body NEAREST to the profile is taken (the sketch's own when it is as near). The journey keeps the Rest as its "wrong way" step on purpose: the Lid is active, the plane and the sketch go into the Lid (checked), the rest is built on the Base (checked: +312 mm3, the Lid untouched), the dialog names "Body1 (Base)" and says "Body1 is in Base, not in the active component Lid: the rest changes it there" |

`journey_plastic` 232 checks, `journey_plastic_rule` 308, `journey_plastic_timeline` 235: PASS.

### The audit (component A active, the command aimed at B)

Reproduced with a probe scenario by real input before any change. Table with sources:
`parity/components.md` Part 4. What was wrong:

1. **The active component switched silently** (Shell, Hole, Thread, an Extrude Cut chosen by
   hand; Fillet / Chamfer started with an edge of B selected). Root cause: the active
   component was READ FROM the active body (`components.active_component`), and these
   commands make the body they work on the active body (`setActiveObject("pdbody", ...)` in
   `pickpanel.activate`, `hole_ui._use_body`, `thread_ui._use_body`, `fillet_ui`; Extrude's
   OK activated "the body the feature is in"). Fix, in one place: the active component is
   what the person chose (`components._chosen`, set by `set_active` and `activate_body`);
   `components.settle_active` gives it its own body back when a dialog closes
   (`taskui.Panel._close`) and before the next command (`commands.finish_open_dialog`);
   `components.activate_result` for the six dialogs that activate their result's body.
2. **Fillet / Chamfer ignored a click on B's edge** (F with nothing selected, then the
   click): the dialog's selection gate only let its own body through, in any design with
   two bodies. Now a first click on another body moves the dialog to that body; with picks
   already it says why not.
3. **PLASTIC Rest** on the wrong body (above).
4. **Nothing was said** when a step went into a body outside the active component, where
   the active component's timeline does not show it. Now a note next to the mouse says so
   when the dialog closes on OK (`components.outside_tips` taken at the dialog's start finds
   it for Combine, Split Body, Mirror, Press Pull and Flange too).

The first builder's open item "a Cut chosen by hand says 'The cut does not go through any
body'" did not reproduce: the cut goes through B's block (checked in the scenario, both in
the preview and after OK). What it probably saw was the active component switching after OK.

## Part 2: the suite with "First component Ground to Parent" on

The harness block that switched the preference off is gone. Every scenario of the brief's
list ran one at a time with the default preference (70 of the list, plus 30 more that the
changed files or the orchestrator's questions touch). Two failed because of the ground
(`components2_bodies`, `components2_move`: they moved their first component with Move) and
one because of the Align fix (`modify_align`); all pass after the scenario changes below.
Nothing else in the list needed the preference off: the joints and VEX scenarios make
their components by Insert or through the modules, which do not ground (Fusion grounds
the first component *created*; an inserted one is not grounded, here as there),
and the Joint dialog ungrounds the first component picked.
Scenarios that assumed a free first component now do what a person does: right-click the
component > Unground From Parent (`component_steps.unground`, real input), with a comment.
App fixes: Align refused nothing (it moved a grounded component); Move's refusal now names
the menu entry.

## Part 3: what the first builder left open

1. **A copy of a subassembly keeps its structure** (`instances.py`): a holder component per
   nested component of the source, inside the instance, named and nested like it
   (`Fission180NestedOf`), with the copy bodies in it. Holders keep no placement of their
   own: the copy features place the solids, so the copy follows a part moved inside the
   original. `sync` adds and removes holders; `hand_over` turns the heir's holders into
   ordinary components. Instances saved before this stay flat (`Fission180Nested` marks the
   new ones): joints made on a flat instance keep their references.
2. **A mirrored component is named "Name (Mirror)"** and is no numbered occurrence.
3. **A construction built on another component keeps its place** when that component moves
   later (`construct._freeze`, `_frozen_world`).
4. **Internal / External** in New Component: External greyed with the reason.
5. **Paste**: Cancel or Esc in the Move that opens takes the paste away again.
6. The "Where each command puts its result" rows: probed in `book_components2_cross`
   (Hole, Thread, Fillet, Chamfer, Shell, patterns / Mirror of bodies, Split, Combine).

## Test results (one scenario at a time, the preference on, real FreeCAD 1.1.4)

New: `book_components2_cross` 235 checks, `book_components2_structure` 89,
`book_components2_refs` 70. The plastic journeys: 232 / 308 / 235. The brief's list of 70
scenarios and 30 more: all PASS after the changes named above (the first run's failures:
`components2_bodies`, `components2_move` (the ground), `modify_align` (Align's refusal),
`book_components_pattern` (my own expectation of the rows)). Unit tests: 3559, OK. Golden
models: 644 pass, 2 expected failures (as on develop).

## Added by the orchestrator while this ran

1. `insert_step` failed at "in the Plate's body" on develop: with the design active the
   sketch on the inserted Plate's face now goes into the design's root (the wave 7 rule,
   and Fusion's). The scenario follows Fusion's workflow now: it checks that result (the
   root, lying on the face, the design still active), then activates the Plate by its ring
   and checks that the next sketch goes into the Plate's body. Its check of the second
   occurrence expects the rows of the parts inside ("two_parts:2" holds Plate and Peg).
   Searched the scenario folder for other "in the clicked body" checks after a Create
   Sketch on a face of an inserted or component-held body: `insert_step` was the only
   scenario that inserts a part and sketches on it itself; `fixsketch_*` ("the sketch is in
   the clicked body") sketch on bodies at the design's root, where the clicked body is in
   the active component. Run after the change: `insert_step`, `insert_svg`,
   `direct_base_feature`, `direct_commands`, `direct_history`, `direct_components`,
   `rebuild_start`, `fixsketch_join`, `fixsketch_move`, `vex_qa_inch_sketch`,
   `meshinspect2_inspect`, the `journey_rebuild*`: see the final report.
2. Properties in the browser: `book_components2_refs` H right-clicks the Nozzle's body row
   and the Nozzle's own row > Properties; the dialog opens for that body / that component
   (its bodies counted, its title).
3. Hardware's inserted standard part is not grounded: nothing in this work grounds an
   inserted component (`components_ui.ground_first` is only called by New Component and
   Create Components from Bodies). A second, separate insert of the same part being a new
   component ("Name (2)"): Fusion does the same by a forum answer ("if you create just one
   fastener ... and use Copy/Paste to duplicate the fastener in Fusion, you do get
   instances, not separate components": separate inserts are separate components). Left as
   it is.

4. The harness's new check "no undo step stays open" (the shell builder) found: Create
   Sketch on a design without a body, then cancelled, left "Add a Body" open with an empty
   body (`origin_squares_small`, `book_components_menus`). Root cause:
   `commands.ensure_body()` runs FreeCAD's Body command, which leaves its step open when it
   is run from inside another command, and nothing closed it when the plane picker was
   cancelled. Fix: `commands.drop_made_body` (the open step is aborted, the body goes with
   it; when a dialog's own step closed it meanwhile it is taken back while it is the newest
   step), called by `SketchPicker.reject`, by a sketch that could not be made, and by
   `taskui.Panel._close` for every cancelled dialog (the CONSTRUCT tools, Insert, Section);
   Box makes its body inside its own step already. `book_components_menus` C relied on the
   body left behind: it now checks that none is left and sets an empty body up through the
   module for its drag. New scenario `book_components2_cancel` (29 checks, the undo check
   strict).

   Run with `FISSION180_STRICT_UNDO=1` on the fully merged code (develop e35d1ef2), one
   at a time: the five `book_components2_*`, the eight `book_components_*`, `components2_*`
   (5), `components_basic / _extrude / _move`, the three `journey_plastic*`, `insert_step`,
   `modify_align`, `origin_squares_small`, `direct_components`, `book_joints_ground`,
   `joints_basic`, `vex_duplicate`, `journey_vex`: all PASS, no undo NOTE left in any of
   them. (`direct_components` first failed there for another reason: it aligned its first,
   grounded component; it ungrounds it in the browser now, like `modify_align`.)

## FreeCAD facts and traps (1.1.4)

- `view.setActiveObject("pdbody", body)` does not touch the "part" slot; Fission 180's
  `commands.find_body()` then called `sync_part_slot`, which is how a body made active by a
  command dragged the active component along.
- `doc.UndoCount` does not count a pending transaction: taken when a dialog opens and
  compared when it closes, it tells an OK that kept a step from a Cancel.
- A disabled `QRadioButton` still shows its tooltip, and a `QTest` click on it does nothing.
- `App::PropertyPlacementList` exists and is saved; a property set inside `execute()` (the
  construction frame freezing itself the first time) does not loop.
- `run_tests.sh` links the module of the tree it is started from: a copy of
  `src/Mod/Fission180`, `tools/fission180` and `docs/fission180` in a scratch folder runs a
  batch while the worktree is edited.
- A shell here-document with code in it is refused by the worktree guard: write the file
  with the editor tools instead.

## Shared files touched (smallest change, each marked "wave 7, components-2")

- `taskui.py` (shell): `set_current` remembers the undo count and the outside bodies' last
  steps; `Panel._close` calls `components.settle_active`.
- `fillet_ui.py` (modify): `_Gate.allow` and `_process_selection` let a first click on
  another body through (`_other_body_pick`, `_follow_other_body`, `_other_solid_body`).
- `extrude_ui.py`, `revolve_ui.py`, `sweep_ui.py`, `loft_ui.py`, `pipe_ui.py`,
  `primitives_ui.py` (extrude): one line each, `components.activate_result(body, feature)`
  instead of `components.activate_body(body)` after OK.
- `plastic_rest.py`, `plastic_rest_ui.py` (plastic): `body_under`; the Builds in label and
  the note.
- `align_ui.py` (modify): a grounded component is refused with Move's sentence.
- `commands.py` (`finish_open_dialog`: components' own area by the brief).
- `Fission180Tests/gui/harness.py`: the block that switched First component Ground to
  Parent off is removed.
- Scenarios updated: `journey_plastic_steps.py`, `components2_bodies`, `components2_move`
  (Unground From Parent first), `components2_copy`, `book_components_move` (Esc after a
  paste takes it away), `book_components_pattern` (structure, the mirror's name);
  `component_steps.py` (`grounded`, `unground`).

## Changelog lines

- A command aimed at a part of another component (Shell, Hole, Thread, Fillet, Chamfer, a
  Cut) no longer makes that component the active one: the component you activated stays
  active.
- Fillet and Chamfer now take an edge of any body when you click it first, also in another
  component.
- When a step changes a body that is not in the active component, a note next to the mouse
  says where the step went.
- PLASTIC > Rest builds on the body nearest to its profile, and names that body with its
  component; it no longer builds on the body the sketch happens to be in.
- A patterned, mirrored or pasted subassembly keeps the parts inside it as rows in the
  browser.
- A mirrored component is called "Name (Mirror)".
- Esc or Cancel right after a Paste takes the pasted copy away again.
- A plane, axis or point built on a part of another component stays where it is when that
  part is moved later (it still follows when the part changes shape).
- New Component shows Internal / External; External is greyed and says what to do instead.
- Align no longer moves a grounded component; it says to unground it first.
- Create Sketch (or a CONSTRUCT tool) cancelled in an empty design leaves no empty body
  behind, and Undo is not confused by it.

## Known issues

- A step made on a body of another component is listed in that body's component, not in the
  active one as in Fusion: activate that component (or the design) to see it in the timeline.
- A fillet or chamfer rounds edges of one body: finish it and start another for the next body.
- A part inside a copy of a subassembly cannot be moved or jointed on its own: move it in
  the original and every copy follows. The copies show the original's joints' positions but
  have no joints of their own.
- A mirrored component cannot be edited on its own (edit the original; the mirror follows).
- Copies of a subassembly made before this version stay flat; delete and make them again to
  get the rows.
- New Component offers no External component; save the part as a design of its own and use
  INSERT > Insert into Current Design.
- Editing a step of another component from the timeline (with the design active) still
  makes that component the active one.
