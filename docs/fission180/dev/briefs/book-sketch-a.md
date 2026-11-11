# Wave 7 builder: sketch-a (drawing, snapping, selection, display, undo in a sketch), branch `sf/book-sketch-a`

Read `book-common.md` first. Report lines: friction patterns 4, 7, 8 (394-417); cheat sheet
449-505; Basics 662-741; Donut 742-870; Saturn V 895-947; Surfboard 990-1022; Tensegrity
1048-1066, 1102-1113; Carabiner 1143-1176; Metric Bolt 1378-1383; Drone 1450-1466, 1501-1505,
1554-1555; Fire Piston 1655-1656, 1669-1670; Hot End 1772-1773, 1812-1813, 1865-1868, 1924-1926;
Pizza Cutter 2025-2026, 2056-2060; Strandbeest 2314-2318; Gear Train 2377-2378.

sketch-b owns constraints, dimensions and the modify tools; you own drawing, snapping,
selection, what a sketch shows, and undo while sketching. MEMORY has a long history of
sketch decisions made with Luca (splines, trim, snapping, the green check): `grep` it for
the file you are about to change before you change behaviour he asked for.

1. **Snap is far too strong** with a coarse grid: clicks 6-8 mm (35-45 px) off the axis
   landed on it. Research Fusion's snap (grid snap vs object inference, their pick radius in
   pixels) and make the radius a screen distance like Fusion's, never a model distance that
   grows with the grid. Check the origin, axes, grid points and inferred lines separately.
2. **No driving angle dimension appears by itself**: a line drawn near 45° / 135° got a
   driving 45° angle (Fusion shows a temporary snap only). It made later dimensions driven
   and Parallel "redundant". Nothing the person did not ask for may be added except Fusion's
   own inferred constraints (horizontal / vertical, coincident, tangent, perpendicular,
   parallel, midpoint ... research the list and when each applies).
3. **Selection in a sketch like Fusion**: a plain click on a second curve REPLACES the
   selection; Ctrl+click and Shift+click add / toggle (today Ctrl+click does not add, with
   real input: Donut 662; the book says "hold Ctrl" many times); **double-click selects the
   connected chain** (Tensegrity 1082-1085: with a real double click it selects and
   deselects); window / crossing as now. This is the one place a C++ change might be the
   only route (FreeCAD's sketcher handles the click): find a Python route first (an event
   filter that owns the selection, as `sketch_select*.py` already does for the box) and say
   exactly what you found. Check every sketch tool that relies on "a plain click adds"
   (constraints with several picks are sketch-b's: tell them through your report, and keep
   their tools working by making the pick mode of a running tool add).
4. **The Line tool**: the chain keeps going when a click lands on existing geometry (the
   origin, a projected edge); **press-and-drag at a line's end draws a tangent arc**
   (Fusion's Line-arc; the core of the Carabiner project; today a straight line continues);
   Esc / Enter end as in Fusion; the construction mode X carries over as in Fusion.
5. **What a sketch shows** (the report's "FreeCAD shows through"): no internal construction
   geometry for ellipses (axis lines, foci) and polygons (circles, spokes) unless Fusion
   shows it (research: Fusion's ellipse shows its axes as construction lines; a centre
   rectangle shows its diagonals); a fit-point spline shows the curve and its fit points
   (and tangent handles when selected), not a control polygon with a cloud of "= 22, 20..."
   labels; no "Solver failed to converge" or "Redundant constraints (17)" caused by FreeCAD's
   internal constraints on a fresh spline / polygon; the fully-defined colour and the
   under-constrained ellipse (its rotation left free: add what Fusion's ellipse has).
   The sketch's vertical axis colour on the Front plane (green = sketch Y; the book says a
   green vertical axis means Z-up is off): show the world axis colours Fusion shows.
6. **Auto-projected edges**: research Fusion's two preferences ("Auto project geometry on
   active sketch plane" and "Auto project edges on reference") and their defaults, and match
   both: names, defaults, behaviour. Deleting an auto-projected edge must stick (today Finish
   Sketch puts it back, `sketch_auto_project.follow`); a projected edge must not split a
   drawn circle into profiles in a way Fusion would not (extrude owns the profile logic).
   The dimension-to-model-edge projection is components' function + sketch-b's tool.
7. **Centerline** linetype (palette Linetype: Normal / Construction / Centerline; research
   Fusion's behaviour): a dimension from a point or line to a centerline offers the DIAMETER
   (Fusion's revolve-profile dimensioning), Revolve picks the centerline as its axis by
   itself (revolve's file is extrude's: one helper call), a centerline never closes or opens
   a profile differently from construction geometry.
8. **Undo and redo inside a sketch**: Ctrl+Z never leaves the sketch (one too many stops at
   the sketch's first state, as Fusion); Redo restores exactly; undo of a drawn polyline
   removes the lines, not only its constraints; one Ctrl+Z per action the person made, never
   two; the SKETCH tab and palette never vanish while a sketch is open (Carabiner 1172-1174);
   undo never changes the X (construction) toggle of something else. The 80 s freeze after a
   drag + undo (Fire Piston 1700-1701): profile it (`undo_*.py` are modify's files).
9. **Fit / Home**: F6 in a sketch frames the geometry, not the grid; Fit / Home in a design
   that has only a sketch (no body) frames the sketch (today ~24 m tall); a new design's Fit
   frames the origin sensibly.
10. **Finish Sketch leaves the sketch visible** until a feature uses it (Drone 1554-1555);
    the Sketch Palette's options (Slice, Show Profile / Points / Dimensions / Constraints /
    Projected Geometries, 3D Sketch) all do what Fusion's do.
11. Snapping the report misses: a slot's end to an arc's midpoint (Carabiner 1155-1157), an
    arc's 3 points, the automatic midpoint (a line end snapped to another line's MIDPOINT
    when the person aimed at the line: make the midpoint snap as narrow as Fusion's triangle
    glyph and visibly different), inference to the origin when a later point passes over it.
12. **"Scale entire sketch at first dimension"** (Fusion preference): build it with its
    preference (preferences are shell's file: one entry).
13. In an inch design the sketch grid and snap are inch (params owns the units helper).

Scenarios `book_sketch_a_*.py` (at least: clicks 40 px off the axis stay where clicked;
a 45° line gets no dimension; plain click replaces, Ctrl and Shift add, double click takes
the chain (real events); line through the origin keeps its chain; line-arc by press and drag
with a tangent constraint; ellipse, polygon and spline show only Fusion's items and report no
false solver errors; delete an auto-projected edge and finish and reopen; centerline diameter
dimension and revolve; five undos in a sketch never leave it and redo restores; Fit in a
sketch-only design; inch grid).
