# Wave 7, the acceptance test, builder replay-g: chapters 7 - 12 of the book (branch `sf/replay-g`, 2026-11-11)

Brief: `docs/fission180/dev/briefs/book-replay.md`. Part of the book: Project 17 "American
Football", Project 18 "Smartphone Case", the Render chapter (out of scope), the Drawings
projects, the Animation project, the Manufacture projects 25 and 26, and Project 27 "Space
Prop Hilt" (report lines 2414 - 2648). Order worked: 27 first (the final exam), then
drawings, animation, manufacture, 17, 18.

The book itself is not in the repository and its downloads cannot be reached: each replay
builds a stand-in to the dimensions the report gives, by real input only (ribbon, keys,
clicks in the view, typed values, browser and timeline), with a user's defaults (full grid
snap, scale at first dimension, first component grounded, layout grid: all ON) and an undo
step left open counted as a failure (`replay_g_steps.defaults_on`).

Helpers: `Fission180Tests/gui/replay_g_steps.py` (new design from Home, New Component by the
dialog, Create Sketch on a plane or a face, Circle / Center Rectangle / Point with typed
sizes, Project (P), Extrude with profile clicks, a free place on a drawing sheet).

## Project 27: Space Prop Hilt (`replay_27_hilt`)

The report did not build the 15-component model ("Not tested... time"). The replay builds a
hilt of six components that uses every tool the report names for this project, in one design:

1. Home > New Design; ASSEMBLE > New Component "Grip" (grounded by itself: the first
   component); sketch on the Top plane, two circles typed 32 and 26, Extrude 120.
2. MODIFY > Chamfer with two selection sets in one feature: 0.4 mm on the top outer edge,
   "+", 2 mm on the bottom outer edge (report 2566).
3. New Component "Emitter"; a sketch on the Grip's top face (another component's face), a
   circle 40, Extrude 30 of the three profiles the Grip's projected edges make: New Body in
   Emitter, the Grip untouched; CREATE > Thread on the 40 mm wall (M40x3 offered).
4. New Component "Pommel"; a sketch on its own Top plane, the view turned with the ViewCube
   to see the Grip from below, Project (P) of the Grip's bottom edge (cross-component: 28
   across), a circle 36, Extrude -15, Fillet 3 on its end.
5. New Component "Switch"; CONSTRUCT > Offset Plane -16 from the Front plane, a sketch on
   it (picked in the browser), Center Rectangle 10 x 40, Extrude -5; a sketch on the plate's
   face with two Points, Hole > From Sketch (Multiple Holes), 3.4 mm, 5 deep (report 2570).
6. INSERT > Hardware (M3 x 10 socket head cap screw; the McMaster-Carr catalogue is out of
   scope): one click on a hole's rim fills both holes, two rigid joints.
7. ASSEMBLE > As-built Joint three times (Emitter, Pommel, Switch to the Grip).
8. MODIFY > Physical Material: Brass on the Emitter, Gold on the Pommel, ABS Plastic on the
   Switch (report 2572); Appearance (A): Powder coat, black on the Grip, Paint, metallic
   black on the Switch, Apply To Faces and LED, red on the Emitter's end face (report 2568,
   2573).
9. Right-click the design's row > Create Drawing (report 2575): Full Assembly, a base view.
10. Workspace > Animation: playhead to 3 s, Auto Explode: One Level with trail lines; back to
    Design (the design did not move).
11. The drawing again (double-click its row in the browser): CREATE > Exploded View (report
    2530) from the Home corner, TABLES > Parts List on it (five rows, the screws as one row
    of quantity 2, Brass / Gold / ABS Plastic in MATERIAL, five balloons), EXPORT > Export
    PDF; Workspace > Design.

Skipped as out of scope: the Render part of the project.

### Hitches found and fixed

| # | What happened | Fusion (source) | Root cause | Fix |
|---|---|---|---|---|
| 1 | As-built Joint: a click on the Pommel took "Switch"; Physical Material and Appearance on the Pommel / the Grip's lower half did nothing. The Switch's offset plane (a large see-through rectangle, still shown after its sketch, as in Fusion) stood in front and took the click | A command only sees what it can use; a plane is no body, the pointer goes through it (Guess, from Fusion's selection filters; Autodesk's forum has no page on this exact case) | FreeCAD gives a click to whatever is drawn in front; `joints.part_of(plane)` is the plane's component | `planes_aside.py` (new): `hold` / `release` switch the planes' pick style nodes (the planes' Selectable switch does not stop FreeCAD 1.1.4 from picking them: checked). `bodies_panel.BodyPanel`: `planes_aside` attribute, `hold_planes()`, released in `cleanup`. `joints_ui.AsBuiltPanel.activated`: aside while the Components box picks. `material_ui.MaterialPanel`, `appearance_ui.AppearancePanel`: `planes_aside = True` |
| 2 | The design's own row had no Create Drawing in its right-click menu (components had it) | "Select any component in the browser, right-click it, and select Create Drawing" (Autodesk, Create a new drawing from a design); the design's row is its top component (Guess for the root) | `browser_core.MENUS["document"]` had no such entry | the entry, and `browser_ui._new_drawing_of_design` (nothing selected: the dialog starts on Full Assembly) |
| 3 | Parts list: "M3 x 10 Socket Head Cap Screw" ran over the DESCRIPTION column ("...ScrewISO 4762") | Fusion's table fits its text (Guess) | fixed column widths in `drawing_core.table_layout` | `drawing_core.fitted_columns`: a column grows to its longest text; unit test `test_table_column_grows_for_a_long_part_number` |
| 4 | In the ANIMATION workspace the offset plane and every joint's mark were drawn (and would be in the published video) | Animation, Simulation and CAM "do not display default construction geometry on the canvas" (Autodesk forum, an Ideastation request); joint marks: Guess | the workspace only moved and hid components | `animation_view.is_extra`, `_hide_extras`, `_show_extras` (display switched off, Visibility untouched, back on leaving); `show` and `restore` call them |

Not hitches (checked): the sketch turns the view to look down on its plane, so the Grip's
bottom edge is hidden behind the Emitter; a person turns the view with the ViewCube (Fusion
the same). A round face shows its seam line (known, MEMORY "Display parity notes").

Scenario `replay_27_hilt`: 260 checks, PASS.

## The Drawings chapter (`replay_drawings`)

Projects 21 + 22 (Drumsticks, Space Prop Emitter) and the drawing parts of 23 + 24 (report
2498 - 2548). Stand-in: a drumstick of three components modelled by hand (Stick 14 x 400 with
a 5 mm round tip, Sleeve 24 x 14 x 60, Butt 24 x 20). DESIGN > Drawing > From Design (ASME,
B), Base View at 1:2, Projected View (right, top, the isometric beyond the corner, Enter:
the report's vanishing third view is kept), Dimension (D) tip to tip 420, Centerline,
Section View (Enter after the cut line, placed left), Detail View B, Leader, Export PDF, Export
DXF; a second drawing with Automatic views (fitted, nothing overlapping), Parts List (three
rows, three balloons), Export CSV, Export DWG (no converter here: the dialog says so and writes
the DXF). 166 checks, PASS.

| # | What happened | Fusion (source) | Root cause | Fix |
|---|---|---|---|---|
| 5 | A Section View whose cut line is near one end of a long part was placed on top of the base view, wherever the click | The section view follows the pointer along its viewing direction (Autodesk, Section View: "move the cursor to place the view") | `SectionPanel.on_move` measured the pointer from the cut line's middle and added that to the parent view's position | `drawing_core.section_position` (from the parent's middle); `drawing_ui.SectionPanel.on_move`; unit test in `test_offset_moves_along_the_side_only` |
| 6 | Export DXF of that drawing printed "makeElementFace: resulting face is invalid" in the Report view | (an error message is never Fusion's answer) | `drawing.section_faces` made one face of the outlines of every body cut (the Sleeve's bore and the Stick's outline are the same circle) | each body is cut by itself |

Not hitches: the report's "MATERIAL shows Steel for parts with no physical material set" is
Fusion's behaviour too (Steel is the default physical material in Fusion; the check says so).

## The Animation chapter (`replay_animation`)

Projects 23 + 24 (Japanese Pull Saw, Machinist Hammer; report 2524 - 2531). Stand-in: a
hammer of three components modelled by hand. Workspace > Animation (sketches not drawn),
Transform Components (Head 60 up at 2 s, Cap 40 down at 4 s), a View action (ViewCube FRONT),
Create Callout with typed text, Space plays to the end, New Storyboard + Auto Explode: All
Levels with trail lines, Duplicate + Reverse of Storyboard1, Publish Video (AVI, frames
counted), Workspace > Drawing > From Animation (four views of the storyboard's end, trail
lines), Parts List, back to Design (nothing moved). 133 checks, PASS.

| # | What happened | Fusion (source) | Root cause | Fix |
|---|---|---|---|---|
| 7 | Drawing > From Animation with Storyboard2 in front drew Storyboard1 | The drawing is made from the storyboard chosen; it starts on the active one (Guess; Autodesk's help: "From Animation" uses the animation's storyboards) | `NewDrawingCommand.run` and `ExplodedViewCommand.run` took `storyboards(doc)[0]` | `drawing_exploded.front_storyboard` (the tab in front); both commands use it |

## The Manufacture chapter (`replay_manufacture`)

Projects 25 + 26 (report 2550 - 2560). Stand-in: a board 200 x 60 x 12 with a recess and two
6 mm holes modelled by hand (Hole > From Sketch on two sketch Points). Workspace >
Manufacture, New Setup (stock: a box round the part, 1 mm over its top), Tool Library (both
sample libraries), 2D Adaptive (6 mm end mill) in the recess, 2D Contour round the outline
with Multiple Depths, Drill (Select Same Diameter), Simulate (no rapid into the stock), Post
Process (the checker passes the G-code), a second setup (Flip Z, stock From preceding setup)
with Face, back to Design (the board unchanged, the timeline as it was). 97 checks, PASS.

| # | What happened | Fusion (source) | Root cause | Fix |
|---|---|---|---|---|
| 8 | CREATE > Point: a point clicked at y 15 on a 10 mm grid stayed at 14.82 (every other tool snaps the click to the grid; the holes then were 30.2 mm apart, not 30) | Snap puts every sketch point on the grid (Fusion's Snap, the same rule as the other tools: book-sketch-c) | the sketch inference did not know the Point tool (`sketch_infer_core.TOOLS`), so FreeCAD's own grid rule (a fifth of the spacing) applied | `sketch_infer_core.TOOLS["Sketcher_CreatePoint"] = "point"`, `POINTS["point"] = 1`, `tool_kind`; unit test `test_the_point_tool_is_a_shape_of_one_click` |

Not replayed (not built, book-cam.md "Known issues"): rest machining, NC Program objects,
machine definitions.

## Project 18: Smartphone Case (`replay_18_phone_case`)

Report 2464 - 2477. The phone (an .f3d download: out of scope) is modelled by hand, 70 x 150
x 10, in component Phone; Case: a 76 x 156 x 8 block in its own component; INSPECT >
Interference (84000 mm3), Combine Cut with the Phone as tool (another component's body),
Keep Tools: a 3 mm frame; Interference again: none; a pin (component Button) along the
case's bottom through its wall, Combine Cut: a notch, no warning (the report's "Cut would
leave nothing of the target body" did not come back); Oak, Texture Map Controls Box at 28 %.
104 checks, PASS.

| # | What happened | Fusion (source) | Root cause | Fix |
|---|---|---|---|---|
| 9 | Interference listed the pair as "Body1 / Body1" (each component's first body is Body1) | Fusion names a body with its component where the name is not enough (Guess) | `analysis` used `o.Label` | `analysis._pair_name` (bodies.shown_name: "Body1 (Phone)") in `InterferenceFeature.execute` and `overlaps` |

## Project 17: American Football (`replay_17_football`)

Report 2423 - 2461. Inch design (browser Units row > Change Active Units). INSERT > Canvas on
the Front plane, Z Angle 1, Calibrate 11.25 in; the profile: L typed 11.25, X, a construction
line 3.4 up from the middle, Fit Point Spline, Mirror about the construction line, Tangent
between the two splines (the report's "added nothing" is fixed: smooth and level at the top);
Revolve 90 about X, Fillet 1/8 on the two curved edges, Circular Pattern (Bodies) x 4,
Combine (target + 3 tools: one body, the tools out of the browser), Display Settings > Visual
Style, Leather, brown; Duplicate, renamed "Football leather" at 50 % (Advanced opened);
INSERT > Decal on the curved side with Chain Faces, a right-click in the browser while it is
open keeps it. 90 checks, PASS.

| # | What happened | Fusion (source) | Root cause | Fix |
|---|---|---|---|---|
| 10 | Fillet "1/8" typed in an inch design and OK clicked: a 1 in fillet that ate the ball's tips (the preview had taken the "1" typed first, and OK that) | A value box takes what is typed when OK is clicked (Autodesk: expressions such as 1/8 in are allowed in every value box) | `blend_field.ValueField` settles a formula only on Enter / Tab / leaving the box; FreeCAD's task OK button does not take the focus | `ValueField._whole_formula` (a complete formula is previewed while typing), `ValueField.settle`; `fillet_ui.BlendPanel.accept` settles every box first (Chamfer too) |

Not replayed: the laces (Sketch Offset, Sweep, Pattern on Path; "not re-tested" in the
report; replayed by the Carabiner and Hot End scenarios).

## Out of scope (skipped, per the brief)

The Render workspace (Projects 19 + 20 entirely, the render parts of 17, 18 and 27);
`.f3d` files (the phone); McMaster-Carr (INSERT > Hardware stands in); the book's downloads
(stand-ins built to the report's dimensions).

## FreeCAD facts

- A datum plane's `ViewObject.Selectable = False` does not stop `getObjectInfo` / a click
  from picking it (FreeCAD 1.1.4). Its view has two `SoPickStyle` nodes; the inner one
  decides. Setting both to UNPICKABLE lets the click through to what is behind.
- A task panel's OK button takes no focus: a `QuantitySpinBox` being typed in gets no
  `editingFinished` before the dialog's `accept` runs.
- `Part.makeFace` of the slices of several touching bodies at once can be invalid where two
  outlines coincide; per body it is fine.

## Tests

Final run through `run_tests.sh`, one scenario after the other: replay_17_football 90,
replay_18_phone_case 104, replay_27_hilt 260, replay_animation 133, replay_drawings 166,
replay_manufacture 97: all PASS. Unit: 3682 tests, 2 failures: `test_vex_qa_freecad`
"parts_list_assembly_twice" (known on develop, another builder's) and the parity checklist
(regenerated in a commit of its own, then OK). Golden: 649 pass, 2 xfail (as before).

Found on the way, not mine: `fillet_qa` fails 9 checks ("P4 one fillet": `blend_steps.blends()`
of `h.body()` is empty after OK although the fillet is there) on the untouched base 39fd9e9b
too (checked on an export of that commit). `fillet_live` failed once on a speed check under
load and passed on its rerun (and on the base).

Each replay alone, one run each (`.probe/run1.sh`, the harness's own runner without the
retry): replay_27_hilt 260, replay_drawings 166, replay_animation 133, replay_manufacture 97,
replay_18_phone_case 104, replay_17_football 90: PASS. Older scenarios of the files changed,
each alone, PASS: book_animation_workspace 75, book_animation_explode 79,
book_animation_book_project 51, book_animation_switching 76, book_animation_publish 67,
book_joints_edit 105, book_looks_faces 106, book_looks_materials 104,
book_drawings_partslist 64, book_drawings_component 53, book_drawings_animation 65,
book_drawings_views 69, book_drawings_exploded 95, book_drawings_export 83,
book_hardware_holes 56, drawing_section 34, drawing2_sections 77, drawing_export 76,
drawing2_sheets 87, drawing2_update 40, drawing2_reopen 44, drawing_reopen 44,
drawing2_breakout 96, drawing_pdf_layers 55, sketch_infer_tools 162, sketch_snaps 113,
hole_sketch 49, inspect_com_interference 79, inspect_qa3 352, inspect_qa4 330.

## Changelog lines

- As-built Joint, Physical Material and Appearance: a click on a part that stands behind a
  construction plane now takes the part (the plane no longer catches the click).
- Right-click the design's own row in the browser > Create Drawing draws the whole design.
- A parts list's columns grow to fit long part numbers (a screw's name no longer runs into
  the next column).
- The ANIMATION workspace no longer draws sketches, construction planes or the joints'
  marks: only the parts, as in the video it publishes.
- Drawing: a Section View follows the pointer to where it is clicked (a cut near the end of
  a long part put it on top of its base view).
- Drawing: Export DXF of a section through two parts that touch no longer prints an error.
- Drawing > From Animation and CREATE > Exploded View start on the storyboard that is in
  front in the ANIMATION workspace (it was always the first).
- Sketch: CREATE > Point snaps to the grid like every other tool.
- Interference names each body with its component when two bodies have the same name.
- Fillet and Chamfer: a fraction or a sum typed in a box ("1/8") is previewed as you type,
  and OK takes it (it took the first digit).

## Known issues

- The laces of the American Football (Sketch Offset, Sweep, Pattern on Path) were not
  replayed here; those tools are covered by the Carabiner and Hot End scenarios.
- A canvas is placed with its middle on the plane's origin: drag it (or type X Distance)
  to line the picture up with the sketch, as in Fusion.
- Rendering, `.f3d` files and McMaster-Carr parts stay out of Fission 180: use File >
  Capture Image, STEP files and INSERT > Hardware.
- Export DWG needs a converter program (LibreDWG, the ODA File Converter or QCAD); without
  one the dialog writes a DXF.
