# Parity spec: Extrude (E) and Press Pull (Q) (outline 7.0, 7.6, 9.1)

Source: Fusion's documented Extrude dialog (Start / Direction / Extent / Taper / Operation; a
negative taper narrows) and everyday Fusion behaviour. Implemented in
`src/Mod/Fission180/fission180/` (`extrude.py` + `extrude_prism.py` geometry, `extrude_ui.py` dialog,
`profile_pick.py` picking, `presspull_core.py` geometry, `presspull_ui.py` dialog, `preview.py`
dialog helpers). Status: **built and tested with real clicks, not yet signed off by Luca**.

## The Operation rule (wave 7, branch `sf/book-extrude`, 2026-11-11)

The book parity report's third pattern: "The Extrude Operation keeps changing" (Symmetric
turned a Cut into a Join, a new component's first extrude cut another component, an edit to
Cut showed Join again, OK "did nothing"). The rule, as one table. Sources: **Autodesk**: Jeff
Strater (Autodesk) on the forum, thread "extrude - what happened": "If the Extrude intersects
a solid, it will default to Cut. If not, it will default to Join/New Body. But, at any time,
you can change this by changing the 'Operation' setting in the tool"; Autodesk Learn, "Create
solids from sketches": a profile that touches nothing is a New Body "in the active
component", a face extruded away from its body a Join, and "when the new extrusion overlaps an
existing solid body, the Operation type automatically switches to Cut". **Forum**: "Recurring
problem with Join vs New Body" (accepted answer): Join only joins bodies of the active
component ("without that activation, has to be New Body, as there is nothing in the other
Component ... to join to"); "Cannot Join Bodies with Extrude": the same; IdeaStation "Stop
automatically changing the operation from New Body to Cut": the operation used to change
after the person had chosen one, and people asked for that to stop. **Forum** "Tool
behaviour - unexpected" gives another reading (mostly inside a body: Cut; mostly outside
but touching or overlapping: Join); the book contradicts it (its thruster cone, 46 % inside
the rocket, comes up as Cut in Fusion, "exactly as the book says"), so Fission 180 follows
Autodesk's own sentence. **Book**: the report quoting *Mastering Autodesk Fusion*. **Guess**:
rows marked so.

| # | Situation (the first row that fits decides) | The dialog shows | Source |
|---|---|---|---|
| 1 | The extrusion **starts inside** a body: its first 0.01 mm lies in material (at least 1 % of it). A face pushed in, a profile on a plane through the part. One Side / Two Sides: side one; **Symmetric: both sides** (a profile on a middle plane) | **Cut** | Autodesk (Strater; Learn); Book (the thruster cone pushed up into the rocket "was set to Cut automatically ... exactly as the book says"; the donut bite) |
| 1b | (wave 7 follow-up, `sf/book-extrude-2`) It lies **mostly inside shown bodies of other components**: more than half of the new solid (a profile pushed into another component's part, To Object through it), whichever component is active, the design's top row included. Those bodies are listed under Bodies to Cut, each with a check box | **Cut** | Autodesk (Strater confirmed a user's reading in "Tool behaviour - unexpected": "if the new body's volume is mostly inside another visible body" it is a Cut); Forum (the automatic Cut happens "even when the cut goes through all components in the assembly"; "extrude-cut through all problem": both components are selected under Objects To Cut). The share of one half is a Guess. A new part that only overlaps another component's part a little is no Cut (row 5: the report's bug 10, a link around another component's pin, 6 % inside) |
| 2 | It **starts on a face** of a body and goes away from it (the profile is the face, or a sketch on it), also when it runs into another part of the body further on (a column next to it that leans over the face) | **Join** | Autodesk Learn ("when you extrude a face in a direction away from the existing body, the Operation type is set to Join") |
| 3 | It starts in the air and **reaches into** a body further on, by at least 1 % of its own volume (a profile beside a step, a sketch on a plane above the part extruded down into it, To Object the underside; a sliver along an edge does not count) | **Cut** | Autodesk (Strater: "intersects a solid"); the report (Hot End flats: "the dialog chose Join") |
| 4 | It only **touches** a body, face to face | **Join** | Autodesk (Strater: "Join/New Body") |
| 5 | None of these: it touches nothing; the first solid; the active component has no solid yet and the extrusion is not mostly inside another component's body (row 1b) | **New Body** | Autodesk Learn ("a New Body in the active component"); the report's bug 10 |
| | Direction Symmetric, Two Sides, Extent All, To Object, Flip, a typed or dragged distance, a negative distance | The same rows, decided again with each preview (60 ms after the last change; while an arrow is dragged, row 1 shows at once) | Autodesk (the rule names no direction); **before wave 7 a symmetric extrude never cut by itself**, which made the book's donut bite a Join |
| | The person picks an operation in the list | That operation, from then on, whatever changes in the dialog (`user_picked_operation`); a build that fails keeps the picked operation shown with the reason beside it (it used to show the old one again) | Forum (IdeaStation); Luca's brief |
| | An extrude edited from the timeline | The saved operation; it never changes by itself | as above |
| | Enter in the distance box | OK: what the dialog shows is made (the automatic choice is settled for the typed value first) | Fusion (everyday use); the report |
| | OK cannot finish (distance 0, nothing to cut, a failed build) | The dialog stays open with the reason, and the reason is said next to the mouse ("Extrude is not finished: ..."), so the click is answered | the report's pattern 1 (silent failures); **Guess** for the wording |
| | Another command is started while the dialog cannot finish | The dialog is cancelled (as before) and says so next to the mouse: "The change to Extrude was not kept: ..." (it was dropped without a word) | the report (Hot End: "feature edits that end with a warning were silently not saved") |

Which bodies count (`extrude_bodies.auto_scope`, the components builder's
`components.may_change`): **only the bodies that belong to the active component**. A body of
another component, or of a component inside the active one, never turns an extrude into a
Cut or a Join by itself. A Join the person picks joins only those bodies too (Forum: Fusion
joins "when you activate the component you want to join to"). **Deliberate difference from
what Fusion probably does for a Cut:** Fusion's Cut reaches bodies of other components (forum
"extrude-cut through all problem" asks for an "Active Component" option), so with component
A active an extrude through a body of component B most likely comes up as Cut there too. In
Fission 180 the *automatic* choice never changes a body outside the active component (the
report's bug 10: "it overlapped a body in another component and cut it, silently changing
that component"). Picking Cut by hand works as in Fusion: the Bodies to Cut row lists every
shown body in the way, other components' too, and each can be clicked away.

**A hand-chosen Cut, Intersect or To Object across components** (found by builder
"components" during the wave; scenario `book_extrude_across`, 43 checks). Sources:
**Autodesk** support, "How to extrude from one component to cut another component" (set
Objects to Cut to the component to cut) and the Extrude reference ("Objects To Cut ...
Auto-Select re-computes the bodies to cut based on the current visibility state");
**Forum**, "extrude-cut through all problem".

| Situation (Axle active; the Nozzle is another component, standing 30 mm off) | Fission 180 | Source |
|---|---|---|
| A sketch on the Nozzle's top face, E | The sketch and the extrude belong to Axle; the dialog proposes New Body (row 5) | Autodesk Learn; the report's bug 10 |
| Operation Cut by hand, -4 | The Nozzle is listed under Bodies to Cut and is cut; nothing is made in Axle | Autodesk support; Forum |
| Operation Cut by hand, +4 (up into the air) | "The cut does not go through any body", which is then true | - |
| Operation Intersect by hand | The Nozzle keeps what the extrusion and it share | **Guess** (the same list of bodies as Cut) |
| Extent To Object, a face of the Nozzle | Ends on that face, wherever the Nozzle stands | Autodesk (To Object takes any face) |
| After OK | **Axle is still the active component.** Before wave 7 the changed body, and with it the Nozzle, became active, so the next sketch and extrude went into the Nozzle (and came up as Cut). Only a body the step made (New Body, New Component), or a body of the active component, becomes the active body (`extrude_finish.activate_result`; Extrude, Revolve, Sweep, Loft, the primitives) | **Guess**: no source says an extrude changes the active component; in Fusion it changes through Activate |

Where the two readings of Fusion's rule part (Strater's "intersects a solid" against the
forum's "mostly inside / mostly outside"), rows 2 and 3 are Fission 180's reading: building
on a face stays a Join whatever it runs into (the forum's reading, and what a person means),
reaching into a body from the air is a Cut (Strater's). The report's fin on the Front plane,
overlapping the rocket by 8 % of its profile, comes up as Cut by row 1, as it did before; the
report calls that friction, Autodesk's sentence says Fusion does the same.

What changed against the rule before wave 7 ("Cut when the first 0.01 mm starts inside a
body; a symmetric extrude never cuts by itself; any shown body counts; a failed build shows
the old operation again"): row 1 for Symmetric, row 3, the active component, and the picked
operation staying put. Code: `extrude_bodies_core.auto_operation` / `scope` (unit
`test_extrude_bodies_core`), `extrude_bodies.start_state` / `in_the_way` (its third list) /
`auto_scope`, `extrude_ui._auto_operation` / `_live_operation`, `extrude_finish.SaysWhy` and
`speaking` (also in Revolve, Sweep, Loft and the primitives). Scenario
`book_extrude_operation` (ten rows, 72 checks).

### Objects To Cut: a list with check boxes, names with their component (`sf/book-extrude-2`)

Fusion lists the bodies a Cut or Intersect acts on under Objects To Cut (Autodesk, Extrude
reference: Objects To Cut, whose Auto-Select "re-computes the bodies to cut based on the
current visibility state"; the support article "How to extrude from one component to cut
another component": "For Objects to Cut, select only the component that you want to cut
from"). That each body has a check box there is the brief's description of Fusion's dialog
(Guess: no page was found that shows it). The Extrude dialog's Bodies to Cut /
Bodies to Intersect row now has that list under it: one check box for each body in the
extrusion's way, ticked when the extrude acts on it; a click on a box leaves the body out or
takes it back (what a click on the body in the view does while the row is active). With
every box cleared the dialog says that the list is empty and what to do, and OK is refused
with the reason next to the mouse. A Join shows the list only when two or more bodies are
in its way.

Bodies are numbered per component (the design's first body and each component's first body
are all "Body1"), so the list, the row's names and the log name a body with its component:
"Body1 (Block)" (`bodies.clear_name`; `bodies.named(doc, text)` finds a body from such a
name, its object name or a label only one body has, and says what to write when several
bodies share it). Scenario `book_extrude2_across` (37 checks); the older
`book_extrude_across` follows row 1b (43 checks).

## Direction and sign (wave 7)

A positive distance goes along the profile's normal, a negative one against it, in every
case (scenario `book_extrude_direction`, 41 checks; the arrow stands where the extrusion
ends). The normal is:

| The profile | Plus goes | Source |
|---|---|---|
| A sketch on the Top plane (XY) | up, +Z | Fusion (Autodesk: "along the positive normal of the sketch plane") |
| A sketch on the Front plane (XZ), or on a plane offset from it | **away from someone looking at the front, +Y**; the book's "Extrude -6" comes towards you | Book (Strandbeest: "towards you"); a third-party Fusion reference: on the XZ plane sketch X is world +X and sketch Y world -Z, so the normal is +Y. FreeCAD's Front plane looks the other way (-Y) |
| A sketch on the Right plane (YZ) | to the right, +X | Fusion |
| A sketch on a face, or the face picked itself | out of the solid; minus goes into it (and is a Cut by itself) | Fusion |

The Front plane: a sketch on it that Extrude is used on for the first time is marked
(`Fission180FrontNormal`, `extrude.adopt_fusion_side`); `extrude.profile_normal` turns the
normal of a marked sketch round, so the arrow, a Start offset, Two Sides, a click on a face to
end the extrusion and the edit dialog all agree. A sketch an extrude already used (a design
made before wave 7, a script, a golden model) has no mark and keeps FreeCAD's way: nothing
that exists changes. A Rib or Web drawn on a Front plane sketch reads the same mark for its
One Side (`parity/sweep-loft-rib.md`).

### One rule on the Front plane for every command (wave 7 follow-up, `sf/book-extrude-2`)

The same positive number now goes the same way on Top, Front and Right in every command that
counts from an origin plane (scenario `book_extrude2_planes`, 114 checks: Box, Hole, Offset
Plane, Extrude on the plane, Extrude on the offset plane, Cylinder, undo / redo, each on the
three planes with the same keys).

| Command on the Front plane (XZ) | Fusion | Source | Fission 180 |
|---|---|---|---|
| Extrude of a sketch | plus is +Y | Book; third-party Fusion reference (sketch x = X, y = -Z) | the sketch's mark (first builder) |
| CONSTRUCT > Offset Plane | "Positive offset goes in the plane's normal direction. For XY: +Z. For XZ: +Y" | third-party Fusion reference (a Fusion scripting guide); Forum (Autodesk community: "XZ plane (FRONT): up and down swapped", i.e. sketch y = -Z, normal +Y) | a new plane notes `Fission180FrontNormal` and counts against FreeCAD's normal (`construct.offset_side`); its arrow points to +Y; a formula is kept as `-(formula)` on the offset and read back as typed; a plane offset from such a plane counts the same way |
| Box, Cylinder (Height) | plus goes along the plane's normal, +Y, like an extrude and an offset from the same plane (a Box is one "Box Primitive" step in Fusion's timeline, not a sketch and an extrude: Forum) | Guess for the sign (no page found that states it; the plane's normal is the one direction Fusion's other commands count along) | a new primitive notes `"front": true` in its options and is built in Fusion's frame of the Front plane (`primitives.front_turned`, `FRONT_TURN`: x = X, y = -Z, z = +Y) |
| Coil (Height) | as Cylinder | Guess (same construction) | the same note |
| Sphere, Torus | lie in the plane's middle: no side | - | the note, no visible change |
| Hole from a sketch point | drills into the part | Guess (what `hole.py` was built to in wave 3: "Fusion drills into the part"); checked in the scenario on the three planes | already so (`hole.py` turns the hole into the material); nothing changed |
| Rib, Web (One Side) | plus is +Y | as Extrude | the sketch's mark (first builder) |
| Revolve (angle), Sweep (distance along the path), Loft, Emboss (depth from the face), the Move triad (world axes) | do not count from a plane's normal | - | nothing to turn |

Only NEW objects count Fusion's way: a primitive, coil or offset plane made in its dialog
from now on. One made before (no note), and one made from code without the note, keeps
FreeCAD's way; edited in its dialog it keeps its side (the scenario's last three steps: an
older box on the Front plane lies from -10 to 0, its arrow points to -Y, a new height of 15
gives -15 to 0).

**The AI tools** (`ai/ops/core.py`, also the language of the golden models) keep their own
documented convention: "XZ (normal -Y)", a positive distance, height or offset goes along
that normal. Chosen because the same step list must build the same solid as before (golden
models, saved scripts, an AI's earlier calls), and their documentation states the normal with
every plane. Two things were done so that this stays true next to the dialogs: the extrude
op turns its options round on a sketch that a person's Extrude marked Fusion's way
(`_along_plane_normal`: the step still goes to -Y), and the tools' help text says that a
number typed in a dialog for a step on XZ has the other sign. Gear (`gear*.py`, modify's)
still counts its thickness FreeCAD's way on the Front plane.

The report's two other sign cases: "Cylinder Height -8 came out going +8 into the first
body" was the typed -8 landing in the box of another arrow (the one the mouse rested on);
the height is now the next typed value after placing (`parity/primitives.md`). "-8 grew INTO
the body" is that same entry in the report's summary.

## Sketch areas keep their identity (wave 7)

The report's drone: "Not changed: with Arm_Length = 60, Extrude 1 would break: Sub shape
not found: Sketch.InternalFace56. The extrude stores sketch areas by number and the numbers
change." What really happens (FreeCAD 1.1.4): a link to a sketch area holds FreeCAD's
internal name for it, made from the corners of its curves; when the curves around the area
change that name is gone, FreeCAD marks the link "?InternalFace56" and the step fails, though
the area is still there, often under the same number. In other cases FreeCAD renames the
link by itself and picks the wrong area without a word (a square of a grid with a hole moved
onto its edge: 17 of 18 squares extruded, no error). Plain scaling (every dimension following
one parameter) FreeCAD gets right.

Fission 180 now notes, for every step that links to sketch areas (Extrude, Revolve, Sweep,
Loft, their hidden profile helpers), what bounds each area: the sketch curves by their
stable ids (FreeCAD's `GeometryFacade.Id`, which survives deleting other curves and
reopening the file) and the side of each curve the area is on, plus a point inside
(`sketch_area_id_core`, property `Fission180AreaIds`). Right after a sketch is computed, and
before the steps that use it, the areas FreeCAD lost or renamed wrongly are found again and
the links written with the numbers they have now (`sketch_area_id.follow`). A curve drawn
across an area, or one deleted, falls back on the most similar bounds, then on the point. A
design made before gets its notes before its first change after opening (kept in memory:
opening a design does not change it). Slivers of next to no area, left where pattern copies
or tangent arcs lie on each other, are never offered as profiles (`extrude.sliver_areas`; the
report's carabiner: "27 regions, many of them zero-area slivers").

Tests: `sketch_area_id_check` (headless, 64 checks, run by `test_sketch_area_id_freecad`): two
overlapping circles moved past each other five times; a 6 x 6 grid with a hole (37 areas),
the 18 squares of a checkerboard extruded, the pitch changed four times, then the hole moved
onto lines and corners six times; the same through Start: Offset's helper; a revolve; a
design saved without the notes; undo / redo. Unit `test_sketch_area_id_core` (16).

## Picking profiles (wave 7)

| Fusion (source) | Fission 180 |
|---|---|
| A click where a shown sketch's profile lies behind a body face takes the profile (the report: "Fusion prefers the sketch profile"; Fusion draws sketches through bodies) | Same in Extrude, Revolve, Sweep and Loft (`ProfilePicker(through=True)`): the area behind the part is drawn as a faint blue through it and lights up under the mouse. Only an area that is already picked leaves the click to the face in front (so a click on a face further on still ends the extrusion there). It used to pick the face |
| A sketch's profiles can be picked while its body is hidden (Book: the nozzle's revolve cut "with the body hidden") | Same: a hidden body is in front of nothing (`profile_pick.shown_part`). Nothing could be clicked |
| "If there is one visible sketch, and if that sketch contains one profile, Extrude will auto-select that profile" (Forum, an Autodesk community manager; Autodesk help: "only one profile visible in your design") | Extrude and Revolve take the newest unused sketch's single area as before, and now also the one profile in view whichever body or component its sketch is in (`profile_pick.only_visible_profiles`) |
| Small things can be clicked in a fitted view (Guess: Fusion's pick radius) | A click up to 4 pixels beside an area takes it (a slot 0.4 mm wide); the rim of a small flat face takes the face (an edge with exactly one flat face toward the viewer); an edge that could mean two faces says so instead of doing nothing. Only a single click counts: the edges a selection window takes along with a face are ignored, as before |
| A box that wants faces or profiles does not take a construction plane (Guess from Fusion's selection filters) | A click on an origin or construction plane's square or axis, in a box that cannot use it, goes to the face behind it (`profile_pick.behind_glyphs`): Extrude's Profiles, Loft's Profiles. (Split Face, where the report met it, is the modify builder's) |
| The value boxes do not hide what is to be clicked next (Guess) | The boxes keep off the six nearest areas not picked yet (`ExtrudePanel._areas_to_keep_free`); the book's thruster: the box sat on the circle's other half |
| Zero-area slivers are no profiles | Never offered (above) |

Not reproduced on develop (0.1.0-beta.3.3.10), and now checked by `book_extrude_picking`:
"starting Extrude hides the shown sketch again" (it stays shown), "Start: Offset lets no
profile be picked" (it does), "the first clicks right after the dialog opens are lost" (the
first click in the same breath is taken), "profiles over a void go to the face behind"
(three circles over a bore are each picked). Scenario `book_extrude_picking` (eleven paths,
49 checks).

## Touching profiles taper as one outline (wave 7)

Forum: adjacent profiles picked together are extruded "like one giant square" and "all
combine into one body, even though the taper angle should cause them to not be connected".
Book: the thruster's circle, split in two by the rocket's projected edge, becomes one cone.
Fission 180 tapered each profile by itself (FreeCAD's Pad does) and so held -11 degrees at
-6.8. Now the profiles that touch are joined into one outline before the taper
(`extrude_prism.merged_faces`); such an extrude is Fission 180's own extrude feature
(`extrude.tapers_as_one`). Profiles that do not touch stay separate. Scenario
`book_extrude_taper` (22 checks).

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

In these dialogs: Press Pull / Offset Face (the distance both ways: a push into the part
stops before it would remove the body or cut it in two; Q on edges: the new fillet's
radius; a fillet / chamfer face clicked: the radius or distance of FreeCAD's step),
Extrude (Taper Angle and side two's, Wall Thickness of a thin extrude, both sides;
checked by building the extrude itself, FreeCAD's Pad / Pocket refuse the taper). Not
held: Press Pull's Modify Existing Feature (the extrude's own length) and a size of
Fission 180's own fillet step clicked with Press Pull (its refusal stays). Scenarios
`limits_presspull`, `limits_extrude`.

## The drag arrow and the taper disc: one look, one screen size (branch `sf/arrows`, 2026-10-18)

Luca: "can we streamline the drag arrows? ... Fission 180 has some janky looking arrows and
sometimes they are oversized and sometimes they are tiny. It should be a consistant size. same
thing for the angle dragger", with a picture of Fusion's Extrude on a cylinder's top face.
Why they varied: Extrude sized its arrows from the profile (15 % of its diagonal, 4 to 30 mm),
the other dialogs from the zoom at the moment the arrow was made (then not again when you
zoomed), Move's manipulator from the bodies (0.45 x their size), and every tool had its own
proportions (Coin's double-headed dragger, a ball with a cone, a curved band). Now one rule
for all (`handle_look_core.py`, unit `test_handle_look_core`; Coin nodes in `handle_look.py`),
drawn in pixels under FreeCAD's SoShapeScale so the size is right on every frame:

| Fusion (Luca's picture) | Fission 180 | Source |
|---|---|---|
| A small solid blue arrow, short shaft and wide head, thin light outline, slightly shaded, about 30-35 px | 32 px from foot to tip (head 13 px long, 15 px wide; shaft 4.5 px wide), blue (0.16, 0.50, 0.93) shaded, a 1.5 px light outline | Luca's picture; exact pixels and colours **Guess** |
| It stays the same size on the screen whatever the part or the zoom | Same: scenario `handle_size` (a 4 mm and a 400 mm block, Fit / zoomed out / in: the arrow's projected length, the blue pixels of the drawn arrow and the scale Coin drew it with all agree within 2-3 px / 2 %) | Luca's picture, everyday Fusion |
| The arrow sits on the face / at the end of the extrusion and points the way it extrudes | It stands at the distance's point and points the way the distance goes (back down for a cut) | Luca's picture; the flip for a minus distance is a **Guess** |
| A thin light line from the profile along the extrude direction | Same, from where the arrow starts (the profile, or the start offset) to its foot | Luca's picture |
| The taper (angle) handle: a small white disc with a dark dot, on a thin light arc | A 19 px white disc facing the viewer, a 6 px dark dot, a thin grey rim, on a light arc 30 px each side of it | Luca's picture; sizes **Guess** |
| Lighter under the mouse and while dragged | The arrow turns light blue, the disc light blue | **Guess** (usual Fusion feel) |
| The value box beside the handle | Unchanged (`taskui.ValueBoxes`), now beside the small arrow / disc | as before |
| Easy to grab | A press up to 4 px off the drawn arrow or disc still takes it: round the head, round the slim shaft, and just past the tip, never behind the foot (the foot stands on the profile, a pattern copy's dot or a face, which must stay clickable). What Coin picks is kept at the view's scale by the handle's poll from the moment it is made, so a press right after a new arrow or a zoom finds the arrow where it is drawn | **Guess** |

The same look and size for every distance arrow and angle handle: Press Pull, Hole, Thread, Rib
/ Web, Emboss, Fillet / Chamfer, the Patterns, Insert / Decal, the surface tools, Offset Plane
and Plane at Angle, Section and the mesh plane cut, Shell / Scale (pickpanel), the primitives
and Pipe, Revolve's angle (a disc on its arc), Draft's angle, Move / Copy's manipulator (its
arrows 96 px from the centre, the turn handles' discs on their arcs, in the axis colours) and
the 3D sketch's point arrows. What each handle drags, its snapping, value box and protractor
are unchanged.

## Value boxes on the remaining handles (branch `sf/polish-2`, 2026-10-16)

Fusion shows the value beside every manipulator while a command is open, and a number typed
with the mouse over the view goes into the box of the handle in use. Sources: **Autodesk**
help "Scale sketch geometry" (type the scale factor or drag the manipulator handle, OK or
Enter ends the tool); **Forum** (Autodesk support: the value changes while dragging, zoom in
for finer steps); the rule that every handle carries its box is Fission 180's reading of
Fusion's dialogs (`value_box_dialogs` scenarios); **Guess**: where exactly each box sits and
that Move shows no box before a handle is used. Handles that had none get one, owned by their dialog
(`taskui.ValueBoxes`) and kept beside the handle by `taskui.BoxCarrier`:

| Handle | The box shows / takes | Code |
|---|---|---|
| Move's triad (Free Move, Translate) | One box beside the handle in use (last dragged, or under the mouse): an arrow's X / Y / Z Distance, a turn handle's X / Y / Z Angle, the Pivot X / Y / Z while Set Pivot moves the manipulator. It never covers the triad's other arrows, arcs and balls (`BoxCarrier.box_avoid`): the mouse over one moves the box to it. No box before a handle is used (Guess). | `move_ui.Triad` (also Components' Move) |
| Insert Mesh's manipulator (the same triad) | X / Y / Z Distance on an arrow, X / Y / Z Angle on a turn handle | `insert_ui.InsertMeshPanel` |
| Move, Rotate | The Angle beside the blue turning handle | `move_ui.MovePanel._make_turn_handle` |
| Scale's arrow(s) | Scale Factor (Uniform) or X / Y / Z Scale (Non Uniform), formulas too | `scale_ui` |
| Draft's angle disc | The draft Angle, formulas too | `draft_ui` |
| Construct (Offset Plane, Plane at Angle, Tangent Plane, along a path) | Distance / Angle, or the fraction along the path while Distance Type is Proportional | `construct_ui` |
| Section Analysis | Distance, X Angle, Y Angle beside their three handles | `section_ui` |
| Sweep's Distance balls | Distance (a share of the path, 0..1), formulas too | `sweep_ui`, `curve_pick.PathHandle` |

Typed in a box: Tab or a click elsewhere takes the value; Enter takes it and finishes the
command (OK), as everywhere in Fission 180 (Fusion: Enter in the box completes the command).
Every value box now also keeps out from under FreeCAD's floating command dialog over the
right of the view (it could be placed there, hidden; `ArrowValueBox._covered`). Scenario
`polish2_value_boxes` (Move typed in the X arrow's box, digits typed over the view into the Z
arrow's box, the Z turn handle's angle and Enter, Scale's factor, Draft's angle, Insert
Mesh's Z arrow, undo / redo, Esc / Cancel).

## Click a face to end the extrude (Luca's request, branch `sf/fix-extrude-to-face`, 2026-10-16)

Luca: "when extruding, clicking on a face should bring that extrusion to the same height as
that face". Sources (autodesk.com and the Autodesk forum were readable only through search
excerpts): **Autodesk** API reference `ExtrudeFeatureInput.profile`: "when an
ObjectCollection is used all of the profiles and faces must be co-planar"; **Autodesk**
Extrude reference: To Object ends at "a body, face, or plane". **Forum** "Extrude to Face /
Edge / Vertex" (Autodesk Community): To Object is parametric; without it "Fusion still
extrudes/revolves to that object but not parametrically, it only sets the extrusion distance
... to the current value"; "the 'To Object' in Fusion supports only Face, Body and Vertex, but
not Edge". **Forum** "Common Bug/Issue when using Extrude tool and snapping to surface or
face": fixed "by editing the existing extrude/push/pull feature, and dragging the arrow and
clicking on the face to snap to again". **Forum** (Press Pull): "Once you start the drag,
clicking a face will cause the face being dragged to snap to the clicked face". **Forum**
IdeaStation "Extrude to limit" (an Autodesk alumnus): Snap To "infers a distance value after
indicating a parallel plane". **Forum** (Shapr3D community, a user describing Fusion): "you
just click on any other geometry at that extent, a surface, a point, an offset, and the
extrude calculates the distance it needs to extrude by and snaps to the distance". **Forum**
"how do I extrude up to a body?": a curved surface is reached with the To extent. **Guess**:
rows marked so (Fusion's own wording is never copied: the dialog's words are Fission 180's).

| Fusion (source) | Fission 180 |
|---|---|
| The profiles of one extrude lie in one plane (Autodesk) | Once a profile is picked, a click on a face out of the profile's plane is no profile: it says where the extrusion ends. A face in a profile's plane is picked or dropped as before; with the Profiles box empty a click on a flat face is the profile, as before (Guess: Fusion's first selection box takes the clicks until it has something) |
| Distance extent: a picked face or point sets the distance to reach it, not parametric (Forum) | A flat face parallel to the profile, a vertex, or a parallel construction plane sets Distance to the exact number (minus for one below), Extent stays Distance, the arrow and its value box move there, and the dialog says "Up to the face: 12.5 mm" ("the point", "the plane"); typing or dragging afterwards drops the words |
| Dragging the arrow over a face snaps to it (Forum, twice); a parallel plane gives the distance (Forum) | While the arrow is held, the mouse over a parallel flat face or a vertex makes the distance that height exactly (the preview and the value box show it, the face or point is marked in blue); let go there and it stays, the arrow jumps to it. Over anything else the arrow drags as before (two decimals). A press on the arrow let go without moving snaps to nothing. While the button is down Coin's arrow keeps following the mouse (its dragger takes its position from the mouse on every move), so the arrow itself jumps on the release |
| Two Sides, Symmetric (Guess) | Two Sides: the side the face is on (side one is the way its distance points); Symmetric: the same distance each way (Whole Length: twice it) |
| A face the extrusion cannot end on at one height: To Object (Autodesk; Forum for curved surfaces) | A curved or tilted face switches Extent to To Object with that face (Extend To Selected Face): "Ends on the curved face (To Object)". Symmetric cannot go To Object (Fusion's dialog): refused, with what to do. A side already To Object takes a clicked flat face as its new object (Guess). A face running along the extrusion is refused with the reason; an edge does nothing (Forum: To Object takes no edge) |
| Press Pull on a sketch area is an Extrude (Fusion) | The same clicks and snaps in the Extrude it opens |
| Every operation, edit from the timeline, one undo step | Join, Cut (a click below the sketch into the part turns it into a Cut by itself), New Body, bodies in (moved) components, edit from the timeline, Esc / Cancel, Undo / Redo, save / reopen (a plain length is stored) |

Found on the way: **FreeCAD's Pad "up to face" on a curved face of another body ends in the
wrong place** (a post up to a cylinder's underside came out 22494 mm^3 instead of 4753, through
the cylinder). To Object on a curved face of another body is now Fission 180's own extrude
feature (`extrude.curved_elsewhere`, in `_structure`), which ends exactly on the face; golden
`extrude_to_cylinder_face`. With a curved face of the same body the Pad is right and stays a
Pad (an older one with later steps on it could not change its kind).

Built in `extrude_to_face_core.py` (the rules and words, Qt-free, `test_extrude_to_face_core`),
`extrude_to_face.py` (what is under a click or the mouse, the snap mark) and `extrude_ui.py`.
Scenarios `extrudeface_basic`, `extrudeface_sides`, `extrudeface_objects`, `extrudeface_drag`.

## Wave 4: To Object's Extend and Offset, a Start Object that follows (branch `sf/modeling-2`, 2026-10-14)

Sources: **Autodesk** Extrude reference, through search excerpts: To Object ends at "a body,
face, or plane"; "Extend (To Object extent type only) determines how the end of the extrusion
meets the selected object"; Start Object "starts extrusion from a face or plane that you
select"; the Extend labels To Selected Face, To Adjacent Faces, To Body, Through Body are
Fusion's dialog words (help "Extrude a solid body"). **Forum**: "Very Buggy Extrude From Object
To Object" (defect FUS-116774). **Guess**: rows marked so.

| Fusion (source) | Fission 180 |
|---|---|
| To Object a face, **Extend**: To Selected Face (the face's surface extended) or To Adjacent Faces (the face and its neighbours as they are) (Autodesk) | Same choice in an Extend row, for side one and side two. To Selected Face as before. To Adjacent Faces: the extrusion ends on the face and on the faces that share an edge with it (a column partly over a slope ends on the slope there) (golden `extrude_to_adjacent_faces`) |
| To Object a body: To Body or Through Body (Autodesk) | To Body: up to where the extrusion first meets the body (as before); Through Body: on through the body to its far side (golden `extrude_through_body`) |
| To Object a plane: no Extend choice (Guess: a plane is endless) | Same: the row hides |
| **Offset** from the object (Autodesk) | An Offset field for each side with To Object (it takes formulas): the end moves that far past the object, a negative value stops short of it (golden `extrude_to_object_offset`) |
| **Start: Object** follows when the object moves (Guess: Fusion is parametric there too) | A hidden helper measures the start offset from the profile to the object at every recompute, so the extrusion moves with the face or plane when an earlier step changes (golden `extrude_start_object_follows`) |

Tests: scenario `modeling2_extrude` (To Adjacent Faces and To Selected Face measured, edit
from the timeline, undo / redo, Esc, a plane with Offset -5, save / reopen); the goldens above
and `extrude_to_selected_face_extended`.

## Extrude

| Fusion | Fission 180 |
|---|---|
| Profiles: click closed areas; click more to add, again to drop | Same. Areas are FreeCAD's own sketch regions (`MakeInternals`, `InternalFaceN`): a circle in a rectangle gives the ring and the disc; crossing curves split areas (two overlapping circles: 3 areas). Flat faces of the part are profiles too. |
| One profile is picked by itself | A sketch just finished (or selected) with exactly one area is taken at once; with several, E waits for clicks. |
| Start: Profile Plane / Offset / Object | Same. Offset has its own blue arrow. Object: a flat face or plane parallel to the profile. |
| Direction: One Side / Two Sides / Symmetric | Same. Two Sides has a Side Two group (extent, distance, taper). Symmetric has Measurement Half / Whole Length (Half by default). |
| Extent: Distance / To Object / All | Same. To Object: a face, a plane or another body (extends the face's plane). All: through everything, with Flip. |
| Taper Angle with a handle | Field plus a curved blue handle at the end of the extrusion; negative narrows (as Fusion). |
| Operation: Join / Cut / Intersect / New Body / New Component | Join, Cut, Intersect, New Body, New Component (`parity/components.md`). Dragging into the part switches to Cut unless you chose. The first solid shows New Body. |
| Live preview, OK / Cancel / Esc, one undo step | Same. Esc works with the mouse in the 3D view. |
| Manipulators drawn over the model and grabbable through it | Same (2026-10-13, Luca: "arrows get occluded by bodies"): the arrows, the taper disc and the hole's position handle are drawn in front of any body (Coin's annotation node) and a press on a visible arrow starts the drag even when a body is nearer to the camera (pick style "shape on top"); `taskui.on_top_root`, scenario `handles_on_top`. The whole drawn arrow is grabbable, the half that sits inside the part included: a press on its line takes the arrow, a press beside it picks the face (`extrude_presspull_qa3` P14). |
| Edit from the timeline: every option again; the profile sketch is shown while editing | Double-click: profiles, start, direction, extents, taper, operation come back (stored on the feature). The extrude's sketch is shown for the edit and hidden again on OK or Cancel, outside the undo step (Undo after OK never flips it); also for an extrude through several bodies. |
| Errors in the dialog | The message shows in the dialog and OK waits; FreeCAD's own recompute messages are kept out of the Report view while the dialog previews. |
| Starts at 0: nothing pops out until you drag or type (Luca R5) | Same: the arrow is there to drag at 0 and the dialog says "Drag the arrow or type a distance."; OK / Enter at 0 keep the dialog open and say the distance must not be zero. Two Sides: side two starts at 0 too (the preview shows side one alone). Scripts and golden models keep 10. |
| Live preview while dragging (R2) | The part follows the arrow while the button is held (rebuilt every 60 ms, up to 400 ms on a heavy part while a drag streams changes). The same in every Fission 180 dialog. |
| Distance shown next to the arrow, editable (R3); a number typed with the mouse over the view goes into it | A value box beside each handle (distance, side two, start offset, the taper disc) shows the dialog's value with units, never over a handle or another box; click it, type a value or formula, Enter (= OK) or click elsewhere (that click only leaves the box). Esc in it cancels. A digit, minus or decimal point typed with the mouse over the 3D view goes into the box of the handle last dragged or hovered (else the distance) with its text selected, so you type straight on; FreeCAD's view keys 0-6 no longer turn the view while a dialog is open. The same boxes in Hole, Fillet / Chamfer, Revolve, Box / Cylinder / Sphere / Torus / Coil, Pipe, the Patterns, Rib / Web, Thread and Shell (`taskui.ValueBoxes`, `taskui.TypeOverView`). |
| Sketch stays visible until OK (R6) | Same: hidden on OK in the same undo step (Undo shows it again); Cancel / Esc leave it. E or Q inside an open sketch open their dialog after FreeCAD's "leave sketch" step, so Cancel cannot undo that. |
| Cuts preview in red (R7) | A see-through red copy of the removed volume with a red outline (picture only, clicks pass through); "All" stops at the far side of every body it cuts. Press Pull pushing into the part shows the removed slab in red. |
| Pick one closed area of a sketch (R1) | Same, inside the open sketch (click; Shift / Ctrl add; click again drops; Esc, empty space or a curve drop) and after Finish Sketch (areas shaded, light up, a click selects one). E / Q extrude exactly the picked areas; Q with several opens Extrude with all. A whole sketch selected + E takes its areas (holes stay holes). |
| Objects To Cut: one extrude through several bodies (R8, "objects being edited") | Same, one timeline step. Row "Bodies to Cut / Join / Intersect" with "N bodies" and the names; click the row, then a body to leave it out or take it back; while the row is active the listed bodies show as see-through blue copies (picture only). Cut / Intersect: hidden follower steps in the other bodies; Join merges the bodies it touches; a Join touching nothing is a New Body. A cut through no body says so and OK waits. The step can be dragged along the timeline like any other (its follower steps go to the matching place in each body); the one refused move, with a plain message, would put it before a body it changes exists. |
| Automatic Cut / Join / New Body | Cut when the extrusion starts inside any shown body (a 0.01 mm start slice, at least 1 % inside); Join when it touches a body face to face; else New Body. Decided with the preview, not on every key. |

### Thin Extrude (2026-10-13, branch `sf/gaps`)

Sources (Autodesk's own pages are not reachable from the sandbox; their search excerpts are
quoted): **Autodesk** Extrude reference (SLD-REF-EXTRUDE): Type "Thin Extrude: extrudes a thin
wall along selected open or closed profiles"; "Wall Location (Thin Extrude type only): Side 1,
Side 2 (offset the extrusion to one side of the profile), Center (centers the extrusion on the
profile)"; "Wall Thickness (Thin Extrude type only)". **Autodesk** API reference:
`ExtrudeFeatureInput.setThinExtrude(wallLocationOne, wallThicknessOne, wallLocationTwo,
wallThicknessTwo)`, so a Two Sides thin extrude has a wall location and thickness per side;
`ThinExtrudeWallLocation` Side1 / Center / Side2. **Forum** (Autodesk Community, "Thin Extrude
issue", "Thin extrudes of open sketch lines"): open sketch lines can be picked once Thin
Extrude is on; a user reports the wall goes inside the line by default and Side 2 puts it
outside. **Tutorial** (techandespresso "Thin Wall Tool"): a taper can be set with a thin
extrude. Not found anywhere: the default thickness (Fission 180: 1 mm, **guess**), which side of an
open curve Side 1 is (Fission 180: the left of the curve as drawn, seen from the sketch's normal,
**guess**), sharp or round outer corners (Fission 180: sharp, **guess**), a drag handle for the
thickness (none found; Fission 180 has none).

| Fusion | Fission 180 |
|---|---|
| Type: Extrude / Thin Extrude, first in the dialog | Same (a drop-down). Thin Extrude shows Wall Location and Wall Thickness under the taper (and again under Side Two for Two Sides) |
| Profiles: closed areas and flat faces (the wall follows every loop of their outline: a rectangle gives a tube, a ring a wall at both circles), and open sketch curves | Same. A click on a sketch curve takes the curves joined to it (an L of two lines is one profile); a click on a picked curve drops them; picked curves are drawn in blue, a curve under the mouse lights up |
| Wall Location Side 1 / Center / Side 2 | Same. Side 1: into a closed profile (out of a hole), on the left of an open curve; Side 2 the other side; Center half each way |
| Wall Thickness (parameters and formulas) | Same; default 1 mm; too thick for the profile: held at the thickest that works and said (Luca, 2026-10-21); a formula that is too thick is explained ("closes up inside it") and OK waits |
| Every extent, direction, start, taper and operation | Same: a taper tilts the wall and keeps its thickness (a positive taper leans it towards Side 2, outward for a closed profile); To Object, All, Two Sides, Symmetric, Offset / Object start; Join / Cut / Intersect / New Body / New Component, the automatic operation and the bodies row use the wall, not the area inside it |
| Edit from the timeline, undo / redo | Same (everything comes back, also the curves) |
| Turning Thin Extrude off with curves picked | The curves are dropped and the dialog says why (a solid extrude needs areas or faces) |

Built as Fission 180's own extrude feature (`fission180.extrude.ExtrudeFeature`, properties `Thin`,
`WallLocation(2)`, `WallThickness(2)`); the wall's cross-section is worked out in
`extrude_prism.thin_walls` (OpenCASCADE's 2D offset of each loop or curve; a straight curve is
done directly, OpenCASCADE finds no plane for it). Golden models `extrude_thin_tube`,
`extrude_thin_open_l`, `extrude_thin_arc_center`, `extrude_thin_taper_center`,
`extrude_thin_to_cylinder_face`; scenario `gaps_thin_extrude` (4 paths).

### Taper with every extent (2026-10-13, branch `sf/gaps`)

Sources: **Forum** (Autodesk Community, "How to get the extrusion taper with an offset"): a taper
with To Object is measured against the "to" object; **Autodesk** Extrude reference: To Object
ends at "a body, face, or plane". So the taper works with To Object whatever the object is, and
each side of Two Sides has its own taper.

| Fusion | Fission 180 |
|---|---|
| Taper up to a flat face or plane | Same (since the first QA pass) |
| Taper up to a curved face | Same: the extrusion ends on the face's whole surface (a cylinder's face: the whole cylinder) |
| Taper up to a whole body (picked in the browser) | Same: the extrusion ends where it first meets the body; a profile partly missing the body is said in the dialog |
| Two Sides: a taper per side | Same (Side Two's Taper Angle) |

FreeCAD's Pad ignores a taper up to a face or a body, so these are Fission 180's own extrude
feature (`extrude_prism._to_shape`: a long prism split by the face's surface or cut by the
body, keeping the piece that holds the profile). Golden `extrude_taper_to_body`; scenario
`gaps_extrude_taper_to` (a column tapered up to another body, edited, undone; Two Sides with
a taper per side).

How it maps onto FreeCAD: Join/Cut are PartDesign Pad/Pocket (patterns, mirror and parameters
keep working on them). Intersect is a Fission 180 PartDesign feature (`fission180.extrude.ExtrudeFeature`)
that keeps the part of the body inside the extrusion. New Body creates a PartDesign Body that becomes
the active one. When FreeCAD cannot link the profile directly (start offset, profiles from several
sketches, a profile in another body) a hidden SubShapeBinder carries it into the feature.

## Press Pull

| Fusion | Fission 180 |
|---|---|
| Faces: offset, neighbours extended or trimmed | Same: slabs are added/removed, then the step faces left at sloped neighbours or shared corners are removed with OpenCASCADE's defeaturing, which extends the neighbours (golden `pp_multi_face_corner`, `pp_slanted_neighbours`, `pp_three_faces_corner`, `pp_slanted_side_pull`, `pp_slanted_push`). |
| Several faces; click again to drop | Same, also on the moved face in the preview. Tangent Chain picks smoothly connected faces (off by default). |
| Edges -> fillet, fillet face -> radius | Same as before. |
| Q on a sketch profile -> Extrude | Same: visible sketch areas are shaded while Press Pull waits. |

## Known gaps (honest list)

- **Complex shapes: work in progress** (Luca, 2026-10-16: "press pulling complex shapes is
  rough. the whole program freezes ... the shape it spits out is all sorts of
  'interesting'"). Faces that are not planes or cylinders go through OpenCASCADE's offset
  with fill and then defeaturing, and every preview tick rebuilds the whole document; on
  freeform or many-face picks that is slow and the kernel's result can be odd. Until the
  face-editing engine (outline 9.1) handles them, the Press Pull icon carries a small
  yellow warning triangle, the ribbon tooltip and the dialog say "Work in progress: on
  complex shapes ... can be slow and give odd results" (scenario `limits_notes` A).

- **Click a face to end the extrude** (2026-10-16): Press Pull on a *face* (an offset, not an
  extrude) does not snap its arrow to a clicked face yet (Fusion does once the drag started,
  Forum); the dragged arrow snaps to parallel faces and vertices, not to edges, sketch points
  or construction planes (a plane works with a click); the arrow itself jumps to the face
  only when let go (Coin's dragger, see the section at the top); a copy of a component (an
  App::Link instance) gives the height of the original's place, like every face pick of the
  extrude; a sketch area of another sketch at another height is still taken as a profile, as
  before (Fusion keeps the profiles in one plane); a sketch area hidden behind *another*
  body still takes a click there (the hiding test looks at the profile's own body only).

- Thin Extrude, New Component and tapers with every extent are built (sections above). Thin
  Extrude's defaults (1 mm, the side an open curve's Side 1 is, sharp outer corners) are
  guesses to check in Fusion.
- **To Object options** (2026-10-14): Extend and Offset are built (section at the top). Found
  on the way, not fixed: a Cut To Object a face that FreeCAD makes as its own Pocket, with the
  profile partly inside the material, also cut away material above the profile plane (900
  instead of 720 mm^3 in the scenario's first try, where the pocket's square overlapped the
  column extruded before it); the scenario's pocket was moved off the column.
- **Start: Object** works with flat faces/planes parallel to the profile (it follows them since
  2026-10-14).
- Several disjoint profiles in one extrude give one body with several solids, as in Fusion
  (FreeCAD 1.1's bodies allow it). A Join that touches no body at all is made as a New Body
  (also from scripts and old steps that have no bodies list; 2026-10-13, sources in
  `parity/revolve.md`); one whose profiles only partly touch keeps the far piece in the body,
  like Fusion's multi-lump bodies (guess).
- Value boxes: every handle has one since polish-2 (section at the top). Which handle a typed
  digit goes to (last dragged or hovered, hover = within the handle plus 14 px) is Fission 180's
  guess. The red colour and transparency of the cut preview, and the blue of the highlighted
  bodies, are Fission 180's choice, not measured.
- Chamfer with Distance and Angle: the arrow sits on the face toward the viewer but still sets
  Distance 1 (measured on the reference face).
- Several bodies (R8): the list is not checked again when an earlier step changes; patterns and
  mirror of a multi-body extrude repeat only the sketch's body; hidden bodies are never listed;
  To Object up to a whole body acts on the sketch's body only; the highlight shows each body as
  it was before this extrude.
- Sketch areas after Finish Sketch light up and select in FreeCAD's yellow / green (Fission 180 does
  not change FreeCAD's selection colours); heavily crossing curves can shade more pieces inside
  the open sketch than FreeCAD makes areas (a pick extrudes the smallest area around it).
- Ctrl+Z / Ctrl+Y are not bound while Fission 180 is on (FreeCAD only honours them with its menu bar
  visible); the application-bar Undo/Redo buttons work.
- Journey pass (sf/journey-pl): New Body chosen after the automatic Join had put the preview
  into a touched body of another component made a second body and left the sketch's own empty
  body beside it; the empty sketch body takes the new solid now. Open question: a Join
  touching only another component's body joins into it (documented above); Fusion keeps a
  feature's new bodies in the active component (G), where New Body may be the better guess.
