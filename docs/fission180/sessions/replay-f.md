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

### Notes for other builders (not changed by me)

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

## Changelog lines

- Typing a new name with its value into a sketch tool's value box (`Width=5mm` for a slot's
  width) makes that parameter; before, the letters ran as keyboard shortcuts.
- While sketching, a click on the middle of a round end (a pin) or in the middle of a hole
  of another part lands exactly on its centre and stays tied to it.
- In Joint and As-built Joint, the dot that is lit under the pointer is always the one a
  click takes (on a link's round end the click sometimes took the end of the arc instead).
- FreeCAD's own "Solve failed" lines no longer appear in the Report view when a joint that
  cannot hold is being previewed.

## Known issues

- In the Line, Circle and Rectangle tools a NEW parameter's name must start with "=" in the
  value box (`=Width=5mm` is not taken either: make the parameter first, or use Sketch
  Dimension, whose box takes `Width=5mm`). Fission 180's own tools (slots, 2-point circle,
  polygons, arcs) take `Width=5mm` directly.
- A link whose slot starts on a pin's centre lies ON the pin (no hole is made there), as in
  Fusion; draw a circle for the hole if you want one.
