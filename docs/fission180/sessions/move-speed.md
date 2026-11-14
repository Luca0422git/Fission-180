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

(filled in below)

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

(filled in below)

## What changed for Luca

(filled in below)
