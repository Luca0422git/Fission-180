# Wave 7 builder: extrude (Extrude, Revolve, Sweep, Loft, primitives, profile picking), branch `sf/book-extrude`

Read `book-common.md` first. Report lines: friction pattern 3 (400-406); cheat sheet
492-503, 514-540; Donut 780-801, 836-870 (the extrude parts); Saturn V 871-953; Surfboard
998-1006, 1042-1043; Carabiner 1196-1199; Play Brick 1219-1223; Geocache 1273-1275, 1306-1307;
Drone 1556-1565, 1628-1633; Hot End 1765, 1774-1779, 1817-1820, 1884-1900, 1906-1907; Pizza
Cutter 2066-2068; Tesla 2161-2163, 2176-2179, 2185-2193; Strandbeest 2297-2298, 2323-2329.

"The Extrude Operation keeps changing" is one of the report's three main patterns.

1. **The Operation rule, written down and tested as a table** (research Fusion: when does
   Extrude start as Join, Cut, New Body, and when does it re-decide while you edit?). The
   report: choosing Symmetric flipped Cut back to Join; Flip left Join where Fusion shows
   Cut; a fin came up as Cut; Symmetric + All switched Cut to Join and OK then did nothing
   with a stale warning; a new component's first extrude defaulted to Cut against another
   component's body (bug 10: components' builder gives the "this component has no solid yet"
   helper; the rule is yours). The rule must be: the automatic choice follows the geometry
   until the PERSON picks an operation; from then on it never changes by itself in that
   dialog. Pressing Enter in the distance box is OK (that is Fusion): it must commit what the
   dialog shows. The same rule for Revolve, Sweep, Loft, Coil, primitives, Hole where they
   share it.
2. **Direction and sign**: a negative distance always goes against the arrow shown, the same
   way in every case (the report: −8 grew INTO the body once; −6 went away from the viewer;
   Cylinder Height −8 went +8). Write the rule (Fusion: positive along the sketch plane's
   normal / away from the face) and test profile-on-plane, profile-on-face, face picked
   directly, primitives, flipped sketches.
3. **A feature edit that ends with a warning must not be silently dropped**, and OK must
   never "do nothing": either the dialog stays open with the reason, or the edit is saved.
   "The cut does not go through any body" on a sketch whose placement is flipped 180° (Hot
   End 1884-1900) is wrong: fix the direction test for flipped sketches; To Object likewise.
4. **Several profiles with a taper are tapered together** as one outline where they touch
   (Saturn V 925-932: "-11° does not fit: limited to -6.8°"), like Fusion.
5. **Picking profiles**: a click where a sketch profile and a body face overlap prefers the
   profile when the sketch is shown (Fusion); profiles lying over a hole or void are
   pickable; profiles of a sketch inside a HIDDEN body are pickable; the first clicks right
   after the dialog opens are not lost; after the first profile Revolve keeps taking
   profiles until the person moves to Axis (research Fusion's exact flow); a single profile
   is pre-picked the same way in Extrude and Revolve (research when Fusion pre-picks); Start
   = Offset lets profiles be picked; thin slots are pickable; the arrow and value boxes never
   sit on top of the next thing to click (they must not swallow a click meant for a profile
   behind them: Saturn V 930-932); construction planes' squares and origin glyphs do not
   swallow clicks meant for faces or points behind them unless Fusion's would (research
   Fusion's selection priority for construction planes; `construct*.py` is components').
6. **Sketch visibility with features**: starting Extrude must not hide a sketch the person
   has just shown (Tesla 2176-2179); a used sketch is hidden after the feature as in Fusion;
   a sketch is not hidden when Revolve starts while its axis is still to be picked (Donut).
7. **Zero-area slivers are never offered as regions** (Carabiner: 27 regions); areas are
   referenced so that the solid survives a parameter change ("Sub shape not found:
   Sketch.InternalFace56": the drone, lines 1628-1633). This is the hard one: design a
   stable identity for a sketch area (the curves that bound it, or a point inside it, as the
   Auto-project code does with `Fission180AutoProjectedAt`), migrate old designs, and prove
   it with params' acceptance scenario (a pattern-heavy sketch, 30+ areas, a parameter
   changed four times).
8. **Loft** to a point: the origin point, a sketch point and a construction point can be
   clicked as a loft section (Surfboard 1001-1006).
9. **Primitives**: Box / Cylinder / Sphere / Torus with Fusion's on-canvas flow (pick plane,
   click, type the first size, Tab, the next, Enter): typed digits go to the on-canvas boxes.
10. **Body names** "Body1", "Body2", ... from the first body on, in every command (today the
    first is "Body", Box makes "Body1"); what a new body is called in a component.
11. Separate areas extruded as New Body making separate bodies (MEMORY 3.3.7,
    `extrude_pieces`) is Luca's decision: keep it, but check Join of several areas
    (Drone 1563-1565).
12. Performance: a Hole "From Sketch (Multiple Holes)" of 5 took 60 s (modify's file; tell
    them what you learn about region picking speed), an extrude dialog with 36 areas.

Scenarios `book_extrude_*.py` (at least: the operation table (each row a path); negative
distances in five situations; edit a feature into a warning and back; two touching profiles
tapered as one cone; profile over a void, in a hidden body, under a face, behind the arrow;
show a used sketch then extrude it; loft to the origin; box by typing on the canvas; body
names; the 30-area parametric plate surviving parameter changes; undo / redo, save / reopen).
