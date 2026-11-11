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

## FreeCAD facts

- A datum plane's `ViewObject.Selectable = False` does not stop `getObjectInfo` / a click
  from picking it (FreeCAD 1.1.4). Its view has two `SoPickStyle` nodes; the inner one
  decides. Setting both to UNPICKABLE lets the click through to what is behind.

## Changelog lines

- As-built Joint, Physical Material and Appearance: a click on a part that stands behind a
  construction plane now takes the part (the plane no longer catches the click).
- Right-click the design's own row in the browser > Create Drawing draws the whole design.
- A parts list's columns grow to fit long part numbers (a screw's name no longer runs into
  the next column).
- The ANIMATION workspace no longer draws sketches, construction planes or the joints'
  marks: only the parts, as in the video it publishes.

## Known issues

- (to be completed at the end of the session)
