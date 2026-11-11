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
