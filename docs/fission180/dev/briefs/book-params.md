# Wave 7 builder: params (parameters, expressions, units), branch `sf/book-params`

Read `book-common.md` first. Report lines: bugs 1-4 (75-105); cheat sheet 586-630; Metric Bolt
1366-1419; Drone 1421-1635 (parameters parts); Fire Piston 1644-1660 (units); Pizza Cutter
1976-1991; Strandbeest 2319-2321; Tesla 2157-2160; Tensegrity 1131-1133.

The report calls parameters "Fission's weakest area": the book's parametric drone "does not
work in Fission". Make Change Parameters and every value box behave like Fusion's.

1. **Bug 1, "+" does nothing** (`parameters_ui.py`: `clicked.connect(self.add_parameter)` gets
   Qt's `checked` as the name: confirmed in the code). Fix it, then grep the whole module for
   the same pattern (`clicked.connect(<method with optional arguments>)`, `triggered.connect`)
   and fix each one in your files; list the ones in other builders' files in your report.
   The "+" / "−" buttons drawn as blank white squares: the cause is probably in the style
   sheet (`theme.py`, shell's file; the "..." buttons of the Save dialog show the same): find
   the cause, tell shell's builder through your report, and fix your own buttons.
2. **Fusion's Parameters dialog**: user parameters with name, unit (mm, in, deg, no unit, ...),
   expression, value, comment; **Favorites**; Model Parameters grouped by step, in the
   design's units (an inch design lists inches), including Coil, Offset Plane, Thread, Hole,
   patterns (everything a step has as a number); rename propagation; a clear red message in
   the dialog for an expression that does not evaluate (never a silent "0 mm": the book's
   `min(100;max(45;Arm_Length))` gave 0 mm with the error only in the log).
3. **Bug 4, negative parameters**: a user parameter in mm must hold −2.5 (it is stored as a
   Length, which FreeCAD clamps at 0). Check every unit type for the same clamp.
4. **Unit-less numbers** in an expression are the design's units, like Fusion:
   `min(100;max(45;Arm_Length))`, `Arm_Length + 5`, `2 * (Width + 3)`. Research how Fusion
   treats them (and `,` vs `;` as the argument separator) and match it.
5. **Creating a parameter by typing** `Name = value` (`Thickness = -2.5 mm`, `Width=5mm`,
   `Head_Diam = 8.5`) in any value box, dialog field or sketch dimension box creates the user
   parameter and uses it (research Fusion's exact rule first).
6. **A parameter name typed bare** (`Head_Length`, `Support_Width/2`, `-2 * Arm_Length`) works
   in every value box: sketch dimension boxes (today it needs a leading `=`, and the bare name
   silently keeps the measured value), dialog fields, the on-canvas value boxes, the **Move
   dialog** (today `Arm_Length` gives 0.00 mm and `-2 * Arm_Length` is read as −2 mm:
   silently wrong, the worst kind), pattern quantities ("A pattern of bodies takes a plain
   number as its quantity"). An expression that cannot be used is refused with the reason in
   red, never silently replaced by a number. Find the one place values are parsed and make
   every field use it; where a field belongs to another builder, give them the function
   (`taskui.DistanceField` is in shell's file but its parsing is yours).
7. **Autocomplete** of parameter names while typing in a value box (type `S`, a list with
   Support_Width; Enter or Tab fills it), like Fusion.
8. **Parametric dimensions are marked** like Fusion's `fx:` in the sketch, and a typed
   expression is kept as typed (`9 * 1.02` stays an expression, as Fusion keeps
   "9.00 in * 1.02"): research Fusion, match it.
9. **Bug 2, the design's units silently go back to mm**: after Ctrl+Z of any step, after a
   Change Parameters edit, after some Chamfer OKs. Find where the design's units are stored
   and what resets them (undo of the transaction that set them? a preference written back?
   FreeCAD's own unit schema being re-applied?). The units of a design must survive undo,
   redo, save / reopen and every command, and Ctrl+Z must never undo a units change made
   earlier unless that is the step being undone. Scenario: Inch, then 5 different commands
   with undo / redo between them, the units checked after each.
10. **An inch design is inch everywhere**: sketch grid and snap steps, Model Parameters,
    tooltips ("Type a value (mm)"), the Thread dialog's read-out ("⌀ 25.4 mm") and its default
    standard (ANSI Unified in an inch design, ISO Metric in a mm one, not "the last used":
    thread's files are modify's: give them a `design_is_inch(doc)` helper and say so), every
    dialog's placeholders. Grep for hard-coded "mm" in user-visible strings in your files and
    list the others.
11. **Bug 3, deleting a sketch constraint mis-wires parameter links** (`Support_Width / 2`
    jumped onto another constraint; "Array out of bound: 34, 31"). Reproduce it first: find
    out whether FreeCAD renumbers `Constraints[n]` expressions on delete and which of Fission
    180's own delete paths bypass that (a Python `delConstraint`, the Delete key handler,
    a rebuild of the constraint list). Every path that removes or reorders constraints must
    carry the expressions with it. sketch-b owns the constraint tools: if the cause is in
    their files, write the fix as a helper in yours and name the call sites in your report.
12. Small things: the hole position box showing "-55.00 um" for a value that is 0 (snap tiny
    values to 0 and never show µm in a mm design unless the person typed it); typed Quantity
    "4" keeping 3 until committed (Drone 1544-1546); Change Parameters missing from the
    sketch's MODIFY menu and listed twice in command search (ribbon / search are shell's
    files: a one-line change each, listed).
13. **The parametric drone must survive a parameter change**: "Extrude 1 would break: Sub
    shape not found: Sketch.InternalFace56" (the extrude stores sketch areas by number; lines
    1628-1633). The area references are extrude's (`sketch_area*.py`): work out with that
    builder's branch what is needed, but the acceptance test is yours: a scenario that builds
    a small parametric plate with a circular sketch pattern, extrudes many areas, then changes
    a parameter in Change Parameters several times and checks the solid each time.

Scenarios `book_params_*.py` (at least: the Metric Bolt's parameter table made with "+" and
used bare in sketch dimensions and dialogs; the drone's `min/max` limits; `Name = value`
typed in Extrude and in a dimension; negative parameter; Move with parameters; inch design
through undo / redo / save / reopen; delete a constraint in a parametric sketch; rename a used
parameter; delete a used parameter (warning); autocomplete). Unit tests for all parsing.
