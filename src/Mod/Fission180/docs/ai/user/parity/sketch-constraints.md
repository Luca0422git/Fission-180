<!-- A copy of docs/fission180/parity/sketch-constraints.md for AI models, made by tools/fission180/make_ai_docs.py: edit the original, then run the script. -->

# Sketch constraints, Sketch Dimension and the sketch's patterns / mirror / offset (wave 7, branch `sf/book-sketch-b`, 2026-11-11)

What the book parity report (`docs/fission180/dev/research/book-parity-report.txt`) logged in
this area, what Fusion really does, and what Fission 180 does now. `parity/sketch.md` has the
earlier rounds; this page is the area of builder sketch-b.

Sources: Autodesk's own hosts cannot be opened from the sandbox, so **Autodesk** rows come from
web-search excerpts of the Fusion help ("Add a horizontal or vertical constraint to a sketch",
"Add a symmetrical constraint to a sketch", "Dimension sketch geometry", "Create a circular /
rectangular sketch pattern", the API reference of `CircularPatternConstraint` /
`RectangularPatternConstraint`) and Autodesk blog posts ("Quick tip: aligned dimensions",
"Mastering Sketch Dimensions: 5 essential right-click tricks"); **Forum**: Autodesk Community
threads ("Dimension ZERO", "zero is a number", "Overconstrained sketch", "How to dimension
against an axis in sketch mode?", "Using coordinate axis for symmetry constraint"); **Book**:
what the report quotes from *Mastering Autodesk Fusion*; **Guess**: no source, Fission 180's
choice.

## Constraints

| Fusion (source) | Fission 180 |
|---|---|
| A constraint tool works on what is selected, or waits for picks (Autodesk, every "Add a ... constraint" page) | Every CONSTRAINTS entry is Fission 180's own pick tool now (`sketch_constrain_tools.py` on `sketch_draw`): fitting things selected first: applied at once, to all of them, one undo step, the tool ends; else it starts and waits. One thing selected that can start the constraint is its first pick. Until wave 7 Coincident, Fix/Unfix, Parallel, Perpendicular, Horizontal/Vertical, Tangent, Equal and Symmetry ran FreeCAD's commands |
| A constraint that cannot be is refused with a message (Forum "Overconstrained sketch") | Every click or constraint that cannot be says why beside the pointer: what the tool takes; which constraints or dimensions it conflicts with (highlighted); what already makes it so. Hidden ties (a pattern's, an offset's, a text frame's) are named as such |
| Horizontal/Vertical: "the geometry snaps to the horizontal or vertical axis, whichever is closest to its original orientation" (Autodesk) | Same, for a line and for two points (`sketch_constrain_core.hv_choice`). **Guess:** for two points, when the nearest cannot be (it conflicts) and the other fits, the other is made and the message says so (the report, Tensegrity: the point could only go upright with the origin) |
| Symmetry: "select the sketch geometry you want to constrain, then select the line of symmetry" (Autodesk); the book: left line, right line, centre line (Book) | Two points, two lines, two circles or two arcs, then the line (FreeCAD's solver knows only two points and a line: lines by their ends in pairs, circles by centres + Equal, arcs by their ends crosswise + Equal). Selected first: the only construction line of three is the mirror, else the last selected (**Guess**) |
| Fusion's sketch axes are not real geometry (Forum "Using coordinate axis for symmetry constraint": "the sketch axis in Fusion are just visual") | Fission 180's axes can be picked as a mirror line or for Coincident (more than Fusion; kept) |
| Collinear on two lines (Autodesk) | A line-line Tangent; when the lines are parallel already (each Vertical, each Horizontal, a Parallel) one end is put on the other line instead (the Tangent would say the direction twice). The report's "the Vertical on Line 12 already makes it so" was the old check misreading FreeCAD's answer: see below |
| Tangent on curves that share an end: silent (Book: the report, "Fusion: silent") | FreeCAD's end-to-end tangency takes the place of the join's Coincident, without a word. FreeCAD's modal "Sketcher Constraint Substitution" box is switched off for good (`NotifyConstraintSubstitutions`, also for FreeCAD's own command). A spline: at its ends only (the solver has no tangency along a spline; said when an end had to be joined) |
| Coincident: a point on a point or on a curve; the midpoint is its own constraint (Autodesk) | Point + point: Coincident; point + curve: on the curve, wherever the line is clicked (FreeCAD's tool took a click near the middle as the midpoint: a Symmetric) |
| Fix/Unfix: fixes or frees what is clicked or selected (Autodesk) | A click toggles; a selection: what is not fixed yet gets fixed, all fixed: all freed (**Guess** for the mixed selection: Fusion's rule was not found) |
| A dimension of 0 is refused: "zero is not a valid value for a sketch dimension" (Forum, a Fusion community manager; several threads) | Refused in the Dimension tool and in the value box, with what to use instead (Coincident, Horizontal/Vertical, Collinear). The report was right that Fusion refuses 0 too |

**What FreeCAD's solver really says** (found with FreeCAD 1.1.4, `sketch_constrain_core.judge`,
unit tested): of the constraints that say a thing twice it flags ONE, often an OLDER one, also
when the new constraint says something new. Collinear on two Vertical lines: `solve()` = -2,
`RedundantConstraints` = the second Vertical, and the degrees of freedom go from 6 to 5. The
old check read "an older one is flagged" as "it is so already". Now: the freedom went down =
it says something new; the older relations it makes repeat can go (FreeCAD's own "substitution"),
or another form of the same constraint is used that repeats nothing.

Also found: a constraint that only a line of no length could meet (Parallel between a
Horizontal and a Vertical line) is "solved" by FreeCAD shrinking the line to a hair; the next
solve then fails with "Both points are equal". Such a try is a conflict (`_squeezed`).

## Sketch Dimension (D)

| Fusion (source) | Fission 180 |
|---|---|
| "Select the sketch curves to dimension, then click to place the dimension" (Autodesk) | Fission 180's own tool (`sketch_dimension_tool.py`, decisions in `sketch_dimension_core.py`): with two things picked the next click places the dimension wherever it lands (FreeCAD's tool took a click on a line as a third pick: Equal constraints, the report) |
| A slanted line or two points: aligned, horizontal or vertical by where the pointer goes; right-click forces one (Autodesk blog "Quick tip: aligned dimensions", "5 right-click tricks"). The zones: aligned "when the cursor is within the bounding box of the end points, then changes to horizontal or vertical when outside the box" (Autodesk Inventor forum "aligned dimensions", the same Autodesk sketch dimension; Autodesk support "How to create an aligned dimension in a part sketch in Inventor"); "the aligned zone can be quite small" for a nearly level or upright line (Fusion forum "Dimension diagonal line"). A point and a line: the distance square to the line, no other (Fusion API `SketchOffsetDimension`) | `sketch_dimension_core.linear_kind` (wave 7, fix-5: one rule for a line, two points and a point picked alone): aligned inside the box the two points span (its edges included), horizontal once the pointer leaves it above or below, vertical once it leaves it left or right; past a corner, the side it is farther out of (**Guess**). Right-click > Aligned / Horizontal / Vertical forces one (sketch-c). A point and a line: always the distance square to the line |
| Fusion's sketch axes cannot be dimensioned to directly (Forum "How to dimension against an axis in sketch mode?": project it, or use the origin point) | An axis clicked after a line or circle places that dimension (the report: it became an Angle); after a point (or first) it is picked: the distance to the axis (more than Fusion; kept) |
| Projected reference on the fly ("Auto project edges on reference", Book: the report) | A click on an edge or corner of the part that is not in the sketch projects it (FreeCAD's external geometry) and picks it; its own undo step |
| "Adding this dimension will over-constrain the sketch. Choose OK to create a Driven Dimension" (Forum, quoted from Fusion) | It is added as a driven dimension (in brackets) without asking, in the SAME undo step, and says what sets the size (no modal box; `feature-guide.md` rule 9). Toggle Driven in the right-click menu on a dimension (Autodesk: Fusion's menu has it) |
| A dimension to a centerline is a diameter (Autodesk blog "5 right-click tricks") | **Not built**: sketch-a had not built the Centerline linetype when this branch ended; FreeCAD has no diameter between a line and a line |

## Sketch patterns

| Fusion (source) | Fission 180 |
|---|---|
| The copies belong to a pattern constraint: they follow the original and the pattern (Autodesk API: `CircularPatternConstraint`, `RectangularPatternConstraint`; Book: the report) | The copies are tied to the original point by point with hidden constraints (`sketch_pattern_ties.py`): a fully constrained sketch stays fully constrained, a later dimension moves the copies, corners close exactly. Splines, ellipses and conic curves cannot be tied (said) |
| "Check Suppression to display a suppression checkbox over each pattern instance in the canvas. Uncheck instances to remove them" (Autodesk) | Suppression in the panel, then click the copies to leave out (shown red; a click brings one back). No check boxes in the canvas |
| Symmetric: "creates the specified number of copies in two directions, symmetrically from the original" (Autodesk; ambiguous); the book: Rectangular Pattern, Symmetric, Quantity 5 gives 5 holes (Book) | Quantity is the number of instances in all, the original in the middle (**Book**). An even quantity puts the extra copy on the positive side (**Guess**). The body patterns (`pattern_core.py`, builder modify) still count each side: see the session log |
| "Double-click the Circular Pattern glyph at the center of the pattern, then adjust the settings" (Autodesk) | **Not built**: no glyph, no edit of a made pattern (delete the copies and pattern again) |

## Mirror, Offset, Fillet

| Fusion (source) | Fission 180 |
|---|---|
| Mirror: points on the mirror line are shared (Book: the report expected a closed profile) | An end of an original within 0.1 mm of the mirror line (5 % of a tiny curve) is joined with its mirror image (Coincident) and kept on the line: the outline closes (**Guess** for the tolerance) |
| Offset gives the parallel curve (Book: the report) | The square helper lines of the offset are hidden (`sketch_helpers.py`); the offset shows its curves and one dimension |
| Fillet: every picked corner, one radius (Autodesk) | Unchanged since 2026-11-10 (the FILLET panel); the report's "typed radius not used" was the tool before it; checked again |

## Hidden helper lines (`sketch_helpers.py`)

FreeCAD's solver has no "copy of that point, turned 60 degrees about this one". A circular
pattern's copies are tied with construction lines from the centre (spokes: Equal to the
original's, at the pattern's angle). They sit on FreeCAD's sketch layer 2: `GeometryLayerId`
(the mark) and the view extension's `VisualLayerId` (which Coin layer draws them), both saved
with the file; while the sketch is open an invisible draw style stands in front of that
layer's line sets and points, so they are neither drawn nor picked. Snapping
(`sketch_draw.Geometry`, `sketch_infer`) and every tool's helper list
(`sketch_build.internal_geometry`) leave them out; the Parameters list skips constraints in
virtual space.

## Tests

Scenarios (real input): `book_sketch_b_constraints`, `book_sketch_b_constraints2`,
`book_sketch_b_dimension`, `book_sketch_b_dimension_edge`, `book_sketch_b_pattern`,
`book_sketch_b_modify`. Unit: `test_sketch_constrain_core`, `test_sketch_dimension_core`,
`test_sketch_pattern_core` (ties, Symmetric, unique moves), `test_sketch_mirror_core`.

## Known gaps

- A dimension to a centerline as a diameter: built by sketch-c after the merge (inside
  Sketch Dimension, with the diameter sign; `parity/sketch.md`, "Wave 7, sketch-c").
- Editing a made sketch pattern (Fusion: double-click its glyph).
- Right-click Aligned / Horizontal / Vertical while placing a dimension: built by
  sketch-c (`Dimension.force`).
- Copies of splines, ellipses and conic curves in a pattern are not tied.
- Deleting the ORIGINAL of a circular pattern leaves its copies loose as a group (their
  hidden spokes stay).
