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
view without touching the design), `animation_ui.py` (the workspace and its commands),
`animation_timeline_ui.py` (the ANIMATION TIMELINE), `animation_panels.py` (the dialogs),
`animation_video.py` + `animation_video_core.py` (Publish Video), `animation_browser.py` (the
browser in the workspace), `ai/ops/animation_ops.py` (steps for golden models and AI tools).

- **Stored in the design**: one hidden object `Animation` (an `App::FeaturePython`,
  `Fission180Type` "Animation") with the property `Fission180Animation`: JSON of every
  storyboard. It is written inside an undo step, so Undo / Redo and save / reopen need
  nothing else. Components are named by their FreeCAD object name: a renamed component keeps
  its actions; an action whose component was deleted is dropped when the storyboard is read
  (the timeline says how many were dropped).
- **Nothing in the design moves.** A time is shown by giving each component's *view* another
  transform (`ViewObject.setTransformation`) and its display switch another state (hidden
  components); callouts, trails and fades are nodes of our own. Leaving the workspace (or
  switching to another design's tab, closing, saving) puts every view back on its
  component's `Placement`. Playing does not mark the design as changed; editing a storyboard
  does (it is saved with the design).
- **A pose at a time**: a component starts at its design placement, times the storyboard's
  start offset (what was done in the scratch zone), then every transform action of that
  component in order of start time, each applied for the fraction of it that has passed
  (move: that fraction of the distance; turn: that fraction of the angle about its axis
  through its pivot, which is the slerp between the two orientations). Offsets are in the
  frame of the component's parent, like `Placement`.
- **Auto Explode** (Fusion's rule is not published; ours): each component moves along the
  main axis (X, Y or Z, signed) of the line from the centre of its assembly to its own
  centre, by `scale x (its distance from the centre along that axis + half the assembly's
  size along it)`; components that go the same way are stacked so that none ends inside
  another. A component that sits on the centre stays when it is the biggest there, else it
  comes out along its own longest side. One Level: the direct children of the selected
  component (nothing selected: of the design). All Levels: the children of every
  subassembly too, each from its own subassembly's centre. One-Step: all bars from the start
  to the playhead; Sequential: one after another in equal parts of that time, the outermost
  first.
- **Publish Video**: frames are rendered from the 3D view off screen, one per 1/fps of each
  storyboard. FreeCAD's AppImage has no ffmpeg program and no Qt Multimedia, so the default
  file is an **AVI with Motion JPEG** written by Fission 180 itself (plays in VLC, Windows'
  player, QuickTime with Perian, ffmpeg, browsers no). When an `ffmpeg` program is found on
  the computer the dialog also offers **MP4 (H.264)**. A **PNG image sequence** is always
  offered. Frame rate: 12 / 24 / 30 / 60 (Fusion: 24, no choice).

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
animation.hidden_at(doc, name, t=None) # -> {object names} hidden at that time
animation.global_placements_at(doc, name, t=None)
    # -> the same with each component's placement in design coordinates (parents applied)
```

All are Qt-free and read only. An unknown storyboard name raises `animation.AnimationError`.

## 3. Differences from Fusion (on purpose or forced)

| Fusion | Fission 180 | Why |
|---|---|---|
| Auto Explode needs a component selected | With nothing selected it explodes the design's top level | No silent failure; one click less |
| Auto Explode shows a small toolbar in the canvas | The same options in the command dialog at the right (Explosion Scale, One-Step / Sequential, Trail Line Visibility, OK / Cancel) | Fission 180's dialogs all live there |
| Manual Explode: click an axis of a triad on the component | The same click on one of six arrows, or the Axis drop-down in the dialog; plus a Distance box | The brief asks for a distance; the scale slider still scales it |
| Callout text shows only on hover in the web viewer and not in the video | The text is drawn in the view and in the video | Forum users ask for exactly that |
| Fades of Show/Hide | A see-through look fading over the action's time | Same |
| Publish Video: cloud save option | Local file only | No cloud |
| Publish Video: .mp4 | AVI (Motion JPEG) unless ffmpeg is installed | No encoder is bundled with FreeCAD |
| Copy / Paste of storyboards | Duplicate (one entry: a copy named "... (copy)") | One step instead of two |
| Bodies cannot be animated | The same, and the commands say so and how to make components | |

## 4. Not built (and why)

See the end of this file: "Gaps".

## Gaps

- **Trails follow a straight line between an action's ends for moves and a polyline for
  turns**; Fusion draws them the same way but lets a trail be edited per action; here Trail
  Line Visibility is per component.
- **Callout anchors** are a point on a component (it follows the component) or a point in
  space; Fusion's callout cannot be styled either. No leader arrows styles.
- **Render-quality video** (materials, lights): the video shows the 3D view as it is.
  Fusion's users ask for it too (Forum: "Publish a video with rendering quality").
- **Joints do not drive the animation** ("Animate Joints" is a Design command): a storyboard
  moves components freely, as in Fusion.
