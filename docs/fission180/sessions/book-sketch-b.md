# Wave 7, builder sketch-b: constraints, Sketch Dimension, sketch patterns / mirror / offset (branch `sf/book-sketch-b`, 2026-11-11)

Brief: `docs/fission180/dev/briefs/book-sketch-b.md`. Spec with sources:
`docs/fission180/parity/sketch-constraints.md`.

## What was reproduced (FreeCAD 1.1.4, real input, before any change)

A probe scenario with real menu clicks and view clicks (not kept) on `develop` 3dbde183:

| Report item | Seen |
|---|---|
| Fix/Unfix, tool first, click a spline | nothing added, no message |
| Fix/Unfix on three selected circles, one fixed | nothing added; only "click what to constrain" |
| Collinear on two Vertical lines / two Horizontal lines | refused: "the Vertical on Line 2 already makes it so" (they were 3 mm apart) |
| Horizontal/Vertical, a point then the origin | FreeCAD picks by its own rule; no fallback, no reason when it conflicts |
| Tangent on an arc and a line sharing an end | FreeCAD's modal `Gui::Dialog::DlgCheckableMessageBox` "Sketcher Constraint Substitution" |
| Tangent, tool first, two splines sharing an end | the same modal box |
| Tangent with the shared spline end selected | nothing, no message |
| Symmetry: line, line, line | nothing, no message |
| D: two parallel lines, the placing click on a third line | two Equal constraints, no dimension |
| D: a point, then empty space | a Distance from the origin (with the box in this run) |
| Coincident, tool first, a click on a line | point-on-line here (FreeCAD takes the midpoint only within its snap radius: the report's case) |

Not reproduced: "rotated dimension labels are hard to hit". FreeCAD finds a dimension by its
whole drawing (text, lines, arrows): every offset tried answered. A fallback hit test along
the text was added anyway (`sketch_dimension_tool.dimension_at`), also for radius labels (the
report's case was a radius of 0.04 in). The report's sketch Fillet item (typed radius not
used) was the tool before 2026-11-10; the FILLET panel of 3.3.10 takes it (checked again).

## What Fusion really does (where the report or the brief was unsure)

- **A dimension of 0**: refused in Fusion too (Autodesk Community, a community manager: "zero
  is not a valid value for a sketch dimension"). The report was right; the message now says
  what to use instead.
- **Horizontal/Vertical**: "whichever is closest to its original orientation" (Autodesk help).
  The report's point was 32 mm to the side and nearer level: Fusion would have tried
  horizontal too. Fission 180 now makes the other one when the nearest conflicts, and says so
  (its own addition).
- **Symmetric patterns**: Autodesk's wording is ambiguous ("the specified number of copies in
  two directions"); the only concrete example is the book's (Symmetric, Quantity 5: five
  holes). The sketch patterns now count the instances in all. **The body patterns
  (`pattern_core.py`, builder modify) still count each side** ("assumed" in
  `parity/patterns.md`): the merger or modify should make them agree.
- **Placing on an axis**: Fusion's sketch axes cannot be picked for a dimension at all (forum);
  so an axis clicked after a line or circle places that dimension. After a point it is still
  a pick here (more than Fusion: the distance to the axis).
- **The report's "Placing a dimension on the construction line again made a pick" (Pizza
  Cutter)**: with ONE line picked, a click on another line is a second pick in Fusion too.
  Left so. With two picked the click places, wherever it lands.
- **Over-constraining dimension**: Fusion asks ("Choose OK to create a Driven Dimension");
  Fission 180 makes it driven without asking and says what sets the size (no modal boxes).

## Root causes and what was built

1. **The constraint tools were FreeCAD's commands** (`sketch_tools_ui._Constraint` ran
   `Sketcher_Constrain*`). All are pick tools on `sketch_draw` now
   (`sketch_constrain_tools.py`; decisions in `sketch_constrain_core.py`).
2. **The redundancy check misread the solver** (see FreeCAD facts). `judge()` reads the
   degrees of freedom; `add_forms()` tries the forms of a constraint in turn and replaces
   older relations the new one makes repeat (tested with them switched off first).
3. **`Sketcher_Dimension`'s placing click is a pick in C++**: Fission 180's own tool
   (`sketch_dimension_tool.py`).
4. **Pattern copies were only Equal to the original**: `sketch_pattern_ties.py` (hidden
   distances / spokes), `sketch_helpers.py` (hidden helper lines).
5. **Mirror**: a Symmetric of a point 0.02 mm off the mirror line keeps it 0.02 mm off on
   the other side: such ends are joined (Coincident) first.
6. **Offset**: its square construction lines showed; they are hidden helper lines now. A
   click on a line where it crosses an axis picked the axis.
7. **A typed Quantity**: the spin box commits on Enter / focus-out, and OK never takes the
   focus: `PatternPanel.commit()`.

## FreeCAD facts and traps (1.1.4)

- `SketchObject.solve()` returns -2 and flags ONE of the constraints that repeat each other,
  often an older one, also when the new one adds something: Vertical, Vertical, line-line
  Tangent: `RedundantConstraints == [2]` (the second Vertical), `DoF` 6 -> 5. `DoF` is right
  even then (the flagged one is left out of the solve).
- A Coincident onto the end of the line a point is already on, a Symmetric (midpoint) of a
  point already on the line: the OLDER PointOnObject is flagged.
- An end-to-end Tangent with the join's Coincident still there: the Coincident is flagged
  (FreeCAD's own tool deletes it and shows its modal box: `NotifyConstraintSubstitutions` in
  `Mod/Sketcher/General` switches the box off).
- Constraints that only a zero-length line can meet: the solver stops a hair before
  (`code == 0`, the line 1e-5 long), the NEXT solve prints "Updating geometry: Error build
  geometry: Both points are equal" / "Invalid solution from DogLeg solver". An open sketch
  solves on every `addConstraint`: trial adds run inside `preview.quiet()`.
- `doc.openTransaction(x); doc.abortTransaction()` (or commit) with NO change leaves the
  name booked: the next change anywhere (a `sketch.solve()`) becomes an undo step "x".
  `App.closeActiveTransaction(abort)` clears it (`preview.end_transaction` knew;
  `sketch_constrain_tools.end_step`).
- Tangent along a B-spline: "Direct tangency constraint including B-splines is not supported",
  solve -5 (malformed). End-to-end and end-to-curve tangency work.
- `Block` can be added twice on one curve without complaint; a `Part::GeomPoint` can be
  blocked.
- A horizontal / vertical dimension is drawn level with its SECOND point (`LabelDistance` is
  measured from there), not the first.
- Which Coin layer draws a sketch curve is `SketcherGui.ViewProviderSketchGeometryExtension.
  VisualLayerId` (settable from Python on a facade, saved with the file), NOT
  `GeometryLayerId`. FreeCAD draws all three Coin layers; `VisualLayerList` has no Python
  side. Coin's `SoSearchAction` does not find `CurvesLineSet20`... by name; a plain walk does.
- `sketch.setVirtualSpace(indices, True)` hides constraints; `constraint.InVirtualSpace`.
- Two lines Symmetric about a line by both end pairs: fine (4 equations). Arcs: both end
  pairs crosswise + Equal (5); centres + both ends would be 6 (redundant).
- `commands.make_way_for("Std_Redo")` with nothing to redo finished the open sketch (any
  command that "cannot start" in a sketch leaves it): Ctrl+Y / Ctrl+Z now only say "Nothing
  to redo / undo".

## Shared files touched (smallest changes)

- `commands.py`: `make_way_for`: Std_Undo / Std_Redo with nothing to do never finish the
  sketch (sketch-a's cfcb3c5c touches the same behaviour: merge by hand).
- `config.py`: `PREFERRED["Sketcher_Dimension"] = "Fission180_SketchDimension"` (the D key).
- `ribbon_config.py`: the Sketch Dimension entry (my line).
- `sketch_mode.py`: `NotifyConstraintSubstitutions` off in `PARAMS`; `label_point` asks
  `sketch_dimension_tool.label_point` first; `double_clicked` falls back to
  `dimension_at`; the 0-value message; `_start` calls `sketch_helpers.opened`.
- `sketch_draw.py` (`Geometry.__init__`) and `sketch_infer.py`: hidden helper lines are
  never snapped to.
- `sketch_build.py`: `internal_geometry` lists the hidden helper lines too.
- `parameters.py`: `model_parameters` skips constraints in virtual space.
- Scenarios updated for the new behaviour: `sketch_qa` (L: a selected line is the first
  pick), `sketch_pattern_tools` (D, F: tied copies, hidden lines).

For the merger: `book_sketch_b_steps.ModalWatch` (an application event filter that records
every QDialog shown) is what the brief asked for as "a harness-level watcher"; it lives in my
steps file. Moving it into `harness.run` would check every scenario.

## Gaps (with evidence)

- **Centerline diameter**: sketch-a had no Centerline linetype on its branch (dab74f7c);
  nothing to test against. FreeCAD has no diameter between two lines: it will have to be a
  distance whose box shows twice the value.
- **Edit Pattern / the pattern glyph**: not built. A pattern is ordinary curves and hidden
  constraints after OK; nothing records it as one pattern.
- **Splines / ellipses in a pattern** are not tied (no solver handle; said to the user).
- **Hidden spokes and selection**: FreeCAD does not draw or pick them, Fission 180's tools
  skip them, and one that gets selected all the same (FreeCAD's box selection takes every
  curve in the box) is let go again at once (`sketch_helpers._NeverSelected`; scenario). A
  chain double-click on CONSTRUCTION curves may still walk into a spoke (`sketch_select`,
  sketch-a's: it chains curves by their ends).
- **Offset "3 open wires"** (Carabiner): not reproduced as such (the book's exact geometry
  is not in the report). An open chain standing on a line and its offset now give a closed,
  extrudable strip (scenario); Fusion's offset of an open chain is open too.
- **Right-click Aligned / Horizontal / Vertical** while placing a dimension: not built.

## Changelog lines

- Sketch constraints (Coincident, Fix/Unfix, Parallel, Perpendicular, Horizontal/Vertical, Tangent, Equal, Symmetry) work both ways now: pick the things first and click the constraint, or click the constraint and then the things.
- A constraint that cannot be added always says why next to the mouse, and shows which constraints or dimensions are in the way.
- Collinear works on two vertical (or two horizontal) lines; it used to say "the Vertical already makes it so".
- Symmetry works on two lines, two circles or two arcs: click the two, then the line to mirror about.
- Tangent on an arc and a line that already meet no longer pops up FreeCAD's "Constraint Substitution" box; Tangent also works on the corner two splines share.
- Horizontal/Vertical between two points picks the direction they are nearest to, and the other one when that is impossible (it tells you).
- Fix/Unfix: a click fixes a curve or point and a second click frees it; with several things selected it fixes the ones that were not fixed yet.
- Sketch Dimension (D) is Fission 180's own tool: the click that places a dimension is never taken as another pick, wherever it lands.
- A slanted line can be dimensioned along its length (pointer beside it) or horizontally / vertically (pointer past its ends).
- Dimensioning to an edge of the part that is not in the sketch projects that edge for you.
- A dimension the sketch already determines is added as a driven dimension (in brackets) in one undo step, and says what determines it.
- Right-click a dimension > Toggle Driven.
- A dimension of 0 is refused with what to use instead (Coincident, Horizontal/Vertical, Collinear).
- Sketch Rectangular and Circular Pattern: the copies now follow the original and later dimensions, and a fully constrained sketch stays fully constrained.
- Sketch patterns: Suppression (tick it, then click the copies to leave out).
- Sketch patterns: with Symmetric, Quantity is the total number of instances (5 means 5).
- Sketch patterns: a typed Quantity counts when you click OK, without pressing Enter first.
- Sketch Mirror joins the end points that lie on the mirror line, so the mirrored outline is closed.
- Sketch Offset shows only the offset curves and their one dimension (its helper lines are hidden).
- Ctrl+Y with nothing to redo no longer closes the open sketch.

## Known issues

- A dimension to a centerline is not shown as a diameter yet: dimension the radius.
- A sketch pattern cannot be edited after OK: undo it, or delete the copies and make it again.
- Copies of splines and ellipses in a sketch pattern are placed but not tied to the original: dimension them if they must not move.
- With Symmetric, sketch patterns count all instances while body patterns (SOLID > CREATE > Pattern) still count each side.
- If you delete the original of a circular sketch pattern, its copies can move together as a group: fix or dimension one of them.
