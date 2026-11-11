# Wave 7, builder "extrude" (branch `sf/book-extrude`, 2026-11-11)

Extrude, Revolve, Sweep, Loft, the primitives and profile picking against the book parity
report (`docs/fission180/dev/research/book-parity-report.txt`), brief
`docs/fission180/dev/briefs/book-extrude.md`. Everything was reproduced first in real FreeCAD
1.1.4 with probe scenarios (real input), then fixed, then proven with the scenarios below.

## What the report said, what I saw, what Fusion really does

| # | Report item | Reproduced on develop (3.3.10)? | Fusion (source) | Root cause | Fix |
|---|---|---|---|---|---|
| 1a | Symmetric turned Cut into Join; Enter then joined (donut) | Yes | A profile inside a body is a Cut whatever the direction (Autodesk: Strater "If the Extrude intersects a solid, it will default to Cut"; Book) | `auto_operation(..., symmetric=True)` never returned Cut; `starts_in_material` returned False for Symmetric | Row 1 of the rule: Symmetric counts when both sides start in material |
| 1b | After Flip (Extent All) the operation stayed Join (surfboard) | No: Flip already turned it into a Cut | Cut (Book) | - | Covered by row R4 of the scenario |
| 1c | A fin came up as Cut (Saturn V) | Yes (by design) | Cut too: the fin overlaps the rocket (Autodesk: "intersects a solid"); the report's expectation of Join has no source | - | Kept; documented |
| 1d | Symmetric + All: Cut became Join, OK "did nothing", stale warning (pizza cutter) | Yes: the Join added nothing and OK closed on it | Cut | as 1a | Row 1; a refused OK now says why next to the mouse |
| 1e | Bug 10: a new component's first extrude was a Cut of another component's body (and -5 a Join into it) | Yes, both | New Body "in the active component" (Autodesk Learn); Join only joins bodies of the active component (Forum). That an overlap with another component's body is no Cut is a deliberate guess: Fusion's Cut reaches other components | Every shown body decided | Only bodies of the active component decide (`extrude_bodies.auto_scope`, the components builder's `components.may_change`) |
| 1f | Hot End: To Object the underside "chose Join"; an edit to Cut showed Join again; edits with a warning silently not saved | Partly: Join yes (the profile starts in the air beside the post); the edit to Cut worked in my model; a failed build did put the old operation back; another command started on a dialog that cannot finish dropped the edit without a word | Cut for an extrusion that reaches into a body (Strater) | The rule only looked at the first 0.01 mm; `_apply` set the combo back on any error; `taskui.Panel.finish` cancels silently | Row 3; the picked operation stays with the reason; `extrude_finish.SaysWhy` |
| 2a | "-6 went AWAY from the front view (book: towards you)" | Yes | Fusion's Front plane has the normal +Y (sketch X = world X, sketch Y = world -Z): plus goes away from the front viewer (Book; a third-party Fusion reference) | FreeCAD's XZ plane looks to -Y | A sketch on the Front plane used by Extrude for the first time counts Fusion's way (`Fission180FrontNormal`); older sketches keep theirs |
| 2b | "Cylinder Height -8 went +8 into the first body" | Not as stated: -8 on the Top plane goes down. What does happen: the typed digits go into the box of the arrow the mouse rests on, so -8 became a diameter | A negative height goes the other way | `ValueBoxes.current()` follows the hovered handle | After placing, the next typed number is the height until the mouse moves |
| 2c | "-8 grew INTO the body" (summary) | It is 2b's entry | - | - | - |
| 3 | "The cut does not go through any body" on a flipped sketch; To Object likewise | Not reproduced: a sketch on a revolved part's top face has its placement turned 180 degrees in its own plane (Yaw 180), the normal still points out, and Cut / To Object work. The message was true in my rebuild of the case (a distance too short to reach the base) | - | - | The dialog now says why OK is refused, keeps the picked operation, and row 3 makes the book's step a Cut by itself |
| 4 | Two profiles tapered separately: "-11 does not fit: limited to -6.8" | Yes | Profiles that touch are one region ("like one giant square", Forum; Book) | FreeCAD's Pad tapers each face | `extrude_prism.merged_faces`, own extrude feature when touching profiles are tapered |
| 5a | A click where a face is in front of a profile picks the face | Yes | The profile (the report; Fusion draws sketches through bodies) | `ProfilePicker` gave the click to the part when it hid the region | `through=True`: the region wins and is drawn through the part |
| 5b | Profiles over a void go to the face behind | No: three circles over a bore are each picked | - | - | Checked (K5) |
| 5c | Profiles of a sketch in a hidden body cannot be clicked | Yes (Extrude and Revolve) | They can (Book) | The hidden body's solid still counted as "in front" | `profile_pick.shown_part` |
| 5d | The first clicks after the dialog opens are lost | No | - | - | Checked (K2) |
| 5e | Revolve: each extra profile needs a click on Profiles | Yes for narrow areas along the axis: the click went to the axis line | Fusion moves on to Axis after the first profile; extra profiles need the Profile box (Forum) | A drawn axis within 4 pixels always won | An area not picked yet wins unless the click is right on a line |
| 5f | E did not pre-pick the only profile (new component) | Plausible: only the active body's newest unused sketch was looked at | The one visible profile is picked (Forum, Autodesk community manager; Autodesk help) | as left | `profile_pick.only_visible_profiles` as a second rule, Extrude and Revolve |
| 5g | Start: Offset lets no profile be picked | No | - | - | Checked (K6) |
| 5h | A thin slot needs its exact inner point; small faces cannot be hit in a fitted view | Yes | - (Fusion's pick radius: Guess) | Exact point-in-face test; an edge click was ignored | 4 pixel reach for areas; an edge with one flat face toward the viewer is that face |
| 5i | The arrow and value box swallow the click meant for the other profile | Yes for the box | - | The box only avoided handles | The boxes keep off the nearest unpicked areas |
| 5j | Construction plane squares and origin glyphs swallow clicks | Yes | A box that wants faces does not take a plane (Guess from Fusion's selection filters) | The plane was simply ignored | `profile_pick.behind_glyphs` in Extrude and Loft; Split Face is modify's |
| 6a | Starting Extrude hides a sketch just shown | No (shown from the browser's menu or its eye: it stays shown; E then takes the selected sketch's areas, as Fusion takes a selected sketch) | - | - | Checked (K1) |
| 6b | The sketch is hidden when Revolve starts | No | - | - | Checked (K4) |
| 7a | 27 regions, many zero-area slivers (carabiner) | Not rebuilt; the filter is tested on a made-up crack | - | FreeCAD's areas include cracks between coincident curves | `extrude.sliver_areas` |
| 7b | "Sub shape not found: Sketch.InternalFace56" after a parameter change | Yes, and worse: FreeCAD also renames a link to the wrong area without a word | The design follows its parameters | FreeCAD follows an area by an internal name made from its corners; it is lost when the curves around the area change | `sketch_area_id`: areas noted by the curves that bound them and found again after each sketch compute |
| 8 | Loft to the origin / a sketch point under the origin's glyphs | Yes | Sketch points and construction points are loft sections (Autodesk); the origin (Book) | Loft only took vertices; a glyph in front was ignored | Point objects as sections; `_behind` |
| 9 | No on-canvas "31.8, Tab, 15.8, Enter, 9.6" | Yes: the digits went into the dialog's field, Tab left for the dialog | Sizes typed in boxes on the work surface, Tab between them (Autodesk; Forum) | No box on the canvas while placing | `PlacingBox` |
| 10 | The first body is "Body", Box makes "Body1" | Yes | Body1, Body2 ... | `commands.ensure_body` kept FreeCAD's label at the root | One line there |
| 11 | Join of several areas (drone) | The report's own cause (an area left out); a New Body of areas that touch is one body | - | - | No change |
| 12 | Speed: an extrude dialog with 36 areas; Hole from sketch | Extrude with 37 areas opens in 0.65 s and answers a click in under 0.2 s plus the hand's pace; not slow. Hole is modify's | - | - | Measured in `book_extrude_areas` |

## What I built

- `extrude_bodies_core.auto_operation` / `scope`, `extrude_bodies.start_state` /
  `in_the_way` (third list: real overlaps) / `auto_scope`; `extrude_ui`: the rule, the picked
  operation that stays, `refuse()`.
- `extrude_finish.py` (new): `SaysWhy` mixin and `speaking` decorator, used by Extrude,
  Revolve, Sweep, Loft, Box / Cylinder / Sphere / Torus / Coil.
- `sketch_area_id.py`, `sketch_area_id_core.py` (new): sketch areas' identity; installed
  with `sketch_area_fill.install()`.
- `profile_pick.py`: `through`, the see-through layer, the pixel reach, `shown_part`,
  `only_visible_profiles`, `behind_glyphs`, `under`, `is_glyph`, `is_point_object`.
- `extrude.py`: `sliver_areas`, `tapers_as_one`, the Front plane (`on_front_plane`,
  `fusion_side`, `adopt_fusion_side`); `extrude_prism.merged_faces`.
- `revolve_ui.py`: an unpicked area against a line; `loft.py` / `loft_ui.py`: point objects
  as sections, `_behind`; `primitives_ui.py`: `PlacingBox`, the height next.
- `commands.ensure_body` (shared, one line): the first body's name.

## FreeCAD facts and traps

- **A link to a sketch area is followed by an internal name, not by its number.** When the
  name is lost FreeCAD writes the sub-element as "?InternalFace3" and the step fails with
  "Sub shape not found"; `PropertyLinks.cpp(516) ... missing element reference` appears in the
  log (a warning line, no error). Setting the link again with the plain name heals it.
- FreeCAD also renames such a link by itself during the sketch's compute, and can pick the
  wrong area. So the notes are never taken from a link while a sketch is being computed, only
  after a step has computed without a problem.
- `GeometryFacade.Id` survives deleting other curves and reopening the file; `Geometry.Tag`
  does not survive reopening.
- FreeCAD 1.1 has no `slotFinishRestoreDocument` for Python document observers (the slot is
  never called: `thread_ui.py` and `undo_fast.py` define one that does nothing). Use
  `slotBeforeChangeObject` / `slotBeforeRecomputeDocument` with `doc.Restoring`.
- Plain scaling of a sketch (all dimensions following one parameter) keeps FreeCAD's area
  names; a curve crossing another, or passing another, does not.
- A sketch on a face of a revolved solid can get its placement turned 180 degrees in its own
  plane; its normal still points out of the solid.
- `QTest.keyClick(widget)` sends the key to that widget whatever has the keyboard; a real key
  goes to the focus widget. The primitives scenario sends every key to `focusWidget()`.
- A dialog class with a method called `_finishing` (primitives) breaks when a mixin stores a
  flag under the same name: the mixin's flag is `_ending_for_another`.
- The value box of whichever handle the mouse rests on takes the digits typed over the view
  (`BoxCarrier.follow_box`): a scenario that hovers "somewhere on the part" before typing can
  feed another box than it means to.

## Shared files touched

- `commands.py` (`ensure_body`, 4 lines): the root's first body is numbered like the others.
- Merged `sf/book-components` (commit 21186dc3) to resolve `extrude_bodies.py` once: that
  builder had added `_joinable` / `components.may_change` to `bodies_in_way`, `in_the_way` and
  `starts_in_material` for bug 10. Kept: their `_joinable` on the Join lists and their
  `may_change` as the one rule for which bodies decide; my `start_state` takes the scope as
  arguments instead of filtering inside.

## Gaps

- Box / Cylinder placed on the Front plane still count their height FreeCAD's way; CONSTRUCT >
  Offset Plane from the Front plane likewise (components' `construct*.py`).
- The automatic Cut looks only at the active component's own bodies (the components builder's
  rule). With the design's top row active and every body inside components, a sketch pushed
  into a part comes up as New Body; the person picks Cut (Fusion most likely shows Cut).
- The report's false "The cut does not go through any body" (Hot End) did not reproduce; if it
  shows again the dialog now keeps the picked operation and says the reason on OK.
- The carabiner's 27 regions were not rebuilt; slivers are filtered by their shape (thinner
  than one millionth of their outline squared, or under 1e-7 mm2).
- Sphere has no size box on the canvas (it has one click).
- Sweep and Loft got the see-through profile pick and the point sections; their automatic
  operation still compares "mostly inside" against their own body only.

## Changelog lines

- Extrude no longer changes the operation you picked, and its automatic choice now follows one rule: Cut when it starts in or reaches into a body, Join when it builds on a face, New Body otherwise.
- Choosing Symmetric no longer turns a Cut into a Join.
- The first extrude in a new, empty component is a New Body, whatever body of another component it overlaps or touches.
- When OK cannot finish a feature, the reason now also shows next to the mouse; when another command has to cancel a feature that could not finish, it says that the change was not kept.
- A design now follows its parameters when a sketch's areas change: extrudes, revolves, sweeps and lofts keep the areas they were made from ("Sub shape not found: Sketch.InternalFace..." no longer breaks them).
- Zero-area slivers are no longer offered as profiles.
- A sketch profile behind a body face can be clicked through the body (it shows as a faint blue), and profiles of a sketch whose body is hidden can be clicked.
- A click a few pixels beside a thin slot, or on the rim of a small flat face, now picks it.
- A click on a construction plane's square goes to the face behind it in Extrude and Loft.
- Value boxes no longer sit on top of a profile that is still to be clicked.
- Extrude and Revolve pick the single profile in view by themselves, also when its sketch is in another component.
- Revolve takes a narrow profile along the axis instead of the axis itself.
- Profiles that touch are tapered as one outline, like Fusion (a circle split by a projected edge becomes one cone).
- On the Front plane a positive Extrude distance now goes away from the front, like Fusion; sketches that were already extruded keep their old direction.
- Loft can end in the origin point or a construction point.
- Box, Cylinder, Torus and Coil show size boxes on the canvas while you place them: type a size, Tab to the next, Enter to place, then type the height.
- The first body of a design is now called Body1.

## Known issues

- A Box or Cylinder placed on the Front plane still grows towards the front for a positive height; type a negative height to go the other way.
- With the design's top row active, pushing a sketch into a part that lives in a component does not switch to Cut by itself: choose Cut in the Operation list.
- A sketch profile hidden behind a body face is picked before that face; to extrude the face itself, hide the sketch first.
