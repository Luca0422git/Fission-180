# Wave 7 builder: modify (fillet, chamfer, thread, hole, patterns, split, combine, gear, timeline), branch `sf/book-modify`

Read `book-common.md` first. Report lines: bugs 18-20 (170-179); Modelling table 223-264;
friction pattern 5 (406-409); cheat sheet 514-540; Saturn V 954-968 and the Split Face
entries on page 20 (the split lost at the next extrude); Tensegrity 1125-1137; Carabiner
1189-1192; Play Brick 1226-1236, 1263-1264; Geocache 1278-1319, 1355-1361; Metric Bolt
1405-1418; Drone 1566-1580; Fire Piston 1673-1683; Hot End 1787-1788, 1814-1832, 1901-1902;
Pizza Cutter 1978-2001, 2019, 2071-2073; Tesla 2180-2195; Gear Train 2345-2378; Football
2433-2435; Smartphone Case 2471-2473.

1. **Fillets and chamfers refused or capped as "too big"** where Fusion accepts them (the
   report's pattern 5; outline 9.2 calls fillet robustness a hard program): a 20 mm chamfer
   on an inner corner "limited to 1.79 mm"; 0.5 / 0.3 / 0.2 mm chamfer on all 71 edges of a
   part; a 4 mm fillet silently capped to 3.99; 0.25 mm on a patterned model; a 0.25" fillet
   where a tangent tube meets a housing; a 0.04" chamfer on two flat faces; a fillet on a
   face whose edges include a thread edge; a chamfer after a modeled thread at any size.
   Reproduce each on the report's geometry (build small golden-style models of each), then
   find out which refusals come from Fission 180's own limit search (`value_limits`,
   `fillet_core`, "does not fit: limited to") being too careful, and which are OpenCASCADE
   failing. Fix the first kind (never refuse or cap what the kernel can build; never cap
   silently: say it); for the second kind add retries (edge order, splitting the selection
   into chains, healing, building the fillet per chain) and measure the before / after on a
   benchmark you commit. A whole-body selection must skip edges that cannot take the size
   only if Fusion does (research: Fusion fails the feature); tangent-chain and face picks
   must not include edges Fusion would not (thread edges).
2. **Threads and the timeline**: the book's trick "drag the Thread before the Chamfer so the
   thread runs into the chamfer" (Geocache 1282-1290; Pizza Cutter 1992-2001): the drag is
   refused silently ("The graph must be a DAG"). Make reordering re-reference the faces by
   geometry so the move works when it is geometrically possible, or refuse with the reason
   next to the pointer; a chamfer made AFTER a modeled thread must work; deleting the
   chamfer must not break the thread ("Pick a cylindrical face to thread"); the thread's
   face survives edits before it. A fast timeline drag must work like a slow one.
3. **Thread tool**: ISO pipe / NPT / BSP thread types (Hole already has NPT / BSPT tables:
   `hole_tables.py`, MEMORY "NPT"); the default standard follows the design's units (params
   gives `design_is_inch`); the read-out in the design's units; "click it again to drop it"
   working from any view; clicks picking the wall in front (say which face is picked and let
   Select Other reach the one behind); the size suggestion (M7 for a 6 mm hole when Fusion
   suggests M6: research Fusion's rule: nearest standard size by the cylinder's diameter).
   **Offset Face / Press Pull on a modeled thread** ("Work in progress on complex shapes",
   nothing selectable): make the faces selectable and the offset work, or refuse clearly;
   a modeled thread's face count (19 B-spline faces vs Fusion's 4) matters for everything
   after it: see whether the thread can be built with fewer, cleaner faces.
4. **Split Face survives later features** (FreeCAD's Refine merges the halves back at the
   next extrude): Refine must not undo a split (how do Fission 180's features set Refine, and
   can split edges be marked to survive?), and a feature pattern that includes a Split Face
   repeats it ("SplitFace002 does not change the part, so there is nothing to repeat").
5. **Patterns**: direction picks take the EDGE clicked, not the face beside it (Play Brick
   1231-1236); Quantity and distances take parameters and expressions (also for bodies:
   "takes a plain number"; params owns the parsing); **performance**: a 25x circular pattern
   of a Coil + Mirror never finished (10 min, 5.8 GB) and the preview of a 6x one took 30 s.
   Profile it: pattern the result faces / use a compound of transformed tool shapes cut or
   fused ONCE (one boolean of a compound, not 25 chained booleans; OCC's fuzzy general fuse),
   an "Optimized / Identical / Adjust" compute like Fusion's, a light preview (transformed
   outlines, no booleans) while typing. Commit a timing benchmark (before / after).
   Hole "From Sketch (Multiple Holes)" of 5 holes took 60 s: the same disease.
6. **Bug 18**: undo of Combine leaves an orphan invalid "Combine 1" step. Find why its undo
   is not one transaction; audit every command of yours for "one command = one undo step,
   and undo removes everything it made" (use joints' transaction-closed helper if it exists).
   Combine Cut with a body of another component: "Cut would leave nothing of the target
   body" for a bolt through a wall (suspicious: placements across components?).
7. **Bug 19**: Gear with a root fillet that does not fit: OK must refuse (or build with the
   largest fillet only if Fusion's add-in does: there is no Fusion behaviour to copy here, so
   refuse and say the maximum), never build a copy of the previous gear (why did it? stale
   dialog state from the last gear: check every dialog that "remembers the last values").
   **Bug 20**: Edit Feature on a Gear step deletes it. Then audit Edit Feature for EVERY step
   type the timeline can show (a table in your session log: step type, opens its dialog?,
   Cancel leaves it unchanged?, OK with no change leaves it unchanged?), with a scenario that
   loops over them. Gear components named like Fusion's add-in names them ("Spur Gear (20
   teeth)": research) and a "Spur Gear" entry in Scripts and Add-Ins that opens the Gear tool
   (scripts are shell's file: a one-line entry).
8. **Draft**: the Pull Direction / Faces boxes (a refused OK cleared the pull direction;
   clicks toggling faces off by accident).
9. **Hole**: its own sketch row hidden from the browser like Fusion (MEMORY, "Questions
   waiting for Luca": the `hole` scenario edits through it: change the scenario to edit from
   the timeline); the dialog remembering the last hole is Fusion's behaviour: keep.
10. Section Analysis creating two entries on a re-pick; Mirror "needs a solid to repeat"
    when the active component is a subassembly (components builds component mirror; make
    the feature / body mirror start anywhere and say what to pick).
11. Timeline: "Group Features" vs Fusion's "Create Group" (name it as Fusion does), the gear
    menu needing a real click (make it a normal menu), fast drags.

Scenarios `book_modify_*.py` (at least: each fillet / chamfer case of item 1 with the size
the book uses; thread then chamfer by timeline drag; chamfer after a modeled thread; NPT
thread; split face then extrude then paint both halves; feature pattern with a split face;
pattern directions by edges; the 25x knurl pattern finishing within a stated time; undo of
Combine; gear with a too-big fillet; Edit Feature over every step type; inch thread default).
Unit tests and golden models for the geometry.
