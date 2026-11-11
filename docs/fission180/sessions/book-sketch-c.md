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
- A text typed over a formula with `sketch.setDatum` leaves the formula bound: the datum shows
  the number until the next recompute puts the formula's value back. The expression has to
  be cleared first (`parameters.set_expression(sketch, path, None)`).
- FreeCAD's on-view value boxes (Line, Rectangle, Circle...) are `QAbstractSpinBox` children
  of the 3D view's MDI widget; the one being typed in has the keyboard focus. Their unit is
  the dynamic property `unit`. Key events sent to the box with `QApplication.sendEvent`
  ("30 mm", then Enter or Tab) are taken exactly like typed ones, and the tool then adds its
  own dimension for the value, which `parameters.bind_typed` finds by value.
- `view.getObjectInfo` at an outline edge of a body often answers the FACE next to it (or
  nothing, one pixel outside): a click "on a model edge" has to look at the pixels around it
  (`sketch_reference.AIM`), the way the test helper `h.click_edge` does.
- An external curve projected inside a mouse press is not known to FreeCAD's own drawing
  tool for that click (its preselection is from the last redraw): the point lands free. The
  inference has to carry the "on this curve" itself (`Inference._on_projected`).
- `Sketcher.GeometryFacade(geo)` with the old facade's extensions set on a scaled copy of its
  geometry, written back through `sketch.GeometryFacadeList`, scales a sketch without losing
  construction marks, layers or internal alignment.
- FreeCAD's own sketch snap takes a line's middle within 5 % of the line's LENGTH
  (`SnapManager::snapToLineMiddle`) and auto-constrains the point Symmetric: a model
  distance that grows with the line, like its grid rule. An event forwarded with `free`
  (`Inference._forward`: Snap off, pick radius 0.01, Autoconstraints off) is placed to the
  pixel; the remembered Result (`on_curve_geo`) then puts it exactly on the curve.
- Any command a menu runs inside a sketch ends Fission 180's running tool first
  (`commands.make_way_for`), unless it is listed in `commands.KEEPS_SKETCH_TOOL`.

## Part 2: what the three builders left open

| # | Item | Reproduced? | Fusion (source) | Root cause | Fix | Proof |
|---|---|---|---|---|---|---|
| 1 | Edit a made pattern (glyph, edit, delete as one; splines / ellipses tied) | Yes, by reading: nothing records a pattern after OK | "Double-click the Rectangular Pattern glyph next to the original instance" (Autodesk help) | No record of a pattern | **Not built** (no room left) | - |
| 2 | Right-click Aligned / Horizontal / Vertical while placing; the same-spot second pick | Yes (no such entries; the same-spot click picked the Y axis instead of the arc) | Autodesk blog "5 Essential Right-Click Tricks", "Quick tip: aligned dimensions" | Not built; an axis a hair nearer the pointer came before the sketch curve through the first pick | `Dimension.force` / `can_force`, three commands in the right-click list, `Dimension._first_through` | `book_sketch_c_dimension` A, B, C |
| 3 | Snaps: midpoint too wide, slot end to an arc's middle, the origin | The midpoint: yes (a Line ended ON a 54 mm line 7 px from its middle got a Symmetric constraint onto the middle). The slot and the origin: not looked at | No pixel number from Autodesk (Guess: the triangle shows only with the pointer on the middle) | Two: Fission 180's snap gave the middle the full 8 px reach; and FreeCAD's own snap (`SnapManager::snapToLineMiddle`) takes the middle within a twentieth of the line's LENGTH (18 px there), with its Symmetric auto-constraint | `sketch_infer_core.nearest_snap`: a middle within 0.6 of the reach; `Inference._beside_middle`: a point on a line or arc inside FreeCAD's zone but off the middle is placed by Fission 180 (FreeCAD's snap off for that event) and held by point-on-curve | `book_sketch_c_grid` B (on the middle: the middle; 7 px beside it: on the line); unit `MidpointReach`. **Slot end / origin: not built** |
| 4 | Grid snap strength | Yes (the 8 px pull is what sketch-a built) | On by default, to grid crossings (Lynda); the minor lines (Autodesk forum: 5 mm / 20 subdivisions snaps every 0.25 mm); sketch geometry first (Autodesk forum) | A decision left open by sketch-a | `GridSnapFull` (on): `sketch_infer_core.grid_snap` / `grid_capped` with reach `FULL`; off in the harness for the scenarios written before | `book_sketch_c_grid` (mm Fixed 50 / 5, typed value, inference, own tool, Snap off, inch Adaptive); unit `FullGridSnap` |
| 5 | Auto project edges on reference | Yes (a line ended on another component's edge stayed free; D on another component's edge placed a distance from the origin) | Autodesk forum (the preference decides whether anything outside the sketch can be snapped to); default not documented | Only P projected; Sketch Dimension only inside the sketch's own body | `sketch_reference.py`; hooks in `sketch_draw.DrawTool._mouse`, `sketch_infer._plan` / `_on_projected`, `Dimension._project_under_pointer`; preference | `book_sketch_c_reference`; `book_sketch_b_dimension_edge` still passes |
| 6 | Scale entire sketch at first dimension | Yes (no such behaviour) | Autodesk API reference; forum; default not documented | Not built | `sketch_first_dimension.py`, `DimensionEditor._scale_at_first`, `SketchSession.show_all_if_outside`; preference | `book_sketch_c_scale`; unit `FirstDimension` |
| 7 | World axis colours on a Front-plane sketch | Not looked at | - | - | **Not built** | - |
| 8 | Older sketches keep their helper clutter | Not looked at | - | - | **Not built** | - |
| 9 | Letter-first parameter names in the drawing boxes | Yes (own boxes: the letter ran its tool's shortcut; FreeCAD's boxes: dropped) | Book; Autodesk forum | Own boxes took letters only after a first character; FreeCAD's boxes are C++ number fields | `sketch_draw.Boxes.starts_name` / `offer_names` / `fill_name`, `parameters_complete.starts_a_name` / `offer` / `step` / `lit`; `sketch_field_names.py` (a text box over FreeCAD's box, the number typed on, the dimension bound after the shape) | `book_sketch_c_names` (Line, Rectangle, Circle, a typo, a tool key, the own 2-Point Circle; one Ctrl+Z each) |
| 10 | One edge of an auto-projected face deleted removes all | By reading (`sketch_mode._delete_projected`) | - | FreeCAD's face reference carries all its edges | **Not built** | - |
| 11 | Control frame follows during the drag | By reading (`ControlFrames`) | - | The sketch's curves change only at the release | **Not built** | - |
| 12 | `Name = value`: a number typed later sets the parameter | Yes; and found: a number typed over ANY formula left the formula bound (the next recompute put the old value back) | Autodesk support article (the name belongs to the dimension) | `DimensionEditor.apply` set the datum over the formula | `sketch_named_dimensions.py`, the box's hint, `apply()` sets the parameter; a plain number now clears the formula first | `book_sketch_c_dimension` D, E, F; unit `NamedDimension` |

Tools that still use FreeCAD's own boxes (they take names through the text box now):
Line, 2-Point Rectangle, Center Rectangle, Center Diameter Circle, 3-Point Circle, 3-Point
Arc, Center Point Arc, Ellipse, Center Point Arc Slot, Control Point Spline, Point, the
polygons' Sides field (a plain number field in FreeCAD's panel: numbers only).

## Shared files touched

- `commands.py`: `KEEPS_SKETCH_TOOL` gets the three right-click orientation commands (black
  also wrapped one over-long line next to it).
- `parameters_complete.py` (params): `starts_a_name`, `offer`, `step`, `lit` (the list for a
  box that never has the keyboard). Nothing existing changed.
- `prefs_core.py`, `preferences_ui.py` (shell): two options, "Auto project edges on
  reference" and "Scale entire sketch at first dimension", and their keys in
  `reset_for_tests`.
- `Fission180Tests/gui/harness.py`: `GridSnapFull` and `ScaleAtFirstDimension` off for the
  scenarios written before (next to components' `FirstComponentGrounded`).
- `Fission180Tests/unit/test_book_sketch_a.py`: the tests of the retired patch replaced.
- Scenarios changed: `book_sketch_a_dimension` (check A), `book_sketch_a_centerline` (the
  sign, one Ctrl+Z).

## Changelog lines

- A dimension to a centerline is a diameter again (it had become a plain distance when the
  two sketch builders were merged), and it is now written with the diameter sign.
- While a sketch dimension follows the pointer, right-click and choose Aligned, Horizontal
  or Vertical to turn it.
- A dimension you named by typing `Width = 12` keeps that name: type 40 into it later and
  Width becomes 40 everywhere. The box tells you so.
- Typing a number over a dimension that followed a parameter now really unlinks it (the old
  value used to come back at the next rebuild).
- A parameter's name can be typed straight into the boxes of the Line, Rectangle, Circle and
  the other drawing tools, with the list of names; the dimension then follows the parameter.
- Snap now works like Fusion's: with Snap ticked in the Sketch Palette every point you click
  freely lands on a crossing of the grid lines. Ends, middles, centres, guides and typed
  values still come first. Untick Snap for no pull at all.
- Clicking an edge or corner of the model while you draw, constrain or dimension in a sketch
  projects it into the sketch by itself (purple), also from another body or component.
  Preferences > Design > Auto project edges on reference switches it off.
- The value typed into the first dimension of a sketch scales the whole sketch, so a shape
  drawn by eye keeps its proportions. Preferences > Design > Scale entire sketch at first
  dimension switches it off.
- A line ended on another line near its middle, but not on it, stays where you aimed
  (it used to jump onto the middle and get a midpoint constraint).
- A double-click on a construction line no longer selects hidden helper lines, and a box
  selection no longer catches helper lines or their end points you cannot see.

## Known issues

- A sketch pattern still cannot be edited after OK: undo it, or delete the copies and
  pattern again. Copies of splines and ellipses are not tied to the original.
- With Snap on a click can move by up to half the distance between two grid lines; zoom in
  (the adaptive grid gets finer) or untick Snap.
- A spline's points follow FreeCAD's own grid rule (they only snap close to a grid line).
- Scale entire sketch at first dimension does nothing when the sketch has a spline, a fixed
  curve or anything projected: dimension each size.
- A model edge only lights up once it is projected (after the click), not on the hover.
- Deleting one of the automatically projected edges of a face removes all of them; project
  the ones you want again with P (or click them while drawing).
- A control point spline's dashed frame catches up when you let go of a dragged point.
- Sketch axes are drawn grey; sketches made before 0.1.0-beta.4 keep FreeCAD's helper
  circles and labels.
