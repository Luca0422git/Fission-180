# Wave 7 builder: animation (the ANIMATION workspace), branch `sf/book-animation`

Read `book-common.md` first. Report lines: Workspaces table 185-222; Animation chapter
2524-2531; Hilt 2577-2578. Luca decided on 2026-11-11 that the Animation workspace is in
scope (the outline's section 8 still says otherwise: the merger updates the outline).

The book's chapter 10 (Japanese Pull Saw, Machinist Hammer) and the final project use Fusion's
ANIMATION workspace for exploded views and assembly animations, then make an exploded drawing
from a storyboard. There is nothing to reproduce: research and build.

1. **Research first** (WebSearch: Autodesk Fusion help "Animation workspace", "storyboard",
   "Transform Components", "Auto Explode", "Manual Explode", "Publish Video", "Create
   Callout", "Show/Hide", "View" toggle, "Restore Home"; tutorials). Write
   `docs/fission180/parity/animation.md` with the behaviour spec and sources before coding:
   the toolbar groups (STORYBOARD, TRANSFORM, ANNOTATION, VIEW, PUBLISH), each command's
   dialog and options, the animation timeline (playhead, scratch zone at time 0 before the
   positive timeline, action bars per component that can be dragged, resized and deleted,
   the View track), what is saved with the design, what a storyboard is (several per design,
   tabs at the bottom, New Storyboard with Clean / Start from end of previous).
2. **The workspace**: an entry "Animation" in the workspace switcher
   (`ribbon_ui._workspace_menu`: add your lines in a block of your own, like Simulation's,
   and read how `simulation_ui.enter_workspace` / `leave_workspace` swap the ribbon, browser
   and timeline: `docs/fission180/dev/research/integration-map.md` describes how a workspace
   plugs in). Its own ribbon tab(s), its own bottom timeline in place of the design timeline
   (`timeline_ui.hold` shows how Home and drawings hide it), the browser showing the
   components with eyes. Entering it never changes the design: an animation moves a
   **display copy of the placements**, and leaving the workspace puts every component back
   exactly (assert it: placements before = after, design not marked changed by a play).
3. **Commands**: New Storyboard (and rename / delete / reorder the tabs), Transform
   Components (move / rotate with the triad and typed values, recorded at the playhead as an
   action of a duration), Restore Home, Auto Explode: One Level and All Levels (components
   move apart along sensible axes, away from the assembly's centre, one after another or all
   at once: research Fusion's options and the "explosion scale" slider), Manual Explode
   (pick components, an axis, a distance), Show / Hide (visibility actions on the timeline),
   Create Callout (a text label tied to a point, shown from a time on), View (record camera
   moves on / off), Play / pause / scrub / loop / reverse the storyboard, per-action
   duration and start edits by dragging and by a right-click > Edit, Trails if Fusion has them
   (it does: "Trail Line Visibility": research).
4. **Publish Video**: scope (current storyboard / all), size, frame rate; rendered from the
   3D view frame by frame to a real video file. Check what the AppImage and the Windows build
   can encode with (Qt multimedia? ffmpeg present? neither is certain): if no encoder is
   bundled, write an animated format that needs none and that players open (a sequence of
   PNGs plus an APNG or GIF written in pure Python, or AVI with MJPEG written by hand, which
   needs only JPEG frames from Qt), say which in the dialog, and use ffmpeg when found on the
   system. No silent failure, no cloud.
5. **For drawings**: `animation.storyboards(doc)` -> names and
   `animation.placements_at(doc, name, t)` -> {object name: App.Placement}, Qt-free, in
   `animation.py`: the drawings builder makes the Drawing workspace's Exploded View from
   them (contract in both parity docs). Storyboards are stored in the design (a hidden
   document object with JSON, like other Fission 180 data: look at how motion studies and
   simulation studies store theirs) and survive save / reopen, undo / redo, renamed and
   deleted components (an action whose component is gone is dropped with a note).
6. Qt-free core with unit tests (`animation_core.py`: actions, interpolation of placements
   (slerp for rotations), auto explode directions, timeline editing), `animation_ui.py` /
   `animation_timeline_ui.py` for the workspace, icons in `icons_animation.py`.
7. AI tools: look at `fission180/ai/ops/` and how other areas expose ops; add ops for
   storyboard creation, auto explode and placements so golden models can cover them.

Scenarios `book_animation_*.py` (at least: enter / leave the workspace with the design
untouched; auto explode one level of the 6-component stand-in assembly and play it
(placements at t = 0, mid, end); transform components by the triad and by typed values; drag
an action's end on the timeline; show / hide action; a callout; two storyboards; reverse;
publish a short video and check the file's frames; save / reopen; undo / redo; a component
deleted in the design afterwards). Golden models for the explode maths.
