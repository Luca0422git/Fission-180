# Session log: book-components (wave 7, 2026-11-11), branch `sf/book-components`

The book parity report's "work across components": bugs 5 - 10 and 15, friction patterns 2
and 9. Brief: `docs/fission180/dev/briefs/book-components.md`. Spec and sources:
`docs/fission180/parity/components.md`, "Part 3".

## What was reproduced (real FreeCAD 1.1.4, real input, before any change)

| Report item | Reproduced? | What I saw |
|---|---|---|
| Bug 5, a sketch on another component's face | Yes (`book_components_active` on 3.3.10) | PTFE Tube active, Create Sketch, click the Nozzle's face: the Nozzle became the active component, the sketch and its extrude went into the Nozzle (the extrude JOINED the Nozzle: 4000 -> 4141 mm3) |
| Bug 6, Extrude a face with New Body | Yes | the new body appeared in the Nozzle ("Body2"), not in the active Gaskets |
| Bug 7, Offset Plane | Yes | Plane1 in the gasket face's component |
| Bug 8, Axis Through Cylinder | Yes | Axis1 in Pins, not in the active Axle |
| Bug 9, New Component ticks From Bodies | Yes (`book_components_new` with the old dialog) | a step selected in the timeline, and also a selected face, ticked From Bodies ("1 bodies: Body1"); OK moved the body |
| Bug 10, first extrude of a new component | Yes, in the Join form | the first extrude in an empty component came up as Join and joined the other component's block; the cause is the same as the report's Cut (bodies of every component decided the operation) |
| Bug 15, nested rows in As-built Joint / Rigid Group | Yes (`book_components_nested`), but not as written | the row was not ignored: the whole top-level subassembly was taken, and the second nested row of the same subassembly dropped it again ("stays Select") |
| Project (P) from another component | Yes | FreeCAD's tool shows a no-entry pointer; `addExternal` raises "is not allowed as external geometry of this sketch" |
| A click on a part of a subassembly picks the subassembly | Yes | `component_to_pick` returned the component below the active one by design |
| Move turns about the bounding-box centre | Yes (the code: `MovePanel._new_pivot` took the middle of the solids) | |
| Paste of Bolt:5 starts on the original | Yes (the code: `make_instance` placed the copy on the source's definition) | |
| Mirror of components "not built yet", "needs a solid to repeat" | Yes (the code said so) | |
| Rectangular Pattern of components "made nothing, no message" | Partly | with the bolt picked (not the subassembly) the pattern works; the report's click took the whole Stator Subassembly (the pick rule above). I could not make it build nothing: with a direction missing the dialog says so in blue |
| Move to Component leaves an empty, invalid Body | Not as written | the empty body was the one made in the active component for the sketch that then went to the other component (bug 5). FreeCAD does not mark an empty body invalid; it has no browser row. It did take the next sketch (`preferred_body` took the oldest body) |
| The first component is not grounded | Yes | by design until now (the joints work's "no automatic ground" was about the joint dialogs grounding by themselves, another thing) |

## Where the report was wrong or incomplete about Fusion

- "Fusion starts a new component's first extrude as New Body": right for the operation
  Fusion proposes, but a Cut chosen by hand does cut bodies of other components in Fusion
  (Objects To Cut; Autodesk knowledge article, forum). Fission 180 now does both.
- "Ground": Fusion's command is **Ground to Parent** / **Unground From Parent** since 2024,
  and it is a preference ("First component Ground to Parent"); the first component picked
  for a joint is ungrounded by itself.
- Bug 15's "clicking does nothing": see above (the subassembly was taken, then dropped).
- "A new component goes inside whatever component is active" (friction 9, Gear Train): that
  is Fusion's behaviour too (the Parent box starts on the active component). Kept.

## Root causes and what was built

1. **One rule** (`components.py`): `new_home(doc)` is the active component;
   `host_body(picked, work)` gives the picked object's body only when it is in the active
   component, else the active component's own body; `body_for_new` puts a New Body there and
   lines it up with the profile's body when the two components stand differently.
   - `sketch_ui.create_sketch` used `activate_body(owner of the face)`; the active component
     is DERIVED from the active body (`active_component`), so activating the clicked body
     switched the component. Now the sketch stays in the active component and hangs on a
     reference to the face.
   - `construct.target_body` said "Fusion puts construction geometry in the component of what
     it is built on" (wrong); it now uses `host_body`.
   - `extrude_bodies.in_the_way` / `bodies_in_way` / `starts_in_material` took every shown
     body: `_joinable` keeps the active component's for Join and for the proposed operation
     (`components.may_change`; an edited step works in its own component).
2. **References across components** (`components.reference_binder`): a hidden
   `ReferenceCopy` (a `Part::Part2DObjectPython`, role `ComponentRef`, so no timeline step, no
   browser row, deleted with what uses it) that depends on the step only and stands where
   the other body stood when it was made. The first version was a `SubShapeBinder` linked
   through the other component: it followed every move (a joint would have reshaped what was
   modelled on a part) and made a Cut of that part from such a sketch a dependency cycle
   (found by the scenario); see "FreeCAD facts" in the parity doc.
2b. **Primitives**: `primitives_ui._ensure_body` made the body at the design's root when the
   active component was empty (and the root became active); `primitives.new_body` put a New
   Body beside the clicked face's body; the active component's own origin plane (browser
   row) was refused. All three go through `components` now.
3. **Project across components**: `sketch_project_across.AcrossWatch` (a Qt event filter on
   the 3D view while FreeCAD's tool runs) + `sketch_external.project_across`.
4. **Bug 9**: `NewComponentPanel._selection_changed` took `body_of(anything selected)`.
5. **Bug 15**: `joints_ui._selection_entries` reads the selection unresolved; FreeCAD gives
   the top container with a path. `components.whole_pick` turns that into the component.
6. **Parts of a subassembly**: `components_core.component_to_pick` gives the nearest component.
7. **Mirror of components**: `component_pattern` kind `mirror` (one copy, `MirrorBase` /
   `MirrorNormal` on the step, `instances.InstanceCopy` mirrors the solids); the dialogs
   open without a solid in the active component.
8. **Ground**: `components_ui.ground_first` in New Component and Create Components from
   Bodies; preference `first_component_grounded`; the browser's menu texts.
9. **Move / paste**: `ComponentMovePanel._new_pivot`; `clipboard_ui.paste` passes the copied
   occurrence's placement.
10. **Move to Component / drag**: `components.drop_unused_bodies`, `preferred_body` prefers a
    body with something in it; the browser drops on the row under the pointer at release.
11. **Menus**: Move/Copy, Create Drawing, Properties (when the command exists), Isolate on
    another row while isolated, the `assembly` icon of the design's row.

## FreeCAD facts and traps (1.1.4)

- See "FreeCAD facts" in `parity/components.md` Part 3 (external geometry scope, attachment
  across parts, the SubShapeBinder link form, unresolved selection, pending transactions).
- FreeCAD's Project tool answers a click on something it refuses with a `ForbiddenCursor` on
  the 3D view that stays until the mouse moves. `sketch_tools_ui.WatchedTool` took any
  pointer change for "the tool ended" and closed its Done panel: it now ignores that pointer,
  and the projector puts the tool's pointer back after a projection.
- `harness.press("Escape")` types the letters E, s, c, a, p, e (E starts Extrude): use
  `h.press(QtCore.Qt.Key_Escape)`.
- A Move triad at a component's origin has its Z arrow through the corner above the origin:
  a Set Pivot click there is the arrow's (components2_move clicks another corner now).

## Shared files touched (smallest change, each marked "wave 7")

- `extrude_bodies.py` (extrude): `_joinable` on the touched bodies and in
  `starts_in_material`.
- `primitives_ui.py`, `primitives.py` (extrude): `_ensure_body` and `_set_plane` use the
  active component; `new_body` calls `components.body_for_new`.
- `joints_ui.py` (joints): `_selection_entries` calls `components.whole_pick`.
- `sketch_tools_ui.py` (sketch-b): Project and Include call `sketch_project_across.watch`;
  `WatchedTool._watch` ignores FreeCAD's no-entry pointer.
- `pattern_ui.py` (modify): Mirror's Components no longer disabled; the dialogs open on
  Components when the active component has no solid; `_components_only`.
- `browser_core.py`, `browser_ui.py` (shell): the component menu's Move/Copy, Create
  Drawing, Properties; Ground to Parent / Unground From Parent; Isolate on another row; the
  assembly icon; the drop row at release.
- `prefs_core.py` (shell): the preference `first_component_grounded`.
- `Fission180Tests/gui/harness.py`: `prepare()` switches First component Ground to Parent
  off (the scenarios written before it move and joint their first component as a free
  one); `book_components_new` switches it on and tests it.
- Scenarios updated for the new behaviour: `components2_move` (the manipulator starts on
  the origin; another corner for Set Pivot; menu names), `joints_asbuilt_group`,
  `joints2_drag` (menu names); `test_components_core.py` (the pick rule).

## Gaps (with what to do instead)

- Snapping / inference to another component's geometry while drawing, and a dimension that
  projects a model edge by itself: not built (the drawing and dimension tools are the sketch
  builders'); `sketch_external.project_across` is the function to call. Today: P, click the
  edge, then snap or dimension to the purple curve.
- Internal / External in New Component, Create Selection Set: not built.
- The first component picked for a Joint is not ungrounded by itself (joints' dialog).
- A mirrored component is a mirrored copy, not a component with features of its own; a
  patterned or mirrored subassembly comes in flat (bodies, not nested rows).
- A construction built on another component follows that component's later MOVES at its
  next recompute (a sketch's reference keeps its place).
- Open: with a sub-component active, a Cut chosen by hand in Extrude said "The cut does not go
  through any body" for a body of another component (both signs; the same profile as New
  Body lies inside it). Fusion cuts it. `extrude_bodies.in_the_way`'s "through" list is not
  filtered by this work; I did not find why it is empty there. For the extrude builder.

## Changelog lines

- New sketches, bodies, planes, axes and points now go into the active component, whatever
  you click to make them: a sketch on another component's face no longer switches the
  active component.
- Extrude's New Body puts the body in the active component, and an extrude no longer joins
  or cuts a body of another component by itself (choose Cut to cut one on purpose).
- Project (P) and Include 3D Geometry now take faces, edges and corners of other components;
  the projected curves follow that part when it changes.
- A Box (and the other primitives) made with an empty component active now goes into that
  component, and a primitive put on another component's face as a New Body goes into the
  active component.
- New Component no longer ticks From Bodies because a step or a face is selected, and says
  which bodies will move when it is ticked.
- The first component of a design is grounded automatically, as in Fusion; the menu now
  reads Ground to Parent / Unground From Parent (Preferences > General > Design to switch it
  off).
- In As-built Joint and Rigid Group, a component inside a subassembly can be picked from the
  browser.
- A click on a part inside a subassembly picks that part for Move/Copy and patterns of
  components (pick the subassembly's browser row to take all of it).
- Mirror now works with Pattern Type Components, and Mirror and the patterns open when the
  active component has no solid of its own.
- Move/Copy turns a component about its own origin, and a pasted component starts where the
  copied one stands.
- The component menu has Move/Copy and Create Drawing; Isolate works on another component
  while one is isolated; the design's row shows an assembly icon when it holds components.

## Known issues

- While drawing, the pointer does not snap to another component's edges by itself: press P
  and click the edge first, then snap to the purple curve.
- With the design's row active, a sketch on a component's face is made in the design's root
  (as in Fusion): activate the component first if the new feature should join its body.
- New Component offers no External component; use Insert into Current Design for a saved
  design.
- A mirrored component cannot be edited on its own (edit the original; the mirror follows).
- With a component active, Extrude's Cut does not cut a body of another component yet:
  activate that body's component (or the design's row) and cut there.
- A projection from another component keeps the place the parts had when it was made: after
  moving a component with Move or a joint it does not move (as in Fusion). Project it again
  if you want the new place.
