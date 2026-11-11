# Wave 7, builder "library-2" (2026-11-11): hardware and looks, the follow-up

Branch `sf/book-library-2` (from 3d7b241a, develop merged later). Takes over the areas of the
builders "hardware" and "looks" (`docs/fission180/sessions/book-hardware.md`,
`book-looks.md`). Specs with sources: `docs/fission180/parity/hardware.md`,
`docs/fission180/parity/appearance.md`.

## Item 1: the dimension tables, verified

- The sandbox cannot open a web page (WebFetch: no host resolves); a web search only gives
  excerpts, and excerpts rarely show table cells: 26 searches confirmed single rows only.
- What worked: the data files of an open-source parts library, **bd_warehouse 0.4.0** (PyPI,
  Apache-2.0), typed from the same standards by other people. A script compared every row
  the two have in common: 1,207 values agreed. Used as a reference only; nothing of it is in
  the repository.
- **Wrong in the first pass (corrected):** AS568 -438 to -445 (the series runs in quarters of
  an inch from -438, the table had eighths: -445 was a whole inch short); ISO 7379 head
  heights of the 12 and 16 mm shoulders (8 -> 9, 10 -> 11); DIN 472 37 mm ring width (3.5 ->
  3.6). 11 rows.
- **Wrong in the reference, not in the table** (each checked with a second source): the
  reference's "ISO 10642" head is DIN 7991's; its thin nuts M10 / M12 have DIN 439's spanner;
  its #1 set screw key is 0.028 (0.035 is right); its DIN 471 48 mm ring is 2 thick (1.75 is
  right); its recessed pan heads #3 - #12 are a few thousandths higher than B18.6.3-2013.
- The unit test that should have caught the AS568 error only checked "a 64th of an inch
  less a constant": it passed for the wrong rows too. New tests: the step between dash
  numbers per series, and rows typed again from suppliers' listings.
- Still a Guess (no source found): the inch retaining rings' radial width, the inch dowel
  pins' chamfer, the metric O-ring pairs, the commercial length ranges. Not confirmed by any
  excerpt (the numbers are two recollections of the standard agreeing): ISO 7040, ISO 2338,
  the set screws' point diameters, ASME low head and flat head socket screws, jam nuts.
  The table in `parity/hardware.md` says which.

## Item 2: a fastener's joint follows its hole

- Reproduced with real input (scenario `book_library2_joint_follows`, first run on the old
  code): the hole's sketch dimension 30 -> 22 typed in the sketch, the hole moved to x 23,
  the screw stayed at x 15. The joint named "Vertex1" of the plate (as built).
- Fusion: "inserted fasteners and their joints appear in the Timeline" (Autodesk, Fasteners);
  the joint is made on the hole's circular edge.
- Built: `hardware.join()` makes the rigid joint with its origin on the round edge of the
  hole (`hardware.hole_edge`: the round edge on the place's axis nearest the place, in the
  body's own shape; `joints.create_as_built_joint(..., origin_pick, origin_snap)`): the
  plate's side follows its geometry (`joints.repair_references`, by name, else by
  likeness), the screw's side keeps its place on the screw. When the hole moves the joints
  watch solves and the screw goes along. Flat faces with no round edge keep the as-built
  joint.
- **Trap:** a joint left in while the Hardware step is edited pulls the part back onto its
  old hole (the joints watch solves after every recompute, also inside a dialog's undo
  step). `hardware.update()` now takes away the joints of the occurrences an edit has moved
  (`_drop_moved_joints`); `join()` makes them again at OK and keeps the ones that still hold
  (same joint objects: the timeline's names stay).
- A joint with an origin draws its mark at the hole: the 3D view's fit changed a little, and
  `hardware_insert`'s click on the 6.2 mm pocket rim (a pixel outside the magnet's 6.0 edge)
  now aims from just outside the rim.
- Not solved here: which part moves when the solver runs is the joints' rule (the group's
  grounded part, else component 2 of its oldest joint): a screw that is itself component 2
  of an older joint would stay and the plate would move.

## Item 13: `body_pick_many`'s flake (1 run in 10)

- Reproduced: `--repeat 10` on develop + item 2: 9 passed, run 10 failed in path B ("Move/Copy
  holds all three bodies: None"), yet the same run logged "Move/Copy done": the dialog was
  on screen and worked, but `taskui.current()` said None.
- Cause: `taskui.current()` forgot the registered dialog whenever no task dialog was on
  screen. A dialog registers itself while it is built, runs its first preview and only then
  is shown. The selection read-out (`properties_readout_ui`, wave 7 looks) asks "is a dialog
  open?" from a timer a moment after every selection change; Move's start clears the
  selection, and a slow first preview lets timers run. Asked in that gap, the dialog was
  forgotten for good: on screen, working, but unknown (no Esc, no "finish it first", no
  typing over the view; the test saw "no body"). `preview.py` already had a comment about
  this hazard for its own call.
- Fixed at the root in `taskui.current()` (shell's file, 12 lines): a dialog that has never
  been on screen is not forgotten, only reported as not open yet. The read-out no longer
  asks through `current()`.
- Proof: `book_library2_dialog_kept` builds Move, asks in the gap, shows it: on the old
  code "it is the open dialog (not forgotten)" fails (run on a snapshot of the old code),
  with the fix it passes.

## The Keep / Remove / Cancel question (GitHub's run of 049c500b: `bodies_look` red)

- The question was a modal `QMessageBox.exec()` started from a 30 ms timer after the click.
  The scenario's answer was set up for a box opened inside the step; on a slower machine
  the box came after the step, nobody answered, and the scenario stood behind a modal box.
- Now the question is a row of the Appearance dialog (text, Keep / Remove / Cancel), never
  a box: nothing waits inside FreeCAD's event handling. One drop or click asks once, also
  for a component's row with several bodies (one question for all); OK waits for the answer
  ("Answer the question first"); a new drop replaces an unanswered question.
- The AI tool `appearance` takes `keep_face_looks` (true / false) and never asks; when the
  body has face looks and the argument is missing it refuses and says what to add.
- Scenarios: the drop step ends with the question open (by state), the next step clicks
  the button; `bodies_look` and `book_looks_faces` check one question per drop and that no
  modal box is up.

## FreeCAD / Fission 180 facts and traps (new)

- `taskui.current()` used to clear the registration as a side effect: any "is a dialog
  open?" asked from a timer was a hazard. It no longer forgets a dialog that was never on
  screen.
- The joints watch solves after every recompute, also while a dialog is open and inside
  its undo step: whatever a dialog moves by hand must not have an active joint that wants
  it elsewhere.
- `run_tests.sh` finds the module relative to itself: a copy of `src/Mod/Fission180` and
  `tools/fission180` in a scratch folder runs a long batch (`--repeat 10`) while the
  worktree is edited.
- A worktree-isolated agent's shell refuses commands that mix `git` with redirects, `cd`
  or here-documents: patch scripts are written with the Write tool and run as plain
  commands.

## Item 7: Component Color Swatch in the browser and the timeline, Cycle Component Color

- Fusion (Autodesk, "Color code components and features", search excerpt): every component
  has a colour in the canvas, the Browser and the Timeline; a feature of several components
  shows a swatch for each; right-click a component > Cycle Component Color; the timeline's
  Settings > Component Color Swatch hides or shows the swatches while the canvas colours can
  stay on. Forum (an Autodesk reply): the Cycle entry only shows while component colours
  are displayed.
- Built: `component_colors_ui` answers two small hooks, `browser_ui.ROW_COLORS` (a square
  before the row's activate ring) and `timeline_ui.STEP_COLORS` (bars along a step's foot).
  A step's component is read from the step's body as it is now (a body moved into a
  component takes its steps along; the timeline item's own `component` field said the
  root for those). Cycle picks the next colour no other component has; the number of
  cycles is a hidden property of the component (saved, undoable).
- The list in the 3D view is gone. Off by default (Guess: Fusion's default was not found).

## Item 11: a new body is drawn in the default look

- Measured first: a new body's colours were FreeCAD's (0.8 grey), the library's Steel,
  satin is (0.62, 0.63, 0.65); the first builder had made the default look's swatch show
  FreeCAD's grey instead of making the body show the look.
- Built at the root: FreeCAD takes a new part's colours from its Part colour preferences
  (`View/DefaultShapeColor`, `DefaultAmbientColor`, `DefaultSpecularColor`,
  `DefaultEmissiveColor`, `DefaultShapeShininess`, `DefaultShapeTransparency`); they are set
  to the default look at start (`appearance.use_default_look`), so FreeCAD itself draws new
  parts in it, and what FreeCAD writes on a body when its material is touched (bug 16's
  grey) is the same look. Bodies of older designs that were saved in the old grey take the
  default look when the design opens (`adopt_default`; the design does not count as
  changed). Bodies with a look are not touched. The themes do not touch these preferences.
- A colour goes through FreeCAD's preferences in 8 bits: the numbers a body is drawn from
  are the look's within 1/255.

## Items 3 and 6: the cosmetic thread, the AI tool

- `thread_ui.cosmetic_spots` got one generic branch: a step may say its own cosmetic
  threads in the hidden property `Fission180CosmeticThreads` (JSON like `thread.computed`'s
  "threads"). The Hardware step says it, and so does the base step of each occurrence's
  body (an occurrence's body is a copy body: its only step is a `PartDesign::FeatureBase`).
- `insert_hardware`: the op had `wall` already, the catalogue did not offer it. Now face /
  edge / wall, and on a hole the dialog's rules (`hardware.fit_to_place`: size from the
  hole, no second hole, the head seated), `similar`, `joint`. The schema's defaults are not
  applied to a call's arguments by the executor: a tool that wants a default on says so
  in a `steps=` function (`_steps_hardware`).

## Item 9: Part Number, Part Name, Description

- The drawing's parts list read the component's name as PART NUMBER and `Label2` as
  DESCRIPTION. Properties now has the three as fields for the one component selected: the
  name is the component's label (renamed through `components.rename`), the description
  `Label2`, the part number a hidden property (`Fission180PartNumber`; empty = the name,
  which is what Fusion starts a part number as). `drawing._part_name` reads the part number
  (one helper, `_number_of`: drawings' file).
- **Trap:** a `QDialog`'s first push button is its default button: Enter typed in a field
  of the Properties dialog pressed Copy to Clipboard. The dialog's buttons are no longer
  auto-default.

## Item 12: a pattern on a finely drawn part

- `appearance_draw.COUNTS` counts how often a big part's pattern was put off and how often
  a pattern was worked out; the scenario orbits and drags by real input and checks the
  pattern is worked out once per change.
- **Found on the way (not in these files, on plain develop too):** Move/Copy on a body whose
  view was given `Deviation = 0.02` and `AngularDeflection = 2` (by script: Fission 180 has
  no setting for them) never comes back from FreeCAD's recompute (`preview.recompute` called
  by the Move dialog's tick; the harness's watchdog ended FreeCAD after 30 s). The same
  torus with FreeCAD's default mesh settings moves fine. Probe scenario, three runs:
  default mesh PASS; fine mesh FAIL on this branch; fine mesh FAIL on develop 049c500b+.
  The scenario's part is therefore made fine by its many faces (28 balls on the donut), not
  by the mesh settings.

## Item 10 (in part): New Appearance picks its colour on a wheel

- Manage Materials > New Appearance had a text box "Colour (#RRGGBB)". It now has the look
  editor's colour wheel (`appearance_edit_ui.ColourWheel`), a brightness slider and a
  swatch; the code is filled in from the pick and can still be typed. Nothing has to be
  typed for the colour.
- Not built: editing a user material in place (name, density, look) and copies that change
  every listed property. `material.create_user_material` only takes a density; a material's
  other values come from the card it was inherited from (`MaterialManager.inheritMaterial`,
  see book-looks.md's trap about `addPhysicalModel`).

## A Hardware step's place follows its own hole

- Found while testing item 2: a screw put on a flat face makes its own Hole step; when that
  hole was moved afterwards, editing the Hardware step put hole and screw back where the
  face had been clicked (the step kept the clicked point). `hardware.pick_of` / `more_of`
  now give the place where the step's own hole is now (`hole.centres`).

## Not done (with the reason)

- **Item 4** (hover preview of the part, a sketch point as a place, a nut or washer clicked
  onto a screw, a hole with a modeled thread read as a hole): not started. Each is a piece
  of `hardware_place.spot` plus dialog work; the room went to items 1, 2, 7, 11, 13, the
  CI failure and items 3, 6, 9, 12.
- **Item 5** (retaining rings with lugs, a real Phillips recess, head and nut chamfers):
  not started; every changed shape needs its volume formula, golden models and the 1,706
  combinations test again.
- **Item 8** (drag handles for Texture Map Controls): not started.
- **Item 10**: only New Appearance's colour wheel (above).
- Item 1: the families marked "not confirmed" in `parity/hardware.md`.

## Tests (FreeCAD 1.1.4, this sandbox, one scenario at a time, from a snapshot of the tree)

See the builder's report for the counts of the last round.

## Changelog lines

- Hardware sizes were checked against a second source: eight large O-rings (AS568 -438 to
  -445) had inside diameters up to an inch too small, two shoulder screws (12 and 16 mm)
  had heads 1 mm too low, and the 37 mm internal retaining ring was 0.1 mm too narrow. They
  are right now.
- A screw, nut, bearing or other hardware part now follows its hole: move the hole (change
  its sketch's dimension, or move its Hole step) and the part goes with it.
- Editing a hardware part whose own hole you moved no longer puts the hole back.
- A hardware part with cosmetic threads now shows its thread as a dashed spiral, like a
  cosmetic thread made with the Thread tool; with Modeled threads on, the real thread is
  cut as before.
- The AI's `insert_hardware` can put a part into a hole from any part of the hole (rim,
  wall, countersink), sizes it from the hole, can fill every hole like it, and joins it.
- Component Color Swatch (the timeline's gear menu) now marks each component's colour on
  its row in the browser and on its steps in the timeline, instead of a list in the 3D
  view. A joint's step shows both components' colours.
- New: right-click a component > Cycle Component Color gives it another colour (while
  component colours or the swatches are shown).
- A new body is now drawn in the default look, "Steel, satin", exactly as In This Design
  lists it (it used to be a lighter grey). Older designs' plain grey bodies take it too
  when they are opened; bodies you gave a look are not touched.
- The question "Keep or Remove the faces' own looks?" is now a row inside the Appearance
  dialog with the buttons Keep, Remove and Cancel, instead of a box that stopped
  everything until it was answered.
- Properties of a component now has Part Number, Part Name and Description: type them
  there; the drawing's parts list shows the part number and the description.
- Manage Materials > New Appearance: pick the colour on a colour wheel (no code to type).
- Fixed: once in a while a dialog (seen with Move/Copy started from several selected
  browser rows) was on screen but Fission 180 did not know it was open, so Esc, typing a
  value over the 3D view or starting the next command did not treat it as open.
- Fixed: pressing Enter in the Properties window no longer copies the list to the
  clipboard.

## Known issues

- A hardware part on a flat face with no hole under it (Make the hole too off) moves with
  the part it sits on, but has no hole to follow: tick Make the hole too, or click a hole.
- When a hole moves, the screw goes to it, unless the screw itself is what an older joint
  holds everything else to: then the holed part comes to the screw. Ground the part that
  should stay (right-click it > Ground to Parent).
- Each hardware joint shows its mark at its hole. Click the eye of the Joints folder in
  the browser to hide them.
- A nut or washer cannot be clicked onto a screw, and a sketch point is not a place for a
  hardware part: click the face or the round edge it sits on. There is no preview of the
  part under the pointer before the click.
- Retaining rings are drawn without their lugs, a Phillips recess as two crossed slots,
  and screw heads and nuts without their chamfers.
- A few hardware families could not be checked against a second source (ISO 7040 lock nuts,
  ISO 2338 pins, set screws' point sizes, inch low head and flat head socket screws, jam
  nuts): check such a size against the supplier's sheet before ordering.
- Component Color Swatch is off until you tick it (the timeline's gear menu). The design's
  own row always keeps the first colour (Cycle Component Color is for components).
- Part Number, Part Name and Description can be typed when ONE component is selected (click
  its row in the browser); for a body or several things the fields are grey.
- Texture Map Controls still has no handles in the 3D view: type the offset, rotation and
  scale.
- A material of your own cannot be edited in place yet: make another copy (double-click).
