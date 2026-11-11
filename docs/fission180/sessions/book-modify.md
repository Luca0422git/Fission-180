# Wave 7 builder "modify": the book parity report (branch `sf/book-modify`, 2026-11-11)

Area: fillet, chamfer, thread, hole, patterns, split, combine, gear, timeline. Brief:
`docs/fission180/dev/briefs/book-modify.md`. Report: `docs/fission180/dev/research/book-parity-report.txt`.
Everything below was reproduced (or not) in real FreeCAD 1.1.4, headless probes for geometry
and GUI probe scenarios with real input for dialogs, before anything was changed.

## What was reproduced, and what the report had wrong

| Report item | Reproduced? | What is really going on |
|---|---|---|
| Drag the Thread before the Chamfer does nothing (Geocache, Pizza Cutter) | Yes | `timeline_ops.move` raised "Thread 1 uses geometry made by a step it would move before": the Thread's `Faces` link pointed at the chamfer, FreeCAD said "The graph must be a DAG", and the chamfer could not be built after a modeled thread at all |
| Deleting the chamfer breaks the thread ("Pick a cylindrical face to thread") | Yes | FreeCAD empties a link whose object is deleted; the thread never looked for its cylinder on its new step before |
| A chamfer after a modeled thread is refused at every size | Yes, on the kernel itself | `shape.makeChamfer` fails ("BRep_API: command not done") for 3, 1, 0.5 and 0.2 mm on the end of a threaded d33 shaft: the end edge is cut through by the grooves |
| Thread suggests M7 for a 6 mm hole | Yes | The first pass matched a hole by its tap drill (a guess). Autodesk: the size nearest the face, and the hole is then given the thread's minor diameter. With the old rule a 6 mm hole threaded M6 got no thread at all (the grooves lay in the air): the report logged that step "OK" without seeing it |
| Thread defaults to ISO in an inch design / to the last standard in a mm design | Yes | One remembered standard for every design |
| "Click it again to drop it" does not work from another view | Yes, for a modeled preview | The selection gate let only cylinder faces through (the preview's grooves are B-spline faces), and FreeCAD gives (0, 0, 0) as the picked point of such a click, which was looked up on the part: the bottom face |
| No ISO pipe / NPT thread types | Yes | Only the Hole had taper pipe threads |
| The split is lost at the next Extrude | Yes | PartDesign's Refine merges faces on one plane / cylinder; nothing can mark an edge "keep" (tried: wrapping one half's surface in a trimmed surface does not stop ModelRefine) |
| A feature pattern with a Split Face is refused | Yes | `pattern.feature_tools` raised for a step that changes no volume |
| Pattern directions: an edge click takes the face | Yes (a click 0.5 mm beside the edge) | FreeCAD's pick reach is about 5 px; the dialog took the face's normal |
| "A pattern of bodies takes a plain number as its quantity" | Yes | By design (each copy is a body); now the formula's value is taken and the dialog says it is kept as a number |
| 25x knurl pattern never finishes | Partly | Here it finishes in 30-40 s (one build per value shown). The report's 10 min / 5.8 GB was not reproduced on this machine; the time is the kernel crossing 50 swept grooves |
| Bug 18: undo of Combine leaves an orphan step | **No** | Four set-ups with real input (two bodies; three separate bodies; three bodies of one multi-body extrude; Ctrl+Z inside the open dialog): Combine is one undo step and its undo removes it. Not fixed because not found; see "Still open" |
| Bug 19: Gear OK with a fillet that does not fit copies the previous gear | Partly | OK is refused (the dialog stays, with the reason). What reads as a copy: the dialog starts with the last gear's values, so the gear shown after placing is the previous one, and it stays shown while the new values do not fit. Also found: Operation New Component silently went back to New Body in that state |
| Bug 20: Edit Feature on a Gear step deletes it | Yes, in one state | When the Gear dialog is still open on that step (its preview is a real step in the timeline): Edit Feature "finished" the dialog, which cancelled it. On a finished gear Edit Feature opens the dialog |
| "Group Features" vs "Create Group" | Yes | Autodesk's help says Create Group |
| A fast timeline drag does nothing | Yes (press, release far away, no move event in between) | It was taken as a click |
| The hole's sketch row in the browser | Yes | Listed under Sketches |
| 20 mm chamfer "limited to 1.79 mm"; 0.5 mm on all 71 edges; 0.04 in on two flat faces; 0.25 in at the tube joint; 0.25 mm on the patterned model | **Not on stand-ins** | On parts built from the report's text OpenCASCADE builds the first three in one run. A tube tangent to a housing and drifted pattern copies do fail on the kernel at every size (benchmark below). The book's own models are needed to say more |
| 4 mm fillet "silently" capped to 3.99 | Kernel: yes | Two 4 mm rounds use up an 8 mm face exactly: OpenCASCADE refuses 4.0, builds 3.99. The dialog's blue note says "4 mm does not fit: limited to 3.99 mm" (Luca's decision of 2026-10-21); the row list showing "3.99 mm" is what the report read as silent |
| Section Analysis: two entries on a re-pick | No | One analysis per dialog in the code and in a probe; not found |

## What Fusion really does (sources)

In the parity docs, each row marked Autodesk / Forum / Book / Guess: `parity/hole-thread.md`,
`parity/fillet.md`, `parity/patterns.md`, `parity/gear.md`, `parity/timeline-browser.md`
(sections "Wave 7, the book parity report"). The ones that changed what was built:

- Autodesk staff (forum "HOLE WITH THREADING OPTION"): "Fusion 360 will currently adjust the
  diameter of a threaded hole to the minor diameter of the thread"; Autodesk tech tip: the
  Thread tool "will find the closest standard thread in relation to the size of the circular
  face you selected". So: nearest nominal size for holes too, and the modeled thread sets
  the diameter.
- Forum (several threads): the thread dragged before the chamfer runs through the chamfer;
  chamfering a modeled threaded HOLE fails in Fusion too.
- Forum: Fusion fails the whole fillet when one edge fails and does not say which. So no
  skipping of edges; but Fission 180 now says how many are in the way.
- Autodesk help ("Use the Timeline"): Create Group.

## What was built

- `fission180/fillet_robust.py` (new): routes for blends the kernel refuses in one run
  (through a modeled thread; on the refined part; group by group), and the count of edges in
  the way. Wired into `fillet_sets.kernel`, `blend.trial` (`blend.make_best`,
  `fillet_sets.rescue`), the Fillet / Chamfer dialog (`BlendPanel._robust`) and the AI op.
- `thread.py`: faces always on the step before, found again by place; `parts()` (add + cut,
  forms, taper), `blank()`, `slack()`; `thread_core.py`: thread forms (ISO, Whitworth, NPT),
  the standard-size rule; `thread_tables.py`: `THREAD_STANDARDS` with pipe (G) and NPT
  tables, the nearest-nominal rule; `thread_ui.py`: units, per-unit memory, drop by clicking
  the preview.
- `timeline_ops.py`: `_free_threads`, `_rescue_blends`, `_names_on` (pieces, thread slack),
  the sets step's Picks rebased (`MOVE_PROPS`), `_keep_splits` in `settle`;
  `timeline_ui.py`: fast drags, Create Group, the refusal next to the pointer, the settings
  menu as a pop-up, Edit Feature on an open dialog's own step.
- `split_face.py`: `keep_splits` (a step after a Split Face that merged the split away is
  built again without Refine; called from `timeline_ops.settle`, and by an observer when
  there is no GUI), `made_edges`, `imprint`; `pattern.py`: `repeat_splits`; `pattern_ui.py`: `_edge_meant`,
  a body pattern's quantity from a formula, the start in an assembly without a solid of its
  own.
- `gear_ui.py` / `gear_core.py`: the operation stays picked, the refusal next to the pointer,
  component names; `fission180/samples/SpurGear.py` + one line in `scripts_ui.entries`.
- `combine.py`: the "Cut would leave nothing" message names the bodies and says which is
  cut by which.
- `browser_core.py` / `browser_ui.py` (two lines): the hole's own sketch has no row.

## Edit Feature over every kind of step (scenario `book_modify_edit_feature`)

Right-click > Edit Feature (Edit Sketch), Cancel, again, OK without a change; after each the
timeline, every body's volume and every step's state are compared with before.

| step | menu entry | opens | Cancel leaves it | OK leaves it |
|---|---|---|---|---|
| Sketch 1 | Edit Sketch | sketch | yes | yes |
| Extrude 1 | Edit Feature | dialog | yes | yes |
| Fillet 1 | Edit Feature | dialog | yes | yes |
| Chamfer 1 | Edit Feature | dialog | yes | yes |
| Hole 1 | Edit Feature | dialog | yes | yes |
| Sketch 2 | Edit Sketch | sketch | yes | yes |
| Extrude 2 | Edit Feature | dialog | yes | yes |
| Thread 1 | Edit Feature | dialog | yes | yes |
| Rectangular Pattern 1 | Edit Feature | dialog | yes | yes |
| Chamfer 2 (two sets: Fission 180's step) | Edit Feature | dialog | yes | yes |
| Gear 1 | Edit Feature | dialog | yes | yes |
| Box 1 | Edit Feature | dialog | yes | yes |
| Combine 1 | Edit Feature | dialog | yes | yes |
| Sphere 1 | Edit Feature | dialog | yes | yes |
| Box 2 | Edit Feature | dialog | yes | yes |
| Split Face 1 | Edit Feature | dialog | yes | yes |

Not in the loop (other builders' steps, or needing their own set-up): Revolve, Sweep, Loft,
Shell, Draft, Scale, Mirror, Circular Pattern, Split Body, Coil, the surface, mesh, sheet
metal, plastic and joint steps. The one real failure of Edit Feature found was the open
dialog's own step (bug 20).

## Benchmarks

Blends (`Fission180Tests/headless/blend_benchmark.py`, real FreeCAD 1.1.4, this machine).
"One run" is what Fission 180 did before (OpenCASCADE's single fillet / chamfer of all the
edges); "with routes" is `fillet_sets.kernel` now:

| case | edges | one run | with routes | how |
|---|---|---|---|---|
| chamfer 3 on the end of a modeled M33 thread | 5 | fails | built (5.7 s) | thread |
| chamfer 1 on the end of a modeled M33 thread | 5 | fails | built (2.4 s) | thread |
| chamfer 0.25 on the end of a modeled M33 thread | 5 | fails | built (1.9 s) | thread |
| fillet 1 on the end of a modeled M33 thread | 5 | fails | built (1.5 s) | thread |
| chamfer 2 on both ends of the thread | 10 | fails | built (1.5 s) | thread |
| fillet 3 along an edge split by an unrefined seam | 2 | built | built | one run |
| chamfer 0.5 on every edge of two blocks joined without Refine | 16 | built | built | one run |
| chamfer 0.5 on every edge of a plate with 12 bosses | 36 | built | built | one run |
| chamfer 0.25 on every edge, copies drifted by micrometres | 116 | fails | fails (2.4 s) | refused: "36 of the 116 edges cannot be bevelled at this size" |
| chamfer 1 where a tangent tube leaves the housing | 2 | fails | fails | refused |

Built in one run: 3 of 10; with the other routes: 8 of 10. The two that still fail are the
kernel's (no size works on those edges); the refusal now counts the edges in the way.

Knurl (a Coil groove, its Mirror, a Circular Pattern of both; `book_modify_knurl`):

| copies | one boolean of all copies (what the pattern does) | one by one | batches of copies that do not touch |
|---|---|---|---|
| 6 | 3.1 s | | |
| 25 | 27 s headless, 32 s in the dialog | 55 s | 31 s |

The pattern is built once per value the dialog shows (3, then 25) and not again by OK.

## Scenarios (real input; `book_modify_*`)

| Scenario | Checks | What it proves |
|---|---|---|
| `book_modify_thread_chamfer` | 52 | chamfer, thread, the Thread dragged before the Chamfer (slow and fast), the chamfer deleted, a chamfer after a modeled thread, its edit, the drag back, a refused drag |
| `book_modify_thread_inch` | 36 | Unified by default and inches in an inch design, drop by clicking the thread, NPT on its cone, G sizes, ISO again in a mm design |
| `book_modify_gear` | 48 | SpurGear in Scripts and Add-Ins, bug 19 (the refusal, the operation kept), bug 20 (Edit Feature while the dialog is open, and after), component names |
| `book_modify_edit_feature` | 197 | Edit Feature / Cancel / OK over 16 kinds of steps |
| `book_modify_split_pattern` | 191 | a split kept under the next feature, both halves pickable, a pattern with a Split Face, a direction by a click beside an edge, undo / redo, the split deleted |
| `book_modify_knurl` | 17 | the 25x knurl pattern: built once per value, valid, under 240 s |

Older scenarios changed for the new (Fusion) behaviour: `hole` (the hole's sketch has no
browser row: edited from the timeline), `hole_qa_thread` T4 and `hole_thread_inside` (a hole
takes the size of its diameter), `misc_scripts` (the SpurGear entry), `patterns_params` (a
body pattern takes a parameter's value), `timeline_browser`, `timeline_browser_qa3`,
`polish2_timeline_groups` (Create Group).

## FreeCAD facts and traps

- **`Gui.Selection`'s PickedPoints can hold (0, 0, 0)** for a click on a face of a body's
  shown step picked through the body: check that a picked point lies on the picked face
  before using it (`thread_ui._face_clicked`).

- **FreeCAD 1.1's Python document observer gets no `slotBeforeRecomputeDocument`.** Only
  `slotRecomputedDocument` arrives. `timeline_ops.RecomputeGuard.slotBeforeRecomputeDocument`
  (the muting of the Report view during recomputes of a design with known problems) has
  never run; its `quiet()` is only entered by `settle()` and the callers that use it
  directly. Left as it is (shell's / timeline's decision what to do about it); a step that
  must change before a recompute changes on its own property change instead
  (`split_face._Keeper`).
- FreeCAD's Refine (ModelRefine) merges two neighbouring faces on one plane or cylinder
  whatever their surface handle: a `RectangularTrimmedSurface` wrapper around one half does
  not stop it (tried, `.probe` experiments). Cones, spheres and tori are never merged.
- OpenCASCADE cannot chamfer or fillet an edge that a swept groove cuts through, at any
  size; it can blend the same edge on the part without the grooves, and cutting the grooves
  afterwards gives the same solid.
- `Part.makeLongHelix(pitch, height, radius, angle)` takes the cone's half angle in degrees
  and only widens upwards (a negative angle is taken as 0): a narrowing thread is built
  widening and turned over.
- A modeled thread's crest between two grooves is ONE cylinder face (a helical strip); its
  end edge on the end face is a true circle arc, so it is found again as "the same circle"
  on the part without the thread, the radius apart by what the thread's class turned off.
- One boolean of all pattern copies is faster than cutting them one by one, also when the
  copies cross each other (the knurl).
- A script run from Scripts and Add-Ins runs inside its own undo step: a script that opens a
  dialog must do so after it ended (`QTimer.singleShot(0, ...)`), or the dialog's step is
  closed under it.

## Still open (with the evidence)

- **Bug 18** (undo of Combine leaves an orphan "Combine 1"): not reproduced in four set-ups
  on 3.3.10 (probe scenarios, real input: Combine of two bodies, of three separate bodies,
  of the three bodies of one multi-body New Body extrude, and Ctrl+Z inside the open
  dialog). In all, `UndoNames` holds one "Combine" step and Ctrl+Z removes the step, the
  bodies come back. The report's design had an extrude whose distance follows a parameter
  ("-Thickness") and 35 picked areas; that is the next thing to try.
- **Whole-body chamfers / the 20 mm chamfer of the Tensegrity / the 0.04 in chamfer and
  0.25 in fillet of the Tesla housing**: need the report's actual models; the stand-ins
  build. The benchmark holds a tangent tube and drifted copies that fail on the kernel.
- **Modeled thread with 4 faces like Fusion's, Offset Face / Press Pull on a thread**: not
  built (the sweep is one face per turn and flank). The dialog's refusal is FreeCAD's.
- **The knurl's time** (30-40 s for 25 copies here): the kernel's; Fusion's "Optimized"
  compute (patterning faces) is not built.
- **Draft's Pull Direction / Faces boxes, Section Analysis's double entry**: not reached.
- A seam can show after a Split Face on a later step that had to be built without Refine
  (one that would have merged the split away), where it lands flush on an older face. The
  first try switched Refine off on every step after a Split Face: Press Pull on one half then
  left three seams (golden `direct_split_face_then_press_pull`: 11 faces for 8); now only a
  step that loses a split line is switched.
- A body pattern's quantity typed as a parameter is taken once (the dialog says so).

## Changelog lines

- Dragging a Thread before the Chamfer of its end in the timeline now works: the thread runs into the chamfer, as in the book's Geocache screw.
- A chamfer or fillet can be made after a modeled thread (it was refused as "too big" at every size).
- Deleting the step before a thread no longer breaks the thread.
- The Thread tool offers the size of the face for a hole too (a 6 mm hole is M6, not M7), and a modeled thread gives a hole or a shaft the thread's standard diameter, like Fusion.
- New thread types: ISO pipe threads (G) and NPT taper pipe threads.
- In an inch design the Thread tool starts with Unified threads and reads its sizes in inches.
- Clicking a threaded face again drops it, also when you click on the modeled thread itself.
- A split face stays split when you add more features after it, so both halves keep their own colour.
- A pattern or mirror of features can include a Split Face: the copies are split too.
- A pattern direction takes the edge you click, also when the click lands a hair beside it.
- A pattern of bodies takes a parameter as its quantity (it uses the parameter's value at that moment and says so).
- Mirror and Pattern start in an assembly whose parts are all in sub-components.
- The Gear tool keeps the Operation you picked while a value does not fit, and says next to the pointer why OK did nothing.
- A gear made as a New Component is named like Fusion names it, for example "Spur Gear (20 teeth)".
- UTILITIES > Scripts and Add-Ins lists "SpurGear", which opens the Gear tool.
- Edit Feature on a step whose dialog is still open no longer removes the step.
- The timeline's "Group Features" is now called "Create Group", as in Fusion.
- A fast drag in the timeline moves the step like a slow one, and a drag that cannot be says why next to the pointer.
- When a fillet or chamfer of many edges does not fit, the message says how many edges are in the way.
- Combine with Cut that would leave nothing says which body is cut by which.
- A single Hole no longer adds a sketch row to the browser.

## Known issues

- After a Split Face, a later feature that would have merged the split away is built without tidying its faces, so where it lands exactly flush on an older face a thin seam line can show. Delete or suppress the Split Face to get the merged face back.
- A pattern of bodies does not follow its quantity parameter by itself: after changing the parameter, edit the pattern and type the parameter again.
- A 25-times pattern of crossing grooves (a knurl) takes about half a minute to build.
- A chamfer on the rim of a hole after its modeled thread is refused (in Fusion too): make the chamfer first, or roll the marker back before the thread.
- Offset Face and Press Pull do not work on a modeled thread: pick a looser Class in the Thread dialog instead.
- A fillet along an edge where the two faces become tangent (a tube leaving a housing at a tangent) cannot be built at any size.
