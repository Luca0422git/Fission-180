# Session log: move-speed (2026-11-13/14), Move drags live on complex parts

Brief: `docs/fission180/dev/briefs/move-speed.md`. Branch `sf/move-speed`. Two runs (the first
was cut off by a container restart after commit bce262e4; the second finished it).

Luca (2026-11-13): "the move tool. its too slow. especially for complex parts. it needs to be
optimized CONSIDERABLY. That relic file that i gave you is a great example of it. while i was
working on it, i could pretty much say goodbye to live movement. only basic shapes move
quickly, and even those are a bit choppy."

## Fusion's behaviour (what is copied)

| Behaviour | Source |
|---|---|
| While the manipulator is dragged the body follows the mouse at the screen's frame rate whatever its size: only the drawn picture moves | Brief (Luca), matches Fusion's Move/Copy |
| The real result is computed when the mouse is let go (or a value typed) | Brief |
| The timeline step, the dialog's values and Undo behave as before; the step appears in the timeline when the command is OK'd | Brief; Guess for when the step appears |
| Nothing is lit (preselected) while a manipulator is dragged | Guess (seen in Fusion) |

## What was slow, and why (profiled)

Measured with real mouse drags under Xvfb (software OpenGL), scenario `move_speed`, and three
scratch experiments that timed every object a recompute rebuilt (a document observer's
`slotRecomputedObject` times) and profiled opening the dialog and the release.

1. **Every pause of the hand rebuilt the Move step, twice drawn.** The dialog rebuilt its
   preview during the drag (only when the hand paused on a slow part: `taskui` SLOW_DRAG), so
   on anything but a box the body did not move at all while dragged (body_frames 0) and
   caught up seconds after the hand stopped. One rebuild copied the solid four times, then
   FreeCAD drew the new solid twice: in the Move step's view and in the **body's own view**.
2. **FreeCAD draws every body twice.** `PartDesignGui::ViewProviderBody::updateData` calls
   `ViewProviderPartExt::updateData`, which tessellates the body's own Shape whenever it changes
   and the body is visible, also in "Through" mode where the body only shows its steps and its
   own triangles are never drawn. `PartDesign::Body::execute` makes that Shape with
   `transformShape(..., copy=true)`: a deep copy with no triangulation, so every rebuild of a
   body meshes its whole solid again from nothing. Measured per body rebuild: 7.5 s for the
   3,000-face solid, 1.3-1.4 s for the 8,500-triangle solid, 1.0-1.1 s for the Relic-like part.
   This is now most of what is left of a release (below).
3. **FreeCAD 1.1 meshes again any shape it has not drawn before.** `setupCoinGeometry` calls
   `BRepTools::Clean(shape, true)` and then `BRepMesh_IncrementalMesh`: an existing
   triangulation on the same faces is thrown away. Only a shape that is a *partner* of the one
   drawn last (same OpenCASCADE TShape, another location) is not redrawn at all
   (`updateVisual`: `lastRenderedShape.IsPartner`): the view keeps its triangles and only its
   transform changes. A new step showing the same solid as the step before it is meshed again
   (the Move step's first drawing: 7.4 s on the 3,000-face solid, 0.55-0.66 s on the
   Relic-like part).
4. **Opening Move made a step that moved nothing**, at once: its first drawing (3.) and a
   rebuild of the body (2.) before the manipulator could be used: 2.1-2.8 s on the Relic-like
   part, 18 s on the 3,000-face solid, 20 s with three bodies. Plus 0.8 s on the Relic-like
   part copying each solid twice per pick only to measure its box (`_unmoved`, for the pivot
   and the manipulator's size).
5. **Preselection** ray-picked through the whole part on every mouse move (4 ms a move on the
   600-face part), and lit the faces the dragged handle passed over.
6. Small ones: the faces of the solid listed (not counted) at every rebuild (0.15 s on 8,500
   faces, three times per rebuild); the triad worked its pixel scale out 24 times a poll;
   Create Copy copied the solid at every rebuild and its new body's first step drew the copy
   again (1.3 s of a 2.6 s rebuild on the Relic-like part).

What a release costs now, per object (`.scratch` experiment `exp_multi`, the second drag of a
dialog, seconds):

| case | Move step(s) | body rebuild (FreeCAD's own drawing of the body, 2.) | total |
|---|---:|---:|---:|
| 3,000-face solid | 0.11 | 7.54 | 7.72 |
| 8,500-triangle solid | 0.30 | 1.30 | 1.75 |
| Relic-like (600 faces, 33 steps) | 0.15 | 1.10 | 1.28 |
| the three bodies at once | 0.42 | 0.00 + 7.59 + 1.39 | 9.63 |
| Relic-like, Create Copy (before the Copy change) | 0.58 copy + 0.81 new body's step | 1.17 | 2.65 |

## What changed

First run (commit bce262e4):

- `move_live.py` (new): while a handle is dragged, each moved body's shown step (its Tip, or
  the first step of a copy's new body) is drawn where the handle puts it by its view's
  transform (`ViewObject.setTransformation`): one scene node changes, nothing is rebuilt or
  tessellated, the document is not touched. A document observer drops that transform the
  moment the step's real Shape or Placement arrives, so no frame shows a body moved twice.
- `move.py`: the Move step keeps its base's solid as it is (the same TShape) at the moved
  placement: no copies, and the step's view only moves what it has drawn (3.).
- `handles3d.py`: preselection off while any handle is dragged, back when the last drag ends.
- `bodies_panel.py`, `move_ui.py`, `revolve_ui.py`, `component_move_ui.py`: a click is judged by
  when FreeCAD made it (after a long rebuild the release of a drag reached the dialog late
  and was taken as a pick of the body); components move live the same way.
- `move_ui.py`: the triad's pixel scale once per poll.
- the scenario `move_speed` with its probe and parts.

Second run:

- `move_ui.py`: **a new Move makes its steps at the first movement** (a drag let go, a value
  typed, a point picked) or at OK, not when the bodies are picked (4.). Until then a drag
  draws each body's last step moved. OK with nothing moved still makes the steps (one Move
  step per body, one undo step, as before); Create Copy still makes its copy at once (it shows
  the new body).
- `move_live.py`: when the steps are made (at the release, a typed value, a pick or OK) each
  body's previous step stays drawn where it was let go until its new Move step has its
  shape (`hand_over`): no frame of the release is without the body.
- `move_ui.py`: the pivot and the manipulator's size come from the bodies' own boxes
  (`optimalBoundingBox`, exact like a copy's), shifted to design coordinates; a body in a
  turned component is still copied and turned.
- `move.py`, `surfmod.py`: faces counted (`countElement`), not listed.
- `move.py`: **Create Copy keeps the source's solid at a placement**; the copy body's first
  step (`PartDesign::FeatureBase`, which drops its base's placement and puts the shape at its
  own) gets the same placement. Its rebuild copies nothing and its view keeps its drawing.
- the probe: `caught_up` waits for every moved body (it looked only at the first: "multi"
  seemed to catch up in 3.7 s while its last body took about 22 s, which read as if the new
  release of 11 s were slower), the time to open the dialog, and the frames drawn between the
  release and the result (where the body was drawn in them, and whether every moved body was
  drawn at all). A new check: the body stays drawn where it was let go until the result.

## Before / after

Scenario `move_speed`, the same scenario file and probe on both: "before" is the code of the
brief's commit 6fe37f27 (a copy in the worktree's ignored `.scratch/before`, run with
`FISSION180_MODULE`), "after" is this branch. This sandbox: 4 shared CPUs (load 1.0-2.0),
Xvfb with software OpenGL, so a frame's drawing alone takes 15-60 ms (a graphics card: 1-5 ms).
Milliseconds. Cases: `box` 40 x 30 x 10; `relic` a part like Luca's Relic (599 faces, 33
steps: 4 pads, 27 pockets, 2 grooves); `dense` a 3,006-face solid; `faceted` an
8,514-triangle solid (a mesh body made solid); `multi` box + dense + faceted at once;
`relic_again` a second drag in the same dialog; `_turn` the Z turn handle, `_copy` Create
Copy, `_rotate` Rotate about the Z axis, `_p2p` Point to Point (two clicks),
`_component` Move Object Components, `_in_component` the body inside a turned component.

- **open**: from M to the dialog ready with its manipulator.
- **frame step**: time between frames that showed the body somewhere new while the hand
  moved ("-": the body never moved while the hand did).
- **lag**: how far the drawn body was behind the hand.
- **caught up**: from the hand stopping until every moved body was drawn where the hand is.
- **release**: from letting go to the exact result. Before, the scenario's hand held the
  button until the app had caught up, so the rebuild happened before the release.
- **hand stop to exact result**: the total wait after the hand stops. This column compares
  across versions.

| case | open | frame step median | step p90 | frames showing the body move | lag median | caught up | release | hand stop to exact result |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| box | 171 → 88 | 93 → 19 | 110 → 23 | 10 of 29 → 50 of 51 | 88 → 10 | 46 → 18 | 553 → 422 | 960 → 444 |
| box_edit (from the timeline) | | 94 → 18 | 108 → 20 | 11 of 29 → 55 of 56 | 78 → 15 | 87 → 17 | 427 → 385 | 885 → 406 |
| relic | 3,847 → 136 | - → 32 | - → 38 | 0 of 20 → 29 of 30 | 534 → 28 | 3,650 → 28 | 515 → 2,004 | 4,760 → 2,040 |
| relic_again (2nd drag) | | → 31 | → 40 | → 31 of 32 | → 23 | → 29 | → 1,568 | → 1,607 |
| relic_turn | 4,188 → 180 | - → 29 | - → 64 | 0 of 29 → 20 of 27 | | | 510 → 1,977 | 4,760 → 2,053 |
| relic_copy | 4,228 → 162 | - → 38 | - → 41 | 0 of 19 → 26 of 27 | 577 → 33 | 4,126 → 37 | 502 → 1,669 | 5,232 → 1,715 |
| relic_rotate | 4,205 → 151 | - → 26 | - → 28 | 0 of 27 → 34 of 36 | | | 508 → 1,958 | 5,161 → 1,991 |
| relic_p2p (2nd click to result) | | | | | | | | 4,320 → 2,205 |
| relic_component | 1,165 → 898 | - → 28 | - → 31 | 0 of 23 → 34 of 35 | 561 → 20 | 264 → 26 | 435 → 585 | 775 → 617 |
| relic_in_component | 5,706 → 1,409 | - → 29 | - → 35 | 0 of 21 → 33 of 34 | 547 → 19 | 4,622 → 29 | 642 → 1,964 | 5,937 → 2,003 |
| dense | 15,381 → 108 | - → 64 | - → 77 | 0 of 9 → 15 of 16 | 538 → 51 | 15,533 → 49 | 523 → 16,811 | 16,739 → 16,888 |
| faceted | 4,874 → 148 | - → 27 | - → 33 | 0 of 21 → 36 of 37 | 617 → 17 | 4,512 → 25 | 542 → 3,426 | 5,808 → 3,458 |
| multi | 23,401 → 183 | - → 57 | - → 60 | 0 of 12 → 18 of 19 | 621 → 31 | 21,614 → 55 | 672 → 20,708 | 23,091 → 20,792 |

Frames: the work for the mouse between two frames (Fission 180's and FreeCAD's, the drawing
left out) went from 10-44 ms to 4-8 ms (median); the rest of each frame is software OpenGL
drawing (15 ms for the box, 25 ms for the Relic-like part, 55 ms for the 3,000-face solid). In
every frame drawn between the release and the result the body is where it was let go
(`release_off` under 0.000003 mm, `release_hidden` 0).

**"multi" was not slower before.** The 3,682 ms "caught up" of the first measurements looked
only at the first body of the three (the box). Measured on every body, the before code caught
up after 21,614 ms and showed the exact result 23,091 ms after the hand stopped. The 10,990 ms
release of the first after measurement (commit bce262e4) did not include the 20,200 ms the
dialog had spent opening. Now the dialog opens in 183 ms and the first release takes
20,792 ms: two meshings of each body, explained below.

A first release is now open's former work plus the release: the new Move step's first
drawing and the body's own drawing, both FreeCAD's (causes 2. and 3.). A second release in
the same dialog redraws only the body (`relic_again` 1.6 s). The dialog takes its rebuild once
for a whole Move. Before, it rebuilt at open, again whenever the hand paused, and again at
the end. For the Relic-like part, open plus drag plus result went from 3.8 + 4.8 = 8.6 s
to 0.1 + 2.0 = 2.1 s.

## FreeCAD facts and traps (for the next one)

- A Part::Feature recomputing puts its Shape at its Placement (`Feature::onChanged`: during a
  recompute `Shape._Shape.setTransform(Placement)`, replacing the location): a step that keeps
  a solid at another place sets Shape first, then Placement.
- `PartDesign::FeatureBase::execute` takes `getTopoShape(BaseFeature, Transform)` and then
  replaces its location with its own Placement: a body's base feature with a placement shows
  its shape where its own Placement says (checked: a box at x = 100 came in at 0).
- A view provider's update cannot be stopped from Python (`ViewProvider::setUpdatesEnabled` is
  not exposed); a hidden view provider marks itself touched and meshes the shape when shown
  again (`VisualTouched`), so hiding a body around its rebuild saves nothing. Setting a body's
  Deviation is copied to all its steps (`unifyVisualProperty`) and redraws them, and a coarse
  triangulation left on a shape makes `Shape.BoundBox` bigger (BRepBndLib uses it).
- `doc.recompute()` processes events between the objects it rebuilds (FreeCAD's progress
  sequencer): the 3D view draws frames in the middle of a long recompute (1-4 per release
  here, `release_inside`). When a new step becomes a body's Tip, FreeCAD hides the previous
  step at once, before the new one has a shape: frames drawn meanwhile showed no body (with
  three bodies, 2 of 9 frames of the release; the new check `release_hidden` caught it). The
  previous step now stays drawn where it was let go until the new one has its shape
  (`move_live.hand_over`). PartDesign shows one step of a body at a time
  (`PartDesignGui::ViewProvider::onChanged`: showing a step hides the body's other steps), so
  showing the previous step hid the new one: at the hand-over the new step is shown first
  (it draws its shape then), which hides the previous one.

## Still open

1. **FreeCAD draws every body's own shape on every rebuild (cause 2.)**: what is left of a
   release. One body rebuild costs 7.5 s on the 3,000-face solid, 1.3 s on the
   8,500-triangle solid and 1.0-1.1 s on the Relic-like part, and every PartDesign change in
   Fission 180 (an extrude, a fillet, an edit) pays it, not only Move. Python cannot stop it
   (facts above). Proposed core patch, **not applied**: it cannot be compiled or tested in
   this sandbox, it needs the 4-hour full build, and Luca's releases are patches.
   - In `ViewProviderBody::updateData`, when `prop` is the body's Shape and
     `DisplayModeBody` is "Through", set `VisualTouched = true` and skip
     `ViewProviderPartExt::updateData` (keep `ViewProviderGeometryObject::updateData`).
   - In `onChanged(DisplayModeBody)`, call `updateVisual()` when the body is switched to
     "Tip" and is touched.
   - Around `ViewProviderPartExt::onChanged(Visibility)` in "Through" mode, do not let a
     touched body mesh its unused shape when it is shown again.
   - Expected: a release on the Relic-like part 0.2 s (2nd drag) / 0.8 s (1st), on the
     3,000-face solid 0.2 s / 7.5 s, and every PartDesign change drawn once instead of twice.
2. **A new step meshes a solid it shares with the step before it (cause 3.)**: the first
   release pays the new Move step's first drawing (0.55-0.66 s on the Relic-like part, 7.4 s
   on the 3,000-face solid). This is FreeCAD 1.1's `BRepTools::Clean` before meshing. A core
   option: skip the clean when the faces' triangulation already meets the deflection.
3. **Cancel after a drag** still rebuilds the body's own drawing: 2.2 s on the Relic-like
   part, 2.3 s before. Cancel after Create Copy dropped from 2.4 s to 0.3 s.
4. **Other live drags** were not measured this time: Press Pull's and Extrude's arrows
   (they change the shape itself, so it cannot simply be moved; on slow parts they rebuild
   only when the hand rests: `taskui` SLOW_DRAG), sketch Move, joint drags. The preselection
   change (off while any handle is dragged) applies to all of them.
5. The frame times here are software OpenGL: on a graphics card a frame is the 4-8 ms of work
   measured plus a few ms of drawing. The scenario checks the work between frames against
   the brief's targets (16 ms box, 33 ms big parts). Measured 4-8 ms, which leaves CI's slower
   machine 2-4 times the room. It is an `h.speed_check`: counted normally, printed only under
   `--stress`.

## What changed for Luca

- **Move (M) opens at once**, even on a big part. Before, it took about 4 s on a part like
  your Relic and 15 s on a 3,000-face block, before you could grab an arrow.
- **While you drag** an arrow, a turn handle or the rotate handle, the part follows the mouse
  smoothly. Only the picture moves, as in Fusion. Before, a complex part did not move at all
  until you stopped, then it jumped there seconds later.
- **When you let go**, Fission 180 works out the real result once, about 2 s on a Relic-like
  part (1.6 s for a second drag in the same dialog). Meanwhile the part stays exactly where
  you dropped it. Before, the whole move took about 8.6 s on that part, from pressing M to
  the result.
- **Nothing else changes**: the typed values, snapping, Point to Point, Rotate, Create Copy,
  OK / Cancel / Esc, one Undo step, editing the Move from the timeline, several bodies at
  once, components.
- **What still takes time** after letting go is FreeCAD redrawing a hidden copy of the
  body's shape. It never shows that copy, but it draws it anyway. Removing that needs a
  change inside FreeCAD and a full build, so it is listed for a full release.
