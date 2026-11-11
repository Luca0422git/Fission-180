# Session log: replay-f (wave 7's acceptance test, the book's chapter 6)

Builder "replay-f", branch `sf/replay-f`. Brief: `docs/fission180/dev/briefs/book-replay.md`.
Part: Project 14 "Strandbeest", Project 15 "Gear Train", Project 16 "Robotic Hand" (report
lines 2284-2413). Scenarios `replay_14_strandbeest`, `replay_15_gear_train`,
`replay_16_robotic_hand`; shared helpers `Fission180Tests/gui/replay_f_steps.py`.

Every replay starts from Home > New Design with a person's defaults (first component
grounded, full grid snap, scale at first dimension, layout grid: `replay_f_steps.user_defaults`)
and fails on an undo step left open (`h.STRICT["undo"]`).

## Project 14: Strandbeest (`replay_14_strandbeest`, 255 checks, PASS)

The report built "a 4-bar slice of the leg" and gives only a few values (pins extruded -6,
the crank 15 between centres, Width=5mm, links -2 thick). The replay builds that slice to
those values and, for the rest, to a stand-in that closes exactly: pins 3 across and 40
apart, the rocker 30, the coupler from the crank's hole to the rocker's (about 35), on a
second layer (Extrude, Start > Offset). Steps, in the report's order: Change Active Units
(mm, not as default); Pins (2 circles, Equal, dimensions, Extrude -6: two bodies, towards
the viewer of the front view); the three-dot options (Shift+S for Center to Center Slot,
Override); A Link (slot started on the pin, aligned 15, `Width=5mm`, a hole, `Thickness=-2mm`
in Extrude: New Body, the pin not cut); the ABS look found with the search; DGF Plate (slot
started on the second pin's centre, another component's); B Link (slot from hole centre to
hole centre, Start > Offset); three As-built Revolute joints; Joint (J) closing the loop;
the crank dragged (the loop follows, one undo step); Animate Joint and Animate Joint
Relationships; Drive Joints; save, close, reopen.

### Hitches found and fixed

| # | Report line | What happened | Fusion (source) | Root cause | Fix (function) |
|---|---|---|---|---|---|
| 1 | 2313-2315 "Typing Width=5mm into the slot-width dimension box does not create a parameter" | In the slot tool's width box the letters ran as keys: W nothing, i Measure, d Sketch Dimension (the slot tool ended), t Trim, h Hole (left the sketch). No slot, no parameter | While a value box is shown the keys go to it, letters too: Autodesk's lesson "Create parameter based sketches" types `L1=20` into the rectangle's box (Autodesk) | `sketch_draw.Boxes.starts_name` took a letter into an empty box only when an EXISTING parameter starts with it | `sketch_draw.Boxes.starts_name` now takes any letter or `_` (rule: `sketch_draw_core.letter_starts_name`, unit tested) |
| 2 | 2308-2310 "The slot's first click cannot snap to the Pin's centre (other component's sketch/body)" | A click on the middle of the second pin's end landed on the X axis only, 0.018 mm beside the pin's axis | Fusion snaps to the centre of a round edge of the model and projects it (Auto project edges on reference; Autodesk forum, as in `sketch_reference.py`'s notes); the centre POINT is projected, so no hole appears (Guess from the report's own "it overlapped the Pin body") | `sketch_reference.element_under` only knew edges and corners under the pointer; a face (the pin's end) or a hole (nothing under the pointer) gave nothing | `sketch_reference.round_centre_under` (+ `_centre_of`, `_place_of`, `_name_of`, class `Centre`): the round edge whose centre is under the pointer (an edge of the flat face there, or the rim of a hole of a solid on show, parallel to the sketch) is projected as a reference that bounds no profile; `project_under` handles `Centre`. Rule `sketch_infer_core.nearest_within`, unit tested |
| 3 | 2325-2328 "Joint (J) to close the loop: hovering picks the wrong one ... OK was refused" | On the round end of a link the rim's centre was lit, the click took the END of the arc: the coupler jumped, the loop broke | The dot that is lit is the one a click takes (Autodesk help, Joint: "select a snap point") | The hover looks a few pixels around the pointer for an edge (so the rim was "under" it); FreeCAD's selection of the same click was the wall next to the rim; `SnapHover.snap_for` then took the candidate nearest in space | `joints_ui.SnapHover.snap_for`, `_pressed_where_lit`, `_button`, `_update`: a click that comes down on the pixel the lit dot was chosen for takes that dot. Rule `hole_snaps_core.same_pixel`, unit tested |
| 4 | (not in the report) | With both snaps picked and the Type still Rigid, FreeCAD's solver wrote "<Assembly> AssemblyObject.cpp(170): Solve failed: iterNo > iterMax" and "vector::_M_range_check: __n (which is 84) >= this->size()" in red into the Report view | Fusion never shows solver internals (friction pattern 6, "FreeCAD shows through") | `joints._run_solver` let FreeCAD's console lines through | `joints._run_solver` runs `asm.solve()` inside `preview.quiet()`; the code is explained by the dialogs as before |

### Report items that simply work now (kept in the replay)

Units for this design only; Equal; "-6 towards you" (y -6..0 on the Front plane); the
three-dot options and Override; the aligned dimension of the slot's centre line (a
`Distance`, not `DistanceX`); bug 10 (New Body proposed although the profile lies on a pin
of another component; the pins are not cut); Start > Offset for the second layer; the
As-built joints; the loop following a drag; the two animations as separate commands; the
ABS look and the search.


## Project 15: Gear Train (`replay_15_gear_train`, 158 checks, PASS)

The report tested "key tools only". The replay does every step it names, with its values,
and goes on to what it left "Not tested" (the copy/paste train and its motion link), on a
stand-in frame: two axles 4 across and 90 apart (the pitch radii 75 + 15). Steps: Axles
(2 circles, Equal, dimensions, Extrude 16); UTILITIES > Scripts and Add-Ins > SpurGear >
Run: 20 teeth, module 1.5, root fillet 0.88, 8 thick, hole 4 (pitch diameter 30); SpurGear
again: 100 teeth, 4 thick, the same 0.88 (pitch diameter 150); Gear 2 > Edit Feature,
Cancel; M, Move Object Components, the 20 tooth gear: Z 4 and Z Angle `360/20/2`; New
Component "Compound Gear", both gears dragged onto its row; Compound Gear copied and pasted,
X 90 and Z 4 typed; as-built Revolute joints of each compound gear on its axle; Motion Link
360 : 72 with Reverse, Animate; Animate Joint Relationships; Drive Joints 100 (the second
gear at -20); save, close, reopen.

### Hitches found and fixed

| # | Report line | What happened | Fusion (source) | Root cause | Fix (function) |
|---|---|---|---|---|---|
| 1 | 2349-2352 bug 19 "100-tooth gear with the book's 0.88 mm root fillet: the dialog warns ... at most 0.741 mm" | Refused; with 0.5 it worked | Autodesk's own SpurGear sample refuses a root fillet only above `toothThickness * .4` (0.4 x pi m cos(alpha) / 2 = 0.8857 mm for m 1.5, 20 deg, whatever the teeth); it fillets one tooth and patterns it, so neighbouring fillets cross on many teeth (Autodesk: the sample's code, as the gear parity notes quote; Book: 0.88 for both gears) | `gear_core.max_fillet` required a flat land between two fillets | `gear_core._involute` (`crossing_fillets`, third return value), `_fillet_crossing`, `fusion_max_fillet`, `_circular`, `_check_lands`, `max_fillet`: up to Fusion's limit each fillet runs to the middle of the gap. Unit tests in `test_gear_core.py`; `book_modify_gear` updated (its refusal step now types 0.89, its gear uses the book's 0.88) |
| 2 | 2357-2359 "The 2nd gear's New Component was created INSIDE the first gear's component (it was left active)" | Reproduced | Fusion's sample adds its component to the design's root (`rootComponent.occurrences.addNewComponent`) and leaves the active component alone (Autodesk: sample code) | The Gear dialog put a New Component under the active component, which the first gear's OK had activated | `gear_ui.GearPanel.__init__`, `_sample_to_root`, `_restore_active`, `reject`, `accept`, `_auto`; `samples/SpurGear.py`: started from the sample the dialog proposes New Component, at the root, and puts the active component back. CREATE > Gear is unchanged |
| 3 | (not in the report) | The Scripts and Add-Ins window stayed open over the design after Run; the next key (M) went to its Create button | Fusion's window closes when a script is run (Guess, from use) | `scripts_ui.ScriptsDialog.run_selected` kept it open | It closes after a script ran (an add-in keeps it open) |
| 4 | (not in the report) | New Component as the first command of a new design ticked From Bodies and said "1 body will move into the new component: Body1" | Fusion has no body before the first solid | The new design's own empty Body1 stays selected; `_whole_bodies` took it | `components_ui.NewComponentPanel._whole_bodies`: a body without a solid is not taken |
| 5 | 2363-2364 "the rotation pivot was ~0.003 mm off the origin" | The second gear, its centre clicked on the origin, landed 0.026 mm off it (on the centre of one of the first gear's tooth-tip arcs) | Fusion snaps to the origin | `primitives_core.nearest_snap` took the nearest of a cloud of snap points a hair apart | `primitives_core.nearest_snap` (`SAME_SPOT`): points within two pixels of the nearest are one spot, the first listed (the origin) wins. Unit test |
| 6 | (not in the report) | A pasted copy's shape held its original's solids too (it "ran into" everything) | - | `joints.part_shape` walked `OutListRecursive`, which reaches the original through the copy's links | `joints.part_shape` / `_inside`: only what lies inside the part |
| 7 | (not in the report) | The second compound gear's joint: "Pick the position on one of the two components" on its pinion's hole | Fusion takes the joint's snap point on any geometry of the two chosen occurrences | `AsBuiltPanel.allow_pick` / `picked_raw` took only bodies directly in a chosen component | `joints_ui.AsBuiltPanel.allow_pick`, `_chosen_part`, `picked_raw` |

### Report items that simply work now (kept in the replay)

The SpurGear entry in Scripts and Add-Ins; component names "Spur Gear (N teeth)"; Edit
Feature on Gear 2 (bug 20); `360/20/2` in Move; the move about the component's origin
(the gear's hole stays exactly on the origin's axis); two drags into Compound Gear; Copy /
Paste keeping the copied component's place; Motion Link with the gear ratio and Reverse;
Animate Joint Relationships.

Not replayed (and why): Split Body with a sketch curve and the auto-project warning (the
report says it worked; time went to the train); the eleven-gear train (two compound gears
test the same tools: paste, joint, link).

## Project 16: Robotic Hand (`replay_16_robotic_hand`, 234 checks, PASS)

The report tested "key tools only" and gives no dimensions of the hand (its ellipses,
splines and loft with rails were not re-tested), so the hand is a stand-in to the chapter's
tools: a Palm 70 x 20 x 10 with a 6 mm hole; a Finger subassembly of two phalanges 10 x 30
x 10 (Proximal, Distal), each a New Component inside the Finger. Steps: Palm (rectangle, two
dimensions, a circle, Extrude 10); Finger, Proximal, Distal; As-built Revolute knuckles
(Finger + Palm, Distal + Proximal) with Minimum / Maximum typed in the dialog; Edit Joint
Limits on the first (-60 .. 60); Drive Joints 45, then 80 (stops at 60); Rectangular
Pattern, Pattern Type Components, of the Finger subassembly: 4 fingers; the second knuckle
driven: every finger bends; Copy, Paste New (the thumb), Move Z 90 / X 20; Mirror of the
thumb subassembly across the palm's end face; Circular Pattern of it about Z, then Ctrl+Z;
New Contact Set (Finger + Palm), Enable Contact Sets, Drive Joints into the palm stops at
the touch and says so, the other way is free; Disable Contact; Motion Study over both
knuckles (points set with Enter, the graph, Play, OK, Edit Motion Study); a component Axle
holding only an Axis Through Cylinder of the palm's hole; save, close, reopen.

### Hitches found and fixed

| # | Report line | What happened | Fusion (source) | Root cause | Fix (function) |
|---|---|---|---|---|---|
| 1 | 2398-2402 "Rectangular Pattern of a subassembly with its joints could not be done ... the 4-finger pattern with inherited links/limits fails" | The pattern itself works now; but afterwards the first knuckle was re-pointed from the Finger to its Proximal (grounded to the Finger), and with contact sets on: "Proximal and Palm are both grounded: unground one to drive Revolute 1" | A joint stays on the occurrences it was made between (Autodesk help, Joint) | `joints.reroot` (run when a component's Group changes, as a pattern does) moved every reference down to the nearest part of the face, also a deliberate reference into a subassembly | `joints._rerooted`: a reference whose path names the nested component stays on its part. `joints_components`, `book_joints_survive`, `bodies_qa_2` still pass |
| 2 | (not in the report) | A mirrored copy of the thumb measured 12000 mm3 for 6000 | - | `joints.part_shape` counted an instance's copy feature and the copy body made from it | `joints.part_shape`, `_is_copy_feature` |
| 3 | (not in the report) | After Rectangular Pattern, Paste New and Mirror, CREATE > Pattern had vanished from the menu (no Circular Pattern) | - | A submenu that nothing on the Python side held was deleted by a garbage collection (proved: a forced `gc.collect()` removed it at once; kept, it stays) | `ribbon_ui.build_menu`: submenus kept with their menu (`_sf_submenus`) |
| 4 | (not in the report) | After Motion Study > Play > OK, the original finger was straight and its three copies stayed bent (the copies lag one move behind their source) | Every occurrence of a component shows the same joints (Fusion) | The study moves parts without a recompute; copies follow only at the next one | `instances.follow`; `joints_motion_ui.MotionStudyPanel._pose`, `before_close`, `_copies_follow` |

### Report items that simply work now (kept in the replay)

New Component inside the active one (Fusion's way); joint limits set in the As-built
dialog; Edit Joint Limits on an as-built joint (the report: "broken"); Drive Joints stopping
at a limit; Rectangular, Circular Pattern and Mirror of components and of subassemblies
with Pattern Type Components; Paste New (an independent copy); Contact Sets stopping a
drive and saying why; Motion Study's graph, Enter that sets a point and keeps the dialog;
an axis made in the active component (the report's "Bug" with Axis Through Cylinder).

Not replayed: Ellipse, Fit Point Spline, Loft with Rails and Hole Extent All (the report
did not re-test them and gives no shapes; they have their own scenarios).

## Tests

- Replays: `replay_14_strandbeest` 255, `replay_15_gear_train` 158, `replay_16_robotic_hand`
  234 checks, all PASS on the final commit.
- Unit: 3692 tests, one failure, the known `test_vex_qa_freecad` "parts_list_assembly_twice"
  (another builder's). New tests: `test_sketch_draw_core.ValueBoxKeys`,
  `test_book_sketch_c.RoundEdgeCentre`, `test_hole_snaps_core.ClickWhereLit`,
  `test_gear_core` (4 new, one limit updated: 1.146 -> 1.18),
  `test_primitives_core.test_snap_points_on_one_spot_give_the_first_listed`.
- Golden: 649 pass, 2 known xfail.
- Older scenarios of the changed functions, all PASS: book_sketch_c_names, sketch_tools_slots,
  sketch_tools_circles, sketch_tools_draw, sketch_tools_modify, sketch_tools_project,
  book_params_sketch, book_sketch_a_shapes, book_sketch_c_reference,
  book_sketch_b_dimension_edge, book_joints_snap, book_joints_limits, book_joints_edit,
  book_joints_motion, book_joints_study, book_joints_survive, joints_components,
  joints2_motion, book_components_nested, book_components_new, book_components_pattern,
  components2_pattern, book_modifyc_mirror_assembly, book_components_move,
  book_components2_structure, bodies_qa_2, book_shell_dialogs, book_shell_ribbon,
  ribbon_customize, misc_scripts (changed, below), gear_spur, gear_types, gear_refuse,
  book_modify_gear (changed), book_modify_edit_feature, primitives_qa, primitives_box,
  book_extrude_primitives, book_components_primitive.
- Changed older scenarios: `book_modify_gear` (Fusion's root fillet limit: the book's 0.88
  is made for 100 teeth, the refusal is tested with 0.89); `misc_scripts` P2 (the window
  closes once a script ran, Fusion's way).
- `joints2_slider` fails at S5 (the wall, made with Create Components from Bodies, is the
  design's first component and so grounded by `components_ui.ground_first`; a drag of it is
  refused). None of my changes touch that path: it comes from the first-component rule of
  wave 7 (the harness does not switch "FirstComponentGrounded" off for older scenarios,
  although book_components_new's notes say it does). For the components builder.

## Notes for other builders (not changed by me)

- FreeCAD's own Line / Circle / Rectangle boxes (`sketch_field_names.FieldNames.wants`)
  still take a first letter only when an existing parameter starts with it
  (`book_sketch_c_names` step E tests that `c` starts the Circle tool). By Autodesk's
  lesson (`L1=20` typed into the rectangle's box) Fusion sends that letter to the box too.
  Left alone: it is the sketch builders' file and their check.
- A circle's rim clicked at a grid crossing ON an axis keeps the pointer's own position
  along the axis (radius 4.955 instead of 5): the axis wins over the grid crossing
  (`sketch_infer`). Harmless here (the circle is dimensioned next).
- In Joint (J), with both snaps picked and the Type still Rigid, the preview across a
  closed loop cannot be solved and the dialog says nothing until the Type is chosen
  (Revolute: fine).
- The first component made inside another (Proximal inside Finger) is grounded to its
  parent (components builder: "the first of its level"). Fusion's preference speaks of
  the design's first component; worth a check by the components builder.
- Other places that move parts without a recompute (a joint's Animate, Animation's
  playback) may show the same lag of instance copies as Motion Study did; not checked.

## Changelog lines

- Typing a new name with its value into a sketch tool's value box (`Width=5mm` for a slot's
  width) makes that parameter; before, the letters ran as keyboard shortcuts.
- While sketching, a click on the middle of a round end (a pin) or in the middle of a hole
  of another part lands exactly on its centre and stays tied to it.
- In Joint and As-built Joint, the dot that is lit under the pointer is always the one a
  click takes (on a link's round end the click sometimes took the end of the arc instead).
- FreeCAD's own "Solve failed" lines no longer appear in the Report view when a joint that
  cannot hold is being previewed.
- The Gear tool takes root fillets as large as Fusion's Spur Gear does (the book's 0.88 mm
  on a 100 tooth gear); neighbouring fillets then meet in the middle of the gap.
- Spur Gear from Scripts and Add-Ins makes each gear a new component of its own at the top
  of the design, whichever component is active, and the window closes when a script runs.
- A gear (or a box, a cylinder...) placed on the origin lands exactly on it, also beside
  another gear.
- New Component as the first command of a new design no longer offers to move the design's
  empty body.
- A joint of a subassembly can be placed on any part inside it, and stays on the
  subassembly after a pattern of it.
- CREATE > Pattern no longer disappears from the menu after some commands.
- After a Motion Study, every copy of a patterned subassembly is back in place with its
  original.

## Known issues

- In the Line, Circle and Rectangle tools a NEW parameter's name must start with "=" in the
  value box (`=Width=5mm` is not taken either: make the parameter first, or use Sketch
  Dimension, whose box takes `Width=5mm`). Fission 180's own tools (slots, 2-point circle,
  polygons, arcs) take `Width=5mm` directly.
- A link whose slot starts on a pin's centre lies ON the pin (no hole is made there), as in
  Fusion; draw a circle for the hole if you want one.
- A part inside a copy of a subassembly cannot be jointed on its own: the copies show the
  original's joints (as the components builder noted).
