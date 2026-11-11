<!-- A copy of docs/fission180/parity/timeline-browser.md for AI models, made by tools/fission180/make_ai_docs.py: edit the original, then run the script. -->

# Parity spec: timeline and browser (outline 7.2, 7.3)

Implemented in `src/Mod/Fission180/fission180/`: `timeline_core.py` (layout logic, unit tested),
`timeline_ops.py` (what the timeline does to the document, also used by the golden-model
builder), `timeline_ui.py`, `browser_core.py`, `browser_ui.py`, `inline_edit.py`.
Tests: `Fission180Tests/unit/test_timeline_core.py`, `test_browser_core.py`, golden models
`tl_*.json`, GUI scenarios `timeline_browser.py`, `timeline_browser_2.py`, `timeline_roll_view.py`
and the QA scenarios `timeline_browser_qa.py` .. `timeline_browser_qa4.py` (24 paths a Fusion
user takes, real mouse and keyboard input only, real-input helpers in
`Fission180Tests/gui/timeline_input.py`). Status: **first full pass + QA pass, not yet signed off
by Luca.**

## Timeline

| Fusion | Fission 180 | How it maps onto FreeCAD |
|---|---|---|
| One timeline for the whole design | Every body's steps, sketches, construction planes and features outside bodies in one row | Each PartDesign body keeps its own list (`Body.Group`); the lists are merged by creation order (`ID`, or the `Fission180Rank` a cross-body move sets). A body's own order is never changed by the merge. |
| Icon per feature | One icon per kind (Extrude, Revolve, Hole, Fillet, patterns, primitives, construction...) | `timeline_core.KIND_BY_TYPEID` / `KIND_BY_FISSION180_TYPE`; unknown Fission 180 features get a readable name from their `Fission180Type`. |
| History marker, drag to roll back | Drag the marker, playback buttons, Roll History Marker Here, settings > Roll History Marker to End | The marker is each body's `Tip`. A body whose first step is after the marker is empty (`Tip` None). |
| Drag a feature to reorder | Drag a step; a red line and a tooltip say why when it cannot go there | Move inside `Body.Group` (`removeObject` + `insertObject` keep the `BaseFeature` chain), then recompute. Refused: a step before something it uses (its sketch, the face it sits on, the features a pattern repeats, parameters); a fillet/chamfer/shell/Press Pull whose edges or faces do not exist on its new base; any move that would break a step that worked. A fillet moved earlier is re-pointed at the same edges on its new base (by geometry). |
| Right-click: Edit Feature, Edit Profile Sketch, Suppress/Unsuppress Features, Roll History Marker Here, Rename, Delete, Find in Browser, Find in Window, Group Features | All of these | |
| Suppress also suppresses what depends on it; Unsuppress brings both back | Same | PartDesign `Suppressed` (FreeCAD 1.1). Sketches and construction planes have none: Fission 180 hides them and freezes them where they are (`Fission180Suppressed`). Steps that only fail after the suppress (edges made by the suppressed step) are suppressed too. References FreeCAD marks lost while a step is off (`?Edge2`) are put back on Unsuppress. |
| Delete keeps later features working where possible | Same | The body re-links its history around the gap; a sketch that sat on a deleted face stays where it was (yellow, with the reason); the sketch of a deleted extrude shows again. A step that cannot work any more is red and adds nothing; the steps after it still build on what came before (FreeCAD would keep the old shape and skip them). |
| Errors red, warnings yellow, reason on hover | Same, also in the browser (sketches, planes) | Reasons are rewritten in plain words ("Its profile is gone (deleted?). Edit it and pick a new profile."). While a design has red or suppressed steps, recomputes run with the Report view's error output muted (the timeline shows them instead). |
| Double-click edits | `taskui.edit_object` (each feature's own dialog via `EDITORS`, else FreeCAD's) | |
| Rename | In place (Enter keeps, Esc cancels, F2) | `Label`; a renamed step shows its own name, others "Extrude 2". |
| Groups | Create Group / Expand / Collapse / Rename / Ungroup / Suppress / Delete / Roll History Marker Here; drag a group's folder to move the whole group (2026-10-16, section below) | `Fission180Group` / `Fission180GroupName` on each member (undo works). Dragging a step out of its group takes it out; dropping it between two grouped steps puts it in. A group dragged as a whole: `timeline_core.plan_group_move`, `timeline_ops.move_group`. |
| Undo/Redo | Every action is one undo step; after Undo/Redo the design is recomputed so no stale red steps remain | |
| Step names never change ("Extrude 3" stays Extrude 3 when moved or when a step is added before it) | Same, but deleting an earlier step renumbers the later ones of that kind | Steps of a kind are numbered in the order they were made (FreeCAD's object `ID`; FreeCAD's label numbers also count cancelled previews). A step Fission 180 rebuilds as another kind (extrude -> cut) is a new object: among default labels of one kind the label order decides, and the label is kept. |
| The marker can stand anywhere, also just before a sketch (that sketch is then not drawn), and at the very beginning (Move to Beginning: an empty design) | Same (2026-10-14: also before the first step; Go to beginning and Play start from the empty design) | The Tips say which solids are active; `Document.Meta["Fission180.MarkerBefore"]` names the sketch/plane right after the marker (ignored when it no longer fits the Tips, e.g. after an undo). Sketches/planes after the marker are hidden and shown again when it passes them (`Fission180RolledHidden`). |
| Edit a step after the marker (double-click, Edit Profile Sketch) | The design rolls to the step while its dialog/sketch is open, then the marker goes back | Not an undo step (the edit is). |
| A step added while rolled back goes in at the marker; the steps after it keep working | Same (2026-10-14: also with the marker before the first step or right before a sketch) | A fillet/chamfer/shell/draft/Press Pull whose base step changes (a step added before it, the step before it deleted, suppressed) gets FreeCAD's old edge names on a new shape ("Invalid edge link", or silently other edges): Fission 180 remembers the edges/faces each step was computed on and finds them again by place and size (`timeline_ops.repair_references`). FreeCAD's `Body.addObject` puts a new step before the next solid step after the Tip, or at the end of a body with no Tip (after every rolled-back step, built on all of them) and after a sketch the marker stands before: `timeline_ops.MarkerInserts` moves it to the marker (`timeline_core.place_at_marker`) inside FreeCAD's Group-change notice, before PartDesign links its base. |
| An edit that breaks a later step (box made lower than a fillet's radius) | The later step goes red, adds nothing, the steps after it still build; nothing in the Report view | `timeline_ops.settle()` runs after every recompute (feature dialogs, undo...), deferred by the timeline's document observer. |
| Play | Animates the history; starting a command stops it | Rolling the design under an open dialog committed the dialog's preview (FreeCAD commits the open undo step when another one opens). |
| Esc while dragging a step or the marker | Drops the drag | |
| Long designs | The timeline keeps the marker in view; mouse wheel and a thin bar scroll it | |
| Right-click while a command waits for picks | Not a pick; the menu entry ends the command first | A right-click selected the step and Fillet took it as "all edges of this feature". |
| Hover a step | Lights up what it made in the 3D view (the faces of an extrude/hole/fillet, a sketch's curves, a plane); nothing for steps after the marker or suppressed | `timeline_hover.py`: a face of the step's result is its own when no face of its base lies on the same surface; drawn in Fission 180's own Coin nodes. |

## Browser

Order: Document Settings (Units), Named Views, Analysis (once there is one), Origin, Bodies,
Sketches, Construction, then the components (each with its own Origin, Bodies, Sketches,
Construction and nested components; the activate ring at the end of a component row and of
the design's row: `parity/components.md`). Folders appear once they have something in them.
Each row: expand arrow, eye, icon, name. Features are not listed (they are in the timeline).
Sketches and construction are called what the timeline calls them ("Sketch 2", "Plane 1", or
the name the user gave them), like Fusion, where both show one name; FreeCAD's label
("Sketch001") still finds the row (`BrowserWidget.row`). Enter in the name field without a
change renames nothing (also in the timeline: "Extrude 1" stays a number, not a fixed name).
One origin (the active body's, else the first body's; FreeCAD gives every body its own).
Suppressed sketches and planes are greyed and struck through, not shown as warnings.

- Eye: shows/hides; a folder's eye does all of its rows. Origin planes/axes show what is really
  on screen (FreeCAD shows them through their Origin); turning one on alone hides the others.
- Selection both ways: a row click selects the object in the 3D view; selecting it in the 3D
  view or the timeline selects the row; clicking empty space clears it. Hover lights the object
  up in the 3D view. Faces and edges picked in the 3D view do not select a row (as in Fusion).
- Right-click menus per kind (`browser_core.MENUS`): body (Activate Body, Show/Hide, Opacity
  Control (parity/bodies.md), Isolate,
  Find in Window, Find in Timeline, Rename, Delete), sketch (Edit Sketch, Show/Hide, Look At,
  Find in Window, Find in Timeline, Rename, Delete), construction (Edit Feature, ...), origin
  (Show/Hide, Create Sketch), Named Views (New Named View), saved view (Go to View, Rename,
  Delete), document (Show All Bodies, Show All Sketches, Hide All Sketches, Rename).
- Double-click a body: activate it (bold, with a dot). Double-click a sketch/plane: edit it.
- A second click on the selected row's name renames it in place (section below).
- A body with nothing solid in it yet is not listed (section below).
- Units: click "Units: mm" for Change Active Units (Millimeter, Centimeter, Meter, Inch, Foot,
  Set as Default) in the task panel. FreeCAD keeps units per document (`Document.UnitSystem`).
- Named Views: TOP, FRONT, RIGHT, HOME, plus saved views (stored in the document's `Meta`).
- F2 renames, Delete deletes (one undo step, same rules as the timeline).

### A second click renames (Luca, 2026-11-02)

Luca: "a second click on a body in the browser should allow me to rename the body. same with
sketches and assemblies". Sources (search summaries only: forums.autodesk.com is blocked from
the sandbox): **Forum** "Unable to slow double click" (2019) and "Rename a body, component,
sketch": a body, sketch or component is renamed in the browser by clicking its name, pausing,
then clicking it again (a "slow double-click"); a quick double-click instead edits a sketch;
users click the name text, not the icons. **Forum** "Can't mass rename anymore": an Autodesk
engineer suggests selecting, then a long click to rename. **Guess**: Windows Explorer's and
Qt's own rule (SelectedClicked): the field opens once the system's double-click time has
passed, so a double-click still does its own thing.

| Fusion | Fission 180 |
|---|---|
| Click a row: it is selected | Same (and in the 3D view) |
| Click the selected row's name again (not a double-click): the name becomes editable, as Rename | Same, for every row that has Rename in its right-click menu and stays selected: bodies, sketches, components, construction planes, joints, joint origins, rigid groups, motion links, contact sets, motion studies, canvases, decals, mesh bodies, analyses, flat patterns, the SIMULATION workspace's studies and items. The field opens after the double-click time (Windows: 500 ms unless changed), with the name selected: typing replaces it, Enter keeps it, Esc cancels, one undo step. It is Rename's own field (also F2 and right-click > Rename). |
| Double-click | Unchanged (edit a sketch or plane, activate a body or component, open a drawing): the rename its first click started is dropped |
| Not a rename | The first click (it only selects); a click on a row selected elsewhere (the 3D view, the timeline: that click is the first one in the browser; **Guess**, the safer reading of "a second click"); a click on the eye, the icon, the expand arrow or a component's activate ring; a drag of the row; Ctrl / Shift clicks or several rows selected; a click while a command's dialog is open or a sketch is being edited (the click is a pick for the command); a key pressed in the double-click time (F2, Delete win) |

The field keeps the keyboard when the 3D view takes it for a moment (`inline_edit.GRACE_MS`,
MEMORY "Typing right after Rename"). Code: `browser_core.second_click` (unit tested,
`SecondClickTests`), `BrowserWidget._note_press` / `_note_release` / `_slow_rename`.
Scenario `browser_second_click` (a body, a sketch and a component renamed with two clicks;
a double-click still edits; the eye, the icon, a drag, Ctrl+click, F2 and the menu).

### No body before the first solid (Luca, 2026-11-02)

Luca: "when making a sketch, a body appears in the browser. but there are no bodies?" (a new
design, Create Sketch just clicked: the browser showed Bodies > Body). Sources (search
summaries only): **Autodesk** tutorial (part modeling): an extrude with the default New Body
operation adds a folder named Bodies to the browser; **Forum** "Body missing from browser":
the Bodies folder is only there when the component has bodies. A Fusion body is made by its
first solid feature; a sketch belongs to the component, not to a body.

| Fusion | Fission 180 |
|---|---|
| A new design: Origin, no Bodies | Fission 180 makes a PartDesign Body to hold the first sketch (its origin planes are what Create Sketch offers). Such a body, with no step that makes a shape (only its origin, sketches and construction: `bodies.is_empty`), is not listed: no Bodies folder while Create Sketch waits, after Esc, while sketching and with sketches only. Its sketches are under Sketches, its planes under Construction, its origin is the design's Origin. |
| The first Extrude (New Body) adds Bodies > Body1 | The first solid step goes into that body (`extrude._structure`), which is then listed as before. Undo of that step: unlisted again. |
| A body that exists stays listed | Unchanged: a hidden body, a surface body, a sheet metal body, a mesh body, a body whose steps the history marker stands before, a body whose only step is in error, bodies in components. |
| A component's empty body | The same in a component: Origin, Sketches, then Bodies once something solid is in it. |
| The body a rebuild is made in (Rebuild with Timeline (AI)) | Fission 180 only: listed from the start, empty (its right-click carries Compare / Finish / Stop Rebuild). |

Create Sketch cancelled with Esc on an empty design leaves its (unlisted) body in the design,
and FreeCAD's "Add a Body" in the undo history: the next Create Sketch uses the same body (no
pile of empty bodies), and Undo then takes it away with no visible change but the Origin
folder (it is that body's origin). Not removed on Esc: that would mean an undo of FreeCAD's
own step from the sketch code. Elsewhere bodies were already listed only with a solid
(Derive, export, the Physical Material dialog); the version compare (`versions.summary`)
counts every PartDesign Body in the file, so a sketch-only design shows "Bodies 1" there.
Code: `bodies.is_empty`, `browser_ui._empty_body` (row flag "empty"), `browser_core._folders`
(unit tests `EmptyBodyTests`). Scenario `browser_empty_body` (Create Sketch and Esc on a new
design, a sketch, undo to the empty design and redo, save and reopen, the first extrude,
Ctrl+Z / Ctrl+Y, a hidden body, a component).

### The 3D view's hover lights the browser row (Luca's request, 2026-10-23)

Luca: "if i hover over a body in the work area, it should get highlighted in the browser".
Fusion's browser and canvas light each other up (forum "Turn off part highlighting when
mousing over": hovering a browser row lights the body in the canvas, the same effect as
hovering the body); Fission 180 had the browser > 3D view direction only.

- The mouse over a body in the 3D view (any of its faces, edges, a step's shape) lights that
  body's row with a light accent-blue band; over a sketch or a plane, its row; over a
  component's body, the body's row (the innermost row wins). With the folder or component
  that holds the row closed, the closed row lights instead. Off the part: nothing lit.
- How: the browser's selection observer gets FreeCAD's preselection changes
  (`setPreselection` / `removePreselection`) and looks a moment later (30 ms, so a sweep over
  many faces is one look): `Gui.Selection.getPreselection()` -> the objects along the
  sub-element path (`getSubObjectList`), a step followed by its body ->
  `browser_core.hover_row` -> `shown_row` (a closed parent) -> the delegate paints it.
  The browser does not scroll or open folders for a hover (a sweep over the part would make
  it jump).
- Scenario `browser_opacity_hover` P4 (real mouse moves over the 3D view); unit tests
  `test_browser_core.HoverTests`.

### A hidden body shows as a ghost while its row is hovered (0.1.0-beta.2.2)

Luca: "If i hover over a body in the browser that is hidden, I should get a preview of that
body in the workspace. A ghost body if you will." Hovering a shown body's row lights it through
FreeCAD's preselection, which colours only what is drawn, so a hidden body showed nothing.

- The mouse over a hidden body's, component's, mesh body's or loose solid's row puts a faint,
  see-through light-blue copy of it in the 3D view (`hover_ghost.py`: a temporary Coin node,
  unclickable). It goes when the mouse leaves the row or the browser, the row is clicked, its
  eye is clicked, or the browser is rebuilt. No document or view property changes (FreeCAD
  would record those in the undo history and the file): nothing goes into Undo.
- A body the timeline marker stands before has no solid there: no ghost (nor for a body a
  component hides because of the marker). Shown bodies get no ghost (they light up as before).
- The tessellation is kept per object until its shape or place changes (coarse: a ghost needs
  no detail), so hovering up and down a big design stays quick.
- Scenario `browser_ghost` (real mouse moves over the rows, the eye clicked).

## Known gaps

- (Done before polish-2, listed here until then: an Extrude made while rolled back before a
  fillet switches to Cut; `extrude.dependents()` skips the fillet's `Base` when it is its
  `BaseFeature`; scenario `timeline_rolled_cut`.)
- Fusion has no drop of a step into a group by dragging (Autodesk staff: delete the group and
  group again); Fission 180 lets a step dragged between two grouped steps join the group
  (kept, a convenience). A group cannot go inside another group (Fission 180 has no nested
  groups; refused with the reason).
- Steps outside any body (plain Part features) are shown in the timeline but never rolled back.
- Saved named views are stored in the document's `Meta`, which Undo does not cover.
- Errors from a recompute run while the design already has red or suppressed steps are not
  printed in the Report view (by design); they are on the timeline. The first failure of a
  healthy design still prints, so the test harness still catches new bugs.
- Bodies have no "New Body" command of their own yet; Extrude > New Body (extrude branch) and
  FreeCAD's PartDesign Body command (command search) create them.

## Groups dragged as a whole, the marker over a group (branch `sf/polish-2`, 2026-10-16)

Sources: **Autodesk** API `TimelineGroup` / `TimelineObject.reorder` and `rollTo` (a group is
reordered as one object and the marker rolls to before or after it; both refuse an expanded
group); **Autodesk** help "Use the Timeline" (the Plus / Minus button expands and collapses a
group); **Forum** (Autodesk QA: "Delete group and expand its contents" is Fusion's ungroup;
Autodesk staff: items cannot be dragged into a group). **Guess**: a group holding the marker
stays open (it cannot be collapsed until the marker leaves) and cannot be dragged.

| Fusion | Fission 180 |
|---|---|
| Drag a collapsed group: its features move together | Drag a group's folder (open or closed): its steps move together, keep their order and their group, and each goes to its place in its own body (several bodies at once: their creation ranks are set for the steps of the group alone). One undo step. Refused with the reason, like a step: a step of the group before something it uses, or a later step using one of the group's steps before it ("Sketch 3 uses Extrude 1, so Group 2 cannot come before it."); a drop inside another group; while the marker is inside the group. Esc while dragging drops the drag. |
| Roll the marker to before / after a group | The marker dropped on a closed folder goes before or after it (which half); Roll History Marker Here in the group's menu puts it after the group's last step. |
| The marker inside a group | The group shows open while the marker is inside: Collapse Group is greyed, a click on the folder keeps it open and says why. |

Code: `timeline_core.group_members`, `marker_in_group`, `plan_group_move`, `_block_keys`
(unit tests `GroupMoveTests`), `timeline_ops.move_group`, `timeline_ui._GroupButton`
(press / drag / release / Esc) and `TimelineWidget._plan`. Scenario `polish2_timeline_groups`
(a group dragged before an earlier step across two bodies, undo / redo, a refused drag, the
marker inside a group, Roll History Marker Here, Esc, rename, ungroup, save and reopen).

## Marker at the beginning, one name (2026-10-14, gaps work)

Sources: **Autodesk** help "Parametric Timeline and Features" (ASM-TIMELINE, search excerpt):
the buttons left of the timeline move the marker to the beginning or the end, play, or step
one feature; the marker can be dragged to any point. **Forum** (Autodesk's community manager,
"Are revisions to Timeline inserted or appended?"): with the marker rolled back, new features
are created at the marker, not at the end. **Autodesk** API `TimelineObject.rollTo` (before or
after an object). **Guess** (from use): the browser and the timeline show one name for a sketch
or a construction plane; renaming it in one renames it in the other (Fission 180 did that already,
only the default names differed).

Before the first step every body has no `Tip` (an empty design; `timeline_core` counts 0
active solid steps). Golden `tl_roll_to_start` (a plate added at the start comes first: the
volume checked right after it is the plate alone), scenario `gaps_timeline_start.py` (drag the
marker before Sketch 1, a post made there goes in first, Go to end builds the box on it,
Ctrl+Z / Ctrl+Y, the browser's "Sketch 1" / "Sketch 2", Enter renames nothing, playback).

## FreeCAD 1.1 findings (worth copying into MEMORY.md)

- A PartDesign feature that fails keeps its last good shape, and FreeCAD skips every step after
  it, so the 3D view keeps showing geometry that no longer exists. `timeline_ops.recompute()`
  passes the step's base shape through and rebuilds the steps after it.
- A body whose Tip has no shape (everything suppressed) fails with "Tip shape is empty" and keeps
  its old shape; Fission 180 empties it.
- `Suppressed` features are still computed; if they fail FreeCAD prints "Failed to recompute
  suppressed feature" every time. References to edges/faces that vanish while a step is off
  are rewritten to `?Edge2` and never come back on their own: Fission 180 stores them before
  suppressing and puts them back on Unsuppress.
- After a reorder, a fillet keeps its old edge *names*, which can mean other edges (or none) on
  the new base: re-point it by geometry.
- Undo/Redo restore shapes but not the error state of steps; recompute afterwards.
- Origin planes/axes are drawn through their `App::Origin`: a plane's own `Visibility` is usually
  True while nothing shows.
- `Gui.Selection.removePreselection()` does not exist in 1.1; it is `clearPreselection()`.
- Qt test input: a `QMenu` ignores a click that comes without mouse movement since it opened;
  `QTest.mouseDClick` sends only the double-click event (send press/release first); widgets
  added to a visible layout are hidden until the event loop runs. `widget_input.py` handles
  all three. A drag's release must go through `QTest.mouseRelease` (the window): released with
  `sendEvent`, Qt kept the button "down" and the next click anywhere went to the dragged widget.
  Qt 6 does not pass a synthetic wheel event on to the parent: send it to the scroll viewport.
- Inserting a step before a dress-up (rolled-back marker) or deleting the step before it
  re-links the dress-up's `Base` to the new base with the old element names: "Invalid edge
  link" (or other edges). `Document.openTransaction` commits the transaction that is open (in
  every document): a timeline/browser action that opens an undo step while a command dialog
  is open must end that command first. Setting `MapMode` attaches at once and prints
  "PositionBySupport: subshape not found" (Report view and a pop-up balloon) if the face is not
  back yet: unsuppress solids, recompute, then sketches.
- A body without a Tip takes a new feature at the end of its Group (`getNextSolidFeature()`
  is null), whatever the rolled-back features are. A Python document observer may reorder the
  Group inside its `slotChangedObject(body, "Group")`: FreeCAD takes the new order as part of
  the same change (no second notice, one undo step) and `setBaseProperty` then links the
  feature's base from the new order.
- A taper added to a Pad turns its side faces into B-splines (flat, but not `GeomPlane`) and
  FreeCAD loses the names of its edges for the steps after it ("?Edge4", "missing element
  reference", printed while the Pad recomputes): `fission180/picks.py` finds them again in the
  same recompute (`slotRecomputedObject` of the Pad comes before the later steps run).

- Journey pass (sf/journey-pl, 2026-10-23): Delete keeps the edges a Lip, Hem or Corner Round
  picked on its base (`Edges` is in the remembered references), also when FreeCAD emptied the
  link because that base step was the deleted one (a Snap Fit's groove step under a Lip).
  Open: a plane or sketch made on a face of the last step counts as depending on that step,
  so Suppress takes it (and what is built on it) along even when the face was made earlier.

## Wave 7, the book parity report: the timeline (2026-11-11)

- Fusion's entry is **Create Group** (Autodesk help, "Use the Timeline": "right-click the
  selection and choose Create Group"); it was "Group Features" here.
- A fast drag (the button let go far from where it was pressed before any move was told)
  moves the step like a slow one. A drag that cannot be says why next to the pointer and
  keeps it up (`commands.tell`): the tip was hidden at once by the mouse still moving.
- The settings (gear) menu is a plain pop-up: it does not wait inside the button's click.
- Edit Feature on the step an open dialog is still making keeps the dialog (see gear.md).
- A step dragged before or after another keeps its picks: a Thread finds its cylinder again,
  a fillet / chamfer its edges (also Fission 180's own step with several sets), within the
  distance a modeled thread moved the surface (`timeline_ops._names_on`).
