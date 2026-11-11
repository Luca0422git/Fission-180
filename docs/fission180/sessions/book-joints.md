# Session log: wave 7 builder "joints" (branch `sf/book-joints`, 2026-11-11)

Brief: `docs/fission180/dev/briefs/book-joints.md` (the joints of the book parity report,
`docs/fission180/dev/research/book-parity-report.txt`). Spec and sources:
`docs/fission180/parity/joints.md`, section "Wave 7".

## What the report said, and what was really happening

Every item was reproduced in real FreeCAD 1.1.4 with real input (probe scenarios) before any
change. Three of the report's five joint bugs had one root cause it did not see.

| Report | Reproduced? | What really happened |
|---|---|---|
| Bug 11: "Edit Joint on an as-built joint leaves its transaction open; the next command aborts it" | Yes, but only with components and a joint made *after* the edited joint (the Pizza Cutter's order). Not with two parts and one joint. | The transaction was not left open after OK: **OK had been refused**. Editing a step rolls the history marker to it; the later components were hidden and their bodies rolled back, but the later joints were still solved and checked. Their references were gone ("?Face6", "Broken link in Reference1"), `broken_joints` named them, the dialog said "The joints cannot all be satisfied together: Rigid 2 fights the others" in its last line and stayed open. The browser already showed "Cylindrical 1" (the preview), so it looked done. The next command then finished the dialog the only way left: Cancel, without a word. |
| Bug 12: "Edit Joint Limits opens showing Rigid with no limits; its Cancel also reverts the earlier edit" | Yes, same setup | The same thing seen from the next command: the edit had just been cancelled by it, so the joint *was* Rigid again. With the edit really kept, the dialog shows the joint's type and limits (it always did: `joints_asbuilt_group` C). |
| Bug 13: "As-built Slider with no axis silently becomes Rigid" | Partly | OK was refused (it always was), in the dialog's last line. But the preview kept the joint it had made while the type was still Rigid: "Rigid 5" stood in the browser and the timeline and looked finished. |
| Bug 14: "Joint references go stale: Broken link, ?Face5, ?Edge41, fights the others" | Yes, three causes | (1) The same rolled-back joints as bug 11 (any roll of the marker, by hand or by an edit). (2) **As-built joints and rigid groups stored the joint origin as a place in the design** and worked it out again against the component's place at every recompute: after a component had moved, the joint silently had a new zero, or fought the others; a rigid group let go of its members (found here, not in the report). (3) The repair by signature only matched an element that had not changed at all, did not run while a dialog was open, never repaired an as-built side, and a snap on an edge of a face (a midpoint, a corner) fell back to the face's centre when the edges were numbered anew. |
| Bug 15: nested components not picked from the browser | see "Nested components" below | |
| "Clicking a round edge gives (corner) or (midpoint)" | Yes | The kernel's own points were offered as snaps: a full circle's seam vertex and the point opposite it, a cylinder's seam line. They are on the edge, so they were always nearer the pointer than the centre. |
| "The (loop) centre is 0.37 mm off on threaded geometry" | Yes (a notched rim) | A hole's centre was the centre of area of its outline; a thread's run-out makes the outline not quite round. |
| "Dragging the crank moved A and B but the rocker stayed" | Yes (headless: the crank did not move at all) | The solver is free to satisfy a closed loop by turning the driven joint back, and did. Cause (2) of bug 14 made it look different each time. |
| "Rest does nothing after a drag" | Yes | Rest was only applied on OK of the dialog. |
| "No Flip, no Preview Limits" | Yes | Not built. (Fusion's button is called Preview Motion; "Preview Limits" is the book's name.) |
| "Enter in Motion Study's value box closes the dialog" | Yes | FreeCAD's task panel presses OK on Enter in any field. |
| "Select Other for coplanar overlapping parts" | Not a bug | A long press already lists what is under the pointer in the joint dialogs; the report did not try it. Now tested (`book_joints_snap` E). |

Where the report was wrong about Fusion: its "Flip" for limits is not an axis flip of the
joint (Autodesk: "swaps the minimum and maximum motion limit values"); "Preview Limits" is
Preview Motion with a With All Limits tick; "Link with Same Joint" exists under that name in
the forum's words only (Autodesk's own page could not be read).

## What was built

- `joints.py`: joints follow the history marker (`mark_rolling`, `rolled_back`,
  `rolled_back_names` with a cache dropped by the document watch, `_only_active` for
  FreeCAD's own solver and `isPartConnected`); as-built origins relative to the component
  (`as_built_record(plc, ref)`, `freeze_as_built`); the repair (`likeness`, `find_alike`,
  `_repair_as_built`, `_remember_snap`, `_snap_of_record`, the `lost` mark, `lost_side`,
  `note_lost`, `lost_text`); keypoints (`_keypoints`, `_true_loop`); a joint's own motions
  tied (`own_link`, `own_ratio`, `tie_own_motions`, `clamp_values`); closed loops
  (`in_loop`, `_holding`, `solve(hold=...)`); Rest (`rest_values`, `settle_rest`); one joint
  alone (`lone_side`, `drive_alone`).
- `joints_ui.py`: a refused OK said next to the mouse, a dialog cancelled by another command
  says so (`_JointsPanel.accept` / `finish`); As-built Joint keeps no joint while a moving
  type waits for its position; `_close_step` for the commands without a dialog; the watch
  repairs with a dialog open and says a lost joint once; `_Limits` with Flip, Preview Motion
  and With All Limits; `Animator(alone=, motions=)`; `animate` (alone) and
  `animate_relationships`; a joint that lost a side says which in its dialog; a re-picked
  side keeps the other side's record.
- `joints_motion_ui.py`: Link with Same Joint; Motion Study's graph (`StudyGraph`) and Enter
  setting the point (`_EnterSetsPoint`); Motion Link's Animate button stops when pressed
  again.
- `joints_drag.py`, `joints_limit_drag.py`: the dragged joint held in a loop, Rest on
  release, a screw led by the motion the pointer asks more of.
- `motion_core.py`: `tied_values`, the graph's maths (unit tested).

## FreeCAD facts and traps

- `Application::closeActiveTransaction(false)` **ignores** the close while a command's
  `AutoTransaction` guard is positive, and `Gui.Control.showDialog` flips that guard
  negative (which is why a dialog opened by a ribbon command keeps its undo step). None of
  this was the bug; it took an hour to rule out.
- FreeCAD's `AssemblyObject.solve()` reads the stored `Placement1/2`; it does not call the
  Python `findPlacement` again. To hold a joint for one solve, set `Placement1` and
  `JointType = "Fixed"` and put both back (`joints._holding`).
- FreeCAD's solver skips a joint that is `Suppressed` (and one in error). There is no way to
  hand it a list, so rolled-back and lost joints are suppressed for the moment of the solve
  (`_only_active`; `JointProxy.onChanged` ignores that).
- `JointObject.Joint.execute` raises "Broken link in: Reference1" for a "?" name: a traceback
  in the Report view at every recompute. `JointProxy.execute` returns instead; the step
  carries `Fission180Warning` (the timeline's yellow note).
- A body rolled back by the marker has an empty shape: every reference to its faces becomes
  "?Face6" until the marker passes it again (FreeCAD puts the name back by itself).
- A full circle's edge has one vertex (its seam) and `Closed` is True; a full cylinder's
  face has a seam edge (`edge.isSeam(face)`).
- `freecadcmd script.py` swallows an exception of the script without a line of output: run
  probes through a wrapper that prints `traceback.format_exc()`.
- The harness's `joints_steps.sample` only watches the Joint dialog's animator; the
  as-built dialog's and the standalone one need `book_joints_steps.sample`.

## For the merger

- **Harness**: `Fission180Tests/gui/book_joints_steps.py` has `no_open_step(where)`: it
  checks `App.getActiveTransaction() is None` and `not doc.HasPendingTransaction`. Every
  `book_joints_*` scenario calls it after each dialog (OK, Cancel, Esc, another command, the
  design closed). It could go into `harness.py` and run after every step in which no dialog
  is open.
- **Shared files touched**: `browser_core.py` (one line: "Animate Joint Relationships" in
  `MENUS["joint"]`), `browser_ui.py` (one line: its handler). Nothing else outside the
  joints files.
- `hole_snaps.py` / `hole_snaps_core.py` (joint snap code, but `hole*.py` is the modify
  builder's by the file list) were **not** edited: the keypoint filter and the loop's true
  centre are in `joints._keypoints` / `_true_loop`, on top of `hole_snaps.snaps`.
- Joints now carry `Fission180Rolls`: the timeline greys them after the marker
  (`timeline_ops.rolls_back`). `timeline_ops.py` was not edited.

## Changelog lines

- Editing a joint no longer fails when the design has components and joints made after it:
  the later joints wait, like every later step, while the earlier one is edited.
- A joint dialog that cannot finish now says why next to the mouse, and says so when another
  command cancels it.
- As-built joints and rigid groups keep holding their parts after the parts were moved.
- Joints keep the face or edge they were made on through more edits of the part; a joint
  whose face is really gone says so and keeps its parts in place until you pick it again.
- A round edge or a round face snaps a joint to its centre, wherever you point at it; the
  centre of a threaded hole is on the hole's axis.
- Joint limits have Flip, Preview Motion and With All Limits, as in Fusion.
- A joint with a Rest position goes back to it when you let its part go.
- Motion Link has Link with Same Joint: a cap or a screw that turns as it slides.
- Dragging one bar of a closed linkage moves the whole linkage.
- Animate Joint plays one joint alone; the new Animate Joint Relationships plays it with
  everything connected to it.
- Motion Study shows a graph of each joint over the steps; Enter in its value box sets the
  point instead of closing the dialog.

## Known issues

- While the history marker is rolled back before a joint, the joint does nothing (as in
  Fusion), but its parts stay where the joint put them (Fusion puts them back where they
  were before the joint). They are right again when the marker is rolled forward.
- Flip puts the limits on the other side of the joint's zero. Autodesk's help only says it
  "swaps" them; if Fusion does something else with two limits on, tell us what you see.
- A joint origin cannot be placed on an imported solid that is not in a component; put the
  solid in a component first (Create Components from Bodies), or joint to it directly.
- Motion Study's points cannot be dragged on the graph; click the line, type the value and
  press Enter.
