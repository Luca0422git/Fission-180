# Session log: wave 7 builder "params" (parameters, formulas, units), branch `sf/book-params`

To be copied into MEMORY.md by whoever merges (this branch does not edit MEMORY.md,
CHANGELOG.md, VERSION or known-issues.md). Brief: `docs/fission180/dev/briefs/book-params.md`.
Report: `docs/fission180/dev/research/book-parity-report.txt`, bugs 1-4 and the parameter
parts of the Metric Bolt, Drone, Fire Piston, Pizza Cutter, Tesla Turbine, Strandbeest and
Tensegrity projects. No FreeCAD core file changed (nothing for `core-patches.md`). Python only.

Parity notes with sources: `docs/fission180/parity/parameters.md` (new).

## What was reproduced, and what the cause really was

1. **Bug 1, "+" does nothing.** Reproduced by reading (`clicked.connect(self.add_parameter)`:
   Qt's `checked` arrives as `name`). Scanned the whole module for the same pattern
   (`clicked` / `triggered` / `toggled.connect(<method whose first argument is not a
   "checked">)`): no other case (five hits, all something else).
   **Found beside it, not in the report:** the dialog's undo step never held. It was opened
   with `doc.openTransaction()` inside the command that shows the dialog, and FreeCAD closes
   a step opened inside a command when the command returns (`App::AutoTransaction`, unless a
   task panel is shown: `Gui.Control.showDialog` switches that off). So nothing done in
   Change Parameters could be undone, and Cancel put nothing back. Now
   `App.setActiveTransaction("Change Parameters", True)` (persist) and the dialog is modal
   like Fusion's (another command started under it would close the step).
2. **Bug 2, units go back to mm.** Not Undo. Reproduced with one hidden document: FreeCAD's
   `Gui::Document::slotChangePropertyEditor` calls `MainWindow::setUserSchema(that
   document's units)` for every property-status change of any object of any document, and
   `setUserSchema` writes into the **active** document. `App.newDocument(name, label,
   hidden=True, temp=True)` makes the old document active again at once, so everything done
   in the throw-away document after that writes its units (the default: mm) into the design.
   Fission 180 computes a Fillet / Chamfer with a size per set (`fillet_sets._scratch`),
   drafts (`drafting._scratch_document`), imports (`insert._temp_document`) and exports
   (`export.py`, `exchange.py`) in such documents. Every rebuild of a chamfer with two sets
   (its OK, a Ctrl+Z that rebuilds it, a Change Parameters edit) set the design to mm, which
   is exactly the report's three cases. A one-set chamfer is FreeCAD's own and does not.
   Proof: `book_params_units` run with the guard off fails at "Chamfer OK: the design is in
   inches: Standard (mm...)" and stays mm through Ctrl+Z / Ctrl+Y; with it, 156 checks pass.
3. **Bug 3, deleting a constraint mis-wires formulas.** Reproduced headless
   (`sketch.delConstraint`, `delGeometry`, `Constraints = [...]`, Undo). The report's
   diagnosis ("FreeCAD does not renumber") is wrong: FreeCAD renumbers
   (`PropertyConstraintList::applyValues` > `constraintsRenamed` >
   `ExpressionEngine.renameExpressions`), but only formulas bound under `Constraints[n]`.
   Fission 180 bound them under `.Constraints[n]`. Same cause for "parametric dimensions are
   not marked": FreeCAD's "(ƒx)" mark looks the formula up under `Constraints[n]`.
4. **Bug 4, negative lengths.** Reproduced headless (`App::PropertyLength` holds 0 for -2.5,
   no error). `App::PropertyAngle` holds 360 for 720 the same way.
5. **`min(100;max(45;Arm_Length))` = 0 mm**: FreeCAD refuses to compare a length with a
   number ("quantities need to have same unit to compare"); the dialog showed the old value.
6. **Move dialog**: its fields are plain `taskui.DistanceField`s; FreeCAD's number box drops
   what it cannot read (a name) and reads a prefix of `-2 * Arm_Length` as -2.
7. **The drone's "Sub shape not found: Sketch.InternalFace56"** did not reproduce with a
   fully constrained sketch: `book_params_drone` (a hub, 8 spokes, a rim that follows
   Arm_Length, five of nine areas extruded) passes six parameter changes, undo, redo and
   save / reopen on this branch as it is. FreeCAD numbers a sketch's areas the same as long
   as the sketch keeps its areas. In the report's drone the sketch pattern's copies were
   free (sketch-b's item), so a parameter change moved only the original, areas appeared and
   vanished, and the numbers shifted. Run `book_params_drone` again after sketch-b's and
   extrude's branches are merged.

## What was built

- `parameters_core.py` (no FreeCAD, unit tested): a reader for what a person types
  (`read()`): tokens, a small parser, and the kind (length / angle / number) of every piece.
  A number without a unit takes the kind of what it is added to, compared with or put in
  `min` / `max` with; a formula without any unit takes the kind of the box; a number
  parameter used as a length becomes `name * 1 mm` (Fusion writes the same). The formula
  FreeCAD stores is the one Fusion shows. `;` and `,` separate arguments, a decimal comma
  still works, `PI` and `ln` are read, refusals are sentences ("There is no parameter named
  'Arm_Lenght'. Did you mean Arm_Length?"). `split_assignment()` for `Name = value`.
  Parameter names FreeCAD reads as units (W, H, T, h, t, s, g, A, N, e...: 116 words from
  `App/Expression.l`) are kept in a property `F180_<name>`; `to_freecad` / `from_freecad`
  hide that.
- `parameters.py`: `read(doc, text, expect, create)` is the one reader for every value box;
  `user_parameters()` / `derived_parameters()` / `_set()` / `set_model()` keep their shape
  and their millimetres for scripts and the AI tools (the dialog uses `user_rows()` and
  passes the design's unit);
  user parameters with a unit of their own (mm, cm, m, in, ft, deg, rad, none; kept in a
  hidden `Fission180Units` map on the Parameters object), favourites (`Fission180Favorites`),
  the order they were made in (`Fission180Order`; FreeCAD moves a renamed property to the
  end), `rename_user` (FreeCAD 1.1's `renameProperty` updates every formula), `set_unit`,
  `users_of`. Model parameters in the design's units, of every step: an Offset Plane's
  distance (`.AttachmentOffset.Base.z` or the helper frame's Distance / Angle), a coil's
  sizes (through `coil.read` / `coil.update`: several properties hold each value), a
  thread's Length and Offset, a hole's counterbore sizes, any Fission 180 step's shown
  numbers. `set_expression` / `expressions_of` / `fix_document` for bug 3.
- `parameters_ui.py`: the dialog rewritten: "+ User Parameter" (Add User Parameter box with
  a live value and red refusals), Delete, a filter, Favorites, a star in front of every
  row, rename by typing over the name, a unit drop-down, model parameters in the design's
  units. One undo step, modal.
- `parameters_complete.py`: the list of parameter names under a value box while typing
  (Down / Up, Enter or Tab fills, Esc closes only the list). One `QApplication.focusChanged`
  watcher; nothing to add in the files of the boxes.
- `design_units.py` + `design_units_core.py`: each design is held to its units (bug 2);
  `design_is_inch(doc)`, `length_unit(doc)`, `length_text(mm, doc)`, `hint(doc)`; the grid,
  the sketch snap and the drag steps of an inch design are in inches.
- Parsing of `taskui.DistanceField`, `preview.FormulaInput`, `preview.set_formula`,
  `blend_field.ValueField`, `extrude.evaluate`, `sketch_mode.DimensionEditor`,
  `sketch_draw.Field` now goes through `parameters.read`.

## FreeCAD facts and traps

- `MainWindow::setUserSchema` writes the units into `App.ActiveDocument`, whoever asked.
  Any code that makes a second document (hidden or not) can change the active design's
  units. `design_units` puts them back; a script's own `doc.UnitSystem = ...` is told apart
  by looking at the Python statement that is running (`STORE_ATTR UnitSystem`).
- A transaction opened inside a command ends when the command returns, unless a task panel
  is shown or it was opened with `App.setActiveTransaction(name, True)`.
- `sketch.setExpression(".Constraints[3]", ...)` and `("Constraints[3]", ...)` compute the
  same; only the second is renumbered, undone correctly and marked "(ƒx)".
  `dict(sketch.ExpressionEngine)` shows which one a design holds.
- A formula on an `App::PropertyLength` / `PropertyAngle` is not held to the property's
  limits (-2.5 mm, 720 deg stay); a value set directly is.
- In a formula, FreeCAD reads `max(10,20)` as `max(10.20)` (a comma between digits is a
  decimal comma) and `2 pi`, `(5) mm` are errors. `App.Units.Quantity("1 in + 2 mm")` is a
  syntax error (its own small parser): formulas are computed with `obj.evalExpression`.
- `Parameters.W`, `.h`, `.t`, `.T`, `.H`, `.A`, `.N`, `.s`, `.g`, `.e`... do not parse (the
  word after the dot is read as a unit).
- `obj.renameProperty(old, new)` exists in 1.1.4 and rewrites formulas in every object.
- A QTableWidget stores a PySide enum given to `setData(..., CheckStateRole)` so that it
  reads back as unchecked: store 0 / 2.
- A spin box keeps the keyboard focus itself (its line edit's focus proxy):
  `QApplication.focusChanged` names the spin box.
- After a modal dialog closes on a screen without a window manager, the main window is not
  active again by itself and its shortcuts (Ctrl+Z) do nothing: `activateWindow()`.
- FreeCAD's adaptive sketch grid is `GridSize x subdivisions^n`: its base decides the unit.
- **A Python document observer's `slotFinishRestoreDocument` is never called** in FreeCAD
  1.1.4 (`App/DocumentObserverPython.cpp` has no such slot; the list is: Created, Deleted,
  Relabel, Activate, Undo, Redo, BeforeChange / Changed (Document and Object), Created /
  Deleted Object, Recomputed, transactions, dynamic properties, ChangePropertyEditor,
  Start / FinishSave). `thread_ui.py` (cosmetic threads after a file is opened) and
  `undo_fast.py` define it and never get it. Opening a file activates the document twice:
  once empty (before it is loaded), once loaded; `doc.Restoring` is true in between.
- FreeCAD's unit schema "Standard" writes a length under 0.1 mm in µm and one over 10 m in
  m; the only schema that always writes mm ("Metric small parts & CNC") writes pressure as
  kg/(mm*s^2), so it cannot simply be switched to.

## Tests

Scenarios (real input, paced by state), all PASS on the last commit:

| Scenario | Checks | What |
|---|---|---|
| `book_params_dialog` | 88 | "+ User Parameter", refusals, a negative length, the book's min / max, units, names like W / h / t, rename, delete (used: refused), stars, filter, one undo step, Cancel |
| `book_params_sketch` | 72 | bare names in the dimension box, the list of names, `Name = value`, `=name` in a sketch tool's box, `9 * 1.02` kept, refusals, delete a dimension + Ctrl+Z / Ctrl+Y (bug 3), Change Parameters, a design made before opened |
| `book_params_fields` | 69 | `Thickness= -2.5 mm` in Extrude, undo / redo of it, the list of names in a dialog field, a typo, the Move dialog with parameters |
| `book_params_units` | 156 | an inch design through Extrude, a Chamfer with two sets, Fillet, Offset Plane, a Change Parameters edit, five undos and redos, a second design in mm, save / reopen; the inch grid; model parameters in inches (bug 2: fails without `design_units`) |
| `book_params_drone` | 85 | a plate of 9 areas whose rim follows Arm_Length, five areas extruded, six parameter changes, undo, redo, save / reopen |

Unit tests: `test_parameters_read.py` (30), `test_parameters_core.py` (10),
`test_design_units_core.py` (7), `test_parameters_freecad.py` (2, running the 17 cases of
`Fission180Tests/headless/parameters_check.py` in FreeCAD without a window).
Whole unit suite: 3162 tests pass (10 skipped) once the generated docs
are regenerated (the last commit). Golden models: 619 pass, 2 xfail (as before).
Headless AI tools: 465 calls, 0 failed; the AI documentation examples: 180 items, 0 failed.
Older scenarios of the files touched, all PASS: parameters_trial, sketch_explain_box,
sketch_qa, sketch_dim_box_closes, sketch_geometry_keep, sketch_geometry_follow,
sketch_move_dialog, sketch_tools_draw, sketch_tools_circles, sketch_text_basic, undo_fast,
misc_derive, shell_draft_qa_scale, patterns_params, value_box_units, navbar_grid,
vex_qa_inch, vex_qa_inch_sketch, fillet_qa_chamfer, fillet2_chamfer, extrude_presspull_qa5,
gaps_formula_units, inspect_construct, hole_qa, modeling2_sweep_formula, revolve_qa,
bodies_move, sheetmetal_parameters, emboss_flat, sim_setup_units, primitives_qa,
primitives_qa_ring.

## For the other builders (their files; nothing was changed there unless listed)

- **modify** (`thread*.py`): `design_units.design_is_inch(doc)` for the Thread dialog's
  default standard (ANSI Unified in an inch design) and `design_units.length_text(mm, doc)`
  for its read-out ("⌀ 25.4 mm" in an inch design). `pattern.py` / `pattern_ui.py`: a
  pattern of bodies still refuses a formula as its quantity ("takes a plain number");
  `parameters.read(doc, text, "number")` gives the value and the formula. `hole*.py`: the
  position box that showed "-55.00 um": the value is a real -0.055 mm left by the drag (snap
  it to the reference); FreeCAD's box writes lengths under 0.1 mm in µm (see above).
  `fillet_sets._scratch`, `drafting._scratch_document`: give the throw-away document the
  design's `UnitSystem` right after making it and FreeCAD has nothing to carry over
  (`design_units` holds the design either way).
- **shell** (`theme.py`): a bare `QToolButton` outside the ribbon / timeline / nav bar has no
  rule in the style sheet, so Qt draws its own light face with the theme's light text: the
  blank white squares ("+", "−", "..."). `QPushButton` is themed. Also theirs by their
  brief: Change Parameters in the sketch's MODIFY menu, listed twice in the search.
  `insert._temp_document`, `export.py`, `exchange.py`: as for modify's scratch documents.
- **sketch-a** (`sketch_draw.py`, `sketch_mode.py`, changed here, see below): FreeCAD's own
  Line / Circle / Rectangle tools take only numbers in their on-view boxes.
- **sketch-b**: the typed Quantity of the sketch pattern (their brief). `sketch_move_tool.py`
  reads a dimension's formula under either spelling now (changed here).
- **extrude**: `extrude.evaluate` delegates to `parameters.read` (changed here).

**Hard-coded "mm" in user-visible text of other builders' files** (an inch design reads
millimetres there; `design_units.length_text(mm, doc)` writes a length in the design's
units): `fillet_ui.py` (the selection-set rows "%g mm", "r %.2f mm", "chord %g mm", the
radius-point help, the sizes list), `hardware_ui.py` (lengths, "Clearance %g mm", the hole
line), `joints_ui.py` / `joints_motion_ui.py` ("slide %.2f mm", limits), `flatpattern_ui.py`
and `browser_ui.py` ("Flat %.2f x %.2f mm"), `insert_ui.py` / `decal_ui.py` ("%.1f x %.1f
mm" of a canvas, a decal, a mesh), `drawing_ui.py` / `drawing_breakout_ui.py` ("Distance
(mm)", "Depth (mm)", the " mm" suffix of gap and size boxes), `export_ui.py` (" mm" suffix),
`extrude_ui.py` (the "%.1f mm2" area message), `thread_ui.py` (the read-out).

## Shared files touched (the smallest change, each with a comment saying why)

- `taskui.py` (shell): `DistanceField` only (its parsing is this brief's): formula text in a
  field without a formula store, `parse()`, the tooltip, the mark for the name list.
- `browser_ui.py` (shell): `set_units` calls `design_units.set_units` (the units code).
- `extrude.py` (extrude): `evaluate()` body.
- `sketch_mode.py` (sketch-a): `DimensionEditor._current_text`, `_value`, the formula branch
  of `apply()`.
- `sketch_draw.py` (sketch-a): `Field.parse`, `Field.formula`, the call of
  `parameters.bind_typed` in `Tool.make`, "=" / "_" / ";" accepted by the boxes' keys.
- `sketch_move_tool.py` (sketch-b), `scale.py`, `ai/actions/sketch_actions.py`: a sketch
  dimension's formula is found under `Constraints[n]` as well as `.Constraints[n]`.
- `blend_field.py`: `evaluate` / `_finished` / the tooltip.
- Scenarios of other areas whose expected words changed (an unknown name is now refused as
  "There is no parameter named ..."): `sketch_explain_box.py`, `sketch_qa.py`,
  `sketch_dim_box_closes.py`; `parameters_trial.py` (same, and one check reads formulas
  through `expressions_of`).

## Gaps (what Fusion does that this does not)

See "Still different from Fusion" in `parity/parameters.md`. In short: `Name = value` makes
a user parameter (Fusion names the dimension's own model parameter); the mark is "(ƒx)"
after the value; model parameters cannot be named in formulas Fusion's way (d12); FreeCAD's
own drawing tools take numbers only; a pattern of bodies takes no formula (modify); a length
under 0.1 mm is written in µm by FreeCAD's boxes.

## Changelog lines

- The "+" in Change Parameters works: "+ User Parameter" opens a small box for the name, the
  unit, the value or formula and a comment, and says in red what is wrong before anything is
  made.
- A parameter can be negative (Thickness = -2.5 mm), in inches, feet, centimetres, metres,
  degrees, radians or without a unit, and can be called W, H, T, h or t.
- Formulas are written like in Fusion: a number without a unit is in the design's units
  (`Arm_Length + 5`, `min(100;max(45;Arm_Length))`), and the formula is kept as typed with
  the unit added (`9 * 1.02` stays `9 mm * 1.02`).
- A parameter's name can be typed on its own in every value box: sketch dimensions (no "="
  needed), dialog fields, the boxes next to the arrows, the Move dialog. While you type, a
  list offers the matching names; Enter or Tab fills one in.
- Typing `Name = value` in a value box (for example `Thickness = -2.5 mm` in Extrude, or
  `Width = 12` in a sketch dimension) makes that parameter and uses it.
- What cannot be used is refused with the reason in red, in the box or next to the mouse
  ("There is no parameter named 'Arm_Lenght'. Did you mean Arm_Length?"), never replaced by
  another number without a word.
- Change Parameters has Favorites (click the star), a filter box, rename by typing over a
  name (every formula follows), a unit list for each parameter, and lists every size of the
  design in the design's units, also of offset planes, coils, threads and holes.
- Everything done in Change Parameters is one undo step, and Cancel puts the design back
  (neither worked before).
- A design set to inches stays in inches: FreeCAD used to switch it back to millimetres
  after a chamfer or fillet with several sets, an Undo or a Change Parameters edit.
- In an inch design the sketch grid, the snap and the drag steps are in inches, and the
  notes of the value boxes ("Largest that fits here") speak inches.
- Deleting a dimension or a line in a sketch no longer moves the formulas of the other
  dimensions onto the wrong ones, and a dimension that follows a parameter is marked "(ƒx)".

## Known issues

- `Name = value` makes a user parameter, edited in Change Parameters; typing a new number
  into that dimension afterwards unlinks it from the parameter (Fusion would change the
  parameter).
- While FreeCAD's own Line, Circle and Rectangle tools draw, their value boxes take numbers
  only: draw the shape, then double-click the dimension and type the parameter. Fission
  180's own sketch tools (2-Point Circle, slots, polygons...) take `=name` in their boxes.
- A pattern of bodies takes a plain number as its quantity (a pattern of features takes a
  parameter).
- A very small length (under 0.1 mm) is shown in µm in a value box; type it in mm.
- The Move dialog takes a parameter's value when you type it; it does not follow the
  parameter later (its fields hold no formula).
