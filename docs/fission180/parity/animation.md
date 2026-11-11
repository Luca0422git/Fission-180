# The ANIMATION workspace (wave 7, builder animation)

Fusion's Animation workspace makes exploded views and assembly animations from the
components of a design, without changing the design. The book *Mastering Autodesk Fusion*
uses it in chapter 10 (Japanese Pull Saw, Machinist Hammer) and in the final project, and then
makes an exploded drawing from a storyboard. The report (book-parity-report.txt 185-222,
2524-2531, 2577-2578) found no such workspace in 0.1.0-beta.3.3.9: there was nothing to
reproduce, this is new.

Sources: **Autodesk** = help.autodesk.com "Fusion-Animate" pages and Autodesk's blog / support
articles (read through search excerpts: the sandbox cannot open the pages), **Forum** =
Autodesk Community answers, **Tutorial** = third-party lessons, **Book** = the report quoting
the book, **Guess** = not found written down; what Fusion is remembered to do, or the plain
choice.

## 1. Behaviour spec (what Fusion does)

### The workspace

| Behaviour | Source |
|---|---|
| Picked from the workspace switcher ("Animation"). Its toolbar has the groups STORYBOARD, TRANSFORM, ANNOTATION, VIEW, PUBLISH. | Autodesk (Animation overview), Book |
| The design timeline is replaced by the ANIMATION TIMELINE along the bottom: a ruler in seconds, a playhead, one row per component that has actions, a View row for the camera, the storyboards as tabs at the bottom left with a "+" to add one. | Autodesk blog (Animation deep-dive), Tutorial (VDCI, Product Design Online) |
| The browser shows the storyboards and the components with their light bulbs (eyes). | Tutorial |
| Animating never changes the design: components go back to their design positions in the Design workspace; storyboards are saved in the design. | Autodesk (Animation overview) |
| Only components are animated: bodies of the top level must be made components first. | Tutorial (Fab Academy), Forum |

### Storyboards

| Behaviour | Source |
|---|---|
| STORYBOARD > New Storyboard opens a dialog with Storyboard Type: **Clean** (no actions, the components where the design has them) or **Start from end of previous** (no actions, every component where the previous storyboard left it). | Autodesk (Create a storyboard); Fusion API `Storyboards.add(isCleanStoryboard)` |
| A design can hold several storyboards; each is its own animation and is published on its own or all together. | Autodesk blog |
| Right-click a storyboard's tab: Rename, Copy, Paste, Delete, **Reverse** (the actions run backwards: an explode becomes an assemble). Copy + Paste + Reverse is the usual way to get "explode, then assemble". Del deletes the active storyboard. | Autodesk (Reverse storyboard), Autodesk support article, Forum |

### The timeline

| Behaviour | Source |
|---|---|
| Each number on the ruler is a second. The playhead is dragged to the time where the next change is recorded. | Tutorial (VDCI) |
| The **scratch zone** is the area left of time 0. With the playhead there (or at 0) nothing is recorded as an action, "but the transforms performed are honored": it sets up how the storyboard starts (moved components, hidden components, the first view). | Autodesk (help, blog) |
| A change made with the playhead at a time T > 0 becomes an **action**: a bar on the row of its component that **ends at the playhead**. | Autodesk blog ("end time at the current location of the playhead") |
| The bar starts where that component's previous action ended, or at 0. | Guess (the blog says Auto Explode's actions start at 0; tutorials then drag the left end later) |
| An action is moved by dragging it, and made longer or shorter by dragging either end. Right-click an action: Edit Start/End (type the times; "a change to the duration adds or removes time at the end"), Delete. | Autodesk (help), Tutorial |
| Transport: go to start, previous action, play / pause, next action, go to end. Space plays. | Tutorial; Autodesk support article (space bar) |

### TRANSFORM

| Command | Behaviour | Source |
|---|---|---|
| Transform Components | Select components (view or browser); a move / rotate manipulator (triad) appears, like Move in Design: move along an axis or in a plane, turn about an axis; X / Y / Z Distance and X / Y / Z Angle can be typed; **Set Pivot** moves the manipulator's centre; **Trail Line Visibility** shows the path as a line. OK records the transform at the playhead (scratch zone: no action). | Autodesk (Transformations), Forum (pivot, trail lines), Tutorial |
| Restore Home | Puts the selected components back where the design has them; with the playhead past the scratch zone it records that as a move action. | Autodesk blog |
| Auto Explode: One Level | Explodes the direct children of the selected assembly; a subassembly moves as one piece. | Autodesk (Explode one level of the model) |
| Auto Explode: All Levels | Explodes every level: subassemblies come apart too. | Autodesk (Explode all levels of the model) |
| (both) | After the click a small toolbar shows: **Explosion Scale** slider (left: closer, right: further apart), **One-Step Explosion** (all at once) or **Sequential Explosion** (one after another), **Trail Line Visibility**, a green check (OK) and a cancel. The actions start at 0 and end at the playhead. | Autodesk Learn (Create an exploded view), Autodesk blog, Tutorial (LinkedIn Learning) |
| Manual Explode | Pick a component, then pick the axis it explodes along; repeat for each component; Explosion Scale, One-Step / Sequential, green check. | Autodesk (Explode the model manually) |
| Show/Hide | Select components, TRANSFORM > Show/Hide (or right-click > Show/Hide, or the light bulb in the browser): a visibility action (a light bulb) is added at the playhead. Right-click it > Edit Action: Instant, or a Duration (a fade). | Autodesk (help), Forum |
| The directions Auto Explode chooses, and its distances | Not documented. | Guess: see "How Fission 180 does it" |

### ANNOTATION, VIEW, PUBLISH

| Command | Behaviour | Source |
|---|---|---|
| Create Callout | Click a point on a component (the pin is green: it follows the component) or in space (red pin), type the text. The callout is an action on the timeline (shown from the playhead on; its bar is dragged like any other). | Autodesk (Annotation; Activity 5) |
| View | A toggle: on (red dot), changes of the view (orbit, pan, zoom, ViewCube) with the playhead past the scratch zone are recorded as View actions on the View row; off (yellow dot), they are not. On by default. A View action is edited like any other (Edit Start/End, drag, Delete). | Autodesk (help), Autodesk support article |
| Publish Video | Video Options: **Video Scope** (Current Storyboard / All Storyboards), **Video Resolution** (Current Document Window Size, presets, Custom with Width, Height, Lock Aspect Ratio); then a save dialog; the video is written to a local file. | Autodesk (Publish documents; Activity 6) |
| Frame rate | Fusion has no setting; an old thread says 24 frames a second. | Forum |
| The file type | .avi in older versions, .mp4 today. | Forum, Autodesk blog (2026) |

### Drawings from an animation

| Behaviour | Source |
|---|---|
| File > New Drawing > From Animation (pick a storyboard), or in a drawing Create > Base View with Representation = a storyboard: the view shows the assembly "as it appears at the end of the playhead in the storyboard", i.e. the storyboard's exploded state. | Autodesk (Create a new drawing from an animation) |

## 2. How Fission 180 does it

Files: `animation_core.py` (pure Python: the storyboard data, quaternions and slerp, poses at a
time, visibility, camera, callouts, the explode maths, timeline edits, reverse),
`animation.py` (the design side: where storyboards are stored, the contract for drawings,
Auto / Manual Explode on real components), `animation_view.py` (showing a time in the 3D
view without touching the design), `animation_ui.py` (the workspace, the playhead and the
playback, recording the view, the commands), `animation_timeline_ui.py` (the ANIMATION
TIMELINE), `animation_panels.py` (the dialogs), `animation_video.py` +
`animation_video_core.py` (Publish Video), `animation_browser.py` (the browser in the
workspace), `ai/ops/animation_ops.py` (steps for golden models and, later, AI tools).

- **Stored in the design**: one hidden object `Animation` (an `App::FeaturePython`,
  `Fission180Type` "Animation", proxy `fission180.animation.StoreProxy`) with the property
  `Fission180Animation`: JSON of every storyboard. It is written inside an undo step, so
  Undo / Redo and save / reopen need nothing else. It is no timeline step and no browser
  row. A design without storyboards shows one empty tab "Storyboard1" that is only made in
  the design when something is recorded on it (entering the workspace changes nothing).
  Components are named by their FreeCAD object name: a renamed component keeps its
  actions (its row takes the new name). What belongs to a component that was deleted is
  left out of every read (the timeline says how many actions) and dropped from the stored
  data at the next change; until then an Undo of the deletion brings it back.
- **Nothing in the design moves.** A time is shown by giving each component's *view* another
  transform (`ViewObject.setTransformation`) and switching its display off (its
  `SwitchNode`) for hidden components; a fade is a material of our own in front of the
  component; callouts and trails are nodes of our own. Leaving the workspace (or
  switching to another design's tab, Home, a drawing, another workspace, closing) puts
  every view back on its component's `Placement`. Scrubbing, playing and publishing do not
  mark the design as changed and make no undo step; recording something on a storyboard
  does (it is saved with the design).
- **A pose at a time**: a component starts at its design placement, times the storyboard's
  start offset (what was done in the scratch zone), then every transform action of that
  component in order of start time, each applied for the fraction of it that has passed
  (move: that fraction of the distance; turn: that fraction of the angle about its axis
  through its pivot, which is the slerp between the two orientations). Offsets are in the
  frame of the component's parent, like `Placement`.
- **The playhead and recording**: at 0 (the scratch zone, drawn left of the ruler's 0)
  nothing is recorded as an action: a transform, an explode or a Show/Hide there changes
  how the storyboard starts. Past 0 a change becomes an action that ends at the playhead
  and starts where that component's previous action of the kind ended (0 when it has
  none; beside it when one already ends at the playhead). Times snap to tenths of a
  second. While a command's dialog is open the playhead and the bars do not move (the
  command works at the time it was started at; a click says so).
- **Selecting**: a click in the 3D view takes the top-level component of what was clicked
  (as Fusion takes the child of the active component); a part inside a subassembly is
  picked by its browser row. Selected before the command, or clicked while its dialog is
  open (a click on a picked one drops it).
- **Auto Explode** (Fusion's rule is not published; ours, `animation_core.explode_moves`):
  among the components of one level the biggest (by its box) stays. Each other one goes
  along the axis on which it lies most outside the biggest one (the lid on top goes up,
  the pin at the side goes sideways); one that lies inside its box on every axis (a shaft
  through a hub) comes out along its own longest side. The gap is `Explosion Scale x a
  quarter of the longest side of them all`: the first component going a way moves until it
  is clear of the biggest one's box, plus the gap; each next one going the same way ends a
  gap beyond the one before. So the gaps are even and no part ends inside another. One
  Level: the direct children of the selected component (nothing selected: of the design);
  selected components that hold none: just those, among their siblings. All Levels: the
  children of every subassembly too, each among its own siblings. One-Step: each bar from
  where its component's last action ended to the playhead; Sequential: one after another
  in equal parts of that time, the one that goes furthest first. The slider's middle is
  scale 1, its left end 0, its right end 3.
- **View**: on by default (Fusion). With it on and the playhead past 0, a change of the view
  (orbit, pan, zoom, ViewCube) that has come to rest is recorded as a View action ending at
  the playhead (a View action that already ends there takes the new view); the view before
  the first one is kept as the storyboard's first view. With the playhead in the scratch
  zone the view is only stored once the storyboard has views. Scrubbing and playing turn
  the camera between the views (the point looked at moves in a line, the direction slerps).
- **Publish Video**: frames are rendered from the 3D view off screen, one per 1/fps of each
  storyboard, both ends included. FreeCAD's AppImage and Windows build have no ffmpeg
  program and no Qt Multimedia (checked: only `libavcodec` inside VTK), so the default file
  is an **AVI with Motion JPEG** written by Fission 180 itself (`AviWriter`: plays in VLC,
  mpv, Windows' players, ffmpeg). When an `ffmpeg` program is found on the computer the
  dialog also offers **MP4 (H.264)**; without it that entry is greyed and says why. A
  **PNG image sequence** is always offered. Frame rate: 12 / 24 / 30 / 60 (Fusion: 24, no
  choice). Cancel stops it and leaves no file.

### The contract for the Drawing workspace (builder drawings uses it)

```python
from fission180 import animation

animation.storyboards(doc)             # -> ["Storyboard1", "Storyboard2", ...] in tab order
animation.duration(doc, name)          # -> seconds (0.0 for an empty storyboard)
animation.placements_at(doc, name, t=None)
    # -> {object name: App.Placement} for every component (App::Part) of the design:
    #    its own Placement (in its parent's frame, like obj.Placement) at time t of that
    #    storyboard. t None = the storyboard's end (what Fusion's exploded view shows).
    #    A component the storyboard never moves is in the dict with its design Placement.
animation.global_placements_at(doc, name, t=None)
    # -> the same with each component's placement in design coordinates (parents applied)
animation.hidden_at(doc, name, t=None) # -> {object names} hidden at that time (by the
                                       #    storyboard, or hidden in the design)
animation.trail_lines(doc, animation.storyboard(doc, name))
    # -> [[App.Vector, ...]] the trail lines of the components with Trail Line Visibility
```

All are Qt-free and read only; they work without the window (headless) and without the
workspace ever having been entered. An unknown storyboard name raises
`animation.AnimationError`.

## 3. Differences from Fusion (on purpose or forced)

| Fusion | Fission 180 | Why |
|---|---|---|
| Auto Explode needs a component selected | With nothing selected it explodes the design's top level | No silent failure; one click less |
| Auto Explode shows a small toolbar in the canvas | The same options in the command dialog at the right (Explosion Scale, One-Step / Sequential, Trail Line Visibility, OK / Cancel) | Fission 180's dialogs all live there |
| Manual Explode: click an axis of a triad on the component | Six arrows on the component (click the dot at an arrow's end), or the Axis list in the dialog; plus a Distance box | The brief asks for a distance; the scale slider still scales it |
| Set Pivot: move the manipulator, confirm with a check | Set Pivot, then one click on the model: the manipulator stands there | One step less |
| A transform is shown as separate Move and Rotate actions | One bar per component and command, called Move, Rotate or Transform | Fewer bars; Reverse and Edit work on the whole |
| Callout text shows only on hover in the web viewer and not in the video | The text is drawn in the view and in the video | Forum users ask for exactly that |
| Storyboard tab: Copy, Paste | Duplicate (one entry: a copy named "... (copy)") | One step instead of two |
| Publish Video: cloud save option | Local file only | No cloud |
| Publish Video: .mp4 | AVI (Motion JPEG) unless ffmpeg is installed | No encoder is bundled with FreeCAD |
| A storyboard shows and hides components whatever the design shows | A component hidden in the design stays hidden (Show/Hide and its eye say so) | Hiding a component in Design also hides what is in it; a storyboard cannot take that back on the view alone |
| Undo in Animation stays in Animation | The same, on the design's one undo history: an Undo that would take back a step of the design is put back at once and says to go to Design for it (steps the workspace made in this session are known by name; after a reopen there is no history anyway) | FreeCAD has one undo history per design |
| Space plays from anywhere | Space plays when the timeline has the keyboard (click it first) | Space over the 3D view is not ours to take |

## 4. Tests

Unit: `Fission180Tests/unit/test_animation_core.py` (60 tests: quaternions and slerp, poses,
the state at a time, cameras, timeline edits, storyboards, reverse, the explode maths, frame
times, the AVI writer, the golden steps' format).
Golden: `anim_auto_explode_one_level`, `anim_sequential_transform_reverse` (hand numbers).
Scenarios (real input): `book_animation_workspace`, `_transform`, `_storyboards`, `_explode`,
`_publish`, `_playback`, `_switching`.

## Gaps

- **No AI tools yet**: the design steps (`anim_storyboard`, `anim_explode`,
  `anim_manual_explode`, `anim_transform`, `anim_restore_home`, `anim_show_hide`,
  `anim_reverse`) are built and golden-tested and wait in `catalog.AI_TOOLS_TO_COME`.
- **File > New Drawing > From Animation / Base View of a storyboard** is the drawings
  builder's (the contract above is what it needs).
- **A click in the view cannot pick a part inside a subassembly** (its browser row does).
- **Trails** are on or off per component (the dialogs' Trail Line Visibility, or
  right-click the row's name); Fusion can also show and hide single trail lines.
- **Fades** are one see-through amount for the whole component (a material in front of
  it), not per body appearance.
- **Callouts** are a pin and a text; no leader styles, no font choice.
- **Render-quality video** (materials, lights): the video shows the 3D view as it is.
  Fusion's users ask for it too (Forum: "Publish a video with rendering quality").
- **Joints do not drive the animation** ("Animate Joints" is a Design command): a
  storyboard moves components freely, as in Fusion.
- **The manipulator has arrows and turn handles**, not Fusion's plane squares (move in a
  plane: drag two arrows, or type two distances).
- **Playback speed** is real time only; no audio.
