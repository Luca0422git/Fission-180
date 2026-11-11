# Parity spec: Components (outline 7.2 browser, 7.10 Assemble; plan.md "Next" item 2)

Implemented in `src/Mod/Fission180/fission180/`: `components_core.py` (pure logic, unit tested),
`components.py` (the document model, no Qt: dialogs, golden builder and headless tests use
it), `components_ui.py` (commands and the New Component / Move to Component dialogs),
`browser_core.py` + `browser_ui.py` (the component tree, activate ring, menus, drag and drop),
`timeline_core.py` / `timeline_ops.py` / `timeline_ui.py` (component steps, the component of
every step, the active component's filter), the New Component operation in `extrude.py`,
`revolve.py`, `sweep.py`, `loft.py` and their dialogs.
Tests: `Fission180Tests/unit/test_components_core.py` (16 tests), GUI scenarios
`components_basic.py` (9 paths), `components_extrude.py` (5 paths), `components_move.py`
(6 paths), all real clicks (helpers in `Fission180Tests/gui/component_steps.py`).
Status: **built and tested with real clicks, not yet signed off by Luca.** Part 2 (moving, copying, patterning components; components-2) is described in its own section below.

## Sources (Fusion's behaviour, researched before building; Autodesk's sites were not
reachable from the sandbox, so the summaries of their pages found by web search are cited)

1. Autodesk Fusion API user manual, "Documents, Products, Components, Occurrences, and
   Proxies": a component node is added to the browser for each new component; "clicking the
   radio button to the right of a component node in the browser activates that component";
   geometry made through the UI goes into the active component; "the root component is always
   active by default after opening or creating a document".
2. Autodesk Community, "How do you deactivate a component?" (accepted answer by an Autodesk
   community manager): to leave a sub-component you activate the root component, the top node
   in the browser; "you are always working inside an activated component. It may be the root".
3. Autodesk Community (several threads): activating a component routes new sketches to that
   component's Sketches folder and bodies to its Bodies folder.
4. Autodesk Learn, "Create a component within an assembly" and the course "Creating
   assemblies": the New Component dialog offers Standard / Sheet Metal, Internal / External,
   From Bodies, a Name, a Parent and Activate; "the new component appears at the bottom of
   the browser"; with Activate on it is activated as soon as it is created.
5. Autodesk Learn ("Creating assemblies") and the Community thread "Sketch to Component":
   Create Components from Bodies (right-click a body) makes a component with an Origin folder
   and a Bodies folder holding the body; the body's sketch "is still resident at the top level
   of the design" (a sketch outside the body stays where it was); several bodies give one
   component per body (thread "Move multiple bodies to new component"); a body called V-block
   gave a component called V-block.
6. Autodesk Fusion help, "Isolate" (GUID-38F2A3B4): "isolate selected bodies or components and
   hide all other objects. When you unisolate, visibility is restored to all objects that were
   visible before you used the isolate. Any objects that were hidden before isolation remain
   hidden." Community threads: Isolate is in the browser's right-click menu.
7. Autodesk Knowledge, "Unable to drag a body from one component to another": bodies are moved
   between components by dragging them in the browser (or cut / paste), which the timeline can
   refuse when it has errors.
8. Autodesk blog "Master the Timeline, Browser, & Preferences" and the Community threads
   "Timeline - All components rolling back", "My brain is fried trying to figure out
   components and timeline history": Fusion has one timeline for the design; activating a
   component "changes the timeline to show features specific to the activated component";
   rolling the marker before a component's creation makes the component disappear from the
   browser (so a component's creation is a step in the timeline).
9. Autodesk's Fusion shortcut list: no key for New Component, Activate or Isolate (Community
   thread "Keyboard Hotkey for Isolate/UnIsolate" asks for one). Fission 180 gives them none.
10. Extrude with Operation "New Component" (Community thread "along"): the result is a new
    component holding the new body; users then drag the sketch into it if they want it there,
    so the sketch stays in its own component.

Guesses (not found in a source, marked for Luca's Fusion check): the component's icon; that
the activate ring is drawn for every component row (Fusion may show it on hover only); the
default name "Component1" (Fusion numbers bodies "Body1", "Body2": components follow); that
Extrude > New Component activates the new component; whether From Bodies in the New Component
dialog makes one component per body (built so, like the right-click command).

## The model (a contract: Joints and other features rely on it)

| Fusion | Fission 180 / FreeCAD |
|---|---|
| A component holds bodies, sketches, construction geometry, joints and nested components | An `App::Part` container. Its name is its `Label`. Bodies (`PartDesign::Body`) are in `part.Group`; sketches, features and construction live inside their body (FreeCAD's PartDesign needs that), so they are in the component through the body. A nested component is an `App::Part` in an `App::Part`. Fission 180 tags its components with the string property `Fission180Type = "Component"`; an `App::Part` from elsewhere (an old FreeCAD file) is a component too. |
| The root component | The document itself: a design without components has no container, so every earlier file and single-body workflow is unchanged. |
| One active component (the radio button); new sketches, bodies and features go into it | FreeCAD's active-object slot `"part"` (`Gui.ActiveDocument.ActiveView.setActiveObject("part", obj)`) plus the rule that the active body (slot `"pdbody"`) lies inside it. `components.active_component(doc)` = the active body's container when a body is active, else the `"part"` slot, else the root (None). `components.set_active(component)` activates a component and makes its preferred body (the one active there last, else the oldest) the active body, or no body when it has none. `components.activate_body(body)` activates a body together with its component. |
| New work goes into the active component | `commands.find_body()` returns the active body, else a body inside the active component (made active); `commands.ensure_body()` creates one *inside the active component* when it has none (FreeCAD's Body command uses the `"part"` slot; Fission 180 moves the body if the slot lagged). Every command that works on "the body" (Create Sketch, Extrude, Hole, patterns ...) therefore works in the active component without knowing about components. |
| A file opens with the root active | FreeCAD stores no active objects: a reopened file has none, so the root is active. |
| Bodies are numbered per component (Body1 in every component) | `components.new_body_in(doc, container)`; FreeCAD's "allow duplicate labels" preference is switched on while Fission 180 is on (kept and given back like the viewer settings, `theme.VIEWER_SETTINGS`), else FreeCAD renamed the second Body1 to Body1001 and the component made from body "Body" to "Body001". |
| Components in the timeline | A component is a timeline step (kind `component`, icon `new_component`, called by the component's name) at its creation, hidden while the history marker stands before it (components-2) and never suppressed. Each step knows its component (`Item.component`, shown in the hover text). |

API for other features (all in `components.py`): `list_components(doc)`, `container_of(obj)`,
`component_of(obj)`, `is_inside(obj, component)`, `ancestors(obj)`, `bodies_in(doc,
component, recursive)`, `components_in(doc, component)`, `new_component(doc, label, parent)`,
`new_body_in(doc, container)`, `from_bodies(doc, bodies, parent, label)`, `place(obj,
component)`, `remove(doc, component)`, `active_component(doc)`, `set_active(component)`,
`activate_body(body)`, `preferred_body(doc, component)`, `isolate_hidden(doc, obj)`,
`move_targets(doc, moving)`. Nothing here opens an undo step except `remove` (one step); the
callers (dialogs, browser) wrap the rest in their own transaction.

## Browser

| Fusion | Fission 180 |
|---|---|
| Root row: Document Settings, Named Views, Origin, Bodies, Sketches, Construction, then the components | Same (`browser_core.build`), components in the order they were made. |
| Component row: eye, icon, name; inside: Origin, Bodies, Sketches, Construction, nested components | Same. The component's Origin folder lists the `App::Part`'s own origin planes and axes (the eye shows and hides them); Create Sketch on one of them puts the sketch on the body's plane of the same role (same place) inside the component. The root's Origin stays the active root body's (as before). |
| The activate radio button; the active component's name is bold | A ring at the end of every component row and of the design's row, filled blue for the active one; the name is bold. Click the ring (or double-click the row) to activate. Activating a component makes its last active body the active body (bold with a dot) or, with no body yet, none: the next sketch or body is made inside it. |
| Right-click a component: Activate, New Component, Show/Hide, Isolate / Unisolate, Find in Window, Find in Timeline, Rename, Delete (Fusion also has Ground, Rigid Group, Copy, Paste, Opacity Control, Selectable, Properties...) | Activate (not on the active one), New Component (the new one goes inside this component), Hide / Show, Isolate / Exit Isolate, Find in Window, Find in Timeline (selects the component's step and every step inside it), Move to Component (Fission 180: a submenu with the root and the components it may go to), Rename, Delete. Joints entries belong to the Joints work. |
| Right-click a body: Create Components from Bodies, ... | Activate Body, Create Components from Bodies (every selected body gets a component named after it, where the body was), Hide / Show, Isolate / Exit Isolate, Find in Window, Find in Timeline, Move to Component, Rename, Delete. |
| Right-click the root row: New Component, Activate ... | Activate (when a sub-component is active), New Component (at the root), Show All Bodies, Show / Hide All Sketches, Rename. |
| Drag a body onto a component to move it there (also a component into a component) | Same, with a blue frame on the row it can be dropped on; the design's row is the root. One undo step. A component never goes into itself. Fusion refuses a drag while the timeline has errors; Fission 180 moves anyway (features keep their links; FreeCAD's PartDesign allows cross-component links). |
| A component's eye hides and shows the component; what is inside keeps its own eyes | Hiding sets the rows under it hidden and remembers which were shown; showing it again shows only those (its origin planes and the sketches its extrudes hid stay hidden; journey_plastic). Without a memory (hidden before a reopen) it shows all but the origin, sketches and construction. |
| Isolate a body or component: everything else hidden; Unisolate restores what Isolate hid | Same: what was hidden before stays hidden; a body's component (and its parents) stay shown. |
| Delete a component deletes its bodies and nested components | Same, one undo step (Undo brings all of it back). F2 renames, Del deletes, as for bodies. |
| Rename in place | Same (`Rename` or F2; Enter keeps, Esc cancels); the timeline's component step follows. |

## Commands

| Fusion | Fission 180 |
|---|---|
| ASSEMBLE > New Component (no key): dialog Type (Standard / Sheet Metal), Internal / External, From Bodies, Name, Parent, Activate (on) | `Fission180_NewComponent` on the ASSEMBLE tab: Name (Component1, Component2 ... proposed), Parent (a drop-down of the root and every component, the active one preselected; Fusion has a selection box), From Bodies (ticked by itself when bodies were picked before the command; the bodies are listed and more can be clicked in the window or the browser, a click on a listed one drops it), Activate (on). OK makes the component(s); Cancel makes nothing. Sheet Metal and External are out of scope (no sheet metal; one design per file). |
| Activate | `Fission180_ActivateComponent` (command search; the browser's ring is the usual way). |
| Isolate / Unisolate | `Fission180_Isolate`, `Fission180_Unisolate` (command search and the browser's menus). |
| Create Components from Bodies (right-click a body) | `Fission180_ComponentsFromBodies` and the browser's body menu. |
| Drag a body into a component | `Fission180_MoveToComponent` (a small dialog: what moves, Into) and the browser's drag or submenu. |
| Extrude / Revolve / Sweep / Loft, Box / Cylinder / Sphere / Torus / Coil / Pipe: Operation New Component | The fifth operation in these dialogs (the primitives since 2026-10-13: **Autodesk** SLD-BOX-SOLID / SLD-CREATE-SOLID-PRIMITIVE list it for Box and the other solid primitives): a new component (Component N, under the active component) with Body1 holding the result; the sketch stays in its own body (Fusion: the sketch stays, people drag it in if they want); the new component becomes active (guess). Editing the step keeps the same component and body; Operation reads New Component. Cancel (or a failed preview) removes the component again. Switching between New Body and New Component in the dialog (or in an edit) moves the result: out of the component (which goes), or into a new one. |

## Timeline

| Fusion | Fission 180 |
|---|---|
| One timeline for the design; a component's creation is a step | Same: the component step at its creation, called by its name; Rename / Delete / Roll Here / Find in Browser work on it; double-click activates it; it is never suppressed (greyed out); with the marker before it the component is hidden and gone from the browser (Part 2 below). Create Components from Bodies adds a step per component. |
| With a component active the timeline shows that component's features | Same: only the steps of the active component and of the components inside it show (the component's own step included); a grey note at the end counts the hidden ones and says how to see all (activate the design's row). The history marker stands before the first shown step after its slot. Dragging the marker or a step still acts on the whole design, as in Fusion. |
| Hover a feature: its name | Also "In component: X" for steps inside a component. |

## Part 2: moving, copying and patterning components (components-2, 2026-10-14)

Built in `src/Mod/Fission180/fission180/`: `component_move.py` (the document side of moving a
component, its captured Move step, the marker), `component_move_ui.py` (the Move/Copy dialog
with Move Object Components; Set Pivot is in `move_ui.py`, shared with bodies),
`instances.py` (linked instances and Paste New), `clipboard_ui.py` (Copy / Paste / Paste New),
`component_pattern.py` (Pattern Type Components), `component_look.py` (Active Component
Visibility); Combine New Component (`combine.py`), Split Body with several tools (`split.py`).
Tests: scenarios `components2_move` (344 checks), `components2_copy` (277),
`components2_pattern` (278), `components2_bodies` (298), `components2_marker` (208); golden
models `comp_*`, `bodies_split_two_planes`, `bodies_combine_new_component`; unit tests in
`test_components_core.py`, `test_timeline_core.py`.

### Sources (Autodesk's sites cannot be opened from the sandbox: search excerpts are quoted)

11. **Autodesk** help, *Move or copy geometry* (SLD-USE-MOVE-COPY): Move Object Bodies /
    Components / Faces / Sketch Objects; Move Types Free Move, Translate, Rotate, Point to
    Point, Point to Position; "Click Set Pivot to adjust the pivot point of the manipulator.
    In the canvas, hover over the geometry you want to snap to, then click to place the pivot
    point, or enter exact values in the dialog"; "Optional (components only): Check the box
    next to Capture Position to capture the new position of the component"; "Check Create
    Copy".
12. **Forum**, *Rotating Assemblies?* and *How to rotate a rectangle?* (Autodesk staff): Set
    Pivot is a toggle; pick the pivot, then click the green check to finish; then type the
    angle.
13. **Forum**, *Move operation not included in Design History?*, *Capturing position*, *Move
    Component Workflow*: a component move is not a timeline step unless its position is
    captured (Capture Position in the dialog or the POSITION panel); the design is then in a
    "position pending" state; **Autodesk** blog *How To Use Capture or Revert*: Capture stores
    the position "on the timeline", Revert returns the component to its last location.
14. **Autodesk** help, *Copy / paste a component* (excerpt): "The new component is linked to
    the original component as an identical duplicate"; **Forum**, *Duplicating or copying
    components*: copies named "Comp: 1", "Comp: 2", editing one changes the other; Paste New
    "pastes independent copies"; **Autodesk** API, *Occurrences.addNewComponentCopy*: "the
    equivalent of copying and using the Paste New command ... a new component that has its
    own definition (sketches, features, etc.)".
15. **Forum** (*Can someone help me copy and paste new for a component?*): after the paste
    Fusion invokes Move with the new component selected.
16. **Forum** (*Break link between copied and pasted components*): "a move on a component
    applies only to that component instance".
17. **Autodesk** help, *Create a rectangular pattern*: Object Type "Components duplicates
    components in an assembly and distributes them according to the pattern settings".
18. **Autodesk** knowledge, *Changing the opacity of a body does not work in Fusion*: the
    preference "Active component visibility" (General > Design) dims the other components;
    **Forum** (*Turn Off See Through / Transparent Components*): other components "are dimmed
    to better show the active component".
19. **Autodesk** help, *Combine reference*: New Component "creates a new component with the
    results".
20. No source shows a "New Body" command that makes an empty body: bodies come from features
    (Operation New Body), components from New Component (Autodesk blog *Getting Started:
    Start with an empty design*, forum *What can bodies do that components cannot?*). Not
    built (brief item 6 asked "if Fusion has it").

Guesses (for Luca's Fusion check): Capture Position starts unticked; Paste goes into the
active component (the right-clicked component from the browser menu); Paste New is named
"Name (1)"; Esc in the Move after a paste keeps the paste where it was pasted; Move with
Create Copy of a component makes a linked instance; the dimmed transparency (75 %).

### What the user does (and what Fission 180 does)

| Fusion | Fission 180 |
|---|---|
| M, Move Object Components: click a component (in the canvas or its browser row) | Same. Move Object switches the dialog to the components one (the move type and values are kept); a component selected before M opens it directly. A click in the canvas picks the component just below the active component on the way to what was clicked (`components_core.component_to_pick`); clicking it again drops it |
| The component moves with everything in it | Same: its Placement changes (a nested component's relative to its parent); its bodies are not changed |
| Free Move / Translate / Rotate / Point to Point / Point to Position; the manipulator; typed values | Same as for bodies (the manipulator sits at the middle of the components); axes and points are taken where they were before the move |
| Set Pivot, then Done (the check) | Same (`parity/bodies.md` Move/Copy); the scenario sets the pivot on a corner and turns the component 90° about it |
| Capture Position (components only) | Ticked: OK records the move as a **Move** step in the timeline (`ComponentMove`, one per component, one undo step). Double-click it to edit it (the dialog opens on it, Capture on); Suppress, Delete or the marker before it put the component back where it stood before it (`component_move.apply_history`). Not ticked: the component just stands there ("position pending"): with joints, joints' Capture Position / Revert are offered (the joints work owns them); a captured move also becomes where Revert returns to |
| A grounded component does not move | Refused with the reason in the dialog ("Bracket is grounded, so it cannot move. Unground it first") |
| Create Copy | The component stays; a linked instance ("Name:2") is moved instead |
| Ctrl+C / Ctrl+V on a component (also the browser's Copy / Paste) | A linked instance "Name:2" in the active component (or in the component whose row was right-clicked; never inside itself). The browser then names the original "Name:1". It is no timeline step. Move/Copy opens on it; Esc leaves it on the original |
| Editing one occurrence changes all | The instance's bodies are copies of the original's (`InstanceCopy`): every change to the original (an extrude made longer, a fillet, a new body in it) shows in every instance. Activating an instance (its ring) activates the original, with a note; renaming one renames the component (all occurrences) |
| Deleting one occurrence keeps the component while another occurrence remains | Same for the occurrences: Delete on the original (or on a component around it) hands over to its first occurrence that stays (`instances.hand_over`; beta 3 VEX QA): it takes the original's name, place and file (Insert STEP of that file is another occurrence of it), its bodies keep the solids they showed, the other occurrences repeat it, it can be copied, duplicated and edited again. One undo step. The original's features go with the original (known gaps) |
| Paste New | An independent component "Name (1)" with copies of every feature (its steps join the timeline, the component step first); Move opens on it |
| Ctrl+C / Ctrl+V on a body | Move/Copy opens on the body with Create Copy ticked (a copy body) |
| Pattern Type Components | Rectangular, Circular and Pattern on Path (`parity/patterns.md`): one pattern step; its copies are instances "Name:2" ... placed by the pattern, following edits of the component; Quantity, Distance, Angle, Suppression; edited from the timeline; deleting the step (or undo) takes the copies with it; the marker before it hides them |
| Combine New Component | `parity/bodies.md` Combine |
| Split Body with several tools | `parity/bodies.md` Split Body |
| An active component shows the rest dimmed (Active Component Visibility, on) | Same: while a component is active, every body and component outside it is drawn see-through (still pickable); the design's ring shows everything normally. Preferences > General > Design > *Active component visibility* switches it off. A look only (a Coin material over the dimmed objects, `component_look.py`): nothing is saved, no undo step |
| The marker before a component's step hides the component | Same: hidden in the window and gone from the browser while the marker stands before its step (unless steps inside it come before the marker: a component made from an existing body stays, else the body would vanish); back when the marker passes it; kept in the file |
| A step made while the timeline is rolled back goes in at the marker | Now also a new component, a captured Move and a pattern of components (`timeline_ops.place_root_step`); steps outside the bodies stand by their own creation order (`timeline_core.merge`) |
| Body Move/Copy with Create Copy, Split Body pieces, pattern-of-bodies copies of a body inside a moved component | The new body's first step now sits in that component (FreeCAD warned "Link(s) ... go out of the allowed scope") and takes its shape in the body's own coordinates (the copy landed moved twice) |

### How it is built on FreeCAD

| Fusion | Fission 180 / FreeCAD |
|---|---|
| A component occurrence's position | The `App::Part`'s Placement |
| A captured component move | `App::FeaturePython` "Move" (Fission180Type `ComponentMove`): Component, Movement (design coordinates), Before (the component's own placement before it), MoveId; it computes nothing; `apply_history` replays the moves that count at the marker from the first one's Before. The timeline treats it, a component step and a pattern of components as steps outside the bodies that roll back (`timeline_core`, "rolls") |
| An instance (Copy/Paste, Create Copy, a pattern's copy) | An `App::Part` with `Fission180InstanceOf` (the source component), labelled "Source:n", hidden from the timeline, holding one copy body per body of the source (nested components' bodies flattened). Each copy body's first step is an `InstanceCopy` (`Part::FeaturePython` inside the instance part: FreeCAD's link scope) that copies the source body's solid: in the source component's frame (the instance's own Placement places it), or moved by its pattern's `Moves` entry. `instances.sync` adds / removes copy bodies when the source's bodies change and keeps the labels (after recomputes, never during undo / redo or a file load). An `App::Link` was not used: everything else in Fission 180 (joints, export, measure, drawings, interference) works on bodies inside components |
| A pattern of components | `App::FeaturePython` (Fission180Type Rectangular/CircularPattern / PatternOnPath, "Fission180Rolls") with Source, the references and choices of a pattern of bodies, and `Moves` (each copy's movement, design coordinates); each reference is read in the frame of its body or component (`component_pattern.frame_of`) |
| Paste New | `doc.copyObject(part, True)` |
| Active Component Visibility | an `SoMaterial` with only its transparency set and the override flag on, at the top of each dimmed object's scene node (a body or a whole component), removed again when it is no longer dimmed |

## Part 3: work across components (wave 7, the book parity report, 2026-11-11)

Built in `components.py` (the one rule: `new_home`, `host_body`, `body_for_new`,
`may_change`, `has_solids`; references to another component: `ReferenceCopy`,
`reference_binder`; `whole_pick`), `sketch_ui.create_sketch`, `construct.target_body`,
`sketch_external.project_across` + `sketch_project_across.py` (Project across components),
`component_pattern.py` (Mirror of components), `component_move_ui.py` (the pivot),
`clipboard_ui.py` / `instances.py` (where a paste stands), `components_ui.py` (From Bodies,
the first component's ground, Isolate), `components_core.component_to_pick`.
Tests: scenarios `book_components_active` (bugs 5 - 8, 10), `book_components_new` (bug 9,
ground, nesting), `book_components_nested` (bug 15, parts of a subassembly),
`book_components_project` (Project across components), `book_components_move` (pivot,
paste, Move to Component), `book_components_pattern` (Mirror and Rectangular Pattern of
components), `book_components_menus` (menus, Isolate, drag, the empty body),
`book_components_primitive` (Box in the active component); unit tests in
`test_components_core.py`, a headless check `headless/component_refs_check.py` (run by
`unit/test_component_refs_freecad.py`).

### Sources (search excerpts; Autodesk's sites cannot be opened from the sandbox)

21. **Autodesk** Learn, *Project geometry into a sketch* / *Sketch basics*: after Create
    Sketch "the new Sketch feature displays in the Timeline and in the Browser, nested
    within the active component"; Project "allows you to project geometry from anywhere in
    your design into the active sketch". With source 1 (API manual: geometry made through
    the UI goes into the active component): **new things go into the active component,
    whatever was clicked.** The report was right.
22. **Forum**, *The active component will switch itself*: a user saw the active component
    change when a face was picked for a sketch; the answer: an existing sketch was picked,
    Fusion does not switch the active component for a new sketch.
23. **Autodesk** training (Fusion CAM 2.5-axis cert prep): "the Operation type is set to
    create a New Body in the active component"; **Forum**, *Cannot Join Bodies with
    Extrude* and *Extrude New Components From Component*: a Join "works when you activate
    the component you want to join to", otherwise "it has to be New Body, as there is nothing
    in the other Component to join to"; two bodies in different components cannot be joined.
24. **Autodesk** knowledge, *How to extrude from one component to cut another component*:
    choose Operation Cut and, under Objects to Cut, the component to cut from; **Forum**:
    "even making the component active, using the cut/hole feature will still affect other
    component". So a Cut reaches bodies of other components, a Join does not. (The report's
    bug 10 said Fusion starts a new component's first extrude as New Body: confirmed for
    the operation proposed by itself; a Cut chosen by hand still cuts other components.)
25. **Autodesk** blog, *Introducing Ground to Parent* (2024) and help *Ground and unground
    components*: "the first component created at each layer of the sub-assembly, whether
    internal or externally referenced, will be Ground to Parent by default"; Preferences >
    Design > Assemblies > "First component Ground to Parent"; right-click > "Unground From
    Parent"; "if it is grounded to parent, the first component you select when you create a
    joint is automatically ungrounded from parent". The report was right (and the menu is
    named Ground to Parent, not Ground).
26. **Forum**, *Rotating Assemblies?* / *Set body pivot point*: "the pivot point for an
    assembly ... is at the assembly origin"; Set Pivot lasts for the command only. **Book**
    (the report quoting it): a pasted copy turned by Move turns about its origin.
27. **Autodesk** help, *Copy / paste a component*: after Paste "the Move/Copy dialog
    displays"; where the paste stands is not said (**Guess**: on the occurrence copied; the
    report expected Bolt:5's place).
28. **Forum**, *Should mirroring components preserve their joints*, *Mirror feature*: a Fusion
    community manager: "Mirror in Fusion is for producing true 'mirrored' components and
    bodies, meaning a 'left' and 'right' handed version of a component with different
    geometry. These are always new part numbers"; staff: "mirroring components does not
    mirror the joints".
29. **Forum** (*Component Gets Rotated But Not All Sub-Components Rotate With It*, staff
    answers on flexible subassemblies): "in Fusion, all sub-assemblies are flexible":
    a part of a subassembly is moved and dragged on its own. **Guess** from that and the
    book's steps: a click in the window picks the part clicked (the nearest component),
    the browser row picks a whole subassembly.
30. When Fusion fills From Bodies by itself: not found in a source. **Guess**: when bodies
    are selected (as bodies) when New Component starts; never from a face, a sketch or a
    timeline step.

### Where each command puts its result

| Command | Fusion | Fission 180 before (3.3.10) | Fission 180 now |
|---|---|---|---|
| Create Sketch on a face or plane of another component | the active component (21) | the clicked face's body, and that component became the active one (bug 5) | the active component's body; the sketch hangs on a hidden reference to the face (`components.reference_binder`, a plane: a hidden plane on it); the active component does not change |
| Create Sketch on a face of another body of the active component | the active component | the clicked body | the same (FreeCAD keeps a sketch in one body; same component) |
| Extrude / Revolve / Sweep / Loft, Operation New Body | a new body in the active component (23) | beside the profile's body (bug 6) | the active component (`components.body_for_new`), standing where the profile is |
| ... Operation New Component | a new component under the active one | the same | the same |
| ... Operation Join | only bodies of the active component (23) | every shown body it touched, any component | only bodies of the active component count (`components.may_change`); touching none: New Body |
| ... the operation proposed by itself | New Body unless a body of the active component is touched or entered (23) | Join / Cut from bodies of any component (bug 10) | from the active component's bodies only |
| ... Operation Cut, chosen by hand | every body in its way (Objects To Cut), any component (24) | the same | the same |
| CONSTRUCT planes, axes, points | the active component (1) | the body of the first pick (bugs 7, 8) | the active component's body (`construct.target_body`); the frame follows the picks in design coordinates |
| Primitives (Box ...) | the active component | an empty active component: the design's root (and the root became active); New Body on another component's face: that component | the active component (`primitives_ui._ensure_body`, `primitives.new_body` -> `components.body_for_new`); the component's own origin plane picked in the browser is taken |
| Hole, Thread, Fillet, Chamfer, Shell, Draft (change a body) | change the body picked | the same | the same |
| Patterns and Mirror of features / faces / bodies | in the body of what is repeated | the same | the same |
| Pattern / Mirror of components | a step of the design; the copies beside the original | patterns: the same; Mirror: not built | the same; Mirror built |
| Canvas | the active component | the active component's body | the same (checked again by components-2: `insert_ui` takes `commands.ensure_body()`) |
| Decal | the active component (Guess: a new object) | the component of the body whose face it is put on (`decal.make`: it is drawn in that component and moves with it) | the same: not the active component when the face is another component's (components-2 corrected this row, which said "the active component's body"); the decal is always on the face clicked |
| Joints, Rigid Groups, Motion Links | the active component's Joints folder | the design's hidden assembly | the same (one Joints folder: FreeCAD's assembly holds them) |
| New Component | under the active component (Parent box) | the same | the same; Parent can be clicked in the browser |
| Paste | the active component | the same | the same, standing on the occurrence copied |

### What else changed (wave 7)

| Fusion | Fission 180 |
|---|---|
| Project (P) takes geometry of any component (21) | While FreeCAD's Project (or Include 3D Geometry) runs, a click on a face, edge or corner of another body or component is projected through a hidden reference inside the sketch's body. One undo step per click; the message beside the mouse says how many curves came from which component; an element projected already says so |
| A projection follows the part it came from; a later Move or joint does not reshape what was modelled on a part | The reference (`components.ReferenceCopy`, a hidden sketch-like object in the sketch's body) depends on the step it copies and stands where the other body stood when it was made: it follows the other part's CHANGES (a pin made thicker), also after save and reopen and when FreeCAD marks the element name as missing; it does not follow later MOVES of either component (Fusion works a projection out where the parts stood at the sketch's place in the timeline; `extrude.py`'s profile copies keep their frame for the same reason). A step of the other body may use what hangs on it |
| New Component: From Bodies | Ticked by itself only when bodies are selected as bodies when the command starts (30); the dialog says "N bodies will move into the new component: ..."; a click on a component's browser row with From Bodies off sets Parent |
| The first component of each level is grounded to its parent (25) | Same (New Component, Create Components from Bodies): a Ground on it, in the same undo step. Preferences > General > Design > *First component Ground to Parent* (on). Menu: Ground to Parent / Unground From Parent |
| Move/Copy of a component: the manipulator on its origin (26) | Same (`ComponentMovePanel._new_pivot`: the first picked component's origin); Set Pivot as before |
| Paste stands on what was copied (27, guess) | Same for Paste and Paste New (a copy of Bolt:5 starts on Bolt:5) |
| A click picks the part clicked, also inside a subassembly (29, guess) | `components_core.component_to_pick`: the nearest component (Move's Components, patterns of components); a browser row picks a whole subassembly |
| A nested component's browser row is that component | `components.whole_pick`: the joint dialogs read the selection through its containers and took the top-level subassembly (bug 15) |
| Mirror, Pattern Type Components: a mirrored component (28) | One Mirror step with one copy whose solids are mirrored across the plane; it follows the original, is edited, rolled back and deleted like a pattern of components; joints are not mirrored (Fusion neither) |
| Mirror / patterns start with any component active | They open when the active component has no solid but the design has components, with Pattern Type Components |
| Isolate another component while one is isolated | Its menu offers Isolate (it only offered Exit Isolate) |
| The design's row of an assembly: stacked blocks | The `assembly` icon when the design holds components |
| Component menu: Move/Copy, Create Drawing, Properties | Move/Copy (Move opens on the component), Create Drawing (the DRAWING workspace's command), Properties (shown once the Properties command exists) |
| Drag a row onto a component | It lands on the row under the pointer when the button is let go (the tree is rebuilt after every drop) |
| Move to Component | An empty body Fission 180 made for a sketch that went elsewhere is removed when the body with the part arrives (`components.drop_unused_bodies`); new work prefers a body with something in it |

### FreeCAD facts (1.1.4, probed)

- `Sketch.addExternal` and FreeCAD's Project tool refuse every object outside the sketch's own
  body ("is not allowed as external geometry of this sketch"; the tool's pointer turns into a
  no-entry sign and stays so until the mouse moves).
- A sketch attached straight to a face of a step in another `App::Part` ignores both parts'
  Placements (it is right only while neither component was moved).
- A `PartDesign::SubShapeBinder` with `Relative` on follows both components only when its
  Support starts at the first container the binder's body is NOT in and names the path from
  there (`(B, "Body.Pad.Face6")` for a sibling, `(Outer, "B.Body.Pad.Face6")` from the root,
  `(Body, "Pad.Face6")` for another body of the same component). Linked straight to the step
  it ignores the other component's Placement; linked through a container both are in, the
  document is no longer a DAG. Such a binder depends on the whole other component: a step of
  that component that uses what hangs on the binder (a Cut of the Nozzle from a sketch put on
  the Nozzle's face) is a dependency cycle, and every joint move reshapes what was modelled
  on it. Not Relative and linked straight to the step, it loses the element's own location
  (a pad's top face lands at z 0) and does not get it back when the step changes. So the
  reference is Fission 180's own object (`ReferenceCopy`).
- An element of a shape carries a location (`shape.Placement`, the pad's height for its top
  face); `transformShape(matrix, True)` keeps it, and FreeCAD replaces it by the object's
  Placement when the shape is given to an object: set the element's Placement to none and
  work `frame * location` into the geometry (`shape.transformed(matrix, True)`).
- A link to an element whose history changed (the sketch behind the step drawn again) reads
  back as `?Edge3`; `Shape.getElement("?Edge3")` raises. The plain name is tried then.
- `Gui.Selection.getSelectionEx("", 0)` gives a nested component selected by its name as its
  top container with the sub path ("Stator", "Housing.").
- `doc.openTransaction()` only names a pending step; `abortTransaction()` on a step without a
  change does nothing, and the next change anywhere becomes a step under that name:
  `App.closeActiveTransaction(True)` closes it.

## Part 4: commands aimed at another component, grounded first components, copies with structure (wave 7, components-2, 2026-11-11)

Built in `components.py` (`active_component` as the person's choice, `settle_active`,
`outside_tips`, `outside_note`, `home_text`, `activate_result`), `taskui.Panel._close` and
`commands.finish_open_dialog` (the hooks), `fillet_ui.py` (a first click on another body),
`plastic_rest.body_under`, `instances.py` (nested structure, mirrored names),
`component_move.refusal`, `component_move_ui._cancel_paste`, `clipboard_ui.py`,
`construct.py` (`_freeze`, `_frozen_world`), `components_ui.py` (Internal / External),
`align_ui.py` (a grounded component). Tests: scenarios `book_components2_cross`,
`book_components2_structure`, `book_components2_refs`; the three `journey_plastic*`; unit
tests in `test_components_core.py`.

### Sources (search excerpts; Autodesk's sites cannot be opened from the sandbox)

31. **Forum**, *Cannot Join Bodies with Extrude*, *Recurring problem with Join vs New
    Body*, *Extrude join to specific body*: a Join reaches the bodies of the active
    component only; "activate the component you want to join to". (Checked again for this
    work: the wave 7 rule stays.)
32. **Autodesk** help, *Snap Fit* (SLD-SNAP-FIT): "Assign a plastic rule to the components
    that contain the bodies"; *Boss* (SLD-BOSS): "fasten two solid bodies together";
    *Lip* (SLD-LIP): "a lip and groove on a pair of solid bodies". The PLASTIC tools work on
    bodies of several components at once, so they change bodies outside the active one.
33. **Autodesk** help, *Bodies* / *QUICK TIP: Body v Component*: bodies are modified "with
    commands like Fillet, Chamfer, Shell, Draft, Combine, and Split Body"; **AU 2016
    handout** (Doering): Fusion works out which component a new fillet or chamfer belongs
    to without activation; **Forum** (source 24): "even making the component active, using
    the cut/hole feature will still affect other component". No source says that a command
    aimed at a body of another component switches the active component: **Guess**, from
    all of these and from source 22 ("Fusion does not switch the active component for a new
    sketch"), that it never does.
34. **Forum**, *To move a grounded object, must always first unground?* (accepted answer):
    "to move a component, whether by dragging or using the move feature, you have to first
    unground it from the parent"; a user in the same thread: Move Object Components "would
    not select a grounded component". **Autodesk** blog *Ground to Parent*: when a moved
    component is grounded again, Fusion offers "Update Initial Position".
35. **Forum**, *Copy/move dialog appears when paste new is used* (Autodesk staff): "It
    pastes the new body/component/whatever in place, then immediately invokes Move so you
    can reposition the copy"; *Comportement of the C/P Cancel button* (Fusion community
    manager): cancelling should cancel the Paste, not just the Move. (Source 27's guess
    "the paste stands on what was copied" is confirmed: in place.)
36. **Forum**, *How to properly create a mirrored component?*: Fusion treats a mirror of
    components "as if everything was copied, PASTE NEW, and reversed"; with source 28 ("a
    left and right handed version ... always new part numbers"): a mirrored component is a
    component of its own. Its name in the browser was not found in a source: **Guess**
    "Name (Mirror)".
37. **Autodesk** help, *Create a rectangular pattern*: "Components duplicates components in
    an assembly"; **Book** (the report, Robotic Hand 2406-2409): the copies of a patterned
    subassembly are subassemblies with their parts and joints.
38. **Autodesk** help, *New Component* (excerpts): Internal "creates the component within
    the current design", External creates it "as a separate design" that the design
    references (X-ref), edited in place.
39. Construction on another component: no source found. **Guess** from the timeline model
    (sources 13, 21: a projection and a captured position are worked out at their place in
    the timeline): a plane built on another component's face does not move when that
    component is moved later.

### A command aimed at a body of ANOTHER component (component A active, the pick on B)

Probed by real input on 3.3.10 + wave 7 before any change (the probe became the scenario
`book_components2_cross`). "Switched" = B silently became the active component.

| Command | Fusion (source or Guess) | Fission 180 before | Fission 180 now |
|---|---|---|---|
| Fillet, Chamfer (edge clicked after the command started) | rounds the edge clicked (33, Guess) | the click was not taken, no word (only the dialog's own body could be picked); OK then said "Select the edges ... first" | the dialog moves to the body of the first edge or face clicked; A stays active; with picks already, a click on another body says "One fillet step works on one body ..." |
| Fillet, Chamfer (edge selected before the command) | the same | worked on B's body, switched | works on B's body, A stays active |
| Shell | hollows the body picked (33) | worked, switched | works, A stays active |
| Hole | drills the face picked (24: "will still affect other component") | worked, switched | works, A stays active |
| Thread | threads the face picked (Guess) | worked, switched | works, A stays active |
| Press Pull (a face) | moves the face picked (Guess) | worked, A stayed | the same |
| Extrude, Operation Cut chosen by hand | cuts every body in its way (24) | worked (the first builder's "does not go through any body" did not reproduce: the cut went through B), switched after OK | works, A stays active |
| Extrude, Join / the proposed operation | bodies of the active component only (31) | wave 7: the same | the same |
| Split Body | splits the body picked (33) | worked, A stayed; the new piece is in B | the same |
| Combine | changes the target picked (33) | worked, A stayed | the same |
| Mirror / patterns of bodies | the copy beside its original (Guess) | worked, A stayed; the copy is in B | the same |
| PLASTIC Boss, Snap Fit, Lip | work on the bodies they are aimed at, in several components (32) | worked | the same |
| PLASTIC Rest | the body under the profile (32, Guess) | built in the body the profile's SKETCH was in (the active component's), nowhere near, no word | the body nearest to the profile; the dialog names it with its component and says it is not in the active component |
| SHEET METAL Flange (an edge) | the sheet metal body of the edge (Guess) | worked, A stayed | the same |
| Create Sketch, CONSTRUCT, primitives, New Body results | the active component (21, 23) | wave 7: the active component | the same |

Every row: the step itself is in B's body (FreeCAD keeps a step inside its body), so with A
active it does not show in A's timeline. Fusion lists such a step under the component that
was active. So that this is never silent, when a dialog closes on OK and a body outside the
active component was changed, a note next to the mouse says "Body1 is in B, not in the
active component A: the step changes it there. Activate it there to see the step in its
timeline." (a new body: "The new body Body5 is in B, beside the body it was made from").
With the design itself active nothing is said: its timeline shows every step.

How: `components.active_component` is now what the person chose (the ring, Activate, New
Component, a body activated in the browser, an edited step); before, it was read from the
active body, and Shell, Hole, Thread, Fillet and the pick panels make the body they work on
the active body. `components.settle_active` gives the active component its own body back
when a dialog closes (and before the next command).

### The first component is grounded (the test harness no longer switches it off)

| Command, on a grounded component | Fusion | Fission 180 |
|---|---|---|
| Move/Copy, Move Object Components | cannot be picked; unground first (34) | refused in the dialog: "Bracket is grounded, so it cannot move. Unground it first (right-click it in the browser > Unground From Parent)" |
| Drag in the window | does not move (34) | says why, names Unground From Parent (joints, wave 7) |
| Joint, first component picked | ungrounded by itself (25) | the same (joints, wave 7) |
| Align, Objects Components | cannot move (34; Guess for Align) | refused with the same sentence (it moved the component without a word) |
| Create Components from Bodies, New Component | the first of a level is grounded (25) | the same |
| Paste, patterns, Mirror, Duplicate With Joints | copies are new occurrences, not grounded (Guess) | the same |

### Copies with structure, mirrored names, Paste, construction, Internal / External

| Fusion | Fission 180 |
|---|---|
| A pattern's copies, a pasted copy and a Create Copy of a subassembly are occurrences with the components inside (37) | An instance keeps a component per nested component of its source ("holders": `instances.NESTED_OF`), named and nested like it, with the copy bodies inside; the browser shows them as rows. The copy features place the solids, so a part moved inside the original moves in every copy. A holder cannot be moved on its own (refused: "... is part of the copy Stator:2: move Bolt in the original"); its ring activates the original's part. Instances saved before this stay flat (joints made on them keep their references) |
| A mirrored component is a component of its own (28, 36) | Named "Name (Mirror)" (then "Name (Mirror) (1)"); it is not counted as an occurrence, so the original is not shown as "Name:1" because of it. It still follows the original and is edited through it (a gap, below) |
| Paste: pasted in place, Move/Copy opens on it; Cancel cancels the Paste (35) | Same: Esc or Cancel in that Move takes the paste away again ("Paste cancelled: the copy was removed"); OK or the next command keeps it |
| A construction built on another component does not move with that component's later moves (39, Guess) | Same as a sketch's reference: the frame is worked out with the picked bodies where they stood, for the construction's own body, when it was made (`ConstructionFrame.Home / Frames`); it follows the other part's CHANGES, not later MOVES of either component. Constructions saved before this freeze at their first recompute |
| New Component: Internal / External (38) | "Saved: Internal / External"; External is greyed, with the reason and what to do instead in its tooltip (one design per file; linked designs are locked until Break Link, so an empty one could not be modelled in) |

## Known gaps (honest list)

- Wave 7: snapping and inference to another component's geometry while drawing, and a
  dimension that references a model edge by itself (Fusion's "Auto project edges on
  reference") are not built: press P and click the edge first (that now works across
  components), then snap or dimension to the projected curve. The function to call is
  `sketch_external.project_across(sketch, object, "EdgeN")` (the drawing and dimension tools
  are the sketch builders').
- Wave 7 (components-2): New Component shows Internal / External with External greyed (an
  External component is a design of its own on disk, edited in place; Insert into Current
  Design links a saved design, but cannot start an empty one or edit it in place). Create
  Selection Set is not built (Fission 180 has no selection sets).
- Wave 7 (components-2): a step made on a body outside the active component (a Hole, a Cut,
  a Fillet, a Rest on another component's part) is a step of that body's component here
  (FreeCAD keeps a step inside its body); Fusion lists it under the component that was
  active. It is said next to the mouse when the dialog closes; the step shows in that
  component's (and the design's) timeline.
- Wave 7 (components-2): one Fillet / Chamfer step rounds edges of one body (Fusion's takes
  edges of several bodies); a click on a second body says so.
- Wave 7 (components-2): "First component Ground to Parent" grounds the first component
  CREATED at a level (New Component, Create Components from Bodies:
  `components_ui.ground_first`). The first one made by Extrude > New Component is not
  grounded here (Fusion's blog says "the first component created at each layer": a gap). An
  INSERTED part is not grounded (the hardware builder's finding for Fusion; kept). Editing
  a step of another component from the timeline still makes that component the active one.
- Wave 7: with the design's row active, a sketch on a face of a component's body goes into the
  root (Fusion does the same) and its extrude makes a New Body at the root unless Cut is
  chosen; activate the component first to add to its body, as in Fusion.
- Ghosting, the marker and instances are built (components-2); what is still missing:
- A component made from bodies that existed before it (Create Components from Bodies) stays
  shown when the marker stands before its step (Fusion puts the body back at the root): hiding
  it would hide the body.
- Sheet Metal components, External components (a component as its own file), Opacity Control,
  Selectable, component colour cycling and Properties are not built.
- A sketch that sits outside every body cannot exist in FreeCAD's PartDesign, so "a sketch at
  the root while the body goes to a component" (Fusion's Create Components from Bodies) is
  approximated: the body's sketches move with the body.
- The New Component dialog's Parent is a drop-down, not Fusion's click-in-the-browser box.
- Instances: editing happens through the original (activating an instance, or a part
  inside it, activates the original; a sketch put directly on an instance's face goes into
  the instance's copy body only, Fusion would edit the component); a part inside a copy of
  a subassembly cannot be moved or jointed on its own (it stands where the original's part
  stands; refused with the reason), and the copies have no joints of their own (they show
  the pose the original's joints give it); instances saved before wave 7 stay flat (no
  rows for the parts inside);
  deleting the original hands over to an occurrence, but the original's features (its
  timeline steps) and decals go with the original: the occurrence that takes over keeps
  the solids as frozen bases (Fusion keeps the features in the component; Undo brings
  them back), and a pattern's copies of the original stay frozen; a body deleted from an
  instance comes back at the next sync.
- A pattern's copies cannot be moved on their own (refused with the reason). A mirrored
  component (wave 7) is named "Name (Mirror)" but is still a copy whose solids are
  mirrored and that is edited through its original, not a new component with features of
  its own as in Fusion; joints are not mirrored (Fusion neither).
- A component move that is not captured, in a design without joints, cannot be reverted
  (joints' Capture Position / Revert need the joints' assembly); Fusion asks to capture or
  revert before the next feature (not built: the pending position simply stays). Rolling the
  marker over a captured move recomputes the component's position from its captured moves, so
  a pending (uncaptured) move of that component made after them is dropped.
- Joints on instances work like on any component, but a joint between two occurrences of one
  component is not special-cased.
- Selection filters / priority Components (SELECT menu) and Component Drag in the canvas belong
  to the selection and joints-2 work.
- No "New Body" command (Fusion has none: bodies come from features).
- STEP files open and insert as components (exchange-2, parity/insert-export.md Part 2): a
  repeated part is an instance; another Fission 180 design inserts as one linked component
  (Break Link copies its features in); both bring nested components of an inserted design
  in flat only where noted there.
