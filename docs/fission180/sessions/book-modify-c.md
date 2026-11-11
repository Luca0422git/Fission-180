# Wave 7 builder "modify-c": the open items of modify (branch `sf/book-modify-c`, 2026-11-11)

Takes over what the first modify builder left open (`docs/fission180/sessions/book-modify.md`,
"Round 2"): big feature patterns, Hole From Sketch, a pattern of bodies following its quantity,
bug 18's last leads, Section Analysis, and what the orchestrator added on the way (GitHub's
failures on develop in these files). Everything was reproduced first, headless for the kernel
and with real input for dialogs.

## 1. Knurls and big feature patterns

### Reproduced

The report's Geocache part, rebuilt from its text (`Fission180Tests/headless/pattern_benchmark.py`):
the bottom screw d33 x 16, chamfer 3, modeled M33 thread, the knob d40 x 8 below it, Coil
(0.1 revolutions, 10 mm, Triangular (Internal), Inside, 1 mm, Cut), Mirror about XZ, Circular
Pattern of both, Z, 25. Processor seconds of the pattern step alone, headless, FreeCAD 1.1.4,
4 shared CPUs (wall times moved between 1x and 2x of these with the other builders' load):

| case | copies | before (3.3.10) | memory | step |
|---|---|---|---|---|
| Geocache knurl, no thread on the body | 25 | 31.6 s | 827 MB | Fission 180's pattern step |
| Geocache knurl, with the modeled thread (the report's) | 25 | 38.2 s | 860 MB | same |
| Geocache knurl | 6 | 2.0 s (8.3 s with the thread) | 170 MB | same |
| Fire Piston knurl (Coil 1.5 revolutions x 3 in, its Mirror) | 6 | 96.4 s | 807 MB | same |
| Metric Bolt, 40 straight knurls | 40 | 0.5 s | 116 MB | FreeCAD's PolarPattern |
| 100 holes (10 x 10) | 100 | 0.3 s | 118 MB | FreeCAD's LinearPattern |

The report's "more than 10 minutes, 5.8 GB" is the same disease at a worse rate: its machine
had 2 cores and software OpenGL, and the dialog built the real pattern again for every value
shown (3, then 2, then 25), each build in the window's own process, nothing said, nothing to
stop it. The Fire Piston's "preview kept the app busy for more than 30 s" is the 100 s row.

### Where the time goes (kernel experiments, `.probe` scripts, numbers in processor seconds)

- One groove against the knob: 0.28 s with the Coil's own tool (a swept strip that lies ON the
  cylinder: a B-spline face nearly coincident with the cylinder face), 0.14 s with the exact
  difference the Coil made (a true cylinder face).
- Two crossing grooves: 0.15 - 0.18 s a pair (Geocache, surfaces of 2 x 6 poles); 1.6 - 2.5 s
  a pair on the Fire Piston (1.5 turns, 2 x 12 poles of degree 11, three crossings a pair).
  25 copies cross 125 times: that is two thirds of the half minute. It grows linearly with
  the copies (6 tools 2.1 s, 12: 5.9, 24: 13.0, 48: 30.1).
- Routes tried for the 25x knurl (48 tool copies): one boolean of all 29.6 s (530 faces);
  with exact difference tools 23.6 s; fuzzy 1e-5 no gain; in groups of 3 copies 36.6 s,
  309 MB, but 541 faces (six groove faces left split, and Refine then made the solid
  invalid); the base cut to the region the tools reach, then fused back: no gain; **the
  unit cell** (one 14.4 degree wedge cut by the 6 tools that reach it: 2 s, then 25 copies
  fused): 134 s for the fuse (every cell meets its neighbours along coincident B-spline
  faces) and 1028 faces that Refine does not merge; clean mirrored tools instead of the
  Mirror step's difference: the same 96 s on the Fire Piston, and an invalid solid.
- So one boolean of all copies is the fastest sound route OpenCASCADE has for crossing swept
  grooves; the seconds are surface-surface intersections of B-splines. Fusion's kernel does
  this in seconds; ours does not.

### What Fusion does (sources)

- Compute Option Optimized / Identical / Adjust: already researched and built (modify-2,
  `parity/patterns.md` C1-C7: Autodesk blog "Understanding Compute Options for Mirror and
  Pattern", API `PatternComputeOptions`, forum). Optimized and Identical give the same solid
  here (one boolean of the tools' copies); Adjust builds every copy again.
- The preview is not the built feature: Autodesk's blog on the compute options describes a
  preview that "shows exactly what you want, but when you click OK, the result doesn't match"
  (A). Autodesk support and staff on the forum: "any pattern large enough will cause some
  performance issues" (F).

### What was built

- **Light preview** (`pattern_light.py`, `pattern_ui.py`): when the copies would be slow to
  build (a score of the faces: flat and round faces 1, swept ones 8, long sweeps more; above
  150), the dialog shows shaded copies of the faces the picked features made (one Coin node,
  a few milliseconds for any count), the step stays the part before it, and the dialog says
  "Preview: 24 copies. Built when you press OK." Plain copies (holes, bosses, the 40 straight
  knurls) are built live as before.
- **The real build once, by OK, outside the window's process** (`pattern_progress.py`,
  `pattern_worker.py`): heavy copies (score above 400) are joined / cut by a command-line
  FreeCAD of its own, as the toolpaths and simulations already are. The window stays alive,
  a small window says what is being built and for how long, **Cancel** stops it at once
  (from a dialog's OK), and the kernel's 830 MB go back to the system with that program. A
  cancelled OK leaves the dialog open with "Cancelled" and the light preview. A recompute of
  the design later (an edit before the pattern, opening the file) shows the same window
  without Cancel.
- **Redo no longer rebuilds a new step** (`undo_fast.py`): Ctrl+Y of any step that made a
  new feature built that feature again (40 s for the knurl) because FreeCAD brings the
  object back without signalling its Shape. The object comes back as it was: it now counts
  as put back.

### After

| case | the dialog answers after the quantity is typed | OK to closed dialog | what it was before |
|---|---|---|---|
| Geocache knurl with the thread, 25 | 0.6 - 0.9 s, 24 shaded copies | 32 s on a quiet machine (the build outside 25 s), 55 - 65 s under the other builders' load; 38 s of processor (the same one boolean, in the other program) | 30 - 40 s for every value shown, in the window's process |
| Fire Piston knurl as the book lays it (along X, X axis), 6 | 0.8 s, 5 shaded copies | 29 s (the build outside 22 s; 47 s of processor) | every value shown built: "> 30 s" in the report |
| Metric Bolt, 40 straight knurls | 1.6 s, built live | at once | the same |

The window's memory no longer grows with the build (the 830 MB are the other program's and
go back to the system when it ends). Redo of the knurl: no build (was 44 s).

The Fire Piston laid along Z with the pattern about Z (the benchmark's `firepiston`) is a
harder solid than the book's (538 faces, 96 s of processor against 202 faces, 47 s): the
grooves start at another angle and cross more often. Both are in the benchmark.

## 2. Hole "From Sketch (Multiple Holes)", 5 holes, ~60 s

- Not reproduced with Simple holes: on a stand-in of the Tesla housing (ring, tangent inlet
  tube with its bore, 5 circles d1/16 in on the tube's end, an inch design, nested
  components) the whole dialog, profiled with cProfile under real input, spends 1.9 s in
  Fission 180 and FreeCAD together; 7 recomputes of 0.17 s.
- Reproduced with what the dialog starts with: the Hole dialog begins with the last hole's
  settings (Fusion's behaviour, kept). After a Tapped + Modeled hole, each click on a circle
  and each key cut every modeled thread again: 3.3 s of processor for one M6 thread, 8.3 s
  for five (656 faces), so 1 + 2 + 3 + 4 + 5 threads for the five clicks alone.
- Fix (`hole_ui.py`): a Hole step with more than one modeled thread previews the drilled
  holes, says "The 5 threads are modeled when you press OK", and OK cuts them once.
- Found on the way: FreeCAD's modeled M1 thread in a Hole leaves an invalid body of two
  solids (FreeCAD's own Hole; not changed).

## 5. Section Analysis listed twice

Reproduced with real input: Section Analysis pressed again while its dialog is open keeps
the first section (Fusion also runs a command that another one ends: Autodesk forum, Brian
Ekins on `isExecutedWhenPreEmpted`) and the new dialog took the first one's pick as its own
selection: a second section on the same plane, without a click. The new dialog now waits
for its own plane (`section_ui.start`).

## 3. A pattern of bodies follows its quantity parameter

- Reproduced: "A pattern of bodies takes a plain number as its quantity" (3.3.9), then the
  number taken once (first pass).
- Fusion: the book types the parameter as Quantity (Book).
- Cause: every copy is a body of its own (objects of the design), and no recompute may add
  or remove objects.
- Fix: the step keeps the formula (`round(...)` on its Quantity, like a pattern of
  features); `pattern.follow_counts` matches the copy bodies to the count after every
  recompute (`timeline_ops.settle`; without the GUI an observer does it). In Change
  Parameters the dialog's undo step is still open when that runs, so one Ctrl+Z takes the
  parameter and the bodies back; an undo of the parameter from anywhere brings the copies
  back to the old count the same way. The copies roll back with the marker and go with
  the step, as before.
- Proof: `book_modifyc_pattern_quantity` (58 checks: 6, 8, undo, redo, 4, the marker, Edit
  Feature, back to nothing and forward again), golden `book_pattern_bodies_follow_quantity`
  (3 -> 5 -> 2 bodies, hand-derived), `patterns_params` updated.
- Not done: a pattern of COMPONENTS still takes a plain number (components' file).

## 4. Bug 18: the orphan step after an undo

- (a) Reproduced, with real input, in `book_modifyc_undo_in_dialog` before the fix: the
  toolbar's Undo with the **Fillet** dialog open put "Fillet" on the Redo list and Redo
  brought the preview back as the step "Fillet 1"; with Combine and only its target picked
  the Undo took away the step BEFORE the command under the open dialog. Only the Ctrl+Z
  key was caught, and only by the dialogs that make a `preview.UndoCancels` (Fillet,
  Draft, Shell, Scale and others have none).
- Fusion: not found what Ctrl+Z does inside one of its own dialogs (Guess: Undo is not
  offered there). An add-in's command is run when another command ends it (Autodesk
  forum, Brian Ekins, `isExecutedWhenPreEmpted`).
- Fix: `commands.make_way_for` (the one door of the toolbar, the menus and the shortcuts)
  asks `preview.dialog_takes` for Undo / Redo: with a dialog open, Undo cancels the command
  (its `reject()`), Redo does nothing, FreeCAD's Undo does not run. Should FreeCAD's own
  Undo still reach a design under a dialog, the dialog's unfinished step is dropped from
  the Redo list (`preview._drop_redo`: FreeCAD has no call for it; the first change of a
  new step empties the list, so an object is added in a step that is then aborted).
- Proof: `book_modifyc_undo_in_dialog` (59 checks: Combine with a target only, Combine,
  Extrude, Fillet, Rectangular Pattern, Hole, and Combine with the key), and the first
  pass's guard `book_modify_combine_undo` (51 checks) still passes.
- (b) "One drag + undo froze the app for about 80 s" (line 421): **not rebuilt**. What was
  found on the way and removes a freeze of that kind: every Redo of a step that made a new
  feature built the feature again (`undo_fast`: 44 s for the knurl), fixed. The report's
  frame of 36 patterned sketch areas with a run of sketch undos before the extrude was not
  rebuilt in this pass.

## 5. Section Analysis listed twice

Reproduced with real input: Section Analysis pressed again while its dialog is open keeps
the first section (Fusion also runs a command that another one ends: Autodesk forum, Brian
Ekins) and the new dialog took the first one's pick as its own selection: a second section
on the same plane, without a click. The new dialog now waits for its own plane
(`section_ui.start`). `book_modifyc_section`, 28 checks. The same pattern (a command
reading the selection an open dialog made) may sit in `com_ui`, `interference_ui` and
`surface_analysis_ui`: not walked.

## 7. The hole position box showing "-55 um"

The dot's drag was rounded to a micrometre. Now a drag lands on the smallest clean step of
the design's unit that is at least two pixels on the screen (`hole_snaps_core.drag_step`,
unit tested; Guess for what Fusion does). `book_modifyc_hole_drag`, 27 checks. FreeCAD's
value box still shows a typed length below 0.1 mm in micrometres: that is
`taskui.DistanceField` (params / shell).

## 9. Mirror in an assembly

`book_modifyc_mirror_assembly` (40 checks): with the Arm (a component inside a component)
active, Mirror of its body (the image goes into the Arm) and of a feature; with the root
active and solids only in components, Mirror starts, takes the body and makes the image.
No code change was needed (components' `pattern_ui.start`).

## The orchestrator's additions

- **GitHub's failures on develop** (049c500b):
  - `hole_tapped`, `hole_qa_more`: the Hole dialog shared the Thread tool's size rule,
    which the first pass changed to "the nearest nominal size" (right for Thread: Autodesk).
    A 5 mm Simple hole made Tapped is drilled 5 mm and is M6x1:
    `hole_tables.size_for_drill`, used by `hole_ui._tap_type_changed`. In Fusion's Hole
    dialog the thread size is picked and the diameter follows.
  - `book_modify_combine_undo`: `parameters.add_user(doc, "Thickness", "", "2.5 mm")`: a
    unitless parameter can no longer take a length; the scenario now makes it in mm. Its
    guard is alive: 51 checks.
  - `patterns_qa_paths`: params' wording ("There is no parameter named 'abc'") and a
    length formula kept with its unit ("4 mm * pi"): the checks follow.
  - `surface4_qa`: bisected with that one scenario: green at 4cb179bd, red at 8b2663f2
    (the first modify merge). `timeline_ops.uses` no longer counts a step's `Picks` on the
    step before it as a dependency (as a fillet's edges never were), so Suppress on the
    surface Press Pull no longer switches the Delete Face after it off; the Delete Face
    finds its wall again (it was there before the pull) and stays on. The check now
    expects the filleted box without that wall (1415.19 = 1585.19 - 170). 88 checks.
- **Timeline Delete on a step that made a component**: Hardware fixed (`timeline_ops.delete`
  hands it to `hardware.remove`, one undo step); a pattern of a component and a component's
  own step already took their components (checked); a pasted occurrence has no step; Insert
  of another design not walked. `book_modifyc_delete_component_steps`, 31 checks.
- **Symmetric: Quantity each side or in all**: **not changed**. Sources: Autodesk's help is
  ambiguous for the sketch pattern and silent on the count for solids ("Symmetric
  distributes pattern instances symmetrically in two directions from the source object");
  the book's example is a sketch pattern (Quantity 5: five holes); an Autodesk Learn
  video only "increases the number to five". No source says what the solid pattern does.
  A change to "in all" touches `pattern_core` (linear_offsets, circular_angles,
  symmetric_walk_terms, instance_count), the expressions of FreeCAD's pattern steps
  (`pattern._symmetric_list_expression`), `component_pattern.all_moves`, the handles of
  the dialog, the stored meaning of every existing symmetric step (a version on the step,
  converted on edit), six golden models and four scenarios. It needs a whole pass and, for
  an even quantity, a decision (sketch-b guessed "the extra copy on the + side").

## Not done (with what is known)

- **6. Seams after a kept split face**: not started (the first pass's note stands: the
  steps in question are FreeCAD's own features; it needs a hidden follower step that draws
  the kept split lines again on the refined result).
- **8. Scratch documents take the design's units**: none of this builder's files makes a
  hidden document; `drafting._scratch_document` is in `drafting.py` (modify-b's by the
  file rule `draft*`).
- **Compute Option**: Optimized and Identical still give the same solid by the same route
  (one boolean of the tools' copies); a face-patterning Optimized was measured (the unit
  cell) and is far slower in OpenCASCADE.

## FreeCAD facts and traps

- A boolean of many crossing swept grooves is dominated by B-spline surface intersections:
  about 0.15 s a crossing for short grooves, 2 s for 1.5-turn ones. Fusing copies that meet
  along coincident B-spline faces (unit cells) is slower by an order of magnitude, and
  Refine does not merge B-spline pieces that come from rotated copies.
- `shape.cut([many])` already runs OpenCASCADE's parallel mode (processor time above wall
  time).
- After a modal window opened from inside a recompute closes, no window is active where
  there is no window manager (Xvfb): the next key goes nowhere. Activate the main window
  and give the focus back (`pattern_progress._Window.close`).
- `doc.openTransaction()` alone does not empty the Redo list; the first change inside the
  step does.
- A Redo brings a removed object back without a Shape signal and marked touched.
- FreeCAD's toolbar Undo with a pending transaction: commits it and undoes it (it lands on
  the Redo list); with a pending transaction that holds no change it undoes the step before.
- FreeCAD's modeled thread in a Hole of size M1 gives an invalid body of two solids.

## Changelog lines

- A pattern with many swept copies (a knurl) no longer freezes the dialog: it shows shaded copies while you type and builds the real ones once, when you press OK.
- A long pattern build shows a small window that says what is being built and for how long, with a Cancel button, and Fission 180 stays responsive meanwhile.
- Ctrl+Y (Redo) of a step no longer builds that step a second time.
- A pattern of bodies follows a parameter typed as its Quantity: change the parameter and bodies are added or taken away.
- Undo pressed while a command's dialog is open now cancels that command, in every dialog; Redo no longer brings a half-made step back (the "orphan Combine 1" kind of step).
- Hole > From Sketch with several modeled threads shows the holes at once and cuts the threads when you press OK.
- A Simple hole of 5 mm made Tapped is M6x1 again (its diameter is the tap drill).
- A hole dragged by its blue dot lands on clean values (no more "-55 um" in the position box).
- Pressing Section Analysis again while its dialog is open no longer makes a second section on the same plane.
- Deleting a Hardware step in the timeline takes the part's component, its holes and its joint with it; Ctrl+Z brings all back.

## Known issues

- A knurl of 25 crossing grooves still takes the geometry kernel about half a minute to build once you press OK (Fusion does it in seconds). The window stays usable and you can cancel.
- With Symmetric, a pattern of features, bodies or components counts the Quantity on each side (3 gives 5), while a sketch pattern counts all instances (5 gives 5).
- After a Split Face, a later feature that would have merged the split away is built without tidying its faces, so a thin seam line can show where it lands flush on an older face.
- A pattern of components does not take a parameter as its Quantity.
- A tapped hole of size M1 with Modeled ticked gives a broken body: untick Modeled for threads that small.
- A length below 0.1 mm typed into a value box is shown in micrometres.
