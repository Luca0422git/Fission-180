# Wave 7, sketch-c: the three sketch builders merged, and what they left open (branch `sf/book-sketch-c`, 2026-11-11)

sketch-a (drawing, snapping, selection, display, undo, Centerline), sketch-b (constraint
tools, Sketch Dimension, patterns, mirror, offset) and params (formulas in every value box)
each worked alone; this session owns the whole sketch area after their merge into `develop`
(1ffb7f33). Part 1: make the merged code work together. Part 2: build what they left open.
Spec with sources: `docs/fission180/parity/sketch.md`, section "Wave 7, sketch-c".

## Part 1: the merged code

Every `book_sketch_a_*`, `book_sketch_b_*`, `book_params_sketch`, `book_params_fields`,
`book_params_drone` scenario was run alone on the merged code first (a snapshot of 1ffb7f33):

| Scenario | Merged code | After this session |
|---|---|---|
| book_sketch_a_dimension | FAIL (1 of 12) | PASS (13) |
| book_sketch_a_centerline | FAIL (7 of 40) | PASS (42) |
| book_sketch_a_select / line / undo / shapes / project / fit | PASS (26 / 36 / 52 / 48 / 17 / 16) | see the table at the end |
| book_sketch_b_constraints / constraints2 / dimension / dimension_edge / modify / pattern | PASS (65 / 62 / 54 / 21 / 36 / 70) | see the table at the end |
| book_params_sketch / fields / drone | PASS (72 / 69 / 85) | see the table at the end |

### The collisions

- **Dimension.** D ran sketch-b's own tool, and sketch-a's two patches sat on FreeCAD's tool,
  which nothing starts any more: the centerline diameter never happened (a dimension to a
  centerline was a plain 10 mm distance), and `book_sketch_a_dimension` expected FreeCAD's
  aligned length where sketch-b's tool gives the vertical distance of a slanted line once the
  pointer is past its ends. Now there is ONE tool (`sketch_dimension_tool.py`): a dimension
  from a point, a line or a circle's centre to a Centerline is the diameter inside it
  (`_centerline_diameter`: the hidden mirror point and its Symmetric are made in the
  dimension's own undo step, `sketch_centerline.mirror_point`), and it is drawn with the
  diameter sign (`sketch_dimension_signs.py`). Retired: `sketch_mode._placing_dimension` /
  `_placed` / `_diameter_dimension`, `sketch_select_core.places_dimension`,
  `sketch_centerline.diameter` / `diameter_plan` (with their unit tests).
- **Selection.** sketch-b's scenarios click through Qt and add with Shift; nothing had
  clicked its tools the way a mouse does on top of sketch-a's "a plain click replaces".
  `book_sketch_c_merge` does, through the X server: selection first (click, Ctrl+click,
  Shift+click) and tool first (plain clicks are picks) for Parallel, Perpendicular, Equal,
  Sketch Dimension, Circular Pattern, Mirror. All worked as merged.
- **Hidden helpers.** Two modules hid geometry with two different marks (sketch-b:
  `GeometryLayerId` 2; sketch-a: only the view's `VisualLayerId` 2) and every tool asked one
  or the other. `sketch_helpers.hidden(sketch)` is now the one answer (either mark);
  `sketch_draw_helpers.hidden` calls it. Found and fixed on the way:
  - a chain double-click on a construction line walked into the hidden spokes ending in the
    same point (`sketch_select.curves_of` now leaves unseen curves out);
  - sketch-b's "a hidden line caught by a box selection is let go" only worked for elements
    selected under the sketch's own name (its scenario added them with
    `Gui.Selection.addSelection`): a real box in a sketch edited through its body names
    them "Sketch.Edge5", where `removeSelection` by the sketch's name removes nothing
    (sketch-a's FreeCAD fact). `sketch_helpers.unselect_unseen` clears and re-selects, once
    per box, and also lets go the END POINTS of hidden lines (Delete on one would have
    removed the constraints that tie a pattern's copies);
  - sketch-a's kind of helper (a polygon's hidden circle, a centerline diameter's mirror
    point) had no such guard at all: the observer is installed for both kinds now;
  - Trim / Extend / Mirror / Move / the patterns (`sketch_build.internal_geometry`) skip
    both kinds.
- **Grid.** Read and checked: mm Fixed 50 / 5 gives lines every 10 mm; an inch design gives
  0.2 in lines (Fixed, default) and a 1 in base (Adaptive). See Part 2, item 4.
- **Undo.** See Part 2, item 9 (a drawn line with a typed parameter name is one step).
- **`commands.make_way_for`**: sketch-a's `NOTHING_TO` kept; `book_sketch_a_undo` passes.

## FreeCAD 1.1.4 facts and traps (new here)

- The text of a dimension is the `string` field (an `SoMFString`) of the `SoDatumLabel` node
  under the sketch's `ConstraintGroup` (one child separator per constraint, in constraint
  order). pivy hands the field out typed: `getValues()`, `set1Value(0, text)`. FreeCAD writes
  it again on every solve / redraw of the constraints, not on a plain mouse move.
- `h.press("Delete")` in a scenario TYPES the letters D, e, l, e, t, e (D starts Sketch
  Dimension...): a key is `QtCore.Qt.Key_Delete`.
