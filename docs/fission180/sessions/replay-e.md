# Session log: wave 7 replay builder "replay-e" (branch `sf/replay-e`, 2026-11-11)

Brief: `docs/fission180/dev/briefs/book-replay.md`. Part of the book: chapter 5, project 12
"Pizza Cutter" and project 13 "Tesla Turbine" (the report's lines 1950-2283). Scenarios:
`replay_12_pizza_cutter`, `replay_13_tesla_turbine`; their steps are in
`Fission180Tests/gui/replay_e_steps.py` (shared) and `replay_12_*_steps.py` /
`replay_13_*_steps.py` (one file per part).

## How the replay is written

- One design per project, every step by real input (ribbon and menu clicks, keys, clicks in
  the view through the X server, typed values, browser and timeline clicks), with the four
  defaults a person has switched back on (`replay_e_steps.user_defaults`) and an undo step
  left open counted as a failure.
- The book itself is not in the repository: the replay does every step the report lists, in
  its order, with the values the report gives. Where the report gives no value (the length of
  the End Cap's shank, the wall of the handle) a stand-in consistent with the others was
  chosen and is named in the step's comment.
- Sketch points are clicked where a person puts them with Snap on: on the grid crossing next
  to the wanted place (`replay_e_steps.on_grid`); the dimensions then make the sketch exact.
- Development aid: `FISSION180_REPLAY_CHECKPOINTS=<folder>` writes a copy of the design after
  each part and `FISSION180_REPLAY_FROM=<part>` starts from the copy before that part. The
  acceptance run uses neither.

## Hitches found and fixed

| # | Project / report line | What happened | Fusion | Root cause | Fix (functions) |
|---|---|---|---|---|---|
| 1 | Pizza Cutter, End Cap, 1992 "Drag the Thread before the Chamfer" | Refused: "Chamfer 1 would fail there: BRep_API: command not done" (0.02 in chamfer on the end of the 0.25 in shank, 1/4-20 UNC modeled). The same drag worked on the M33 shaft the modify builder tested. | The thread then runs into the chamfer (Book; Forum, see `parity/hole-thread.md`) | A bevel after a modeled thread is built on the shaft under the thread and the grooves are cut again; the grooves were taken as the kernel's difference "shaft minus threaded shaft", which came back as the whole shaft here (both solids share every face but the grooves), so the result was empty | `fillet_robust._grooves_of` (new: the difference only when its volume is what the thread took, else the thread's own cutting solids), `fillet_robust._cut_grooves` (new), `fillet_robust.thread_twin`, `fillet_robust._through_thread`; `thread.grooves` (new), `thread._recorded` (new, shared with `thread.blank`). Golden model `book_thread_quarter_inch_before_chamfer` (analytic) |
| 2 | Pizza Cutter, Inner Body, 2013 Hole | The first tapped hole of the inch design came up as "ISO Metric profile", M6x1 | Fusion follows the design's units (the Thread tool was already fixed for this by the modify builder) | `HolePanel` started from `hole.DEFAULTS` or the last hole, whatever the units | `hole_ui._thread_start`, `hole_ui._design_standard` (new), `HolePanel.__init__`, `HolePanel.accept` (per-unit memory of thread type, size, designation, class) |

## Report items that now simply work (replayed the book's way, no workaround)

Pizza Cutter, End Cap: Change Active Units > Inch + Set as Default; the first component
grounded by itself; Line + 3-Point Arc; Coincident arc centre onto the bottom line; the
bottom line as Centerline and the book's DIAMETER dimensions 1.00 and 0.25 (report: radii);
the dimension between the origin and the arc's end point (report: a grey driven 0); Revolve
with the centerline as the axis by itself; the value boxes' tooltips name inches; Thread
offers ANSI Unified 1/4-20 UNC with an inch read-out; the look dropped on the body; Move/Copy
and Create Drawing in the component's menu.

Inner Body: Project (P) of the End Cap's head face from the Inner Body's sketch (report:
nothing projected); the rectangle from the projected face; Revolve as a New Body of the new
component; Chamfer by clicking the round face; Hole with the dot dragged onto the centre,
Countersink + Tapped + 1/4-20 + 0.625 + 0.25 + Modeled; no helper sketch row in the browser;
Midplane; Mirror of the Hole step; As-built Joint; Unground From Parent / Ground to Parent.

## Steps skipped as out of scope

(filled in at the end)

## Changelog lines

- Dragging a Thread before the small chamfer of a quarter-inch shank now works (the Pizza
  Cutter's End Cap): it was refused with "would fail there".
- A tapped hole in an inch design starts as a Unified thread (1/4-20 UNC), not as M6.

## Known issues

- Create Selection Set (in Fusion's component menu) is not built: Fission 180 has no
  selection sets.
