# Wave 7 builder: sketch-b (constraints, dimensions, sketch modify tools), branch `sf/book-sketch-b`

Read `book-common.md` first. Report lines: friction patterns 1, 4, 6 (377-409); cheat sheet
449-505; Donut 810-822 (Fix), 836-838; Surfboard 1034-1041; Tensegrity 1051-1115; Carabiner
1149-1171, 1185-1188, 1196-1199; Play Brick 1241-1243; Drone 1456-1507, 1542-1550; Fire
Piston 1691-1697; Hot End 1768-1773, 1812-1813, 1821-1823, 1873-1879; Pizza Cutter 1971-1973,
2037-2039, 2056-2060, 2104-2108; Tesla 2185-2188; Strandbeest 2317-2318; Football 2431-2432.

sketch-a owns drawing, snapping, selection and display; you own every CONSTRAINT tool, the
Dimension tool (D) and the sketch's MODIFY / pattern tools. The report's pattern 1 (silent
failures) lives mostly here: "Tangent and Collinear constraints that add nothing", "Fix/Unfix
ignoring a mixed selection".

1. **Every constraint tool works both ways Fusion does**: tool first then picks, and picks
   first then tool (Fix/Unfix with nothing selected only locked points; Coincident tool-first
   resolved a line click into a Midpoint / Symmetric). And never silently does nothing: a
   refusal says which existing constraint or dimension is in the way and what to do.
2. **Wrong refusals**: Collinear on two vertical lines refused as "the Vertical on Line 12
   already makes it so" (two vertical lines are only parallel: the redundancy check is
   wrong; audit that check for every constraint type); Collinear on lines that are each
   Horizontal added nothing; Horizontal/Vertical between a point and the origin picked the
   wrong one and silently refused (pick the one that fits the geometry, as Fusion does:
   research how Fusion chooses) and a dimension of 0 is refused (research: Fusion refuses 0
   too? then the message must say to use Coincident / Horizontal/Vertical); Tangent between
   a text frame line and a circle, between two spline ends, added nothing.
3. **Symmetry like Fusion**: two lines (or two points, or two circles) then the symmetry
   line; today only FreeCAD's two points + line works and the lines version does nothing.
4. **FreeCAD's modal "Sketcher Constraint Substitution" box never shows** (Tangent on an arc
   and line that share an endpoint; it even stole keyboard focus so later value boxes got no
   keys). Find the preference or code path that suppresses it for good (FreeCAD has a
   "notify constraint substitutions" setting) and check the other FreeCAD message boxes the
   sketcher can raise (redundant constraints, malformed, "Remove redundant?"): none may
   appear in Fission 180; each becomes Fission 180's own in-panel message or nothing.
5. **The Dimension tool (D)** like Fusion's Sketch Dimension (research its inference):
   - two polygon CORNERS that also lie on a construction circle give the distance;
   - the click that PLACES a dimension is never a pick, wherever it lands (on a line, on an
     axis: today it became Equal or Angle constraints: Drone 1496-1500, Hot End 1812-1813);
   - a slanted line gives the ALIGNED length when the pointer is moved off perpendicular to
     it, horizontal / vertical when moved along the axes, like Fusion (today DistanceX);
   - a model EDGE (not sketch geometry) is projected on the fly and dimensioned to (the
     projection function is components'; today a nonsense 0 mm dimension that Ctrl+Z would
     not remove);
   - a point then empty space always opens the value box; never a dimension at the measured
     value without a box; a dimension that is already determined asks or becomes driven as
     Fusion does ("over-constrain? create a driven dimension"), in brackets;
   - right-click a dimension > Toggle Driven; an origin-to-arc-end distance of 0;
   - to a **centerline** it offers the diameter (sketch-a builds the linetype: use its test);
   - rotated dimension labels are easy to hit (double-click opens the box).
6. **Sketch patterns** (Rectangular, Circular): the copies are TIED to the original like
   Fusion's (today only Equal: 25-79 loose degrees of freedom, copies drift by µm, later
   dimensions do not move the copies, profiles do not close). Build real pattern
   constraints: the copies follow the original and the pattern's parameters, the sketch
   stays fully constrained when the original is, and editing the pattern (quantity, angle)
   afterwards works as in Fusion (research: Fusion keeps a pattern glyph you can double-click
   to edit). **Suppression** check boxes per instance; **Symmetric** counts like Fusion
   (the report: Quantity counts per side; research which is right); typed Quantity taken
   without an extra commit.
7. **Sketch Mirror** merges the mirrored end points that lie ON the mirror line with the
   originals (2 µm gaps left the profile open).
8. **Offset** gives the parallel curve only (today: 6 extra connector lines, 3 open wires;
   Carabiner 1185-1188) and it closes with what it was offset from when Fusion's would;
   Chain Selection and its options as Fusion.
9. **Sketch Fillet** uses the typed radius (0.04 typed, 0.0317 kept); several corners kept
   equal as Fusion does.
10. Leftovers after deleting pattern copies (two overlapping arcs that could not be clicked;
    zero-area slivers offered as extrude regions: Carabiner 1169-1171, 1196-1199): duplicates
    must not be created, and overlapping curves must be selectable (Select Other).
11. Undo: a constraint tool is one undo step; undo of a "driven dimension" conversion gives
    back the state before, not a redundant duplicate (Hot End 1821-1823).
12. Text: the fonts Fusion's books use are Autodesk's; ship nothing proprietary, but make
    sure a missing font says so and falls back visibly.

Scenarios `book_sketch_b_*.py` (at least: each constraint tool in both orders with a refusal
message check; collinear on two verticals; symmetry with lines; tangent arc-line with no
modal box (assert no QMessageBox ever opened: add a harness-level watcher and tell the merger);
D on polygon corners, with the placement click on a line, aligned on a slanted line, on a
model edge; a circular pattern whose copies follow a later dimension and stay fully
constrained, with suppression; mirror closing a profile; offset closing a profile and
extruding it; fillet with a typed radius; undo / redo of each).
