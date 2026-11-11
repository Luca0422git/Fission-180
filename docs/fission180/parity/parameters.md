# Parity: parameters, formulas and units (wave 7, the book parity report)

Area: MODIFY > Change Parameters, every value box (dialog fields, sketch dimension boxes, the
boxes next to handles), the design's units. Files: `parameters_core.py` (reading what was
typed, no FreeCAD), `parameters.py` (the design side), `parameters_ui.py` (the dialog),
`parameters_complete.py` (names offered while typing), `design_units.py` (the units of a
design), the parsing of `taskui.DistanceField`, `preview.FormulaInput`, `blend_field.py`,
`sketch_mode.DimensionEditor`, `sketch_draw.Field`.

Source marks: **Autodesk** (help.autodesk.com, Autodesk blog / Learn, the Fusion API
reference), **Forum** (forums.autodesk.com), **Book** (the parity report quoting *Mastering
Autodesk Fusion*, 2nd ed.), **Guess**. autodesk.com is only readable through search excerpts
from the sandbox.

## What Fusion does

| # | Behaviour | Source |
|---|---|---|
| 1 | The Parameters dialog lists Favorites, User Parameters and Model Parameters; "+ User Parameter" opens Add User Parameter (Name, Unit, Expression, Value, Comment); a new user parameter appears under Favorites | Autodesk (help "Parameters reference", Learn "Sketch basics": "click + User Parameter ... Name box ... Set the Unit to mm ... Expression") |
| 2 | Any user or model parameter can be starred into Favorites; a model parameter named while modelling is added to Favorites by itself | Autodesk (blog "Mastering Fusion parameters") |
| 3 | A parameter has a unit (mm, in, deg, No Units...); "No unit" is a number | Autodesk (help "Unit types") |
| 4 | A number without a unit is in the document's default units ("6.25 ... interpreted based on whatever the default units are for the document") | Autodesk (API reference, `Parameter.expression`) |
| 5 | A unitless parameter used where a length is meant is rewritten by Fusion as `name * 1 in` (the document's unit) | Forum ("User Parameters set to No Units behave like they are set to units downstream") |
| 6 | The expression is kept and shown with units added (`9.00 in * 1.02`) | Book (report line 2158) |
| 7 | Function arguments are separated by `;` (`pow(expr1; expr2)`, `max(a; b)`) | Autodesk (help "Parameters reference"; Inventor's expression reference lists `max(expr1;expr2)`) |
| 8 | A parameter name is typed bare in any value box (`Head_Length`, `Support_Width/2`), with a list of matching names while typing; Enter fills the name | Autodesk (Learn "Sketch basics"), Book (report 1464) |
| 9 | Typing `width=30` in a sketch dimension or a feature input makes a parameter of that name; it is listed (favourite) and usable everywhere | Autodesk (blog "Mastering Fusion parameters": "type the parameter name ... e.g. width=30"; Learn video: "type a parameter name, the equals sign, and the value") |
| 10 | A dimension driven by a parameter or formula shows `fx:` before its value | Autodesk (Learn "Sketch basics": "fx preceding the value"), Forum |
| 11 | A user parameter that another parameter or a feature uses cannot be deleted ("Parameter deletion failed ... it is used in the expression of another parameter") | Forum (thread 8492871), Autodesk (API `UserParameter.deleteMe`) |
| 12 | Renaming a parameter updates every expression that names it | Guess (the dialog's Name cell is editable; expressions hold references) |
| 13 | The Parameters dialog is modal (a non-modal one is a feature request) | Forum (thread 12575090) |
| 14 | Model Parameters are grouped by component, then by feature / sketch, and shown in the document's units | Autodesk (help "Parameters reference") + Book (report 1657: an inch design should list inches) |
| 15 | The design's units are set per design (Document Settings > Units > Change Active Units, "Set as Default") and never change by themselves | Autodesk (help), Book (bug 2) |
| 16 | In an inch design the thread type offered first is an inch one (ANSI Unified) | Book (report 1674, 1991). Not checked against Autodesk's help |

## Where the report was wrong

- **Bug 3, "the expressions on later dimensions don't renumber".** FreeCAD does renumber them
  (`PropertyConstraintList::applyValues` > `SketchObject::constraintsRenamed`), but only
  formulas bound under the path `Constraints[n]`. Fission 180 bound them under
  `.Constraints[n]`; that spelling is computed the same but not matched by the renumbering.
  The fix is the spelling, not a renumbering of our own.
- **"Parametric dimensions show 53 mm, not fx".** Same cause: FreeCAD marks a parametric
  dimension with "(ƒx)" and a colour of its own, when the formula is bound under
  `Constraints[n]`. It never matched. Now it shows (after the value, not before it as in
  Fusion: the text is built in FreeCAD's C++).
- **Bug 2, "Ctrl+Z resets the units".** Undo is not the cause. Any rebuild of a Fillet or
  Chamfer that has a size per selection set (computed in a hidden throw-away document) wrote
  that document's units (the default, mm) into the active design, through FreeCAD's window
  code (`Gui::Document::slotChangePropertyEditor` > `MainWindow::setUserSchema`, which writes
  into the *active* document). Ctrl+Z, a Change Parameters edit and the chamfer's own OK all
  rebuild that step. A plain one-set chamfer does not use the hidden document, which is why
  it happened "after some Chamfer OKs" only.
- **Bug 1's fix, "connect to lambda: self.add_parameter()".** Right about the cause, but the
  dialog had a second, bigger fault the report could not see: its undo step was closed by
  FreeCAD as soon as the command that opened the dialog returned, so nothing done in it could
  be undone and Cancel put nothing back.
- **Bug 4, "stored as a Length".** Right. New length parameters are `App::PropertyDistance`;
  a length parameter of an older design takes a negative value as a formula (`-2.5 mm`).
- **"Typing Head_Diam = 8.5 should create a user parameter".** In Fusion it names the model
  parameter of that dimension (and stars it). Fission 180 makes a user parameter of that name
  and binds the dimension to it: the name works everywhere and is in Favorites, as in Fusion;
  the difference is where the value is then edited (Change Parameters, not the dimension).

## What Fission 180 does now

| # | Fusion | Fission 180 | Proof |
|---|---|---|---|
| 1 | + User Parameter | A real button with its words; Add User Parameter with Name, Unit, Expression, Value (live), Comment; refusals in red in the box | `book_params_dialog` A, B |
| 2 | Favorites | A star in front of every user and model parameter; a Favorites list on top; new user parameters are starred | `book_params_dialog` A, H |
| 3 | Units per parameter | mm, cm, m, in, ft, deg, rad, No Units; shown and typed in its own unit; the Unit cell is a drop-down | `book_params_dialog` E |
| 4-6 | Unitless numbers | `parameters_core.read`: numbers of a sum, of `min` / `max`, of a comparison take the kind of the other side; a formula without any unit takes the box's kind; the formula stored and shown has the units added | unit tests `test_parameters_read.py`; `book_params_dialog` C, D; `book_params_sketch` D |
| 7 | `;` | `;` and `,` both separate arguments (`max(10,20)` is two numbers; FreeCAD read 10.20); a decimal comma still works (`2,5`, `max(2,5; 3)`) | unit tests |
| 8 | Bare names, the list | Every value box; the list opens under the box (Down / Up choose, Enter or Tab fill, Esc closes) | `book_params_sketch` A, B; `book_params_fields` |
| 9 | `Name = value` | In a sketch dimension box, a dialog field, a box next to a handle, a sketch tool's box: makes the user parameter (the box's kind, the design's unit), stars it, binds the value to it. An existing name is refused with what to do | `book_params_sketch` C, E; `book_params_fields` |
| 10 | `fx:` | FreeCAD's own "(ƒx)" mark after the value | by eye (`book_params_sketch-B-names.png`) |
| 11 | Delete in use | Refused in red with what uses it (other parameters, steps by their timeline names) | `book_params_dialog` G |
| 12 | Rename | Type over the name; every formula follows (`renameProperty`), the row keeps its place | `book_params_dialog` F |
| 13 | Modal | Modal, one undo step, Cancel puts everything back | `book_params_dialog` I |
| 14 | Model parameters | Grouped by step, in the design's units, including Offset Plane, Coil, Thread, Hole, patterns, primitives (every number a step shows) | `book_params_units` F |
| 15 | Units stay | `design_units.py` holds each design to its units | `book_params_units` (149 checks; fails without the guard) |
| 16 | Thread default | `design_units.design_is_inch(doc)` for the thread builder | see the session log |

Names: W, H, T, h, t, s, g, A, N... are fine as parameter names (FreeCAD reads them as units:
watt, henry, tesla, hour, tonne...; such a parameter is kept in a property called `F180_<name>`
that the person never sees). mm, cm, m, in, ft, deg, rad, pi and the function names stay
reserved.

## Still different from Fusion

- `Name = value` makes a user parameter, not a named model parameter (see above).
- The `fx` mark is "(ƒx)" after the value, not "fx:" before it (FreeCAD's C++ draws it).
- Model parameters have no names of their own (d1, d2...) that a formula could use; a sketch
  dimension can be named in FreeCAD's way (`Sketch.Constraints.name`), a feature's value as
  `Pad.Length`. Fusion's `d12` style is not built.
- While FreeCAD's own Line / Circle / Rectangle tools draw, their value boxes take numbers
  only (FreeCAD's on-view parameters, C++). Fission 180's own sketch tools take `=name`. A
  letter typed first is the letter's shortcut, as in Fusion while a tool runs.
- Units Fusion also offers for a parameter (mass, time, area...) are not offered: mm, cm, m,
  in, ft, deg, rad and No Units are.
- `log` is the natural logarithm (FreeCAD's); `ln` is accepted too. Fusion's `log` is base 10
  (Inventor's is): type `log10` for that. `sin(30)` reads 30 as degrees (FreeCAD); Fusion
  wants `30 deg`.
