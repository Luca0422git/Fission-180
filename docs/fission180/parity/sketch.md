# Parity spec: the SKETCH workspace (outline 7.5)

Source: Fusion's documented behaviour and everyday use. Not yet checked against Luca's own
screen captures (outline 2.4). Implemented in `src/Mod/Fission180/fission180/sketch_*.py` on top of
FreeCAD 1.1.4's Sketcher. Status: **first pass + QA pass, not yet signed off**.

## Values past what fits stop at the limit (Luca's decision, 2026-10-21)

**This deliberately differs from Fusion.** Fusion refuses a value that does not fit (a
radius too big, a wall too thick, an angle too steep) with an error, and the dialog waits
until a smaller value is typed. Luca (2026-10-21): "limit edits to stop at that limit, so if
I want to chamfer something to the max I can quickly drag it without having to type
whatever obscure value the error spits out", and "add the functionality to any tool that
can give that sort of error". So in Fission 180 (shared helper `fission180/value_limits.py`):

- an arrow (or disc) dragged past the limit stops there, like the end of a slider; the
  preview shows that result and a blue note under the message says "Largest that fits
  here: 3.47 mm" ("Furthest that fits here" for a limit on the other side: a push into the
  part, a negative angle); OK works at once;
- a plain number typed past the limit is set to it and the note says so: "5 mm does not
  fit: limited to 3.47 mm" (the box keeps what is being typed and shows the limit once it
  is left);
- the limit is found once (a time-budgeted bisection), rounded toward the safe side to the
  box's precision (0.01 mm, 0.1 deg) and built once more to be sure; it is kept for the
  inputs it was found for (the part, the picks, the other values), so a drag never runs a
  search on every mouse move;
- a value from a formula or parameter ("width / 2") is never rewritten: the dialog keeps
  the explanation, with "Largest that fits here: ..." added, and OK waits.

In sketch mode: Fillet (the radius: the pointer far out or a typed number; Enter makes the
largest fillet that fits and the text by the pointer says so) and Chamfer between two
lines (Distance and Distance 2). Not held: the chamfer's angle and a chamfer between a
line and an arc (their refusals stay). `sketch2_fillet` B updated. Offset (2026-11-02):
an inner offset wider than the curves allow stops at the largest that fits (section
"Sketch Offset with Fusion's OFFSET panel").

**The largest sketch fillet or chamfer takes the curve whole** (2026-10-22, integration
fixes). In a sketch the limit is where the fillet or chamfer reaches the far end of a curve.
It is worked out exactly (not rounded to the box's precision, which left a sliver: a 30 mm
equal chamfer on a 17.1132 mm side was held at 17.11 and left a line of 0.003 mm), and a
value within the box's precision of it (0.01 mm) counts as that largest one too. The curve
the fillet or chamfer uses up is not cut to nothing: it stays whole as a construction line
(or arc) with every constraint and dimension it had, and the chamfer line or fillet arc
ends at its far end, joined to whatever met it there (the fillet arc tangent to it). The
note says "30 mm does not fit: limited to 17.11 mm" (typed) or "Largest that fits here:
17.11 mm" (pointer). A sketch that was fully constrained stays so; the chamfer's dimension
on the used-up side is a reference (the side fixes it). Scenarios `modeling2_sketch` (2),
`sketch2_fillet` (B).

## Luca's fourth round (patch 0.1.0-beta.3.3.4, `develop`, 2026-11-06)

Source: Luca on 0.1.0-beta.3.3.3 (four screenshots: Trim on a rectangle's top under a
control-point spline that ends on the line 15 mm short of the corner; after the trim the
line's new end sits left of the spline's end, the spline's last segment at another angle):
"THIS IS SUPPOSED TO BE CAD. IT HAS TO BE ACCURATE"; the check then Trim; "spline just does
not snap"; the Feature Options' selected type was orange. Scenario
`sketch_trim_after_spline` (his steps, on the Fission 180 AppImage), headless
`trim_accuracy_check` (unit `test_trim_accuracy_freecad`).

| Fusion (source) | Fission 180 before | Fission 180 now |
|---|---|---|
| Trim removes the piece between the crossing curves and moves nothing else (Autodesk "Trim or extend sketch geometry") | FreeCAD's `trim` stops at every curve, a spline's control-point circles too: the line was cut at the end pole's circle (x = 44 for a spline ending at 45) and its new end tied PointOnObject to that circle; the solve then moved the spline (reproduced headless on the AppImage) | Lines, arcs, circles: `sketch_modify_tools._trim_exact` splits at the piece's exact ends with FreeCAD's `split` (exact, its constraint transfer), deletes the piece (FreeCAD's delete keeps corners joined), joins each end left to the crossing curve: Coincident on that curve's end when it ends there (`cut_at`), else PointOnObject, the stale PointOnObject dropped. Other curves: FreeCAD's trim + leftovers. Every trim: `snapshot` / `moved_curves` (by geometry tag; a spline's knot points FreeCAD makes anew are matched by place) to 1e-6 mm, else `TrimRefused` (the undo step is aborted, a note says so). 40 headless checks: spline ending on the line, corner to corner, fit spline, circle between lines, dimensioned line |
| Spline points snap like every sketch point (ends, midpoints, centres, intersections, inference lines) | FreeCAD's spline tools were not in `sketch_infer_core.TOOLS`: no Fission 180 snap, dot or guide; only FreeCAD's 5-pixel pick | Kind "spline" (every click a point, no direction); a spline started another way is told by FreeCAD's spline panel; after each click the point / control circle centre is moved exactly onto the snap (`_spline_exact`, in the spline's undo step; no constraint of ours then: FreeCAD adds its own at the end, two would be redundant); once the spline exists its ends that snapped onto something get the right tie (`_spline_ties`: Coincident on a point, FreeCAD's PointOnObject on a line through it dropped; checked, redundant ones not added). A spline's control circles are no snap target for any tool (their quadrants and crossings mean nothing; a fit point snapped onto one broke FreeCAD's next spline) |
| Fusion's palette colours: blue for the current choice | The selected type was orange (#f5a142) | The theme's blue (#3fa9f5) |
| Any tool replaces the running one | Not reproduced (the ribbon button, T and the right-click menu start Trim after the check, with FreeCAD's tool making the spline and with Fission 180 making it) | `sketch_draw.run` and `give_way` also stop FreeCAD's tool when its spline panel shows (its pointer may not be on the view) |

## Luca's third round (patch 0.1.0-beta.3.3.3, `develop`, 2026-11-05)

Source: Luca on 0.1.0-beta.3.3.2 (Windows): OK in the right-click menu still lost the spline
and left its orange points; the green check vanished when the pointer went onto it (only
after that did OK work); no box selection in Mirror; Select in the toolbar closed the sketch;
"make some unique icons for the different sketch tools".

| Fusion (source) | Fission 180 before | Fission 180 now |
|---|---|---|
| OK in the marking menu, the check, Enter and Finish Sketch make the spline being drawn | "A spline is being drawn" was asked again at OK time from signs that can change meanwhile (the 3D view's cursor, the last recorded command, FreeCAD's tool panel); when one said no, the tool was ended as a cancel and the points stayed | `_spline_from` (the curve count at the spline's first click) and its loose points are the sure sign (`SketchSession.spline_drawn`); every exit (finish_tool, give_way, escape, Finish Sketch) uses it. Safety net `rescue_spline` (the check's 100 ms timer): no spline tool, no panel, no own tool for 3 ticks while its points are loose: the spline is made from them (one point: removed). Scenario `sketch_spline_luca` K (the tool forced unrecognised), L (FreeCAD's tool stopped behind Fission 180's back) |
| The check stays by the last point until clicked | Its place came from counted presses while the spline tool was recognised | Anchored on the spline's last loose point in the sketch. Scenario `sketch_spline_luca` J (pointer resting on it for 5 ticks) |
| A three-point fit spline's points are its own | FreeCAD 1.1.4 ties the middle point of a three-point spline with PointOnObject (no knot there), not InternalAlignment: it counted as loose (and could be taken into the next spline) | `sketch_spline.on_a_spline`; unit `test_sketch_spline` |
| Box selection: left to right takes what is fully inside, right to left what the box touches (Autodesk "Select objects") | The Mirror tool took the mouse: dragging did nothing | `sketch_mirror_core.boxed` (screen pixels, unit tested) with `sketch_select_core.box_plan` (Shift adds, Ctrl toggles); a dashed box shows. Scenario `sketch_mirror_dialog` H |
| Select ends the running command, the sketch stays open | Select closed the open dialog the way Finish does: the sketch was left | In a sketch, Select ends the tool and any pick in wait only. Scenario `sketch_mirror_dialog` I |
| Each tool type has its own icon | One icon per family | 22 original icons (`tools/fission180/icons_sketch_types.py`): the shape and, in blue, the points clicked; used in the ribbon, menus, marking menu and Feature Options (now icon and name). Fusion's icons are not copied |

## Luca's second round (patch 0.1.0-beta.3.3.2, `develop`, 2026-11-04)

Source: Luca on 0.1.0-beta.3.3.1, two screenshots (Trim on a rectangle's top under a
control-point spline: the red piece stops short of the corner; fit points left in orange
over a rectangle). Everything below was reproduced or checked on the released Fission 180
AppImage itself (not only on stock FreeCAD), scenario `sketch_spline_luca`.

| Fusion (source) | Fission 180 before | Fission 180 now |
|---|---|---|
| The spline being drawn is made by the green check / OK / Finish Sketch, however it was started | "A spline is being drawn" came from the last recorded command: the command search did not record, FreeCAD's own menus do not; then the green check belonged to the Line chain left on from before (its click ended the "chain", the spline went) and Finish Sketch dropped it; fit points stayed. Not reproduced on Linux with the menus: the state that loses it is how the tool was started | `_spline_tool()` also reads FreeCAD's tool panel (TaskSketcherTool shown, header "B-Spline ..."); the check prefers the spline over a Line chain; `_commit_spline` checks a spline came of FreeCAD's Esc, else `sketch_spline.plan/build` make it from the loose points (fit points: interpolated; control circles: their poles), ends re-joined, the points removed, FreeCAD's tool stopped and restarted; Esc removes the points of a cancelled spline even when they were outside its undo step (`_spline_from`: the curve count at its first click). Search records what it runs. Unit `test_sketch_spline`; scenario `sketch_spline_luca` F, F2, G, H |
| Trim removes the piece between real curves (Autodesk "Trim or extend sketch geometry") | Pieces were cut at every curve, a spline's control-point circles too (FreeCAD's construction helpers: Fusion's spline has none): 1 mm of the rectangle's top stayed at each corner; the preview (Fission 180's) and the trim (FreeCAD's `trim`) also disagreed | `sketch_build.internal_geometry` (InternalAlignment helpers) are neither cutters nor targets for Trim, Extend, Break; `trim_piece` removes what FreeCAD's trim left inside the previewed piece. `sketch_spline_luca` C |
| Command search finds a tool by its menu name | Only FreeCAD's command names: "Control Point Spline" ran "Toggle B-Spline Control Point Weight" | Fission 180's menu entries are listed by their labels; a full-phrase match ranks first (`search_core.score`). Unit `test_search_core` |
| Sketch Mirror: the MIRROR panel, Objects then Mirror Line, OK; Symmetry constraints (Autodesk "Mirror sketch geometry") | Click curves, Enter, then FreeCAD's Symmetry tool for the line, no panel | `sketch_mirror_tool.py` (panel, picks, preview, OK / Enter / Cancel / Esc); `SketchObject.addSymmetric`, copied constraints other than Coincident / InternalAlignment dropped, Symmetric / Equal ties as FreeCAD's own `addSymmetryConstraints` pairs (`sketch_mirror_core.ties`, unit tested), redundant ones left out. Preselected curves = Objects, Mirror Line active (**Guess**). Scenario `sketch_mirror_dialog` |
| Sketch Palette Feature Options: switch rectangle / circle (arc, polygon, slot, spline) types while the tool runs (Autodesk "Create rectangles", "Create circles", Sketch Palette reference) | None | `sketch_palette.FeatureOptions` from the SKETCH > CREATE submenus (`sketch_feature_options`, unit tested): the types as buttons, the current one lit, a click ends the running tool and starts that type. Fusion's own type icons are not copied: the type names are shown. Scenario `sketch_feature_options` |

## Luca's polish list (patch 0.1.0-beta.3.3.1, `develop`, 2026-11-04)

Source: Luca's message of 2026-11-04 with a screenshot of Fission 180 (a control-point spline
over a profile, a line drawn down at 90 degrees onto the bottom line: no mark at the corner).

| Fusion (source) | Fission 180 before | Fission 180 now |
|---|---|---|
| Finish Sketch (the green check) while a spline is drawn: the spline is made, as with Enter (Luca: "it should also work when pressing the checkmark ok") | Every SKETCH command first ends the running tool (`give_way`, "another tool replaces it"), which drops a half-drawn spline as Esc does; and the spline test (`_spline_tool`) asked whether the *last* command was a spline tool, which by then was Finish Sketch. The spline vanished, its poles / fit points stayed in the sketch as loose construction circles and points | Finish Sketch does not give way (`_SketchCommand.gives_way`); `finish_sketch` runs `finish_tool` first (Fusion's OK): FreeCAD's spline is made from the points clicked, Fission 180's own tool makes what it can (`on_finish`: conic, Offset, Project to Surface, 3D Spline). `recent.running_tool()` looks past Finish Sketch (recorded before it runs). Scenario `sketch_spline_ok` G (fails on the old code: 4 loose circles) |
| One Ctrl+Z takes a spline back | Two: FreeCAD records the constraints of the spline's ends as their own step "Add Auto-Constraints" after "Add Sketch B-Spline" | That step is undone / redone with the spline step before it (`sketch_mode._glued_next`, only after a spline: FreeCAD's Line keeps its two steps, as before). `sketch_spline_ok` A - E |
| The green check beside the last point, OK in the right-click menu, Enter, a click on the first point (closed): each makes the spline | Worked (checked again: a spline from one line end to another, both ends joined) | Unchanged. `sketch_spline_ok` A - F |
| A right angle the sketch keeps shows a symbol at the corner (Fusion's Perpendicular glyph; Luca: "Sketch lines are still missing 90 degree markings where they connect at 90 degrees") | FreeCAD draws its Perpendicular icon in the middle of each line; a corner held by Horizontal + Vertical (an upright line on a level one, also what the Line tool gives) shows nothing at the corner | Fission 180's own square corner mark (the one shown while drawing at 90 degrees), 10 screen pixels (at most 40 % of the shorter line), in the constraint glyphs' colour, at every corner where two lines touch (shared end, or one's end on the other's middle: on the longer side) and a Perpendicular, or Horizontal on one and Vertical on the other, holds 90 degrees that the sketch has now; redrawn on zoom; hidden with Show Constraints (`sketch_right_angles.py`). The constraints are unchanged (Horizontal / Vertical stay: whether Fusion's Line gives Perpendicular instead stays **Unconfirmed**, Inference table). **Guess**: the mark's look (Fusion's glyph is its own artwork). Unit `test_sketch_right_angles`, scenario `sketch_right_angle_marks` |
| A sketch tool shows its picture beside the pointer (Luca: "the cut tool doesnt have one") | FreeCAD's tools have their pointer pictures; Fission 180's own tools (`sketch_draw.DrawTool`: Trim, Extend, Break, Fillet, Chamfer, Offset, 2-Point / tangent circles, Tangent Arc, Midpoint Line, 3-Point Rectangle, Edge Polygon, slots, Conic, Project to Surface, Collinear, Concentric, Midpoint, Curvature, 3D Line / Spline, Isoparametric Curve) showed Qt's bare cross | FreeCAD's layout (32 x 32, crosshair centred at 8, 8 in FreeCAD's crosshair colour, the picture bottom right) with the tool's own ribbon picture and a soft shadow (`sketch_cursor.py`). A tool still tells its own pointer from a FreeCAD tool's (`sketch_cursor.is_own`: the picture's cache key), so L, C, D... started over it still take over. The pick-first commands (Mirror, patterns, Move/Copy, Scale) keep the arrow while curves are picked. Scenario `sketch_tool_cursor` |

## Luca's sketch fixes (patch 0.1.0-beta.3.2.1, `develop`, 2026-11-02)

Source: Luca's list "fission180 sketch fixes" with screenshots of his Fusion (the Offset
dialog; a corner hovered with the sketch Fillet: a white dot on the corner and the fillet's
arc; a line being drawn with its length and angle boxes).

| Fusion (source) | Fission 180 before | Fission 180 now |
|---|---|---|
| In a value box while drawing, the arrow keys move the typing cursor (Luca) | Fission 180's own tools' boxes (Fillet, Chamfer, 3-Point Rectangle, slots, circles, polygon...) never take the keyboard and had no cursor: Left / Right went on to FreeCAD's 3D view, which pans with the arrow keys. FreeCAD's own fields (Line, Rectangle) and the dimension box were right | A caret is drawn in the box being typed into (`sketch_draw.ValueBox`); Left / Right / Home / End move it, Backspace / Delete take out the character before / after it, typing goes in at the caret; Up / Down are kept off the view while typing. An arrow in a box that shows the pointer's value starts editing that value. Scenario `sketch_value_box_keys` (also checks FreeCAD's Line and Rectangle fields and the dimension box) |
| Any tool replaces the one running (Luca: Rectangle, then Offset, stays Rectangle) | Offset, Mirror, the patterns, Move/Copy, Scale and the constraints ended only Fission 180's own tools; FreeCAD's Rectangle went on taking the clicks | `SketchSession.give_way()`: the running tool ends first, Fission 180's or FreeCAD's, keeping what is selected. Scenario `sketch_tool_switch` |
| Sketch Fillet: several corners in one go, one radius (Luca: "does not let me select multiple edges") | One corner (or two curves) per fillet | After the first corner, clicks on more corners add them; Enter (or a click away from the corners) makes them all in one undo step "Fillet": the first gets the Radius dimension, the others are **Equal** to it (**Guess**: Fusion's constraint between fillets made together is not documented). With several corners the pointer no longer sizes the radius (it travels from corner to corner): it holds at the last fillet's radius (else a fifth of the shortest side) until a value is typed. Two corners on one line leave a piece of it between their fillets: a radius past that stops at the largest that fits (`sketch_fillet_core.largest_shared`, 1 % of the line kept). Corner points selected before Fillet are all taken. Enter with nothing typed makes the fillet(s) at the radius shown (it ended the tool before) |
| A corner under the pointer shows: a dot on it and the fillet's arc (Luca's screenshot) | A small cyan square at the corner and one of its two curves lit | Both curves of the corner light up, the arc it would get shows (the last radius made, else the guess) and the snap dot sits on the corner. Scenario `sketch_fillet_corners` |
| A dot where the point snaps (Luca: "there should be a dot at the end of the snap point") | Glyphs only (end square, middle triangle...), none when FreeCAD snapped onto a curve | A white dot with a dark rim, a few screen pixels wide, where the point lands: on an end, middle, centre, quadrant or crossing (with the glyph), on a curve (FreeCAD's own snap onto it: Fission 180 shows where), on a line or curve the inferred direction meets; in FreeCAD's tools (`sketch_infer.Overlay`) and Fission 180's (`DrawTool.show_dot`). Tools that pick curves (Trim, Extend, Break, the pick-two constraints, Project to Surface) show none; Fillet and Chamfer only on a corner. Exact look of Fusion's dot: **Guess** from the screenshot. Scenario `sketch_snap_dot` (screen pixels) |
| A line drawn at 90 degrees from the line it starts on, onto a curve, keeps the 90 degrees (Luca) | On a curve the point was left to FreeCAD: the line ended where the pointer touched the curve, a degree or two off, without Perpendicular | The direction the line would snap to in free space (perpendicular to the line it starts on, level, upright, 45 degrees) is kept up to the curve under the pointer: the end goes where that direction meets it (exactly on an arc's circle), with the Perpendicular / Horizontal / Vertical / 45 degree constraint and the end kept on the curve (`sketch_infer_core.direction_meets_curve`). The ending-on-a-line-at-90-degrees rule stays (the nearer of the two wins). Unit tests `DirectionOntoACurve`, scenario `sketch_line_perpendicular_to_curve` |

## Sketch, part 2: chain selection, Project to Surface in the sketch, 3D Sketch, fillet and chamfer with arcs, the text frame, Slice (branch `sf/sketch-2`, 2026-10-16)

Researched before building. Autodesk's hosts cannot be opened from the sandbox, so the
**Autodesk** rows come from web-search excerpts of these pages: Fusion help "Create a 3D
sketch" (SKT-CREATE-3D-SKETCH), "Add chamfers to sketch geometry", "Sketch modification
tools", "Create construction geometry in a sketch"; the Autodesk tech tip "When and why to
turn on Allow 3D sketching of lines and splines"; the Fusion API (SketchLines.addDistanceChamfer
/ addAngleChamfer take two SketchLines). **Forum**: Autodesk Community threads ("chain
select": a consultant's answer, double-click a curve of the chain; "Fusion will accommodate
moves off the sketch plane, and convert automatically to 3d, if you have 3d ticked";
"3D spline point: select it, Move, the manipulator handles") and the Fusion course
"Selecting sketch chained entities" (LinkedIn Learning). **Guess**: no source found; to be
checked in Luca's Fusion.

| Fusion (source) | Fission 180 |
|---|---|
| A double-click on a sketch curve selects the chain of curves joined to it, without a window (Forum, course) | Same (`sketch_select.py`, rule in `sketch_select_core.py`): the curves reached through shared end points, branches too, of the clicked curve's line type (normal, construction, projected: **Guess**); a circle alone. Added to the selection. FreeCAD 1.1.4's own double-click "wire" selection never fired under Fission 180 (checked with real double-clicks), so Fission 180 finds the curve itself |
| A box in the sketch: window to the right, crossing to the left; a plain box replaces the selection, Shift adds, Ctrl toggles (as on the part: `parity/selection.md`) | FreeCAD's sketch box does window / crossing by direction but only added: before FreeCAD sees the release Fission 180 clears the selection (plain) or puts it aside and toggles afterwards (Ctrl) |
| Sketch Fillet: a vertex, two lines, two arcs (or a line and an arc), then the radius (Autodesk "Sketch modification tools") | Fission 180's own Fillet (`sketch_fillet_tool.py`, maths `sketch_fillet_core.py`): a corner point or two curves (lines, arcs, circles), the pointer gives the radius (the arc passes as far from the corner as the pointer is), the R box takes a typed one, Enter or a click makes it; FreeCAD's sketch fillet trims (a corner of two lines keeps its point, construction, with its constraints); a Radius dimension. A radius past what fits stops at the largest that fits and the text by the pointer says so (Luca, 2026-10-21; Fusion refuses it). It picks curves itself: FreeCAD's own fillet tool never saw a click on CI (CI #123-#126); `modeling2_sketch` uses it now |
| Sketch Chamfer: "a vertex, or two lines" (Autodesk); the API's chamfers are line methods | Lines as before, and **Fission 180 goes further**: a line and an arc (the corner point, or the two curves), all three types. The setback on the arc is the straight distance from the old corner (what a dimension between the points shows); Distance and angle: on the line, the angle between the line and the chamfer. The old corner stays as a construction point on both curves (where the line meets the arc's circle) with the values as dimensions from it; the constraints that were on the corner point go (FreeCAD's fillet of curves does the same). Two arcs: refused, "a chamfer needs a line" |
| Project / Include: the edges come in as purple linked curves that follow the source when it changes (Autodesk "Project and include geometry") | Unchanged, now checked: FreeCAD's external geometry in the sketch, purple; widening the block moves the projected line along (`sketch2_project` A, B). **Limit found**: stock FreeCAD 1.1.4 loses some references when the source changes: after widening a padded rectangle, its vertical edges and corners at the moved side ("missing element reference", "Failed to project external geometry"; the projected curve stays where it was). Reproduced headless without Fission 180 (`Pad.Edge2`, `Edge5`, four vertices of twelve edges and eight vertices); the top and bottom edges follow |
| Project to Surface: the curves are in the sketch (Fusion's sketches hold 3D curves) | The "Projected Curves" object now belongs to its sketch (`sketch_companions.py`): listed under the sketch in the browser (a row of its own, eye, Delete), shown and hidden with the sketch (the eye, Finish Sketch, Suppress, the history marker), hidden by Show Projected Geometries while the sketch is open, no timeline step of its own (the sketch's step is theirs, as in Fusion), deleted with the sketch (one undo step), saved with the file; older files' Projected Curves are adopted by the sketch whose curves they project |
| 3D Sketch box in the Sketch Palette; with it, lines and splines can leave the sketch plane; "the 3D Sketch Manipulator appears at the origin once a sketch tool is picked; click one of its planes to sketch on it; its origin moves to the last point placed" (Autodesk "Create a 3D sketch"; tech tip; Forum) | Built on Fission 180's own sketch handler (`sketch3d_ui.py`): the palette's 3D Sketch box; Line (L) and CREATE > Spline > Fit Point Spline then draw in 3D. The manipulator (three small squares, XY blue, YZ red, ZX green, the active one filled) sits at the last point (the sketch origin at first); a click on a square makes that plane the drawing plane through that point. A point lands on a 3D point already drawn, a point of the flat sketch (tied: it follows it), a corner or an edge of the design, or the grid of the drawing plane (within a fifth of the spacing, as the sketch's own snap); Ctrl: exactly under the pointer. Line: points chain, a click on the first point closes, Esc / Enter ends; Spline: points, Enter or OK makes it, Esc drops it. One undo step per line / spline. A line whose two ends lie on the sketch plane is an ordinary sketch line, joined (Coincident) to the sketch points at its ends, level / upright when it is, so it makes profiles ("Fusion will accommodate moves off the sketch plane, and convert automatically to 3d": Forum); a 3D line starting where a sketch line ends is tied to that end. A sketch that has 3D curves opens with the box checked (**Guess**) |
| Moving a point of a 3D sketch: select it, Move, the manipulator's arrows (Forum, tech tip) | A click on a 3D point (no tool running) shows a triad (three arrows along the sketch's X, Y, Z): drag an arrow to slide the point along it, or type a distance (along the arrow used last, Z at first) and Enter: it moves that far from where it was; one undo step "Move 3D Point"; Esc hides the triad |
| (Where the 3D curves live) | FreeCAD's sketches are flat (every curve of a Sketcher sketch lies in its plane), so the 3D curves are a "3D Curves" object of the sketch (`sketch3d.py`, a companion like Projected Curves: same browser, visibility, timeline and delete rules), in the sketch's coordinates (they move with the sketch). Sweep takes its edges as a path (`sketch2_3d` F: a tube up a 3D line) |
| Text: drag a corner of the text's frame to resize it; the letters keep their height (Forum; T17 of `parity/text-emboss.md`) | Same (`text_ui.TextLayer`): a press on a corner of a text's frame and a drag: the opposite corner stays, the frame keeps its angle, the letters are laid out again; one undo step "Resize Text Frame". A dimension that holds the size wins (the reason by the pointer) |
| Window / crossing selection takes construction planes and axes too (**Guess**: the Work Geometry filter covers window selection like the other kinds) | Same (`selection_ui._work_elements`): the planes, axes and points that are shown (an origin's only while its origin is shown), as the view draws them at rest (FreeCAD draws an origin plane as a quadrant square, the whole square only while lit up: a box that passes over it measures the square it showed); see-through, so no visibility test. Selected by their path, as a click selects them: Create Sketch then uses the boxed plane |
| Sketch Palette: Linetype, Look At, Sketch Grid, Snap, Slice, Show Profile / Points / Dimensions / Constraints / Projected Geometries, 3D Sketch (Autodesk) | All there. Checked again: Slice keeps only what lies behind the sketch plane as seen (a pick in the middle of a block reaches the sketch plane, not the top face; seen from below the other half stays) (`sketch2_palette`). Not built: the Linetype's Centerline (below) |

Tests (real FreeCAD 1.1.4, real input): `sketch2_select` (chains of a rectangle, an open
chain, a circle; plain / Shift / crossing / Ctrl boxes; empty space; the Line tool's own
double-click), `sketch2_fillet` (line-arc fillet, corner fillet with a refusal, the three
chamfer types with a line and an arc, two arcs refused, undo / redo, save / reopen with
the fx dimension following), `sketch2_text_frame`, `sketch2_box_planes`, `sketch2_project`,
`sketch2_3d` (lines off the plane through the manipulator, the triad typed and dragged,
undo / redo, a 3D spline, a triangle on the sketch plane that is a profile and a 3D line
tied to its corner, the browser and the eye, a sweep along a 3D line, save / reopen,
3D Sketch off), `sketch2_palette` (no sketch open, Slice both ways, 3D Sketch in a moved
component: a sketch line on the plane, a 3D line from its end); unit tests `test_sketch_select_core.py`, `test_sketch_fillet_core.py`,
`test_sketch3d_core.py`, `test_sketch_chamfer_core.LineAndArc`,
`test_browser_core` (curves under their sketch), `test_selection_core` (work geometry boxed).

## Sketch, part 3: snapping, 45 degrees, glyphs, Auto project, profiles on faces, z-fighting (branch `sf/sketch-3`, 2026-10-16)

Luca's list (CI #131's quick update): "When sketching on a face of a body, the edges of the
face should already be projected" (F8); "Projected edges should have the same snap points as
sketch elements (endpoint, midpoint)", "lines are often not connected because it's slightly
off the corner", "circles and arcs ... should show their middle ... and you should be able to
snap to them" (F5); "Sketching lines should have snap points at 90 and 45 degree angles (and
all flipsides)" (F6: always on, Ctrl = no snaps, his choice); "the little sketch icons for the
midpoint etc. from Fusion, the triangle for the midpoint" (F7); "When lines are connected to a
projection on a face, any shape that is sketched will not be selectable to extrude; only the
whole face" (F9); "Faces that are sketched on have z-fighting" (F10).

Sources (autodesk.com only through search excerpts from the sandbox): **Autodesk**:
[Fusion API, FusionProductPreferences](https://help.autodesk.com/cloudhelp/ENU/Fusion-360-API/files/FusionProductPreferences.htm)
(isAutoProjectGeometry: "Auto project geometry on active sketch plane";
isAutoProjectEdgesOnReference), [Cannot snap to circle quadrant in Autodesk Fusion](https://www.autodesk.com/support/technical/article/caas/sfdcarticles/sfdcarticles/Cannot-snap-to-circle-quadrant-in-Autodesk-Fusion.html),
[Mastering sketch constraints](https://www.autodesk.com/products/fusion-360/blog/mastering-sketch-constraints-autodesk-fusion-tutorial/);
**Course**: [Product Design Online, Learn Fusion 360 in 30 days, day 17 (the 12 sketch
constraints)](https://productdesignonline.com/day-17-of-learn-fusion-360-in-30-days-for-complete-beginners-2023-edition-learn-all-12-fusion-360-sketch-constraints/)
(the midpoint triangle glyph); **Forum**: [Help with unwanted auto projected geometry](https://forums.autodesk.com/t5/fusion-design-validate-document/help-with-unwanted-auto-projected-geometry/td-p/7742224),
[Beginner needs help with pink/purple sketches to become faces](https://forums.autodesk.com/t5/fusion-design-validate-document/beginner-needs-help-with-pink-purple-sketches-to-become-faces/td-p/8455824).
**Guess**: no source found.

| Fusion (source) | Fission 180 |
|---|---|
| A sketch can snap to end points, midpoints (the triangle glyph; Shift brings hidden midpoints) and centres of sketch curves (Autodesk blog, Course) | One snap engine for every tool (`sketch_infer_core.snap_points`, unit tested): ends, middles of lines and arcs, centres of circles, arcs and ellipses, ends of conic arcs and splines, sketch points and the origin. Within `SnapPixels` (8 screen pixels, never less than FreeCAD's own pick radius) the point lands exactly there. FreeCAD's tools (Line, Rectangle, Circle, ...): the pointer FreeCAD gets is moved onto the snap point (`sketch_infer.Inference._plan`), so FreeCAD lights it up and adds its own Coincident / Symmetric; after the click Fission 180 makes the point exact and adds what FreeCAD did not (`_snap_constraints`). Fission 180's own tools (`sketch_draw.DrawTool.snap`) the same. Shift for hidden midpoints: not built (every midpoint is offered) |
| Projected geometry snaps like sketch geometry; snapping to a model corner auto-projects it (Autodesk preference "Auto project edges on reference") | Projected (purple) curves give the same snap points (geo -3, -4, ...). Snapping to an edge of the part that is not projected: not built (FreeCAD only picks projected curves while drawing) |
| No direct snap to a circle's quadrant (Autodesk support article: draw a construction line through the centre) | **Beyond Fusion** (Luca asked): the 0 / 90 / 180 / 270 degree points of circles and arcs snap (the point is put exactly there and kept on the circle: PointOnObject). Where two curves cross (lines, circles, arcs) the point lands on the crossing and is kept on both (two PointOnObject); Fusion shows an intersection glyph (an X): **Guess** that it snaps there |
| (A scaled Windows screen) | The cause of "slightly off the corner": FreeCAD's pick radius counts device pixels, Fission 180 counted screen (logical) pixels and left the snap to FreeCAD within 5 of them: on a 150 % screen FreeCAD reached only 3.3, so between 3.3 and 5 pixels nothing snapped and the line ended a hair beside the corner (on the projected line, PointOnObject). Reproduced with `QT_SCALE_FACTOR=1.5` (a click 4 px off a projected corner: the line started at (0.297, 0)); fixed: `sketch_snaps` and `sketch_projected_profiles` pass at 150 % too |
| Lines are inferred level and upright (and perpendicular, parallel, tangent); no 45 degree inference (Autodesk blog, Forum) | **Beyond Fusion** (Luca: "always on, Ctrl = no snaps"): a line (a slot's centre line, a Midpoint Line) within `DiagonalDegrees` (4) of 45, 135, 225 or 315 degrees snaps there; after the click an Angle constraint (from the sketch's X axis) holds it. Level / upright and perpendicular come first. Ctrl frees the point as before |
| Glyphs while drawing: the midpoint triangle (Course), an intersection X (Guess), the constraint glyphs after the click | Fission 180's own pictograms at the snap point while the pointer is there, in the guide colour: end / coincident = a small square, middle = a small triangle, centre = a circle with a dot, quadrant = a diamond, crossing = an X, 45 degrees = a small arc from level to the line with "45". Fusion's exact look is not documented (**Guess**); after the click FreeCAD's constraint glyphs take over |
| "Auto project geometry on active sketch plane": a new sketch on a face gets the face's edges projected; the option exists in Preferences, off by default today (Autodesk API, Forum) | Preferences > General > Design > Sketch: "Auto project the face's edges when sketching on a face", **on** by default (Luca's wish). Create Sketch on a flat face projects the face's edges as purple, profile-making curves (`sketch_auto_project.py`, one external reference to the face). The face is taken from the step the sketch hangs on (the earliest step with that face, `sketch_ui._earliest`): suppressing a later hole leaves the sketch alone (referencing the hole's face broke the sketch: fixsketch_hole D); edges a later step added (that hole) are projected with P |
| Projected geometry is purple and bounds profiles together with sketch lines (Forum) | Same (FreeCAD's "defining" external geometry). P on an edge or face already in the sketch adds nothing (FreeCAD failed on a face linked twice: "Link to Face5 already exists"); P on a face whose outline is in but not a later hole adds only the hole's edge (`sketch_mode.projection_refused`) |
| A shape drawn against projected edges is a profile of its own (Forum) | Same: the root cause of "only the whole face" was the end a hair off the projected corner (the loop never closed); with exact snapping and Coincident at the corner the drawn area is its own profile (`sketch_projected_profiles`, goldens `sketch_face_projected_corner` / `_rest`) |
| With Auto project on, the face around what is drawn is a profile too: a click there picks that profile, E right after drawing takes nothing by itself (Guess, follows from the projected outline making profiles) | Fission 180's choice, so the face keeps working as before: an area that only the face's own edges bound (the curves Auto project made, ids kept in the sketch's hidden `Fission180AutoProjected`) is the face's: it is not shaded or offered as a profile, and a click there takes the face (Press Pull / Extrude of the face, `sketch_area_pick` lets the click through, `profile_pick` leaves it out). Areas drawn against the projected edges (a rectangle from a projected corner, a U onto the edges) and areas of curves projected with P stay profiles. Extrude and Revolve still take by themselves the areas inside the one area the drawn curves close on their own (a circle on a face: the disc; a rectangle from a face's edge; a rectangle over a rim split by its inner edges: every piece inside it), as without the projected edges (`extrude.taken_by_itself`). A drawn shape that crosses a projected edge is split into two profiles there (as in Fusion) |
| Sketch faces drawn cleanly on the face they lie on | A finished sketch's areas (FreeCAD's SoSketchFaces) and Extrude's shaded profiles are drawn with a polygon offset in front of the faces (factor -1, units -1; FreeCAD pushes faces back by +1): no more z-fighting in commands or after a zoom. The front shift that lets a click pick a sketch area on a face is brought up to date after a wheel zoom too |

Settings (`BaseApp/Preferences/Mod/Fission180/SketchInference`): `SnapPixels` (8), `DiagonalDegrees`
(4; 0 = off), `AutoProject` (on, also in Preferences).

Tests: `sketch_snaps` (projected corner, projected middle, circle quadrant and centre, arc
middle, crossing, Fission 180's Midpoint Line, Ctrl, undo / redo; also run at 150 %),
`sketch_projected_profiles` (Auto project, a rectangle from the projected corner, lines onto
projected edges, three areas, E takes the drawn one, a click adds another, undo / redo; also at
150 %), `sketch_glyphs` (glyphs added), `sketch_face_zfight` (screen pixels over a sketched
face: idle, after a wheel zoom, at a slant, inside Fillet and Extrude; the sandbox's software
renderer never showed the stripes, so it guards the drawing); unit tests `test_sketch_infer_core` (SnapPoints, Crossings,
SnapAfterTheClick, Diagonal, Glyphs); goldens `sketch_face_projected_corner`,
`sketch_face_projected_rest`.

## A sketch on a face of an edited part (fix, branch `sf/fix-sketch-face`, 2026-10-16)

Luca (CI #117's quick update): "sketching on an edited object will revert it to a previous
state, making it impossible to sketch on edited faces". Cause: Create Sketch hangs a sketch on
the earliest step that already has the clicked flat face (`hole.earliest_face`, made for the
hole QA), and FreeCAD's sketch "Show support" showed that step while the sketch was open; a
PartDesign body draws one step at a time, so the part was drawn as its first extrude (no
fillet, hole, join, shell, draft, Press Pull, Offset Face, the move undone). Researched before
the fix; autodesk.com cannot be opened from the sandbox, so the rows come from web-search
excerpts. **Forum**: Autodesk Community threads named in the row. **Guess**: no source found.

| Fusion (source) | Fission 180 |
|---|---|
| A new feature, a sketch too, goes in at the history marker: at the end of the timeline unless the marker was rolled back (Forum: Autodesk's Jeff Strater and Phil Eichmiller in "Are revisions to Timeline inserted or appended?") | Same (`timeline_ops.MarkerInserts`, unchanged) |
| While a new sketch is open the design is the one at the marker: every edit made so far stays (follows from the row above; Fusion never draws another state) | Same since this fix: FreeCAD's "Show support" is off for every sketch Fission 180 opens (`sketch_ui.open_sketch`) and `sketch_ui.show_design_at` draws the body's step at the sketch's place (the Tip for a new sketch), through the sketch's TempoVis so Finish Sketch puts every step back. Also for sketches opened elsewhere (`sketch_mode._start`) |
| Editing a sketch rolls the design back to where the sketch was made: later features are not computed, a component moved after the sketch shows where it was, it cannot be avoided (Forum: Autodesk staff in "sketches and bodies are disappearing during edit sketch" (to prevent circular references) and in "Component keeps reverting to an earlier shape when I start a sketch") | The body draws its newest step that comes before the sketch in the timeline and does not use it (`timeline_core.shown_while_sketching`, unit tested); FreeCAD already hides the steps that use the sketch. Only the drawing rolls back, the marker stays where it is. Not done: other bodies' later steps stay drawn |
| A sketch on a face keeps its face when an unrelated later step is suppressed or deleted (Guess, from Fusion's face naming; the hole QA) | Unchanged: the sketch hangs on the earliest step that already has the flat face (a hole drilled in it later, a fillet on its edges, a join that made it larger do not count). Its extrude still builds on the body's newest step |
| A sketch on a planar face has its origin at the component's origin projected onto the plane; moving the body along that plane does not take the sketch along, only projected geometry follows (Forum: "Sketch Origin from Offset plane problem\bug"; "Constrain extrusion to origin": keep a part and its sketches in a component to move them together) | FreeCAD's flat-face attachment does the same (the origin projected onto the plane), whichever step the sketch hangs on |
| A sketch on a face of a moved part is on the moved face: an edit of the move that lifts or tilts the part takes the sketch along (Guess: the sketch's plane is the face) | `earliest_face` never goes back past a step that moves the whole solid (Move/Copy, Align, Scale): the sketch hangs on that step (before: on the face before the move, and the boss sank into the part when the move was edited to lift it). Suppressing that move then takes the sketch along, as for a sketch on a Press Pull face (Fission 180's suppress rule) |
| A sketch on a copied body belongs to that body (Guess) | `earliest_face` stays inside the body: a copy's first step, not the copy step outside the body |

Tests: scenarios `fixsketch_fillet` (fillet, chamfer, the front face, undo / redo, edit from
the timeline, suppress), `fixsketch_presspull` (Offset Face, Press Pull, undo / redo, save and
reopen, edit after reopening), `fixsketch_move` (Move, the Move edited to lift the part,
undo / redo, Create Copy), `fixsketch_join` (the first extrude edited, a Join, top and front
faces, undo / redo, edit), `fixsketch_shell_draft` (Shell, Draft, undo / redo, edit),
`fixsketch_hole` (Hole, Project of the hole's edge while sketching, suppress, edit, undo /
redo); unit tests `test_timeline_core.ShownWhileSketchingTests`.

## Wave 4: sketch Chamfer, the fillet radius, typed line angles (branch `sf/modeling-2`, 2026-10-14)

Researched before building. Autodesk's hosts cannot be opened from the sandbox, so the
**Autodesk** rows come from web-search excerpts of the Fusion help pages "Add chamfers to
sketch geometry" and "Create lines in a sketch". **Forum**: Autodesk Community threads
"Sketching a line an controlling it's angle", "Constrain angle of one sketch line to another"
and "Sketching angles question". **Guess**: no source found; Fission 180's choice, to be checked
in Luca's Fusion.

| Fusion (source) | Fission 180 |
|---|---|
| SKETCH > MODIFY > Chamfer, with a type: Equal distance, Distance and angle, Two distances (Autodesk) | Fission 180's own tool (`sketch_chamfer_tool.py`, the maths in `sketch_chamfer_core.py`): while it runs a "Chamfer Type" box sits at the top left of the 3D view; the last type is remembered (Guess) |
| Pick the corner: the two lines, or the point where they meet (Autodesk) | Click a point where exactly two lines meet, or click the two lines on the parts that stay (lines that do not touch are cut back to where their extensions cross). Lines or a corner point selected before the command count. Parallel lines, a point where more lines meet, an arc: refused with the reason beside the pointer |
| Drag, or type the values; Enter (Autodesk) | The pointer gives the size as it moves (Equal distance: the chamfer runs through the pointer). Value boxes beside the corner: D (Equal distance), D and A (Distance and angle; A starts at the angle that cuts both lines back equally, 45 degrees in a square corner), D1 and D2 (Two distances, D1 on the first line picked). Tab moves between them, Enter makes the chamfer, the tool waits for the next corner, Esc ends it. A chamfer longer than a line was refused with the reason; since Luca's decision of 2026-10-21 it is held at the largest that fits, which takes that line whole (see the top of this page) |
| The values stay as sketch dimensions (Autodesk; their exact form: Guess) | FreeCAD's sketch chamfer trims the lines and keeps the old corner as a construction point (the constraints that were on the corner move to it); the values become dimensions from that point: the distance to the chamfer's end on each line, and for Distance and angle the angle between the first line and the chamfer. Equal distance: the second distance is an expression of the first (fx), so a new value in the first moves both. One undo step per chamfer |
| Sketch Fillet: pick a corner or two curves, type the radius (Autodesk) | Unchanged, now checked by a scenario: FreeCAD's fillet, then the radius box opens on a new Radius dimension |
| A typed line angle is measured from the sketch's X axis (its positive side), not from the previous line: to get an angle between two lines users add an angular dimension afterwards, or type 180 minus the angle when the line before is level (Forum, three threads; no Autodesk page found that says otherwise) | Same: FreeCAD's line tool measures the typed angle anticlockwise from the X axis, its value box shows that angle with an arc from the X axis, and the typed angle becomes an Angle dimension from the X axis. Checked with a chain whose second line is typed at 135 degrees |

Tests: scenario `modeling2_sketch` (the three types with their dimensions, a chamfer too long
held at the largest that fits (it takes the side whole),
the command without a sketch, undo / redo, the fillet radius, two typed line angles, the plate
extruded, save / reopen with the fx dimension still following), unit tests
`test_sketch_chamfer_core.py`.

## The floating green check (branch `sf/polish-2`, 2026-10-16)

Sources: **Autodesk** help "Create lines in a sketch" (click the Check icon to finish the line
set, then start another line or press Enter to leave the tool); **Autodesk** sketch basics
course (click the green check mark or double-click the end point to end the current chain and
stay in the Line command; Esc leaves it); **Forum** "Sketching issue" (a user: a green tick
appears where the next line would go; clicking it ends the chain). **Guess**: where exactly it
sits (20 px right of and 22 px below the chain's last point, so FreeCAD's length box above
the new line does not cover it), its look (Fission 180's own round green check), and that the
splines show it too once they have two points.

| Fusion | Fission 180 |
|---|---|
| A green check beside the chain being drawn; a click ends the chain, the Line tool stays on | Same (`sketch_check.FloatingCheck`, one per open sketch): shown while the Line chain has a line and goes on from its end; a click ends the chain (`LineChain.break_chain`, as the double-click does): no line from the old end, the tool waits for a new first point. It follows the point when the view turns or zooms, never takes the keyboard, and goes with Esc, Enter, the next tool or Finish Sketch. |
| The same check while a spline is drawn | Fit Point / Control Point Spline: shown beside the last point once two are placed; a click makes the spline from the points so far and the tool stays on for the next one. |
| (Fission 180's own multi-click tools: 3-point rectangle, slots, conic, ...) | No check: they end by themselves after their last click (Enter / OK finish them as before). |

Scenario `polish2_sketch_check` (the check beside the end, on top of the view, following a
zoom; a click ends the chain and the tool stays on; a new chain; Ctrl+Z; Esc; a spline;
Finish Sketch).

## Sketch Offset with Fusion's OFFSET panel (2026-11-02)

Luca (2026-11-02): "sketching an offset does not have a dialog box. usually you could select
if you want chain select or not. theres no option for that. so its always chain select. what
if i just want to offset 1 line?", with a screen capture of Fusion's OFFSET panel: Curves
(Select), Chain Selection (ticked), Direction (One Side), Flip, OK (greyed until curves are
picked), Cancel. Fission 180's Offset was FreeCAD's offset tool started on the whole chain of
the clicked curve, with round corners (its switch to sharp corners did not take).

Sources: Autodesk's hosts cannot be opened from the sandbox (help.autodesk.com and
forums.autodesk.com are outside its network), so the **Autodesk** rows come from web-search
excerpts of Fusion help "Offset sketch geometry" (SKT-OFFSET), the Fusion API reference
(Sketch.offset, SketchOffsetDimension, OffsetConstraint) and the support article "Cannot
select lines / edges to Offset in a Fusion sketch"; **Forum**: Autodesk Community threads
"Negative offset in sketch not working" (Fusion added Flip so the side changes without a
negative value), "Offset multiple sketch curves", "offset editing", "Sketch offset dimension
value"; **Luca**: his capture; **Guess**: no source found, Fission 180's choice.

| Fusion (source) | Fission 180 |
|---|---|
| MODIFY > Offset, key O; the OFFSET panel: Curves (Select), Chain Selection, Direction, Flip, OK / Cancel (Luca; Autodesk) | Same: Fission 180's own tool (`sketch_offset_tool.py`, command in `sketch_offset_ui.py`, maths in `sketch_offset_core.py`, constraints in `sketch_offset_build.py`). The panel sits at the top of the sketch panel, above the SKETCH PALETTE (where Fission 180's other sketch panels sit); its buttons never take the keyboard (Esc, Enter and typed values stay with the 3D view) |
| Pick a sketch curve, a chain of connected curves or a profile; Chain Selection on: one click takes the connected chain; off: each click takes just that curve; several curves can be picked (Autodesk; Luca) | Same: clicks on the sketch's curves (projected ones too) pick them; Chain Selection uses the double-click chain rule (curves of the same line type joined end to end). A click on a picked curve drops it (with Chain Selection on, its chain) (Guess: Fusion's selection toggle); the x drops all; the panel counts them. The picks are yellow, what a click would add lights up, what it would drop is red. Curves selected before O are the picks, as they are (no chain added: Guess). Lines, arcs and circles |
| (Is Chain Selection remembered?) | Remembered between sessions, like the palette's options; Direction for the session (Guess) |
| Drag or type the distance; a value box in the canvas (Autodesk) | The offset follows the pointer: it runs through the pointer, on the pointer's side. A click (or a press-drag) off the curves keeps that distance; a number typed goes into the box by the pointer, or into Distance in the panel. A plain number is in the design's units. The first distance before the pointer moves: the last one used (Guess) |
| Direction One Side / Symmetric (both sides, one distance) (Luca's capture; Autodesk also lists Two Sides) | One Side and Symmetric. Two Sides: gap |
| Flip changes the side (Forum) | Same: the offset goes to the other side and keeps the distance shown; greyed for Symmetric. 0 or a negative value is refused (Flip is the way) |
| OK / Enter makes it, Cancel / Esc makes nothing (Autodesk) | Same; one undo step "Offset"; OK in the right-click menu too. O again, or another sketch tool, ends Offset without making anything (Guess) |
| Corners stay sharp: a rectangle offset outwards is a bigger rectangle (Luca) | Same: neighbouring offset lines and arcs are cut or extended to where they meet; smooth joints (a slot, rounded corners) stay smooth; an open chain's ends stay square to the original's ends |
| After OK: the offset curves, an offset dimension and an offset constraint; editing the dimension moves the offset; deleting the glyph unlinks them (Autodesk; Forum) | The offset keeps one dimension (its text just beyond the offset): a double-click, a new value, and the whole offset moves (both sides for Symmetric). Underneath, unseen (FreeCAD's "virtual space"): each offset line is Parallel to its original, an arc or circle shares its centre, short construction lines square to the originals are Equal to the one that carries the dimension (FreeCAD's own offset uses such lines), corners meet. Fixed (Fix/Unfix, FreeCAD's Block) originals get the same ties by their position (FreeCAD 1.1.4 calls a sketch over-constrained when any constraint names a blocked curve). Originals whose own size is free: FreeCAD's solver may share a new distance between them and the offset (give them sizes, as typed values do) |
| A value past what fits (this page's top) | An inner offset wider than the curves allow stops at the largest that fits; the note by the pointer says so ("20 mm does not fit: limited to 14.99 mm"); Fusion refuses it |

Tests: scenario `sketch_offset_dialog` (real clicks: Chain Selection off and one line of a
rectangle; on and the whole rectangle with sharp corners and the exact typed distance; the
dimension changed by a double-click moves the whole offset; picks dropped; Cancel; Symmetric
on a circle; Flip; Esc; a line selected first; O again; one Ctrl+Z per offset; an inner
offset held at the largest that fits), `sketch_modify` (O, a click, 3: a rectangle 3 mm
out, sharp corners), `sketch_qa` C (Offset waits for a pick, Esc ends it); unit
`test_sketch_offset_core.py`.

## What the user does (and what Fission 180 does)

| Fusion | Fission 180 |
|---|---|
| Create Sketch: the origin planes appear; click a plane or a flat face; the camera turns to look at it | Same (`sketch_ui.py`). A curved face or an edge is refused with the reason next to the mouse and does not stay selected. An edge or corner of the part in front of an origin square hides it (as a face does), and a click on an edge takes the flat face under the mouse there (Fusion's Create Sketch only takes planes and flat faces, so the edge is not a candidate). Before (found by the Pi 5 case test): a click on the 2 mm rim of a shelled box met an edge lying on the XZ square, the square took the click and the sketch landed on XZ. A sketch's curve or a construction line only hides a square it lies in front of. `pi5_case` (the lid sketch) |
| SKETCH tab; Finish Sketch (ribbon, palette, right click) always works, also with a tool running or a value being typed; the camera goes back | Same (`sketch_mode.finish_sketch`) |
| L: lines joined end to end; type the length and Enter (the pointer gives the direction), or the length, Tab, the angle, Enter; the typed length becomes a dimension; a click on the first point closes the shape and the next click starts a new chain | Same: FreeCAD's line tool (on-screen Length/Angle) joined end to end by `sketch_line.py`; one Enter after a value finishes the shape (FreeCAD alone would move to the next field) |
| Ending a line (Luca, 2026-10-13: "no way to end a line"): Esc exits the Line command; the green check or a double-click on the end point ends the chain and stays in the Line tool; a line that ends on existing geometry ends the chain too; Enter completes the tool; right-click: OK / Cancel (Autodesk's sketch basics course, the Create Lines help, forum answers) | Same (`sketch_end_line` scenario): Esc stops the tool; a double-click on the point the chain goes on from, or a line ending on another curve or point, ends the chain and the tool waits for a new first point (the origin and axes do not count); Enter with nothing typed completes the tool (with a value typed it still draws the shape); the right-click menu shows OK at 3 o'clock and Cancel at 9 o'clock while any tool runs: OK ends the tool and keeps what was drawn, Cancel is Esc. Fusion's floating green check: section "The floating green check" (polish-2) |
| R 2-point rectangle, C centre-diameter circle (type the diameter), polygons (6 sides, sides in the panel, size typed) | Same. Circumscribed polygon: the typed size is the radius of the circle it is drawn around (what the preview shows) |
| D: click a curve (or two), place, a value box opens; Enter keeps it, Esc keeps the measured value | Same (`DimensionEditor`). Refuses 0, negative sizes, text and wrong units with the reason in the box; takes expressions (`10+15*2`, `=Parameters.w`). A plain number is in the design's units and the box shows them, like Fusion (a design in inches: "1.5" is 1.5 in; the boxes of Fission 180's own tools too: beta 3 VEX QA) |
| A dimension on a size that is already set: Fusion offers a driven dimension | Made a driven dimension at once (no pop-up), with a message; the sketch never ends up over-constrained |
| Double-click a dimension to change it | Same (also radius/diameter); a driven dimension says it cannot be changed |
| T trim, O offset, X construction, P project, Include 3D Geometry, Mirror/patterns with nothing selected | Same (first pass). T is Fission 180's Trim (press and drag across pieces) since `sf/sketch-tools`; O is Fission 180's Offset with its OFFSET panel (Chain Selection, One Side / Symmetric, Flip, sharp corners) since 2026-11-02 (section "Sketch Offset with Fusion's OFFSET panel") |
| A constraint tool clicked with a selection that does not fit (Parallel with one line) starts and waits for picks | Same (`sketch_tools_ui._Constraint`); FreeCAD alone only noted "Wrong selection" |
| Fix/Unfix with curves selected fixes them where they are | Same: FreeCAD's Block on curves, Lock on points |
| Sketch fillet: click a corner, type the radius | Same: the radius box opens on a new radius dimension |
| Esc stops the tool, a second Esc clears the selection; Esc never leaves the sketch | Same, also with the keyboard in the side panel (after a palette click) or in FreeCAD's value field next to the pointer, right after typing a value |
| E in a sketch: finishes it and starts Extrude with the profile | Same, also with a drawing tool still running |
| M moves/copies sketch curves, Del deletes sketch curves, Ctrl+C/Ctrl+X/Ctrl+V copy/cut/paste (the copy hangs on the mouse) | Same (keys handled by the sketch view while a sketch is open) |
| A tool's key (L, C, R, D, T...) switches tools at any time, also halfway through a shape | Same, also when FreeCAD's value field has the keyboard; after a value typed into the field, letters are a unit ("12 mm") |
| Right click: the marking menu with sketch tools and Finish Sketch; OK and Cancel while a command is active | Same (`sketch_marking.py`): Repeat, Delete, Line, Undo, Finish Sketch, Circle, Sketch Dimension, Rectangle; list: Redo, Trim, Offset, Project, Move/Copy, Normal/Construction, Fit, Look At. While a tool runs, OK (3 o'clock) and Cancel (9 o'clock) replace Line and Sketch Dimension. Also after switching to another program and back (Luca saw the part menu there, 2026-10-12), and only in the open sketch's own view: another design's view gives the part menu |
| The dimension box closes when you click elsewhere, finish the sketch or start another dimension | Same; a value that cannot be set (text, or the dimension was undone while the box was open) closes the box and says why. No box is ever left over the part (Luca saw "Invalid constraint index" boxes stay, 2026-10-12) |
| Click inside a closed area of the open sketch: the profile is selected (Shift / Ctrl add, click again drops; Esc, empty space or a curve drop); E / Q extrude the selected | Same (`sketch_areas.py`, Luca R1); the area under the mouse lights up; the picked ones are a stronger blue |
| After Finish Sketch, profiles are shaded, light up and can be clicked; E / Q take them | Same, with FreeCAD's sketch areas (MakeInternals on while Fission 180 is on; older sketches get them when opened); the light-up and selection are FreeCAD's yellow / green |
| SKETCH PALETTE: Linetype (construction), Look At, Sketch Grid, Snap, Slice, Show Profile/Points/Dimensions/Constraints/Projected Geometries | Same (`sketch_palette.py`). Linetype turns orange while new curves are construction (X with nothing selected), and every new sketch starts with normal lines. FreeCAD's constraint/element lists are hidden |
| Closed areas shaded light blue (also where curves cross) | Same (`sketch_regions.py`) |
| Ctrl+Z after Finish Sketch takes the last sketch change back with its effect on the part (one press) | Same: FreeCAD's separate "Sketch recompute" step is undone/redone together with the change before it |
| Editing a sketch features depend on; the part follows. A profile broken by the edit: the feature fails, the user is told | Same; the message next to the mouse names the feature and says to edit again or Ctrl+Z (no FreeCAD balloon) |
| No pop-ups | FreeCAD's notification balloons are off while Fission 180 is on (its messages stay in its list and the Report view) |

## Inference while drawing (`sketch_infer.py`, 2026-10-12)

Built in Python on top of FreeCAD's own line tool (no C++ change, ships in a quick update).
Evidence labels as in `reports/Fusion sketching ViewCube and navigation.md`: **Autodesk**,
**Forum** (old forum posts / tutorials), **Unconfirmed** (to check in real Fusion).

| Fusion (evidence) | Fission 180 | Status |
|---|---|---|
| Holding Ctrl turns off all snapping and automatic constraints while drawing (Autodesk staff on the forum, tutorial) | Same, in every sketch drawing tool: the Ctrl point lands exactly where the mouse is, no coincident/on-curve/level/upright constraint for it, no grid snap. FreeCAD alone gave Ctrl the opposite job (5-degree angle steps) and still jumped to a point under the mouse | Matches |
| Ctrl only frees the point being placed; the line's start keeps what it snapped to (follows from "while picking") | Same: Ctrl on the second click keeps the start's coincident | Matches |
| Hover a point to "acquire" it; at most 3 are kept; the points of the lines drawn in the current command count automatically (Forum, about 2016) | Same: the last 3 hovered points plus every point of the lines drawn since L started (the line's own start excepted: its level/upright snap covers it) | Matches the old forum rule; **Unconfirmed** for today's Fusion (hover time, how many) |
| A dashed guide shows when the pointer lines up with an acquired point (Forum, video titles); colour blue or green, dash pattern and length unknown (Unconfirmed) | A dashed light-cyan guide (Fission 180's own colour) from the acquired point to the pointer, horizontal or vertical; the point snaps onto it within 6 pixels; two guides meet at their crossing; a guide also meets a level/upright/perpendicular direction. The other coordinate keeps the grid snap | Behaviour matches; look **Unconfirmed** |
| What a click on a guide adds (Unconfirmed: no source) | A Vertical/Horizontal constraint between the two points (Fusion's H/V constraint takes two points), like Onshape. Parameter `GuideConstraint` (default on); off: the point is only placed exactly on the guide | **Unconfirmed**, an option |
| A line close to level or upright snaps and gets Horizontal/Vertical (Autodesk); tolerance not published | Within 4 degrees (FreeCAD alone: 2), parameter `HVDegrees` | Tolerance **Unconfirmed** |
| Perpendicular inferred when a new line starts from, or ends on, another line at about 90 degrees (Forum 2015) | Same, within 4 degrees (`PerpendicularDegrees`): snaps to exactly 90, a small right-angle mark at the corner while drawing, a Perpendicular constraint after the click. A line ending on another line goes to the foot of the perpendicular (on that line) | Matches; tolerance **Unconfirmed** |
| Perpendicular beat Vertical in 2015 (Forum idea post) | Level/upright wins (FreeCAD adds it); no Perpendicular on top of it (it would be redundant) | **Unconfirmed** which wins today |
| Parallel to a separate line: no source shows it | Off by default; parameter `Parallel` turns it on (to a line hovered in this command, within 3 degrees, `ParallelDegrees`) | **Unconfirmed** |
| Fusion does not infer from construction lines (Forum) | No perpendicular/parallel to construction lines (they still snap points, like FreeCAD) | Matches |
| One Ctrl+Z per drawn line | Ctrl+Z takes back Fission 180's inferred constraints together with FreeCAD's automatic ones (one step, "Inferred Constraints" glued to the step before); the line itself is FreeCAD's separate step, as for every line | Close: one more press than Fusion (FreeCAD's own two steps) |
| Guides for the points of every drawing tool (Unconfirmed which tools Fusion guides) | 2026-10-13 (`sf/sketch-feel`): rectangle corners (2-point and centre), circle centre and rim point, centre-point arc centre and start, 3-point circle and arc, polygon centre and corner, slot centres. After the click the point is put exactly on the guide and a Vertical / Horizontal point-to-point constraint is added in the same glued step; a point that is no vertex of the shape (a circle's rim) is only snapped. The slot's centre line also gets level / upright / perpendicular (on the slot's side line). The curves a new constraint refers to are held still (a temporary Block) while the shape is made exact | Behaviour **Unconfirmed**; not yet: the centre-point arc's end-angle click and the slot's width click |
| A small glyph beside the line while it snaps level or upright (Autodesk) | Fission 180's own mark near the pointer's end (short stroke under or beside the line) in the guide colour; after the click FreeCAD's glyph takes over. FreeCAD's cursor hint icons cannot be switched off (`Gui::ToolHandler::addCursorTail` has no switch) | Look **Unconfirmed** |
| Press-and-drag from the end of the line being drawn makes a tangent arc (Autodesk) | Same: press on the start of the line being drawn (the end of the last curve) and drag more than 6 px (`DragPixels`): an arc tangent to that curve follows the pointer with Fission 180's preview and a tangent mark; release places its end (snapped to a sketch point, a guide crossing or the grid; Ctrl frees it); the chain goes on from there. Works from a line's and from an arc's end. Arc + Tangent + the end's constraints are one undo step "Tangent arc". A plain click (< 6 px) still does what it did. Setting `TangentArc` (on) | From an arc's end, the snapping, the threshold and the one undo step **Unconfirmed** |
| Fixed geometry green; fully defined black (white on dark) (Autodesk) | Blocked curves and locked points (Fix / Unfix) are painted green (`#4ad66d`) after each of FreeCAD's recolourings (`sketch_mode.FixedColour`); fully constrained stays white. Selection (`#3b5bdb`, the value FreeCAD's own packs write) and hover (`#246eab`) colours are pinned while Fission 180 is on so a selected or hovered line is never the free blue (FreeCAD's Light theme hovers in green); given back when Fission 180 is off. They are FreeCAD-wide: part selection and hover use them too | Shades **Unconfirmed**; a Block on a construction line is green (FreeCAD alone: orange) |
| Undo while the line tool draws | Review fix 2026-10-13: FreeCAD's tool keeps the point it was started on across undo and would join the next line to itself (solver failure). Fission 180 stops and restarts the line tool after every undo / redo and goes on from the newest remaining end, or says "Line: click where to start."; a self-joined Coincident is removed and logged | Matches (no corruption) |

Settings live in FreeCAD's parameters at `BaseApp/Preferences/Mod/Fission180/SketchInference`
(`Enabled`, `CtrlFree`, `GuideConstraint`, `GuidePixels`, `MaxHovered`, `HVDegrees`,
`PerpendicularDegrees`, `Parallel`, `ParallelDegrees`); there is no dialog yet.

How it works (and its limits): FreeCAD computes the snapped point in C++ from the mouse
pixel. Fission 180's filter on the 3D view swallows each mouse event and gives FreeCAD a copy
moved to the pixel nearest to the guide, so FreeCAD's own tool draws the preview and
places the point there; after the click the point is moved exactly onto the guide and the
constraint is added. Limits found while building it:

- A pixel is about 0.1-0.3 mm, so the preview is within half a pixel of the guide; the
  finished geometry is exact (the constraint and an exact move after the click).
- FreeCAD's grid snap stays on for that copy unless it would pull the point off the guide
  (a guide from a point just off a grid line, perpendicular, parallel): then Fission 180
  snaps the free coordinate to the same grid itself (FreeCAD's grid spacing is
  recomputed in Python from the camera, as `ViewProviderGridExtension` does).
- A length typed into FreeCAD's field wins: when the line's end is no longer on the
  guide, the guide is not shown and nothing is added; a level/upright/perpendicular
  direction still applies (also for a line finished with Enter).
- Cost: about 2 ms per mouse move on a 400-curve sketch (8 ms right after a change).
- FreeCAD's click jumps to a point marker under the mouse before any snapping
  (`ViewProviderSketch::mouseButtonPressed` uses the picked point's position): for Ctrl,
  Fission 180 shrinks the view's pick radius for that click.
- Guides: not for the centre-point arc's end-angle click and the slot's width click (the
  point placed is not at the pointer); 3-point circle / arc and circle rim points get the
  snap but no constraint and no exact move after the click (within half a pixel).
- `_check_preview` hides a guide when FreeCAD's preview is more than 3 px away; for circles
  with a radius over about 500 mm the 50-segment preview can exceed that.
- A tangent arc is also offered at a chain's first point when it sits on existing curves
  (tangent to the newest curve ending there). After Ctrl+Z of a tangent arc the Line tool
  waits for a new first point. A drag within 1 degree of the tangent makes no arc.
- FreeCAD's own hint icons for its constraints still follow the cursor; Fission 180's marks
  (guide, right angle, level / upright, tangent) are drawn in the scene.
- Pressing or releasing Ctrl without moving the mouse changes nothing until the next move
  or click.
- A C++ version (`SnapManager::snap`, `DrawSketchHandler::seekAutoConstraint`) would give
  sub-pixel previews and FreeCAD's single undo step; it is not needed for the behaviour.

Scenario `sketch_infer` (all real mouse moves and clicks): Ctrl, guides (also on a sketch
on the XZ plane), perpendicular from and onto a slanted line, level within 4 degrees,
parallel off/on, a typed length beating a guide, undo/redo. 2026-10-13: `sketch_infer_tools`
(guides in every tool, undo, cost under 2 ms per move on a 400-curve sketch),
`sketch_glyphs`, `sketch_tangent_arc`, `sketch_colours` (screen pixels), `sketch_infer_undo`
(undo while drawing, L again mid-line, Leave, a turned plane in a tilted view, a tool started
outside Fission 180). Unit tests `test_sketch_infer_core.py`. Settings added: `TangentArc`,
`DragPixels` (6).

## The remaining sketch tools and constraints (branch `sf/sketch-tools`, 2026-10-13)

Researched before building. Autodesk's own hosts cannot be opened from the sandbox, so
the **Autodesk** rows come from web-search summaries of these pages (titles as Autodesk
names them): Fusion help "Create midpoint lines in a sketch", "Create rectangles",
"Create circles in a sketch", "Create arcs in a sketch", "Create polygons", "Create
slots in a sketch" and "Slots in sketches", "Create conic curves in sketches" and "Conic
curves in sketches", "Project to surface", "Create splines in a sketch", "Trim or extend
sketch geometry", "Add chamfers to sketch geometry", "Project and include geometry in
sketches", "Add a collinear / concentric / midpoint / curvature constraint to a sketch";
the Fusion API reference (SketchCircles.addByTwoTangents / addByThreeTangents with a hint
point, SketchLines.addEdgePolygon, Sketch.addCenterPointSlot, SketchConicCurves.add with
0 < rho < 1, SketchCurve.breakCurve); Autodesk's shortcut table and the blog "15+
Essential Fusion Shortcuts"; the Autodesk support article on wrapping a sketch onto a
surface. **Forum** rows: Autodesk Community threads ("3-Tangent Circle Sketch Tool":
lines only; "Is there a way to specify tangency direction/side": the click picks the
quadrant; "Sketching bug: Escape and Return behave differently for Lines and Splines":
Esc cancels a spline in progress, Enter commits it; "Find sketch objects centre point";
"Curvature constraint unable to select geometry"). **Guess**: no source found; Fission 180's
choice, to be checked in Luca's Fusion.

### New drawing tools

| Tool | Fusion (source) | Fission 180 |
|---|---|---|
| Midpoint Line | Click the middle, then the end (or type the length and angle, then click); the line is symmetric about the first click; repeats; Enter ends (Autodesk) | Fission 180's own tool (`sketch_draw_tools.MidpointLine`): length and angle boxes, a level/upright line snaps and gets Horizontal/Vertical, a first click on a point or curve puts the line's middle on it (Symmetric, FreeCAD's form of Fusion's midpoint constraint); in empty space a point is left at the middle (Guess: keeps the middle to dimension from) |
| 3-Point Rectangle | First corner, second corner (length and direction), third point (width); length and width can be typed; repeats; Enter ends (Autodesk) | Fission 180's own tool: length and angle boxes for the first side, a width box; four lines with coincident corners, one Perpendicular and two Parallel (it stays a rectangle at any angle); typed values become dimensions. (FreeCAD's rectangle has a "3 corners" mode, but it makes a parallelogram through the third click: `DrawSketchHandlerRectangle.h`, checked in FreeCAD 1.1.4) |
| 2-Point Circle | Two clicks are the ends of a diameter; a typed diameter becomes a dimension; repeats (Autodesk) | Fission 180's own tool: diameter box; a click on a point or curve makes the circle pass through it |
| 2-Tangent Circle | Pick 2 lines, then type the radius and/or click: the click picks which of the possible circles (the quadrant) (Autodesk; API hint point; Forum) | Fission 180's own tool: two line clicks (selected lines count), the circle in the pointer's quadrant follows the mouse, radius box; Tangent to both lines, a typed radius becomes a dimension |
| 3-Tangent Circle | Pick 3 lines (lines only: Forum, Autodesk staff); the circle nearest the pointer (API hint point) | Fission 180's own tool: three line clicks, then the circle of the possible ones (incircle and excircles; two between parallel lines) whose centre is nearest the pointer follows it; a click places it; Tangent to all three |
| Tangent Arc | Click an end point of existing geometry (the arc starts tangent there), click the end or type a radius; repeat; Enter ends (Autodesk). The Line tool's press-and-drag arc is the other way in (Autodesk blog) | Fission 180's own tool: first click on the end of a line or arc, the arc follows the pointer, radius box, Tangent at the start, the far end snaps like any point |
| Edge Polygon | Click the two ends of one edge (or type its length and angle), set the number of sides, click the side the polygon goes to (Autodesk) | Fission 180's own tool: edge length, angle and sides boxes (U / J change the sides, as the other polygons), the third click picks the side; equal sides on a construction circle like Fission 180's other polygons |
| Overall Slot | Click the two ends of the slot (overall length; distance and angle can be typed), then click or type the width (Autodesk) | Fission 180's slot tool, overall mode: length, angle and width boxes; a construction line along the overall length |
| Center Point Slot | Click the slot's centre, then an arc centre, then the width (click, or type the diameter of the ends) (Autodesk; API: width, half length, angle; a construction centre line) | Fission 180's slot tool, centre-point mode: the clicked centre sits on the middle of a construction centre line |
| Conic Curve | Click the start, the end, the apex; drag the rho handle or type rho (0 < rho < 1; elliptical below 0.5, parabolic at 0.5, hyperbolic above); Enter; guidelines from the ends to the apex give tangency (Autodesk; API) | Fission 180's own tool: an exact rational quadratic B-spline (poles start, apex, end; apex weight rho/(1-rho), held by a Weight constraint), two construction guidelines from the ends to the apex; after the apex the curve's shoulder follows the pointer (along the line from the chord's middle to the apex) and a click sets rho, or type it in the rho box (0.5 to start), Enter |
| Project to Surface | Pick faces, then sketch curves / edges / points; Projection type Closest Point or Along Vector; OK (Autodesk) | Fission 180's own tool with a small panel above the sketch palette (Faces and Curves counts, Projection Type, Next, OK, Cancel): click faces, Next (or Enter), click sketch curves or body edges, OK (or Enter); Esc cancels. The result is a "Projected Curves" object of the sketch (3D curves that follow their faces and curves when the design recomputes): FreeCAD sketches are flat, so the curves cannot live in the sketch itself; since sketch-2 they belong to it (browser, visibility, timeline step, delete: section "Sketch, part 2") |

### New constraints

| Constraint | Fusion (source) | Fission 180 |
|---|---|---|
| Collinear | Click two lines; they come onto one line; a badge shows (Autodesk) | Tangent between the two lines (in FreeCAD's solver a line-line tangency is exactly collinear) |
| Concentric | Click two circles / arcs / ellipses; their centres meet (Autodesk) | Coincident between the two centres |
| Midpoint | Click a point, then a line (or the other way); the point goes to the line's middle (Autodesk; Autodesk blog) | Symmetric (the line's two ends about the point); for an arc: the point on the arc and a construction line from the centre that bisects the arc's ends |
| Curvature (G2) | Pick a spline and a curve chained to it; smooth G2 join (Autodesk); in practice spline-to-spline (Forum) | FreeCAD's solver has no curvature constraint (19 constraint types in `Sketcher/App/Constraint.h`, none for curvature; no curvature class in `planegcs/Constraints.h`). Spline + line: exact G2 (tangent end to end plus the spline's third pole on the line: curvature 0 at the joint, checked in FreeCAD). Spline + arc / circle / spline: Tangent (G1) and a note saying so |
| The pick flow (all four) | Start the command, click the two things, the constraint is added, the command waits for the next pair; with two fitting things selected first it applies at once; Esc ends (Autodesk "select the geometry to constrain"; the rest Guess) | Same, with a hint next to the pointer for each click; a wrong pick says why and waits |

### FreeCAD's tools under the SKETCH tab: the audit

| Tool | Fusion (source) | FreeCAD 1.1.4 as it was | Fission 180 now |
|---|---|---|---|
| 2-Point / Center Rectangle | Repeats until Enter / Esc; width and height boxes; H/V sides, coincident corners; the centre one has a centre point (Autodesk; Forum) | Same (continuous mode, value boxes, H/V; centre point + Symmetric) | Unchanged |
| Center Diameter / 3-Point Circle | Diameter box; repeats (Autodesk) | Same (FreeCAD's circle box shows the diameter) | Unchanged |
| 3-Point / Center Point Arc | Start, end, a point on the arc / centre, start, end (Autodesk) | Same order | Unchanged |
| Ellipse | Centre, major axis, minor axis (Autodesk) | Same order; FreeCAD also adds its axis lines and foci as construction | Unchanged (the foci are FreeCAD's) |
| Center to Center Slot | Click the two arc centres, then click or **type the width** (the diameter of the ends) (Autodesk) | The third value box is the end **radius**: typing 10 made a 20 mm wide slot | Fission 180's slot tool, centre-to-centre mode: a width box; a typed width becomes the ends' diameter dimension |
| Three Point Arc Slot | The two end centres, a point on the centre arc, the width (Autodesk) | Not in FreeCAD: the menu ran the centre-point arc slot | Fission 180's own tool: width box; outer and inner arcs and two end caps, concentric, joined tangent end to end (a construction centre arc would be redundant for FreeCAD's solver, so there is none) |
| Center Point Arc Slot | Centre, start, end, width (Autodesk; Inventor help for the same tool) | Same clicks | Unchanged |
| Fit Point / Control Point Spline | Click points; Enter or the check commits the spline; Esc cancels the spline in progress (Autodesk; Forum) | Right click or Esc commits; Fission 180's Enter ("complete the tool") dropped the spline. FreeCAD's command runner also closes the spline tool's undo step right after the tool starts, so the points clicked were in no undo step (Ctrl+Z after a spline undid the step before it) | Enter and OK in the right-click menu make the spline and end the tool; Esc cancels the spline in progress (nothing of it stays); the finished spline is one Ctrl+Z (Fission 180 reopens the step at the first click) |
| Point | Click points; repeats (Autodesk) | Same | Unchanged |
| Fillet | Pick a corner or two curves, type the radius (Autodesk) | Radius from the mouse | Unchanged (Fission 180 already opens the radius box) |
| Chamfer | Pick a corner or two lines, drag or type the distance; Equal distance / Distance and angle / Two distances (Autodesk) | Distance from the mouse, no dimension | Fission 180's Chamfer (2026-10-14, section at the top) |
| Trim | Hover shows the piece, a click deletes it back to the nearest intersections, **press and drag across several pieces trims each one**, a curve with no intersection is deleted (Autodesk) | Click trims; no drag | Fission 180's Trim (T): a click trims as FreeCAD's trim does, a press-drag trims every piece the pointer crosses (one undo step) |
| Extend | Hover previews, **one click** extends to the nearest (extended) intersection; nothing in range: nothing happens (Autodesk) | Two steps: click the curve, then drag its end and click again | Fission 180's Extend: hover preview, one click extends the clicked end to the nearest curve it meets; the end gets a point-on-curve constraint |
| Break | Click a curve: it is broken at the intersections nearest to the click into 2 or 3 pieces, joined by constraints (Autodesk API breakCurve; Autodesk help) | FreeCAD's Split: the curve is split at the clicked point | Fission 180's Break: at the nearest intersections on each side of the click (2 or 3 pieces, coincident joints; a circle becomes two arcs joined at both cuts); a curve with no intersection says so |
| Sketch Dimension, Toggle Construction, Intersect | D / X / Intersect as Fusion (Autodesk) | Same (D: Fission 180's value box since 2026-10-10) | Unchanged |

### Keys (Autodesk shortcut table)

Fusion's sketch defaults: L Line, R 2-Point Rectangle, C Center Diameter Circle, D Sketch
Dimension, T Trim, O Offset, P Project, X Normal/Construction (and, everywhere, E Extrude,
Q Press Pull, M Move/Copy, S the toolbox). No other sketch tool has a default key. T runs
Fission 180's Trim and P Fission 180's Project (`config.PREFERRED`).

## Known gaps

| Fusion | Why not yet |
|---|---|
| Shift to force a midpoint; guides for the arc's end-angle click and the slot's width click | Not built (`sketch_infer.py`) |
| A typed line angle measured from the previous line, if a newer Fusion does that (the forum threads found are from 2016 to 2020 and say: from the X axis) | Fission 180 measures it from the X axis, as those threads describe |
| Chamfer and Fillet: a drag arrow on the corner | The pointer gives the size as it moves (no arrow to drag); a line and an arc work since sketch-2 |
| Project to Surface: the projected curves inside the sketch itself | FreeCAD sketches are flat: the curves are a "Projected Curves" object that belongs to the sketch (sketch-2: listed under it, shown, hidden and deleted with it, part of its step); they cannot be dimensioned or constrained from the sketch, and Break Link is not built |
| Conic: dragging the rho handle of a finished conic, rho shown as rho | After the click the curve keeps FreeCAD's Weight constraint (w = rho / (1 - rho)) on the apex pole; its pole circles show while the sketch is open |
| Curvature (G2) between a spline and an arc, circle or other spline | FreeCAD's solver has no curvature constraint: those get Tangent (G1) and a note; G2 only with a line |
| 2-Tangent / 3-Tangent Circle tangent to arcs and circles | Lines only (Fusion's 3-Tangent Circle is lines only too: Forum) |
| Guides (inference) for the width click of the slots and the 3-Point Rectangle, the conic's rho | Not built (as for FreeCAD's tools above) |
| Fusion's constraint glyph look | FreeCAD's glyphs, recoloured (no red) |
| 3D Sketch: the manipulator's rotation handles (turn the drawing plane), the plane cycled by a key, typed lengths and angles of a 3D line, constraints and dimensions on 3D curves, 3D arcs and other 3D tools | Not built: the 3D curves are points placed on planes and moved by the triad; a 3D point keeps its place unless it sits on a point of the flat sketch (then it follows it). FreeCAD's solver cannot hold 3D constraints: the curves live outside the sketch (`sketch3d.py`) |
| 3D Sketch: a spline whose points all lie on the sketch plane, drawn with the box checked, is a curve of the sketch | It is a 3D curve (no profile); turn 3D Sketch off for a flat spline (lines on the plane are sketch lines) |
| A projected edge or corner that FreeCAD's naming loses when its body changes (vertical edges and corners of a padded sketch that got wider) | Stock FreeCAD 1.1.4 drops the reference (Report: "missing element reference"), the projected curve stays where it was; project it again (Fusion follows). Reproduced without Fission 180; a repair by geometry is not built (FreeCAD offers no Python call to re-point one external reference in place) |
| Linetype Centerline (Fusion: a centerline revolves profiles and gives diameter dimensions) | Not built: FreeCAD has construction and normal curves only |
| Sketch double-click chain for curves touching across line types | The chain keeps to the clicked curve's line type (Guess) |
| Shift to show hidden midpoints | Every midpoint is offered (no hidden ones) |
| Snapping to an edge or corner of the part that is not projected projects it (Autodesk "Auto project edges on reference") | Not built: FreeCAD's tools only pick the sketch's own and projected curves while drawing |
| A rectangle drawn over a projected rounded outline (FreeCAD 1.1.4 limit) | Fixed 2026-10-18: FreeCAD's sketch areas (WireJoiner, "tight bound") make no area where an arc ends tangent on the middle of a line (a sharp rectangle over a rounded outline lost the big area). Right after FreeCAD computes a sketch, `sketch_area_fill.py` adds the areas Fission 180's own region finder sees (`sketch_regions`) to its InternalShape; FreeCAD's own areas keep their numbers. Extrude's "could not make an area" message stays as a safety net |
| Every closed area is a profile, also where a line crosses a circle inside another area (a line across a face to find its middle and a circle on it: each half of the circle is a profile) | FreeCAD 1.1.4 made no area at all for this layout (the whole sketch lost its areas; Extrude took the face; Luca 2026-10-18). `sketch_area_fill.py` adds them as above. Golden `sketch_face_line_through_circle`, `_half`, `sketch_line_through_circle_overhang`; scenario `sketch_line_through_circle` (real clicks: line, circle on its middle, E, a click in each half) |
| Auto project from a face changed by a later step (a fillet on its edges, a hole in it) | The outline is the face of the step the sketch hangs on (stable when the later step is suppressed): a fillet's rounded corners or a later hole are not in it; P adds them |
| Fusion's exact glyph pictures | Fission 180's own (Guess) |
| Offset: Direction Two Sides (a distance for each side) | Not built: One Side and Symmetric are |
| Offset of splines, ellipses and conics | Refused with the reason (lines, arcs and circles only); untick Chain Selection to offset the lines and arcs of such a chain |
| Offset: the offset glyph (delete it to unlink), right-click "Add Offset Dimension", an arrow to drag | Not built: one dimension and unseen constraints; the pointer (or a press-drag) gives the distance |
| Offset: an inner offset whose curves would cross each other further away (a narrow notch closing up) | Only a curve that turns over or vanishes is caught (held at the largest that fits); crossings between far apart curves are not trimmed |
