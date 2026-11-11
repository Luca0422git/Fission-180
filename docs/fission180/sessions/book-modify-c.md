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

| case | dialog answers after typing the quantity | OK to closed dialog | window's memory |
|---|---|---|---|
| Geocache knurl with the thread, 25 | 0.6 - 0.9 s (was 30 - 40 s a value) | 55 - 65 s wall under the other builders' load (the same boolean, in the other program; 38 s of processor) | unchanged (the 830 MB are the other program's) |
| Metric Bolt, 40 straight knurls | 1.6 s, built live | at once | |

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

(More below as the items are done.)

## Changelog lines

- A pattern with many swept copies (a knurl) no longer freezes the dialog: it shows shaded copies while you type and builds the real ones once, when you press OK.
- A long pattern build shows a small window that says what is being built and for how long, with a Cancel button.
- Ctrl+Y (Redo) of a step no longer builds that step a second time.
- Hole > From Sketch with several modeled threads shows the holes at once and cuts the threads when you press OK.
- Pressing Section Analysis again while its dialog is open no longer makes a second section on the same plane.
- A pattern of bodies follows a parameter typed as its Quantity: change the parameter and bodies are added or taken away.

## Known issues

- A knurl of 25 crossing grooves still takes the geometry kernel about half a minute to build once you press OK (the Fire Piston's long grooves: more than a minute). You can keep the window open and cancel; Fusion does this in seconds.
- A tapped hole of size M1 with Modeled ticked gives a broken body: untick Modeled for threads that small.
