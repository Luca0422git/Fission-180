# Wave 7 builder "modify-b": fillet / chamfer robustness, thread, draft (branch `sf/book-modify-b`, 2026-11-11)

Takes over three open items of builder "modify" (`sessions/book-modify.md`): every fillet /
chamfer entry of the book parity report with the book's value, the modeled thread's faces and
Offset Face on a thread, the Draft dialog. Everything was reproduced in real FreeCAD 1.1.4
before it was changed: kernel probes headless (`.probe/`, not committed) and GUI scenarios
with real input.

## Item 1: fillets and chamfers

### The Tensegrity Tower (report lines 1048-1137)

**The book's part, rebuilt.** The report's step list gives it exactly: hexagon 100 mm across
corners, six triangles 6 mm from the edge and 3 mm from the spoke lines, four 3.5 mm holes,
6 mm thick: 18,376.1 mm3 (the report: 18,376). The arm: dimensions 6 (between the two leaning
lines), 10 (flat top), 6 (drop), 75 (height). 10 sin - 6 cos = 6 gives sin = 15/17, cos =
8/17 (an 8-15-17 triangle, 61.93 degrees), and a foot of 6 / sin = 6.8 mm: the report's driven
"(6.8 mm)" dimension. The foot's midpoint is over the origin (the report's Point + Vertical).

**"20 mm does not fit: limited to 1.79 mm": reproduced, to the digit.** The arm's foot is at
x = 3.4; the frame's top face narrows to the 6 mm spoke at x = 5.196 (the pockets' corners):
5.196 - 3.4 = 1.796. So it was not a cautious limit of Fission 180: OpenCASCADE's chamfer
(`makeChamfer`) is valid up to 1.79 and gives an invalid solid or fails from 1.8 on, because
its bevel face would have to go on along the spoke's edges. `book_modifyb_tensegrity` run
with `FISSION180_BOOK_BEFORE=1` shows the report's words.

**Fix: `fillet_section.py`.** The bevel is plain geometry: a triangle (20 mm along each face)
swept along the 6 mm edge, added to the part (an inside corner) or cut away (an outside
edge). Built for straight edges between flat faces and circles between faces turned about
the circle's axis, chains of them, constant size; the open ends are cut off by the flat
faces that meet the edge there. It only builds when both landing strips lie on the edge's own
two faces (probed at 28 points per face), the result is one sound solid and the volume
changed by the section's area times the length. 20 mm: +1058.82 mm3 = 20 * 20 * sin / 2 * 6.
Up to 46.6 mm (the hexagon's corner) builds; beyond it nothing is under the bevel: refused.

**"Chamfer 0.5 mm on all of them: too big; 0.3 and 0.2 too": reproduced, two causes.**
1. The report's part had its 1.79 mm chamfer, whose foot ends 0.006 mm from the pocket's
   corner: no bevel fits past that point at any size (2 of 102 edges in the way). With the
   book's 20 mm chamfer the kernel bevels all 98 sharp edges in one run (1 s).
2. The window drag takes what the view shows: 15 faces and 53 edges, 72 of the 98 sharp
   edges. On that pick OpenCASCADE fails at every size (and takes 8 to 18 s to hand back an
   invalid solid): at the hidden ends of the pockets' corners a filled inside corner and a
   bevelled outside edge meet at a point whose third edge is not picked.
   **Fix: `fillet_robust._in_turn`**: such a group is built in two runs, the inside corners
   first, then the outside edges on what that left, plus the new rim edges on top of a filled
   corner that join two picked rim edges (`_bridges`), so the bevel goes round a fully
   picked corner as one run's does. On an L block (inside corner + one top edge) the result
   differs from OpenCASCADE's one run by 0.08 mm3 at 0.5 mm (its corner patch is a B-spline
   face; the two runs give flat faces).

**What Fusion does.** The book expects both steps to work (Book). Autodesk's help on
selection filters: "Select Through: selects hidden objects in Window or Freeform selection";
an Autodesk engineer on the forum ("Can't select edges and vertices with window selection"):
a window drag outside a command takes no edges, only inside Fillet / Chamfer. So in Fusion the
window pick of the whole model is every face (hidden ones too), and the chamfer gets every
edge. **For shell** (`selection_core.DEFAULT_SELECT_THROUGH`, their parity doc marks "off" as
a Guess): the book's step only gives "every edge" with Select Through on from the start.
Not changed here (their file, their scenarios). With it on the chamfer takes 1 s; with it
off it now builds the visible edges in about 6 s.

### Refusals come quickly (`fillet_robust.first`)

OpenCASCADE takes 2 to 18 s to fail on some picks, and the dialog's search for the largest
size that fits asks for many sizes (the report's "20 s of frozen app"). Asked BEFORE the
kernel's one run now:
- what was built or refused for this very blend a moment ago (preview, the step, OK);
- `fillet_section.misses`: across the middle of the edge, a point of the strip the blend
  would cover lies off the face and the face ends there in a sharp edge (a wall, a hole's
  rim, the face's end). Probe `.probe/landhole.py`: OpenCASCADE builds no such blend (it
  fails or returns an invalid solid). Refused at once, with its own words;
- the group that was in the way at the last size is built alone first;
- a pick with a "mixed open corner" goes group by group straight away.
The window pick on the Tensegrity: 20 mm refused in 1.0 s (was 17 s), 5 mm in 0.8 s.
`fillet_sets.kernel` no longer hands on a solid that is not valid.

### Found on the way

- **A size held at its limit without a word** when another route than the kernel's one run
  builds it: the limit note's key held `_uses_step()` and the set's pick `count`, both of
  which change the moment Fission 180's own step takes over, so "50 mm does not fit: limited
  to 6 mm" was dropped as made for other inputs. Fixed in `fillet_ui._limit_key`.
- `kernel_once` built `shape.Edges` once per picked edge (FreeCAD makes the list anew each
  time): 1 s of a 72-edge chamfer.

### The Carabiner (report lines 1189-1192)

"Fillet top face + chamfer's top edges at 4 mm: silently capped to 3.99 mm". The book's part
is an 8 x 8 section swept round a closed outline; two 4 mm rounds use up the 8 mm top face
exactly. OpenCASCADE fails at 4.0 and builds 3.99 (the first builder's finding). The section
route builds the second round where the first one left exactly its width of face: lines and
arcs of the outline as one chain (extrusions and revolutions of the same section). Probe: on
the ring with its 2 mm bottom chamfer, 4 mm on the top face's two loops and the chamfer's two
top loops builds in 1.9 s, valid, no flat face left on top. `book_modifyb_carabiner` (22
checks). `book_modify_fillet_limit_note` (the first builder's) now expects 4 mm to build on
its bar and checks the "held and said" rule with 5 mm (held at 4.00) and with the top face
picked whole (its short end edges with it: three rounds meet in a ball corner there, which
the section route does not build: held just under 4, and said).

### The Tesla Turbine's housing (report lines 2147-2185)

The report gives the ring's bore (9 * 1.02 = 9.18 in), its thickness (2.25 in) and the
0.84 in hole 4.17 in up (it touches the bore at its top: 4.17 + 0.42 = 4.59), but neither the
ring's outside nor the inlet tube's size, and a web search did not turn up the book's
numbers. The part was built by the book's steps (ring, hole, tube revolved about the hole's
line and joined, bore cut again) in three shapes the tube can have:

| tube | 0.25 in fillet at the junction | 0.04 in chamfer on the two flat faces |
|---|---|---|
| thinner than the ring's wall (ring 11, tube 1.25) | builds (one run) | builds (one run) |
| its top level with the ring's (ring 10, tube 1.66): the two cylinders touch at the top, the junction is one closed edge through that point | OpenCASCADE fails at every size, after 3 to 9 s (25 s with the retries). **Refused at once now**, with its own words ("at one end the two faces run into each other smoothly ... no corner left for a round to end in"), no limit search | builds |
| wider than the ring (ring 11, tube 2.6): the tube cuts through the flat faces, which is what the report's "(even without the tube edge)" says its part was like | fails: 1 of the 3 junction edges; refused in 1.4 s naming it | failed at every size, single edges too; **builds now** ("tolerance") |

Root cause of the third row: the part itself. `shape.check(True)` (OpenCASCADE's check for
booleans) reports "BOPAlgo_InvalidCurveOnSurface" on the Revolution's join and on the bore's
second cut: edges that do not lie on their faces within tolerance (2.4e-4 mm), left by
booleans of faces that touch along a line (the hole on the bore; the tube's bore on the
hole). `isValid()` still says True. `fix()`, `removeSplitter()`, `sewShape()`,
`limitTolerance()` do not mend it; `fixTolerance(0.001)` on a copy does for the chamfer
(`fillet_robust._loosened`). Building faces again from surface + 3D curves crashed FreeCAD
(`Face.validate()` segfault): not used. **Open:** the junction fillet on rows 2 and 3. Row 2
needs a rolling-ball surface that fades out at the tangent point (not built; nothing in
OpenCASCADE's fillet does it); row 3 needs the Revolution / Pocket steps (FreeCAD's C++, the
extrude builder's area) to leave a clean part.

### The Drone (report line 1578) and the Pizza Cutter (line 2071)

- Drone, "window drag + Chamfer 0.25 mm: too big, also 0.1": the same pick as the
  Tensegrity's (a plate with pockets, the edges the view shows), which now builds. The
  report's own diagnosis (micro-edges of drifting pattern copies) could not be checked: the
  frame's sketch is not in the report in enough detail to rebuild. The first builder's
  stand-in with 0.5 micrometre steps is still refused, now saying why ("on 20 of the 116
  edges the bevel would run past the end of a face next to the edge").
- Pizza Cutter, "Fillet 0.02 in on the flat face that also has the threaded countersink
  edge": not reproduced. A block with a countersunk 1/4-20 hole (tapped, modeled or plain) and
  the face's five edges filleted 0.508 mm builds in one run in all four variants.
- Hot End: the book itself rolls back before the threads to chamfer (Fusion refuses a
  chamfer on a threaded hole): nothing to fix.

## Item 2: the modeled thread

**Faces (measured, not changed).** One helix edge per turn gives one flank / root face per
turn: 21 faces on M33x3.5 x 16 (the report's "19 B-spline faces" are the thread's own), 41
on x 40, 97 on M6 x 30. Tried: (1) `Part.makeHelix` (one edge for the whole length) and
(2) the one-turn sweep's four B-spline patches repeated along the helix into ONE surface per
flank (poles moved up one pitch per turn; the tool is valid and closed in 0.2 s). Both give
Fusion's count (3 B-spline faces + the crest + 2 ends). But OpenCASCADE's booleans misjudge
such a tool: of 12 cuts (4 sizes, the shaft's seam turned, with and without the trimming
cylinder) 5 were wrong (nothing cut, or the whole shaft gone), and (1) is 2 % off in volume
on 32 turns. Kept as it is. Times are the same either way (2.5 s for M33 x 16, 9.5 s for
M6 x 30: the cut, not the sweep).

**Offset Face on the thread (built).** The report's entry reproduced by reading the code
path: a click on a thread face went to `core.match_pick` against the step before, found
nothing, and Offset Face's WIP note was all the dialog said. Now `presspull_ui._start_thread_edit`
(the thread branch only; the file is not this builder's) takes the Thread step, and
`thread.parts(face_offset=...)` moves every face: `thread_core.moved_groove` (each side of the
groove polygon moved square to itself) and `fitted_groove` (its open side put back past the
crest, never a pitch wide). -0.25 mm on M33x3.5 x 16 removes 614.9 mm3; the faces' area
times 0.25 is 622. +0.5 / -0.5 are refused with the reason.

## Item 3: Draft (report lines 1226-1230, 1263)

Reproduced with a probe that became `book_modifyb_draft`: with the Faces box active, a
click on the pull direction's own face (it is shown selected) dropped the pull direction and
made Pull Direction the active box; the next face clicked then became the pull direction.
That is the report's "a face sometimes did nothing" and "cleared the pull direction". A
refused OK alone does not clear it (checked). Fixed in `draft_ui.picks_changed`; the reason
is said next to the pointer. "Some of my clicks toggled faces off" is Fusion's own rule.

## The regression in Auto Timeline (orchestrator, mid-session)

"rebuild e2e" failed 3 checks on the part "threaded" after the first builder's thread work.
Cause: a threaded hole's bore is left in helical strips (the hole is brought to the minor
diameter) and `recognize._hole_void` added each strip up as a whole cylinder. Fixed there
(commit 5a8f6a51, cherry-picked to develop). The third check (match > 0.999 with a plain
hole) cannot hold on a 40 x 30 plate with a real M6 thread (0.32 % of it); the fixture's
plate is 120 x 90 now, the check unchanged (accepted by the orchestrator).

## From builder params (hand-over)

1. `fillet_sets._scratch` and `drafting._scratch_document` take the design's `UnitSystem`.
2. `thread_ui` uses `design_units.design_is_inch` / `length_text`; `fillet_ui`'s rows, radius
   point help, value boxes of inactive rows and the full round's line write lengths in the
   design's units (`_in_units`).
3. `thread_ui`'s `slotFinishRestoreDocument` removed (never called); nothing lost:
   `slotActivateDocument` and the recompute after loading draw a file's cosmetic threads.
4. Value boxes: the fillet / chamfer rows go through `blend_field` (params changed it to
   `parameters.read`), the thread's Length / Offset and the draft's angles through
   `preview.FormulaInput` (the same). Read in the code; no scenario of this builder types a
   parameter name there.

## From the orchestrator, late in the session

- **The largest-size search gave another answer under load** (docs example: "Largest radius
  found that fits here: 19.98 mm" instead of "... that fits here: 19.99 mm"). The search was
  cut off by seconds: 1.5 s in the dialogs (`value_limits.BUDGET`), 3 s in the AI tools
  (`ai/value_fit.BUDGET`), 0.6 s in `blend.max_size`, 1 s in `fillet_robust._alone`. It ends
  by itself when its gap is under the box's step (0.01 mm: about a dozen builds from 30 mm),
  so the seconds are now a far guard only (30 s, 60 s, 20 s; `_alone` is bounded by the
  number of edges, 16). When the guard does stop a search, the note and the AI's answer say
  "about". Unit tests with a slow clock (`SlowComputer` in `test_value_limits` and
  `test_ai_value_fit`): the same number and the same sentence at 1 ms and at 2.5 s a build.
- **The half sentence "(30 mm do"** was the log's cut; the sentence is whole (unit tested).
  But the sentence before it was wrong on that example: "1 of the 4 edges cannot be rounded;
  the other 3 can ... (a tiny step or sliver ...)" for four corners that each build alone and
  do not fit together. Now: "The rounds do not fit together: every edge can be rounded on its
  own, but once the other 3 are built there is no room left for the last of the 4 ...".
  Singular / plural fixed; no "click them again" in a tool's answer.
- **The docs' example now answers 20.00 mm**: 30 mm on the four corners of a 60 x 40 plate;
  two 20 mm rounds use up the 40 mm side exactly, which builds now (`fillet_section`).
  `edit_step` on FreeCAD's own Fillet step still answers 19.99 (that step cannot hold the
  other route's result; the dialog switches to Fission 180's step, the AI's edit does not).
- **Windows golden models**: `book_chamfer_after_modeled_thread` and
  `book_thread_dragged_before_chamfer` held Linux's printed volume at 1e-6. Hand formula now
  (the threaded shaft less the bevel's ring less the grooves' share of it): 29457.434, with
  the other swept-thread models' 2e-5 (Linux: 29457.470).
- **`fillet_qa_more` P18**: the step types `2*0.25`; the sum is kept as typed since builder
  params' merge (Fusion's rule). The check expected it dropped: updated, reason at the line.

## FreeCAD facts and traps

- `shape.Edges[i]` in a loop builds the whole edge list every time. Take the list once.
- OpenCASCADE's `makeChamfer` / `makeFillet` can return a solid that is not valid instead
  of failing (and take longer over it than over a success): always check.
- The extrude op's `"direction": "symmetric"` takes the whole length as `distance`.

- `Part.Face.validate()` on a face made from a surface and wires of fresh edges can crash
  FreeCAD (segfault in BRepLib_MakeFace::Add): do not heal faces that way.
- A solid can be `isValid()` and still fail `shape.check(True)` (edges off their faces after
  a boolean of touching round faces); blends then fail on plain edges of it.
  `fixTolerance(0.001)` on a copy is the one mend found.
- OpenCASCADE's booleans cannot be trusted with a tool whose face winds round many turns (a
  whole thread's flank as one B-spline face).
- The pick panel keeps its picks in FreeCAD's selection: a pick clicked again is "dropped".
  A dialog with two boxes must decide which box a dropped pick belonged to.

## Tests

| Scenario | Checks | Result |
|---|---|---|
| `book_modifyb_tensegrity` | 25 | PASS (fails 12 with `FISSION180_BOOK_BEFORE=1`) |
| `book_modifyb_carabiner` | 22 | PASS |
| `book_modifyb_thread_offset` | 22 | PASS |
| `book_modifyb_draft` | 31 | PASS (fails 7 without the fix) |
| `book_modify_fillet_limit_note` (changed) | 18 | PASS |

Golden: `book_tensegrity_corner_chamfer_20` (analytic), `book_carabiner_full_round_4`,
`book_thread_face_offset`. Unit: `test_fillet_core.SectionTests`,
`test_thread_core.MovedGrooveTests`. Benchmark: `blend_benchmark.py` (21 cases).

## Still open

- The Tesla housing's junction fillet where the tube's top is level with the ring's (a blend
  that fades out at a tangent point) and on a part that is not clean (see above).
- The thread's face count (one per turn and flank): the kernel's booleans, measured.
- Select Through starts off (shell's): the book's "window-pick the whole model" takes only
  what the view shows. The chamfer of that pick builds now, but it is not "every edge".
- No highlight of the edges in the way: the refusal counts them and says why, in words.
- A full round whose pick includes the face's short end edges is held just under (and said).
- No GUI scenario for the Tesla cases (the benchmark holds them).
- The AI's `edit_step` on FreeCAD's own Fillet / Chamfer step cannot reach a size only
  another route builds (it answers the kernel's limit, 19.99 for the docs' plate); a new
  `fillet` call can (20).

## Changelog lines

- A chamfer or fillet can now run on past the point where a face next to its edge gets narrower (the book's 20 mm chamfer in the Tensegrity Tower's corner was limited to 1.79 mm).
- Two fillets that use up the face between them exactly now build as typed (4 mm on both edges of the Carabiner's 8 mm face was held at 3.99 mm).
- Chamfering or filleting a window-picked part works when only the edges you can see were picked.
- When a fillet or chamfer does not fit, Fission 180 says so within a second or two instead of freezing, and says when it would run past the end of a face.
- A size that had to be held at the largest that fits is always said in the dialog.
- A fillet on an edge where two round faces run into each other smoothly is refused at once with the reason, instead of freezing for many seconds.
- A chamfer on a part whose earlier steps left it slightly out of true (a tube joined to a ring it only just touches) can now be built.
- Offset Face and Press Pull work on a modeled thread: click the thread and type a distance, and all its faces move together (a negative distance makes the thread looser).
- The Draft dialog keeps its pull direction when you click that face again while picking faces, and says why nothing was dropped.
- The Fillet and Chamfer dialogs write their sizes in the design's units (inches in an inch design).
- An inch design no longer goes back to millimetres after a chamfer with two sizes (the cause is fixed, not only guarded).
- Auto Timeline reads a part with a modeled thread again.
- The largest size that fits is the same on a slow computer as on a fast one (it could come out a hundredth smaller, with another sentence, when the computer was busy).
- When several fillets each fit on their own but not together, the message says that, instead of naming one edge as the culprit.

## Known issues

- A window-picked chamfer of many edges that the kernel cannot build in one run takes several seconds.
- A window drag picks only what the view shows: to chamfer every edge of a part, turn the part and add the rest, or switch on SELECT > Selection Filters > Select Through first.
- A fillet where a tube leaves a round housing exactly level with its top cannot be built: move the tube a little so the faces meet at an angle everywhere.
- A modeled thread has one face per turn on each flank (Fusion: one face), so picking "the thread" by hand takes many clicks; Offset Face and Press Pull take the whole thread with one click.
- A full round made by picking the whole top face of a bar with open ends is held a hair under the full size (the dialog says so); pick the two long edges instead.
