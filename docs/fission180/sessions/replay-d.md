# Session log: replay-d (wave 7, the acceptance test: chapter 4 of the book)

Builder "replay-d", branch `sf/replay-d` (from develop 39fd9e9b). Brief:
`docs/fission180/dev/briefs/book-replay.md`. Part of the book: Chapter 4, Project 10 "Fire
Piston" and Project 11 "3D Printer Hot End" (report lines 1637-1949).

## What was built

- `Fission180Tests/gui/scenarios/replay_10_fire_piston.py` with its steps in
  `Fission180Tests/gui/replay_10_steps.py` and the shared helpers in
  `Fission180Tests/gui/replay_d_steps.py`: the Fire Piston from Change Active Units to the
  last joint in ONE design, by real input, with a user's defaults (first component grounded,
  full grid snap, scale at first dimension, layout grid on) and an open undo step a failure.
- The book's figures are not in the repository: every profile is a stand-in drawn to the
  numbers the report quotes from the book (4, 0.5, 0.70/2, 25/64/2, 0.35/2, 3/32, 0.02, the
  coil's 0.70 / 1.5 / -3 / 0.02, R0.04, 0.465, 5/32 ...). The report's line is named at each
  step.
- Development aid in `replay_d_steps.stages`: `REPLAY_D_SAVE=<folder>` saves a copy of the
  design after each stage, `REPLAY_D_FROM=<stage>` starts from the copy saved before a stage.
  The test runner never sets them; a full run is always from the first step.

## Hitches found and fixed

| Report line | What happened in the replay | Fusion | Root cause | Fix (function) |
|---|---|---|---|---|
| 1675 (chamfer sets after the modeled thread) | Set 2 (outer rim + the left end FACE, whose inner rim is the threaded hole's mouth): after each pick the dialog was busy for 8 - 25 s, and the 0.02 typed right after the face click took 9 s to arrive (one trial build ran between every two keys) | The picks and the typed size are taken at once (Guess: no source says how long Fusion takes; it never blocks typing) | (1) `value_limits.Background` ran one trial build per turn of the event loop also while the person typed; (2) `fillet_robust._clean` kept its verdict in the per-part table, the tables of part-way solids pushed the part's own out (4 are kept), and OpenCASCADE's `check` (2 - 5 s on a modeled thread) ran again at every second trial | `value_limits.Background._watch_input / _typing / _waits` (no build for 0.4 s after a key, a press, a drag move); `fillet_robust._clean` (own cache `_STATE["clean"]`, 6 parts) |
| 1716 (Joint: "the O-ring landed off-axis") | J, the pointer on the O-ring: the lit snap was "circle" at 5.5 mm from the ring's axis: the centre of the ring's cross-section circle (the seam of its round face), a point inside the rubber | Fusion offers the centre of the ring (Guess from the book's step: "select the O-ring", then the cap; the ring lands on the axis) | `joints._face_keypoints` / `_edge_keypoints` offered the centre of every circular edge of a face; a torus has a seam circle that is its cross-section. `_face_frame` asked for "Part::GeomTorus"; FreeCAD's name is "Part::GeomToroid" | `joints._face_keypoints` (no off-axis circle centres on a ring), `joints._edge_keypoints` + new `_ring_of`, `_off_axis` (the seam circle offers the ring's centre), `joints._face_frame` (a whole ring: centre and axis) |

## Hitches found and NOT fixed

- **Construction planes are drawn as large as the whole part.** The Offset Plane 0.5 in inside
  the Piston Body is drawn 38 mm square (FreeCAD's automatic size: the body's box plus a
  tenth of its longest side, here the 4 in length); Fusion draws it as large as the face it
  came from (18 mm). From the home view it lies, see-through, in front of the End Cap's
  shank, and J on the shank's end face takes the plane ("origin"): the O-ring jumped into
  the Piston Body. The replay clicks the eye of the Construction folder first, as the
  report's tester hid parts for the picks (line 1720). What it would take: size the plane to
  its face in `construct.update` (ResizeMode Manual, Length / Width from the face) and re-run
  the 32 scenarios that use offset planes (several click a plane where it shows).

## Things learned (FreeCAD / harness facts)

- `Shape.BoundBox` of a part with a modeled thread is larger than the part (it counts the
  hidden ends of the swept faces): use `optimalBoundingBox(False, False)` in checks.
- A click that lands on a dialog's floating value box is taken by the box (as in Fusion): the
  replay clicks a rim clear of it (`replay_d_steps.click_rim`).
- After a design is saved, closed and opened, the design's row is active; Revolve then says
  "Revolve needs a sketch: use Create Sketch first" although a component holds an unused
  sketch (`commands.find_body` finds no body at the root). Not on the book's path; not fixed.

## Changelog lines

- Typing a size right after clicking an edge or face in Fillet or Chamfer no longer waits
  behind the search for the largest size that fits.
- A chamfer or fillet on a part with a modeled thread previews faster: the part is checked
  once, not at every try.
- A Joint clicked on an O-ring now takes the centre of the ring, on its axis; it could take a
  point inside the rubber and put the ring off-centre.

## Known issues

- A construction plane is drawn as large as its whole part, not as its face: hide it (the
  eye of the Construction folder) when it lies in front of something you want to click.
- A fillet or chamfer on the end face of a threaded hole still takes a second or two per
  preview.
