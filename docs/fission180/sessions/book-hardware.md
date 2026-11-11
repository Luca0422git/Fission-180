### Session log: book-hardware (wave 7, branch `sf/book-hardware`, 2026-11-11)

Written by the hardware builder instead of a MEMORY.md entry (every branch editing MEMORY.md
conflicts at the merge). The behaviour spec with its sources, the families and their
standards, the guesses and the gaps are in `docs/fission180/parity/hardware.md`.

#### The report's items, reproduced first

- **"INSERT > Hardware has only metric screws, nuts, washers, inserts and magnets (no
  O-rings, no inch sizes) ... no set screws or Phillips pan heads"** (Fire Piston 1702, Hot
  End 1943, Tesla 2280, Hilt 2579): reproduced with a probe scenario on develop 3.3.10: Type
  listed Screw / Nut / Washer / Heat-set insert / Magnet, Size M2 - M8.
- **"my attempt to place an M3x20 countersunk screw on the chamfered rim did not pick the
  rim"** (Hot End 1946): reproduced in part. With real input the click that lands on the
  TOP edge of a chamfered rim was taken in 3.3.10 (probe: the screw was placed). A headless
  probe of `hardware.spot()` on the same chamfered hole showed what a click one pixel away
  gets: the chamfer's cone face and the hole's wall were refused with "That face is curved.
  Click a flat face, or the round edge at a hole's opening.", the chamfer's lower edge with
  "That round edge has no flat face beside it." The root cause was the place rule, not the
  mouse: only a round edge with a flat face beside it was a place. A chamfer is a
  millimetre wide on the screen, so "the rim" is the cone or its lower edge as often as
  its top edge. (The report's own diagnosis, "did not pick the rim", was right about the
  effect; the dialog did say why, in its message line.)

#### What Fusion really does (sources in the parity doc)

- Insert McMaster-Carr Component: the supplier's site in a window, STEP or SAT only, the
  part comes in as a component at the origin "automatically set into the move copy
  command" (tutorial excerpt); it is then joined by hand.
- Insert Fastener: a circular edge, a cylindrical or conical face, a sketch point or
  another fastener; Size and Length Auto from the geometry; Select Similar on by default;
  placed with joints that appear in the timeline (one group for several); threads are the
  Thread feature.
- An inserted component is not grounded by "First component Ground to Parent" (that is for
  the first component created).

#### Built

- `hardware_tables.py`: Fission 180's own dimension tables, typed from the public standards
  (51 families' worth: ISO 4762, 7380-1, 10642, 4017, 7045, 1580, 4026 - 4029, 7379, 4032,
  4035, 7040, 7089, 2338; DIN 7984, 127, 471, 472, 6885; ASME B18.3, B18.2.1, B18.2.2,
  B18.6.3, B18.16.6, B18.21.1, B18.27.1, B18.8.2, B17.1; SAE AS568; ISO 15 / ABMA bearings).
  Thread pitches and tap drills are NOT copied: they come from `thread_tables.py`.
- `hardware_core.py` (rewritten): the registry of standards, sizes, lengths, names,
  hole options (inch through `hole_tables`' "ansi" rows, a tapped hole for set screws),
  `seat_in_cone` / `seat_for_hole` (how a head seats in a hole that is there),
  `size_for_hole` for every kind, hand-derived volumes, `search()`.
- `hardware_shapes.py`: the solids; `threaded()` cuts modeled threads with `thread.build`.
- `hardware_place.py`: `spot()` reads the whole hole from any part of it (its "stack" of
  coaxial round faces from the opening inwards), shafts, round edges, flat faces;
  `similar()` finds the holes like it on the same face.
- `hardware.py`: v2 meta (`pick`, `more`, `joints`), occurrences through
  `instances.make_instance`, a Hole step per place (each made on the one before), physical
  material (`material.assign`; "Rubber (NBR)" made once as a user material), `join()` (as-
  built rigid joints, kept when nothing moved), a part at the origin when no place is given.
- `hardware_ui.py`: Search, Units, Thread, Seals, Modeled threads, All holes like it,
  Offset, Rigid joint; a click on one of the screws just placed takes it away; a stray face
  click keeps several filled holes and says what to click; OK with nothing clicked = origin
  + Move.
- `hardware_catalog.py` / `hardware_catalog_ui.py`: INSERT > Insert Catalogue Part...
- `tools/fission180/icons_hardware.py` (icon `catalogue_part`), one ribbon entry.

#### FreeCAD facts and traps

- **A task panel object's attribute named `open` is called by FreeCAD** (the task dialog
  protocol: open / accept / reject / clicked ...). `self.open = QPushButton(...)` made every
  dialog start log "PyCXX: Error creating object of type Callable". Buttons are named
  `open_button` etc.
- **Bounding boxes are loose around a torus and a filleted edge** (`Shape.BoundBox` of an
  O-ring was 8 % too wide, of a pan head 8 % too): measure with
  `shape.optimalBoundingBox(False, False)`.
- **A PartDesign Hole made a moment ago has a null shape until recomputed**: a second hole
  made in the same handler found "no solid to make the hole in". `hardware._hole_base`
  recomputes just that hole and its sketch (`doc.recompute([sketch, hole])`).
- `shape.ancestorsOfType(edge, Part.Face)` gives the faces beside a clicked edge; a face's
  `normalAt` against the direction away from its axis tells a hole's wall from a shaft.
- `insert.design_unit(doc)` does `int(doc.UnitSystem)` on FreeCAD's unit system NAME, so
  it always answers "Millimeter" (not hardware's file: reported). `browser_core.
  doc_length_unit(doc)` is the one that works.
- The MCP extension ships `fission180/ai/` without the rest of the package: the AI
  catalogue cannot import `hardware_core` (its list of standards is typed again, a unit
  test keeps the two alike).
- `thread.build()` on a nut fills the hole down to the thread's minor diameter before it
  cuts the grooves: a nut with modeled threads has MORE material than the plain one.
- The scratchpad folder is shared between builders: another builder overwrote a helper
  script there. Own files go in a folder of their own.

#### Tests

- Unit: `test_hardware_core.py` (76: every table by sample rows and by formula, names,
  search, holes, seats, sizes from holes, volumes), `test_hardware_catalog.py` (13).
- Headless (not in the suite; run by hand): every size of every family at its shortest,
  default and longest length builds one valid solid whose volume equals the formula (1,706
  parts, worst relative error 3e-12).
- Golden: 13 new `hardware_*` models with hand-derived volumes (21 with the old ones).
- Scenarios (real input): `book_hardware_countersunk`, `book_hardware_inch`,
  `book_hardware_oring_bearing`, `book_hardware_holes`, `book_hardware_joint`,
  `book_hardware_catalogue`; the old `hardware_insert` updated for the new names.

#### Gaps

See "Known gaps" in the parity doc: the joint is as-built (it does not follow a hole that
moves inside its component), no hover preview, no sketch point or other fastener as a
place, no dashed helix for cosmetic threads, deleting only the Hardware step leaves its
component, a modeled-thread hole is not read as a hole. The tables were typed from the
standards without a way to open them in the sandbox (search excerpts confirmed three
samples; formulas check every row): a size ordered for real should be checked against the
supplier's sheet.

## Changelog lines

- INSERT > Hardware is now a full standard-parts library, metric and inch: socket head,
  button head, countersunk, low head, hex head and pan head (Phillips and slotted) screws,
  set screws (cup, flat, cone, dog point), shoulder screws, hex / jam / nylon lock nuts,
  flat and split lock washers, O-rings (AS568 dash numbers and metric), ball bearings (60,
  62, 63, 68, 69 series, miniature and inch R sizes; open, shielded or sealed), retaining
  rings (for shafts and bores), dowel pins, keys, standoffs and spacers, besides the
  heat-set inserts and magnets.
- Type what you want into the new Search box of the Hardware dialog ("set screw m3",
  "6202", "o-ring 012", "1/4-20 pan") and click the result.
- A part can be put on any part of a hole now: its rim, its wall, its countersink or the
  chamfer on its rim (a countersunk screw on a chamfered rim was refused before). The part
  takes the hole's size by itself and its head seats in the countersink or counterbore.
- One click fills every hole of the same size on that face ("All holes like it"); the
  parts list then shows one row with the count.
- A bearing clicked into a bore takes the bore's size; clicked on a shaft, the shaft's. A
  retaining ring turns into the shaft or the bore kind by what you click.
- Hardware parts are named like you would order them ("M3 x 20 Countersunk Screw",
  "O-Ring AS568-012"), are made of steel, brass or rubber and so have a mass, and are held
  to the part they were put on by a rigid joint.
- "Modeled threads" in the Hardware dialog cuts the real thread on a screw, a set screw or
  a nut; "Offset" slides a part along its axis (an O-ring into its groove).
- OK in the Hardware dialog without clicking a place puts the part at the origin and opens
  Move, as Fusion's Insert McMaster-Carr Component does.
- New: INSERT > Insert Catalogue Part... opens a supplier's website (McMaster-Carr and
  others, or your own) in your web browser and inserts the STEP file you download there.
- In an inch design the Hardware dialog starts with inch parts.

## Known issues

- A hardware part moves with the part it was put on, but it does not follow its hole when
  you move the hole itself (edit its sketch): double-click the Hardware step and click the
  hole again.
- Deleting only the Hardware step in the timeline leaves an empty component: delete the
  part's component in the browser instead (with several holes filled: each of them).
- A nut cannot be clicked onto a screw: click the face or the round edge it sits on, or
  press OK without a place and move it.
- The thread of a hardware part is not drawn as a dashed line; tick Modeled threads to see
  it.
- The sizes come from the published standards; before ordering parts by a size from the
  dialog, check it against the supplier's own data sheet.
- Insert Catalogue Part cannot show a supplier's catalogue inside Fission 180: it opens in
  your web browser, and the file you download there is what gets inserted.
